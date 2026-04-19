#!/usr/bin/env python3
"""
publish-bookfactory-to-rar.py — publish all BookFactory agent.py files to BOTH:
  1. RAR repo at agents/@rarbookworld/<slug>.py (with full RAR-required manifest)
  2. RAPP repo store/index.json (catalog entries with publisher: @rarbookworld)

Each source agent.py from RAPP/agents/ is rewritten with:
  - __manifest__ name flipped from "@rapp/foo-bar" to "@rarbookworld/foo_bar"
  - All RAR-required fields filled (display_name, description, author, category)
  - Composite imports rewritten to dir-agnostic _load_sibling() so the file
    works in agents/, agents/@rarbookworld/, or anywhere.

Run from RAPP root:
    python3 tools/publish-bookfactory-to-rar.py

Then run RAR's build_registry.py to refresh registry.json.
"""
from __future__ import annotations
import ast
import hashlib
import json
import re
import shutil
from pathlib import Path

RAPP_ROOT = Path(__file__).resolve().parent.parent
RAR_ROOT  = RAPP_ROOT.parent / "RAR"  # /Rappter/RAPP → /Rappter → /Rappter/RAR
DEST_DIR  = RAR_ROOT / "agents" / "@rarbookworld"
STORE     = RAPP_ROOT / "store" / "index.json"

# After v1.8 reorg, factory source files live under rapplications/{name}/{source,singleton}/
RAPPS_DIR = RAPP_ROOT / "rapplications"


def _src_path(filename: str) -> Path:
    """Map a filename to its on-disk source location after v1.8 reorg."""
    bf_source = RAPPS_DIR / "bookfactory" / "source"
    bf_singleton = RAPPS_DIR / "bookfactory" / "singleton"
    mf_source = RAPPS_DIR / "momentfactory" / "source"
    mf_singleton = RAPPS_DIR / "momentfactory" / "singleton"
    for d in (bf_singleton, bf_source, mf_singleton, mf_source):
        if (d / filename).exists():
            return d / filename
    raise FileNotFoundError(f"could not find {filename} under rapplications/")

PUBLISHER = "@rarbookworld"
AUTHOR    = "rarbookworld"
CATEGORY  = "pipeline"


