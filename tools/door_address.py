"""door_address — pure derivation of a door's canonical URL set from its rappid.

Authority: pages/docs/ESTATE_SPEC.md (CONSTITUTION Article XLVI + XXXIV.1).

This is the SINGLE implementation of the Estate Spec's `door_from_rappid()`
contract (ESTATE_SPEC §5). Every consumer that maps rappid → door URLs uses
this module — never reinvents the parsing, never patches around it.

THE CONSOLIDATED RAPPID (the one format, locked 2026-06-03)
----------------------------------------------------------
    rappid:@<owner>/<slug>:<64hex>

One string that is BOTH identity and self-locating:
  - `@<owner>/<slug>` — the canonical location. `github.com/<owner>/<slug>` is
    the door; every door URL derives from it by string parsing (no lookup, no
    API), preserving the Article-XLVI curl-discovery property.
  - `<64hex>` — the full 256-bit SHA-256 identity hash. The hash is the identity
    and the JOIN KEY; matching/dedup is always on the hash, never the slug.
  - `kind` and all other structure live in the `rappid.json` RECORD (fetched
    from the located repo), not the string — per the Eternity standard.

The string is NEVER re-versioned. This consolidates the three prior forms:
  - v1  `<uuid>`                                              (bare UUID — not self-locating)
  - v2  `rappid:v2:<kind>:@<owner>/<repo>:<32hex>@github.com/<owner>/<repo>`
  - the bare-Eternity `rappid:<slug>:<64hex>`                 (not self-locating)
into the one self-locating Eternity form above.

COMPATIBILITY: every legacy form is READ FOREVER and canonicalized
(`canonicalize_rappid`); only the consolidated form is emitted. A consumer
holding a legacy rappid still resolves; door_from_rappid returns `kind`/
`door_type` from the legacy v2 string when present, or from a record-supplied
`kind` for the consolidated form, else None (resolve kind from the record).

Pure stdlib. Zero deps. Importable from agents/, tools/, tests/, or anywhere.
"""
from __future__ import annotations

import re

_NAME = r"[A-Za-z0-9][A-Za-z0-9._-]*"

# Consolidated canonical form: rappid:@<owner>/<slug>:<64hex>
_CANON_RE = re.compile(
    rf"^rappid:@(?P<owner>{_NAME})/(?P<slug>{_NAME}):(?P<hash>[a-f0-9]{{64}})$"
)
# Legacy v2 (read-only): rappid:v2:<kind>:@<owner>/<repo>:<32hex>@github.com/<owner>/<repo>
_V2_RE = re.compile(
    rf"^rappid:v2:(?P<kind>[a-z][a-z0-9-]*):"
    rf"@(?P<owner>{_NAME})/(?P<repo>{_NAME}):(?P<hash>[a-f0-9]{{32}})"
    rf"@github\.com/(?P<owner2>{_NAME})/(?P<repo2>{_NAME})$"
)
# Legacy v1 (read-only): a bare UUID. Carries NO location — callers must supply
# the repo (owner/slug) out of band to build URLs or canonicalize.
_UUID_RE = re.compile(
    r"^(?P<hash>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$"
)
# Grandfathered canonical structure: a legacy hash (e.g. a migrated v2 32-hex not
# yet re-anchored to 256-bit) carried in the new self-locating structure. Checked
# LAST so a real 64-hex always matches _CANON_RE first.
_CANON_LEGACYHASH_RE = re.compile(
    rf"^rappid:@(?P<owner>{_NAME})/(?P<slug>{_NAME}):(?P<hash>[a-f0-9]{{8,}})$"
)


# Front-door kinds: a single AI presence (CONSTITUTION Art. XLVI.2). `place` is a
# gate (a location others enter). Extended 2026-06-02; place reclassified 2026-06-03.
_FRONT_DOOR_KINDS = frozenset({
    "twin", "operator", "personal", "project", "memorial",
    "pre-founder", "mirror", "experiment", "custom",
})
_GATE_KINDS = frozenset({
    "neighborhood", "ant-farm", "braintrust", "workspace",
    "hatched", "rapplication", "prototype", "place",
})
VALID_KINDS = _FRONT_DOOR_KINDS | _GATE_KINDS


def _door_type_for_kind(kind: str | None) -> str | None:
    if kind is None:
        return None
    return "front_door" if kind in _FRONT_DOOR_KINDS else "gate"


class InvalidRappidError(ValueError):
    """Raised for a rappid that matches no known form (consolidated or legacy)."""


