"""Fail-closed tombstone for the retired Cave RAR steward."""

try:
    from agents.basic_agent import BasicAgent  # type: ignore
except ImportError:
    try:
        from basic_agent import BasicAgent  # type: ignore
    except ImportError:
        class BasicAgent:
            def __init__(self, name="Agent", metadata=None):
                self.name = name
                self.metadata = metadata or {}


__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "@rapp/rar_steward",
    "version": "1.0.0",
    "display_name": "RarStewardAgent (retired)",
    "description": "Retired capability. Every invocation is refused.",
    "status": "retired",
    "active_distribution": False,
    "streamable": False,
    "dependencies": [],
}

REFUSAL = (
    "410 Gone: the Cave RAR steward is retired. It will not fetch moving "
    "catalogs, create GitHub issues, curate entries, install artifacts, or "
    "perform network or repository side effects. See RAPP1_AUTHORITY.json "
    "and RAPP1_STATUS.md."
)


class RarStewardAgent(BasicAgent):
    def __init__(self):
        self.name = "RarStewardAgent"
        self.metadata = {
            "name": self.name,
            "description": "Retired capability. Every invocation is refused.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        }
        super().__init__(self.name, self.metadata)

    def system_context(self):
        return (
            "RarStewardAgent is retired and must not be used for catalog "
            "discovery, issue creation, installation, or curation."
        )

    def perform(self, **_kwargs):
        raise RuntimeError(REFUSAL)
