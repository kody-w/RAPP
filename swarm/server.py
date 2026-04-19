#!/usr/bin/env python3
"""
RAPP Swarm Server — host many RAPP swarms behind one endpoint, routed by GUID.

A "swarm" is the bundle of agents you pushed from the brainstem's Deploy as
Swarm action. Each swarm has its own GUID, its own agents directory, and its
own per-user memory namespace. One endpoint can host hundreds of swarms; each
chat request picks a swarm by GUID, optionally a user by GUID, and gets back
isolated agent execution + memory.

Layout on disk (~/.rapp-swarm by default):

    swarms/
      <swarm_guid>/
        manifest.json                 ← name, purpose, soul, created_at, …
        agents/
          hacker_news_agent.py
          save_memory_agent.py
          …
        memory/
          <user_guid>/memory.json     ← per-user memory inside this swarm
          shared/memory.json          ← swarm-wide shared memory (anonymous)

Routing follows the community-RAPP pattern: a request without a user_guid is
treated as anonymous and uses the swarm's shared memory. The default sentinel
"c0p110t0-aaaa-bbbb-cccc-123456789abc" is the same intentional-invalid GUID
the OG uses to mark anonymous sessions in logs while routing to shared memory.

Endpoints:
    GET    /api/swarm/healthz                List all swarms with stats
    POST   /api/swarm/deploy                 Install a rapp-swarm/1.0 bundle
    GET    /api/swarm/{guid}/healthz         Info + agents for one swarm
    POST   /api/swarm/{guid}/agent           Run an agent in this swarm
    DELETE /api/swarm/{guid}                 Tear down a swarm

Stdlib only. No venv, no pip, no Azure Functions runtime needed locally.
The Tier 2 deploy story (Azure Functions, hippocampus engine) layers on top
of this same wire format — same /api/swarm/deploy contract, same routing.
"""

import argparse
import importlib.util
import json
import os
import re
import sys
import threading
import time
import traceback
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse


# ─── CONSTANTS ──────────────────────────────────────────────────────────

# Same sentinel the community RAPP brainstem uses: not a valid UUID
# (contains 'p' and 'l'), so it can never collide with a real user GUID
# but is instantly recognizable in logs as "anonymous session".
DEFAULT_USER_GUID = "c0p110t0-aaaa-bbbb-cccc-123456789abc"

GUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

ALLOWED_ORIGINS = (
    "https://kody-w.github.io",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
)


class SealedSwarmError(Exception):
    """Raised when a write-path operation targets a sealed swarm."""
    pass


def _now_iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _now_compact():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _b64_decode(s):
    import base64
    return base64.b64decode(s) if s else b""


# ─── D2D integration (lazy-imported so swarm server stays usable without it) ─

_t2t_manager = None

def get_t2t_manager(root):
    """Get the T2T (twin-to-twin) manager. T2T is the user-facing protocol name;
    the implementation is the daemon-to-daemon (D2D) layer underneath."""
    global _t2t_manager
    if _t2t_manager is None:
        try:
            from swarm.t2t import T2TManager
        except ImportError:
            import sys as _sys
            _sys.path.insert(0, str(Path(__file__).parent))
            from t2t import T2TManager
        _t2t_manager = T2TManager(root)
    return _t2t_manager


# ─── .env loader (stdlib — no python-dotenv dependency) ─────────────────

def load_dotenv(path=None):
    """Read a .env file into os.environ. Existing env vars win.
    Looks at $RAPP_DOTENV, then ./.env, then ../.env (repo root)."""
    candidates = []
    if path:
        candidates.append(Path(path))
    if os.environ.get("RAPP_DOTENV"):
        candidates.append(Path(os.environ["RAPP_DOTENV"]))
    here = Path(__file__).resolve().parent
    candidates += [
        Path.cwd() / ".env",
        here / ".env",
        here.parent / ".env",
    ]
    for p in candidates:
        if p and p.is_file():
            try:
                for line in p.read_text().splitlines():
                    s = line.strip()
                    if not s or s.startswith("#") or "=" not in s:
                        continue
                    k, v = s.split("=", 1)
                    k, v = k.strip(), v.strip()
                    if v and v[0] in ('"', "'") and v[-1] == v[0]:
                        v = v[1:-1]
                    os.environ.setdefault(k, v)
                return p
            except Exception:
                continue
    return None


# ─── LLM dispatch lazy loader (for /api/swarm/{guid}/chat) ─────────────

def get_llm_chat():
    """Lazy import the chat loop so the server is usable without it
    (e.g., in pure-T2T deployments)."""
    try:
        from swarm.chat import chat_with_swarm, diagnostics
    except ImportError:
        sys.path.insert(0, str(Path(__file__).parent))
        from chat import chat_with_swarm, diagnostics  # type: ignore
    return chat_with_swarm, diagnostics


_workspace = None
def get_workspace(root):
    """Lazy workspace (per-twin documents + inbox + outbox)."""
    global _workspace
    if _workspace is None:
        try:
            from swarm.workspace import Workspace
        except ImportError:
            sys.path.insert(0, str(Path(__file__).parent))
            from workspace import Workspace  # type: ignore
        _workspace = Workspace(root)
    return _workspace


# ─── SWARM STORE ────────────────────────────────────────────────────────

