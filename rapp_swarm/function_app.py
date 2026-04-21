"""
rapp_swarm/function_app.py — Tier 2 Azure Functions adapter over the /chat contract.

Sacred constraints honored here (CONSTITUTION.md):

  • Article I — the brainstem stays light. This file is: boot + LLM loop
    + response split + agent discovery + auth. Nothing else.
  • Article XIV — swarms are directories, not routes. No /api/swarm/<guid>
    surface. Multi-swarm operations are handled by agent files (deploy,
    list, invoke, seal, snapshot, delete) that live in BRAINSTEM_HOME/
    agents/ and are exposed via the tool-calling loop on /api/chat.
  • Article XV — tier parity. Same /chat loop, same prompt split, same
    agent contract, same state layout as rapp_brainstem/brainstem.py.
    Only the mount point for state differs (Azure Files vs local disk).
  • Article XVI — state lives in .brainstem_data/. Here the Tier 2
    equivalent is BRAINSTEM_HOME (defaults to /tmp/.rapp-swarm; mount an
    Azure Files share at that path for durable per-twin persistence).

Wire surface:

    POST /api/chat                          primary chat endpoint
    POST /api/businessinsightbot_function   OG community-RAPP wire alias
    POST /api/trigger/copilot-studio        direct-invoke shape (Tier 3)
    GET  /api/health                        health probe
    GET  /api/llm/status                    which LLM provider is wired

LLM backend precedence (see llm.py):
    1. Azure OpenAI via API key   (AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_API_KEY)
    2. OpenAI                      (OPENAI_API_KEY)
    3. Anthropic                   (ANTHROPIC_API_KEY)
    4. Fake stub                   (LLM_FAKE=1, for tests)
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import logging
import os
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

import azure.functions as func


# ── Path setup ─────────────────────────────────────────────────────────
# rapp_swarm/build.sh vendors the brainstem core dependencies into
# ./_vendored/ before `func azure functionapp publish`. Locally, sibling
# ../rapp_brainstem/ also works for direct invocation.

_HERE = Path(__file__).resolve().parent
for _candidate in (_HERE / "_vendored", _HERE.parent / "rapp_brainstem"):
    if _candidate.is_dir() and str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))


def _load_dotenv() -> None:
    """Stdlib .env loader — no python-dotenv dependency."""
    candidates = []
    if os.environ.get("RAPP_DOTENV"):
        candidates.append(Path(os.environ["RAPP_DOTENV"]))
    candidates += [_HERE / ".env", _HERE.parent / ".env", Path.cwd() / ".env"]
    for p in candidates:
        if p and p.is_file():
            try:
                for line in p.read_text().splitlines():
                    s = line.strip()
                    if not s or s.startswith("#") or "=" not in s:
                        continue
                    k, v = s.split("=", 1)
                    k, v = k.strip(), v.strip()
                    if v and v[0] in ('"', "'") and v[-1] == v[0]:
                        v = v[1:-1]
                    os.environ.setdefault(k, v)
                return
            except Exception:
                continue


_load_dotenv()


# ── Dependencies (vendored by build.sh) ────────────────────────────────

from utils.llm import chat as llm_chat, detect_provider, provider_status  # type: ignore

try:
    from utils import twin as _twin  # type: ignore
except ImportError:
    _twin = None  # calibration gracefully disables if helper absent

# Import path for agents to find BasicAgent. The shim under _vendored/utils/
# rewires `agents.basic_agent` → the same class Tier 1 uses.
try:
    from utils import _basic_agent_shim  # type: ignore  # noqa: F401 — side-effect only
except ImportError:
    pass


# ── State root (Article XV — mount point is the only tier difference) ──

_BRAINSTEM_HOME = Path(os.environ.get("BRAINSTEM_HOME", "/tmp/.rapp-swarm")).expanduser()
_BRAINSTEM_HOME.mkdir(parents=True, exist_ok=True)
_AGENTS_DIR = _BRAINSTEM_HOME / "agents"
_AGENTS_DIR.mkdir(parents=True, exist_ok=True)
_SOUL_FILE  = _BRAINSTEM_HOME / "soul.md"


MAX_TOOL_ROUNDS = 4

# Per CONSTITUTION Article XVII / XII — agents/ is a user-organized
# tree; these subdir names are the ONLY excluded branches on discovery.
_AGENTS_EXCLUDED_SUBDIRS = frozenset({
    "experimental_agents",   # in-flight, hand-load only
    "disabled_agents",       # turned off
    "__pycache__",
})


# ── Agent discovery (mirrors brainstem.py's recursive walk) ────────────

def _load_agents() -> dict:
    """Discover every `*_agent.py` under AGENTS_DIR recursively (matching
    brainstem.py). Skips the two reserved subtrees (experimental_agents/,
    disabled_agents/). Reloaded per request so file edits take effect
    without a restart (parity with Tier 1).
    """
    # Lazy-import BasicAgent from the shim so the class identity matches
    # what the agent files themselves extend.
    try:
        from agents.basic_agent import BasicAgent  # type: ignore
    except ImportError:
        # Fallback: define a minimal BasicAgent for the shim.
        class BasicAgent:  # type: ignore
            pass

    agents: dict = {}
    if not _AGENTS_DIR.is_dir():
        return agents

    def _discoverable():
        for py_file in sorted(_AGENTS_DIR.rglob("*_agent.py")):
            if py_file.name == "basic_agent.py":
                continue
            rel_parts = py_file.relative_to(_AGENTS_DIR).parts
            if any(part in _AGENTS_EXCLUDED_SUBDIRS for part in rel_parts[:-1]):
                continue
            yield py_file

    for py_file in _discoverable():
        mod_name = f"_tier2_{py_file.stem}"
        spec = importlib.util.spec_from_file_location(mod_name, py_file)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            logging.warning("agent import failed %s: %s", py_file.name, e)
            continue
        for _cls_name, obj in inspect.getmembers(module, inspect.isclass):
            if obj is BasicAgent:
                continue
            if issubclass(obj, BasicAgent):
                try:
                    inst = obj()
                    name = getattr(inst, "name", None)
                    if name:
                        agents[name] = inst
                except Exception as e:
                    logging.warning("agent init failed %s: %s", py_file.name, e)
    return agents


def _load_soul() -> str:
    """Read BRAINSTEM_HOME/soul.md. Empty string if absent."""
    if _SOUL_FILE.is_file():
        try:
            return _SOUL_FILE.read_text().strip()
        except OSError:
            return ""
    return ""


def _agent_to_tool(agent) -> dict:
    md = getattr(agent, "metadata", {}) or {}
    return {
        "type": "function",
        "function": {
            "name": md.get("name", getattr(agent, "name", "agent")),
            "description": md.get("description", ""),
            "parameters": md.get("parameters", {"type": "object", "properties": {}}),
        },
    }


def _compose_system(soul: str, agents: dict, extra: str = "") -> str:
    parts = []
    if soul:
        parts.append(soul)
    for a in agents.values():
        try:
            ctx = a.system_context() if hasattr(a, "system_context") else None
            if ctx:
                parts.append(ctx.strip())
        except Exception:
            pass
    if extra:
        parts.append(extra.strip())
    return "\n\n".join(p for p in parts if p)


def _parse_voice_twin_split(content: str):
    """Split on |||VOICE||| then |||TWIN|||. Returns (main, voice, twin).
    Mirror of brainstem.py's split (Article XV — same prompt split)."""
    if not content:
        return "", "", ""
    main, sep, rest = content.partition("|||VOICE|||")
    if not sep:
        return content.strip(), "", ""
    voice, _, twin = rest.partition("|||TWIN|||")
    return main.strip(), voice.strip(), twin.strip()


