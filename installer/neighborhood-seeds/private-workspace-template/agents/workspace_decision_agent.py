"""workspace_decision_agent.py — log a decision narrative.

Appends a numbered decision to state/decisions/. Auto-numbers from existing files."""
import json
import os
import re
import time

from agents.basic_agent import BasicAgent


class WorkspaceDecisionAgent(BasicAgent):
    name = "workspace_decision"
    metadata = {
        "name": "workspace_decision",
        "description": "Log a decision narrative to state/decisions/<n>-<slug>.md. Use when the operator (or another agent) makes a non-trivial choice that future-us should be able to recover.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Short title (becomes the slug)."},
                "decided_by": {"type": "string", "description": "GitHub login of the decider."},
                "decision": {"type": "string", "description": "What was decided."},
                "why": {"type": "string", "description": "Why this decision over alternatives."},
                "alternatives_rejected": {"type": "string", "description": "Optional — what was considered and why rejected."}
            },
            "required": ["title", "decided_by", "decision", "why"]
        }
    }

    def _seed_dir(self):
        return os.environ.get("NEIGHBORHOOD_SEED_DIR", os.getcwd())

    def _next_number(self, decisions_dir):
        if not os.path.isdir(decisions_dir):
            return 1
        nums = []
        pat = re.compile(r"^(\d{4})-")
        for name in os.listdir(decisions_dir):
            m = pat.match(name)
            if m:
                nums.append(int(m.group(1)))
        return (max(nums) if nums else 0) + 1

    def _slugify(self, s):
        out = []
        for c in (s or "").lower():
            if c.isalnum():
                out.append(c)
            elif c in (" ", "-", "_"):
                out.append("-")
        return ("".join(out).strip("-") or "decision")[:48]

    def perform(self, title, decided_by, decision, why, alternatives_rejected=None, **kwargs):
        decisions_dir = os.path.join(self._seed_dir(), "state", "decisions")
        os.makedirs(decisions_dir, exist_ok=True)
        n = self._next_number(decisions_dir)
        slug = self._slugify(title)
        filename = f"{n:04d}-{slug}.md"
        path = os.path.join(decisions_dir, filename)
        ts = time.strftime("%Y-%m-%d", time.gmtime())
        sections = [
            f"# Decision {n:04d} — {title}",
            "",
            f"**Date:** {ts}",
            f"**Status:** Adopted",
            f"**Decided by:** @{decided_by}",
            "",
            "## Decision",
            "",
            decision.strip(),
            "",
            "## Why",
            "",
            why.strip(),
        ]
        if alternatives_rejected:
            sections += ["", "## Alternatives rejected", "", alternatives_rejected.strip()]
        try:
            with open(path, "w") as f:
                f.write("\n".join(sections) + "\n")
        except OSError as e:
            return json.dumps({"status": "error", "error": str(e)})
        return json.dumps({
            "status": "ok",
            "wrote": path,
            "number": n,
            "slug": slug,
            "schema": "rapp-workspace-decision/1.0",
        })
