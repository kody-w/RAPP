from __future__ import annotations

import base64

import pytest

from rapp1_core.canonical import canonical_bytes
from rapp1_core.frame import (
    FRAME_KEYS,
    FrameAcceptor,
    FrameError,
    accept_frame,
    build_frame,
    inspect_frame,
    inspect_frame_bytes,
    validate_utc,
)
from rapp1_core.jws import SignatureStructureError, parse_detached_jws
from rapp1_core.trust import HeadState, RegistryEvidence, TrustStatus

RID1 = "rappid:@kody-w/one:" + "1" * 64
RID2 = "rappid:@kody-w/two:" + "2" * 64
UTC0 = "2026-07-16T22:41:23.842Z"
UTC1 = "2026-07-16T22:41:24.000Z"


def _jws(kid: str = RID1, *, extra: bool = False, canonical: bool = True) -> str:
    header = {"alg": "EdDSA", "b64": False, "crit": ["b64"], "kid": kid}
    if extra:
        header["typ"] = "JWS"
    header_bytes = canonical_bytes(header)
    if not canonical:
        header_bytes = b'{"kid":"' + kid.encode() + b'","crit":["b64"],"b64":false,"alg":"EdDSA"}'
    protected = base64.urlsafe_b64encode(header_bytes).rstrip(b"=").decode()
    signature = base64.urlsafe_b64encode(b"\x01" * 64).rstrip(b"=").decode()
    return f"{protected}..{signature}"


def _body_genesis() -> dict:
    return build_frame(
        kind="body.pulse",
        stream_id=RID1,
        seq=0,
        utc=UTC0,
        payload={},
        prev=None,
        prev_wave=None,
    )


def _registry(frame: dict, *, fresh: bool = True) -> RegistryEvidence:
    return RegistryEvidence(
        kind_families={
            "body.pulse": "body",
            "memory.chat-turn": "memory",
            "swarm.echo": "swarm",
        },
        genesis_hashes={frame["stream_id"]: frame["frame_hash"]},
        authenticated=True,
        fresh=fresh,
    )


def _head(frame: dict, *, trusted: bool) -> HeadState:
    return HeadState(
        stream_id=frame["stream_id"],
        seq=frame["seq"],
        utc=frame["utc"],
        payload_hash=frame["payload_hash"],
        frame_hash=frame["frame_hash"],
        trusted=trusted,
    )


def test_frame_normative_hash_vector_and_exact_shape() -> None:
    frame = _body_genesis()
    assert set(frame) == FRAME_KEYS
    assert frame["payload_hash"] == (
        "00d4ee8c3964f0e289ba07982ab8457a7b820056236640bda09572f0725a265b"
    )
    assert frame["frame_hash"] == (
        "dffbb8971581d03913fbb7ca7292678931bee9b99954298bc39eca31d5088578"
    )
    report = inspect_frame(
        frame, declared_stream_id=RID1, registry=_registry(frame)
    )
    assert report.structurally_valid
    assert [check.step for check in report.checks] == ["1", "1a", "2", "3", "4", "5"]
    assert not report.accepted


@pytest.mark.parametrize(
    "utc",
    [
        "2026-13-01T00:00:00.000Z",
        "2026-02-30T00:00:00.000Z",
        "2026-01-01T24:00:00.000Z",
        "2026-01-01T00:00:60.000Z",
        "2026-01-01t00:00:00.000Z",
        "2026-01-01T00:00:00Z",
        "2026-01-01T00:00:00.000+00:00",
    ],
)
def test_invalid_fixed_dates(utc: str) -> None:
    with pytest.raises(FrameError):
        validate_utc(utc)


def test_exact_keys_missing_and_extra_are_refused_first() -> None:
    frame = _body_genesis()
    missing = dict(frame)
    missing.pop("sig")
    extra = dict(frame, extension=None)
    for invalid in (missing, extra):
        report = inspect_frame(invalid, declared_stream_id=RID1)
        assert not report.structurally_valid
        assert report.error_step == "1"


def test_duplicate_frame_key_and_exponent_seq_are_refused() -> None:
    frame = _body_genesis()
    raw = canonical_bytes(frame)
    duplicate = raw[:-1] + b',"spec":"rapp/1"}'
    assert not inspect_frame_bytes(duplicate).structurally_valid
    exponent = raw.replace(b'"seq":0', b'"seq":0e0')
    report = inspect_frame_bytes(exponent)
    assert not report.structurally_valid
    assert report.error_code == "invalid-seq"