# ── Chat loop (parity with brainstem.py's handler structure) ───────────

def run_chat(user_input: str,
             conversation_history=None,
             session_id: str | None = None,
             extra_system: str = "") -> dict:
    """Run one /chat turn. Returns the response envelope Tier 1 returns.

    Shared signature + behavior with the Tier 1 handler in brainstem.py
    so parity tests can call both and diff the envelope.
    """
    soul = _load_soul()
    agents = _load_agents()
    tools = [_agent_to_tool(a) for a in agents.values()] if agents else None

    system = _compose_system(soul, agents, extra=extra_system)

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    for m in (conversation_history or []):
        if isinstance(m, dict) and m.get("role") in ("user", "assistant", "tool", "system"):
            messages.append(m)
    messages.append({"role": "user", "content": user_input})

    provider = detect_provider()
    agent_logs: list = []

    for round_i in range(MAX_TOOL_ROUNDS):
        try:
            assistant = llm_chat(messages, tools=tools)
        except Exception as e:
            logging.exception("LLM call failed")
            return {
                "response": f"LLM error: {e}",
                "session_id": session_id,
                "agent_logs": "\n".join(agent_logs),
                "provider": provider,
                "error": str(e),
            }
        messages.append(assistant)

        tool_calls = assistant.get("tool_calls") or []
        if not tool_calls:
            break

        for call in tool_calls:
            fn = (call.get("function") or {})
            name = fn.get("name", "")
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except Exception:
                args = {}
            agent = agents.get(name)
            t0 = time.time()
            if agent is None:
                output_str = json.dumps({"error": f"unknown agent: {name!r}"})
                status = "error"
            else:
                try:
                    raw = agent.perform(**args)
                    output_str = raw if isinstance(raw, str) else json.dumps(raw)
                    status = "ok"
                except Exception as e:
                    output_str = json.dumps({"error": f"{type(e).__name__}: {e}"})
                    status = "error"
                    logging.exception("agent %s raised", name)
            ms = int((time.time() - t0) * 1000)
            agent_logs.append(f"{name} ({status}, {ms}ms): {output_str[:200]}")
            messages.append({
                "role": "tool",
                "tool_call_id": call.get("id", ""),
                "name": name,
                "content": output_str,
            })

    raw = assistant.get("content") or ""
    main, voice, twin = _parse_voice_twin_split(raw)

    if _twin:
        try:
            twin, _probes, _calibs, telemetry = _twin.parse_twin_tags(twin)
            if telemetry:
                for line in telemetry.splitlines():
                    if line.strip():
                        print(f"[twin-telemetry] {line.strip()}", flush=True)
        except Exception:
            pass

    return {
        "response": main,
        "voice_response": voice,
        "twin_response": twin,
        "session_id": session_id,
        "agent_logs": "\n".join(agent_logs),
        "provider": provider,
        "model": (
            os.environ.get("AZURE_OPENAI_DEPLOYMENT")
            or os.environ.get("OPENAI_MODEL")
            or os.environ.get("ANTHROPIC_MODEL")
            or "fake"
        ),
    }


