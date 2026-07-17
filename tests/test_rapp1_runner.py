from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "tests/run_rapp1_conformance.py"
STATIC_PATH = ROOT / "tests/check_rapp1_static.py"

spec = importlib.util.spec_from_file_location("rapp1_conformance_runner", RUNNER_PATH)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = runner
spec.loader.exec_module(runner)

static_spec = importlib.util.spec_from_file_location(
    "rapp1_static_checks",
    STATIC_PATH,
)
static_checks = importlib.util.module_from_spec(static_spec)
assert static_spec.loader is not None
static_spec.loader.exec_module(static_checks)


def test_runner_has_one_explicit_authoritative_gate_set():
    names = [gate.name for gate in runner.gates()]
    assert names == [
        "offline-boundary",
        "python-offline",
        "node-contract",
        "vault",
        "worker-containment",
        "documentation",
        "kernel-pin-local",
        "static-inspection",
        "html-smoke",
        "ui-smoke",
        "ecosystem-audit-offline",
        "organism-offline",
        "metropolis-directory",
        "metropolis-federation",
        "distribution-retirement",
        "t2t-removal",
        "plant-retirement",
        "twin-egg-retirement",
    ]
    assert len(names) == len(set(names))


def test_python_gate_covers_target_owned_offline_pytests():
    command = next(
        gate.command for gate in runner.gates() if gate.name == "python-offline"
    )
    expected = {
        "rapp_brainstem/test_local_agents.py",
        "rapp_brainstem/test_rapp1_facade.py",
        "rapp_brainstem/test_reserved_agents.py",
        "tests/rapp1_core",
        *(
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "tests").glob("test_*.py")
            if path.relative_to(ROOT).as_posix()
            != "tests/test_ecosystem_graph.py"
        ),
    }
    assert expected <= set(command)
    assert "tests/test_ecosystem_graph.py" not in command
    exclusion = command[command.index("--deselect") + 1]
    assert exclusion == (
        "rapp_brainstem/test_local_agents.py::"
        "TestMemoryAgentIntegration::test_manage_then_recall_memory"
    )
    assert {
        "tests/test_ecosystem_graph.py",
        (
            "rapp_brainstem/test_local_agents.py::"
            "TestMemoryAgentIntegration::test_manage_then_recall_memory"
        ),
    } <= set(runner.EXCLUDED_EXTERNAL_SUITES)
    assert {
        "tests/doorman/chat.js",
        "tests/doorman/smoke.js",
        "tests/dreamcatcher-conformance/runner.py",
        "tests/mirror-drift.sh",
        "tests/osi/L4a-tether-browser.sh",
    } <= set(runner.EXCLUDED_EXTERNAL_SUITES)


def test_runner_executes_every_gate_and_preserves_failure(monkeypatch):
    selected = (
        runner.Gate("first", ("first",), "first gate"),
        runner.Gate("second", ("second",), "second gate"),
    )
    returncodes = iter((0, 7))
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return type("Completed", (), {"returncode": next(returncodes)})()

    stable = runner.TrackedTreeState("head", "patch", ("preexisting",))
    monkeypatch.setattr(runner, "tracked_tree_state", lambda: stable)
    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    results = runner.run_gates(selected, {"TEST": "1"})

    assert [result.returncode for result in results] == [0, 7]
    assert [call[0] for call in calls] == [("first",), ("second",)]
    assert all(call[1]["check"] is False for call in calls)
    assert all(call[1]["cwd"] == ROOT for call in calls)


def test_main_returns_failure_when_any_gate_fails(monkeypatch):
    selected = (runner.Gate("injected", ("false",), "failure propagation"),)
    result = runner.GateResult(selected[0], 9)
    work_root = ROOT / "tests/.rapp1-runner-test"

    monkeypatch.setattr(runner, "_preflight", lambda: [])
    monkeypatch.setattr(runner, "prepare_isolated_brainstem", lambda: None)
    monkeypatch.setattr(runner, "gates", lambda: selected)
    monkeypatch.setattr(runner, "run_gates", lambda _gates: (result,))
    monkeypatch.setattr(runner, "WORK_ROOT", work_root)

    assert runner.main([]) == 1
    assert not work_root.exists()


