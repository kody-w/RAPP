"""private_estate_init — bootstrap an Article-XLVIII-compliant private estate.

Authority: pages/docs/PUBLIC_PRIVATE_BOUNDARY.md + CONSTITUTION Article XLVIII.

Creates `<handle>/rapp-estate-private` as a PRIVATE GitHub repo, mints a
per-operator HMAC secret (stored ONLY at ~/.brainstem/private-estate-secret,
mode 0600), and scaffolds the opaque file set:

    meta.json         ← schema + index pointer (rapp-private-estate/1.0)
    README.md         ← "see operator's local brainstem map"
    objects/.gitkeep  ← content-addressed storage placeholder
    kinds/.gitkeep    ← HMAC'd kind/id storage placeholder

Idempotent: safe to re-run. Skips repo creation if it exists; refreshes
meta.json + README; never touches the secret if one already exists.

USAGE:
    python3 tools/private_estate_init.py --handle <gh>
    python3 tools/private_estate_init.py --handle <gh> --verify-commitment
    python3 tools/private_estate_init.py --handle <gh> --dry-run

NEVER prints the HMAC secret. NEVER includes it in commits, beacons, or
any other output. Article XLVIII.6 enforced.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "tools"))

from path_opacity import OPACITY_REGEX, audit_paths  # noqa: E402
from rapp1_core import parse_rappid, strict_loads  # noqa: E402
from rapp1_core.errors import IdentityError  # noqa: E402
from rapp1_core.identity import validate_owner  # noqa: E402


_SCHEMA = "rapp-private-estate/1.0"
_SECRET_PATH = Path(os.path.expanduser("~/.brainstem/private-estate-secret"))
_LOCAL_MAP_PATH = Path(os.path.expanduser("~/.brainstem/private-estate-map.json"))


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _gh(args: list[str]) -> tuple[int, str, str]:
    p = subprocess.run(["gh", *args], capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def _ensure_secret() -> bytes:
    """Mint or load the per-operator HMAC secret. Stored at file mode 0600
    so other users on the system can't read it. Article XLVIII.6 keys-to-the-kingdom.
    """
    _SECRET_PATH.parent.mkdir(parents=True, exist_ok=True)
    if _SECRET_PATH.exists():
        secret = _SECRET_PATH.read_bytes()
        if len(secret) >= 16:
            return secret
        # Existing secret is too short — rotate (rare; only happens if file was tampered)
    secret = secrets.token_bytes(32)
    _SECRET_PATH.write_bytes(secret)
    try:
        os.chmod(_SECRET_PATH, 0o600)
    except OSError:
        pass  # best-effort; some filesystems don't support chmod
    return secret


def _ensure_local_map() -> dict:
    """Load or initialize the operator's local map. The map records
    human-readable kind/id ↔ opaque token mappings. Encrypted-at-rest
    in a future round; cleartext in Round 1 (the file lives only in
    ~/.brainstem/ which is the operator's home).
    """
    if _LOCAL_MAP_PATH.exists():
        try:
            return json.loads(_LOCAL_MAP_PATH.read_text())
        except Exception:
            pass
    return {
        "schema": "rapp-private-estate-localmap/1.0",
        "_note": "Local map ↔ opaque tokens. NEVER published. Lives only on the operator's machine.",
        "kinds": [],
        "ids":   {},  # kind → list[id]
        "updated_at": _now_iso(),
    }


def _save_local_map(m: dict) -> None:
    _LOCAL_MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    m["updated_at"] = _now_iso()
    _LOCAL_MAP_PATH.write_text(json.dumps(m, indent=2))
    try:
        os.chmod(_LOCAL_MAP_PATH, 0o600)
    except OSError:
        pass


# ─── private repo scaffold ────────────────────────────────────────────────

def _build_meta_json(operator_rappid: str, github_handle: str) -> bytes:
    """The single well-known content-free file in the private repo. Safe to
    expose because it carries no semantic information.
    """
    return (json.dumps({
        "schema": _SCHEMA,
        "owner": {
            "rappid": operator_rappid,
            "github": github_handle,
        },
        "private_door_count": 0,
        "kinds": {},          # populated as kinds get used
        "objects_count": 0,
        "kinds_count": 0,
        "updated_at": _now_iso(),
        "_note": (
            "Article XLVIII.6: semantic kind/id mappings live ONLY in the operator's "
            "local map at ~/.brainstem/private-estate-map.json. This meta.json carries "
            "no content; its purpose is operator-side index navigation."
        ),
    }, indent=2) + "\n").encode()


def _build_readme(github_handle: str) -> bytes:
    return (
        f"# {github_handle}/rapp-estate-private\n\n"
        f"This is the **private tier** of `{github_handle}`'s RAPP estate (CONSTITUTION Article XLVIII).\n\n"
        f"## Why this repo is private\n\n"
        f"The RAPP network's discovery surface is public (`{github_handle}/rapp-estate`). This repo holds the *substance* — PII, contacts, mailbox content, conversation history, private trust signals — anything that should not be publicly indexable.\n\n"
        f"## Why every path here is opaque\n\n"
        f"Per **Article XLVIII.6 (URL Opacity)**, every path inside this repo carries zero semantic information. A 404 on any path here reveals nothing about what would have been there.\n\n"
        f"- `meta.json` — schema + index pointer (content-free)\n"
        f"- `README.md` — this file\n"
        f"- `objects/<sha256>.json` — content-addressed artifacts\n"
        f"- `kinds/<HMAC>/<HMAC>.json` — kind/id pairs hashed with the operator's HMAC secret\n\n"
        f"## How to navigate\n\n"
        f"The human-readable mapping (kind+id ↔ opaque token) lives ONLY in the operator's local brainstem at `~/.brainstem/private-estate-map.json`. Without that map (or the operator's HMAC secret), the structure of this repo is uniformly meaningless.\n\n"
        f"## Spec\n\n"
        f"Authoritative spec: [PUBLIC_PRIVATE_BOUNDARY.md](https://raw.githubusercontent.com/kody-w/RAPP/main/pages/docs/PUBLIC_PRIVATE_BOUNDARY.md).\n\n"
        f"Constitutional anchor: [Article XLVIII](https://raw.githubusercontent.com/kody-w/RAPP/main/CONSTITUTION.md).\n\n"
        f"---\n"
        f"*Created at {_now_iso()} by `tools/private_estate_init.py`.*\n"
    ).encode()


def _load_operator_identity(path: Path, expected_owner: str) -> tuple[str, str]:
    value = strict_loads(path.read_bytes())
    if type(value) is not dict:
        raise ValueError("operator identity record must be an object")
    rappid = value.get("rappid")
    parsed = parse_rappid(rappid)
    if parsed.owner != expected_owner:
        raise ValueError(
            "operator identity owner does not match requested GitHub handle"
        )
    kind = value.get("kind")
    if kind != "operator":
        raise ValueError("operator identity record kind must be 'operator'")
    return str(parsed), kind


def _normalized_state_hash(meta_bytes: bytes, file_paths: list[str]) -> str:
    """Compute the private estate's commitment hash.

    Hashes the sorted list of opaque paths + the meta.json bytes. Empty
    estate (no objects, no kinds) has a stable hash that becomes the
    operator's first commitment. Anyone with read access can recompute
    and verify the operator hasn't substituted a different private
    estate behind their back.
    """
    h = hashlib.sha256()
    h.update(b"rapp-private-estate-commitment/1.0\n")
    h.update(meta_bytes)
    h.update(b"\n--paths--\n")
    for p in sorted(file_paths):
        h.update(p.encode("utf-8") + b"\n")
    return h.hexdigest()


def _gh_repo_exists(slug: str) -> bool:
    rc, _, _ = _gh(["repo", "view", slug])
    return rc == 0


def _gh_create_private(slug: str, description: str) -> tuple[bool, str]:
    rc, out, err = _gh(["repo", "create", slug, "--private", "--description", description])
    if rc == 0:
        return True, out.strip() or f"https://github.com/{slug}"
    return False, err.strip()[:300]


def _gh_put_file(slug: str, path: str, content_bytes: bytes, message: str) -> tuple[bool, str]:
    """Idempotent PUT — looks up existing sha so updates work."""
    full = f"/repos/{slug}/contents/{path}"
    rc_get, out_get, _ = _gh(["api", full])
    sha_args: list[str] = []
    if rc_get == 0:
        try:
            sha = json.loads(out_get).get("sha", "")
            if sha:
                sha_args = ["-f", f"sha={sha}"]
        except Exception:
            pass
    b64 = base64.b64encode(content_bytes).decode("ascii")
    rc_put, _, err = _gh([
        "api", "-X", "PUT", full,
        "-f", f"message={message}",
        "-f", f"content={b64}",
        *sha_args,
    ])
    if rc_put == 0:
        return True, f"wrote {path} ({len(content_bytes)}B)"
    return False, f"PUT failed: {err.strip()[:160]}"


def _gh_read_file(slug: str, path: str) -> tuple[bool, bytes | None, str]:
    rc, output, error = _gh(["api", f"/repos/{slug}/contents/{path}"])
    if rc != 0:
        return False, None, f"verification GET failed: {error.strip()[:160]}"
    try:
        response = json.loads(output)
        if type(response) is not dict:
            raise ValueError("content response is not an object")
        encoded = response.get("content")
        if type(encoded) is not str:
            raise ValueError("content response does not contain base64 text")
        encoded = encoded.replace("\n", "")
        if not encoded and response.get("size") != 0:
            raise ValueError("content response has no bytes")
        content = base64.b64decode(encoded, validate=True) if encoded else b""
    except (TypeError, ValueError) as exc:
        return False, None, f"verification response invalid: {exc}"
    return True, content, "verified"


def _remote_failure(
    *,
    slug: str,
    repo_created: bool,
    results: list[dict],
    status: str,
    error: str,
    verification_failures: list[dict] | None = None,
) -> dict:
    successful = [result for result in results if result.get("ok")]
    failed = [result for result in results if not result.get("ok")]
    return {
        "ok": False,
        "schema": "rapp-private-estate-init-failure/1.0",
        "status": status,
        "error": error,
        "publish_permitted": False,
        "repo_url": f"https://github.com/{slug}",
        "repo_created": repo_created,
        "partial_remote_writes": successful,
        "files_failed": failed,
        "verification_failures": verification_failures or [],
        "recovery": (
            "Inspect the private repository, repair or remove every reported "
            "partial write, verify all scaffold bytes, then rerun initialization. "
            "Do not publish a private-estate commitment or beacon pointer."
        ),
    }


def _gh_list_tree_checked(slug: str) -> tuple[bool, list[str], str]:
    rc, output, error = _gh(
        ["api", f"/repos/{slug}/git/trees/main?recursive=1"]
    )
    if rc != 0:
        return False, [], f"tree verification failed: {error.strip()[:160]}"
    try:
        response = json.loads(output)
        if type(response) is not dict or type(response.get("tree")) is not list:
            raise ValueError("tree response is not an object with a tree")
        paths = [
            item["path"]
            for item in response["tree"]
            if type(item) is dict
            and item.get("type") == "blob"
            and type(item.get("path")) is str
        ]
    except (TypeError, ValueError) as exc:
        return False, [], f"tree verification response invalid: {exc}"
    return True, paths, "verified"


def _gh_list_tree(slug: str) -> list[str]:
    """Return the list of file paths in the repo's main branch tree."""
    verified, paths, _ = _gh_list_tree_checked(slug)
    return paths if verified else []


# ─── Top-level init ──────────────────────────────────────────────────────

def init_private_estate(github_handle: str, dry_run: bool = False) -> dict:
    """Bootstrap the private estate for `github_handle`.

    Idempotent. Returns an envelope with the repo URL + commitment hash.
    """
    try:
        github_handle = validate_owner(github_handle)
    except (IdentityError, TypeError) as exc:
        return {"ok": False, "error": f"invalid exact owner: {exc}"}
    slug = f"{github_handle}/rapp-estate-private"

    rappid_path = Path(os.path.expanduser("~/.brainstem/rappid.json"))
    try:
        operator_rappid, operator_kind = _load_operator_identity(
            rappid_path, github_handle
        )
    except (IdentityError, OSError, TypeError, ValueError) as exc:
        return {
            "ok": False,
            "error": f"exact operator identity required before initialization: {exc}",
        }

    secret_present = _SECRET_PATH.exists()

    # 3. Create the repo if missing
    repo_created = False
    if not _gh_repo_exists(slug):
        if dry_run:
            return {
                "ok": True, "dry_run": True,
                "would_create": slug, "private": True,
                "secret_present": secret_present,
                "operator_rappid": operator_rappid,
                "operator_kind": operator_kind,
                "next_step": f"re-run without --dry-run to create {slug} as PRIVATE",
            }
        ok, msg = _gh_create_private(slug, f"{github_handle}'s RAPP private estate (Article XLVIII)")
        if not ok:
            return {"ok": False, "error": f"gh repo create failed: {msg}"}
        repo_created = True

    # 4. Build the scaffold files (deterministic; same content on idempotent re-run)
    meta_bytes = _build_meta_json(operator_rappid, github_handle)
    readme_bytes = _build_readme(github_handle)

    files: dict[str, bytes] = {
        "meta.json":         meta_bytes,
        "README.md":         readme_bytes,
        "objects/.gitkeep":  b"",
        "kinds/.gitkeep":    b"",
    }

    # 5. Verify all paths are opaque (paranoid self-check)
    violations = audit_paths(list(files.keys()))
    if violations:
        return {"ok": False, "error": f"INTERNAL: scaffold paths violate Article XLVIII.6: {violations}"}

    if dry_run:
        return {
            "ok": True, "dry_run": True,
            "would_write": sorted(files.keys()),
            "secret_present": secret_present,
            "operator_rappid": operator_rappid,
            "operator_kind": operator_kind,
        }

    # 6. PUT each file
    results: list[dict] = []
    for path, body in files.items():
        ok, msg = _gh_put_file(slug, path, body,
                                f"private-estate-init: scaffold {path} (Article XLVIII)")
        results.append({"path": path, "ok": ok, "msg": msg})
        if not ok:
            return _remote_failure(
                slug=slug,
                repo_created=repo_created,
                results=results,
                status=(
                    "PARTIAL_REMOTE_WRITE"
                    if repo_created or any(row["ok"] for row in results)
                    else "REMOTE_WRITE_FAILED"
                ),
                error=f"GitHub PUT failed for {path}: {msg}",
            )

    verification_failures: list[dict] = []
    for path, expected in files.items():
        verified, remote_bytes, detail = _gh_read_file(slug, path)
        if not verified or remote_bytes != expected:
            verification_failures.append(
                {
                    "path": path,
                    "error": (
                        detail
                        if not verified
                        else "remote bytes do not match the requested write"
                    ),
                }
            )
    if verification_failures:
        return _remote_failure(
            slug=slug,
            repo_created=repo_created,
            results=results,
            status="REMOTE_VERIFICATION_FAILED",
            error="one or more GitHub PUTs could not be verified",
            verification_failures=verification_failures,
        )

    tree_verified, tree, tree_detail = _gh_list_tree_checked(slug)
    missing_paths = sorted(set(files) - set(tree))
    if not tree_verified or missing_paths:
        return _remote_failure(
            slug=slug,
            repo_created=repo_created,
            results=results,
            status="REMOTE_VERIFICATION_FAILED",
            error=(
                tree_detail
                if not tree_verified
                else f"verified tree is missing scaffold paths: {missing_paths}"
            ),
        )

    # 7. Initialize local state only after every remote write verifies.
    try:
        _ensure_secret()
        local_map = _ensure_local_map()
        _save_local_map(local_map)
    except OSError as exc:
        return _remote_failure(
            slug=slug,
            repo_created=repo_created,
            results=results,
            status="LOCAL_STATE_FAILED",
            error=f"remote scaffold verified but local state failed: {exc}",
        )

    # 8. Compute a commitment only after remote and local state are complete.
    commitment = _normalized_state_hash(meta_bytes, tree)

    return {
        "ok": True,
        "schema": "rapp-private-estate-init-result/1.0",
        "github": github_handle,
        "slug": slug,
        "repo_url": f"https://github.com/{slug}",
        "private": True,
        "repo_created": repo_created,
        "files_written": [r for r in results if r["ok"]],
        "files_failed":  [r for r in results if not r["ok"]],
        "private_estate_commitment": commitment,
        "private_door_count": 0,
        "secret_present": True,
        "local_map_path": str(_LOCAL_MAP_PATH),
        "operator_rappid": operator_rappid,
        "operator_kind": operator_kind,
        "next_step": (
            f"Beacon should be updated with private_estate_pointer=https://github.com/{slug}, "
            f"private_estate_commitment={commitment[:16]}…, private_door_count=0. "
            "Re-run estate_agent.publish to refresh."
        ),
    }


def verify_commitment(github_handle: str) -> dict:
    """Re-compute the commitment hash from the live private repo state +
    compare to the published beacon. Operator-side audit tool."""
    import urllib.request

    slug = f"{github_handle}/rapp-estate-private"
    if not _gh_repo_exists(slug):
        return {"ok": False, "error": f"{slug} doesn't exist"}

    # Fetch meta.json via gh api (auth required; this is operator-side)
    rc, out, _ = _gh(["api", f"/repos/{slug}/contents/meta.json"])
    if rc != 0:
        return {"ok": False, "error": f"could not fetch meta.json from {slug}"}
    try:
        d = json.loads(out)
        meta_bytes = base64.b64decode(d["content"].replace("\n", ""))
    except Exception as e:
        return {"ok": False, "error": f"meta.json malformed: {e}"}

    tree = _gh_list_tree(slug)
    computed = _normalized_state_hash(meta_bytes, tree)

    # Fetch published beacon (raw — public)
    beacon_url = f"https://raw.githubusercontent.com/{github_handle}/rapp-estate/main/.well-known/rapp-network.json"
    try:
        with urllib.request.urlopen(beacon_url, timeout=8) as r:
            beacon = json.loads(r.read())
        published = beacon.get("private_estate_commitment", "")
    except Exception as e:
        return {"ok": False, "error": f"could not fetch public beacon: {e}",
                "computed_commitment": computed}

    matches = published == computed
    return {
        "ok": matches,
        "computed_commitment": computed,
        "published_commitment": published,
        "matches": matches,
        "diagnosis": ("OK — published commitment matches live private state"
                       if matches else
                       "DRIFT — published commitment is stale; re-run estate_agent.publish"),
    }


# ─── CLI ──────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--handle", required=True, help="GitHub handle to bootstrap private estate for")
    ap.add_argument("--dry-run", action="store_true", help="report planned actions; do not write")
    ap.add_argument("--verify-commitment", action="store_true",
                    help="recompute commitment hash + compare to published beacon")
    args = ap.parse_args()

    if args.verify_commitment:
        out = verify_commitment(args.handle)
    else:
        out = init_private_estate(args.handle, dry_run=args.dry_run)

    print(json.dumps(out, indent=2))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
