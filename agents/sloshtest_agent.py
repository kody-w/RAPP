"""
sloshtest_agent.py — demonstrates data_slush chaining (SPEC §5.4, §6).

Reads `self.context.slush` (signals from the upstream agent in a chain) and
formats them. If you call this right after WeatherPoet, it picks up mood,
temp_f, city automatically — no LLM in the middle.
"""

import json
from agents.basic_agent import BasicAgent


__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "@rapp/sloshtest",
    "version": "1.0.0",
    "display_name": "Slosh Test",
    "description": "Reports the upstream data_slush context. Chain primer.",
    "author": "RAPP",
    "tags": ["starter", "chain", "diagnostic"],
    "category": "core",
    "quality_tier": "official",
    "requires_env": [],
}


class SloshTestAgent(BasicAgent):
    def __init__(self):
        self.name = "SloshTest"
        self.metadata = {
            "name": self.name,
            "description": "Echoes the upstream slush from the previous agent in the chain.",
            "parameters": {
                "type": "object",
                "properties": {
                    "label": {"type": "string", "description": "Optional label for the report."}
                },
                "required": [],
            },
        }
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        label = kwargs.get("label") or "slosh report"
        slush = (self.context or {}).get("slush") or {}
        return json.dumps(
            {
                "status": "success",
                "label": label,
                "received_slush": slush,
                "summary": f"{label}: {len(slush)} signal(s) from upstream — {list(slush.keys())}",
                "data_slush": {"reported": True, "upstream_keys": list(slush.keys())},
            }
        )
