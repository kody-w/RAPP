"""
swarm_seal_agent.py — seal/unseal a sibling swarm.

A sealed swarm is marked read-only by convention: other swarm agents
(deploy, invoke's memory writes, snapshot, delete) check for a `.sealed`
marker and refuse writes. Sealing and unsealing are themselves write
operations, so they are the only legal edits to a sealed swarm's
directory — which is why they live in this agent.

Pure filesystem: creates or removes `<swarm_dir>/.sealed`.
"""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from agents.basic_agent import BasicAgent


__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "@rapp/swarm_seal",
    "version": "1.0.0",
    "display_name": "Seal Swarm",
    "description": "Seal or unseal a swarm (marks it read-only by convention).",
    "author": "RAPP",
    "tags": ["starter", "swarm", "infrastructure"],
    "category": "core",
    "quality_tier": "official",
    "requires_env": [],
    "example_call": "Seal swarm <guid> so nothing else can write to it.",
}


_GUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _swarms_root() -> Path:
    """Where sibling swarms live on this device.

    Priority: $BRAINSTEM_SWARMS_PATH env → default ~/.brainstem/swarms/.
    Same pattern as save_memory_agent.py / recall_memory_agent.py.
    """
    p = os.environ.get("BRAINSTEM_SWARMS_PATH")
    return Path(p) if p else Path(os.path.expanduser("~/.brainstem/swarms"))


def _resolve_swarm(guid: str) -> Path:
    if not _GUID_RE.match(guid):
        raise ValueError(f"invalid swarm guid: {guid!r}")
    d = _swarms_root() / guid
    if not d.is_dir():
        raise FileNotFoundError(f"swarm not found: {guid}")
    return d


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class SwarmSealAgent(BasicAgent):
    def __init__(self):
        self.name = "SealSwarm"
        self.metadata = {
            "name": self.name,
            "description": (
                "Seals or unseals a swarm. A sealed swarm is marked "
                "read-only by convention: deploy/invoke-writes/snapshot/"
                "delete all refuse to write to it. Use action='seal' to "
                "lock, action='unseal' to remove the lock, or action='status' "
                "to check without modifying."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "swarm_guid": {
                        "type": "string",
                        "description": "Swarm GUID.",
                    },
                    "action": {
                        "type": "string",
                        "description": "'seal', 'unseal', or 'status'.",
                        "enum": ["seal", "unseal", "status"],
                    },
                    "reason": {
                        "type": "string",
                        "description": "Optional human note stored in the marker.",
                    },
                },
                "required": ["swarm_guid", "action"],
            },
        }
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        try:
            swarm_dir = _resolve_swarm(kwargs.get("swarm_guid", ""))
        except (ValueError, FileNotFoundError) as e:
            return json.dumps({"status": "error", "message": str(e)})

        action = (kwargs.get("action") or "").lower()
        marker = swarm_dir / ".sealed"

        if action == "status":
            sealed = marker.is_file()
            payload = json.loads(marker.read_text()) if sealed else None
            return json.dumps({
                "status": "success",
                "swarm_guid": swarm_dir.name,
                "sealed": sealed,
                "seal_info": payload,
                "summary": f"swarm {swarm_dir.name} is {'sealed' if sealed else 'unsealed'}.",
                "data_slush": {"sealed": sealed},
            })

        if action == "seal":
            if marker.is_file():
                return json.dumps({
                    "status": "success",
                    "swarm_guid": swarm_dir.name,
                    "sealed": True,
                    "summary": f"swarm {swarm_dir.name} was already sealed.",
                    "data_slush": {"sealed": True, "changed": False},
                })
            info = {"sealed_at": _now_iso(), "reason": kwargs.get("reason", "")}
            marker.write_text(json.dumps(info, indent=2), encoding="utf-8")
            return json.dumps({
                "status": "success",
                "swarm_guid": swarm_dir.name,
                "sealed": True,
                "summary": f"Sealed swarm {swarm_dir.name}.",
                "data_slush": {"sealed": True, "changed": True},
            })

        if action == "unseal":
            if not marker.is_file():
                return json.dumps({
                    "status": "success",
                    "swarm_guid": swarm_dir.name,
                    "sealed": False,
                    "summary": f"swarm {swarm_dir.name} was already unsealed.",
                    "data_slush": {"sealed": False, "changed": False},
                })
            marker.unlink()
            return json.dumps({
                "status": "success",
                "swarm_guid": swarm_dir.name,
                "sealed": False,
                "summary": f"Unsealed swarm {swarm_dir.name}.",
                "data_slush": {"sealed": False, "changed": True},
            })

        return json.dumps({
            "status": "error",
            "message": f"unknown action {action!r}; expected 'seal' | 'unseal' | 'status'",
        })
