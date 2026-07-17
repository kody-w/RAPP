from __future__ import annotations

import ast
import copy
import json
import shutil
import sqlite3
import threading
import uuid
from pathlib import Path
from typing import Any, Sequence

import pytest
from rapp1_core import canonical_bytes
from rapp1_core.canonical import MAX_JSON_DEPTH

import rapp_brainstem.rapp1_facade as facade_module
from rapp_brainstem.rapp1_facade import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    FINGERPRINT_VERSION_CANONICAL_SEMANTIC,
    FINGERPRINT_VERSION_UNBOUND,
    GRAIL_PORT,
    MAX_RAW_REQUEST_BYTES,
    PENDING_REGISTRY_ERROR_CODES,
    create_app,
    runtime_config,
)


def completion(text: str) -> dict[str, Any]:
    return {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": text},
            }
        ]
    }


class RecordingInference:
    def __init__(self) -> None:
        self.calls: list[tuple[list[dict[str, str]], None]] = []
        self._lock = threading.Lock()

    def __call__(
        self,
        messages: Sequence[dict[str, str]],
        tools: None = None,
    ) -> dict[str, Any]:
        assert tools is None
        with self._lock:
            copied = copy.deepcopy(list(messages))
            self.calls.append((copied, tools))
        return completion(f"reply:{copied[-1]['content']}")


@pytest.fixture
def test_dir():
    root = Path(__file__).resolve().parent / ".rapp1-facade-test-data"
    path = root / str(uuid.uuid4())
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
        try:
            root.rmdir()
        except OSError:
            pass


def make_app(database: Path, inference: Any):
    app = create_app(inference=inference, database_path=database)
    app.config["TESTING"] = True
    return app


def post_json(client, value: dict[str, Any]):
    return client.post(
        "/chat",
        data=json.dumps(value, separators=(",", ":")),
        content_type="application/json",
    )


def assert_error(response, code: str) -> None:
    assert response.status_code == 422
    assert response.get_json() == {"error": {"code": code, "step": None}}


