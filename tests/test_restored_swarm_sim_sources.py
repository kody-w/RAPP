from __future__ import annotations

import ast
import hashlib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

PROVENANCE = {
    "rapp_swarm/index.html": (
        "da6cb94985c9525b681bc20c2926656bdfdad565",
        "c2a34b63b697653a60612ad218a7e0f4caf11672",
        "cc4e23ce16003f911ec1ae5d6fd7ba210fbf9d08d560f11013b1ce9c48779aa5",
        9004,
    ),
    "rapp_swarm/build.sh": (
        "7bcc3d24ab3759605630625225fd190612c3d594",
        "ddcdf06751f7100511d53ba1e6a84c8ac6b803f9",
        "9f9a786d61f623e001923b89f6b83ca85549452a58dc41e357120c0afb157fb9",
        3976,
    ),
    "rapp_swarm/provision-twin.sh": (
        "925dee4a211965f2582e71a6d2ad75f60a54ea7d",
        "45c3888358470a2bf54d7b6a509d436cb3bc882e",
        "3a51eb5639180247a57e2e37a292c063ffe9f1f756b9810ffd346a54ddf6a468",
        8837,
    ),
    "rapp_swarm/provision-twin-lite.sh": (
        "4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6",
        "895ddfee47e57dd77a17d1bde4c9c7c80fbdfeab",
        "2be7348ff7cf7cd6a8bdc7243dd9afd047f86dc8ca8dcb898d1bd8828336ade5",
        6391,
    ),
    "rapp_swarm/function_app.py": (
        "7246d15d03809dd9df644270d920b1a5743d2515",
        "eeeb8ba5a04af38d1639ff42074381c7025d334f",
        "044f9e2c48032ec3d9199924d0bf609eb67eba6006739c87277ec249c5e196c3",
        49364,
    ),
    "rapp_swarm/twin-sim.sh": (
        "da6cb94985c9525b681bc20c2926656bdfdad565",
        "3e7c04a241c64035b97a6beccadf9f97ff1d3888",
        "19e60871021e7c1ee549ef7b42217f1bf1544d9f7790f5ea9da97aa284802bf4",
        33480,
    ),
    "rapp_swarm/twin-egg.sh": (
        "da6cb94985c9525b681bc20c2926656bdfdad565",
        "eafd5c92af6cc275bfd3e3c16ee4a9a95c43eb97",
        "faafb112ff6eb2a9d145479a018e2e5dbffa276185df6f87ddbb2c924d215a52",
        12904,
    ),
    "tools/test_brainstem_server.py": (
        "dd36590c8f5601c3ccf241844cdc9db54f7c420b",
        "9675cfc201e1aedffb6a3bf118bace07a8381897",
        "399f3d1e7227787846e347232ba35456e8c73ac5a685acdbcc59df9f830130e5",
        7441,
    ),
    "pages/tutorials/egg_hatcher_agent.py": (
        "f715eb3e6d4b473bbc34c472d3ad60cf6a2e144f",
        "be409f4f5c7d821e6573d182a34a663442177961",
        "bdd2b796aeac17d01a8c675acf8dfcf717aaa29601451aefccf7feffe6b8cf04",
        14962,
    ),
    "tools/front_door_specs.py": (
        "2efdc1f230ec939f0a1041caeb2813e5c4f59a1f",
        "f140e9ff2ff0fe9ed9b2a9c104cad6061b95a5bc",
        "c2a69e9be236a0bf76c356aadafd107a4e28d68ceb8ab601ba71b701b5fe65be",
        52574,
    ),
    "tools/sim/README.md": (
        "05f75bd40dd37f4590da6ebab28110d9a4b4094a",
        "9a966032e0c167ab26393f2ac784b6f676d76e27",
        "ada367799ca3a84c4b4d3275d4317357f2611b6113ae696f3ddbf0bcbf8d9a9b",
        6006,
    ),
    "tools/sim/loop_orchestrator.sh": (
        "55b91b9ecd182a3ce2057787f07c60e9aa3ca128",
        "9e345f817d06fe5fadfba60e24b7b3b28eea10b2",
        "4473c3abdb547b877570df80b063c440ad418228c95cd5c8c81346444e0589bc",
        3103,
    ),
    "tools/sim/observe.py": (
        "55b91b9ecd182a3ce2057787f07c60e9aa3ca128",
        "5539942887c866bfd0cdc087ad68cf77a0c39b8f",
        "b2f29a703daa82d5d738df2b31f2915a874dfae373dfa043d2a31b890c7c54db",
        15513,
    ),
    "tools/sim/plant_two_brainstems.py": (
        "40f00e1e669d4cd4bb97e2947a0b79739a9ba701",
        "aa15a82542aadee01afda555e7e3ac64e3e9436e",
        "676364e8d62d49965e3e1c588ef1352448a8e77491e9d21cfed110b3454a18f3",
        23169,
    ),
    "tools/sim/push_canvas.sh": (
        "8d089dc459f156fb214316db3383e2d95355261d",
        "31f09a46735aa0d058bd55fab22dc6a55d921698",
        "734670eaa877b78e3f913d2abc3235baab17ddb358d94181abc89c8ca367e88e",
        2353,
    ),
    "tools/sim/tick_twin.py": (
        "05f75bd40dd37f4590da6ebab28110d9a4b4094a",
        "70e1e36890238745729117d6d029640f06262d66",
        "2e1016a842336d7b5e2eff50d6d05b5ad6da33fd1590936ac18d24f6ee6d5405",
        16102,
    ),
    "cave/agents/cave_agent.py": (
        "cdf1aba25ba39c373ba4c738e7c6d421fff0cf86",
        "a3fdc75afccce81e16eda5c5e7e5f5963495eb96",
        "c8480ab51c661939d74b91e78f0c33c121034da114d5956494e3cf192db3c45b",
        10977,
    ),
}

