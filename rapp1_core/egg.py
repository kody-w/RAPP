"""Strict deterministic RAPP/1 egg packing, inspection, and staged extraction."""

from __future__ import annotations

import os
import shutil
import struct
import tempfile
import unicodedata
import zlib
from dataclasses import dataclass, replace
from pathlib import Path, PureWindowsPath
from typing import Any, Mapping

from .canonical import CanonicalizationError, canonical_bytes, strict_loads
from .errors import EggError, FrameError, IdentityError, SignatureStructureError
from .frame import validate_utc
from .hashing import EGG_FILE_SPACE, EGG_MANIFEST_SPACE, hash_bytes, hash_value
from .identity import LOWER_HASH_RE, Rappid, parse_rappid
from .jws import parse_detached_jws
from .trust import CheckResult, CheckStatus, RegistryEvidence, TrustStatus

MANIFEST_KEYS = frozenset(
    {"schema", "variant", "rappid", "created_utc", "contents", "payload", "sig"}
)
CONTENT_KEYS = frozenset({"path", "hash"})
VARIANTS = frozenset(
    {"organism", "rapplication", "session", "invite", "neighborhood", "estate"}
)
JSON_VARIANTS = frozenset({"session", "invite"})
ZIP_VARIANTS = VARIANTS - JSON_VARIANTS

ZIP_LOCAL_SIGNATURE = 0x04034B50
ZIP_CENTRAL_SIGNATURE = 0x02014B50
ZIP_EOCD_SIGNATURE = 0x06054B50
ZIP_UTF8_FLAG = 1 << 11
ZIP_STORED = 0
ZIP_VERSION = 20
ZIP_DOS_TIME = 0
ZIP_DOS_DATE = (1 << 5) | 1
ZIP_LOCAL = struct.Struct("<IHHHHHIIIHH")
ZIP_CENTRAL = struct.Struct("<IHHHHHHIIIHHHHHII")
ZIP_EOCD = struct.Struct("<IHHHHIIH")


@dataclass(frozen=True)
class EggInspection:
    structurally_valid: bool
    accepted: bool
    trust_status: TrustStatus
    checks: tuple[CheckResult, ...]
    manifest: dict[str, Any] | None = None
    egg_hash: str | None = None
    egg_variants: tuple[str, ...] = ()
    signature_kids: tuple[str, ...] = ()
    error_code: str | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "structurally-valid": self.structurally_valid,
            "accepted": self.accepted,
            "trust-status": self.trust_status.value,
            "checks": [check.as_dict() for check in self.checks],
        }
        if self.manifest is not None:
            result["variant"] = self.manifest["variant"]
            result["rappid"] = self.manifest["rappid"]
        if self.egg_hash is not None:
            result["egg-hash"] = self.egg_hash
        if self.egg_variants:
            result["egg-variants"] = list(self.egg_variants)
        if self.signature_kids:
            result["signature-kids"] = list(self.signature_kids)
        if self.error_code is not None:
            result["error"] = {"code": self.error_code, "message": self.error}
        return result


@dataclass(frozen=True)
class _ZipMember:
    name: str
    data: bytes


@dataclass(frozen=True)
class _InspectedEgg:
    report: EggInspection
    members: tuple[_ZipMember, ...] = ()


def validate_egg_path(value: str) -> str:
    if type(value) is not str or not value:
        raise EggError("invalid-egg-path", "egg path must be a non-empty string")
    if unicodedata.normalize("NFC", value) != value:
        raise EggError("invalid-egg-path", "egg path must be Unicode NFC")
    if (
        value.startswith("/")
        or "\\" in value
        or "\x00" in value
    ):
        raise EggError(
            "invalid-egg-path",
            "egg path must be relative POSIX without leading slash/backslash/NUL",
        )
    segments = value.split("/")
    if any(not segment or segment in {".", ".."} for segment in segments):
        raise EggError(
            "invalid-egg-path", "egg path contains an empty, dot, or dot-dot segment"
        )
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise EggError("invalid-egg-path", "egg path is not strict UTF-8") from exc
    return value


