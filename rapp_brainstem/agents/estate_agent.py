"""estate_agent — local-first RAPP estate (single JSON file).

Per the operator: "make it local first import export json so I can back up
my estate, that is loaded into the application from the github raw user
data based api that is globally available."

ONE file: ~/.brainstem/estate.json — the canonical inventory of every
neighborhood + twin you've planted (created/) and every neighborhood you
joined as a contributor (member/). The user's personal rappid is the
universal anchor: ancestor for things they created, member-proof for
things they didn't.

Local is the source of truth. The public mirror at
    https://raw.githubusercontent.com/<user>/rapp-estate/main/estate.json
is just a published copy — globally available via GitHub's CDN, no auth,
no rate limits for public reads.

Per CONSTITUTION Article XLVI (the Estate Spec — see pages/docs/ESTATE_SPEC.md
and specs/SPEC.md §4): each entry stores ONLY {rappid, added_at, via}.
Owner, repo, kind, door_type, summon URL, holocard URL — every other field —
is DERIVED at read time via tools/door_address.py::door_from_rappid().
There are no fallbacks. If a rappid is invalid, the entry surfaces as an
error rather than being silently fixed up.

Actions (all operator-mediated):
    show     — print the current local estate (with derived doors view)
    export   — write the local estate to a path (for backup / sharing)
    import   — load a JSON file into the local estate (replace or merge)
    publish  — push the local estate to <user>/rapp-estate (gh api)
    fetch    — read someone else's published estate via raw.githubusercontent.com
    add      — append an entry by rappid (the only required field)
    remove   — drop an entry by rappid
    scan     — walk the operator's GitHub repos and add doors with rappid.json

Schema: `rapp-estate/1.1`. No cron, no workflow, no directory-of-files.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

try:
    from agents.basic_agent import BasicAgent
except ImportError:
    from basic_agent import BasicAgent


__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "estate",
    "kind": "agent",
    "summary": "Local-first RAPP estate as a single JSON file (import / export / publish / fetch / scan).",
    "tags": ["estate", "lineage", "rappid", "backup", "local-first", "article-xlvi"],
}


_ESTATE_SCHEMA = "rapp-estate/1.1"
_ESTATE_FILE = Path(os.path.expanduser("~/.brainstem/estate.json"))
_RAPPID_FILE = Path(os.path.expanduser("~/.brainstem/rappid.json"))
_RAW_URL_TEMPLATE = "https://raw.githubusercontent.com/{user}/rapp-estate/main/estate.json"
_FETCH_TIMEOUT = 8


# ─── Import door_from_rappid from tools/ (no fallback parser) ─────────────
# The single derivation function for the entire codebase. Per Article XLVI:
# per-consumer rappid parsers are forbidden.

def _import_door_address():
    """Return tools.door_address module by walking up to find tools/."""
    here = os.path.abspath(__file__)
    for cand in (
        # rapp_brainstem/agents/ → repo_root/tools/
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(here))), "tools"),
        # rapp_brainstem/ → repo_root/tools/  (alternate layout depth)
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(here)))), "tools"),
    ):
        if os.path.isfile(os.path.join(cand, "door_address.py")):
            if cand not in sys.path:
                sys.path.insert(0, cand)
            import door_address
            return door_address
    raise ImportError(
        "tools/door_address.py not found. The estate agent requires the canonical "
        "door_from_rappid() implementation; per Article XLVI per-consumer parsers "
        "are forbidden."
    )


_door_address = _import_door_address()
door_from_rappid = _door_address.door_from_rappid
InvalidRappidError = _door_address.InvalidRappidError
estate_url = _door_address.estate_url


# ─── Local file I/O ───────────────────────────────────────────────────────

def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _read_local_rappid() -> tuple[str, str]:
    """Return (rappid, github_handle) of the operator from ~/.brainstem/rappid.json.

    The github handle comes from the rappid's @<owner>/<repo> segment via
    door_from_rappid — no string-fishing fallback.
    """
    if not _RAPPID_FILE.exists():
        return "", ""
    try:
        d = json.loads(_RAPPID_FILE.read_text())
        rappid = d.get("rappid", "")
        if not rappid:
            return "", d.get("github", "")
        try:
            door = door_from_rappid(rappid)
            return rappid, door["owner"]
        except InvalidRappidError:
            # Operator's own rappid is malformed — surface, don't fix.
            return rappid, d.get("github", "")
    except Exception:
        return "", ""


def _empty_estate() -> dict:
    rappid, github = _read_local_rappid()
    return {
        "schema": _ESTATE_SCHEMA,
        "owner": {"rappid": rappid, "github": github},
        "created": [],
        "member": [],
        "updated_at": _now_iso(),
    }


def _normalize_entry(entry: dict) -> dict:
    """Strip a stored entry to the spec-compliant shape: {rappid, added_at, via}.

    Per Article XLVI.5: estate entries store ONLY rappid + provenance. Stored
    derived fields (kind, name, url, summon_url, door_type, etc.) are dropped
    on save — they are recomputed at read time via door_from_rappid().
    """
    out = {
        "rappid":   entry.get("rappid", ""),
        "added_at": entry.get("added_at") or _now_iso(),
        "via":      entry.get("via") or "manual",
    }
    return out


def _load_local() -> dict:
    if not _ESTATE_FILE.exists():
        return _empty_estate()
    try:
        d = json.loads(_ESTATE_FILE.read_text())
    except Exception:
        return _empty_estate()
    d.setdefault("schema", _ESTATE_SCHEMA)
    d.setdefault("owner", {"rappid": "", "github": ""})
    d["created"] = [_normalize_entry(e) for e in d.get("created", [])]
    d["member"]  = [_normalize_entry(e) for e in d.get("member", [])]
    return d


def _save_local(estate: dict) -> None:
    _ESTATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    estate["schema"] = _ESTATE_SCHEMA
    estate["updated_at"] = _now_iso()
    # Strict shape on save: drop any leaked derived fields.
    estate["created"] = [_normalize_entry(e) for e in estate.get("created", [])]
    estate["member"]  = [_normalize_entry(e) for e in estate.get("member", [])]
    _ESTATE_FILE.write_text(json.dumps(estate, indent=2))


# ─── GitHub helpers (publish/fetch/scan) ──────────────────────────────────

def _gh(args: list[str]) -> tuple[int, str, str]:
    p = subprocess.run(["gh", *args], capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def _fetch_remote(github_user: str) -> dict:
    url = _RAW_URL_TEMPLATE.format(user=github_user)
    req = urllib.request.Request(url, headers={"User-Agent": "rapp-estate-agent/1.0"})
    with urllib.request.urlopen(req, timeout=_FETCH_TIMEOUT) as r:
        return json.loads(r.read())


def _publish_to_github(estate: dict, github_user: str, create_if_missing: bool) -> tuple[bool, str]:
    repo = f"{github_user}/rapp-estate"
    rc_check, _, _ = _gh(["repo", "view", repo])
    if rc_check != 0:
        if not create_if_missing:
            return False, f"repo {repo} does not exist; pass create_if_missing=true to plant it"
        rc_create, _, err = _gh([
            "repo", "create", repo, "--public",
            "--description", f"{github_user}'s RAPP estate (local-first inventory)",
        ])
        if rc_create != 0:
            return False, f"gh repo create failed: {err.strip()[:200]}"

    body = json.dumps(estate, indent=2).encode("utf-8")
    b64 = base64.b64encode(body).decode("ascii")

    rc_get, out_get, _ = _gh(["api", f"/repos/{repo}/contents/estate.json"])
    sha_args = []
    if rc_get == 0:
        try:
            sha = json.loads(out_get).get("sha", "")
            if sha:
                sha_args = ["-f", f"sha={sha}"]
        except Exception:
            pass

    rc_put, _, err = _gh([
        "api", "-X", "PUT", f"/repos/{repo}/contents/estate.json",
        "-f", f"message=estate: pulse @ {_now_iso()}",
        "-f", f"content={b64}",
        *sha_args,
    ])
    if rc_put != 0:
        return False, f"gh api PUT failed: {err.strip()[:200]}"
    return True, _RAW_URL_TEMPLATE.format(user=github_user)


def _scan_user_repos(github_user: str, max_repos: int = 200) -> list[dict]:
    """List all public repos owned by github_user via gh."""
    rc, out, _ = _gh([
        "api", "--paginate",
        f"/users/{github_user}/repos?per_page=100&type=owner",
    ])
    if rc != 0:
        return []
    try:
        items = json.loads(out) if out.strip().startswith("[") else []
    except Exception:
        return []
    return items[:max_repos]


def _probe_repo_rappid(owner: str, repo: str) -> str:
    """Try to read a rappid from <owner>/<repo>/main/rappid.json or holo.md.

    Returns the rappid string. Empty string if no rappid is reachable.
    Validation (via door_from_rappid) happens at the call site so the caller
    can decide whether to skip or error on invalid rappids.
    """
    for path in ("rappid.json", "holo.md"):
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/{path}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "rapp-estate-agent/1.0"})
            with urllib.request.urlopen(req, timeout=_FETCH_TIMEOUT) as r:
                body = r.read().decode("utf-8", errors="replace")
        except Exception:
            continue
        if path == "rappid.json":
            try:
                d = json.loads(body)
                rappid = d.get("rappid", "") or d.get("self", {}).get("rappid", "")
            except Exception:
                rappid = ""
        else:
            rappid = ""
            for line in body.splitlines():
                s = line.strip()
                if s.startswith("rappid:") and "rappid:v2:" in s:
                    rappid = s.split(":", 1)[1].strip().strip('"').strip("'")
                    break
        if rappid:
            return rappid
    return ""


# ─── Public helpers ───────────────────────────────────────────────────────

def _find_entry(items: list[dict], rappid: str) -> int:
    for i, it in enumerate(items):
        if it.get("rappid") == rappid:
            return i
    return -1


def append_to_estate(side: str, entry: dict) -> None:
    """Public helper used by plant_seed_agent on successful plant.

    Validates the rappid via door_from_rappid before storing — invalid rappids
    raise InvalidRappidError, which propagates to the caller (Article XLVI.5:
    no silent fix-ups).
    """
    if side not in ("created", "member"):
        return
    rappid = entry.get("rappid", "")
    door_from_rappid(rappid)  # validates; raises InvalidRappidError on bad input
    estate = _load_local()
    items = estate[side]
    normalized = _normalize_entry(entry)
    idx = _find_entry(items, rappid)
    if idx >= 0:
        items[idx] = normalized
    else:
        items.append(normalized)
    _save_local(estate)


def _expand_door(entry: dict) -> dict:
    """Expand an estate entry into a render-ready door object via door_from_rappid.

    Returns:
      On success: {rappid, added_at, via, owner, repo, kind, door_type, urls, summon_url, name}
      On invalid rappid: {rappid, added_at, via, error: "..."} — surfaced for
      the operator to see and reissue (per Article XLVI.5).
    """
    base = {**_normalize_entry(entry)}
    try:
        door = door_from_rappid(base["rappid"])
        return {
            **base,
            "owner":      door["owner"],
            "repo":       door["repo"],
            "kind":       door["kind"],
            "door_type":  door["door_type"],
            "name":       door["repo"],         # repo name is the canonical short name
            "summon_url": door["urls"]["front"],
            "urls":       door["urls"],
        }
    except InvalidRappidError as e:
        return {**base, "error": str(e)}


def _doors_view(estate: dict) -> dict:
    """Render the 'doors I own + doors I visit' view from a loaded estate.

    Every field in the rendered output is derived from the rappid via
    door_from_rappid(). Stored entry shape is unchanged.
    """
    expanded_created = [_expand_door(e) for e in estate.get("created", [])]
    expanded_member  = [_expand_door(e) for e in estate.get("member",  [])]

    gates       = [d for d in expanded_created if d.get("door_type") == "gate"]
    front_doors = [d for d in expanded_created if d.get("door_type") == "front_door"]
    invalid     = [d for d in expanded_created + expanded_member if "error" in d]

    return {
        "doors_i_own": {
            "gates":       [{k: d[k] for k in ("name", "summon_url", "urls", "rappid") if k in d} for d in gates],
            "front_doors": [{k: d[k] for k in ("name", "summon_url", "urls", "rappid") if k in d} for d in front_doors],
        },
        "doors_i_visit": [{k: d[k] for k in ("name", "summon_url", "urls", "rappid") if k in d} for d in expanded_member if "error" not in d],
        "invalid":       invalid,  # surfaced loudly per Article XLVI.5
        "totals": {
            "gates_owned":       len(gates),
            "front_doors_owned": len(front_doors),
            "doors_visited":     len([d for d in expanded_member if "error" not in d]),
            "invalid":           len(invalid),
        },
    }


# ─── Agent ────────────────────────────────────────────────────────────────

class EstateAgent(BasicAgent):
    metadata = {
        "name": "estate",
        "description": (
            "Manage the local-first RAPP estate — your inventory of created neighborhoods/twins "
            "and contributor memberships, stored as a single JSON file at ~/.brainstem/estate.json. "
            "Per Article XLVI, each entry stores ONLY {rappid, added_at, via}; everything else is "
            "derived at read time. Actions: show | export | import | publish | fetch | add | remove | scan. "
            "Local is source of truth; raw.githubusercontent.com/<user>/rapp-estate/main/estate.json is the public mirror."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["show", "export", "import", "publish", "fetch", "add", "remove", "scan", "rebuild"],
                    "description": "Which estate operation to perform. 'rebuild' reconstructs the estate from pure GitHub raw data (Article XLVI.6 disaster recovery). 'fetch' accepts user= OR rappid= (drop in any rappid → see whose estate owns that door).",
                },
                "path":   {"type": "string", "description": "File path for export (write) or import (read)."},
                "user":   {"type": "string", "description": "GitHub user whose published estate to fetch."},
                "merge":  {"type": "boolean", "description": "import: merge into existing local estate (default: replace)."},
                "create_if_missing": {"type": "boolean", "description": "publish: create <user>/rapp-estate if it doesn't exist."},
                "side":   {"type": "string", "enum": ["created", "member"], "description": "add/remove: which side of the estate."},
                "rappid": {"type": "string", "description": "add/remove: rappid of the entry. (The ONLY required identifying field — kind, name, owner are derived.)"},
                "via":    {"type": "string", "description": "add: provenance of how this entry came in (created/scan/manual/import)."},
            },
            "required": ["action"],
        },
    }

    def __init__(self):
        super().__init__(
            name=self.metadata["name"],
            metadata=self.metadata,
        )

    def perform(self, **kwargs) -> str:
        action = (kwargs.get("action") or "show").lower()

        if action == "show":
            estate = _load_local()
            return json.dumps({
                "ok": True,
                "estate_file": str(_ESTATE_FILE),
                "owner": estate["owner"],
                "created_count": len(estate["created"]),
                "member_count": len(estate["member"]),
                "updated_at": estate.get("updated_at"),
                "doors": _doors_view(estate),
                "estate": estate,
            }, indent=2)

        if action == "export":
            estate = _load_local()
            path = kwargs.get("path") or f"./estate-{time.strftime('%Y%m%d-%H%M%S')}.json"
            out = Path(os.path.expanduser(path))
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(estate, indent=2))
            return json.dumps({
                "ok": True,
                "action": "export",
                "wrote": str(out),
                "bytes": out.stat().st_size,
                "next_step": f"Email/AirDrop/USB this file. Restore with action=import path={out}",
            }, indent=2)

        if action == "import":
            path = kwargs.get("path")
            if not path:
                return json.dumps({"ok": False, "error": "path required for import"}, indent=2)
            src = Path(os.path.expanduser(path))
            if not src.exists():
                return json.dumps({"ok": False, "error": f"file not found: {src}"}, indent=2)
            try:
                incoming = json.loads(src.read_text())
            except Exception as e:
                return json.dumps({"ok": False, "error": f"not valid JSON: {e}"}, indent=2)
            if incoming.get("schema") not in (_ESTATE_SCHEMA, "rapp-estate/1.0"):
                return json.dumps({"ok": False, "error": f"schema mismatch: expected {_ESTATE_SCHEMA}, got {incoming.get('schema')}"}, indent=2)

            if kwargs.get("merge"):
                current = _load_local()
                for side in ("created", "member"):
                    for entry in incoming.get(side, []):
                        normalized = _normalize_entry(entry)
                        idx = _find_entry(current[side], normalized["rappid"])
                        if idx >= 0:
                            current[side][idx] = normalized
                        else:
                            current[side].append(normalized)
                if not current["owner"].get("rappid"):
                    current["owner"] = incoming.get("owner", current["owner"])
                _save_local(current)
                merged = current
            else:
                _save_local(incoming)
                merged = _load_local()
            return json.dumps({
                "ok": True,
                "action": "import",
                "merged": bool(kwargs.get("merge")),
                "from": str(src),
                "created_count": len(merged.get("created", [])),
                "member_count": len(merged.get("member", [])),
            }, indent=2)

        if action == "publish":
            estate = _load_local()
            github = estate["owner"].get("github") or kwargs.get("user")
            if not github:
                return json.dumps({"ok": False, "error": "owner.github unknown — pass user= or set ~/.brainstem/rappid.json"}, indent=2)
            ok, msg = _publish_to_github(estate, github, bool(kwargs.get("create_if_missing", True)))
            return json.dumps({
                "ok": ok,
                "action": "publish",
                "github_user": github,
                "result": msg,
                "public_url": _RAW_URL_TEMPLATE.format(user=github) if ok else None,
            }, indent=2)

        if action == "fetch":
            user = kwargs.get("user", "")
            rappid_in = kwargs.get("rappid", "")
            via = "user"

            # Drop in any rappid → resolve to the OPERATOR's handle, then fetch.
            # If rappid is an operator-kind rappid → owner is the operator's handle.
            # If rappid is a door-kind rappid → fetch the door's rappid.json,
            # read parent_rappid (the operator's rappid), use its owner.
            if not user and rappid_in:
                try:
                    door = door_from_rappid(rappid_in)
                except InvalidRappidError as e:
                    return json.dumps({"ok": False, "error": f"invalid rappid: {e}"}, indent=2)
                if door["kind"] == "operator":
                    user = door["owner"]
                    via = "rappid:operator-direct"
                else:
                    # Door rappid — fetch its rappid.json to find parent
                    try:
                        req = urllib.request.Request(door["urls"]["identity"],
                                                      headers={"User-Agent": "rapp-estate-agent/1.0"})
                        with urllib.request.urlopen(req, timeout=_FETCH_TIMEOUT) as r:
                            door_meta = json.loads(r.read())
                        parent = door_meta.get("parent_rappid", "")
                        if not parent:
                            return json.dumps({
                                "ok": False,
                                "error": "door has no parent_rappid; cannot trace to operator's estate",
                                "hint": "operator can run tools/backfill_seeds.py --patch-parents to set it",
                            }, indent=2)
                        parent_door = door_from_rappid(parent)
                        user = parent_door["owner"]
                        via = "rappid:door-via-parent"
                    except urllib.error.HTTPError as e:
                        return json.dumps({"ok": False, "error": f"HTTP {e.code} fetching door's rappid.json"}, indent=2)
                    except (InvalidRappidError, ValueError) as e:
                        return json.dumps({"ok": False, "error": f"door's parent_rappid malformed: {e}"}, indent=2)
                    except Exception as e:
                        return json.dumps({"ok": False, "error": f"door trace failed: {e}"}, indent=2)

            if not user:
                return json.dumps({"ok": False, "error": "fetch requires user=<handle> OR rappid=<any-rappid>"}, indent=2)

            try:
                remote = _fetch_remote(user)
                remote.setdefault("created", [])
                remote.setdefault("member", [])
                # Normalize on the wire so the doors view runs consistently
                remote["created"] = [_normalize_entry(e) for e in remote["created"]]
                remote["member"]  = [_normalize_entry(e) for e in remote["member"]]
                return json.dumps({
                    "ok": True,
                    "action": "fetch",
                    "user": user,
                    "via": via,
                    "source": _RAW_URL_TEMPLATE.format(user=user),
                    "doors": _doors_view(remote),
                    "estate": remote,
                }, indent=2)
            except urllib.error.HTTPError as e:
                return json.dumps({"ok": False, "error": f"HTTP {e.code} fetching {user}'s estate", "hint": "they may not have published one yet"}, indent=2)
            except Exception as e:
                return json.dumps({"ok": False, "error": f"fetch failed: {e}"}, indent=2)

        if action == "add":
            side = kwargs.get("side")
            rappid = kwargs.get("rappid", "")
            if side not in ("created", "member") or not rappid:
                return json.dumps({"ok": False, "error": "add requires side=created|member and rappid="}, indent=2)
            try:
                append_to_estate(side, {
                    "rappid":   rappid,
                    "added_at": _now_iso(),
                    "via":      kwargs.get("via") or "manual",
                })
            except InvalidRappidError as e:
                return json.dumps({"ok": False, "error": f"invalid rappid: {e}", "hint": "Article XLVI.5: reissue the rappid; do not patch around it."}, indent=2)
            estate = _load_local()
            return json.dumps({
                "ok": True,
                "action": "add",
                "side": side,
                "totals": {"created": len(estate["created"]), "member": len(estate["member"])},
            }, indent=2)

        if action == "scan":
            estate = _load_local()
            github = estate["owner"].get("github") or kwargs.get("user")
            if not github:
                return json.dumps({"ok": False, "error": "owner.github unknown — pass user=<gh handle>"}, indent=2)
            repos = _scan_user_repos(github)
            if not repos:
                return json.dumps({"ok": False, "error": f"no repos found for {github} (gh auth may be missing)"}, indent=2)
            scanned, added, skipped, invalid = [], [], [], []
            for r in repos:
                name = r.get("name", "")
                if not name or r.get("fork"):
                    skipped.append({"repo": name, "reason": "fork or empty"})
                    continue
                rappid = _probe_repo_rappid(github, name)
                scanned.append({"repo": name, "has_rappid": bool(rappid)})
                if not rappid:
                    skipped.append({"repo": name, "reason": "no rappid.json or holo.md"})
                    continue
                # Validate via the canonical parser — invalid rappids are SURFACED, not patched.
                try:
                    door_from_rappid(rappid)
                except InvalidRappidError as e:
                    invalid.append({"repo": name, "rappid": rappid, "error": str(e)[:120]})
                    continue
                try:
                    append_to_estate("created", {
                        "rappid":   rappid,
                        "added_at": _now_iso(),
                        "via":      "scan",
                    })
                    added.append({"repo": name, "rappid": rappid})
                except InvalidRappidError as e:
                    invalid.append({"repo": name, "rappid": rappid, "error": str(e)[:120]})
            estate = _load_local()
            return json.dumps({
                "ok": True,
                "action": "scan",
                "github_user": github,
                "repos_scanned": len(scanned),
                "added_count": len(added),
                "skipped_count": len(skipped),
                "invalid_count": len(invalid),
                "added": added,
                "invalid": invalid,
                "totals": {"created": len(estate["created"]), "member": len(estate["member"])},
                "next_step": "Reissue any invalid rappids (Article XLVI.5). Then action=publish to push to <user>/rapp-estate.",
            }, indent=2)

        if action == "rebuild":
            # Article XLVI.6: reconstruct the estate from pure GitHub raw data.
            # Delegates to tools/rebuild_estate.py, which walks <handle>/* repos
            # for created[] and uses gh search code for member[]. Default is
            # dry-run (just returns the reconstructed estate); apply=true writes
            # to ~/.brainstem/estate.json (operator-mediated).
            estate = _load_local()
            handle = kwargs.get("user") or estate["owner"].get("github", "")
            if not handle:
                return json.dumps({"ok": False, "error": "rebuild requires user=<handle> OR a seeded ~/.brainstem/rappid.json"}, indent=2)
            apply_flag = bool(kwargs.get("apply", False))
            # Find tools/rebuild_estate.py by walking up to repo root
            here = os.path.abspath(__file__)
            for cand in (
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(here))), "tools", "rebuild_estate.py"),
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(here)))), "tools", "rebuild_estate.py"),
            ):
                if os.path.isfile(cand):
                    rebuild_script = cand
                    break
            else:
                return json.dumps({"ok": False, "error": "tools/rebuild_estate.py not found"}, indent=2)
            cmd = ["python3", rebuild_script, "--handle", handle]
            if apply_flag:
                cmd.append("--apply")
            if kwargs.get("operator_rappid"):
                cmd += ["--operator-rappid", kwargs["operator_rappid"]]
            p = subprocess.run(cmd, capture_output=True, text=True)
            try:
                report = json.loads(p.stdout) if p.stdout.strip() else {"ok": False, "error": "rebuild emitted no output"}
            except Exception as e:
                return json.dumps({"ok": False, "error": f"rebuild output not JSON: {e}", "stderr": p.stderr[:300]}, indent=2)
            return json.dumps({
                "ok":         report.get("ok", False),
                "action":     "rebuild",
                "applied":    apply_flag,
                "handle":     handle,
                "rebuild":    report.get("_rebuild", {}),
                "estate":     {k: v for k, v in report.items() if k not in ("_rebuild", "ok", "error")},
                "stderr":     p.stderr[-500:] if p.stderr else "",
            }, indent=2)

        if action == "remove":
            side = kwargs.get("side")
            rappid = kwargs.get("rappid", "")
            if side not in ("created", "member") or not rappid:
                return json.dumps({"ok": False, "error": "remove requires side=created|member and rappid="}, indent=2)
            estate = _load_local()
            before = len(estate[side])
            estate[side] = [e for e in estate[side] if e.get("rappid") != rappid]
            removed = before - len(estate[side])
            _save_local(estate)
            return json.dumps({
                "ok": True,
                "action": "remove",
                "side": side,
                "removed": removed,
            }, indent=2)

        return json.dumps({"ok": False, "error": f"unknown action: {action}"}, indent=2)
