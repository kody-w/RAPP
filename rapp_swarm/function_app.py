"""
hippocampus/function_app.py — The graduated brainstem in the cloud.

This is the OG CommunityRAPP Assistant pattern, ported to drive RAPP as a
whole: the same `Assistant` class, the same |||VOICE||| split, the same
sacred BasicAgent contract — but parameterized by `swarm_guid` so each
request loads THAT swarm's agents + memory, hot-swapped per call.

    POST /api/businessinsightbot_function   (sacred OG wire shape)
    POST /api/chat                          (alias)
    POST /api/trigger/copilot-studio        (sacred OG direct-invoke shape)
    GET  /api/health                        (sacred OG health probe)

Plus the Twin Stack swarm + T2T cloud surface (driven by swarm_guid):

    POST /api/swarm/deploy                  (push a rapp-swarm/1.0 bundle)
    GET  /api/swarm/healthz, /{guid}/healthz
    POST /api/swarm/{guid}/agent            (single-agent call)
    POST /api/swarm/{guid}/chat             (LLM-driven chat per swarm)
    GET/POST /api/swarm/{guid}/seal
    POST/GET /api/swarm/{guid}/snapshot, /snapshots, /snapshots/{snap}/agent
    GET/POST /api/t2t/identity, /peers, /handshake, /message, /invoke
    GET  /api/llm/status

Sacred:
  • `function_app.py` is the cloud brainstem.
  • Agents are `agents/*_agent.py` extending BasicAgent (rapp-agent/1.0).
  • `swarm_guid` selects which agent set + memory namespace per request.
  • Default sentinel GUID `c0p110t0-…` routes to shared memory inside a swarm.

Backend (in priority order):
  1. Azure OpenAI via API key   (AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_API_KEY)
  2. Azure OpenAI via MI/Entra  (AZURE_OPENAI_ENDPOINT only — uses ChainedTokenCredential)
  3. OpenAI                      (OPENAI_API_KEY)
  4. Anthropic                   (ANTHROPIC_API_KEY)
  5. Fake stub                   (LLM_FAKE=1, for tests)

Storage: BRAINSTEM_HOME env var (default /tmp/.rapp-swarm). For
per-twin durable persistence, mount Azure Files at this path in your
Function App's appSettings.
"""

import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import azure.functions as func


# ─── Path setup ─────────────────────────────────────────────────────────
# `rapp_swarm/build.sh` vendors the brainstem core into ./_vendored/
# before `func azure functionapp publish`. Locally, sibling ../rapp_brainstem/
# also works for direct invocation.

_HERE = Path(__file__).resolve().parent
for _candidate in (_HERE / "_vendored", _HERE.parent / "rapp_brainstem"):
    if _candidate.is_dir() and str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

# Twin calibration helpers — vendored alongside chat.py/llm.py.
try:
    import twin as _twin  # type: ignore
except ImportError:
    _twin = None  # calibration gracefully disables if the helper is missing


def _load_dotenv():
    """Stdlib .env loader (no python-dotenv dependency required)."""
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
                return p
            except Exception:
                continue
    return None

_load_dotenv()

# Now import the swarm core (vendored).
# Try `brainstem` first (the new name), fall back to `server` (the vendored alias).
try:
    from brainstem import SwarmStore, get_t2t_manager, SealedSwarmError  # type: ignore
except ImportError:
    from server import SwarmStore, get_t2t_manager, SealedSwarmError  # type: ignore
from chat import chat_with_swarm, diagnostics as llm_diagnostics  # type: ignore
from llm import chat as llm_chat, detect_provider  # type: ignore
from t2t import verify as t2t_verify  # type: ignore


# ─── Sacred constants (from OG CommunityRAPP) ──────────────────────────

# Default GUID — INTENTIONALLY INVALID UUID (contains 'p','l' = "copilot")
# Spelled this way to make it a database-insertion guardrail and instantly
# recognizable in logs as "no real user context — route to shared memory".
DEFAULT_USER_GUID = "c0p110t0-aaaa-bbbb-cccc-123456789abc"

GUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


# ─── Singletons ─────────────────────────────────────────────────────────

_BRAINSTEM_HOME = Path(os.environ.get("BRAINSTEM_HOME", "/tmp/.rapp-swarm")).expanduser()
_BRAINSTEM_HOME.mkdir(parents=True, exist_ok=True)
STORE = SwarmStore(_BRAINSTEM_HOME)


# ─── Helpers ────────────────────────────────────────────────────────────

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