class SwarmStore:
    """Disk-backed registry of swarms. Thread-safe for the small ops we do."""

    def __init__(self, root: Path):
        self.root = root
        self.swarms_dir = root / "swarms"
        self.swarms_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._loaded_agents = {}   # swarm_guid -> {name: agent_instance}

    # ── Layout helpers ──

    def swarm_dir(self, swarm_guid: str) -> Path:
        return self.swarms_dir / swarm_guid

    def agents_dir(self, swarm_guid: str) -> Path:
        return self.swarm_dir(swarm_guid) / "agents"

    def memory_path(self, swarm_guid, user_guid):
        """Per-user memory file inside a swarm. None / sentinel → shared."""
        if not user_guid or user_guid == DEFAULT_USER_GUID or not GUID_RE.match(user_guid):
            return self.swarm_dir(swarm_guid) / "memory" / "shared" / "memory.json"
        return self.swarm_dir(swarm_guid) / "memory" / user_guid / "memory.json"

    def manifest_path(self, swarm_guid: str) -> Path:
        return self.swarm_dir(swarm_guid) / "manifest.json"

    # ── Listing / lookup ──

    def list_swarms(self):
        out = []
        for d in sorted(self.swarms_dir.iterdir()) if self.swarms_dir.exists() else []:
            if not d.is_dir():
                continue
            mp = d / "manifest.json"
            if not mp.exists():
                continue
            try:
                m = json.loads(mp.read_text())
            except Exception:
                continue
            out.append({
                "swarm_guid": d.name,
                "name": m.get("name", d.name),
                "purpose": m.get("purpose", ""),
                "agent_count": m.get("agent_count", 0),
                "created_at": m.get("created_at", ""),
                "created_by": m.get("created_by", ""),
            })
        return out

    def get_manifest(self, swarm_guid):
        mp = self.manifest_path(swarm_guid)
        if not mp.exists():
            return None
        try:
            return json.loads(mp.read_text())
        except Exception:
            return None

    # ── Sealing ──
    # Sealing transitions a swarm to immutable state: writes rejected, reads OK.
    # Sealed swarms can still be queried and snapshotted (final-archive use case).
    # The sealing PRIMITIVE is public and lives here; the operational PRODUCT
    # around it (endowment funding, ceremony, family notification) is downstream.

    def is_sealed(self, swarm_guid):
        m = self.get_manifest(swarm_guid)
        if not m:
            return False
        return m.get("sealing", {}).get("status") in ("sealed", "eternal")

    def seal_status(self, swarm_guid):
        m = self.get_manifest(swarm_guid)
        if not m:
            return {"sealed": False, "exists": False}
        s = m.get("sealing", {})
        return {
            "sealed": s.get("status") in ("sealed", "eternal"),
            "exists": True,
            "status": s.get("status", "active"),
            "sealed_at": s.get("sealed_at"),
            "sealed_by": s.get("sealed_by"),
            "trigger": s.get("trigger"),
        }

    def seal(self, swarm_guid, actor=None, trigger="voluntary"):
        with self._lock:
            m = self.get_manifest(swarm_guid)
            if not m:
                raise FileNotFoundError(f"swarm not found: {swarm_guid}")
            existing = m.get("sealing", {})
            if existing.get("status") in ("sealed", "eternal"):
                # Idempotent — already sealed
                return existing
            sealing = {
                "status": "sealed",
                "sealed_at": _now_iso(),
                "sealed_by": actor or "anonymous",
                "trigger": trigger,
            }
            m["sealing"] = sealing
            self.manifest_path(swarm_guid).write_text(json.dumps(m, indent=2))
            # Make all existing memory files read-only on POSIX so writes from
            # agent code fail loudly (not silently). Cross-platform graceful.
            self._chmod_memory_readonly(swarm_guid)
            return sealing

    def _chmod_memory_readonly(self, swarm_guid):
        mem_root = self.swarm_dir(swarm_guid) / "memory"
        if not mem_root.exists():
            return
        if os.name != "posix":
            return
        for p in mem_root.rglob("*"):
            try:
                if p.is_file():
                    os.chmod(p, 0o444)
                elif p.is_dir():
                    os.chmod(p, 0o555)
            except OSError:
                pass

    # ── Snapshots ──
    # Snapshots are temporally-versioned read-only copies of swarm state.
    # Created at any time on an active or sealed swarm. Each snapshot has its
    # own swarm_dir with frozen agents/, memory/, and a snapshot manifest.

    def snapshots_dir(self, swarm_guid):
        return self.swarm_dir(swarm_guid) / "snapshots"

    def create_snapshot(self, swarm_guid, label=None):
        sd = self.swarm_dir(swarm_guid)
        if not sd.exists():
            raise FileNotFoundError(f"swarm not found: {swarm_guid}")
        with self._lock:
            ts = _now_compact()
            safe_label = "".join(c if c.isalnum() or c in "-_" else "_" for c in (label or "snapshot"))[:64]
            snap_name = f"{ts}_{safe_label}"
            snap_root = self.snapshots_dir(swarm_guid) / snap_name
            snap_root.mkdir(parents=True, exist_ok=False)

            import shutil
            # Copy agents (skip __pycache__)
            src_agents = sd / "agents"
            if src_agents.exists():
                shutil.copytree(src_agents, snap_root / "agents",
                                ignore=shutil.ignore_patterns("__pycache__"))
            # Copy memory tree
            src_memory = sd / "memory"
            if src_memory.exists():
                shutil.copytree(src_memory, snap_root / "memory")
            # Copy manifest under a snapshot-specific name
            src_manifest = sd / "manifest.json"
            if src_manifest.exists():
                shutil.copy2(src_manifest, snap_root / "source_manifest.json")

            meta = {
                "snapshot_label": label or "snapshot",
                "snapshot_iso": _now_iso(),
                "snapshot_name": snap_name,
                "swarm_guid": swarm_guid,
            }
            (snap_root / "snapshot_metadata.json").write_text(json.dumps(meta, indent=2))

            # Mark snapshot files read-only on POSIX
            if os.name == "posix":
                for p in snap_root.rglob("*"):
                    try:
                        if p.is_file():
                            os.chmod(p, 0o444)
                        elif p.is_dir():
                            os.chmod(p, 0o555)
                    except OSError:
                        pass

            return meta

    def list_snapshots(self, swarm_guid):
        snap_dir = self.snapshots_dir(swarm_guid)
        if not snap_dir.exists():
            return []
        out = []
        for d in sorted(snap_dir.iterdir()):
            if not d.is_dir():
                continue
            meta_file = d / "snapshot_metadata.json"
            if meta_file.exists():
                try:
                    out.append(json.loads(meta_file.read_text()))
                except Exception:
                    continue
        return out

    def execute_against_snapshot(self, swarm_guid, snapshot_name, agent_name, args, user_guid):
        """Execute an agent against a frozen snapshot. Reads work, writes fail."""
        snap_root = self.snapshots_dir(swarm_guid) / snapshot_name
        if not snap_root.exists():
            return {"status": "error", "message": f"snapshot not found: {snapshot_name}"}

        # Use a separate cache key so snapshot vs live agents don't collide.
        cache_key = f"{swarm_guid}::snapshot::{snapshot_name}"
        if cache_key not in self._loaded_agents:
            agents = {}
            ad = snap_root / "agents"
            if ad.exists():
                # Reuse the same loading path as live agents — module names must
                # be unique per snapshot to avoid sys.modules collision.
                self._ensure_basic_agent_shim()
                for path in sorted(ad.glob("*_agent.py")):
                    if path.name == "basic_agent.py":
                        continue
                    try:
                        modname = f"snap_{swarm_guid.replace('-', '_')}_{snapshot_name}_{path.stem}"
                        spec = importlib.util.spec_from_file_location(modname, str(path))
                        mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(mod)
                        for attr in dir(mod):
                            cls = getattr(mod, attr)
                            if not isinstance(cls, type):
                                continue
                            if attr.endswith("Agent") and attr != "BasicAgent":
                                try:
                                    inst = cls()
                                    agents[inst.name] = inst
                                except Exception:
                                    pass
                    except Exception:
                        pass
            self._loaded_agents[cache_key] = agents

        agents = self._loaded_agents[cache_key]
        agent = agents.get(agent_name)
        if not agent:
            return {"status": "error", "message": f"unknown agent in snapshot: {agent_name}",
                    "available": sorted(agents.keys())}

        # Point memory at the snapshot's frozen memory tree (read-only on POSIX).
        # Agents that try to write will get PermissionError; we surface that as
        # a clean error so callers know snapshots are read-only.
        if user_guid and GUID_RE.match(user_guid) and user_guid != DEFAULT_USER_GUID:
            mem_path = snap_root / "memory" / user_guid / "memory.json"
        else:
            mem_path = snap_root / "memory" / "shared" / "memory.json"

        old_env = os.environ.get("BRAINSTEM_MEMORY_PATH")
        os.environ["BRAINSTEM_MEMORY_PATH"] = str(mem_path)
        try:
            output = agent.perform(**(args or {}))
            # Heuristic: if the agent raised PermissionError, the output captures
            # that. We also check the output for telltale write-failure signs.
            return {"status": "ok", "output": output, "snapshot": snapshot_name, "read_only": True}
        except PermissionError as e:
            return {"status": "error", "message": f"snapshot is read-only: {e}",
                    "snapshot": snapshot_name}
        except Exception as e:
            traceback.print_exc()
            return {"status": "error", "message": str(e), "snapshot": snapshot_name}
        finally:
            if old_env is None:
                os.environ.pop("BRAINSTEM_MEMORY_PATH", None)
            else:
                os.environ["BRAINSTEM_MEMORY_PATH"] = old_env

    def _ensure_basic_agent_shim(self):
        """Make sure the agents.basic_agent shim is registered in sys.modules.
        Safe to call multiple times; idempotent."""
        if "agents" not in sys.modules:
            pkg = type(sys)("agents")
            pkg.__path__ = []
            sys.modules["agents"] = pkg
        if "agents.basic_agent" in sys.modules:
            return
        here = Path(__file__).parent.resolve()
        vendored = here / "_basic_agent_shim.py"
        if not vendored.exists():
            self._write_basic_agent_shim(vendored)
        spec = importlib.util.spec_from_file_location("agents.basic_agent", str(vendored))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules["agents.basic_agent"] = mod

    # ── Deploy ──

    def deploy(self, bundle):
        """Persist a rapp-swarm/1.0 bundle to disk. Returns the manifest."""
        if bundle.get("schema") != "rapp-swarm/1.0":
            raise ValueError(f"unsupported bundle schema: {bundle.get('schema')}")

        # Use the bundle's swarm_guid if present and valid; otherwise mint one.
        sg = (bundle.get("swarm_guid") or "").strip().lower()
        if not (sg and GUID_RE.match(sg)):
            sg = str(uuid.uuid4())

        # Sealed swarms are immutable — reject any redeploy attempt that
        # targets a sealed swarm_guid.
        if self.is_sealed(sg):
            raise SealedSwarmError(f"swarm {sg} is sealed; redeploy rejected")

        with self._lock:
            sd = self.swarm_dir(sg)
            ad = self.agents_dir(sg)
            sd.mkdir(parents=True, exist_ok=True)
            ad.mkdir(parents=True, exist_ok=True)
            (sd / "memory" / "shared").mkdir(parents=True, exist_ok=True)

            # Write each agent's source. Filenames are sandboxed to a basename
            # to prevent path traversal — bundles can't escape their swarm dir.
            written_agents = []
            for a in bundle.get("agents", []):
                fname = os.path.basename(a.get("filename", "") or "")
                if not fname.endswith("_agent.py"):
                    continue
                src = a.get("source") or ""
                if not src.strip():
                    continue
                (ad / fname).write_text(src)
                written_agents.append(fname)

            # Write the manifest (drop the heavy source bodies — keep metadata).
            manifest = {
                "schema": "rapp-swarm/1.0",
                "swarm_guid": sg,
                "name": bundle.get("name", "untitled-swarm"),
                "purpose": bundle.get("purpose", ""),
                "soul": bundle.get("soul", ""),
                "created_at": bundle.get("created_at", ""),
                "created_by": bundle.get("created_by", "anonymous"),
                "agent_count": len(written_agents),
                "agents": [
                    {k: v for k, v in a.items() if k != "source"}
                    for a in bundle.get("agents", [])
                ],
            }
            self.manifest_path(sg).write_text(json.dumps(manifest, indent=2))

            # Invalidate any cached agent instances so the next call re-imports.
            self._loaded_agents.pop(sg, None)

            return manifest

    def remove(self, swarm_guid):
        if self.is_sealed(swarm_guid):
            raise SealedSwarmError(f"swarm {swarm_guid} is sealed; deletion rejected")
        with self._lock:
            sd = self.swarm_dir(swarm_guid)
            if not sd.exists():
                return False
            # Recursively delete the swarm dir.
            for root_path, dirs, files in os.walk(sd, topdown=False):
                for f in files:
                    os.remove(os.path.join(root_path, f))
                for d in dirs:
                    os.rmdir(os.path.join(root_path, d))
            os.rmdir(sd)
            self._loaded_agents.pop(swarm_guid, None)
            return True

    # ── Agent loading & execution ──

    def load_agents(self, swarm_guid):
        """Import every agent file under this swarm's agents/ dir. Cached."""
        if swarm_guid in self._loaded_agents:
            return self._loaded_agents[swarm_guid]

        agents = {}
        ad = self.agents_dir(swarm_guid)
        if not ad.exists():
            return agents

        # Allow agents to do `from agents.basic_agent import BasicAgent`.
        # We provide a synthetic `agents` package pointing at our shared
        # stdlib basic_agent (vendored alongside the server).
        here = Path(__file__).parent.resolve()
        vendored_basic = here / "_basic_agent_shim.py"
        if not vendored_basic.exists():
            self._write_basic_agent_shim(vendored_basic)

        # Inject `agents` package + `agents.basic_agent` module into sys.modules
        # so per-swarm files can import normally.
        if "agents" not in sys.modules:
            pkg = type(sys)("agents")
            pkg.__path__ = []  # marks it as a namespace package
            sys.modules["agents"] = pkg
        if "agents.basic_agent" not in sys.modules:
            spec = importlib.util.spec_from_file_location(
                "agents.basic_agent", str(vendored_basic)
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            sys.modules["agents.basic_agent"] = mod

        # Two-pass load:
        #   Pass 1 — import every module and register it under both
        #            `swarm_<guid>_<stem>` (per-swarm unique) AND
        #            `agents.<stem>`     (so composite agents can do
        #                                  `from agents.editor_cutweak_agent
        #                                   import EditorCutweakAgent`)
        #   Pass 2 — instantiate the *Agent classes. Defers instantiation
        #            so a composite's dependencies are all in sys.modules
        #            before its class body executes. Some composites import
        #            specialists at class-definition time; passing twice
        #            avoids glob-order accidents.
        loaded_mods = []
        for path in sorted(ad.glob("*_agent.py")):
            if path.name == "basic_agent.py":
                continue
            try:
                modname = f"swarm_{swarm_guid.replace('-', '_')}_{path.stem}"
                spec = importlib.util.spec_from_file_location(modname, str(path))
                mod = importlib.util.module_from_spec(spec)
                # Pre-register both names BEFORE exec so a composite that
                # imports a sibling that hasn't been exec'd yet still resolves
                # (the second pass below re-execs anything that failed)
                sys.modules[modname] = mod
                sys.modules[f"agents.{path.stem}"] = mod
                spec.loader.exec_module(mod)
                loaded_mods.append((path, mod))
            except Exception as e:
                # Defer the error — composite's dependency may not be loaded yet.
                # We retry in pass 2 below.
                loaded_mods.append((path, None))
                print(f"  ⏳ {path.name} → import deferred ({e})")

        # Pass 2: re-execute any that deferred (their deps should now exist)
        for i, (path, mod) in enumerate(loaded_mods):
            if mod is not None: continue
            try:
                modname = f"swarm_{swarm_guid.replace('-', '_')}_{path.stem}"
                spec = importlib.util.spec_from_file_location(modname, str(path))
                mod = importlib.util.module_from_spec(spec)
                sys.modules[modname] = mod
                sys.modules[f"agents.{path.stem}"] = mod
                spec.loader.exec_module(mod)
                loaded_mods[i] = (path, mod)
            except Exception as e:
                print(f"  ✗ {path.name} → import: {e}")

        # Pass 3: instantiate every *Agent class
        for path, mod in loaded_mods:
            if mod is None: continue
            for attr in dir(mod):
                cls = getattr(mod, attr)
                if not isinstance(cls, type):
                    continue
                if attr.endswith("Agent") and attr != "BasicAgent":
                    try:
                        inst = cls()
                        agents[inst.name] = inst
                    except Exception as e:
                        print(f"  ✗ {path.name} → instantiate {attr}: {e}")

        self._loaded_agents[swarm_guid] = agents
        return agents

    @staticmethod
    def _write_basic_agent_shim(p):
        """Tiny BasicAgent so swarm agent files can `from agents.basic_agent import BasicAgent`."""
        p.write_text(
            "class BasicAgent:\n"
            "    def __init__(self, name=None, metadata=None):\n"
            "        if name is not None: self.name = name\n"
            "        elif not hasattr(self, 'name'): self.name = 'BasicAgent'\n"
            "        if metadata is not None: self.metadata = metadata\n"
            "        elif not hasattr(self, 'metadata'):\n"
            "            self.metadata = {'name': self.name, 'description': '', 'parameters': {'type': 'object', 'properties': {}}}\n"
            "    def perform(self, **kwargs):\n"
            "        return 'Not implemented.'\n"
            "    def system_context(self):\n"
            "        return None\n"
            "    def to_tool(self):\n"
            "        return {'type': 'function', 'function': {\n"
            "            'name': self.name,\n"
            "            'description': self.metadata.get('description', ''),\n"
            "            'parameters': self.metadata.get('parameters', {'type': 'object', 'properties': {}})}}\n"
        )

    # ── Memory routing ──
    # Each agent file has its own _read_memory/_write_memory shim that ends up
    # at ~/.brainstem/memory.json by default. To route per-swarm-per-user, we
    # patch the env var BRAINSTEM_MEMORY_PATH around each call. Agents that
    # use the standard shim respect it; legacy agents that ignore it will
    # continue using their default path (which is a graceful degradation,
    # not a bug — they just won't get isolation).

    def execute(self, swarm_guid, agent_name, args, user_guid):
        agents = self.load_agents(swarm_guid)
        agent = agents.get(agent_name)
        if not agent:
            return {"status": "error", "message": f"unknown agent: {agent_name}",
                    "available": sorted(agents.keys())}

        # Set the memory path for this (swarm, user) tuple. Agent files that
        # check os.environ['BRAINSTEM_MEMORY_PATH'] route to our isolated file;
        # ones that don't fall back to the default ~/.brainstem/memory.json.
        mem_path = self.memory_path(swarm_guid, user_guid)
        mem_path.parent.mkdir(parents=True, exist_ok=True)

        # If sealed, force the memory file to read-only so any agent that tries
        # to write fails with PermissionError. Reads still work — that's the
        # whole point of sealing (preserved but queryable).
        sealed = self.is_sealed(swarm_guid)
        if sealed and os.name == "posix" and mem_path.exists():
            try:
                os.chmod(mem_path, 0o444)
            except OSError:
                pass

        old_env = os.environ.get("BRAINSTEM_MEMORY_PATH")
        os.environ["BRAINSTEM_MEMORY_PATH"] = str(mem_path)
        try:
            output = agent.perform(**(args or {}))
            # Heuristic post-check: if sealed, see if the agent's output
            # claims success despite the swarm being sealed (most write agents
            # fail loudly, but some catch and return their own envelope).
            if sealed and isinstance(output, str):
                # If a write-style agent returned a "success" envelope, override.
                # Detect by looking for 'saved' / 'success' tokens. Conservative.
                low = output.lower()
                if '"status": "success"' in low and ("saved" in low or "wrote" in low or "stored" in low):
                    return {"status": "ok", "output": json.dumps({
                        "status": "error",
                        "message": "swarm is sealed; writes are rejected",
                        "sealed": True,
                    })}
            return {"status": "ok", "output": output}
        except PermissionError as e:
            # Most common path when sealed: agent's _write_memory hit chmod 0444
            return {"status": "ok", "output": json.dumps({
                "status": "error",
                "message": f"swarm is sealed; writes rejected ({e})",
                "sealed": True,
            })}
        except Exception as e:
            traceback.print_exc()
            return {"status": "error", "message": str(e),
                    "trace": traceback.format_exc(limit=5)}
        finally:
            if old_env is None:
                os.environ.pop("BRAINSTEM_MEMORY_PATH", None)
            else:
                os.environ["BRAINSTEM_MEMORY_PATH"] = old_env


# ─── HTTP HANDLER ───────────────────────────────────────────────────────

class SwarmHandler(BaseHTTPRequestHandler):
    store = None  # SwarmStore, set by main()

    # ── CORS / response helpers ──

    def _cors_headers(self):
        origin = self.headers.get("Origin", "")
        if (
            origin in ALLOWED_ORIGINS
            or origin.startswith("http://localhost")
            or origin.startswith("http://127.0.0.1")
        ):
            self.send_header("Access-Control-Allow-Origin", origin)
        else:
            self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        # Required for Chrome to allow https://kody-w.github.io → http://localhost.
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Access-Control-Max-Age", "600")

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        n = int(self.headers.get("Content-Length", 0))
        if n <= 0:
            return {}
        return json.loads(self.rfile.read(n).decode("utf-8"))

    # ── Routing ──

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        # /api/swarm/healthz — top-level: list all swarms
        if path in ("/api/swarm/healthz", "/healthz"):
            return self._send_json(200, {
                "status": "ok",
                "schema": "rapp-swarm/1.0",
                "version": "1.0.0",
                "host": self.headers.get("Host", "localhost"),
                "swarm_count": len(self.store.list_swarms()),
                "swarms": self.store.list_swarms(),
            })

        # /api/swarm/list — convenience alias
        if path == "/api/swarm/list":
            return self._send_json(200, {"swarms": self.store.list_swarms()})

        # /api/swarm/{guid}/healthz — info about one swarm
        m = re.match(r"^/api/swarm/([0-9a-f-]+)/healthz/?$", path)
        if m:
            sg = m.group(1)
            manifest = self.store.get_manifest(sg)
            if not manifest:
                return self._send_json(404, {"status": "error", "message": "swarm not found"})
            agents = self.store.load_agents(sg)
            seal = self.store.seal_status(sg)
            return self._send_json(200, {
                "status": "ok",
                "swarm_guid": sg,
                "name": manifest.get("name"),
                "purpose": manifest.get("purpose"),
                "agent_count": len(agents),
                "agents": sorted(agents.keys()),
                "sealed": seal["sealed"],
                "sealing": {
                    "status": seal.get("status"),
                    "sealed_at": seal.get("sealed_at"),
                    "sealed_by": seal.get("sealed_by"),
                    "trigger": seal.get("trigger"),
                },
            })

        # /api/swarm/{guid}/seal — get sealing status
        m = re.match(r"^/api/swarm/([0-9a-f-]+)/seal/?$", path)
        if m:
            sg = m.group(1)
            seal = self.store.seal_status(sg)
            if not seal["exists"]:
                return self._send_json(404, {"status": "error", "message": "swarm not found"})
            return self._send_json(200, seal)

        # /api/swarm/{guid}/snapshots — list snapshots for a swarm
        m = re.match(r"^/api/swarm/([0-9a-f-]+)/snapshots/?$", path)
        if m:
            sg = m.group(1)
            if self.store.get_manifest(sg) is None:
                return self._send_json(404, {"status": "error", "message": "swarm not found"})
            return self._send_json(200, {
                "swarm_guid": sg,
                "snapshots": self.store.list_snapshots(sg),
            })

        # /api/workspace — twin metadata + counts
        if path == "/api/workspace":
            return self._send_json(200, get_workspace(self.store.root).info())

        # /api/workspace/documents — list mine + inbox + outbox
        if path == "/api/workspace/documents":
            return self._send_json(200, get_workspace(self.store.root).list_documents())

        # /api/workspace/documents/<name>?location=documents|inbox|outbox
        m = re.match(r"^/api/workspace/documents/([^/]+)/?$", path)
        if m:
            from urllib.parse import parse_qs
            qs = parse_qs(urlparse(self.path).query)
            location = (qs.get("location") or ["documents"])[0]
            doc = get_workspace(self.store.root).read_document(m.group(1), location)
            if not doc:
                return self._send_json(404, {"status": "error", "message": "document not found"})
            return self._send_json(200, doc)

        # /api/llm/status — what LLM provider is wired in (diagnostic)
        if path == "/api/llm/status":
            try:
                _, diagnostics = get_llm_chat()
                return self._send_json(200, diagnostics())
            except Exception as e:
                return self._send_json(500, {"status": "error", "message": str(e)})

        # /api/t2t/identity — this twin's public identity (cloud_id, handle, capabilities)
        if path == "/api/t2t/identity":
            mgr = get_t2t_manager(self.store.root)
            return self._send_json(200, mgr.get_identity_public())

        # /api/t2t/peers — list whitelisted peer twins
        if path == "/api/t2t/peers":
            mgr = get_t2t_manager(self.store.root)
            return self._send_json(200, {"peers": mgr.list_peers()})

        return self._send_json(404, {"status": "error", "message": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path

        # /api/swarm/deploy — install a bundle
        if path == "/api/swarm/deploy":
            try:
                bundle = self._read_json()
            except Exception as e:
                return self._send_json(400, {"status": "error", "message": f"bad json: {e}"})
            try:
                manifest = self.store.deploy(bundle)
            except SealedSwarmError as e:
                return self._send_json(423, {"status": "error", "message": str(e), "sealed": True})
            except ValueError as e:
                return self._send_json(400, {"status": "error", "message": str(e)})
            except Exception as e:
                traceback.print_exc()
                return self._send_json(500, {"status": "error", "message": str(e)})

            host = self.headers.get("Host", "localhost")
            scheme = "https" if self.headers.get("X-Forwarded-Proto") == "https" else "http"
            base = f"{scheme}://{host}"
            return self._send_json(200, {
                "status": "ok",
                "swarm_guid": manifest["swarm_guid"],
                "name": manifest["name"],
                "swarm_url": f"{base}/api/swarm/{manifest['swarm_guid']}/agent",
                "info_url":  f"{base}/api/swarm/{manifest['swarm_guid']}/healthz",
                "agent_count": manifest["agent_count"],
            })

        # /api/swarm/{guid}/agent — execute an agent
        m = re.match(r"^/api/swarm/([0-9a-f-]+)/agent/?$", path)
        if m:
            sg = m.group(1)
            try:
                body = self._read_json()
            except Exception as e:
                return self._send_json(400, {"status": "error", "message": f"bad json: {e}"})
            name = body.get("name")
            args = body.get("args") or {}
            user_guid = body.get("user_guid")
            if not name:
                return self._send_json(400, {"status": "error", "message": "missing 'name'"})
            result = self.store.execute(sg, name, args, user_guid)
            status = 200 if result.get("status") == "ok" else (
                404 if "unknown agent" in result.get("message", "") else 500
            )
            return self._send_json(status, result)

        # /api/swarm/{guid}/chat — LLM-driven chat against this swarm's
        # agents (the same wire shape the OG community RAPP brainstem uses).
        m = re.match(r"^/api/swarm/([0-9a-f-]+)/chat/?$", path)
        if m:
            sg = m.group(1)
            try:
                body = self._read_json()
            except Exception as e:
                return self._send_json(400, {"status": "error", "message": f"bad json: {e}"})
            user_input = body.get("user_input") or body.get("input") or ""
            if not user_input:
                return self._send_json(400, {"status": "error", "message": "missing 'user_input'"})
            try:
                chat_with_swarm, _ = get_llm_chat()
                result = chat_with_swarm(
                    self.store, sg,
                    user_input=user_input,
                    conversation_history=body.get("conversation_history") or [],
                    user_guid=body.get("user_guid"),
                    extra_system=body.get("extra_system", ""),
                )
                status = 200 if not result.get("error") else 500
                return self._send_json(status, result)
            except Exception as e:
                traceback.print_exc()
                return self._send_json(500, {"status": "error", "message": str(e)})

        # /api/swarm/{guid}/seal — seal a swarm (immutable, queryable)
        m = re.match(r"^/api/swarm/([0-9a-f-]+)/seal/?$", path)
        if m:
            sg = m.group(1)
            try:
                body = self._read_json()
            except Exception:
                body = {}
            actor = body.get("actor") or "anonymous"
            trigger = body.get("trigger") or "voluntary"
            try:
                sealing = self.store.seal(sg, actor=actor, trigger=trigger)
                return self._send_json(200, {"status": "ok", "swarm_guid": sg, "sealing": sealing})
            except FileNotFoundError as e:
                return self._send_json(404, {"status": "error", "message": str(e)})
            except Exception as e:
                traceback.print_exc()
                return self._send_json(500, {"status": "error", "message": str(e)})

        # /api/swarm/{guid}/snapshot — create a snapshot
        m = re.match(r"^/api/swarm/([0-9a-f-]+)/snapshot/?$", path)
        if m:
            sg = m.group(1)
            try:
                body = self._read_json()
            except Exception:
                body = {}
            label = body.get("label")
            try:
                meta = self.store.create_snapshot(sg, label=label)
                return self._send_json(200, {"status": "ok", **meta})
            except FileNotFoundError as e:
                return self._send_json(404, {"status": "error", "message": str(e)})
            except Exception as e:
                traceback.print_exc()
                return self._send_json(500, {"status": "error", "message": str(e)})

        # /api/workspace/documents/<name> — save (write/overwrite)
        m = re.match(r"^/api/workspace/documents/([^/]+)/?$", path)
        if m:
            try:
                body = self._read_json()
            except Exception as e:
                return self._send_json(400, {"status": "error", "message": f"bad json: {e}"})
            content_b64 = body.get("content_b64") or ""
            location = body.get("location", "documents")
            try:
                import base64 as _b64
                content = _b64.b64decode(content_b64) if content_b64 else (
                    (body.get("content") or "").encode("utf-8")
                )
                meta = get_workspace(self.store.root).write_document(
                    m.group(1), content, location
                )
                return self._send_json(200, {"status": "ok", **meta})
            except ValueError as e:
                return self._send_json(400, {"status": "error", "message": str(e)})

        # /api/t2t/send-document — sign + push doc to a peer twin
        if path == "/api/t2t/send-document":
            try:
                body = self._read_json()
            except Exception as e:
                return self._send_json(400, {"status": "error", "message": f"bad json: {e}"})
            to_cloud_id = body.get("to", "")
            doc_name = body.get("document_name", "")
            location = body.get("from_location", "documents")
            mgr = get_t2t_manager(self.store.root)
            ws = get_workspace(self.store.root)
            peer = mgr.peers.get_peer(to_cloud_id)
            if not peer:
                return self._send_json(403, {"status": "error", "message": "peer not whitelisted"})
            if not peer.get("url"):
                return self._send_json(400, {"status": "error", "message": "peer has no URL on file"})
            doc = ws.read_document(doc_name, location)
            if not doc:
                return self._send_json(404, {"status": "error", "message": "document not found"})

            # Sign the (from, doc_name, content_b64) tuple with MY secret
            try:
                from swarm.t2t import sign as _sign
            except ImportError:
                from t2t import sign as _sign  # type: ignore
            my_id = mgr.identity.get_or_create()["cloud_id"]
            my_secret = mgr.identity.get_secret()
            payload_obj = {
                "from": my_id,
                "name": doc["name"],
                "bytes": doc["bytes"],
                "content_b64": doc["content_b64"],
                "sent_at": _now_iso(),
            }
            payload_str = json.dumps(payload_obj, sort_keys=True, separators=(",", ":"))
            sig = _sign(payload_str, my_secret)

            # Send to peer
            import urllib.request as _ur
            import urllib.error as _ue
            req = _ur.Request(
                peer["url"].rstrip("/") + "/api/t2t/receive-document",
                data=json.dumps({**payload_obj, "sig": sig}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with _ur.urlopen(req, timeout=15) as resp:
                    peer_resp = json.loads(resp.read().decode("utf-8"))
            except _ue.HTTPError as e:
                return self._send_json(502, {"status": "error",
                                              "message": f"peer HTTP {e.code}",
                                              "details": e.read().decode("utf-8")[:300]})
            except _ue.URLError as e:
                return self._send_json(502, {"status": "error", "message": f"peer unreachable: {e}"})

            # Mirror to MY outbox for audit
            try:
                ws.write_document(doc["name"], _b64_decode(doc["content_b64"]), "outbox")
            except Exception:
                pass
            return self._send_json(200, {"status": "ok", "peer_response": peer_resp,
                                          "name": doc["name"]})

        # /api/t2t/receive-document — accept doc from a known peer
        if path == "/api/t2t/receive-document":
            try:
                body = self._read_json()
            except Exception as e:
                return self._send_json(400, {"status": "error", "message": f"bad json: {e}"})
            from_cloud_id = body.get("from", "")
            sig = body.get("sig", "")
            mgr = get_t2t_manager(self.store.root)
            peer = mgr.peers.get_peer(from_cloud_id)
            if not peer:
                return self._send_json(403, {"status": "error", "message": "unknown sender"})
            try:
                from swarm.t2t import verify as _verify
            except ImportError:
                from t2t import verify as _verify  # type: ignore
            payload_obj = {k: body[k] for k in ("from", "name", "bytes", "content_b64", "sent_at") if k in body}
            payload_str = json.dumps(payload_obj, sort_keys=True, separators=(",", ":"))
            if not _verify(payload_str, sig, peer["secret"]):
                return self._send_json(403, {"status": "error", "message": "signature failed"})
            # Save to inbox, namespaced by sender's cloud_id
            ws = get_workspace(self.store.root)
            try:
                content = _b64_decode(body.get("content_b64", ""))
                fname = f"{from_cloud_id[:8]}_{body.get('name','document')}"
                meta = ws.write_document(fname, content, "inbox")
                return self._send_json(200, {"status": "ok", "received": True,
                                              "saved_as": meta["name"]})
            except ValueError as e:
                return self._send_json(400, {"status": "error", "message": str(e)})

        # /api/t2t/peers — whitelist a peer twin
        if path == "/api/t2t/peers":
            try:
                body = self._read_json()
            except Exception as e:
                return self._send_json(400, {"status": "error", "message": f"bad json: {e}"})
            cloud_id = body.get("cloud_id")
            secret = body.get("secret")
            if not cloud_id or not secret:
                return self._send_json(400, {"status": "error", "message": "cloud_id and secret required"})
            mgr = get_t2t_manager(self.store.root)
            peer = mgr.add_peer(
                cloud_id=cloud_id, secret=secret,
                handle=body.get("handle", ""), url=body.get("url", ""),
                allowed_caps=body.get("allowed_caps") or ["*"],
            )
            peer = {k: v for k, v in peer.items() if k != "secret"}
            return self._send_json(200, {"status": "ok", "peer": peer})

        # /api/t2t/handshake — accept an incoming handshake
        if path == "/api/t2t/handshake":
            try:
                body = self._read_json()
            except Exception as e:
                return self._send_json(400, {"status": "error", "message": f"bad json: {e}"})
            mgr = get_t2t_manager(self.store.root)
            result = mgr.handshake(
                from_cloud_id=body.get("from", ""),
                conv_id=body.get("conv_id", ""),
                intro=body.get("intro") or {},
                sig=body.get("sig", ""),
            )
            status = 200 if result.get("accepted") else 403
            return self._send_json(status, result)

        # /api/t2t/message — receive an inbound message
        if path == "/api/t2t/message":
            try:
                body = self._read_json()
            except Exception as e:
                return self._send_json(400, {"status": "error", "message": f"bad json: {e}"})
            mgr = get_t2t_manager(self.store.root)
            result = mgr.receive_message(
                from_cloud_id=body.get("from", ""),
                conv_id=body.get("conv_id", ""),
                seq=body.get("seq", 0),
                body=body.get("body") or {},
                sig=body.get("sig", ""),
            )
            status = 200 if result.get("received") else 403
            return self._send_json(status, result)

        # /api/t2t/invoke — peer twin invokes one of MY capabilities (a swarm/agent call)
        if path == "/api/t2t/invoke":
            try:
                body = self._read_json()
            except Exception as e:
                return self._send_json(400, {"status": "error", "message": f"bad json: {e}"})
            mgr = get_t2t_manager(self.store.root)
            from_cloud_id = body.get("from", "")
            sig = body.get("sig", "")
            invocation = body.get("invocation") or {}
            # Verify sig against the peer's secret
            payload = json.dumps({"from": from_cloud_id, "invocation": invocation},
                                 sort_keys=True, separators=(",", ":"))
            peer = mgr.peers.get_peer(from_cloud_id)
            if not peer:
                return self._send_json(403, {"status": "error", "message": "peer not whitelisted"})
            try:
                from swarm.t2t import verify as _verify_t2t  # type: ignore
            except ImportError:
                from t2t import verify as _verify_t2t  # type: ignore
            if not _verify_t2t(payload, sig, peer["secret"]):
                return self._send_json(403, {"status": "error", "message": "signature failed"})
            # Check capability allowlist
            target_swarm = invocation.get("swarm_guid", "")
            agent_name = invocation.get("agent", "")
            if not mgr.can_peer_invoke(from_cloud_id, agent_name):
                return self._send_json(403, {"status": "error",
                                              "message": f"peer not authorized for capability '{agent_name}'"})
            # Execute the agent — same path as /api/swarm/{guid}/agent but invoked via T2T
            result = self.store.execute(target_swarm, agent_name,
                                         invocation.get("args") or {},
                                         user_guid=None)  # T2T calls are anonymous to the target's memory
            return self._send_json(200, {"status": "ok", "result": result, "invoked_by": from_cloud_id})

        # /api/swarm/{guid}/snapshots/{snap_name}/agent — query an agent against a snapshot
        m = re.match(r"^/api/swarm/([0-9a-f-]+)/snapshots/([0-9A-Za-z_\-]+)/agent/?$", path)
        if m:
            sg = m.group(1)
            snap_name = m.group(2)
            try:
                body = self._read_json()
            except Exception as e:
                return self._send_json(400, {"status": "error", "message": f"bad json: {e}"})
            name = body.get("name")
            args = body.get("args") or {}
            user_guid = body.get("user_guid")
            if not name:
                return self._send_json(400, {"status": "error", "message": "missing 'name'"})
            result = self.store.execute_against_snapshot(sg, snap_name, name, args, user_guid)
            status = 200 if result.get("status") == "ok" else (
                404 if "not found" in result.get("message", "") else 500
            )
            return self._send_json(status, result)

        return self._send_json(404, {"status": "error", "message": "not found"})

    def do_DELETE(self):
        path = urlparse(self.path).path
        # /api/workspace/documents/<name>?location=…
        m = re.match(r"^/api/workspace/documents/([^/]+)/?$", path)
        if m:
            from urllib.parse import parse_qs
            qs = parse_qs(urlparse(self.path).query)
            location = (qs.get("location") or ["documents"])[0]
            ok = get_workspace(self.store.root).delete_document(m.group(1), location)
            return self._send_json(200 if ok else 404,
                                    {"status": "ok" if ok else "error",
                                     "removed": m.group(1) if ok else None,
                                     "message": None if ok else "document not found"})

        m = re.match(r"^/api/swarm/([0-9a-f-]+)/?$", path)
        if not m:
            return self._send_json(404, {"status": "error", "message": "not found"})
        sg = m.group(1)
        try:
            ok = self.store.remove(sg)
        except SealedSwarmError as e:
            return self._send_json(423, {"status": "error", "message": str(e), "sealed": True})
        if not ok:
            return self._send_json(404, {"status": "error", "message": "swarm not found"})
        return self._send_json(200, {"status": "ok", "removed": sg})

    def log_message(self, fmt, *args):
        sys.stderr.write(f"  → {fmt % args}\n")


# ─── ENTRY POINT ────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        description="RAPP Swarm Server — host many swarms behind one endpoint, routed by GUID."
    )
    p.add_argument("--port", type=int, default=7080)
    p.add_argument("--host", default="127.0.0.1",
                   help="Bind address. Use 0.0.0.0 to expose on LAN.")
    p.add_argument("--root", default="~/.rapp-swarm",
                   help="Where to persist swarms. Default: ~/.rapp-swarm")
    args = p.parse_args()

    # Load root .env (Azure OpenAI keys, etc) — does NOT overwrite existing env.
    loaded = load_dotenv()
    if loaded:
        print(f"  Loaded env from {loaded}")

    root = Path(os.path.expanduser(args.root)).resolve()
    root.mkdir(parents=True, exist_ok=True)

    SwarmHandler.store = SwarmStore(root)
    existing = SwarmHandler.store.list_swarms()

    print(f"\n  RAPP Swarm Server")
    print(f"  {'─' * 36}")
    print(f"  Root: {root}")
    print(f"  Swarms loaded: {len(existing)}")
    for s in existing:
        print(f"    • {s['name']}  ({s['agent_count']} agents)  {s['swarm_guid']}")

    url = f"http://{args.host}:{args.port}"
    print(f"\n  Listening on  {url}")
    print(f"  Health check  {url}/api/swarm/healthz")
    print(f"\n  Deploy a swarm from the brainstem:")
    print(f"    Settings → 🐝 Deploy as Swarm → Push to endpoint: {url}\n")
    print(f"  Ctrl-C to stop.\n")

    server = HTTPServer((args.host, args.port), SwarmHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Shutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
