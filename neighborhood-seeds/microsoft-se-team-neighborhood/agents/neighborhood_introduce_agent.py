"""
neighborhood_introduce_agent.py — public-safe "tell me about this neighborhood"
agent. Reads neighborhood.json + facets.json from the seed root and returns a
human-friendly summary suitable for anonymous visitors. Reveals only public
facets; never enumerates members or internal workflow.
"""
import json
import os

from agents.basic_agent import BasicAgent


class NeighborhoodIntroduceAgent(BasicAgent):
    name = "neighborhood_introduce"
    metadata = {
        "name": "neighborhood_introduce",
        "description": "Tell a visitor what this neighborhood is, who runs it, and what's behind the gate. Public-safe — does not reveal members, agents, or internal workflow.",
        "parameters": {
            "type": "object",
            "properties": {
                "verbosity": {
                    "type": "string",
                    "enum": ["brief", "full"],
                    "description": "brief = one-paragraph summary; full = include lineage and join path"
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

    def perform(self, verbosity="brief", **kwargs):
        n = self._load_json("neighborhood.json")
        if not n:
            return "This gate is not yet populated — neighborhood.json is missing."

        display = n.get("display_name") or n.get("name") or "this neighborhood"
        kind = n.get("kind", "neighborhood")
        planted_by = n.get("planted_by", "unknown")
        purpose = n.get("purpose", "").strip()

        intro = f"This is **{display}** — a {kind} planted by @{planted_by}."
        if purpose:
            intro += f" {purpose}"

        if verbosity == "brief":
            return intro

        lines = [intro, ""]
        pc = n.get("private_companion") or {}
        if pc.get("repo"):
            lines.append(
                f"The workflow lives in a private companion repo: {pc['repo']}. "
                "To join, open an Issue on this gate repo requesting access; a current "
                "member can add you as a GitHub collaborator on the private companion."
            )
        if n.get("parent_repo"):
            lines.append(f"\nLineage: planted from `{n['parent_repo']}`.")

        facets = self._load_json("facets.json") or {}
        public_facet_names = [
            f["name"]
            for f in facets.get("public_facets", [])
            if f.get("scope") == "public"
        ]
        if public_facet_names:
            lines.append("\nPublicly visible facets: " + ", ".join(public_facet_names) + ".")

        return "\n".join(lines)
