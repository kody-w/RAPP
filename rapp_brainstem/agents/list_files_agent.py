"""
list_files_agent.py — sample tether-required agent.

Demonstrates the contract: an agent that needs OS access (filesystem in
this case) declares `tether_required: true` in its __manifest__. The chat
loop sees that flag and routes the tool call through the local tether
process. If the tether isn't running, the LLM gets a graceful error and
can tell the user to start it.

Without `tether_required`, this agent would just run as an in-browser
stub returning its description — useless for actually listing files.
"""
from agents.basic_agent import BasicAgent
import os


__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "@rapp/list-files",
    "tier": "core",
    "trust": "community",
    "version": "0.1.0",
    "tags": ["tether", "filesystem"],
    "tether_required": True,
    "example_call": {"args": {"path": "~/Documents"}},
}


class ListFilesAgent(BasicAgent):
    def __init__(self):
        self.name = "ListFiles"
        self.metadata = {
            "name": self.name,
            "description": "List files and folders at a local path. "
                           "Requires the local tether (real filesystem access).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path or ~-prefixed home path",
                    },
                    "max_entries": {
                        "type": "integer",
                        "description": "Cap on entries returned (default 50)",
                    },
                },
                "required": ["path"],
            },
            "tether_required": True,
        }
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, path="~", max_entries=50, **kwargs):
        target = os.path.expanduser(str(path))
        if not os.path.exists(target):
            return f"Path not found: {target}"
        if not os.path.isdir(target):
            return f"Not a directory: {target}"
        try:
            entries = sorted(os.listdir(target))[: int(max_entries)]
        except PermissionError:
            return f"Permission denied: {target}"
        rows = []
        for e in entries:
            full = os.path.join(target, e)
            kind = "/" if os.path.isdir(full) else ""
            try:
                size = os.path.getsize(full)
            except OSError:
                size = 0
            rows.append(f"  {e}{kind}  ({size}b)")
        return f"Listing {target} ({len(entries)} entries):\n" + "\n".join(rows)