PYTHON_SOURCES = {
    "rapp_swarm/function_app.py",
    "tools/test_brainstem_server.py",
    "pages/tutorials/egg_hatcher_agent.py",
    "tools/front_door_specs.py",
    "tools/sim/observe.py",
    "tools/sim/plant_two_brainstems.py",
    "tools/sim/tick_twin.py",
    "cave/agents/cave_agent.py",
}

LINE_COVERAGE_MINIMUM = {
    "rapp_swarm/index.html": 0.85,
}

REQUIRED_MARKERS = {
    "rapp_swarm/index.html": (
        "Azure Functions · Python 3.11",
        "Application Insights",
        "data-historical-href",
        "connect-src 'none'",
        "http://127.0.0.1:7073/chat",
    ),
    "rapp_swarm/build.sh": ("rm -rf \"$DEST\"", "rsync -a", "services/*_service.py"),
    "rapp_swarm/provision-twin.sh": (
        "az deployment group create",
        "func azure functionapp publish",
        "AZURE_OPENAI_API_KEY",
    ),
    "rapp_swarm/provision-twin-lite.sh": (
        "az storage account create",
        "az functionapp create",
        "func azure functionapp publish",
    ),
    "rapp_swarm/function_app.py": (
        "class Assistant",
        "def load_agents_from_folder",
        "def _get_openai_client",
        "def _historical_main",
    ),
    "rapp_swarm/twin-sim.sh": (
        "cmd_demo_book()",
        "cmd_demo_hero()",
        "http://127.0.0.1:7073/chat",
    ),
    "rapp_swarm/twin-egg.sh": (
        "cmd_pack()",
        "cmd_unpack()",
        "egg-manifest.json",
    ),
    "tools/test_brainstem_server.py": (
        "class _ThreadingServer",
        "def _build_handler",
        "http://127.0.0.1:7073/chat",
    ),
    "pages/tutorials/egg_hatcher_agent.py": (
        "def _historical_read_bytes",
        "def _historical_route_organism",
        "def _historical_route_rapplication",
        "def _historical_route_neighborhood",
        "def apply_hatch",
    ),
    "tools/front_door_specs.py": (
        "def _agent_spec",
        "def _rapplication_spec",
        "def _neighborhood_protocol",
    ),
    "tools/sim/README.md": (
        "Grail-driven autonomy",
        "Local-first survival",
        "Exact source provenance",
    ),
    "tools/sim/loop_orchestrator.sh": (
        "tick_twin.py",
        "push_canvas.sh",
        "historical_orchestrator_cycle",
    ),
    "tools/sim/observe.py": (
        "def compute_adjustments",
        "def check_antipatterns",
        "def sandbox_observation",
    ),
    "tools/sim/plant_two_brainstems.py": (
        "def plant_brainstem",
        "def plant_local_neighborhood",
        "def submit_piece",
    ),
    "tools/sim/push_canvas.sh": (
        "git add",
        "commit -q -m",
        "git push",
    ),
    "tools/sim/tick_twin.py": (
        "def build_prompt",
        "def validate_action",
        "def _historical_execute_action",
    ),
    "cave/agents/cave_agent.py": (
        "class CaveAgent",
        "def _historical_cave_root",
        "def _historical_load",
    ),
}

SHELL_DEFAULTS = {
    "rapp_swarm/build.sh": ("--apply",),
    "rapp_swarm/provision-twin.sh": ("--deploy",),
    "rapp_swarm/provision-twin-lite.sh": ("--deploy",),
    "rapp_swarm/twin-sim.sh": ("--run",),
    "rapp_swarm/twin-egg.sh": ("pack",),
    "tools/sim/loop_orchestrator.sh": ("--run",),
    "tools/sim/push_canvas.sh": ("--apply",),
}

PYTHON_DEFAULTS = (
    "rapp_swarm/function_app.py",
    "tools/test_brainstem_server.py",
    "pages/tutorials/egg_hatcher_agent.py",
    "tools/front_door_specs.py",
    "tools/sim/observe.py",
    "tools/sim/plant_two_brainstems.py",
    "tools/sim/tick_twin.py",
    "cave/agents/cave_agent.py",
)


def _git_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(("git", "show", f"{commit}:{path}"), cwd=ROOT)


def _git_blob(commit: str, path: str) -> str:
    return subprocess.check_output(
        ("git", "rev-parse", f"{commit}:{path}"),
        cwd=ROOT,
        text=True,
    ).strip()


def _symbols(source: bytes) -> set[str]:
    tree = ast.parse(source.decode("utf-8"))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }


def _line_coverage(source: bytes, restored: bytes) -> float:
    restored_text = " ".join(restored.decode("utf-8").split())
    lines = [
        " ".join(line.split())
        for line in source.decode("utf-8").splitlines()
        if len(" ".join(line.split())) >= 8
    ]
    return sum(line in restored_text for line in lines) / len(lines)


