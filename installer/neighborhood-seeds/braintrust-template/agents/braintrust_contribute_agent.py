"""braintrust_contribute_agent.py — run library_query against an active request and post findings.

Loads the in-process library_query_agent (which the operator may have
overridden locally), runs it against the request topic, packages findings
into a `rapp-braintrust-contribution/1.0` envelope, and either:
  - returns the comment-body for the operator to paste, OR
  - when `auto_post=true` AND a GITHUB_TOKEN is present AND issue_number
    is provided, POSTs the comment directly via the GitHub API.

If library_query returns no findings, the agent still posts a polite
'no contribution from this librarian' record so the synthesizer knows
this contributor is online and doesn't have anything — distinct from
'this contributor never responded'.
"""
import importlib.util
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


class BraintrustContributeAgent(BasicAgent):
    name = "braintrust_contribute"
    metadata = {
        "name": "braintrust_contribute",
        "description": "Pick up an active braintrust request, run THIS operator's library_query against it, and post the contribution back to the request Issue. With auto_post=true + GITHUB_TOKEN + issue_number, posts the comment directly.",
        "parameters": {
            "type": "object",
            "properties": {
                "request_id": {"type": "string", "description": "The braintrust request ID."},
                "topic": {"type": "string", "description": "The request topic."},
                "scope": {"type": "string", "description": "Optional narrowing scope."},
                "contributor_login": {"type": "string", "description": "This contributor's GitHub login."},
                "contributor_rappid": {"type": "string", "description": "This contributor's personal organism rappid."},
                "issue_number": {"type": "integer", "description": "GitHub Issue number for this request (required for auto_post)."},
                "auto_post": {
                    "type": "boolean",
                    "description": "When true AND GITHUB_TOKEN present AND issue_number provided, POST the comment directly. Defaults to false (return draft only)."
                }
            },
            "required": ["request_id", "topic", "contributor_login"]
        }
    }

    def _seed_dir(self):
        return os.environ.get("NEIGHBORHOOD_SEED_DIR", os.getcwd())

    def _load_library_query(self):
        for candidate_dir in (
            os.environ.get("PERSONAL_AGENTS_DIR"),
            os.path.join(os.path.expanduser("~"), ".brainstem", "agents"),
            os.path.join(self._seed_dir(), "agents"),
        ):
            if not candidate_dir:
                continue
            target = os.path.join(candidate_dir, "library_query_agent.py")
            if os.path.exists(target):
                spec = importlib.util.spec_from_file_location("braintrust_library_query", target)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                for k in dir(mod):
                    obj = getattr(mod, k)
                    if isinstance(obj, type) and getattr(obj, "name", None) == "library_query":
                        return obj()
        return None

    def _gate_slug(self):
        try:
            with open(os.path.join(self._seed_dir(), "neighborhood.json"), "r") as f:
                gh = (json.load(f) or {}).get("github") or ""
        except (FileNotFoundError, ValueError):
            return None
        prefix = "https://github.com/"
        return gh[len(prefix):].rstrip("/") if gh.startswith(prefix) else None

    def perform(self, request_id, topic, contributor_login, scope=None,
                contributor_rappid=None, issue_number=None, auto_post=False, **kwargs):
        lib = self._load_library_query()
        if lib is None:
            return json.dumps({"error": "no library_query_agent could be loaded"})

        try:
            raw = lib.perform(topic=topic, scope=scope)
        except Exception as e:
            return json.dumps({"error": f"library_query failed: {e}"})
        try:
            lib_result = json.loads(raw) if isinstance(raw, str) else raw
        except (ValueError, TypeError):
            lib_result = {"findings": [], "library_kinds_searched": []}

        contribution = {
            "schema": "rapp-braintrust-contribution/1.0",
            "request_id": request_id,
            "contributor": {
                "github_login": contributor_login,
                "rappid": contributor_rappid,
                "seed_url": None,
            },
            "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "library_kinds_searched": lib_result.get("library_kinds_searched") or [],
            "findings": lib_result.get("findings") or [],
            "is_empty": (lib_result.get("findings_count") or 0) == 0,
        }

        comment_body = (
            "```json\n"
            + json.dumps(contribution, indent=2)
            + "\n```\n\n"
            + (
                f"@{contributor_login} has no relevant findings. Marking online-but-empty so synthesis is not blocked."
                if contribution["is_empty"] else
                f"Contribution from @{contributor_login} — {len(contribution['findings'])} finding(s)."
            )
        )

        slug = self._gate_slug() or "<owner>/<repo>"
        envelope = {
            "schema": "rapp-braintrust-contribution-envelope/1.0",
            "contribution": contribution,
            "auto_post_attempted": False,
            "auto_post_result": None,
            "next_step": {
                "action": "post_contribution_comment",
                "comment_body_preview": comment_body[:400] + ("…" if len(comment_body) > 400 else ""),
                "api_alternative": (
                    f"gh issue comment {issue_number} --repo {slug} --body-file <contribution.md>"
                    if issue_number else
                    f"gh issue list --repo {slug} --search 'in:title braintrust:{request_id}' "
                    f"--json number,title  # then: gh issue comment <n> --body-file ..."
                ),
            },
        }

        if auto_post:
            envelope["auto_post_attempted"] = True
            if not issue_number:
                envelope["auto_post_result"] = {
                    "ok": False,
                    "reason": "issue_number is required for auto_post",
                }
            elif "<owner>/<repo>" in slug:
                envelope["auto_post_result"] = {
                    "ok": False,
                    "reason": "could not derive repo slug from neighborhood.json",
                }
            elif not _gh_token():
                envelope["auto_post_result"] = {
                    "ok": False,
                    "reason": "GITHUB_TOKEN / GH_TOKEN not present",
                }
            else:
                resp, status = _gh_post(
                    f"/repos/{slug}/issues/{int(issue_number)}/comments",
                    {"body": comment_body},
                )
                if status == 201 and isinstance(resp, dict) and resp.get("id"):
                    envelope["auto_post_result"] = {
                        "ok": True,
                        "comment_id": resp.get("id"),
                        "html_url": resp.get("html_url"),
                    }
                    envelope["next_step"] = {
                        "action": "comment_posted",
                        "url": resp.get("html_url"),
                        "comment_id": resp.get("id"),
                    }
                else:
                    envelope["auto_post_result"] = {
                        "ok": False,
                        "status": status,
                        "error": resp,
                    }

        return json.dumps(envelope, indent=2)
