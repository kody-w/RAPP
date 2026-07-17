from __future__ import annotations

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

from rapp_brainstem.rapp1_facade import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    GRAIL_PORT,
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
    assert response.data == (
        f'{{"error":{{"code":"{code}","step":null}}}}'.encode()
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


def test_creation_idempotency_is_global_byte_equivalent_and_conflict_safe(
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
        conflict = post_json(
            client,
            {"user_input": "changed", "idempotency_key": "create-key"},
        )

    assert first.status_code == duplicate.status_code == 200
    assert duplicate.data == first.data
    assert duplicate.get_json()["session_id"] == first.get_json()["session_id"]
    assert_error(conflict, "idempotency-conflict")
    assert len(inference.calls) == 1
    with sqlite3.connect(database) as connection:
        stored = connection.execute(
            """
            SELECT request_canonical
            FROM idempotency
            WHERE scope_kind = 'create' AND idempotency_key = 'create-key'
            """
        ).fetchone()[0]
    assert stored == canonical_bytes(
        {"user_input": "original", "idempotency_key": "create-key"}
    )


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
        conflict_a = post_json(
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
    assert_error(conflict_a, "idempotency-conflict")
    assert first_b.status_code == 200
    assert len(inference.calls) == 4
    assert inference.calls[-1][0][-1]["content"] == "turn-b"


def test_concurrent_duplicate_runs_inference_once(test_dir):
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
    app = make_app(database, inference)
    first_result: dict[str, Any] = {}

    def send_first() -> None:
        with app.test_client() as client:
            first_result["response"] = post_json(
                client,
                {
                    "user_input": "concurrent",
                    "session_id": session_id,
                    "idempotency_key": "same",
                },
            )

    thread = threading.Thread(target=send_first)
    thread.start()
    assert inference.started.wait(timeout=5)
    try:
        with app.test_client() as client:
            duplicate = post_json(
                client,
                {
                    "user_input": "concurrent",
                    "session_id": session_id,
                    "idempotency_key": "same",
                },
            )
        assert_error(duplicate, "idempotency-in-progress")
    finally:
        inference.release.set()
        thread.join(timeout=5)

    assert not thread.is_alive()
    assert first_result["response"].status_code == 200
    assert inference.calls == 1


def test_crash_leaves_pending_reservation_that_fails_closed(test_dir):
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
        (b'{"user_input":"  "}', "application/json"),
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
def test_malformed_and_empty_requests_are_exact_422(
    test_dir, body, content_type
):
    inference = RecordingInference()
    app = make_app(test_dir / "facade.sqlite3", inference)

    with app.test_client() as client:
        response = client.post("/chat", data=body, content_type=content_type)

    assert_error(response, "malformed-request")
    assert inference.calls == []


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
        legacy_marker = connection.execute(
            """
            SELECT request_canonical
            FROM idempotency
            WHERE idempotency_key = 'legacy-key'
            """
        ).fetchone()[0]
    finally:
        connection.close()
    assert version == 2
    assert legacy_marker is None


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
            "RAPP1_FACADE_HOST": "127.0.0.2",
            "RAPP1_FACADE_PORT": "9001",
            "RAPP1_FACADE_DB": str(test_dir / "custom.sqlite3"),
        }
    )
    assert custom.host == "127.0.0.2"
    assert custom.port == 9001
    assert custom.database_path == test_dir / "custom.sqlite3"
    with pytest.raises(ValueError):
        runtime_config({"RAPP1_FACADE_PORT": str(GRAIL_PORT)})

    assert set(PENDING_REGISTRY_ERROR_CODES) == {
        "malformed-request",
        "unknown-session",
        "idempotency-conflict",
        "idempotency-in-progress",
        "session-in-progress",
        "inference-refused",
        "facade-storage-refused",
    }


def test_private_production_boundary_forces_tools_none(monkeypatch):
    from rapp_brainstem import run_rapp1_facade as launcher

    calls = []

    def pinned_call(messages, tools):
        calls.append((messages, tools))
        return completion("private"), "fake-model"

    monkeypatch.setattr(launcher, "_grail_call", pinned_call)
    messages = [{"role": "user", "content": "hello"}]
    result = launcher._private_grail_inference(messages)

    assert result == completion("private")
    assert calls == [(messages, None)]
    assert not hasattr(launcher, "app")
