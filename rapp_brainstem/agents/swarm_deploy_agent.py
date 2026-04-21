"""
swarm_deploy_agent.py — install a rapp-swarm/1.0 bundle as a sibling swarm.

A "swarm" is a directory under the twin's state root (`.brainstem_data/swarms/
<guid>/`) holding its own agents, soul, and memory. This agent takes a bundle
describing a swarm and materializes it on disk. Nothing else.

Drop-in compatibility: uses only BasicAgent + stdlib + filesystem. No new
brainstem core symbols, no imports from sibling agent files. Copy this file
into any v1-compliant brainstem and it works.
"""

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from agents.basic_agent import BasicAgent


__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "@rapp/swarm_deploy",
    "version": "1.0.0",
    "display_name": "Deploy Swarm",
    "description": "Installs a rapp-swarm/1.0 bundle into the twin's swarms directory.",
    "author": "RAPP",
    "tags": ["starter", "swarm", "infrastructure"],
    "category": "core",
    "quality_tier": "official",
    "requires_env": [],
    "example_call": "Deploy the swarm bundle saved at /tmp/mybundle.json.",
}


# ─── Swarm state layout (Article XVI / XI — state in .brainstem_data/) ──

def _swarms_root() -> Path:
    """Resolve `.brainstem_data/swarms/` for the active twin.

    Priority: $BRAINSTEM_HOME/swarms → <cwd>/.brainstem_data/swarms
    → ~/.brainstem_data/swarms. First option that exists or can be created.
    """
    override = os.environ.get("BRAINSTEM_HOME")
    if override:
        return (Path(override).expanduser() / "swarms").resolve()
    here_local = (Path.cwd() / ".brainstem_data" / "swarms").resolve()
    if (Path.cwd() / "brainstem.py").is_file() or (Path.cwd() / ".brainstem_data").is_dir():
        return here_local
    return (Path.home() / ".brainstem_data" / "swarms").resolve()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


_SAFE_FILENAME_RE = re.compile(r"^[A-Za-z0-9_.\-]+\.py$")


def _load_bundle(kwargs: dict) -> dict:
    """Accept a bundle dict inline OR a filesystem path to a bundle JSON."""
    if kwargs.get("bundle") is not None:
        b = kwargs["bundle"]
        if isinstance(b, str):
            b = json.loads(b)
        if not isinstance(b, dict):
            raise ValueError("bundle must be an object or a JSON string")
        return b
    path = kwargs.get("bundle_path")
    if path:
        with open(os.path.expanduser(path)) as fh:
            return json.load(fh)
    raise ValueError("must provide either 'bundle' or 'bundle_path'")


def _validate_bundle(b: dict) -> None:
    if b.get("schema") not in ("rapp-swarm/1.0", None):
        raise ValueError(f"unsupported bundle schema: {b.get('schema')!r}")
    if not b.get("name") or not isinstance(b["name"], str):
        raise ValueError("bundle.name is required (string)")
    agents = b.get("agents") or []
    if not isinstance(agents, list):
        raise ValueError("bundle.agents must be an array")
    for i, a in enumerate(agents):
        if not isinstance(a, dict):
            raise ValueError(f"bundle.agents[{i}] must be an object")
        fname = a.get("filename") or ""
        if not _SAFE_FILENAME_RE.match(fname):
            raise ValueError(f"bundle.agents[{i}].filename is invalid: {fname!r}")
        if not fname.endswith("_agent.py"):
            raise ValueError(f"bundle.agents[{i}].filename must end with '_agent.py'")
        if not isinstance(a.get("source", ""), str):
            raise ValueError(f"bundle.agents[{i}].source must be a string")


class SwarmDeployAgent(BasicAgent):
    def __init__(self):
        self.name = "DeploySwarm"
        self.metadata = {
            "name": self.name,
            "description": (
                "Installs a rapp-swarm/1.0 bundle as a new sibling swarm on "
                "this twin. A bundle has a name, optional purpose/soul, and "
                "a list of agent files ({filename, source}). On success, "
                "returns the new swarm's GUID — use it with ListSwarms, "
                "InvokeSwarm, SnapshotSwarm, SealSwarm, or DeleteSwarm."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "bundle": {
                        "type": "object",
                        "description": (
                            "Inline rapp-swarm/1.0 bundle object: "
                            "{name, purpose?, soul?, created_by?, agents: [{filename, source}]}. "
                            "Either this OR bundle_path must be provided."
                        ),
                    },
                    "bundle_path": {
                        "type": "string",
                        "description": (
                            "Filesystem path to a bundle JSON file. Use when "
                            "the bundle is too large to pass inline."
                        ),
                    },
                },
                "required": [],
            },
        }
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        try:
            bundle = _load_bundle(kwargs)
            _validate_bundle(bundle)
        except (ValueError, OSError, json.JSONDecodeError) as e:
            return json.dumps({"status": "error", "message": str(e)})

        root = _swarms_root()
        root.mkdir(parents=True, exist_ok=True)

        swarm_guid = str(uuid.uuid4())
        swarm_dir = root / swarm_guid
        if swarm_dir.exists():
            return json.dumps({"status": "error", "message": f"GUID collision: {swarm_guid}"})

        agents_dir = swarm_dir / "agents"
        memory_dir = swarm_dir / "memory" / "shared"
        agents_dir.mkdir(parents=True, exist_ok=True)
        memory_dir.mkdir(parents=True, exist_ok=True)

        written = []
        for a in bundle.get("agents") or []:
            dest = agents_dir / a["filename"]
            dest.write_text(a.get("source") or "", encoding="utf-8")
            written.append(a["filename"])

        manifest = {
            "schema": "rapp-swarm/1.0",
            "swarm_guid": swarm_guid,
            "name": bundle["name"],
            "purpose": bundle.get("purpose", ""),
            "soul": bundle.get("soul", ""),
            "created_by": bundle.get("created_by", ""),
            "created_at": _now_iso(),
            "agent_count": len(written),
            "agents": written,
        }
        (swarm_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )

        return json.dumps({
            "status": "success",
            "swarm_guid": swarm_guid,
            "name": manifest["name"],
            "path": str(swarm_dir),
            "agent_count": manifest["agent_count"],
            "summary": f"Deployed swarm '{manifest['name']}' with {manifest['agent_count']} agent(s) at {swarm_dir}",
            "data_slush": {
                "swarm_guid": swarm_guid,
                "swarm_path": str(swarm_dir),
                "agent_count": manifest["agent_count"],
            },
        })
