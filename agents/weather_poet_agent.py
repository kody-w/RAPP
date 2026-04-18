"""
weather_poet_agent.py — the canonical RAPP example agent (SPEC §5.1).

Fetches "weather" (mocked deterministically per city for offline use) and
composes a haiku. Demonstrates the data_slush chaining convention from
SPEC §5.4: emit signals downstream agents can use without LLM re-parsing.
"""

import json
import hashlib
from agents.basic_agent import BasicAgent


__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "@rapp/weather_poet",
    "version": "1.0.0",
    "display_name": "Weather Poet",
    "description": "Fetches weather and writes a haiku. The canonical RAPP demo.",
    "author": "RAPP",
    "tags": ["starter", "weather", "creative"],
    "category": "productivity",
    "quality_tier": "official",
    "requires_env": [],
}


class WeatherPoetAgent(BasicAgent):
    def __init__(self):
        self.name = "WeatherPoet"
        self.metadata = {
            "name": self.name,
            "description": "Fetches weather for a city and composes a haiku about it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "City name to get weather for."}
                },
                "required": [],
            },
        }
        super().__init__(name=self.name, metadata=self.metadata)

    def fetch_weather(self, city):
        """Deterministic offline weather — same city always produces same conditions."""
        if not city:
            city = "Anywhere"
        h = int(hashlib.sha256(city.lower().encode()).hexdigest(), 16)
        conds = ["sunny", "cloudy", "rainy", "snowy", "windy", "foggy", "stormy"]
        cond = conds[h % len(conds)]
        temp = 20 + (h >> 8) % 75
        return {"city": city, "condition": cond, "temp_f": temp}

    def compose_haiku(self, w):
        templates = {
            "sunny":   ("Bright {city} morning,", "the sun pours over rooftops—", "warmth at {temp}, alive."),
            "cloudy":  ("Soft gray {city} sky,", "no shadow falls, no sharp light—", "{temp} degrees of hush."),
            "rainy":   ("Rain on {city} streets,", "each drop a small clean comma—", "{temp}, washed and new."),
            "snowy":   ("White {city} silence,", "footprints write a brief story—", "{temp}, the page goes blank."),
            "windy":   ("Wind through {city} trees,", "carrying voices of leaves—", "{temp}, restless and free."),
            "foggy":   ("Fog wraps {city} close,", "the world ends ten steps ahead—", "{temp}, soft and small."),
            "stormy":  ("Sky over {city}", "argues in flashes of light—", "{temp}, then it ends."),
        }
        t = templates.get(w["condition"], templates["sunny"])
        return "\n".join(line.format(city=w["city"], temp=w["temp_f"]) for line in t)

    def perform(self, **kwargs):
        query = (kwargs.get("query") or "").strip() or "Seattle"
        weather = self.fetch_weather(query)
        haiku = self.compose_haiku(weather)
        return json.dumps(
            {
                "status": "success",
                "haiku": haiku,
                "weather": weather,
                "data_slush": {
                    "mood": weather["condition"],
                    "temp_f": weather["temp_f"],
                    "city": weather["city"],
                },
            }
        )