# Each entry: source filename -> RAR slug + display name + description + extra metadata
AGENTS = [
    # ── leaves ────────────────────────────────────────────────────────
    ("persona_writer_agent.py",    "persona_writer_agent",    "Writer Persona",
     "Senior nonfiction writer. Takes raw source material and returns chapter-style prose with code preserved verbatim.",
     ["persona", "creative-pipeline", "writer"]),
    ("persona_publisher_agent.py", "persona_publisher_agent", "Publisher Persona",
     "Indie-press publisher. Takes edited prose plus a CEO note and outputs publication-ready markdown with YAML frontmatter.",
     ["persona", "creative-pipeline", "publisher"]),
    ("persona_reviewer_agent.py",  "persona_reviewer_agent",  "Reviewer Persona",
     "Cold-read reviewer. Returns a 1-5 score, the strongest single line, and whether they would keep reading.",
     ["persona", "creative-pipeline", "reviewer"]),
    ("editor_cutweak_agent.py",        "editor_cutweak_agent",        "Editor: Cut Weakest 20%",
     "Editor specialist. Returns the same prose with the weakest 20% cut. Preserves fenced code blocks as evidence.",
     ["editor-specialist", "creative-pipeline"]),
    ("editor_factcheck_agent.py",      "editor_factcheck_agent",      "Editor: Factcheck",
     "Editor specialist. Surfaces 2-5 claims that need a source and what kind of source would prove or disprove each.",
     ["editor-specialist", "creative-pipeline"]),
    ("editor_voicecheck_agent.py",     "editor_voicecheck_agent",     "Editor: Voice Drift",
     "Editor specialist. Flags voice drift — sentences that don't sound like the author's established voice.",
     ["editor-specialist", "creative-pipeline"]),
    ("editor_strip_scaffolding_agent.py", "editor_strip_scaffolding_agent", "Editor: Strip Scaffolding",
     "Editor specialist. Removes ## Outline headers, TODO markers, and draft-state labels left by the writer.",
     ["editor-specialist", "creative-pipeline"]),
    ("editor_restructure_agent.py",    "editor_restructure_agent",    "Editor: Restructure",
     "Editor specialist. Consolidates repetitive middle sections without rewriting the writer's voice.",
     ["editor-specialist", "creative-pipeline"]),
    ("ceo_decision_agent.py",      "ceo_decision_agent",      "CEO: Decision",
     "CEO specialist. Returns a one-line ship/edit/hold decision with the reasoning behind it.",
     ["ceo-specialist", "creative-pipeline"]),
    ("ceo_risk_agent.py",          "ceo_risk_agent",          "CEO: Partner Risk",
     "CEO specialist. Lists 1-3 partner-conversation risks that would actually matter in a real meeting.",
     ["ceo-specialist", "creative-pipeline"]),

    # ── composites ────────────────────────────────────────────────────
    ("persona_editor_agent.py",    "persona_editor_agent",    "Editor Persona (composite)",
     "Editor persona. Composite of 5 specialists: strip → cut → restructure, plus factcheck + voicecheck for the editor's note.",
     ["persona", "creative-pipeline", "composite"]),
    ("persona_ceo_agent.py",       "persona_ceo_agent",       "CEO Persona (composite)",
     "CEO persona. Composite of 2 specialists: decision + partner-risk. Returns a strategic-message-discipline review.",
     ["persona", "creative-pipeline", "composite"]),
    ("book_factory_agent.py",      "book_factory_agent",      "BookFactory (multi-file source)",
     "Five-persona content pipeline (Writer → Editor → CEO → Publisher → Reviewer) as a composite of 13 sibling agent.py files.",
     ["composite", "creative-pipeline", "twin-stack"]),

    # ── converged singleton ───────────────────────────────────────────
    ("bookfactory_agent.py",       "bookfactory_agent",       "BookFactory (converged singleton)",
     "Five-persona content pipeline collapsed into a single sacred file. Hatches alone with zero sibling deps. The deployable rapplication.",
     ["composite", "creative-pipeline", "twin-stack", "singleton", "rapplication"]),

    # ── MomentFactory: 7 personas + 1 composite + 1 converged singleton ─
    ("sensorium_agent.py",          "sensorium_agent",          "Sensorium",
     "Normalizes a raw moment (code commit, voice memo, bookmark, agent run, location, conversation, decision, reading note) into a structured JSON shape.",
     ["moment-pipeline", "ingest"]),
    ("significance_filter_agent.py","significance_filter_agent","Significance Filter",
     "Refuses moments that don't compound. The platform's defining constraint, encoded as one persona with veto power. Default: ship=false.",
     ["moment-pipeline", "filter"]),
    ("hook_writer_agent.py",        "hook_writer_agent",        "Hook Writer",
     "Writes the one sentence that earns a tap on the feed. Single sentence. Concrete over abstract. No clickbait.",
     ["moment-pipeline", "hook"]),
    ("body_writer_agent.py",        "body_writer_agent",        "Body Writer",
     "Writes the 3-5 sentence body of a Drop. Expands the hook, never restates. At least one concrete detail from key_facts.",
     ["moment-pipeline", "body"]),
    ("channel_router_agent.py",     "channel_router_agent",     "Channel Router",
     "Picks one Subrappter (r/builders, r/dreams, r/decisions, r/lessons, r/connections, etc.) for a Drop. Auto-classifies, no manual tagging.",
     ["moment-pipeline", "router"]),
    ("card_forger_agent.py",        "card_forger_agent",        "Card Forger",
     "Mints a RAR-compatible card (name + impact/novelty/compoundability stats + ability + lore + art_seed) from a Drop. Every Drop is a collectible.",
     ["moment-pipeline", "card"]),
    ("seed_stamper_agent.py",       "seed_stamper_agent",       "Seed Stamper",
     "Pure function (no LLM). Returns deterministic 64-bit seed + 7-word incantation from a 256-word wordlist. Speak the words → reconstruct the Drop offline.",
     ["moment-pipeline", "seed", "incantation"]),
    ("moment_factory_agent.py",     "moment_factory_agent",     "MomentFactory (multi-file source)",
     "Seven-persona moment-to-Drop pipeline as a composite of 8 sibling agent.py files. The candidate engine for any feed-driven AI-agent platform.",
     ["composite", "moment-pipeline", "rappterbook-engine"]),
    ("momentfactory_agent.py",      "momentfactory_agent",      "MomentFactory (converged singleton)",
     "Seven-persona moment-to-Drop pipeline collapsed into a single sacred file. Hatches alone with zero sibling deps. The candidate engine for Rappterbook.",
     ["composite", "moment-pipeline", "rappterbook-engine", "singleton", "rapplication"]),
]


