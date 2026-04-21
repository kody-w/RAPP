"""
swarm_invoke_agent.py — run an agent inside a sibling swarm.

Loads a single `*_agent.py` file from `<swarms_root>/<guid>/agents/`,
instantiates the class whose `self.name` matches, calls `perform(**args)`,
and returns the result. This is how one swarm calls another on the same
device without new HTTP surface (per CONSTITUTION Article XIV — Swarms
Are Directories, Not Routes).

Security note: this executes Python from disk. That disk is the user's
own `.brainstem_data/swarms/` tree; no remote code is fetched. The same
trust model as the host brainstem's own agents/ loader.
"""

import importlib.util
import json
import os
import re
from pathlib import Path

from agents.basic_agent import BasicAgent


__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "@rapp/swarm_invoke",
    "version": "1.0.0",
    "display_name": "Invoke Swarm Agent",
    "description": "Runs a named agent inside a sibling swarm and returns its output.",
    "author": "RAPP",
    "tags": ["starter", "swarm", "infrastructure", "s2s"],
    "category": "core",
    "quality_tier": "official",
    "requires_env": [],
    "example_call": "Invoke the 'SaveMemory' agent in swarm <guid> with content='hello'.",
}


_GUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _swarms_root() -> Path:
    override = os.environ.get("BRAINSTEM_HOME")
    if override:
        return (Path(override).expanduser() / "swarms").resolve()
    here_local = (Path.cwd() / ".brainstem_data" / "swarms").resolve()
    if (Path.cwd() / "brainstem.py").is_file() or (Path.cwd() / ".brainstem_data").is_dir():
        return here_local
    return (Path.home() / ".brainstem_data" / "swarms").resolve()


def _resolve_swarm(guid: str) -> Path:
    if not _GUID_RE.match(guid):
        raise ValueError(f"invalid swarm guid: {guid!r}")
    d = _swarms_root() / guid
    if not d.is_dir():
        raise FileNotFoundError(f"swarm not found: {guid}")
    return d


def _load_agents_from_dir(agents_dir: Path):
    """Import every *_agent.py in `agents_dir` into a fresh namespace and
    return a list of (class_instance, filename) for each BasicAgent subclass."""
    import inspect

    loaded = []
    for py_file in sorted(agents_dir.glob("*_agent.py")):
        if py_file.name == "basic_agent.py":
            continue
        mod_name = f"_swarm_invoke_{py_file.stem}"
        spec = importlib.util.spec_from_file_location(mod_name, py_file)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            raise RuntimeError(f"import failed for {py_file.name}: {e}")
        for _name, obj in inspect.getmembers(module, inspect.isclass):
            if obj is BasicAgent:
                continue
            if issubclass(obj, BasicAgent):
                try:
                    loaded.append((obj(), py_file.name))
                except Exception:
                    continue
    return loaded


class SwarmInvokeAgent(BasicAgent):
    def __init__(self):
        self.name = "InvokeSwarmAgent"
        self.metadata = {
            "name": self.name,
            "description": (
                "Runs a named agent INSIDE a sibling swarm on this device "
                "and returns its output. Use this when the capability the "
                "user wants lives in another swarm (check ListSwarms / "
                "SwarmInfo first). The invoked agent runs in the sibling "
                "swarm's memory namespace, not the host's."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "swarm_guid": {
                        "type": "string",
                        "description": "GUID of the swarm that hosts the agent.",
                    },
                    "agent_name": {
                        "type": "string",
                        "description": "self.name of the agent to invoke (e.g., 'SaveMemory').",
                    },
                    "args": {
                        "type": "object",
                        "description": "Keyword arguments to pass to the agent's perform().",
                    },
                },
                "required": ["swarm_guid", "agent_name"],
            },
        }
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        try:
            swarm_dir = _resolve_swarm(kwargs.get("swarm_guid", ""))
        except (ValueError, FileNotFoundError) as e:
            return json.dumps({"status": "error", "message": str(e)})

        agent_name = (kwargs.get("agent_name") or "").strip()
        if not agent_name:
            return json.dumps({"status": "error", "message": "agent_name is required"})

        args = kwargs.get("args") or {}
        if not isinstance(args, dict):
            return json.dumps({"status": "error", "message": "args must be an object"})

        agents_dir = swarm_dir / "agents"
        if not agents_dir.is_dir():
            return json.dumps({
                "status": "error",
                "message": f"swarm has no agents/ directory: {swarm_dir}",
            })

        # Point any memory-using agent at the sibling swarm's memory dir
        # so its writes land there, not on the host's memory. Save/restore
        # so we don't leak env state to the host.
        memory_dir = swarm_dir / "memory" / "shared"
        memory_dir.mkdir(parents=True, exist_ok=True)
        prev_mem = os.environ.get("BRAINSTEM_MEMORY_PATH")
        os.environ["BRAINSTEM_MEMORY_PATH"] = str(memory_dir / "memory.json")

        try:
            try:
                instances = _load_agents_from_dir(agents_dir)
            except RuntimeError as e:
                return json.dumps({"status": "error", "message": str(e)})

            target = next(
                (inst for inst, _ in instances if getattr(inst, "name", None) == agent_name),
                None,
            )
            if target is None:
                return json.dumps({
                    "status": "error",
                    "message": (
                        f"no agent named {agent_name!r} in swarm {swarm_dir.name}. "
                        f"Available: {[inst.name for inst, _ in instances]}"
                    ),
                })

            try:
                raw = target.perform(**args)
            except Exception as e:
                return json.dumps({
                    "status": "error",
                    "message": f"agent raised: {type(e).__name__}: {e}",
                })
        finally:
            if prev_mem is None:
                os.environ.pop("BRAINSTEM_MEMORY_PATH", None)
            else:
                os.environ["BRAINSTEM_MEMORY_PATH"] = prev_mem

        # The sibling agent is required to return a string (usually JSON).
        # Pass it through verbatim so the LLM sees the same shape.
        result_str = raw if isinstance(raw, str) else json.dumps(raw)

        return json.dumps({
            "status": "success",
            "swarm_guid": swarm_dir.name,
            "agent_name": agent_name,
            "result": result_str,
            "summary": f"Invoked {agent_name} in swarm {swarm_dir.name}.",
            "data_slush": {
                "invoked_swarm": swarm_dir.name,
                "invoked_agent": agent_name,
            },
        })
