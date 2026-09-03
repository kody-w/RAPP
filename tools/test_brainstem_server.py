#!/usr/bin/env python3
"""tools/test_brainstem_server.py — minimal HTTP server wrapping the
neighborhood_membership_organ for federation tests.

Current no-flag behavior emits a deterministic no-bind replay. The historical
server implementation is retained, but a real bind requires reviewed injected
home/organ/server/facade dependencies, an exact target receipt, and fresh
authenticated section-13 evidence.

Boots a stdlib http.server on the requested port that exposes the same
/api/neighborhoods/* surface as the full brainstem. Used in scenarios
that need to exercise REAL cross-process HTTP federation (one process
POSTs to another's /api/.../contribute) without the cost of starting
multiple full Flask brainstems with venvs and deps.

Usage:
    python3 tools/test_brainstem_server.py
    python3 tools/test_brainstem_server.py --serve --port 7081 --home /tmp/bs-A
    # in another terminal:
    python3 tools/test_brainstem_server.py --port 7082 --home /tmp/bs-B
    # then POST a join + contribute between them.

Mounts:
  GET  /health                                  → {"ok": true, "port": <port>, "home": <home>}
  GET  /api/neighborhoods                       → list subscriptions
  POST /api/neighborhoods/join                  → join via gate_url
  GET  /api/neighborhoods/estate                → synthesized estate
  GET  /api/neighborhoods/by-rappid/<rappid>    → estate-by-identity lookup
  GET  /api/neighborhoods/<owner>/<repo>        → subscription detail
  POST /api/neighborhoods/<owner>/<repo>/sync   → resync
  GET  /api/neighborhoods/<owner>/<repo>/members
  POST /api/neighborhoods/<owner>/<repo>/leave
  POST /api/neighborhoods/<owner>/<repo>/contribute   ← federation receiver
  GET  /api/neighborhoods/<owner>/<repo>/contributions

The organ's HOME_BRAINSTEM / SUBS_FILE / CACHE_DIR are redirected to the
provided --home so each test process has its own subscription cache.
Logs to stderr; uses no third-party deps.
"""

import argparse
import hashlib
import http.server
import importlib.util
import json
import os
import socket
import socketserver
import sys
import threading
import time
from collections.abc import Callable, Mapping
from urllib.parse import urlsplit

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

try:
    from rapp1_core import canonical_bytes, strict_loads
except (ImportError, ModuleNotFoundError):
    canonical_bytes = None
    strict_loads = None


HISTORICAL_SOURCE = {
    "path": "tools/test_brainstem_server.py",
    "commit": "dd36590c8f5601c3ccf241844cdc9db54f7c420b",
    "blob": "9675cfc201e1aedffb6a3bf118bace07a8381897",
    "sha256": "399f3d1e7227787846e347232ba35456e8c73ac5a685acdbcc59df9f830130e5",
    "bytes": 7441,
}
FACADE_URL = "http://127.0.0.1:7073/chat"
TARGET_RECEIPT_SCHEMA = "rapp-effect-target-receipt/1.0"
PENDING_FACADE_ERROR_CODES = {
    "malformed-request",
    "unknown-session",
    "idempotency-in-progress",
    "session-in-progress",
    "inference-refused",
    "facade-storage-refused",
}
MAX_RAW_REQUEST_BYTES = 2 * 1024 * 1024
MAX_CANONICAL_REQUEST_BYTES = 1024 * 1024


DEFAULT_ORGAN = os.path.join(
    REPO_ROOT,
    "rapp_brainstem", "utils", "organs", "neighborhood_membership_organ.py",
)


def _load_organ(path, home_dir):
    spec = importlib.util.spec_from_file_location("test_membership_organ", path)
    organ = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(organ)
    organ.HOME_BRAINSTEM = home_dir
    organ.SUBS_FILE = os.path.join(home_dir, "neighborhoods.json")
    organ.CACHE_DIR = os.path.join(home_dir, "neighborhoods")
    os.makedirs(organ.CACHE_DIR, exist_ok=True)
    return organ


def exact_target_receipt(operation, target):
    return {
        "schema": TARGET_RECEIPT_SCHEMA,
        "operation": operation,
        "target": dict(target),
    }


def rapp_chat_target(request_sha256):
    return {
        "url": FACADE_URL,
        "wire": "rapp/1-section-8",
        "request_sha256": request_sha256,
    }


def organ_request_target(method, path, request_sha256):
    return {
        "surface": "historical-neighborhood-organ",
        "method": method,
        "path": path,
        "request_sha256": request_sha256,
    }


