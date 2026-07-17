from __future__ import annotations

import math
import uuid

import pytest

from rapp1_core.canonical import (
    MAX_CANONICAL_BYTES,
    CanonicalizationError,
    canonical_bytes,
    strict_loads,
)
from rapp1_core.hashing import (
    EGG_FILE_SPACE,
    PARTICLE_SPACE,
    RAPPID_SPACE,
    hash_bytes,
    hash_value,
)
from rapp1_core.identity import (
    IdentityError,
    mint_keyless_rappid,
    mint_spki_rappid,
    parse_rappid,
    parse_stream_id,
    validate_kind,
)

TAIL = "a" * 64


def test_rfc8785_positive_vector() -> None:
    value = {
        "numbers": [333333333.33333329, 1e30, 4.50, 2e-3, 1e-27],
        "string": "€$\x0f\nA'B\"\\\"/",
        "literals": [None, True, False],
    }
    assert canonical_bytes(value) == (
        b'{"literals":[null,true,false],"numbers":[333333333.3333333,'
        b'1e+30,4.5,0.002,1e-27],"string":"\xe2\x82\xac$\\u000f\\n'
        b'A\'B\\"\\\\\\"/"}'
    )


@pytest.mark.parametrize(
    "raw",
    [
        b'{"outer":{"x":1,"x":2}}',
        b'{"x":1,"x":2}',
    ],
)
def test_duplicate_keys_are_refused_at_every_depth(raw: bytes) -> None:
    with pytest.raises(CanonicalizationError, match="duplicate"):
        strict_loads(raw)


@pytest.mark.parametrize(
    "raw",
    [
        b'"\\ud800"',
        b'{"\\udfff":1}',
        b"\xed\xa0\x80",
    ],
)
def test_lone_surrogates_and_surrogate_utf8_are_refused(raw: bytes) -> None:
    with pytest.raises(CanonicalizationError):
        strict_loads(raw)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (b"0.1", b"0.1"),
        (b"0.10000000000000000", b"0.1"),
        (b"1e3", b"1000"),
        (b"9007199254740992", b"9007199254740992"),
        (b"-0", b"0"),
    ],
)
def test_binary64_roundtrip_positive_numbers(raw: bytes, expected: bytes) -> None:
    assert canonical_bytes(strict_loads(raw)) == expected


@pytest.mark.parametrize(
    "raw",
    [
        b"9007199254740993",
        b"-9007199254740993",
        b"333333333.33333329",
        b"1e999",
        b"1e-999",
        b"NaN",
        b"Infinity",
    ],
)
def test_binary64_roundtrip_and_nonfinite_negative_numbers(raw: bytes) -> None:
    with pytest.raises(CanonicalizationError):
        strict_loads(raw)


def test_programmatic_nonfinite_is_refused() -> None:
    for value in (math.inf, -math.inf, math.nan):
        with pytest.raises(CanonicalizationError):
            canonical_bytes(value)


def test_depth_limit_is_root_one() -> None:
    depth_64 = b"[" * 64 + b"0" + b"]" * 64
    depth_65 = b"[" * 65 + b"0" + b"]" * 65
    strict_loads(depth_64)
    with pytest.raises(CanonicalizationError, match="depth"):
        strict_loads(depth_65)


def test_canonical_size_limit() -> None:
    exact = b'"' + b"a" * (MAX_CANONICAL_BYTES - 2) + b'"'
    too_large = b'"' + b"a" * (MAX_CANONICAL_BYTES - 1) + b'"'
    assert len(canonical_bytes(strict_loads(exact))) == MAX_CANONICAL_BYTES
    with pytest.raises(CanonicalizationError, match="exceeds"):
        strict_loads(too_large)


def test_utf8_bom_and_invalid_utf8_are_refused() -> None:
    with pytest.raises(CanonicalizationError):
        strict_loads(b"\xef\xbb\xbf{}")
    with pytest.raises(CanonicalizationError):
        strict_loads(b'"\xff"')


def test_domain_hash_vectors_and_domain_types() -> None:
    assert hash_value(PARTICLE_SPACE, {}) == (
        "00d4ee8c3964f0e289ba07982ab8457a7b820056236640bda09572f0725a265b"
    )
    assert len(hash_bytes(EGG_FILE_SPACE, b"payload")) == 64
    with pytest.raises(ValueError):
        hash_value(RAPPID_SPACE, {})
    with pytest.raises(ValueError):
        hash_bytes(PARTICLE_SPACE, b"{}")


def test_exact_rappid_lengths_and_abnf() -> None:
    valid = f"rappid:@{'a' * 39}/{'b' * 100}:{TAIL}"
    assert str(parse_rappid(valid)) == valid
    for invalid in (
        f"rappid:@{'a' * 40}/slug:{TAIL}",
        f"rappid:@owner/{'b' * 101}:{TAIL}",
        f"rappid:@Owner/slug:{TAIL}",
        f"rappid:@owner/-slug:{TAIL}",
        f"rappid:@owner/slug-:{TAIL}",
        f"rappid:@owner/slug:{'A' * 64}",
        f"rappid:owner/slug:{TAIL}",
    ):
        with pytest.raises(IdentityError):
            parse_rappid(invalid)


def test_kind_and_stream_grammars() -> None:
    rappid = f"rappid:@owner/slug:{TAIL}"
    assert validate_kind("body.twin-pulse") == "body.twin-pulse"
    assert parse_stream_id(rappid).family == "body"
    assert parse_stream_id(f"{rappid}:primary").family == "memory"
    assert parse_stream_id("net:planetary-wire").family == "swarm"
    for invalid in (
        "Body.pulse",
        "body",
        f"{'a' * 65}.pulse",
        "body..pulse",
    ):
        with pytest.raises(IdentityError):
            validate_kind(invalid)
    for invalid in (
        f"{rappid}:UPPER",
        "net:-bad",
        "net:a--b",
        "rappid:@owner/slug:" + "a" * 32,
    ):
        with pytest.raises(IdentityError):
            parse_stream_id(invalid)


def test_keyless_mint_fixed_uuid_vector() -> None:
    identifier = uuid.UUID("123e4567-e89b-42d3-a456-426614174000")
    assert mint_keyless_rappid("kody-w", "core", uuid_value=identifier) == (
        "rappid:@kody-w/core:"
        "5c7df8a50ffa8ff68ede5d4bd52f5f96033d5af63ea5320562eecba0b2c38109"
    )
    with pytest.raises(IdentityError):
        mint_keyless_rappid(
            "kody-w",
            "core",
            uuid_value=uuid.UUID("123e4567-e89b-12d3-a456-426614174000"),
        )


def test_spki_bound_mint_vector_and_invalid_der() -> None:
    spki = bytes.fromhex("302a300506032b6570032100" + "11" * 32)
    assert mint_spki_rappid("kody-w", "keyed", spki) == (
        "rappid:@kody-w/keyed:"
        "0a9d127d7d27e63cc63b16b15725e39305d53d5618f9edb07522eecdfc435e73"
    )
    with pytest.raises(IdentityError):
        mint_spki_rappid("kody-w", "keyed", b"not an SPKI")
    with pytest.raises(IdentityError):
        mint_spki_rappid(
            "kody-w",
            "keyed",
            bytes.fromhex("302e300906032b657005000500032100" + "11" * 32),
        )
    with pytest.raises(IdentityError):
        mint_spki_rappid(
            "kody-w",
            "keyed",
            bytes.fromhex("302c300706032b65700000032100" + "11" * 32),
        )