def _load_module(relative: str):
    path = ROOT / relative
    name = "restored_" + relative.replace("/", "_").replace(".", "_")
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _write_command_sentinels(directory: Path, marker: Path) -> None:
    directory.mkdir()
    commands = (
        "az", "func", "curl", "git", "gh", "python", "python3", "rm", "cp",
        "rsync", "mkdir", "zip", "unzip", "lsof", "xargs", "kill", "open",
        "xdg-open", "date", "shasum", "find", "wc", "tr", "basename",
        "dirname", "stat", "sed", "head", "tail", "awk", "grep", "ls",
        "chmod", "nohup",
    )
    source = (
        "#!/bin/sh\n"
        'printf "%s\\n" "${0##*/}" >> "$RAPP_EFFECT_MARKER"\n'
        "exit 97\n"
    )
    for command in commands:
        path = directory / command
        path.write_text(source, encoding="utf-8")
        path.chmod(0o755)
    marker.parent.mkdir(parents=True, exist_ok=True)


def _gate_dependencies(events: list[str], executor_name: str) -> dict:
    def review(_dependencies, _operation, _target):
        events.append("review")
        return True

    def authenticate(_evidence, _operation, _target):
        events.append("authority")
        return {
            "authenticated": False,
            "fresh": False,
            "owner_anchor_verified": False,
        }

    def executor(*_args, **_kwargs):
        events.append(executor_name)
        raise AssertionError("executor must not run after rejected authority")

    return {
        "review": review,
        "authenticate_section13": authenticate,
        executor_name: executor,
    }


def test_exact_provenance_and_historical_implementation_retention():
    for relative, (commit, blob, digest, byte_length) in PROVENANCE.items():
        source = _git_bytes(commit, relative)
        current = (ROOT / relative).read_bytes()
        assert _git_blob(commit, relative) == blob, relative
        assert hashlib.sha256(source).hexdigest() == digest, relative
        assert len(source) == byte_length, relative

        text = current.decode("utf-8")
        assert commit in text, relative
        assert blob in text, relative
        assert digest in text, relative
        for marker in REQUIRED_MARKERS[relative]:
            assert marker in text, (relative, marker)

        if relative in PYTHON_SOURCES:
            assert _symbols(source) <= _symbols(current), relative
        else:
            assert _line_coverage(source, current) >= LINE_COVERAGE_MINIMUM.get(
                relative, 0.985
            ), relative


