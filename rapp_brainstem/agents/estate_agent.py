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
no rate limits for public reads. Anyone can fetch any user's estate JSON.

Actions (all operator-mediated):
    show     — print the current local estate
    export   — write the local estate to a path (for backup / sharing)
    import   — load a JSON file into the local estate (replace or merge)
    publish  — push the local estate to <user>/rapp-estate (gh api)
    fetch    — read someone else's published estate via raw.githubusercontent.com
    add      — append an entry to created[] or member[]
    remove   — drop an entry by rappid

Schema: `rapp-estate/1.0`. No cron, no workflow, no directory-of-files —
just one JSON file you can email yourself.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
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
    "summary": "Local-first RAPP estate as a single JSON file (import / export / publish / fetch).",
    "tags": ["estate", "lineage", "rappid", "backup", "local-first"],
}


_ESTATE_SCHEMA = "rapp-estate/1.0"
_ESTATE_FILE = Path(os.path.expanduser("~/.brainstem/estate.json"))
_RAPPID_FILE = Path(os.path.expanduser("~/.brainstem/rappid.json"))
_RAW_URL_TEMPLATE = "https://raw.githubusercontent.com/{user}/rapp-estate/main/estate.json"
_FETCH_TIMEOUT = 8


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _read_local_rappid() -> tuple[str, str]:
    """Return (rappid, github_handle) of the operator from ~/.brainstem/rappid.json."""
    if not _RAPPID_FILE.exists():
        return "", ""
    try:
        d = json.loads(_RAPPID_FILE.read_text())
        rappid = d.get("rappid", "")
        github = ""
        # rappid:v2:<kind>:@<owner>/<repo>:<32hex>@github.com/<owner>/<repo>
        if rappid.startswith("rappid:v2:"):
            tail = rappid.split(":@", 1)
            if len(tail) == 2:
                github = tail[1].split("/", 1)[0]
        return rappid, github or d.get("github", "")
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


def _load_local() -> dict:
    if not _ESTATE_FILE.exists():
        return _empty_estate()
    try:
        d = json.loads(_ESTATE_FILE.read_text())
        if d.get("schema") != _ESTATE_SCHEMA:
            d["schema"] = _ESTATE_SCHEMA
        d.setdefault("owner", {"rappid": "", "github": ""})
        d.setdefault("created", [])
        d.setdefault("member", [])
        return d
    except Exception:
        return _empty_estate()


def _save_local(estate: dict) -> None:
    _ESTATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    estate["updated_at"] = _now_iso()
    _ESTATE_FILE.write_text(json.dumps(estate, indent=2))


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

    # Look up existing file SHA so PUT is an update, not a clobber-error
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
    return True, f"https://raw.githubusercontent.com/{github_user}/rapp-estate/main/estate.json"


def _find_entry(items: list[dict], rappid: str) -> int:
    for i, it in enumerate(items):
        if it.get("rappid") == rappid:
            return i
    return -1


def append_to_estate(side: str, entry: dict) -> None:
    """Public helper used by plant_seed_agent on successful plant."""
    if side not in ("created", "member"):
        return
    estate = _load_local()
    items = estate[side]
    idx = _find_entry(items, entry.get("rappid", ""))
    if idx >= 0:
        items[idx] = {**items[idx], **entry}
    else:
        items.append(entry)
    _save_local(estate)


class EstateAgent(BasicAgent):
    metadata = {
        "name": "estate",
        "description": (
            "Manage the local-first RAPP estate — your inventory of created neighborhoods/twins "
            "and contributor memberships, stored as a single JSON file at ~/.brainstem/estate.json. "
            "Actions: show | export | import | publish | fetch | add | remove. "
            "Local is source of truth; raw.githubusercontent.com/<user>/rapp-estate/main/estate.json is the public mirror."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["show", "export", "import", "publish", "fetch", "add", "remove"],
                    "description": "Which estate operation to perform.",
                },
                "path": {"type": "string", "description": "File path for export (write) or import (read)."},
                "user": {"type": "string", "description": "GitHub user whose published estate to fetch."},
                "merge": {"type": "boolean", "description": "import: merge into existing local estate (default: replace)."},
                "create_if_missing": {"type": "boolean", "description": "publish: create <user>/rapp-estate if it doesn't exist."},
                "side": {"type": "string", "enum": ["created", "member"], "description": "add/remove: which side of the estate."},
                "rappid": {"type": "string", "description": "add/remove: rappid of the entry."},
                "url": {"type": "string", "description": "add: github URL of the neighborhood/twin."},
                "kind": {"type": "string", "description": "add: 'twin' or 'neighborhood'."},
                "name": {"type": "string", "description": "add: human-readable name."},
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
            if incoming.get("schema") != _ESTATE_SCHEMA:
                return json.dumps({"ok": False, "error": f"schema mismatch: expected {_ESTATE_SCHEMA}, got {incoming.get('schema')}"}, indent=2)

            if kwargs.get("merge"):
                current = _load_local()
                for side in ("created", "member"):
                    for entry in incoming.get(side, []):
                        idx = _find_entry(current[side], entry.get("rappid", ""))
                        if idx >= 0:
                            current[side][idx] = {**current[side][idx], **entry}
                        else:
                            current[side].append(entry)
                if not current["owner"].get("rappid"):
                    current["owner"] = incoming.get("owner", current["owner"])
                _save_local(current)
                merged = current
            else:
                _save_local(incoming)
                merged = incoming
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
            user = kwargs.get("user")
            if not user:
                return json.dumps({"ok": False, "error": "user= required (the GitHub handle to fetch)"}, indent=2)
            try:
                remote = _fetch_remote(user)
                return json.dumps({
                    "ok": True,
                    "action": "fetch",
                    "user": user,
                    "source": _RAW_URL_TEMPLATE.format(user=user),
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
            entry = {
                "rappid": rappid,
                "kind": kwargs.get("kind", "neighborhood"),
                "name": kwargs.get("name", ""),
                "url": kwargs.get("url", ""),
                "added_at": _now_iso(),
            }
            append_to_estate(side, entry)
            estate = _load_local()
            return json.dumps({
                "ok": True,
                "action": "add",
                "side": side,
                "entry": entry,
                "totals": {"created": len(estate["created"]), "member": len(estate["member"])},
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
