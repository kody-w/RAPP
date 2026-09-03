#!/usr/bin/env python3
"""
swarm/chat.py — LLM-driven tool-calling chat loop for a hatched swarm.

Given a swarm_guid (the swarm to drive) and a user_input, builds:
    - System prompt: soul + agent system_context() injections
    - Tools: each agent's metadata becomes one OpenAI-format function-tool
    - Loop: call LLM → execute tool calls → loop (cap 4 rounds) → return reply

Same wire shape as the OG community RAPP brainstem (rapp_brainstem/) so
clients (browser brainstem, function_app.py, swarm/server.py) all speak
the same /chat envelope:

    POST { user_input, conversation_history?, session_id? }
       → { response, agent_logs, model, provider }

Stdlib only — uses swarm/llm.py for the actual provider dispatch.
"""

from __future__ import annotations
import json
import os
import time
import traceback

# Local import (sibling module) — works whether we're running as
# swarm.chat or as plain `chat` (Azure Functions package layout).
try:
    from swarm.llm import chat as llm_chat, detect_provider, provider_status
except ImportError:
    from llm import chat as llm_chat, detect_provider, provider_status  # type: ignore

# Twin calibration helpers — sibling module, vendored into rapp_swarm/_vendored/.
try:
    from rapp_brainstem import twin as _twin
except ImportError:
    try:
        import twin as _twin  # type: ignore
    except ImportError:
        _twin = None  # calibration is optional; feature gracefully disables


MAX_TOOL_ROUNDS = 4


def _parse_voice_twin_split(content: str):
    """Split on |||VOICE||| then |||TWIN|||. Returns (main, voice, twin).
    |||TWIN||| is the twin's entire real estate — probes, calibrations, and
    telemetry all live INSIDE it as tags that get stripped before render."""
    if not content:
        return "", "", ""
    main, sep, rest = content.partition("|||VOICE|||")
    if not sep:
        return content.strip(), "", ""
    voice, _, twin = rest.partition("|||TWIN|||")
    return main.strip(), voice.strip(), twin.strip()


def _emit_telemetry(telemetry: str) -> None:
    """Print twin-authored telemetry to stdout, grouped with the existing
    `[brainstem] …` log lines. Server-only — never returned to the client."""
    t = (telemetry or "").strip()
    if not t:
        return
    for line in t.splitlines():
        line = line.strip()
        if line:
            print(f"[twin-telemetry] {line}", flush=True)


def _calibration_root(store, swarm_guid, extra_hint=None):
    """Resolve where the twin calibration log should live for this tenant."""
    if extra_hint:
        return extra_hint
    for attr in ("swarm_dir", "swarm_root", "root_for", "get_root"):
        fn = getattr(store, attr, None)
        if callable(fn):
            try:
                p = fn(swarm_guid) if swarm_guid else fn()
                if p:
                    return str(p)
            except TypeError:
                pass
    base = getattr(store, "root", None) or "."
    return str(base) if not swarm_guid else f"{base}/swarms/{swarm_guid}"


def _agent_to_tool(agent) -> dict:
    """Build an OpenAI-format tool definition from an agent's metadata."""
    md = getattr(agent, "metadata", {}) or {}
    return {
        "type": "function",
        "function": {
            "name": md.get("name", getattr(agent, "name", "agent")),
            "description": md.get("description", ""),
            "parameters": md.get("parameters", {"type": "object", "properties": {}}),
        },
    }


def _system_prompt(soul: str, agents: dict, extra: str = "") -> str:
    """Compose the system prompt: soul + each agent's optional
    system_context()."""
    parts = []
    if soul:
        parts.append(soul.strip())
    for a in agents.values():
        try:
            ctx = a.system_context() if hasattr(a, "system_context") else None
            if ctx:
                parts.append(ctx.strip())
        except Exception:
            pass
    if extra:
        parts.append(extra.strip())
    return "\n\n".join([p for p in parts if p])