def _read_json(req):
    try:
        return req.get_json() or {}
    except Exception:
        body = (req.get_body() or b"").decode("utf-8")
        if not body.strip():
            return {}
        return json.loads(body)


def _ensure_string_content(message):
    """Safe-coerce a message dict so role + content are always strings."""
    if message is None:
        return {"role": "user", "content": ""}
    if not isinstance(message, dict):
        return {"role": "user", "content": str(message)}
    m = dict(message)
    m.setdefault("role", "user")
    if "content" in m:
        m["content"] = "" if m["content"] is None else str(m["content"])
    else:
        m["content"] = ""
    return m


def _parse_voice_split(content):
    """Split on |||VOICE||| then |||TWIN|||. Returns (formatted, voice, twin).
    Every delimiter is optional. |||TWIN||| is the twin's entire real estate —
    anything the twin emits (commentary, <probe/>, <calibration/>, <telemetry>)
    lives inside it. Nothing twin-related leaks outside its block."""
    if not content:
        return "", "", ""
    main, sep, rest = content.partition("|||VOICE|||")
    if not sep:
        formatted = content.strip()
        sentence = formatted.split(".")[0] if formatted else "OK."
        voice = re.sub(r"\*\*|`|#|>|---", "", sentence).strip()
        voice = re.sub(r"\s+", " ", voice).strip()
        if voice and not voice.endswith("."):
            voice += "."
        return formatted, voice, ""
    voice, _, twin = rest.partition("|||TWIN|||")
    return main.strip(), voice.strip(), twin.strip()


def _select_swarm(req_body):
    """Resolve which swarm to drive for this request.
    Priority: body.swarm_guid → DEFAULT_SWARM_GUID env → only-hosted-swarm.
    Returns (swarm_guid, error_response_or_None)."""
    sg = (req_body.get("swarm_guid") or os.environ.get("DEFAULT_SWARM_GUID") or "").strip().lower()
    if sg and STORE.get_manifest(sg) is not None:
        return sg, None
    swarms = STORE.list_swarms()
    if len(swarms) == 1:
        return swarms[0]["swarm_guid"], None
    return None, {
        "error": "no swarm selected",
        "message": "specify swarm_guid in request body, or set DEFAULT_SWARM_GUID, "
                   "or hatch exactly one swarm into this function app",
        "available_swarms": [s["swarm_guid"] for s in swarms],
    }


def _resolve_user_guid(req_body, conversation_history, prompt):
    """Sacred OG behavior: a first message that's ONLY a GUID becomes the
    user_guid (memory namespace pin)."""
    explicit = req_body.get("user_guid")
    if explicit and GUID_RE.match(str(explicit).strip()):
        return str(explicit).strip()
    # First conversation_history message that's a bare GUID
    if conversation_history:
        first = conversation_history[0] or {}
        if first.get("role") == "user":
            content = (first.get("content") or "").strip()
            if GUID_RE.match(content):
                return content
    # The current prompt itself, if bare GUID
    if prompt:
        s = str(prompt).strip()
        if GUID_RE.match(s):
            return s
    return DEFAULT_USER_GUID


# ─── The Assistant — graduated brainstem, swarm-scoped ─────────────────

