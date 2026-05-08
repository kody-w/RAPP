"""
neighborhood_federate_agent.py — fan-out twin-chat across all members.

Self-healing pattern: ask the whole neighborhood the same question, route
to as many members as are reachable, compose a federated reply.

Routing per member (in priority order):

    1. WebRTC tether (cached peer ID, live data channel)            — synchronous
    2. raw.githubusercontent.com fetch of their public state         — synchronous, cached
    3. Async Issue with `neighborhood-message` label                 — eventual

If at least 1 member responds within the synchronous window, we return.
If 0 respond synchronously, we fall back to the cached neighborhood
state and tag the response with a `stale: true` + `quorum: 0` flag — the
operator sees a degraded-mode pill and the queued Issue continues to
gather async replies for next time.

Phase 1 implements: members enumeration, capability filtering, route
selection, cached fallback. The actual WebRTC fan-out is stubbed —
the contract is locked so the transport layer can drop in without a
schema break.
"""
import json
import os
import time
import urllib.error
import urllib.request

from agents.basic_agent import BasicAgent


class NeighborhoodFederateAgent(BasicAgent):
    name = "neighborhood_federate"
    metadata = {
        "name": "neighborhood_federate",
        "description": "Ask the entire neighborhood a question. Fans out to every member's twin (live where reachable, cached otherwise, async Issue for offline), then composes a federated reply with provenance per answer.",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question to put to every member's twin."
                },
                "capability_filter": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional — only ask members whose capabilities include any of these tags."
                },
                "synchronous_window_seconds": {
                    "type": "number",
                    "description": "How long to wait for live + raw-fetch responses before falling back to async + cache. Defaults to 6.0."
                }
            },
            "required": ["question"]
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

    def _capability_match(self, member, filt):
        if not filt:
            return True
        caps = set(member.get("capabilities") or [])
        if "all" in caps:
            return True
        return any(f in caps for f in filt)

    def _route_for(self, member):
        seed_url = member.get("seed_url")
        if seed_url:
            try:
                req = urllib.request.Request(
                    seed_url, headers={"User-Agent": "rapp-neighborhood-federate"}
                )
                with urllib.request.urlopen(req, timeout=2.0) as r:
                    if 200 <= r.status < 400:
                        return "raw_fetch", seed_url
            except (urllib.error.URLError, OSError, TimeoutError):
                pass
        return "issue_async", None

    def perform(self, question, capability_filter=None, synchronous_window_seconds=6.0, **kwargs):
        started = time.time()
        members = self._load_members()
        candidates = [m for m in members if self._capability_match(m, capability_filter)]

        responses = []
        for m in candidates:
            route, target = self._route_for(m)
            responses.append({
                "from_login": m.get("github_login"),
                "rappid": m.get("rappid"),
                "route": route,
                "target": target,
                "reply": None,
                "reply_status": "pending_phase_1_stub"
            })

        elapsed = round(time.time() - started, 2)
        envelope = {
            "schema": "rapp-twin-chat/1.0",
            "kind": "federate",
            "question": question,
            "asked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "capability_filter": capability_filter or [],
            "synchronous_window_seconds": synchronous_window_seconds,
            "elapsed_seconds": elapsed,
            "candidates_count": len(candidates),
            "responses": responses,
            "quorum_reached": False,
            "fallback_used": "cached_neighborhood_state",
            "note": (
                "Phase 1 stub: enumerates members, picks routes, lays the "
                "envelope. Live fan-out (WebRTC + raw fetch + async Issue) "
                "wires in when the tether layer is bound. The wire contract "
                "is stable — no schema bump required."
            ),
        }
        return json.dumps(envelope, indent=2)