def mark_pending_orphaned(database: Path) -> None:
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            UPDATE sessions
            SET pending_since_utc = '2000-01-01T00:00:00+00:00'
            WHERE pending_token IS NOT NULL
            """
        )


def create_v1_completed_database(path: Path) -> bytes:
    response_body = (
        b'{"response":"legacy","agent_logs":[],"session_id":"legacy-session"}'
    )
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            """
            CREATE TABLE sessions (
                session_id TEXT PRIMARY KEY,
                created_utc TEXT NOT NULL,
                pending_token TEXT,
                pending_since_utc TEXT,
                CHECK (
                    (pending_token IS NULL AND pending_since_utc IS NULL)
                    OR
                    (
                        pending_token IS NOT NULL
                        AND pending_since_utc IS NOT NULL
                    )
                )
            );
            CREATE TABLE turns (
                session_id TEXT NOT NULL,
                turn_index INTEGER NOT NULL CHECK (turn_index > 0),
                user_input TEXT NOT NULL,
                response TEXT NOT NULL,
                agent_logs_json TEXT NOT NULL,
                completed_utc TEXT NOT NULL,
                PRIMARY KEY (session_id, turn_index),
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );
            CREATE TABLE idempotency (
                scope_kind TEXT NOT NULL
                    CHECK (scope_kind IN ('create', 'session')),
                scope_session_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                session_id TEXT NOT NULL,
                state TEXT NOT NULL
                    CHECK (state IN ('pending', 'completed', 'refused')),
                response_status INTEGER,
                response_body BLOB,
                created_utc TEXT NOT NULL,
                finished_utc TEXT,
                PRIMARY KEY (
                    scope_kind, scope_session_id, idempotency_key
                ),
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );
            PRAGMA user_version = 1;
            """
        )
        now = "2026-07-16T00:00:00+00:00"
        connection.execute(
            """
            INSERT INTO sessions (session_id, created_utc)
            VALUES ('legacy-session', ?)
            """,
            (now,),
        )
        connection.execute(
            """
            INSERT INTO idempotency (
                scope_kind, scope_session_id, idempotency_key,
                session_id, state, response_status, response_body,
                created_utc, finished_utc
            ) VALUES (
                'create', '', 'legacy-key', 'legacy-session',
                'completed', 200, ?, ?, ?
            )
            """,
            (sqlite3.Binary(response_body), now, now),
        )
        connection.commit()
    finally:
        connection.close()
    return response_body


def create_v2_completed_database(
    path: Path, *, transitional: bool = False
) -> tuple[bytes, bytes]:
    response_body = create_v1_completed_database(path)
    legacy_fingerprint = json.dumps(
        {
            "user_input": "legacy turn",
            "session_id": "legacy-session",
        },
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    if transitional:
        legacy_fingerprint = canonical_bytes(
            {
                "user_input": "legacy turn",
                "session_id": "legacy-session",
                "idempotency_key": "legacy-key",
            }
        )
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "ALTER TABLE idempotency ADD COLUMN request_canonical BLOB"
        )
        connection.execute(
            """
            UPDATE idempotency
            SET scope_kind = 'session',
                scope_session_id = 'legacy-session',
                request_canonical = ?
            WHERE idempotency_key = 'legacy-key'
            """,
            (sqlite3.Binary(legacy_fingerprint),),
        )
        connection.execute("PRAGMA user_version = 2")
        connection.commit()
    finally:
        connection.close()
    return response_body, legacy_fingerprint


def initialize_with_old_v2_logic(path: Path) -> None:
    """Reproduce the deployed v1→v2 migration that left old rows unbound."""
    connection = sqlite3.connect(path)
    try:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
        connection.execute(
            "ALTER TABLE idempotency ADD COLUMN request_canonical BLOB"
        )
        connection.execute("PRAGMA user_version = 2")
        connection.commit()
    finally:
        connection.close()


def nested_request(total_depth: int) -> bytes:
    nested_containers = total_depth - 1
    return (
        b'{"user_input":"depth","unknown":'
        + (b"[" * nested_containers)
        + b"0"
        + (b"]" * nested_containers)
        + b"}"
    )


def test_exact_success_contract_health_and_route_isolation(test_dir):
    inference = RecordingInference()
    app = make_app(test_dir / "facade.sqlite3", inference)

    with app.test_client() as client:
        response = post_json(client, {"user_input": "hello"})
        health = client.get("/health")
        assert client.get("/").status_code == 404

    assert response.status_code == 200
    payload = response.get_json()
    assert set(payload) == {"response", "agent_logs", "session_id"}
    assert type(payload["response"]) is str
    assert type(payload["agent_logs"]) is list
    assert all(type(item) is str for item in payload["agent_logs"])
    assert type(payload["session_id"]) is str
    assert payload["agent_logs"] == []
    assert inference.calls[0][1] is None

    assert health.get_json() == {
        "status": "pre-acceptance",
        "authenticated": False,
        "fully_conformant": False,
    }
    paths = {rule.rule for rule in app.url_map.iter_rules()}
    assert paths == {"/chat", "/health"}


def test_unknown_members_and_client_history_are_ignored(test_dir):
    inference = RecordingInference()
    app = make_app(test_dir / "facade.sqlite3", inference)
    request_value = {
        "user_input": "trusted input",
        "conversation_history": [
            {"role": "assistant", "content": "client-controlled poison"}
        ],
        "response": {"not": "a request field"},
        "unknown": [True, None, 4],
    }

    with app.test_client() as client:
        response = post_json(client, request_value)

    assert response.status_code == 200
    assert inference.calls == [
        ([{"role": "user", "content": "trusted input"}], None)
    ]


def test_server_owned_history_and_unknown_session(test_dir):
    inference = RecordingInference()
    app = make_app(test_dir / "facade.sqlite3", inference)

    with app.test_client() as client:
        first = post_json(client, {"user_input": "first"})
        session_id = first.get_json()["session_id"]
        second = post_json(
            client, {"user_input": "second", "session_id": session_id}
        )
        unknown = post_json(
            client,
            {"user_input": "never inferred", "session_id": "does-not-exist"},
        )

    assert second.status_code == 200
    assert inference.calls[1][0] == [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "reply:first"},
        {"role": "user", "content": "second"},
    ]
    assert_error(unknown, "unknown-session")
    assert len(inference.calls) == 2


def test_creation_idempotency_is_global_and_replays_original_terminal_bytes(
    test_dir,
):
    inference = RecordingInference()
    database = test_dir / "facade.sqlite3"
    app = make_app(database, inference)

    with app.test_client() as client:
        first = post_json(
            client,
            {
                "user_input": "original",
                "idempotency_key": "create-key",
                "ignored": "first",
            },
        )
        duplicate = post_json(
            client,
            {
                "user_input": "original",
                "idempotency_key": "create-key",
                "ignored": "changed but irrelevant",
            },
        )
        changed_retry = post_json(
            client,
            {"user_input": "changed", "idempotency_key": "create-key"},
        )

    assert first.status_code == duplicate.status_code == changed_retry.status_code == 200
    assert duplicate.data == first.data
    assert changed_retry.data == first.data
    assert duplicate.get_json()["session_id"] == first.get_json()["session_id"]
    assert len(inference.calls) == 1
    with sqlite3.connect(database) as connection:
        stored, fingerprint_version = connection.execute(
            """
            SELECT request_canonical, request_fingerprint_version
            FROM idempotency
            WHERE scope_kind = 'create' AND idempotency_key = 'create-key'
            """
        ).fetchone()
    assert stored == canonical_bytes({"user_input": "original"})
    assert fingerprint_version == FINGERPRINT_VERSION_CANONICAL_SEMANTIC


def test_existing_session_idempotency_is_scoped_by_session(test_dir):
    inference = RecordingInference()
    app = make_app(test_dir / "facade.sqlite3", inference)

    with app.test_client() as client:
        session_a = post_json(client, {"user_input": "create-a"}).get_json()[
            "session_id"
        ]
        session_b = post_json(client, {"user_input": "create-b"}).get_json()[
            "session_id"
        ]
        first_a = post_json(
            client,
            {
                "user_input": "turn-a",
                "session_id": session_a,
                "idempotency_key": "shared-key",
            },
        )
        duplicate_a = post_json(
            client,
            {
                "user_input": "turn-a",
                "session_id": session_a,
                "idempotency_key": "shared-key",
            },
        )
        changed_retry_a = post_json(
            client,
            {
                "user_input": "must-not-run",
                "session_id": session_a,
                "idempotency_key": "shared-key",
            },
        )
        first_b = post_json(
            client,
            {
                "user_input": "turn-b",
                "session_id": session_b,
                "idempotency_key": "shared-key",
            },
        )

    assert duplicate_a.data == first_a.data
    assert changed_retry_a.data == first_a.data
    assert first_b.status_code == 200
    assert len(inference.calls) == 4
    assert inference.calls[-1][0][-1]["content"] == "turn-b"


@pytest.mark.parametrize(
    "isolate_waiter",
    [False, True],
    ids=["process-condition", "durable-db-poll"],
)
def test_concurrent_duplicate_waits_and_replays_once(
    test_dir, isolate_waiter, monkeypatch
):
    monkeypatch.setattr(
        facade_module, "IDEMPOTENCY_HEARTBEAT_SECONDS", 0.01
    )
    monkeypatch.setattr(
        facade_module, "IDEMPOTENCY_ORPHAN_AFTER_SECONDS", 0.05
    )
    monkeypatch.setattr(
        facade_module, "IDEMPOTENCY_POLL_SECONDS", 0.005
    )
    database = test_dir / "facade.sqlite3"
    setup_inference = RecordingInference()
    setup_app = make_app(database, setup_inference)
    with setup_app.test_client() as client:
        session_id = post_json(client, {"user_input": "setup"}).get_json()[
            "session_id"
        ]

    class BlockingInference:
        def __init__(self) -> None:
            self.calls = 0
            self.started = threading.Event()
            self.release = threading.Event()

        def __call__(self, messages, tools=None):
            assert tools is None
            self.calls += 1
            self.started.set()
            assert self.release.wait(timeout=5)
            return completion("one execution")

    inference = BlockingInference()
    owner_app = make_app(database, inference)
    duplicate_inference = RecordingInference()
    duplicate_app = (
        make_app(database, duplicate_inference)
        if isolate_waiter
        else owner_app
    )
    if isolate_waiter:
        duplicate_store = duplicate_app.extensions["rapp1_facade_store"]
        duplicate_store._coordinator = type(duplicate_store._coordinator)()
    first_result: dict[str, Any] = {}
    duplicate_result: dict[str, Any] = {}
    duplicate_started = threading.Event()

    def send_first() -> None:
        with owner_app.test_client() as client:
            first_result["response"] = post_json(
                client,
                {
                    "user_input": "concurrent",
                    "session_id": session_id,
                    "idempotency_key": "same",
                },
            )

    def send_duplicate() -> None:
        duplicate_started.set()
        with duplicate_app.test_client() as client:
            duplicate_result["response"] = post_json(
                client,
                {
                    "user_input": "different content while pending",
                    "session_id": session_id,
                    "idempotency_key": "same",
                },
            )

    owner_thread = threading.Thread(target=send_first)
    owner_thread.start()
    assert inference.started.wait(timeout=5)
    duplicate_thread = threading.Thread(target=send_duplicate)
    duplicate_thread.start()
    assert duplicate_started.wait(timeout=5)
    duplicate_thread.join(timeout=0.15)
    assert duplicate_thread.is_alive()
    assert inference.calls == 1

    inference.release.set()
    owner_thread.join(timeout=5)
    duplicate_thread.join(timeout=5)

    assert not owner_thread.is_alive()
    assert not duplicate_thread.is_alive()
    original = first_result["response"]
    duplicate = duplicate_result["response"]
    assert original.status_code == duplicate.status_code == 200
    assert duplicate.data == original.data
    assert inference.calls == 1
    assert duplicate_inference.calls == []


def test_crash_leaves_pending_reservation_that_fails_closed(
    test_dir, monkeypatch
):
    monkeypatch.setattr(
        facade_module, "IDEMPOTENCY_ORPHAN_AFTER_SECONDS", 0.05
    )
    monkeypatch.setattr(
        facade_module, "IDEMPOTENCY_POLL_SECONDS", 0.005
    )
    database = test_dir / "facade.sqlite3"

    class SimulatedCrash(BaseException):
        pass

    class CrashingInference:
        def __init__(self) -> None:
            self.calls = 0

        def __call__(self, messages, tools=None):
            self.calls += 1
            raise SimulatedCrash()

    crashing = CrashingInference()
    first_app = make_app(database, crashing)
    with pytest.raises(SimulatedCrash):
        with first_app.test_client() as client:
            post_json(
                client,
                {"user_input": "crash", "idempotency_key": "crash-key"},
            )

    replacement = RecordingInference()
    recreated_app = make_app(database, replacement)
    with recreated_app.test_client() as client:
        duplicate = post_json(
            client,
            {"user_input": "crash", "idempotency_key": "crash-key"},
        )

    assert_error(duplicate, "idempotency-in-progress")
    assert crashing.calls == 1
    assert replacement.calls == []


@pytest.mark.parametrize(
    ("body", "content_type"),
    [
        (b"", "application/json"),
        (b"{", "application/json"),
        (b"[]", "application/json"),
        (b"{}", "application/json"),
        (b'{"user_input":null}', "application/json"),
        (b'{"user_input":3}', "application/json"),
        (
            b'{"user_input":"ok","session_id":null}',
            "application/json",
        ),
        (
            b'{"user_input":"ok","idempotency_key":false}',
            "application/json",
        ),
        (
            b'{"user_input":"one","user_input":"two"}',
            "application/json",
        ),
        (
            b'{"user_input":"ok","ignored":1,"ignored":2}',
            "application/json",
        ),
        (
            b'{"user_input":"ok","unknown":NaN}',
            "application/json",
        ),
        (
            b'{"user_input":"ok","unknown":9007199254740993}',
            "application/json",
        ),
        (
            b'{"user_input":"ok","unknown":"\\ud800"}',
            "application/json",
        ),
        (
            b'\xef\xbb\xbf{"user_input":"ok"}',
            "application/json",
        ),
        (
            b'{"user_input":"ok","unknown":"\xff"}',
            "application/json",
        ),
        (b'{"user_input":"ok"}', "text/plain"),
    ],
)
def test_malformed_requests_are_exact_422(
    test_dir, body, content_type
):
    inference = RecordingInference()
    app = make_app(test_dir / "facade.sqlite3", inference)

    with app.test_client() as client:
        response = client.post("/chat", data=body, content_type=content_type)

    assert_error(response, "malformed-request")
    assert inference.calls == []


@pytest.mark.parametrize("user_input", ["", " ", "\n\t"])
def test_empty_and_whitespace_user_input_is_preserved(test_dir, user_input):
    inference = RecordingInference()
    app = make_app(test_dir / "facade.sqlite3", inference)

    with app.test_client() as client:
        response = post_json(client, {"user_input": user_input})

    assert response.status_code == 200
    assert inference.calls == [
        ([{"role": "user", "content": user_input}], None)
    ]
    assert response.get_json()["response"] == f"reply:{user_input}"


def test_user_input_is_not_normalized_and_new_assistant_text_is_nfc(test_dir):
    decomposed = "Cafe\u0301"

    class DecomposedInference:
        def __init__(self):
            self.calls = []

        def __call__(self, messages):
            self.calls.append(copy.deepcopy(list(messages)))
            return completion(decomposed)

    inference = DecomposedInference()
    app = make_app(test_dir / "facade.sqlite3", inference)

    with app.test_client() as client:
        first = post_json(
            client,
            {
                "user_input": decomposed,
                "idempotency_key": "nfc-response",
            },
        )
        replay = post_json(
            client,
            {
                "user_input": "different retry content",
                "idempotency_key": "nfc-response",
            },
        )
        second = post_json(
            client,
            {
                "user_input": "next",
                "session_id": first.get_json()["session_id"],
            },
        )

    assert inference.calls[0][-1]["content"] == decomposed
    assert first.get_json()["response"] == "Café"
    assert replay.data == first.data
    assert inference.calls[1][1] == {"role": "assistant", "content": "Café"}
    assert second.status_code == 200


def test_oversized_request_is_exact_422(test_dir):
    inference = RecordingInference()
    app = make_app(test_dir / "facade.sqlite3", inference)

    with app.test_client() as client:
        response = client.post(
            "/chat",
            data=b'{"user_input":"' + (b"x" * 1_048_576) + b'"}',
            content_type="application/json",
        )

    assert_error(response, "malformed-request")
    assert inference.calls == []


def test_oversized_canonical_ignored_member_is_exact_422(test_dir):
    inference = RecordingInference()
    app = make_app(test_dir / "facade.sqlite3", inference)

    with app.test_client() as client:
        response = client.post(
            "/chat",
            data=(
                b'{"user_input":"ok","ignored":"'
                + (b"x" * 1_048_576)
                + b'"}'
            ),
            content_type="application/json",
        )

    assert_error(response, "malformed-request")
    assert inference.calls == []


@pytest.mark.parametrize(
    "body",
    [
        (b" " * MAX_RAW_REQUEST_BYTES) + b'{"user_input":"ok"}',
        b'{"user_input":"' + (b"x" * MAX_RAW_REQUEST_BYTES) + b'"}',
    ],
)
def test_raw_transport_cap_refuses_oversized_whitespace_and_body(
    test_dir, body
):
    inference = RecordingInference()
    app = make_app(test_dir / "facade.sqlite3", inference)

    with app.test_client() as client:
        response = client.post(
            "/chat",
            data=body,
            content_type="application/json",
        )

    assert_error(response, "malformed-request")
    assert inference.calls == []


@pytest.mark.parametrize("depth", [MAX_JSON_DEPTH + 1, 1100])
def test_deep_json_is_exact_malformed_422_before_inference(test_dir, depth):
    inference = RecordingInference()
    app = make_app(test_dir / "facade.sqlite3", inference)

    with app.test_client() as client:
        response = client.post(
            "/chat",
            data=nested_request(depth),
            content_type="application/json",
        )

    assert_error(response, "malformed-request")
    assert inference.calls == []


def test_json_at_maximum_depth_is_accepted(test_dir):
    inference = RecordingInference()
    app = make_app(test_dir / "facade.sqlite3", inference)

    with app.test_client() as client:
        response = client.post(
            "/chat",
            data=nested_request(MAX_JSON_DEPTH),
            content_type="application/json",
        )

    assert response.status_code == 200
    assert len(inference.calls) == 1


def test_upstream_error_is_terminal_and_replayed_without_retry(test_dir):
    class FailingInference:
        def __init__(self) -> None:
            self.calls = 0

        def __call__(self, messages, tools=None):
            assert tools is None
            self.calls += 1
            raise RuntimeError("upstream unavailable")

    inference = FailingInference()
    app = make_app(test_dir / "facade.sqlite3", inference)
    request_value = {"user_input": "hello", "idempotency_key": "failure"}

    with app.test_client() as client:
        first = post_json(client, request_value)
        duplicate = post_json(client, request_value)

    assert_error(first, "inference-refused")
    assert duplicate.data == first.data
    assert inference.calls == 1


def test_refusal_transition_failure_reports_storage_and_stays_pending(
    test_dir, monkeypatch
):
    database = test_dir / "facade.sqlite3"
    calls = 0

    def failing_inference(messages):
        nonlocal calls
        calls += 1
        raise RuntimeError("upstream unavailable")

    app = make_app(database, failing_inference)
    store = app.extensions["rapp1_facade_store"]

    def fail_refusal_transition(*args, **kwargs):
        raise sqlite3.OperationalError("simulated durable transition failure")

    monkeypatch.setattr(store, "refuse", fail_refusal_transition)
    request_value = {
        "user_input": "hello",
        "idempotency_key": "failed-transition",
    }
    with app.test_client() as client:
        first = post_json(client, request_value)
    mark_pending_orphaned(database)
    with app.test_client() as client:
        repeated = post_json(client, request_value)

    assert_error(first, "facade-storage-refused")
    assert_error(repeated, "idempotency-in-progress")
    assert calls == 1

    connection = sqlite3.connect(database)
    try:
        row = connection.execute(
            """
            SELECT state, response_status, response_body
            FROM idempotency
            WHERE scope_kind = 'create'
              AND scope_session_id = ''
              AND idempotency_key = 'failed-transition'
            """
        ).fetchone()
    finally:
        connection.close()
    assert row == ("pending", None, None)


def test_tool_bearing_or_non_strict_inference_is_refused_without_execution(
    test_dir,
):
    tool_was_run = False

    def forbidden_tool() -> None:
        nonlocal tool_was_run
        tool_was_run = True

    class ToolBearingInference:
        def __call__(self, messages, tools=None):
            assert tools is None
            return {
                "choices": [
                    {
                        "finish_reason": "tool_calls",
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call-1",
                                    "function": {
                                        "name": "forbidden_tool",
                                        "arguments": "{}",
                                    },
                                }
                            ],
                        },
                    }
                ]
            }

    assert callable(forbidden_tool)
    app = make_app(test_dir / "facade.sqlite3", ToolBearingInference())
    with app.test_client() as client:
        response = post_json(client, {"user_input": "use a tool"})

    assert_error(response, "inference-refused")
    assert tool_was_run is False


@pytest.mark.parametrize(
    "result",
    [
        {"choices": []},
        {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "one"},
                },
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "two"},
                },
            ]
        },
        {
            "choices": [
                {
                    "finish_reason": "length",
                    "message": {"role": "assistant", "content": "partial"},
                }
            ]
        },
        {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": 4},
                }
            ]
        },
    ],
)
def test_non_strict_choice_shapes_are_refused(test_dir, result):
    def inference(messages, tools=None):
        assert tools is None
        return result

    app = make_app(test_dir / "facade.sqlite3", inference)
    with app.test_client() as client:
        response = post_json(client, {"user_input": "hello"})
    assert_error(response, "inference-refused")


def test_sessions_and_completed_idempotency_survive_app_recreation(test_dir):
    database = test_dir / "facade.sqlite3"
    first_inference = RecordingInference()
    first_app = make_app(database, first_inference)
    request_value = {
        "user_input": "persistent",
        "idempotency_key": "persistent-key",
    }
    with first_app.test_client() as client:
        original = post_json(client, request_value)
    session_id = original.get_json()["session_id"]

    second_inference = RecordingInference()
    second_app = make_app(database, second_inference)
    with second_app.test_client() as client:
        duplicate = post_json(
            client,
            {
                "user_input": "persistent",
                "idempotency_key": "persistent-key",
            },
        )
        next_turn = post_json(
            client, {"user_input": "after restart", "session_id": session_id}
        )

    assert duplicate.data == original.data
    assert next_turn.status_code == 200
    assert len(second_inference.calls) == 1
    assert second_inference.calls[0][0] == [
        {"role": "user", "content": "persistent"},
        {"role": "assistant", "content": "reply:persistent"},
        {"role": "user", "content": "after restart"},
    ]


def test_v1_completed_idempotency_replays_unbound_terminal_bytes(test_dir):
    database = test_dir / "facade.sqlite3"
    legacy_body = create_v1_completed_database(database)
    inference = RecordingInference()
    app = make_app(database, inference)

    with app.test_client() as client:
        first = post_json(
            client,
            {
                "user_input": "different legacy request",
                "idempotency_key": "legacy-key",
            },
        )
        repeated = post_json(
            client,
            {
                "user_input": "another different request",
                "idempotency_key": "legacy-key",
            },
        )

    assert first.status_code == repeated.status_code == 200
    assert first.data == repeated.data == legacy_body
    assert inference.calls == []

    connection = sqlite3.connect(database)
    try:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        legacy_marker, fingerprint_version = connection.execute(
            """
            SELECT request_canonical, request_fingerprint_version
            FROM idempotency
            WHERE idempotency_key = 'legacy-key'
            """
        ).fetchone()
    finally:
        connection.close()
    assert version == 3
    assert legacy_marker is None
    assert fingerprint_version == FINGERPRINT_VERSION_UNBOUND


def test_v1_through_old_v2_preserves_unbound_completed_and_pending_rows(
    test_dir,
):
    database = test_dir / "facade-v1-v2-v3.sqlite3"
    legacy_body = create_v1_completed_database(database)
    now = "2026-07-16T00:00:00+00:00"
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            INSERT INTO sessions (session_id, created_utc)
            VALUES ('legacy-pending-session', ?)
            """,
            (now,),
        )
        connection.execute(
            """
            INSERT INTO idempotency (
                scope_kind, scope_session_id, idempotency_key,
                session_id, state, response_status, response_body,
                created_utc, finished_utc
            ) VALUES (
                'create', '', 'legacy-pending-key',
                'legacy-pending-session', 'pending', NULL, NULL, ?, NULL
            )
            """,
            (now,),
        )

    initialize_with_old_v2_logic(database)
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
        assert connection.execute(
            """
            SELECT COUNT(*)
            FROM idempotency
            WHERE request_canonical IS NULL
            """
        ).fetchone()[0] == 2

    inference = RecordingInference()
    app = make_app(database, inference)
    with app.test_client() as client:
        completed = post_json(
            client,
            {
                "user_input": "different request still replays terminal bytes",
                "idempotency_key": "legacy-key",
            },
        )
        pending = post_json(
            client,
            {
                "user_input": "pending request must not re-execute",
                "idempotency_key": "legacy-pending-key",
            },
        )

    assert completed.status_code == 200
    assert completed.data == legacy_body
    assert_error(pending, "idempotency-in-progress")
    assert inference.calls == []

    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
        rows = connection.execute(
            """
            SELECT idempotency_key, state, request_canonical,
                   request_fingerprint_version
            FROM idempotency
            ORDER BY idempotency_key
            """
        ).fetchall()
    assert rows == [
        (
            "legacy-key",
            "completed",
            None,
            FINGERPRINT_VERSION_UNBOUND,
        ),
        (
            "legacy-pending-key",
            "pending",
            None,
            FINGERPRINT_VERSION_UNBOUND,
        ),
    ]


