#!/usr/bin/env python3
"""Verify canonical kernel.json shape and any declared local vendored bytes."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
PIN_PATH = ROOT / "kernel.json"
REQUIRED = {"kernel", "sha", "version", "path", "kernel_blob"}
OPTIONAL = {
    "pinned",
    "ui_path",
    "ui_blob",
    "soul_path",
    "soul_blob",
    "contract",
    "rule",
    "vendored",
}
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
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

    if not isinstance(pin, dict):
        return results, ["kernel.json must be a JSON object"]
    missing = sorted(REQUIRED - set(pin))
    extra = sorted(set(pin) - REQUIRED - OPTIONAL)
    if missing:
        errors.append(f"kernel.json missing required keys: {', '.join(missing)}")
    if extra:
        errors.append(f"kernel.json has unsupported keys: {', '.join(extra)}")
    if pin.get("kernel") != "kody-w/rapp-installer":
        errors.append("kernel.json kernel must be kody-w/rapp-installer")
    if not isinstance(pin.get("sha"), str) or SHA1_RE.fullmatch(pin["sha"]) is None:
        errors.append("kernel.json sha must be a 40-hex commit")
    if not isinstance(pin.get("kernel_blob"), str) or SHA1_RE.fullmatch(pin["kernel_blob"]) is None:
        errors.append("kernel.json kernel_blob must be a 40-hex git blob")
    if not isinstance(pin.get("version"), str) or not pin["version"]:
        errors.append("kernel.json version must be a non-empty string")
    kernel_path = pin.get("path")
    if not isinstance(kernel_path, str) or not kernel_path:
        errors.append("kernel.json path must be a non-empty relative path")
    else:
        posix = PurePosixPath(kernel_path)
        if posix.is_absolute() or ".." in posix.parts:
            errors.append("kernel.json path must be a safe relative path")

    vendored = pin.get("vendored", {})
    if not isinstance(vendored, dict):
        errors.append("kernel.json vendored must be an object")
        return results, errors

    for relative, expected in sorted(vendored.items()):
        posix = PurePosixPath(relative) if isinstance(relative, str) else None
        if (
            posix is None
            or posix.is_absolute()
            or ".." in posix.parts
            or not relative
        ):
            errors.append(f"unsafe vendored path: {relative!r}")
            continue
        if not isinstance(expected, str) or SHA256_RE.fullmatch(expected) is None:
            errors.append(f"invalid vendored SHA-256 for {relative}")
            continue

        path = root.joinpath(*posix.parts)
        if not path.is_file() or path.is_symlink():
            actual = "MISSING"
            errors.append(f"missing regular vendored file: {relative}")
        else:
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != expected:
                errors.append(
                    f"vendored byte mismatch: {relative}: "
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
    print(f"\nLocal kernel pin verified ({len(results)} vendored files; no network)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
