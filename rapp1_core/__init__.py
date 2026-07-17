"""Target-owned strict structural core for the RAPP/1 protocol suite."""

from .canonical import canonical_bytes, require_canonical_json, strict_loads
from .egg import accept_egg, extract_egg, inspect_egg, pack_egg
from .frame import (
    AcceptedFrameSnapshot,
    FrameAcceptor,
    FrameAcceptorSnapshot,
    accept_frame,
    build_frame,
    inspect_frame,
    inspect_frame_bytes,
    validate_utc,
)
from .hashing import H, Hb, hash_bytes, hash_value
from .identity import (
    mint_keyless_rappid,
    mint_spki_rappid,
    parse_rappid,
    parse_stream_id,
    validate_kind,
)
from .jws import parse_detached_jws
from .trust import AuthenticatedHeadProof, HeadState, RegistryEvidence, TrustStatus

__all__ = [
    "H",
    "Hb",
    "AcceptedFrameSnapshot",
    "AuthenticatedHeadProof",
    "FrameAcceptor",
    "FrameAcceptorSnapshot",
    "HeadState",
    "RegistryEvidence",
    "TrustStatus",
    "accept_egg",
    "accept_frame",
    "build_frame",
    "canonical_bytes",
    "extract_egg",
    "hash_bytes",
    "hash_value",
    "inspect_egg",
    "inspect_frame",
    "inspect_frame_bytes",
    "mint_keyless_rappid",
    "mint_spki_rappid",
    "pack_egg",
    "parse_detached_jws",
    "parse_rappid",
    "parse_stream_id",
    "require_canonical_json",
    "strict_loads",
    "validate_kind",
    "validate_utc",
]
