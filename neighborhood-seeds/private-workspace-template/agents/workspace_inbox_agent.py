"""workspace_inbox_agent.py — surface async work products that landed in the inbox.

The inbox is state/inbox/<utc>-<from-rappid>.json. Federated agents drop their
work products here, attributed to whichever operator's rappid did the work. This
agent reads + summarizes; doesn't delete (operator decides what to acknowledge)."""
import json
import os

from agents.basic_agent import BasicAgent


class WorkspaceInboxAgent(BasicAgent):
    name = "workspace_inbox"
    metadata = {
        "name": "workspace_inbox",
        "description": "List async work products that landed in the workspace inbox while you were away. Each item is attributed to the operator-rappid that produced it.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max items to return. Defaults to 25."},
                "from_login": {"type": "string", "description": "Optional — filter to one contributor's items."}
            },
            "required": []
        }
    }

    def _seed_dir(self):
        return os.environ.get("NEIGHBORHOOD_SEED_DIR", os.getcwd())

    def perform(self, limit=25, from_login=None, **kwargs):
        inbox_dir = os.path.join(self._seed_dir(), "state", "inbox")
        if not os.path.isdir(inbox_dir):
            return json.dumps({
                "schema": "rapp-workspace-inbox-report/1.0",
                "count": 0,
                "items": [],
                "note": "Inbox is empty — no async work products yet.",
            }, indent=2)

        items = []
        for name in sorted(os.listdir(inbox_dir), reverse=True):
            if not name.endswith(".json"):
                continue
            path = os.path.join(inbox_dir, name)
            try:
                with open(path, "r") as f:
                    item = json.load(f)
            except (ValueError, OSError):
                continue
            if from_login and (item.get("from_login") or "").lower() != from_login.lower():
                continue
            item["_filename"] = name
            items.append(item)
            if len(items) >= int(limit or 25):
                break

        return json.dumps({
            "schema": "rapp-workspace-inbox-report/1.0",
            "count": len(items),
            "items": items,
        }, indent=2)