def chat_with_swarm(store, swarm_guid: str, user_input: str,
                    conversation_history: list | None = None,
                    user_guid: str | None = None,
                    extra_system: str = "") -> dict:
    """Drive an LLM-powered chat against one swarm's agents.

    Returns:
        {
          "response":         <assistant text>,
          "agent_logs":       [{"name":..., "args":..., "output":..., "ms":...}],
          "model":            <model id used>,
          "provider":         <azure-openai|openai|anthropic|fake>,
          "rounds":           <how many tool-call rounds before final reply>,
          "swarm_guid":       <which swarm answered>,
        }
    """
    manifest = store.get_manifest(swarm_guid)
    if manifest is None:
        return {"response": "", "error": f"swarm not found: {swarm_guid}",
                "swarm_guid": swarm_guid}

    soul = (manifest.get("soul") or "").strip()
    agents = store.load_agents(swarm_guid)
    tools = [_agent_to_tool(a) for a in agents.values()]

    # Calibration block (pending probes + rolling accuracy) — injected
    # alongside the soul so the twin can self-judge prior turns.
    calib_root = _calibration_root(store, swarm_guid)
    calib_block = _twin.build_calibration_system_block(calib_root) if _twin else ""
    system = _system_prompt(soul, agents, extra=(extra_system + ("\n\n" + calib_block if calib_block else "")).strip())

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    for m in (conversation_history or []):
        if not isinstance(m, dict): continue
        role = m.get("role")
        if role in ("user", "assistant", "tool", "system"):
            messages.append(m)
    messages.append({"role": "user", "content": user_input})

    provider = detect_provider()
    agent_logs: list = []
    rounds = 0

    while True:
        rounds += 1
        try:
            assistant = llm_chat(messages, tools=tools or None)
        except Exception as e:
            return {
                "response": f"LLM error: {e}",
                "agent_logs": agent_logs,
                "provider": provider,
                "rounds": rounds,
                "swarm_guid": swarm_guid,
                "error": str(e),
            }
        messages.append(assistant)

        tool_calls = assistant.get("tool_calls") or []
        if not tool_calls or rounds >= MAX_TOOL_ROUNDS:
            raw = assistant.get("content") or ""
            main, voice, twin = _parse_voice_twin_split(raw)
            # Extract twin-authored tags: <probe/>, <calibration/>, <telemetry>.
            # Probes + calibrations go to the calibration log; telemetry to
            # server stdout; everything else stays as the twin panel text.
            if _twin:
                twin, probes, calibrations, telemetry = _twin.parse_twin_tags(twin)
                _emit_telemetry(telemetry)
                try:
                    _twin.log_events(calib_root, probes, calibrations)
                except OSError:
                    pass  # best-effort; never fail the reply for logging
            return {
                "response": main,
                "voice_response": voice,
                "twin_response": twin,
                "agent_logs": agent_logs,
                "provider": provider,
                "rounds": rounds,
                "swarm_guid": swarm_guid,
                "model": os.environ.get("AZURE_OPENAI_DEPLOYMENT")
                          or os.environ.get("OPENAI_MODEL")
                          or os.environ.get("ANTHROPIC_MODEL")
                          or "fake",
            }

        # Execute each tool call against the swarm's agents.
        for call in tool_calls:
            fn = (call.get("function") or {})
            name = fn.get("name", "")
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except Exception:
                args = {}
            t0 = time.time()
            result = store.execute(swarm_guid, name, args, user_guid)
            ms = int((time.time() - t0) * 1000)
            output_str = result.get("output") if result.get("status") == "ok" \
                          else json.dumps({"error": result.get("message", "agent error")})
            if not isinstance(output_str, str):
                output_str = json.dumps(output_str)
            agent_logs.append({
                "name": name,
                "args": args,
                "output": output_str[:2000],
                "ms": ms,
                "status": result.get("status"),
            })
            messages.append({
                "role": "tool",
                "tool_call_id": call.get("id", ""),
                "name": name,
                "content": output_str,
            })


def chat_with_binder(store, agents_dir, user_input: str,
                     conversation_history=None,
                     soul: str = "",
                     extra_system: str = "") -> dict:
    """Drive an LLM-powered chat against the binder-installed agents.

    Mirrors chat_with_swarm but loads agents from <root>/agents/ (the binder's
    materialization target) instead of a per-swarm dir. Lets a user install
    rapplications via the binder API and immediately call them via /chat.
    """
    from pathlib import Path as _P
    agents_dir = _P(agents_dir)

    # Use the same loader the binder/agent route uses, with cache key '__binder__'
    # (busted by /api/binder/install + /api/binder/installed/{id}).
    if "__binder__" not in store._loaded_agents:
        # Trigger one warm load via execute_in_dir with a sentinel — easier to
        # just poke the cache by hand than to refactor execute_in_dir.
        store.execute_in_dir(agents_dir, "__warmup__", {}, cache_key="__binder__")
    agents = store._loaded_agents.get("__binder__", {}) or {}

    tools = [_agent_to_tool(a) for a in agents.values()]
    system = _system_prompt(soul, agents, extra=extra_system)

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    for m in (conversation_history or []):
        if isinstance(m, dict) and m.get("role") in ("user", "assistant", "tool", "system"):
            messages.append(m)
    messages.append({"role": "user", "content": user_input})

    provider = detect_provider()
    agent_logs: list = []
    rounds = 0

    while True:
        rounds += 1
        try:
            assistant = llm_chat(messages, tools=tools or None)
        except Exception as e:
            return {
                "response":   f"LLM error: {e}",
                "agent_logs": agent_logs,
                "provider":   provider,
                "rounds":     rounds,
                "context":    "binder",
                "error":      str(e),
            }
        messages.append(assistant)

        tool_calls = assistant.get("tool_calls") or []
        if not tool_calls or rounds >= MAX_TOOL_ROUNDS:
            raw = assistant.get("content") or ""
            main, voice, twin = _parse_voice_twin_split(raw)
            if _twin:
                twin, _probes, _calibs, telemetry = _twin.parse_twin_tags(twin)
                _emit_telemetry(telemetry)
            return {
                "response":       main,
                "voice_response": voice,
                "twin_response":  twin,
                "agent_logs":     agent_logs,
                "provider":       provider,
                "rounds":         rounds,
                "context":        "binder",
                "agents_available": sorted(agents.keys()),
                "model":          os.environ.get("AZURE_OPENAI_DEPLOYMENT")
                                  or os.environ.get("OPENAI_MODEL")
                                  or os.environ.get("ANTHROPIC_MODEL")
                                  or "fake",
            }

        # Execute each tool call against the binder-loaded agents.
        for call in tool_calls:
            fn = (call.get("function") or {})
            name = fn.get("name", "")
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except Exception:
                args = {}
            t0 = time.time()
            result = store.execute_in_dir(agents_dir, name, args, cache_key="__binder__")
            ms = int((time.time() - t0) * 1000)
            output_str = result.get("output") if result.get("status") == "ok" \
                          else json.dumps({"error": result.get("message", "agent error")})
            if not isinstance(output_str, str):
                output_str = json.dumps(output_str)
            agent_logs.append({
                "name":   name,
                "args":   args,
                "output": output_str[:2000],
                "ms":     ms,
                "status": result.get("status"),
            })
            messages.append({
                "role":         "tool",
                "tool_call_id": call.get("id", ""),
                "name":         name,
                "content":      output_str,
            })


def diagnostics() -> dict:
    """For /api/swarm/healthz to expose what LLM provider it's wired to."""
    return provider_status()
