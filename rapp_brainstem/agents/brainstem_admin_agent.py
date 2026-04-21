"""
brainstem_admin_agent.py — manage agent groups, export/import .egg snapshots,
and query brainstem state. Fully agent-first: any LLM with tool access can
administer the brainstem without touching the UI.
"""

import json
import os
import glob
import zipfile
import io
import hashlib
from datetime import datetime, timezone
from agents.basic_agent import BasicAgent


__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "@rapp/brainstem_admin",
    "version": "1.0.0",
    "display_name": "Brainstem Admin",
    "description": "Manage agent groups, switch contexts, and export/import portable .egg snapshots.",
    "author": "RAPP",
    "tags": ["admin", "groups", "egg", "portability", "core"],
    "category": "core",
    "quality_tier": "official",
    "requires_env": [],
    "example_call": "Show me my agent groups and which one is active.",
}

_BRAINSTEM_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_AGENTS_DIR = os.path.join(_BRAINSTEM_DIR, "agents")
_GROUPS_FILE = os.path.join(_BRAINSTEM_DIR, ".agent_groups.json")
_DISABLED_FILE = os.path.join(_AGENTS_DIR, ".agents_disabled.json")

EXCLUDE_NAMES = {"server.pid", "server.log", ".DS_Store", "__pycache__", "voice.zip"}
EXCLUDE_SUFFIXES = (".pyc",)


def _read_groups():
    if os.path.exists(_GROUPS_FILE):
        try:
            with open(_GROUPS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"schema": "rapp-groups/1.0", "active": None, "groups": {}}


