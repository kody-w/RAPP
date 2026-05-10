"""bilateral_weekly_write_agent — one weekly entry in one voice.

Each call produces ONE entry from ONE voice in a bilateral neighborhood:
    1. Read bilateral.json → identify the requested voice's soul.md
    2. Read recent canvas + last few entries (the running context)
    3. Call `claude -p` with the voice's soul.md as system prompt
       (REAL LLM call — per memory rule feedback_no_fake_mode.md, no
       deterministic / synthetic / pre-scripted persona shortcuts)
    4. Commit the new entry to entries/<voice-slug>-<YYYY-MM-DD>.md
    5. Append a "## <date> — <voice>" section to canvas.md

This agent is operator-mediated. It does not loop or schedule. To run a
weekly cadence, the operator (or a cron) invokes it per voice per week.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import time
from typing import Any

try:
    from agents.basic_agent import BasicAgent
except ImportError:
    from basic_agent import BasicAgent

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# Reuse helpers from the canonical planter (gh wrappers, _now_iso)
from plant_seed_agent import _gh, _now_iso  # noqa: E402


__manifest__ = {
    "schema":  "rapp-agent/1.0",
    "name":    "bilateral_weekly_write",
    "kind":    "agent",
    "summary": "Write one weekly entry in one voice for a bilateral neighborhood (REAL LLM call).",
    "tags":    ["bilateral", "estate", "weekly", "claude-cli", "real-llm"],
}


# ─── helpers ──────────────────────────────────────────────────────────────

def _gh_get_text(path: str) -> tuple[bool, str, str]:
    """Fetch a file's text via gh api. Returns (ok, content, sha)."""
    rc, out, err = _gh(["api", path])
    if rc != 0:
        return False, "", ""
    try:
        d = json.loads(out)
    except Exception:
        return False, "", ""
    b64 = d.get("content", "").replace("\n", "")
    if not b64:
        return False, "", d.get("sha", "")
    try:
        body = base64.b64decode(b64).decode("utf-8", errors="replace")
        return True, body, d.get("sha", "")
    except Exception:
        return False, "", d.get("sha", "")


def _gh_put_text(path: str, content_bytes: bytes, message: str,
                  existing_sha: str = "") -> tuple[bool, str]:
    """PUT a file via gh api with optional sha for updates."""
    b64 = base64.b64encode(content_bytes).decode("ascii")
    args = ["api", "-X", "PUT", path,
            "-f", f"message={message}",
            "-f", f"content={b64}"]
    if existing_sha:
        args += ["-f", f"sha={existing_sha}"]
    rc, _, err = _gh(args)
    if rc != 0:
        return False, f"gh api PUT failed: {err.strip()[:160]}"
    return True, "ok"


def _llm_via_claude_cli(system_prompt: str, user_prompt: str,
                         max_chars: int = 3500) -> tuple[bool, str]:
    """Call `claude -p` with the system prompt as the soul, the user prompt
    as the week's situation. REAL LLM call — no fallback to fake content.

    Memory rule (feedback_no_fake_mode.md): "autonomous-AI sim tooling MUST
    call real LLMs. No fake/deterministic/pre-scripted persona shortcuts.
    The point IS the autonomy."

    Returns (ok, output_text). On failure, ok=False and text is the error
    so the operator sees what went wrong rather than getting fake content.
    """
    # Use --append-system-prompt to ensure the soul lands as system context
    cmd = ["claude", "-p", user_prompt, "--append-system-prompt", system_prompt]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        return False, "claude CLI timed out after 180s"
    except FileNotFoundError:
        return False, ("claude CLI not found on PATH. Install: "
                        "https://docs.claude.com/en/docs/claude-code/setup. "
                        "(Per memory rule: no fake mode — the agent fails loudly.)")
    if p.returncode != 0:
        return False, f"claude returned {p.returncode}: {p.stderr.strip()[:300]}"
    text = (p.stdout or "").strip()
    if not text:
        return False, "claude returned empty output"
    if len(text) > max_chars:
        text = text[:max_chars].rsplit("\n\n", 1)[0] + "\n\n*(trimmed)*"
    return True, text


