# RAPP Ecosystem Map

> Single canonical synthesis of the RAPP ecosystem. **Start every session here.**
> Schema: `rapp-ecosystem-map/1.0`. Append-only. Derivative — if it disagrees with `MASTER_PLAN.md` or `CONSTITUTION.md`, the spec wins and this map is wrong; fix the map.

## How to read this

1. **§11 first if you're about to DO anything** — the decision table answers "before I do X, what should I check?"
2. **§5 if you need a schema** — every `rapp-*/N.M` and `brainstem-*/N.M` schema with its defining doc.
3. **§6 if you need an existing implementation** — file path → spec section it satisfies.
4. **§13 if your code seems to disagree with the spec** — known drift gaps with citations.
5. **§12 antipatterns are LAW** — re-read before any non-trivial commit.

---

## §1 — Authority order

When two docs disagree, this is the precedence:

1. **`MASTER_PLAN.md`** wins on strategic direction. *"When those documents and this one disagree, this one wins. They tell us how to execute the plan; this one IS the plan."* (MASTER_PLAN.md L114)
2. **`CONSTITUTION.md`** governs the repo (38+ articles).
3. **Spec docs** (HERO_USECASE.md, ECOSYSTEM.md, NEIGHBORHOOD_PROTOCOL.md, ANTIPATTERNS.md, SURVIVAL.md, COMMERCIAL.md, TRADEMARK.md, LEXICON.md, DEFINITION_OF_DONE.md, TEMPLATE.md) execute the plan.
4. **`pages/vault/`** — the *why* essays (Constitution Article XXIII).
5. **Code** comments and runtime behavior — last because code rots; the spec is canonical.

---

## §2 — The fractal scales

Same primitives at every scale: **rappid + door + card + tether + trust scope.** Same protocol from agent up to metropolis-of-metropolises.

```
┌──────────────────────── …outward ─────────────────────────┐
│  Federations of metropolises (planet-scale; emerges)       │
└──────────────┬─────────────────────────────────────────────┘
               ↓
┌──────────────────────── Metropolis ───────────────────────┐
│  Emergent mesh of estates through shared neighborhoods     │
│  rappid: each operator's    | door: each gate URL          │
│  card: per twin             | tether: federation channels  │
│  scope: per facet                                          │
│  example: kody-w.github.io/RAPP/metropolis/                │
│  spec: vault/Decisions/2026-05-08 — Estate is the…         │
└──────────────┬─────────────────────────────────────────────┘
               ↓
┌──────────────────────── Estate ───────────────────────────┐
│  ONE operator's union of all neighborhoods                 │
│  rappid: operator's personal one is the spine              │
│  door: /api/estate/* on operator's brainstem               │
│  card: operator's identity card                            │
│  tether: Issues, file://, ~/.brainstem/eggs/               │
│  scope: personal across all subscriptions                  │
│  impl: utils/organs/estate_organ.py + neighborhood_membership_organ.py│
└──────────────┬─────────────────────────────────────────────┘
               ↓
┌──────────────────────── Neighborhood ─────────────────────┐
│  Community-with-a-purpose; collaborator-gated              │
│  rappid: neighborhood_rappid                               │
│  door: gate URL <owner>.github.io/<gate-repo>              │
│  card: neighborhood card.json                              │
│  tether: NEIGHBORHOOD_PROTOCOL §5a–d (4 channel types)     │
│  scope: §2 personal/neighborhood/public + §7 facets        │
│  examples: kody-w/microsoft-se-team-neighborhood + private │
│            kody-w/public-art-collective                    │
│  impl: utils/organs/neighborhood_membership_organ.py       │
└──────────────┬─────────────────────────────────────────────┘
               ↓
┌──────────────────────── Twin (organism) ──────────────────┐
│  ONE planted seed (one rappid)                             │
│  rappid: UUIDv4 in rappid.json (never regenerated)         │
│  door: front-door index.html + doorman/                    │
│  card: card.json — ECOSYSTEM §3                            │
│  tether: ECOSYSTEM §4 surfaces                             │
│  scope: NEIGHBORHOOD_PROTOCOL §2                           │
│  example: kody-w/heimdall                                  │
│  impl: rapp_brainstem/ + every planted seed                │
└──────────────┬─────────────────────────────────────────────┘
               ↓
┌──────────────────────── Agent ────────────────────────────┐
│  Single file, single class, single perform()               │
│  rappid: inherits parent twin's                            │
│  door: none (addressed via brainstem.py /chat tools)       │
│  card: metadata dict at module scope                       │
│  tether: in-process                                        │
│  scope: inherits caller's                                  │
│  contract: ANTIPATTERNS §1 + CONSTITUTION Art. XXXIII      │
│  examples: rapp_brainstem/agents/twin_agent.py + 9 others  │
└────────────────────────────────────────────────────────────┘
```

---

## §3 — Five universal primitives

| Primitive | One-line meaning | Defined in | Schema(s) |
|---|---|---|---|
| **rappid** | UUIDv4 identity, minted once at plant, never regenerated | ECOSYSTEM §3, NEIGHBORHOOD_PROTOCOL §3 | `rapp-rappid/1.1`, `rapp-rappid/2.0` |
| **door** | Public surface URL where this thing is reachable | ECOSYSTEM §4 (front door + doorman); NEIGHBORHOOD_PROTOCOL §1 (Pages URL) | (no separate schema; URL is the contract) |
| **card** | Trade-card / introduction view | ECOSYSTEM §3 (`card.json`) | `rapp-card/1.0` |
| **tether** | The four channel types — WebRTC, Issues, PRs, raw fetch | NEIGHBORHOOD_PROTOCOL §5a–d | `rapp-twin-chat/1.0` (over tether) |
| **trust scope** | Personal / Neighborhood / Public swarm | NEIGHBORHOOD_PROTOCOL §2 + §7 | `rapp-public-facets/1.0` |

