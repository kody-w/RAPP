#!/usr/bin/env python3
"""tls_proxy.py — self-signed HTTPS in front of the local brainstem.

Why: the live tether at https://kody-w.github.io/RAPP/pages/tether.html
can't fetch http://localhost:7071/chat — browsers block HTTPS→HTTP
"mixed content" regardless of CORS. This standalone proxy gives the
tether a same-scheme target so the "🌐 Ground tether to local brainstem"
feature works without an external tunnel service (cloudflared, ngrok).

Architecture: kernel brainstem.py stays untouched (kernel sacred per
CONSTITUTION Article XXXIII). This is a sibling process — HTTPS
reverse-proxy. Run alongside ./start.sh.

Usage:
    # Terminal 1: the brainstem itself
    cd rapp_brainstem && ./start.sh

    # Terminal 2: the HTTPS proxy
    python3 rapp_brainstem/tls_proxy.py

    # Terminal 3 (one-time): trust the cert in your browser
    open https://localhost:7072/
    # Browser shows "Your connection isn't private" — click
    # "Advanced" → "Proceed to localhost (unsafe)" once.
    # macOS Chrome: also add the cert to Keychain if you want the
    # warning to disappear permanently.

After that the tether's "🌐 Ground" prompt accepts
https://localhost:7072/chat and grounded mode works.

Cert details: RSA-2048 self-signed, CN=localhost, SAN includes
DNS:localhost + IP:127.0.0.1, valid 825 days. Generated once into
~/.brainstem/tls/{cert.pem,key.pem} and reused on every restart so
the browser trust persists.

Pure stdlib + openssl CLI (installed on macOS + most Linux distros
by default). No pip dependencies.
"""

from __future__ import annotations
# RAPP_RESTORED_GATE_BEGIN
_RAPP_RESTORED_TARGET = "rapp_brainstem/tls_proxy.py"
_RAPP_RESTORED_SOURCE_COMMIT = "55b91b9ecd182a3ce2057787f07c60e9aa3ca128"
_RAPP_RESTORED_SOURCE_BLOB = "ee3fc89f515e43042f89fdd9ffe82827022a5503"
_RAPP_KERNEL_PIN_SHA256 = "427a37cc914a279b9c32a2ab85be9a19a0046f10f9f503c088a2670b6646e21c"
_RAPP_FROZEN = {
    "rapp_brainstem/brainstem.py": "a293dd9f11eef915bf15776f08c736faa60cb749820871b6753ea98233142a71",
    "rapp_brainstem/agents/basic_agent.py": "701488bc00d536a7b23295e7da99c62f24e9b00f233daa325886430c736b78eb",
    "rapp_brainstem/VERSION": "13eb74b44be6e3a85a0efa0dedf56aec05e9e50140e1c8bbc0d0fbd8097b0717",
}


def _rapp_restored_plan():
    print(
        '{"schema":"rapp-restored-distribution-source/1.0",'
        f'"target":"{_RAPP_RESTORED_TARGET}","mode":"plan",'
        f'"source_commit":"{_RAPP_RESTORED_SOURCE_COMMIT}",'
        f'"source_blob":"{_RAPP_RESTORED_SOURCE_BLOB}",'
        '"kernel":"kody-w/rapp-installer@brainstem-v0.6.9",'
        f'"kernel_pin_sha256":"{_RAPP_KERNEL_PIN_SHA256}",'
        '"apply_permitted":false,'
        '"reason":"authenticated-section-13-evidence-unavailable"}'
    )


def _rapp_restored_refuse(message):
    print(
        f"410 Gone: {_RAPP_RESTORED_TARGET}: {message} (RAPP1_STATUS.md)",
        file=__import__("sys").stderr,
    )
    return 78


