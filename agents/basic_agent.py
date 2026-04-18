"""
basic_agent.py — the canonical RAPP v1 base class.

This is the only "framework" code a single-file agent inherits. Drop it in
your agents/ directory once. Every other *_agent.py file extends BasicAgent
and is otherwise self-contained.

The base class is intentionally tiny. RAPP's contract lives in §5 of SPEC.md.
"""


class BasicAgent:
    """Base class for all RAPP v1 agents. Extend this in single-file *_agent.py files."""

    def __init__(self, name=None, metadata=None):
        if name is not None:
            self.name = name
        elif not hasattr(self, "name"):
            self.name = "BasicAgent"
        if metadata is not None:
            self.metadata = metadata
        elif not hasattr(self, "metadata"):
            self.metadata = {
                "name": self.name,
                "description": "Base agent — override this.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            }
        # Implicit context (data sloshing) — populated by the runtime before perform()
        self.context = {}

    def perform(self, **kwargs):
        return "Not implemented."

    def system_context(self):
        """Optional: return a string injected into the system prompt each turn."""
        return None

    def to_tool(self):
        """OpenAI function-calling tool definition."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.metadata.get("description", ""),
                "parameters": self.metadata.get(
                    "parameters", {"type": "object", "properties": {}}
                ),
            },
        }
