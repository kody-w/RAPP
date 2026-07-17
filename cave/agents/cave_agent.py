"""Fail-closed tombstone for the retired public Cave agent."""

from agents.basic_agent import BasicAgent


REFUSAL = (
    "410 Gone: the target-owned Cave capability is retired and will not "
    "clone, import, verify, or execute agents. See RAPP1_STATUS.md."
)


class CaveAgent(BasicAgent):
    def __init__(self):
        self.name = "Cave"
        self.metadata = {
            "name": self.name,
            "description": "Retired capability. Every invocation is refused.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        }

    def perform(self, **_kwargs):
        raise RuntimeError(REFUSAL)
