from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "RAPP1_ADAPTATION_INVENTORY.json"
LEDGER_PATH = ROOT / "HISTORICAL_SOURCE_LEDGER.json"
REQUIRED_GAPS = {
    "canonicalization_addressing",
    "identity_rappid",
    "exact_chat_wire",
    "frames",
    "eggs",
    "registry_trust_freshness",
    "grail_installer_pin",
    "side_effects",
}
OWNER_DEPENDENCIES = {"OA-REG", "OA-ROOT", "OA-INVITE"}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _tracked_paths() -> list[str]:
    raw = subprocess.check_output(("git", "ls-files", "-z"), cwd=ROOT)
    return sorted(
        item.decode("utf-8")
        for item in raw.split(b"\0")
        if item
    )


def _path_digest(paths: list[str]) -> str:
    payload = "".join(f"{path}\n" for path in sorted(paths))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _source_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(("git", "show", f"{commit}:{path}"), cwd=ROOT)


def _source_blob(commit: str, path: str) -> str:
    return subprocess.check_output(
        ("git", "rev-parse", f"{commit}:{path}"),
        cwd=ROOT,
        text=True,
    ).strip()


def _python_symbols(source: bytes) -> set[str]:
    tree = ast.parse(source.decode("utf-8"))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }


def _normalized_line_coverage(source: bytes, restored: bytes) -> float:
    restored_text = re.sub(r"\s+", " ", restored.decode("utf-8"))
    source_lines = [
        re.sub(r"\s+", " ", line.strip())
        for line in source.decode("utf-8").splitlines()
        if len(re.sub(r"\s+", " ", line.strip())) >= 8
    ]
    assert source_lines
    return sum(line in restored_text for line in source_lines) / len(source_lines)


def test_adaptation_inventory_is_candidate_evidence_not_authority():
    inventory = _load(INVENTORY_PATH)
    assert inventory["schema"] == "rapp1-adaptation-inventory/1.0"
    assert inventory["record_kind"] == "candidate-compliance-adaptation-inventory"
    assert inventory["status"] == "candidate"
    assert inventory["is_section_13_registry"] is False
    assert inventory["authenticated_acceptance_allowed"] is False
    assert inventory["repository"]["conformance"] == (
        "not-yet-fully-rapp-1-conformant"
    )
    policy = inventory["policies"]["adapt_dont_kill"]
    assert policy["preserve_data_exhaust"] is True
    assert policy["restore_fullest_artifact_first"] is True
    assert policy["blank_refusals_allowed_as_target_state"] is False
    assert policy["semantic_tombstones_allowed_as_target_state"] is False


def test_inventory_path_sets_match_the_tracked_tree():
    inventory = _load(INVENTORY_PATH)
    tracked = _tracked_paths()
    snapshot = inventory["snapshot"]
    assert snapshot["tracked_path_count"] == len(tracked)
    assert snapshot["tracked_path_set_sha256"] == _path_digest(tracked)

    seen: set[str] = set()
    for record in inventory["path_sets"]:
        assert record["id"] not in seen
        seen.add(record["id"])
        selector = record["selector"]
        if selector["type"] == "git-prefix":
            paths = [
                path
                for path in tracked
                if path.startswith(selector["prefix"])
            ]
        elif selector["type"] == "explicit":
            paths = sorted(selector["paths"])
            assert all(path in tracked for path in paths)
        else:
            raise AssertionError(f"unsupported path-set selector: {selector}")
        assert record["expected_count"] == len(paths), record["id"]
        assert record["path_set_sha256"] == _path_digest(paths), record["id"]


def test_every_surface_has_the_complete_gap_and_acceptance_contract():
    inventory = _load(INVENTORY_PATH)
    path_set_ids = {record["id"] for record in inventory["path_sets"]}
    surface_ids = [record["id"] for record in inventory["surfaces"]]
    assert len(surface_ids) == len(set(surface_ids))
    assert inventory["completeness"]["surface_count"] == len(surface_ids)
    assert set(inventory["completeness"]["required_gap_fields"]) == REQUIRED_GAPS

    for surface in inventory["surfaces"]:
        assert set(surface["gap_matrix"]) == REQUIRED_GAPS, surface["id"]
        assert surface["desired_state"] not in {
            "deleted",
            "removed",
            "tombstone",
            "tombstone-shell",
        }
        assert surface["next_local_adaptation"].strip()
        assert surface["acceptance_tests"]
        assert surface["data_exhaust"]["preserve"] is True
        assert set(surface["path_set_refs"]) <= path_set_ids
        assert set(surface["owner_dependencies"]) <= OWNER_DEPENDENCIES
        for relative in surface.get("paths", []):
            assert (ROOT / relative).exists(), (surface["id"], relative)


def test_owner_dependencies_match_the_status_blockers():
    inventory = _load(INVENTORY_PATH)
    dependencies = inventory["owner_dependencies"]
    assert {item["id"] for item in dependencies} == OWNER_DEPENDENCIES
    assert all(item["status"] == "owner-action-required" for item in dependencies)
    status = (ROOT / "RAPP1_STATUS.md").read_text(encoding="utf-8")
    for phrase in (
        "Signed monotonic registry and out-of-band anchor",
        "Lawful root re-anchor",
        "Signed replacement invite",
    ):
        assert f"**{phrase}**" in status


