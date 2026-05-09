"""species_leaderboard_agent — global MMR ladder across the species tree.

Walks the GitHub forks API recursively from the species root (kody-w/RAPP),
collects every planted descendant, computes MMR per ECOSYSTEM §6, returns
the sorted ladder. Caches signals locally so repeated calls don't blow GH
rate limits.

Closes ECOSYSTEM §15 row "Global leaderboard (aggregate the species via
fork-tree walking)". Single-file agent per ANTIPATTERNS §1.

Usage from /chat (LLM tool-call):
    SpeciesLeaderboard.rank(top_n=20, max_forks=200)
"""

from __future__ import annotations

import json
import math
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
_USER_AGENT = "rapp-species-leaderboard/1.0"
_HTTP_TIMEOUT = 8.0
_SPECIES_ROOT_OWNER = "kody-w"
_SPECIES_ROOT_REPO = "RAPP"

_MMR_BASELINE = 1000
_TIER_LADDER = [
    (6000, "Immortal"), (4500, "Divine"), (3500, "Ancient"),
    (3000, "Legend"), (2500, "Archon"), (2000, "Crusader"),
    (1500, "Guardian"), (0, "Herald"),
]

_CACHE_PATH = os.path.expanduser("~/.brainstem/species_leaderboard_cache.json")
_CACHE_TTL_SECONDS = 600  # 10 minutes


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


def _fetch_rappid_json(owner: str, repo: str) -> dict | None:
    url = f"{_RAW}/{owner}/{repo}/main/rappid.json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))
    except Exception:
        return None


def _activity_factor(last_commit_iso: str | None) -> float:
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


def _tier(mmr: int) -> str:
    for threshold, name in _TIER_LADDER:
        if mmr >= threshold:
            return name
    return "Herald"


def _signals_for(owner: str, repo: str) -> dict:
    """Same signal collection as lineage_rollup — kept inline for single-file portability."""
    signals = {"mem_count": 0, "mut_count": 0, "age_days": 0.0,
               "fork_count": 0, "custom_agent_count": 0, "last_commit_at": None}
    meta = _gh_get(f"{_GH_API}/repos/{owner}/{repo}")
    if isinstance(meta, dict):
        signals["fork_count"] = int(meta.get("forks_count", 0))
        created = meta.get("created_at")
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
        kernel_agents = {"basic_agent.py", "manage_memory_agent.py", "context_memory_agent.py"}
        signals["custom_agent_count"] = sum(
            1 for f in agents_dir
            if f.get("name", "").endswith("_agent.py") and f.get("name") not in kernel_agents
        )
    return signals


def _compute_mmr(signals: dict) -> int:
    base = (_MMR_BASELINE + signals["mem_count"] * 30
            + math.sqrt(max(0, signals["mut_count"])) * 250
            + signals["custom_agent_count"] * 350
            + math.sqrt(max(0.0, signals["age_days"])) * 80
            + math.sqrt(max(0, signals["fork_count"])) * 400)
    decayed = max(0, base - _MMR_BASELINE) * _activity_factor(signals.get("last_commit_at"))
    return int(_MMR_BASELINE + decayed)


def _read_cache() -> dict | None:
    if not os.path.exists(_CACHE_PATH):
        return None
    try:
        with open(_CACHE_PATH) as f:
            cached = json.load(f)
        if (time.time() - cached.get("cached_at_unix", 0)) < _CACHE_TTL_SECONDS:
            return cached
    except (OSError, ValueError):
        pass
    return None


def _write_cache(payload: dict) -> None:
    try:
        os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
        with open(_CACHE_PATH, "w") as f:
            json.dump(payload, f, indent=2)
    except OSError:
        pass


