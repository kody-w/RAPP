"""lineage_check — variant lineage / uninitialized-template-clone detection.

Constitution Article XXXIV (single-parent rule) + TEMPLATE.md boot guard.

`check_lineage()` classifies the repo it runs in by comparing the identity its
`rappid.json` declares against the repo the git remote actually points at:

    self / master         this repo IS a known template root (e.g. the rapp
                          species root). Its rappid is a KNOWN_TEMPLATE_REPOS
                          rappid and its remote matches that template's repo.
    variant_uninitialized a fresh "Use this template" clone: rappid.json still
                          carries a known template's rappid, but the remote
                          points at a different owner/repo. Must run
                          installer/initialize-variant.sh to mint its own rappid.
    variant_initialized   a properly initialized variant: it has its own rappid
                          (owner/slug matches its remote) and a parent_rappid.
    no_rappid             no rappid.json at the repo root.
    lineage_mismatch      rappid.json present but inconsistent / unparseable.

These are exactly the statuses installer/initialize-variant.sh branches on.

To make a NEW template repo's uninitialized clones detectable, append its
(canonical rappid -> "owner/repo") pair to KNOWN_TEMPLATE_REPOS.

This guard is deliberately standard-library-only because sparse and installed
brainstems do not contain the repository-root strict core dependencies. Its
section 6.1 parser is parity-tested against ``rapp1_core.parse_rappid``.
"""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
from decimal import Decimal, InvalidOperation
from pathlib import Path

MAX_IDENTITY_RECORD_BYTES = 1024 * 1024
MAX_CANONICAL_IDENTITY_RECORD_BYTES = 1024 * 1024
MAX_JSON_DEPTH = 64
_MAX_BINARY64_CANONICAL_BYTES = 32
_LABEL = r"[a-z0-9]+(?:-[a-z0-9]+)*"
_RAPPID_RE = re.compile(
    rf"^rappid:@(?P<owner>{_LABEL})/(?P<slug>{_LABEL}):"
    r"(?P<tail>[0-9a-f]{64})$",
    re.ASCII,
)

# canonical Eternity rappid  ->  the template repo's canonical "owner/repo".
# Seeded with the rapp species root (the godfather).
KNOWN_TEMPLATE_REPOS = {
    "rappid:@kody-w/rapp:9a8f0a4b5a710e20f4d819a0f37d2a4c9f113b5e78fb3c29e70b54fff48a38f9": "kody-w/RAPP",
}


def _repo_root(start: str | None = None) -> str:
    requested = Path(start or os.getcwd()).resolve()
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=requested,
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:
        pass

    candidates = (requested, *requested.parents[:2], Path(__file__).resolve().parents[2])
    for candidate in candidates:
        if (candidate / "rappid.json").is_file():
            return str(candidate)
    return str(requested)


def _git_remote_owner_repo(root: str) -> str | None:
    """Return 'owner/repo' parsed from origin, or None."""
    try:
        out = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=root, capture_output=True, text=True, timeout=5,
        )
    except Exception:
        return None
    url = (out.stdout or "").strip()
    if not url:
        return None
    url = url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    for p in ("https://github.com/", "http://github.com/",
              "git@github.com:", "ssh://git@github.com/"):
        if url.startswith(p):
            url = url[len(p):]
            break
    else:
        raise ValueError("origin is not an exact GitHub repository URL")
    parts = [s for s in url.split("/") if s]
    if len(parts) != 2:
        raise ValueError("origin does not identify exactly one owner/repository")
    owner, slug = (part.lower() for part in parts)
    if (
        len(owner) > 39
        or len(slug) > 100
        or re.fullmatch(_LABEL, owner, re.ASCII) is None
        or re.fullmatch(_LABEL, slug, re.ASCII) is None
    ):
        raise ValueError("origin owner/repository is outside section 6.1 grammar")
    return f"{owner}/{slug}"


def _rappid_owner_slug(rappid: str) -> str | None:
    """Parse exact section 6.1 identity and return its owner/slug."""
    if type(rappid) is not str:
        return None
    match = _RAPPID_RE.fullmatch(rappid)
    if match is None:
        return None
    owner = match.group("owner")
    slug = match.group("slug")
    if len(owner) > 39 or len(slug) > 100:
        return None
    return f"{owner}/{slug}"


def _number(token: str, *, integer: bool):
    try:
        binary64 = float(token)
        if not math.isfinite(binary64):
            raise ValueError("number is not finite")
        if Decimal(token) != Decimal(repr(binary64)):
            raise ValueError("number changes value through binary64")
    except (InvalidOperation, OverflowError) as exc:
        raise ValueError("number is outside the binary64 domain") from exc
    return int(token) if integer else binary64


def _object_from_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON member: {key}")
        value[key] = item
    return value


def _validate_json_value(value, depth: int = 1) -> None:
    if depth > MAX_JSON_DEPTH:
        raise ValueError("identity record exceeds JSON depth limit")
    if type(value) is str:
        value.encode("utf-8")
    elif type(value) is list:
        for item in value:
            _validate_json_value(
                item, depth + 1 if type(item) in (list, dict) else depth
            )
    elif type(value) is dict:
        for key, item in value.items():
            key.encode("utf-8")
            _validate_json_value(
                item, depth + 1 if type(item) in (list, dict) else depth
            )


