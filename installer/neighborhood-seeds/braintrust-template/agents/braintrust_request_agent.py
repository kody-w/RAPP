"""braintrust_request_agent.py — open a new federated-research request.

Drafts the request artifact (rapp-braintrust-request/1.0) and either:
  - returns a pre-filled GitHub Issue URL the operator can click, OR
  - when `auto_post=true` AND a GITHUB_TOKEN/GH_TOKEN is present, POSTs the
    Issue directly via the GitHub API and returns the issue number.

The Issue gets the `braintrust-request` label so other contributors'
brainstems pick it up via braintrust_contribute_agent.
"""
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from agents.basic_agent import BasicAgent


GH_API = "https://api.github.com"


def _gh_token():
    return (os.environ.get("GITHUB_TOKEN")
            or os.environ.get("GH_TOKEN")
            or "")


def _gh_post(path, body):
    """POST to GitHub API. Returns (response_dict, status_code).
    No auth = (None, 0). Failures return ({"error": ...}, status)."""
    token = _gh_token()
    if not token:
        return None, 0
    req = urllib.request.Request(
        GH_API + path,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "User-Agent": "rapp-braintrust",
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8.0) as r:
            return json.loads(r.read().decode("utf-8")), r.status
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode("utf-8"))
        except Exception:
            payload = {"error": str(e)}
        return payload, e.code
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        return {"error": str(e)}, 0


class BraintrustRequestAgent(BasicAgent):
    name = "braintrust_request"
    metadata = {
        "name": "braintrust_request",
        "description": "Open a new federated-research request in this braintrust. Drafts the request artifact + Issue body, returns the pre-filled URL OR (with auto_post=true + GITHUB_TOKEN) actually POSTs the Issue and returns the issue number.",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "What the requester wants to know."},
                "scope": {"type": "string", "description": "Optional — narrow the search."},
                "requester_login": {"type": "string", "description": "GitHub login of the requester."},
                "requester_rappid": {"type": "string", "description": "The requester's personal organism rappid (preserved across the federation)."},
                "deadline_hours": {"type": "integer", "description": "Hours until contributions close. Default 24."},
                "min_quorum": {"type": "integer", "description": "Minimum contributors before synthesis. Default 1."},
                "library_kinds_requested": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Hint to contributors about which library kinds are relevant. Defaults to empty (any)."
                },
                "auto_post": {
                    "type": "boolean",
                    "description": "When true AND a GITHUB_TOKEN is present, POST the Issue directly via the GitHub API and return the issue number. When false (default), return only the pre-filled Issue URL."
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
                deadline_hours=24, min_quorum=1, library_kinds_requested=None,
                auto_post=False, **kwargs):
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
        title_text = f"[braintrust:{request_id}] {topic[:60]}"
        title_q = urllib.parse.quote(title_text)
        body_q = urllib.parse.quote(body)
        issue_url = f"https://github.com/{slug}/issues/new?title={title_q}&body={body_q}&labels=braintrust-request"

        envelope = {
            "schema": "rapp-braintrust-request-envelope/1.0",
            "request": artifact,
            "auto_post_attempted": False,
            "auto_post_result": None,
            "next_step": {
                "action": "open_request_issue",
                "url": issue_url,
                "api_alternative": (
                    f"gh issue create --repo {slug} --title \"{title_text}\" "
                    f"--label braintrust-request --body-file <draft>"
                ),
            },
        }

        if auto_post:
            envelope["auto_post_attempted"] = True
            if "<owner>/<repo>" in slug:
                envelope["auto_post_result"] = {
                    "ok": False,
                    "reason": "could not derive repo slug from neighborhood.json",
                }
            elif not _gh_token():
                envelope["auto_post_result"] = {
                    "ok": False,
                    "reason": "GITHUB_TOKEN / GH_TOKEN not present in environment",
                }
            else:
                resp, status = _gh_post(
                    f"/repos/{slug}/issues",
                    {"title": title_text, "body": body, "labels": ["braintrust-request"]},
                )
                if status == 201 and isinstance(resp, dict) and resp.get("number"):
                    envelope["auto_post_result"] = {
                        "ok": True,
                        "issue_number": resp.get("number"),
                        "html_url": resp.get("html_url"),
                        "node_id": resp.get("node_id"),
                    }
                    envelope["next_step"] = {
                        "action": "issue_posted",
                        "url": resp.get("html_url"),
                        "issue_number": resp.get("number"),
                    }
                else:
                    envelope["auto_post_result"] = {
                        "ok": False,
                        "status": status,
                        "error": resp,
                    }

        return json.dumps(envelope, indent=2)
