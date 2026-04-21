"""
recall_memory_agent.py — read back what was saved, optionally filter by keyword.

Renamed from context_memory_agent for clarity: this agent READS what
save_memory wrote. Also defines system_context() so the brainstem
auto-injects the user's stored memories into every system prompt.
"""

import json
from agents.basic_agent import BasicAgent


__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "@rapp/recall_memory",
    "version": "1.0.0",
    "display_name": "Recall Memory",
    "description": "Reads previously-saved memories. Auto-injects stored memories into context.",
    "author": "RAPP",
    "tags": ["starter", "memory", "retrieval"],
    "category": "core",
    "quality_tier": "official",
    "requires_env": [],
    "example_call": "What do you remember about me?",
}


_MEM_KEY = "rapp_memory_v1"

def _memory_path():
    """Where this process's memory lives — swarm server overrides via env."""
    import os
    p = os.environ.get("BRAINSTEM_MEMORY_PATH")
    return p if p else os.path.expanduser("~/.brainstem/memory.json")


def _read_memory():
    try:
        from js import localStorage  # type: ignore
        raw = localStorage.getItem(_MEM_KEY)
        return json.loads(raw) if raw else {}
    except Exception:
        import os
        path = _memory_path()
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return {}


class RecallMemoryAgent(BasicAgent):
    def __init__(self):
        self.name = "RecallMemory"
        self.metadata = {
            "name": self.name,
            "description": (
                "Recalls previously-saved memories. Call this when the user asks "
                "what you remember about them, asks for facts they shared earlier, "
                "or wants you to use prior context. Optionally filter by keywords."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional keywords to filter memories by content or tag.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Max number of memories to return. Default 20.",
                        "minimum": 1,
                        "maximum": 200,
                    },
                },
                "required": [],
            },
        }
        super().__init__(name=self.name, metadata=self.metadata)

    def system_context(self):
        """Inject stored memories into the system prompt every turn (SPEC §6)."""
        memories = _read_memory()
        if not memories:
            return None
        items = list(memories.values())
        items.sort(key=lambda m: (m.get("date", ""), m.get("time", "")), reverse=True)
        items = items[:50]
        lines = [f'- [{m.get("type", "fact")}] {m.get("content", "")}' for m in items]
        return (
            "<memory>\n" + "\n".join(lines) + "\n</memory>\n"
            "<memory_instructions>\n"
            "- The above are stored memories from previous conversations.\n"
            "- Use them to provide continuity and personalized responses.\n"
            "- When the user asks what you remember, reference these memories directly.\n"
            "</memory_instructions>"
        )

    def perform(self, **kwargs):
        keywords = [k.lower() for k in (kwargs.get("keywords") or [])]
        max_results = int(kwargs.get("max_results", 20))

        memories = _read_memory()
        if not memories:
            return json.dumps({
                "status": "success",
                "summary": "No memories stored yet.",
                "memories": [],
                "data_slush": {"count": 0},
            })

        items = list(memories.values())
        if keywords:
            def match(m):
                hay = (m.get("content", "") + " " + " ".join(m.get("tags", []))).lower()
                return any(kw in hay for kw in keywords)
            items = [m for m in items if match(m)]

        items.sort(key=lambda m: (m.get("date", ""), m.get("time", "")), reverse=True)
        items = items[:max_results]

        if not items:
            return json.dumps({
                "status": "success",
                "summary": f"No memories match {keywords}.",
                "memories": [],
                "data_slush": {"count": 0, "keywords": keywords},
            })

        lines = [f'- [{m.get("type", "fact")}] {m.get("content", "")} ({m.get("date", "?")})' for m in items]
        return json.dumps({
            "status": "success",
            "summary": f"Found {len(items)} memor{'y' if len(items) == 1 else 'ies'}:\n" + "\n".join(lines),
            "memories": items,
            "data_slush": {"count": len(items), "keywords": keywords},
        })
