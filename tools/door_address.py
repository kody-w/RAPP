"""door_address — pure derivation of a door's canonical URL set from its rappid.

Authority: pages/docs/ESTATE_SPEC.md (CONSTITUTION Article XLVI).

Canonical form: the self-locating Eternity rappid `rappid:@<owner>/<slug>:<64hex>`
(CONSTITUTION Art. XXXIV.1, finalized 2026-06-03) — owner/slug locate the door, the
256-bit hash is the identity, and `kind` lives in the door's rappid.json record.
The legacy v2 form (`rappid:v2:<kind>:@<owner>/<repo>:<32hex>@github.com/<owner>/<repo>`)
is read-compatible per the compatibility contract (read every legacy form, emit Eternity).

This is the SINGLE implementation of the Estate Spec's `door_from_rappid()`
contract (ESTATE_SPEC §5). Every consumer that maps rappid → door URLs uses
this module — never reinvents the parsing, never patches around it.

Per Article XLVI.5 (No Fallbacks; Spec Says What's True): an invalid rappid
raises InvalidRappidError. There is no "best-effort" mode, no `local.github.io`
workaround, no "guess the kind from the name." The string either matches the
spec or it doesn't.

Pure stdlib. Zero deps. Importable from agents/, tools/, tests/, or anywhere.
"""

from __future__ import annotations

import re


# Canonical: the self-locating Eternity rappid (CONSTITUTION Art. XXXIV.1, 2026-06-03).
# rappid:@<owner>/<slug>:<64hex> — owner/slug locate the door; the 256-bit hash is the
# identity; `kind` is NOT in the string (it lives in the rappid.json record and is passed
# to door_from_rappid). 64 lowercase hex = full SHA-256, never the truncated 32.
_ETERNITY_RE = re.compile(
    r"^rappid:@(?P<owner>[A-Za-z0-9][A-Za-z0-9._-]*)/(?P<slug>[A-Za-z0-9][A-Za-z0-9._-]*):"
    r"(?P<hex>[a-f0-9]{64})$"
)

# Legacy v2 rappid addressing regex — read-compatible, no longer emitted.
# rappid:v2:<kind>:@<owner>/<repo>:<32-hex-no-dashes>@github.com/<owner2>/<repo2>
# Where (owner, repo) MUST equal (owner2, repo2) — that equality is checked
# explicitly below because regex backreferences make the pattern unreadable.
_RAPPID_RE = re.compile(
    r"^rappid:v2:"
    r"(?P<kind>[a-z][a-z0-9-]*):"
    r"@(?P<owner>[A-Za-z0-9][A-Za-z0-9._-]*)/(?P<repo>[A-Za-z0-9][A-Za-z0-9._-]*):"
    r"(?P<hex>[a-f0-9]{32})"
    r"@github\.com/(?P<owner2>[A-Za-z0-9][A-Za-z0-9._-]*)/(?P<repo2>[A-Za-z0-9][A-Za-z0-9._-]*)$"
)


# Per ESTATE_SPEC §1: valid kinds are frozen as of 2026-05-09. Adding a kind
# requires a CONSTITUTION amendment because every consumer derives behavior
# from this token.
# Front-door kinds: a single AI presence. Extended 2026-06-02 (CONSTITUTION
# Art. XLVI.2 amendment) to ratify the single-presence kinds already emitted
# across the kernel (TWIN_LIFECYCLE_SPEC, NEIGHBORHOOD_EGG_SPEC, ECOSYSTEM),
# RAR `@rapp/twin_agent`, and RAPP-Network's `project_twin_agent.py`.
_FRONT_DOOR_KINDS = frozenset({
    "twin", "operator", "personal", "project", "memorial",
    "pre-founder", "mirror", "experiment", "custom",
})
# Gate kinds: a community AI you enter to find others. `place` is a gate — a
# location others enter, not a single presence (reclassified 2026-06-03).
_GATE_KINDS = frozenset({
    "neighborhood", "ant-farm", "braintrust", "workspace",
    "hatched", "rapplication", "prototype", "place",
})
VALID_KINDS = _FRONT_DOOR_KINDS | _GATE_KINDS


# Per ESTATE_SPEC §2 / CONSTITUTION Art. XLVI.2: door type is deterministic
# from kind. A single AI presence is a front door; a community AI you enter to
# find others is a gate. The `operator` kind names a person's personal brainstem
# identity, which functions as their own front door.
def _door_type_for_kind(kind: str) -> str:
    return "front_door" if kind in _FRONT_DOOR_KINDS else "gate"


class InvalidRappidError(ValueError):
    """Raised by door_from_rappid for any rappid that doesn't match the spec.

    Subclasses ValueError so callers can `except ValueError` if they want a
    catch-all, but typed for explicit handling per ESTATE_SPEC §6 (stale
    rappid rejection).
    """


