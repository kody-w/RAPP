"""Target-owned, pre-acceptance RAPP/1 ``/chat`` facade.

This module is intentionally independent of the immutable brainstem Flask app.
The injected inference boundary receives messages only; the production launcher
privately calls the pinned grail with ``tools=None``.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Sequence

from flask import Flask, Response, request
from werkzeug.exceptions import RequestEntityTooLarge


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7073
GRAIL_PORT = 7071
MAX_REQUEST_BYTES = 1_048_576

# These names are candidates awaiting the authenticated RAPP/1 section 13
# owner registry. They are explicitly NOT registered error codes.
PENDING_REGISTRY_ERROR_CODES = (
    "malformed-request",
    "unknown-session",
    "idempotency-conflict",
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
class Reservation:
    session_id: str
    token: str
    messages: tuple[dict[str, str], ...]
    idempotency_scope: tuple[str, str, str] | None
    request_canonical: bytes


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
    if not host:
        raise ValueError("RAPP1_FACADE_HOST must not be empty")

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


def _reject_duplicate_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, member in pairs:
        if key in value:
            raise ValueError("duplicate JSON member")
        value[key] = member
    return value


def _reject_non_json_constant(value: str) -> None:
    raise ValueError(f"non-JSON numeric constant: {value}")


def _parse_request() -> tuple[str, str | None, str | None]:
    if request.mimetype != "application/json":
        raise FacadeRefusal("malformed-request")
    raw = request.get_data(cache=False)
    if not raw:
        raise FacadeRefusal("malformed-request")
    try:
        text = raw.decode("utf-8")
        data = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_members,
            parse_constant=_reject_non_json_constant,
        )
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        raise FacadeRefusal("malformed-request") from exc
    if type(data) is not dict:
        raise FacadeRefusal("malformed-request")

    user_input = data.get("user_input")
    if type(user_input) is not str or not user_input.strip():
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


class FacadeStore:
    _SCHEMA_VERSION = 2

    def __init__(self, database_path: Path | str) -> None:
        self.path = Path(database_path).expanduser()
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
            if version not in (0, 1, self._SCHEMA_VERSION):
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
            if version in (0, 1):
                connection.execute(
                    f"PRAGMA user_version = {self._SCHEMA_VERSION}"
                )

    @staticmethod
    def _stored_response(
        row: sqlite3.Row, request_canonical: bytes
    ) -> StoredResponse:
        stored_request = row["request_canonical"]
        if not isinstance(stored_request, (bytes, bytearray)):
            raise FacadeRefusal("facade-storage-refused")
        if bytes(stored_request) != request_canonical:
            raise FacadeRefusal("idempotency-conflict")
        state = row["state"]
        if state == "pending":
            raise FacadeRefusal("idempotency-in-progress")
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
            SELECT state, response_status, response_body, request_canonical
            FROM idempotency
            WHERE scope_kind = ?
              AND scope_session_id = ?
              AND idempotency_key = ?
            """,
            scope,
        ).fetchone()

    def reserve(
        self,
        supplied_session_id: str | None,
        idempotency_key: str | None,
        request_canonical: bytes,
    ) -> Reservation | StoredResponse:
        with self._transaction() as connection:
            scope: tuple[str, str, str] | None = None
            if supplied_session_id is None:
                if idempotency_key is not None:
                    scope = ("create", "", idempotency_key)
                    existing = self._idempotency_row(connection, scope)
                    if existing is not None:
                        return self._stored_response(
                            existing, request_canonical
                        )
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
                        return self._stored_response(
                            existing, request_canonical
                        )
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
                        session_id, state, request_canonical, created_utc
                    ) VALUES (?, ?, ?, ?, 'pending', ?, ?)
                    """,
                    (
                        *scope,
                        session_id,
                        sqlite3.Binary(request_canonical),
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
                request_canonical=request_canonical,
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
                    """,
                    (
                        sqlite3.Binary(response_body),
                        now,
                        *reservation.idempotency_scope,
                        reservation.session_id,
                        sqlite3.Binary(reservation.request_canonical),
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
                    """,
                    (
                        sqlite3.Binary(response_body),
                        now,
                        *reservation.idempotency_scope,
                        reservation.session_id,
                        sqlite3.Binary(reservation.request_canonical),
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
    app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_BYTES
    app.extensions["rapp1_facade_store"] = store

    @app.post("/chat")
    def chat() -> Response:
        try:
            user_input, session_id, idempotency_key = _parse_request()
        except FacadeRefusal as refusal:
            return _error_response(refusal.code)

        try:
            canonical_request = {"user_input": user_input}
            if session_id is not None:
                canonical_request["session_id"] = session_id
            reserved = store.reserve(
                session_id,
                idempotency_key,
                _json_bytes(canonical_request),
            )
        except FacadeRefusal as refusal:
            return _error_response(refusal.code)
        except Exception:
            return _error_response("facade-storage-refused")

        if isinstance(reserved, StoredResponse):
            return _http_response(reserved.body, reserved.status)

        messages = [*reserved.messages, {"role": "user", "content": user_input}]
        try:
            raw_result = inference(messages)
            response_text = _strict_inference_text(raw_result)
        except Exception:
            refusal_body = _error_body("inference-refused")
            try:
                store.refuse(reserved, response_body=refusal_body)
            except Exception:
                pass
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
