from __future__ import annotations

import ast
import base64
import gzip
import hashlib
import json
import re
import stat
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
REQUIRED_SURFACE_IDS = {
    "GOV-001",
    "CORE-001",
    "IDENT-001",
    "FRAME-001",
    "EGG-001",
    "TRUST-001",
    "WIRE-001",
    "GRAIL-001",
    "WORKER-001",
    "BROWSER-001",
    "PAGES-001",
    "METRO-001",
    "CAVE-001",
    "ESTATE-001",
    "NETWORK-001",
    "SWARM-001",
    "GENERATED-001",
    "HISTORY-001",
    "TEST-001",
    "MIRROR-001",
}
REQUIRED_RESTORED_SOURCE_PATHS = {
    "azuredeploy.json",
    "cave/.well-known/rapp-cave.json",
    "cave/agents/cave_agent.py",
    "community_rapp/agent-repo-skill.md",
    "community_rapp/install.ps1",
    "community_rapp/install.sh",
    "deploy.ps1",
    "deploy.sh",
    "docs/install.cmd",
    "docs/install.command",
    "docs/install.sh",
    "historical/source-archive/rapp_brainstem/chat.py.txt",
    "historical/source-archive/rapp_brainstem/swarm_server.py.txt",
    "historical/source-archive/rapp_brainstem/t2t.py.txt",
    "historical/source-archive/rapp_brainstem/utils/organs/lifecycle_organ.py.txt",
    "historical/source-archive/rapp_brainstem/utils/organs/neighborhood_membership_organ.py.txt",
    "historical/source-archive/rapp_brainstem/utils/reserved_agents/__init__.py.txt",
    "historical/source-archive/rapp_brainstem/utils/reserved_agents/upgrade_agent.py.txt",
    "historical/source-archive/rapp_brainstem/workspace.py.txt",
    "install.cmd",
    "install.command",
    "install.ps1",
    "install.sh",
    "installer/README.md",
    "installer/azuredeploy.json",
    "installer/hatchling",
    "installer/install-swarm.sh",
    "installer/install.cmd",
    "installer/install.ps1",
    "installer/install.sh",
    "installer/integration_plant.sh",
    "installer/plant.sh",
    "installer/start-local.sh",
    "pages/tutorials/egg_hatcher_agent.py",
    "rapp_brainstem/start.ps1",
    "rapp_brainstem/start.sh",
    "rapp_brainstem/tls_proxy.py",
    "rapp_brainstem/utils/boot.py",
    "rapp_swarm/README.md",
    "rapp_swarm/build.sh",
    "rapp_swarm/function_app.py",
    "rapp_swarm/index.html",
    "rapp_swarm/provision-twin-lite.sh",
    "rapp_swarm/provision-twin.sh",
    "rapp_swarm/twin-egg.sh",
    "rapp_swarm/twin-sim.sh",
    "tools/front_door_specs.py",
    "tools/lan_advertise.py",
    "tools/sign_release.py",
    "tools/sim/README.md",
    "tools/sim/loop_orchestrator.sh",
    "tools/sim/observe.py",
    "tools/sim/plant_two_brainstems.py",
    "tools/sim/push_canvas.sh",
    "tools/sim/tick_twin.py",
    "tools/templates/rapp_estate_grail.html",
    "tools/test_brainstem_server.py",
    "worker/README.md",
}


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


def _walk(value, path: str = "$"):
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, f"{path}[{index}]")


def _selector_matches(
    selector: dict,
    relative: str,
    path_sets: dict[str, set[str]],
) -> bool:
    kind = selector["type"]
    if kind == "explicit":
        return relative in selector["paths"]
    if kind == "prefix":
        return any(relative.startswith(prefix) for prefix in selector["prefixes"])
    if kind == "explicit-and-prefix":
        return relative in selector["paths"] or any(
            relative.startswith(prefix) for prefix in selector["prefixes"]
        )
    if kind == "path-set-ref":
        return relative in path_sets[selector["path_set_ref"]]
    if kind == "root-files":
        return "/" not in relative
    raise AssertionError(f"unsupported primary selector: {selector}")


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
    assert set(surface_ids) == REQUIRED_SURFACE_IDS
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


def test_primary_classification_covers_every_tracked_path_once():
    inventory = _load(INVENTORY_PATH)
    tracked = _tracked_paths()
    path_sets: dict[str, set[str]] = {}
    for record in inventory["path_sets"]:
        selector = record["selector"]
        if selector["type"] == "git-prefix":
            selected = {
                path for path in tracked if path.startswith(selector["prefix"])
            }
        else:
            selected = set(selector["paths"])
        path_sets[record["id"]] = selected

    classification = inventory["primary_classification"]
    assert set(classification["required_surface_ids"]) == REQUIRED_SURFACE_IDS
    assert classification["fallback_surface_id"] in REQUIRED_SURFACE_IDS
    rule_ids = [rule["id"] for rule in classification["rules"]]
    assert len(rule_ids) == len(set(rule_ids))
    counts = {surface_id: 0 for surface_id in REQUIRED_SURFACE_IDS}
    assigned: dict[str, str] = {}
    fallback_paths: list[str] = []
    for relative in tracked:
        matched = next(
            (
                rule["surface_id"]
                for rule in classification["rules"]
                if _selector_matches(rule["selector"], relative, path_sets)
            ),
            None,
        )
        surface_id = matched or classification["fallback_surface_id"]
        if matched is None:
            fallback_paths.append(relative)
        assert surface_id in REQUIRED_SURFACE_IDS
        assigned[relative] = surface_id
        counts[surface_id] += 1
    assert set(assigned) == set(tracked)
    assert fallback_paths == []
    assert all(count > 0 for count in counts.values()), counts


