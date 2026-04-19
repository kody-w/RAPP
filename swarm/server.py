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

    # ── Deploy ──

    def deploy(self, bundle):
        """Persist a rapp-swarm/1.0 bundle to disk. Returns the manifest."""
        if bundle.get("schema") != "rapp-swarm/1.0":
            raise ValueError(f"unsupported bundle schema: {bundle.get('schema')}")

        # Use the bundle's swarm_guid if present and valid; otherwise mint one.
        sg = (bundle.get("swarm_guid") or "").strip().lower()
        if not (sg and GUID_RE.match(sg)):
            sg = str(uuid.uuid4())

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

        for path in sorted(ad.glob("*_agent.py")):
            if path.name == "basic_agent.py":
                continue
            try:
                # Module name is namespaced by swarm so two swarms with
                # same-named files don't collide in sys.modules.
                modname = f"swarm_{swarm_guid.replace('-', '_')}_{path.stem}"
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
                        except Exception as e:
                            print(f"  ✗ {path.name} → instantiate: {e}")
            except Exception as e:
                print(f"  ✗ {path.name} → import: {e}")

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
        old_env = os.environ.get("BRAINSTEM_MEMORY_PATH")
        os.environ["BRAINSTEM_MEMORY_PATH"] = str(mem_path)
        try:
            output = agent.perform(**(args or {}))
            return {"status": "ok", "output": output}
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
            return self._send_json(200, {
                "status": "ok",
                "swarm_guid": sg,
                "name": manifest.get("name"),
                "purpose": manifest.get("purpose"),
                "agent_count": len(agents),
                "agents": sorted(agents.keys()),
            })

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

        return self._send_json(404, {"status": "error", "message": "not found"})

    def do_DELETE(self):
        path = urlparse(self.path).path
        m = re.match(r"^/api/swarm/([0-9a-f-]+)/?$", path)
        if not m:
            return self._send_json(404, {"status": "error", "message": "not found"})
        sg = m.group(1)
        ok = self.store.remove(sg)
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