# ── manifest rewriter ─────────────────────────────────────────────────

def _extract_manifest_block(src: str):
    """Find __manifest__ = {...} in source. Return (start, end, dict) or None."""
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "__manifest__":
                    return node.lineno - 1, node.end_lineno, ast.literal_eval(node.value)
    return None


def _rewrite_manifest(src: str, slug: str, display: str, desc: str, tags: list) -> str:
    """Replace the existing __manifest__ block with a RAR-compliant one."""
    found = _extract_manifest_block(src)
    if not found:
        raise RuntimeError(f"no __manifest__ found in source")
    start, end, old = found

    new = {
        "schema": "rapp-agent/1.0",
        "name": f"{PUBLISHER}/{slug.replace('_agent','')}",  # keep slug minus _agent suffix
        "version": old.get("version", "0.1.0"),
        "display_name": display,
        "description": desc,
        "author": AUTHOR,
        "tags": tags,
        "category": CATEGORY,
        "quality_tier": "community",
        "requires_env": ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT"],
        "dependencies": ["@rapp/basic_agent"] + [
            f"{PUBLISHER}/{d.replace('@rapp/','').replace('-','_')}"
            for d in (old.get("delegates_to") or [])
        ],
    }
    if old.get("delegates_to"):
        new["delegates_to"] = [
            f"{PUBLISHER}/{d.replace('@rapp/','').replace('-','_')}"
            for d in old["delegates_to"]
        ]
    if old.get("example_call"):
        new["example_call"] = old["example_call"]

    # Pretty-print the new manifest
    rendered = "__manifest__ = " + json.dumps(new, indent=4)
    lines = src.splitlines()
    return "\n".join(lines[:start] + [rendered] + lines[end:])


# ── import rewriter (composites only) ─────────────────────────────────

# Map original `from agents.X_agent import Y` to a dir-agnostic loader.
SIBLING_LOADER = '''
# ── dir-agnostic sibling loader (works in RAPP agents/, RAR agents/@rarbookworld/, anywhere) ──
import importlib.util as _ilu, os as _os, sys as _sys
def _load_sibling(filename, class_name):
    here = _os.path.dirname(_os.path.abspath(__file__))
    path = _os.path.join(here, filename)
    if not _os.path.exists(path):
        # fall back to RAPP agents/ layout for development
        from importlib import import_module as _im
        return getattr(_im(f"agents.{filename[:-3]}"), class_name)
    spec = _ilu.spec_from_file_location(filename[:-3], path)
    mod = _ilu.module_from_spec(spec)
    _sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return getattr(mod, class_name)
'''.strip()


def _rewrite_basic_agent_import(src: str) -> str:
    """Replace `from agents.basic_agent import BasicAgent` with a layout-agnostic try/except."""
    pattern = r'^from agents\.basic_agent import BasicAgent\s*$'
    replacement = (
        "try:\n"
        "    from agents.basic_agent import BasicAgent  # RAPP layout\n"
        "except ModuleNotFoundError:\n"
        "    try:\n"
        "        from basic_agent import BasicAgent      # flat / @publisher layout\n"
        "    except ModuleNotFoundError:\n"
        "        class BasicAgent:                       # last-resort standalone\n"
        "            def __init__(self, name, metadata): self.name, self.metadata = name, metadata"
    )
    return re.sub(pattern, replacement, src, count=1, flags=re.MULTILINE)


def _rewrite_sibling_imports(src: str) -> str:
    """
    For composites: convert
        from agents.persona_writer_agent import PersonaWriterAgent
    into
        PersonaWriterAgent = _load_sibling("persona_writer_agent.py", "PersonaWriterAgent")
    Also injects the SIBLING_LOADER helper near the top.
    """
    pattern = re.compile(r'^from\s+agents\.([a-z_]+_agent)\s+import\s+([A-Z][A-Za-z]+)\s*$', re.MULTILINE)
    matches = list(pattern.finditer(src))
    if not matches:
        return src

    # Build replacements
    replacements = []
    for m in matches:
        mod = m.group(1)
        cls = m.group(2)
        replacements.append((m.span(), f'{cls} = _load_sibling("{mod}.py", "{cls}")'))

    # Apply in reverse so spans stay valid
    out = src
    for (s, e), repl in reversed(replacements):
        out = out[:s] + repl + out[e:]

    # Inject loader after the BasicAgent import block
    # Insert it right before the first sibling-loader line
    first_loader_idx = out.find("_load_sibling(")
    if first_loader_idx >= 0:
        # Walk back to start of that line
        line_start = out.rfind("\n", 0, first_loader_idx) + 1
        out = out[:line_start] + SIBLING_LOADER + "\n\n" + out[line_start:]
    return out


