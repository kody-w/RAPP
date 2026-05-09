"""dock_agent — universal additive-merge primitive.

The docking-without-destruction property — applied at ANY scale of the
RAPP stack, not just neighborhood-grafting. Per the operator's framing:

  > "this should be a part of any part of this stack…going from a single
  >  cell to a full metropolis…even things like rars should have this
  >  assimilation without destruction"

Every layer of the fractal already implements docking at its own scope:

  - ant_agent          → docks new pheromones into a chain (prev_hash linked)
  - rar_loader         → docks new agents into local agents/ (sha256 verified)
  - graft_neighborhood → docks neighborhoods into a repo (bond technique)
  - bond.py egg/hatch  → docks a new kernel onto a brainstem (bond cycle)
  - Dream Catcher      → docks parallel-dimension frames into canon

`dock_agent` is the GENERIC form. Given any rar-shaped registry JSON
(rar/index.json, rar/cards/*.card.json, _metropolis.json, members.json,
neighborhood.json, etc.) and a list of new entries, it:

  1. Reads the existing registry (or creates an empty one).
  2. For each new entry: looks up by stable key (default: "name").
     - If key exists in registry → SKIP (preserve existing).
     - If key absent → APPEND (additive only).
  3. Optionally re-emits sha256 over the canonical merged bytes for
     integrity tracking.
  4. Writes the registry back atomically.
  5. Returns a summary (`rapp-dock-result/1.0`) describing what was
     added vs skipped, plus the parallel-to-Dream-Catcher framing.

Default `dry_run=True`. Like every other dock variant: never overwrites,
never destroys, always logs.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any

try:
    from agents.basic_agent import BasicAgent
except ImportError:
    from basic_agent import BasicAgent


_DOCK_RESULT_SCHEMA = "rapp-dock-result/1.0"


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _read_json_or_default(path: str, default: dict | list) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _atomic_write_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def _entry_key(entry: dict, key_field: str) -> str | None:
    """Read the stable key for dedup. Supports nested keys via dotted path."""
    if "." not in key_field:
        return entry.get(key_field)
    cur = entry
    for part in key_field.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def dock_into_list(target: list, entries: list[dict], key_field: str) -> dict:
    """Merge entries into target (a list) additively. Returns {added, skipped}."""
    existing_keys = {_entry_key(e, key_field) for e in target if isinstance(e, dict)}
    added, skipped = [], []
    for entry in entries:
        if not isinstance(entry, dict):
            skipped.append({"reason": "non_dict_entry", "value": str(entry)[:120]})
            continue
        k = _entry_key(entry, key_field)
        if k is None:
            skipped.append({"reason": f"missing_key_{key_field}", "entry_keys": list(entry.keys())})
            continue
        if k in existing_keys:
            skipped.append({"reason": "key_already_exists", "key": k})
            continue
        target.append(entry)
        existing_keys.add(k)
        added.append({"key": k, "kind": entry.get("kind")})
    return {"added": added, "skipped": skipped}


def _resolve_entries_path(registry: Any, entries_path: str) -> list:
    """Walk the registry to find the list at entries_path (dotted; default 'entries').

    For top-level lists, pass entries_path=''. For nested dicts (like
    _metropolis.json's 'entries' list inside the index dict), pass a
    dotted path. Creates the nested key path on the way down if missing.
    """
    if not entries_path:
        if not isinstance(registry, list):
            raise ValueError("registry is not a list and no entries_path given")
        return registry
    if not isinstance(registry, dict):
        raise ValueError(f"registry must be dict to walk entries_path={entries_path!r}")
    cur = registry
    parts = entries_path.split(".")
    for i, p in enumerate(parts):
        if i == len(parts) - 1:
            if p not in cur or not isinstance(cur[p], list):
                cur[p] = []
            return cur[p]
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = {}
        cur = cur[p]
    raise ValueError("unreachable")


class DockAgent(BasicAgent):
    metadata = {
        "name": "Dock",
        "description": (
            "Universal additive-merge primitive — docks new entries into any "
            "rar-shaped registry (rar/index.json, _metropolis.json, members.json, "
            "any list-of-dicts file) WITHOUT clobbering existing entries. Same "
            "preserve-local property as the bond technique, the Dream Catcher, "
            "the rar_loader, and the graft agent — applied at the entry scope. "
            "Default dry_run=True."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "registry_path": {"type": "string",
                                  "description": "Path to the registry JSON file. Created with default skeleton if absent."},
                "entries_path": {"type": "string", "default": "entries",
                                 "description": "Dotted path to the list of entries inside the registry. Default: 'entries'. Use '' for a top-level list."},
                "key_field": {"type": "string", "default": "name",
                              "description": "Field used to dedup entries (default: 'name'). Supports dotted nested keys."},
                "new_entries": {"type": "array",
                                "description": "List of new entry dicts to merge in additively."},
                "default_skeleton": {"type": "object",
                                     "description": "If registry doesn't exist, create with this skeleton. Default: {schema, entries:[]}."},
                "dry_run": {"type": "boolean", "default": True,
                            "description": "If true, return what would be added without writing."},
                "log_path": {"type": "string",
                             "description": "Optional bonds.json-style path to append a 'dock' event."},
            },
            "required": ["registry_path", "new_entries"],
        },
    }

    def __init__(self):
        self.name = "Dock"

    def perform(self, **kwargs) -> str:
        registry_path = kwargs.get("registry_path") or ""
        if not registry_path:
            return json.dumps({"ok": False, "error": "registry_path required"})
        entries_path = kwargs.get("entries_path", "entries")
        key_field = kwargs.get("key_field") or "name"
        new_entries = kwargs.get("new_entries") or []
        if not isinstance(new_entries, list):
            return json.dumps({"ok": False, "error": "new_entries must be a list"})
        dry_run = kwargs.get("dry_run", True)
        default_skeleton = kwargs.get("default_skeleton") or {
            "schema": "rapp-rar-index/1.0",
            "entries": [],
            "_note": "Created by dock_agent on first dock; subsequent docks append additively.",
        }

        # Read or initialize registry
        if entries_path:
            registry = _read_json_or_default(registry_path, default_skeleton)
        else:
            registry = _read_json_or_default(registry_path, [])

        # Snapshot pre-dock for the bond-preserve-local property
        pre_text = json.dumps(registry, indent=2, sort_keys=True)
        pre_sha256 = _sha256_text(pre_text)

        # Walk to the entries list + merge
        try:
            entries_list = _resolve_entries_path(registry, entries_path)
        except ValueError as e:
            return json.dumps({"ok": False, "error": str(e)})

        merge_result = dock_into_list(entries_list, new_entries, key_field)

        # Re-snapshot post-dock
        post_text = json.dumps(registry, indent=2, sort_keys=True)
        post_sha256 = _sha256_text(post_text)

        # Write (or simulate)
        if not dry_run and merge_result["added"]:
            _atomic_write_json(registry_path, registry)

        # Optional bond-event log
        log_event = None
        log_path = kwargs.get("log_path")
        if log_path and not dry_run and merge_result["added"]:
            log_event = {
                "at": _now_iso(),
                "kind": "dock",
                "registry_path": registry_path,
                "entries_path": entries_path,
                "added_count": len(merge_result["added"]),
                "skipped_count": len(merge_result["skipped"]),
                "pre_sha256": pre_sha256,
                "post_sha256": post_sha256,
            }
            log = _read_json_or_default(log_path, {"events": []})
            if not isinstance(log.get("events"), list):
                log["events"] = []
            log["events"].append(log_event)
            _atomic_write_json(log_path, log)

        return json.dumps({
            "schema": _DOCK_RESULT_SCHEMA,
            "ok": True,
            "dry_run": dry_run,
            "registry_path": registry_path,
            "entries_path": entries_path,
            "key_field": key_field,
            "result": merge_result,
            "summary": {
                "added": len(merge_result["added"]),
                "skipped": len(merge_result["skipped"]),
                "pre_sha256": pre_sha256[:16],
                "post_sha256": post_sha256[:16],
                "preserve_local": pre_sha256 == post_sha256 if not merge_result["added"] else "modified-additively",
            },
            "bond_event": log_event,
            "parallel_to": {
                "_purpose": "Same primitive at every scope of the fractal — additive, content-addressed, append-only, identity-preserving.",
                "ant_agent_pheromone": "dock at frame scope (rapp-frame/1.0 chain)",
                "rar_loader": "dock at agent/organ/sense scope (sha256-verified install)",
                "graft_neighborhood": "dock at neighborhood scope (bond technique)",
                "bond_py_egg_hatch": "dock at kernel scope (egg → overlay → hatch back)",
                "dream_catcher": "dock at parallel-dimension scope (UTC-first canon)",
                "this_dock_agent": "dock at registry/list-of-dicts scope — generic primitive",
            },
        }, indent=2)
