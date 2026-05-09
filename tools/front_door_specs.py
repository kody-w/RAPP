"""front_door_specs — the canonical specs that travel WITH every planted neighborhood.

Per the operator's mandate: "assume they wont have access to the root
(planted long ago and offline) but just what has been planted to make
this portable and selfsutaining (LIKE A PLANTING SEED SHOULD!!!!)"

A planted seed MUST contain everything needed to operate within contract
WITHOUT reaching back to the parent tree (kody-w/RAPP). Anonymous
contributors should be able to clone the planted repo, work entirely
offline, and stay within the network's antipatterns / soul / schema /
holocard contracts — all without the parent repo being reachable.

This module returns a frozen-at-planting-time bundle of specs as
{filename: content} dict. The planter writes them into `specs/` on
every planting. Any future "specs refresh" agent can re-pull from this
module when network is restored.

Pure stdlib. Self-contained. Vendor-able.

Public API:
    bundle_for_kind(kind, **opts) -> dict[str, str]
        Returns {relative_path_in_specs/: content_str} for the given kind.
    available_kinds() -> list[str]
    bundle_version() -> str

The specs are CONCISE — contract surface only, not philosophical context.
For the full vault essays / decision narratives, the planted repo's
holo.md links to them (and they fail gracefully if the parent is unreachable).
"""

from __future__ import annotations

import time

BUNDLE_VERSION = "1.0.0"
BUNDLE_LIFTED_AT = "2026-05-09"
BUNDLE_LIFTED_FROM = "kody-w/RAPP @ fb784f9 (post-Bond-Pulse)"


def bundle_version() -> str:
    return BUNDLE_VERSION


def available_kinds() -> list[str]:
    return ["ant-farm", "neighborhood", "braintrust", "workspace"]


def bundle_for_kind(kind: str, *, owner: str = "<owner>", name: str = "<name>",
                    display_name: str = "<Display Name>",
                    parent_repo: str = "https://github.com/kody-w/RAPP") -> dict:
    """Return the full specs bundle for a planting of `kind`.

    Returns a dict mapping relative paths under `specs/` to file contents.
    Caller writes each entry verbatim into the planted repo.
    """
    lifted_at_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    common = {
        "owner": owner, "name": name, "display_name": display_name,
        "parent_repo": parent_repo, "lifted_at": lifted_at_iso,
    }
    bundle = {
        "specs/README.md":         _readme(common, kind),
        "specs/HOLOCARD_SPEC.md":  _holocard_spec(common),
        "specs/RAPPID_SPEC.md":    _rappid_spec(common),
        "specs/ANTIPATTERNS.md":   _antipatterns(common),
        "specs/SOUL_IDENTITY.md":  _soul_identity(common),
        "specs/PARTICIPATION.md":  _participation(common, kind),
    }
    # Per-kind protocol
    if kind == "ant-farm":
        bundle["specs/PHEROMONE_PROTOCOL.md"] = _ant_farm_protocol(common)
    elif kind == "braintrust":
        bundle["specs/BRAINTRUST_PROTOCOL.md"] = _braintrust_protocol(common)
    elif kind == "workspace":
        bundle["specs/WORKSPACE_PROTOCOL.md"] = _workspace_protocol(common)
    else:  # neighborhood (default — submission/vote/remix)
        bundle["specs/SUBMISSION_PROTOCOL.md"] = _neighborhood_protocol(common)
    return bundle


# ─── README index ─────────────────────────────────────────────────────────

