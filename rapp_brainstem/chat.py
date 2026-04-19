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


MAX_TOOL_ROUNDS = 4


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
    system = _system_prompt(soul, agents, extra=extra_system)

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
            return {
                "response": assistant.get("content") or "",
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


def diagnostics() -> dict:
    """For /api/swarm/healthz to expose what LLM provider it's wired to."""
    return provider_status()
