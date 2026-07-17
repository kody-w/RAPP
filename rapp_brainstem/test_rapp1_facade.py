from __future__ import annotations

import copy
import json
import shutil
import threading
import uuid
from pathlib import Path
from typing import Any, Sequence

import pytest

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
    app = make_app(test_dir / "facade.sqlite3", inference)

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
            b'{"user_input":"ok","unknown":NaN}',
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