def test_successful_gate_fails_if_it_repairs_a_tracked_file(monkeypatch):
    states = iter(
        (
            runner.TrackedTreeState("head", "dirty-patch", ("tracked.html",)),
            runner.TrackedTreeState("head", "clean-patch", ()),
        )
    )
    monkeypatch.setattr(runner, "tracked_tree_state", lambda: next(states))
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda *_args, **_kwargs: type("Completed", (), {"returncode": 0})(),
    )

    result = runner.run_gate(
        runner.Gate("write-back", ("repair",), "must be detected"),
        {},
    )

    assert result.returncode == 0
    assert result.tracked_mutation == ("tracked.html",)
    assert not result.passed


def test_gate_environment_scrubs_credentials_and_isolates_config(monkeypatch):
    scratch = ROOT / "tests/.rapp1-environment-test"
    shutil.rmtree(scratch, ignore_errors=True)
    monkeypatch.setattr(runner, "WORK_ROOT", scratch)
    sentinels = {
        "ACTIONS_RUNTIME_TOKEN": "actions-secret",
        "ANTHROPIC_API_KEY": "anthropic-key",
        "AWS_ACCESS_KEY_ID": "aws-key-id",
        "AWS_SECRET_ACCESS_KEY": "aws-secret",
        "AWS_SHARED_CREDENTIALS_FILE": "/ambient/aws",
        "AZURE_CLIENT_SECRET": "azure-secret",
        "COPILOT_SESSION_TOKEN": "copilot-secret",
        "COPILOT_TOKEN": "copilot-token",
        "DOCKER_CONFIG": "/ambient/docker",
        "GITHUB_APP_PRIVATE_KEY": "private-key",
        "GITHUB_PASSWORD": "github-password",
        "GITHUB_TOKEN": "github-secret",
        "GH_TOKEN": "gh-secret",
        "GOOGLE_APPLICATION_CREDENTIALS": "/ambient/google.json",
        "KUBECONFIG": "/ambient/kubeconfig",
        "NPM_CONFIG_USERCONFIG": "/ambient/npmrc",
        "OPENAI_API_KEY": "openai-key",
        "RAPP_SENTINEL_KEY": "arbitrary-key",
        "RAPP_SENTINEL_SECRET": "arbitrary-secret",
        "RAPP_SENTINEL_TOKEN": "arbitrary-token",
        "SSH_AUTH_SOCK": "/ambient/ssh-agent.sock",
    }
    for name, value in sentinels.items():
        monkeypatch.setenv(name, value)
    ambient_handles = {
        "CURL_HOME": "/ambient/curl",
        "GH_CONFIG_DIR": "/ambient/gh",
        "GIT_CONFIG_GLOBAL": "/ambient/gitconfig",
        "HOME": "/ambient/home",
        "NETRC": "/ambient/netrc",
        "XDG_CONFIG_HOME": "/ambient/xdg",
    }
    for name, value in ambient_handles.items():
        monkeypatch.setenv(name, value)
    try:
        environment = runner.gate_environment()
        assert set(sentinels).isdisjoint(environment)
        assert set(ambient_handles.values()).isdisjoint(environment.values())
        assert not any(
            name.endswith(("_KEY", "_PASSWORD", "_SECRET", "_TOKEN"))
            for name in environment
        )
        assert environment["HOME"] == os.fspath(scratch / "home")
        assert environment["GH_CONFIG_DIR"].startswith(environment["HOME"])
        assert environment["GIT_CONFIG_GLOBAL"] == os.devnull
        assert environment["NETRC"] == os.devnull
        assert environment["PYTHON_DOTENV_DISABLED"] == "1"
        assert environment["HTTP_PROXY"] == runner.OFFLINE_PROXY
        assert environment["http_proxy"] == runner.OFFLINE_PROXY
        assert set(environment["NO_PROXY"].split(",")) >= {
            "localhost",
            "127.0.0.1",
            "::1",
        }
        assert "node-network-guard.cjs" in environment["NODE_OPTIONS"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_isolated_brainstem_contains_only_tracked_files(monkeypatch):
    scratch = ROOT / "tests/.rapp1-runtime-copy-test"
    shutil.rmtree(scratch, ignore_errors=True)
    monkeypatch.setattr(runner, "WORK_ROOT", scratch)
    try:
        destination = runner.prepare_isolated_brainstem()
        source_root = ROOT / "rapp_brainstem"
        expected = {
            path.relative_to(source_root)
            for path in runner._tracked_brainstem_files()
            if path.is_file() or path.is_symlink()
        }
        actual = {
            path.relative_to(destination)
            for path in destination.rglob("*")
            if path.is_file() or path.is_symlink()
        }
        assert actual == expected
        assert not runner.RUNTIME_CREDENTIAL_FILES & actual
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_brainstem_boot_gates_require_isolated_unauthenticated_runtime():
    for relative in (
        "tests/e2e/07-ui-smoke.sh",
        "tests/organism/01-canonical-kernel-boots.sh",
        "tests/organism/06-stdout-wrapper-non-unicode-locale.sh",
    ):
        source = (ROOT / relative).read_text(encoding="utf-8")
        assert "RAPP1_BRAINSTEM_BOOT_DIR" in source
        assert "git archive --format=tar HEAD rapp_brainstem" in source
        assert 'HOME="$TEST_HOME"' in source
        assert 'PYTHONPATH="$OFFLINE_GUARD"' in source
        assert '"status":"unauthenticated"' in source
        assert '"status":"(ok|unauthenticated)"' not in source


def test_brainstem_boot_gates_poll_readiness_with_bounded_diagnostics():
    for relative in (
        "tests/e2e/07-ui-smoke.sh",
        "tests/organism/01-canonical-kernel-boots.sh",
    ):
        source = (ROOT / relative).read_text(encoding="utf-8")
        assert "wait_for_health" in source
        assert "RAPP1_BOOT_TIMEOUT_SECONDS" in source
        assert "boot_diagnostics" in source
        assert "kill -0" in source
        assert "process_is_expected" in source
        assert "ps -p" in source
        assert "discover_bound_port" in source
        assert "PORT=0" in source
        assert "OS-assigned process-owned port" in source
        assert "--connect-timeout 1 --max-time 1" in source
        assert "lsof -i" not in source
        assert "sock.bind" not in source
        assert "seq 1 30" not in source


def test_canonical_kernel_boots_concurrently_on_process_owned_ports(monkeypatch):
    scratch = ROOT / f"tests/.rapp1-concurrent-boots-{os.getpid()}"
    shutil.rmtree(scratch, ignore_errors=True)
    monkeypatch.setattr(runner, "WORK_ROOT", scratch)
    processes = []
    try:
        runner.prepare_isolated_brainstem()
        environment = runner.gate_environment()
        environment["RAPP1_BOOT_TIMEOUT_SECONDS"] = "20"
        for _ in range(2):
            processes.append(
                subprocess.Popen(
                    ("bash", "tests/organism/01-canonical-kernel-boots.sh"),
                    cwd=ROOT,
                    env=environment,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )
            )

        outputs = []
        for process in processes:
            output, _ = process.communicate(timeout=40)
            outputs.append(output)
            assert process.returncode == 0, output
        ports = []
        for output in outputs:
            match = re.search(r"ready: pid=\d+ port=(\d+)", output)
            assert match, output
            ports.append(int(match.group(1)))
        assert all(port > 0 for port in ports)
        assert len(set(ports)) == 2
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
        shutil.rmtree(scratch, ignore_errors=True)


def test_offline_boundary_harness_blocks_external_network(monkeypatch):
    scratch = ROOT / "tests/.rapp1-network-test"
    shutil.rmtree(scratch, ignore_errors=True)
    monkeypatch.setattr(runner, "WORK_ROOT", scratch)
    try:
        environment = runner.gate_environment()
        result = runner.subprocess.run(
            [sys.executable, "tests/check_offline_boundary.py"],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert "external HTTP denied" in result.stdout
        assert "external UDP and reverse DNS denied" in result.stdout
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_owner_blockers_are_separate_and_exact():
    assert runner.owner_blockers() == runner.EXPECTED_OWNER_BLOCKERS
    assert "authenticated" in runner.__doc__.lower()


def test_list_mode_does_not_execute_gates(monkeypatch, capsys):
    monkeypatch.setattr(
        runner,
        "run_gates",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("--list must not execute gates")
        ),
    )
    assert runner.main(["--list"]) == 0
    output = capsys.readouterr().out
    assert runner.INSTALL_COMMAND in output
    assert "Owner-action blockers (not local gate failures)" in output


def test_conformance_workflow_is_immutable_and_runs_canonical_runner():
    workflow = (
        ROOT / ".github/workflows/rapp1-conformance.yml"
    ).read_text(encoding="utf-8")
    uses = static_checks.extract_workflow_uses(workflow)
    assert len(uses) == 3
    assert all(
        re.fullmatch(r"[0-9a-f]{40}", value.rsplit("@", 1)[1])
        for _, value in uses
    )
    assert "python-version: '3.11'" in workflow
    assert "node-version: '20'" in workflow
    assert "-r requirements-rapp1-core.txt" in workflow
    assert "-r rapp_brainstem/requirements.txt" in workflow
    assert "python3 tests/run_rapp1_conformance.py" in workflow


def test_every_workflow_dependency_ref_is_immutable():
    references = static_checks.workflow_action_references()
    assert len(references) == 10
    assert static_checks.check_workflow_actions() == 10
    assert all(
        re.fullmatch(r"[0-9a-f]{40}", value.rsplit("@", 1)[1])
        for _, _, value in references
    )


def test_static_gate_scans_every_tracked_json_and_dynamic_live_categories():
    tracked = static_checks._cached_relative_paths()
    json_count = sum(Path(relative).suffix.lower() == ".json" for relative in tracked)
    assert static_checks.check_json() == json_count
    counts = static_checks.check_live_surface_inventory()
    assert counts["tracked"] == len(tracked)
    assert set(counts) == {
        "tracked",
        "installer",
        "marketing",
        "containment",
        "browser",
        "wire",
    }
    assert all(counts[category] > 0 for category in counts)


def test_workflow_action_parser_handles_step_and_job_uses_syntax():
    sha = "a" * 40
    source = f"""
jobs:
  reusable:
    uses: owner/repo/.github/workflows/check.yml@{sha}
  build:
    steps:
      - uses: actions/checkout@{sha} # pinned
      - name: Setup
        uses: 'actions/setup-python@{sha}'
"""
    assert static_checks.extract_workflow_uses(source) == (
        (4, f"owner/repo/.github/workflows/check.yml@{sha}"),
        (7, f"actions/checkout@{sha}"),
        (9, f"actions/setup-python@{sha}"),
    )


def test_ecosystem_map_requires_current_paths_or_explicit_retirement():
    assert static_checks.check_ecosystem_map_paths() > 50
    valid = """\
## §6 — Implementation map (file → spec section)
| File | Owns | Spec section |
|---|---|---|
| `tests/run-tests.mjs` | Current checks | current |
| `missing/old.py` | Historical/retired path | history |
| `README.md` | Current root file | current |
## §7 — Next
"""
    assert static_checks.validate_ecosystem_map_paths(valid) == 3

    missing = valid.replace("Historical/retired path", "Current implementation")
    with pytest.raises(AssertionError, match="missing without an explicit"):
        static_checks.validate_ecosystem_map_paths(missing)

    missing_root = valid.replace("`README.md`", "`MISSING_ROOT_DECLARATION.md`")
    with pytest.raises(AssertionError, match="MISSING_ROOT_DECLARATION.md"):
        static_checks.validate_ecosystem_map_paths(missing_root)

    stale_web = valid.replace(
        "`missing/old.py` | Historical/retired path",
        "`rapp_brainstem/utils/web/index.html` | Current implementation",
    )
    with pytest.raises(AssertionError, match="removed utils/web tree"):
        static_checks.validate_ecosystem_map_paths(stale_web)


def test_active_suite_inventory_has_no_orphan_executable():
    inventory = json.loads(
        static_checks.SUITE_INVENTORY_PATH.read_text(encoding="utf-8")
    )
    discovered = static_checks.discovered_test_candidates(inventory)
    assert static_checks.validate_test_suite_inventory(
        inventory,
        discovered,
    ) == len(discovered)
    with pytest.raises(AssertionError, match="unclassified executable"):
        static_checks.validate_test_suite_inventory(
            inventory,
            discovered | {"tests/orphan-test.sh"},
        )
    sources = {
        path: (ROOT / path).read_text(encoding="utf-8")
        for path in discovered
    }
    assert static_checks.validate_test_executable_references(
        inventory,
        sources,
    ) == len(sources)
    missing_reference = "/".join(("brainstem", "rapp.js"))
    with pytest.raises(AssertionError, match="missing retired files"):
        static_checks.validate_test_executable_references(
            inventory,
            {"tests/stale-browser.html": f'<script src="../{missing_reference}">'},
        )


def test_external_drift_gate_is_supplemental_and_commit_pinned():
    workflow = (ROOT / ".github/workflows/drift-lint.yml").read_text()
    commit = "de1c664154d3456224bdf95e830736ffb5270c2b"
    assert f"@{commit}" in workflow
    documentation = (ROOT / "tests/README.md").read_text()
    assert commit in documentation
    assert "supplemental" in documentation.lower()
    assert "not RAPP/1" in documentation
