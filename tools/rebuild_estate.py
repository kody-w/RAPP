"""rebuild_estate — reconstruct an operator's estate from pure GitHub raw data.

Per the operator: "and can this be completely rebuilt by basically reading the
estate from the global githubrawuser data across this full network to basically
rebuild this data structure from scratch if we lose it... that's the point..."

This is the disaster-recovery floor for the Estate Spec (Article XLVI.6).
Given just a GitHub handle, walks public data and reconstructs:

  created[]  — every door this operator planted (filtered by parent_rappid)
  member[]   — every gate this operator joined (filtered by their rappid in members.json)

The estate file becomes provably a CACHE of facts the network already publishes,
not the source of truth. Local + published-mirror are conveniences; this tool
proves the relationships are recomputable from raw URLs.

USAGE:
    python3 tools/rebuild_estate.py --handle <gh>                # dry-run, prints
    python3 tools/rebuild_estate.py --handle <gh> --apply        # write to ~/.brainstem/estate.json
    python3 tools/rebuild_estate.py --handle <gh> --out ./estate.json
    python3 tools/rebuild_estate.py --handle <gh> --operator-rappid <rappid>
                                                                  # skip discovery, use this one

DISCOVERY:
  1. Operator rappid:
     a. Try ~/.brainstem/rappid.json locally (fast path)
     b. Try conventional repos: <handle>/<handle>-twin, <handle>/<handle>-brainstem,
        <handle>/.brainstem, <handle>/kody-twin (operator-specific patterns)
     c. Walk all <handle>/* repos via gh repo list, fetch each rappid.json,
        and accept only an exact identity whose record kind is `operator`
     d. Fail with operator-action message ("pass --operator-rappid <rappid>")

  2. created[] discovery:
     gh repo list <handle> --limit 200 → for each repo with a fetchable
     rappid.json → if parent_rappid matches operator → include it.

  3. member[] discovery:
     gh search code "<operator-rappid>" filename:members.json → for each hit,
     fetch the gate's rappid.json to get the gate's own rappid → include it.

Operator-mediated by default: default mode is dry-run; --apply writes the
file. Idempotent: safe to re-run.

Stdlib + gh CLI only.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# Add repo's tools/ to sys.path so we can import door_address
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "tools"))

from door_address import door_from_rappid, parse_rappid, InvalidRappidError, estate_url  # noqa: E402
from rapp1_core import strict_loads  # noqa: E402


def _looks_like_rappid(rappid: object) -> bool:
    """Return whether a value is an exact section 6.1 identity."""
    if not isinstance(rappid, str):
        return False
    try:
        parse_rappid(rappid)
        return True
    except InvalidRappidError:
        return False


_ESTATE_SCHEMA = "rapp-estate/1.1"
_FETCH_TIMEOUT = 8


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _gh(args: list[str]) -> tuple[int, str, str]:
    p = subprocess.run(["gh", *args], capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def _gh_get_json(path: str) -> dict | list | None:
    rc, out, _ = _gh(["api", path])
    if rc != 0:
        return None
    try:
        return json.loads(out)
    except Exception:
        return None


def _raw_fetch_json_checked(
    owner: str, repo: str, path: str
) -> tuple[dict | None, str, str]:
    """Fetch JSON while distinguishing absence/invalidity from API failure."""
    rc, output, error = _gh(["api", f"/repos/{owner}/{repo}/contents/{path}"])
    if rc != 0:
        if "HTTP 404" in error or "not found" in error.lower():
            return None, "missing", "file not found"
        return None, "error", f"GitHub API fetch failed: {error.strip()[:160]}"
    try:
        response = json.loads(output)
        if type(response) is not dict:
            raise TypeError("content response is not an object")
        encoded = response.get("content")
        if type(encoded) is not str:
            raise ValueError("content response has no base64 text")
        if not encoded and response.get("size") != 0:
            raise ValueError("content response has no base64 text")
        body = (
            base64.b64decode(encoded.replace("\n", ""), validate=True)
            if encoded
            else b""
        )
    except (TypeError, ValueError) as exc:
        return None, "error", f"GitHub content response invalid: {exc}"
    try:
        value = strict_loads(body)
        if type(value) is not dict:
            return None, "invalid", "JSON file is not an object"
        return value, "ok", ""
    except (TypeError, ValueError) as exc:
        return None, "invalid", f"invalid JSON file: {exc}"


def _raw_fetch_json(owner: str, repo: str, path: str) -> dict | None:
    """Compatibility wrapper for best-effort operator identity probes."""
    value, status, _ = _raw_fetch_json_checked(owner, repo, path)
    return value if status == "ok" else None


# ─── Operator-rappid discovery ────────────────────────────────────────────

def _try_local_brainstem(handle: str) -> str:
    """If running on the operator's machine, ~/.brainstem/rappid.json is the
    fastest path. Returns "" if not present or malformed."""
    p = Path(os.path.expanduser("~/.brainstem/rappid.json"))
    if not p.exists():
        return ""
    try:
        d = strict_loads(p.read_bytes())
        if type(d) is not dict:
            return ""
        rappid = d.get("rappid", "")
        door = door_from_rappid(rappid, identity_record=d)
        if door["kind"] == "operator" and door["owner"] == handle:
            return rappid
    except (InvalidRappidError, OSError, ValueError):
        pass
    return ""


def _try_conventional_repos(handle: str) -> str:
    """Probe conventional anchor repos for a record-declared operator rappid."""
    candidates = [
        f"{handle}-twin",
        f"{handle}-brainstem",
        ".brainstem",
        "kody-twin",   # legacy convention used by this codebase's operator
    ]
    for repo in candidates:
        d = _raw_fetch_json(handle, repo, "rappid.json")
        if not d:
            continue
        rappid = d.get("rappid", "")
        if not _looks_like_rappid(rappid):
            continue
        try:
            door = door_from_rappid(rappid, identity_record=d)
        except InvalidRappidError:
            continue
        if (
            door["kind"] == "operator"
            and door["owner"] == handle
            and door["slug"] == repo.lower()
        ):
            return rappid
    return ""


def _scan_handle_for_operator(handle: str) -> str:
    """Last-ditch: walk every repo for a record-declared operator identity."""
    repos = _gh_get_json(f"/users/{handle}/repos?per_page=100&type=owner")
    if not isinstance(repos, list):
        return ""
    for r in repos:
        if not isinstance(r, dict) or r.get("fork"):
            continue
        name = r.get("name", "")
        if not name:
            continue
        d = _raw_fetch_json(handle, name, "rappid.json")
        if not d:
            continue
        rappid = d.get("rappid", "")
        if not isinstance(rappid, str):
            continue
        try:
            door = door_from_rappid(rappid, identity_record=d)
        except InvalidRappidError:
            continue
        if (
            door["kind"] == "operator"
            and door["owner"] == handle
            and door["slug"] == name.lower()
        ):
            return rappid
    return ""


def discover_operator_rappid(handle: str) -> str:
    """Try every discovery path in order. Returns "" if none succeed."""
    for fn in (lambda: _try_local_brainstem(handle),
               lambda: _try_conventional_repos(handle),
               lambda: _scan_handle_for_operator(handle)):
        rappid = fn()
        if rappid:
            try:
                door = door_from_rappid(rappid)
                if door["owner"] == handle:
                    return rappid
            except InvalidRappidError:
                continue
    return ""


# ─── created[] discovery ──────────────────────────────────────────────────

def _list_handle_repos(handle: str) -> tuple[list, list[str]]:
    """List all repos owned by handle. If handle matches the gh-authenticated
    user, uses /user/repos to include private repos too (operator-self path).
    Otherwise falls back to public-only /users/<handle>/repos.

    The second return value reports fatal/incomplete discovery. A valid empty
    response is ``([], [])`` and must not be conflated with an API failure.
    """
    auth_user = _gh_get_json("/user") or {}
    self_path = isinstance(auth_user, dict) and auth_user.get("login") == handle
    api_path = ("/user/repos?per_page=100&affiliation=owner"
                if self_path else
                f"/users/{handle}/repos?per_page=100&type=owner")
    rc, out, err = _gh(["api", "--paginate", api_path])
    if rc != 0:
        return [], [f"repository listing failed: {err.strip()[:160]}"]
    # --paginate concatenates JSON arrays; parse them as a stream
    repos: list = []
    decoder = json.JSONDecoder()
    s = out.strip()
    if not s:
        return [], ["repository listing response was empty"]
    pos = 0
    try:
        while pos < len(s):
            s_remaining = s[pos:].lstrip()
            if not s_remaining:
                break
            leading_ws = len(s) - pos - len(s_remaining)
            obj, end = decoder.raw_decode(s_remaining)
            if type(obj) is not list:
                raise ValueError("repository page is not a JSON array")
            # When using /user/repos, we may see repos owned by other accounts
            # the operator collaborates on — filter to only handle's repos.
            for r in obj:
                if type(r) is not dict or type(r.get("owner")) is not dict:
                    raise ValueError("repository entry is not an object with an owner")
                rowner = r["owner"].get("login")
                if type(rowner) is not str:
                    raise ValueError("repository owner login is not a string")
                if rowner.lower() == handle:
                    repos.append(r)
            pos += leading_ws + end
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return [], [f"repository listing response invalid: {exc}"]
    return repos, []


def discover_created(
    handle: str, operator_rappid: str, on_progress=None
) -> tuple[list, list, list[str]]:
    """Walk handle's repos; return entries, ordinary skips, and fatal errors."""
    repos, discovery_errors = _list_handle_repos(handle)
    if discovery_errors:
        return [], [], discovery_errors
    created = []
    skipped = []
    fetch_errors = []
    for r in repos:
        if not isinstance(r, dict) or r.get("fork"):
            continue
        name = r.get("name", "")
        if not name:
            continue
        if on_progress:
            on_progress(f"checking {handle}/{name}")
        d, fetch_status, fetch_detail = _raw_fetch_json_checked(
            handle, name, "rappid.json"
        )
        if fetch_status == "error":
            fetch_errors.append(
                {"repo": name, "path": "rappid.json", "error": fetch_detail}
            )
            continue
        if d is None:
            skipped.append(
                {
                    "repo": name,
                    "reason": (
                        "no rappid.json"
                        if fetch_status == "missing"
                        else fetch_detail
                    ),
                }
            )
            continue
        rappid = d.get("rappid", "")
        if not isinstance(rappid, str):
            skipped.append({"repo": name, "reason": "rappid not a string"})
            continue
        try:
            door = door_from_rappid(rappid, identity_record=d)
        except InvalidRappidError as e:
            skipped.append({"repo": name, "reason": f"invalid rappid: {str(e)[:80]}"})
            continue
        if door["owner"] != handle or door["slug"] != name.lower():
            skipped.append(
                {
                    "repo": name,
                    "reason": "rappid owner/slug does not match source repository",
                }
            )
            continue
        if d.get("parent_rappid") != operator_rappid:
            skipped.append({"repo": name, "reason": "parent_rappid does not match operator"})
            continue
        created.append({
            "rappid":   rappid,
            "added_at": _now_iso(),
            "via":      "rebuild",
        })
    return (
        created,
        skipped,
        [
            "one or more repository identity fetches failed: "
            + json.dumps(fetch_errors, sort_keys=True)
        ]
        if fetch_errors
        else [],
    )


