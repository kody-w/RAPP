#!/usr/bin/env python3
"""
RAPP Tether Server — exposes local *_agent.py files to the virtual brainstem
running at https://kody-w.github.io/RAPP/brainstem/.

Why: the virtual brainstem runs in the browser via Pyodide. Pyodide can't
touch the local filesystem, spawn subprocesses, hit the LAN, or talk to
hardware. The tether server bridges that gap — when "Tether" is enabled in
the virtual brainstem's Settings, every agent call routes through this
process instead of Pyodide, so you get real OS access for free.

Usage:
    python tether/server.py                          # localhost:8765, ./agents
    python tether/server.py --port 9000
    python tether/server.py --agents /path/to/dir
    python tether/server.py --host 0.0.0.0           # expose on LAN

Stdlib only — no pip install required.
"""

import argparse
import importlib.util
import json
import sys
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


# Browsers send Origin on every CORS request; we whitelist the published
# brainstem and any localhost dev server. Other origins fall back to "*"
# which is fine here because the server only listens on localhost by default.
ALLOWED_ORIGINS = (
    "https://kody-w.github.io",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
)


def load_agents(agents_dir: Path):
    """Import every *_agent.py in agents_dir and instantiate the *Agent class.
    Returns {agent.name: instance}. Skips basic_agent.py (the base class)."""
    agents = {}
    # Make `from agents.basic_agent import BasicAgent` resolvable
    sys.path.insert(0, str(agents_dir.parent.absolute()))
    for path in sorted(agents_dir.glob("*_agent.py")):
        if path.name == "basic_agent.py":
            continue
        try:
            spec = importlib.util.spec_from_file_location(path.stem, path)
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
                        print(f"  ✓ {inst.name:24s} {path.name}")
                    except Exception as e:
                        print(f"  ✗ {path.name} → instantiate failed: {e}")
        except Exception as e:
            print(f"  ✗ {path.name} → import failed: {e}")
    return agents


class TetherHandler(BaseHTTPRequestHandler):
    # Class-level so the same handler instance can use them across requests
    agents = {}

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
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        # Chrome's Private Network Access preflight — required to call
        # http://localhost from an https:// origin in newer Chromium.
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

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path in ("/tether/healthz", "/healthz"):
            return self._send_json(200, {
                "status": "ok",
                "schema": "rapp-tether/1.0",
                "version": "1.0.0",
                "host": self.headers.get("Host", "localhost"),
                "agents": sorted(self.agents.keys()),
                "count": len(self.agents),
            })
        return self._send_json(404, {"status": "error", "message": "not found"})

    def do_POST(self):
        if self.path != "/tether/agent":
            return self._send_json(404, {"status": "error", "message": "not found"})
        try:
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n).decode("utf-8")) if n else {}
        except Exception as e:
            return self._send_json(400, {"status": "error", "message": f"bad json: {e}"})

        name = body.get("name") or ""
        args = body.get("args") or {}
        agent = self.agents.get(name)
        if not agent:
            return self._send_json(404, {
                "status": "error",
                "message": f"unknown agent: {name}",
                "available": sorted(self.agents.keys()),
            })
        try:
            output = agent.perform(**args)
            return self._send_json(200, {"status": "ok", "output": output})
        except Exception as e:
            traceback.print_exc()
            return self._send_json(500, {
                "status": "error",
                "message": str(e),
                "trace": traceback.format_exc(limit=5),
            })

    # Quieter than the default access log.
    def log_message(self, fmt, *args):
        sys.stderr.write(f"  → {fmt % args}\n")


def main():
    p = argparse.ArgumentParser(
        description="RAPP Tether Server — bridges local agents to the virtual brainstem."
    )
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--host", default="127.0.0.1",
                   help="Bind address. Use 0.0.0.0 to expose on LAN (default: localhost only)")
    p.add_argument("--agents", default="./agents",
                   help="Directory of *_agent.py files (default: ./agents)")
    args = p.parse_args()

    agents_dir = Path(args.agents).resolve()
    if not agents_dir.exists():
        print(f"  Agents directory not found: {agents_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"\n  RAPP Tether Server")
    print(f"  {'─' * 36}")
    print(f"  Loading agents from {agents_dir}\n")
    TetherHandler.agents = load_agents(agents_dir)

    if not TetherHandler.agents:
        print(f"\n  No agents loaded. Drop *_agent.py files into {agents_dir}.", file=sys.stderr)
        sys.exit(1)

    url = f"http://{args.host}:{args.port}"
    print(f"\n  Listening on  {url}")
    print(f"  Health check  {url}/tether/healthz")
    print(f"\n  → In the virtual brainstem (https://kody-w.github.io/RAPP/brainstem/)")
    print(f"    open Settings → Tether → paste {url} → Save.")
    print(f"\n  Ctrl-C to stop.\n")

    server = HTTPServer((args.host, args.port), TetherHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Shutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