class Assistant:
    """One Assistant per request. Loads the chosen swarm's agents, runs
    the LLM chat loop with tool-calling, returns the formatted +
    voice-split response (sacred OG shape)."""

    def __init__(self, swarm_guid, user_guid=None):
        self.swarm_guid = swarm_guid
        self.user_guid = user_guid or DEFAULT_USER_GUID

        manifest = STORE.get_manifest(swarm_guid) or {}
        self.swarm_name = manifest.get("name") or "Twin Stack"
        self.soul = (manifest.get("soul") or "").strip()

        self.assistant_name = (
            manifest.get("name")
            or os.environ.get("ASSISTANT_NAME", "Twin Stack Assistant")
        )
        self.characteristic = (
            manifest.get("purpose")
            or os.environ.get("CHARACTERISTIC_DESCRIPTION", "your digital twin")
        )

        # Hot-load this swarm's agents (cached inside SwarmStore by guid)
        self.agents = STORE.load_agents(swarm_guid)
        self.tools = [self._agent_to_tool(a) for a in self.agents.values()]

    # ── tool definitions ──

    @staticmethod
    def _agent_to_tool(agent):
        md = getattr(agent, "metadata", {}) or {}
        return {
            "type": "function",
            "function": {
                "name": md.get("name", getattr(agent, "name", "agent")),
                "description": md.get("description", ""),
                "parameters": md.get("parameters", {"type": "object", "properties": {}}),
            },
        }

    # ── system prompt (sacred OG shape) ──

    def _calibration_root(self):
        try:
            return str(STORE.swarm_dir(self.swarm_guid))
        except Exception:
            return str(_BRAINSTEM_HOME)

    def _system_prompt(self, shared_memory="", user_memory=""):
        soul_block = self.soul or ""
        agent_ctx = "\n\n".join(
            (a.system_context() or "").strip()
            for a in self.agents.values()
            if hasattr(a, "system_context") and a.system_context()
        )
        calib_block = ""
        if _twin:
            try:
                calib_block = _twin.build_calibration_system_block(self._calibration_root())
            except Exception:
                calib_block = ""
        # Inject calibration block (if any) right after agent_context so the
        # twin sees its prior probes + historical accuracy with the rest of
        # the orientation material.
        extra_calib = ("\n\n" + calib_block) if calib_block else ""
        return f"""<identity>
You are {self.assistant_name} — {self.characteristic}.
You operate inside the Twin Stack as a hatched swarm cloud
({self.swarm_name}, swarm_guid={self.swarm_guid}).
</identity>

<soul>
{soul_block}
</soul>

<agent_context>
{agent_ctx}
</agent_context>
{extra_calib}
<shared_memory_output>
These are memories accessible across every conversation in this swarm:
{shared_memory or "(none)"}
</shared_memory_output>

<specific_memory_output>
These are memories specific to user_guid={self.user_guid}:
{user_memory or "(none)"}
</specific_memory_output>

<context_instructions>
- shared_memory is common knowledge across conversations
- specific_memory belongs to THIS specific user/conversation
- Apply specific context with HIGHER precedence than shared
- Synthesize information from both for comprehensive responses
</context_instructions>

<agent_usage>
IMPORTANT — be honest and accurate about agent usage:
- NEVER pretend or imply you've executed an agent when you haven't actually called it
- NEVER say "using my agent" unless you are actually invoking it via tool-call
- NEVER fabricate success messages about data operations that haven't occurred
- If you need an agent that doesn't exist here, say so directly
- ALWAYS trust the tool schema — if a parameter is defined, USE IT
</agent_usage>

<response_format>
CRITICAL: structure your response in THREE parts separated by |||VOICE||| then |||TWIN|||.

1. FIRST PART (before |||VOICE|||): full formatted response
   - Use **bold**, `code`, # headings, > quotes, --- rules, lists
   - Be substantive and useful
2. SECOND PART (between |||VOICE||| and |||TWIN|||): a concise voice response
   - 1–2 sentences max
   - Plain English, no markdown
   - Sound like a colleague over a cubicle wall
3. THIRD PART (after |||TWIN|||): the user's digital twin reacting to the turn
   - First person — speak AS the user, to the user ("I'd push back on that third point…")
   - Short. One or two observations, hints, risks, or questions.
   - Plain markdown is fine. Bold single-word tags work well (**Risk:**, **Hint:**, **Question:**).
   - Silent is allowed — leave the twin section empty if there's nothing worth saying this turn.
   - Do NOT re-answer the question. The twin comments on the turn; it does not replace any part of it.

CALIBRATION (optional, in the |||TWIN||| block only):
- When you make a claim you could be right OR wrong about, tag it with a probe:
    <probe id="t-<unique>" kind="<priority-claim|risk-flag|api-shape-guess|...>" subject="<what you're claiming about>" confidence="0.0-1.0"/>
  Use a short slug for `kind` so different claims of the same category aggregate.
- When a <twin_calibration> block appears in your system context with pending probes,
  judge each against what the user's most recent message actually showed:
    <calibration id="<probe id>" outcome="validated|contradicted|silent" note="<why>"/>
  * validated = the user's behavior or message confirms the claim
  * contradicted = the user's behavior or message refutes it
  * silent = the user neither confirmed nor refuted — don't penalize yourself for guessing in the quiet
- Both tag types are stripped before the user sees the panel. The user never reads the tags.
  Only your historical accuracy numbers come back to you in future turns.

TELEMETRY (optional, in the |||TWIN||| block only):
- When the twin wants to surface a server-side observation for the operator —
  a routing note, a memory hit-rate comment, a suspected prompt drift — wrap it in:
    <telemetry>one fact per line, plain text</telemetry>
- The block is printed to the server logs with a [twin-telemetry] prefix and
  stripped before the panel is rendered. The user never reads it.
- This is debug signal, not commentary. Keep it terse. Leave it out when there's
  nothing worth logging this turn.

Order is fixed: |||VOICE||| always comes before |||TWIN|||.

EXAMPLE:
Here's the analysis:

**Findings:** Revenue +12%, satisfaction up.

|||VOICE|||
Revenue's up 12 percent and customers are happier.

|||TWIN|||
**Hint:** the +12% is YoY — worth checking the seasonally-adjusted number before I take it into the board review.
</response_format>"""

    # ── memory recall (best-effort via the swarm's own memory agents) ──

    def _recall_memory(self):
        """Try a couple of well-known memory recall agent names.
        Returns (shared_memory, user_memory). Soft-failure: returns ("","")."""
        shared, specific = "", ""
        for agent_name in ("ContextMemory", "RecallMemory", "MemoryRecall"):
            if agent_name not in self.agents:
                continue
            try:
                # Shared memory recall (no user_guid)
                shared_res = STORE.execute(self.swarm_guid, agent_name,
                                            {"full_recall": True}, None)
                if shared_res.get("status") == "ok":
                    shared = str(shared_res.get("output") or "")[:4000]
                # Per-user recall
                if self.user_guid != DEFAULT_USER_GUID:
                    user_res = STORE.execute(self.swarm_guid, agent_name,
                                              {"full_recall": True,
                                               "user_guid": self.user_guid},
                                              self.user_guid)
                    if user_res.get("status") == "ok":
                        specific = str(user_res.get("output") or "")[:4000]
                break
            except Exception as e:
                logging.warning(f"memory recall via {agent_name} failed: {e}")
        return shared, specific

    # ── execute one tool call against a swarm agent ──

    def _execute_agent(self, agent_name, args_json):
        try:
            args = json.loads(args_json or "{}")
        except Exception:
            args = {}
        # Sacred behavior: memory agents receive the user_guid automatically
        if agent_name in ("ManageMemory", "ContextMemory", "SaveMemory", "RecallMemory"):
            args.setdefault("user_guid", self.user_guid)
        result = STORE.execute(self.swarm_guid, agent_name, args, self.user_guid)
        if result.get("status") == "ok":
            output = result.get("output")
            return (output if isinstance(output, str) else json.dumps(output)), None
        return None, result.get("message", "agent error")

    # ── run the chat loop ──

    def run(self, user_input, conversation_history, max_rounds=4):
        """Returns (formatted_response, voice_response, twin_response, agent_logs_str).
        Any <telemetry> tags inside |||TWIN||| are printed to server logs
        (prefixed [twin-telemetry]) and stripped before the twin renders."""
        shared_mem, user_mem = self._recall_memory()
        messages = [
            _ensure_string_content({"role": "system",
                                    "content": self._system_prompt(shared_mem, user_mem)}),
        ]
        # OG behavior: skip the first message if it's a GUID-only pin
        skip_first = False
        if conversation_history:
            first = conversation_history[0] or {}
            if first.get("role") == "user" and GUID_RE.match((first.get("content") or "").strip()):
                skip_first = True
        history = (conversation_history or [])[1 if skip_first else 0:]
        for m in history[-20:]:
            messages.append(_ensure_string_content(m))
        messages.append(_ensure_string_content({"role": "user", "content": user_input}))

        agent_logs = []

        for round_idx in range(max_rounds):
            try:
                assistant_msg = llm_chat(messages, tools=self.tools or None)
            except Exception as e:
                err = f"LLM error: {e}"
                logging.error(err)
                return err, "Something went wrong with the model.", "", "\n".join(agent_logs)

            messages.append(assistant_msg)
            tool_calls = assistant_msg.get("tool_calls") or []

            if not tool_calls:
                content = assistant_msg.get("content") or ""
                formatted, voice, twin = _parse_voice_split(content)
                twin = self._log_twin_tags(twin)
                return formatted, voice, twin, "\n".join(agent_logs)

            # Execute each tool call → loop
            for call in tool_calls:
                fn = call.get("function") or {}
                agent_name = fn.get("name", "")
                args_json = fn.get("arguments", "{}")
                output, err = self._execute_agent(agent_name, args_json)
                if err:
                    output = json.dumps({"status": "error", "message": err})
                agent_logs.append(f"Performed {agent_name} → {output[:200]}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.get("id", ""),
                    "name": agent_name,
                    "content": output or "",
                })

        # Hit max rounds — return last LLM content best-effort
        last_text = ""
        for m in reversed(messages):
            if m.get("role") == "assistant" and m.get("content"):
                last_text = m["content"]
                break
        formatted, voice, twin = _parse_voice_split(last_text or "(no response)")
        twin = self._log_twin_tags(twin)
        return formatted, voice, twin, "\n".join(agent_logs)

    def _log_twin_tags(self, twin_text: str) -> str:
        """Extract <telemetry>, <probe/>, <calibration/> from the twin block.
        Telemetry lines are written to server logs; probes + calibrations are
        appended to the calibration JSONL. All three tag types are stripped
        from the returned text so nothing twin-auxiliary leaks to the user."""
        if not _twin or not twin_text:
            return twin_text
        try:
            cleaned, probes, calibrations, telemetry = _twin.parse_twin_tags(twin_text)
            if probes or calibrations:
                _twin.log_events(self._calibration_root(), probes, calibrations)
            for line in (telemetry or "").splitlines():
                line = line.strip()
                if line:
                    logging.info("[twin-telemetry] %s", line)
            return cleaned
        except Exception:
            return twin_text


