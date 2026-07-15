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
"""

from __future__ import annotations

import json
import os
import subprocess

# canonical Eternity rappid  ->  the template repo's canonical "owner/repo".
# Seeded with the rapp species root (the godfather).
KNOWN_TEMPLATE_REPOS = {
    "rappid:@kody-w/rapp:9a8f0a4b5a710e20f4d819a0f37d2a4c9f113b5e78fb3c29e70b54fff48a38f9": "kody-w/RAPP",
}


def _repo_root(start: str | None = None) -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start or os.getcwd(),
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:
        pass
    return start or os.getcwd()


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
        # unknown host form — fall back to the last two path segments
        url = "/".join(url.split("/")[-2:])
    parts = [s for s in url.split("/") if s]
    if len(parts) < 2:
        return None
    return f"{parts[-2]}/{parts[-1]}"


def _rappid_owner_slug(rappid: str) -> str | None:
    """Parse 'owner/slug' from a canonical Eternity rappid:@<owner>/<slug>:<hash>."""
    if not isinstance(rappid, str) or not rappid.startswith("rappid:@"):
        return None
    body = rappid[len("rappid:@"):]
    if "/" not in body or ":" not in body:
        return None
    owner_slug = body.rsplit(":", 1)[0]  # drop ':<hash>'
    parts = owner_slug.split("/")
    if len(parts) != 2 or not all(parts):
        return None
    return f"{parts[0]}/{parts[1]}"


def check_lineage(repo_root: str | None = None) -> dict:
    """Classify this repo's lineage state. Returns {'status': ..., ...}."""
    root = _repo_root(repo_root)
    manifest = os.path.join(root, "rappid.json")
    if not os.path.isfile(manifest):
        return {"status": "no_rappid", "root": root}

    try:
        with open(manifest) as fh:
            data = json.load(fh)
    except Exception as e:
        return {"status": "lineage_mismatch", "root": root, "detail": f"unreadable rappid.json: {e}"}

    rappid = data.get("rappid") or ""
    parent_rappid = data.get("parent_rappid")
    remote = _git_remote_owner_repo(root)

    info = {"root": root, "rappid": rappid, "remote": remote, "parent_rappid": parent_rappid}

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

    # An initialized variant's own rappid owner/slug should match its remote.
    if remote and owner_slug.lower() != remote.lower():
        return {**info, "status": "lineage_mismatch",
                "detail": f"rappid says {owner_slug} but remote is {remote}"}

    return {**info, "status": "variant_initialized"}


if __name__ == "__main__":
    import sys
    result = check_lineage()
    print(json.dumps(result, indent=2))
    # Non-zero exit for states that should block a variant boot/init.
    sys.exit(0 if result["status"] in ("self", "master", "variant_initialized") else 1)
