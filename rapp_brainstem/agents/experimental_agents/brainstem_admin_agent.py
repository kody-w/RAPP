"""
brainstem_admin_agent.py — manage swarms, export/import .egg snapshots,
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
    "version": "2.0.0",
    "display_name": "Brainstem Admin",
    "description": "Manage swarms (agent collections), switch contexts, layer multiple swarms, and export/import portable .egg snapshots.",
    "author": "RAPP",
    "tags": ["admin", "swarms", "egg", "portability", "core"],
    "category": "core",
    "quality_tier": "official",
    "requires_env": [],
    "example_call": "Show me my swarms and which ones are active.",
}

_BRAINSTEM_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_AGENTS_DIR = os.path.join(_BRAINSTEM_DIR, "agents")
_SWARMS_FILE = os.path.join(_BRAINSTEM_DIR, ".swarms.json")
_DISABLED_FILE = os.path.join(_AGENTS_DIR, ".agents_disabled.json")

EXCLUDE_NAMES = {"server.pid", "server.log", ".DS_Store", "__pycache__", "voice.zip"}
EXCLUDE_SUFFIXES = (".pyc",)


def _read_swarms():
    if os.path.exists(_SWARMS_FILE):
        try:
            with open(_SWARMS_FILE) as f:
                data = json.load(f)
            if isinstance(data.get("active"), str):
                data["active"] = [data["active"]] if data["active"] else []
            return data
        except Exception:
            pass
    return {"schema": "rapp-swarms/1.0", "active": [], "swarms": {}}


def _write_swarms(data):
    data.setdefault("schema", "rapp-swarms/1.0")
    if isinstance(data.get("active"), str):
        data["active"] = [data["active"]] if data["active"] else []
    with open(_SWARMS_FILE, "w") as f:
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
                "- List, create, delete, or load swarms (e.g. work, personal, project-X)\n"
                "- Load multiple swarms at once for layered agent access (Venn diagram style)\n"
                "- Toggle swarm mode between 'stack' (individual agents) and 'converged' (unified agent)\n"
                "- See which agents are available and which swarms are active\n"
                "- Export the entire brainstem as a portable .egg snapshot (agents, memories, soul, swarms)\n"
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
                            "list_swarms",
                            "create_swarm",
                            "update_swarm",
                            "delete_swarm",
                            "load_swarms",
                            "set_mode",
                            "export_egg",
                            "egg_info",
                        ],
                        "description": (
                            "status: brainstem overview. "
                            "list_agents: all agent files. "
                            "list_swarms: all swarms + active. "
                            "create_swarm: make a new swarm. "
                            "update_swarm: change agents/mode in a swarm. "
                            "delete_swarm: remove a swarm. "
                            "load_swarms: activate one or more swarms (pass array; empty=all). "
                            "set_mode: toggle a swarm between 'stack' and 'converged'. "
                            "export_egg: save .egg to disk. "
                            "egg_info: inspect an existing .egg file."
                        ),
                    },
                    "swarm_name": {
                        "type": "string",
                        "description": "Swarm name for create/update/delete/set_mode actions.",
                    },
                    "swarm_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Array of swarm names to load (for load_swarms). Empty array = all agents.",
                    },
                    "agents": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Agent filenames (e.g. ['hacker_news_agent.py']) for create/update.",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["stack", "converged"],
                        "description": "Swarm mode: 'stack' = individual agents, 'converged' = unified single agent.",
                    },
                    "soul_override": {
                        "type": "string",
                        "description": "Optional path to a soul.md override for this swarm.",
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

    def perform(self, action, swarm_name=None, swarm_names=None, agents=None,
                mode=None, soul_override=None, egg_path=None,
                group_name=None, **kwargs):
        # backward compat: accept group_name as alias for swarm_name
        if not swarm_name and group_name:
            swarm_name = group_name
        try:
            if action == "status":
                return self._status()
            elif action == "list_agents":
                return self._list_agents()
            elif action in ("list_swarms", "list_groups"):
                return self._list_swarms()
            elif action in ("create_swarm", "create_group"):
                return self._create_swarm(swarm_name, agents or [], mode or "stack", soul_override)
            elif action in ("update_swarm", "update_group"):
                return self._update_swarm(swarm_name, agents, mode, soul_override)
            elif action in ("delete_swarm", "delete_group"):
                return self._delete_swarm(swarm_name)
            elif action in ("load_swarms", "switch_group"):
                if action == "switch_group" and swarm_name:
                    swarm_names = [swarm_name] if swarm_name else []
                return self._load_swarms(swarm_names or [])
            elif action == "set_mode":
                return self._set_mode(swarm_name, mode or "stack")
            elif action == "export_egg":
                return self._export_egg(egg_path)
            elif action == "egg_info":
                return self._egg_info(egg_path)
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _status(self):
        sdata = _read_swarms()
        all_files = _list_agent_files()
        active = sdata.get("active", [])
        swarm_filter = None
        if active:
            swarm_filter = set()
            for sname in active:
                swarm = sdata.get("swarms", {}).get(sname, {})
                swarm_filter.update(swarm.get("agents", []))

        loaded = [f for f in all_files if swarm_filter is None or f in swarm_filter]
        data_dir = os.path.join(_BRAINSTEM_DIR, ".brainstem_data")
        has_memories = os.path.isdir(data_dir) and any(os.scandir(data_dir))

        return json.dumps({
            "brainstem_dir": _BRAINSTEM_DIR,
            "total_agents": len(all_files),
            "loaded_agents": len(loaded),
            "active_swarms": active,
            "swarms": list(sdata.get("swarms", {}).keys()),
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
        sdata = _read_swarms()
        result = []
        for fname in files:
            swarms_in = [s for s, d in sdata.get("swarms", {}).items() if fname in d.get("agents", [])]
            result.append({
                "filename": fname,
                "enabled": fname not in disabled,
                "swarms": swarms_in,
            })
        return json.dumps({"agents": result, "total": len(result)}, indent=2)

    def _list_swarms(self):
        sdata = _read_swarms()
        return json.dumps(sdata, indent=2)

    def _create_swarm(self, name, agent_files, mode="stack", soul_override=None):
        if not name:
            return json.dumps({"error": "swarm_name is required"})
        sdata = _read_swarms()
        if name in sdata.get("swarms", {}):
            return json.dumps({"error": f"Swarm '{name}' already exists. Use update_swarm to modify it."})
        sdata.setdefault("swarms", {})[name] = {
            "agents": agent_files,
            "mode": mode,
            "soul_override": soul_override,
            "memory_namespace": name,
        }
        _write_swarms(sdata)
        return json.dumps({"status": "ok", "created": name, "agents": agent_files, "mode": mode})

    def _update_swarm(self, name, agent_files=None, mode=None, soul_override=None):
        if not name:
            return json.dumps({"error": "swarm_name is required"})
        sdata = _read_swarms()
        swarm = sdata.get("swarms", {}).get(name)
        if not swarm:
            return json.dumps({"error": f"Swarm '{name}' not found"})
        if agent_files is not None:
            swarm["agents"] = agent_files
        if mode is not None:
            swarm["mode"] = mode
        if soul_override is not None:
            swarm["soul_override"] = soul_override or None
        _write_swarms(sdata)
        return json.dumps({"status": "ok", "updated": name, "data": swarm})

    def _delete_swarm(self, name):
        if not name:
            return json.dumps({"error": "swarm_name is required"})
        sdata = _read_swarms()
        if name not in sdata.get("swarms", {}):
            return json.dumps({"error": f"Swarm '{name}' not found"})
        del sdata["swarms"][name]
        active = sdata.get("active", [])
        if name in active:
            active.remove(name)
            sdata["active"] = active
            try:
                import sys
                main = sys.modules.get("__main__")
                if main and hasattr(main, "_ACTIVE_SWARMS"):
                    main._ACTIVE_SWARMS = active
            except Exception:
                pass
        _write_swarms(sdata)
        return json.dumps({"status": "ok", "deleted": name})

    def _load_swarms(self, names):
        sdata = _read_swarms()
        if isinstance(names, str):
            names = [names] if names else []
        for n in names:
            if n not in sdata.get("swarms", {}):
                return json.dumps({"error": f"Swarm '{n}' not found. Available: {list(sdata.get('swarms', {}).keys())}"})
        sdata["active"] = names
        _write_swarms(sdata)
        try:
            import sys
            main = sys.modules.get("__main__")
            if main and hasattr(main, "_ACTIVE_SWARMS"):
                main._ACTIVE_SWARMS = names
        except Exception:
            pass
        if names:
            all_agents = set()
            for n in names:
                all_agents.update(sdata["swarms"][n].get("agents", []))
            return json.dumps({"status": "ok", "active_swarms": names, "agents_loaded": sorted(all_agents)})
        return json.dumps({"status": "ok", "active_swarms": [], "message": "All agents are now active."})

    def _set_mode(self, name, mode):
        if not name:
            return json.dumps({"error": "swarm_name is required"})
        if mode not in ("stack", "converged"):
            return json.dumps({"error": "mode must be 'stack' or 'converged'"})
        sdata = _read_swarms()
        swarm = sdata.get("swarms", {}).get(name)
        if not swarm:
            return json.dumps({"error": f"Swarm '{name}' not found"})
        swarm["mode"] = mode
        _write_swarms(sdata)
        return json.dumps({"status": "ok", "swarm": name, "mode": mode})

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
            for config in ["soul.md", ".swarms.json"]:
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

            sdata = _read_swarms()
            now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            twin_bundle = {
                "schema": "rapp-twin/1.0",
                "handle": "@digitaltwin",
                "cloud_id": "egg-" + hashlib.sha256(now.encode()).hexdigest()[:16],
                "origin": "brainstem-egg",
                "exported_at": now,
                "soul": soul_text,
                "swarm_configs": sdata.get("swarms", {}),
                "active_swarms": sdata.get("active", []),
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
