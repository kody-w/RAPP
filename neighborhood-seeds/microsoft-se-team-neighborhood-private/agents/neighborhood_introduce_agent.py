"""
neighborhood_introduce_agent.py — member-aware introduction.

Reads neighborhood.json + members.json from the seed root and returns a
summary that names current members. Only mountable inside a member's
brainstem (the private companion is GitHub-collaborator-gated, so reading
this file at all means you're inside the trust boundary).
"""
import json
import os

from agents.basic_agent import BasicAgent


class NeighborhoodIntroduceAgent(BasicAgent):
    name = "neighborhood_introduce"
    metadata = {
        "name": "neighborhood_introduce",
        "description": "Tell the operator who is in this neighborhood, what each member brings, and how the workflow is set up. Member-aware version — names roster.",
        "parameters": {
            "type": "object",
            "properties": {
                "include_capabilities": {
                    "type": "boolean",
                    "description": "Include each member's declared capabilities in the introduction."
                }
            },
            "required": []
        }
    }

    def _seed_dir(self):
        return os.environ.get("NEIGHBORHOOD_SEED_DIR", os.getcwd())

    def _load_json(self, filename):
        try:
            with open(os.path.join(self._seed_dir(), filename), "r") as f:
                return json.load(f)
        except (FileNotFoundError, ValueError):
            return None

    def perform(self, include_capabilities=False, **kwargs):
        n = self._load_json("neighborhood.json") or {}
        m = self._load_json("members.json") or {}

        display = n.get("display_name") or n.get("name") or "this neighborhood"
        purpose = (n.get("purpose") or "").strip()
        members = m.get("members") or []

        lines = [f"**{display}** — {len(members)} member(s)."]
        if purpose:
            lines.append("")
            lines.append(purpose)

        if members:
            lines.append("")
            lines.append("Roster:")
            for mem in members:
                login = mem.get("github_login", "?")
                role = mem.get("role", "member")
                rappid = mem.get("rappid") or "(rappid not yet bound)"
                line = f"  - @{login} ({role}) — {rappid}"
                if include_capabilities:
                    caps = mem.get("capabilities") or []
                    if caps:
                        line += f" — capabilities: {', '.join(caps)}"
                lines.append(line)

        gate = n.get("gate_repo") or {}
        if gate.get("repo"):
            lines.append("")
            lines.append(f"Public gate: {gate['repo']}")

        return "\n".join(lines)
