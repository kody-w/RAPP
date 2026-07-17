#!/usr/bin/env python3
"""Canonical offline RAPP/1 structural/pre-acceptance gate.

Install once from the repository root:

    python3.11 -m pip install \
      -r requirements-rapp1-core.txt \
      -r rapp_brainstem/requirements.txt \
      pytest

Then run:

    python3.11 tests/run_rapp1_conformance.py

Passing is not authenticated RAPP/1 acceptance. Owner-only blockers are
reported separately from target-owned gate failures.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "RAPP1_STATUS.md"
WORK_ROOT = ROOT / "tests/.rapp1-work"
INSTALL_COMMAND = (
    "python3.11 -m pip install -r requirements-rapp1-core.txt "
    "-r rapp_brainstem/requirements.txt pytest"
)
EXPECTED_OWNER_BLOCKERS = (
    "Signed monotonic registry and out-of-band anchor",
    "Lawful root re-anchor",
    "Signed replacement invite",
    "External mirror correction",
)
EXCLUDED_EXTERNAL_SUITES = {
    "tests/test_ecosystem_graph.py": (
        "invokes the authenticated gh CLI and rewrites external-inventory "
        "snapshots"
    ),
    (
        "rapp_brainstem/test_local_agents.py::"
        "TestMemoryAgentIntegration::test_manage_then_recall_memory"
    ): (
        "downloads moving agent sources over the network"
    ),
}


@dataclass(frozen=True)
class Gate:
    name: str
    command: tuple[str, ...]
    purpose: str


@dataclass(frozen=True)
class GateResult:
    gate: Gate
    returncode: int

    @property
    def passed(self) -> bool:
        return self.returncode == 0


def _pytest_command() -> tuple[str, ...]:
    top_level = sorted(
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "tests").glob("test_*.py")
        if path.relative_to(ROOT).as_posix() not in EXCLUDED_EXTERNAL_SUITES
    )
    paths = (
        "rapp_brainstem/test_local_agents.py",
        "rapp_brainstem/test_rapp1_facade.py",
        "rapp_brainstem/test_reserved_agents.py",
        "tests/rapp1_core",
        *top_level,
    )
    return (
        sys.executable,
        "-m",
        "pytest",
        "-q",
        *paths,
        "--deselect",
        (
            "rapp_brainstem/test_local_agents.py::"
            "TestMemoryAgentIntegration::test_manage_then_recall_memory"
        ),
    )


def gates() -> tuple[Gate, ...]:
    return (
        Gate(
            "python-offline",
            _pytest_command(),
            "core, facade, authority, containment, docs, migrations, and runner tests",
        ),
        Gate(
            "node-contract",
            ("node", "tests/run-tests.mjs"),
            "current self-contained JavaScript/static contracts",
        ),
        Gate(
            "vault",
            ("node", "tests/vault-check.mjs"),
            "vault links, aliases, frontmatter, manifest, and PII guard",
        ),
        Gate(
            "worker-containment",
            ("node", "tests/test-worker-containment.mjs"),
            "retired inference proxy and preserved control plane",
        ),
        Gate(
            "documentation",
            (sys.executable, "tools/check_rapp1_docs.py"),
            "managed current, historical, generated, and excluded document scope",
        ),
        Gate(
            "kernel-pin",
            (sys.executable, "check_kernel_pin.py"),
            "immutable grail bytes and target distro pin",
        ),
        Gate(
            "static-inspection",
            (sys.executable, "tests/check_rapp1_static.py"),
            "strict JSON, HTML parse, shell/JS syntax, and legacy-test inventory",
        ),
        Gate(
            "html-smoke",
            ("bash", "tests/e2e/08-html-pages.sh"),
            "target-owned HTML parse and content smoke checks",
        ),
        Gate(
            "plant-retirement",
            ("bash", "installer/test_plant.sh"),
            "target-owned planter returns 410 without side effects",
        ),
        Gate(
            "twin-egg-retirement",
            ("bash", "tests/test-twin-egg.sh"),
            "contained Tier 2 egg executable refuses packaging",
        ),
    )


def owner_blockers(text: str | None = None) -> tuple[str, ...]:
    source = STATUS_PATH.read_text(encoding="utf-8") if text is None else text
    match = re.search(
        r"^## Owner-action blockers\s*$([\s\S]*?)(?=^## |\Z)",
        source,
        flags=re.MULTILINE,
    )
    if not match:
        raise ValueError("RAPP1_STATUS.md has no Owner-action blockers section")
    return tuple(
        re.findall(r"^\d+\.\s+\*\*(.+?)\*\*", match.group(1), re.MULTILINE)
    )


def gate_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": os.fspath(ROOT),
            "TMPDIR": os.fspath(WORK_ROOT),
            "RAPP1_OFFLINE": "1",
        }
    )
    return environment


def run_gate(
    gate: Gate,
    environment: Mapping[str, str],
) -> GateResult:
    print(f"\n━━ {gate.name}: {gate.purpose}")
    print("+ " + " ".join(gate.command), flush=True)
    completed = subprocess.run(
        gate.command,
        cwd=ROOT,
        env=environment,
        check=False,
    )
    state = "PASS" if completed.returncode == 0 else "FAIL"
    print(f"{state}: {gate.name} (exit {completed.returncode})")
    return GateResult(gate, completed.returncode)


def run_gates(
    selected: Sequence[Gate],
    environment: Mapping[str, str] | None = None,
) -> tuple[GateResult, ...]:
    effective_environment = gate_environment() if environment is None else environment
    return tuple(run_gate(gate, effective_environment) for gate in selected)


def _preflight() -> list[str]:
    failures = []
    if sys.version_info < (3, 11):
        failures.append(
            f"Python 3.11+ required; running {sys.version.split()[0]}"
        )
    for executable in ("bash", "git", "node"):
        if shutil.which(executable) is None:
            failures.append(f"required executable not found: {executable}")
    try:
        blockers = owner_blockers()
        if blockers != EXPECTED_OWNER_BLOCKERS:
            failures.append(
                "owner-action blocker set drifted: "
                f"expected {EXPECTED_OWNER_BLOCKERS!r}, got {blockers!r}"
            )
    except (OSError, ValueError) as error:
        failures.append(str(error))
    return failures


def _print_owner_blockers() -> None:
    print("\n━━ Owner-action blockers (not local gate failures)")
    for index, blocker in enumerate(owner_blockers(), 1):
        print(f"{index}. {blocker}")
    print(
        "These require authenticated estate-owner action; this runner neither "
        "creates nor substitutes trust evidence."
    )


def _print_list() -> None:
    print("Install:")
    print(f"  {INSTALL_COMMAND}")
    print("\nCanonical gates:")
    for gate in gates():
        print(f"  {gate.name:20} {gate.purpose}")
    print("\nCredentialed/external suites intentionally excluded:")
    for path, reason in EXCLUDED_EXTERNAL_SUITES.items():
        print(f"  {path}: {reason}")
    _print_owner_blockers()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run target-owned offline RAPP/1 rev-5 structural/pre-acceptance "
            "gates. Passing does not establish authenticated acceptance."
        ),
        epilog=f"Install dependencies with: {INSTALL_COMMAND}",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="list gates and owner-action blockers without executing tests",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    if arguments.list:
        _print_list()
        return 0

    failures = _preflight()
    if failures:
        for failure in failures:
            print(f"PRECHECK FAIL: {failure}", file=sys.stderr)
        _print_owner_blockers()
        return 2

    WORK_ROOT.mkdir(parents=True, exist_ok=True)
    try:
        results = run_gates(gates())
    finally:
        shutil.rmtree(WORK_ROOT, ignore_errors=True)

    failed = [result for result in results if not result.passed]
    print("\n━━ Local structural/pre-acceptance summary")
    for result in results:
        state = "PASS" if result.passed else "FAIL"
        print(f"{state:4} {result.gate.name}")
    _print_owner_blockers()

    if failed:
        print(
            f"\nLOCAL PRE-ACCEPTANCE: FAIL ({len(failed)} gate(s) failed)",
            file=sys.stderr,
        )
        return 1
    print(
        "\nLOCAL PRE-ACCEPTANCE: PASS — repository remains "
        "NOT YET FULLY RAPP/1 CONFORMANT"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
