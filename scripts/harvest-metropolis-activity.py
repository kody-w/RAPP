#!/usr/bin/env python3
"""
Runtime containment note (2026-09-03): collection and writes are disabled.
The fullest historical collector source is intentionally retained in place
below unconditional refusal boundaries as provenance and learning corpus.

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

COMPATIBILITY_RESULT = {
    "status": "gone",
    "code": "metropolis-activity-harvester-retired",
    "accepted": False,
    "network_used": False,
    "write_performed": False,
    "historical_source_commit": "1d4141f32a0b90c8de24be136478cc583bed6474",
    "historical_source_blob": "1629e896160200a6ce7b08dc1c188908df236060",
    "message": "Collection is disabled; the explorer reads frozen local snapshots.",
}


def slug_from_gate_repo(gate_repo):
    if not gate_repo:
        return None
    s = gate_repo.rstrip("/")
    prefix = "https://github.com/"
    if not s.startswith(prefix):
        return None
    return s[len(prefix):]


def fetch_events(slug, token=None):
    # BEGIN INERT HISTORICAL SOURCE — the unconditional return is the safety
    # boundary. The original network collector remains below it verbatim.
    return []

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


def validate_local_snapshots():
    federated_path = os.path.join(ROOT, "pages", "metropolis", "federated-demo.json")
    with open(INDEX_PATH, encoding="utf-8") as f:
        index = json.load(f)
    with open(federated_path, encoding="utf-8") as f:
        federated = json.load(f)
    with open(SNAPSHOT_PATH, encoding="utf-8") as f:
        snapshot = json.load(f)

    for path, document in (
        (INDEX_PATH, index),
        (federated_path, federated),
        (SNAPSHOT_PATH, snapshot),
    ):
        if document.get("status") != "historical-retired":
            raise ValueError(f"{path} is not bounded historical data")
        if document.get("accepted") is not False:
            raise ValueError(f"{path} does not declare accepted=false")
        if document.get("rapp_protocol_authority") is not False:
            raise ValueError(f"{path} does not declare rapp_protocol_authority=false")

    if index.get("federated_trackers") != ["./federated-demo.json"]:
        raise ValueError("index.json must point only to its local peer snapshot")
    if federated.get("federated_trackers") != ["./index.json"]:
        raise ValueError("federated-demo.json must point only to its local root snapshot")

    events = snapshot.get("activity") or {}
    return {
        "status": "frozen-snapshots-valid",
        "accepted": False,
        "network_used": False,
        "write_performed": False,
        "primary_entries": len(index.get("entries") or []),
        "federated_entries": len(federated.get("entries") or []),
        "activity_records": sum(
            len(records) for records in events.values() if isinstance(records, list)
        ),
    }


def main():
    if sys.argv[1:] == ["--check"]:
        print(json.dumps(validate_local_snapshots(), sort_keys=True))
        return 0

    print(json.dumps(COMPATIBILITY_RESULT, sort_keys=True))
    return 78

    # BEGIN INERT HISTORICAL SOURCE — original scheduled-writer body retained
    # verbatim after the unconditional refusal above.
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
    raise SystemExit(main())
