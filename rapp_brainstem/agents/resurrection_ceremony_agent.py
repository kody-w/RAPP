"""resurrection_ceremony_agent — wake an organism out of stasis.

Per ECOSYSTEM §6 + §15, an organism with no commits in 3+ years floors at
MMR baseline (1000) — the **stasis** state. The organism is preserved as
artifact; the resurrection ceremony lets the operator (or a successor)
revive it without changing its rappid identity (Article XXXIV.5 — never
regenerate).

The ceremony is a content-addressed `rapp-frame/1.0` event of kind
`resurrection`, signed by the reviver's own rappid. Filing the ceremony
is itself a fresh commit — which automatically restores the activity
multiplier from 0.45 → 1.00 in the next MMR computation, lifting the
organism out of stasis.

Closes ECOSYSTEM §15 row "Stasis recovery / resurrection ceremony".
Single-file agent per ANTIPATTERNS §1.

Usage from /chat (LLM tool-call):
    Resurrection.assess(rappid_or_url=...)         # Just check stasis state
    Resurrection.compose(rappid_or_url=..., reviver_rappid=..., note="...")
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request

try:
    from agents.basic_agent import BasicAgent
except ImportError:
    from basic_agent import BasicAgent


_GH_API = "https://api.github.com"
_RAW = "https://raw.githubusercontent.com"
_USER_AGENT = "rapp-resurrection/1.0"
_HTTP_TIMEOUT = 8.0
_STASIS_THRESHOLD_DAYS = 365 * 3  # 3 years per ECOSYSTEM §6


def _gh_get(url: str) -> dict | list | None:
    try:
        req = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": _USER_AGENT,
        })
        with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError):
        return None


def _resolve_repo(rappid_or_url: str) -> tuple[str, str] | None:
    s = (rappid_or_url or "").strip()
    if s.startswith("https://github.com/"):
        tail = s[len("https://github.com/"):].rstrip("/").split("/")
        if len(tail) >= 2:
            return tail[0], tail[1]
    if s.startswith("rappid:v2:"):
        # parse host field: rappid:v2:<kind>:@<pub>/<slug>:<hash>@<host>
        try:
            host = s.rsplit("@", 1)[1]
            if host.startswith("github.com/"):
                parts = host[len("github.com/"):].split("/")
                if len(parts) >= 2:
                    return parts[0], parts[1]
        except IndexError:
            pass
    return None


def _last_commit_age_days(owner: str, repo: str) -> tuple[float | None, str | None]:
    commits = _gh_get(f"{_GH_API}/repos/{owner}/{repo}/commits?per_page=1")
    if not isinstance(commits, list) or not commits:
        return None, None
    last = commits[0].get("commit", {}).get("author", {}).get("date")
    if not last:
        return None, None
    try:
        last_ts = time.mktime(time.strptime(last[:19], "%Y-%m-%dT%H:%M:%S"))
        return ((time.time() - last_ts) / 86400.0, last)
    except ValueError:
        return None, last


def _classify_activity(age_days: float | None) -> str:
    if age_days is None:               return "unknown"
    if age_days <= 30:                 return "active"
    if age_days <= 180:                return "slowing"
    if age_days <= _STASIS_THRESHOLD_DAYS: return "dormant"
    return "stasis"


def _frame_hash(prev_hash: str, utc: str, frame_n: int, kind: str, payload: dict) -> str:
    body = (prev_hash or "") + "|" + utc + "|" + str(frame_n) + "|" + kind + "|" + json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


class ResurrectionCeremonyAgent(BasicAgent):
    metadata = {
        "name": "Resurrection",
        "description": (
            "Detect stasis state (>3 years no commits) and compose the resurrection "
            "ceremony — a rapp-frame/1.0 event of kind 'resurrection' attesting that "
            "a successor wakes the organism. Filing the ceremony as a commit lifts the "
            "activity multiplier from 0.45 back to 1.00 (organism's rappid unchanged "
            "per Art. XXXIV.5 — same identity, restored heartbeat)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["assess", "compose"], "default": "assess"},
                "rappid_or_url": {"type": "string",
                                  "description": "Target organism: v2 rappid string OR github.com URL."},
                "reviver_rappid": {"type": "string",
                                   "description": "The reviver's own rappid (for compose)."},
                "note": {"type": "string", "default": "",
                         "description": "Operator's ceremony note (kept on the resurrection frame)."},
                "witness_rappids": {"type": "array", "items": {"type": "string"},
                                    "description": "Optional kin witnesses to the ceremony."},
                "prev_hash": {"type": "string", "default": "",
                              "description": "Prev frame hash for chain continuity (default: '')."},
                "frame_n": {"type": "integer", "default": 0,
                            "description": "Frame number in the resurrection stream."},
            },
            "required": ["rappid_or_url"],
        },
    }

    def __init__(self):
        self.name = "Resurrection"

    def perform(self, **kwargs) -> str:
        action = (kwargs.get("action") or "assess").lower()
        rappid_or_url = (kwargs.get("rappid_or_url") or "").strip()
        repo = _resolve_repo(rappid_or_url)
        if not repo:
            return json.dumps({"ok": False, "error": "could not resolve a github repo from rappid_or_url"})
        owner, name = repo

        age_days, last_commit = _last_commit_age_days(owner, name)
        activity = _classify_activity(age_days)

        assessment = {
            "schema": "rapp-resurrection-assessment/1.0",
            "owner": owner, "repo": name,
            "last_commit_at": last_commit,
            "age_days": round(age_days, 1) if age_days is not None else None,
            "activity_kind": activity,
            "in_stasis": activity == "stasis",
            "stasis_threshold_days": _STASIS_THRESHOLD_DAYS,
        }

        if action == "assess":
            return json.dumps(assessment, indent=2)

        # action = compose — emit the ceremony frame
        if not assessment["in_stasis"]:
            return json.dumps({
                "ok": False,
                "error": f"organism is not in stasis (activity_kind={activity}); ceremony refused",
                "assessment": assessment,
            }, indent=2)

        reviver = (kwargs.get("reviver_rappid") or "").strip()
        if not reviver:
            return json.dumps({"ok": False, "error": "reviver_rappid required for compose"})

        note = (kwargs.get("note") or "").strip()
        witnesses = kwargs.get("witness_rappids") or []
        prev_hash = (kwargs.get("prev_hash") or "").strip()
        frame_n = int(kwargs.get("frame_n") or 0)

        utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        payload = {
            "ceremony": "resurrection",
            "target_rappid_or_url": rappid_or_url,
            "target_repo": f"{owner}/{name}",
            "reviver_rappid": reviver,
            "witness_rappids": list(witnesses) if isinstance(witnesses, list) else [],
            "note": note,
            "stasis_at_resurrection": {
                "age_days": assessment["age_days"],
                "last_commit_at": last_commit,
            },
            "doctrine": (
                "Per CONSTITUTION Art. XXXIV.5, the rappid is permanent; this ceremony "
                "records that the organism's heartbeat is being restored without "
                "regenerating its identity. Filing this frame as a commit lifts the "
                "activity multiplier (0.45 → 1.00) per ECOSYSTEM §6."
            ),
        }

        h = _frame_hash(prev_hash, utc, frame_n, "resurrection", payload)
        frame = {
            "stream_id": f"resurrection:{owner}/{name}",
            "frame_n": frame_n,
            "utc": utc,
            "kind": "resurrection",
            "payload": payload,
            "prev_hash": prev_hash,
            "hash": h,
        }

        # Suggest the operator's next-step commit message + Issues label.
        commit_message = f"resurrection: wake {name} from stasis"
        commit_body = (
            "<!-- rapp-frame/1.0 resurrection ceremony -->\n\n"
            f"```json\n{json.dumps(frame, indent=2)}\n```\n\n"
            "This commit restarts the activity heartbeat per ECOSYSTEM §6 + Art. XXXIV.5.\n"
            "Reviver: " + reviver + "\n"
            + (f"Witnesses: {', '.join(witnesses)}\n" if witnesses else "")
        )

        return json.dumps({
            "schema": "rapp-resurrection-ceremony/1.0",
            "ok": True,
            "assessment": assessment,
            "frame": frame,
            "next_step": {
                "instruction": (
                    f"Commit this frame to {owner}/{name} (e.g., append to "
                    f"data/frames.json or as a standalone resurrection.json), then push. "
                    "The fresh commit lifts the activity multiplier."
                ),
                "commit_message": commit_message,
                "commit_body": commit_body,
                "issue_label": "resurrection",
            },
        }, indent=2)
