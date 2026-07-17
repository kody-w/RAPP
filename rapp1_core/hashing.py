"""Exact domain-separated RAPP/1 content addresses."""

from __future__ import annotations

import hashlib
from typing import Any

from .canonical import canonical_bytes
from .errors import RappError

PARTICLE_SPACE = "rapp/1:particle"
WAVE_SPACE = "rapp/1:wave"
EGG_FILE_SPACE = "rapp/1:egg"
EGG_MANIFEST_SPACE = "rapp/1:egg-manifest"
RAPPID_SPACE = "rapp/1:rappid"
SEAL_SPACE = "rapp/1:seal"

VALUE_SPACES = frozenset({PARTICLE_SPACE, WAVE_SPACE, EGG_MANIFEST_SPACE})
BYTE_SPACES = frozenset({EGG_FILE_SPACE, RAPPID_SPACE, SEAL_SPACE})


def _prefix(space: str) -> bytes:
    try:
        encoded = space.encode("ascii")
    except UnicodeEncodeError as exc:
        raise RappError("invalid-hash-space", "hash space must be ASCII") from exc
    if b"\n" in encoded:
        raise RappError("invalid-hash-space", "hash space cannot contain LF")
    return encoded + b"\n"


def hash_value(space: str, value: Any) -> str:
    """H(space, value), restricted to the value-address spaces in SPEC §5."""

    if space not in VALUE_SPACES:
        raise RappError("wrong-hash-domain", f"{space!r} is not a value hash space")
    return hashlib.sha256(_prefix(space) + canonical_bytes(value)).hexdigest()


def hash_bytes(space: str, data: bytes | bytearray | memoryview) -> str:
    """Hb(space, octets), restricted to the byte-address spaces in SPEC §5."""

    if space not in BYTE_SPACES:
        raise RappError("wrong-hash-domain", f"{space!r} is not a byte hash space")
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("hash_bytes requires bytes")
    return hashlib.sha256(_prefix(space) + bytes(data)).hexdigest()


H = hash_value
Hb = hash_bytes
