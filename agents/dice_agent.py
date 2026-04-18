"""
dice_agent.py — rolls dice. Demonstrates parameter validation and data_slush.

A handy chain primer: pipe the rolled total into the next agent via
data_slush.total — whatever follows can use the number without the LLM
having to re-parse a sentence.
"""

import json
import random
from agents.basic_agent import BasicAgent


__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "@rapp/dice",
    "version": "1.0.0",
    "display_name": "Dice",
    "description": "Rolls N dice with S sides. Returns rolls + total.",
    "author": "RAPP",
    "tags": ["starter", "random", "game"],
    "category": "general",
    "quality_tier": "official",
    "requires_env": [],
}


class DiceAgent(BasicAgent):
    def __init__(self):
        self.name = "Dice"
        self.metadata = {
            "name": self.name,
            "description": "Roll N dice, each with S sides. Returns the individual rolls and the total.",
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {"type": "integer", "description": "How many dice to roll. 1–100.", "minimum": 1, "maximum": 100},
                    "sides": {"type": "integer", "description": "Sides per die. Default 6.", "minimum": 2, "maximum": 1000},
                },
                "required": [],
            },
        }
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        count = max(1, min(100, int(kwargs.get("count", 1) or 1)))
        sides = max(2, min(1000, int(kwargs.get("sides", 6) or 6)))
        rolls = [random.randint(1, sides) for _ in range(count)]
        total = sum(rolls)
        return json.dumps(
            {
                "status": "success",
                "rolls": rolls,
                "total": total,
                "summary": f"Rolled {count}d{sides}: {rolls} → {total}",
                "data_slush": {"total": total, "count": count, "sides": sides},
            }
        )