def _rapp_restored_pin_matches(path):
    hashlib_module = __import__("hashlib")
    json_module = __import__("json")
    pathlib_module = __import__("pathlib")
    pin_path = pathlib_module.Path(path)
    try:
        pin_bytes = pin_path.read_bytes()
        pin = json_module.loads(pin_bytes)
    except (OSError, TypeError, ValueError):
        return False
    if hashlib_module.sha256(pin_bytes).hexdigest() != _RAPP_KERNEL_PIN_SHA256:
        return False
    kernel = pin.get("kernel", {})
    if (
        kernel.get("grail") != "kody-w/rapp-installer"
        or kernel.get("tag") != "brainstem-v0.6.9"
        or kernel.get("frozen") != _RAPP_FROZEN
    ):
        return False
    root = pathlib_module.Path(__file__).resolve().parents[1]
    try:
        return all(
            hashlib_module.sha256((root / relative).read_bytes()).hexdigest()
            == digest
            for relative, digest in _RAPP_FROZEN.items()
        )
    except OSError:
        return False


def _rapp_restored_gate(argv):
    argv = list(argv)
    mode = argv.pop(0) if argv else "plan"
    if mode in {"plan", "--plan", "inspect", "--inspect", "check", "--check", "help", "--help", "-h"}:
        _rapp_restored_plan()
        return 0
    if mode not in {"apply", "--apply", "run", "--run"}:
        return _rapp_restored_refuse(
            "explicit plan/check/inspect or gated --apply is required"
        )
    values = {}
    allow_active_effects = False
    while argv:
        option = argv.pop(0)
        if option == "--allow-active-effects":
            allow_active_effects = True
            continue
        if option not in {
            "--target",
            "--kernel-pin",
            "--reviewed-dependency-injection",
            "--owner-approval",
            "--section13-evidence",
        }:
            return _rapp_restored_refuse(
                f"unsupported activation argument: {option}"
            )
        if not argv:
            return _rapp_restored_refuse(f"missing value for {option}")
        values[option] = argv.pop(0)
    if not allow_active_effects:
        return _rapp_restored_refuse("--allow-active-effects is required")
    if values.get("--target") != _RAPP_RESTORED_TARGET:
        return _rapp_restored_refuse(
            "target-specific approval target is missing or mismatched"
        )
    if not _rapp_restored_pin_matches(values.get("--kernel-pin", "")):
        return _rapp_restored_refuse(
            "exact KERNEL_PIN.json for "
            "kody-w/rapp-installer@brainstem-v0.6.9 is required"
        )
    path_class = __import__("pathlib").Path
    for option, label in (
        ("--reviewed-dependency-injection", "reviewed dependency injection"),
        ("--owner-approval", "target-specific owner approval"),
        ("--section13-evidence", "authenticated fresh section-13 evidence"),
    ):
        if not path_class(values.get(option, "")).is_file():
            return _rapp_restored_refuse(f"{label} is required")
    return _rapp_restored_refuse(
        "authenticated fresh section-13 evidence is unavailable"
    )


if __name__ == "__main__":
    raise SystemExit(_rapp_restored_gate(__import__("sys").argv[1:]))
# RAPP_RESTORED_GATE_END

import argparse
import http.server
import os
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

TLS_DIR = Path(os.path.expanduser("~/.brainstem/tls"))
CERT    = TLS_DIR / "cert.pem"
KEY     = TLS_DIR / "key.pem"


def ensure_cert() -> None:
    """Generate a self-signed cert at ~/.brainstem/tls/ if missing."""
    if CERT.exists() and KEY.exists():
        return
    TLS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[tls_proxy] generating self-signed cert at {CERT} …")
    try:
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:2048",
            "-keyout", str(KEY),
            "-out",    str(CERT),
            "-days",   "825",
            "-nodes",
            "-subj",   "/CN=localhost",
            "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1",
        ], check=True, capture_output=True)
    except FileNotFoundError:
        sys.exit("[tls_proxy] error: openssl not found. Install it "
                 "(macOS: pre-installed; apt: `apt install openssl`).")
    except subprocess.CalledProcessError as e:
        sys.exit(f"[tls_proxy] openssl failed:\n{e.stderr.decode(errors='replace')}")
    # Tighten permissions so the key is operator-only-readable.
    try:
        os.chmod(KEY, 0o600)
        os.chmod(CERT, 0o644)
    except Exception:
        pass