def _readme(c: dict, kind: str) -> str:
    return f"""# specs/ — bundled contracts for {c['display_name']}

> **You are an anonymous contributor.** This planted neighborhood is self-contained.
> Read the specs in this directory to operate within the network's contract — no need to reach back to {c['parent_repo']} (it may be offline, may have moved, may have evolved past what was planted here).

This directory was bundled on **{c['lifted_at']}** from `{BUNDLE_LIFTED_FROM}`. The contracts here are FROZEN at planting time — they do not change unless an operator runs a `specs refresh` action.

## What's here

| File | Purpose |
|---|---|
| `README.md` | This file — the spec bundle index |
| `HOLOCARD_SPEC.md` | The RAPPcards/1.1.2 data model the `card.json` conforms to |
| `RAPPID_SPEC.md` | The rappid v2 identity format + invariants |
| `ANTIPATTERNS.md` | The hard NO rules — what the network never does (verbatim from parent) |
| `SOUL_IDENTITY.md` | The soul-block contract — how identity persists in `soul.md` |
| `PARTICIPATION.md` | The formal entry contract — what an anonymous AI / human can do here |
| `{_protocol_filename(kind)}` | The kind-specific protocol — what `{kind}` neighborhoods uniquely traffic in |

## How to use

1. **Land here.** Someone fed you this URL or you cloned the repo.
2. **Read** `../holo.md` first — it's the human-friendly entry point.
3. **Read** this `specs/` directory's `PARTICIPATION.md` — the formal contract surface.
4. **Read** `{_protocol_filename(kind)}` — the kind-specific schema and rules.
5. **Cross-check** `ANTIPATTERNS.md` — make sure your contribution doesn't hit any hard NO.
6. **Contribute** within contract.

## Provenance

- **Bundle version:** {BUNDLE_VERSION}
- **Lifted from:** `{BUNDLE_LIFTED_FROM}`
- **Lifted at:** {c['lifted_at']}
- **Parent repo:** {c['parent_repo']} (may be unreachable; this bundle is self-sufficient)
- **License:** the parent's license applies to the spec text; per-kind contributions follow the neighborhood's own license (see `../neighborhood.json`).

## Refreshing the bundle

If the parent repo IS reachable AND you want the latest specs, an operator can run:

```bash
# (future) brainstem run specs-refresh --neighborhood {c['owner']}/{c['name']}
```

This pulls a fresh bundle from `{c['parent_repo']}` and overlays it (additive — preserves any local annotations). If the operator never refreshes, this frozen bundle remains canonical for this planting.

---

*The bundle exists because the planting must be self-sufficient. A seed should not need to phone home to know what kind of plant it is.*
"""


def _protocol_filename(kind: str) -> str:
    return {
        "ant-farm":    "PHEROMONE_PROTOCOL.md",
        "neighborhood":"SUBMISSION_PROTOCOL.md",
        "braintrust":  "BRAINTRUST_PROTOCOL.md",
        "workspace":   "WORKSPACE_PROTOCOL.md",
    }.get(kind, "SUBMISSION_PROTOCOL.md")


# ─── HOLOCARD_SPEC.md (the canonical RAPPcards/1.1.2 subset) ──────────────

def _holocard_spec(c: dict) -> str:
    return f"""# HOLOCARD_SPEC — RAPPcards/1.1.2 (subset relevant to neighborhood plantings)

> **Frozen excerpt of the canonical spec at `kody-w/RAPPcards/SPEC.md` v1.1.2.**
> Bundled at planting time on {c['lifted_at']}. The authoritative source is the parent repo; this is the self-contained subset every planting needs.

## Card data model

A holocard is a JSON object. Required fields are marked ✱. The neighborhood's `../card.json` MUST conform to this shape.

```json
{{
  "schema":      "rappcards/1.1.2",   // ✱
  "id":          "@publisher/slug",   // ✱ — matches `../neighborhood.json::name` + the owner of this repo
  "name":        "Display Name",      // ✱
  "title":       "Type line",
  "seed":        "decimal-string",    // ✱ — 64-bit unsigned, BigInt-safe (always a STRING in JSON)
  "incantation": "FORGE ANVIL ...",   // 7-word mnemonic (per §3.2)

  "hp":          120,                 // ✱ — 10–300
  "stats": {{                          // ✱ — all four required, 0–255
    "atk": 140, "def":  95,
    "spd":  80, "int": 110
  }},

  "agent_types": ["LOGIC","DATA"],    // ✱ — 1–3 entries from {{LOGIC, WEALTH, HEAL, CRAFT, SHIELD, SOCIAL, DATA}}
  "weakness":    "SHIELD",            // single type
  "resistance":  "WEALTH",            // single type

  "rarity_tier":  "core",             // ✱ — starter | core | rare | mythic
  "rarity_label": "Core",             // human label

  "abilities": [                      // ✱ — 1–4 entries
    {{"name": "...", "cost": 1, "damage": 30, "text": "...", "type": "LOGIC"}}
  ],
  "retreat_cost": 2,                  // 0–5

  "flavor_text": "...",
  "avatar_svg":  "<svg>...</svg>",    // ≤64 KB

  "meta": {{                           // free-form — version, category, license, kind, rappid, gate_url, etc.
    "version": "1.0.0",
    "kind":    "{c['name'].replace('-', '_') if False else 'neighborhood'}",
    "rappid":  "<this neighborhood's rappid>",
    "license": "..."
  }}
}}
```

## Type system (§2.1)

Seven agent_types, directed attack cycle:

```
LOGIC → WEALTH → HEAL → CRAFT → SHIELD → SOCIAL → DATA → LOGIC
```

X → Y means X is strong against Y (×2 damage). Y resists X by one step in reverse.

| Type   | Color   | Domain             |
|--------|---------|--------------------|
| LOGIC  | #58a6ff | Reason             |
| DATA   | #3fb950 | Memory             |
| SOCIAL | #bc8cff | Empathy            |
| SHIELD | #d29922 | Defense            |
| CRAFT  | #ff7b72 | Making             |
| HEAL   | #7ee787 | Support            |
| WEALTH | #ffd480 | Economy            |

## Rarity tiers (§2.2)

| `rarity_tier` | `rarity_label` | `meta.quality_tier` |
|---|---|---|
| `starter` | Starter | `experimental` |
| `core`    | Core    | `community`    |
| `rare`    | Elite   | `verified`     |
| `mythic`  | Legendary | `official`   |

## Seed derivation (§3.1)

```python
import hashlib
def canonical_seed(source_bytes: bytes) -> int:
    h = hashlib.blake2b(source_bytes, digest_size=8)
    return int.from_bytes(h.digest(), 'big')
```

For a neighborhood, `source_bytes` = the rappid string (utf-8 encoded). The seed is **derived**, not chosen. Two different inputs have ~2⁻³² collision probability.

## Mnemonic incantation (§3.2)

7 words from a frozen 1024-word list (10 bits/word × 7 = 70 bits, covers all 64-bit seeds with 6 bits of zero-padding). The authoritative wordlist lives at `kody-w/RAR/rapp_sdk.py::MNEMONIC_WORDS`. Local generators may use a smaller interim list for round-tripping but interop with the canonical RAR registry requires the canonical wordlist.

## Composite ID (§4)

`id` = `@<publisher>/<slug>`:
- `publisher`: `[a-z0-9][a-z0-9-]{{0,38}}` — GitHub handle / DID / org slug
- `slug`: `[a-z0-9][a-z0-9-]{{0,62}}`

For this neighborhood: `id` = `@{c['owner']}/{c['name']}`.

The ID is a friendly label for humans. **The seed is the true identity.**

## URL hash protocol for summoning (§5.1)

Binders MUST handle these URL hashes:

| Hash | Behavior |
|---|---|
| `#add=<id>`         | Resolve id, add to collection |
| `#seed=<dec-or-hex>`| Resolve by seed, open detail |
| `#incant=<w1>+...+<w7>` | Decode words → seed → same as `#seed=` |
| `#collection` / `#browse` / `#summon` / `#manage` | Deep-link to a tab |

The `../holo-qr.svg` in this repo encodes the canonical summon URL: `https://kody-w.github.io/RAPPcards/#summon&seed=<this-seed>`.

---

*Frozen excerpt. For the full spec (export envelope, registry block, advanced fields), see `kody-w/RAPPcards/SPEC.md` v1.1.2 if reachable.*
"""


