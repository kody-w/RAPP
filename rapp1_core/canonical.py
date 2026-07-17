"""Strict RAPP I-JSON parsing and RFC 8785 canonicalization."""

from __future__ import annotations

import json
import math
from decimal import Decimal, InvalidOperation
from typing import Any

import rfc8785

from .errors import CanonicalizationError

MAX_CANONICAL_BYTES = 1024 * 1024
MAX_JSON_DEPTH = 64
MAX_SAFE_INTEGER = (1 << 53) - 1

JsonValue = Any


def _has_lone_surrogate(value: str) -> bool:
    return any(0xD800 <= ord(character) <= 0xDFFF for character in value)


def _number_text(value: float) -> str:
    try:
        return rfc8785.dumps(value).decode("ascii")
    except Exception as exc:
        raise CanonicalizationError(
            "number-not-ijson", "number is outside the RFC 8785 binary64 domain"
        ) from exc


def _validate_number_token(token: str) -> float:
    try:
        binary64 = float(token)
    except (OverflowError, ValueError) as exc:
        raise CanonicalizationError(
            "number-not-binary64", f"number token does not map to binary64: {token}"
        ) from exc
    if not math.isfinite(binary64):
        raise CanonicalizationError(
            "number-not-finite", f"number token maps to a non-finite value: {token}"
        )
    rendered = _number_text(binary64)
    try:
        if Decimal(token) != Decimal(rendered):
            raise CanonicalizationError(
                "number-not-roundtrip",
                f"number token changes mathematical value through binary64: {token}",
            )
    except InvalidOperation as exc:
        raise CanonicalizationError(
            "number-not-ijson", f"invalid JSON number token: {token}"
        ) from exc
    return binary64


def _parse_integer(token: str) -> int:
    _validate_number_token(token)
    return int(token)


def _parse_float(token: str) -> float:
    return _validate_number_token(token)


def _reject_constant(token: str) -> None:
    raise CanonicalizationError(
        "number-not-finite", f"non-finite JSON number is forbidden: {token}"
    )


def _object_from_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CanonicalizationError(
                "duplicate-key", f"duplicate JSON object member: {key!r}"
            )
        result[key] = value
    return result


def _prepare_for_jcs(value: Any, depth: int = 1) -> JsonValue:
    if depth > MAX_JSON_DEPTH:
        raise CanonicalizationError(
            "depth-exceeded", f"JSON nesting depth exceeds {MAX_JSON_DEPTH}"
        )
    if value is None or type(value) is bool:
        return value
    if type(value) is int:
        binary64 = _validate_number_token(str(value))
        if -MAX_SAFE_INTEGER <= value <= MAX_SAFE_INTEGER:
            return value
        return binary64
    if type(value) is float:
        if not math.isfinite(value):
            raise CanonicalizationError(
                "number-not-finite", "non-finite JSON number is forbidden"
            )
        return value
    if type(value) is str:
        if _has_lone_surrogate(value):
            raise CanonicalizationError(
                "lone-surrogate", "unpaired UTF-16 surrogate is forbidden"
            )
        return value
    if type(value) is list:
        prepared: list[JsonValue] = []
        for item in value:
            child_depth = depth + 1 if type(item) in (dict, list) else depth
            prepared.append(_prepare_for_jcs(item, child_depth))
        return prepared
    if type(value) is dict:
        prepared_object: dict[str, JsonValue] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise CanonicalizationError(
                    "non-string-key", "JSON object member names must be strings"
                )
            if _has_lone_surrogate(key):
                raise CanonicalizationError(
                    "lone-surrogate", "unpaired UTF-16 surrogate in member name"
                )
            child_depth = depth + 1 if type(item) in (dict, list) else depth
            prepared_object[key] = _prepare_for_jcs(item, child_depth)
        return prepared_object
    raise CanonicalizationError(
        "non-json-type", f"value of type {type(value).__name__} is not JSON"
    )


def canonical_bytes(value: Any) -> bytes:
    """Return RFC 8785 bytes after enforcing the complete RAPP input profile."""

    prepared = _prepare_for_jcs(value)
    try:
        encoded = rfc8785.dumps(prepared)
    except Exception as exc:
        raise CanonicalizationError(
            "canonicalization-failed", "RFC 8785 canonicalization failed"
        ) from exc
    if len(encoded) > MAX_CANONICAL_BYTES:
        raise CanonicalizationError(
            "canonical-size-exceeded",
            f"canonical form exceeds {MAX_CANONICAL_BYTES} bytes",
        )
    return encoded


def strict_loads(data: bytes | bytearray | memoryview) -> JsonValue:
    """Parse UTF-8 JSON without repair and validate its canonical-domain limits."""

    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("strict_loads accepts UTF-8 bytes, not text")
    octets = bytes(data)
    if octets.startswith(b"\xef\xbb\xbf"):
        raise CanonicalizationError("utf8-bom", "a UTF-8 byte-order mark is forbidden")
    try:
        text = octets.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise CanonicalizationError("invalid-utf8", "input is not strict UTF-8") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_object_from_pairs,
            parse_int=_parse_integer,
            parse_float=_parse_float,
            parse_constant=_reject_constant,
        )
    except CanonicalizationError:
        raise
    except (json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise CanonicalizationError("invalid-json", "input is not valid JSON") from exc
    canonical_bytes(value)
    return value


def require_canonical_json(data: bytes | bytearray | memoryview) -> JsonValue:
    """Parse JSON and require its source octets to already be canonical."""

    octets = bytes(data)
    value = strict_loads(octets)
    if canonical_bytes(value) != octets:
        raise CanonicalizationError(
            "noncanonical-json", "serialized JSON is not its RFC 8785 canonical form"
        )
    return value
