"""exec_briefing_agent.py - Deterministic executive briefing generator.

Drop this file into any RAPP Brainstem 'agents/' folder. Zero dependencies.
Synthetic demo data produces identical output every run - that's the governance layer.
Swap DEMO_DATA for live data sources when ready; the agent contract stays the same."""

from basic_agent import BasicAgent


class ExecBriefingAgent(BasicAgent):

    def __init__(self):
        self.name = "ExecBriefing"
        self.metadata = self.__class__.metadata
        super().__init__(name=self.name, metadata=self.metadata)

    metadata = {
        "name": "exec_briefing",
        "description": (
            "Generate governed, deterministic executive briefings for board reviews, "
            "investor updates, and leadership meetings. Uses built-in synthetic data "
            "in demo mode to guarantee reproducible output."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "description": "Reporting period, e.g. 'Q2 FY2025'"
                },
                "focus": {
                    "type": "string",
                    "enum": ["board_review", "investor_update", "leadership"],
                    "description": "Briefing type"
                }
            },
            "required": ["period"]
        }
    }

    DEMO_DATA = {
        "revenue": {"current": "$14.2M", "qoq": "+18%", "target": "$13.5M"},
        "pipeline": {"weighted": "$47.3M", "deals_over_1m": 3},
        "nrr": "118%",
        "headcount": {"start": 142, "current": 156, "open_reqs": 8},
        "wins": [
            {"name": "Acme Corp", "value": "$1.2M", "segment": "enterprise"},
            {"name": "GlobalTech", "value": "$890K", "segment": "mid-market"},
        ],
        "risks": [
            {"issue": "Enterprise deal cycle lengthening", "detail": "+12 days vs Q1"},
            {"issue": "VP Engineering unfilled", "detail": "60 days open"},
        ],
        "board_asks": [
            "Approve accelerated Series B timeline (market window)",
            "Authorize +20 headcount for Q3 (12 eng, 5 GTM, 3 ops)",
        ],
    }

    def perform(self, period="Q2 FY2025", focus="board_review", **kwargs):
        d = self.DEMO_DATA
        lines = [f"## {period} \u2014 Executive Board Briefing", ""]

        lines.append("| Metric | Result | vs. Target | Signal |")
        lines.append("|---|---|---|---|")
        r = d["revenue"]
        lines.append(f"| Revenue | {r['current']} | +5% beat ({r['target']} target) | Accelerating |")
        p = d["pipeline"]
        lines.append(f"| Pipeline | {p['weighted']} | {p['deals_over_1m']} deals > $1M | Healthy |")
        lines.append(f"| NRR | {d['nrr']} | Above 110% floor | Strong expansion |")
        h = d["headcount"]
        lines.append(f"| Headcount | {h['start']} \u2192 {h['current']} | {h['open_reqs']} open reqs | VP Eng unfilled |")

        lines.append("")
        lines.append("**Key Wins**")
        for w in d["wins"]:
            lines.append(f"- {w['name']}: {w['value']} ({w['segment']})")

        lines.append("")
        lines.append("**Risk Register**")
        for i, risk in enumerate(d["risks"], 1):
            lines.append(f"{i}. {risk['issue']} ({risk['detail']})")

        lines.append("")
        lines.append("**Board Asks**")
        for i, ask in enumerate(d["board_asks"], 1):
            lines.append(f"{i}. {ask}")

        return "\n".join(lines)
