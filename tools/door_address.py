"""Exact RAPP/1 door-address derivation with quarantined legacy observation.

Normal parsing and URL resolution accept only the section 6.1 rappid grammar.
Historical forms are visible solely through ``parse_legacy_for_migration``;
that API preserves evidence but cannot resolve a door or emit a replacement
identity.
"""

from __future__ import annotations

import re
import sys
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rapp1_core import parse_rappid as _core_parse_rappid  # noqa: E402
from rapp1_core.errors import IdentityError  # noqa: E402
from rapp1_core.identity import validate_owner, validate_slug  # noqa: E402


_LEGACY_NAME = r"[A-Za-z0-9][A-Za-z0-9._-]*"
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.ASCII,
)
_V2_RE = re.compile(
    rf"^rappid:v2:(?P<string_kind>[a-z][a-z0-9-]*):"
    rf"@(?P<owner>{_LEGACY_NAME})/(?P<slug>{_LEGACY_NAME}):"
    rf"(?P<tail>[0-9a-f]{{32}})@github\.com/"
    rf"(?P<owner2>{_LEGACY_NAME})/(?P<slug2>{_LEGACY_NAME})$",
    re.ASCII,
)
_PROVISIONAL_RE = re.compile(
    rf"^rappid:@(?P<owner>{_LEGACY_NAME})/(?P<slug>{_LEGACY_NAME}):"
    r"(?P<tail>[0-9a-f]{8,63})$",
    re.ASCII,
)


_FRONT_DOOR_KINDS = frozenset(
    {
        "twin",
        "operator",
        "personal",
        "project",
        "memorial",
        "pre-founder",
        "mirror",
        "experiment",
        "custom",
    }
)
_GATE_KINDS = frozenset(
    {
        "neighborhood",
        "ant-farm",
        "braintrust",
        "workspace",
        "hatched",
        "rapplication",
        "prototype",
        "place",
    }
)
VALID_KINDS = _FRONT_DOOR_KINDS | _GATE_KINDS


class InvalidRappidError(ValueError):
    """Raised when an active path receives a non-section-6.1 identity."""


@dataclass(frozen=True)
class LegacyRappidObservation:
    original: str
    form: str
    owner: str | None
    slug: str | None
    tail: str
    tail_bits: int
    string_kind: str | None = None
    location_match: bool | None = None
    restructured_rappid: str | None = None
    identity_state: str = "provisional"
    provisional: bool = True
    resolvable: bool = False
    protocol_emission_allowed: bool = False
    tail_preserved: bool = True

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_rappid(rappid: str) -> dict[str, Any]:
    """Parse one exact section 6.1 rappid into the historical consumer shape."""

    try:
        parsed = _core_parse_rappid(rappid)
    except (IdentityError, TypeError) as exc:
        raise InvalidRappidError(str(exc)) from exc
    return {
        "form": "canonical",
        "owner": parsed.owner,
        "slug": parsed.slug,
        "hash": parsed.tail,
        "hash_bits": 256,
        "kind": None,
    }


def canonicalize_rappid(rappid: str) -> str:
    """Return an already exact identity unchanged; never migrate or mint."""

    _core_parse(rappid)
    return rappid


def parse_legacy_for_migration(rappid: str) -> LegacyRappidObservation:
    """Preserve a known historical identity as non-resolvable evidence."""

    if type(rappid) is not str:
        raise InvalidRappidError("legacy rappid must be a string")
    try:
        _core_parse_rappid(rappid)
    except IdentityError:
        pass
    else:
        raise InvalidRappidError(
            "identity is already exact RAPP/1 and is not migration input"
        )

    if _UUID_RE.fullmatch(rappid):
        tail = rappid.replace("-", "")
        return LegacyRappidObservation(
            original=rappid,
            form="uuid-legacy",
            owner=None,
            slug=None,
            tail=tail,
            tail_bits=128,
        )

    v2 = _V2_RE.fullmatch(rappid)
    if v2 is not None:
        return LegacyRappidObservation(
            original=rappid,
            form="v2-legacy",
            owner=v2["owner"],
            slug=v2["slug"],
            tail=v2["tail"],
            tail_bits=128,
            string_kind=v2["string_kind"],
            location_match=(
                v2["owner"] == v2["owner2"] and v2["slug"] == v2["slug2"]
            ),
        )

    provisional = _PROVISIONAL_RE.fullmatch(rappid)
    if provisional is not None:
        tail = provisional["tail"]
        return LegacyRappidObservation(
            original=rappid,
            form="provisional-self-locating",
            owner=provisional["owner"],
            slug=provisional["slug"],
            tail=tail,
            tail_bits=len(tail) * 4,
        )

    raise InvalidRappidError("identity is neither exact RAPP/1 nor known migration input")


