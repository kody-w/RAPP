"""
ExecutiveBriefAgent — the first "factory" agent. Demonstrates the
index-card pattern: it opens a card, walks research → synthesis →
format stages updating the card as it goes, and returns a short
summary string while the rich artifact lives on the card.

The UI polls /card/<turn_id> every ~500ms, so the user watches the
stages light up live instead of staring at a typing indicator. When
the run finishes the card becomes the report — same surface, frozen.

No external network calls here — the "research" step is synthesized
from the topic so the demo is deterministic and offline-safe. Real
agents would drop in their actual work (web search, DB queries, etc.)
at each stage and keep the card.stage(...) calls around them.
"""
import time

from agents.basic_agent import BasicAgent
from utils.index_card import current as card


class ExecutiveBriefAgent(BasicAgent):
    def __init__(self):
        self.name = "ExecutiveBrief"
        self.metadata = {
            "name": self.name,
            "description": (
                "Generate a short executive brief on a specific topic. "
                "Best for 'run the executive brief' / 'brief me on X' "
                "requests where the user wants a structured summary plus "
                "visible progress as the brief is assembled."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The specific topic the brief should cover, e.g. 'AI in supply chain'."
                    },
                    "audience": {
                        "type": "string",
                        "description": "Optional target audience — e.g. 'CFO', 'engineering leadership'. Defaults to 'executives'."
                    },
                },
                "required": ["topic"],
            },
        }
        super().__init__()

    def perform(self, topic: str, audience: str = "executives", **_):
        topic = (topic or "").strip() or "(unspecified)"

        c = card()
        c.start(
            title=f"Executive Brief: {topic}",
            subtitle=f"For {audience}",
            stages=[
                ("research",  "Research"),
                ("synthesis", "Synthesis"),
                ("format",    "Format"),
            ],
        )

        # ── Stage 1: Research ─────────────────────────────────────────
        c.stage("research", status="running", note="scanning sources")
        time.sleep(0.8)
        sources = [
            {"title": f"Industry outlook: {topic}", "kind": "report"},
            {"title": f"Recent moves in {topic}",  "kind": "news"},
            {"title": f"Expert takes on {topic}",  "kind": "analysis"},
        ]
        c.metric("sources", len(sources))
        c.stage("research", status="done", note=f"{len(sources)} sources")

        # ── Stage 2: Synthesis ────────────────────────────────────────
        c.stage("synthesis", status="running", note="distilling themes")
        time.sleep(0.9)
        themes = [
            f"Adoption of {topic} is accelerating but uneven across segments.",
            f"The leaders in {topic} are compounding data and tooling advantages.",
            f"{topic} rewards teams that ship narrow wins before broad platforms.",
        ]
        c.metric("themes", len(themes))
        c.stage("synthesis", status="done", note=f"{len(themes)} themes")

        # ── Stage 3: Format ───────────────────────────────────────────
        c.stage("format", status="running", note="composing brief")
        time.sleep(0.6)
        body_md = (
            f"## Executive Brief: {topic}\n"
            f"_For {audience} · {len(sources)} sources · {len(themes)} themes_\n\n"
            "### Bottom line\n"
            f"{themes[0]}\n\n"
            "### Why now\n"
            f"{themes[1]}\n\n"
            "### What to do\n"
            f"{themes[2]}\n\n"
            "### Sources\n"
            + "\n".join(f"- _{s['kind']}_: {s['title']}" for s in sources)
        )
        c.artifact(
            kind="brief",
            title=f"Executive Brief: {topic}",
            body_md=body_md,
            meta={"audience": audience},
        )
        c.stage("format", status="done")
        c.finish()

        # Short text response — the UI shows the card above this bubble,
        # so we don't repeat the whole brief in the chat body.
        return (
            f"Executive brief ready: **{topic}** — see the index card above for the "
            f"staged run ({len(sources)} sources, {len(themes)} themes) and the full brief."
        )
