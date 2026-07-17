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


FORBIDDEN_AMBIENT_ENV = (
    "ANTHROPIC_API_KEY",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SHARED_CREDENTIALS_FILE",
    "AZURE_CLIENT_SECRET",
    "AZURE_CONFIG_DIR",
    "COPILOT_API_TOKEN",
    "COPILOT_GITHUB_TOKEN",
    "DOCKER_CONFIG",
    "GITHUB_TOKEN",
    "GITHUB_APP_PRIVATE_KEY",
    "GITHUB_COPILOT_TOKEN",
    "GITHUB_PASSWORD",
    "GH_TOKEN",
    "COPILOT_TOKEN",
    "GIT_ASKPASS",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "KUBECONFIG",
    "NPM_CONFIG_USERCONFIG",
    "OPENAI_API_KEY",
    "RAPP_SENTINEL_KEY",
    "RAPP_SENTINEL_SECRET",
    "RAPP_SENTINEL_TOKEN",
    "SSH_ASKPASS",
    "SSH_AUTH_SOCK",
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
    leaked = [
        name
        for name in FORBIDDEN_AMBIENT_ENV
        if name in os.environ
    ]
    leaked.extend(
        name
        for name in os.environ
        if name.upper().endswith(("_KEY", "_PASSWORD", "_SECRET", "_TOKEN"))
    )
    if leaked:
        raise AssertionError(f"ambient credentials were passed: {sorted(set(leaked))}")
    root = Path(os.environ["RAPP1_WORK_ROOT"]).resolve()
    for name in ("CURL_HOME", "HOME", "GH_CONFIG_DIR", "XDG_CONFIG_HOME"):
        Path(os.environ[name]).resolve().relative_to(root)
    if os.environ["GIT_CONFIG_GLOBAL"] != os.devnull:
        raise AssertionError("ambient global Git config was not disabled")
    if os.environ["NETRC"] != os.devnull:
        raise AssertionError("ambient netrc handle was not disabled")
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
    wildcard_listener = socket.socket()
    wildcard_listener.bind(("0.0.0.0", 0))
    if wildcard_listener.getsockname()[0] != "127.0.0.1":
        raise AssertionError("wildcard Python bind was not rewritten to loopback")
    wildcard_listener.close()

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

    udp_listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_listener.bind(("127.0.0.1", 0))
    udp_listener.settimeout(1)
    udp_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        udp_client.sendto(b"loopback-sendto", udp_listener.getsockname())
        payload, _ = udp_listener.recvfrom(1024)
        if payload != b"loopback-sendto":
            raise AssertionError("loopback UDP sendto payload changed")
        if hasattr(udp_client, "sendmsg"):
            udp_client.sendmsg(
                [b"loopback-", b"sendmsg"],
                [],
                0,
                udp_listener.getsockname(),
            )
            payload, _ = udp_listener.recvfrom(1024)
            if payload != b"loopback-sendmsg":
                raise AssertionError("loopback UDP sendmsg payload changed")
    finally:
        udp_client.close()
        udp_listener.close()

    external_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        for label, operation in (
            (
                "sendto",
                lambda: external_udp.sendto(b"blocked", ("192.0.2.1", 9)),
            ),
            *(
                (
                    (
                        "sendmsg",
                        lambda: external_udp.sendmsg(
                            [b"blocked"], [], 0, ("192.0.2.1", 9)
                        ),
                    ),
                )
                if hasattr(external_udp, "sendmsg")
                else ()
            ),
        ):
            try:
                operation()
            except OSError as error:
                if "RAPP1 offline gate blocks" not in str(error):
                    raise AssertionError(
                        f"unexpected external UDP {label} failure: {error}"
                    ) from error
            else:
                raise AssertionError(f"external UDP {label} was not blocked")
    finally:
        external_udp.close()

    for label, operation in (
        ("getfqdn", lambda: socket.getfqdn("192.0.2.1")),
        ("gethostbyaddr", lambda: socket.gethostbyaddr("192.0.2.1")),
        (
            "getnameinfo",
            lambda: socket.getnameinfo(("192.0.2.1", 80), 0),
        ),
    ):
        try:
            operation()
        except OSError as error:
            if "RAPP1 offline gate blocks" not in str(error):
                raise AssertionError(
                    f"unexpected external reverse-DNS {label} failure: {error}"
                ) from error
        else:
            raise AssertionError(f"external reverse-DNS {label} was not blocked")

    if not socket.getfqdn("127.0.0.1"):
        raise AssertionError("loopback getfqdn was not preserved")
    loopback_name, _, loopback_addresses = socket.gethostbyaddr("127.0.0.1")
    if not loopback_name or "127.0.0.1" not in loopback_addresses:
        raise AssertionError("loopback gethostbyaddr was not preserved")
    if not socket.getnameinfo(
        ("127.0.0.1", 0),
        socket.NI_NUMERICHOST | socket.NI_NUMERICSERV,
    )[0]:
        raise AssertionError("loopback getnameinfo was not preserved")

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
            "tests/offline_guard/node-network-probe.cjs",
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
    if "permits loopback" not in node.stdout:
        raise AssertionError(f"Node loopback probe did not complete: {node.stdout}")


def main() -> int:
    _check_environment()
    _check_python_sockets()
    _check_http_clients()
    print(
        "Offline boundary verified: credentials scrubbed; loopback allowed; "
        "external HTTP denied; external UDP and reverse DNS denied"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
