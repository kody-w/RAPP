"""Tests for tools/door_address.py — the one rappid → door parser.

Covers the canonical self-locating Eternity form `rappid:@<owner>/<slug>:<64hex>`
(CONSTITUTION Art. XXXIV.1) and the legacy v2 form (read-compatible).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import door_address as d  # noqa: E402

H64 = "a" * 64
H32 = "b" * 32
V2 = f"rappid:v2:twin:@kody-w/echo-brainstem:{H32}@github.com/kody-w/echo-brainstem"


def test_eternity_canonical_with_kind():
    e = d.door_from_rappid(f"rappid:@kody-w/echo-brainstem:{H64}", kind="twin")
    assert e["owner"] == "kody-w" and e["repo"] == "echo-brainstem"
    assert e["kind"] == "twin" and e["door_type"] == "front_door"
    assert e["urls"]["identity"] == "https://raw.githubusercontent.com/kody-w/echo-brainstem/main/rappid.json"
    assert e["urls"]["front"] == "https://kody-w.github.io/echo-brainstem/"


def test_eternity_without_kind_still_self_locates():
    e = d.door_from_rappid(f"rappid:@kody-w/echo-brainstem:{H64}")
    assert e["kind"] is None and e["door_type"] is None
    assert e["urls"]["repo"] == "https://github.com/kody-w/echo-brainstem"


def test_legacy_v2_unchanged():
    l = d.door_from_rappid(V2)
    assert l["owner"] == "kody-w" and l["kind"] == "twin" and l["door_type"] == "front_door"


def test_owner_repo_from_both_forms():
    assert d.owner_repo_from_rappid(f"rappid:@kody-w/x:{H64}") == ("kody-w", "x")
    assert d.owner_repo_from_rappid(V2) == ("kody-w", "echo-brainstem")


def test_invalid_forms_raise():
    for bad in ["nonsense", f"rappid:@kody-w/x:{H32}",  # 32-hex is too short for Eternity
                f"rappid:v2:twin:@a/b:{H32}@github.com/a/c"]:  # v2 origin mismatch
        try:
            d.door_from_rappid(bad)
            assert False, f"should have raised for {bad!r}"
        except d.InvalidRappidError:
            pass


def test_unknown_kind_rejected():
    try:
        d.door_from_rappid(f"rappid:@a/b:{H64}", kind="bogus")
        assert False, "bogus kind should raise"
    except d.InvalidRappidError:
        pass
