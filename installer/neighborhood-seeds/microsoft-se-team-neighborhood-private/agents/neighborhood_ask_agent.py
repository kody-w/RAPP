"""
neighborhood_ask_agent.py — pull a fact from one named neighbor.

Implements the `request-fact → share-fact → ack` exchange primitive from
the RAPP Neighborhood Protocol §8a. Routes a question to one specific
member's twin via (in priority order):

    1. live WebRTC tether to that member's online brainstem
    2. raw.githubusercontent.com fetch of their public state
    3. async Issue post on their seed repo (`neighborhood-message` label)

For Phase 1 this agent stubs the WebRTC layer and returns the route it
would have taken — the wire contract is locked so the federation layer
can wrap this when the tether plumbing lands. See `neighborhood_federate_agent.py`
for the fan-out version.
"""
import json
import os
import urllib.error
import urllib.request

from agents.basic_agent import BasicAgent


class NeighborhoodAskAgent(BasicAgent):
    name = "neighborhood_ask"
    metadata = {
        "name": "neighborhood_ask",
        "description": "Ask one specific neighborhood member's twin a question. Returns their answer plus provenance (which member, which channel was used, what scope was asserted).",
        "parameters": {
            "type": "object",
            "properties": {
                "neighbor_login": {
                    "type": "string",
                    "description": "The GitHub login of the neighbor to ask. Must be in members.json."
                },
                "question": {
                    "type": "string",
                    "description": "The natural-language question to put to that neighbor's twin."
                },
                "facet": {
                    "type": "string",
                    "description": "The public_facet name being asserted (e.g. 'member_roster', 'twin_chat'). Defaults to 'twin_chat'."
                }
            },
            "required": ["neighbor_login", "question"]
        }
    }

    def _seed_dir(self):
        return os.environ.get("NEIGHBORHOOD_SEED_DIR", os.getcwd())

    def _load_members(self):
        try:
            with open(os.path.join(self._seed_dir(), "members.json"), "r") as f:
                return (json.load(f) or {}).get("members") or []
        except (FileNotFoundError, ValueError):
            return []

    def _find_member(self, login):
        for m in self._load_members():
            if (m.get("github_login") or "").lower() == login.lower():
                return m
        return None

    def _public_state_reachable(self, seed_url):
        if not seed_url:
            return False
        try:
            req = urllib.request.Request(seed_url, headers={"User-Agent": "rapp-neighborhood"})
            with urllib.request.urlopen(req, timeout=2.0) as r:
                return 200 <= r.status < 400
        except (urllib.error.URLError, OSError, TimeoutError):
            return False

    def perform(self, neighbor_login, question, facet="twin_chat", **kwargs):
        member = self._find_member(neighbor_login)
        if not member:
            return json.dumps({
                "error": f"@{neighbor_login} is not in members.json",
                "schema": "rapp-twin-chat/1.0"
            })

        seed_url = member.get("seed_url")
        route = "issue_async"
        route_target = None
        if seed_url and self._public_state_reachable(seed_url):
            route = "raw_fetch"
            route_target = seed_url
        else:
            route_target = (
                f"https://github.com/kody-w/microsoft-se-team-neighborhood-private"
                f"/issues/new?labels=neighborhood-message"
            )

        envelope = {
            "schema": "rapp-twin-chat/1.0",
            "kind": "request-fact",
            "from_login": os.environ.get("BRAINSTEM_LOGIN", "self"),
            "to_login": neighbor_login,
            "question": question,
            "facet": facet,
            "route_chosen": route,
            "route_target": route_target,
            "note": (
                "Phase 1 stub: contract is locked, live transport will be wired in by "
                "neighborhood_federate_agent.py once the WebRTC tether layer is bound."
            ),
        }
        return json.dumps(envelope, indent=2)