def _door_dict(rappid: str, owner: str, repo: str, kind: str | None) -> dict:
    """Build the canonical door object from a located (owner, repo) and optional kind."""
    raw_base = f"https://raw.githubusercontent.com/{owner}/{repo}/main"
    return {
        "rappid": rappid,
        "owner": owner,
        "repo": repo,
        "kind": kind,
        "door_type": _door_type_for_kind(kind) if kind else None,
        "urls": {
            "repo":      f"https://github.com/{owner}/{repo}",
            "front":     f"https://{owner}.github.io/{repo}/",
            "identity":  f"{raw_base}/rappid.json",
            "holocard":  f"{raw_base}/card.json",
            "holo_md":   f"{raw_base}/holo.md",
            "avatar":    f"{raw_base}/holo.svg",
            "summon_qr": f"{raw_base}/holo-qr.svg",
            "members":   f"{raw_base}/members.json",
            "facets":    f"{raw_base}/facets.json",
        },
    }


def door_from_rappid(rappid: str, kind: str | None = None) -> dict:
    """Return the canonical door object for a rappid. Pure function.

    Implements the contract in ESTATE_SPEC §5. Accepts the **canonical self-locating
    Eternity** rappid `rappid:@<owner>/<slug>:<64hex>` and the **legacy v2** form
    `rappid:v2:<kind>:@<owner>/<repo>:<32hex>@github.com/<owner>/<repo>`.

    Args:
      rappid: the rappid string (Eternity canonical, or legacy v2).
      kind: the organism kind, read from the door's rappid.json record. Used only for the
        Eternity form (whose string carries no kind); ignored for v2 (kind parsed from the
        string). If omitted for an Eternity rappid, `kind` and `door_type` come back None.

    Returns:
      A dict with keys: rappid, owner, repo, kind, door_type, urls. `urls` has keys:
      repo, front, identity, holocard, holo_md, avatar, summon_qr, members, facets. The
      `members` URL is populated only for gates; twins return an empty members.json (or 404).

    Raises:
      InvalidRappidError: if the string matches neither the canonical Eternity form nor the
        legacy v2 form; if a v2 rappid's left (owner, repo) != its origin pin; or if a
        supplied kind is not in VALID_KINDS.
    """
    if not isinstance(rappid, str):
        raise InvalidRappidError(f"rappid must be a string, got {type(rappid).__name__}")

    # Canonical: the self-locating Eternity form. owner/slug locate the door; kind (and
    # thus door_type) comes from the record, supplied by the caller.
    em = _ETERNITY_RE.match(rappid)
    if em:
        if kind is not None and kind not in VALID_KINDS:
            raise InvalidRappidError(
                f"rappid kind {kind!r} is not in VALID_KINDS={sorted(VALID_KINDS)}. "
                f"Adding a kind requires a CONSTITUTION amendment (Article XLVI)."
            )
        return _door_dict(rappid, em.group("owner"), em.group("slug"), kind)

    # Legacy: the v2 addressing form. kind is parsed from the string.
    m = _RAPPID_RE.match(rappid)
    if not m:
        raise InvalidRappidError(
            f"rappid matches neither the canonical Eternity form "
            f"(rappid:@<owner>/<slug>:<64hex>) nor the legacy v2 form: {rappid!r}"
        )

    owner = m.group("owner")
    repo = m.group("repo")
    if owner != m.group("owner2") or repo != m.group("repo2"):
        raise InvalidRappidError(
            f"rappid origin mismatch: identity says @{owner}/{repo}, origin pin says "
            f"@github.com/{m.group('owner2')}/{m.group('repo2')}. The two MUST be equal."
        )
    v2_kind = m.group("kind")
    if v2_kind not in VALID_KINDS:
        raise InvalidRappidError(
            f"rappid kind {v2_kind!r} is not in VALID_KINDS={sorted(VALID_KINDS)}. "
            f"Adding a kind requires a CONSTITUTION amendment (Article XLVI)."
        )
    return _door_dict(rappid, owner, repo, v2_kind)


def estate_url(github_handle: str) -> str:
    """The canonical pure-raw URL for a user's full estate.

    Per ESTATE_SPEC §4.2 — single roundtrip, no auth, no API.
    """
    if not github_handle or "/" in github_handle or " " in github_handle:
        raise InvalidRappidError(f"invalid github handle: {github_handle!r}")
    return f"https://raw.githubusercontent.com/{github_handle}/rapp-estate/main/estate.json"


# Convenience: parse just the (owner, repo) without building the full URL set.
# Used by the planter where it needs the pair but not the URLs.
def owner_repo_from_rappid(rappid: str) -> tuple[str, str]:
    """Return (owner, repo) for a valid rappid. Raises InvalidRappidError."""
    door = door_from_rappid(rappid)
    return door["owner"], door["repo"]