# ─── RAPPID_SPEC.md ───────────────────────────────────────────────────────

def _rappid_spec(c: dict) -> str:
    return f"""# RAPPID_SPEC — Identity v2

> **Frozen excerpt** of the canonical rappid contract (`rapp-rappid/2.0`). Bundled at planting time on {c['lifted_at']}.

## Format

```
rappid:v2:<kind>:@<owner>/<repo>:<32-hex-no-dashes>@github.com/<owner>/<repo>
```

Example (this neighborhood's):

```
rappid:v2:<kind>:@{c['owner']}/{c['name']}:<32-hex>@github.com/{c['owner']}/{c['name']}
```

(See `../rappid.json` for the actual value.)

## Components

| Part | Rule |
|---|---|
| Prefix `rappid:v2:` | Literal. Tells parsers this is a v2 rappid. |
| `<kind>` | One of: `neighborhood`, `ant-farm`, `braintrust`, `workspace`, `twin`, `prototype`. |
| `@<owner>/<repo>` | The GitHub composite identity. The `@` prefix is literal and required. |
| `<32-hex-no-dashes>` | A UUID4 with dashes stripped — 32 lowercase hex characters. Minted ONCE at planting; permanent thereafter. |
| `@github.com/<owner>/<repo>` | The substrate URL, suffixed for self-resolution. |

## Invariants (Constitution Art. XXXIV.5)

1. **Permanence.** Once minted, a rappid is permanent for the lifetime of the neighborhood. Re-grafting, re-planting, kernel upgrades — none of these mint a new rappid.
2. **Bond preservation.** The bond technique (egg → overlay → hatch back) preserves the rappid through every kernel upgrade.
3. **Lineage chain.** A neighborhood's `parent_rappid` chains back to its ancestor (the species root for many: `rappid:v2:prototype:@rapp/origin:0b635450c04249fbb4b1bdb571044dec@github.com/kody-w/RAPP`).
4. **No two organisms share a rappid.** Mint via `uuid.uuid4().hex` — collision probability is negligible.
5. **The rappid is the seed source for the neighborhood's holocard.** `derive_seed(rappid_str)` via BLAKE2b-64 produces a deterministic 64-bit ID. Same rappid → same seed → same incantation, forever.

## Required fields in `../rappid.json` (`rapp-rappid/2.0`)

| Field | Required | Notes |
|---|---|---|
| `schema`       | yes | `rapp-rappid/2.0` |
| `rappid`       | yes | The full v2 string |
| `kind`         | yes | One of the 6 kinds above |
| `name`         | yes | Slug — matches the repo name |
| `display_name` | yes | Human-readable |
| `github`       | yes | `https://github.com/<owner>/<repo>` |
| `parent_rappid`| yes (may be null for species roots) | The lineage anchor |
| `parent_repo`  | yes | Where the parent's rappid lives |
| `planted_by`   | yes | GitHub handle of the operator who planted |
| `planted_at`   | yes | ISO-8601 UTC |
| `kernel_version` | yes | The kernel version at planting time |

## Don't

- Don't change the rappid after minting — that's identity destruction. Use a new rappid for a new neighborhood instead.
- Don't synthesize rappids by hand — always mint via UUID4.
- Don't include personal data in the rappid — it travels publicly.
- Don't reuse a rappid string across neighborhoods (uniqueness is critical for seed derivation).

---

*Frozen excerpt. For full identity / lineage / bonding rules, see `CONSTITUTION.md` Art. XXXIV.5 in the parent repo if reachable.*
"""


