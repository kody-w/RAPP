"""Structural parsing for the exact detached, unencoded RAPP JWS profile."""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass

from .canonical import canonical_bytes, strict_loads
from .errors import CanonicalizationError, SignatureStructureError
from .identity import parse_rappid

BASE64URL_RE = re.compile(r"^[A-Za-z0-9_-]+$", re.ASCII)
HEADER_KEYS = frozenset({"alg", "b64", "crit", "kid"})


@dataclass(frozen=True)
class DetachedJws:
    alg: str
    kid: str
    protected_segment: str
    signature: bytes


def _decode_base64url(segment: str, *, field: str) -> bytes:
    if not segment or BASE64URL_RE.fullmatch(segment) is None:
        raise SignatureStructureError(
            "invalid-jws-base64url", f"{field} is not unpadded base64url"
        )
    try:
        decoded = base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))
    except ValueError as exc:
        raise SignatureStructureError(
            "invalid-jws-base64url", f"{field} cannot be decoded"
        ) from exc
    canonical = base64.urlsafe_b64encode(decoded).rstrip(b"=").decode("ascii")
    if canonical != segment:
        raise SignatureStructureError(
            "invalid-jws-base64url", f"{field} is not canonical base64url"
        )
    return decoded


def parse_detached_jws(value: str) -> DetachedJws:
    if type(value) is not str:
        raise SignatureStructureError("invalid-jws", "JWS must be a string")
    parts = value.split(".")
    if len(parts) != 3 or parts[1] != "":
        raise SignatureStructureError(
            "invalid-jws", "JWS must use detached compact serialization"
        )
    protected_octets = _decode_base64url(parts[0], field="protected header")
    signature = _decode_base64url(parts[2], field="signature")
    try:
        header = strict_loads(protected_octets)
    except CanonicalizationError as exc:
        raise SignatureStructureError(
            "invalid-jws-header", "protected header is not strict I-JSON"
        ) from exc
    if type(header) is not dict or set(header) != HEADER_KEYS:
        raise SignatureStructureError(
            "invalid-jws-header", "protected header must contain exactly four members"
        )
    if canonical_bytes(header) != protected_octets:
        raise SignatureStructureError(
            "noncanonical-jws-header", "protected header octets are not RFC 8785"
        )
    alg = header["alg"]
    if alg not in ("EdDSA", "ES256"):
        raise SignatureStructureError("invalid-jws-alg", "alg must be EdDSA or ES256")
    if header["b64"] is not False or header["crit"] != ["b64"]:
        raise SignatureStructureError(
            "invalid-jws-header", "b64 and crit do not select RFC 7797"
        )
    kid = header["kid"]
    try:
        parse_rappid(kid)
    except Exception as exc:
        raise SignatureStructureError(
            "invalid-jws-kid", "kid must be a conformant rappid"
        ) from exc
    if len(signature) != 64:
        raise SignatureStructureError(
            "invalid-jws-signature", f"{alg} JWS signature must be 64 octets"
        )
    return DetachedJws(
        alg=alg, kid=kid, protected_segment=parts[0], signature=signature
    )