def test_shell_defaults_and_rejected_modes_invoke_no_external_effect(tmp_path):
    marker = tmp_path / "effects.log"
    sentinels = tmp_path / "sentinels"
    home = tmp_path / "home"
    home.mkdir()
    _write_command_sentinels(sentinels, marker)
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(home),
            "PATH": f"{sentinels}:/usr/bin:/bin",
            "RAPP_EFFECT_MARKER": str(marker),
        }
    )

    for relative, rejected_args in SHELL_DEFAULTS.items():
        default = subprocess.run(
            ("/bin/bash", str(ROOT / relative)),
            cwd=tmp_path,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        assert default.returncode == 0, (relative, default.stderr)
        assert '"effects":[]' in default.stdout, relative
        assert not marker.exists(), relative

        rejected = subprocess.run(
            ("/bin/bash", str(ROOT / relative), *rejected_args),
            cwd=tmp_path,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        assert rejected.returncode == 78, (relative, rejected.stderr)
        assert '"effects_started":false' in rejected.stderr, relative
        assert not marker.exists(), relative

    assert list(home.iterdir()) == []


def test_python_no_flag_modes_are_deterministic_and_effect_free(tmp_path):
    marker = tmp_path / "effects.log"
    sentinels = tmp_path / "sentinels"
    home = tmp_path / "home"
    home.mkdir()
    _write_command_sentinels(sentinels, marker)
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(home),
            "PATH": f"{sentinels}:/usr/bin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "RAPP_EFFECT_MARKER": str(marker),
        }
    )

    for relative in PYTHON_DEFAULTS:
        outputs = []
        for _ in range(2):
            result = subprocess.run(
                (sys.executable, str(ROOT / relative)),
                cwd=tmp_path,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            assert result.returncode == 0, (relative, result.stderr)
            outputs.append((result.stdout, result.stderr))
        assert outputs[0] == outputs[1], relative
        assert not marker.exists(), relative

    rejected = subprocess.run(
        (sys.executable, str(ROOT / "tools/sim/tick_twin.py"), "--apply"),
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert rejected.returncode == 78
    assert '"effects_started": false' in rejected.stdout
    assert not marker.exists()
    assert list(home.iterdir()) == []


def test_function_app_uses_exact_facade_and_refuses_before_transport():
    module = _load_module("rapp_swarm/function_app.py")

    class Request:
        method = "POST"
        headers = {}

        @staticmethod
        def get_json():
            return {"user_input": "hello"}

    default = module.main(Request())
    assert default.status_code == 422
    assert json.loads(default.get_body()) == {
        "error": {"code": "inference-refused", "step": None}
    }

    events: list[str] = []
    dependencies = _gate_dependencies(events, "facade_transport")
    payload, request_sha256 = module._parse_rapp_request(Request())
    assert payload == {"user_input": "hello"}
    target = module.rapp_chat_target(request_sha256)
    receipt = module.exact_target_receipt("rapp-chat-facade-forward", target)
    response = module.handle_rapp_chat(
        Request(),
        dependencies=dependencies,
        target_receipt=receipt,
        authority_evidence={"schema": "candidate-only"},
    )
    assert response.status_code == 422
    assert json.loads(response.get_body()) == {
        "error": {"code": "inference-refused", "step": None}
    }
    assert events == ["review", "authority"]
    assert module.FACADE_URL == "http://127.0.0.1:7073/chat"
    source = (ROOT / "rapp_swarm/function_app.py").read_text()
    assert '@app.route(route="businessinsightbot_function"' not in source
    for invalid in (
        (422, {"error": {"code": 123, "step": None}}),
        (422, {"error": {"code": "inference-refused", "step": []}}),
        (422, {"error": {"code": "inference-refused", "step": "1"}}),
        (422, {"error": {"code": "invented", "step": None}}),
    ):
        try:
            module._validated_facade_result(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid facade refusal accepted: {invalid!r}")

    class ExtraRequest:
        method = "POST"
        headers = {}

        @staticmethod
        def get_json():
            return {
                "user_input": "hello",
                "conversation_history": [{"role": "user", "content": "ignored"}],
            }

    extra_payload, extra_sha256 = module._parse_rapp_request(ExtraRequest())
    assert extra_payload == {"user_input": "hello"}
    assert extra_sha256 != request_sha256
    mismatch_events: list[str] = []
    mismatch_dependencies = _gate_dependencies(
        mismatch_events, "facade_transport"
    )
    mismatch = module.handle_rapp_chat(
        ExtraRequest(),
        dependencies=mismatch_dependencies,
        target_receipt=receipt,
        authority_evidence={"schema": "candidate-only"},
    )
    assert mismatch.status_code == 422
    assert mismatch_events == ["review"]


def test_simulation_effect_gates_stop_before_executors(tmp_path):
    tick = _load_module("tools/sim/tick_twin.py")
    events: list[str] = []
    dependencies = _gate_dependencies(events, "action_executor")
    twin = {
        "name": "bill-brainstem",
        "display_name": "Bill",
        "rappid": "candidate-unminted",
        "dir": str(tmp_path / "bill"),
    }
    action = {"action": "observe-only", "reason": "test"}
    state = {
        "submissions": [],
        "votes": [],
        "neighborhood": {"name": "local-art-collective"},
    }
    target = tick.action_effect_target(
        action, twin, str(tmp_path / "neighborhood"), state
    )
    result = tick.execute_action(
        action,
        twin,
        str(tmp_path / "neighborhood"),
        dry_run=False,
        dependencies=dependencies,
        target_receipt=tick.exact_target_receipt(
            "simulation-tick-apply", target
        ),
        authority_evidence={"schema": "candidate-only"},
        nb_state=state,
    )
    assert result["applied"] is False
    assert result["effects_started"] is False
    assert events == ["review", "authority"]

    success_events: list[str] = []

    def review(_dependencies, _operation, _target):
        success_events.append("review")
        return True

    def authenticate(_evidence, _operation, _target):
        success_events.append("authority")
        return {
            "authenticated": True,
            "fresh": True,
            "owner_anchor_verified": True,
        }

    class Lock:
        def __enter__(self):
            success_events.append("lock-enter")

        def __exit__(self, _kind, _value, _traceback):
            success_events.append("lock-exit")

    def lock_factory(_target):
        success_events.append("lock")
        return Lock()

    def state_reader(_neighborhood_dir):
        success_events.append("state")
        return json.loads(json.dumps(state))

    def executor(function, bound_action, bound_twin, bound_dir, bound_state):
        success_events.append("executor")
        return function(
            bound_action,
            bound_twin,
            bound_dir,
            dry_run=True,
            nb_state=bound_state,
        )

    success_dependencies = {
        "review": review,
        "authenticate_section13": authenticate,
        "action_lock": lock_factory,
        "read_neighborhood_state": state_reader,
        "action_executor": executor,
    }
    success = tick.execute_action(
        action,
        twin,
        str(tmp_path / "neighborhood"),
        dry_run=False,
        dependencies=success_dependencies,
        target_receipt=tick.exact_target_receipt(
            "simulation-tick-apply", target
        ),
        authority_evidence={"schema": "test-only"},
        nb_state=state,
    )
    assert success["applied"] is False
    assert success_events == [
        "review",
        "authority",
        "lock",
        "lock-enter",
        "state",
        "executor",
        "lock-exit",
    ]

    observe = _load_module("tools/sim/observe.py")
    observe.SIM_ROOT = str(tmp_path / "sim")
    events = []
    dependencies = _gate_dependencies(events, "observer_executor")
    out_dir = tmp_path / "observations"
    target = {
        "sim_root": observe.SIM_ROOT,
        "out_dir": str(out_dir.resolve()),
        "ecosystem_pulse": False,
    }
    result = observe.run_observer(
        ["--out-dir", str(out_dir)],
        dependencies=dependencies,
        target_receipt=observe.exact_target_receipt(
            "simulation-observation-write", target
        ),
        authority_evidence={"schema": "candidate-only"},
    )
    assert result["written"] is False
    assert result["effects_started"] is False
    assert events == ["review", "authority"]
    assert not out_dir.exists()

    duplicate_events: list[str] = []
    duplicate_dependencies = _gate_dependencies(
        duplicate_events, "observer_executor"
    )
    duplicate = observe.run_observer(
        [
            "--out-dir",
            str(tmp_path / "authorized"),
            "--out-dir",
            str(tmp_path / "unreviewed"),
        ],
        dependencies=duplicate_dependencies,
        target_receipt={},
        authority_evidence={"schema": "candidate-only"},
    )
    assert duplicate["error"]["code"] == "invalid-arguments"
    assert duplicate["effects_started"] is False
    assert duplicate_events == []
    assert not (tmp_path / "authorized").exists()
    assert not (tmp_path / "unreviewed").exists()
    equals_duplicate = observe.run_observer(
        [
            f"--out-dir={tmp_path / 'authorized'}",
            f"--out-dir={tmp_path / 'unreviewed'}",
        ],
        dependencies=duplicate_dependencies,
        target_receipt={},
        authority_evidence={"schema": "candidate-only"},
    )
    assert equals_duplicate["error"]["code"] == "invalid-arguments"
    assert duplicate_events == []

    plant = _load_module("tools/sim/plant_two_brainstems.py")
    events = []
    dependencies = _gate_dependencies(events, "plant_executor")
    sim_root = tmp_path / "plant"
    target = {
        "sim_root": str(sim_root.resolve()),
        "brainstems": ["bill-brainstem", "alice-brainstem"],
        "neighborhood": "local-art-collective",
    }
    result = plant.run_plant(
        sim_root=str(sim_root),
        dependencies=dependencies,
        target_receipt=plant.exact_target_receipt(
            "plant-two-brainstems", target
        ),
        authority_evidence={"schema": "candidate-only"},
    )
    assert result["planted"] is False
    assert result["effects_started"] is False
    assert events == ["review", "authority"]
    assert not sim_root.exists()


def test_tick_rejects_traversal_and_incomplete_payloads_before_effects(tmp_path):
    tick = _load_module("tools/sim/tick_twin.py")
    twin = {
        "name": "bill-brainstem",
        "display_name": "Bill",
        "rappid": "candidate-unminted",
        "dir": str(tmp_path / "bill"),
    }
    state = {
        "submissions": [
            {
                "slug": "alice-piece",
                "title": "Alice Piece",
                "contributor": "Alice",
            }
        ],
        "votes": [],
        "neighborhood": {"name": "local-art-collective"},
    }
    invalid_actions = (
        {
            "action": "remix",
            "remix": {
                "slug": "../../escaped",
                "title": "Escape",
                "kind": "text",
                "content": "bad",
                "remix_of": "alice-piece",
            },
        },
        {
            "action": "submit",
            "submit": {
                "slug": "valid-slug",
                "title": "Missing content",
                "kind": "text",
            },
        },
        {
            "action": "remix",
            "remix": {
                "slug": "valid-remix",
                "title": "Missing content",
                "kind": "text",
                "remix_of": "alice-piece",
            },
        },
        {
            "action": "vote",
            "vote": {"slug": "../../escaped", "reaction": "🩵"},
        },
        {
            "action": "submit",
            "submit": {
                "slug": "alice-piece",
                "title": "Duplicate",
                "kind": "text",
                "content": "duplicate",
            },
        },
        {
            "action": "remix",
            "remix": {
                "slug": "valid-remix",
                "title": "Missing source",
                "kind": "text",
                "content": "missing",
                "remix_of": "does-not-exist",
            },
        },
    )
    for action in invalid_actions:
        ok, _ = tick.validate_action(action, twin, state)
        assert ok is False
        result = tick.execute_action(
            action,
            twin,
            str(tmp_path / "neighborhood"),
            dry_run=False,
            nb_state=state,
        )
        assert result["applied"] is False
        assert result["effects_started"] is False
        assert result["error"]["code"] == "invalid-action"
    assert not (tmp_path / "neighborhood").exists()
    assert not (tmp_path / "escaped").exists()

    valid_action = {
        "action": "vote",
        "vote": {"slug": "alice-piece", "reaction": "🩵"},
    }
    bill_target = tick.action_effect_target(
        valid_action, twin, str(tmp_path / "neighborhood"), state
    )
    mallory = {
        **twin,
        "display_name": "Mallory",
        "rappid": "different-rappid",
    }
    mallory_target = tick.action_effect_target(
        valid_action, mallory, str(tmp_path / "neighborhood"), state
    )
    assert bill_target["action_sha256"] == mallory_target["action_sha256"]
    assert bill_target["twin"] != mallory_target["twin"]
    assert (
        tick.exact_target_receipt("simulation-tick-apply", bill_target)
        != tick.exact_target_receipt("simulation-tick-apply", mallory_target)
    )


def test_server_and_cave_gates_stop_before_bind_or_mutation(tmp_path):
    server = _load_module("tools/test_brainstem_server.py")
    events: list[str] = []
    dependencies = _gate_dependencies(events, "server_factory")

    def blocked(name):
        def callback(*_args, **_kwargs):
            events.append(name)
            raise AssertionError(f"{name} must not run")
        return callback

    dependencies.update(
        {
            "prepare_home": blocked("prepare_home"),
            "load_organ": blocked("load_organ"),
            "facade_transport": blocked("facade_transport"),
        }
    )
    home = tmp_path / "brainstem"
    organ = tmp_path / "organ.py"
    target = {
        "bind": "127.0.0.1",
        "port": 7081,
        "home": str(home.resolve()),
        "organ": str(organ.resolve()),
        "facade": server.FACADE_URL,
    }
    result = server.serve(
        port=7081,
        home=str(home),
        organ_path=str(organ),
        dependencies=dependencies,
        target_receipt=server.exact_target_receipt(
            "test-brainstem-bind", target
        ),
        authority_evidence={"schema": "candidate-only"},
    )
    assert result["bound"] is False
    assert result["effects_started"] is False
    assert events == ["review", "authority"]
    assert not home.exists()

    handler_type = server._build_handler(
        organ=None,
        port=7081,
        home_dir=str(home),
        facade_transport=None,
    )
    handler = object.__new__(handler_type)
    raw = json.dumps(
        {
            "user_input": "hello",
            "conversation_history": [{"role": "user", "content": "ignored"}],
        }
    ).encode()
    handler.headers = {
        "Content-Type": "application/json",
        "Content-Length": str(len(raw)),
    }
    handler.rfile = io.BytesIO(raw)
    payload, request_sha256 = handler._read_chat_body()
    assert payload == {"user_input": "hello"}
    chat_events: list[str] = []
    chat_dependencies = _gate_dependencies(
        chat_events, "facade_transport"
    )
    chat_target = server.rapp_chat_target(request_sha256)
    chat_dependencies["chat_target_receipts"] = {
        request_sha256: server.exact_target_receipt(
            "test-brainstem-chat-forward", chat_target
        )
    }
    chat_dependencies["chat_authority_evidence"] = {
        "schema": "candidate-only"
    }
    refusal = server._authorize_chat_forward(
        request_sha256, chat_dependencies
    )
    assert refusal["code"] == "authenticated-registry-unavailable"
    assert chat_events == ["review", "authority"]

    organ_path = "/api/neighborhoods/join"
    organ_raw = json.dumps({"gate_url": "https://example.invalid"}).encode()
    handler.headers = {"Content-Length": str(len(organ_raw))}
    handler.rfile = io.BytesIO(organ_raw)
    organ_body, organ_sha256 = handler._read_organ_body(
        "POST", organ_path
    )
    assert organ_body == {"gate_url": "https://example.invalid"}
    organ_events: list[str] = []
    organ_dependencies = _gate_dependencies(
        organ_events, "organ_executor"
    )
    organ_target = server.organ_request_target(
        "POST", organ_path, organ_sha256
    )
    organ_dependencies["organ_target_receipts"] = {
        organ_sha256: server.exact_target_receipt(
            "test-brainstem-organ-dispatch", organ_target
        )
    }
    organ_dependencies["organ_authority_evidence"] = {
        "schema": "candidate-only"
    }
    organ_refusal = server._authorize_organ_forward(
        "POST", organ_path, organ_sha256, organ_dependencies
    )
    assert organ_refusal["code"] == "authenticated-registry-unavailable"
    assert organ_events == ["review", "authority"]
    assert server._is_allowed_loopback_origin("http://127.0.0.1:8000")
    assert not server._is_allowed_loopback_origin("https://example.com")

    duplicate = b'{"user_input":"first","user_input":"second"}'
    handler.headers = {
        "Content-Type": "application/json",
        "Content-Length": str(len(duplicate)),
    }
    handler.rfile = io.BytesIO(duplicate)
    try:
        handler._read_chat_body()
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate chat members were accepted")

    for invalid in (
        (422, {"error": {"code": 123, "step": None}}),
        (422, {"error": {"code": "inference-refused", "step": []}}),
        (422, {"error": {"code": "inference-refused", "step": "1"}}),
        (422, {"error": {"code": "invented", "step": None}}),
    ):
        try:
            server._validated_facade_result(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid facade refusal accepted: {invalid!r}")

    cave_module = _load_module("cave/agents/cave_agent.py")
    cave_root = tmp_path / "cave"
    source = cave_root / "cubbies" / "alice" / "agents"
    source.mkdir(parents=True)
    (source / "sample_agent.py").write_text("VALUE = 1\n", encoding="utf-8")
    brainstem = tmp_path / "host"
    (brainstem / ".git").mkdir(parents=True)
    events = []
    dependencies = _gate_dependencies(events, "cave_executor")
    dependencies["cave_root"] = str(cave_root)
    cave_agent = cave_module.CaveAgent()
    snapshot = cave_agent._load_source_snapshot(
        str(cave_root), str(source), False
    )
    target = {
        "cubby": "alice",
        "source": str(source.resolve()),
        "brainstem": str(brainstem.resolve()),
        "verify": False,
        "source_snapshot_sha256": snapshot["sha256"],
        "source_entries": snapshot["entries"],
        "git_exclude": str(
            (brainstem / ".git" / "info" / "exclude").resolve()
        ),
    }
    output = json.loads(
        cave_agent.perform(
            action="load",
            cubby="alice",
            verify=False,
            _cave_root=str(cave_root),
            _brainstem_dir=str(brainstem),
            _dependencies=dependencies,
            _target_receipt=cave_module.exact_target_receipt(
                "cave-load-agents", target
            ),
            _authority_evidence={"schema": "candidate-only"},
        )
    )
    assert output["loaded"] == []
    assert output["effects_started"] is False
    assert events == ["review", "authority"]
    assert not (brainstem / "agents").exists()
    assert not (brainstem / ".git" / "info").exists()


def test_read_only_algorithms_remain_usable(tmp_path):
    specs = _load_module("tools/front_door_specs.py")
    bundle = specs.bundle_for_kind(
        "neighborhood",
        owner="local",
        name="test-neighborhood",
        display_name="Test Neighborhood",
    )
    assert len(bundle) >= 10
    assert "specs/AGENT_SPEC.md" in bundle
    assert "specs/RAPPLICATION_SPEC.md" in bundle
    assert "specs/SENSE_SPEC.md" in bundle
    assert "specs/SUBMISSION_PROTOCOL.md" in bundle
    assert all(len(content) > 200 for content in bundle.values())

    cave_module = _load_module("cave/agents/cave_agent.py")
    cave_root = tmp_path / "cave"
    (cave_root / "cubbies").mkdir(parents=True)
    (cave_root / "super-rar").mkdir()
    (cave_root / "cubbies" / "index.json").write_text(
        json.dumps({"cubbies": [{"github_login": "alice"}]}),
        encoding="utf-8",
    )
    (cave_root / "super-rar" / "index.json").write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "kind": "agent",
                        "name": "AliceAgent",
                        "purpose": "local test",
                        "cubby": "alice",
                    }
                ],
                "by_kind": {"agent": 1},
            }
        ),
        encoding="utf-8",
    )
    agent = cave_module.CaveAgent()
    listed = json.loads(agent.perform(action="list", _cave_root=str(cave_root)))
    searched = json.loads(
        agent.perform(
            action="super_rar",
            query="alice",
            kind="agent",
            _cave_root=str(cave_root),
        )
    )
    assert listed["cubbies"] == [{"github_login": "alice"}]
    assert searched["count"] == 1
    assert searched["results"][0]["name"] == "AliceAgent"

    source = cave_root / "cubbies" / "alice" / "agents"
    source.mkdir(parents=True)
    (source / "unpinned_agent.py").write_text("VALUE = 1\n", encoding="utf-8")
    outside = tmp_path / "outside_agent.py"
    outside.write_text("VALUE = 2\n", encoding="utf-8")
    (source / "linked_agent.py").symlink_to(outside)
    snapshot = agent._load_source_snapshot(
        str(cave_root), str(source), True
    )
    statuses = {entry["file"]: entry["status"] for entry in snapshot["entries"]}
    assert statuses["unpinned_agent.py"] == "pin-required"
    assert statuses["linked_agent.py"] == "symlink-refused"

    worktree = tmp_path / "worktree"
    git_common = tmp_path / "git-common"
    git_dir = git_common / "worktrees" / "worktree"
    worktree.mkdir()
    git_dir.mkdir(parents=True)
    (worktree / ".git").write_text(
        f"gitdir: {git_dir}\n",
        encoding="utf-8",
    )
    (git_dir / "commondir").write_text("../..\n", encoding="utf-8")
    excluded = agent._register_excludes(
        str(worktree), ["sample_agent.py"]
    )
    assert excluded == ["agents/sample_agent.py"]
    assert (
        git_common / "info" / "exclude"
    ).read_text(encoding="utf-8") == "agents/sample_agent.py\n"
    concurrent_names = [f"agent_{index}_agent.py" for index in range(12)]
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(
            pool.map(
                lambda name: agent._register_excludes(
                    str(worktree), [name]
                ),
                concurrent_names,
            )
        )
    assert results == [
        [f"agents/{name}"] for name in concurrent_names
    ]
    final_excludes = set(
        (git_common / "info" / "exclude").read_text(
            encoding="utf-8"
        ).splitlines()
    )
    assert {
        "agents/sample_agent.py",
        *(f"agents/{name}" for name in concurrent_names),
    } <= final_excludes
    assert (git_common / "info" / "rapp-cave-exclude.lock").is_file()

    safe_cave = tmp_path / "safe-cave"
    safe_source = safe_cave / "cubbies" / "alice" / "agents"
    safe_source.mkdir(parents=True)
    (safe_source / "sample_agent.py").write_text(
        "VALUE = 3\n", encoding="utf-8"
    )
    host_agents = worktree / "agents"
    host_agents.mkdir()
    escaped_destination = tmp_path / "escaped-destination.py"
    (host_agents / "sample_agent.py").symlink_to(escaped_destination)
    safe_snapshot = agent._load_source_snapshot(
        str(safe_cave), str(safe_source), False
    )
    safe_target = {
        "cubby": "alice",
        "source": str(safe_source.resolve()),
        "brainstem": str(worktree.resolve()),
        "verify": False,
        "source_snapshot_sha256": safe_snapshot["sha256"],
        "source_entries": safe_snapshot["entries"],
        "git_exclude": str(
            (git_common / "info" / "exclude").resolve()
        ),
    }
    load_result = json.loads(
        agent._historical_load(
            {
                "cubby": "alice",
                "verify": False,
                "_brainstem_dir": str(worktree),
            },
            str(safe_cave),
            safe_target,
            safe_snapshot,
        )
    )
    assert load_result["loaded"] == []
    assert any(
        item["why"] == "destination already exists — won't overwrite"
        for item in load_result["skipped"]
    )
    assert not escaped_destination.exists()

    tick = _load_module("tools/sim/tick_twin.py")
    replay = tick.sandbox_replay()
    assert replay["validation"] == {"ok": True, "message": "ok"}
    assert replay["result"]["applied"] is False
    assert replay["result"]["at"] == "2000-01-01T00:00:00Z"