def _is_allowed_loopback_origin(origin):
    try:
        parsed = urlsplit(origin)
    except (TypeError, ValueError):
        return False
    return (
        parsed.scheme in {"http", "https"}
        and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        and parsed.username is None
        and parsed.password is None
    )


def authorize_effect(
    *,
    operation,
    target,
    dependencies,
    target_receipt,
    authority_evidence,
):
    """Authorize in review -> receipt -> section-13 order."""
    if not isinstance(dependencies, Mapping):
        return {"code": "reviewed-dependency-injection-required", "step": "dependency-injection"}
    review = dependencies.get("review")
    if not isinstance(review, Callable) or review(dependencies, operation, target) is not True:
        return {"code": "reviewed-dependency-injection-required", "step": "dependency-review"}
    if target_receipt != exact_target_receipt(operation, target):
        return {"code": "exact-target-receipt-required", "step": "target-receipt"}
    authenticate = dependencies.get("authenticate_section13")
    if not isinstance(authenticate, Callable):
        return {"code": "authenticated-registry-unavailable", "step": "section-13-authentication"}
    verdict = authenticate(authority_evidence, operation, target)
    if (
        not isinstance(verdict, Mapping)
        or verdict.get("authenticated") is not True
        or verdict.get("fresh") is not True
        or verdict.get("owner_anchor_verified") is not True
    ):
        return {"code": "authenticated-registry-unavailable", "step": "section-13-authentication"}
    return None


def _validated_facade_result(result):
    if (
        not isinstance(result, tuple)
        or len(result) != 2
        or type(result[0]) is not int
        or not isinstance(result[1], Mapping)
    ):
        raise ValueError("facade transport must return (status, mapping)")
    status, body = result
    if status == 200:
        if set(body) != {"response", "agent_logs", "session_id"}:
            raise ValueError("invalid facade success members")
        if (
            type(body["response"]) is not str
            or type(body["agent_logs"]) is not list
            or type(body["session_id"]) is not str
        ):
            raise ValueError("invalid facade success types")
    elif status == 422:
        if (
            set(body) != {"error"}
            or type(body["error"]) is not dict
            or set(body["error"]) != {"code", "step"}
        ):
            raise ValueError("invalid facade refusal")
        code = body["error"]["code"]
        step = body["error"]["step"]
        if type(code) is not str or code not in PENDING_FACADE_ERROR_CODES:
            raise ValueError("invalid facade refusal code")
        if step is not None:
            raise ValueError("invalid facade refusal step")
    else:
        raise ValueError("invalid facade status")
    return status, body


def _authorize_chat_forward(request_sha256, dependencies):
    target = rapp_chat_target(request_sha256)
    receipts = (
        dependencies.get("chat_target_receipts")
        if isinstance(dependencies, Mapping)
        else None
    )
    target_receipt = (
        receipts.get(request_sha256)
        if isinstance(receipts, Mapping)
        else None
    )
    authority_evidence = (
        dependencies.get("chat_authority_evidence")
        if isinstance(dependencies, Mapping)
        else None
    )
    return authorize_effect(
        operation="test-brainstem-chat-forward",
        target=target,
        dependencies=dependencies,
        target_receipt=target_receipt,
        authority_evidence=authority_evidence,
    )


def _authorize_organ_forward(method, path, request_sha256, dependencies):
    target = organ_request_target(method, path, request_sha256)
    receipts = (
        dependencies.get("organ_target_receipts")
        if isinstance(dependencies, Mapping)
        else None
    )
    target_receipt = (
        receipts.get(request_sha256)
        if isinstance(receipts, Mapping)
        else None
    )
    authority_evidence = (
        dependencies.get("organ_authority_evidence")
        if isinstance(dependencies, Mapping)
        else None
    )
    return authorize_effect(
        operation="test-brainstem-organ-dispatch",
        target=target,
        dependencies=dependencies,
        target_receipt=target_receipt,
        authority_evidence=authority_evidence,
    )


