from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "tests/run_rapp1_conformance.py"

spec = importlib.util.spec_from_file_location("rapp1_conformance_runner", RUNNER_PATH)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = runner
spec.loader.exec_module(runner)


def test_runner_has_one_explicit_authoritative_gate_set():
    names = [gate.name for gate in runner.gates()]
    assert names == [
        "python-offline",
        "node-contract",
        "vault",
        "worker-containment",
        "documentation",
        "kernel-pin",
        "static-inspection",
        "html-smoke",
        "plant-retirement",
        "twin-egg-retirement",
    ]
    assert len(names) == len(set(names))


def test_python_gate_covers_target_owned_offline_pytests():
    command = runner.gates()[0].command
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
    assert set(runner.EXCLUDED_EXTERNAL_SUITES) == {
        "tests/test_ecosystem_graph.py",
        (
            "rapp_brainstem/test_local_agents.py::"
            "TestMemoryAgentIntegration::test_manage_then_recall_memory"
        ),
    }


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
    monkeypatch.setattr(runner, "gates", lambda: selected)
    monkeypatch.setattr(runner, "run_gates", lambda _gates: (result,))
    monkeypatch.setattr(runner, "WORK_ROOT", work_root)

    assert runner.main([]) == 1
    assert not work_root.exists()


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
    uses = re.findall(r"^\s*uses:\s*\S+@([^\s#]+)", workflow, re.MULTILINE)
    assert uses
    assert all(re.fullmatch(r"[0-9a-f]{40}", ref) for ref in uses)
    assert "python-version: '3.11'" in workflow
    assert "node-version: '20'" in workflow
    assert "-r requirements-rapp1-core.txt" in workflow
    assert "-r rapp_brainstem/requirements.txt" in workflow
    assert "python3.11 tests/run_rapp1_conformance.py" in workflow


def test_every_workflow_dependency_ref_is_immutable():
    mutable = []
    workflows = {
        *ROOT.joinpath(".github/workflows").glob("*.yml"),
        *ROOT.joinpath(".github/workflows").glob("*.yaml"),
    }
    for path in sorted(workflows):
        source = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(source.splitlines(), 1):
            match = re.match(r"^\s*uses:\s*\S+@([^\s#]+)", line)
            if match and not re.fullmatch(r"[0-9a-f]{40}", match.group(1)):
                mutable.append(f"{path.name}:{line_number}:{match.group(1)}")
    assert mutable == []


def test_external_drift_gate_is_supplemental_and_commit_pinned():
    workflow = (ROOT / ".github/workflows/drift-lint.yml").read_text()
    commit = "de1c664154d3456224bdf95e830736ffb5270c2b"
    assert f"@{commit}" in workflow
    status = (ROOT / "RAPP1_STATUS.md").read_text()
    assert commit in status
    assert "supplemental" in status.lower()
    assert "not RAPP/1 authority" in status
