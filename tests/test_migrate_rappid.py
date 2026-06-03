"""Tests for the rappid.json → consolidated-form migration tool.

    python3 -m pytest tests/test_migrate_rappid.py -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from migrate_rappid import migrate_record  # noqa: E402

H32 = "15461d6259ec49bdaf8ea032571b3f03"
UUID = "915f54e5-4c71-4de9-bba3-6604461d05e5"
V2 = f"rappid:v2:twin:@kody-w/echo-brainstem:{H32}@github.com/kody-w/echo-brainstem"


def test_v2_record_consolidates_and_lifts_kind():
    rec = {"rappid": V2, "name": "Echo"}
    out, changed = migrate_record(rec, "kody-w", "echo-brainstem")
    assert changed
    assert out["rappid"] == f"rappid:@kody-w/echo-brainstem:{H32}"  # hash preserved
    assert out["kind"] == "twin"                                    # lifted into the record
    assert out["_migrated_from"] == V2
    assert out["name"] == "Echo"                                    # other fields untouched


def test_v2_keeps_existing_kind_field():
    rec = {"rappid": V2, "kind": "twin"}
    out, _ = migrate_record(rec, "kody-w", "echo-brainstem")
    assert out["kind"] == "twin" and "_migrated_from" in out


def test_bare_uuid_consolidates_with_location():
    rec = {"rappid": UUID, "kind": "twin"}
    out, changed = migrate_record(rec, "kody-w", "heimdall")
    assert changed
    assert out["rappid"] == f"rappid:@kody-w/heimdall:{UUID.replace('-', '')}"
    assert out["_migrated_from"] == UUID


def test_parent_rappid_is_canonicalized():
    rec = {"rappid": V2,
           "parent_rappid": "rappid:v2:operator:@kody-w/kody-w-twin:" + H32 + "@github.com/kody-w/kody-w-twin"}
    out, _ = migrate_record(rec, "kody-w", "echo-brainstem")
    assert out["parent_rappid"] == f"rappid:@kody-w/kody-w-twin:{H32}"


def test_idempotent_on_consolidated():
    rec = {"rappid": f"rappid:@kody-w/echo-brainstem:{H32}", "kind": "twin"}
    out, changed = migrate_record(rec, "kody-w", "echo-brainstem")
    assert not changed
    assert out == rec  # no _migrated_from, no rewrite


def test_double_migration_is_stable():
    rec = {"rappid": V2}
    once, _ = migrate_record(rec, "kody-w", "echo-brainstem")
    twice, changed2 = migrate_record(once, "kody-w", "echo-brainstem")
    assert not changed2 and twice["rappid"] == once["rappid"]


def test_bare_uuid_parent_left_alone():
    # a parent that is a bare UUID (no location) is left intact, not crashed on
    rec = {"rappid": V2, "parent_rappid": UUID}
    out, _ = migrate_record(rec, "kody-w", "echo-brainstem")
    assert out["parent_rappid"] == UUID
