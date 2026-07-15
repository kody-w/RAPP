"""Tests for the consolidated rappid (`rappid:@<owner>/<slug>:<64hex>`) parser.

    python3 -m pytest tests/test_door_address.py -v

Covers: canonical parse + door URLs, reading the non-v2 legacy forms (bare UUID),
the RETIREMENT of the v2 form (the live parser now refuses it — only the one-shot
migrate_rappid tool still reads v2, to convert stragglers), canonicalization
(idempotent), invalid-form rejection, kind/door_type sourcing, back-compat API.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import door_address as da  # noqa: E402

H64 = "15461d6259ec49bdaf8ea032571b3f0315461d6259ec49bdaf8ea032571b3f03"  # 64 hex
H32 = "15461d6259ec49bdaf8ea032571b3f03"                                  # 32 hex (retired v2)
CANON = f"rappid:@kody-w/echo-brainstem:{H64}"
V2 = f"rappid:v2:twin:@kody-w/echo-brainstem:{H32}@github.com/kody-w/echo-brainstem"  # RETIRED — live parser refuses
UUID = "915f54e5-4c71-4de9-bba3-6604461d05e5"


# ── parse ─────────────────────────────────────────────────────────────────────
def test_parse_canonical():
    p = da.parse_rappid(CANON)
    assert p == {"form": "canonical", "owner": "kody-w", "slug": "echo-brainstem",
                 "hash": H64, "hash_bits": 256, "kind": None}


def test_parse_v2_now_refused():
    # v2 is RETIRED — the live parser no longer reads it (STEAMROLL LEGACY).
    with pytest.raises(da.InvalidRappidError):
        da.parse_rappid(V2)


def test_parse_uuid_legacy_has_no_location():
    p = da.parse_rappid(UUID)
    assert p["form"] == "uuid-legacy"
    assert p["owner"] is None and p["slug"] is None
    assert p["hash"] == UUID.replace("-", "")


def test_parse_v2_variants_all_refused():
    # Any v2 shape (even a well-formed one) is refused by the live parser now.
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


def test_canonicalize_v2_now_refused():
    # canonicalize routes through the live parser, which no longer reads v2.
    # v2 → canonical is now the exclusive job of tools/migrate_rappid.py.
    with pytest.raises(da.InvalidRappidError):
        da.canonicalize_rappid(V2)


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


def test_v2_door_now_refused():
    # A v2 string no longer resolves to a door on the live path — it must be
    # migrated to canonical first (tools/migrate_rappid.py).
    with pytest.raises(da.InvalidRappidError):
        da.door_from_rappid(V2)


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


def test_door_dict_has_back_compat_keys():
    d = da.door_from_rappid(CANON, kind="twin")
    for k in ("rappid", "owner", "repo", "kind", "door_type", "urls"):
        assert k in d, f"consumers rely on door['{k}']"


def test_estate_url():
    assert da.estate_url("kody-w") == \
        "https://raw.githubusercontent.com/kody-w/rapp-estate/main/estate.json"
    with pytest.raises(da.InvalidRappidError):
        da.estate_url("bad/handle")
