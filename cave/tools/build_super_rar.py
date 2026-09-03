#!/usr/bin/env python3
"""Validate the sealed, inert Cave catalog ledgers without generating files.

The former super-RAR builder is retired. This target-owned replacement accepts
only ``--check`` and verifies that the committed Cave ledgers remain historical,
non-streamable, non-distributable, and internally consistent. It never rebuilds
an index, discovers new entries, writes a file, or publishes an artifact.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


CAVE = Path(__file__).resolve().parents[1]
NEIGHBORHOOD_RAPPID = (
    "rappid:@kody-w/rapp-cave:"
    "ca72ca0a3cb90c357fb09e38b02f85f09935cacbf61e94740c57f1eb30a73e0a"
)
RAR_NOTE = (
    "Inert historical ledger. Every entry is retired, non-streamable, and "
    "non-distributable. Paths and hashes are evidence only; this file is not "
    "a registry, download index, installation source, or acceptance record."
)
SUPER_RAR_NOTE = (
    "Inert historical Cave inventory. Every entry is retired, non-streamable, "
    "and non-distributable. No entry may be fetched, installed, or executed "
    "from this ledger."
)

EXPECTED_HEADERS = {
    "cubbies/index.json": {
        "schema": "rapp-cave-cubbies/1.0",
        "status": "retired",
        "active_distribution": False,
        "streamable": False,
        "neighborhood_rappid": NEIGHBORHOOD_RAPPID,
        "cubbies": [],
    },
    "rar/index.json": {
        "schema": "rapp-rar-index/1.1",
        "status": "retired",
        "active_distribution": False,
        "streamable": False,
        "neighborhood_rappid": NEIGHBORHOOD_RAPPID,
        "rar_for": "kody-w/RAPP",
        "kind": "workspace",
        "raw_url_prefix": None,
        "note": RAR_NOTE,
    },
    "super-rar/index.json": {
        "schema": "rapp-super-rar/1.0",
        "status": "retired",
        "active_distribution": False,
        "streamable": False,
        "neighborhood_rappid": NEIGHBORHOOD_RAPPID,
        "raw_url_prefix": None,
        "note": SUPER_RAR_NOTE,
    },
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(relative: str) -> tuple[dict | None, list[str]]:
    path = CAVE / relative
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"cannot read valid JSON: {exc}"]
    if not isinstance(value, dict):
        return None, ["top-level value must be an object"]
    return value, []


def _entries(relative: str, document: dict) -> list[tuple[str, int, object]]:
    if relative == "rar/index.json":
        groups = ("agents", "rapps")
    if relative == "super-rar/index.json":
        groups = ("entries",)
    if relative not in ("rar/index.json", "super-rar/index.json"):
        return []

    result = []
    for group in groups:
        values = document.get(group)
        if isinstance(values, list):
            result.extend(
                (group, index, entry) for index, entry in enumerate(values)
            )
    return result


def _validate_entry(group: str, index: int, entry: object) -> list[str]:
    prefix = f"{group}[{index}]"
    if not isinstance(entry, dict):
        return [f"{prefix} must be an object"]

    errors = []
    expected = {
        "status": "retired",
        "active_distribution": False,
        "streamable": False,
    }
    for key, value in expected.items():
        if entry.get(key) != value:
            errors.append(f"{prefix}.{key} must be {value!r}")

    relative = entry.get("path")
    if not isinstance(relative, str) or not relative:
        errors.append(f"{prefix}.path must be a non-empty repository-relative path")
        return errors
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or "://" in relative:
        errors.append(f"{prefix}.path is not a safe repository-relative path")
        return errors

    source = CAVE / path
    if not source.exists():
        errors.append(f"{prefix}.path does not exist: {relative}")
        return errors

    expected_hash = entry.get("sha256")
    if expected_hash is not None:
        if not source.is_file():
            errors.append(f"{prefix}.sha256 may describe only a file")
        elif expected_hash != _sha256(source):
            errors.append(f"{prefix}.sha256 does not match retained bytes")

    if "rapplications/rapp-installer" in relative:
        if entry.get("immutable_prepared_snapshot") is not True:
            errors.append(
                f"{prefix} must identify the prepared installer as immutable history"
            )
    return errors


def _validate_catalog(relative: str) -> list[str]:
    document, errors = _load(relative)
    if document is None:
        return errors

    for key, expected in EXPECTED_HEADERS[relative].items():
        if document.get(key) != expected:
            errors.append(f"{key} must be {expected!r}")

    for group, values in (
        ("agents", document.get("agents")),
        ("rapps", document.get("rapps")),
        ("entries", document.get("entries")),
    ):
        if group in document and not isinstance(values, list):
            errors.append(f"{group} must be an array")

    for group, index, entry in _entries(relative, document):
        errors.extend(_validate_entry(group, index, entry))

    if relative == "rar/index.json":
        verification = document.get("verification")
        if not isinstance(verification, dict):
            errors.append("verification must be an object")
        else:
            for key in (
                "authorizes_fetch",
                "authorizes_installation",
                "authorizes_execution",
            ):
                if verification.get(key) is not False:
                    errors.append(f"verification.{key} must be false")

    if relative == "super-rar/index.json":
        entries = document.get("entries")
        if isinstance(entries, list):
            if document.get("count") != len(entries):
                errors.append("count must match the number of retained entries")
            by_kind = {}
            for entry in entries:
                if isinstance(entry, dict) and isinstance(entry.get("kind"), str):
                    kind = entry["kind"]
                    by_kind[kind] = by_kind.get(kind, 0) + 1
            if document.get("by_kind") != by_kind:
                errors.append("by_kind must match the retained entry kinds")

    return errors


def _validate_steward() -> list[str]:
    path = CAVE / "agents/rar_steward_agent.py"
    source = path.read_text(encoding="utf-8")
    errors = []
    for marker in (
        "import subprocess",
        "import urllib",
        "urlopen(",
        "gh\", \"issue",
        "file_issues",
        "INDEX_URL",
        "STEWARD_TRACKER",
    ):
        if marker in source:
            errors.append(f"retired steward still contains side-effect marker {marker!r}")
    for marker in ("410 Gone", '"status": "retired"', '"streamable": False'):
        if marker not in source:
            errors.append(f"retired steward is missing marker {marker!r}")
    return errors


def main() -> int:
    if sys.argv[1:] != ["--check"]:
        print(
            "RETIRED: this tool validates sealed historical ledgers only. "
            "Use --check; no rebuild or write mode exists."
        )
        return 2

    failed = False
    for relative in EXPECTED_HEADERS:
        errors = _validate_catalog(relative)
        if errors:
            failed = True
            print(f"DRIFT: {relative}")
            for error in errors:
                print(f"  - {error}")

    steward_errors = _validate_steward()
    if steward_errors:
        failed = True
        print("DRIFT: agents/rar_steward_agent.py")
        for error in steward_errors:
            print(f"  - {error}")

    if failed:
        return 1

    print(
        "Cave historical ledgers are inert, non-streamable, "
        "non-distributable, and internally consistent."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
