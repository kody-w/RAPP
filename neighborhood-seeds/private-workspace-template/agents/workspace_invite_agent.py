"""workspace_invite_agent.py — compose the exact `gh api` command for granting access.

The trust anchor is GitHub collaborator status. There is no separate auth.
This agent does NOT call the API itself — it returns the exact command the
operator (founder, admin) runs to grant access. Audit-friendly by design."""
import json
import os

from agents.basic_agent import BasicAgent


class WorkspaceInviteAgent(BasicAgent):
    name = "workspace_invite"
    metadata = {
        "name": "workspace_invite",
        "description": "Generate the exact `gh api` command to add a new collaborator to this private workspace. Returns the command for the operator to run; does not execute it.",
        "parameters": {
            "type": "object",
            "properties": {
                "github_login": {"type": "string", "description": "The login to add."},
                "permission": {
                    "type": "string",
                    "enum": ["pull", "push", "admin"],
                    "description": "Permission level (push is the default workspace member level)."
                },
                "reason": {"type": "string", "description": "Optional — note for the audit log."}
            },
            "required": ["github_login"]
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

    def perform(self, github_login, permission="push", reason=None, **kwargs):
        slug = self._gate_slug() or "<owner>/<repo>"
        cmd = (
            f"gh api -X PUT /repos/{slug}/collaborators/{github_login} "
            f"-f permission={permission}"
        )
        return json.dumps({
            "schema": "rapp-workspace-invite-envelope/1.0",
            "subject_login": github_login,
            "permission": permission,
            "reason": reason,
            "command": cmd,
            "next_step": (
                f"Run the command above. {github_login} accepts the invite via email "
                f"or `gh repo accept-invitation`. Their brainstem then subscribes via "
                f"`brainstem join https://github.com/{slug}` and the workspace agents auto-mount."
            ),
        }, indent=2)
