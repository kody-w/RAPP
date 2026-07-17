"""Target-owned, pre-acceptance RAPP/1 ``/chat`` facade.

This module is intentionally independent of the immutable brainstem Flask app.
The injected inference boundary receives messages only. The production launcher
defaults to refusal until a reviewed side-effect-free adapter is injected.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import unicodedata
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Sequence
from urllib.parse import urlsplit

from flask import Flask, Response, request
from rapp1_core import canonical_bytes, strict_loads
from werkzeug.exceptions import RequestEntityTooLarge


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7073
GRAIL_PORT = 7071
MAX_RAW_REQUEST_BYTES = 2 * 1024 * 1024
FINGERPRINT_VERSION_UNBOUND = 1
FINGERPRINT_VERSION_LEGACY_JSON = 2
FINGERPRINT_VERSION_CANONICAL_SEMANTIC = 3
IDEMPOTENCY_POLL_SECONDS = 0.05
IDEMPOTENCY_HEARTBEAT_SECONDS = 0.25
IDEMPOTENCY_ORPHAN_AFTER_SECONDS = 30.0

# These names are candidates awaiting the authenticated RAPP/1 section 13
# owner registry. They are explicitly NOT registered error codes.
PENDING_REGISTRY_ERROR_CODES = (
    "malformed-request",
    "unknown-session",
    "idempotency-in-progress",
    "session-in-progress",
    "inference-refused",
    "facade-storage-refused",
)

Inference = Callable[[Sequence[dict[str, str]]], Any]


@dataclass(frozen=True)
class RuntimeConfig:
    host: str
    port: int
    database_path: Path


@dataclass(frozen=True)
class StoredResponse:
    status: int
    body: bytes


@dataclass(frozen=True)
class PendingIdempotency:
    scope: tuple[str, str, str]


@dataclass(frozen=True)
class Reservation:
    session_id: str
    token: str
    messages: tuple[dict[str, str], ...]
    idempotency_scope: tuple[str, str, str] | None
    request_fingerprint: bytes


class _ProcessCoordinator:
    def __init__(self) -> None:
        self.condition = threading.Condition()
        self.active_scopes: set[tuple[str, str, str]] = set()


_COORDINATORS_LOCK = threading.Lock()
_COORDINATORS: dict[str, _ProcessCoordinator] = {}


def _coordinator_for(database_path: Path) -> _ProcessCoordinator:
    key = str(database_path.resolve())
    with _COORDINATORS_LOCK:
        coordinator = _COORDINATORS.get(key)
        if coordinator is None:
            coordinator = _ProcessCoordinator()
            _COORDINATORS[key] = coordinator
        return coordinator


class FacadeRefusal(Exception):
    def __init__(self, code: str) -> None:
        if code not in PENDING_REGISTRY_ERROR_CODES:
            raise ValueError(f"unknown pending error code: {code}")
        super().__init__(code)
        self.code = code


def default_database_path(home: Path | None = None) -> Path:
    root = home if home is not None else Path.home()
    return root / ".brainstem" / "rapp1-facade.sqlite3"


def runtime_config(
    environ: Mapping[str, str] | None = None, *, home: Path | None = None
) -> RuntimeConfig:
    env = os.environ if environ is None else environ
    host = env.get("RAPP1_FACADE_HOST", DEFAULT_HOST)
    if host != DEFAULT_HOST:
        raise ValueError("RAPP1_FACADE_HOST must equal 127.0.0.1")

    port_text = env.get("RAPP1_FACADE_PORT", str(DEFAULT_PORT))
    try:
        port = int(port_text)
    except (TypeError, ValueError) as exc:
        raise ValueError("RAPP1_FACADE_PORT must be an integer") from exc
    if not 1 <= port <= 65535:
        raise ValueError("RAPP1_FACADE_PORT must be between 1 and 65535")
    if port == GRAIL_PORT:
        raise ValueError("the RAPP/1 facade must not use the grail port")

    configured_path = env.get("RAPP1_FACADE_DB")
    database_path = (
        Path(configured_path).expanduser()
        if configured_path
        else default_database_path(home)
    )
    return RuntimeConfig(host=host, port=port, database_path=database_path)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _json_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _http_response(body: bytes, status: int) -> Response:
    return Response(body, status=status, content_type="application/json")


def _error_body(code: str) -> bytes:
    if code not in PENDING_REGISTRY_ERROR_CODES:
        raise ValueError(f"unknown pending error code: {code}")
    return _json_bytes({"error": {"code": code, "step": None}})


def _error_response(code: str) -> Response:
    return _http_response(_error_body(code), 422)


def _parse_request() -> tuple[str, str | None, str | None]:
    if request.mimetype != "application/json":
        raise FacadeRefusal("malformed-request")
    content_length = request.content_length
    if content_length is not None and (
        content_length < 0 or content_length > MAX_RAW_REQUEST_BYTES
    ):
        raise FacadeRefusal("malformed-request")
    try:
        raw = request.stream.read(MAX_RAW_REQUEST_BYTES + 1)
    except RequestEntityTooLarge as exc:
        raise FacadeRefusal("malformed-request") from exc
    if len(raw) > MAX_RAW_REQUEST_BYTES:
        raise FacadeRefusal("malformed-request")
    if not raw:
        raise FacadeRefusal("malformed-request")
    try:
        data = strict_loads(raw)
    except (TypeError, ValueError, RecursionError) as exc:
        raise FacadeRefusal("malformed-request") from exc
    if type(data) is not dict:
        raise FacadeRefusal("malformed-request")

    user_input = data.get("user_input")
    if type(user_input) is not str:
        raise FacadeRefusal("malformed-request")

    if "session_id" in data and type(data["session_id"]) is not str:
        raise FacadeRefusal("malformed-request")
    if "idempotency_key" in data and type(data["idempotency_key"]) is not str:
        raise FacadeRefusal("malformed-request")

    try:
        user_input.encode("utf-8")
        session_id = data.get("session_id")
        idempotency_key = data.get("idempotency_key")
        if session_id is not None:
            session_id.encode("utf-8")
        if idempotency_key is not None:
            idempotency_key.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise FacadeRefusal("malformed-request") from exc

    return user_input, session_id, idempotency_key


def _request_fingerprint(
    user_input: str,
    session_id: str | None,
) -> bytes:
    semantic_request = {"user_input": user_input}
    if session_id is not None:
        semantic_request["session_id"] = session_id
    return canonical_bytes(semantic_request)


class FacadeStore:
    _SCHEMA_VERSION = 3

    def __init__(self, database_path: Path | str) -> None:
        self.path = Path(database_path).expanduser()
        self._coordinator = _coordinator_for(self.path)
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._initialize()
        try:
            self.path.chmod(0o600)
        except OSError:
            pass

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            str(self.path), timeout=5.0, isolation_level=None
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        connection = self._connect()
        try:
            connection.execute("PRAGMA journal_mode = WAL")
        finally:
            connection.close()

        with self._transaction() as connection:
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if version not in (0, 1, 2, self._SCHEMA_VERSION):
                raise RuntimeError(
                    f"unsupported RAPP/1 facade database version: {version}"
                )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_utc TEXT NOT NULL,
                    pending_token TEXT,
                    pending_since_utc TEXT,
                    CHECK (
                        (pending_token IS NULL AND pending_since_utc IS NULL)
                        OR
                        (pending_token IS NOT NULL AND pending_since_utc IS NOT NULL)
                    )
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS turns (
                    session_id TEXT NOT NULL,
                    turn_index INTEGER NOT NULL CHECK (turn_index > 0),
                    user_input TEXT NOT NULL,
                    response TEXT NOT NULL,
                    agent_logs_json TEXT NOT NULL,
                    completed_utc TEXT NOT NULL,
                    PRIMARY KEY (session_id, turn_index),
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS idempotency (
                    scope_kind TEXT NOT NULL
                        CHECK (scope_kind IN ('create', 'session')),
                    scope_session_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    state TEXT NOT NULL
                        CHECK (state IN ('pending', 'completed', 'refused')),
                    response_status INTEGER,
                    response_body BLOB,
                    request_canonical BLOB NOT NULL,
                    request_fingerprint_version INTEGER NOT NULL
                        CHECK (request_fingerprint_version IN (1, 2, 3)),
                    created_utc TEXT NOT NULL,
                    finished_utc TEXT,
                    PRIMARY KEY (
                        scope_kind, scope_session_id, idempotency_key
                    ),
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id),
                    CHECK (
                        (
                            state = 'pending'
                            AND response_status IS NULL
                            AND response_body IS NULL
                            AND finished_utc IS NULL
                        )
                        OR
                        (
                            state IN ('completed', 'refused')
                            AND response_status IN (200, 422)
                            AND response_body IS NOT NULL
                            AND finished_utc IS NOT NULL
                        )
                    ),
                    CHECK (
                        (scope_kind = 'create' AND scope_session_id = '')
                        OR
                        (
                            scope_kind = 'session'
                            AND scope_session_id = session_id
                        )
                    )
                )
                """
            )
            if version == 1:
                connection.execute(
                    """
                    ALTER TABLE idempotency
                    ADD COLUMN request_canonical BLOB
                    """
                )
            if version in (1, 2):
                connection.execute(
                    """
                    ALTER TABLE idempotency
                    ADD COLUMN request_fingerprint_version INTEGER NOT NULL
                        DEFAULT 1
                        CHECK (request_fingerprint_version IN (1, 2, 3))
                    """
                )
                connection.execute(
                    """
                    UPDATE idempotency
                    SET request_fingerprint_version =
                        CASE
                            WHEN request_canonical IS NULL THEN ?
                            ELSE ?
                        END
                    """,
                    (
                        FINGERPRINT_VERSION_UNBOUND,
                        FINGERPRINT_VERSION_LEGACY_JSON,
                    ),
                )
            if version in (0, 1, 2):
                connection.execute(
                    f"PRAGMA user_version = {self._SCHEMA_VERSION}"
                )

    @staticmethod
    def _stored_response(
        row: sqlite3.Row,
        scope: tuple[str, str, str],
    ) -> StoredResponse | PendingIdempotency:
        state = row["state"]
        if state == "pending":
            return PendingIdempotency(scope)
        stored_request = row["request_canonical"]
        fingerprint_version = row["request_fingerprint_version"]
        if stored_request is None:
            # v1 had no request binding. Its migration deliberately leaves NULL
            # as a legacy-unbound marker: terminal bytes replay unconditionally,
            # while pending work remains pending, so neither path re-executes.
            if fingerprint_version != FINGERPRINT_VERSION_UNBOUND:
                raise FacadeRefusal("facade-storage-refused")
        elif not isinstance(stored_request, (bytes, bytearray)):
            raise FacadeRefusal("facade-storage-refused")
        elif fingerprint_version not in (
            FINGERPRINT_VERSION_LEGACY_JSON,
            FINGERPRINT_VERSION_CANONICAL_SEMANTIC,
        ):
            raise FacadeRefusal("facade-storage-refused")
        status = row["response_status"]
        body = row["response_body"]
        if (
            state not in ("completed", "refused")
            or status not in (200, 422)
            or not isinstance(body, (bytes, bytearray))
        ):
            raise FacadeRefusal("facade-storage-refused")
        return StoredResponse(status=int(status), body=bytes(body))

    @staticmethod
    def _idempotency_row(
        connection: sqlite3.Connection,
        scope: tuple[str, str, str],
    ) -> sqlite3.Row | None:
        return connection.execute(
            """
            SELECT i.state, i.response_status, i.response_body,
                   i.request_canonical, i.request_fingerprint_version,
                   s.pending_token, s.pending_since_utc
            FROM idempotency AS i
            JOIN sessions AS s ON s.session_id = i.session_id
            WHERE i.scope_kind = ?
              AND i.scope_session_id = ?
              AND i.idempotency_key = ?
            """,
            scope,
        ).fetchone()

    def _read_idempotency_row(
        self, scope: tuple[str, str, str]
    ) -> sqlite3.Row | None:
        connection = self._connect()
        try:
            return self._idempotency_row(connection, scope)
        finally:
            connection.close()

    @staticmethod
    def _heartbeat_age_seconds(value: Any) -> float:
        if type(value) is not str:
            raise FacadeRefusal("facade-storage-refused")
        try:
            heartbeat = datetime.fromisoformat(value)
        except ValueError as exc:
            raise FacadeRefusal("facade-storage-refused") from exc
        if heartbeat.tzinfo is None or heartbeat.utcoffset() is None:
            raise FacadeRefusal("facade-storage-refused")
        return (datetime.now(timezone.utc) - heartbeat).total_seconds()

    def wait_for_terminal(
        self, pending: PendingIdempotency
    ) -> StoredResponse:
        scope = pending.scope
        while True:
            row = self._read_idempotency_row(scope)
            if row is None:
                raise FacadeRefusal("facade-storage-refused")
            stored = self._stored_response(row, scope)
            if isinstance(stored, StoredResponse):
                return stored

            with self._coordinator.condition:
                active_here = scope in self._coordinator.active_scopes
            if row["pending_token"] is None:
                raise FacadeRefusal("idempotency-in-progress")
            age = self._heartbeat_age_seconds(row["pending_since_utc"])
            if (
                not active_here
                and age >= IDEMPOTENCY_ORPHAN_AFTER_SECONDS
            ):
                raise FacadeRefusal("idempotency-in-progress")

            with self._coordinator.condition:
                self._coordinator.condition.wait(
                    timeout=IDEMPOTENCY_POLL_SECONDS
                )

    def _refresh_heartbeat(self, reservation: Reservation) -> bool:
        with self._transaction() as connection:
            updated = connection.execute(
                """
                UPDATE sessions
                SET pending_since_utc = ?
                WHERE session_id = ? AND pending_token = ?
                """,
                (_utc_now(), reservation.session_id, reservation.token),
            )
            return updated.rowcount == 1

    @contextmanager
    def pending_activity(
        self, reservation: Reservation
    ) -> Iterator[None]:
        scope = reservation.idempotency_scope
        if scope is None:
            yield
            return

        stop = threading.Event()
        with self._coordinator.condition:
            self._coordinator.active_scopes.add(scope)
            self._coordinator.condition.notify_all()

        def heartbeat() -> None:
            while not stop.wait(IDEMPOTENCY_HEARTBEAT_SECONDS):
                try:
                    if not self._refresh_heartbeat(reservation):
                        return
                except sqlite3.Error:
                    continue

        thread = threading.Thread(
            target=heartbeat,
            name="rapp1-idempotency-heartbeat",
            daemon=True,
        )
        thread.start()
        try:
            yield
        finally:
            stop.set()
            thread.join(timeout=IDEMPOTENCY_HEARTBEAT_SECONDS * 2)
            with self._coordinator.condition:
                self._coordinator.active_scopes.discard(scope)
                self._coordinator.condition.notify_all()

    def reserve(
        self,
        supplied_session_id: str | None,
        idempotency_key: str | None,
        request_fingerprint: bytes,
    ) -> Reservation | StoredResponse | PendingIdempotency:
        with self._transaction() as connection:
            scope: tuple[str, str, str] | None = None
            if supplied_session_id is None:
                if idempotency_key is not None:
                    scope = ("create", "", idempotency_key)
                    existing = self._idempotency_row(connection, scope)
                    if existing is not None:
                        return self._stored_response(existing, scope)
                session_id = str(uuid.uuid4())
                token = str(uuid.uuid4())
                now = _utc_now()
                connection.execute(
                    """
                    INSERT INTO sessions (
                        session_id, created_utc, pending_token, pending_since_utc
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (session_id, now, token, now),
                )
            else:
                session_id = supplied_session_id
                session = connection.execute(
                    """
                    SELECT pending_token
                    FROM sessions
                    WHERE session_id = ?
                    """,
                    (session_id,),
                ).fetchone()
                if session is None:
                    raise FacadeRefusal("unknown-session")
                if idempotency_key is not None:
                    scope = ("session", session_id, idempotency_key)
                    existing = self._idempotency_row(connection, scope)
                    if existing is not None:
                        return self._stored_response(existing, scope)
                if session["pending_token"] is not None:
                    raise FacadeRefusal("session-in-progress")
                token = str(uuid.uuid4())
                now = _utc_now()
                updated = connection.execute(
                    """
                    UPDATE sessions
                    SET pending_token = ?, pending_since_utc = ?
                    WHERE session_id = ? AND pending_token IS NULL
                    """,
                    (token, now, session_id),
                )
                if updated.rowcount != 1:
                    raise FacadeRefusal("session-in-progress")

            if scope is not None:
                connection.execute(
                    """
                    INSERT INTO idempotency (
                        scope_kind, scope_session_id, idempotency_key,
                        session_id, state, request_canonical,
                        request_fingerprint_version, created_utc
                    ) VALUES (?, ?, ?, ?, 'pending', ?, ?, ?)
                    """,
                    (
                        *scope,
                        session_id,
                        sqlite3.Binary(request_fingerprint),
                        FINGERPRINT_VERSION_CANONICAL_SEMANTIC,
                        _utc_now(),
                    ),
                )

            rows = connection.execute(
                """
                SELECT user_input, response
                FROM turns
                WHERE session_id = ?
                ORDER BY turn_index
                """,
                (session_id,),
            ).fetchall()
            messages: list[dict[str, str]] = []
            for row in rows:
                messages.append({"role": "user", "content": row["user_input"]})
                messages.append({"role": "assistant", "content": row["response"]})

            return Reservation(
                session_id=session_id,
                token=token,
                messages=tuple(messages),
                idempotency_scope=scope,
                request_fingerprint=request_fingerprint,
            )

    @staticmethod
    def _require_pending_session(
        connection: sqlite3.Connection, reservation: Reservation
    ) -> None:
        row = connection.execute(
            """
            SELECT pending_token
            FROM sessions
            WHERE session_id = ?
            """,
            (reservation.session_id,),
        ).fetchone()
        if row is None or row["pending_token"] != reservation.token:
            raise RuntimeError("session reservation is not pending")

    def complete(
        self,
        reservation: Reservation,
        *,
        user_input: str,
        response_text: str,
        response_body: bytes,
    ) -> None:
        with self._transaction() as connection:
            self._require_pending_session(connection, reservation)
            next_turn = connection.execute(
                """
                SELECT COALESCE(MAX(turn_index), 0) + 1
                FROM turns
                WHERE session_id = ?
                """,
                (reservation.session_id,),
            ).fetchone()[0]
            now = _utc_now()
            connection.execute(
                """
                INSERT INTO turns (
                    session_id, turn_index, user_input, response,
                    agent_logs_json, completed_utc
                ) VALUES (?, ?, ?, ?, '[]', ?)
                """,
                (
                    reservation.session_id,
                    next_turn,
                    user_input,
                    response_text,
                    now,
                ),
            )
            if reservation.idempotency_scope is not None:
                updated = connection.execute(
                    """
                    UPDATE idempotency
                    SET state = 'completed',
                        response_status = 200,
                        response_body = ?,
                        finished_utc = ?
                    WHERE scope_kind = ?
                      AND scope_session_id = ?
                      AND idempotency_key = ?
                      AND session_id = ?
                      AND state = 'pending'
                      AND request_canonical = ?
                      AND request_fingerprint_version = ?
                    """,
                    (
                        sqlite3.Binary(response_body),
                        now,
                        *reservation.idempotency_scope,
                        reservation.session_id,
                        sqlite3.Binary(reservation.request_fingerprint),
                        FINGERPRINT_VERSION_CANONICAL_SEMANTIC,
                    ),
                )
                if updated.rowcount != 1:
                    raise RuntimeError("idempotency reservation is not pending")
            updated = connection.execute(
                """
                UPDATE sessions
                SET pending_token = NULL, pending_since_utc = NULL
                WHERE session_id = ? AND pending_token = ?
                """,
                (reservation.session_id, reservation.token),
            )
            if updated.rowcount != 1:
                raise RuntimeError("session reservation changed")
        with self._coordinator.condition:
            self._coordinator.condition.notify_all()

    def refuse(
        self, reservation: Reservation, *, response_body: bytes
    ) -> None:
        with self._transaction() as connection:
            self._require_pending_session(connection, reservation)
            now = _utc_now()
            if reservation.idempotency_scope is not None:
                updated = connection.execute(
                    """
                    UPDATE idempotency
                    SET state = 'refused',
                        response_status = 422,
                        response_body = ?,
                        finished_utc = ?
                    WHERE scope_kind = ?
                      AND scope_session_id = ?
                      AND idempotency_key = ?
                      AND session_id = ?
                      AND state = 'pending'
                      AND request_canonical = ?
                      AND request_fingerprint_version = ?
                    """,
                    (
                        sqlite3.Binary(response_body),
                        now,
                        *reservation.idempotency_scope,
                        reservation.session_id,
                        sqlite3.Binary(reservation.request_fingerprint),
                        FINGERPRINT_VERSION_CANONICAL_SEMANTIC,
                    ),
                )
                if updated.rowcount != 1:
                    raise RuntimeError("idempotency reservation is not pending")
            updated = connection.execute(
                """
                UPDATE sessions
                SET pending_token = NULL, pending_since_utc = NULL
                WHERE session_id = ? AND pending_token = ?
                """,
                (reservation.session_id, reservation.token),
            )
            if updated.rowcount != 1:
                raise RuntimeError("session reservation changed")
        with self._coordinator.condition:
            self._coordinator.condition.notify_all()


def _strict_inference_text(result: Any) -> str:
    if type(result) is not dict:
        raise ValueError("invalid inference result")

    choices = result.get("choices")
    if type(choices) is not list or len(choices) != 1:
        raise ValueError("inference must return exactly one choice")
    choice = choices[0]
    if type(choice) is not dict or choice.get("finish_reason") != "stop":
        raise ValueError("inference did not stop cleanly")
    message = choice.get("message")
    if type(message) is not dict or message.get("role") != "assistant":
        raise ValueError("invalid assistant message")
    if "tool_calls" in message or "function_call" in message:
        raise ValueError("tool-bearing inference is refused")
    if message.get("refusal") is not None:
        raise ValueError("upstream inference refused")
    content = message.get("content")
    if type(content) is not str or not content.strip():
        raise ValueError("inference returned no text")
    content.encode("utf-8")
    return content


def _is_allowed_browser_origin(origin: str) -> bool:
    try:
        parsed = urlsplit(origin)
        _ = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme in {"http", "https"}
        and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        and parsed.username is None
        and parsed.password is None
        and parsed.path in {"", "/"}
        and not parsed.query
        and not parsed.fragment
    )


def create_app(
    *,
    inference: Inference,
    database_path: Path | str | None = None,
) -> Flask:
    if not callable(inference):
        raise TypeError("inference must be callable")
    store = FacadeStore(
        database_path if database_path is not None else default_database_path()
    )
    app = Flask("rapp1_facade", static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = MAX_RAW_REQUEST_BYTES
    app.extensions["rapp1_facade_store"] = store

    @app.after_request
    def allow_loopback_ui(response: Response) -> Response:
        origin = request.headers.get("Origin")
        if request.path == "/chat" and origin and _is_allowed_browser_origin(origin):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers.add("Vary", "Origin")
        return response

    @app.route("/chat", methods=["OPTIONS"])
    def chat_preflight() -> Response:
        origin = request.headers.get("Origin", "")
        if (
            not _is_allowed_browser_origin(origin)
            or request.headers.get("Access-Control-Request-Method") != "POST"
        ):
            return Response(status=403)
        requested_headers = {
            value.strip().lower()
            for value in request.headers.get(
                "Access-Control-Request-Headers", ""
            ).split(",")
            if value.strip()
        }
        if not requested_headers.issubset({"content-type"}):
            return Response(status=403)
        response = Response(status=204)
        response.headers["Access-Control-Allow-Methods"] = "POST"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    @app.post("/chat")
    def chat() -> Response:
        origin = request.headers.get("Origin")
        if origin and not _is_allowed_browser_origin(origin):
            return _error_response("malformed-request")
        try:
            user_input, session_id, idempotency_key = _parse_request()
        except FacadeRefusal as refusal:
            return _error_response(refusal.code)

        try:
            request_fingerprint = _request_fingerprint(
                user_input,
                session_id,
            )
            reserved = store.reserve(
                session_id,
                idempotency_key,
                request_fingerprint,
            )
            if isinstance(reserved, PendingIdempotency):
                reserved = store.wait_for_terminal(reserved)
        except FacadeRefusal as refusal:
            return _error_response(refusal.code)
        except Exception:
            return _error_response("facade-storage-refused")

        if isinstance(reserved, StoredResponse):
            return _http_response(reserved.body, reserved.status)

        with store.pending_activity(reserved):
            messages = [
                *reserved.messages,
                {"role": "user", "content": user_input},
            ]
            try:
                raw_result = inference(messages)
                response_text = unicodedata.normalize(
                    "NFC", _strict_inference_text(raw_result)
                )
            except Exception:
                refusal_body = _error_body("inference-refused")
                try:
                    store.refuse(reserved, response_body=refusal_body)
                except Exception:
                    return _error_response("facade-storage-refused")
                return _http_response(refusal_body, 422)

            response_body = _json_bytes(
                {
                    "response": response_text,
                    "agent_logs": [],
                    "session_id": reserved.session_id,
                }
            )
            try:
                store.complete(
                    reserved,
                    user_input=user_input,
                    response_text=response_text,
                    response_body=response_body,
                )
            except Exception:
                return _error_response("facade-storage-refused")
            return _http_response(response_body, 200)

    @app.get("/health")
    def health() -> Response:
        return _http_response(
            _json_bytes(
                {
                    "status": "pre-acceptance",
                    "authenticated": False,
                    "fully_conformant": False,
                }
            ),
            200,
        )

    @app.errorhandler(RequestEntityTooLarge)
    def request_too_large(_: RequestEntityTooLarge) -> Response:
        return _error_response("malformed-request")

    return app
