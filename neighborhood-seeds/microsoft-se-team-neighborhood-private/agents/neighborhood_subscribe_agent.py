"""
neighborhood_subscribe_agent.py — listener + reconciler.

Two responsibilities:

  1. Long-poll Issues with label `neighborhood-message` on the private
     companion repo. Surface new messages to the operator.

  2. Reconcile members.json against the live GitHub collaborators API.
     If they drift (someone added/removed via gh CLI), open a PR
     updating members.json so the cache catches up.

This agent is what makes the neighborhood self-healing across cache
boundaries — when an offline member comes back online, their queued
Issues get picked up here, and any roster changes that happened while
they were away land via reconciliation.

Phase 1: implements the API calls + the diff. Phase 2 wires it into
the brainstem's background scheduler so it runs without the LLM having
to invoke it.
"""
import json
import os
import urllib.error
import urllib.request

from agents.basic_agent import BasicAgent


GH_API = "https://api.github.com"


class NeighborhoodSubscribeAgent(BasicAgent):
    name = "neighborhood_subscribe"
    metadata = {
        "name": "neighborhood_subscribe",
        "description": "Pick up async neighborhood-message Issues and reconcile members.json with the live GitHub collaborators list. Surface deltas to the operator.",
        "parameters": {
            "type": "object",
            "properties": {
                "since": {
                    "type": "string",
                    "description": "ISO8601 timestamp — only return Issues created after this. Defaults to last 24h."
                }
            },
            "required": []
        }
    }

    def _seed_dir(self):
        return os.environ.get("NEIGHBORHOOD_SEED_DIR", os.getcwd())

    def _gh_token(self):
        return os.environ.get("GITHUB_TOKEN") or ""

    def _gh_get(self, path):
        token = self._gh_token()
        req = urllib.request.Request(
            GH_API + path,
            headers={
                "User-Agent": "rapp-neighborhood-subscribe",
                "Accept": "application/vnd.github+json",
                **({"Authorization": f"Bearer {token}"} if token else {}),
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=5.0) as r:
                return json.loads(r.read().decode("utf-8")), r.status
        except urllib.error.HTTPError as e:
            return {"error": str(e), "status": e.code}, e.code
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            return {"error": str(e)}, 0

    def _load_members_file(self):
        try:
            with open(os.path.join(self._seed_dir(), "members.json"), "r") as f:
                return json.load(f) or {}
        except (FileNotFoundError, ValueError):
            return {}

    def _repo_slug_from_neighborhood(self):
        try:
            with open(os.path.join(self._seed_dir(), "neighborhood.json"), "r") as f:
                n = json.load(f)
        except (FileNotFoundError, ValueError):
            return None
        url = (n.get("github") or "").rstrip("/")
        prefix = "https://github.com/"
        if url.startswith(prefix):
            return url[len(prefix):]
        return None

    def perform(self, since=None, **kwargs):
        slug = self._repo_slug_from_neighborhood()
        if not slug:
            return json.dumps({"error": "could not derive repo slug from neighborhood.json"})

        issues_path = f"/repos/{slug}/issues?state=open&labels=neighborhood-message&per_page=20"
        if since:
            issues_path += f"&since={since}"
        issues, issues_status = self._gh_get(issues_path)

        collabs, collabs_status = self._gh_get(f"/repos/{slug}/collaborators")
        live_logins = []
        if isinstance(collabs, list):
            live_logins = sorted({(c.get("login") or "").lower() for c in collabs if c.get("login")})

        members_doc = self._load_members_file()
        cached_logins = sorted({
            (m.get("github_login") or "").lower()
            for m in (members_doc.get("members") or [])
            if m.get("github_login")
        })
        added = sorted(set(live_logins) - set(cached_logins))
        removed = sorted(set(cached_logins) - set(live_logins))

        return json.dumps({
            "schema": "rapp-neighborhood-subscribe-report/1.0",
            "repo": slug,
            "issues_status": issues_status,
            "issues_count": len(issues) if isinstance(issues, list) else 0,
            "issues_preview": [
                {"number": i.get("number"), "title": i.get("title"), "user": (i.get("user") or {}).get("login")}
                for i in (issues if isinstance(issues, list) else [])[:5]
            ],
            "collaborators_status": collabs_status,
            "live_logins": live_logins,
            "cached_logins": cached_logins,
            "drift": {"added": added, "removed": removed},
            "next_action": (
                "Open a PR updating members.json" if (added or removed)
                else "No drift — members.json is in sync."
            ),
        }, indent=2)
