"""RAPP/1 frame construction, structural inspection, and trust-gated acceptance."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, replace
from datetime import datetime
from threading import RLock
from typing import Any

from .canonical import CanonicalizationError, canonical_bytes, strict_loads
from .errors import FrameError, IdentityError, SignatureStructureError
from .hashing import PARTICLE_SPACE, WAVE_SPACE, hash_value
from .identity import LOWER_HASH_RE, parse_stream_id, validate_kind
from .jws import parse_detached_jws
from .trust import (
    AuthenticatedHeadProof,
    CheckResult,
    CheckStatus,
    HeadState,
    RegistryEvidence,
    TrustStatus,
)

FRAME_KEYS = frozenset(
    {
        "spec",
        "kind",
        "stream_id",
        "seq",
        "utc",
        "payload",
        "payload_hash",
        "frame_hash",
        "prev",
        "prev_wave",
        "sig",
    }
)
UTC_RE = re.compile(
    r"^(?P<year>[0-9]{4})-(?P<month>[0-9]{2})-(?P<day>[0-9]{2})"
    r"T(?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}):(?P<second>[0-9]{2})"
    r"\.(?P<millisecond>[0-9]{3})Z$",
    re.ASCII,
)
UINT53_MAX = (1 << 53) - 1
REGENESIS_KINDS = {
    "memory.re-genesis": "memory",
    "swarm.re-genesis": "swarm",
    "body.re-genesis": "body",
}


def _require_nfc_payload_keys(value: Any) -> None:
    if type(value) is dict:
        for key, child in value.items():
            if type(key) is str and unicodedata.normalize("NFC", key) != key:
                raise FrameError(
                    "invalid-payload",
                    "producer payload object keys must be Unicode NFC",
                    step="1",
                )
            _require_nfc_payload_keys(child)
    elif type(value) is list:
        for child in value:
            _require_nfc_payload_keys(child)


@dataclass(frozen=True)
class FrameInspection:
    structurally_valid: bool
    accepted: bool
    trust_status: TrustStatus
    checks: tuple[CheckResult, ...]
    frame: dict[str, Any] | None = None
    error_code: str | None = None
    error_step: str | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "structurally-valid": self.structurally_valid,
            "accepted": self.accepted,
            "trust-status": self.trust_status.value,
            "checks": [check.as_dict() for check in self.checks],
        }
        if self.frame is not None and {
            "frame_hash",
            "payload_hash",
            "stream_id",
            "seq",
        }.issubset(self.frame):
            result["frame-hash"] = self.frame["frame_hash"]
            result["payload-hash"] = self.frame["payload_hash"]
            result["stream-id"] = self.frame["stream_id"]
            result["seq"] = self.frame["seq"]
        if self.error_code is not None:
            result["error"] = {
                "code": self.error_code,
                "step": self.error_step,
                "message": self.error,
            }
        return result


def validate_utc(value: str) -> str:
    if type(value) is not str or len(value.encode("utf-8", errors="ignore")) != 24:
        raise FrameError(
            "invalid-utc", "utc must be the fixed 24-byte form", step="1"
        )
    match = UTC_RE.fullmatch(value)
    if match is None or match.group("second") == "60":
        raise FrameError(
            "invalid-utc", "utc does not match the fixed RAPP form", step="1"
        )
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError as exc:
        raise FrameError(
            "invalid-utc", "utc is not a calendar-valid date-time", step="1"
        ) from exc
    return value


def _validate_hash(value: Any, *, field: str, nullable: bool = False) -> None:
    if nullable and value is None:
        return
    if type(value) is not str or LOWER_HASH_RE.fullmatch(value) is None:
        raise FrameError(
            "invalid-hash", f"{field} must be 64 lowercase hex or allowed null", step="1"
        )


def _is_regenesis(frame: dict[str, Any]) -> bool:
    return frame.get("kind") in REGENESIS_KINDS


def _validate_regenesis_shape(frame: dict[str, Any]) -> None:
    if frame["seq"] != 0:
        raise FrameError(
            "invalid-re-genesis-seq", "re-genesis must have seq 0", step="1"
        )
    if frame["sig"] is None:
        raise FrameError(
            "unsigned-re-genesis", "re-genesis requires a structural JWS", step="1"
        )
    payload = frame["payload"]
    if set(payload) != {"migrated_from"} or type(payload["migrated_from"]) is not dict:
        raise FrameError(
            "invalid-re-genesis-payload",
            "re-genesis payload must contain exactly migrated_from",
            step="1",
        )
    migrated = payload["migrated_from"]
    if set(migrated) != {"stream_id", "terminal_seal", "terminal_seq"}:
        raise FrameError(
            "invalid-re-genesis-payload",
            "migrated_from must contain exactly stream_id, terminal_seal, terminal_seq",
            step="1",
        )
    try:
        parse_stream_id(migrated["stream_id"])
    except IdentityError as exc:
        raise FrameError(
            "invalid-re-genesis-payload",
            "migrated_from.stream_id is invalid",
            step="1",
        ) from exc
    _validate_hash(migrated["terminal_seal"], field="terminal_seal")
    if (
        type(migrated["terminal_seq"]) is not int
        or not 0 <= migrated["terminal_seq"] <= UINT53_MAX
    ):
        raise FrameError(
            "invalid-re-genesis-payload",
            "migrated_from.terminal_seq must be uint53",
            step="1",
        )


def _shape_and_family(
    frame: dict[str, Any],
    registry: RegistryEvidence | None,
) -> tuple[str, CheckStatus, str]:
    if set(frame) != FRAME_KEYS:
        missing = sorted(FRAME_KEYS - set(frame))
        extra = sorted(set(frame) - FRAME_KEYS)
        raise FrameError(
            "invalid-frame-shape",
            f"frame must have exactly eleven keys; missing={missing}, extra={extra}",
            step="1",
        )
    if frame["spec"] != "rapp/1":
        raise FrameError("invalid-spec", "spec must equal 'rapp/1'", step="1")
    try:
        validate_kind(frame["kind"])
        stream = parse_stream_id(frame["stream_id"])
    except IdentityError as exc:
        raise FrameError(exc.code, str(exc), step="1") from exc
    if type(frame["seq"]) is not int or not 0 <= frame["seq"] <= UINT53_MAX:
        raise FrameError(
            "invalid-seq", "seq must be a non-exponent uint53 integer", step="1"
        )
    validate_utc(frame["utc"])
    if type(frame["payload"]) is not dict:
        raise FrameError("invalid-payload", "payload must be an object", step="1")
    _validate_hash(frame["payload_hash"], field="payload_hash")
    _validate_hash(frame["frame_hash"], field="frame_hash")
    _validate_hash(frame["prev"], field="prev", nullable=True)
    _validate_hash(frame["prev_wave"], field="prev_wave", nullable=True)
    if frame["sig"] is not None:
        try:
            parse_detached_jws(frame["sig"])
        except SignatureStructureError as exc:
            raise FrameError(exc.code, str(exc), step="1") from exc
    regenesis = _is_regenesis(frame)
    if regenesis:
        _validate_regenesis_shape(frame)

    if registry is None or not registry.authenticated:
        if regenesis:
            raise FrameError(
                "missing-re-genesis-context",
                "re-genesis requires an authenticated registered reset",
                step="1",
            )
        return (
            stream.family,
            CheckStatus.UNVERIFIED,
            "shape and local grammar pass; kind registry is not authenticated",
        )
    registered_family = registry.kind_families.get(frame["kind"])
    if registered_family is None:
        if registry.fresh or regenesis:
            raise FrameError(
                "unregistered-kind",
                f"kind {frame['kind']!r} is absent from the authenticated registry",
                step="1",
            )
        return (
            stream.family,
            CheckStatus.UNVERIFIED,
            "shape passes; stale registry cannot decide whether kind is registered",
        )
    if registered_family not in {"memory", "body", "swarm"}:
        raise FrameError(
            "invalid-kind-family", "registry contains an invalid family", step="1"
        )
    if registered_family != stream.family:
        raise FrameError(
            "kind-stream-mismatch",
            f"kind family {registered_family!r} cannot use {stream.family!r} stream",
            step="1",
        )
    if regenesis:
        expected_family = REGENESIS_KINDS[frame["kind"]]
        if expected_family != stream.family:
            raise FrameError(
                "re-genesis-family-mismatch",
                "re-genesis kind does not match its stream family",
                step="1",
            )
        if registry.genesis_hashes.get(frame["stream_id"]) != frame["frame_hash"]:
            raise FrameError(
                "unregistered-re-genesis",
                "authenticated registry does not name this reset genesis",
                step="1",
            )
    return stream.family, CheckStatus.PASS, "shape, grammar, and registry family pass"


def _failure(
    exc: Exception,
    checks: list[CheckResult],
    *,
    frame: dict[str, Any] | None = None,
) -> FrameInspection:
    if isinstance(exc, FrameError):
        code, step = exc.code, exc.step
    elif isinstance(exc, CanonicalizationError):
        code, step = exc.code, "1"
    else:
        code, step = "invalid-frame", "1"
    checks.append(CheckResult(step or "1", CheckStatus.FAIL, str(exc)))
    return FrameInspection(
        structurally_valid=False,
        accepted=False,
        trust_status=TrustStatus.DRIFT,
        checks=tuple(checks),
        frame=frame,
        error_code=code,
        error_step=step,
        error=str(exc),
    )


def _validate_head_state(head: HeadState) -> None:
    try:
        parse_stream_id(head.stream_id)
    except IdentityError as exc:
        raise FrameError("invalid-head", "head has an invalid stream_id", step="4") from exc
    if type(head.seq) is not int or not 0 <= head.seq <= UINT53_MAX:
        raise FrameError("invalid-head", "head has an invalid seq", step="4")
    try:
        validate_utc(head.utc)
    except FrameError as exc:
        raise FrameError("invalid-head", "head has an invalid utc", step="4") from exc
    try:
        _validate_hash(head.payload_hash, field="head.payload_hash")
        _validate_hash(head.frame_hash, field="head.frame_hash")
        if head.genesis_hash is not None:
            _validate_hash(head.genesis_hash, field="head.genesis_hash")
    except FrameError as exc:
        raise FrameError("invalid-head", "head has an invalid hash", step="4") from exc
    if head.signature_present is not None and type(head.signature_present) is not bool:
        raise FrameError(
            "invalid-head", "head signature_present must be bool or null", step="4"
        )


def _head_proof(head: HeadState) -> AuthenticatedHeadProof:
    if head.genesis_hash is None or type(head.signature_present) is not bool:
        raise FrameError(
            "head-proof-unverified",
            "head lacks genesis or signature-presence proof",
            step="head",
        )
    return AuthenticatedHeadProof(
        stream_id=head.stream_id,
        seq=head.seq,
        utc=head.utc,
        payload_hash=head.payload_hash,
        frame_hash=head.frame_hash,
        genesis_hash=head.genesis_hash,
        signature_present=head.signature_present,
    )


def _validate_head_proof(
    head: HeadState, proof: AuthenticatedHeadProof
) -> None:
    if not isinstance(proof, AuthenticatedHeadProof):
        raise FrameError(
            "invalid-head-proof",
            "head proof must be an AuthenticatedHeadProof",
            step="head",
        )
    expected = _head_proof(head)
    if proof != expected:
        raise FrameError(
            "head-proof-mismatch",
            "authenticated head proof does not bind the supplied head exactly",
            step="head",
        )


def _registry_snapshot(registry: RegistryEvidence) -> RegistryEvidence:
    if not isinstance(registry, RegistryEvidence):
        raise TypeError("registry must be RegistryEvidence")
    return RegistryEvidence(
        kind_families=registry.kind_families,
        deprecated_kinds=registry.deprecated_kinds,
        genesis_hashes=registry.genesis_hashes,
        registered_egg_variants=registry.registered_egg_variants,
        authenticated=registry.authenticated,
        fresh=registry.fresh,
    )


def _head_epoch_problem(
    head: HeadState, registry: RegistryEvidence | None
) -> tuple[TrustStatus, str, str] | None:
    if registry is None or not registry.authenticated:
        return (
            TrustStatus.UNVERIFIED,
            "head-epoch-unverified",
            "head epoch requires an authenticated registry",
        )
    if not registry.fresh:
        return (
            TrustStatus.STALE,
            "head-epoch-stale",
            "head epoch cannot be extended with a stale registry",
        )
    current_genesis = registry.genesis_hashes.get(head.stream_id)
    if head.genesis_hash is None or current_genesis is None:
        return (
            TrustStatus.UNVERIFIED,
            "head-epoch-unverified",
            "head lacks current registry genesis proof",
        )
    if head.genesis_hash != current_genesis:
        return (
            TrustStatus.DRIFT,
            "retired-genesis-epoch",
            "head belongs to a retired registry genesis epoch",
        )
    return None


def inspect_frame(
    frame: dict[str, Any],
    *,
    declared_stream_id: str | None = None,
    head: HeadState | None = None,
    registry: RegistryEvidence | None = None,
) -> FrameInspection:
    """Run checklist steps 1–5; never claim trust-dependent acceptance."""

    checks: list[CheckResult] = []
    try:
        canonical_bytes(frame)
        family, shape_status, shape_detail = _shape_and_family(frame, registry)
        checks.append(CheckResult("1", shape_status, shape_detail))

        if declared_stream_id is None:
            checks.append(
                CheckResult(
                    "1a",
                    CheckStatus.UNVERIFIED,
                    "declared stream context was not supplied",
                )
            )
        elif frame["stream_id"] != declared_stream_id:
            raise FrameError(
                "stream-binding-mismatch",
                "frame stream_id differs from the stream being read",
                step="1a",
            )
        else:
            checks.append(
                CheckResult("1a", CheckStatus.PASS, "stream binding matches")
            )

        expected_payload_hash = hash_value(PARTICLE_SPACE, frame["payload"])
        if frame["payload_hash"] != expected_payload_hash:
            raise FrameError(
                "payload-hash-mismatch", "payload_hash does not match payload", step="2"
            )
        checks.append(CheckResult("2", CheckStatus.PASS, "particle hash matches"))

        wave_preimage = {
            key: value
            for key, value in frame.items()
            if key not in {"frame_hash", "sig"}
        }
        expected_frame_hash = hash_value(WAVE_SPACE, wave_preimage)
        if frame["frame_hash"] != expected_frame_hash:
            raise FrameError(
                "frame-hash-mismatch", "frame_hash does not match wave preimage", step="3"
            )
        checks.append(CheckResult("3", CheckStatus.PASS, "wave hash matches"))

        seq = frame["seq"]
        if head is not None:
            _validate_head_state(head)
        if seq == 0:
            if frame["prev"] is not None:
                raise FrameError(
                    "invalid-genesis-chain", "genesis prev must be null", step="4"
                )
            if head is not None and not _is_regenesis(frame):
                raise FrameError(
                    "unexpected-genesis", "genesis cannot extend an existing head", step="4"
                )
            detail = (
                "authenticated registry authorizes structural re-genesis reset"
                if _is_regenesis(frame)
                else "genesis chain is valid"
            )
            checks.append(CheckResult("4", CheckStatus.PASS, detail))
        else:
            if frame["prev"] is None:
                raise FrameError(
                    "missing-prev", "non-genesis prev must be non-null", step="4"
                )
            if head is None:
                checks.append(
                    CheckResult(
                        "4",
                        CheckStatus.UNVERIFIED,
                        "head is absent; predecessor equality cannot be checked",
                    )
                )
            else:
                if head.stream_id != frame["stream_id"]:
                    raise FrameError(
                        "cross-stream-chain",
                        "predecessor head belongs to a different stream",
                        step="4",
                    )
                if seq != head.seq + 1 or frame["prev"] != head.payload_hash:
                    raise FrameError(
                        "chain-mismatch",
                        "seq/prev do not extend the supplied head",
                        step="4",
                    )
                if frame["utc"] < head.utc:
                    raise FrameError(
                        "time-regression",
                        "utc precedes the supplied head",
                        step="4",
                    )
                checks.append(
                    CheckResult("4", CheckStatus.PASS, "worldline chain matches head")
                )

        if family == "swarm" and seq > 0:
            if frame["prev_wave"] is None:
                raise FrameError(
                    "missing-prev-wave",
                    "non-genesis swarm frame requires prev_wave",
                    step="5",
                )
            if head is None:
                checks.append(
                    CheckResult(
                        "5",
                        CheckStatus.UNVERIFIED,
                        "head is absent; prev_wave equality cannot be checked",
                    )
                )
            elif frame["prev_wave"] != head.frame_hash:
                raise FrameError(
                    "wire-chain-mismatch",
                    "prev_wave does not match the supplied head",
                    step="5",
                )
            else:
                checks.append(
                    CheckResult("5", CheckStatus.PASS, "wire chain matches head")
                )
        else:
            if frame["prev_wave"] is not None:
                raise FrameError(
                    "unexpected-prev-wave",
                    "prev_wave must be null for this frame",
                    step="5",
                )
            checks.append(CheckResult("5", CheckStatus.PASS, "wire rule passes"))
    except Exception as exc:
        return _failure(exc, checks, frame=frame)

    status = (
        TrustStatus.STALE
        if registry is not None and registry.authenticated and not registry.fresh
        else TrustStatus.UNVERIFIED
    )
    return FrameInspection(
        structurally_valid=True,
        accepted=False,
        trust_status=status,
        checks=tuple(checks),
        frame=frame,
    )


def inspect_frame_bytes(
    data: bytes | bytearray | memoryview,
    *,
    declared_stream_id: str | None = None,
    head: HeadState | None = None,
    registry: RegistryEvidence | None = None,
) -> FrameInspection:
    checks: list[CheckResult] = []
    try:
        parsed = strict_loads(data)
        if type(parsed) is not dict:
            raise FrameError("invalid-frame-shape", "frame root must be an object", step="1")
    except Exception as exc:
        return _failure(exc, checks)
    return inspect_frame(
        parsed,
        declared_stream_id=declared_stream_id,
        head=head,
        registry=registry,
    )


def accept_frame(
    frame: dict[str, Any],
    *,
    declared_stream_id: str | None,
    head: HeadState | None = None,
    head_proof: AuthenticatedHeadProof | None = None,
    registry: RegistryEvidence | None = None,
) -> FrameInspection:
    """Accept only unsigned memory/body frames with complete external trust evidence."""

    inspected = inspect_frame(
        frame,
        declared_stream_id=declared_stream_id,
        head=head,
        registry=registry,
    )
    if not inspected.structurally_valid:
        return inspected
    checks = list(inspected.checks)
    if _is_regenesis(frame):
        checks.append(
            CheckResult(
                "6",
                CheckStatus.UNVERIFIED,
                "owner-signature verification for re-genesis is unsupported",
            )
        )
        return replace(
            inspected,
            accepted=False,
            trust_status=TrustStatus.UNVERIFIED,
            checks=tuple(checks),
        )
    if registry is None or not registry.authenticated:
        checks.append(
            CheckResult(
                "6",
                CheckStatus.UNVERIFIED,
                "acceptance requires an authenticated registry",
            )
        )
        return replace(
            inspected, trust_status=TrustStatus.UNVERIFIED, checks=tuple(checks)
        )
    if not registry.fresh:
        checks.append(
            CheckResult(
                "6",
                CheckStatus.UNVERIFIED,
                "registry is older than the caller's staleness policy",
            )
        )
        return replace(inspected, trust_status=TrustStatus.STALE, checks=tuple(checks))
    if frame["kind"] in registry.deprecated_kinds:
        checks.append(
            CheckResult(
                "append",
                CheckStatus.FAIL,
                "deprecated kind cannot be produced or appended",
            )
        )
        return replace(
            inspected,
            accepted=False,
            trust_status=TrustStatus.DRIFT,
            checks=tuple(checks),
            error_code="deprecated-kind-for-append",
            error_step="append",
            error="deprecated kind cannot be produced or appended",
        )
    if any(check.status is CheckStatus.UNVERIFIED for check in inspected.checks):
        checks.append(
            CheckResult(
                "6",
                CheckStatus.UNVERIFIED,
                "earlier checklist context is incomplete",
            )
        )
        return replace(
            inspected, trust_status=TrustStatus.UNVERIFIED, checks=tuple(checks)
        )
    assert inspected.frame is not None
    stream = parse_stream_id(inspected.frame["stream_id"])
    if inspected.frame["seq"] == 0:
        registered = registry.genesis_hashes.get(inspected.frame["stream_id"])
        if registered != inspected.frame["frame_hash"]:
            checks.append(
                CheckResult(
                    "head",
                    CheckStatus.FAIL,
                    "genesis is not the authenticated registry genesis",
                )
            )
            return replace(
                inspected, trust_status=TrustStatus.DRIFT, checks=tuple(checks)
            )
    elif head is None:
        checks.append(
            CheckResult(
                "head",
                CheckStatus.UNVERIFIED,
                "predecessor head is absent",
            )
        )
        return replace(
            inspected, trust_status=TrustStatus.UNVERIFIED, checks=tuple(checks)
        )
    elif head_proof is None:
        detail = "predecessor head lacks explicit authenticated caller proof"
        checks.append(CheckResult("head", CheckStatus.UNVERIFIED, detail))
        return replace(
            inspected,
            accepted=False,
            trust_status=TrustStatus.UNVERIFIED,
            checks=tuple(checks),
            error_code="head-proof-unverified",
            error_step="head",
            error=detail,
        )
    else:
        try:
            _validate_head_proof(head, head_proof)
        except FrameError as exc:
            checks.append(CheckResult("head", CheckStatus.FAIL, str(exc)))
            return replace(
                inspected,
                accepted=False,
                trust_status=TrustStatus.DRIFT,
                checks=tuple(checks),
                error_code=exc.code,
                error_step=exc.step,
                error=str(exc),
            )
    if head is not None:
        epoch_problem = _head_epoch_problem(head, registry)
        if epoch_problem is not None:
            status, code, detail = epoch_problem
            checks.append(
                CheckResult(
                    "head",
                    CheckStatus.FAIL
                    if status is TrustStatus.DRIFT
                    else CheckStatus.UNVERIFIED,
                    detail,
                )
            )
            return replace(
                inspected,
                accepted=False,
                trust_status=status,
                checks=tuple(checks),
                error_code=code,
                error_step="head",
                error=detail,
            )
    if stream.family == "swarm" and inspected.frame["sig"] is None:
        checks.append(
            CheckResult("6", CheckStatus.FAIL, "swarm frame signature is required")
        )
        return replace(inspected, trust_status=TrustStatus.DRIFT, checks=tuple(checks))
    if inspected.frame["sig"] is not None:
        checks.append(
            CheckResult(
                "6",
                CheckStatus.UNVERIFIED,
                "cryptographic JWS/registry verification is deliberately unsupported",
            )
        )
        return replace(
            inspected, trust_status=TrustStatus.UNVERIFIED, checks=tuple(checks)
        )
    checks.append(
        CheckResult(
            "6",
            CheckStatus.PASS,
            "signature is optional; acceptance makes no authorship claim",
        )
    )
    return replace(
        inspected,
        accepted=True,
        trust_status=TrustStatus.VERIFIED,
        checks=tuple(checks),
    )


@dataclass(frozen=True)
class AcceptedFrameSnapshot:
    stream_id: str
    seq: int
    utc: str
    payload_hash: str
    frame_hash: str
    genesis_hash: str
    signature_present: bool
    prev: str | None
    predecessor_known: bool
    frame_bytes: bytes | None

    def as_dict(self) -> dict[str, Any]:
        frame: dict[str, Any] | None = None
        if self.frame_bytes is not None:
            parsed = strict_loads(self.frame_bytes)
            if type(parsed) is not dict:
                raise FrameError(
                    "invalid-acceptor-snapshot",
                    "persisted full frame is not an object",
                )
            frame = parsed
        return {
            "stream_id": self.stream_id,
            "seq": self.seq,
            "utc": self.utc,
            "payload_hash": self.payload_hash,
            "frame_hash": self.frame_hash,
            "genesis_hash": self.genesis_hash,
            "signature_present": self.signature_present,
            "prev": self.prev,
            "predecessor_known": self.predecessor_known,
            "frame": frame,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "AcceptedFrameSnapshot":
        expected = {
            "stream_id",
            "seq",
            "utc",
            "payload_hash",
            "frame_hash",
            "genesis_hash",
            "signature_present",
            "prev",
            "predecessor_known",
            "frame",
        }
        if type(value) is not dict or set(value) != expected:
            raise FrameError(
                "invalid-acceptor-snapshot",
                "accepted frame snapshot has an invalid member set",
            )
        if value["frame"] is not None and type(value["frame"]) is not dict:
            raise FrameError(
                "invalid-acceptor-snapshot",
                "accepted frame snapshot full frame must be an object or null",
            )
        try:
            frame_bytes = (
                None
                if value["frame"] is None
                else canonical_bytes(value["frame"])
            )
        except CanonicalizationError as exc:
            raise FrameError(
                "invalid-acceptor-snapshot",
                "accepted frame snapshot full frame is invalid",
            ) from exc
        return cls(
            stream_id=value["stream_id"],
            seq=value["seq"],
            utc=value["utc"],
            payload_hash=value["payload_hash"],
            frame_hash=value["frame_hash"],
            genesis_hash=value["genesis_hash"],
            signature_present=value["signature_present"],
            prev=value["prev"],
            predecessor_known=value["predecessor_known"],
            frame_bytes=frame_bytes,
        )

    def as_head(self) -> HeadState:
        return HeadState(
            stream_id=self.stream_id,
            seq=self.seq,
            utc=self.utc,
            payload_hash=self.payload_hash,
            frame_hash=self.frame_hash,
            trusted=True,
            genesis_hash=self.genesis_hash,
            signature_present=self.signature_present,
        )


@dataclass(frozen=True)
class FrameAcceptorSnapshot:
    frames: tuple[AcceptedFrameSnapshot, ...]
    quarantined_streams: tuple[str, ...]
    frozen_streams: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "frames": [frame.as_dict() for frame in self.frames],
            "quarantined_streams": list(self.quarantined_streams),
            "frozen_streams": list(self.frozen_streams),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "FrameAcceptorSnapshot":
        if type(value) is not dict or set(value) != {
            "frames",
            "quarantined_streams",
            "frozen_streams",
        }:
            raise FrameError(
                "invalid-acceptor-snapshot",
                "acceptor snapshot has an invalid member set",
            )
        if type(value["frames"]) is not list or type(
            value["quarantined_streams"]
        ) is not list or type(value["frozen_streams"]) is not list:
            raise FrameError(
                "invalid-acceptor-snapshot", "acceptor snapshot members must be arrays"
            )
        snapshot = cls(
            frames=tuple(
                AcceptedFrameSnapshot.from_dict(frame)
                for frame in value["frames"]
            ),
            quarantined_streams=tuple(value["quarantined_streams"]),
            frozen_streams=tuple(value["frozen_streams"]),
        )
        _validate_acceptor_snapshot(snapshot)
        return snapshot


def _snapshot_frame_value(
    frame: AcceptedFrameSnapshot,
) -> dict[str, Any] | None:
    if frame.frame_bytes is None:
        return None
    if type(frame.frame_bytes) is not bytes:
        raise FrameError(
            "invalid-acceptor-snapshot",
            "persisted full frame must be immutable canonical bytes",
        )
    try:
        value = strict_loads(frame.frame_bytes)
        if type(value) is not dict or canonical_bytes(value) != frame.frame_bytes:
            raise FrameError(
                "invalid-acceptor-snapshot",
                "persisted full frame is not a canonical frame object",
            )
    except (CanonicalizationError, FrameError) as exc:
        if isinstance(exc, FrameError):
            raise
        raise FrameError(
            "invalid-acceptor-snapshot",
            "persisted full frame is invalid",
        ) from exc
    return value


def _validate_acceptor_snapshot(snapshot: FrameAcceptorSnapshot) -> None:
    if not isinstance(snapshot, FrameAcceptorSnapshot):
        raise TypeError("snapshot must be FrameAcceptorSnapshot")
    seen: set[tuple[str, int]] = set()
    by_stream: dict[str, dict[int, AcceptedFrameSnapshot]] = {}
    for frame in snapshot.frames:
        if not isinstance(frame, AcceptedFrameSnapshot):
            raise FrameError(
                "invalid-acceptor-snapshot", "snapshot frame has an invalid type"
            )
        try:
            _validate_head_state(frame.as_head())
            _validate_hash(frame.prev, field="snapshot.prev", nullable=True)
        except FrameError as exc:
            raise FrameError(
                "invalid-acceptor-snapshot", "snapshot frame fields are invalid"
            ) from exc
        if type(frame.predecessor_known) is not bool:
            raise FrameError(
                "invalid-acceptor-snapshot",
                "predecessor_known must be a boolean",
            )
        if type(frame.signature_present) is not bool or frame.genesis_hash is None:
            raise FrameError(
                "invalid-acceptor-snapshot",
                "snapshot requires genesis and signature-presence proof",
            )
        full_frame = _snapshot_frame_value(frame)
        if full_frame is not None:
            expected_metadata = (
                full_frame.get("stream_id"),
                full_frame.get("seq"),
                full_frame.get("utc"),
                full_frame.get("payload_hash"),
                full_frame.get("frame_hash"),
                full_frame.get("sig") is not None,
                full_frame.get("prev"),
            )
            persisted_metadata = (
                frame.stream_id,
                frame.seq,
                frame.utc,
                frame.payload_hash,
                frame.frame_hash,
                frame.signature_present,
                frame.prev,
            )
            if expected_metadata != persisted_metadata:
                raise FrameError(
                    "invalid-acceptor-snapshot",
                    "persisted full frame conflicts with snapshot metadata",
                )
            if not frame.predecessor_known:
                raise FrameError(
                    "invalid-acceptor-snapshot",
                    "persisted full frame must retain predecessor evidence",
                )
        key = (frame.stream_id, frame.seq)
        if key in seen:
            raise FrameError(
                "invalid-acceptor-snapshot", "snapshot contains duplicate stream/seq"
            )
        seen.add(key)
        by_stream.setdefault(frame.stream_id, {})[frame.seq] = frame
        if frame.predecessor_known and (
            (frame.seq == 0 and frame.prev is not None)
            or (frame.seq > 0 and frame.prev is None)
        ):
            raise FrameError(
                "invalid-acceptor-snapshot",
                "known predecessor shape conflicts with frame seq",
            )

    expected_frames = tuple(
        sorted(
            snapshot.frames,
            key=lambda frame: (frame.stream_id.encode("utf-8"), frame.seq),
        )
    )
    if snapshot.frames != expected_frames:
        raise FrameError(
            "invalid-acceptor-snapshot", "snapshot frames are not deterministically sorted"
        )
    for stream_frames in by_stream.values():
        if len({frame.genesis_hash for frame in stream_frames.values()}) != 1:
            raise FrameError(
                "invalid-acceptor-snapshot",
                "snapshot stream spans more than one genesis epoch",
            )
        full_count = sum(
            frame.frame_bytes is not None for frame in stream_frames.values()
        )
        if full_count == len(stream_frames):
            sequences = sorted(stream_frames)
            if sequences != list(range(sequences[-1] + 1)):
                raise FrameError(
                    "invalid-acceptor-snapshot",
                    "persisted full history must descend contiguously from seq 0",
                )
            root = stream_frames[0]
            if root.frame_hash != root.genesis_hash:
                raise FrameError(
                    "invalid-acceptor-snapshot",
                    "persisted seq-0 frame does not equal the claimed genesis",
                )
            predecessor: AcceptedFrameSnapshot | None = None
            for seq in sequences:
                persisted = stream_frames[seq]
                value = _snapshot_frame_value(persisted)
                assert value is not None
                inspected = inspect_frame(
                    value,
                    declared_stream_id=persisted.stream_id,
                    head=None if predecessor is None else predecessor.as_head(),
                )
                if not inspected.structurally_valid:
                    raise FrameError(
                        "invalid-acceptor-snapshot",
                        "persisted full history fails structural verification",
                    )
                predecessor = persisted
        for seq, frame in stream_frames.items():
            if not frame.predecessor_known or seq == 0:
                continue
            predecessor = stream_frames.get(seq - 1)
            if (
                predecessor is None
                or frame.prev != predecessor.payload_hash
                or frame.utc < predecessor.utc
            ):
                raise FrameError(
                    "invalid-acceptor-snapshot",
                    "snapshot history is not a contiguous non-regressing chain",
                )

    for label, stream_ids in (
        ("quarantined", snapshot.quarantined_streams),
        ("frozen", snapshot.frozen_streams),
    ):
        if any(type(stream_id) is not str for stream_id in stream_ids):
            raise FrameError(
                "invalid-acceptor-snapshot",
                f"{label} stream ids must be strings",
            )
        expected = tuple(
            sorted(set(stream_ids), key=lambda value: value.encode("utf-8"))
        )
        if stream_ids != expected:
            raise FrameError(
                "invalid-acceptor-snapshot",
                f"{label} stream ids must be unique and sorted",
            )
        for stream_id in stream_ids:
            try:
                parse_stream_id(stream_id)
            except IdentityError as exc:
                raise FrameError(
                    "invalid-acceptor-snapshot",
                    f"{label} stream id is invalid",
                ) from exc
            if stream_id not in by_stream:
                raise FrameError(
                    "invalid-acceptor-snapshot",
                    f"{label} stream has no persisted accepted head",
                )


def _validate_snapshot_roots(
    snapshot: FrameAcceptorSnapshot, registry: RegistryEvidence
) -> None:
    if not registry.authenticated:
        raise FrameError(
            "snapshot-registry-unverified",
            "snapshot restoration requires an authenticated registry",
        )
    if not registry.fresh:
        raise FrameError(
            "snapshot-registry-stale",
            "snapshot restoration requires a fresh registry",
        )
    by_stream: dict[str, list[AcceptedFrameSnapshot]] = {}
    for frame in snapshot.frames:
        by_stream.setdefault(frame.stream_id, []).append(frame)
    for stream_id, stream_frames in by_stream.items():
        if any(frame.frame_bytes is None for frame in stream_frames):
            raise FrameError(
                "snapshot-root-unverified",
                "rootless snapshot history requires separate caller authentication",
            )
        root = stream_frames[0]
        current_genesis = registry.genesis_hashes.get(stream_id)
        if (
            root.seq != 0
            or root.frame_hash != root.genesis_hash
            or root.frame_hash != current_genesis
        ):
            raise FrameError(
                "snapshot-genesis-mismatch",
                "snapshot root is not the current authenticated registry genesis",
            )
        predecessor: AcceptedFrameSnapshot | None = None
        for persisted in stream_frames:
            value = _snapshot_frame_value(persisted)
            assert value is not None
            inspected = inspect_frame(
                value,
                declared_stream_id=stream_id,
                head=None if predecessor is None else predecessor.as_head(),
                registry=registry,
            )
            if (
                not inspected.structurally_valid
                or any(
                    check.status is CheckStatus.UNVERIFIED
                    for check in inspected.checks
                )
            ):
                raise FrameError(
                    "snapshot-history-invalid",
                    "snapshot history does not verify under the current registry",
                )
            stream = parse_stream_id(stream_id)
            if (
                _is_regenesis(value)
                or stream.family == "swarm"
                or value["sig"] is not None
            ):
                raise FrameError(
                    "snapshot-acceptance-unverified",
                    "snapshot contains a frame this core cannot authenticate",
                )
            predecessor = persisted


class FrameAcceptor:
    """Thread-safe no-rollback acceptor with persistent fork quarantine."""

    def __init__(
        self,
        registry: RegistryEvidence,
        *,
        snapshot: FrameAcceptorSnapshot | None = None,
    ) -> None:
        self._lock = RLock()
        self._registry = _registry_snapshot(registry)
        self._heads: dict[str, HeadState] = {}
        self._history: dict[str, dict[int, AcceptedFrameSnapshot]] = {}
        self._quarantined: set[str] = set()
        self._frozen_streams: set[str] = set()
        if snapshot is not None:
            self._restore(snapshot)

    def head(self, stream_id: str) -> HeadState | None:
        with self._lock:
            return self._heads.get(stream_id)

    def is_quarantined(self, stream_id: str) -> bool:
        with self._lock:
            return stream_id in self._quarantined

    def is_epoch_frozen(self, stream_id: str) -> bool:
        with self._lock:
            return stream_id in self._frozen_streams

    def update_registry(self, registry: RegistryEvidence) -> None:
        with self._lock:
            replacement = _registry_snapshot(registry)
            self._registry = replacement
            if replacement.authenticated and replacement.fresh:
                for stream_id, head in self._heads.items():
                    if (
                        replacement.genesis_hashes.get(stream_id)
                        != head.genesis_hash
                    ):
                        self._frozen_streams.add(stream_id)

    def snapshot(self) -> FrameAcceptorSnapshot:
        with self._lock:
            return self._snapshot_locked()

    def _snapshot_locked(self) -> FrameAcceptorSnapshot:
        frames = tuple(
            sorted(
                (
                    frame
                    for stream_history in self._history.values()
                    for frame in stream_history.values()
                ),
                key=lambda frame: (frame.stream_id.encode("utf-8"), frame.seq),
            )
        )
        quarantined = tuple(
            sorted(self._quarantined, key=lambda value: value.encode("utf-8"))
        )
        frozen = tuple(
            sorted(self._frozen_streams, key=lambda value: value.encode("utf-8"))
        )
        snapshot = FrameAcceptorSnapshot(
            frames=frames,
            quarantined_streams=quarantined,
            frozen_streams=frozen,
        )
        _validate_acceptor_snapshot(snapshot)
        return snapshot

    def _restore(self, snapshot: FrameAcceptorSnapshot) -> None:
        with self._lock:
            _validate_acceptor_snapshot(snapshot)
            _validate_snapshot_roots(snapshot, self._registry)
            for frame in snapshot.frames:
                self._history.setdefault(frame.stream_id, {})[frame.seq] = frame
                current = self._heads.get(frame.stream_id)
                if current is None or frame.seq > current.seq:
                    self._heads[frame.stream_id] = frame.as_head()
            self._quarantined.update(snapshot.quarantined_streams)
            self._frozen_streams.update(snapshot.frozen_streams)

    @staticmethod
    def _state_failure(
        inspected: FrameInspection, *, code: str, detail: str
    ) -> FrameInspection:
        checks = inspected.checks + (
            CheckResult("head", CheckStatus.FAIL, detail),
        )
        return replace(
            inspected,
            accepted=False,
            trust_status=TrustStatus.DRIFT,
            checks=checks,
            error_code=code,
            error_step="head",
            error=detail,
        )

    @staticmethod
    def _epoch_failure(
        inspected: FrameInspection,
        problem: tuple[TrustStatus, str, str],
    ) -> FrameInspection:
        status, code, detail = problem
        checks = inspected.checks + (
            CheckResult(
                "head",
                CheckStatus.FAIL
                if status is TrustStatus.DRIFT
                else CheckStatus.UNVERIFIED,
                detail,
            ),
        )
        return replace(
            inspected,
            accepted=False,
            trust_status=status,
            checks=checks,
            error_code=code,
            error_step="head",
            error=detail,
        )

    def _record(self, frame: dict[str, Any], *, genesis_hash: str) -> None:
        _validate_hash(genesis_hash, field="validated genesis_hash")
        head = HeadState(
            stream_id=frame["stream_id"],
            seq=frame["seq"],
            utc=frame["utc"],
            payload_hash=frame["payload_hash"],
            frame_hash=frame["frame_hash"],
            trusted=True,
            genesis_hash=genesis_hash,
            signature_present=frame["sig"] is not None,
        )
        self._heads[frame["stream_id"]] = head
        stream_history = self._history.setdefault(frame["stream_id"], {})
        retain_full_frame = frame["seq"] == 0 or (
            0 in stream_history
            and all(
                persisted.frame_bytes is not None
                for persisted in stream_history.values()
            )
        )
        stream_history[frame["seq"]] = (
            AcceptedFrameSnapshot(
                stream_id=head.stream_id,
                seq=head.seq,
                utc=head.utc,
                payload_hash=head.payload_hash,
                frame_hash=head.frame_hash,
                genesis_hash=head.genesis_hash,
                signature_present=head.signature_present,
                prev=frame["prev"],
                predecessor_known=True,
                frame_bytes=canonical_bytes(frame) if retain_full_frame else None,
            )
        )

    def seed_trusted_head(
        self,
        head: HeadState,
        *,
        proof: AuthenticatedHeadProof | None = None,
    ) -> None:
        with self._lock:
            self._seed_trusted_head_locked(head, proof=proof)

    def _seed_trusted_head_locked(
        self,
        head: HeadState,
        *,
        proof: AuthenticatedHeadProof | None,
    ) -> None:
        _validate_head_state(head)
        if not head.trusted:
            raise FrameError(
                "untrusted-head", "only an externally trusted head can seed state"
            )
        registry = self._registry
        current = self._heads.get(head.stream_id)
        if head.stream_id in self._frozen_streams:
            raise FrameError(
                "retired-genesis-epoch",
                "stream is frozen after an authenticated registry epoch change",
            )
        if current == head:
            epoch_problem = _head_epoch_problem(head, registry)
            if epoch_problem is not None:
                _, code, detail = epoch_problem
                raise FrameError(code, detail)
            return
        if proof is None:
            raise FrameError(
                "head-proof-unverified",
                "rootless seed requires an explicit AuthenticatedHeadProof",
            )
        _validate_head_proof(head, proof)
        epoch_problem = _head_epoch_problem(head, registry)
        if epoch_problem is not None:
            _, code, detail = epoch_problem
            raise FrameError(code, detail)
        if type(head.signature_present) is not bool:
            raise FrameError(
                "head-signature-proof-missing",
                "seed head requires signature-presence proof",
            )
        if head.stream_id in self._quarantined:
            raise FrameError(
                "stream-quarantined",
                "fork quarantine can end only through verified re-genesis",
            )
        if current is not None and (
            head.seq < current.seq
            or (head.seq == current.seq and head.frame_hash != current.frame_hash)
        ):
            raise FrameError(
                "head-rollback", "seed head would roll back or reorganize state"
            )
        if (
            current is not None
            and head.seq == current.seq
            and head.frame_hash == current.frame_hash
        ):
            raise FrameError(
                "head-state-mismatch",
                "same frame hash cannot replace differing persisted head metadata",
            )
        self._heads[head.stream_id] = head
        self._history.setdefault(head.stream_id, {})[head.seq] = (
            AcceptedFrameSnapshot(
                stream_id=head.stream_id,
                seq=head.seq,
                utc=head.utc,
                payload_hash=head.payload_hash,
                frame_hash=head.frame_hash,
                genesis_hash=head.genesis_hash,
                signature_present=head.signature_present,
                prev=None,
                predecessor_known=False,
                frame_bytes=None,
            )
        )

    def _replay_current(
        self,
        frame: dict[str, Any],
        current: HeadState,
        standalone: FrameInspection,
        registry: RegistryEvidence,
    ) -> FrameInspection:
        if not registry.authenticated:
            return replace(standalone, trust_status=TrustStatus.UNVERIFIED)
        if not registry.fresh:
            return replace(standalone, trust_status=TrustStatus.STALE)
        if any(
            check.status is CheckStatus.UNVERIFIED and check.step not in {"4", "5"}
            for check in standalone.checks
        ):
            return replace(standalone, trust_status=TrustStatus.UNVERIFIED)
        checks = list(
            CheckResult(
                check.step,
                CheckStatus.PASS,
                "frame matches the persisted accepted head",
            )
            if check.step in {"4", "5"}
            and check.status is CheckStatus.UNVERIFIED
            else check
            for check in standalone.checks
        )
        checks.append(
            CheckResult(
                "head",
                CheckStatus.PASS,
                "frame hash matches the persisted accepted head",
            )
        )
        if current.signature_present is None:
            checks.append(
                CheckResult(
                    "6",
                    CheckStatus.UNVERIFIED,
                    "persisted head lacks signature-presence proof",
                )
            )
            return replace(
                standalone,
                accepted=False,
                trust_status=TrustStatus.UNVERIFIED,
                checks=tuple(checks),
                error_code="replay-signature-unverified",
                error_step="6",
                error="persisted head lacks signature-presence proof",
            )
        presented_signature = frame["sig"] is not None
        if current.signature_present and not presented_signature:
            checks.append(
                CheckResult(
                    "6",
                    CheckStatus.FAIL,
                    "replay stripped the persisted head signature",
                )
            )
            return replace(
                standalone,
                accepted=False,
                trust_status=TrustStatus.DRIFT,
                checks=tuple(checks),
                error_code="replay-signature-mismatch",
                error_step="6",
                error="replay stripped the persisted head signature",
            )
        if presented_signature:
            checks.append(
                CheckResult(
                    "6",
                    CheckStatus.UNVERIFIED,
                    "cryptographic JWS/registry verification is deliberately unsupported",
                )
            )
            return replace(
                standalone,
                accepted=False,
                trust_status=TrustStatus.UNVERIFIED,
                checks=tuple(checks),
                error_code="replay-signature-unverified",
                error_step="6",
                error="cryptographic signature verification is unsupported",
            )
        stream = parse_stream_id(frame["stream_id"])
        if stream.family == "swarm":
            checks.append(
                CheckResult(
                    "6", CheckStatus.FAIL, "swarm frame signature is required"
                )
            )
            return replace(
                standalone,
                accepted=False,
                trust_status=TrustStatus.DRIFT,
                checks=tuple(checks),
                error_code="unsigned-swarm-replay",
                error_step="6",
                error="swarm frame signature is required",
            )
        checks.append(
            CheckResult(
                "6",
                CheckStatus.PASS,
                "signature is optional; acceptance makes no authorship claim",
            )
        )
        return replace(
            standalone,
            accepted=True,
            trust_status=TrustStatus.VERIFIED,
            checks=tuple(checks),
        )

    def _verify_historical_competitor(
        self,
        frame: dict[str, Any],
        *,
        declared_stream_id: str,
        predecessor: HeadState | None,
        registry: RegistryEvidence,
    ) -> FrameInspection:
        inspected = inspect_frame(
            frame,
            declared_stream_id=declared_stream_id,
            head=predecessor,
            registry=registry,
        )
        if not inspected.structurally_valid:
            return inspected
        checks = list(inspected.checks)
        if not registry.authenticated:
            checks.append(
                CheckResult("6", CheckStatus.UNVERIFIED, "registry is unauthenticated")
            )
            return replace(
                inspected,
                trust_status=TrustStatus.UNVERIFIED,
                checks=tuple(checks),
            )
        if not registry.fresh:
            checks.append(
                CheckResult("6", CheckStatus.UNVERIFIED, "registry is stale")
            )
            return replace(
                inspected, trust_status=TrustStatus.STALE, checks=tuple(checks)
            )
        if any(check.status is CheckStatus.UNVERIFIED for check in inspected.checks):
            checks.append(
                CheckResult(
                    "6",
                    CheckStatus.UNVERIFIED,
                    "historical predecessor context is incomplete",
                )
            )
            return replace(
                inspected,
                trust_status=TrustStatus.UNVERIFIED,
                checks=tuple(checks),
            )
        if (
            frame["seq"] == 0
            and registry.genesis_hashes.get(frame["stream_id"])
            != frame["frame_hash"]
        ):
            detail = (
                "historical genesis is not the current authenticated "
                "registry genesis"
            )
            checks.append(CheckResult("head", CheckStatus.FAIL, detail))
            return replace(
                inspected,
                accepted=False,
                trust_status=TrustStatus.DRIFT,
                checks=tuple(checks),
                error_code="unregistered-genesis",
                error_step="head",
                error=detail,
            )
        if predecessor is not None:
            epoch_problem = _head_epoch_problem(predecessor, registry)
            if epoch_problem is not None:
                return self._epoch_failure(inspected, epoch_problem)
        stream = parse_stream_id(frame["stream_id"])
        if stream.family == "swarm" and frame["sig"] is None:
            checks.append(
                CheckResult(
                    "6", CheckStatus.FAIL, "swarm frame signature is required"
                )
            )
            return replace(
                inspected,
                trust_status=TrustStatus.DRIFT,
                checks=tuple(checks),
                error_code="unsigned-swarm-fork",
                error_step="6",
                error="swarm frame signature is required",
            )
        if frame["sig"] is not None:
            checks.append(
                CheckResult(
                    "6",
                    CheckStatus.UNVERIFIED,
                    "cryptographic JWS/registry verification is deliberately unsupported",
                )
            )
            return replace(
                inspected,
                trust_status=TrustStatus.UNVERIFIED,
                checks=tuple(checks),
            )
        checks.append(
            CheckResult(
                "6",
                CheckStatus.PASS,
                "historical unsigned frame passes without an authorship claim",
            )
        )
        return replace(
            inspected,
            accepted=True,
            trust_status=TrustStatus.VERIFIED,
            checks=tuple(checks),
        )

    def accept(
        self, frame: dict[str, Any], *, declared_stream_id: str
    ) -> FrameInspection:
        with self._lock:
            return self._accept_locked(
                frame, declared_stream_id=declared_stream_id
            )

    def _accept_locked(
        self, frame: dict[str, Any], *, declared_stream_id: str
    ) -> FrameInspection:
        registry = self._registry
        validated_genesis = registry.genesis_hashes.get(declared_stream_id)
        current = self._heads.get(declared_stream_id)
        if _is_regenesis(frame):
            return accept_frame(
                frame,
                declared_stream_id=declared_stream_id,
                head=current,
                head_proof=None if current is None else _head_proof(current),
                registry=registry,
            )

        if declared_stream_id in self._frozen_streams:
            standalone = inspect_frame(
                frame,
                declared_stream_id=declared_stream_id,
                registry=registry,
            )
            if not standalone.structurally_valid:
                return standalone
            return self._state_failure(
                standalone,
                code="retired-genesis-epoch",
                detail=(
                    "stream is frozen after an authenticated registry epoch change"
                ),
            )

        if current is not None:
            epoch_problem = _head_epoch_problem(current, registry)
            if epoch_problem is not None:
                standalone = inspect_frame(
                    frame,
                    declared_stream_id=declared_stream_id,
                    registry=registry,
                )
                if not standalone.structurally_valid:
                    return standalone
                return self._epoch_failure(standalone, epoch_problem)

        if declared_stream_id in self._quarantined:
            standalone = inspect_frame(
                frame,
                declared_stream_id=declared_stream_id,
                registry=registry,
            )
            if not standalone.structurally_valid:
                return standalone
            return self._state_failure(
                standalone,
                code="stream-quarantined",
                detail=(
                    "stream is fork-quarantined until authenticated verified re-genesis"
                ),
            )

        if (
            current is not None
            and type(frame.get("seq")) is int
            and frame["seq"] <= current.seq
        ):
            standalone = inspect_frame(
                frame,
                declared_stream_id=declared_stream_id,
                registry=registry,
            )
            if not standalone.structurally_valid:
                return standalone
            if (
                frame["seq"] == current.seq
                and frame["frame_hash"] == current.frame_hash
            ):
                return self._replay_current(
                    frame, current, standalone, registry
                )

            history = self._history.get(declared_stream_id, {})
            accepted_at_seq = history.get(frame["seq"])
            predecessor = (
                history.get(frame["seq"] - 1) if frame["seq"] > 0 else None
            )
            if (
                accepted_at_seq is not None
                and accepted_at_seq.predecessor_known
                and (frame["seq"] == 0 or predecessor is not None)
            ):
                competing = self._verify_historical_competitor(
                    frame,
                    declared_stream_id=declared_stream_id,
                    predecessor=None
                    if predecessor is None
                    else predecessor.as_head(),
                    registry=registry,
                )
                if (
                    competing.accepted
                    and frame["prev"] == accepted_at_seq.prev
                    and frame["frame_hash"] != accepted_at_seq.frame_hash
                ):
                    self._quarantined.add(declared_stream_id)
                    return self._state_failure(
                        competing,
                        code="fork-quarantined",
                        detail=(
                            "competing same-seq/predecessor frame forked the stream"
                        ),
                    )
                if not competing.accepted:
                    return competing

            return self._state_failure(
                standalone,
                code="head-rollback",
                detail="presented frame would roll back or reorganize accepted state",
            )

        inspected = accept_frame(
            frame,
            declared_stream_id=declared_stream_id,
            head=current,
            head_proof=None if current is None else _head_proof(current),
            registry=registry,
        )
        if inspected.accepted:
            if validated_genesis is None:
                raise FrameError(
                    "head-epoch-unverified",
                    "accepted frame lacks validated registry genesis",
                )
            self._record(frame, genesis_hash=validated_genesis)
        return inspected


def build_frame(
    *,
    kind: str,
    stream_id: str,
    seq: int,
    utc: str,
    payload: dict[str, Any],
    prev: str | None,
    prev_wave: str | None,
    sig: str | None = None,
) -> dict[str, Any]:
    """Build an eleven-key frame and compute particle then wave addresses."""

    _require_nfc_payload_keys(payload)
    frame: dict[str, Any] = {
        "spec": "rapp/1",
        "kind": kind,
        "stream_id": stream_id,
        "seq": seq,
        "utc": utc,
        "payload": payload,
        "payload_hash": hash_value(PARTICLE_SPACE, payload),
        "frame_hash": "0" * 64,
        "prev": prev,
        "prev_wave": prev_wave,
        "sig": sig,
    }
    wave_preimage = {
        key: value
        for key, value in frame.items()
        if key not in {"frame_hash", "sig"}
    }
    frame["frame_hash"] = hash_value(WAVE_SPACE, wave_preimage)
    inspected = inspect_frame(frame, declared_stream_id=stream_id)
    if not inspected.structurally_valid:
        raise FrameError(
            inspected.error_code or "invalid-frame",
            inspected.error or "constructed frame is invalid",
            step=inspected.error_step,
        )
    return frame