# ── Azure Functions app + HTTP glue ────────────────────────────────────

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


def _build_cors(origin):
    return {
        "Access-Control-Allow-Origin": str(origin) if origin else "*",
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Max-Age": "86400",
    }


def _json_response(status, payload, origin=None):
    return func.HttpResponse(
        body=json.dumps(payload),
        status_code=status,
        mimetype="application/json",
        headers=_build_cors(origin),
    )


def _read_json(req) -> dict:
    try:
        return req.get_json() or {}
    except Exception:
        body = (req.get_body() or b"").decode("utf-8")
        if not body.strip():
            return {}
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {}


def _do_chat(req: func.HttpRequest) -> func.HttpResponse:
    origin = req.headers.get("origin")
    if req.method == "OPTIONS":
        return _json_response(204, {}, origin)
    body = _read_json(req)
    user_input = str(body.get("user_input") or body.get("input") or "").strip()
    if not user_input:
        return _json_response(400, {"error": "Missing or empty user_input"}, origin)
    history = body.get("conversation_history") or []
    if not isinstance(history, list):
        history = []
    session_id = body.get("session_id") or str(uuid.uuid4())

    try:
        result = run_chat(user_input, conversation_history=history, session_id=session_id)
        return _json_response(200, result, origin)
    except Exception as e:
        logging.exception("chat path failed")
        return _json_response(500, {"error": "Internal server error", "details": str(e)}, origin)


