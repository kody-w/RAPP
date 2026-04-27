"""
peer_registry.py — shared local-machine registry of installed brainstems.

A "good neighbor" pattern for multi-brainstem hosts: each install records
its claimed port + brainstem dir at a shared XDG path so subsequent
installs can pick non-conflicting ports, and a running brainstem can
discover its peers without a tree search.

Registry schema (forever-additive, like the /chat envelope):
    {
      "schema": "rapp-peers/1.0",
      "peers": [
        {
          "id":             "<sha256(brainstem_dir)[:12]>",
          "brainstem_dir":  "/abs/path/to/.brainstem/src/rapp_brainstem",
          "port":           7072,
          "is_global":      false,
          "project_name":   "my-project",
          "installed_at":   "2026-04-26T20:30:00Z",
          "version":        "0.12.2"
        }, ...
      ]
    }

The registry is intentionally a passive ledger — entries are appended on
install and read on lookup. Liveness is determined by probing /health, not
by entries getting "registered" and "unregistered" at runtime. This keeps
the data model simple and survives ungraceful brainstem shutdowns.
"""

import hashlib
import json
import os
import time
from typing import Optional


SCHEMA = "rapp-peers/1.0"


def registry_path() -> str:
    """XDG-style registry path: $XDG_CONFIG_HOME/rapp/peers.json or ~/.config/rapp/peers.json."""
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "rapp", "peers.json")


def _peer_id(brainstem_dir: str) -> str:
    return hashlib.sha256(os.path.abspath(brainstem_dir).encode()).hexdigest()[:12]


def _project_name(brainstem_dir: str) -> str:
    """Best-effort project label from the path. /Users/x/proj/.brainstem/src/rapp_brainstem → 'proj'.
    The global install at $HOME/.brainstem/... is labeled 'global' instead of $USER."""
    if _is_global(brainstem_dir):
        return "global"
    parts = os.path.abspath(brainstem_dir).split(os.sep)
    try:
        bs_idx = parts.index(".brainstem")
        return parts[bs_idx - 1] if bs_idx > 0 else "global"
    except ValueError:
        return os.path.basename(os.path.dirname(brainstem_dir)) or "unknown"


def _is_global(brainstem_dir: str) -> bool:
    """Global install lives directly under $HOME/.brainstem (not project-local)."""
    home = os.path.expanduser("~")
    return os.path.abspath(brainstem_dir).startswith(os.path.join(home, ".brainstem", ""))


def load() -> dict:
    """Read the registry. Returns the empty registry if missing or unparseable."""
    path = registry_path()
    if not os.path.exists(path):
        return {"schema": SCHEMA, "peers": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "peers" not in data:
            return {"schema": SCHEMA, "peers": []}
        data.setdefault("schema", SCHEMA)
        return data
    except (json.JSONDecodeError, OSError):
        return {"schema": SCHEMA, "peers": []}


def _save(data: dict) -> None:
    path = registry_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def upsert(brainstem_dir: str, port: int, version: Optional[str] = None) -> dict:
    """Add or update a peer entry. Idempotent — repeat installs at the same dir overwrite cleanly."""
    abs_dir = os.path.abspath(brainstem_dir)
    pid = _peer_id(abs_dir)
    entry = {
        "id": pid,
        "brainstem_dir": abs_dir,
        "port": int(port),
        "is_global": _is_global(abs_dir),
        "project_name": _project_name(abs_dir),
        "installed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "version": version or "",
    }
    data = load()
    data["peers"] = [p for p in data["peers"] if p.get("id") != pid]
    data["peers"].append(entry)
    _save(data)
    return entry


def forget(brainstem_dir: str) -> bool:
    """Remove a peer entry. Returns True if anything was removed."""
    pid = _peer_id(brainstem_dir)
    data = load()
    before = len(data["peers"])
    data["peers"] = [p for p in data["peers"] if p.get("id") != pid]
    removed = len(data["peers"]) != before
    if removed:
        _save(data)
    return removed


def claimed_ports() -> set:
    """Set of ports currently claimed by registered peers — for find_free_port to avoid."""
    data = load()
    return {int(p["port"]) for p in data["peers"] if isinstance(p.get("port"), int)}


if __name__ == "__main__":
    # CLI shim so install.sh can shell out for upsert/claimed-ports without
    # rewriting the logic in bash. Usage:
    #   python3 peer_registry.py claimed-ports
    #   python3 peer_registry.py upsert <brainstem_dir> <port> [version]
    #   python3 peer_registry.py forget <brainstem_dir>
    #   python3 peer_registry.py list
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "claimed-ports":
        print(" ".join(str(p) for p in sorted(claimed_ports())))
    elif cmd == "upsert":
        e = upsert(sys.argv[2], int(sys.argv[3]), sys.argv[4] if len(sys.argv) > 4 else None)
        print(json.dumps(e))
    elif cmd == "forget":
        print("removed" if forget(sys.argv[2]) else "not-found")
    elif cmd == "list":
        print(json.dumps(load(), indent=2))
    else:
        print(f"unknown command: {cmd}", file=sys.stderr)
        sys.exit(2)
