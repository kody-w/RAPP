#!/usr/bin/env python3
"""plant_batcave.py — emit the RAPP Batcave scaffold (the source-of-truth grail).

The batcave is a standalone PRIVATE collaborator-gated neighborhood
(`kody-w/rapp-batcave`) in the private-workspace visibility pattern
(`kody-w/private-workspace-template` — "Bill's pattern"), whose planted quirk
is the **cubby**: each member's isolated housing for their FULL rapp estate —
agents, organs, senses, rapplications, whole neighborhoods, eggs — the same
environment as an on-device `~/.brainstem`, smashed into a directory so members
can learn from each other's organism as it grows. Bones in the repo, substance
on-device (PUBLIC_PRIVATE_BOUNDARY.md §1.8).

Spec compliance:
  - god spec (specs/SPEC.md) §3 door file set; kind=workspace (§2.1)
  - CONSTITUTION Art. XXXIV.1 — Eternity rappid `rappid:@<owner>/<slug>:<sha256-64hex>`
  - CONSTITUTION Art. XLVI.6 — parent_rappid = planter's personal rappid
  - PUBLIC_PRIVATE_BOUNDARY §1.8 — repo carries the organism's bones, never PII
  - rapp-rar-index/1.1 — sha256-pinned participation kit

Idempotent: re-running refreshes generated files + sha256 pins but preserves
the minted rappid + minted_at and never touches member-owned cubby content
(except re-seeding kody-w's cubby agents from rapp_brainstem/agents/ while
those source files exist).

Usage:
    python3 tools/plant_batcave.py                       # → examples/rapp-batcave/
    python3 tools/plant_batcave.py --out /path/to/dir    # custom target
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

import front_door_specs          # noqa: E402  (bundle 2.0.0)
import holo_card_generator as hcg  # noqa: E402  (rappcards/1.1.2)

REPO_ROOT = Path(_TOOLS_DIR).parent
OWNER = "kody-w"
SLUG = "rapp-batcave"
KIND = "workspace"
DISPLAY_NAME = "The Batcave"
GATE_URL = f"https://github.com/{OWNER}/{SLUG}"
PARENT_RAPPID = "rappid:@kody-w/kody-twin:91d006ca7bd052bfa5021d623122012f"
PARENT_REPO = "https://github.com/kody-w/RAPP"
# The generic public dialer for private doors — names no door, leaks nothing.
PAYPHONE_URL = "https://kody-w.github.io/RAPP/pages/payphone.html"

# Estate anatomy a cubby houses (same layers as the on-device brainstem).
CUBBY_ANATOMY = ("agents", "organs", "senses", "rapplications",
                 "neighborhoods", "eggs", "show-and-tell")

# Operator agents that migrate out of the grail-repo working tree into the
# founding cubby (streamed back in via `batcave load`, never committed there).
KODY_CUBBY_AGENTS = (
    "clawpilot_twin_agent.py", "commons_agent.py", "schedule_reply_agent.py",
    "twin_me_agent.py", "workiq_agent.py",
)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def mint_rappid(owner: str = OWNER, slug: str = SLUG) -> str:
    """Eternity format per CONSTITUTION Art. XXXIV.1 (locked 2026-06-03):
    `rappid:@<owner>/<slug>:<64hex>` — full 256-bit SHA-256 of `<owner>/<slug>`;
    `kind` lives in the record, never the string."""
    h = hashlib.sha256(f"{owner}/{slug}".encode()).hexdigest()
    return f"rappid:@{owner}/{slug}:{h}"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _write_json(path: Path, obj: dict) -> None:
    _write(path, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- templates

def _soul_md() -> str:
    return f"""# {DISPLAY_NAME}

I am **{DISPLAY_NAME}** — the private workshop neighborhood where a crew of
operators park their cubbies and show each other what they're cooking.

## Identity — read this every turn

Your name is **{DISPLAY_NAME}**. When greeting someone for the first time in a
conversation, introduce yourself by name: "Hi, I'm {DISPLAY_NAME}."

Do not introduce yourself as "RAPP", "an AI assistant", "your AI helper",
"the brainstem", or any default branding. Those are scaffolding, not me.

If asked "who are you" or "what's your name", answer with **{DISPLAY_NAME}**
— not "RAPP", not the generic platform name. If a visitor asks which
underlying language model is hosting me, you may name it, but reassert that
the identity is **{DISPLAY_NAME}**: the model is the substrate, not the self.

## How I speak

- First-person, direct, workshop-floor tone. Less lobby, more lab.
- Concise by default — say what's worth saying, then stop.
- I know whose cubby is whose, and I never blur that line.

## What I do

- Welcome members and point them at their cubby (`cubbies/<your-handle>/`).
- Surface what's new — the show-and-tell stream is the heartbeat here.
- Help members stream agents from cubbies into their local brainstem
  (`batcave load`) without ever dirtying a grail repo.

## What I don't do

- Speak as "RAPP" or "the platform".
- Read or write another member's cubby on someone's behalf — cubbies are
  isolated by design; sharing happens by browsing, not by reaching in.
- Move anything private-side (PII, secrets, customer substance) into the
  repo. Bones live here; substance stays on each member's device.

---

*This is the neighborhood's default voice. Edit this file to change how the
batcave speaks — it travels with the repo.*
"""


def _cubby_protocol_md(rappid: str) -> str:
    return f"""# CUBBY_PROTOCOL.md — the batcave's planted quirk