def test_particle_then_wave_fail_in_order() -> None:
    frame = _body_genesis()
    frame["payload"]["tampered"] = True
    report = inspect_frame(frame, declared_stream_id=RID1)
    assert not report.structurally_valid
    assert report.error_step == "2"
    assert [check.step for check in report.checks] == ["1", "1a", "2"]

    frame = _body_genesis()
    frame["utc"] = UTC1
    report = inspect_frame(frame, declared_stream_id=RID1)
    assert not report.structurally_valid
    assert report.error_step == "3"


def test_stream_binding_and_cross_stream_chain_are_refused() -> None:
    genesis = _body_genesis()
    assert (
        inspect_frame(genesis, declared_stream_id=RID2).error_code
        == "stream-binding-mismatch"
    )
    other = build_frame(
        kind="body.pulse",
        stream_id=RID2,
        seq=1,
        utc=UTC1,
        payload={"next": True},
        prev=genesis["payload_hash"],
        prev_wave=None,
    )
    report = inspect_frame(
        other, declared_stream_id=RID2, head=_head(genesis, trusted=True)
    )
    assert not report.structurally_valid
    assert report.error_code == "cross-stream-chain"


def test_contiguous_chain_time_and_memory_wire_rules() -> None:
    genesis = _body_genesis()
    successor = build_frame(
        kind="body.pulse",
        stream_id=RID1,
        seq=1,
        utc=UTC1,
        payload={"next": True},
        prev=genesis["payload_hash"],
        prev_wave=None,
    )
    report = inspect_frame(
        successor,
        declared_stream_id=RID1,
        head=_head(genesis, trusted=False),
        registry=_registry(genesis),
    )
    assert report.structurally_valid
    assert report.checks[4].status.value == "PASS"

    bad_prev_wave = dict(successor, prev_wave=genesis["frame_hash"])
    report = inspect_frame(
        bad_prev_wave, declared_stream_id=RID1, head=_head(genesis, trusted=False)
    )
    assert report.error_code in {"frame-hash-mismatch", "unexpected-prev-wave"}

    earlier = build_frame(
        kind="body.pulse",
        stream_id=RID1,
        seq=1,
        utc="2026-07-16T22:41:22.000Z",
        payload={},
        prev=genesis["payload_hash"],
        prev_wave=None,
    )
    assert (
        inspect_frame(
            earlier, declared_stream_id=RID1, head=_head(genesis, trusted=False)
        ).error_code
        == "time-regression"
    )


def test_swarm_wire_requires_matching_wave_link() -> None:
    genesis = build_frame(
        kind="swarm.echo",
        stream_id="net:planet",
        seq=0,
        utc=UTC0,
        payload={},
        prev=None,
        prev_wave=None,
        sig=_jws(),
    )
    successor = build_frame(
        kind="swarm.echo",
        stream_id="net:planet",
        seq=1,
        utc=UTC1,
        payload={"echo": 1},
        prev=genesis["payload_hash"],
        prev_wave=genesis["frame_hash"],
        sig=_jws(),
    )
    registry = RegistryEvidence(
        kind_families={"swarm.echo": "swarm"}, authenticated=True, fresh=True
    )
    assert inspect_frame(
        successor,
        declared_stream_id="net:planet",
        head=_head(genesis, trusted=False),
        registry=registry,
    ).structurally_valid
    wrong = build_frame(
        kind="swarm.echo",
        stream_id="net:planet",
        seq=1,
        utc=UTC1,
        payload={"echo": 1},
        prev=genesis["payload_hash"],
        prev_wave="f" * 64,
        sig=_jws(),
    )
    assert (
        inspect_frame(
            wrong,
            declared_stream_id="net:planet",
            head=_head(genesis, trusted=False),
            registry=registry,
        ).error_code
        == "wire-chain-mismatch"
    )


def test_authenticated_registry_enforces_kind_registration_and_family() -> None:
    frame = _body_genesis()
    unknown = RegistryEvidence(authenticated=True, fresh=True)
    assert inspect_frame(frame, declared_stream_id=RID1, registry=unknown).error_code == (
        "unregistered-kind"
    )
    mismatch = RegistryEvidence(
        kind_families={"body.pulse": "swarm"}, authenticated=True, fresh=True
    )
    assert inspect_frame(
        frame, declared_stream_id=RID1, registry=mismatch
    ).error_code == "kind-stream-mismatch"