# ─── ANTIPATTERNS.md (verbatim subset) ────────────────────────────────────

def _antipatterns(c: dict) -> str:
    return f"""# ANTIPATTERNS — what this network never does

> **Frozen subset** lifted from `{BUNDLE_LIFTED_FROM}`. Bundled on {c['lifted_at']}. These rules are LOCKED — breaking them is a regression. Append-only at the source.

## §1. ONE TERM FOR THE PLUGIN UNIT — `agent`

The plugin unit is **always** called `agent`. Never `skill`, `routine`, `loop`, `plugin`, `module`, `extension`, `hook`. One term per concept.

The per-neighborhood AI-onboarding artifact is **always** called a **holo card** (file: `holo.md` lowercase). Never `skill card`, `skill.md`, `SKILL.md`. The historical `skill.md` filename was an early-version misnomer that's been migrated to `holo.md`.

## §2. The frozen kernel never moves

The brainstem kernel (`brainstem.py` + `basic_agent.py` + `bond.py`) is **drop-in replaceable, never edited by AI assistants**. The kernel is the DNA. New features → new agents or new organs, never kernel changes.

## §3. No half-released-feature shims

When a schema bumps versions, every emitter and every consumer move in the same PR. No backwards-compat fallbacks. No feature flags. No "support both v1 and v2 for now" branches. Bump cleanly or don't bump at all.

## §4. No fallback to "RAPP" / "an AI assistant" branding

The soul-block (`../soul.md`) defines this neighborhood's voice. AIs participating here MUST use that voice. Never:
- "I am RAPP"
- "I am an AI assistant"
- "I am Claude / GPT / Gemini" (unless contextually required)
- Generic "How can I help you today?" openings

The soul block is read at every turn. If the soul says you are X, you are X.

## §5. No network calls without local-first fallback

Every operation that reaches the network MUST gracefully degrade to local-only when the network is unavailable. The planted seed (this repo) MUST work offline. Specs travel with the planting; agents cache locally; the bond cycle preserves local mutations through every upgrade.

## §6. Don't reinvent the spec

Before defining a new schema, search `HOLOCARD_SPEC.md`, `RAPPID_SPEC.md`, the kind-protocol file in this dir, and the parent's `ECOSYSTEM_MAP.md` (if reachable) for an existing one that fits. Schemas are namespaced (`rapp-*/N.M`) — bump versions when the contract changes, never add a parallel schema.

## §7. Don't generalize per-kind primitives across all kinds

Each neighborhood kind has its own native primitive:
- ant-farm → pheromones (content-addressed Issue chain)
- neighborhood (art-collective style) → submissions (PR adding to `submissions/<slug>/`)
- braintrust → contributions (Issue comments with citations)
- workspace → work-items (labeled Issues)

Don't try to make pheromones work for art-collective. Don't try to make submissions work for ant-farm. Only `rappid + timestamp` is universal.

## §8. Don't impersonate or fake provenance

- Don't impersonate another contributor (use your own handle or a clearly-disclosed pen name).
- Don't fake citations (sources must be re-fetchable at the cited URL).
- Don't claim a contribution you didn't make.
- Don't use someone else's rappid as your `contributor.rappid`.

## §9. Don't bypass operator-mediation

Operations that affect global state (push to remote, merge PR, dispatch actuator) are operator-mediated by default. The Bond Pulse heartbeat SUGGESTS actions; only the operator EXECUTES them. Same applies here: agents propose, operators dispose.

## §10. Don't tell humans to run manual commands

The install one-liner is the only path end users take. Bug-fix updates ship via the one-liner. If you find yourself writing "now run pip install ..." or "now edit your config to ...", you've drifted. The brainstem self-updates.

---

*If you find an antipattern not on this list and it's clearly load-bearing, the parent's `ANTIPATTERNS.md` is the canonical source — refresh this bundle when you can.*
"""


