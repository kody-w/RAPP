#!/usr/bin/env python3
"""
Static Data Covenant harvester (RAR CONSTITUTION.md Article XXIV).

Runs in CI (or by hand as the "CI harvester") with a token that has GitHub
API access. It reads pages/metropolis/index.json, fetches each public
neighborhood's recent events from api.github.com, and writes a trimmed,
committed snapshot at pages/metropolis/activity-snapshot.json.

The browser-facing page (pages/metropolis/index.html) never calls
api.github.com directly — it reads this committed snapshot instead.

Usage:
    python3 scripts/harvest-metropolis-activity.py

Env:
    GITHUB_TOKEN   optional; if set, used for higher API rate limits.
"""
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = os.path.join(ROOT, "pages", "metropolis", "index.json")
SNAPSHOT_PATH = os.path.join(ROOT, "pages", "metropolis", "activity-snapshot.json")
WINDOW_MINUTES = 15


def slug_from_gate_repo(gate_repo):
    if not gate_repo:
        return None
    s = gate_repo.rstrip("/")
    prefix = "https://github.com/"
    if not s.startswith(prefix):
        return None
    return s[len(prefix):]


def fetch_events(slug, token=None):
    url = f"https://api.github.com/repos/{slug}/events?per_page=50"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"  warn: {slug} -> HTTP {e.code}", file=sys.stderr)
        return []
    except Exception as e:  # noqa: BLE001
        print(f"  warn: {slug} -> {e}", file=sys.stderr)
        return []
    if not isinstance(data, list):
        return []
    trimmed = []
    for ev in data:
        actor = ev.get("actor") or {}
        login = actor.get("login")
        created_at = ev.get("created_at")
        if login and created_at:
            trimmed.append({"created_at": created_at, "actor": {"login": login}})
    return trimmed


def main():
    with open(INDEX_PATH) as f:
        index = json.load(f)

    token = os.environ.get("GITHUB_TOKEN")
    activity = {}
    for entry in index.get("entries", []):
        visibility = entry.get("visibility") or ""
        if visibility.startswith("private"):
            continue
        slug = slug_from_gate_repo(entry.get("gate_repo"))
        if not slug:
            continue
        print(f"harvesting {slug} ...")
        activity[slug] = fetch_events(slug, token)

    snapshot = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_minutes": WINDOW_MINUTES,
        "source": "https://api.github.com/repos/{slug}/events (harvested by CI, not the browser)",
        "activity": activity,
    }
    with open(SNAPSHOT_PATH, "w") as f:
        json.dump(snapshot, f, indent=2)
        f.write("\n")
    print(f"wrote {SNAPSHOT_PATH}")


if __name__ == "__main__":
    main()