def _build_handler(
    organ,
    port,
    home_dir,
    facade_transport=None,
    effect_dependencies=None,
):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            sys.stderr.write(f"[{port}] {fmt % args}\n")

        def _read_body(self):
            length = int(self.headers.get("Content-Length") or 0)
            if not length:
                return None
            raw = self.rfile.read(length).decode("utf-8")
            if not raw:
                return None
            try:
                return json.loads(raw)
            except ValueError:
                return None

        def _read_chat_body(self):
            if canonical_bytes is None or strict_loads is None:
                raise ValueError("strict RAPP request validator is unavailable")
            content_type = self.headers.get("Content-Type")
            if content_type and not content_type.lower().startswith(
                "application/json"
            ):
                raise ValueError("chat content type must be application/json")
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > MAX_RAW_REQUEST_BYTES:
                raise ValueError("chat body length is invalid")
            raw = self.rfile.read(length)
            try:
                body = strict_loads(raw)
                canonical = canonical_bytes(body)
            except (TypeError, ValueError, RecursionError) as exc:
                raise ValueError("chat body violates strict JSON") from exc
            if len(canonical) > MAX_CANONICAL_REQUEST_BYTES:
                raise ValueError("canonical chat body exceeds one MiB")
            if type(body) is not dict or type(body.get("user_input")) is not str:
                raise ValueError("chat body has invalid recognized members")
            for optional in ("session_id", "idempotency_key"):
                if optional in body and type(body[optional]) is not str:
                    raise ValueError(f"{optional} must be a string")
            try:
                body["user_input"].encode("utf-8")
                for optional in ("session_id", "idempotency_key"):
                    if optional in body:
                        body[optional].encode("utf-8")
            except UnicodeEncodeError as exc:
                raise ValueError("chat body contains an invalid string") from exc
            payload = {"user_input": body["user_input"]}
            for optional in ("session_id", "idempotency_key"):
                if optional in body:
                    payload[optional] = body[optional]
            return payload, hashlib.sha256(canonical).hexdigest()

        def _send(self, status, body):
            payload = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            origin = self.headers.get("Origin")
            if origin and _is_allowed_loopback_origin(origin):
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _read_organ_body(self, method, path):
            length = int(self.headers.get("Content-Length") or 0)
            if length < 0 or length > MAX_RAW_REQUEST_BYTES:
                raise ValueError("organ body length is invalid")
            if length:
                raw = self.rfile.read(length)
                try:
                    body = strict_loads(raw)
                    canonical_body = canonical_bytes(body)
                except (TypeError, ValueError, RecursionError) as exc:
                    raise ValueError("organ body violates strict JSON") from exc
                if len(canonical_body) > MAX_CANONICAL_REQUEST_BYTES:
                    raise ValueError("canonical organ body exceeds one MiB")
            else:
                body = None
            request_value = {
                "method": method,
                "path": path,
                "body": body,
            }
            canonical_request = canonical_bytes(request_value)
            if len(canonical_request) > MAX_CANONICAL_REQUEST_BYTES:
                raise ValueError("canonical organ request exceeds one MiB")
            return body, hashlib.sha256(canonical_request).hexdigest()

        def _handle(self, method):
            path = self.path.split("?", 1)[0]
            origin = self.headers.get("Origin")
            if origin and not _is_allowed_loopback_origin(origin):
                if path == "/chat":
                    self._send(422, {"error": {"code": "malformed-request", "step": None}})
                else:
                    self._send(403, {"error": "loopback browser origin required"})
                return
            if path == "/health":
                self._send(200, {
                    "ok": True, "port": port, "home": home_dir,
                    "schema": "rapp-test-brainstem/1.0",
                    "organ": "neighborhood_membership_organ",
                })
                return
            # Candidate RAPP chat uses only the exact target-owned loopback
            # facade. The historical echo envelope is retained in provenance,
            # not revived as a second wire.
            if path == "/chat" and method == "POST":
                try:
                    body, request_sha256 = self._read_chat_body()
                except ValueError:
                    self._send(422, {"error": {"code": "malformed-request", "step": None}})
                    return
                if not isinstance(facade_transport, Callable):
                    self._send(422, {"error": {"code": "inference-refused", "step": None}})
                    return
                if _authorize_chat_forward(request_sha256, effect_dependencies) is not None:
                    self._send(422, {"error": {"code": "inference-refused", "step": None}})
                    return
                try:
                    status, response = _validated_facade_result(
                        facade_transport(FACADE_URL, body)
                    )
                except (OSError, TypeError, ValueError):
                    self._send(422, {"error": {"code": "inference-refused", "step": None}})
                    return
                self._send(status, response)
                return
            if not path.startswith("/api/neighborhoods"):
                self._send(404, {"error": "no route"})
                return
            rest = path[len("/api/neighborhoods"):].lstrip("/")
            try:
                body, request_sha256 = self._read_organ_body(
                    method, path
                )
            except ValueError:
                self._send(400, {"error": "invalid organ request"})
                return
            if _authorize_organ_forward(
                method,
                path,
                request_sha256,
                effect_dependencies,
            ) is not None:
                self._send(403, {"error": "organ request not authorized"})
                return
            try:
                result, status = organ.handle(method, rest, body)
            except Exception as e:
                import traceback
                self._send(500, {"error": str(e), "traceback": traceback.format_exc()[-2000:]})
                return
            self._send(status, result)

        def do_GET(self):    self._handle("GET")
        def do_POST(self):   self._handle("POST")
        def do_PATCH(self):  self._handle("PATCH")
        def do_DELETE(self): self._handle("DELETE")
        def do_OPTIONS(self):
            origin = self.headers.get("Origin")
            if not origin or not _is_allowed_loopback_origin(origin):
                self.send_response(403)
                self.end_headers()
                return
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
    return Handler