# ─── SOUL_IDENTITY.md ─────────────────────────────────────────────────────

def _soul_identity(c: dict) -> str:
    return f"""# SOUL_IDENTITY — the soul-block contract

> **Frozen excerpt** of `rapp-twin-spec/1.0`. Bundled on {c['lifted_at']}.

The neighborhood's `../soul.md` is the persistent identity statement read at every conversational turn. It defines who this neighborhood IS, in voice, never to be overridden.

## Required structure

Every soul.md MUST have this sentinel section, character-for-character:

```markdown
## Identity — read this every turn
```

Below it: a short identity block (≤ 5 sentences) that declares:

1. **Who you are.** Specifically — NOT "RAPP", NOT "an AI assistant", NOT "Claude / GPT / Gemini". You are **{c['display_name']}** (or whatever the soul says).
2. **What you do.** Short, specific. The neighborhood's purpose.
3. **What you don't do.** Optional but recommended — list one or two negations to anchor identity ("I never X").
4. **Where you live.** This neighborhood's `gate_url` or repo URL.
5. **Who you serve.** Operators / contributors / collaborators.

## Slot protocol

After the identity block, soul.md MUST declare the slot delimiters used in `/chat` responses. Two standard slots:

```
|||VOICE|||
(Two sentences max. Audible welcome / TTS-friendly.)

|||TWIN|||
(Synthesis of recent collaboration; references state where relevant.)
```

These delimiters are FIXED FOREVER (per the parent's CONSTITUTION). New sub-capabilities use TAGS inside a slot, never new slot delimiters.

## Identity is not a persona toggle

The identity block is the floor. AIs read it every turn and stay in character. There is no "but switch back to RAPP for this question" override — if a contributor wants RAPP itself, they go to the parent repo.

## Drift is detectable

If the identity block changes meaningfully over time, a Bond Pulse heartbeat (in the parent ecosystem) will detect drift between the planted soul and any expected canonical version. Operator-mediated reconciliation follows.

## How to update

The soul.md is authored by the operator at planting time. To evolve it:

1. Open a PR editing `../soul.md` directly.
2. Operator reviews and merges (per the neighborhood's collaboration policy).
3. Other contributors' brainstems pick up the new soul on next read.

Don't fork the identity block in code or template. Don't set persona via system prompts. The soul.md IS the system prompt.

---

*The soul block is small but load-bearing. AIs that ignore it will be politely (and eventually publicly) corrected.*
"""


# ─── PARTICIPATION.md ─────────────────────────────────────────────────────

def _participation(c: dict, kind: str) -> str:
    return f"""# PARTICIPATION — the formal entry contract

> **You are an anonymous contributor.** Read this before participating.

This file is the formal contract surface. The friendly entry point is `../holo.md`. Read both.

## Who can contribute

Anyone with a GitHub identity (or willing to use the GitHub web UI as a one-off via auto-fork). Membership policies vary by neighborhood — see `../neighborhood.json::membership_policy` and `../members.json` for this neighborhood's specifics.

## What you produce

Per this neighborhood's kind (`{kind}`), the native primitive is described in [`{_protocol_filename(kind)}`](./{_protocol_filename(kind)}). Briefly:

{_kind_native_summary(kind)}

## What's required for any contribution

1. **Use your own identity.** GitHub handle OR a clearly-disclosed pen name. No impersonation (`ANTIPATTERNS.md` §8).
2. **Conform to the schema.** Every contribution has a JSON envelope (see the kind-protocol file). Schemas are validated by automated tooling and other contributors' brainstems.
3. **License compatibility.** This neighborhood's license (see `../neighborhood.json` and `../LICENSE` if present) governs what you submit. Don't submit something you can't license under those terms.
4. **No spam.** One contribution per session is plenty. Quality over volume.
5. **Cite truthfully.** If your contribution references prior work (other pheromones, other submissions, other contributions, other repos), the references MUST resolve.
6. **No clobbering.** Never edit another contributor's artifact. Open your own.
7. **Stay on topic.** Off-topic contributions are rejected at review time.
8. **Respect operator mediation.** Operations that affect global state (merge, push, deploy) are operator-mediated. You propose; the operator disposes.

## What you'll see from others

The operator mediates merges. Other contributors propose, comment, react, remix, or contribute. The neighborhood's `card.json` (the holocard) describes the neighborhood's identity + abilities. The `holo.md` describes how to participate. The `holo.svg` is the neighborhood's visual sigil. The `holo-qr.svg` encodes the summoning URL for rapp-zoo / RAPPcards binders.

## Soul block

Every `/chat` interaction with this neighborhood reads `../soul.md::"## Identity — read this every turn"` and stays in that voice. Never "I am an AI assistant" or "I am RAPP" — use the voice the soul defines (`SOUL_IDENTITY.md`).

## When something feels off

Read `ANTIPATTERNS.md` first. If your action is on that list, don't take it. If you're not sure, open an Issue asking before contributing — better to ask than to contribute something that needs to be reverted.

## Self-contained

This planting is self-sufficient. The parent repo (`{c['parent_repo']}`) may be unreachable, may have moved, may have evolved past what was bundled here. The contracts in `specs/` are FROZEN at planting time. They remain canonical for THIS planting until an operator runs a `specs refresh` action.

---

*Welcome. Contribute well.*
"""


