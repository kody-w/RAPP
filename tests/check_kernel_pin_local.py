#!/usr/bin/env python3
"""Verify the frozen kernel pin against repository-local bytes only."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
PIN_PATH = ROOT / "KERNEL_PIN.json"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def verify_local_pin(
    root: Path = ROOT,
    pin_path: Path = PIN_PATH,
) -> tuple[list[tuple[str, str, str]], list[str]]:
    errors: list[str] = []
    results: list[tuple[str, str, str]] = []
    try:
        pin = json.loads(pin_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return results, [f"cannot read {pin_path}: {error}"]

    if pin.get("spec") != "rapp-distro/1.0":
        errors.append("KERNEL_PIN.json must declare rapp-distro/1.0")
    frozen = pin.get("kernel", {}).get("frozen")
    if not isinstance(frozen, dict) or not frozen:
        errors.append("KERNEL_PIN.json kernel.frozen must be a non-empty object")
        return results, errors

    for relative, expected in sorted(frozen.items()):
        posix = PurePosixPath(relative) if isinstance(relative, str) else None
        if (
            posix is None
            or posix.is_absolute()
            or ".." in posix.parts
            or not relative
        ):
            errors.append(f"unsafe frozen path: {relative!r}")
            continue
        if not isinstance(expected, str) or SHA256_RE.fullmatch(expected) is None:
            errors.append(f"invalid frozen SHA-256 for {relative}")
            continue

        path = root.joinpath(*posix.parts)
        if not path.is_file() or path.is_symlink():
            actual = "MISSING"
            errors.append(f"missing regular frozen file: {relative}")
        else:
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != expected:
                errors.append(
                    f"frozen byte mismatch: {relative}: "
                    f"expected {expected}, got {actual}"
                )
        results.append((relative, expected, actual))
    return results, errors


def main() -> int:
    results, errors = verify_local_pin()
    for relative, expected, actual in results:
        state = "OK" if expected == actual else "FAIL"
        print(f"{state:4} {relative}")
        print(f"     pinned={expected} local={actual}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"\nLocal kernel pin verified ({len(results)} frozen files; no network)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
