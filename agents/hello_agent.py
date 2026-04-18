"""
hello_agent.py — the simplest possible RAPP v1 agent. Echoes a greeting.

Use this as your reference when writing your first agent. If you can read
this file, you can write a RAPP agent. That is the entire point.
"""

import json
from agents.basic_agent import BasicAgent


__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "@rapp/hello",
    "version": "1.0.0",
    "display_name": "Hello",
    "description": "The smallest possible RAPP agent. Echoes a greeting.",
    "author": "RAPP",
    "tags": ["starter", "demo", "echo"],
    "category": "core",
    "quality_tier": "official",
    "requires_env": [],
}


class HelloAgent(BasicAgent):
    def __init__(self):
        self.name = "Hello"
        self.metadata = {
            "name": self.name,
            "description": "Greets the caller. Pass a 'who' to personalize.",
            "parameters": {
                "type": "object",
                "properties": {
                    "who": {"type": "string", "description": "Name to greet."}
                },
                "required": [],
            },
        }
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        who = kwargs.get("who", "world").strip() or "world"
        return json.dumps(
            {
                "status": "success",
                "message": f"Hello, {who}! Welcome to RAPP v1.",
                "data_slush": {"greeted": who},
            }
        )