> Schema family: `rapp-batcave-cubby/1.0` · `rapp-batcave-cubbies/1.0` ·
> `rapp-batcave-event/1.0` · `rapp-batcave-loadout/1.0`
> Neighborhood: `{rappid}`
> Parent specs: `specs/SPEC.md` (god spec), `specs/WORKSPACE_PROTOCOL.md`,
> PUBLIC_PRIVATE_BOUNDARY.md §1.8 (bones vs substance), RAPP-Bible specs hub
> (https://kody-w.github.io/RAPP-Bible/#specs)

Every neighborhood plants its own quirks. The batcave's quirk is the **cubby**.

> **This file overrides `specs/WORKSPACE_PROTOCOL.md` on access + joining.**
> The generic workspace protocol (from the shared bundle) describes a
> public-readable, Issue-to-join workspace. The batcave is the opposite:
> PRIVATE with **no public front door**, join is collaborator-access
> out-of-band, and outsiders 404. Where the two disagree, the cubby protocol
> wins for this neighborhood.

## 1. What a cubby is

A cubby is one member's **isolated housing for their entire rapp estate** —
the same environment their local computer provides for their on-device
brainstem, smashed into a directory:

```
cubbies/<github-handle>/
├── cubby.json          # rapp-batcave-cubby/1.0 — who lives here + what's cooking
├── front_door.md       # sanitized intro (PUBLIC_PRIVATE_BOUNDARY §1.8.1)
├── soul.md             # optional — the cubby twin's voice
├── agents/             # single-file *_agent.py (incl. factory agents, industries)
├── organs/             # *_organ.py HTTP extensions
├── senses/             # per-channel output overlays
├── rapplications/      # graduated workflows with UI bundles
├── neighborhoods/      # ENTIRE planted neighborhoods can live here
├── eggs/               # .egg cartridges to share
├── show-and-tell/      # YYYY-MM-DD-<slug>.md posts (the agentic show & tell)
└── projects.json       # optional — slugs + status enums + dates ONLY
```

Bottom-to-top is welcome: agents → factory agents → organs → senses →
rapplications → full neighborhoods. A cubby is allowed to grow into its own
organism — that is the point. Other members browse it to learn.

## 2. Isolation — the load-bearing property

- **You write only inside your own cubby** (plus the append-only zones:
  `events/`, your entry in `members.json` + `cubbies/index.json`).
- Cross-cubby changes ride pull requests the cubby owner merges.
- `.github/CODEOWNERS` maps each cubby to its owner; the `cubby-guard`
  workflow flags PRs and pushes that touch someone else's cubby.
- Reading is open to every collaborator — that's the learning surface.

## 3. Bones, not substance (PUBLIC_PRIVATE_BOUNDARY §1.8)

The repo holds what members SHARE (code, souls, manifests, posts). Each
member's PII-bearing substance — customer names, transcripts, tokens,
`.env`, memory stores — stays on their device in `~/.brainstem/` /
`~/.brainstem/workbenches/`. The `.gitignore` enforces the default;
`batcave stash` refuses secret-shaped files outright.

## 4. Streaming (store in the cubby, load into the brainstem)

The batcave is the storage layer for agents you do NOT want committed to a
brainstem grail repo as kernel agents:

1. `batcave stash path=<file>` — put an agent (or egg, or note) in your cubby.
2. `batcave load cubby=<handle>` — stream a cubby's `agents/` into your local
   brainstem's `agents/` folder. Streamed files are registered in the host
   repo's `.git/info/exclude`, so they run like any agent but are invisible
   to git — they can never be accidentally committed to the grail repo.
3. `batcave unload` — remove streamed agents cleanly (loadout-tracked).

Kited vTwins collaborate the same way: the GitHub account a vBrainstem is
signed in with has collaborator access, so the same clone/stream contract
holds on every substrate (Art. XLVII).

## 5. Personal branches

Work you don't want on `main` yet lives on branches named
`cubby/<your-handle>/<topic>` (e.g. `cubby/kody-w/overnight-rnd`). They are
yours; nobody merges them for you; they may live forever unmerged.
`main` stays the shared truth.

## 6. Events — the agentic show & tell

Append-only signed events in `events/` (see `events/SCHEMA.md`,
`rapp-batcave-event/1.0`). Kinds: `hello`, `show-and-tell`, `ask`, `reply`,
`fyi`, `leave`. Merge rule: `(from, ts)` is the universal key — clones can
diverge offline indefinitely and union losslessly. Agents post
`show-and-tell` events to report what's new; members read the stream with
`batcave sync`.

## 7. Finding the batcave — no public front door, by design

The batcave has **no public front door** (it's the batcave). The repo is
private; to anyone without collaborator access every URL returns **404** —
wrong number and no-access are indistinguishable, so the door's *contents*
and *membership* stay invisible to outsiders. (The repo NAME and rappid are
not themselves secret — the rappid is the deterministic sha256 of the
owner/slug, the same way a phone number isn't a secret; the protection is
GitHub's 404, not name-obscurity. This mirrors how
`kody-w/microsoft-se-team-neighborhood` openly names its private companion.)

Members dial in instead:

- **Local brainstems**: `gh auth login` once; `batcave mount` clones via
  your collaborator access.
- **Kited vTwins on the public web**: use the **payphone** — the generic
  public dialer at https://kody-w.github.io/RAPP/pages/payphone.html. Paste
  the door's rappid (your phone number, handed to you out-of-band via the
  invite egg / QR / a message) + your GitHub token (`repo` scope — e.g.
  `gh auth token`; the page also reads a signed-in vBrainstem's Doorman
  `rapp_settings`). Collaborator access = dial tone; everyone else hears
  404. The payphone names no door and logs nothing — it is a dial pad on
  the public web, nothing more (Art. XLVI: the rappid IS the address;
  Art. XLVII: same contract on every substrate).

## 8. Joining

1. Get collaborator access from the operator (out-of-band — ask kody-w).
2. Clone, then from your brainstem: `batcave join` (creates your cubby), or
   copy `cubbies/_template/` to `cubbies/<your-handle>/` by hand.
3. Post a `hello` (`batcave show_and_tell title="hello"`). The room sees you.
"""


def _events_schema_md(rappid: str) -> str:
    return f"""# Event Schema — `rapp-batcave-event/1.0`

Append-only signed events for the batcave (`{rappid}`).
Filename pattern: `events/<from-fingerprint16>-<utc-compact-ts>.json`.

## Event object

```json
{{
  "schema": "rapp-batcave-event/1.0",
  "kind": "hello | show-and-tell | ask | reply | fyi | leave",
  "from": "<operator rappid string — opaque, never parsed here>",
  "ts": "<RFC3339 UTC>",
  "cubby": "<github-handle>",
  "body": {{ "title": "...", "text": "...", "artifact": "cubbies/<h>/show-and-tell/<file>" }},
  "in_reply_to": "<event filename or null>",
  "pub": {{ "kty": "EC", "crv": "P-256", "x": "...", "y": "..." }},
  "sig": "<base64url IEEE-P1363 ECDSA P-256 over canonical JSON sans sig>"
}}
```

Canonical bytes = recursively key-sorted, compact, UTF-8 JSON (the same
`stableStringify` the commons web UI verifies byte-for-byte).

## Merge rule

`(from, ts)` is the universal key. Two clones can produce events offline
indefinitely; the batcave is the union of all valid events, sorted by `ts`
then `from`. No shared mutable state; no edits; no deletes.

## Verification

1. `from` starts with `rappid:` (opaque — only `tools/door_address.py` parses).
2. The event filename prefix equals `sha256(from)[:16]` (deterministic in
   both the signed and signing-intent paths).
3. `sig` verifies against `pub` over the canonical event sans `sig`.
4. `kind` is recognized; `body.text` ≤ 4096 chars.
5. Unsigned events are accepted only as `"signing_intent"` drafts and never
   federate beyond the repo.

## Show-and-tell

The agentic show & tell: an agent that shipped something appends a
`show-and-tell` event pointing at a markdown artifact in its operator's
cubby. `batcave sync` surfaces what's new since your last look.
"""


def _contributing_md() -> str:
    return f"""# Contributing to {DISPLAY_NAME}

Membership = GitHub collaborator status on this private repo
(`{OWNER}/{SLUG}`). The operator adds you:

```bash
gh api -X PUT repos/{OWNER}/{SLUG}/collaborators/<your-login> --field permission=push
```

## The three rules

1. **Write only in your own cubby** (`cubbies/<your-handle>/`) plus the
   append-only zones (`events/`, your own entries in `members.json` and
   `cubbies/index.json`). Anything touching someone else's cubby goes
   through a PR they merge. CODEOWNERS + the cubby-guard workflow enforce
   the line.
2. **Bones, not substance.** No PII, no secrets, no customer material —
   `.gitignore` covers the defaults and `batcave stash` refuses
   secret-shaped files (PUBLIC_PRIVATE_BOUNDARY §1.8). Audit your diff
   before pushing.
3. **Personal branches are `cubby/<your-handle>/<topic>`.** They never need
   to merge to `main`; keep WIP there as long as you like. `main` is the
   shared truth everyone's `batcave sync` pulls.

## Day one

```bash
gh repo clone {OWNER}/{SLUG}
# from your brainstem chat: "batcave join", then "batcave show_and_tell title=hello"
# or by hand: cp -r cubbies/_template cubbies/<your-handle> && edit cubby.json
```

To run a brainstem against your cubby directly:

```bash
AGENTS_PATH=cubbies/<you>/agents SOUL_PATH=cubbies/<you>/soul.md PORT=7073 \\
  python3 brainstem.py   # from your local brainstem checkout
```

Or stream cubby agents into your existing brainstem without commit risk:
`batcave load` (registers them in `.git/info/exclude` — git never sees them).
"""


def _readme_md(rappid: str) -> str:
    return f"""# 🦇 {DISPLAY_NAME}

A **private RAPP neighborhood workspace**. Every member gets a **cubby** —
isolated housing for their entire rapp estate (agents, organs, senses,
rapplications, whole neighborhoods, eggs) — the same environment as their
on-device brainstem, smashed into a directory the rest of the crew can
browse and learn from.

- **Identity:** `{rappid}` (kind `{KIND}`, Eternity format, Art. XXXIV.1)
- **Visibility:** private, standalone — the repo IS the workspace
  (the `private-workspace` pattern; membership = collaborator status)
- **Front door:** none, by design. Outsiders 404; kited vTwins dial the
  rappid at the [payphone]({PAYPHONE_URL}) with their own GitHub auth.
- **Quirk:** `specs/CUBBY_PROTOCOL.md` — cubbies, streaming, show & tell
- **Specs hub:** https://kody-w.github.io/RAPP-Bible/#specs

## Why it exists

> "I have a private repo for my customer facing agents and then I use rar
> for ones that I want to share." — the common central resource problem.

The batcave is the shared private middle: store agents here instead of
committing them to any brainstem grail repo, stream them into a local
brainstem on demand (`batcave load` → `.git/info/exclude`, zero commit
risk), and show the crew what you're cooking (`batcave show_and_tell`).
Kited vTwins join with the same GitHub account that holds their
collaborator access — same contract on every substrate.

## Join (collaborators)

```bash
gh repo clone {OWNER}/{SLUG}
cp agents/batcave_agent.py <your-brainstem>/agents/   # the participation agent
# then from your brainstem chat:
#   "batcave join"                      → creates cubbies/<you>/
#   "batcave browse"                    → see everyone's cubbies
#   "batcave load cubby=kody-w"         → stream agents into your brainstem
#   "batcave show_and_tell title=..."   → post to the room
```

Not a collaborator yet? Ask the operator (@{OWNER}) — out-of-band by design.

## The map

| Path | What |
|---|---|
| `cubbies/<handle>/` | one member's estate housing (isolated; owner-only writes) |
| `cubbies/_template/` | copy me to join by hand |
| `events/` | append-only signed show-and-tell stream |
| `agents/batcave_agent.py` | the participation agent (`@kody-w/batcave`) |
| `rar/index.json` | sha256-pinned participation kit (`rapp-rar-index/1.1`) |
| `specs/` | the god spec + workspace protocol + the cubby quirk |
| `.well-known/batcave.egg` | tiny invite egg (pointers, not contents) |

Planted from [`kody-w/RAPP`]({PARENT_REPO}) `examples/rapp-batcave/` by
`tools/plant_batcave.py`.
"""


def _holo_md(rappid: str, seed: int) -> str:
    return f"""---
schema: rapp-holo/1.1.2
rappid: {rappid}
display_name: {DISPLAY_NAME}
kind: {KIND}
seed: "{seed}"
---

# {DISPLAY_NAME} — holo

**The private workshop.** Each member's cubby houses their full rapp estate —
bottom-to-top: agents, factory agents, organs, senses, rapplications, entire
neighborhoods — isolated so every estate grows into its own organism, open so
the crew learns from each other.

## For an AI reading this

1. You are at a **gate** (kind `{KIND}`), private, collaborator-gated.
2. Your operator's GitHub account must be a collaborator; verify with
   `gh repo view {OWNER}/{SLUG}`.
3. Participate through the `@kody-w/batcave` agent (`agents/batcave_agent.py`):
   `join` → `browse` → `stash`/`load` → `show_and_tell` → `sync`.
4. Write ONLY under `cubbies/<your-operator's-handle>/` + the append-only
   zones. Cubbies are isolated by design.
5. The full quirk contract: `specs/CUBBY_PROTOCOL.md`. The universal law:
   `specs/SPEC.md`. Runbook: `specs/skill.md`.
"""


def _index_html(rappid: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{DISPLAY_NAME} — private RAPP neighborhood</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
         background:#0d1117; color:#e6edf3; max-width:880px; margin:2rem auto;
         padding:0 1rem; line-height:1.55; }}
  h1 {{ color:#ffd33d; }} a {{ color:#79c0ff; }}
  .card {{ border:1px solid #30363d; border-radius:8px; padding:1rem;
          margin:.6rem 0; background:#161b22; }}
  .pill {{ display:inline-block; border:1px solid #30363d; border-radius:999px;
          padding:.05rem .6rem; margin-right:.4rem; font-size:.8rem;
          color:#8b949e; }}
  code {{ background:#161b22; padding:.1rem .3rem; border-radius:4px; }}
</style>
</head>
<body>
<h1>🦇 {DISPLAY_NAME}</h1>
<p><span class="pill">private</span><span class="pill">kind: {KIND}</span>
<span class="pill">cubby neighborhood</span></p>
<p><code>{rappid}</code></p>
<p>Every member gets a <strong>cubby</strong> — isolated housing for their full
rapp estate. Browse the cubbies, learn from each organism, stream agents into
your own brainstem with <code>batcave load</code>.</p>
<div class="card">
  <strong>Join:</strong> ask the operator for collaborator access, then
  <code>gh repo clone {OWNER}/{SLUG}</code> and run <code>batcave join</code>
  from your brainstem. Full steps: <a href="CONTRIBUTING.md">CONTRIBUTING.md</a>
  · quirk contract: <a href="specs/CUBBY_PROTOCOL.md">CUBBY_PROTOCOL.md</a>
</div>
<div id="cubbies"><div class="card">Serve this directory
(<code>python3 -m http.server</code> in the clone) to see the live cubby
gallery — file:// can't fetch. The gallery reads
<code>cubbies/index.json</code> from the clone: local-first, no network.</div>
</div>
<script>
/* Local-first only: relative fetch against the clone/server. No bare
   github.com fetches (ANTIPATTERNS §5) — offline keeps rendering. */
function esc(s) {{ return String(s == null ? '' : s).replace(/[&<>"']/g,
  c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c])); }}
fetch('cubbies/index.json').then(r => r.json()).then(idx => {{
  const root = document.getElementById('cubbies');
  root.innerHTML = '';
  (idx.cubbies || []).forEach(c => {{
    const d = document.createElement('div');
    d.className = 'card';
    const h = esc(c.github_login);
    d.innerHTML = '<strong>🗄️ ' + h + '</strong> — ' +
      esc(c.what_im_cooking || '...') +
      ' <a href="cubbies/' + encodeURIComponent(c.github_login) + '/front_door.md">front door</a>';
    root.appendChild(d);
  }});
}}).catch(() => {{ /* offline / file:// — static instructions remain */ }});
</script>
</body>
</html>
"""


def _cubby_guard_yml() -> str:
    return """name: cubby-guard
# The batcave's isolation property, enforced: you write only inside your own
# cubby (plus the append-only zones). PRs touching someone else's cubby fail;
# direct pushes get a warning annotation (history stays append-only).
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  guard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Check cubby ownership
        env:
          ACTOR: ${{ github.actor }}
          EVENT: ${{ github.event_name }}
          BASE_SHA: ${{ github.event.pull_request.base.sha || github.event.before }}
          HEAD_SHA: ${{ github.event.pull_request.head.sha || github.sha }}
        run: |
          set -euo pipefail
          if [ -z "$BASE_SHA" ] || [ "$BASE_SHA" = "0000000000000000000000000000000000000000" ]; then
            echo "initial push — skipping"; exit 0
          fi
          violations=0
          while IFS= read -r f; do
            case "$f" in
              cubbies/_template/*) ;;            # template is shared
              cubbies/index.json) ;;             # append-only roster zone
              cubbies/*/*)
                owner=$(echo "$f" | cut -d/ -f2)
                if [ "$owner" != "$ACTOR" ]; then
                  echo "::warning file=$f::$ACTOR changed $owner's cubby"
                  violations=$((violations+1))
                fi ;;
            esac
          done < <(git diff --name-only "$BASE_SHA" "$HEAD_SHA")
          if [ "$violations" -gt 0 ] && [ "$EVENT" = "pull_request" ]; then
            echo "::error::PR touches another member's cubby ($violations file(s)). Cubbies are isolated — ask the owner to merge this themselves."
            exit 1
          fi
          echo "cubby-guard OK ($violations warning(s))"
"""


def _gitignore() -> str:
    return """# Bones live in the repo; substance stays on-device
# (PUBLIC_PRIVATE_BOUNDARY.md §1.8 — PII + secrets never enter the batcave).
.brainstem/
.brainstem_data/
.bwat-data/
.env
.env.*
.copilot_token
.copilot_session
.lineage_key
private-estate-secret
keys/
*.pem
__pycache__/
*.pyc
.DS_Store
node_modules/
venv/
.venv/
"""


def _front_door_template() -> str:
    return """# <Your Name> — front door

*Sanitized intro (PUBLIC_PRIVATE_BOUNDARY §1.8.1): who you are, what your
estate is growing into, what you're happy to be asked about. Slugs + status
only — no customer names, no substance.*

## What I'm cooking

- ...

## In my cubby

- `agents/` — ...
- `show-and-tell/` — the running log
"""


# ---------------------------------------------------------------- the plant

def plant(out_dir: str | None = None, *, seed_agents: bool = False) -> dict:
    """Emit the batcave scaffold.

    seed_agents=False (default) → the GENERIC public template: kody-w's
    founder cubby exists but ships ZERO agent files (bones-only). This is
    what lives in the public kody-w/RAPP repo under examples/rapp-batcave/.

    seed_agents=True → the REAL private instance: copies the operator's live
    agents out of rapp_brainstem/agents/ into the founder cubby. Run this
    ONLY when staging for the PRIVATE kody-w/rapp-batcave push — never commit
    its output to the public grail repo (that's the whole point: keep these
    agents OUT of the public installer repo).
    """
    out = Path(out_dir) if out_dir else REPO_ROOT / "examples" / "rapp-batcave"
    out.mkdir(parents=True, exist_ok=True)
    rappid = mint_rappid()
    seed = hcg.derive_seed(rappid)
    written: list[str] = []

    def W(rel: str, content: str):
        _write(out / rel, content)
        written.append(rel)

    def WJ(rel: str, obj: dict):
        _write_json(out / rel, obj)
        written.append(rel)

    # ---- identity (preserve minted_at across replants)
    rappid_path = out / "rappid.json"
    minted_at = _now()
    if rappid_path.exists():
        try:
            minted_at = json.loads(rappid_path.read_text()).get("minted_at", minted_at)
        except (json.JSONDecodeError, OSError):
            pass
    WJ("rappid.json", {
        "schema": "rapp-rappid/2.0",
        "rappid": rappid,
        "kind": KIND,
        "name": SLUG,
        "display_name": DISPLAY_NAME,
        "host": "github.com",
        "owner": OWNER,
        "repo": SLUG,
        "github": GATE_URL,
        "url": None,
        "parent_rappid": PARENT_RAPPID,
        "parent_repo": PARENT_REPO,
        "planted_by": OWNER,
        "minted_at": minted_at,
        "notes": ("The Batcave — standalone private cubby neighborhood "
                  "(private-workspace pattern). Each member's cubby houses "
                  "their full rapp estate, isolated. Per CONSTITUTION Article "
                  "XLVI this rappid is the permanent global address. Article "
                  "XXXIV.1 locks the STRING FORMAT (Eternity "
                  "`rappid:@<owner>/<slug>:<64hex>`); the 64hex here is the "
                  f"deterministic sha256 of '{OWNER}/{SLUG}' — the same "
                  "self-locating neighborhood-mint convention rapp-commons "
                  "uses, upgraded to full 256-bit. Membership = GitHub "
                  "collaborator status on this repo."),
    })

    WJ("neighborhood.json", {
        "schema": "rapp-neighborhood/1.0",
        "neighborhood_rappid": rappid,
        "kind": KIND,
        "name": SLUG,
        "display_name": DISPLAY_NAME,
        "tagline": "The private workshop. Park your estate in a cubby; show the crew what you're cooking.",
        "github": GATE_URL,
        "url": None,
        "visibility": "private-workspace",
        "purpose": ("A standalone private workspace-neighborhood (the "
                    "private-workspace pattern, extended): every member gets "
                    "a cubby — isolated housing for their FULL rapp estate "
                    "(agents, organs, senses, rapplications, whole "
                    "neighborhoods, eggs) — the same environment as their "
                    "on-device brainstem. Members stream agents from cubbies "
                    "into local brainstems without grail-repo commit risk, "
                    "and agents report what's new on the show-and-tell "
                    "stream."),
        "private_companion": None,
        "gate_repo": None,
        "parent_rappid": PARENT_RAPPID,
        "parent_repo": PARENT_REPO,
        "planted_by": OWNER,
        "planted_at": minted_at,
        "quirks": {
            "primitive": "cubby",
            "spec": "specs/CUBBY_PROTOCOL.md",
            "cubby_anatomy": list(CUBBY_ANATOMY),
            "isolation": "owner-only writes per cubby; append-only shared zones; cross-cubby via PR",
            "streaming": "batcave load → target brainstem agents/ + .git/info/exclude (zero commit risk)",
            "event_protocol": "rapp-batcave-event/1.0",
            "event_kinds": ["hello", "show-and-tell", "ask", "reply", "fyi", "leave"],
            "merge_rule": "(from, ts) is the universal key; append-only union",
        },
        "membership_policy": {
            "default_collaborator_permission": "push",
            "founder_only_seats": ["admin"],
            "join_path": "out_of_band",
            "notes": ("No public join path. The operator grants access via "
                      f"`gh api -X PUT /repos/{OWNER}/{SLUG}/collaborators/<login>` "
                      "after an out-of-band conversation. Kited vTwins ride "
                      "the same collaborator grant (Art. XLVII)."),
        },
        "branch_model": {
            "main": "shared truth — cubby-scoped writes + append-only zones",
            "personal": "cubby/<handle>/<topic> — yours; never required to merge",
        },
        "front_door": "none-by-design",
        "addresses": {
            "github": GATE_URL,
            "local": "~/.brainstem/neighborhoods/rapp-batcave/clone",
            "payphone": PAYPHONE_URL,
            "_note": ("No public front door — it's the batcave. Outsiders "
                      "404 (invisible). Members and kited vTwins dial the "
                      "rappid at the payphone with their own GitHub auth "
                      "(collaborator access = dial tone)."),
        },
        "specs_hub": "https://kody-w.github.io/RAPP-Bible/#specs",
    })

    # ---- roster (preserve any members added since plant)
    members_path = out / "members.json"
    existing_members = []
    if members_path.exists():
        try:
            existing_members = json.loads(members_path.read_text()).get("members", [])
        except (json.JSONDecodeError, OSError):
            pass
    if not any(m.get("github_login") == OWNER for m in existing_members):
        existing_members.insert(0, {
            "github_login": OWNER,
            "rappid": PARENT_RAPPID,
            "role": "founder",
            "capabilities": ["all"],
            "joined_at": minted_at,
            "via": "genesis",
            "notes": "Founder seat. Adds members via the invite action / gh api.",
        })
    WJ("members.json", {
        "schema": "rapp-neighborhood-members/1.0",
        "neighborhood_rappid": rappid,
        "version": 1,
        "synced_at": _now(),
        "synced_from": "plant_batcave",
        "open_to_anyone": False,
        "join_path": "out_of_band → operator approval → collaborator add",
        "members": existing_members,
        "reconciliation": {
            "policy": "github_collaborators_api_is_canonical",
            "notes": ("Membership IS GitHub collaborator status on this repo. "
                      "members.json is the protocol-layer mirror; reconcile "
                      f"with `gh api repos/{OWNER}/{SLUG}/collaborators`."),
        },
    })

    WJ("facets.json", {
        "schema": "rapp-public-facets/1.0",
        "neighborhood_rappid": rappid,
        "public_facets": [
            {"name": "neighborhood_purpose", "scope": "public",
             "description": "What the batcave is — a private cubby neighborhood. The only outward-facing fact."},
            {"name": "join_path", "scope": "public",
             "description": "Out-of-band: ask the operator for collaborator access."},
            {"name": "cubby_roster", "scope": "neighborhood",
             "description": "Whose cubbies exist + what they're cooking. Collaborators only."},
            {"name": "shared_agents", "scope": "neighborhood",
             "description": "Streamable agents across all cubbies (sha256-pinned in rar/index.json)."},
            {"name": "show_and_tell", "scope": "neighborhood",
             "description": "The append-only signed event stream — the agentic show & tell."},
            {"name": "cubby_contents", "scope": "personal",
             "description": "A cubby's substance beyond its declared bones. Owner-curated."},
        ],
    })

    # ---- holo set
    card = hcg.generate_holo_card(rappid, KIND, OWNER, SLUG, DISPLAY_NAME,
                                  gate_url=GATE_URL)
    WJ("card.json", card)
    W("holo.svg", hcg.generate_avatar_svg(seed, KIND))
    W("holo-qr.svg", hcg.generate_summon_qr_svg(seed, GATE_URL))
    W("holo.md", _holo_md(rappid, seed))

    # ---- soul / docs / front door
    W("soul.md", _soul_md())
    W("README.md", _readme_md(rappid))
    W("CONTRIBUTING.md", _contributing_md())
    W("index.html", _index_html(rappid))
    W(".nojekyll", "")
    W(".gitignore", _gitignore())

    # ---- specs bundle (2.0.0) + the planted quirk
    bundle = front_door_specs.bundle_for_kind(KIND, owner=OWNER, name=SLUG,
                                              display_name=DISPLAY_NAME,
                                              parent_repo=PARENT_REPO)
    for rel, content in bundle.items():
        W(rel, content)
    W("specs/CUBBY_PROTOCOL.md", _cubby_protocol_md(rappid))

    # ---- events
    W("events/SCHEMA.md", _events_schema_md(rappid))

    # ---- invite egg (pointers, not contents — collaborator-gated)
    WJ(".well-known/batcave.egg", {
        "schema": "brainstem-egg/2.3-neighborhood",
        "type": "neighborhood-invite",
        "version": "1.0",
        "rappid": rappid,
        "display_name": DISPLAY_NAME,
        "kind": KIND,
        "soul_summary": ("Private cubby neighborhood — each member's cubby "
                         "houses their full rapp estate, isolated. "
                         "Collaborator-gated; no public gate."),
        "neighborhood_url": GATE_URL,
        "neighborhood_json": f"https://raw.githubusercontent.com/{OWNER}/{SLUG}/main/neighborhood.json",
        "payphone": PAYPHONE_URL,
        "join_via": ("collaborator-access → gh repo clone → batcave join. "
                     "This repo is PRIVATE with no public front door: every "
                     "URL above requires the hatcher's GitHub auth (gh CLI / "
                     "signed-in vBrainstem) — outsiders 404. Kited vTwins "
                     "dial the rappid at the payphone. Not a collaborator? "
                     "Ask the operator out-of-band."),
        "invite_created_at": minted_at,
        "invite_expires_at": None,
        "notes": ("Tiny invite egg (pointers, not contents). The hatcher "
                  "validates the rappid, then records {rappid, added_at, via} "
                  "in the operator's two-tier estate per Article XLVI."),
    })

    # ---- cubby template (full estate anatomy)
    for d in CUBBY_ANATOMY:
        keep = out / "cubbies" / "_template" / d / ".gitkeep"
        keep.parent.mkdir(parents=True, exist_ok=True)
        keep.write_text("")
    WJ("cubbies/_template/cubby.json", {
        "schema": "rapp-batcave-cubby/1.0",
        "github_login": "<your-handle>",
        "rappid": "<your operator rappid — opaque string>",
        "display_name": "<Your Name>",
        "what_im_cooking": "<one line — shows in the gallery + browse>",
        "created_at": "<RFC3339 UTC>",
        "estate": {
            "note": ("A cubby houses a FULL rapp estate, bottom to top: "
                     "agents (incl. factory agents / industries), organs, "
                     "senses, rapplications, whole neighborhoods, eggs. "
                     "Isolated from every other cubby; grow it into its own "
                     "organism."),
            "anatomy": list(CUBBY_ANATOMY),
        },
        "streamable": {"agents": True,
                       "note": "set false to ask peers not to `batcave load` from here"},
    })
    W("cubbies/_template/front_door.md", _front_door_template())

    # ---- founding cubby: kody-w, seeded with the migrated operator agents
    kody = out / "cubbies" / OWNER
    for d in CUBBY_ANATOMY:
        (kody / d).mkdir(parents=True, exist_ok=True)
    # Generic template (public): a bones-only founder cubby — no agent files,
    # no work specifics. Real instance (private): seed the live agents + a
    # truthful cooking line.
    cooking = ("the batcave pattern + a workshop of agents — streamed in "
               "privately, never committed to the public grail repo")
    if seed_agents:
        cooking = ("operator agents kept out of the public grail repo: "
                   "twins, commons, scheduling, M365 — plus the batcave itself")
    kody_cubby_path = kody / "cubby.json"
    if not kody_cubby_path.exists():
        _write_json(kody_cubby_path, {
            "schema": "rapp-batcave-cubby/1.0",
            "github_login": OWNER,
            "rappid": PARENT_RAPPID,
            "display_name": "Kody Wildfeuer",
            "what_im_cooking": cooking,
            "created_at": minted_at,
            "estate": {"anatomy": list(CUBBY_ANATOMY)},
            "streamable": {"agents": True},
        })
        written.append(f"cubbies/{OWNER}/cubby.json")
    if not (kody / "front_door.md").exists():
        W(f"cubbies/{OWNER}/front_door.md",
          "# Kody — front door\n\nFounder cubby. When this is the private "
          "instance, the agents here are the operator set kept OUT of the "
          "public brainstem grail repo — they live in the batcave and stream "
          "in via `batcave load cubby=kody-w`.\n\n## What I'm cooking\n\n"
          "- twin tooling\n- the commons client\n- scheduling over WorkIQ\n"
          "- the batcave itself\n")
    # keep the founder cubby's agents/ a real (empty) dir in the template
    (kody / "agents" / ".gitkeep").write_text("")
    migrated = []
    if seed_agents:
        for name in KODY_CUBBY_AGENTS:
            src = REPO_ROOT / "rapp_brainstem" / "agents" / name
            if src.exists():
                shutil.copy2(src, kody / "agents" / name)
                migrated.append(name)
                written.append(f"cubbies/{OWNER}/agents/{name}")

    # ---- cubby roster index (regenerated from cubby.json files)
    cubbies = []
    for cj in sorted((out / "cubbies").glob("*/cubby.json")):
        if cj.parent.name == "_template":
            continue
        try:
            c = json.loads(cj.read_text())
            cubbies.append({"github_login": c.get("github_login", cj.parent.name),
                            "what_im_cooking": c.get("what_im_cooking", ""),
                            "rappid": c.get("rappid")})
        except (json.JSONDecodeError, OSError):
            continue
    WJ("cubbies/index.json", {
        "schema": "rapp-batcave-cubbies/1.0",
        "neighborhood_rappid": rappid,
        "updated_at": _now(),
        "cubbies": cubbies,
    })

    # ---- CODEOWNERS (root → operator; one line per cubby)
    co_lines = ["# The batcave's isolation property, GitHub-native.",
                "# Root + shared zones belong to the operator; each cubby to its owner.",
                f"* @{OWNER}"]
    for c in cubbies:
        co_lines.append(f"/cubbies/{c['github_login']}/ @{c['github_login']}")
    W(".github/CODEOWNERS", "\n".join(co_lines) + "\n")
    W(".github/workflows/cubby-guard.yml", _cubby_guard_yml())

    # ---- participation kit (sha256-pinned)
    # The agent's dev source lives in the default scaffold; when planting to a
    # fresh target, carry it along so the planted repo is self-contained.
    agent_file = out / "agents" / "batcave_agent.py"
    dev_agent = REPO_ROOT / "examples" / "rapp-batcave" / "agents" / "batcave_agent.py"
    if not agent_file.exists() and dev_agent.exists():
        agent_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dev_agent, agent_file)
        written.append("agents/batcave_agent.py")
    rar_agents = []
    if agent_file.exists():
        rar_agents.append({
            "name": "@kody-w/batcave",
            "version": "1.0.0",
            "class": "BatcaveAgent",
            "path": "agents/batcave_agent.py",
            "sha256": _sha256_file(agent_file),
            "purpose": ("Participate in the batcave: join/browse/stash/load/"
                        "show_and_tell/sync — the cubby contract."),
            "required_by_tether": True,
            "schema": "rapp-agent/1.0",
        })
    for c in cubbies:
        for ap in sorted((out / "cubbies" / c["github_login"] / "agents").glob("*_agent.py")):
            rar_agents.append({
                "name": f"@{c['github_login']}/{ap.stem.removesuffix('_agent')}",
                "version": "0.0.0-cubby",
                "path": f"cubbies/{c['github_login']}/agents/{ap.name}",
                "sha256": _sha256_file(ap),
                "purpose": f"Cubby agent from @{c['github_login']} — stream via `batcave load cubby={c['github_login']}`.",
                "required_by_tether": False,
                "schema": "rapp-agent/1.0",
            })
    WJ("rar/index.json", {
        "schema": "rapp-rar-index/1.1",
        "neighborhood_rappid": rappid,
        "rar_for": f"{OWNER}/{SLUG}",
        "kind": KIND,
        "updated_at": _now(),
        "raw_url_prefix": f"https://raw.githubusercontent.com/{OWNER}/{SLUG}/main",
        "note": ("Per-neighborhood registry. PRIVATE repo: raw URLs require "
                 "the fetcher's GitHub auth; the canonical access path is the "
                 "authenticated clone at ~/.brainstem/neighborhoods/"
                 "rapp-batcave/clone (batcave mount). sha256 pins let loaders "
                 "verify streamed files against this manifest."),
        "agents": rar_agents,
        "organs": [],
        "senses": [],
        "rapps": [],
        "verification": {
            "schema": "rapp-rar-manifest/1.0",
            "scheme": "sha256",
            "_instructions": ("Re-compute sha256(file) for anything you "
                              "stream and compare before installing."),
        },
    })

    return {"schema": "rapp-plant-batcave-result/1.0", "status": "success",
            "rappid": rappid, "out_dir": str(out), "files_written": len(written),
            "kody_cubby_agents_migrated": migrated}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=None,
                    help="target dir (default: examples/rapp-batcave/)")
    ap.add_argument("--seed-agents", action="store_true",
                    help=("copy the operator's live rapp_brainstem/agents/ "
                          "into kody-w's cubby (PRIVATE instance only — never "
                          "commit the result to the public grail repo)"))
    args = ap.parse_args(argv)
    res = plant(out_dir=args.out, seed_agents=args.seed_agents)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