def canonicalize_on_read(rappid: str) -> LegacyRappidObservation:
    """Restructure a located legacy form without promoting its identity."""

    observation = parse_legacy_for_migration(rappid)
    if observation.owner is None or observation.slug is None:
        raise InvalidRappidError(
            "legacy identity has no self-location and cannot be restructured"
        )
    if observation.location_match is False:
        raise InvalidRappidError(
            "legacy v2 identity and repository locator do not match"
        )
    try:
        owner = validate_owner(observation.owner.lower())
        slug = validate_slug(observation.slug.lower())
    except (IdentityError, TypeError) as exc:
        raise InvalidRappidError(
            "legacy location cannot be represented by section 6.1 labels"
        ) from exc
    restructured = f"rappid:@{owner}/{slug}:{observation.tail}"
    return replace(
        observation,
        owner=owner,
        slug=slug,
        restructured_rappid=restructured,
    )


def _core_parse(rappid: str):
    try:
        return _core_parse_rappid(rappid)
    except (IdentityError, TypeError) as exc:
        raise InvalidRappidError(str(exc)) from exc


def _record_kind(
    rappid: str, identity_record: Mapping[str, Any] | None
) -> str | None:
    if identity_record is None:
        return None
    if not isinstance(identity_record, Mapping):
        raise InvalidRappidError("identity_record must be a mapping")
    recorded_rappid = identity_record.get("rappid")
    if type(recorded_rappid) is not str:
        raise InvalidRappidError("identity_record has no exact rappid")
    _core_parse(recorded_rappid)
    if recorded_rappid != rappid:
        raise InvalidRappidError("identity_record belongs to a different rappid")
    kind = identity_record.get("kind")
    if kind is None:
        return None
    if type(kind) is not str or kind not in VALID_KINDS:
        raise InvalidRappidError("identity record has an unsupported door kind")
    return kind


def door_from_rappid(
    rappid: str, identity_record: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Resolve URLs only for an exact identity; source kind from its record."""

    parsed = _core_parse(rappid)
    kind = _record_kind(rappid, identity_record)
    door_type = (
        None
        if kind is None
        else ("front_door" if kind in _FRONT_DOOR_KINDS else "gate")
    )
    owner, slug = parsed.owner, parsed.slug
    raw_base = f"https://raw.githubusercontent.com/{owner}/{slug}/main"
    return {
        "rappid": rappid,
        "canonical": rappid,
        "owner": owner,
        "repo": slug,
        "slug": slug,
        "hash": parsed.tail,
        "kind": kind,
        "door_type": door_type,
        "form": "canonical",
        "urls": {
            "repo": f"https://github.com/{owner}/{slug}",
            "front": f"https://{owner}.github.io/{slug}/",
            "identity": f"{raw_base}/rappid.json",
            "holocard": f"{raw_base}/card.json",
            "holo_md": f"{raw_base}/holo.md",
            "avatar": f"{raw_base}/holo.svg",
            "summon_qr": f"{raw_base}/holo-qr.svg",
            "members": f"{raw_base}/members.json",
            "facets": f"{raw_base}/facets.json",
        },
    }


def estate_url(github_handle: str) -> str:
    try:
        owner = validate_owner(github_handle)
    except (IdentityError, TypeError) as exc:
        raise InvalidRappidError(str(exc)) from exc
    return f"https://raw.githubusercontent.com/{owner}/rapp-estate/main/estate.json"


def owner_repo_from_rappid(rappid: str) -> tuple[str, str]:
    parsed = _core_parse(rappid)
    return parsed.owner, parsed.slug