# ─── member[] discovery ───────────────────────────────────────────────────

def discover_memberships(
    operator_rappid: str, on_progress=None
) -> tuple[list, list, list[str]]:
    """Use gh search code to find every members.json containing the operator
    rappid. Each hit is a gate the operator is a member of."""
    rc, out, err = _gh(["search", "code", operator_rappid, "filename:members.json",
                        "--limit", "100", "--json", "repository,path"])
    if rc != 0:
        return [], [], [f"GitHub code search failed: {err.strip()[:200]}"]
    try:
        if not out.strip():
            raise ValueError("response was empty")
        hits = json.loads(out)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return [], [], [f"GitHub code search response invalid: {exc}"]
    if type(hits) is not list:
        return [], [], [
            f"unexpected GitHub code search shape: {type(hits).__name__}"
        ]
    member = []
    skipped = []
    fetch_errors = []
    seen = set()
    for hit in hits:
        if not isinstance(hit, dict):
            fetch_errors.append({"repo": None, "error": "invalid code-search hit"})
            continue
        repo_obj = hit.get("repository", {}) or {}
        if type(repo_obj) is not dict:
            fetch_errors.append(
                {"repo": None, "error": "code-search repository is not an object"}
            )
            continue
        full = repo_obj.get("nameWithOwner") or repo_obj.get("name", "")
        if not full or "/" not in full:
            fetch_errors.append(
                {"repo": None, "error": "code-search hit has no repository"}
            )
            continue
        if full in seen:
            continue
        seen.add(full)
        owner, repo = full.split("/", 1)
        if on_progress:
            on_progress(f"checking gate {owner}/{repo}")
        # Verify the operator is actually listed in members.json (not just
        # mentioned somewhere in the file body — code search matches anywhere)
        members, members_status, members_detail = _raw_fetch_json_checked(
            owner, repo, "members.json"
        )
        if members_status == "error":
            fetch_errors.append(
                {"repo": full, "path": "members.json", "error": members_detail}
            )
            continue
        if not isinstance(members, dict):
            skipped.append(
                {
                    "repo": full,
                    "reason": (
                        "members.json disappeared after code search"
                        if members_status == "missing"
                        else members_detail
                    ),
                }
            )
            continue
        listed = any(
            isinstance(m, dict) and m.get("rappid") == operator_rappid
            for m in members.get("members", [])
        )
        if not listed:
            skipped.append({"repo": full, "reason": "operator not in members[] (substring match only)"})
            continue
        # Get the gate's own rappid
        gate_meta, gate_status, gate_detail = _raw_fetch_json_checked(
            owner, repo, "rappid.json"
        )
        if gate_status == "error":
            fetch_errors.append(
                {"repo": full, "path": "rappid.json", "error": gate_detail}
            )
            continue
        if not isinstance(gate_meta, dict):
            skipped.append(
                {
                    "repo": full,
                    "reason": (
                        "gate has no rappid.json"
                        if gate_status == "missing"
                        else gate_detail
                    ),
                }
            )
            continue
        gate_rappid = gate_meta.get("rappid", "")
        if not isinstance(gate_rappid, str):
            continue
        try:
            gate_door = door_from_rappid(
                gate_rappid, identity_record=gate_meta
            )
        except InvalidRappidError as e:
            skipped.append({"repo": full, "reason": f"gate rappid invalid: {str(e)[:60]}"})
            continue
        if (
            gate_door["owner"] != owner.lower()
            or gate_door["slug"] != repo.lower()
        ):
            skipped.append(
                {
                    "repo": full,
                    "reason": "gate rappid does not match source repository",
                }
            )
            continue
        member.append({
            "rappid":   gate_rappid,
            "added_at": _now_iso(),
            "via":      "rebuild",
        })
    return (
        member,
        skipped,
        [
            "one or more code-search result fetches failed: "
            + json.dumps(fetch_errors, sort_keys=True)
        ]
        if fetch_errors
        else [],
    )