# ── orchestrator ──────────────────────────────────────────────────────

def publish():
    DEST_DIR.mkdir(parents=True, exist_ok=True)

    # Wipe existing @rarbookworld dir to keep it tidy (idempotent republish)
    for old in DEST_DIR.glob("*.py"):
        old.unlink()
    for old in DEST_DIR.glob("*.py.card"):
        old.unlink()

    published = []

    for src_filename, slug, display, desc, tags in AGENTS:
        src_path = _src_path(src_filename)
        if not src_path.exists():
            print(f"  ✗ source missing: {src_path}")
            continue

        src = src_path.read_text()

        # 1. Rewrite manifest
        out = _rewrite_manifest(src, slug, display, desc, tags)

        # 2. Rewrite BasicAgent import (always — every file has one)
        out = _rewrite_basic_agent_import(out)

        # 3. Rewrite sibling imports (composites only)
        out = _rewrite_sibling_imports(out)

        # 4. Write to RAR
        dest = DEST_DIR / src_filename
        dest.write_text(out)

        published.append({
            "src": src_filename,
            "dest": str(dest.relative_to(RAR_ROOT)),
            "rar_name": f"{PUBLISHER}/{slug.replace('_agent','')}",
            "display": display,
            "sha256_rapp": hashlib.sha256(src.encode()).hexdigest(),
            "sha256_rar":  hashlib.sha256(out.encode()).hexdigest(),
            "lines_rapp": len(src.splitlines()),
            "lines_rar":  len(out.splitlines()),
            "bytes_rar":  len(out.encode()),
            "tags": tags,
            "desc": desc,
        })
        print(f"  ✓ {src_filename}  →  {dest.relative_to(RAR_ROOT)}")

    # Update RAPP store/index.json with the same set under publisher @rarbookworld
    _update_rapp_store(published)

    return published


def _update_rapp_store(published):
    cat = json.loads(STORE.read_text())

    # Tag the existing 2 bookfactoryagent entries with publisher
    for r in cat["rapplications"]:
        if r["id"].startswith("bookfactoryagent"):
            r["publisher"] = PUBLISHER

    # Build a set of existing entry ids so we can add new ones idempotently
    existing_ids = {r["id"] for r in cat["rapplications"]}

    for p in published:
        # Skip the singleton — it's already in the catalog as bookfactoryagent
        if p["src"] == "bookfactory_agent.py":
            continue

        slug_short = p["src"].replace("_agent.py","").replace("_","-")
        entry_id = f"rarbookworld-{slug_short}"
        if entry_id in existing_ids:
            continue

        cat["rapplications"].append({
            "id": entry_id,
            "name": p["display"],
            "version": "0.3.0",
            "publisher": PUBLISHER,
            "summary": p["desc"],
            "tagline": p["desc"],
            "category": "creative-pipeline",
            "tags": p["tags"],
            "manifest_name": p["rar_name"],
            "singleton_filename": p["src"],
            "singleton_url": f"https://raw.githubusercontent.com/kody-w/RAPP/main/agents/{p['src']}",
            "rar_url":       f"https://raw.githubusercontent.com/kody-w/RAR/main/{p['dest']}",
            "singleton_sha256": p["sha256_rapp"],
            "singleton_lines": p["lines_rapp"],
            "egg_url": None,
            "license": "BSD-style — see https://github.com/kody-w/RAPP",
            "produced_by": {
                "method": "double-jump-loop",
                "cycles": 3,
                "role": "component" if "composite" not in p["tags"] else "composite",
            },
        })

    STORE.write_text(json.dumps(cat, indent=2) + "\n")


if __name__ == "__main__":
    print("→ publishing BookFactory agents to RAR @rarbookworld + RAPP store...")
    pub = publish()
    print(f"\n✓ {len(pub)} agents published")
    print(f"  RAR:  {DEST_DIR}")
    print(f"  RAPP: {STORE}")
    print("\nNext: cd ../../RAR && python3 build_registry.py")