def _canonical_size_upper_bound(value) -> int:
    """Bound RFC 8785 output size without requiring its unavailable package.

    JSON string encoding is measured directly. Every accepted number has
    already round-tripped through finite IEEE-754 binary64; 32 bytes safely
    bounds its shortest ECMAScript serialization (including fixed notation).
    The deliberately conservative number bound may reject unusually numeric
    records, which is appropriate for this small fail-closed identity record.
    """
    if value is None:
        return 4
    if type(value) is bool:
        return 4 if value else 5
    if type(value) in (int, float):
        return _MAX_BINARY64_CANONICAL_BYTES
    if type(value) is str:
        return len(
            json.dumps(value, ensure_ascii=False).encode("utf-8", errors="strict")
        )
    if type(value) is list:
        size = 2 + max(0, len(value) - 1)
        for item in value:
            size += _canonical_size_upper_bound(item)
            if size > MAX_CANONICAL_IDENTITY_RECORD_BYTES:
                return size
        return size
    if type(value) is dict:
        size = 2 + max(0, len(value) - 1)
        for key, item in value.items():
            size += _canonical_size_upper_bound(key) + 1
            size += _canonical_size_upper_bound(item)
            if size > MAX_CANONICAL_IDENTITY_RECORD_BYTES:
                return size
        return size
    raise ValueError(f"unsupported JSON value: {type(value).__name__}")


def _load_identity_record(path: Path) -> dict:
    raw = path.read_bytes()
    if len(raw) > MAX_IDENTITY_RECORD_BYTES:
        raise ValueError("identity record exceeds 1 MiB")
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("identity record has a UTF-8 BOM")
    text = raw.decode("utf-8", errors="strict")
    value = json.loads(
        text,
        object_pairs_hook=_object_from_pairs,
        parse_int=lambda token: _number(token, integer=True),
        parse_float=lambda token: _number(token, integer=False),
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"forbidden JSON number: {token}")
        ),
    )
    if type(value) is not dict:
        raise ValueError("identity record must be a JSON object")
    _validate_json_value(value)
    if _canonical_size_upper_bound(value) > MAX_CANONICAL_IDENTITY_RECORD_BYTES:
        raise ValueError("identity record canonical-size upper bound exceeds 1 MiB")
    return value


def check_lineage(repo_root: str | None = None) -> dict:
    """Classify this repo's lineage state. Returns {'status': ..., ...}."""
    root = _repo_root(repo_root)
    manifest = os.path.join(root, "rappid.json")
    if not os.path.isfile(manifest):
        return {"status": "no_rappid", "root": root}

    try:
        data = _load_identity_record(Path(manifest))
    except Exception as e:
        return {"status": "lineage_mismatch", "root": root, "detail": f"unreadable rappid.json: {e}"}

    rappid = data.get("rappid") or ""
    parent_rappid = data.get("parent_rappid")
    record_kind = data.get("kind")
    try:
        remote = _git_remote_owner_repo(root)
    except ValueError as exc:
        return {
            "status": "lineage_mismatch",
            "root": root,
            "rappid": rappid,
            "parent_rappid": parent_rappid,
            "kind": record_kind,
            "detail": str(exc),
        }

    info = {
        "root": root,
        "rappid": rappid,
        "remote": remote,
        "parent_rappid": parent_rappid,
        "kind": record_kind,
    }

    if rappid in KNOWN_TEMPLATE_REPOS:
        canonical = KNOWN_TEMPLATE_REPOS[rappid]
        # No remote (not yet pushed) — assume we are the template itself.
        if remote is None or remote.lower() == canonical.lower():
            return {**info, "status": "self", "template": canonical}
        # Carries a template's rappid but lives at a different repo => fresh clone.
        return {**info, "status": "variant_uninitialized", "template": canonical}

    if not rappid:
        return {**info, "status": "lineage_mismatch", "detail": "rappid.json has no 'rappid' field"}

    owner_slug = _rappid_owner_slug(rappid)
    if owner_slug is None:
        return {**info, "status": "lineage_mismatch", "detail": f"unparseable rappid: {rappid}"}

    if not parent_rappid or _rappid_owner_slug(parent_rappid) is None:
        return {
            **info,
            "status": "lineage_mismatch",
            "detail": "initialized variant has no exact parent_rappid",
        }

    # An initialized variant's own rappid owner/slug should match its remote.
    if remote and owner_slug != remote.lower():
        return {**info, "status": "lineage_mismatch",
                "detail": f"rappid says {owner_slug} but remote is {remote}"}

    return {**info, "status": "variant_initialized"}


if __name__ == "__main__":
    import sys
    result = check_lineage()
    print(json.dumps(result, indent=2))
    # Non-zero exit for states that should block a variant boot/init.
    sys.exit(0 if result["status"] in ("self", "master", "variant_initialized") else 1)