def test_candidate_evidence_cannot_claim_authenticated_acceptance():
    inventory = _load(INVENTORY_PATH)
    forbidden_true = {
        "accepted",
        "fresh",
        "cryptographically_verified",
        "authenticated_acceptance_allowed",
    }
    for path, value in _walk(inventory):
        key = path.rsplit(".", 1)[-1]
        if key in forbidden_true:
            assert value is False, path
        if key == "verified":
            assert value is not True, path
    discovery = _load(ROOT / "rapp-ai.json")
    for path, value in _walk(discovery):
        key = path.rsplit(".", 1)[-1]
        if key in {"accepted", "fresh", "cryptographically_verified"}:
            assert value is not True, path
        if key == "verified":
            assert value is not True, path


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
    assert ledger["authenticated_acceptance_allowed"] is False

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
        capsule = source["capsule"]
        assert capsule["encoding"] == "gzip+base64"
        compressed = base64.b64decode(capsule["payload"])
        assert compressed[:3] == b"\x1f\x8b\x08"
        assert compressed[9] == 255
        assert gzip.decompress(compressed) == old_bytes

        restored = record["restored"]
        current_bytes = current.read_bytes()
        assert hashlib.sha256(current_bytes).hexdigest() == restored["sha256"], relative
        assert len(current_bytes) == restored["bytes"], relative
        assert re.fullmatch(r"[0-9a-f]{40}", restored["commit"])
        committed_bytes = _source_bytes(restored["commit"], relative)
        assert hashlib.sha256(committed_bytes).hexdigest() == restored["sha256"], relative
        assert len(committed_bytes) == restored["bytes"], relative
        assert len(current_bytes) >= source["bytes"] * 0.9, relative
        assert record["trust_state"] == {
            "observed": True,
            "structurally_valid": True,
            "cryptographically_verified": False,
            "fresh": False,
            "accepted": False,
        }

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
            assert (
                _normalized_line_coverage(old_bytes, current_bytes)
                >= check["minimum_line_coverage"]
            ), relative
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
            assert (
                _normalized_line_coverage(old_bytes, current_bytes)
                >= check["minimum_line_coverage"]
            ), relative
        else:
            raise AssertionError(f"unsupported preservation check: {check}")

        if record["category"] == "browser-page":
            text = current_bytes.decode("utf-8").lower()
            assert "retired semantic tombstone" not in text
            assert source["commit"] in text
            assert source["sha256"] in text
    assert REQUIRED_RESTORED_SOURCE_PATHS <= current_paths


def test_removed_runtime_sources_survive_as_exact_inert_archives():
    archive_manifest = _load(
        ROOT / "historical/source-archive/manifest.json"
    )
    assert archive_manifest["schema"] == "rapp-historical-source-archive/1.0"
    assert archive_manifest["record_kind"] == "inert-exact-source-archive"
    assert archive_manifest["status"] == "historical-observation"
    assert archive_manifest["executable"] is False
    assert archive_manifest["importable"] is False
    assert archive_manifest["published_by_pages"] is False
    assert archive_manifest["accepted"] is False

    ledger = _load(LEDGER_PATH)
    ledger_by_path = {
        record["current_path"]: record
        for record in ledger["artifacts"]
    }
    records = archive_manifest["records"]
    assert len(records) == 8
    for record in records:
        source_path = record["source_path"]
        archive_path = record["archive_path"]
        archived = ROOT / archive_path
        assert not (ROOT / source_path).exists(), source_path
        assert archived.is_file(), archive_path
        assert archived.suffix == ".txt"
        assert not (archived.stat().st_mode & stat.S_IXUSR)

        source_bytes = _source_bytes(record["commit"], source_path)
        assert _source_blob(record["commit"], source_path) == record["blob"]
        assert archived.read_bytes() == source_bytes
        assert hashlib.sha256(source_bytes).hexdigest() == record["sha256"]
        assert len(source_bytes) == record["bytes"]

        ledger_record = ledger_by_path[archive_path]
        assert ledger_record["source"]["path"] == source_path
        assert ledger_record["source"]["commit"] == record["commit"]
        assert ledger_record["source"]["blob"] == record["blob"]


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


def test_marker_mode_rejects_a_padded_marker_only_stub():
    source = _source_bytes(
        "4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6",
        "worker/worker.js",
    )
    markers = (
        "export const HISTORICAL_SOURCE",
        "DEFAULT_CAPABILITIES",
        "RAPP_BROWSER_RUNTIME_ENABLED",
        "explicit-reviewed-runtime-binding-required",
        "/api/copilot/chat",
    )
    stub = ("\n".join(f"// {marker}" for marker in markers)).encode("utf-8")
    stub += b"\n" + b"x" * len(source)
    assert len(stub) >= len(source) * 0.9
    assert _normalized_line_coverage(source, stub) < 0.335


def test_symbol_mode_rejects_a_padded_symbol_only_stub():
    source = _source_bytes(
        "591e7aec3b2183e0d48a1d6dfb6ebc59f177daea",
        "tools/private_estate_init.py",
    )
    names = sorted(_python_symbols(source))
    stub_text = "\n".join(f"def {name}(*args, **kwargs):\n    pass" for name in names)
    stub = stub_text.encode("utf-8") + b"\n#" + b"x" * len(source)
    assert _python_symbols(source) <= _python_symbols(stub)
    assert len(stub) >= len(source) * 0.9
    assert _normalized_line_coverage(source, stub) < 0.875
