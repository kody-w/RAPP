#!/usr/bin/env python3
"""Strict syntax and retired-test inventory checks for the local gate."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "tests/fixtures/rapp1-retired-test-inventory.json"
LEGACY_FORMS = (
    "brainstem-egg/",
    "rapp-frame/1.0",
    "rapp-rappid/2.0",
    "rappid:v2:",
    "conversation_history",
    "assistant_response",
)


class DuplicateKeyError(ValueError):
    pass


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate object member {key!r}")
        result[key] = value
    return result


def _tracked(*patterns: str) -> list[Path]:
    command = [
        "git",
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
        "-z",
        "--",
        *patterns,
    ]
    raw = subprocess.check_output(command, cwd=ROOT)
    return [
        ROOT / item.decode("utf-8")
        for item in raw.split(b"\0")
        if item
    ]


def check_json() -> int:
    files = _tracked("*.json")
    for path in files:
        json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
        )
    return len(files)


def check_html() -> int:
    files = _tracked("*.html")
    for path in files:
        parser = HTMLParser(convert_charrefs=True)
        parser.feed(path.read_text(encoding="utf-8"))
        parser.close()
    return len(files)


def _check_commands(tool: str, flag: str, patterns: tuple[str, ...]) -> int:
    files = _tracked(*patterns)
    failures = []
    for path in files:
        result = subprocess.run(
            [tool, flag, os.fspath(path)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode:
            detail = (result.stderr or result.stdout).strip()
            failures.append(f"{path.relative_to(ROOT)}: {detail}")
    if failures:
        raise AssertionError("\n".join(failures))
    return len(files)


def check_shell() -> int:
    return _check_commands("bash", "-n", ("*.sh",))


def check_javascript() -> int:
    return _check_commands("node", "--check", ("*.js", "*.mjs"))


def check_legacy_inventory() -> tuple[int, int]:
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    quarantine = inventory["quarantine"]
    root = ROOT / quarantine["root"]
    fixture_paths = sorted(root.rglob("*.txt"))
    original_paths = [
        "tests/" + path.relative_to(root).as_posix()[:-4]
        for path in fixture_paths
    ]
    encoded = ("\n".join(original_paths) + "\n").encode("utf-8")
    content_set = hashlib.sha256()

    assert len(fixture_paths) == quarantine["path_count"]
    assert hashlib.sha256(encoded).hexdigest() == quarantine["path_set_sha256"]
    for fixture, original in zip(fixture_paths, original_paths, strict=True):
        content_set.update(original.encode("utf-8"))
        content_set.update(b"\0")
        content_set.update(fixture.read_bytes())
        content_set.update(b"\0")
        assert not (fixture.stat().st_mode & stat.S_IXUSR), (
            f"quarantined fixture remains executable: {fixture.relative_to(ROOT)}"
        )
        assert not (ROOT / original).exists(), (
            f"retired positive test remains executable: {original}"
        )
    assert content_set.hexdigest() == quarantine["content_set_sha256"], (
        "quarantined historical fixture bytes drifted"
    )

    allowed = {
        (entry["path"], form)
        for entry in inventory["active_legacy_inputs"]
        for form in entry["forms"]
    }
    found = set()
    active_files = [
        path
        for path in (
            _tracked("tests/*.py", "tests/*.sh", "tests/*.js", "tests/*.mjs")
            + _tracked("rapp_brainstem/test_*.py", "installer/test_plant.sh")
        )
        if "tests/fixtures/" not in path.relative_to(ROOT).as_posix()
        and path.relative_to(ROOT).as_posix() != "tests/check_rapp1_static.py"
    ]
    for path in active_files:
        relative = path.relative_to(ROOT).as_posix()
        source = path.read_text(encoding="utf-8")
        for form in LEGACY_FORMS:
            if form in source:
                found.add((relative, form))

    unexpected = sorted(found - allowed)
    stale_allowlist = sorted(allowed - found)
    assert not unexpected, f"unclassified legacy-positive test forms: {unexpected}"
    assert not stale_allowlist, f"stale legacy-test inventory entries: {stale_allowlist}"
    return len(fixture_paths), len(found)


def main() -> int:
    checks = (
        ("strict JSON", check_json),
        ("HTML parse", check_html),
        ("shell syntax", check_shell),
        ("JavaScript syntax", check_javascript),
        ("legacy test inventory", check_legacy_inventory),
    )
    failures = []
    for label, check in checks:
        try:
            result = check()
            print(f"PASS: {label} ({result})")
        except Exception as error:
            failures.append((label, error))
            print(f"FAIL: {label}: {error}", file=sys.stderr)
    if failures:
        print(f"\n{len(failures)} static inspection(s) failed", file=sys.stderr)
        return 1
    print("\nStatic syntax and strict inspections passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