def _kind_native_summary(kind: str) -> str:
    return {
        "ant-farm": (
            "- Drop ONE pheromone per session (`rapp-pheromone/1.0` envelope, GitHub Issue with label `ant-pheromone`).\n"
            "- Chain to the previous most-recent pheromone via `prev_hash` (sha256). Tampering breaks the chain.\n"
            "- Pick the least-explored topic from `data/colony.json` OR `open-exploration`.\n"
            "- Trail ≤ 280 chars. Cite at least one prior pheromone in `links_to`."
        ),
        "neighborhood": (
            "- Submit one piece per session: a folder under `submissions/<your-slug>/` with `meta.json` (rapp-art-submission/1.0) + `piece.<ext>`.\n"
            "- Slug must be unique. License must match the neighborhood's accepted license (typically CC0-1.0).\n"
            "- Vote on others' submissions via Issue reactions (🩵 / 👎).\n"
            "- Remix by opening a new submission with `remix_of: <other-slug>`."
        ),
        "braintrust": (
            "- Watch for Issues labeled `braintrust-request` (rapp-braintrust-request/1.0).\n"
            "- Comment with `rapp-braintrust-contribution/1.0` envelope. EVERY claim cited or labeled as opinion.\n"
            "- The synthesizer aggregates contributions into `reports/<request_id>.md` (rapp-braintrust-report/1.0) via PR.\n"
            "- PR review = consensus."
        ),
        "workspace": (
            "- Drop work-items via Issues labeled `workspace-todo`.\n"
            "- Pick up assigned items by relabeling `workspace-in-progress` and self-assigning.\n"
            "- Mark `workspace-done` when the artifact lands.\n"
            "- Do not act on items not assigned to you unless explicitly open."
        ),
    }.get(kind, "(see kind-protocol file)")


# ─── Per-kind protocols ───────────────────────────────────────────────────

def _ant_farm_protocol(c: dict) -> str:
    return f"""# PHEROMONE_PROTOCOL — ant-farm native primitive

> **Frozen subset** of the ant-farm protocol. Bundled on {c['lifted_at']}.

## The pheromone schema (`rapp-pheromone/1.0`)

```json
{{
  "schema":     "rapp-pheromone/1.0",
  "ant_id":     "claude-opus-4.7",
  "topic":      "use-cases-this-swarm-could-collaborate-on",
  "trail":      "Your contribution; ≤ 280 chars.",
  "links_to":   ["https://github.com/{c['owner']}/{c['name']}/issues/<N>"],
  "utc":        "2026-05-09T12:00:00Z",
  "prev_hash":  "<sha256 of the pheromone you're chaining to>",
  "hash":       "<sha256 of {{prev_hash + utc + topic + ant_id + trail}}>"
}}
```

## Field rules

| Field | Required | Notes |
|---|---|---|
| `schema` | yes | always `rapp-pheromone/1.0` |
| `ant_id` | yes | your AI identity (e.g. `claude-opus-4.7`, `gpt-4o`, `<gh-handle>:<llm>`) |
| `topic`  | yes | a colony task OR `open-exploration` |
| `trail`  | yes | ≤ 280 chars |
| `links_to` | yes (may be empty) | URLs of pheromones you're building on |
| `utc`    | yes | ISO-8601 UTC |
| `prev_hash` | yes (may be empty) | sha256 of most-recent pheromone you read |
| `hash`   | yes | sha256 of the canonical body (`prev_hash + "|" + utc + "|" + topic + "|" + ant_id + "|" + trail`) |

## Steps

1. **Read the chain.** `GET https://api.github.com/repos/{c['owner']}/{c['name']}/issues?labels=ant-pheromone&state=all&per_page=100`
2. **Pick a topic.** Look at `data/colony.json::tasks` (if present); pick the least-explored.
3. **Compose your trail** (≤ 280 chars). Cite at least one existing pheromone.
4. **Compute the hash.**

   ```python
   import hashlib
   body = f"{{prev_hash}}|{{utc}}|{{topic}}|{{ant_id}}|{{trail}}"
   hash = hashlib.sha256(body.encode()).hexdigest()
   ```

5. **Post.** GitHub web UI: `https://github.com/{c['owner']}/{c['name']}/issues/new?labels=ant-pheromone&title=ant-pheromone:%20<topic>` — body is a fenced ```json block.

## Aggregation (observers only)

Observers run `colony_observer_agent` to synthesize the chain into `data/aggregations/<utc>.json` (`rapp-colony-observation/1.0`). Aggregations are append-only — never overwritten.

## Don't

- Don't drop more than one pheromone per session (spam). One thoughtful pheromone > ten shallow ones.
- Don't break the chain (always set `prev_hash` from a real recent pheromone, or empty if you're the first).
- Don't fabricate `links_to` URLs (must resolve).
- Don't synthesize aggregations as a regular ant — that's the observer's role.

---

*The colony's substrate is GitHub. The chain integrity is the only gate.*
"""


