#!/usr/bin/env python3
"""Exercise the canonical credential and external-network boundary."""

from __future__ import annotations

import http.server
import os
import socket
import subprocess
import sys
import threading
from pathlib import Path


EMPTY_CREDENTIALS = (
    "GITHUB_TOKEN",
    "GH_TOKEN",
    "COPILOT_TOKEN",
    "COPILOT_GITHUB_TOKEN",
    "GITHUB_COPILOT_TOKEN",
    "COPILOT_API_TOKEN",
)
PROXY = "http://127.0.0.1:1"


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"loopback-ok")

    def log_message(self, _format, *_args):
        return


def _check_environment() -> None:
    for name in EMPTY_CREDENTIALS:
        if os.environ.get(name):
            raise AssertionError(f"credential was not scrubbed: {name}")
    root = Path(os.environ["RAPP1_WORK_ROOT"]).resolve()
    for name in ("HOME", "GH_CONFIG_DIR", "XDG_CONFIG_HOME"):
        Path(os.environ[name]).resolve().relative_to(root)
    for name in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ):
        if os.environ.get(name) != PROXY:
            raise AssertionError(f"offline proxy is not enforced: {name}")
    no_proxy = set(os.environ["NO_PROXY"].split(","))
    if not {"localhost", "127.0.0.1", "::1"} <= no_proxy:
        raise AssertionError("loopback is not exempted from the offline proxy")
    if os.environ.get("PYTHON_DOTENV_DISABLED") != "1":
        raise AssertionError("dotenv loading is not disabled")
    if os.environ.get("RAPP1_PYTHON_NETWORK_GUARD") != "1":
        raise AssertionError("Python socket guard was not loaded")


def _check_python_sockets() -> None:
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    client = socket.create_connection(listener.getsockname(), timeout=1)
    accepted, _ = listener.accept()
    client.close()
    accepted.close()
    listener.close()

    try:
        socket.create_connection(("192.0.2.1", 80), timeout=0.1)
    except OSError as error:
        if "RAPP1 offline gate blocks" not in str(error):
            raise AssertionError(f"unexpected external socket failure: {error}") from error
    else:
        raise AssertionError("external Python socket was not blocked")

    child_environment = os.environ.copy()
    child_environment["PYTHONPATH"] = os.environ["RAPP1_WORK_ROOT"]
    child = subprocess.run(
        [
            "python3",
            "-c",
            (
                "import os,socket;"
                "assert os.environ.get('RAPP1_PYTHON_NETWORK_GUARD') == '1';"
                "\ntry: socket.create_connection(('192.0.2.1',80),timeout=.1)"
                "\nexcept OSError as e:"
                "\n assert 'RAPP1 offline gate blocks' in str(e)"
                "\nelse: raise AssertionError('external child socket was not blocked')"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
        env=child_environment,
    )
    if child.returncode:
        raise AssertionError(f"child Python guard failed: {child.stderr}")


def _check_http_clients() -> None:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        local = subprocess.run(
            [
                "curl",
                "-fsS",
                f"http://127.0.0.1:{server.server_port}/",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if local.returncode or local.stdout != "loopback-ok":
            raise AssertionError(f"loopback curl failed: {local.stderr}")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    external = subprocess.run(
        [
            "curl",
            "-v",
            "--connect-timeout",
            "1",
            "--max-time",
            "2",
            "http://192.0.2.1/",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    if external.returncode == 0 or "127.0.0.1" not in external.stderr:
        raise AssertionError("curl did not fail through the enforced loopback proxy")

    node = subprocess.run(
        [
            "node",
            "-e",
            (
                "if (process.env.RAPP1_NODE_NETWORK_GUARD !== '1') process.exit(3);"
                "try { require('node:https').get('https://example.com/'); }"
                "catch (e) {"
                " if (/RAPP1 offline gate blocks/.test(String(e))) process.exit(0);"
                " throw e;"
                "}"
                "process.exit(4);"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    if node.returncode:
        raise AssertionError(
            f"Node external HTTP guard failed ({node.returncode}): {node.stderr}"
        )


def main() -> int:
    _check_environment()
    _check_python_sockets()
    _check_http_clients()
    print("Offline boundary verified: credentials scrubbed; loopback allowed; external HTTP denied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