@pytest.mark.parametrize("transitional", [False, True])
def test_v2_fingerprint_replays_for_changed_content_without_rewriting(
    test_dir, transitional
):
    database = test_dir / "facade-v2.sqlite3"
    legacy_body, legacy_fingerprint = create_v2_completed_database(
        database, transitional=transitional
    )
    inference = RecordingInference()
    app = make_app(database, inference)

    with app.test_client() as client:
        replay = post_json(
            client,
            {
                "user_input": "legacy turn",
                "session_id": "legacy-session",
                "idempotency_key": "legacy-key",
            },
        )
        changed_retry = post_json(
            client,
            {
                "user_input": "different turn",
                "session_id": "legacy-session",
                "idempotency_key": "legacy-key",
            },
        )

    assert replay.status_code == 200
    assert replay.data == legacy_body
    assert changed_retry.status_code == 200
    assert changed_retry.data == legacy_body
    assert inference.calls == []

    with sqlite3.connect(database) as connection:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        stored, fingerprint_version = connection.execute(
            """
            SELECT request_canonical, request_fingerprint_version
            FROM idempotency
            WHERE idempotency_key = 'legacy-key'
            """
        ).fetchone()
    assert version == 3
    assert stored == legacy_fingerprint
    assert fingerprint_version == 2


