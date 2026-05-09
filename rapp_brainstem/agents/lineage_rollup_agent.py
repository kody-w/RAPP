"""lineage_rollup_agent — aggregate stats across an organism's lineage tree.

Walks `parent_rappid` backward to the species root + the GitHub forks API
forward to enumerate descendants. Fetches each organism's `rappid.json` +
state-derived signals, computes the documented MMR formula per ECOSYSTEM §6,
returns avg/median/count with the full ladder.

Closes ECOSYSTEM §15 row "Lineage roll-up stats (avg/median MMR across the
lineage tree)". Pure agent (single-file) per ANTIPATTERNS §1 — no kernel
edits required. Tier-portable: same file runs on Tier 1 / Tier 2 / Tier 3.

Usage from /chat (LLM tool-call):
    LineageRollup.compute(rappid="<v2 string or UUID>", max_depth=4)
"""

from __future__ import annotations

import json
import math
import re
import statistics
import time
import urllib.error
import urllib.request

try:
    from agents.basic_agent import BasicAgent
except ImportError:
    from basic_agent import BasicAgent


_GH_API = "https://api.github.com"
_RAW = "https://raw.githubusercontent.com"
_USER_AGENT = "rapp-lineage-rollup/1.0"
_HTTP_TIMEOUT = 8.0
_DEFAULT_MAX_DEPTH = 4
_DEFAULT_MAX_FORKS = 50

# MMR formula constants per ECOSYSTEM §6
_MMR_BASELINE = 1000
_MMR_PER_MEM = 30
_MMR_PER_SQRT_MUT = 250
_MMR_PER_AGENT = 350
_MMR_PER_SQRT_AGE_DAYS = 80
_MMR_PER_SQRT_FORK = 400


def _gh_get(url: str) -> dict | list | None:
    """GET a JSON resource; return None on any failure (graceful)."""
    try:
        req = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": _USER_AGENT,
        })
        with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError):
        return None


def _parse_v2_rappid(rappid: str) -> dict | None:
    """Parse `rappid:v2:<kind>:@<pub>/<slug>:<hash>@<host>` → components."""
    if not isinstance(rappid, str) or not rappid.startswith("rappid:v2:"):
        return None
    m = re.match(
        r'^rappid:v\d+:([A-Za-z][A-Za-z0-9_-]*):@([A-Za-z0-9_-]+)/([A-Za-z0-9_-]+):([0-9a-f]+)@([A-Za-z0-9.\-/_]+)$',
        rappid,
    )
    if not m:
        return None
    return {"kind": m.group(1), "pub": m.group(2), "slug": m.group(3),
            "hash": m.group(4), "host": m.group(5)}


def _rappid_to_repo(rappid: str) -> tuple[str, str] | None:
    """Best-effort: pull (owner, repo) from a v2-format rappid's host field."""
    parsed = _parse_v2_rappid(rappid)
    if not parsed:
        return None
    host = parsed["host"]
    if host.startswith("github.com/"):
        parts = host[len("github.com/"):].split("/")
        if len(parts) >= 2:
            return parts[0], parts[1]
    return None


def _fetch_rappid_json(owner: str, repo: str) -> dict | None:
    """Fetch the seed's rappid.json from raw.githubusercontent.com."""
    url = f"{_RAW}/{owner}/{repo}/main/rappid.json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))
    except Exception:
        return None