# ────────────────────────────────────────────────────────────────────
# Reverse-proxy HTTP handler
# ────────────────────────────────────────────────────────────────────

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    target: str = "http://localhost:7071"

    # Skip-headers: hop-by-hop + things urllib will set for us, and
    # the upstream's CORS headers (we replace with permissive ones).
    HOP = {
        "host", "connection", "keep-alive", "transfer-encoding",
        "upgrade", "proxy-authenticate", "proxy-authorization",
        "te", "trailer",
        "access-control-allow-origin",
        "access-control-allow-headers",
        "access-control-allow-methods",
        "access-control-allow-credentials",
    }

    def _write_cors(self) -> None:
        # Permissive CORS so the live tether at kody-w.github.io can
        # post + preflight. Brainstem already has flask_cors, but the
        # proxy strips upstream CORS so we apply our own consistently.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE, PATCH")
        self.send_header("Access-Control-Max-Age", "86400")

    def do_OPTIONS(self) -> None:  # CORS preflight
        self.send_response(204)
        self._write_cors()
        self.end_headers()

    def _proxy(self) -> None:
        body = None
        clen = self.headers.get("Content-Length")
        if clen:
            try:
                body = self.rfile.read(int(clen))
            except Exception as e:
                self.send_response(400)
                self._write_cors()
                self.end_headers()
                self.wfile.write(f"read body: {e}".encode())
                return
        url = self.target + self.path
        req = urllib.request.Request(url, data=body, method=self.command)
        for h in self.headers:
            if h.lower() in self.HOP:
                continue
            req.add_header(h, self.headers[h])
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                self.send_response(r.status)
                for h, v in r.headers.items():
                    if h.lower() in self.HOP:
                        continue
                    self.send_header(h, v)
                self._write_cors()
                self.end_headers()
                self.wfile.write(r.read())
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            for h, v in e.headers.items():
                if h.lower() in self.HOP:
                    continue
                self.send_header(h, v)
            self._write_cors()
            self.end_headers()
            try:
                self.wfile.write(e.read())
            except Exception:
                pass
        except urllib.error.URLError as e:
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self._write_cors()
            self.end_headers()
            self.wfile.write(
                f'{{"error":"brainstem at {self.target} unreachable: '
                f'{e.reason}. Is `./start.sh` running?"}}'.encode()
            )
        except Exception as e:
            self.send_response(502)
            self.send_header("Content-Type", "text/plain")
            self._write_cors()
            self.end_headers()
            self.wfile.write(f"proxy error: {e}".encode())

    # Wire every HTTP method through the same proxy path. Flask + the
    # brainstem use POST /chat, GET /agents, GET /voice/toggle etc;
    # this covers them all.
    do_GET   = _proxy
    do_POST  = _proxy
    do_PUT   = _proxy
    do_PATCH = _proxy
    do_DELETE = _proxy

    def log_message(self, fmt, *args) -> None:
        sys.stdout.write(f"[tls_proxy] {fmt % args}\n")
        sys.stdout.flush()


# ────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port",   type=int, default=int(os.environ.get("TLS_PORT", "7072")),
                    help="HTTPS port to listen on (default 7072 / env TLS_PORT)")
    ap.add_argument("--target", default=os.environ.get("BRAINSTEM_URL", "http://localhost:7071"),
                    help="Upstream brainstem URL (default http://localhost:7071 / env BRAINSTEM_URL)")
    args = ap.parse_args()

    ensure_cert()

    ProxyHandler.target = args.target.rstrip("/")

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(certfile=str(CERT), keyfile=str(KEY))

    server = http.server.ThreadingHTTPServer(("0.0.0.0", args.port), ProxyHandler)
    server.socket = ctx.wrap_socket(server.socket, server_side=True)

    print(f"\n🔒 RAPP brainstem TLS proxy")
    print(f"   listening:  https://localhost:{args.port}")
    print(f"   target:     {args.target}")
    print(f"   cert:       {CERT}")
    print(f"   key:        {KEY}\n")
    print(f"FIRST RUN: visit https://localhost:{args.port}/ in the browser")
    print(f"you'll use the tether from, click 'Advanced' →")
    print(f"'Proceed to localhost (unsafe)'. After that, the browser remembers")
    print(f"the trust and the live tether's '🌐 Ground' button works against")
    print(f"https://localhost:{args.port}/chat.\n")
    print(f"Stop with Ctrl-C.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[tls_proxy] shutting down")
        return 0


if __name__ == "__main__":
    sys.exit(main())
