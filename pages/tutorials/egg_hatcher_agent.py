"""Retired tutorial egg hatcher.

The former implementation accepted nonconformant cartridges and could mutate
local state without authenticated RAPP/1 acceptance. This agent is retained
only as a fail-closed retirement marker.
"""

from agents.basic_agent import BasicAgent


RETIREMENT_NOTICE = (
    "410 Gone: this nonconformant egg hatcher is retired and performed no "
    "inspection, extraction, or import. See RAPP1_STATUS.md."
)

__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "@rapp/egg_hatcher",
    "version": "retired",
    "display_name": "EggHatcher (retired)",
    "description": RETIREMENT_NOTICE,
    "author": "RAPP",
    "tags": ["retired", "egg"],
    "category": "retired",
    "quality_tier": "retired",
    "requires_env": [],
    "dependencies": ["@rapp/basic_agent"],
}


class EggHatcherAgent(BasicAgent):
    def __init__(self):
        self.name = "HatchEgg"
        self.metadata = {
            "name": self.name,
            "description": RETIREMENT_NOTICE,
            "parameters": {
                "type": "object",
                "properties": {
                    "egg_path": {
                        "type": "string",
                        "description": "Ignored because this agent is retired.",
                    }
                },
                "required": [],
            },
        }
        super().__init__(self.name, self.metadata)

    def perform(self, **kwargs) -> str:
        return RETIREMENT_NOTICE
