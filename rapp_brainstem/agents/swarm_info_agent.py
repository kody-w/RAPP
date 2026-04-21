"""
swarm_info_agent.py — describe a specific swarm by GUID.

Reads manifest.json + agents/ + seal marker + snapshot directory. Returns
a richer view than ListSwarms (which only summarizes). Pure filesystem read.
"""

import json
import os
import re
from pathlib import Path

from agents.basic_agent import BasicAgent


__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "@rapp/swarm_info",
    "version": "1.0.0",
    "display_name": "Swarm Info",
    "description": "Returns detailed info about one swarm: manifest, agents, seal status, snapshot list.",
    "author": "RAPP",
    "tags": ["starter", "swarm", "infrastructure"],
    "category": "core",
    "quality_tier": "official",
    "requires_env": [],
    "example_call": "Show me details for swarm <guid>.",
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


class SwarmInfoAgent(BasicAgent):
    def __init__(self):
        self.name = "SwarmInfo"
        self.metadata = {
            "name": self.name,
            "description": (
                "Returns detailed info about a specific swarm by GUID: "
                "its manifest (name, purpose, soul, created_at), the list "
                "of agent filenames it contains, whether it's sealed, and "
                "the names of any snapshots taken."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "swarm_guid": {
                        "type": "string",
                        "description": "The swarm's GUID (as returned by DeploySwarm / ListSwarms).",
                    },
                },
                "required": ["swarm_guid"],
            },
        }
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        try:
            swarm_dir = _resolve_swarm(kwargs.get("swarm_guid", ""))
        except (ValueError, FileNotFoundError) as e:
            return json.dumps({"status": "error", "message": str(e)})

        try:
            manifest = json.loads((swarm_dir / "manifest.json").read_text())
        except (OSError, json.JSONDecodeError) as e:
            return json.dumps({"status": "error", "message": f"manifest unreadable: {e}"})

        agents_dir = swarm_dir / "agents"
        agent_files = sorted(
            p.name for p in agents_dir.glob("*_agent.py")
        ) if agents_dir.is_dir() else []

        snapshots_dir = swarm_dir / "snapshots"
        snapshots = sorted(
            p.name for p in snapshots_dir.iterdir() if p.is_dir()
        ) if snapshots_dir.is_dir() else []

        sealed = (swarm_dir / ".sealed").is_file()

        return json.dumps({
            "status": "success",
            "swarm_guid": manifest.get("swarm_guid", swarm_dir.name),
            "name": manifest.get("name", ""),
            "purpose": manifest.get("purpose", ""),
            "soul": manifest.get("soul", ""),
            "created_by": manifest.get("created_by", ""),
            "created_at": manifest.get("created_at", ""),
            "sealed": sealed,
            "path": str(swarm_dir),
            "agents": agent_files,
            "agent_count": len(agent_files),
            "snapshots": snapshots,
            "snapshot_count": len(snapshots),
            "summary": (
                f"Swarm '{manifest.get('name','')}' "
                f"({len(agent_files)} agent(s), "
                f"{len(snapshots)} snapshot(s), "
                f"{'sealed' if sealed else 'unsealed'})."
            ),
            "data_slush": {
                "swarm_guid": manifest.get("swarm_guid", swarm_dir.name),
                "sealed": sealed,
                "agent_count": len(agent_files),
            },
        })