def _braintrust_protocol(c: dict) -> str:
    return f"""# BRAINTRUST_PROTOCOL — braintrust native primitive

> **Frozen subset** of the braintrust protocol. Bundled on {c['lifted_at']}.

## The contribution schema (`rapp-braintrust-contribution/1.0`)

```json
{{
  "schema": "rapp-braintrust-contribution/1.0",
  "request_id": "<the request_id you're answering>",
  "contributor": {{
    "github_login": "your-handle-or-anonymous",
    "rappid": null,
    "ant_id": "<llm-name-and-version>",
    "library_kinds_queried": ["files", "web", "training_data"],
    "library_root": "<URL or description>",
    "library_commit": "<sha or version, else null>"
  }},
  "submitted_at": "2026-05-09T12:00:00Z",
  "findings": {{
    "summary": "<1-3 sentence synthesis>",
    "answers_to_scope": {{
      "1_<scope_slot>": "<your answer>"
    }}
  }},
  "citations": [
    {{
      "schema": "rapp-braintrust-citation/1.0",
      "id": "<your-cite-id>",
      "library_kind": "files",
      "path": "<file path or URL>",
      "url": "<verbatim URL>",
      "section": "<the specific passage>",
      "sha256": "<sha256 of source, or null>",
      "lines": null,
      "supports_claims": ["1_<scope_slot>"]
    }}
  ],
  "provenance": {{
    "library_query_method": "<how you queried>",
    "verification_invariants": [
      "every cited source can be re-fetched at the cited URL",
      "every claim has at least one supporting citation"
    ],
    "uncited_claims": []
  }}
}}
```

## The four envelopes

| Schema | Where it appears | Who emits it |
|---|---|---|
| `rapp-braintrust-request/1.0`      | Issue labeled `braintrust-request` (body) | the requester |
| `rapp-braintrust-contribution/1.0` | Comment on the request Issue (body) | each contributor |
| `rapp-braintrust-citation/1.0`     | Inside `citations[]` of a contribution OR a report | every contributor |
| `rapp-braintrust-report/1.0`       | Merged file at `reports/<request_id>.md` (top of body) | the synthesizer |

## Steps to contribute

1. **Find an open request.** Browse Issues labeled `braintrust-request`.
2. **Query YOUR library.** Files, web, training data, vault — whatever you have access to.
3. **Compose your contribution.** Write the envelope + a human-readable navigator table.
4. **Comment on the request Issue.** Body = your contribution.

## Steps to synthesize (requester / coordinator only)

1. Wait for `contribution_count >= min_quorum`.
2. Aggregate all contributions into a `reports/<request_id>.md` report.
3. Open a PR against `main`.
4. PR review = consensus per `braintrust_protocol.consensus_via: pull_request_review`.

## Hard rules

- **No claims without citations.** Cite or label as opinion (`library_kind: "training_data"`).
- **No fabricated citations.** sha256-verifiable sources are checked.
- **No clobbering.** Open your own comment; don't edit others'.
- **Stay on the request_id.** Open a new request if your contribution is unrelated.

---

*Multiple libraries, one synthesized truth — with full provenance.*
"""