def test_v2_fingerprint_mismatch_still_replays_terminal_bytes(test_dir):
    database = test_dir / "facade-v2-conflict.sqlite3"
    legacy_body, legacy_fingerprint = create_v2_completed_database(database)
    inference = RecordingInference()
    app = make_app(database, inference)

    with app.test_client() as client:
        replay = post_json(
            client,
            {
                "user_input": "not the legacy turn",
                "session_id": "legacy-session",
                "idempotency_key": "legacy-key",
            },
        )

    assert replay.status_code == 200
    assert replay.data == legacy_body
    assert inference.calls == []
    with sqlite3.connect(database) as connection:
        stored, fingerprint_version = connection.execute(
            """
            SELECT request_canonical, request_fingerprint_version
            FROM idempotency
            WHERE idempotency_key = 'legacy-key'
            """
        ).fetchone()
    assert stored == legacy_fingerprint
    assert fingerprint_version == 2


def test_loopback_separate_port_and_external_default_store(test_dir):
    config = runtime_config({}, home=test_dir / "home")
    assert config.host == DEFAULT_HOST == "127.0.0.1"
    assert config.port == DEFAULT_PORT
    assert config.port != GRAIL_PORT
    assert config.database_path == (
        test_dir / "home" / ".brainstem" / "rapp1-facade.sqlite3"
    )

    custom = runtime_config(
        {
            "RAPP1_FACADE_HOST": DEFAULT_HOST,
            "RAPP1_FACADE_PORT": "9001",
            "RAPP1_FACADE_DB": str(test_dir / "custom.sqlite3"),
        }
    )
    assert custom.host == DEFAULT_HOST
    assert custom.port == 9001
    assert custom.database_path == test_dir / "custom.sqlite3"
    with pytest.raises(ValueError):
        runtime_config({"RAPP1_FACADE_PORT": str(GRAIL_PORT)})
    for exposed_host in ("0.0.0.0", "127.0.0.2", "localhost", "::1", ""):
        with pytest.raises(ValueError):
            runtime_config({"RAPP1_FACADE_HOST": exposed_host})

    assert set(PENDING_REGISTRY_ERROR_CODES) == {
        "malformed-request",
        "unknown-session",
        "idempotency-in-progress",
        "session-in-progress",
        "inference-refused",
        "facade-storage-refused",
    }