def _validate_extraction_path(
    value: str, *, platform: str | None = None
) -> str:
    target_platform = os.name if platform is None else platform
    if target_platform == "posix":
        return value
    if target_platform != "nt":
        raise EggError(
            "unsafe-extraction-path",
            f"unsupported extraction platform: {target_platform!r}",
        )
    windows_path = PureWindowsPath(value)
    segments = value.split("/")
    if (
        windows_path.drive
        or windows_path.root
        or windows_path.is_absolute()
        or any(
            ":" in segment
            or segment.endswith((" ", "."))
            or PureWindowsPath(segment).is_reserved()
            for segment in segments
        )
    ):
        raise EggError(
            "unsafe-extraction-path",
            f"egg path cannot be represented safely on Windows: {value!r}",
        )
    return value


def _require_nfc_payload_keys(value: Any) -> None:
    if type(value) is dict:
        for key, child in value.items():
            if type(key) is str and unicodedata.normalize("NFC", key) != key:
                raise EggError(
                    "invalid-egg-payload",
                    "producer payload object keys must be Unicode NFC",
                )
            _require_nfc_payload_keys(child)
    elif type(value) is list:
        for child in value:
            _require_nfc_payload_keys(child)


def _member_filename(rappid: Rappid) -> str:
    return f"{rappid.owner}--{rappid.slug}.egg"


def _validate_path_prefixes(paths: list[str]) -> None:
    path_set = set(paths)
    for path in paths:
        if path == "manifest.json" or path.startswith("manifest.json/"):
            raise EggError(
                "path-prefix-conflict",
                "contents cannot replace manifest.json or descend from it",
            )
        segments = path.split("/")
        for length in range(1, len(segments)):
            ancestor = "/".join(segments[:length])
            if ancestor in path_set:
                raise EggError(
                    "path-prefix-conflict",
                    f"file path {ancestor!r} is an ancestor of {path!r}",
                )


