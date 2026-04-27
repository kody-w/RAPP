"""binder_agent.py — chat-callable surface for the binder package manager.

Kernel-baked alongside binder_service.py per Article XXVII.4 (this is a
bare agent that ships with the brainstem because it's the bootstrap
loader for everything else — it can't be installed via the catalog
because it IS the installer). Closes kody-w/RAPP#22.

Talks to all three stores in the RAPP ecosystem (Article XXVII / XXXI):

    rapplications  → kody-w/RAPP_Store
    bare agents    → kody-w/RAR
    senses         → kody-w/RAPP_Sense_Store

Delegates to binder_service.handle() in-process — no HTTP loopback,
keeps Tier 1 lean.
"""
from __future__ import annotations

import json

from agents.basic_agent import BasicAgent


__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "@rapp/binder",
    "display_name": "Binder",
    "version": "1.1.0",
    "description": (
        "Browse and install RAPP artifacts from the three peer stores: "
        "rapplications (kody-w/RAPP_Store), bare agents (kody-w/RAR), and "
        "senses (kody-w/RAPP_Sense_Store). Use this whenever the user "
        "wants to install, remove, or browse anything that lives in those "
        "stores."
    ),
    "author": "RAPP",
    "tags": ["package-manager", "store", "platform", "kernel-baked"],
    "category": "platform",
    "quality_tier": "official",
    "requires_env": [],
    "example_call": {"args": {"action": "browse"}},
}


class BinderAgent(BasicAgent):
    def __init__(self):
        self.name = "Binder"
        self.metadata = {
            "name": "binder",
            "description": (
                "Package manager for the RAPP three-store ecosystem. Browse "
                "or install rapplications (bundled apps with UI / service / "
                "eggs), bare agents (single-file *_agent.py), or senses "
                "(per-channel output overlays). Calls the local "
                "binder_service in-process — no HTTP roundtrip. Use this "
                "whenever the user wants to add, remove, or discover any "
                "RAPP artifact."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "list",
                            "browse",
                            "browse_agents",
                            "browse_senses",
                            "browse_all",
                            "install",
                            "install_agent",
                            "install_sense",
                            "uninstall",
                            "uninstall_agent",
                            "uninstall_sense",
                        ],
                        "description": (
                            "list                — what's installed (all kinds)\n"
                            "browse              — rapplication catalog\n"
                            "browse_agents       — bare-agent registry (RAR)\n"
                            "browse_senses       — sense catalog\n"
                            "browse_all          — aggregated three-store view\n"
                            "install <id>        — rapplication by id\n"
                            "install_agent <name>— bare agent by '@publisher/slug'\n"
                            "install_sense <name>— sense by slug\n"
                            "uninstall* — the matching reverse"
                        ),
                    },
                    "id": {
                        "type": "string",
                        "description": "Rapplication id (for install / uninstall).",
                    },
                    "name": {
                        "type": "string",
                        "description": (
                            "Agent name '@publisher/slug' (for install_agent / "
                            "uninstall_agent) or sense name (for install_sense / "
                            "uninstall_sense)."
                        ),
                    },
                },
                "required": ["action"],
            },
        }
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        # Lazy import so the brainstem can load binder_agent before the
        # services dir is even on sys.path. binder_service is kernel-baked
        # in utils/services/, sibling to this file.
        try:
            from utils.services.binder_service import handle
        except ImportError:
            try:
                # Path fallback if imports are mounted differently in
                # alternate brainstem layouts (Tier 2/3, openrappter).
                import importlib, sys, os
                sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from utils.services.binder_service import handle
            except Exception as e:
                return json.dumps({"error": f"binder_service unavailable: {e}"})

        action = kwargs.get("action")
        rid = kwargs.get("id", "")
        name = kwargs.get("name", "")

        # Map action → (HTTP method, path, body)
        if action == "list":
            method, path, body = "GET", "", None
        elif action == "browse":
            method, path, body = "GET", "catalog", None
        elif action == "browse_agents":
            method, path, body = "GET", "catalog/agents", None
        elif action == "browse_senses":
            method, path, body = "GET", "catalog/senses", None
        elif action == "browse_all":
            method, path, body = "GET", "catalog/all", None
        elif action == "install":
            if not rid:
                return json.dumps({"error": "id required for action=install"})
            method, path, body = "POST", "install", {"id": rid}
        elif action == "install_agent":
            if not name:
                return json.dumps({"error": "name required (e.g. '@rapp/learn_new')"})
            method, path, body = "POST", "install/agent", {"name": name}
        elif action == "install_sense":
            if not name:
                return json.dumps({"error": "name required (sense slug)"})
            method, path, body = "POST", "install/sense", {"name": name}
        elif action == "uninstall":
            if not rid:
                return json.dumps({"error": "id required for action=uninstall"})
            method, path, body = "DELETE", f"installed/{rid}", None
        elif action == "uninstall_agent":
            if not name:
                return json.dumps({"error": "name required"})
            method, path, body = "DELETE", f"installed/agent/{name}", None
        elif action == "uninstall_sense":
            if not name:
                return json.dumps({"error": "name required"})
            method, path, body = "DELETE", f"installed/sense/{name}", None
        else:
            return json.dumps({"error": f"unknown action: {action}"})

        try:
            result = handle(method, path, body)
        except Exception as e:
            return json.dumps({"error": f"binder_service.handle failed: {e}"})

        # binder_service returns either (body, status) or (body, status, headers)
        if isinstance(result, tuple):
            payload = result[0]
        else:
            payload = result

        if isinstance(payload, (dict, list)):
            return json.dumps(payload, default=str)
        return str(payload)
