#!/usr/bin/env python3
"""Strict syntax and retired-test inventory checks for the local gate."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "tests/fixtures/rapp1-retired-test-inventory.json"
SUITE_INVENTORY_PATH = ROOT / "tests/rapp1-test-suite-inventory.json"
LIVE_INVENTORY_PATH = ROOT / "tests/rapp1-live-surface-inventory.json"
ECOSYSTEM_MAP_PATH = ROOT / "ECOSYSTEM_MAP.md"
WORKFLOW_ROOT = ROOT / ".github/workflows"
EXPECTED_WORKFLOW_USE_COUNTS = {
    "cave-super-rar.yml": 2,
    "drift-lint.yml": 1,
    "kernel-freeze.yml": 2,
    "plant-approved-place.yml": 2,
    "rapp1-conformance.yml": 3,
}
WORKFLOW_USES_RE = re.compile(
    r"""^\s*(?:-\s*)?uses\s*:\s*
        (?:
            "(?P<double>[^"]+)"
          | '(?P<single>[^']+)'
          | (?P<bare>[^\s#]+)
        )
        \s*(?:\#.*)?$
    """,
    re.VERBOSE,
)
LEGACY_FORMS = (
    "brainstem-egg/",
    "rapp-frame/1.0",
    "rapp-rappid/2.0",
    "rappid:v2:",
    "conversation_history",
    "assistant_response",
)
NONCURRENT_MAP_MARKERS = (
    "external template",
    "historical",
    "migration-only",
    "not a repository-local implementation path",
    "retired",
    "superseded",
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
        if item and not item.decode("utf-8").startswith("tests/.rapp1-work/")
    ]


def _cached_relative_paths() -> tuple[str, ...]:
    raw = subprocess.check_output(
        ("git", "ls-files", "--cached", "-z"),
        cwd=ROOT,
    )
    return tuple(
        item.decode("utf-8")
        for item in raw.split(b"\0")
        if item
    )


def check_json() -> int:
    files = [
        ROOT / relative
        for relative in _cached_relative_paths()
        if Path(relative).suffix.lower() == ".json"
    ]
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
    return _check_commands("node", "--check", ("*.js", "*.mjs", "*.cjs"))


def check_untracked_executables() -> int:
    raw = subprocess.check_output(
        (
            "git",
            "ls-files",
            "--others",
            "--exclude-standard",
            "-z",
        ),
        cwd=ROOT,
    )
    untracked = [
        ROOT / item.decode("utf-8")
        for item in raw.split(b"\0")
        if item
        and not item.decode("utf-8").startswith("tests/.rapp1-work/")
    ]
    executable = sorted(
        path.relative_to(ROOT).as_posix()
        for path in untracked
        if path.is_file()
        and path.stat().st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    )
    assert not executable, (
        "untracked executable paths must be removed, staged, or explicitly "
        f"quarantined as non-executable fixtures: {executable}"
    )
    return len(untracked)


def check_live_surface_inventory() -> dict[str, int]:
    inventory = json.loads(
        LIVE_INVENTORY_PATH.read_text(encoding="utf-8"),
        object_pairs_hook=_unique_object,
    )
    assert inventory["schema"] == "rapp1-live-surface-inventory/1.0"
    assert set(inventory["categories"]) == {
        "installer",
        "marketing",
        "containment",
        "browser",
        "wire",
    }
    assert "git ls-files" in inventory["count_policy"]
    assert not {"path_count", "tracked_count", "total_count"} & set(inventory), (
        "live inventory must derive repository counts instead of storing totals"
    )

    tracked = set(_cached_relative_paths())
    counts = {"tracked": len(tracked)}
    for category, paths in inventory["categories"].items():
        assert paths, f"empty live inventory category: {category}"
        assert len(paths) == len(set(paths)), (
            f"duplicate path in live inventory category {category}"
        )
        for relative in paths:
            path = Path(relative)
            assert not path.is_absolute() and ".." not in path.parts, (
                f"unsafe live inventory path: {relative}"
            )
            assert relative in tracked, (
                f"untracked or stale {category} inventory path: {relative}"
            )
        counts[category] = len(paths)

    declared_installers = set(inventory["categories"]["installer"])
    installer_candidates = {
        relative
        for relative in tracked
        if re.fullmatch(
            r"(?:(?:docs|community_rapp|installer)/)?"
            r"install(?:-swarm)?\.(?:sh|ps1|cmd|command)",
            relative,
        )
        or relative
        in {
            "deploy.sh",
            "deploy.ps1",
            "azuredeploy.json",
            "installer/azuredeploy.json",
            "installer/start-local.sh",
        }
    }
    assert installer_candidates == declared_installers, (
        "live installer inventory drifted: "
        f"missing={sorted(installer_candidates - declared_installers)}, "
        f"stale={sorted(declared_installers - installer_candidates)}"
    )

    boundary = inventory["protected_boundaries"]
    assert boundary["prepared_snapshot_prefix"] == (
        "cave/rapplications/rapp-installer/"
    )
    assert any(
        path.startswith(boundary["prepared_snapshot_prefix"])
        for path in tracked
    ), "prepared snapshot boundary no longer matches tracked paths"
    assert set(boundary["immutable_grail_paths"]) == set(
        json.loads((ROOT / "KERNEL_PIN.json").read_text(encoding="utf-8"))[
            "kernel"
        ]["frozen"]
    )
    assert boundary["archive_manifest"] in tracked
    return counts


def extract_workflow_uses(source: str) -> tuple[tuple[int, str], ...]:
    references = []
    for line_number, line in enumerate(source.splitlines(), 1):
        if not re.match(r"^\s*(?:-\s*)?uses\s*:", line):
            continue
        match = WORKFLOW_USES_RE.fullmatch(line)
        assert match, f"unparsed workflow uses at line {line_number}: {line!r}"
        value = next(
            group for group in match.group("double", "single", "bare") if group
        )
        references.append((line_number, value))
    return tuple(references)


def workflow_action_references() -> tuple[tuple[str, int, str], ...]:
    references = []
    workflows = sorted((*WORKFLOW_ROOT.glob("*.yml"), *WORKFLOW_ROOT.glob("*.yaml")))
    for path in workflows:
        for line_number, value in extract_workflow_uses(
            path.read_text(encoding="utf-8")
        ):
            references.append((path.name, line_number, value))
    return tuple(references)


def check_workflow_actions() -> int:
    references = workflow_action_references()
    counts = {
        name: sum(1 for path, _, _ in references if path == name)
        for name in EXPECTED_WORKFLOW_USE_COUNTS
    }
    assert counts == EXPECTED_WORKFLOW_USE_COUNTS, (
        f"workflow action-reference counts drifted: {counts!r}"
    )
    assert len(references) == sum(EXPECTED_WORKFLOW_USE_COUNTS.values())
    for path, line_number, value in references:
        if value.startswith("./"):
            continue
        assert "@" in value, f"{path}:{line_number}: action ref has no pin: {value}"
        _, ref = value.rsplit("@", 1)
        assert re.fullmatch(r"[0-9a-f]{40}", ref), (
            f"{path}:{line_number}: action ref is not an immutable commit: {value}"
        )
    return len(references)


def validate_ecosystem_map_paths(
    source: str,
    root: Path = ROOT,
) -> int:
    match = re.search(
        r"^## §6 — Implementation map.*?$\n([\s\S]*?)(?=^## §7 )",
        source,
        flags=re.MULTILINE,
    )
    assert match, "ECOSYSTEM_MAP.md has no bounded §6 implementation map"
    section_start = source[: match.start(1)].count("\n") + 1
    section_lines = match.group(1).splitlines()
    stale_web = [
        f"line {line_number}: {line.strip()}"
        for line_number, line in enumerate(source.splitlines(), 1)
        if "utils/web/" in line
        and not any(marker in line.lower() for marker in NONCURRENT_MAP_MARKERS)
    ]
    assert not stale_web, (
        "ECOSYSTEM_MAP has unretired references to the removed utils/web tree: "
        f"{stale_web}"
    )

    declarations = 0
    missing = []
    for line_number, line in enumerate(section_lines, section_start):
        if not line.startswith("|"):
            continue
        cells = line.split("|")
        first_cell = cells[1].strip()
        if first_cell.startswith("RAR:"):
            continue
        tokens = re.findall(r"`([^`]+)`", first_cell)
        previous_parent = None
        for token in tokens:
            if "<" in token or ">" in token:
                continue
            candidate = token
            if "/" not in candidate and previous_parent is not None:
                candidate = (previous_parent / candidate).as_posix()
            declared = Path(candidate.rstrip("/"))
            previous_parent = declared.parent
            declarations += 1
            if any(marker in line.lower() for marker in NONCURRENT_MAP_MARKERS):
                continue
            if any(character in candidate for character in "*?["):
                exists = any(root.glob(candidate))
            else:
                exists = (root / declared).exists()
            if not exists:
                missing.append(f"line {line_number}: {candidate}")
    assert not missing, (
        "current ECOSYSTEM_MAP implementation paths are missing without an "
        f"explicit retirement marker: {missing}"
    )
    return declarations


def check_ecosystem_map_paths() -> int:
    return validate_ecosystem_map_paths(
        ECOSYSTEM_MAP_PATH.read_text(encoding="utf-8")
    )


def discovered_test_candidates(inventory: dict) -> set[str]:
    raw = subprocess.check_output(
        (
            "git",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
            "--",
            "tests",
        ),
        cwd=ROOT,
    )
    suffixes = set(inventory["candidate_suffixes"])
    excluded = tuple(inventory["excluded_prefixes"])
    return {
        item.decode("utf-8")
        for item in raw.split(b"\0")
        if item
        and Path(item.decode("utf-8")).suffix in suffixes
        and not item.decode("utf-8").startswith(excluded)
    }


def validate_test_suite_inventory(
    inventory: dict,
    discovered: set[str],
) -> int:
    entries = inventory["entries"]
    paths = [entry["path"] for entry in entries]
    assert len(paths) == len(set(paths)), "duplicate active-suite inventory path"
    for entry in entries:
        assert entry["reason"].strip(), f"missing rationale: {entry['path']}"
        assert entry["disposition"] in {
            "canonical-direct",
            "canonical-child",
            "canonical-helper",
            "canonical-entrypoint",
            "support",
            "external",
            "credentialed-destructive",
            "destructive-network",
        }, f"invalid disposition: {entry!r}"
        if entry["disposition"] in {
            "canonical-direct",
            "canonical-child",
            "canonical-helper",
        }:
            assert entry.get("gate"), f"canonical path has no gate: {entry['path']}"
    missing = sorted(discovered - set(paths))
    stale = sorted(set(paths) - discovered)
    assert not missing, f"unclassified executable test candidates: {missing}"
    assert not stale, f"stale active-suite inventory paths: {stale}"
    return len(paths)


def validate_test_executable_references(
    inventory: dict,
    sources: dict[str, str],
) -> int:
    forbidden = tuple(inventory["forbidden_executable_references"])
    offenders = sorted(
        (path, marker)
        for path, source in sources.items()
        for marker in forbidden
        if marker in source
    )
    assert not offenders, (
        f"executable tests reference missing retired files: {offenders}"
    )
    return len(sources)


def check_test_suite_inventory() -> int:
    inventory = json.loads(SUITE_INVENTORY_PATH.read_text(encoding="utf-8"))
    discovered = discovered_test_candidates(inventory)
    count = validate_test_suite_inventory(inventory, discovered)
    validate_test_executable_references(
        inventory,
        {
            path: (ROOT / path).read_text(encoding="utf-8")
            for path in discovered
        },
    )
    return count


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
    file_entries = {
        entry["fixture"]: entry for entry in quarantine["files"]
    }

    assert len(fixture_paths) == quarantine["path_count"]
    assert len(file_entries) == len(fixture_paths)
    assert hashlib.sha256(encoded).hexdigest() == quarantine["path_set_sha256"]
    for fixture, original in zip(fixture_paths, original_paths):
        relative_fixture = fixture.relative_to(ROOT).as_posix()
        entry = file_entries.get(relative_fixture)
        assert entry is not None, f"quarantine file has no rationale: {relative_fixture}"
        assert entry["source_path"] == original
        assert entry["rationale"].strip()
        assert entry["sha256"] == hashlib.sha256(fixture.read_bytes()).hexdigest()
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
        ("untracked executable containment", check_untracked_executables),
        ("live surface inventory", check_live_surface_inventory),
        ("immutable workflow actions", check_workflow_actions),
        ("ecosystem implementation map", check_ecosystem_map_paths),
        ("active test-suite inventory", check_test_suite_inventory),
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