class _ThreadingServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def _wait_for_port(port, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                return True
        except (OSError, ConnectionRefusedError):
            time.sleep(0.05)
    return False


def serve(
    *,
    port,
    home,
    organ_path=DEFAULT_ORGAN,
    bind="127.0.0.1",
    dependencies=None,
    target_receipt=None,
    authority_evidence=None,
):
    target = {
        "bind": bind,
        "port": port,
        "home": os.path.abspath(home),
        "organ": os.path.abspath(organ_path),
        "facade": FACADE_URL,
    }
    if bind != "127.0.0.1":
        return {
            "schema": "rapp-test-brainstem-result/1.0",
            "ok": False,
            "bound": False,
            "effects_started": False,
            "error": {
                "code": "loopback-bind-required",
                "step": "bind-target",
            },
            "target": target,
        }
    refusal = authorize_effect(
        operation="test-brainstem-bind",
        target=target,
        dependencies=dependencies,
        target_receipt=target_receipt,
        authority_evidence=authority_evidence,
    )
    if refusal is not None:
        return {
            "schema": "rapp-test-brainstem-result/1.0",
            "ok": False,
            "bound": False,
            "effects_started": False,
            "error": refusal,
            "target": target,
        }

    facade_transport = dependencies.get("facade_transport")
    prepare_home = dependencies.get("prepare_home")
    load_organ = dependencies.get("load_organ")
    server_factory = dependencies.get("server_factory")
    if not all(
        isinstance(candidate, Callable)
        for candidate in (facade_transport, prepare_home, load_organ, server_factory)
    ):
        return {
            "schema": "rapp-test-brainstem-result/1.0",
            "ok": False,
            "bound": False,
            "effects_started": False,
            "error": {
                "code": "reviewed-dependency-injection-required",
                "step": "server-dependencies",
            },
            "target": target,
        }

    prepare_home(home)
    organ = load_organ(organ_path, home)
    handler = _build_handler(
        organ,
        port,
        home,
        facade_transport,
        dependencies,
    )
    server = server_factory((bind, port), handler)

    sys.stdout.write(f"PORT={port} HOME={home}\n")
    sys.stdout.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.stderr.write("interrupted; shutting down\n")
    finally:
        server.shutdown()
        server.server_close()
    return {
        "schema": "rapp-test-brainstem-result/1.0",
        "ok": True,
        "bound": True,
        "target": target,
    }


def sandbox_replay():
    return {
        "schema": "rapp-test-brainstem-sandbox/1.0",
        "mode": "sandbox",
        "facade": FACADE_URL,
        "routes": [
            "/health",
            "/chat",
            "/api/neighborhoods",
            "/api/neighborhoods/join",
            "/api/neighborhoods/estate",
            "/api/neighborhoods/by-rappid/<rappid>",
            "/api/neighborhoods/<owner>/<repo>/contribute",
        ],
        "chat_result": {
            "status": 422,
            "body": {"error": {"code": "inference-refused", "step": None}},
        },
        "effects": [],
        "historical_source": HISTORICAL_SOURCE,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="test brainstem server (membership organ only)")
    p.add_argument("--serve", action="store_true", help="request an authenticated loopback bind")
    p.add_argument("--sandbox-replay", action="store_true", help="emit deterministic no-bind replay")
    p.add_argument("--port", type=int)
    p.add_argument("--home", type=str, help="sandboxed ~/.brainstem dir")
    p.add_argument("--organ", type=str, default=DEFAULT_ORGAN, help="path to membership organ")
    p.add_argument("--bind", type=str, default="127.0.0.1")
    args = p.parse_args(argv)

    if not args.serve:
        print(json.dumps(sandbox_replay(), indent=2, sort_keys=True))
        return 0
    if args.port is None or args.home is None:
        p.error("--serve requires --port and --home")

    result = serve(
        port=args.port,
        home=args.home,
        organ_path=args.organ,
        bind=args.bind,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 78


if __name__ == "__main__":
    raise SystemExit(main())
