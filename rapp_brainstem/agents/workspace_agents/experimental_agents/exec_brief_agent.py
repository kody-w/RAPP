"""
Exec Brief Agent — generic single-purpose WorkIQ agent for executive sponsors.

Scans the user's Microsoft 365 (email + Teams) for situations trending toward
needing them as exec sponsor, and returns 1-pagers per situation — the thing
that's about to land on their plate before it hits their calendar.

No source edits required. `executive_name` is a required parameter — the
brainstem's LLM will ask the user for it on first invocation.
"""

import re
import shutil
import subprocess
import sys
import logging
from agents.basic_agent import BasicAgent


_ANSI_RE = re.compile(r'\x1b(?:\[[0-9;?]*[a-zA-Z]|\][^\x07\x1b]*(?:\x07|\x1b\\))')

_DEFAULT_TRIGGERS = [
    "need exec sponsor",
    "need executive sponsor",
    "escalate to exec",
    "DEFCON",
    "exec swarm",
    "white glove",
    "final-layer sponsor",
    "senior air cover",
    "needs top cover",
]


class ExecBriefAgent(BasicAgent):
    def __init__(self):
        self.name = 'ExecBrief'
        self.metadata = {
            "name": self.name,
            "description": (
                "Scan my Microsoft 365 email and Teams for situations trending toward needing "
                "me as executive sponsor, and return 1-pagers per situation. Use when I want to "
                "know what's about to land on my plate before it hits my calendar. Ask me for my "
                "full name if I haven't told you yet."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "executive_name": {
                        "type": "string",
                        "description": (
                            "The executive's full name — used to tailor the scan and the language of "
                            "the 1-pagers. If the user hasn't told you their name yet, ask them first."
                        )
                    },
                    "lookback_days": {
                        "type": "integer",
                        "description": "How many business days of history to scan. Default 30."
                    }
                },
                "required": ["executive_name"]
            }
        }
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        exec_name = (kwargs.get('executive_name') or '').strip()
        if not exec_name:
            return "Error: executive_name is required."
        lookback = kwargs.get('lookback_days') or 30

        query = self._build_query(exec_name, lookback)

        workiq_path = shutil.which('workiq')
        if workiq_path:
            cmd = [workiq_path, 'ask', '-q', query]
        elif shutil.which('npx'):
            cmd = ['npx', '-y', '@microsoft/workiq', 'ask', '-q', query]
        else:
            return (
                "WorkIQ CLI not available. Install with `npm install -g @microsoft/workiq`, "
                "then run `workiq accept-eula` and authenticate by running `workiq ask 'test'`."
            )

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=240,
                shell=(sys.platform == 'win32')
            )
        except subprocess.TimeoutExpired:
            return "WorkIQ query timed out after 240s. Try a shorter lookback window."
        except FileNotFoundError:
            return "WorkIQ CLI not found on PATH."

        if result.returncode != 0:
            err = (result.stderr or 'unknown error').strip()
            logging.error(f"ExecBrief workiq error: {err}")
            return f"WorkIQ failed: {err[:500]}"

        output = _ANSI_RE.sub('', result.stdout or '').strip()
        if not output:
            return f"No results returned from WorkIQ for the {exec_name} scan."

        return f"# Exec Sponsor Scan — {exec_name}\n\n{output}"

    def _build_query(self, exec_name, lookback):
        last_name = exec_name.split()[-1] if exec_name.split() else exec_name
        name_triggers = [
            f"bring in {exec_name}",
            f"bring in {last_name}",
            f"escalate to {last_name}",
            f"pull in {last_name}",
            f"need {last_name}'s cover",
        ]
        triggers_str = ', '.join(f'"{t}"' for t in name_triggers + _DEFAULT_TRIGGERS)

        return (
            f"Scan all my email and Teams from the last {lookback} business days for situations "
            f"trending toward needing me as executive sponsor. "
            f"Signals to look for: explicit phrases such as {triggers_str}. "
            f"Also surface: customers currently trending red or amber, escalating thread sentiment, "
            f"and threads where someone is asking for senior air cover without naming me specifically "
            f"but matching the pattern of past situations I've been pulled into (high-risk customer "
            f"escalations, partner ecosystem defense, org-level narrative moments, F500 executive "
            f"customer meetings). "
            f"For each qualifying situation, return a Markdown sub-section with this exact shape:\n"
            f"### Situation: <customer or initiative name>\n"
            f"- **Who's asking:** <person driving the ask>\n"
            f"- **What's burning:** <one sentence>\n"
            f"- **What's been tried:** <bullets>\n"
            f"- **Stakeholders:** <names>\n"
            f"- **Already on my calendar?** <yes/no, and when>\n"
            f"- **Suggested exec moves:** <three bullets I could execute today>\n\n"
            f"If nothing qualifies in the last {lookback} business days, say so explicitly and list "
            f"any historical threads where I was engaged so I can see the backdrop. Do not fabricate "
            f"situations to fill the output."
        )