# ─── Estate assembly ──────────────────────────────────────────────────────

def rebuild(handle: str, operator_rappid: str = "", on_progress=None) -> dict:
    """Top-level: discover operator, walk created/member, return spec-compliant estate."""
    try:
        estate_url(handle)
    except InvalidRappidError as exc:
        return {
            "schema": _ESTATE_SCHEMA,
            "ok": False,
            "error": f"invalid exact handle: {exc}",
        }
    if not operator_rappid:
        if on_progress:
            on_progress("discovering operator rappid…")
        operator_rappid = discover_operator_rappid(handle)
        if not operator_rappid:
            return {
                "schema": _ESTATE_SCHEMA, "ok": False,
                "error": (
                    f"could not discover operator rappid for {handle}. "
                    f"Pass --operator-rappid explicitly. The conventional anchors "
                    f"(<handle>-twin, <handle>-brainstem, .brainstem, kody-twin) "
                    f"and a full repo scan all came up empty."
                ),
            }
    # Validate one more time
    try:
        operator_door = door_from_rappid(operator_rappid)
    except InvalidRappidError as e:
        return {"schema": _ESTATE_SCHEMA, "ok": False,
                "error": f"operator rappid invalid: {e}"}
    if operator_door["owner"] != handle:
        return {
            "schema": _ESTATE_SCHEMA,
            "ok": False,
            "error": (
                "operator rappid owner does not match requested GitHub handle"
            ),
        }

    if on_progress:
        on_progress("walking handle's repos for created[]…")
    created, created_skipped, created_errors = discover_created(
        handle, operator_rappid, on_progress
    )
    if created_errors:
        return {
            "schema": _ESTATE_SCHEMA,
            "ok": False,
            "status": "DISCOVERY_INCOMPLETE",
            "phase": "repository-listing",
            "error": "GitHub repository discovery was incomplete; refusing rebuild",
            "discovery_errors": created_errors,
            "apply_permitted": False,
            "recovery": (
                "Restore GitHub API access, rerun without --apply, and inspect "
                "a complete plan before replacing any estate file."
            ),
        }

    if on_progress:
        on_progress("searching for memberships in members.json files…")
    member, member_skipped, member_errors = discover_memberships(
        operator_rappid, on_progress
    )
    if member_errors:
        return {
            "schema": _ESTATE_SCHEMA,
            "ok": False,
            "status": "DISCOVERY_INCOMPLETE",
            "phase": "code-search",
            "error": "GitHub membership discovery was incomplete; refusing rebuild",
            "discovery_errors": member_errors,
            "apply_permitted": False,
            "partial_discovery": {
                "created": created,
                "created_skipped": created_skipped,
            },
            "recovery": (
                "Restore GitHub code-search access, rerun without --apply, and "
                "inspect a complete plan before replacing any estate file."
            ),
        }

    return {
        "schema": _ESTATE_SCHEMA,
        "ok": True,
        "owner": {"rappid": operator_rappid, "github": handle},
        "created": created,
        "member":  member,
        "updated_at": _now_iso(),
        "_rebuild": {
            "tool":              "tools/rebuild_estate.py",
            "operator_rappid":   operator_rappid,
            "created_count":     len(created),
            "member_count":      len(member),
            "created_skipped":   created_skipped,
            "member_skipped":    member_skipped,
            "rebuilt_at":        _now_iso(),
            "public_url":        estate_url(handle),
        },
    }