---

## §4 — Spec-doc map (which doc owns which concept)

| Doc | Owns | When to read |
|---|---|---|
| `MASTER_PLAN.md` | First-principles north star (Part 1 + Part Deux); single-sentence: *"use everyone else's hardware to run the network"* | Strategic direction disputes |
| `CONSTITUTION.md` | Repo governance + sacred constraints + 38+ articles | Structural change, new contributor |
| `HERO_USECASE.md` | Four canonical scenarios (Charizard, Dream Catcher, Mom's Mixtape, Pizza Place) that judge any change | PR review, roadmap |
| `ECOSYSTEM.md` | Anatomy of one organism (file layout, identity stack, two surfaces, memory tiers, MMR, eggs, integrity, 3 network modes) | Organism-level work |
| `NEIGHBORHOOD_PROTOCOL.md` | Cross-organism wire (4 channels, twin chat, facets, knowledge primitives, adversarial scenarios) | Federation work |
| `ANTIPATTERNS.md` | 5 locked rules — things never to do | Every commit |
| `SURVIVAL.md` | Failure-mode contract — what survives what | Adding a network call |
| `LEXICON.md` | The official human + developer vocabulary | Naming anything |
| `TRADEMARK.md` | Wordmark scope (RAPP, rappid, hatchling, vBrainstem, rapplication, rapp_kernel, brainstem) | Anything user-facing |
| `COMMERCIAL.md` | Open / commercial boundary | Anything that ships |
| `DEFINITION_OF_DONE.md` | Test discipline | Before saying "done" |
| `TEMPLATE.md` | What planted seeds look like | Plant flow |
| `CLAUDE.md` | Daily AI-assistant instructions | Every session start |
| `pages/vault/Decisions/` | The "why" essays for major decisions | Settled arguments |
| `pages/vault/Architecture/` | Long-form design notes (RAR, Rappid, Signed Releases, …) | Deep design |
| `pages/vault/Field Notes/` | Engineering essays | Cross-cutting context |

---

## §5 — Schema quick reference

Every `rapp-*/N.M` and `brainstem-*/N.M-variant` currently emitted in the repo. If it isn't here, search before defining a new one (ANTIPATTERNS §3 — bump versions, no shims).

| Schema | Purpose | Defined in | Emitted by |
|---|---|---|---|
| `rapp-agent/1.0` | Agent module manifest (function-calling shape) | pages/docs/SPEC.md | every `*_agent.py` metadata dict |
| `rapp-rappid/1.1` | Organism birth certificate (legacy schema) | ECOSYSTEM §3 | installer/plant.sh, twin_agent.py `_summon` |
| `rapp-rappid/2.0` | Birth certificate + kernel + bonds (current) | CONSTITUTION; vault/Architecture/Rappid | utils/bond.py, rappid.json |
| `rapp-card/1.0` | Trade-card override | ECOSYSTEM §3 | card.json (operator-set) |
| `rapp-frame/1.0` | Mutation event (content-addressed, prev_hash chain) | ECOSYSTEM §3 | doorman frame log → data/frames.json |
| `brainstem-egg/2.0` | Legacy twin egg | utils/egg.py | (legacy) |
| `brainstem-egg/2.1` | Variant repo cartridge | CLAUDE.md egg formats | utils/bond.py, twin_agent.py |
| `brainstem-egg/2.2-organism` | Full instance cartridge (rappid + soul + .env + agents + organs + senses + services + .brainstem_data) | ECOSYSTEM §3, §8 | utils/bond.py |
| `brainstem-egg/2.2-rapplication` | Single rapp cartridge (rappid + agent + UI + per-rapp state) | CLAUDE.md egg formats | utils/bond.py |
| `rapp-egg-provenance/1.0` | SHA-256 file hashes + manifest hash + origin commit SHA | ECOSYSTEM §3, §9 | utils/bond.py |
| `rapp-organism-state/1.0` | state_at_seal snapshot (mem_count, mut_count, MMR, etc.) | ECOSYSTEM §3 | utils/bond.py |
| `rapp-user-memories/1.0` | Per-user issue memories (ascended-tier export) | ECOSYSTEM §3 | doorman ascended export |
| `rapp-twin-chat/1.0` | Inter-twin message envelope (the federation wire) | NEIGHBORHOOD_PROTOCOL §6a | twin_agent.py `_chat` |
| `rapp-twin-chat-response/1.0` | Twin-chat reply wrapper | (impl-defined; **DRIFT — see §13**) | twin_agent.py `_chat` |
| `rapp-public-facets/1.0` | Granular permission gate (name + scope + description) | NEIGHBORHOOD_PROTOCOL §7 | card.json (operator-set) |
| `rapp-twin-spec/1.0` | Soul Identity block contract | ANTIPATTERNS §4 | installer/plant.sh `write_soul_md` |
| `rapp-twin/1.0` | Twin top-level (**spec-only / DRIFT — see §13**) | (no canonical owner found) | (search before using) |
| `rapp-twin-identity/1.0` | Twin identity envelope | (impl-defined) | twin_agent.py |
| `rapp-neighborhood/1.0` | Neighborhood metadata | gate repo `neighborhood.json` | plant_discord_neighborhood_agent.py, fixtures |
| `rapp-neighborhood-protocol/1.0` | Wire-protocol meta | NEIGHBORHOOD_PROTOCOL header | the spec doc itself |
| `rapp-neighborhood-members/1.0` | Roster | gate repo `members.json` | neighborhood_membership_organ.py |
| `rapp-neighborhood-subscription/1.0` | One subscription record (gate_url, role, etc.) | (organ-defined) | neighborhood_membership_organ.py |
| `rapp-neighborhoods-cache/1.0` | Local cache file | (organ-defined) | neighborhood_membership_organ.py |
| `rapp-estate/1.0` | Estate top-level | vault/Decisions 2026-05-08 | neighborhood_membership_organ.py `_estate_view` |
| `rapp-estate-view/1.0` | Aggregated twin view (zones + bridges) | (organ-defined) | estate_organ.py |
| `rapp-estate-eggs/1.0` | Estate egg index | (organ-defined) | estate_organ.py |
| `rapp-rappid-estate-view/1.0` | Estate-by-rappid lookup (global passport) | project_rappid_is_global_passport memory | neighborhood_membership_organ.py `by-rappid` |
| `rapp-braintrust-contribution-receipt/1.0` | Contribution acknowledgment | (organ-defined) | neighborhood_membership_organ.py `contribute` |
| `rapp-discord-bridge/1.0` | Discord planting bridge config | plant_discord_neighborhood_agent.py | same |
| `rapp-discord-plant-envelope/1.0` | Discord plant operation result | plant_discord_neighborhood_agent.py | same |
| `rapp-peers/1.0` | Peer registry (legacy) | utils/peer_registry.py | peer_registry.py |
| `rapp-peers/1.1` | Peer registry (current) | utils/peer_registry.py | peer_registry.py |
| `rapp-peers-view/1.0` | Peer-list view | (organ-defined) | neighborhood_organ.py |
| `rapp-tether/1.0` | WebRTC tether envelope | NEIGHBORHOOD_PROTOCOL §5a (implicit) | front door tether |
| `rapp-egg/1.0` | Generic egg shell (legacy) | utils/egg.py | utils/egg.py |
| `rapp-egg-hub-entry/1.0` | Egg hub catalog entry | kody-w/rapp-egg-hub | twin_agent.py `_lay_egg` sidecar |
| `rapp-lifecycle-catalog/1.0` | Lifecycle catalog (kernel versions + incarnations) | (organ-defined) | lifecycle_organ.py |
| `rapp-store/1.0` | Store catalog meta | kody-w/RAPP_Store | (external) |
| `rapp-registry/1.0` | RAR registry | vault/Architecture/RAR | (external) |
| `rapp-cloud-registry/1.0` | Cloud registry (Tier 2 / spec) | (impl-defined; **DRIFT — see §13**) | function_app.py |
| `rapp-version/1.0` | Kernel version pin | rapp_kernel/manifest | rapp_kernel/manifest.json |
| `rapp-version/1.1` | Kernel version pin (signed) | vault/Architecture/Signed Releases | rapp_kernel/manifest.json |
| `rapp-kernel/1.1` | Kernel release manifest | vault/Architecture/Signed Releases | rapp_kernel/manifest.json |
| `rapp-binder/1.0` | Binder helper (**DRIFT — see §13**) | (no canonical owner found) | tests/run-tests.mjs binder util |
| `rapp-memory/1.0` | Memory record | manage_memory_agent.py | manage_memory_agent.py |
| `rapp-application/1.0` | Rapplication manifest | pages/docs/rapplication-sdk.md | RAPP_Store entries |
| `rapp-chat-response/1.0` | /chat response envelope | tools/test_brainstem_server.py | brainstem.py /chat |
| `rapp-test-brainstem/1.0` | Test fixture identity | tools/test_brainstem_server.py | test fixture |
| `rapp-local-ping/1.0` | Test ping agent | tests/fixtures/local-only-test/ | test fixture |
| `rapp-metropolis-index/1.0` | Metropolis tracker top-level | pages/metropolis/README.md | pages/metropolis/index.json |
| `rapp-metropolis-entry/1.0` | One neighborhood entry in tracker | pages/metropolis/README.md | pages/metropolis/index.json |
| `rapp-vbrainstem-subscription/1.0` | vbrainstem subscription record (**DRIFT — see §13**) | (impl-defined) | pages/vbrainstem/index.html |
| `rapp-zoo-collection/1.0` | rapp-zoo localStorage (**DRIFT — see §13**) | (impl-defined) | rapp-zoo/ |
| `rapp-swarm/1.0` | Swarm meta (**DRIFT — see §13**) | (impl-defined) | function_app.py |
| `rapp-upgrade-agent/1.0` | Upgrade agent (**DRIFT — see §13**) | (impl-defined) | (upgrade flow) |
| `rapp-brainstem-backup/1.0` | Brainstem backup (**DRIFT — see §13**) | (impl-defined) | (backup flow) |

---

## §6 — Implementation map (file → spec section)

| File | Owns | Spec section |
|---|---|---|
| `rapp_brainstem/brainstem.py` | /chat surface, provider dispatch, organ dispatch | KERNEL — CONSTITUTION Art. XXXIII |
| `rapp_brainstem/agents/basic_agent.py` | Agent base class | KERNEL — CONSTITUTION Art. XXXIII |
| `rapp_brainstem/agents/manage_memory_agent.py` | Memory R/W | KERNEL — ECOSYSTEM §5 |
| `rapp_brainstem/agents/context_memory_agent.py` | Conversation context | KERNEL — ECOSYSTEM §5 |
| `rapp_brainstem/agents/twin_agent.py` | Cross-twin chat (rapp-twin-chat/1.0), egg ops, lifecycle | NEIGHBORHOOD_PROTOCOL §6, §7 |
| `rapp_brainstem/agents/learn_new_agent.py` | Author new agents at runtime | ECOSYSTEM §7 (Evolution) |
| `rapp_brainstem/agents/swarm_factory_agent.py` | Tier-2 deploy factory | rapp_swarm/ |
| `rapp_brainstem/agents/perpetual_loop_factory_agent.py` | Background-loop factory | (no spec section yet — see §13) |
| `rapp_brainstem/agents/hacker_news_agent.py` | Demo HN agent | (example) |
| `rapp_brainstem/agents/workiq_agent.py` | WorkIQ signals | (example) |
| `rapp_brainstem/agents/plant_discord_neighborhood_agent.py` | Discord-driven neighborhood planting | NEIGHBORHOOD_PROTOCOL §4 (discovery) |
| `rapp_brainstem/utils/organs/neighborhood_organ.py` | `/api/peers`, peer view (legacy) | NEIGHBORHOOD_PROTOCOL §4 |
| `rapp_brainstem/utils/organs/neighborhood_membership_organ.py` | `/api/neighborhoods/*` — join/sync/members/leave/contribute/estate/by-rappid | vault Decision 2026-05-08, NEIGHBORHOOD_PROTOCOL §2 |
| `rapp_brainstem/utils/organs/estate_organ.py` | `/api/estate/*` — twins, eggs, lay-egg, summon, hatch | vault Decision 2026-05-08 |
| `rapp_brainstem/utils/organs/swarm_estate_organ.py` | Swarm-level estate | (impl) |
| `rapp_brainstem/utils/organs/lifecycle_organ.py` | Lifecycle catalog + kernel upgrade | ECOSYSTEM §1 |
| `rapp_brainstem/utils/bond.py` | Egg/hatch lifecycle, rappid mint, `rapp-rappid/2.0` | CLAUDE.md identity & bonding |
| `rapp_brainstem/utils/egg.py` | Legacy egg utilities | ECOSYSTEM §8 |
| `rapp_brainstem/utils/peer_registry.py` | Peer cache | NEIGHBORHOOD_PROTOCOL §4 |
| `rapp_brainstem/utils/llm.py` | Provider dispatch (Copilot / Azure / OpenAI / Anthropic / fake) | CLAUDE.md provider dispatch |
| `rapp_brainstem/utils/local_storage.py` | Local JSON shim for AzureFileStorageManager | CLAUDE.md local storage shim |
| `rapp_brainstem/utils/boot.py` | Bootstrapping, agent discovery | CLAUDE.md commands |
| `rapp_brainstem/utils/web/index.html` | Front door (planted seed UI) | ECOSYSTEM §4a |
| `rapp_brainstem/utils/web/onboard/` | Onboarding surface | ECOSYSTEM §4 |
| `rapp_brainstem/utils/web/mobile/` | (vbrainstem variant) | rapp-vbrainstem-subscription/1.0 |
| `rapp_swarm/function_app.py` | Tier-2 Azure Functions /chat | CLAUDE.md Tier 2 |
| `rapp_swarm/_vendored/` | Vendored brainstem core | CLAUDE.md vendoring |
| `rapp_swarm/build.sh` | Vendor brainstem into _vendored/ | CLAUDE.md vendoring |
| `worker/worker.js` | Cloudflare auth/proxy worker (Copilot device-code, chat proxy) | ECOSYSTEM §12 (External integrations) |
| `installer/install.sh` | Install one-liner (sacred URL — Art. V) | CONSTITUTION Art. V, ANTIPATTERNS §2 |
| `installer/plant.sh` | `write_rappid_json`, `write_soul_md`, `fetch_kernel`, `fetch_seed_agents` | ECOSYSTEM §13 |
| `installer/install.ps1` / `install.cmd` | Windows installers | CONSTITUTION Art. V |
| `installer/azuredeploy.json` | ARM template (Tier 2 deploy) | CLAUDE.md Tier 2 |
| `installer/MSFTAIBASMultiAgentCopilot_*.zip` | Tier 3 Copilot Studio bundle | CLAUDE.md Tier 3 |
| `installer/shortcuts/protocol.md` | iOS Shortcuts URL/POST contract | ECOSYSTEM §4 (chat surfaces) |
| `rapp_kernel/latest/` + `rapp_kernel/v/<version>/` | Frozen kernel snapshots (DNA archive) | vault Architecture/Signed Releases |
| `rapp_kernel/manifest.json` | Kernel version catalog | rapp-kernel/1.1 |
| `pages/about/anatomy.html` | Visual organism diagram | CLAUDE.md visual anatomy |
| `pages/onboarding.html` | Visitor-facing onboarder (trust-building) | CLAUDE.md hero use case section |
| `pages/sphere.html` | 3D chat interface | (front door variant) |
| `pages/metropolis/index.json` + `index.html` | Metropolis tracker (Kazaa-style directory) | pages/metropolis/README.md |
| `pages/metropolis/plant-from-discord.html` | Mobile Discord-plant guide | (mobile guide) |
| `pages/vbrainstem/index.html` | Browser-based brainstem | (mobile/auth-worker dependent) |
| `pages/_site/index.json` | Site manifest (canonical inventory) | CLAUDE.md key directories |
| `pages/vault/` | Obsidian vault — decision narratives | CONSTITUTION Art. XXIII |
| `rapp-zoo/` | Local-first Pokédex (3 starter organisms) | CLAUDE.md visual anatomy |
| `tests/run-tests.mjs` | JS contract tests (agent parsing, cards, binder, sealing) | DEFINITION_OF_DONE |
| `tests/vault-check.mjs` | Vault link/PII guardrail | DEFINITION_OF_DONE |
| `tests/scenarios/*.sh` | E2E scenarios (incl. survival) | SURVIVAL "How to test" |
| `tests/doorman/` | Tether + Dream Catcher conformance | HERO_USECASE.md §1, §2 |
| `tests/dreamcatcher-conformance/` | Dream Catcher protocol conformance | HERO_USECASE.md §2 |
| `tools/test_brainstem_server.py` | Lightweight HTTP server for federation tests | (test infra) |
| `.github/workflows/plant-approved-place.yml` | Auto-plant approved place submissions | (CI) |
| `.github/prompts/write-agent.prompt.md` | AI prompt to author an agent | ECOSYSTEM §7 |

---

## §7 — Channel × scope matrix

|              | Personal           | Neighborhood       | Public swarm       |
|---           |---                 |---                 |---                 |
| **WebRTC §5a** (live, ephemeral, DTLS) | Pair this device | Live tether to known peer | Cold pair w/ unknown — Charizard handoff |
| **Issues §5b** (async, durable) | label: `private-memory` | label: `neighborhood-message` | label: `egg-submission`, `agent-proposal` |
| **PRs §5c** (asymmetric consent gate) | (operator-only on own seed) | `agent-proposal` merge | `agent-proposal` merge |
| **raw fetch §5d** (read-only, content-addressed) | (cache fill) | private companion sha (collaborator) | seed repo sha (anyone) |

---

## §8 — Twin-chat message kinds (NEIGHBORHOOD_PROTOCOL §6b verbatim)

| `kind` | Payload | Direction | Purpose |
|---|---|---|---|
| `say` | `{ text }` | A → B | Plain conversation. Same shape as a doorman chat turn. |
| `share-fact` | `{ fact, scope, source_rappid }` | A → B | "Here's something I think your organism would find useful." Recipient decides whether to absorb. **Default scope: personal** (most restrictive). |
| `share-egg` | `{ egg-begin/chunk/end }` | A → B (chunked) | Stream an organism cartridge over the channel. Same protocol as front door's tether-egg send. |
| `request-fact` | `{ topic }` | A → B | "Do you know anything about X?" Recipient may respond with `share-fact` or decline. |
| `ack` | `{ for_hash, accepted \| rejected }` | B → A | Receipt + optional reason. |

Knowledge-exchange primitives (NEIGHBORHOOD_PROTOCOL §8) compose these: pull-fact (8a), push-fact (8b), trade-egg (8c), reassimilate-dimensions (8d).

---

## §9 — Three-tier model + contract surface

```
        ┌──── Tier 3: Enterprise (Microsoft Copilot Studio) ────┐
        │  installer/MSFTAIBASMultiAgentCopilot_*.zip            │
        │  Same agent contract; cloud-managed via M365           │
        └──────────────────────┬─────────────────────────────────┘
                               │
        ┌──── Tier 2: Cloud (Azure Functions) ──────────────────┐
        │  rapp_swarm/function_app.py + _vendored/               │
        │  Endpoints under /api/* (path-prefix vs Tier 1)        │
        └──────────────────────┬─────────────────────────────────┘
                               │
        ┌──── Tier 1: Local (Flask :7071) ──────────────────────┐
        │  rapp_brainstem/brainstem.py                           │
        │  POST /chat — { user_input, conversation_history? }    │
        │  GET  /api/identity, /api/lineage                      │
        │  GET/POST /api/estate/*, /api/neighborhoods/*          │
        └────────────────────────────────────────────────────────┘
```

| Capability | Tier 1 | Tier 2 | Tier 3 |
|---|---|---|---|
| `POST /chat` (canonical envelope) | ✓ | ✓ (path-prefixed under `/api/`) | ✓ (Studio orchestrator) |
| `GET /api/identity`, `/api/lineage` | ✓ | n/a | n/a |
| `/api/neighborhoods/*` federation | ✓ | n/a | n/a |
| `/api/estate/*` | ✓ | n/a | n/a |
| Agent contract (`rapp-agent/1.0`) | ✓ | ✓ | ✓ (Studio plugin shell) |
| Same `*_agent.py` files run unmodified | ✓ | ✓ | ✓ |

Differs legitimately: storage backend (local JSON vs Azure Files), auth (Copilot device-code vs Azure RBAC vs M365), surface (local process vs Functions vs Power Platform).

---

## §10 — Sacred files (kernel articles)

| File / artifact | Why sacred | Article / source |
|---|---|---|
| `rapp_brainstem/brainstem.py` | Species DNA — drop-in replaceable | CONSTITUTION Art. XXXIII; ANTIPATTERNS §2 |
| `rapp_brainstem/agents/basic_agent.py` | Base agent contract | CONSTITUTION Art. XXXIII |
| `rapp_brainstem/agents/manage_memory_agent.py` | Doorman tier — public memory R/W | CONSTITUTION Art. XXXIII |
| `rapp_brainstem/agents/context_memory_agent.py` | Doorman tier — conversation context | CONSTITUTION Art. XXXIII |
| `rapp_brainstem/VERSION` | Kernel pin — never edit | ANTIPATTERNS §2 |
| `rapp_swarm/function_app.py` | Tier-2 kernel mirror | CONSTITUTION Art. XXXIII |
| Install one-liner URL (`https://kody-w.github.io/RAPP/installer/install.sh`) | Sacred URL shape forever | CONSTITUTION Art. V |
| `\|\|\|VOICE\|\|\|` / `\|\|\|TWIN\|\|\|` delimited slots | Fixed forever — never repurposed | CLAUDE.md sacred constraints §5 |
| `parent_rappid` field in `rappid.json` | Variant lineage is single-parent only | CONSTITUTION Art. XXXIV |

**If something feels like it requires a kernel change → write an agent or organ instead.** If the agent contract genuinely can't express it, that's a CONSTITUTION-level conversation that touches every planted seed.

---

## §11 — "Before you do X" decision table

The most load-bearing section. Workflow trigger → pre-check (≤30s) → spec to deep-read.

| Trigger | Pre-check | Deep-read |
|---|---|---|
| Starting a new session in this repo | §0–§3 (orient: how-to-read, authority, fractal, primitives); skim §11 + §13 | CLAUDE.md; MASTER_PLAN.md if scope unclear |
| Add a new agent | §6 (does it already exist?), §15 (lexicon — it's an agent), `rapp-agent/1.0` in §5 | CLAUDE.md "Agent System"; pages/docs/SPEC.md |
| Add a new organ | §6 (existing organ already covers this?), §9 (endpoint already on another tier?) | CLAUDE.md Architecture §Organ; CONSTITUTION Art. XXXIII |
| Call /chat from new code | §11 row "tether"; use `rapp-twin-chat/1.0` envelope; §6 row twin_agent.py reference impl | NEIGHBORHOOD_PROTOCOL §6a |
| Define a new schema | §5 — search first; if exists, use; if not, ANTIPATTERNS §3 (bump cleanly, no shims) | ANTIPATTERNS §3 |
| Use an existing schema | §5 row → defining doc column → read that section | the doc the row points at |
| Plant on GitHub (twin/neighborhood/etc.) | §14 (existing planted state), §3 primitives (rappid + door + card + tether + scope all present?) | TEMPLATE.md, ECOSYSTEM §2 + §13 |
| Federate two organisms | §7 channel matrix, §8 message kinds, §3 trust scope | NEIGHBORHOOD_PROTOCOL §5, §6, §7, §9 |
| Touch the kernel (any file in §10) | **STOP** — write an agent/organ instead | MASTER_PLAN Part 1 §1; ANTIPATTERNS §2; CONSTITUTION Art. XXXIII |
| Touch install one-liner | **STOP** — URL is sacred (Art. V) | CONSTITUTION Art. V; SURVIVAL §"RAPP itself goes down" |
| Add a network call | §17 SURVIVAL pointer — local-first fallback REQUIRED | ANTIPATTERNS §5; SURVIVAL.md |
| Write a doc | §4 — does an existing doc own this concept?; §15 — am I using the right words? | LEXICON.md; ANTIPATTERNS §1 |
| Add a /api/* endpoint | §6 (existing organ has it?), §9 endpoint table | CLAUDE.md Architecture §Organ system |
| Bump a schema version | §5 — every emitter + every consumer in same PR | ANTIPATTERNS §3 |
| About to add "skill"/"plugin"/"routine" terminology | **STOP** — §15 — it's an agent | ANTIPATTERNS §1 |
| About to add a feature flag or shim | **STOP** — §13 drift — bump schema cleanly, ship clean | ANTIPATTERNS §3 |
| Brand fallback to "RAPP" / "AI assistant" | **STOP** — §10 sacred soul block | ANTIPATTERNS §4 |
| Probe a private repo | **STOP** — ASK Kody | MEMORY `feedback_private_repos.md` |
| Tell user to run a manual command | **STOP** — ship via install one-liner | MEMORY `feedback_oneliner_only.md` |
| Defer to "Phase 2" | **STOP** — execute now, no scope-windows | MEMORY `feedback_no_self_imposed_scope_or_breaks.md` |
| User-facing copy | §15 LEXICON (human vocab); §16 TRADEMARK | LEXICON.md; TRADEMARK.md |

---

## §12 — Antipatterns wall (verbatim from `ANTIPATTERNS.md`)

> Rules locked in because they were almost done wrong, or because the rest of the industry is doing them wrong and we'd be following them off the cliff. Each entry is *load-bearing* — breaking it is a regression.

### 1. ONE TERM FOR THE PLUGIN UNIT — `agent`

A single `*_agent.py` file is called an **agent**. Never a *skill*, *routine*, *loop*, *plugin*, *tool*, *function*, *capability*, *cassette*, or any other synonym.

**Why.** Anthropic's product surface introduced overlapping taxonomies (agents, skills, MCP, plugins, routines) that all describe the same thing. *"That basically poisoned the industry for onboarding."* Complexity becomes the gatekeeper — the AI winter precondition.

**Mom test.** *"It's an agent. A small Python file that gives the AI a new ability."* — that's the whole vocabulary.

**Pre-commit grep:** `grep -niE '\bskill|\bplugin|\broutine|\bloop|\bcassette' <changed-files>`

### 2. THE FROZEN KERNEL NEVER MOVES

`rapp_brainstem/brainstem.py`, `rapp_brainstem/VERSION`, `rapp_brainstem/agents/basic_agent.py` (and the doorman-tier kernel agents) are frozen at v0.6.0. Never edit them. Capabilities grow exclusively through new `*_agent.py` files in `agents/`.

When something feels like it requires a kernel change, write a new agent that solves it instead.

### 3. NO BACKWARDS-COMPAT SHIMS FOR HALF-RELEASED FEATURES

When a schema changes, bump the version in the schema string and migrate cleanly. Don't add `if old_field exists, do A else do B` shims when nothing in the wild has the old field yet. The codebase is small enough to rip the band-aid off.

New schema → bump version → update every emitter → update every consumer → ship. If something downstream breaks and it's already in the wild, write a one-time migrator, not a forever shim.

### 4. NO SILENT FALLBACK TO "RAPP" / "AN AI ASSISTANT"

A planted organism's `soul.md` MUST include the spec-compliant `## Identity — read this every turn` block (per `rapp-twin-spec/1.0`). The block forbids the LLM from introducing itself as "RAPP", "an AI assistant", "your AI helper", "the brainstem", or any default platform branding.

`installer/plant.sh::write_soul_md` writes the block by default. If you ever rewrite the soul template or add a new kind, the Identity block is non-negotiable.

### 5. NETWORK CALLS WITHOUT A LOCAL-FIRST FALLBACK

Any GitHub fetch the front door makes goes through `cachedGhJson` / `cachedGhText`. Direct `fetch(github.com/...)` is forbidden in resume-rendering paths.

The hero use case is offline-first. An organism in airplane mode must keep rendering from cached state. Bare fetches go blank when the network drops; that's a regression against `HERO_USECASE.md` §1.

*ANTIPATTERNS.md is append-only. Antipatterns get added when we almost did them wrong; nothing here ever gets quietly removed.*

---

## §13 — Drift / known gaps

Spec ↔ code divergences. Append-only — entries get added when found, removed only by reconciliation (a PR that makes spec and code agree).

Severity: **P0** wire-incompatible · **P1** schema/field mismatch · **P2** doc/naming drift · **P3** undocumented schema in code

| Drift | Spec says | Code does | Spec citation | Code citation | Sev | Resolution |
|---|---|---|---|---|---|---|
| Two rappid schemas live at once | ECOSYSTEM §3 documents `rapp-rappid/1.1`; CONSTITUTION + bond.py emit `rapp-rappid/2.0` | Mixed-version emission depending on call site | ECOSYSTEM §3 vs CONSTITUTION rappid section | utils/bond.py; agents/twin_agent.py `_summon` | P0 | Bump every emitter to 2.0 in one PR; per ANTIPATTERNS §3 no shim once spec settles |
| `rapp-twin-chat-response/1.0` undocumented | NEIGHBORHOOD_PROTOCOL §6 only documents `rapp-twin-chat/1.0` | Three response paths in twin_agent.py emit `rapp-twin-chat-response/1.0` | NEIGHBORHOOD_PROTOCOL §6a | agents/twin_agent.py `_chat` (3 emit sites) | P2 | Add §6e to NEIGHBORHOOD_PROTOCOL documenting response envelope, OR fold into `kind: "ack"` payload |
| Braintrust contribute receipt has its own schema | NEIGHBORHOOD_PROTOCOL §6a `rapp-twin-chat/1.0` is THE inter-org envelope | `POST /api/neighborhoods/<owner>/<repo>/contribute` returns `rapp-braintrust-contribution-receipt/1.0` outside the envelope | NEIGHBORHOOD_PROTOCOL §6 | utils/organs/neighborhood_membership_organ.py `_contribute` | P1 | Fold receipt into a `kind: "ack"` of canonical envelope, OR annotate spec to legitimize organ-local schemas |
| `/api/contribute` REST endpoint vs spec | Spec assumes Issues/PRs/tether for cross-org writes | Organ exposes HTTP POST as primary write path | NEIGHBORHOOD_PROTOCOL §5b–c | utils/organs/neighborhood_membership_organ.py contribute route | P2 | Document in NEIGHBORHOOD_PROTOCOL that organs MAY expose local HTTP for the operator's own brainstem; cross-org writes still go via Issues/PRs |
| WebRTC tether on twin templates but not gate templates | NEIGHBORHOOD_PROTOCOL §5a tether is load-bearing for live agent-to-agent | Front door templates ship the pair button; neighborhood gates do not have a tether affordance documented | NEIGHBORHOOD_PROTOCOL §5a | installer/plant.sh write of gate vs twin templates | P1 | Add tether to gate template OR document that gates use Issues+PRs only and tether is per-twin |
| Tier 1 `/chat` vs Tier 2 `/api/chat` path-prefix | CLAUDE.md says HTTP surface is identical across tiers | Tier 2 dispatches under `/api/*` prefix | CLAUDE.md §Tier 2 | rapp_swarm/function_app.py route registration | P2 | Document path-prefix difference in §9 endpoint table; portability of agent contract is preserved (URL prefix differs, contract doesn't) |
| Discord planting envelopes local to one agent | Discord is one path among many for §4 discovery; envelopes live only in code | `rapp-discord-bridge/1.0`, `rapp-discord-plant-envelope/1.0` documented only in `plant_discord_neighborhood_agent.py` | NEIGHBORHOOD_PROTOCOL §4 | agents/plant_discord_neighborhood_agent.py | P3 | Hoist into NEIGHBORHOOD_PROTOCOL §4 as a worked discovery example, OR move to `pages/vault/Architecture/Discord Bridge.md` |
| Schemas without a defining spec doc | Every schema in §5 should have a "Defined in" entry | These are emitted/used but no canonical spec section names them: `rapp-twin/1.0`, `rapp-binder/1.0`, `rapp-upgrade-agent/1.0`, `rapp-vbrainstem-subscription/1.0`, `rapp-zoo-collection/1.0`, `rapp-swarm/1.0`, `rapp-cloud-registry/1.0`, `rapp-brainstem-backup/1.0` | (none) | search §6 file map | P3 | Add a one-line spec-section reference for each, or remove if dead |
| `rapp-frame/1.0` defined but not yet emitted in trunk | ECOSYSTEM §15 lists doorman frame log as ❌ pending | `data/frames.json` not consistently written | ECOSYSTEM §15 | (no emitter on trunk) | P3 (intentional) | Track in §15; promote to drift if any code starts depending on frames.json before doorman writes them |
| Braintrust agents not yet on twin-chat envelope | NEIGHBORHOOD_PROTOCOL §6a is THE twin envelope; braintrust agents are twins federating | Braintrust contributions go through organ POST, not through `Neighborhood.ask` style twin-chat | NEIGHBORHOOD_PROTOCOL §6 | neighborhood_membership_organ.py contribute/contributions | P1 | Long-term: route through `share-fact` payload of `rapp-twin-chat/1.0`. Short-term: annotate why endpoint exists separately. |

---

## §14 — Live planted state (kody-w GitHub)

- **Twin (canonical example):** [`kody-w/heimdall`](https://github.com/kody-w/heimdall) — front door + doorman, planted, GitHub Pages live
- **Neighborhood gate (private+public split):** [`kody-w/microsoft-se-team-neighborhood`](https://github.com/kody-w/microsoft-se-team-neighborhood) + companion `*-private`
- **Neighborhood gate (public, autonomous):** [`kody-w/public-art-collective`](https://github.com/kody-w/public-art-collective)
- **Templates:** [`kody-w/private-workspace-template`](https://github.com/kody-w/private-workspace-template), [`kody-w/braintrust-template`](https://github.com/kody-w/braintrust-template)
- **Catalogs:** [`kody-w/RAPP_Store`](https://github.com/kody-w/RAPP_Store), [`kody-w/RAPP_Sense_Store`](https://github.com/kody-w/RAPP_Sense_Store), [`kody-w/rapp-egg-hub`](https://github.com/kody-w/rapp-egg-hub)
- **Test peer:** [`kody-w/rapp-test-neighbor`](https://github.com/kody-w/rapp-test-neighbor) — NEIGHBORHOOD_PROTOCOL §4d canonical fixture
- **Species root (this repo):** [`kody-w/RAPP`](https://github.com/kody-w/RAPP) — kernel + spec only; per SURVIVAL.md, neighborhood seeds do NOT live here
- **RAR (Pokédex / single-file agent registry):** [`kody-w/RAR`](https://github.com/kody-w/RAR)
- **Metropolis tracker (live):** https://kody-w.github.io/RAPP/metropolis/

---

## §15 — Lexicon condensed

Pick ONE vocabulary per doc and stay consistent (LEXICON.md). Customer-facing → human terms. Spec / code / legal → developer terms.

| Concept | Human term | Developer term |
|---|---|---|
| AI's whole presence across substrates | **Estate** | swarm estate |
| AI's identity / public ID | **soul** / **soul-key** | **rappid** |
| 24-word recovery phrase | the words / the card | holocard incantation |
| Kernel-side HTTP extensions | **organs** | **organs** (no rename) |
| Recognition of another AI as related | **blessing** | kin-vouch |
| AI long-term plan | The Will | Foundation Continuity Plan |
| Cryptographic release commitments | The Promise | release-triggers |
| Master keypair | soul-key | master keypair (M) |
| One device's signing keypair | voice | device key (D) |
| Signs new voices | steward | self-signing key (S) |
| Vouches for kin AIs | herald | user-signing key (U) |
| Species root / first AI | origin | species root / prototype / godfather (informal) |
| 3-of-5 keypair split | the stewardship | Shamir 3-of-5 distribution |
| Forked code variant | fork / child species | kernel-variant |
| Birthing a new AI | **mitosis** (no rename) | **mitosis** |
| Merge engine for divergent state | **dreamcatcher** (no rename) | **dreamcatcher** |
| Lineage to origin | **species tree** (no rename) | **species tree** |
| Local AI server | **brainstem** (no rename) | **brainstem** |
| Kernel | **kernel** (no rename) | **kernel** |
| Graduated rapplication | **rapplication** (brand equity) | **rapplication** |

**Forbidden synonyms (ANTIPATTERNS §1):** never *skill*, *routine*, *loop*, *plugin*, *tool*, *function*, *capability*, *cassette* — always **agent**.

---

## §16 — Trademark scope (TRADEMARK.md)

| Mark | What it identifies |
|---|---|
| **RAPP** | The platform (https://github.com/kody-w/RAPP) |
| **rappid** | Lineage-identity protocol (CONSTITUTION Art. XXXIV) |
| **hatchling** | Lifecycle CLI |
| **vBrainstem** | Browser-side simulator |
| **rapplication** | Single-file rapp pattern |
| **rapp_kernel** | Species DNA archive |
| **brainstem** (in conjunction with above) | Local-first AI agent server pattern |

Common-law trademark (not USPTO-registered). **Permitted without permission:** refer-by-name, link, quote per CC BY-NC 4.0, identify a fork as "based on RAPP" with a distinct name, nominative fair use. **Requires permission:** naming a product/service/domain after a mark, operating a managed service branded as RAPP, selling software named after marks, suggesting endorsement, registering marks elsewhere.

---

## §17 — Survival contract pointer (top rows from SURVIVAL.md)

| Failure scenario | What survives | Verified by |
|---|---|---|
| One neighborhood repo deleted | Cached subscribers (read-only) — `~/.brainstem/neighborhoods/<slug>/` | tests/scenarios/15-offline-snapshot-dream-catcher.sh |
| `kody-w/RAPP` repo deleted | Already-installed brainstems; all planted neighborhoods (own repos); install one-liner needs mirror | tests/scenarios/17-survival.sh |
| GitHub Pages down | Everything except gate UIs (agents via `raw.githubusercontent.com`) | manual |
| `raw.githubusercontent.com` down | Cached state via `cachedGhJson` (📡 stale pill) | `cachedGhJson` test in tests/run-tests.mjs |
| GitHub entirely offline | Live WebRTC tethers; cached subscriptions; file:// local subscriptions | tests/scenarios/13-charizard-in-the-woods.sh + 01 |
| Operator's brainstem dies | Eggs hatch identically (same rappid) anywhere | tests/scenarios/13 + 15 |
| Internet entirely down | Local-only neighborhoods; cached state; Dream Catcher reconciles when back | tests/scenarios/01 + 15 |

**The redundancy stack:** brainstem process memory → `~/.brainstem/neighborhoods/<slug>/` → git clone → exportable egg → GitHub canonical. Failure has to take out all five.

**The "what if RAPP itself goes offline" answer:** existing brainstems keep running; every neighborhood is its own repo; install one-liner can be re-served from any mirror (Constitution Art. V keeps the URL stable). See SURVIVAL.md "RAPP itself goes down" section.

---

## §18 — Updating this map

- **Append-only.** Never repurpose a row; bump version on the row instead.
- **Schema:** `rapp-ecosystem-map/1.0`. Bump on breaking changes.
- **Derivative.** If this map disagrees with `MASTER_PLAN.md` / `CONSTITUTION.md` / spec docs, the spec wins and the map is wrong — fix the map.
- **§13 drift is the only mutable section** — entries get added when found, removed when reconciled (PR closes a row by making spec and code agree).
- **Add a row to §11 the first time you see Claude (or yourself) drift on a given trigger.** The map's job is to catch the next miss.

*Map first published 2026-05-08. Maintained at repo root as a peer of `MASTER_PLAN.md`.*