def _fetch_signals(owner: str, repo: str) -> dict:
    """Fetch state-derived MMR signals: mem count, mut count, age, forks, agents."""
    signals = {"mem_count": 0, "mut_count": 0, "age_days": 0.0,
               "fork_count": 0, "custom_agent_count": 0, "last_commit_at": None}

    repo_meta = _gh_get(f"{_GH_API}/repos/{owner}/{repo}")
    if isinstance(repo_meta, dict):
        signals["fork_count"] = int(repo_meta.get("forks_count", 0))
        created = repo_meta.get("created_at")
        if created:
            try:
                created_ts = time.mktime(time.strptime(created, "%Y-%m-%dT%H:%M:%SZ"))
                signals["age_days"] = max(0.0, (time.time() - created_ts) / 86400.0)
            except ValueError:
                pass

    commits = _gh_get(f"{_GH_API}/repos/{owner}/{repo}/commits?per_page=100")
    if isinstance(commits, list):
        signals["mut_count"] = len(commits)
        if commits:
            signals["last_commit_at"] = (commits[0].get("commit", {})
                                                   .get("author", {}).get("date"))

    agents_dir = _gh_get(f"{_GH_API}/repos/{owner}/{repo}/contents/agents")
    if isinstance(agents_dir, list):
        # exclude basic_agent.py, manage_memory_agent.py, context_memory_agent.py (kernel tier)
        kernel_agents = {"basic_agent.py", "manage_memory_agent.py", "context_memory_agent.py"}
        signals["custom_agent_count"] = sum(
            1 for f in agents_dir
            if f.get("name", "").endswith("_agent.py") and f.get("name") not in kernel_agents
        )

    mem_blob = _gh_get(f"{_GH_API}/repos/{owner}/{repo}/contents/.brainstem_data/memory.json")
    if isinstance(mem_blob, dict) and mem_blob.get("content"):
        try:
            import base64
            decoded = base64.b64decode(mem_blob["content"]).decode("utf-8", errors="replace")
            mem_obj = json.loads(decoded)
            signals["mem_count"] = len(mem_obj.get("public", [])) if isinstance(mem_obj, dict) else 0
        except Exception:
            pass

    return signals


def _activity_factor(last_commit_iso: str | None) -> float:
    """Per ECOSYSTEM §6: 1.00 / 0.85 / 0.65 / 0.45 by recency."""
    if not last_commit_iso:
        return 0.45
    try:
        last_ts = time.mktime(time.strptime(last_commit_iso[:19], "%Y-%m-%dT%H:%M:%S"))
        age_days = (time.time() - last_ts) / 86400.0
    except ValueError:
        return 0.45
    if age_days <= 30:    return 1.00
    if age_days <= 180:   return 0.85
    if age_days <= 365 * 3: return 0.65
    return 0.45


def _compute_mmr(signals: dict, lineage_gift: int = 0) -> int:
    """ECOSYSTEM §6 formula. lineage_gift = 30% of parent's above-baseline."""
    base = (_MMR_BASELINE
            + signals["mem_count"] * _MMR_PER_MEM
            + math.sqrt(max(0, signals["mut_count"])) * _MMR_PER_SQRT_MUT
            + signals["custom_agent_count"] * _MMR_PER_AGENT
            + math.sqrt(max(0.0, signals["age_days"])) * _MMR_PER_SQRT_AGE_DAYS
            + math.sqrt(max(0, signals["fork_count"])) * _MMR_PER_SQRT_FORK)
    above = max(0, base - _MMR_BASELINE)
    decayed = above * _activity_factor(signals.get("last_commit_at"))
    return int(_MMR_BASELINE + decayed + lineage_gift)


def _walk_ancestors(rappid: str, max_depth: int) -> list[dict]:
    """Walk parent_rappid backward; return ordered list (closest first)."""
    out = []
    current_rappid = rappid
    seen = set()
    for _ in range(max_depth):
        if not current_rappid or current_rappid in seen:
            break
        seen.add(current_rappid)
        repo = _rappid_to_repo(current_rappid)
        if not repo:
            break
        owner, name = repo
        rj = _fetch_rappid_json(owner, name)
        if not rj:
            break
        signals = _fetch_signals(owner, name)
        out.append({
            "rappid": current_rappid, "owner": owner, "repo": name,
            "kind": rj.get("kind"), "name": rj.get("name"),
            "display_name": rj.get("display_name"),
            "signals": signals, "mmr": _compute_mmr(signals),
        })
        parent = rj.get("parent_rappid")
        if not parent:
            break
        current_rappid = parent
    return out


