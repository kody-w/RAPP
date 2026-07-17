#!/usr/bin/env python3
"""Canonical offline RAPP/1 structural/pre-acceptance gate.

Install once from the repository root:

    python3 -m pip install \
      -r requirements-rapp1-core.txt \
      -r rapp_brainstem/requirements.txt \
      pytest

Then run:

    python3 tests/run_rapp1_conformance.py

Passing is not authenticated RAPP/1 acceptance. Owner-only blockers are
reported separately from target-owned gate failures.
"""

from __future__ import annotations

import argparse
import hashlib
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
    "python3 -m pip install -r requirements-rapp1-core.txt "
    "-r rapp_brainstem/requirements.txt pytest"
)
EXPECTED_OWNER_BLOCKERS = (
    "Signed monotonic registry and out-of-band anchor",
    "Lawful root re-anchor",
    "Signed replacement invite",
    "External mirror correction",
)
EXCLUDED_EXTERNAL_SUITES = {
    "tests/doorman/chat.js": "requires a live authenticated doorman/chat service",
    "tests/doorman/smoke.js": "requires a live authenticated doorman service",
    "tests/dreamcatcher-conformance/runner.py": (
        "requires the external Dreamcatcher execution engine"
    ),
    "tests/e2e/enable-mi-on-twin.sh": (
        "mutates Azure managed identity and requires cloud credentials"
    ),
    "tests/mirror-drift.sh": "queries external mirrors over the network",
    "tests/osi/L4a-tether-browser.sh": (
        "downloads/launches Playwright Chromium and uses an external PeerJS broker"
    ),
    "tests/test_ecosystem_graph.py": (
        "invokes the authenticated gh CLI and rewrites external-inventory "
        "snapshots"
    ),
    "tests/test_installer.sh": "downloads and installs into user-owned locations",
    "tests/test-t2t-removal.sh": (
        "destructively rebuilds tracked vendor and removal artifacts"
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
    tracked_mutation: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return self.returncode == 0 and not self.tracked_mutation


@dataclass(frozen=True)
class TrackedTreeState:
    head: str
    patch_sha256: str
    changed_paths: tuple[str, ...]


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
            "kernel-pin-local",
            (sys.executable, "tests/check_kernel_pin_local.py"),
            "KERNEL_PIN frozen hashes against local bytes (no network)",
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
            "ui-smoke",
            ("bash", "tests/e2e/07-ui-smoke.sh"),
            "local brainstem boot and current served-UI contract",
        ),
        Gate(
            "ecosystem-audit-offline",
            ("bash", "tests/features/F10-ecosystem-audit.sh"),
            "offline ecosystem contract and drift fixtures",
        ),
        Gate(
            "organism-offline",
            ("bash", "tests/organism/run-all.sh"),
            "retained local kernel, encoding, storage, and concurrency fixtures",
        ),
        Gate(
            "metropolis-directory",
            ("bash", "tests/scenarios/16-metropolis-tracker.sh"),
            "offline decentralized tracker schema and directory checks",
        ),
        Gate(
            "metropolis-federation",
            ("bash", "tests/scenarios/20-cross-tracker-federation.sh"),
            "offline cross-tracker merge and deduplication checks",
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


def tracked_tree_state() -> TrackedTreeState:
    """Snapshot all tracked index/worktree changes relative to HEAD."""
    common = (
        "git",
        "--no-pager",
        "diff",
        "--binary",
        "--full-index",
        "--no-ext-diff",
        "--no-textconv",
        "HEAD",
        "--",
    )
    patch = subprocess.check_output(common, cwd=ROOT)
    raw_paths = subprocess.check_output(
        (
            "git",
            "--no-pager",
            "diff",
            "--name-only",
            "-z",
            "--no-ext-diff",
            "--no-textconv",
            "HEAD",
            "--",
        ),
        cwd=ROOT,
    )
    head = subprocess.check_output(
        ("git", "rev-parse", "HEAD"),
        cwd=ROOT,
        text=True,
    ).strip()
    paths = tuple(
        item.decode("utf-8")
        for item in raw_paths.split(b"\0")
        if item
    )
    return TrackedTreeState(
        head=head,
        patch_sha256=hashlib.sha256(patch).hexdigest(),
        changed_paths=paths,
    )


def run_gate(
    gate: Gate,
    environment: Mapping[str, str],
) -> GateResult:
    print(f"\n━━ {gate.name}: {gate.purpose}")
    print("+ " + " ".join(gate.command), flush=True)
    before = tracked_tree_state()
    completed = subprocess.run(
        gate.command,
        cwd=ROOT,
        env=environment,
        check=False,
    )
    after = tracked_tree_state()
    mutated = ()
    if after != before:
        mutated = tuple(
            sorted(set(before.changed_paths) | set(after.changed_paths))
        ) or ("<tracked tree or HEAD>",)
        print(
            "FAIL: gate changed tracked files: " + ", ".join(mutated),
            file=sys.stderr,
        )
    state = "PASS" if completed.returncode == 0 and not mutated else "FAIL"
    print(f"{state}: {gate.name} (exit {completed.returncode})")
    return GateResult(gate, completed.returncode, mutated)


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
