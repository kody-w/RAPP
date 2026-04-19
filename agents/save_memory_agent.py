"""
save_memory_agent.py — store a fact, preference, or task to persistent memory.

Renamed from manage_memory_agent for clarity: this agent SAVES, the
recall_memory agent READS. Single file, browser- and server-friendly:
falls back from JS localStorage (Pyodide) to a JSON file (real Python).
"""

import json
import uuid
from datetime import datetime
from agents.basic_agent import BasicAgent


__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "@rapp/save_memory",
    "version": "1.0.0",
    "display_name": "Save Memory",
    "description": "Saves a fact, preference, insight, or task to persistent memory.",
    "author": "RAPP",
    "tags": ["starter", "memory", "storage"],
    "category": "core",
    "quality_tier": "official",
    "requires_env": [],
    "example_call": "Remember that my name is Kody and I work on RAPP.",
}


# ── Storage shim: prefer browser localStorage (Pyodide), fall back to disk. ──

_MEM_KEY = "rapp_memory_v1"

def _read_memory():
    try:
        from js import localStorage  # type: ignore
        raw = localStorage.getItem(_MEM_KEY)
        return json.loads(raw) if raw else {}
    except Exception:
        import os
        path = os.path.expanduser("~/.brainstem/memory.json")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return {}


def _write_memory(data):
    try:
        from js import localStorage  # type: ignore
        localStorage.setItem(_MEM_KEY, json.dumps(data))
        return
    except Exception:
        pass
    import os
    path = os.path.expanduser("~/.brainstem/memory.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


class SaveMemoryAgent(BasicAgent):
    def __init__(self):
        self.name = "SaveMemory"
        self.metadata = {
            "name": self.name,
            "description": (
                "Saves information to persistent memory for future conversations. "
                "Call this whenever the user asks you to remember something, "
                "shares personal facts (name, preferences, birthdays), or tells "
                "you something they expect you to recall later. Do not just "
                "acknowledge — call this tool or the information will be lost."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "memory_type": {
                        "type": "string",
                        "description": "Category of memory to store.",
                        "enum": ["fact", "preference", "insight", "task"],
                    },
                    "content": {
                        "type": "string",
                        "description": "The actual content to remember. Be concise but precise.",
                    },
                    "importance": {
                        "type": "integer",
                        "description": "Importance rating 1–5 (5 = critical).",
                        "minimum": 1,
                        "maximum": 5,
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional tags for later retrieval.",
                    },
                },
                "required": ["memory_type", "content"],
            },
        }
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        memory_type = kwargs.get("memory_type", "fact")
        content = (kwargs.get("content") or "").strip()
        importance = int(kwargs.get("importance", 3))
        tags = kwargs.get("tags") or []
        if not content:
            return json.dumps({"status": "error", "message": "no content provided"})

        memories = _read_memory()
        mid = str(uuid.uuid4())
        now = datetime.now()
        memories[mid] = {
            "id": mid,
            "type": memory_type,
            "content": content,
            "importance": importance,
            "tags": tags,
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
        }
        _write_memory(memories)
        return json.dumps({
            "status": "success",
            "id": mid,
            "summary": f'Saved {memory_type}: "{content}"',
            "data_slush": {"saved_id": mid, "memory_type": memory_type, "importance": importance},
        })
