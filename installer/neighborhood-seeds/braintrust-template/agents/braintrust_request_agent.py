"""braintrust_request_agent.py — open a new federated-research request.

Drafts the request artifact (rapp-braintrust-request/1.0) and returns a
pre-filled GitHub Issue URL the operator (or follow-up agent) can submit.
The Issue gets the `braintrust-request` label so other contributors'
brainstems pick it up via braintrust_contribute_agent.

Phase 1 stops at the URL. Phase 2 will optionally POST via gh CLI when
authorized."""
import hashlib
import json
import os
import time
import urllib.parse

from agents.basic_agent import BasicAgent


class BraintrustRequestAgent(BasicAgent):
    name = "braintrust_request"
    metadata = {
        "name": "braintrust_request",
        "description": "Open a new federated-research request in this braintrust. Drafts the request artifact, returns a pre-filled GitHub Issue URL with braintrust-request label.",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "What the requester wants to know."},
                "scope": {"type": "string", "description": "Optional — narrow the search (e.g. 'last quarter only', 'enterprise customers')."},
                "requester_login": {"type": "string", "description": "GitHub login of the requester."},
                "requester_rappid": {"type": "string", "description": "The requester's personal organism rappid (preserved across the federation)."},
                "deadline_hours": {"type": "integer", "description": "Hours until contributions close. Default 24."},
                "min_quorum": {"type": "integer", "description": "Minimum contributors before synthesis. Default 1 — adapt-to-who's-home is the default mode."},
                "library_kinds_requested": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Hint to contributors about which library kinds are most relevant (memory / files / vault / url / api). Defaults to empty (any)."
                }
            },
            "required": ["topic", "requester_login"]
        }
    }

    def _seed_dir(self):
        return os.environ.get("NEIGHBORHOOD_SEED_DIR", os.getcwd())

    def _gate_slug(self):
        try:
            with open(os.path.join(self._seed_dir(), "neighborhood.json"), "r") as f:
                gh = (json.load(f) or {}).get("github") or ""
        except (FileNotFoundError, ValueError):
            return None
        prefix = "https://github.com/"
        return gh[len(prefix):].rstrip("/") if gh.startswith(prefix) else None

    def _request_id(self, topic, requester_login, ts):
        return hashlib.sha256(f"{topic}|{requester_login}|{ts}".encode("utf-8")).hexdigest()[:8]

    def perform(self, topic, requester_login, scope=None, requester_rappid=None,
                deadline_hours=24, min_quorum=1, library_kinds_requested=None, **kwargs):
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        request_id = self._request_id(topic, requester_login, ts)
        deadline = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ",
            time.gmtime(time.time() + max(1, int(deadline_hours)) * 3600),
        )
        artifact = {
            "schema": "rapp-braintrust-request/1.0",
            "request_id": request_id,
            "topic": topic,
            "scope": scope,
            "requester": {
                "github_login": requester_login,
                "rappid": requester_rappid,
                "seed_url": None,
            },
            "created_at": ts,
            "deadline": deadline,
            "min_quorum": int(min_quorum or 1),
            "library_kinds_requested": library_kinds_requested or [],
        }

        body = (
            "```json\n"
            + json.dumps(artifact, indent=2)
            + "\n```\n\n"
            + "Contributors: pick this up via your `braintrust_contribute_agent`. "
            + "Adapt-to-who's-home is the default — synthesis will use whatever contributions are present at deadline."
        )

        slug = self._gate_slug() or "<owner>/<repo>"
        title = urllib.parse.quote(f"[braintrust:{request_id}] {topic[:60]}")
        body_q = urllib.parse.quote(body)
        issue_url = f"https://github.com/{slug}/issues/new?title={title}&body={body_q}&labels=braintrust-request"

        return json.dumps({
            "schema": "rapp-braintrust-request-envelope/1.0",
            "request": artifact,
            "next_step": {
                "action": "open_request_issue",
                "url": issue_url,
                "api_alternative": (
                    f"gh issue create --repo {slug} --title \"[braintrust:{request_id}] {topic[:60]}\" "
                    f"--label braintrust-request --body-file <draft>"
                )
            }
        }, indent=2)
