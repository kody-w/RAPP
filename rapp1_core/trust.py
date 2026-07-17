"""Explicit trust evidence and inspection status types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


class TrustStatus(str, Enum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    STALE = "STALE"
    DRIFT = "DRIFT"


class CheckStatus(str, Enum):
    PASS = "PASS"
    UNVERIFIED = "UNVERIFIED"
    FAIL = "FAIL"


@dataclass(frozen=True)
class CheckResult:
    step: str
    status: CheckStatus
    detail: str

    def as_dict(self) -> dict[str, str]:
        return {
            "step": self.step,
            "status": self.status.value,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class RegistryEvidence:
    """Facts from a registry authenticated outside this structural-only core."""

    kind_families: Mapping[str, str] = field(default_factory=dict)
    deprecated_kinds: frozenset[str] = frozenset()
    genesis_hashes: Mapping[str, str] = field(default_factory=dict)
    authenticated: bool = False
    fresh: bool = False


@dataclass(frozen=True)
class HeadState:
    stream_id: str
    seq: int
    utc: str
    payload_hash: str
    frame_hash: str
    trusted: bool = False
