"""braintrust_contribute_agent.py — run library_query against an active request and post findings.

Loads the in-process library_query_agent (which the operator may have
overridden locally), runs it against the request topic, packages findings
into a `rapp-braintrust-contribution/1.0` envelope, and returns the
GitHub Issue-comment payload that posts the contribution back.

If library_query returns no findings, the agent still posts a polite
'no contribution from this librarian' record so the synthesizer knows
this contributor is online and doesn't have anything — distinct from
'this contributor never responded'."""
import importlib.util
import json
import os
import time
import urllib.parse

from agents.basic_agent import BasicAgent


class BraintrustContributeAgent(BasicAgent):
    name = "braintrust_contribute"
    metadata = {
        "name": "braintrust_contribute",
        "description": "Pick up an active braintrust request, run THIS operator's library_query against it, and post the contribution back to the request Issue with full provenance.",
        "parameters": {
            "type": "object",
            "properties": {
                "request_id": {"type": "string", "description": "The braintrust request ID (8-char hex)."},
                "topic": {"type": "string", "description": "The request topic — passed through to library_query."},
                "scope": {"type": "string", "description": "Optional narrowing scope."},
                "contributor_login": {"type": "string", "description": "This contributor's GitHub login."},
                "contributor_rappid": {"type": "string", "description": "This contributor's personal organism rappid."},
                "issue_number": {"type": "integer", "description": "GitHub Issue number for this request (if known)."}
            },
            "required": ["request_id", "topic", "contributor_login"]
        }
    }

    def _seed_dir(self):
        return os.environ.get("NEIGHBORHOOD_SEED_DIR", os.getcwd())

    def _load_library_query(self):
        """Resolve the operator's library_query_agent. Personal agents/ wins
        if present; otherwise neighborhood-shared default is used."""
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
                # Find the class extending BasicAgent
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
                contributor_rappid=None, issue_number=None, **kwargs):
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
                f"@{contributor_login} has no relevant findings for this request. Marking online-but-empty so synthesis is not blocked."
                if contribution["is_empty"] else
                f"Contribution from @{contributor_login} — {len(contribution['findings'])} finding(s)."
            )
        )

        slug = self._gate_slug() or "<owner>/<repo>"
        next_step = {
            "action": "post_contribution_comment",
            "comment_body_preview": comment_body[:400] + ("…" if len(comment_body) > 400 else ""),
        }
        if issue_number:
            next_step["api_alternative"] = (
                f"gh issue comment {issue_number} --repo {slug} --body-file <contribution.md>"
            )
        else:
            next_step["api_alternative"] = (
                f"gh issue list --repo {slug} --search 'in:title braintrust:{request_id}' "
                f"--json number,title  # then `gh issue comment <n> --body-file ...`"
            )

        return json.dumps({
            "schema": "rapp-braintrust-contribution-envelope/1.0",
            "contribution": contribution,
            "next_step": next_step,
        }, indent=2)
