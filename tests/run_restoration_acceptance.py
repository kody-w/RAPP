#!/usr/bin/env python3
"""Machine-checkable stop condition for the provenance-preserving restoration."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BANNER_MARKERS = (
    'class="current-note"',
    'class="section-note"',
    'class="history-context"',
    'class="rapp-2026-note"',
    'class="rapp-local-boundary"',
)


@dataclass(frozen=True)
class Gate:
    name: str
    command: tuple[str, ...]


GATES = (
    Gate(
        "source-ledger",
        (sys.executable, "tools/build_historical_source_ledger.py", "--check"),
    ),
    Gate(
        "vault-bundle",
        (sys.executable, "tools/build_vault_bundle.py", "--check"),
    ),
    Gate("pages", (sys.executable, "tests/check_pages.py")),
    Gate("node-contract", ("node", "tests/run-tests.mjs")),
    Gate("vault", ("node", "tests/vault-check.mjs")),
    Gate("plant-compatibility", ("bash", "installer/test_plant.sh")),
    Gate("metropolis", ("bash", "tests/scenarios/16-metropolis-tracker.sh")),
    Gate(
        "metropolis-federation",
        ("bash", "tests/scenarios/20-cross-tracker-federation.sh"),
    ),
    Gate("grail", (sys.executable, "tests/check_kernel_pin_local.py")),
    Gate(
        "canonical-conformance",
        (sys.executable, "tests/run_rapp1_conformance.py"),
    ),
)


def preflight() -> list[str]:
    errors: list[str] = []
    html_paths = sorted(ROOT.rglob("*.html"))
    for path in html_paths:
        relative = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        if "Retired semantic tombstone" in text:
            errors.append(f"{relative}: semantic tombstone remains")
        for marker in BANNER_MARKERS:
            if marker in text:
                errors.append(f"{relative}: intrusive restoration banner {marker}")
    diff = subprocess.run(
        ("git", "diff", "--check"),
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if diff.returncode:
        errors.append(diff.stdout + diff.stderr)
    return errors


def main() -> int:
    failures = preflight()
    if failures:
        print("RESTORATION PREFLIGHT FAILED", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1

    for gate in GATES:
        print(f"\n=== {gate.name} ===", flush=True)
        result = subprocess.run(gate.command, cwd=ROOT, check=False)
        if result.returncode:
            print(
                f"\nRESTORATION NOT ACCEPTED: {gate.name} exited "
                f"{result.returncode}",
                file=sys.stderr,
            )
            return result.returncode

    print("\nRESTORATION ACCEPTED: every machine-checkable gate passed")
    print(
        "Authenticated RAPP/1 acceptance remains blocked by the three "
        "owner-only actions in RAPP1_STATUS.md."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