# ─── HTTP App ───────────────────────────────────────────────────────────

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


# ── /api/health (sacred OG shape) ───────────────────────────────────────

@app.function_name(name="health_check")
@app.route(route="health", methods=["GET", "OPTIONS"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return _json_response(200, {}, req.headers.get("origin"))
    started = time.time()
    deep = (req.params.get("deep", "").lower() == "true")
    health = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "version": "1.0.0",
        "stack": "The Twin Stack",
        "checks": {"basic": {"status": "pass", "message": "Function app responding"}},
    }
    if deep:
        try:
            health["checks"]["llm"] = {**llm_diagnostics(), "status": "pass"}
        except Exception as e:
            health["checks"]["llm"] = {"status": "fail", "message": str(e)}
            health["status"] = "degraded"
        swarms = STORE.list_swarms()
        health["checks"]["swarms"] = {
            "status": "pass",
            "swarm_count": len(swarms),
            "swarms": [s["swarm_guid"] for s in swarms],
        }
        try:
            ident = get_t2t_manager(STORE.root).get_identity_public()
            health["checks"]["t2t"] = {"status": "pass", "cloud_id": ident["cloud_id"], "handle": ident["handle"]}
        except Exception as e:
            health["checks"]["t2t"] = {"status": "warn", "message": str(e)}
    health["response_time_ms"] = round((time.time() - started) * 1000, 2)
    return _json_response(200 if health["status"] == "healthy" else 503,
                          health, req.headers.get("origin"))


# ── /api/businessinsightbot_function (sacred OG wire shape) ────────────
# Same shape the OG MultiAgentCopilot bot calls. Per-request swarm_guid
# chooses which swarm's agents + memory drive THIS request.

@app.function_name(name="businessinsightbot_function")
@app.route(route="businessinsightbot_function", methods=["POST", "OPTIONS"])
def businessinsightbot_function(req: func.HttpRequest) -> func.HttpResponse:
    return _do_chat(req)


@app.function_name(name="chat_alias")
@app.route(route="chat", methods=["POST", "OPTIONS"])
def chat_alias(req: func.HttpRequest) -> func.HttpResponse:
    return _do_chat(req)


def _do_chat(req: func.HttpRequest) -> func.HttpResponse:
    origin = req.headers.get("origin")
    if req.method == "OPTIONS":
        return _json_response(204, {}, origin)
    body = _read_json(req)
    user_input = body.get("user_input") or body.get("input") or ""
    user_input = str(user_input) if user_input is not None else ""
    conversation_history = body.get("conversation_history") or []
    if not isinstance(conversation_history, list):
        conversation_history = []

    is_guid_only = bool(GUID_RE.match(user_input.strip()))
    if not is_guid_only and not user_input.strip():
        return _json_response(400, {"error": "Missing or empty user_input"}, origin)

    sg, err = _select_swarm(body)
    if err:
        return _json_response(400, err, origin)

    user_guid = _resolve_user_guid(body, conversation_history, user_input)

    # Bare-GUID prompt: don't drive the LLM, just acknowledge the pin
    if is_guid_only and user_guid == user_input.strip():
        return _json_response(200, {
            "assistant_response": "I've loaded your conversation memory. How can I assist you today?",
            "voice_response": "I've loaded your memory — what can I help with?",
            "twin_response": "",
            "agent_logs": "",
            "user_guid": user_guid,
            "swarm_guid": sg,
        }, origin)

    try:
        assistant = Assistant(swarm_guid=sg, user_guid=user_guid)
        formatted, voice, twin, logs = assistant.run(user_input, conversation_history)
        return _json_response(200, {
            "assistant_response": str(formatted),
            "voice_response": str(voice),
            "twin_response": str(twin),
            "agent_logs": str(logs),
            "user_guid": assistant.user_guid,
            "swarm_guid": sg,
            "provider": detect_provider(),
        }, origin)
    except Exception as e:
        logging.exception("chat path failed")
        return _json_response(500, {"error": "Internal server error", "details": str(e)}, origin)


# ── /api/trigger/copilot-studio (sacred OG direct-invoke shape) ────────

@app.function_name(name="copilot_studio_trigger")
@app.route(route="trigger/copilot-studio", methods=["POST", "OPTIONS"])
def copilot_studio_trigger(req: func.HttpRequest) -> func.HttpResponse:
    origin = req.headers.get("origin")
    if req.method == "OPTIONS":
        return _json_response(200, {}, origin)
    payload = _read_json(req)
    if "agent" not in payload or "action" not in payload:
        return _json_response(400, {"error": "Missing 'agent' and 'action' fields"}, origin)
    agent_name = payload["agent"]
    action = payload["action"]
    parameters = payload.get("parameters") or {}
    parameters["action"] = action
    sg, err = _select_swarm(payload)
    if err:
        return _json_response(400, err, origin)
    result = STORE.execute(sg, agent_name, parameters, payload.get("user_guid"))
    if result.get("status") != "ok":
        return _json_response(404 if "unknown" in (result.get("message", "") or "") else 500, {
            "status": "error", "error": result.get("message"),
            "copilot_studio_format": {
                "type": "event", "name": "agent.error",
                "value": {"success": False, "message": result.get("message")},
            },
        }, origin)
    return _json_response(200, {
        "status": "success",
        "response": result.get("output"),
        "copilot_studio_format": {
            "type": "event", "name": "agent.response",
            "value": {"success": True, "message": str(result.get("output"))},
        },
    }, origin)


# ── /api/swarm/* (Twin Stack additions) ────────────────────────────────

@app.function_name(name="swarm_healthz")
@app.route(route="swarm/healthz", methods=["GET", "OPTIONS"])
def swarm_healthz(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS": return _json_response(204, {}, req.headers.get("origin"))
    swarms = STORE.list_swarms()
    return _json_response(200, {
        "status": "ok",
        "schema": "rapp-swarm/1.0",
        "version": "1.0.0",
        "stack": "The Twin Stack",
        "swarm_count": len(swarms),
        "swarms": swarms,
        "llm": llm_diagnostics(),
    }, req.headers.get("origin"))


@app.function_name(name="swarm_one_healthz")
@app.route(route="swarm/{swarm_guid}/healthz", methods=["GET", "OPTIONS"])
def swarm_one_healthz(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS": return _json_response(204, {}, req.headers.get("origin"))
    sg = req.route_params.get("swarm_guid", "")
    manifest = STORE.get_manifest(sg)
    if not manifest:
        return _json_response(404, {"status": "error", "message": "swarm not found"}, req.headers.get("origin"))
    agents = STORE.load_agents(sg)
    seal = STORE.seal_status(sg)
    return _json_response(200, {
        "status": "ok",
        "swarm_guid": sg,
        "name": manifest.get("name"),
        "purpose": manifest.get("purpose"),
        "agent_count": len(agents),
        "agents": sorted(agents.keys()),
        "sealed": seal["sealed"],
        "sealing": seal,
    }, req.headers.get("origin"))


@app.function_name(name="swarm_deploy")
@app.route(route="swarm/deploy", methods=["POST", "OPTIONS"])
def swarm_deploy(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS": return _json_response(204, {}, req.headers.get("origin"))
    body = _read_json(req)
    try:
        manifest = STORE.deploy(body)
    except SealedSwarmError as e:
        return _json_response(423, {"status": "error", "message": str(e), "sealed": True}, req.headers.get("origin"))
    except ValueError as e:
        return _json_response(400, {"status": "error", "message": str(e)}, req.headers.get("origin"))
    except Exception as e:
        return _json_response(500, {"status": "error", "message": str(e)}, req.headers.get("origin"))
    host = req.headers.get("Host", "")
    base = f"https://{host}" if host else ""
    return _json_response(200, {
        "status": "ok",
        "swarm_guid": manifest["swarm_guid"],
        "name": manifest["name"],
        "swarm_url": f"{base}/api/swarm/{manifest['swarm_guid']}/agent",
        "info_url":  f"{base}/api/swarm/{manifest['swarm_guid']}/healthz",
        "agent_count": manifest["agent_count"],
    }, req.headers.get("origin"))


@app.function_name(name="swarm_agent")
@app.route(route="swarm/{swarm_guid}/agent", methods=["POST", "OPTIONS"])
def swarm_agent(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS": return _json_response(204, {}, req.headers.get("origin"))
    sg = req.route_params.get("swarm_guid", "")
    body = _read_json(req)
    name = body.get("name")
    if not name:
        return _json_response(400, {"status": "error", "message": "missing 'name'"}, req.headers.get("origin"))
    result = STORE.execute(sg, name, body.get("args") or {}, body.get("user_guid"))
    status = 200 if result.get("status") == "ok" else (
        404 if "unknown agent" in (result.get("message", "") or "") else 500
    )
    return _json_response(status, result, req.headers.get("origin"))


@app.function_name(name="swarm_chat")
@app.route(route="swarm/{swarm_guid}/chat", methods=["POST", "OPTIONS"])
def swarm_chat(req: func.HttpRequest) -> func.HttpResponse:
    """Per-swarm LLM-driven chat using the same Assistant pattern as
    /api/chat — but with the swarm_guid pinned by URL."""
    if req.method == "OPTIONS": return _json_response(204, {}, req.headers.get("origin"))
    sg = req.route_params.get("swarm_guid", "")
    body = _read_json(req)
    body["swarm_guid"] = sg  # force per-URL guid even if body disagrees
    return _do_chat(req)


# ── Sealing ────────────────────────────────────────────────────────────

@app.function_name(name="swarm_seal_get")
@app.route(route="swarm/{swarm_guid}/seal", methods=["GET", "OPTIONS"])
def swarm_seal_get(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS": return _json_response(204, {}, req.headers.get("origin"))
    sg = req.route_params.get("swarm_guid", "")
    seal = STORE.seal_status(sg)
    if not seal["exists"]:
        return _json_response(404, {"status": "error", "message": "swarm not found"}, req.headers.get("origin"))
    return _json_response(200, seal, req.headers.get("origin"))


@app.function_name(name="swarm_seal_post")
@app.route(route="swarm/{swarm_guid}/seal", methods=["POST"])
def swarm_seal_post(req: func.HttpRequest) -> func.HttpResponse:
    sg = req.route_params.get("swarm_guid", "")
    body = _read_json(req)
    try:
        sealing = STORE.seal(sg, actor=body.get("actor"), trigger=body.get("trigger") or "voluntary")
        return _json_response(200, {"status": "ok", "swarm_guid": sg, "sealing": sealing}, req.headers.get("origin"))
    except FileNotFoundError as e:
        return _json_response(404, {"status": "error", "message": str(e)}, req.headers.get("origin"))


# ── Snapshots ──────────────────────────────────────────────────────────

@app.function_name(name="swarm_snapshot_post")
@app.route(route="swarm/{swarm_guid}/snapshot", methods=["POST"])
def swarm_snapshot_post(req: func.HttpRequest) -> func.HttpResponse:
    sg = req.route_params.get("swarm_guid", "")
    body = _read_json(req)
    try:
        meta = STORE.create_snapshot(sg, label=body.get("label"))
        return _json_response(200, {"status": "ok", **meta}, req.headers.get("origin"))
    except FileNotFoundError as e:
        return _json_response(404, {"status": "error", "message": str(e)}, req.headers.get("origin"))


@app.function_name(name="swarm_snapshot_list")
@app.route(route="swarm/{swarm_guid}/snapshots", methods=["GET", "OPTIONS"])
def swarm_snapshot_list(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS": return _json_response(204, {}, req.headers.get("origin"))
    sg = req.route_params.get("swarm_guid", "")
    if STORE.get_manifest(sg) is None:
        return _json_response(404, {"status": "error", "message": "swarm not found"}, req.headers.get("origin"))
    return _json_response(200, {"swarm_guid": sg, "snapshots": STORE.list_snapshots(sg)},
                           req.headers.get("origin"))


@app.function_name(name="swarm_snapshot_agent")
@app.route(route="swarm/{swarm_guid}/snapshots/{snap_name}/agent", methods=["POST"])
def swarm_snapshot_agent(req: func.HttpRequest) -> func.HttpResponse:
    sg = req.route_params.get("swarm_guid", "")
    snap = req.route_params.get("snap_name", "")
    body = _read_json(req)
    name = body.get("name")
    if not name:
        return _json_response(400, {"status": "error", "message": "missing 'name'"}, req.headers.get("origin"))
    result = STORE.execute_against_snapshot(sg, snap, name, body.get("args") or {}, body.get("user_guid"))
    status = 200 if result.get("status") == "ok" else 404
    return _json_response(status, result, req.headers.get("origin"))


# ── T2T (twin-to-twin) ─────────────────────────────────────────────────

@app.function_name(name="t2t_identity")
@app.route(route="t2t/identity", methods=["GET", "OPTIONS"])
def t2t_identity(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS": return _json_response(204, {}, req.headers.get("origin"))
    return _json_response(200, get_t2t_manager(STORE.root).get_identity_public(),
                           req.headers.get("origin"))


@app.function_name(name="t2t_peers_list")
@app.route(route="t2t/peers", methods=["GET", "OPTIONS"])
def t2t_peers_list(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS": return _json_response(204, {}, req.headers.get("origin"))
    return _json_response(200, {"peers": get_t2t_manager(STORE.root).list_peers()},
                           req.headers.get("origin"))


@app.function_name(name="t2t_peers_add")
@app.route(route="t2t/peers", methods=["POST"])
def t2t_peers_add(req: func.HttpRequest) -> func.HttpResponse:
    body = _read_json(req)
    cloud_id = body.get("cloud_id"); secret = body.get("secret")
    if not cloud_id or not secret:
        return _json_response(400, {"status": "error", "message": "cloud_id and secret required"},
                               req.headers.get("origin"))
    mgr = get_t2t_manager(STORE.root)
    peer = mgr.add_peer(cloud_id=cloud_id, secret=secret,
                         handle=body.get("handle", ""), url=body.get("url", ""),
                         allowed_caps=body.get("allowed_caps") or ["*"])
    peer = {k: v for k, v in peer.items() if k != "secret"}
    return _json_response(200, {"status": "ok", "peer": peer}, req.headers.get("origin"))


@app.function_name(name="t2t_handshake")
@app.route(route="t2t/handshake", methods=["POST"])
def t2t_handshake(req: func.HttpRequest) -> func.HttpResponse:
    body = _read_json(req)
    mgr = get_t2t_manager(STORE.root)
    result = mgr.handshake(
        from_cloud_id=body.get("from", ""), conv_id=body.get("conv_id", ""),
        intro=body.get("intro") or {}, sig=body.get("sig", ""),
    )
    return _json_response(200 if result.get("accepted") else 403, result, req.headers.get("origin"))


@app.function_name(name="t2t_message")
@app.route(route="t2t/message", methods=["POST"])
def t2t_message(req: func.HttpRequest) -> func.HttpResponse:
    body = _read_json(req)
    mgr = get_t2t_manager(STORE.root)
    result = mgr.receive_message(
        from_cloud_id=body.get("from", ""), conv_id=body.get("conv_id", ""),
        seq=body.get("seq", 0), body=body.get("body") or {}, sig=body.get("sig", ""),
    )
    return _json_response(200 if result.get("received") else 403, result, req.headers.get("origin"))


@app.function_name(name="t2t_invoke")
@app.route(route="t2t/invoke", methods=["POST"])
def t2t_invoke(req: func.HttpRequest) -> func.HttpResponse:
    body = _read_json(req)
    mgr = get_t2t_manager(STORE.root)
    from_cloud_id = body.get("from", "")
    sig = body.get("sig", "")
    invocation = body.get("invocation") or {}
    payload = json.dumps({"from": from_cloud_id, "invocation": invocation},
                         sort_keys=True, separators=(",", ":"))
    peer = mgr.peers.get_peer(from_cloud_id)
    if not peer:
        return _json_response(403, {"status": "error", "message": "peer not whitelisted"}, req.headers.get("origin"))
    if not t2t_verify(payload, sig, peer["secret"]):
        return _json_response(403, {"status": "error", "message": "signature failed"}, req.headers.get("origin"))
    target_swarm = invocation.get("swarm_guid", "")
    agent_name = invocation.get("agent", "")
    if not mgr.can_peer_invoke(from_cloud_id, agent_name):
        return _json_response(403, {"status": "error",
                                     "message": f"peer not authorized for capability '{agent_name}'"},
                               req.headers.get("origin"))
    result = STORE.execute(target_swarm, agent_name, invocation.get("args") or {}, user_guid=None)
    return _json_response(200, {"status": "ok", "result": result, "invoked_by": from_cloud_id},
                           req.headers.get("origin"))


# ── /api/llm/status (which LLM provider is wired) ──────────────────────

@app.function_name(name="llm_status")
@app.route(route="llm/status", methods=["GET", "OPTIONS"])
def llm_status(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS": return _json_response(204, {}, req.headers.get("origin"))
    return _json_response(200, llm_diagnostics(), req.headers.get("origin"))