def _validate_manifest(
    manifest: dict[str, Any], *, container: str
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if set(manifest) != MANIFEST_KEYS:
        raise EggError(
            "invalid-manifest-shape", "manifest must contain exactly seven members"
        )
    if manifest["schema"] != "rapp/1-egg":
        raise EggError("invalid-egg-schema", "schema must equal 'rapp/1-egg'")
    variant = manifest["variant"]
    if type(variant) is not str or variant not in VARIANTS:
        raise EggError("invalid-egg-variant", "variant is not one of the six variants")
    expected_container = "json" if variant in JSON_VARIANTS else "zip"
    if container != expected_container:
        raise EggError(
            "wrong-egg-container",
            f"{variant} requires a {expected_container.upper()} container",
        )
    try:
        parse_rappid(manifest["rappid"])
        validate_utc(manifest["created_utc"])
    except (IdentityError, FrameError) as exc:
        raise EggError("invalid-manifest-field", str(exc)) from exc
    if type(manifest["contents"]) is not list:
        raise EggError("invalid-contents", "contents must be an array")
    if type(manifest["payload"]) is not dict:
        raise EggError("invalid-egg-payload", "payload must be an object")

    paths: list[str] = []
    for entry in manifest["contents"]:
        if type(entry) is not dict or set(entry) != CONTENT_KEYS:
            raise EggError(
                "invalid-content-entry",
                "each contents entry must contain exactly path and hash",
            )
        path = validate_egg_path(entry["path"])
        if (
            type(entry["hash"]) is not str
            or LOWER_HASH_RE.fullmatch(entry["hash"]) is None
        ):
            raise EggError(
                "invalid-content-hash", "contents hash must be 64 lowercase hex"
            )
        paths.append(path)
    if len(paths) != len(set(paths)):
        raise EggError("duplicate-content-path", "manifest contains duplicate paths")
    _validate_path_prefixes(paths)
    if paths != sorted(paths, key=lambda item: item.encode("utf-8")):
        raise EggError(
            "unsorted-contents", "contents must be sorted by UTF-8 path bytes"
        )
    if variant in JSON_VARIANTS and paths:
        raise EggError("json-variant-has-files", "JSON variant contents must be []")

    signature_kids: tuple[str, ...] = ()
    if manifest["sig"] is not None:
        try:
            parsed_jws = parse_detached_jws(manifest["sig"])
        except SignatureStructureError as exc:
            raise EggError(exc.code, str(exc)) from exc
        signature_kids = (parsed_jws.kid,)
    elif variant == "invite":
        raise EggError("unsigned-invite", "invite sig is required")

    _validate_variant_shape(manifest, paths)
    canonical_bytes(manifest)
    return tuple(paths), signature_kids


def _validate_rappid_list(value: Any, *, field: str) -> tuple[Rappid, ...]:
    if type(value) is not list:
        raise EggError("invalid-egg-payload", f"{field} must be an array")
    parsed: list[Rappid] = []
    strings: list[str] = []
    for item in value:
        try:
            identity = parse_rappid(item)
        except IdentityError as exc:
            raise EggError(
                "invalid-egg-payload", f"{field} contains an invalid rappid"
            ) from exc
        parsed.append(identity)
        strings.append(item)
    if len(strings) != len(set(strings)):
        raise EggError("duplicate-member", f"{field} contains a duplicate rappid")
    locations = [(identity.owner, identity.slug) for identity in parsed]
    if len(locations) != len(set(locations)):
        raise EggError(
            "sub-egg-name-collision",
            f"{field} contains identities with colliding owner/slug names",
        )
    return tuple(parsed)


def _validate_variant_shape(manifest: dict[str, Any], paths: list[str]) -> None:
    variant = manifest["variant"]
    payload = manifest["payload"]
    if variant == "organism":
        if not {"rappid.json", "soul.md"}.issubset(paths):
            raise EggError(
                "inviable-organism", "organism must include rappid.json and soul.md"
            )
    elif variant == "rapplication":
        required = {"rappid.json", "agent.py"}
        if not required.issubset(paths):
            raise EggError(
                "inviable-rapplication",
                "rapplication must include rappid.json and root agent.py",
            )
        allowed_roots = {"rappid.json", "agent.py", "ui.html"}
        if any(
            path not in allowed_roots and not path.startswith("state/")
            for path in paths
        ):
            raise EggError(
                "inviable-rapplication",
                "rapplication contains a path outside its ratified layout",
            )
    elif variant == "session":
        if set(payload) != {"runtime", "transcript"}:
            raise EggError(
                "invalid-session-payload",
                "session payload must contain exactly runtime and transcript",
            )
        if type(payload["runtime"]) is not str or type(payload["transcript"]) is not list:
            raise EggError(
                "invalid-session-payload", "runtime/transcript have invalid types"
            )
        if any(type(turn) is not dict for turn in payload["transcript"]):
            raise EggError(
                "invalid-session-payload", "every transcript item must be an object"
            )
    elif variant == "invite":
        if set(payload) != {"target_rappid", "target_url", "target_kind"}:
            raise EggError(
                "invalid-invite-payload",
                "invite payload must contain exactly its three pointer members",
            )
        try:
            parse_rappid(payload["target_rappid"])
        except IdentityError as exc:
            raise EggError(
                "invalid-invite-payload", "target_rappid is invalid"
            ) from exc
        if type(payload["target_url"]) is not str or payload["target_kind"] not in {
            "neighborhood",
            "estate",
        }:
            raise EggError(
                "invalid-invite-payload", "target_url or target_kind is invalid"
            )
    elif variant == "neighborhood":
        if set(payload) != {"members"}:
            raise EggError(
                "invalid-neighborhood-payload",
                "neighborhood payload must contain exactly members",
            )
        members = _validate_rappid_list(payload["members"], field="members")
        expected = sorted(
            (_member_filename(member) for member in members),
            key=lambda item: item.encode("utf-8"),
        )
        if paths != expected:
            raise EggError(
                "neighborhood-member-mismatch",
                "contents do not exactly match payload.members",
            )
    elif variant == "estate":
        if set(payload) != {"neighborhoods"}:
            raise EggError(
                "invalid-estate-payload",
                "estate payload must contain exactly neighborhoods",
            )
        neighborhoods = _validate_rappid_list(
            payload["neighborhoods"], field="neighborhoods"
        )
        expected = sorted(
            (_member_filename(neighborhood) for neighborhood in neighborhoods),
            key=lambda item: item.encode("utf-8"),
        )
        if paths != expected:
            raise EggError(
                "estate-neighborhood-mismatch",
                "contents do not exactly match payload.neighborhoods",
            )


def _encode_zip(entries: list[tuple[str, bytes]]) -> bytes:
    if len(entries) > 0xFFFF:
        raise EggError("zip64-forbidden", "ZIP64 entry counts are not supported")
    local_parts: list[bytes] = []
    central_parts: list[bytes] = []
    offset = 0
    for name, data in entries:
        name_octets = name.encode("utf-8")
        if len(name_octets) > 0xFFFF or len(data) > 0xFFFFFFFF:
            raise EggError("zip64-forbidden", "ZIP64 sizes are not supported")
        checksum = zlib.crc32(data) & 0xFFFFFFFF
        local_header = ZIP_LOCAL.pack(
            ZIP_LOCAL_SIGNATURE,
            ZIP_VERSION,
            ZIP_UTF8_FLAG,
            ZIP_STORED,
            ZIP_DOS_TIME,
            ZIP_DOS_DATE,
            checksum,
            len(data),
            len(data),
            len(name_octets),
            0,
        )
        local_parts.extend((local_header, name_octets, data))
        central_parts.extend(
            (
                ZIP_CENTRAL.pack(
                    ZIP_CENTRAL_SIGNATURE,
                    ZIP_VERSION,
                    ZIP_VERSION,
                    ZIP_UTF8_FLAG,
                    ZIP_STORED,
                    ZIP_DOS_TIME,
                    ZIP_DOS_DATE,
                    checksum,
                    len(data),
                    len(data),
                    len(name_octets),
                    0,
                    0,
                    0,
                    0,
                    0,
                    offset,
                ),
                name_octets,
            )
        )
        offset += len(local_header) + len(name_octets) + len(data)
    central = b"".join(central_parts)
    eocd = ZIP_EOCD.pack(
        ZIP_EOCD_SIGNATURE,
        0,
        0,
        len(entries),
        len(entries),
        len(central),
        offset,
        0,
    )
    return b"".join(local_parts) + central + eocd


def _slice(data: bytes, offset: int, length: int, *, label: str) -> bytes:
    end = offset + length
    if offset < 0 or length < 0 or end > len(data):
        raise EggError("invalid-zip", f"truncated {label}")
    return data[offset:end]


def _decode_zip_name(name_octets: bytes) -> str:
    try:
        name = name_octets.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise EggError("invalid-zip-name", "ZIP filename is not UTF-8") from exc
    if name.encode("utf-8") != name_octets:
        raise EggError("invalid-zip-name", "ZIP filename UTF-8 is not canonical")
    return name


def _decode_zip(data: bytes) -> tuple[_ZipMember, ...]:
    if len(data) < ZIP_EOCD.size:
        raise EggError("invalid-zip", "ZIP is too short")
    eocd_offset = len(data) - ZIP_EOCD.size
    (
        signature,
        disk,
        central_disk,
        disk_entries,
        total_entries,
        central_size,
        central_offset,
        comment_length,
    ) = ZIP_EOCD.unpack_from(data, eocd_offset)
    if (
        signature != ZIP_EOCD_SIGNATURE
        or disk != 0
        or central_disk != 0
        or disk_entries != total_entries
        or comment_length != 0
        or central_offset + central_size != eocd_offset
    ):
        raise EggError(
            "invalid-zip-metadata", "ZIP EOCD is not the deterministic RAPP form"
        )

    central_entries: list[tuple[str, int, int, int, int]] = []
    cursor = central_offset
    for _ in range(total_entries):
        header = _slice(data, cursor, ZIP_CENTRAL.size, label="central header")
        fields = ZIP_CENTRAL.unpack(header)
        (
            central_signature,
            made_by,
            needed,
            flags,
            method,
            dos_time,
            dos_date,
            checksum,
            compressed_size,
            uncompressed_size,
            name_length,
            extra_length,
            member_comment_length,
            start_disk,
            internal_attributes,
            external_attributes,
            local_offset,
        ) = fields
        cursor += ZIP_CENTRAL.size
        name_octets = _slice(data, cursor, name_length, label="central filename")
        cursor += name_length
        _slice(data, cursor, extra_length + member_comment_length, label="central extras")
        cursor += extra_length + member_comment_length
        if (
            central_signature != ZIP_CENTRAL_SIGNATURE
            or flags != ZIP_UTF8_FLAG
            or method != ZIP_STORED
            or dos_time != ZIP_DOS_TIME
            or dos_date != ZIP_DOS_DATE
            or compressed_size != uncompressed_size
            or extra_length != 0
            or member_comment_length != 0
            or start_disk != 0
        ):
            raise EggError(
                "invalid-zip-metadata",
                "central entry is not stored/epoch/UTF-8/no-extras",
            )
        central_entries.append(
            (
                _decode_zip_name(name_octets),
                checksum,
                uncompressed_size,
                local_offset,
                flags,
            )
        )
    if cursor != central_offset + central_size:
        raise EggError("invalid-zip", "central directory size is inconsistent")

    names = [entry[0] for entry in central_entries]
    if len(names) != len(set(names)):
        raise EggError("duplicate-zip-member", "ZIP contains duplicate member names")

    members: list[_ZipMember] = []
    expected_local_offset = 0
    for name, checksum, size, local_offset, central_flags in central_entries:
        if local_offset != expected_local_offset:
            raise EggError(
                "invalid-zip-order", "local entries are not contiguous central order"
            )
        header = _slice(data, local_offset, ZIP_LOCAL.size, label="local header")
        (
            local_signature,
            needed,
            flags,
            method,
            dos_time,
            dos_date,
            local_checksum,
            compressed_size,
            uncompressed_size,
            name_length,
            extra_length,
        ) = ZIP_LOCAL.unpack(header)
        name_offset = local_offset + ZIP_LOCAL.size
        name_octets = _slice(data, name_offset, name_length, label="local filename")
        extra_offset = name_offset + name_length
        _slice(data, extra_offset, extra_length, label="local extra")
        body_offset = extra_offset + extra_length
        body = _slice(data, body_offset, compressed_size, label="member data")
        if (
            local_signature != ZIP_LOCAL_SIGNATURE
            or flags != ZIP_UTF8_FLAG
            or flags != central_flags
            or method != ZIP_STORED
            or dos_time != ZIP_DOS_TIME
            or dos_date != ZIP_DOS_DATE
            or local_checksum != checksum
            or compressed_size != size
            or uncompressed_size != size
            or extra_length != 0
            or _decode_zip_name(name_octets) != name
            or zlib.crc32(body) & 0xFFFFFFFF != checksum
        ):
            raise EggError(
                "invalid-zip-metadata",
                "local entry differs from deterministic central metadata",
            )
        members.append(_ZipMember(name=name, data=body))
        expected_local_offset = body_offset + compressed_size
    if expected_local_offset != central_offset:
        raise EggError("invalid-zip", "unexpected octets before central directory")
    if _encode_zip([(member.name, member.data) for member in members]) != data:
        raise EggError(
            "invalid-zip-metadata",
            "ZIP bytes differ from the deterministic RAPP encoding",
        )
    return tuple(members)


def _failure(exc: Exception, checks: list[CheckResult]) -> _InspectedEgg:
    if isinstance(exc, (EggError, CanonicalizationError)):
        code = exc.code
    else:
        code = "invalid-egg"
    checks.append(CheckResult("egg", CheckStatus.FAIL, str(exc)))
    return _InspectedEgg(
        EggInspection(
            structurally_valid=False,
            accepted=False,
            trust_status=TrustStatus.DRIFT,
            checks=tuple(checks),
            error_code=code,
            error=str(exc),
        )
    )


def _inspect(data: bytes, *, nesting: int = 0) -> _InspectedEgg:
    checks: list[CheckResult] = []
    try:
        if nesting > 3:
            raise EggError("egg-nesting-exceeded", "egg nesting exceeds estate depth")
        if data.startswith(b"PK\x03\x04"):
            container = "zip"
            members = _decode_zip(data)
            if not members or members[0].name != "manifest.json":
                raise EggError(
                    "manifest-not-first", "manifest.json must be the first ZIP entry"
                )
            manifest_octets = members[0].data
        else:
            container = "json"
            members = ()
            manifest_octets = data

        parsed = strict_loads(manifest_octets)
        if type(parsed) is not dict:
            raise EggError("invalid-manifest-shape", "manifest root must be an object")
        if canonical_bytes(parsed) != manifest_octets:
            raise EggError(
                "noncanonical-manifest", "manifest octets must be canonical JSON"
            )
        paths, root_signature_kids = _validate_manifest(parsed, container=container)
        checks.append(
            CheckResult("manifest", CheckStatus.PASS, "manifest shape and form pass")
        )

        if container == "zip":
            names = tuple(member.name for member in members)
            if names != ("manifest.json",) + paths:
                raise EggError(
                    "archive-member-mismatch",
                    "archive order/set must equal manifest then contents order",
                )
            file_members = members[1:]
            for entry, member in zip(parsed["contents"], file_members):
                expected = hash_bytes(EGG_FILE_SPACE, member.data)
                if entry["hash"] != expected:
                    raise EggError(
                        "content-hash-mismatch", f"hash mismatch for {member.name}"
                    )
            checks.append(
                CheckResult(
                    "integrity",
                    CheckStatus.PASS,
                    "archive metadata, order, set, and file hashes pass",
                )
            )
        else:
            file_members = ()
            checks.append(
                CheckResult("integrity", CheckStatus.PASS, "canonical JSON egg passes")
            )

        nested_signature_kids: list[str] = []
        nested_variants: list[str] = []
        if parsed["variant"] in {"neighborhood", "estate"}:
            payload_key = (
                "members" if parsed["variant"] == "neighborhood" else "neighborhoods"
            )
            expected_variant = (
                "organism" if parsed["variant"] == "neighborhood" else "neighborhood"
            )
            expected_by_name = {
                _member_filename(parse_rappid(identity)): identity
                for identity in parsed["payload"][payload_key]
            }
            for member in file_members:
                child = _inspect(member.data, nesting=nesting + 1)
                if not child.report.structurally_valid:
                    raise EggError(
                        "invalid-sub-egg",
                        f"{member.name}: {child.report.error or 'invalid sub-egg'}",
                    )
                assert child.report.manifest is not None
                if (
                    child.report.manifest["variant"] != expected_variant
                    or child.report.manifest["rappid"] != expected_by_name[member.name]
                ):
                    raise EggError(
                        "sub-egg-mismatch",
                        f"{member.name} variant/rappid does not match its parent",
                    )
                nested_signature_kids.extend(child.report.signature_kids)
                nested_variants.extend(child.report.egg_variants)
        checks.append(
            CheckResult(
                "viability",
                CheckStatus.PASS,
                "variant and recursive viability checks pass",
            )
        )

        manifest_address_value = {
            key: value for key, value in parsed.items() if key != "sig"
        }
        egg_hash = hash_value(EGG_MANIFEST_SPACE, manifest_address_value)
        signatures = root_signature_kids + tuple(nested_signature_kids)
        checks.append(
            CheckResult(
                "trust",
                CheckStatus.UNVERIFIED,
                "structural inspection does not authenticate registry keys or signatures",
            )
        )
        report = EggInspection(
            structurally_valid=True,
            accepted=False,
            trust_status=TrustStatus.UNVERIFIED,
            checks=tuple(checks),
            manifest=parsed,
            egg_hash=egg_hash,
            egg_variants=(parsed["variant"], *nested_variants),
            signature_kids=signatures,
        )
        return _InspectedEgg(report=report, members=members)
    except Exception as exc:
        return _failure(exc, checks)


def inspect_egg(data: bytes | bytearray | memoryview) -> EggInspection:
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("inspect_egg requires bytes")
    return _inspect(bytes(data)).report


def _accept_inspected_egg(
    inspected: EggInspection, registry: RegistryEvidence | None
) -> EggInspection:
    if not inspected.structurally_valid:
        return inspected
    if inspected.signature_kids:
        return replace(inspected, trust_status=TrustStatus.UNVERIFIED)
    if registry is None or not registry.authenticated:
        return inspected
    if not registry.fresh:
        checks = inspected.checks[:-1] + (
            CheckResult(
                "trust",
                CheckStatus.UNVERIFIED,
                "registry is older than the caller's staleness policy",
            ),
        )
        return replace(inspected, trust_status=TrustStatus.STALE, checks=checks)
    assert inspected.manifest is not None
    missing_variants = sorted(
        set(inspected.egg_variants)
        - registry.registered_egg_variants
    )
    if missing_variants:
        checks = inspected.checks[:-1] + (
            CheckResult(
                "trust",
                CheckStatus.UNVERIFIED,
                "authenticated registry has no exact registration for egg "
                f"variant(s): {', '.join(missing_variants)}",
            ),
        )
        return replace(
            inspected,
            trust_status=TrustStatus.UNVERIFIED,
            checks=checks,
        )
    checks = inspected.checks[:-1] + (
        CheckResult(
            "trust",
            CheckStatus.PASS,
            "fresh authenticated registry exactly registers every unsigned "
            "egg variant in the recursive artifact",
        ),
    )
    return replace(
        inspected,
        accepted=True,
        trust_status=TrustStatus.VERIFIED,
        checks=checks,
    )


def accept_egg(
    data: bytes | bytearray | memoryview,
    *,
    registry: RegistryEvidence | None = None,
) -> EggInspection:
    return _accept_inspected_egg(inspect_egg(data), registry)


def pack_egg(
    *,
    variant: str,
    rappid: str,
    created_utc: str,
    payload: dict[str, Any],
    files: Mapping[str, bytes] | None = None,
    sig: str | None = None,
) -> bytes:
    """Pack one of all six variants into canonical JSON or deterministic ZIP."""

    if variant not in VARIANTS:
        raise EggError("invalid-egg-variant", "variant is not one of the six variants")
    _require_nfc_payload_keys(payload)
    if (
        variant == "session"
        and type(payload) is dict
        and type(payload.get("runtime")) is str
        and unicodedata.normalize("NFC", payload["runtime"]) != payload["runtime"]
    ):
        raise EggError(
            "invalid-session-payload",
            "producer session runtime identifier must be Unicode NFC",
        )
    supplied_files = {} if files is None else dict(files)
    normalized_files: dict[str, bytes] = {}
    for path, content in supplied_files.items():
        validated_path = validate_egg_path(path)
        if validated_path == "manifest.json":
            raise EggError("reserved-egg-path", "manifest.json is generated by the packer")
        if not isinstance(content, (bytes, bytearray, memoryview)):
            raise TypeError(f"file {path!r} content must be bytes")
        normalized_files[validated_path] = bytes(content)
    if len(normalized_files) != len(supplied_files):
        raise EggError("duplicate-content-path", "normalized file paths collide")
    if variant in JSON_VARIANTS and normalized_files:
        raise EggError("json-variant-has-files", "JSON variants cannot pack files")

    paths = sorted(normalized_files, key=lambda item: item.encode("utf-8"))
    contents = [
        {"path": path, "hash": hash_bytes(EGG_FILE_SPACE, normalized_files[path])}
        for path in paths
    ]
    manifest: dict[str, Any] = {
        "schema": "rapp/1-egg",
        "variant": variant,
        "rappid": rappid,
        "created_utc": created_utc,
        "contents": contents,
        "payload": payload,
        "sig": sig,
    }
    _validate_manifest(
        manifest, container="json" if variant in JSON_VARIANTS else "zip"
    )
    manifest_octets = canonical_bytes(manifest)
    if variant in JSON_VARIANTS:
        packed = manifest_octets
    else:
        packed = _encode_zip(
            [("manifest.json", manifest_octets)]
            + [(path, normalized_files[path]) for path in paths]
        )
    inspected = inspect_egg(packed)
    if not inspected.structurally_valid:
        raise EggError(
            inspected.error_code or "invalid-packed-egg",
            inspected.error or "packer produced an invalid egg",
        )
    return packed


def _resolved_staging_path(stage: Path, member_name: str) -> Path:
    stage_root = stage.resolve(strict=True)
    candidate = stage.joinpath(*member_name.split("/")).resolve(strict=False)
    try:
        candidate.relative_to(stage_root)
    except ValueError as exc:
        raise EggError(
            "extraction-path-escape",
            f"archive member resolves outside staging: {member_name}",
        ) from exc
    if candidate == stage_root:
        raise EggError(
            "extraction-path-escape", "archive member resolves to staging root"
        )
    return candidate


def extract_egg(
    data: bytes | bytearray | memoryview,
    destination: str | os.PathLike[str],
    *,
    registry: RegistryEvidence | None = None,
) -> Path:
    """Accept the complete egg, then extract into a sibling staging directory."""

    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("extract_egg requires bytes")
    inspected = _inspect(bytes(data))
    if not inspected.report.structurally_valid:
        raise EggError(
            inspected.report.error_code or "invalid-egg",
            inspected.report.error or "egg verification failed",
        )
    accepted = _accept_inspected_egg(inspected.report, registry)
    if not accepted.accepted:
        code = (
            "signed-egg-unverified"
            if inspected.report.signature_kids
            else "egg-not-accepted"
        )
        raise EggError(
            code,
            "egg extraction requires fresh authenticated acceptance; "
            "signature verification is unsupported",
        )
    assert inspected.report.manifest is not None
    if inspected.report.manifest["variant"] in JSON_VARIANTS:
        raise EggError("json-egg-not-extractable", "JSON variants have no file tree")
    for member in inspected.members:
        _validate_extraction_path(member.name)

    target = Path(destination)
    if target.exists():
        raise EggError("destination-exists", "extraction destination already exists")
    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)
    stage = Path(
        tempfile.mkdtemp(prefix=f".{target.name}.rapp1-stage-", dir=str(parent))
    )
    try:
        for member in inspected.members:
            output = _resolved_staging_path(stage, member.name)
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("xb") as handle:
                handle.write(member.data)
        os.replace(stage, target)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return target
