"""Exact active-path and quarantined migration tests for door_address."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import door_address as da  # noqa: E402


H64 = "15461d6259ec49bdaf8ea032571b3f0315461d6259ec49bdaf8ea032571b3f03"
H32 = "15461d6259ec49bdaf8ea032571b3f03"
CANON = f"rappid:@kody-w/echo-brainstem:{H64}"
V2 = (
    f"rappid:v2:twin:@kody-w/echo-brainstem:{H32}"
    "@github.com/kody-w/echo-brainstem"
)
UUID = "915f54e5-4c71-4de9-bba3-6604461d05e5"


def test_parse_exact_rapp1_uses_core_shape():
    assert da.parse_rappid(CANON) == {
        "form": "canonical",
        "owner": "kody-w",
        "slug": "echo-brainstem",
        "hash": H64,
        "hash_bits": 256,
        "kind": None,
    }
    assert da.canonicalize_rappid(CANON) == CANON


@pytest.mark.parametrize(
    "bad",
    [
        "",
        V2,
        UUID,
        f"rappid:@kody-w/echo-brainstem:{H32}",
        f"rappid:@Kody-w/echo-brainstem:{H64}",
        f"rappid:@kody_w/echo-brainstem:{H64}",
        f"rappid:@kody-w/echo.brainstem:{H64}",
        f"rappid:@kody-w/-echo:{H64}",
        123,
    ],
)
def test_normal_parser_and_canonicalizer_reject_non_section_6_1(bad):
    with pytest.raises(da.InvalidRappidError):
        da.parse_rappid(bad)
    with pytest.raises((da.InvalidRappidError, TypeError)):
        da.canonicalize_rappid(bad)


@pytest.mark.parametrize(
    ("legacy", "form", "bits"),
    [
        (V2, "v2-legacy", 128),
        (UUID, "uuid-legacy", 128),
        (
            f"rappid:@kody-w/echo-brainstem:{H32}",
            "provisional-self-locating",
            128,
        ),
    ],
)
def test_explicit_migration_api_preserves_but_never_resolves(legacy, form, bits):
    observation = da.parse_legacy_for_migration(legacy)
    report = observation.as_dict()
    assert report["original"] == legacy
    assert report["form"] == form
    assert report["tail_bits"] == bits
    assert report["identity_state"] == "provisional"
    assert report["provisional"] is True
    assert report["resolvable"] is False
    assert report["protocol_emission_allowed"] is False
    assert report["tail_preserved"] is True
    assert "canonical" not in report
    assert "urls" not in report
    with pytest.raises(da.InvalidRappidError):
        da.door_from_rappid(legacy)


@pytest.mark.parametrize(
    "legacy",
    [
        V2,
        f"rappid:@kody-w/echo-brainstem:{H32}",
    ],
)
def test_canonicalize_on_read_restructures_and_preserves_provisional_tail(
    legacy,
):
    migrated = da.canonicalize_on_read(legacy)

    assert migrated.restructured_rappid == (
        f"rappid:@kody-w/echo-brainstem:{H32}"
    )
    assert migrated.tail == H32
    assert migrated.tail_bits == 128
    assert migrated.provisional is True
    assert migrated.resolvable is False
    assert migrated.protocol_emission_allowed is False
    with pytest.raises(da.InvalidRappidError):
        da.parse_rappid(migrated.restructured_rappid)
    with pytest.raises(da.InvalidRappidError):
        da.door_from_rappid(migrated.restructured_rappid)


def test_canonicalize_on_read_refuses_unlocated_or_ambiguous_legacy_forms():
    with pytest.raises(da.InvalidRappidError, match="no self-location"):
        da.canonicalize_on_read(UUID)

    mismatch = (
        f"rappid:v2:twin:@kody-w/echo-brainstem:{H32}"
        "@github.com/kody-w/other"
    )
    with pytest.raises(da.InvalidRappidError, match="do not match"):
        da.canonicalize_on_read(mismatch)


def test_migration_api_is_not_a_second_exact_parser():
    with pytest.raises(da.InvalidRappidError):
        da.parse_legacy_for_migration(CANON)
    with pytest.raises(da.InvalidRappidError):
        da.canonicalize_on_read(CANON)


def test_door_urls_resolve_only_exact_identity():
    door = da.door_from_rappid(CANON)
    assert door["owner"] == "kody-w"
    assert door["repo"] == "echo-brainstem"
    assert door["canonical"] == CANON
    assert door["kind"] is None
    assert door["urls"]["identity"] == (
        "https://raw.githubusercontent.com/kody-w/"
        "echo-brainstem/main/rappid.json"
    )


def test_kind_is_read_from_matching_identity_record_not_string():
    record = {"rappid": CANON, "kind": "neighborhood"}
    door = da.door_from_rappid(CANON, identity_record=record)
    assert door["kind"] == "neighborhood"
    assert door["door_type"] == "gate"

    with pytest.raises(da.InvalidRappidError):
        da.door_from_rappid(
            CANON,
            identity_record={
                "rappid": f"rappid:@kody-w/other:{'a' * 64}",
                "kind": "twin",
            },
        )
    with pytest.raises(da.InvalidRappidError):
        da.door_from_rappid(CANON, identity_record={"kind": "not-a-kind"})
    with pytest.raises(da.InvalidRappidError):
        da.door_from_rappid(CANON, identity_record={"kind": "twin"})


def test_owner_helpers_enforce_lowercase_grammar():
    assert da.owner_repo_from_rappid(CANON) == ("kody-w", "echo-brainstem")
    assert da.estate_url("kody-w") == (
        "https://raw.githubusercontent.com/kody-w/rapp-estate/main/estate.json"
    )
    for invalid in ("Kody-w", "kody_w", "bad/handle", "-bad"):
        with pytest.raises(da.InvalidRappidError):
            da.estate_url(invalid)