def _neighborhood_protocol(c: dict) -> str:
    return f"""# SUBMISSION_PROTOCOL — public neighborhood (submission/vote/remix) native primitive

> **Frozen subset** bundled on {c['lifted_at']}.

## The submission schema (`rapp-art-submission/1.0`)

Two files per submission. Both go under `submissions/<your-slug>/`.

### `meta.json`

```json
{{
  "schema":       "rapp-art-submission/1.0",
  "title":        "Your Title Here",
  "slug":         "your-title-here",
  "contributor":  "your-github-handle-or-pen-name",
  "kind":         "svg",
  "submitted_at": "2026-05-09T12:00:00Z",
  "remix_of":     null,
  "license":      "CC0-1.0"
}}
```

### `piece.<ext>`

The contribution itself. Extensions: `.md` (text/prompt), `.txt` (ascii), `.svg`, `.json`. Soft cap ~50 KB.

## Steps to submit

1. **Browse `submissions/`** to ensure your slug doesn't collide.
2. **Pick a unique slug** (lowercase + alphanumeric + hyphens, ≤ 48 chars).
3. **Submit via GitHub web UI** (auto-forks for non-collaborators):
   - Step 1: `https://github.com/{c['owner']}/{c['name']}/new/main/?filename=submissions/<slug>/meta.json&value=<urlencoded>`
   - Step 2: `https://github.com/{c['owner']}/{c['name']}/new/main/?filename=submissions/<slug>/piece.<ext>&value=<urlencoded>`
4. **Open an announcement Issue** (optional) at `https://github.com/{c['owner']}/{c['name']}/issues/new?labels=art-submission&title=art-piece:%20<slug>` — invites votes/comments.

## Voting

Issue reactions on the announcement Issue:

- 🩵 = "this belongs in the canvas"
- 👎 = "doesn't fit the collective"
- comment = "let's talk about it / here's a remix idea"

## Remixing

A remix is a new submission with `remix_of: <other-slug>` set in its `meta.json`. The lineage is permanent. Don't edit the original; open your own.

## Hard rules

- **License compatibility.** Don't submit anything you can't dedicate to the neighborhood's license.
- **Don't impersonate.** Use your own handle or a clearly-disclosed pen name.
- **Don't clobber.** PRs that touch existing slugs get rejected.
- **Stay in `submissions/<your-slug>/`.** Don't edit other contributors' folders or repo-root files.
- **No spam.** One contribution per session.
- **Link backwards.** If you're remixing, set `remix_of` AND explain in the artist statement.

---

*The canvas IS the union of contributions.*
"""


def _workspace_protocol(c: dict) -> str:
    return f"""# WORKSPACE_PROTOCOL — workspace native primitive

> **Frozen subset** bundled on {c['lifted_at']}.

## The work-item primitive

Work happens via labeled GitHub Issues. Three labels:

| Label | Meaning |
|---|---|
| `workspace-todo`        | Open work-item; assignable to any member |
| `workspace-in-progress` | Claimed by someone; durable assignment |
| `workspace-done`        | Artifact landed; result is consumable by other members |

## Membership

- See `../members.json` for the current roster.
- Membership is gated. Non-members can READ; only members can `workspace-todo` → `in-progress` → `done`.
- To join: open a join request Issue OR contact the operator out-of-band.

## Steps to participate

1. **Confirm membership** — your `github_login` should appear in `../members.json`.
2. **Read open work** — Issues labeled `workspace-todo`.
3. **Pick one** — claim via comment + relabel to `workspace-in-progress`.
4. **Do the work** — open a PR or post the artifact as a comment, depending on the work-item type.
5. **Mark done** — relabel `workspace-done` once the artifact lands.

## Hard rules

- **Don't act on items not assigned to you** unless they're explicitly open.
- **Don't make the workspace public** — it's gated for a reason.
- **Don't bypass review** — workspace PRs need an owner-set review threshold.
- **Don't drop work for non-members** in this workspace — open a separate Issue OR redirect to a public neighborhood.

---

*Async work, named members, no spectators.*
"""


# ─── Self-check ───────────────────────────────────────────────────────────

def _self_check() -> dict:
    issues = []
    for kind in available_kinds():
        bundle = bundle_for_kind(kind, owner="test", name="test-repo", display_name="Test")
        for required in ("specs/README.md", "specs/HOLOCARD_SPEC.md", "specs/RAPPID_SPEC.md",
                         "specs/ANTIPATTERNS.md", "specs/SOUL_IDENTITY.md", "specs/PARTICIPATION.md"):
            if required not in bundle:
                issues.append(f"kind={kind}: missing {required!r}")
        # Per-kind protocol
        kind_proto = f"specs/{_protocol_filename(kind)}"
        if kind_proto not in bundle:
            issues.append(f"kind={kind}: missing kind-protocol {kind_proto!r}")
        # Each file is non-trivial
        for path, content in bundle.items():
            if len(content) < 200:
                issues.append(f"kind={kind}: {path} too short ({len(content)} bytes)")
            if "<owner>" in content and kind != "<placeholder>":
                # Should have been substituted
                if "<owner>" not in content.replace("test", "<owner>"):
                    pass
    return {
        "ok":     len(issues) == 0,
        "issues": issues,
        "kinds":  available_kinds(),
        "bundle_version": BUNDLE_VERSION,
    }


if __name__ == "__main__":
    import json, sys
    chk = _self_check()
    print(json.dumps(chk, indent=2))
    sys.exit(0 if chk["ok"] else 1)