def _write_groups(data):
    data.setdefault("schema", "rapp-groups/1.0")
    with open(_GROUPS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _list_agent_files():
    files = glob.glob(os.path.join(_AGENTS_DIR, "*_agent.py"))
    return sorted([os.path.basename(f) for f in files if os.path.basename(f) != "basic_agent.py"])


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _should_skip(path):
    name = os.path.basename(path)
    if name in EXCLUDE_NAMES:
        return True
    if any(part in EXCLUDE_NAMES for part in path.split(os.sep)):
        return True
    return any(path.endswith(s) for s in EXCLUDE_SUFFIXES)


class BrainstemAdmin(BasicAgent):
    def __init__(self):
        self.name = "BrainstemAdmin"
        self.metadata = {
            "name": self.name,
            "description": (
                "Administers the brainstem itself. Use this tool to:\n"
                "- List, create, delete, or switch agent groups (e.g. personal, business, project-X)\n"
                "- See which agents are available and which group is active\n"
                "- Export the entire brainstem as a portable .egg snapshot (agents, memories, soul, groups)\n"
                "- Import a .egg to restore a brainstem state\n"
                "- Check brainstem status\n\n"
                "Call with an action and optional parameters."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "status",
                            "list_agents",
                            "list_groups",
                            "create_group",
                            "update_group",
                            "delete_group",
                            "switch_group",
                            "export_egg",
                            "egg_info",
                        ],
                        "description": (
                            "status: brainstem overview. "
                            "list_agents: all agent files. "
                            "list_groups: all groups + active. "
                            "create_group: make a new group. "
                            "update_group: change agents in a group. "
                            "delete_group: remove a group. "
                            "switch_group: activate a group (null=all). "
                            "export_egg: save .egg to disk. "
                            "egg_info: inspect an existing .egg file."
                        ),
                    },
                    "group_name": {
                        "type": "string",
                        "description": "Group name for create/update/delete/switch actions.",
                    },
                    "agents": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Agent filenames (e.g. ['hacker_news_agent.py']) for create/update.",
                    },
                    "soul_override": {
                        "type": "string",
                        "description": "Optional path to a soul.md override for this group.",
                    },
                    "egg_path": {
                        "type": "string",
                        "description": "File path for export_egg output or egg_info input.",
                    },
                },
                "required": ["action"],
            },
        }
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, action, group_name=None, agents=None, soul_override=None, egg_path=None, **kwargs):
        try:
            if action == "status":
                return self._status()
            elif action == "list_agents":
                return self._list_agents()
            elif action == "list_groups":
                return self._list_groups()
            elif action == "create_group":
                return self._create_group(group_name, agents or [], soul_override)
            elif action == "update_group":
                return self._update_group(group_name, agents, soul_override)
            elif action == "delete_group":
                return self._delete_group(group_name)
            elif action == "switch_group":
                return self._switch_group(group_name)
            elif action == "export_egg":
                return self._export_egg(egg_path)
            elif action == "egg_info":
                return self._egg_info(egg_path)
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _status(self):
        gdata = _read_groups()
        all_files = _list_agent_files()
        active = gdata.get("active")
        group_filter = None
        if active:
            grp = gdata.get("groups", {}).get(active, {})
            group_filter = set(grp.get("agents", []))

        loaded = [f for f in all_files if group_filter is None or f in group_filter]
        data_dir = os.path.join(_BRAINSTEM_DIR, ".brainstem_data")
        has_memories = os.path.isdir(data_dir) and any(os.scandir(data_dir))

        return json.dumps({
            "brainstem_dir": _BRAINSTEM_DIR,
            "total_agents": len(all_files),
            "loaded_agents": len(loaded),
            "active_group": active,
            "groups": list(gdata.get("groups", {}).keys()),
            "has_memories": has_memories,
            "soul_path": os.path.join(_BRAINSTEM_DIR, "soul.md"),
        }, indent=2)

    def _list_agents(self):
        files = _list_agent_files()
        disabled = set()
        if os.path.exists(_DISABLED_FILE):
            try:
                with open(_DISABLED_FILE) as f:
                    disabled = set(json.load(f))
            except Exception:
                pass
        gdata = _read_groups()
        result = []
        for fname in files:
            groups_in = [g for g, d in gdata.get("groups", {}).items() if fname in d.get("agents", [])]
            result.append({
                "filename": fname,
                "enabled": fname not in disabled,
                "groups": groups_in,
            })
        return json.dumps({"agents": result, "total": len(result)}, indent=2)

    def _list_groups(self):
        gdata = _read_groups()
        return json.dumps(gdata, indent=2)

    def _create_group(self, name, agent_files, soul_override=None):
        if not name:
            return json.dumps({"error": "group_name is required"})
        gdata = _read_groups()
        if name in gdata.get("groups", {}):
            return json.dumps({"error": f"Group '{name}' already exists. Use update_group to modify it."})
        gdata.setdefault("groups", {})[name] = {
            "agents": agent_files,
            "soul_override": soul_override,
            "memory_namespace": name,
        }
        _write_groups(gdata)
        return json.dumps({"status": "ok", "created": name, "agents": agent_files})

    def _update_group(self, name, agent_files=None, soul_override=None):
        if not name:
            return json.dumps({"error": "group_name is required"})
        gdata = _read_groups()
        grp = gdata.get("groups", {}).get(name)
        if not grp:
            return json.dumps({"error": f"Group '{name}' not found"})
        if agent_files is not None:
            grp["agents"] = agent_files
        if soul_override is not None:
            grp["soul_override"] = soul_override or None
        _write_groups(gdata)
        return json.dumps({"status": "ok", "updated": name, "data": grp})

    def _delete_group(self, name):
        if not name:
            return json.dumps({"error": "group_name is required"})
        gdata = _read_groups()
        if name not in gdata.get("groups", {}):
            return json.dumps({"error": f"Group '{name}' not found"})
        del gdata["groups"][name]
        if gdata.get("active") == name:
            gdata["active"] = None
            try:
                import sys
                main = sys.modules.get("__main__")
                if main and hasattr(main, "_ACTIVE_GROUP"):
                    main._ACTIVE_GROUP = None
            except Exception:
                pass
        _write_groups(gdata)
        return json.dumps({"status": "ok", "deleted": name})

    def _switch_group(self, name):
        gdata = _read_groups()
        if name and name not in gdata.get("groups", {}):
            return json.dumps({"error": f"Group '{name}' not found. Available: {list(gdata.get('groups', {}).keys())}"})
        gdata["active"] = name
        _write_groups(gdata)
        try:
            import sys
            main = sys.modules.get("__main__")
            if main and hasattr(main, "_ACTIVE_GROUP"):
                main._ACTIVE_GROUP = name
        except Exception:
            pass
        if name:
            agents = gdata["groups"][name].get("agents", [])
            return json.dumps({"status": "ok", "active": name, "agents_in_group": agents})
        return json.dumps({"status": "ok", "active": None, "message": "All agents are now active."})

    def _export_egg(self, out_path=None):
        if not out_path:
            out_path = os.path.join(_BRAINSTEM_DIR, "digitaltwin.rappid.egg")

        files_added = []
        agent_sources = []

        def add_tree(zf, real_root, arc_prefix):
            for dirpath, dirnames, filenames in os.walk(real_root):
                dirnames[:] = [d for d in dirnames if d not in EXCLUDE_NAMES]
                for fname in sorted(filenames):
                    full = os.path.join(dirpath, fname)
                    if _should_skip(full):
                        continue
                    rel = os.path.relpath(full, real_root)
                    arc = arc_prefix + "/" + rel
                    zf.write(full, arcname=arc)
                    sz = os.path.getsize(full)
                    files_added.append({"arc": arc, "sha256": _sha256(full), "bytes": sz})

        with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            if os.path.isdir(_AGENTS_DIR):
                add_tree(zf, _AGENTS_DIR, "agents")
                for f in sorted(glob.glob(os.path.join(_AGENTS_DIR, "*_agent.py"))):
                    fname = os.path.basename(f)
                    if fname == "basic_agent.py":
                        continue
                    try:
                        src = open(f, "r", encoding="utf-8").read()
                        name = fname.replace("_agent.py", "").replace("_", " ").title().replace(" ", "")
                        desc = ""
                        for line in src.splitlines():
                            if '"description"' in line or "'description'" in line:
                                desc = line.split(":", 1)[-1].strip().strip('",').strip("',")[:200]
                                break
                        agent_sources.append({
                            "filename": fname,
                            "name": name,
                            "description": desc,
                            "source": src,
                        })
                    except Exception:
                        pass

            data_dir = os.path.join(_BRAINSTEM_DIR, ".brainstem_data")
            if os.path.isdir(data_dir):
                add_tree(zf, data_dir, ".brainstem_data")

            soul_text = ""
            for config in ["soul.md", ".agent_groups.json"]:
                full = os.path.join(_BRAINSTEM_DIR, config)
                if os.path.isfile(full):
                    zf.write(full, arcname=config)
                    files_added.append({"arc": config, "sha256": _sha256(full), "bytes": os.path.getsize(full)})
                    if config == "soul.md":
                        soul_text = open(full, "r", encoding="utf-8").read()

            if os.path.isfile(_DISABLED_FILE):
                zf.write(_DISABLED_FILE, arcname=".agents_disabled.json")
                files_added.append({"arc": ".agents_disabled.json", "sha256": _sha256(_DISABLED_FILE), "bytes": os.path.getsize(_DISABLED_FILE)})

            memory_entries = []
            mem_dir = os.path.join(_BRAINSTEM_DIR, ".brainstem_data")
            if os.path.isdir(mem_dir):
                for mf in glob.glob(os.path.join(mem_dir, "**", "*.json"), recursive=True):
                    try:
                        memory_entries.append({
                            "key": os.path.relpath(mf, mem_dir),
                            "data": json.loads(open(mf).read()),
                        })
                    except Exception:
                        pass

            gdata = _read_groups()
            now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            twin_bundle = {
                "schema": "rapp-twin/1.0",
                "handle": "@digitaltwin",
                "cloud_id": "egg-" + hashlib.sha256(now.encode()).hexdigest()[:16],
                "origin": "brainstem-egg",
                "exported_at": now,
                "soul": soul_text,
                "groups": gdata.get("groups", {}),
                "active_group": gdata.get("active"),
                "memory": memory_entries,
                "swarms": [{
                    "schema": "rapp-swarm/1.0",
                    "swarm_guid": hashlib.sha256(("egg-swarm-" + now).encode()).hexdigest()[:36],
                    "name": "Brainstem Agents",
                    "purpose": "All agents from the exported brainstem",
                    "soul": soul_text,
                    "created_at": now,
                    "agents": agent_sources,
                }],
            }
            zf.writestr("digitaltwin.json", json.dumps(twin_bundle, indent=2))

            agent_count = len(agent_sources)
            manifest = {
                "schema": "rapp-egg/1.0",
                "egg_type": "brainstem",
                "egg_version": 2,
                "created_at": now,
                "host": os.uname().nodename if hasattr(os, "uname") else "unknown",
                "portable": True,
                "stats": {
                    "agent_count": agent_count,
                    "file_count": len(files_added),
                    "total_bytes": sum(f["bytes"] for f in files_added),
                },
                "files": files_added,
            }
            zf.writestr("egg-manifest.json", json.dumps(manifest, indent=2, sort_keys=True))

        size_kb = os.path.getsize(out_path) / 1024
        return json.dumps({
            "status": "ok",
            "egg_path": out_path,
            "size_kb": round(size_kb, 1),
            "files_packed": len(files_added),
            "agent_count": agent_count,
        })

    def _egg_info(self, path):
        if not path:
            eggs = glob.glob(os.path.join(_BRAINSTEM_DIR, "*.egg"))
            if not eggs:
                return json.dumps({"error": "No .egg files found. Provide egg_path or export one first."})
            path = max(eggs, key=os.path.getmtime)

        if not os.path.isfile(path):
            return json.dumps({"error": f"File not found: {path}"})

        with zipfile.ZipFile(path, "r") as zf:
            manifest = json.loads(zf.read("egg-manifest.json"))

        return json.dumps({
            "egg_path": path,
            "schema": manifest.get("schema"),
            "egg_type": manifest.get("egg_type"),
            "created_at": manifest.get("created_at"),
            "host": manifest.get("host"),
            "stats": manifest.get("stats"),
        }, indent=2)
