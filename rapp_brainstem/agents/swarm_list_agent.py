"""
swarm_list_agent.py — list swarms deployed under the twin's state root.

Reads `.brainstem_data/swarms/<guid>/manifest.json` for every subdirectory
and returns a summary. Pure filesystem read; no brainstem core dependency.
"""

import json
import os
from pathlib import Path

from agents.basic_agent import BasicAgent


__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "@rapp/swarm_list",
    "version": "1.0.0",
    "display_name": "List Swarms",
    "description": "Lists every swarm currently deployed on this twin.",
    "author": "RAPP",
    "tags": ["starter", "swarm", "infrastructure"],
    "category": "core",
    "quality_tier": "official",
    "requires_env": [],
    "example_call": "What swarms are deployed?",
}


def _swarms_root() -> Path:
    """Where sibling swarms live on this device.

    Priority: $BRAINSTEM_SWARMS_PATH env → default ~/.brainstem/swarms/.
    Same pattern as save_memory_agent.py / recall_memory_agent.py.
    """
    p = os.environ.get("BRAINSTEM_SWARMS_PATH")
    return Path(p) if p else Path(os.path.expanduser("~/.brainstem/swarms"))


class SwarmListAgent(BasicAgent):
    def __init__(self):
        self.name = "ListSwarms"
        self.metadata = {
            "name": self.name,
            "description": (
                "Lists all swarms currently deployed on this twin. Returns "
                "each swarm's GUID, name, purpose, agent count, seal status, "
                "and creation time. Use this to see what swarms exist before "
                "invoking one."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        }
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        root = _swarms_root()
        if not root.exists():
            return json.dumps({
                "status": "success",
                "swarm_count": 0,
                "swarms": [],
                "summary": f"No swarms deployed yet (root does not exist: {root}).",
            })

        swarms = []
        for entry in sorted(root.iterdir()):
            if not entry.is_dir():
                continue
            manifest_path = entry / "manifest.json"
            if not manifest_path.is_file():
                continue
            try:
                m = json.loads(manifest_path.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            swarms.append({
                "swarm_guid": m.get("swarm_guid", entry.name),
                "name": m.get("name", ""),
                "purpose": m.get("purpose", ""),
                "agent_count": m.get("agent_count", 0),
                "created_at": m.get("created_at", ""),
                "sealed": (entry / ".sealed").is_file(),
            })

        return json.dumps({
            "status": "success",
            "swarm_count": len(swarms),
            "swarms": swarms,
            "summary": f"{len(swarms)} swarm(s) deployed at {root}.",
            "data_slush": {"swarm_count": len(swarms)},
        })