def test_chat_cors_is_limited_to_loopback_ui_origins(test_dir):
    inference = RecordingInference()
    app = make_app(test_dir / "facade.sqlite3", inference)

    with app.test_client() as client:
        preflight = client.options(
            "/chat",
            headers={
                "Origin": "http://127.0.0.1:7071",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        allowed = client.post(
            "/chat",
            data='{"user_input":""}',
            content_type="application/json",
            headers={"Origin": "http://127.0.0.1:7071"},
        )
        denied = client.post(
            "/chat",
            data='{"user_input":"must not run"}',
            content_type="application/json",
            headers={"Origin": "https://example.test"},
        )

    assert preflight.status_code == 204
    assert preflight.headers["Access-Control-Allow-Origin"] == (
        "http://127.0.0.1:7071"
    )
    assert preflight.headers["Access-Control-Allow-Methods"] == "POST"
    assert allowed.status_code == 200
    assert allowed.headers["Access-Control-Allow-Origin"] == (
        "http://127.0.0.1:7071"
    )
    assert_error(denied, "malformed-request")
    assert "Access-Control-Allow-Origin" not in denied.headers
    assert len(inference.calls) == 1


def test_production_launcher_defaults_to_exact_inference_refusal(test_dir):
    from rapp_brainstem import run_rapp1_facade as launcher

    config = runtime_config(
        {"RAPP1_FACADE_DB": str(test_dir / "refusing.sqlite3")}
    )
    app = launcher.create_production_app(config=config)
    app.config["TESTING"] = True
    with app.test_client() as client:
        response = post_json(client, {"user_input": "must fail closed"})
    assert_error(response, "inference-refused")


def test_production_launcher_accepts_only_explicit_inference_injection(test_dir):
    from rapp_brainstem import run_rapp1_facade as launcher

    inference = RecordingInference()
    config = runtime_config(
        {"RAPP1_FACADE_DB": str(test_dir / "injected.sqlite3")}
    )
    app = launcher.create_production_app(
        inference=inference,
        config=config,
    )
    app.config["TESTING"] = True
    with app.test_client() as client:
        response = post_json(client, {"user_input": "explicit"})

    assert response.status_code == 200
    assert response.get_json()["response"] == "reply:explicit"
    assert len(inference.calls) == 1


def test_production_launcher_has_no_grail_or_side_effect_coupling():
    from rapp_brainstem import run_rapp1_facade as launcher

    source = Path(launcher.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "brainstem" not in imported_modules
    assert "rapp_brainstem.brainstem" not in imported_modules
    for marker in (
        "call_copilot",
        ".copilot_token",
        ".copilot_session",
        "telemetry",
        "load_agents",
        "run_tool_calls",
        "subprocess",
    ):
        assert marker not in source
    assert not hasattr(launcher, "app")