def parse_rappid(rappid: str) -> dict:
    """Parse any rappid form. Returns a dict:

      {form, owner, slug, hash, hash_bits, kind}

    - form: "canonical" | "canonical-legacyhash" | "v2-legacy" | "uuid-legacy"
    - owner/slug: the location (None for a bare UUID, which is not self-locating)
    - hash: the identity hash (hex, dashes stripped for UUIDs)
    - hash_bits: 256 for a full 64-hex, else the legacy bit-width (128 for v2/UUID)
    - kind: present only for v2-legacy (it carried kind inline); else None

    Reads every legacy form forever. Raises InvalidRappidError on no match.
    """
    if not isinstance(rappid, str):
        raise InvalidRappidError(f"rappid must be a string, got {type(rappid).__name__}")

    m = _CANON_RE.match(rappid)
    if m:
        return {"form": "canonical", "owner": m["owner"], "slug": m["slug"],
                "hash": m["hash"], "hash_bits": 256, "kind": None}

    m = _V2_RE.match(rappid)
    if m:
        if m["owner"] != m["owner2"] or m["repo"] != m["repo2"]:
            raise InvalidRappidError(
                f"v2 rappid origin mismatch: @{m['owner']}/{m['repo']} vs "
                f"@github.com/{m['owner2']}/{m['repo2']} — the two MUST be equal.")
        return {"form": "v2-legacy", "owner": m["owner"], "slug": m["repo"],
                "hash": m["hash"], "hash_bits": 128, "kind": m["kind"]}

    m = _UUID_RE.match(rappid)
    if m:
        return {"form": "uuid-legacy", "owner": None, "slug": None,
                "hash": m["hash"].replace("-", ""), "hash_bits": 128, "kind": None}

    m = _CANON_LEGACYHASH_RE.match(rappid)
    if m:
        return {"form": "canonical-legacyhash", "owner": m["owner"], "slug": m["slug"],
                "hash": m["hash"], "hash_bits": len(m["hash"]) * 4, "kind": None}

    raise InvalidRappidError(
        f"rappid matches no known form: {rappid!r}. "
        f"Canonical: rappid:@<owner>/<slug>:<64hex>")


def canonicalize_rappid(rappid: str, owner: str | None = None, slug: str | None = None) -> str:
    """Return the consolidated canonical string for any rappid form.

    Restructures into `rappid:@<owner>/<slug>:<hash>`, PRESERVING the hash (the
    identity). A v2 string drops its `v2:`/`<kind>`/`@host` decorations; a bare
    UUID needs `owner`/`slug` supplied (it carries no location). Idempotent on an
    already-canonical string. The one-time 128→256-bit re-anchor (minting a fresh
    64-hex and recording the old id in `_migrated_from`) is a separate step — this
    function never invents a hash.
    """
    p = parse_rappid(rappid)
    o = p["owner"] or owner
    s = p["slug"] or slug
    if not o or not s:
        raise InvalidRappidError(
            f"cannot canonicalize {rappid!r}: it carries no location (bare UUID); "
            f"supply owner=/slug= (the repo it lives in).")
    return f"rappid:@{o}/{s}:{p['hash']}"


def door_from_rappid(rappid: str, kind: str | None = None) -> dict:
    """Return the canonical door object for a rappid. Pure function (no I/O).

    Reads the consolidated form and every legacy form. The door's URLs derive
    purely from the self-locating `@<owner>/<slug>` (or a v2 string's owner/repo).

    `kind`/`door_type`: taken from the v2-legacy string when present, else from
    the `kind` argument (which a caller resolves from the fetched `rappid.json`
    record for the consolidated form), else None.

    Returns: {rappid, canonical, owner, repo, slug, hash, kind, door_type, urls, form}

    Raises InvalidRappidError if the string matches no form, or carries no
    location (a bare UUID — supply owner/slug via canonicalize first), or if a
    provided/parsed kind is not in VALID_KINDS.
    """
    p = parse_rappid(rappid)
    if not p["owner"] or not p["slug"]:
        raise InvalidRappidError(
            f"rappid {rappid!r} is a bare UUID (no location). Canonicalize it with "
            f"owner=/slug= before resolving a door.")

    owner, slug = p["owner"], p["slug"]
    resolved_kind = p["kind"] if p["kind"] is not None else kind
    if resolved_kind is not None and resolved_kind not in VALID_KINDS:
        raise InvalidRappidError(
            f"rappid kind {resolved_kind!r} is not in VALID_KINDS={sorted(VALID_KINDS)}. "
            f"Adding a kind requires a CONSTITUTION amendment (Article XLVI.2).")

    raw_base = f"https://raw.githubusercontent.com/{owner}/{slug}/main"
    return {
        "rappid": rappid,
        "canonical": f"rappid:@{owner}/{slug}:{p['hash']}",
        "owner": owner,
        "repo": slug,   # back-compat alias; slug IS the repo for a door
        "slug": slug,
        "hash": p["hash"],
        "kind": resolved_kind,
        "door_type": _door_type_for_kind(resolved_kind),
        "form": p["form"],
        "urls": {
            "repo":      f"https://github.com/{owner}/{slug}",
            "front":     f"https://{owner}.github.io/{slug}/",
            "identity":  f"{raw_base}/rappid.json",
            "holocard":  f"{raw_base}/card.json",
            "holo_md":   f"{raw_base}/holo.md",
            "avatar":    f"{raw_base}/holo.svg",
            "summon_qr": f"{raw_base}/holo-qr.svg",
            "members":   f"{raw_base}/members.json",
            "facets":    f"{raw_base}/facets.json",
        },
    }


def estate_url(github_handle: str) -> str:
    """The canonical pure-raw URL for a user's full estate.

    Per ESTATE_SPEC §4.2 — single roundtrip, no auth, no API.
    """
    if not github_handle or "/" in github_handle or " " in github_handle:
        raise InvalidRappidError(f"invalid github handle: {github_handle!r}")
    return f"https://raw.githubusercontent.com/{github_handle}/rapp-estate/main/estate.json"


def owner_repo_from_rappid(rappid: str) -> tuple[str, str]:
    """Return (owner, repo) for a self-locating rappid. Raises InvalidRappidError
    for a bare UUID (no location)."""
    door = door_from_rappid(rappid)
    return door["owner"], door["repo"]