def _walk_species(max_forks: int) -> list[dict]:
    """BFS the fork tree from the species root; return planted seeds with MMR."""
    out = []
    queue = [(_SPECIES_ROOT_OWNER, _SPECIES_ROOT_REPO, 0)]
    seen = set()

    # Include the species root itself
    rj_root = _fetch_rappid_json(_SPECIES_ROOT_OWNER, _SPECIES_ROOT_REPO)
    if rj_root:
        sig = _signals_for(_SPECIES_ROOT_OWNER, _SPECIES_ROOT_REPO)
        mmr = _compute_mmr(sig)
        out.append({
            "rappid": rj_root.get("rappid"),
            "owner": _SPECIES_ROOT_OWNER, "repo": _SPECIES_ROOT_REPO,
            "name": rj_root.get("name"), "display_name": rj_root.get("display_name", _SPECIES_ROOT_REPO),
            "kind": rj_root.get("kind", "prototype"),
            "mmr": mmr, "tier": _tier(mmr), "depth": 0,
            "url": f"https://{_SPECIES_ROOT_OWNER}.github.io/{_SPECIES_ROOT_REPO}/",
        })

    while queue and len(out) < max_forks:
        owner, repo, depth = queue.pop(0)
        if (owner, repo) in seen:
            continue
        seen.add((owner, repo))
        forks = _gh_get(f"{_GH_API}/repos/{owner}/{repo}/forks?per_page=30")
        if not isinstance(forks, list):
            continue
        for fork in forks:
            fowner = fork.get("owner", {}).get("login")
            fname = fork.get("name")
            if not fowner or not fname or (fowner, fname) in seen:
                continue
            rj = _fetch_rappid_json(fowner, fname)
            if not rj:
                continue
            sig = _signals_for(fowner, fname)
            mmr = _compute_mmr(sig)
            out.append({
                "rappid": rj.get("rappid"),
                "owner": fowner, "repo": fname,
                "name": rj.get("name"), "display_name": rj.get("display_name", fname),
                "kind": rj.get("kind", "unknown"),
                "mmr": mmr, "tier": _tier(mmr), "depth": depth + 1,
                "url": f"https://{fowner}.github.io/{fname}/",
            })
            queue.append((fowner, fname, depth + 1))
            if len(out) >= max_forks:
                break
    return out


class SpeciesLeaderboardAgent(BasicAgent):
    metadata = {
        "name": "SpeciesLeaderboard",
        "description": (
            "Compute the global RAPP species leaderboard. Walks the fork tree "
            "from kody-w/RAPP, fetches each planted descendant's MMR signals, "
            "returns the sorted ladder with tier (Herald → Immortal). "
            "Caches results for 10 minutes to respect GitHub rate limits."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "top_n": {"type": "integer", "default": 20,
                          "description": "Number of top entries to return."},
                "max_forks": {"type": "integer", "default": 100,
                              "description": "Max planted seeds to enumerate."},
                "force_refresh": {"type": "boolean", "default": False,
                                  "description": "Skip the cache."},
            },
            "required": [],
        },
    }

    def __init__(self):
        self.name = "SpeciesLeaderboard"

    def perform(self, **kwargs) -> str:
        top_n = int(kwargs.get("top_n") or 20)
        max_forks = int(kwargs.get("max_forks") or 100)
        force_refresh = bool(kwargs.get("force_refresh"))

        if not force_refresh:
            cached = _read_cache()
            if cached:
                # Re-rank with potentially-different top_n; data is already collected.
                cached["entries"] = sorted(cached.get("entries", []), key=lambda e: -e["mmr"])[:top_n]
                cached["from_cache"] = True
                cached["top_n"] = top_n
                return json.dumps(cached, indent=2)

        entries = _walk_species(max_forks)
        ladder = sorted(entries, key=lambda e: -e["mmr"])
        payload = {
            "schema": "rapp-species-leaderboard/1.0",
            "species_root": f"{_SPECIES_ROOT_OWNER}/{_SPECIES_ROOT_REPO}",
            "computed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "cached_at_unix": int(time.time()),
            "from_cache": False,
            "total_seen": len(entries),
            "top_n": top_n,
            "entries": ladder[:top_n],
        }
        _write_cache(payload)
        return json.dumps(payload, indent=2)
