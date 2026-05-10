"""sniff_network — decentralized RAPP network discovery (Article XLVII).

Per the operator's framing: "robots.txt but for the rapp network." A new
estate becomes part of the network the moment it's published per spec —
NOT by registering with a central authority.

PURE-RAW DISCOVERY (default — no GitHub API rate limits):
    1. Fetch the well-known seed at
       https://raw.githubusercontent.com/kody-w/RAPP/main/.well-known/rapp-network-seed.json
    2. For each operator listed there, fetch their `.well-known/rapp-network.json`
       beacon at <handle>/rapp-estate/main/.well-known/rapp-network.json
    3. Each beacon's `discovery.federation_hints[]` adds more handles to the queue
    4. BFS until no new nodes
    5. Optionally fetch each estate.json for a full inventory

ALL raw.githubusercontent.com URLs. No `gh search`. No API token. No rate limit
concerns at our scale (raw is CDN-fronted; topic search would lag minutes-to-hours).

OPTIONAL TOPIC FALLBACK (--via topic):
    Uses `gh search repos topic:rapp-estate` to catch operators who aren't
    in any federation hint chain. Eventually-consistent; useful as a sweep.

USAGE:
    python3 tools/sniff_network.py                       # raw BFS, print summary
    python3 tools/sniff_network.py --json                # full envelope
    python3 tools/sniff_network.py --apply               # write ~/.brainstem/network-sniff.json
    python3 tools/sniff_network.py --seed-url <url>      # start from a different seed
    python3 tools/sniff_network.py --max-hops 5          # cap BFS depth (default 10)
    python3 tools/sniff_network.py --via topic           # use gh search instead (slower, lags)
    python3 tools/sniff_network.py --include-private     # ignore beacon opt-out flag

Stdlib only for --via raw (the default). gh CLI only for --via topic.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import deque
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "tools"))

from door_address import door_from_rappid, InvalidRappidError, estate_url  # noqa: E402


_TOPIC = "rapp-estate"
_BEACON_PATH = ".well-known/rapp-network.json"
_BEACON_SCHEMA = "rapp-network-beacon/1.0"
_SEED_SCHEMA = "rapp-network-seed/1.0"
_DEFAULT_SEED_URL = "https://raw.githubusercontent.com/kody-w/RAPP/main/.well-known/rapp-network-seed.json"
_FETCH_TIMEOUT = 8


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _raw_get_json(url: str) -> dict | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "rapp-network-sniffer/1.0"})
        with urllib.request.urlopen(req, timeout=_FETCH_TIMEOUT) as r:
            return json.loads(r.read())
    except Exception:
        return None


def fetch_seed(seed_url: str) -> dict | None:
    d = _raw_get_json(seed_url)
    if not isinstance(d, dict):
        return None
    if d.get("schema") != _SEED_SCHEMA:
        return None
    return d


def fetch_beacon_for_handle(handle: str) -> dict | None:
    """Fetch <handle>/rapp-estate/main/.well-known/rapp-network.json via raw.

    The beacon path is canonical (Article XLVII): every published estate has
    one at this exact location. No fallback paths.
    """
    url = f"https://raw.githubusercontent.com/{handle}/rapp-estate/main/{_BEACON_PATH}"
    d = _raw_get_json(url)
    if not isinstance(d, dict):
        return None
    if d.get("schema") != _BEACON_SCHEMA:
        return None
    return d


def fetch_estate_for_handle(handle: str) -> dict | None:
    url = f"https://raw.githubusercontent.com/{handle}/rapp-estate/main/estate.json"
    d = _raw_get_json(url)
    return d if isinstance(d, dict) else None


# ─── Pure-raw BFS sniffer ──────────────────────────────────────────────────

def sniff_via_raw(seed_url: str = _DEFAULT_SEED_URL,
                   max_hops: int = 10,
                   include_private: bool = False,
                   fetch_estates: bool = True,
                   on_progress=None) -> dict:
    """BFS from a seed across operator beacons. All raw URLs."""
    seed = fetch_seed(seed_url)
    if not seed:
        return {
            "schema": "rapp-network-sniff/1.0", "via": "raw",
            "ok": False,
            "error": f"could not fetch seed at {seed_url}",
        }

    if on_progress:
        on_progress(f"seed loaded: {len(seed.get('operators', []))} initial operators")

    # BFS state
    queue: deque[tuple[str, int, str]] = deque()  # (handle, hop, source)
    visited: set[str] = set()
    operators: list[dict] = []
    skipped: list[dict] = []

    # Seed operators
    for op in seed.get("operators", []):
        if isinstance(op, dict) and op.get("github"):
            queue.append((op["github"], 0, "seed"))

    while queue:
        handle, hop, source = queue.popleft()
        if handle in visited:
            continue
        visited.add(handle)
        if hop > max_hops:
            skipped.append({"handle": handle, "reason": f"max_hops={max_hops} exceeded"})
            continue

        if on_progress:
            on_progress(f"hop {hop}: {handle} (via {source})")

        beacon = fetch_beacon_for_handle(handle)
        if not beacon:
            skipped.append({"handle": handle,
                             "reason": f"no valid beacon at {handle}/rapp-estate/main/{_BEACON_PATH}"})
            continue

        indexable = bool(beacon.get("discovery", {}).get("indexable", True))
        if not indexable and not include_private:
            skipped.append({"handle": handle,
                             "reason": "discovery.indexable=false (opt-out honored)"})
            continue

        op_rappid = beacon.get("operator_rappid", "")
        try:
            door_from_rappid(op_rappid)
        except InvalidRappidError as e:
            skipped.append({"handle": handle,
                             "reason": f"operator_rappid invalid: {str(e)[:120]}"})
            continue

        record: dict = {
            "github":          handle,
            "operator_rappid": op_rappid,
            "estate_url":      beacon.get("estate_url"),
            "grail_url":       beacon.get("grail_url", ""),
            "spec_implements": beacon.get("protocol", {}).get("implements", []),
            "minted_at":       beacon.get("minted_at"),
            "indexable":       indexable,
            "discovered_via":  source,
            "hop":             hop,
        }

        if fetch_estates:
            estate = fetch_estate_for_handle(handle)
            if estate:
                record["created_count"] = len(estate.get("created", []) or [])
                record["member_count"]  = len(estate.get("member", []) or [])

        operators.append(record)

        # Enqueue this beacon's federation hints
        hints = beacon.get("discovery", {}).get("federation_hints", []) or []
        for hint in hints:
            if isinstance(hint, str) and hint and hint not in visited:
                queue.append((hint, hop + 1, f"hint:{handle}"))
            elif isinstance(hint, dict) and hint.get("github") and hint["github"] not in visited:
                queue.append((hint["github"], hop + 1, f"hint:{handle}"))

    federation_doors = sum(op.get("created_count", 0) + op.get("member_count", 0)
                            for op in operators)

    return {
        "schema":            "rapp-network-sniff/1.0",
        "via":               "raw",
        "ok":                True,
        "seed_url":          seed_url,
        "max_hops":          max_hops,
        "operators_indexed": len(operators),
        "operators_skipped": len(skipped),
        "federation_doors":  federation_doors,
        "operators":         operators,
        "skipped":           skipped,
        "sniffed_at":        _now_iso(),
    }


# ─── Topic-search fallback (gh search repos) ──────────────────────────────

def _gh(args: list[str]) -> tuple[int, str, str]:
    p = subprocess.run(["gh", *args], capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def sniff_via_topic(limit: int = 100, include_private: bool = False,
                     fetch_estates: bool = True, on_progress=None) -> dict:
    """Use `gh search repos topic:rapp-estate`. Eventually-consistent (lags
    indexing by minutes-to-hours); use as a periodic sweep, not a primary."""
    rc, out, err = _gh([
        "search", "repos", f"topic:{_TOPIC}",
        "--json", "owner,name,topics,stargazerCount,updatedAt",
        "--limit", str(limit),
    ])
    if rc != 0:
        return {"schema": "rapp-network-sniff/1.0", "via": "topic",
                 "ok": False, "error": f"gh search failed: {err.strip()[:200]}"}
    try:
        repos = json.loads(out) or []
    except Exception:
        repos = []

    operators: list[dict] = []
    skipped: list[dict] = []
    for r in repos:
        if not isinstance(r, dict):
            continue
        owner = (r.get("owner") or {}).get("login", "")
        name = r.get("name", "")
        if name != "rapp-estate":
            skipped.append({"repo": f"{owner}/{name}",
                             "reason": "topic match but not <handle>/rapp-estate"})
            continue
        if on_progress:
            on_progress(f"validating: {owner}/rapp-estate")
        beacon = fetch_beacon_for_handle(owner)
        if not beacon:
            skipped.append({"repo": f"{owner}/{name}", "reason": "no valid beacon"})
            continue
        indexable = bool(beacon.get("discovery", {}).get("indexable", True))
        if not indexable and not include_private:
            skipped.append({"repo": f"{owner}/{name}", "reason": "indexable=false"})
            continue
        op_rappid = beacon.get("operator_rappid", "")
        try:
            door_from_rappid(op_rappid)
        except InvalidRappidError as e:
            skipped.append({"repo": f"{owner}/{name}", "reason": f"bad rappid: {e}"})
            continue
        record: dict = {
            "github":          owner,
            "operator_rappid": op_rappid,
            "estate_url":      beacon.get("estate_url"),
            "grail_url":       beacon.get("grail_url", ""),
            "minted_at":       beacon.get("minted_at"),
            "indexable":       indexable,
            "discovered_via":  "topic",
        }
        if fetch_estates:
            est = fetch_estate_for_handle(owner)
            if est:
                record["created_count"] = len(est.get("created", []) or [])
                record["member_count"]  = len(est.get("member", []) or [])
        operators.append(record)

    federation_doors = sum(op.get("created_count", 0) + op.get("member_count", 0)
                            for op in operators)
    return {
        "schema":            "rapp-network-sniff/1.0",
        "via":               "topic",
        "ok":                True,
        "topic":             _TOPIC,
        "repos_found":       len(repos),
        "operators_indexed": len(operators),
        "operators_skipped": len(skipped),
        "federation_doors":  federation_doors,
        "operators":         operators,
        "skipped":           skipped,
        "sniffed_at":        _now_iso(),
    }


# ─── CLI ──────────────────────────────────────────────────────────────────

def _print_summary(out: dict) -> None:
    print(f"=== rapp-network-sniff/1.0 (via {out.get('via','?')}) ===")
    if not out.get("ok"):
        print(f"  ERROR: {out.get('error', 'unknown')}")
        return
    if out["via"] == "raw":
        print(f"  seed:              {out['seed_url']}")
        print(f"  max hops:          {out['max_hops']}")
    else:
        print(f"  topic:             {out['topic']}")
        print(f"  repos found:       {out.get('repos_found', '?')}")
    print(f"  operators indexed: {out['operators_indexed']}")
    print(f"  federation doors:  {out['federation_doors']}")
    print(f"  skipped:           {out['operators_skipped']}")
    print()
    for op in out["operators"]:
        marker = "★" if op.get("hop") == 0 else "·"
        cc = op.get("created_count", "?")
        mc = op.get("member_count", "?")
        hop_info = f"hop={op.get('hop')}" if "hop" in op else "topic"
        print(f"  {marker} {op['github']:24s}  doors: {cc:>3} created · {mc:>3} member  ({hop_info}, via {op.get('discovered_via','?')})")
        print(f"    estate: {op.get('estate_url','')}")
        if op.get("grail_url"):
            print(f"    grail:  {op['grail_url']}")
    if out["skipped"]:
        print()
        print(f"  Skipped ({out['operators_skipped']}):")
        for s in out["skipped"][:10]:
            label = s.get("handle") or s.get("repo") or "?"
            print(f"    - {label}: {s['reason']}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--via", choices=["raw", "topic"], default="raw",
                    help="discovery method (default: raw — pure URL fetches, no API)")
    ap.add_argument("--seed-url", default=_DEFAULT_SEED_URL,
                    help="raw URL to start the BFS (default: kody-w/RAPP seed)")
    ap.add_argument("--max-hops", type=int, default=10,
                    help="BFS depth cap (default 10)")
    ap.add_argument("--limit", type=int, default=100,
                    help="for --via topic: max repos to search (default 100)")
    ap.add_argument("--include-private", action="store_true",
                    help="ignore discovery.indexable=false (audit only)")
    ap.add_argument("--no-estates", action="store_true",
                    help="skip fetching each estate.json (faster)")
    ap.add_argument("--apply", action="store_true",
                    help="write ~/.brainstem/network-sniff.json")
    ap.add_argument("--out", default="", help="write the envelope to this path")
    ap.add_argument("--json", action="store_true",
                    help="emit full JSON envelope (default: human summary)")
    args = ap.parse_args()

    def _progress(msg: str) -> None:
        print(f"  · {msg}", file=sys.stderr)

    if args.via == "raw":
        out = sniff_via_raw(seed_url=args.seed_url, max_hops=args.max_hops,
                             include_private=args.include_private,
                             fetch_estates=not args.no_estates,
                             on_progress=_progress)
    else:
        out = sniff_via_topic(limit=args.limit,
                               include_private=args.include_private,
                               fetch_estates=not args.no_estates,
                               on_progress=_progress)

    if args.apply or args.out:
        path = args.out or os.path.expanduser("~/.brainstem/network-sniff.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        Path(path).write_text(json.dumps(out, indent=2))
        out["_wrote_to"] = path

    if args.json:
        print(json.dumps(out, indent=2))
    else:
        _print_summary(out)
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
