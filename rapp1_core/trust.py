"""Explicit trust evidence and inspection status types."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import AbstractSet, Mapping


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
    deprecated_kinds: AbstractSet[str] = field(default_factory=frozenset)
    genesis_hashes: Mapping[str, str] = field(default_factory=dict)
    authenticated: bool = False
    fresh: bool = False
    registered_egg_variants: AbstractSet[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if type(self.authenticated) is not bool or type(self.fresh) is not bool:
            raise TypeError("registry authentication flags must be booleans")
        kind_families = deepcopy(dict(self.kind_families))
        deprecated_kinds = deepcopy(tuple(self.deprecated_kinds))
        genesis_hashes = deepcopy(dict(self.genesis_hashes))
        registered_egg_variants = deepcopy(
            tuple(self.registered_egg_variants)
        )
        if (
            any(
                type(key) is not str or type(value) is not str
                for key, value in kind_families.items()
            )
            or any(
                type(key) is not str or type(value) is not str
                for key, value in genesis_hashes.items()
            )
            or any(type(kind) is not str for kind in deprecated_kinds)
            or any(
                type(variant) is not str
                for variant in registered_egg_variants
            )
        ):
            raise TypeError("registry mappings and sets must contain only strings")
        object.__setattr__(
            self,
            "kind_families",
            MappingProxyType(kind_families),
        )
        object.__setattr__(
            self,
            "deprecated_kinds",
            frozenset(deprecated_kinds),
        )
        object.__setattr__(
            self,
            "genesis_hashes",
            MappingProxyType(genesis_hashes),
        )
        object.__setattr__(
            self,
            "registered_egg_variants",
            frozenset(registered_egg_variants),
        )


@dataclass(frozen=True)
class HeadState:
    stream_id: str
    seq: int
    utc: str
    payload_hash: str
    frame_hash: str
    trusted: bool = False
    genesis_hash: str | None = None
    signature_present: bool | None = None


@dataclass(frozen=True)
class AuthenticatedHeadProof:
    """Caller-authenticated proof binding a rootless head to a registry epoch.

    This type deliberately has no JSON parser or serializer. Constructing it is
    an explicit external trust-boundary operation; HeadState fields alone never
    prove that a head was authenticated.
    """

    stream_id: str
    seq: int
    utc: str
    payload_hash: str
    frame_hash: str
    genesis_hash: str
    signature_present: bool