# ─── CLI ──────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--handle", required=True, help="GitHub handle to rebuild estate for")
    ap.add_argument("--operator-rappid", default="",
                    help="skip operator discovery; use this rappid as the operator's identity")
    ap.add_argument("--out", default="",
                    help="write estate.json here (default: print only — i.e. dry-run)")
    ap.add_argument("--apply", action="store_true",
                    help="write to ~/.brainstem/estate.json (overrides --out)")
    args = ap.parse_args()

    def _progress(msg: str) -> None:
        print(f"  · {msg}", file=sys.stderr)

    estate = rebuild(args.handle, args.operator_rappid, on_progress=_progress)

    # Strip the rebuild metadata if we're writing to a real estate file
    write_path = ""
    if args.apply:
        write_path = os.path.expanduser("~/.brainstem/estate.json")
    elif args.out:
        write_path = os.path.expanduser(args.out)

    if write_path and estate.get("ok"):
        clean = {k: v for k, v in estate.items() if k not in ("ok", "_rebuild")}
        os.makedirs(os.path.dirname(write_path), exist_ok=True)
        Path(write_path).write_text(json.dumps(clean, indent=2))
        estate["_rebuild"]["wrote_to"] = write_path

    print(json.dumps(estate, indent=2))
    return 0 if estate.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
