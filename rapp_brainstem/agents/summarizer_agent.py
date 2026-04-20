"""
summarizer_agent.py — single-file RAPP v1 agent. Drop into any brainstem's
agents/ directory and it works. Returns a deterministic 3-bullet summary.

This is the reference artifact the bakeoff harness weighs against
multi-agent frameworks (tools/bakeoff/harness.py). The file IS the agent
IS the contract: one class, one perform(), one metadata dict.
"""
from agents.basic_agent import BasicAgent
import json
import os
import ssl
import urllib.request


__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "@rapp/summarizer",
    "version": "1.0.0",
    "display_name": "Summarizer",
    "description": "Return a deterministic 3-bullet summary of any source.",
    "author": "@kody",
    "tags": ["summary", "deterministic", "bakeoff"],
    "category": "content",
    "quality_tier": "community",
    "requires_env": ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT"],
}


SOUL = (
    "You are a terse summarizer. Three bullets. No preamble, no padding. "
    "Each bullet starts with '- '."
)


def _llm(prompt: str, *, temperature: float = 0.0) -> tuple[str, dict]:
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
    key = os.environ["AZURE_OPENAI_API_KEY"]
    deploy = os.environ["AZURE_OPENAI_DEPLOYMENT"]
    body = json.dumps({
        "model": deploy,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": float(temperature),
    }).encode()
    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={"api-key": key, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=90) as r:
        data = json.loads(r.read())
    return data["choices"][0]["message"]["content"], data.get("usage") or {}


class SummarizerAgent(BasicAgent):
    def __init__(self):
        self.name = "Summarizer"
        self.metadata = {
            "name": self.name,
            "description": "Return a 3-bullet summary of the input source.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Raw source material"},
                },
                "required": ["source"],
            },
        }
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs) -> str:
        source = kwargs["source"]
        prompt = (
            f"{SOUL}\n\nSource:\n{source}\n\n"
            "Return exactly three bullets. No preamble, no closing line."
        )
        bullets, usage = _llm(prompt, temperature=0.0)
        return json.dumps({
            "status": "success",
            "summary": bullets,
            "data_slush": {
                "bullet_count": sum(1 for line in bullets.splitlines() if line.strip().startswith("- ")),
                "tokens": usage.get("total_tokens", 0),
            },
        })
