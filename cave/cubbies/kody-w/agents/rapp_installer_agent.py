"""Fail-closed tombstone for the retired Cave RAPP Installer agent."""

from agents.basic_agent import BasicAgent


REFUSAL = (
    "410 Gone: the Cave RAPP Installer agent is retired. It will not provide "
    "bootstrap commands, probe the legacy runtime, or expose prepared paths. "
    "See RAPP1_STATUS.md."
)


class RappInstallerAgent(BasicAgent):
    def __init__(self):
        self.name = "RappInstaller"
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
