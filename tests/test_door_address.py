"""Tests for the consolidated rappid (`rappid:@<owner>/<slug>:<64hex>`) parser.

    python3 -m pytest tests/test_door_address.py -v

Covers: canonical parse + door URLs, reading every legacy form (v2, bare UUID),
canonicalization (idempotent; v2 → canonical preserves the hash), invalid-form
rejection, kind/door_type sourcing, and the back-compat consumer API.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import door_address as da  # noqa: E402

H64 = "15461d6259ec49bdaf8ea032571b3f0315461d6259ec49bdaf8ea032571b3f03"  # 64 hex
H32 = "15461d6259ec49bdaf8ea032571b3f03"                                  # 32 hex (legacy v2)
CANON = f"rappid:@kody-w/echo-brainstem:{H64}"
V2 = f"rappid:v2:twin:@kody-w/echo-brainstem:{H32}@github.com/kody-w/echo-brainstem"
UUID = "915f54e5-4c71-4de9-bba3-6604461d05e5"


# ── parse ─────────────────────────────────────────────────────────────────────
def test_parse_canonical():
    p = da.parse_rappid(CANON)
    assert p == {"form": "canonical", "owner": "kody-w", "slug": "echo-brainstem",
                 "hash": H64, "hash_bits": 256, "kind": None}


def test_parse_v2_legacy():
    p = da.parse_rappid(V2)
    assert p["form"] == "v2-legacy"
    assert p["owner"] == "kody-w" and p["slug"] == "echo-brainstem"
    assert p["hash"] == H32 and p["hash_bits"] == 128 and p["kind"] == "twin"


def test_parse_uuid_legacy_has_no_location():
    p = da.parse_rappid(UUID)
    assert p["form"] == "uuid-legacy"
    assert p["owner"] is None and p["slug"] is None
    assert p["hash"] == UUID.replace("-", "")


def test_parse_v2_origin_mismatch_rejected():
    bad = f"rappid:v2:twin:@kody-w/echo-brainstem:{H32}@github.com/kody-w/OTHER"
    with pytest.raises(da.InvalidRappidError):
        da.parse_rappid(bad)


@pytest.mark.parametrize("bad", ["", "nope", "rappid:@kody-w:abc", f"rappid:@k/s:{H64}x",
                                 "rappid:@kody-w/echo:xyz", 123])
def test_parse_invalid_rejected(bad):
    with pytest.raises(da.InvalidRappidError):
        da.parse_rappid(bad)


# ── canonicalize ────────────────────────────────────────────────────────────────
def test_canonicalize_idempotent():
    assert da.canonicalize_rappid(CANON) == CANON


def test_canonicalize_v2_drops_decorations_keeps_hash():
    # v2 → consolidated structure, hash preserved (no re-anchor here)
    assert da.canonicalize_rappid(V2) == f"rappid:@kody-w/echo-brainstem:{H32}"


def test_canonicalize_uuid_needs_location():
    with pytest.raises(da.InvalidRappidError):
        da.canonicalize_rappid(UUID)  # bare UUID carries no owner/slug
    assert da.canonicalize_rappid(UUID, owner="kody-w", slug="heimdall") == \
        f"rappid:@kody-w/heimdall:{UUID.replace('-', '')}"


# ── door_from_rappid: self-location + URLs ──────────────────────────────────────
def test_door_urls_from_canonical():
    d = da.door_from_rappid(CANON)
    assert d["owner"] == "kody-w" and d["repo"] == "echo-brainstem"
    assert d["urls"]["repo"] == "https://github.com/kody-w/echo-brainstem"
    assert d["urls"]["front"] == "https://kody-w.github.io/echo-brainstem/"
    assert d["urls"]["identity"] == \
        "https://raw.githubusercontent.com/kody-w/echo-brainstem/main/rappid.json"
    assert d["canonical"] == CANON


def test_door_urls_identical_across_canonical_and_v2():
    # The whole point: a v2 door and its consolidated form resolve to the SAME door.
    assert da.door_from_rappid(CANON)["urls"] == da.door_from_rappid(V2)["urls"]


def test_kind_and_door_type_from_v2_string():
    d = da.door_from_rappid(V2)
    assert d["kind"] == "twin" and d["door_type"] == "front_door"


def test_kind_from_record_arg_for_canonical():
    assert da.door_from_rappid(CANON)["kind"] is None          # not in the string
    assert da.door_from_rappid(CANON)["door_type"] is None
    d = da.door_from_rappid(CANON, kind="neighborhood")        # supplied from the record
    assert d["kind"] == "neighborhood" and d["door_type"] == "gate"


def test_invalid_kind_rejected():
    with pytest.raises(da.InvalidRappidError):
        da.door_from_rappid(CANON, kind="not-a-kind")


def test_bare_uuid_door_raises_without_location():
    with pytest.raises(da.InvalidRappidError):
        da.door_from_rappid(UUID)


# ── back-compat consumer API (rebuild_estate etc. rely on these) ────────────────
def test_owner_repo_helper():
    assert da.owner_repo_from_rappid(CANON) == ("kody-w", "echo-brainstem")
    assert da.owner_repo_from_rappid(V2) == ("kody-w", "echo-brainstem")


def test_door_dict_has_back_compat_keys():
    d = da.door_from_rappid(V2)
    for k in ("rappid", "owner", "repo", "kind", "door_type", "urls"):
        assert k in d, f"consumers rely on door['{k}']"


def test_estate_url():
    assert da.estate_url("kody-w") == \
        "https://raw.githubusercontent.com/kody-w/rapp-estate/main/estate.json"
    with pytest.raises(da.InvalidRappidError):
        da.estate_url("bad/handle")