def test_historical_source_ledger_verifies_old_and_restored_bytes():
    ledger = _load(LEDGER_PATH)
    assert ledger["schema"] == "rapp-historical-source-ledger/1.0"
    assert ledger["record_kind"] == "candidate-restoration-provenance"
    assert ledger["status"] == "candidate"
    assert ledger["is_section_13_registry"] is False

    record_ids: set[str] = set()
    current_paths: set[str] = set()
    for record in ledger["artifacts"]:
        assert record["id"] not in record_ids
        record_ids.add(record["id"])
        relative = record["current_path"]
        assert relative not in current_paths
        current_paths.add(relative)
        current = ROOT / relative
        assert current.is_file(), relative

        source = record["source"]
        assert re.fullmatch(r"[0-9a-f]{40}", source["commit"])
        assert re.fullmatch(r"[0-9a-f]{40}", source["blob"])
        assert re.fullmatch(r"[0-9a-f]{64}", source["sha256"])
        old_bytes = _source_bytes(source["commit"], source["path"])
        assert _source_blob(source["commit"], source["path"]) == source["blob"]
        assert hashlib.sha256(old_bytes).hexdigest() == source["sha256"]
        assert len(old_bytes) == source["bytes"]

        restored = record["restored"]
        current_bytes = current.read_bytes()
        assert hashlib.sha256(current_bytes).hexdigest() == restored["sha256"], relative
        assert len(current_bytes) == restored["bytes"], relative
        assert re.fullmatch(r"[0-9a-f]{40}", restored["commit"])

        check = record["preservation_check"]
        if check["type"] == "line-subsequence":
            source_lines = [
                line.rstrip()
                for line in old_bytes.decode("utf-8").splitlines()
                if line.strip()
            ]
            restored_lines = [
                line.rstrip()
                for line in current_bytes.decode("utf-8").splitlines()
            ]
            offset = 0
            for line in restored_lines:
                if offset < len(source_lines) and line == source_lines[offset]:
                    offset += 1
            assert offset == len(source_lines), relative
        elif check["type"] == "python-symbol-superset":
            assert _python_symbols(old_bytes) <= _python_symbols(current_bytes), relative
        elif check["type"] == "normalized-line-coverage":
            coverage = _normalized_line_coverage(old_bytes, current_bytes)
            assert coverage >= check["minimum"], (
                relative,
                coverage,
                check["minimum"],
            )
            for marker in check["markers"]:
                assert marker in current_bytes.decode("utf-8"), (relative, marker)
        elif check["type"] == "marker-set":
            text = current_bytes.decode("utf-8")
            for marker in check["markers"]:
                assert marker in text, (relative, marker)
        else:
            raise AssertionError(f"unsupported preservation check: {check}")

        if record["category"] == "browser-page":
            text = current_bytes.decode("utf-8").lower()
            assert "retired semantic tombstone" not in text
            assert source["commit"] in text
            assert source["sha256"] in text


def test_every_adapted_page_is_in_the_source_ledger_and_pages_manifest():
    inventory = _load(INVENTORY_PATH)
    ledger = _load(LEDGER_PATH)
    adapted = next(
        record
        for record in inventory["path_sets"]
        if record["id"] == "PS-ADAPTED-PAGES"
    )["selector"]["paths"]
    ledger_pages = {
        record["current_path"]
        for record in ledger["artifacts"]
        if record["category"] == "browser-page"
    }
    assert set(adapted) <= ledger_pages

    manifest = _load(ROOT / "pages/_site/index.json")
    manifest_by_path = {
        page["path"]: page
        for section in manifest["sections"]
        for page in section["pages"]
    }
    for relative in adapted:
        if not relative.startswith("pages/"):
            continue
        page = manifest_by_path[relative.removeprefix("pages/")]
        assert page["classification"] == "adapted_historical_page"
        assert page["status"] == "adapted-historical"
        assert page["navigation"] is False


def test_machine_discovery_links_the_inventory_and_source_ledger():
    discovery = _load(ROOT / "rapp-ai.json")
    hrefs = {entry["href"] for entry in discovery["entrypoints"]}
    assert "RAPP1_ADAPTATION_INVENTORY.json" in hrefs
    assert "HISTORICAL_SOURCE_LEDGER.json" in hrefs
    guide = (ROOT / "llms.txt").read_text(encoding="utf-8")
    assert "RAPP1_ADAPTATION_INVENTORY.json" in guide
    assert "HISTORICAL_SOURCE_LEDGER.json" in guide


def test_preservation_metric_detects_a_removed_historical_line():
    source = _source_bytes(
        "8c5555be80357e795090d79c4fb5a33beb0eaab8",
        "pages/onboarding.html",
    )
    restored = (ROOT / "pages/onboarding.html").read_bytes()
    assert _normalized_line_coverage(source, restored) == 1.0

    restored_text = restored.decode("utf-8")
    unique_line = next(
        line
        for line in source.decode("utf-8").splitlines()
        if len(re.sub(r"\s+", " ", line.strip())) >= 32
        and restored_text.count(line) == 1
    )
    mutated = restored_text.replace(unique_line, "", 1).encode("utf-8")
    assert _normalized_line_coverage(source, mutated) < 1.0
