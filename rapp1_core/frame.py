"""RAPP/1 frame construction, structural inspection, and trust-gated acceptance."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

from .canonical import CanonicalizationError, canonical_bytes, strict_loads
from .errors import FrameError, IdentityError, SignatureStructureError
from .hashing import PARTICLE_SPACE, WAVE_SPACE, hash_value
from .identity import LOWER_HASH_RE, parse_stream_id, validate_kind
from .jws import parse_detached_jws
from .trust import (
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

    if registry is None or not registry.authenticated:
        return (
            stream.family,
            CheckStatus.UNVERIFIED,
            "shape and local grammar pass; kind registry is not authenticated",
        )
    registered_family = registry.kind_families.get(frame["kind"])
    if registered_family is None:
        if registry.fresh:
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
    if frame["kind"] in registry.deprecated_kinds:
        raise FrameError("deprecated-kind", "registered kind is deprecated", step="1")
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
    except FrameError as exc:
        raise FrameError("invalid-head", "head has an invalid hash", step="4") from exc


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
            if head is not None:
                raise FrameError(
                    "unexpected-genesis", "genesis cannot extend an existing head", step="4"
                )
            checks.append(CheckResult("4", CheckStatus.PASS, "genesis chain is valid"))
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
    elif head is None or not head.trusted:
        checks.append(
            CheckResult(
                "head",
                CheckStatus.UNVERIFIED,
                "predecessor head is not externally trusted",
            )
        )
        return replace(
            inspected, trust_status=TrustStatus.UNVERIFIED, checks=tuple(checks)
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


class FrameAcceptor:
    """Stateful no-rollback acceptor for externally authenticated registry evidence."""

    def __init__(self, registry: RegistryEvidence) -> None:
        self._registry = registry
        self._heads: dict[str, HeadState] = {}

    def head(self, stream_id: str) -> HeadState | None:
        return self._heads.get(stream_id)

    def seed_trusted_head(self, head: HeadState) -> None:
        _validate_head_state(head)
        if not head.trusted:
            raise FrameError(
                "untrusted-head", "only an externally trusted head can seed state"
            )
        current = self._heads.get(head.stream_id)
        if current is not None and (
            head.seq < current.seq
            or (head.seq == current.seq and head.frame_hash != current.frame_hash)
        ):
            raise FrameError(
                "head-rollback", "seed head would roll back or reorganize state"
            )
        self._heads[head.stream_id] = head

    def accept(
        self, frame: dict[str, Any], *, declared_stream_id: str
    ) -> FrameInspection:
        current = self._heads.get(declared_stream_id)
        if (
            current is not None
            and type(frame.get("seq")) is int
            and frame["seq"] <= current.seq
        ):
            standalone = inspect_frame(
                frame,
                declared_stream_id=declared_stream_id,
                registry=self._registry,
            )
            if not standalone.structurally_valid:
                return standalone
            if (
                frame["seq"] == current.seq
                and frame["frame_hash"] == current.frame_hash
                and frame["sig"] is None
            ):
                if not self._registry.authenticated:
                    return replace(
                        standalone, trust_status=TrustStatus.UNVERIFIED
                    )
                if not self._registry.fresh:
                    return replace(standalone, trust_status=TrustStatus.STALE)
                if any(
                    check.status is CheckStatus.UNVERIFIED
                    and check.step not in {"4", "5"}
                    for check in standalone.checks
                ):
                    return replace(
                        standalone, trust_status=TrustStatus.UNVERIFIED
                    )
                checks = tuple(
                    CheckResult(
                        check.step,
                        CheckStatus.PASS,
                        "frame matches the persisted accepted head",
                    )
                    if check.step in {"4", "5"}
                    and check.status is CheckStatus.UNVERIFIED
                    else check
                    for check in standalone.checks
                ) + (
                    CheckResult(
                        "head",
                        CheckStatus.PASS,
                        "frame hash matches the persisted accepted head",
                    ),
                    CheckResult(
                        "6",
                        CheckStatus.PASS,
                        "signature is optional; acceptance makes no authorship claim",
                    ),
                )
                return replace(
                    standalone,
                    accepted=True,
                    trust_status=TrustStatus.VERIFIED,
                    checks=checks,
                )
            checks = standalone.checks + (
                CheckResult(
                    "head",
                    CheckStatus.FAIL,
                    "presented frame would roll back or reorganize accepted state",
                ),
            )
            return replace(
                standalone,
                accepted=False,
                trust_status=TrustStatus.DRIFT,
                checks=checks,
                error_code="head-rollback",
                error_step="head",
                error="presented frame would roll back or reorganize accepted state",
            )
        inspected = accept_frame(
            frame,
            declared_stream_id=declared_stream_id,
            head=current,
            registry=self._registry,
        )
        if inspected.accepted:
            self._heads[declared_stream_id] = HeadState(
                stream_id=frame["stream_id"],
                seq=frame["seq"],
                utc=frame["utc"],
                payload_hash=frame["payload_hash"],
                frame_hash=frame["frame_hash"],
                trusted=True,
            )
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