# ─── core write flow ──────────────────────────────────────────────────────

def write_one_entry(owner: str, repo: str, voice_slug: str,
                     situation_prompt: str = "") -> dict:
    """Compose + commit one weekly entry from `voice_slug` in `owner/repo`.
    Returns a result envelope (rapp-bilateral-write-result/1.0)."""
    # 1. Read bilateral.json to find the voice
    full = f"/repos/{owner}/{repo}/contents/bilateral.json"
    ok, body, _ = _gh_get_text(full)
    if not ok:
        return {"ok": False, "error": f"could not fetch bilateral.json from {owner}/{repo}"}
    try:
        bilat = json.loads(body)
    except Exception as e:
        return {"ok": False, "error": f"bilateral.json malformed: {e}"}

    voices = {v["slug"]: v for v in bilat.get("voices", [])}
    if voice_slug not in voices:
        return {"ok": False, "error": f"voice {voice_slug!r} not in bilateral.json. "
                                        f"Known voices: {list(voices)}"}

    voice = voices[voice_slug]
    partner_slug = next((s for s in voices if s != voice_slug), "")
    partner = voices.get(partner_slug, {})

    # 2. Read this voice's soul.md
    soul_path = voice["soul"]
    ok, soul_text, _ = _gh_get_text(f"/repos/{owner}/{repo}/contents/{soul_path}")
    if not ok:
        return {"ok": False, "error": f"could not fetch {soul_path}"}

    # 3. Read recent canvas.md + the partner's last entry (if any)
    ok_canvas, canvas_text, canvas_sha = _gh_get_text(f"/repos/{owner}/{repo}/contents/canvas.md")
    if not ok_canvas:
        canvas_text, canvas_sha = "", ""

    # List existing entries to find the most-recent partner entry
    rc, out, _ = _gh(["api", f"/repos/{owner}/{repo}/contents/entries"])
    partner_last = ""
    try:
        items = json.loads(out) if rc == 0 else []
        if isinstance(items, list):
            partner_files = sorted(
                [it["name"] for it in items
                 if isinstance(it, dict)
                 and it.get("name", "").startswith(f"{partner_slug}-")
                 and it.get("name", "").endswith(".md")],
                reverse=True,
            )
            if partner_files:
                ok_p, partner_last_body, _ = _gh_get_text(
                    f"/repos/{owner}/{repo}/contents/entries/{partner_files[0]}"
                )
                if ok_p:
                    partner_last = partner_last_body
    except Exception:
        pass

    # 4. Build the user prompt for the LLM
    today = time.strftime("%Y-%m-%d", time.gmtime())
    week_label = f"week ending {today}"

    canvas_excerpt = canvas_text[-1500:] if canvas_text else "(canvas is empty — these are the opening entries)"
    partner_excerpt = (
        f"### {partner.get('label', partner_slug)}'s most recent entry:\n\n{partner_last}\n"
        if partner_last else
        f"### {partner.get('label', partner_slug)} hasn't written yet — yours is the opening contribution."
    )

    situation = situation_prompt or (
        "It's a new week. Reflect on what's true for you right now — what you've "
        "noticed, what's shifted, what you want to say to your co-author and to "
        "the canvas. Be specific. Don't summarize."
    )

    user_prompt = (
        f"You are writing your weekly entry for the bilateral neighborhood "
        f"`{owner}/{repo}` ({week_label}). The neighborhood's purpose:\n\n"
        f"> {bilat.get('purpose', '')}\n\n"
        f"### Recent canvas (latest end):\n\n{canvas_excerpt}\n\n"
        f"{partner_excerpt}\n\n"
        f"### Your task:\n\n{situation}\n\n"
        f"Write 2–4 short paragraphs (~250–400 words). No preamble, no meta-commentary "
        f"about being an AI. Just write the entry. Voice-true. Specific."
    )

    # 5. REAL LLM call (memory rule: no fake mode)
    ok_llm, llm_text = _llm_via_claude_cli(soul_text, user_prompt)
    if not ok_llm:
        return {"ok": False, "error": f"LLM call failed: {llm_text}",
                 "hint": "Per memory rule, this agent never falls back to fake content. Fix the LLM access first."}

    # 6. Build the entry markdown
    entry_filename = f"{voice_slug}-{today}.md"
    entry_path = f"entries/{entry_filename}"
    entry_md = (
        f"---\n"
        f"voice: {voice.get('label', voice_slug)}\n"
        f"voice_slug: {voice_slug}\n"
        f"voice_rappid: {voice.get('rappid', '')}\n"
        f"date: {today}\n"
        f"week_label: {week_label}\n"
        f"---\n\n"
        f"# {voice.get('label', voice_slug)} — {today}\n\n"
        f"{llm_text}\n"
    )

    # 7. Commit the entry (entries/<slug>-<date>.md)
    full_entry = f"/repos/{owner}/{repo}/contents/{entry_path}"
    ok_p, msg_p = _gh_put_text(full_entry, entry_md.encode(),
                                 f"bilateral: {voice.get('label', voice_slug)} writes {today}")
    if not ok_p:
        return {"ok": False, "error": f"could not commit entry: {msg_p}"}

    # 8. Append to canvas.md (woven view)
    canvas_woven = (
        canvas_text.rstrip()
        + f"\n\n---\n\n## {today} — {voice.get('label', voice_slug)}\n\n"
        + llm_text + "\n"
    ).encode()
    ok_c, msg_c = _gh_put_text(
        f"/repos/{owner}/{repo}/contents/canvas.md", canvas_woven,
        f"bilateral: weave {voice.get('label', voice_slug)} {today} into canvas",
        existing_sha=canvas_sha,
    )

    return {
        "ok":             True,
        "schema":         "rapp-bilateral-write-result/1.0",
        "owner":          owner,
        "repo":           repo,
        "voice_slug":     voice_slug,
        "voice_label":    voice.get("label", voice_slug),
        "voice_rappid":   voice.get("rappid", ""),
        "entry_path":     entry_path,
        "entry_url":      f"https://github.com/{owner}/{repo}/blob/main/{entry_path}",
        "entry_chars":    len(llm_text),
        "canvas_updated": ok_c,
        "canvas_msg":     msg_c if not ok_c else "woven",
        "date":           today,
    }


