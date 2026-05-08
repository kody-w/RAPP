"""workspace_init_agent.py — bootstrap a fresh private workspace.

Writes the founder's first decision narrative ("Why this workspace exists")
to state/decisions/0001-<slug>.md so future-me has the context for what this
workspace is for. Idempotent — refuses to overwrite an existing 0001."""
import json
import os
import time

from agents.basic_agent import BasicAgent


class WorkspaceInitAgent(BasicAgent):
    name = "workspace_init"
    metadata = {
        "name": "workspace_init",
        "description": "Bootstrap a freshly-planted private workspace by writing the founder's first decision (`Why this workspace exists`). Idempotent.",
        "parameters": {
            "type": "object",
            "properties": {
                "purpose": {"type": "string", "description": "One paragraph on why this workspace exists."},
                "founder_login": {"type": "string", "description": "Founder's GitHub login."}
            },
            "required": ["purpose", "founder_login"]
        }
    }

    def _seed_dir(self):
        return os.environ.get("NEIGHBORHOOD_SEED_DIR", os.getcwd())

    def perform(self, purpose, founder_login, **kwargs):
        decisions_dir = os.path.join(self._seed_dir(), "state", "decisions")
        os.makedirs(decisions_dir, exist_ok=True)
        path = os.path.join(decisions_dir, "0001-why-this-workspace.md")
        if os.path.exists(path):
            return json.dumps({"status": "noop", "reason": "0001 decision already exists", "path": path})

        ts = time.strftime("%Y-%m-%d", time.gmtime())
        body = (
            f"# Decision 0001 — Why this workspace exists\n\n"
            f"**Date:** {ts}\n"
            f"**Status:** Adopted\n"
            f"**Decided by:** @{founder_login} (founder)\n\n"
            f"## Purpose\n\n{purpose.strip()}\n\n"
            f"## How this gets used\n\n"
            f"This workspace runs solo until the founder grants additional collaborator access. "
            f"All decisions land in `state/decisions/`. Async work products from federated agents "
            f"land in `state/inbox/`. The workspace agents (init / decision / invite / inbox) "
            f"are the only auto-mounted toolkit.\n"
        )
        try:
            with open(path, "w") as f:
                f.write(body)
        except OSError as e:
            return json.dumps({"status": "error", "error": str(e)})
        return json.dumps({"status": "ok", "wrote": path, "schema": "rapp-workspace-decision/1.0"})