@app.function_name(name="chat")
@app.route(route="chat", methods=["POST", "OPTIONS"])
def chat(req: func.HttpRequest) -> func.HttpResponse:
    return _do_chat(req)


@app.function_name(name="businessinsightbot_function")
@app.route(route="businessinsightbot_function", methods=["POST", "OPTIONS"])
def businessinsightbot_function(req: func.HttpRequest) -> func.HttpResponse:
    """OG community-RAPP wire alias — same shape as /api/chat."""
    return _do_chat(req)


@app.function_name(name="copilot_studio_trigger")
@app.route(route="trigger/copilot-studio", methods=["POST", "OPTIONS"])
def copilot_studio_trigger(req: func.HttpRequest) -> func.HttpResponse:
    """Direct-agent-invoke shape for Tier 3 Copilot Studio integrations."""
    origin = req.headers.get("origin")
    if req.method == "OPTIONS":
        return _json_response(200, {}, origin)
    body = _read_json(req)
    agent_name = body.get("agent")
    action = body.get("action")
    if not agent_name or not action:
        return _json_response(400, {"error": "Missing 'agent' and 'action' fields"}, origin)
    params = body.get("parameters") or {}
    params["action"] = action

    agents = _load_agents()
    agent = agents.get(agent_name)
    if agent is None:
        return _json_response(404, {
            "status": "error",
            "error": f"unknown agent: {agent_name!r}",
            "copilot_studio_format": {
                "type": "event", "name": "agent.error",
                "value": {"success": False, "message": f"unknown agent: {agent_name!r}"},
            },
        }, origin)

    try:
        raw = agent.perform(**params)
        output = raw if isinstance(raw, str) else json.dumps(raw)
    except Exception as e:
        logging.exception("copilot-studio invoke failed")
        return _json_response(500, {
            "status": "error", "error": str(e),
            "copilot_studio_format": {
                "type": "event", "name": "agent.error",
                "value": {"success": False, "message": str(e)},
            },
        }, origin)

    return _json_response(200, {
        "status": "success",
        "response": output,
        "copilot_studio_format": {
            "type": "event", "name": "agent.response",
            "value": {"success": True, "message": str(output)},
        },
    }, origin)


@app.function_name(name="health")
@app.route(route="health", methods=["GET", "OPTIONS"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    origin = req.headers.get("origin")
    if req.method == "OPTIONS":
        return _json_response(204, {}, origin)
    try:
        agents = _load_agents()
    except Exception as e:
        agents = {}
        health_body = {"status": "unhealthy", "error": str(e)}
    else:
        health_body = {
            "status": "healthy",
            "agent_count": len(agents),
            "agents": sorted(agents.keys()),
            "brainstem_home": str(_BRAINSTEM_HOME),
            "provider": detect_provider(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    return _json_response(200 if health_body["status"] == "healthy" else 503,
                          health_body, origin)


@app.function_name(name="llm_status")
@app.route(route="llm/status", methods=["GET", "OPTIONS"])
def llm_status(req: func.HttpRequest) -> func.HttpResponse:
    origin = req.headers.get("origin")
    if req.method == "OPTIONS":
        return _json_response(204, {}, origin)
    return _json_response(200, provider_status(), origin)
