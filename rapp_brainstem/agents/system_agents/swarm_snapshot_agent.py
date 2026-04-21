"""
swarm_snapshot_agent.py — create / list snapshots of a swarm.

A snapshot is a point-in-time copy of a swarm's state (manifest + agents/
+ memory/) stored under `<swarm_dir>/snapshots/<snap_name>/`. Snapshots
are read-only artifacts; nothing in this repo writes to them after
creation.

Supported actions:
  - action='create' (default) — copy the current state into snapshots/<name>/
  - action='list' — enumerate existing snapshots
"""

import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from agents.basic_agent import BasicAgent


__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "@rapp/swarm_snapshot",
    "version": "1.0.0",
    "display_name": "Snapshot Swarm",
    "description": "Create or list read-only snapshots of a swarm's state.",
    "author": "RAPP",
    "tags": ["starter", "swarm", "infrastructure"],
    "category": "core",
    "quality_tier": "official",
    "requires_env": [],
    "example_call": "Snapshot swarm <guid> as 'before-migration'.",
}


_GUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_SNAP_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-]{0,63}$")


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


def _now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


class SwarmSnapshotAgent(BasicAgent):
    def __init__(self):
        self.name = "SnapshotSwarm"
        self.metadata = {
            "name": self.name,
            "description": (
                "Creates or lists snapshots of a swarm. A snapshot is a "
                "read-only copy of the swarm's current state (manifest, "
                "agents, memory) stored under snapshots/<name>/. Use "
                "action='create' with a name to take a snapshot, or "
                "action='list' to enumerate existing ones."
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
                        "description": "'create' (default) or 'list'.",
                        "enum": ["create", "list"],
                    },
                    "name": {
                        "type": "string",
                        "description": (
                            "Snapshot name (used only for 'create'). "
                            "Alphanumeric + dashes/underscores. Defaults to "
                            "a UTC timestamp like '20260421T144301Z'."
                        ),
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

        snapshots_dir = swarm_dir / "snapshots"
        action = (kwargs.get("action") or "create").lower()

        if action == "list":
            existing = sorted(
                p.name for p in snapshots_dir.iterdir() if p.is_dir()
            ) if snapshots_dir.is_dir() else []
            return json.dumps({
                "status": "success",
                "swarm_guid": swarm_dir.name,
                "snapshots": existing,
                "snapshot_count": len(existing),
                "summary": f"{len(existing)} snapshot(s) on swarm {swarm_dir.name}.",
                "data_slush": {"snapshot_count": len(existing)},
            })

        if action != "create":
            return json.dumps({
                "status": "error",
                "message": f"unknown action {action!r}; expected 'create' | 'list'",
            })

        # Refuse to write if sealed
        if (swarm_dir / ".sealed").is_file():
            return json.dumps({
                "status": "error",
                "message": f"swarm {swarm_dir.name} is sealed; unseal before snapshotting",
            })

        snap_name = (kwargs.get("name") or "").strip() or _now_compact()
        if not _SNAP_NAME_RE.match(snap_name):
            return json.dumps({
                "status": "error",
                "message": f"invalid snapshot name {snap_name!r} (alphanumeric + dashes/underscores only)",
            })

        snap_dir = snapshots_dir / snap_name
        if snap_dir.exists():
            return json.dumps({
                "status": "error",
                "message": f"snapshot {snap_name!r} already exists on swarm {swarm_dir.name}",
            })

        # Copy manifest + agents/ + memory/ (but NOT snapshots/ — no nesting)
        snap_dir.mkdir(parents=True, exist_ok=False)
        if (swarm_dir / "manifest.json").is_file():
            shutil.copy2(swarm_dir / "manifest.json", snap_dir / "manifest.json")
        if (swarm_dir / "agents").is_dir():
            shutil.copytree(swarm_dir / "agents", snap_dir / "agents")
        if (swarm_dir / "memory").is_dir():
            shutil.copytree(swarm_dir / "memory", snap_dir / "memory")

        # Stamp the snapshot itself with a tiny manifest
        (snap_dir / ".snapshot.json").write_text(
            json.dumps({
                "schema": "rapp-snapshot/1.0",
                "swarm_guid": swarm_dir.name,
                "snapshot_name": snap_name,
                "taken_at": _now_iso(),
            }, indent=2),
            encoding="utf-8",
        )

        return json.dumps({
            "status": "success",
            "swarm_guid": swarm_dir.name,
            "snapshot_name": snap_name,
            "path": str(snap_dir),
            "summary": f"Snapshotted swarm {swarm_dir.name} as '{snap_name}'.",
            "data_slush": {
                "snapshot_name": snap_name,
                "swarm_guid": swarm_dir.name,
            },
        })
