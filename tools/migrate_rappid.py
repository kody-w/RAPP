"""migrate_rappid — rewrite a door's `rappid.json` to the consolidated rappid.

The canonical rappid is `rappid:@<owner>/<slug>:<64hex>` (CONSTITUTION Art.
XXXIV.1, locked 2026-06-03). This tool migrates any deployed door off a legacy
form (v1 bare-UUID, v2-structured) onto the consolidated form, in place:

  - `rappid`        → canonicalized (legacy hash preserved; v1 UUID gets its
                      location from the repo's <owner>/<slug>).
  - `kind`          → moved into the record if it was only in a v2 string.
  - `parent_rappid` → canonicalized when it is self-locating.
  - `_migrated_from`→ the original rappid string (stamped once, audit trail).

Idempotent: re-running on an already-consolidated record is a no-op. Pure data
transform; the CLI does the file I/O. Reuses the one parser (`door_address`).

    python3 tools/migrate_rappid.py <repo_dir>          # rewrites <repo_dir>/rappid.json
    python3 tools/migrate_rappid.py <repo_dir> --check  # report only, exit 1 if stale
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from door_address import canonicalize_rappid, parse_rappid, InvalidRappidError  # noqa: E402


def migrate_record(data: dict, owner: str, slug: str) -> tuple[dict, bool]:
    """Return (migrated_record, changed). `owner`/`slug` locate the door (used
    when the rappid is a bare UUID that carries no location)."""
    out = dict(data)
    changed = False

    old = data.get("rappid")
    if isinstance(old, str) and old:
        p = parse_rappid(old)  # raises on a truly unknown form — surfaces, never silently skips
        # kind was only in a v2 string → lift it into the record
        if p.get("kind") and not out.get("kind"):
            out["kind"] = p["kind"]
            changed = True
        new = canonicalize_rappid(old, owner=owner, slug=slug)
        if new != old:
            out["rappid"] = new
            out.setdefault("_migrated_from", old)
            changed = True

    par = data.get("parent_rappid")
    if isinstance(par, str) and par:
        try:
            newp = canonicalize_rappid(par)  # parent must be self-locating already
            if newp != par:
                out["parent_rappid"] = newp
                changed = True
        except InvalidRappidError:
            pass  # bare-UUID parent without location — leave it (re-anchor separately)

    return out, changed


def migrate_file(path: str, owner: str, slug: str, check: bool) -> int:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    migrated, changed = migrate_record(data, owner, slug)
    if check:
        print(f"{'STALE' if changed else 'ok'}: {path}"
              + (f"  {data.get('rappid')} -> {migrated.get('rappid')}" if changed else ""))
        return 1 if changed else 0
    if changed:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(migrated, f, indent=2)
            f.write("\n")
        print(f"migrated: {path}  rappid={migrated.get('rappid')}")
    else:
        print(f"unchanged (already consolidated): {path}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Migrate a door's rappid.json to the consolidated rappid.")
    ap.add_argument("repo_dir", help="the door repo dir (contains rappid.json)")
    ap.add_argument("--owner", help="owner for a bare-UUID rappid (default: infer from git remote)")
    ap.add_argument("--slug", help="slug/repo for a bare-UUID rappid (default: dir name)")
    ap.add_argument("--check", action="store_true", help="report only; exit 1 if stale")
    a = ap.parse_args()
    path = os.path.join(a.repo_dir, "rappid.json")
    if not os.path.exists(path):
        print(f"no rappid.json in {a.repo_dir}", file=sys.stderr)
        return 2
    owner = a.owner or _infer_owner(a.repo_dir) or "kody-w"
    slug = a.slug or os.path.basename(os.path.abspath(a.repo_dir))
    return migrate_file(path, owner, slug, a.check)


def _infer_owner(repo_dir: str) -> str | None:
    try:
        import subprocess
        url = subprocess.run(["git", "-C", repo_dir, "remote", "get-url", "origin"],
                             capture_output=True, text=True).stdout.strip()
        # https://github.com/<owner>/<repo>(.git) or git@github.com:<owner>/<repo>
        m = url.replace("git@github.com:", "github.com/").split("github.com/")
        if len(m) > 1:
            return m[1].split("/")[0]
    except Exception:
        pass
    return None


if __name__ == "__main__":
    sys.exit(main())
