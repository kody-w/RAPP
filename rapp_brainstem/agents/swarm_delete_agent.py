"""
swarm_delete_agent.py — remove a sibling swarm from disk.

Refuses if the swarm is sealed (Article XIV/XI: sealed = read-only by
convention). To delete a sealed swarm, unseal it first with SealSwarm.
"""

import json
import os
import re
import shutil
from pathlib import Path

from agents.basic_agent import BasicAgent


__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "@rapp/swarm_delete",
    "version": "1.0.0",
    "display_name": "Delete Swarm",
    "description": "Removes a swarm directory. Refuses if the swarm is sealed.",
    "author": "RAPP",
    "tags": ["starter", "swarm", "infrastructure"],
    "category": "core",
    "quality_tier": "official",
    "requires_env": [],
    "example_call": "Delete swarm <guid>.",
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


class SwarmDeleteAgent(BasicAgent):
    def __init__(self):
        self.name = "DeleteSwarm"
        self.metadata = {
            "name": self.name,
            "description": (
                "Removes a swarm directory from disk. Refuses if the swarm "
                "is sealed — unseal it first with SealSwarm(action='unseal') "
                "if you really mean to delete. Pass confirm=true to proceed; "
                "this is irreversible."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "swarm_guid": {
                        "type": "string",
                        "description": "GUID of the swarm to remove.",
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "Must be true. Guards against accidental deletes.",
                    },
                },
                "required": ["swarm_guid", "confirm"],
            },
        }
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        if not kwargs.get("confirm"):
            return json.dumps({
                "status": "error",
                "message": "refusing to delete without confirm=true",
            })

        try:
            swarm_dir = _resolve_swarm(kwargs.get("swarm_guid", ""))
        except (ValueError, FileNotFoundError) as e:
            return json.dumps({"status": "error", "message": str(e)})

        if (swarm_dir / ".sealed").is_file():
            return json.dumps({
                "status": "error",
                "message": (
                    f"swarm {swarm_dir.name} is sealed; unseal with "
                    f"SealSwarm(action='unseal') before deleting"
                ),
            })

        try:
            shutil.rmtree(swarm_dir)
        except OSError as e:
            return json.dumps({"status": "error", "message": f"delete failed: {e}"})

        return json.dumps({
            "status": "success",
            "swarm_guid": swarm_dir.name,
            "summary": f"Deleted swarm {swarm_dir.name}.",
            "data_slush": {"deleted_swarm": swarm_dir.name},
        })