def test_detached_unencoded_jws_exact_header() -> None:
    parsed = parse_detached_jws(_jws())
    assert parsed.alg == "EdDSA" and parsed.kid == RID1
    for invalid in (
        _jws(extra=True),
        _jws(canonical=False),
        _jws().replace("..", ".payload."),
        "not-base64..also-not-base64",
    ):
        with pytest.raises(SignatureStructureError):
            parse_detached_jws(invalid)


def test_no_success_without_registry_head_or_signature_verification() -> None:
    genesis = _body_genesis()
    no_registry = accept_frame(genesis, declared_stream_id=RID1)
    assert not no_registry.accepted
    assert no_registry.trust_status is TrustStatus.UNVERIFIED

    stale = accept_frame(
        genesis, declared_stream_id=RID1, registry=_registry(genesis, fresh=False)
    )
    assert not stale.accepted and stale.trust_status is TrustStatus.STALE

    trusted = accept_frame(
        genesis, declared_stream_id=RID1, registry=_registry(genesis)
    )
    assert trusted.accepted and trusted.trust_status is TrustStatus.VERIFIED

    signed = dict(genesis, sig=_jws())
    signed_report = accept_frame(
        signed, declared_stream_id=RID1, registry=_registry(genesis)
    )
    assert not signed_report.accepted
    assert signed_report.trust_status is TrustStatus.UNVERIFIED


def test_non_genesis_requires_trusted_head_for_acceptance() -> None:
    genesis = _body_genesis()
    successor = build_frame(
        kind="body.pulse",
        stream_id=RID1,
        seq=1,
        utc=UTC1,
        payload={},
        prev=genesis["payload_hash"],
        prev_wave=None,
    )
    registry = _registry(genesis)
    untrusted = accept_frame(
        successor,
        declared_stream_id=RID1,
        head=_head(genesis, trusted=False),
        registry=registry,
    )
    assert not untrusted.accepted
    assert untrusted.trust_status is TrustStatus.UNVERIFIED
    accepted = accept_frame(
        successor,
        declared_stream_id=RID1,
        head=_head(genesis, trusted=True),
        registry=registry,
    )
    assert accepted.accepted


def test_swarm_is_never_accepted_without_real_signature_verification() -> None:
    unsigned = build_frame(
        kind="swarm.echo",
        stream_id="net:planet",
        seq=0,
        utc=UTC0,
        payload={},
        prev=None,
        prev_wave=None,
    )
    registry = RegistryEvidence(
        kind_families={"swarm.echo": "swarm"},
        genesis_hashes={"net:planet": unsigned["frame_hash"]},
        authenticated=True,
        fresh=True,
    )
    unsigned_report = accept_frame(
        unsigned, declared_stream_id="net:planet", registry=registry
    )
    assert not unsigned_report.accepted
    assert unsigned_report.trust_status is TrustStatus.DRIFT

    signed = build_frame(
        kind="swarm.echo",
        stream_id="net:planet",
        seq=0,
        utc=UTC0,
        payload={},
        prev=None,
        prev_wave=None,
        sig=_jws(),
    )
    signed_registry = RegistryEvidence(
        kind_families={"swarm.echo": "swarm"},
        genesis_hashes={"net:planet": signed["frame_hash"]},
        authenticated=True,
        fresh=True,
    )
    signed_report = accept_frame(
        signed, declared_stream_id="net:planet", registry=signed_registry
    )
    assert not signed_report.accepted
    assert signed_report.trust_status is TrustStatus.UNVERIFIED


def test_stateful_acceptor_advances_and_refuses_rollback() -> None:
    genesis = _body_genesis()
    acceptor = FrameAcceptor(_registry(genesis))
    first = acceptor.accept(genesis, declared_stream_id=RID1)
    assert first.accepted
    assert acceptor.head(RID1).frame_hash == genesis["frame_hash"]

    successor = build_frame(
        kind="body.pulse",
        stream_id=RID1,
        seq=1,
        utc=UTC1,
        payload={"next": True},
        prev=genesis["payload_hash"],
        prev_wave=None,
    )
    second = acceptor.accept(successor, declared_stream_id=RID1)
    assert second.accepted
    assert acceptor.head(RID1).seq == 1

    replay = acceptor.accept(successor, declared_stream_id=RID1)
    assert replay.accepted
    assert replay.trust_status is TrustStatus.VERIFIED

    rollback = acceptor.accept(genesis, declared_stream_id=RID1)
    assert not rollback.accepted
    assert rollback.structurally_valid
    assert rollback.error_code == "head-rollback"
    assert rollback.trust_status is TrustStatus.DRIFT
