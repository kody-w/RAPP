"""Strict RAPP/1 identity, stream, kind, and minting helpers."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from .errors import IdentityError
from .hashing import RAPPID_SPACE, hash_bytes

LOWER_HASH_RE = re.compile(r"^[0-9a-f]{64}$", re.ASCII)
LABEL_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", re.ASCII)
RAPPID_RE = re.compile(
    r"^rappid:@(?P<owner>[a-z0-9]+(?:-[a-z0-9]+)*)/"
    r"(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*):(?P<tail>[0-9a-f]{64})$",
    re.ASCII,
)
KIND_RE = re.compile(
    r"^(?P<left>[a-z0-9]+(?:-[a-z0-9]+)*)\."
    r"(?P<right>[a-z0-9]+(?:-[a-z0-9]+)*)$",
    re.ASCII,
)
MEMORY_STREAM_RE = re.compile(
    r"^(?P<rappid>rappid:@[a-z0-9]+(?:-[a-z0-9]+)*/"
    r"[a-z0-9]+(?:-[a-z0-9]+)*:[0-9a-f]{64}):"
    r"(?P<instance>[a-z0-9]+(?:-[a-z0-9]+)*)$",
    re.ASCII,
)


@dataclass(frozen=True)
class Rappid:
    owner: str
    slug: str
    tail: str

    def __str__(self) -> str:
        return f"rappid:@{self.owner}/{self.slug}:{self.tail}"


@dataclass(frozen=True)
class StreamId:
    value: str
    family: str
    rappid: Rappid | None = None
    instance: str | None = None


def _validate_label(value: str, *, name: str, maximum: int) -> str:
    if type(value) is not str:
        raise IdentityError("invalid-label", f"{name} must be a string")
    if not 1 <= len(value) <= maximum or LABEL_RE.fullmatch(value) is None:
        raise IdentityError(
            "invalid-label",
            f"{name} must be 1-{maximum} lowercase alphanumeric/hyphen characters",
        )
    return value


def validate_owner(owner: str) -> str:
    return _validate_label(owner, name="owner", maximum=39)


def validate_slug(slug: str) -> str:
    return _validate_label(slug, name="slug", maximum=100)


def parse_rappid(value: str) -> Rappid:
    if type(value) is not str:
        raise IdentityError("invalid-rappid", "rappid must be a string")
    match = RAPPID_RE.fullmatch(value)
    if match is None:
        raise IdentityError("invalid-rappid", "rappid does not match the RAPP/1 ABNF")
    owner = validate_owner(match.group("owner"))
    slug = validate_slug(match.group("slug"))
    return Rappid(owner, slug, match.group("tail"))


def validate_kind(value: str) -> str:
    if type(value) is not str:
        raise IdentityError("invalid-kind", "kind must be a string")
    match = KIND_RE.fullmatch(value)
    if match is None:
        raise IdentityError("invalid-kind", "kind does not match the RAPP/1 ABNF")
    _validate_label(match.group("left"), name="kind label", maximum=64)
    _validate_label(match.group("right"), name="kind label", maximum=64)
    return value


def parse_stream_id(value: str) -> StreamId:
    if type(value) is not str:
        raise IdentityError("invalid-stream-id", "stream_id must be a string")
    if value.startswith("net:"):
        label = value[4:]
        _validate_label(label, name="swarm stream label", maximum=64)
        return StreamId(value=value, family="swarm")
    memory = MEMORY_STREAM_RE.fullmatch(value)
    if memory is not None:
        rappid = parse_rappid(memory.group("rappid"))
        instance = _validate_label(
            memory.group("instance"), name="memory stream instance", maximum=64
        )
        return StreamId(
            value=value, family="memory", rappid=rappid, instance=instance
        )
    try:
        rappid = parse_rappid(value)
    except IdentityError as exc:
        raise IdentityError(
            "invalid-stream-id", "stream_id does not match a RAPP/1 stream form"
        ) from exc
    return StreamId(value=value, family="body", rappid=rappid)


def _format_rappid(owner: str, slug: str, tail: str) -> str:
    validate_owner(owner)
    validate_slug(slug)
    if LOWER_HASH_RE.fullmatch(tail) is None:
        raise IdentityError("invalid-rappid-tail", "rappid tail must be 64 lowercase hex")
    return str(Rappid(owner, slug, tail))


def mint_keyless_rappid(
    owner: str, slug: str, *, uuid_value: uuid.UUID | None = None
) -> str:
    """Mint a keyless identity from the 16 binary octets of an RFC 9562 UUIDv4."""

    identifier = uuid.uuid4() if uuid_value is None else uuid_value
    if not isinstance(identifier, uuid.UUID):
        raise TypeError("uuid_value must be uuid.UUID")
    if identifier.version != 4 or identifier.variant != uuid.RFC_4122:
        raise IdentityError("invalid-uuid4", "keyless minting requires an RFC 9562 UUIDv4")
    tail = hash_bytes(RAPPID_SPACE, identifier.bytes)
    return _format_rappid(owner, slug, tail)


def _read_der_length(data: bytes, offset: int) -> tuple[int, int]:
    if offset >= len(data):
        raise IdentityError("invalid-spki", "truncated DER length")
    first = data[offset]
    offset += 1
    if first < 0x80:
        return first, offset
    count = first & 0x7F
    if count == 0 or count > 4 or offset + count > len(data):
        raise IdentityError("invalid-spki", "invalid DER length")
    encoded = data[offset : offset + count]
    if encoded[0] == 0:
        raise IdentityError("invalid-spki", "non-minimal DER length")
    length = int.from_bytes(encoded, "big")
    if length < 0x80:
        raise IdentityError("invalid-spki", "non-minimal DER long length")
    return length, offset + count


def _read_der_tlv(data: bytes, offset: int) -> tuple[int, bytes, int]:
    if offset >= len(data):
        raise IdentityError("invalid-spki", "truncated DER value")
    tag = data[offset]
    length, content_offset = _read_der_length(data, offset + 1)
    end = content_offset + length
    if end > len(data):
        raise IdentityError("invalid-spki", "truncated DER content")
    return tag, data[content_offset:end], end


def validate_spki_der(spki_der: bytes | bytearray | memoryview) -> bytes:
    """Validate the outer RFC 5280 SubjectPublicKeyInfo DER structure."""

    if not isinstance(spki_der, (bytes, bytearray, memoryview)):
        raise TypeError("SPKI must be DER bytes")
    data = bytes(spki_der)
    tag, outer, end = _read_der_tlv(data, 0)
    if tag != 0x30 or end != len(data):
        raise IdentityError("invalid-spki", "SPKI must be one DER SEQUENCE")
    algorithm_tag, algorithm, offset = _read_der_tlv(outer, 0)
    bit_tag, bit_string, final = _read_der_tlv(outer, offset)
    if algorithm_tag != 0x30 or bit_tag != 0x03 or final != len(outer):
        raise IdentityError(
            "invalid-spki", "SPKI must contain AlgorithmIdentifier and BIT STRING"
        )
    oid_tag, oid, algorithm_offset = _read_der_tlv(algorithm, 0)
    if oid_tag != 0x06 or not oid:
        raise IdentityError("invalid-spki", "AlgorithmIdentifier must start with an OID")
    oid_offset = 0
    while oid_offset < len(oid):
        if oid[oid_offset] == 0x80:
            raise IdentityError("invalid-spki", "OID has a non-minimal subidentifier")
        while oid_offset < len(oid) and oid[oid_offset] & 0x80:
            oid_offset += 1
        if oid_offset >= len(oid):
            raise IdentityError("invalid-spki", "OID has an unterminated subidentifier")
        oid_offset += 1
    if algorithm_offset < len(algorithm):
        _, _, algorithm_offset = _read_der_tlv(algorithm, algorithm_offset)
    if algorithm_offset != len(algorithm):
        raise IdentityError(
            "invalid-spki", "AlgorithmIdentifier has more than one parameters value"
        )
    if not bit_string or bit_string[0] > 7:
        raise IdentityError("invalid-spki", "invalid subjectPublicKey BIT STRING")
    if len(bit_string) == 1 and bit_string[0] != 0:
        raise IdentityError("invalid-spki", "empty BIT STRING has unused bits")
    if len(bit_string) > 1 and bit_string[0]:
        mask = (1 << bit_string[0]) - 1
        if bit_string[-1] & mask:
            raise IdentityError("invalid-spki", "non-zero unused BIT STRING bits")
    return data


def mint_spki_rappid(
    owner: str, slug: str, spki_der: bytes | bytearray | memoryview
) -> str:
    """Mint a keyed identity from exact DER SubjectPublicKeyInfo octets."""

    data = validate_spki_der(spki_der)
    tail = hash_bytes(RAPPID_SPACE, data)
    return _format_rappid(owner, slug, tail)