def _walk_descendants(rappid: str, max_depth: int, max_forks: int) -> list[dict]:
    """Walk forks API forward; return flat list across depth-first walk."""
    out = []
    seed_repo = _rappid_to_repo(rappid)
    if not seed_repo:
        return out
    queue = [(seed_repo[0], seed_repo[1], 0)]
    seen = set()
    while queue and len(out) < max_forks:
        owner, name, depth = queue.pop(0)
        if (owner, name) in seen or depth > max_depth:
            continue
        seen.add((owner, name))
        forks = _gh_get(f"{_GH_API}/repos/{owner}/{name}/forks?per_page=20")
        if not isinstance(forks, list):
            continue
        for fork in forks:
            fowner = fork.get("owner", {}).get("login")
            fname = fork.get("name")
            if not fowner or not fname or (fowner, fname) in seen:
                continue
            rj = _fetch_rappid_json(fowner, fname)
            if not rj:
                continue  # not a planted seed; skip
            signals = _fetch_signals(fowner, fname)
            out.append({
                "rappid": rj.get("rappid"), "owner": fowner, "repo": fname,
                "kind": rj.get("kind"), "name": rj.get("name"),
                "display_name": rj.get("display_name"),
                "signals": signals, "mmr": _compute_mmr(signals),
                "depth": depth + 1,
            })
            queue.append((fowner, fname, depth + 1))
            if len(out) >= max_forks:
                break
    return out


class LineageRollupAgent(BasicAgent):
    metadata = {
        "name": "LineageRollup",
        "description": (
            "Aggregate stats across an organism's lineage tree. Walks parent_rappid "
            "backward to the species root and the GitHub forks API forward to enumerate "
            "descendants. Returns avg/median/min/max MMR + the full ladder."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "rappid": {"type": "string",
                           "description": "v2-format rappid string OR a github.com/<owner>/<repo> URL."},
                "max_depth": {"type": "integer", "default": _DEFAULT_MAX_DEPTH,
                              "description": "Max ancestry + descent depth."},
                "max_forks": {"type": "integer", "default": _DEFAULT_MAX_FORKS,
                              "description": "Max number of descendants to enumerate."},
            },
            "required": ["rappid"],
        },
    }

    def __init__(self):
        self.name = "LineageRollup"

    def perform(self, **kwargs) -> str:
        rappid = (kwargs.get("rappid") or "").strip()
        max_depth = int(kwargs.get("max_depth") or _DEFAULT_MAX_DEPTH)
        max_forks = int(kwargs.get("max_forks") or _DEFAULT_MAX_FORKS)

        # Allow a github URL as a convenience input — derive rappid by fetching rappid.json.
        if rappid.startswith("https://github.com/"):
            tail = rappid[len("https://github.com/"):].rstrip("/").split("/")
            if len(tail) >= 2:
                rj = _fetch_rappid_json(tail[0], tail[1])
                if not rj:
                    return json.dumps({"ok": False, "error": "could not fetch rappid.json from URL"})
                rappid = rj.get("rappid", "")

        if not rappid:
            return json.dumps({"ok": False, "error": "rappid required"})

        ancestors = _walk_ancestors(rappid, max_depth)
        descendants = _walk_descendants(rappid, max_depth, max_forks)

        all_mmr = [n["mmr"] for n in ancestors] + [n["mmr"] for n in descendants]
        result = {
            "schema": "rapp-lineage-rollup/1.0",
            "rappid": rappid,
            "ancestors": ancestors,
            "descendants": descendants,
            "stats": {
                "ancestor_count": len(ancestors),
                "descendant_count": len(descendants),
                "total": len(all_mmr),
                "avg_mmr": int(statistics.mean(all_mmr)) if all_mmr else _MMR_BASELINE,
                "median_mmr": int(statistics.median(all_mmr)) if all_mmr else _MMR_BASELINE,
                "min_mmr": min(all_mmr) if all_mmr else _MMR_BASELINE,
                "max_mmr": max(all_mmr) if all_mmr else _MMR_BASELINE,
            },
        }
        return json.dumps(result, indent=2)