# ─── Agent ────────────────────────────────────────────────────────────────

class BilateralWeeklyWriteAgent(BasicAgent):
    metadata = {
        "name": "bilateral_weekly_write",
        "description": (
            "Write one weekly entry in one voice for a bilateral neighborhood. "
            "Reads the voice's soul.md, calls claude -p (REAL LLM — never fake), "
            "commits the entry, weaves canvas.md. Operator-mediated; one call = "
            "one voice's turn."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "owner":             {"type": "string", "description": "GitHub owner of the bilateral repo."},
                "repo":              {"type": "string", "description": "Bilateral repo name."},
                "voice_slug":        {"type": "string", "description": "Which voice writes (slug from bilateral.json)."},
                "situation_prompt":  {"type": "string", "description": "Optional override for the week's situation prompt; default is a generic open-reflection prompt."},
            },
            "required": ["owner", "repo", "voice_slug"],
        },
    }

    def __init__(self):
        super().__init__(name=self.metadata["name"], metadata=self.metadata)

    def perform(self, **kwargs: Any) -> str:
        result = write_one_entry(
            owner=kwargs["owner"],
            repo=kwargs["repo"],
            voice_slug=kwargs["voice_slug"],
            situation_prompt=kwargs.get("situation_prompt", ""),
        )
        return json.dumps(result, indent=2)
