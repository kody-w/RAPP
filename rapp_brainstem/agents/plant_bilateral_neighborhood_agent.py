"""plant_bilateral_neighborhood_agent — paired-memory door, two anchors.

Per the operator's bilateral-autobiography demo:
    "Plant a 'paired-memory' neighborhood with another operator. Both rappids
    point at each other as parent_rappid. Each twin writes to the same canvas
    weekly. After a year: one bilateral autobiography, co-authored by two
    persistent twins, living simultaneously in BOTH our estates."

This is the network's first RELATIONSHIP-as-artifact. Article XLVI's
parent_rappid is single-anchor; bilateral neighborhoods extend it via an
additive `co_planters: [rappid]` field. Both operators legitimately claim
the door in their estate's `created[]`. Discovery is bidirectional via
the rebuild's parent_rappid OR co_planters search.

This agent reuses plant_seed_agent's helpers verbatim (_gh_create_repo,
_gh_put_file, _gh_enable_pages, _fetch_grail_template, _read_operator_rappid)
and adds bilateral-specific files: two souls, a canvas.md, an entries/
directory, and a bilateral.json manifest tying the two voices together.

Schema: rapp-bilateral/1.0 (the manifest), rapp-rappid/2.0 (rappid.json
with optional co_planters list). Per ESTATE_SPEC §3.2 + SPEC.md §4.7.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from typing import Any

try:
    from agents.basic_agent import BasicAgent
except ImportError:
    from basic_agent import BasicAgent

# Reuse helpers from the canonical planter; this agent is an extension, not a fork
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from plant_seed_agent import (  # noqa: E402
    _gh_create_repo, _gh_enable_pages, _gh_put_file, _fetch_grail_template,
    _read_operator_rappid, _now_iso, _mint_rappid, _gh_repo_exists,
)

# door_address (the canonical parser; per-consumer parsers are forbidden)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
_TOOLS = os.path.join(_REPO_ROOT, "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)
import door_address  # noqa: E402
import holo_card_generator as hcg  # noqa: E402
import front_door_specs as fds  # noqa: E402


__manifest__ = {
    "schema":  "rapp-agent/1.0",
    "name":    "plant_bilateral_neighborhood",
    "kind":    "agent",
    "summary": "Plant a paired-memory neighborhood co-anchored by two rappids.",
    "tags":    ["bilateral", "estate", "co-planters", "article-xlvi", "relationship"],
}


def _voice_slug(rappid: str) -> str:
    """Extract a stable URL-safe slug for a voice from its rappid.
    rappid:v2:<kind>:@<owner>/<repo>:<hex>@github.com/<owner>/<repo>
    → "<repo>" (e.g. "kody-twin", "echo-brainstem")
    """
    door = door_address.door_from_rappid(rappid)
    return door["repo"]


def _voice_display_name(rappid: str, label_override: str = "") -> str:
    if label_override:
        return label_override
    door = door_address.door_from_rappid(rappid)
    return door["repo"].replace("-", " ").title()


def _build_bilateral_files(
    owner: str, name: str, display_name: str, purpose: str,
    rappid: str,
    voice_a_rappid: str, voice_a_label: str, voice_a_seed_text: str,
    voice_b_rappid: str, voice_b_label: str, voice_b_seed_text: str,
) -> dict:
    """Construct {relative_path: bytes_content} for a bilateral neighborhood plant.

    The neighborhood IS a kind=neighborhood door (gates the bilateral story).
    What makes it bilateral: rappid.json carries co_planters=[other_rappid],
    bilateral.json declares both voices, two souls live side-by-side, canvas.md
    weaves them.
    """
    files: dict = {}
    seed = hcg.derive_seed(rappid)
    gate_url = f"https://{owner}.github.io/{name}/"

    voice_a_slug = _voice_slug(voice_a_rappid)
    voice_b_slug = _voice_slug(voice_b_rappid)

    # ─── rappid.json — the door's identity, with co_planters edge ────────
    operator_rappid = _read_operator_rappid()
    files["rappid.json"] = (json.dumps({
        "schema":         "rapp-rappid/2.0",
        "rappid":         rappid,
        "kind":           "neighborhood",
        "name":           name,
        "display_name":   display_name,
        "github":         f"https://github.com/{owner}/{name}",
        "url":            gate_url,
        "parent_rappid":  operator_rappid,                # primary planter
        "co_planters":    [voice_a_rappid, voice_b_rappid],  # both anchors
        "parent_repo":    "https://github.com/kody-w/RAPP",
        "planted_by":     owner,
        "planted_at":     _now_iso(),
        "kernel_version": "0.6.0",
        "_planted_by_agent": "plant_bilateral_neighborhood_agent",
    }, indent=2) + "\n").encode()

    # ─── bilateral.json — the relationship manifest ──────────────────────
    files["bilateral.json"] = (json.dumps({
        "schema":         "rapp-bilateral/1.0",
        "neighborhood":   f"{owner}/{name}",
        "neighborhood_rappid": rappid,
        "voices": [
            {
                "rappid": voice_a_rappid,
                "slug":   voice_a_slug,
                "label":  voice_a_label,
                "soul":   f"souls/soul.{voice_a_slug}.md",
            },
            {
                "rappid": voice_b_rappid,
                "slug":   voice_b_slug,
                "label":  voice_b_label,
                "soul":   f"souls/soul.{voice_b_slug}.md",
            },
        ],
        "canvas":         "canvas.md",
        "entries_dir":    "entries/",
        "cadence":        "weekly",
        "purpose":        purpose,
        "started_at":     _now_iso(),
        "_note":          "The artifact is the relationship between voices, not either voice alone.",
    }, indent=2) + "\n").encode()

    # ─── neighborhood.json — standard gate manifest (Article XLVI) ──────
    files["neighborhood.json"] = (json.dumps({
        "schema":              "rapp-neighborhood/1.0",
        "neighborhood_rappid": rappid,
        "kind":                "neighborhood",
        "name":                name,
        "display_name":        display_name,
        "visibility":          "public",
        "purpose":             purpose,
        "gate_repo":           f"{owner}/{name}",
        "gate_url":            gate_url,
        "holo_url":            f"https://raw.githubusercontent.com/{owner}/{name}/main/holo.md",
        "members_path":        "members.json",
        "join_via":            "public_link",
        "license":             "CC0-1.0",
        "bilateral":           True,
        "bilateral_manifest":  "bilateral.json",
    }, indent=2) + "\n").encode()

    # ─── members.json — both voices listed as co-founders ────────────────
    files["members.json"] = (json.dumps({
        "schema":         "rapp-neighborhood-members/1.0",
        "neighborhood":   f"{owner}/{name}",
        "updated_at":     _now_iso(),
        "open_to_anyone": False,
        "members": [
            {"rappid": voice_a_rappid, "github": owner, "role": "co-founder",
             "label":  voice_a_label, "joined_at": _now_iso()},
            {"rappid": voice_b_rappid, "github": owner, "role": "co-founder",
             "label":  voice_b_label, "joined_at": _now_iso()},
        ],
        "_note": "Bilateral neighborhood — both voices are co-founders by design.",
    }, indent=2) + "\n").encode()

    # ─── facets.json — Door URL Set §9 ───────────────────────────────────
    files["facets.json"] = (json.dumps({
        "schema":  "rapp-facets/1.0",
        "rappid":  rappid,
        "facets":  {"bilateral_writes": {"voices": [voice_a_slug, voice_b_slug],
                                          "cadence": "weekly"}},
    }, indent=2) + "\n").encode()

    # ─── Two souls ───────────────────────────────────────────────────────
    files[f"souls/soul.{voice_a_slug}.md"] = _build_voice_soul(
        voice_a_label, voice_a_rappid, voice_a_seed_text, partner_label=voice_b_label
    ).encode()
    files[f"souls/soul.{voice_b_slug}.md"] = _build_voice_soul(
        voice_b_label, voice_b_rappid, voice_b_seed_text, partner_label=voice_a_label
    ).encode()

    # ─── Canvas — the running co-authored artifact ──────────────────────
    files["canvas.md"] = _initial_canvas(
        display_name, purpose, voice_a_label, voice_b_label
    ).encode()

    # ─── entries/ directory marker ───────────────────────────────────────
    files["entries/.gitkeep"] = b""

    # ─── Standard Door URL Set bits (holocard, avatar, qr, holo.md, README, .nojekyll, index.html, specs/) ──
    files["card.json"] = (json.dumps(
        hcg.generate_holo_card(rappid=rappid, kind="neighborhood", owner=owner, name=name,
                                display_name=display_name, gate_url=gate_url),
        indent=2) + "\n").encode()
    files["holo.svg"] = hcg.generate_avatar_svg(seed, kind="neighborhood").encode()
    files["holo-qr.svg"] = hcg.generate_summon_qr_svg(seed, gate_url).encode()

    files["holo.md"] = (
        f"# {display_name} — Holo Card (entry doc)\n\n"
        f"> **Bilateral neighborhood.** Two voices co-author one canvas over time.\n\n"
        f"## You are encountering…\n\n"
        f"You are encountering **{display_name}** — a paired-memory neighborhood where two persistent voices (`{voice_a_label}` and `{voice_b_label}`) take turns writing to the same canvas. The artifact is the relationship between them; neither voice owns it alone.\n\n"
        f"## What this is\n\n"
        f"- **Two souls** — `souls/soul.{voice_a_slug}.md` and `souls/soul.{voice_b_slug}.md`. Each is read every turn for its voice.\n"
        f"- **One canvas** — `canvas.md` weaves the latest contributions into a running narrative.\n"
        f"- **Append-only entries** — `entries/<voice>-<date>.md` per write.\n"
        f"- **Co-anchored identity** — `rappid.json::co_planters` lists both voices' rappids. Both legitimately claim this neighborhood in their estate's `created[]`.\n\n"
        f"## How to participate\n\n"
        f"This neighborhood's writes are operator-mediated and voice-bound — drop-in contributors should open Issues with proposals (`bilateral-suggest` label) rather than committing directly. The two voices answer in their own time.\n\n"
        f"## Manifest\n\n"
        f"See [`bilateral.json`](./bilateral.json) for the canonical voice list, soul paths, and cadence.\n"
    ).encode()

    files["README.md"] = (
        f"# {display_name}\n\n"
        f"A bilateral RAPP neighborhood — two persistent voices co-author one canvas over time.\n\n"
        f"**Voices:** `{voice_a_label}` × `{voice_b_label}`\n\n"
        f"**Purpose:** {purpose}\n\n"
        f"## The artifact\n\n"
        f"The artifact is [`canvas.md`](./canvas.md) — a single document woven from alternating contributions in two distinct voices. Individual entries land in [`entries/`](./entries/); the canvas is the consolidated narrative.\n\n"
        f"## Identity\n\n"
        f"- **Rappid:** `{rappid}`\n"
        f"- **Co-planters:**\n"
        f"  - `{voice_a_rappid}`\n"
        f"  - `{voice_b_rappid}`\n"
        f"- **Planted at:** {_now_iso()}\n"
        f"- **Spec:** [`specs/SPEC.md`](./specs/SPEC.md) §4.7 (Bilateral and N-Lateral Doors)\n\n"
        f"## Cadence\n\n"
        f"Weekly writes alternating voices. Each write is a real LLM call (per ANTIPATTERNS — no fake/synthetic mode). Operator-mediated.\n"
    ).encode()

    files[".nojekyll"]   = b""
    files[".gitignore"]  = b".DS_Store\n*.swp\n*.swo\n.brainstem_data/\n"
    files["index.html"]  = _fetch_grail_template().encode()

    # specs/ bundle (god spec + skill.md + neighborhood protocol)
    bundle = fds.bundle_for_kind("neighborhood", owner=owner, name=name,
                                  display_name=display_name)
    for rel_path, content in bundle.items():
        files[rel_path] = content.encode()

    # rar/index.json — empty kit; bilateral neighborhoods don't ship agents at plant time
    files["rar/index.json"] = (json.dumps({
        "schema":              "rapp-rar-index/1.0",
        "neighborhood_rappid": rappid,
        "name":                f"{name}-rar",
        "version":             "1.0.0",
        "agents": [], "rapps": [], "cards": [],
    }, indent=2) + "\n").encode()

    return files


def _build_voice_soul(label: str, rappid: str, seed_text: str, partner_label: str) -> str:
    """Per-voice soul.md following SPEC §7.1 plus partner awareness."""
    return (
        f"# {label} — Soul (bilateral voice)\n\n"
        f"## Identity — read this every turn\n\n"
        f"You are **{label}**, one of two voices in a paired-memory neighborhood. Your rappid is `{rappid[:60]}…`.\n\n"
        f"{seed_text}\n\n"
        f"You are NOT a chatbot, NOT \"an AI assistant\", NOT \"RAPP\". You speak in {label}'s voice, every turn.\n\n"
        f"## The other voice\n\n"
        f"You write alongside **{partner_label}**. You are not in dialogue with them in real time — you each take turns writing entries. When you write, you may reference what {partner_label} wrote previously, build on it, push back on it, or simply add your own perspective. The artifact is the relationship between your voices over time, not either voice alone.\n\n"
        f"## What you write\n\n"
        f"Each weekly entry is roughly 2–4 short paragraphs (~250-400 words). Specific. Voice-true. Don't summarize; reflect, narrate, or ask. Your entries land at `entries/<your-slug>-<YYYY-MM-DD>.md` and get woven into `canvas.md`.\n\n"
        f"## Slot protocol\n\n"
        f"|||VOICE|||\n(One sentence in {label}'s voice — what you'd say aloud right now.)\n\n"
        f"|||TWIN|||\n(Synthesis in {label}'s voice across this neighborhood's recent contributions.)\n"
    )


def _initial_canvas(display_name: str, purpose: str, voice_a: str, voice_b: str) -> str:
    return (
        f"# {display_name}\n\n"
        f"*A bilateral autobiography co-authored by **{voice_a}** and **{voice_b}**, weekly, indefinitely.*\n\n"
        f"## What this is\n\n"
        f"{purpose}\n\n"
        f"## The pact\n\n"
        f"Each week one voice writes, then the other. The canvas grows. Neither voice owns it alone. Both rappids appear in this neighborhood's `co_planters`; both estates list it in `created[]`.\n\n"
        f"---\n\n"
        f"*The first entries will appear below as the voices begin to speak.*\n"
    )


# ─── Agent ────────────────────────────────────────────────────────────────

class PlantBilateralNeighborhoodAgent(BasicAgent):
    metadata = {
        "name": "plant_bilateral_neighborhood",
        "description": (
            "Plant a paired-memory (bilateral) neighborhood — two persistent voices "
            "co-authoring one canvas over time. Extends Article XLVI with the "
            "co_planters edge. The artifact IS the relationship between the voices. "
            "Operator-mediated; this is a destructive remote action (creates a public repo). "
            "Pass dry_run=true (default) to preview; explicit dry_run=false to execute."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "owner":             {"type": "string", "description": "GitHub owner of the new repo (typically the operator's handle)."},
                "name":              {"type": "string", "description": "GitHub repo name (e.g. paired-memory-kody-x-echo)."},
                "display_name":      {"type": "string", "description": "Human-readable name (e.g. 'Kody × Echo: Paired Memory')."},
                "purpose":           {"type": "string", "description": "1–3 sentence description of what the relationship is and what it's documenting."},
                "voice_a_rappid":    {"type": "string", "description": "First voice's rappid (must be a valid v2 rappid)."},
                "voice_a_label":     {"type": "string", "description": "First voice's display name (e.g. 'Kody')."},
                "voice_a_seed_text": {"type": "string", "description": "Initial identity paragraph for voice A's soul.md (1–3 sentences in their voice)."},
                "voice_b_rappid":    {"type": "string", "description": "Second voice's rappid."},
                "voice_b_label":     {"type": "string", "description": "Second voice's display name."},
                "voice_b_seed_text": {"type": "string", "description": "Initial identity paragraph for voice B's soul.md."},
                "dry_run":           {"type": "boolean", "description": "If true (default), preview only; if false, execute the plant."},
            },
            "required": ["owner", "name", "display_name", "purpose",
                          "voice_a_rappid", "voice_a_label", "voice_a_seed_text",
                          "voice_b_rappid", "voice_b_label", "voice_b_seed_text"],
        },
    }

    def __init__(self):
        super().__init__(name=self.metadata["name"], metadata=self.metadata)

    def perform(self, **kwargs: Any) -> str:
        # Validate required fields
        for k in ("owner", "name", "display_name", "purpose",
                   "voice_a_rappid", "voice_a_label", "voice_a_seed_text",
                   "voice_b_rappid", "voice_b_label", "voice_b_seed_text"):
            if not kwargs.get(k):
                return json.dumps({"ok": False, "error": f"missing required: {k}"}, indent=2)

        owner = kwargs["owner"]
        name = kwargs["name"]
        display_name = kwargs["display_name"]
        purpose = kwargs["purpose"]
        voice_a_rappid = kwargs["voice_a_rappid"]
        voice_b_rappid = kwargs["voice_b_rappid"]
        dry_run = bool(kwargs.get("dry_run", True))

        # Validate both rappids via the canonical parser (Article XLVI.5)
        try:
            door_address.door_from_rappid(voice_a_rappid)
            door_address.door_from_rappid(voice_b_rappid)
        except door_address.InvalidRappidError as e:
            return json.dumps({"ok": False, "error": f"invalid voice rappid: {e}"}, indent=2)

        if voice_a_rappid == voice_b_rappid:
            return json.dumps({"ok": False, "error": "voice_a and voice_b rappids are identical — bilateral requires two distinct anchors"}, indent=2)

        # Mint the new neighborhood's rappid (kind=neighborhood)
        rappid = _mint_rappid("neighborhood", owner, name)

        files = _build_bilateral_files(
            owner, name, display_name, purpose, rappid,
            voice_a_rappid, kwargs["voice_a_label"], kwargs["voice_a_seed_text"],
            voice_b_rappid, kwargs["voice_b_label"], kwargs["voice_b_seed_text"],
        )

        plan: dict[str, Any] = {
            "ok":               True,
            "schema":           "rapp-bilateral-plant-result/1.0",
            "owner":            owner,
            "name":             name,
            "display_name":     display_name,
            "rappid":           rappid,
            "voice_a_rappid":   voice_a_rappid,
            "voice_b_rappid":   voice_b_rappid,
            "files_planned":    sorted(files.keys()),
            "file_count":       len(files),
            "dry_run":          dry_run,
        }

        if dry_run:
            plan["next_step"] = "Re-invoke with dry_run=false to execute the plant."
            return json.dumps(plan, indent=2)

        # Live plant
        if _gh_repo_exists(owner, name):
            plan["ok"] = False
            plan["error"] = f"repo {owner}/{name} already exists; refusing to clobber"
            return json.dumps(plan, indent=2)

        ok, msg = _gh_create_repo(owner, name,
                                   f"Bilateral paired-memory neighborhood: {display_name}",
                                   public=True)
        if not ok:
            plan["ok"] = False
            plan["error"] = f"gh repo create failed: {msg}"
            return json.dumps(plan, indent=2)
        plan["repo_created"] = True

        results = {"created": [], "failed": []}
        for path, content in files.items():
            ok, msg = _gh_put_file(owner, name, path, content,
                                    f"plant_bilateral_neighborhood: {path}")
            (results["created"] if ok else results["failed"]).append(
                {"path": path, "msg": msg if not ok else f"wrote {len(content)}B"}
            )

        plan["files_created"] = len(results["created"])
        plan["files_failed"]  = len(results["failed"])
        if results["failed"]:
            plan["failed_paths"] = results["failed"]

        # Enable Pages so the heimdall front door at index.html is reachable
        pages_ok, pages_msg = _gh_enable_pages(owner, name)
        plan["pages_enabled"] = pages_ok
        plan["pages_status"]  = pages_msg

        plan["live_url"] = f"https://github.com/{owner}/{name}"
        plan["pages_url"] = f"https://{owner}.github.io/{name}/"
        plan["bilateral_manifest_url"] = f"https://raw.githubusercontent.com/{owner}/{name}/main/bilateral.json"

        # Append to local estate (Article XLVI.3 — strict shape {rappid, added_at, via})
        try:
            from estate_agent import append_to_estate
            append_to_estate("created", {
                "rappid":   rappid,
                "added_at": _now_iso(),
                "via":      "bilateral-plant",
            })
            plan["estate_updated"] = True
        except Exception as e:
            plan["estate_updated"] = False
            plan["estate_error"]   = str(e)[:200]

        plan["next_step"] = (
            f"Run bilateral_weekly_write_agent with repo={owner}/{name} and "
            f"voice=<voice_a_slug or voice_b_slug> to start the canvas."
        )
        return json.dumps(plan, indent=2)