def test_swarm_index_is_a_complete_inert_deployment_plan():
    source = (ROOT / "rapp_swarm/index.html").read_text(encoding="utf-8")
    assert "<script" not in source.lower()
    assert "<form" not in source.lower()
    assert "onclick=" not in source.lower()
    assert not re.search(
        r'(?:^|\s)href=["\']https?://', source, re.IGNORECASE
    )
    assert "default-src 'none'" in source
    assert "connect-src 'none'" in source
    assert "form-action 'none'" in source
    assert "data-historical-href=\"https://portal.azure.com/" in source
    assert "data-historical-href=\"https://github.com/kody-w/CommunityRAPP\"" in source
    assert "http://127.0.0.1:7073/chat" in source
    assert "Deployment disabled" in source


def test_egg_hatcher_inspects_locally_and_gates_network_and_apply(
    tmp_path, monkeypatch
):
    module = _load_module("pages/tutorials/egg_hatcher_agent.py")
    session_egg = tmp_path / "session.egg"
    session_egg.write_text(
        json.dumps(
            {
                "schema": "brainstem-egg/2.3-session",
                "type": "session",
                "name": "test-session",
                "title": "Test Session",
                "runtime": {"type": "html", "sha256": "a" * 64, "payload": ""},
                "transcript": [],
                "participants": [],
            }
        ),
        encoding="utf-8",
    )
    agent = module.EggHatcherAgent()
    inspected = json.loads(agent.perform(egg_path=str(session_egg)))
    assert inspected["ok"] is True
    assert inspected["mode"] == "inspect"
    assert inspected["route"] == "session"
    assert inspected["effects"] == []
    assert inspected["manifest"]["schema"] == "brainstem-egg/2.3-session"
    assert "Session cartridges run in a console" in inspected["plan"]

    zip_egg = tmp_path / "organism.egg"
    manifest = {
        "schema": "brainstem-egg/2.2-organism",
        "type": "organism",
        "rappid": "legacy-test-organism",
    }
    with zipfile.ZipFile(zip_egg, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
    blob = zip_egg.read_bytes()
    info = module._introspect(blob)
    assert info["container"] == "zip"
    assert module._route_kind(info["manifest"]) == "organism"

    network_calls: list[str] = []

    def forbidden_urlopen(*_args, **_kwargs):
        network_calls.append("urlopen")
        raise AssertionError("default inspection must not access the network")

    monkeypatch.setattr(module.urllib.request, "urlopen", forbidden_urlopen)
    network_result = json.loads(
        agent.perform(egg_path="https://example.invalid/test.egg")
    )
    assert network_result["read"] is False
    assert network_result["effects_started"] is False
    assert network_result["error"]["code"] == (
        "reviewed-dependency-injection-required"
    )
    assert network_calls == []

    destination = {"path": str(tmp_path / "hatched"), "kind": "organism"}
    target = module.hatch_target(info, blob, destination)
    events: list[str] = []
    dependencies = _gate_dependencies(events, "hatch_executor")
    apply_result = json.loads(
        agent.perform(
            egg_path=str(zip_egg),
            mode="apply",
            destination=destination,
            _dependencies=dependencies,
            _target_receipt=module.exact_target_receipt(
                "legacy-egg-hatch", target
            ),
            _authority_evidence={"schema": "candidate-only"},
        )
    )
    assert apply_result["applied"] is False
    assert apply_result["effects_started"] is False
    assert apply_result["error"]["code"] == "authenticated-registry-unavailable"
    assert events == ["review", "authority"]
    assert not (tmp_path / "hatched").exists()

    executor_events: list[object] = []

    def review(_dependencies, _operation, _target):
        executor_events.append("review")
        return True

    def authenticate(_evidence, _operation, _target):
        executor_events.append("authority")
        return {
            "authenticated": True,
            "fresh": True,
            "owner_anchor_verified": True,
        }

    def executor(route, bound_manifest, bound_blob, bound_target):
        executor_events.append(
            {
                "route": route,
                "manifest": bound_manifest,
                "blob": bound_blob,
                "target": bound_target,
            }
        )
        return {"ok": True, "applied": False, "test_only": True}

    fake_dependencies = {
        "review": review,
        "authenticate_section13": authenticate,
        "hatch_executor": executor,
    }
    fake_result = module.apply_hatch(
        info,
        blob,
        destination=destination,
        dependencies=fake_dependencies,
        target_receipt=module.exact_target_receipt(
            "legacy-egg-hatch", target
        ),
        authority_evidence={"schema": "test-only"},
    )
    assert fake_result == {"ok": True, "applied": False, "test_only": True}
    assert executor_events[:2] == ["review", "authority"]
    bound = executor_events[2]
    assert bound["route"] == "organism"
    assert not callable(bound["route"])
    assert isinstance(bound["manifest"], bytes)
    assert isinstance(bound["target"], bytes)
    bound_target = json.loads(bound["target"])
    bound_manifest = json.loads(bound["manifest"])
    assert bound_target["destination"] == {
        "kind": "organism",
        "path": str((tmp_path / "hatched").resolve()),
    }
    assert bound_manifest == manifest
    assert bound["blob"] == blob

    malformed = tmp_path / "malformed-session.egg"
    malformed.write_text(
        json.dumps(
            {
                "schema": "brainstem-egg/2.3-session",
                "type": "session",
                "runtime": "not-an-object",
            }
        ),
        encoding="utf-8",
    )
    malformed_result = json.loads(agent.perform(egg_path=str(malformed)))
    assert malformed_result["ok"] is False
    assert malformed_result["error"]["code"] == "egg-introspection-failed"

    duplicate = tmp_path / "duplicate-members.egg"
    duplicate.write_text(
        '{"schema":"brainstem-egg/2.3-session","schema":"other"}',
        encoding="utf-8",
    )
    duplicate_result = json.loads(agent.perform(egg_path=str(duplicate)))
    assert duplicate_result["ok"] is False
    assert duplicate_result["error"]["code"] == "egg-introspection-failed"

    symlink = tmp_path / "linked.egg"
    symlink.symlink_to(session_egg)
    symlink_result = json.loads(agent.perform(egg_path=str(symlink)))
    assert symlink_result["read"] is False
    assert symlink_result["error"]["code"] == "egg-read-failed"


def test_vendored_evidence_and_immutable_grail_are_unchanged():
    vendored_diff = subprocess.check_output(
        ("git", "diff", "--name-only", "--", "rapp_swarm/_vendored"),
        cwd=ROOT,
        text=True,
    )
    assert vendored_diff == ""

    authority = json.loads((ROOT / "RAPP1_AUTHORITY.json").read_text())
    frozen = authority["immutable_grail_boundary"]["frozen"]
    for relative, expected in frozen.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
