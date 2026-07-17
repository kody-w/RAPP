"""Plan-only rappid migration tests."""

from __future__ import annotations

import json
import shutil
import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from migrate_rappid import plan_file, plan_record  # noqa: E402


H32 = "15461d6259ec49bdaf8ea032571b3f03"
H64 = H32 * 2
UUID = "915f54e5-4c71-4de9-bba3-6604461d05e5"
V2 = (
    f"rappid:v2:twin:@kody-w/echo-brainstem:{H32}"
    "@github.com/kody-w/echo-brainstem"
)
CANON = f"rappid:@kody-w/echo-brainstem:{H64}"


@pytest.fixture
def migration_dir():
    root = ROOT / "tests" / ".rappid-migration-test-data"
    path = root / str(uuid.uuid4())
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
        try:
            root.rmdir()
        except OSError:
            pass


@pytest.mark.parametrize("legacy", [V2, UUID, f"rappid:@kody-w/echo:{H32}"])
def test_legacy_identity_requires_owner_action_without_proposal(legacy):
    plan = plan_record(
        {"rappid": legacy, "kind": "neighborhood"},
        "kody-w",
        "echo-brainstem",
    )
    assert plan["status"] == "OWNER_ACTION_REQUIRED"
    assert plan["write-permitted"] is False
    assert plan["authorization-verifier"] == "UNAVAILABLE"
    assert plan["record-kind"] == "neighborhood"
    assert plan["legacy-string-kind-authoritative"] is False
    assert plan["proposed-rappid"] is None
    assert plan["identity"]["classification"] == "legacy-quarantined"
    assert plan["required-actions"]


def test_v2_kind_is_not_lifted_from_identity_string():
    plan = plan_record({"rappid": V2}, "kody-w", "echo-brainstem")
    observation = plan["identity"]["observation"]
    assert observation["string_kind"] == "twin"
    assert plan["record-kind"] is None


def test_exact_identity_needs_no_migration_and_is_not_rewritten():
    record = {"rappid": CANON, "kind": "twin", "name": "Echo"}
    plan = plan_record(record, "kody-w", "echo-brainstem")
    assert plan["status"] == "NO_ACTION"
    assert plan["context-binding"] == "MATCH"
    assert plan["write-permitted"] is False
    assert plan["identity"]["rappid"] == CANON
    assert plan["proposed-rappid"] is None


def test_exact_identity_requires_matching_owner_slug_context():
    alice_identity = f"rappid:@alice/echo-brainstem:{H64}"
    missing = plan_record({"rappid": CANON, "kind": "twin"})
    mismatch = plan_record(
        {"rappid": alice_identity, "kind": "twin"},
        "bob",
        "echo-brainstem",
    )

    assert missing["status"] == "OWNER_ACTION_REQUIRED"
    assert mismatch["status"] == "OWNER_ACTION_REQUIRED"
    assert missing["context-binding"] == "OWNER_SLUG_MISMATCH_OR_UNAVAILABLE"
    assert mismatch["context-binding"] == "OWNER_SLUG_MISMATCH_OR_UNAVAILABLE"
    assert missing["proposed-rappid"] is None
    assert mismatch["proposed-rappid"] is None


def test_legacy_parent_is_quarantined_without_rewrite():
    plan = plan_record(
        {"rappid": CANON, "parent_rappid": UUID},
        "kody-w",
        "echo-brainstem",
    )
    assert plan["status"] == "OWNER_ACTION_REQUIRED"
    assert plan["parent-identity"]["classification"] == "legacy-quarantined"
    assert plan["proposed-rappid"] is None


@pytest.mark.parametrize("parent", ["", 7, {"rappid": CANON}])
def test_malformed_present_parent_requires_owner_action(parent):
    plan = plan_record(
        {"rappid": CANON, "parent_rappid": parent},
        "kody-w",
        "echo-brainstem",
    )
    assert plan["status"] == "OWNER_ACTION_REQUIRED"
    assert plan["write-permitted"] is False
    assert plan["proposed-rappid"] is None


def test_plan_file_is_strict_and_never_changes_source(migration_dir):
    path = migration_dir / "rappid.json"
    original = json.dumps({"rappid": V2, "kind": "twin"}).encode()
    path.write_bytes(original)

    plan = plan_file(path, "kody-w", "echo-brainstem")

    assert plan["status"] == "OWNER_ACTION_REQUIRED"
    assert path.read_bytes() == original
    assert list(migration_dir.iterdir()) == [path]


def test_plan_file_rejects_duplicate_json_without_writes(migration_dir):
    path = migration_dir / "rappid.json"
    original = b'{"rappid":"first","rappid":"second"}'
    path.write_bytes(original)
    with pytest.raises(ValueError):
        plan_file(path)
    assert path.read_bytes() == original
