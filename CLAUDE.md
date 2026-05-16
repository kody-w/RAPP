# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Where to start reading.** The unified human-facing entry point is **[`pages/kernel.html`](https://kody-w.github.io/RAPP/pages/kernel.html)** — it surfaces every canon doc in canonical reading order with audience-specific Reading Paths. When you need to direct a human to the docs, point there. When *you* need to read, start with [`MASTER_PLAN.md`](./MASTER_PLAN.md), [`HERO_USECASE.md`](./HERO_USECASE.md), [`ECOSYSTEM.md`](./ECOSYSTEM.md), [`CONSTITUTION.md`](./CONSTITUTION.md), [`ANTIPATTERNS.md`](./ANTIPATTERNS.md) in that order.

## Project Overview

RAPP (Rapid Agent Prototyping Platform) is a platform implementing a three-tier AI agent platform. Philosophy: "engine, not experience" — infrastructure only, no opinionated UI or workflows.

The three tiers are independently runnable and share the same single-file agent contract:
- **Tier 1 (Local):** `rapp_brainstem/` — Python Flask server on port 7071
- **Tier 2 (Cloud):** `rapp_swarm/` — Azure Functions deployment with vendored brainstem core
- **Tier 3 (Enterprise):** `installer/MSFTAIBASMultiAgentCopilot_*.zip` — Power Platform solution download for Microsoft Copilot Studio (an install artifact, not a tier directory — Studio runs in Microsoft's cloud, not in this repo)

## Commands

```bash
# Tier 1 — Local brainstem
cd rapp_brainstem
./start.sh                              # Creates venv, installs deps, runs on :7071
python brainstem.py                     # Direct run (deps must already be installed)
pip3 install -r requirements.txt        # Install dependencies

# Tests (run from repo root unless noted)
python3 -m pytest rapp_brainstem/test_local_agents.py -v           # Python agent tests
python3 -m pytest rapp_brainstem/test_local_agents.py::TestLocalStorage::test_write_and_read -v  # Single test
node tests/run-tests.mjs                                           # JS contract tests (agent parsing, cards, binder, sealing)
node tests/vault-check.mjs                                         # Vault link/PII guardrail
bash tests/e2e/08-html-pages.sh                                    # Marketing pages content checks

# Tier 2 — Azure Functions
bash rapp_swarm/build.sh                # Vendor brainstem core into _vendored/
cd rapp_swarm && func start             # Start locally (requires local.settings.json)

# Tier 3 — Cloudflare auth worker
cd worker && npx wrangler dev           # Local dev on :8787
```

No linter, type checker, or CI pipeline is configured.

## Cloning a single tier (optional)

Default is a full clone — users typically progress from Tier 1 (brainstem) to Tier 2 (swarm) to Tier 3 (enterprise) over time, so the install one-liner pulls everything. The catalog (`kody-w/rapp_store`) is the only repo split out.

If a contributor explicitly wants a leaner clone for one-tier work, sparse-checkout is supported (each tier is self-contained — never reaches up to the monorepo root):

```bash
git clone --filter=blob:none --no-checkout https://github.com/kody-w/RAPP.git brainstem
cd brainstem
git sparse-checkout init --cone
git sparse-checkout set rapp_brainstem      # or rapp_swarm, or worker
git checkout main
```

Suggest sparse-checkout only when explicitly asked or when the user names a single tier. Otherwise default-recommend the full clone — they'll likely want the other tiers later.

## Architecture

### Request Flow (POST /chat)

1. Load `soul.md` (system prompt) + fresh-discover agents from `agents/`
2. Build OpenAI-format tool definitions from agent metadata
3. Call LLM via provider dispatch (GitHub Copilot API, Azure OpenAI, OpenAI, or Anthropic)
4. If LLM returns tool_calls → execute agent `.perform()` methods → loop (max 3 rounds Tier 1, 4 rounds Tier 2)
5. Split response on `|||VOICE|||` and `|||TWIN|||` delimiters
6. Return response + `agent_logs` + telemetry

### Agent System

- Auto-discovered via glob `agents/*_agent.py` (flat only — `agents/experimental/` excluded)
- Each agent: one file, one class extending `BasicAgent`, one `metadata` dict, one `perform(**kwargs) -> str`
- Reloaded from disk every request — edit without restart
- Missing pip deps auto-installed at import time
- Portable: same file runs unmodified across all three tiers

### Data Sloshing

Agents return JSON with optional `"data_slush": { ... }` — lands in next agent's `self.context.slush` deterministically without LLM interpretation.

### Local Storage Shim

Agents import `from utils.azure_file_storage import AzureFileStorageManager` — brainstem intercepts via `sys.modules` and provides a JSON-file implementation under `.brainstem_data/`. Transparent migration to Azure.

### Provider Dispatch (`llm.py`)

Routes to GitHub Copilot API (default), Azure OpenAI, OpenAI, Anthropic, or a deterministic fake (for tests via `LLM_FAKE=1`).

### Auth Chain (Tier 1)

`GITHUB_TOKEN` env → `.copilot_token` file (device-code OAuth) → `gh auth token` CLI. Token exchanged for short-lived Copilot API token cached in `.copilot_session`.

## Sacred Constraints (`pages/docs/SPEC.md` & `CONSTITUTION.md`)

These are inviolable — do not break backwards compatibility:

1. **Single-file agents are the unit of extension.** One file = one class = one `perform()` = one metadata dict. No build steps, no sibling imports, no frameworks. (We say "agent" — never "skill"/"plugin"/"routine"/"loop". See [`ANTIPATTERNS.md`](./ANTIPATTERNS.md) §1.)
2. **Single-file organs are the HTTP extension system.** One file = `name` + `handle(method, path, body) → (dict, status)`. Dispatched via `/api/<name>/<path>`. Organs serve UIs; agents serve LLMs. They never overlap. (Constitution Article XXXIII canonical: `*_organ.py` under `utils/organs/`. Legacy `*_body_function.py` and `*_service.py` files in older installs continue to work via transitional discovery.)
3. **Agent-first rule.** Every rapplication MUST work fully through the agent alone. The organ is always optional — it's a view, not the application.
4. **Brainstem stays light.** The kernel is `brainstem.py` + `basic_agent.py`. It is the **DNA** of the digital organism (Constitution Article XXXIII) — universal, drop-in replaceable, **never edited by AI assistants**. New features → new agents or new organs, never kernel changes.
5. **Delimited slots are fixed forever.** `|||VOICE|||` and `|||TWIN|||` never get repurposed or overloaded. New sub-capabilities use tags inside the slot.
6. **Tier portability guarantee.** An agent that runs in Tier 1 must run unmodified in Tier 2 & 3.
7. **Rapplications ARE organisms** ([Constitution Article XXXVII](./CONSTITUTION.md), shipped 2026-05-02). Same rappid format, same egg distribution, same bonding lifecycle, just different scope. "Rapplication" is a quality tier (graduated, has skin), not a structural type. All five catalog forms (organism / rapplication / variant / sense / bare agent) live on one address space.

## Identity & bonding (the organism layer)

Every locally-installed brainstem is its own digital organism with persistent identity:

- `~/.brainstem/rappid.json` — organism identity (parent_rappid points at the species root, [`kody-w/RAPP`](https://github.com/kody-w/RAPP)). Minted ONCE per machine on first install. Survives every kernel upgrade.
- `~/.brainstem/bonds.json` — append-only lineage log. Event kinds: `birth`, `bond` (kernel upgrade), `adoption` (legacy install retroactively given identity), `hatch` (egg arrived from elsewhere), `graft` (additive overlay onto an existing public repo via `graft_neighborhood_agent`), `launch` (LOCAL→GLOBAL push of the local brainstem to a target public repo via `launch_to_public_agent`), `rhythm` (Bond Pulse heartbeat — `bond_rhythm_agent` reconciling local + global on a beat).
- `~/.brainstem/.bond/last-pre-bond.egg` — recovery checkpoint, snapshot of organism state right before the last kernel overlay.
- **Bond cycle** runs every time the install one-liner detects a remote VERSION upgrade: 🥚 egg the organism → 🌐 overlay the new kernel → 🐣 hatch the egg back. rappid + soul + custom agents + memory + secrets all preserved. Implemented in `installer/install.sh` + `rapp_brainstem/utils/bond.py` (stdlib-only, runs before the venv exists).
- **Egg formats** (all `brainstem-egg/*` schemas live in `utils/bond.py`):
  - `2.2-organism` — full instance cartridge (rappid + soul + .env + agents + organs + senses + services + .brainstem_data)
  - `2.2-rapplication` — single rapp cartridge (rappid + agent + UI + per-rapp state)
  - `2.1` — variant repo cartridge (templated brainstem clone)
- **CLI**: `brainstem identity` / `brainstem egg [out]` / `brainstem hatch <egg>`
- **API**: `GET /api/identity` returns rappid + bonds + kernel version. `GET /api/lineage` walks parent_rappid back to species root.
- **Bond Pulse** ([vault/Decisions/2026-05-09 — Bond Pulse](./pages/vault/Decisions/2026-05-09%20%E2%80%94%20Bond%20Pulse%20%E2%80%94%20the%20on-going%20beat%20for%20the%20full%20organism.md)) — the on-going local↔global heartbeat for the FULL organism (global body = offspring repos; local body = `~/.brainstem/`). One pulse: `tools/ecosystem_audit.py` detects drift → `bond_rhythm_agent` classifies as LOCAL→GLOBAL push (suggest `Launch`/`Graft`) vs GLOBAL→LOCAL pull (suggest `RarLoader`) vs informational → records `kind="rhythm"` event → returns `rapp-rhythm-pulse/1.0`. Operator-mediated: SUGGESTS but never auto-executes. Connection-aware: gracefully degrades to local-only when offline; next pulse with connection catches the body up.

## Visual anatomy + Pokédex (where to send users to learn)

- [`pages/about/anatomy.html`](./pages/about/anatomy.html) — full visual diagram of an organism. DNA / soul / organs / senses / cells / memory / skin / egg with hover-to-highlight cards. Linked from the brainstem's settings panel as the canonical onboarding artifact.
- [`rapp-zoo/`](https://github.com/kody-w/rappter-distro/tree/main/rapp-zoo) — the local-first Pokédex. Three tabs (My collection / Starters / Discover), drag-drop egg import, deterministic SVG sprites per organism, three bundled starters (workday/playtime/journal). Single-file static page; localStorage holds metadata, IndexedDB holds blobs, the whole collection round-trips through one JSON for backup. **Lives in [kody-w/rappter-distro](https://github.com/kody-w/rappter-distro) as of 2026-05-16** — moved out of the kernel mirror so RAPP can be a god SPEC repo. CONSTITUTION Article XXXVIII.4 was amended accordingly.
- [`kody-w/RAPP_Store`](https://github.com/kody-w/RAPP_Store) `/api/v1/` — PokeAPI-style static catalog. Each cataloged rapplication has an entry JSON, a sprite SVG, and a downloadable `.egg`. Hosted via `raw.githubusercontent.com`.

## vBrainstem + the `.egg` cartridge family (the tethered surface)

Shipped 2026-05-10. See `pages/docs/SPEC.md` §18.10–§18.12 for the canonical spec.

- [`pages/vbrainstem.html`](./pages/vbrainstem.html) ([live at `kody-w.github.io/RAPP/pages/vbrainstem.html`](https://kody-w.github.io/RAPP/pages/vbrainstem.html)) — multi-participant browser-tab tether. Two devices pair via QR (PeerJS public broker → WebRTC data channel, ECDSA P-256 keypair + 6-digit safety code), both screens stay synced; an autonomous Coordinator twin drives a 4-step debate workflow (Reporter fetches HN top story → DebaterA → DebaterB → Editor newsletter). Three exchangeable LLM backends: localhost `:7071` (default), `?brainstem=URL`, `?copilot=1` (Pyodide-loaded Python agents + Copilot via Doorman). The session IS a `brainstem-egg/2.3-session` cartridge — exportable as `.egg`.
- The `.egg` cartridge family (single sneakernet primitive across the ecosystem; same extension, same rappzoo Pokédex shelf): `brainstem-egg/2.2-organism`, `2.2-rapplication`, `2.3-session`, `2.3-neighborhood` (planned), `2.3-estate` (planned). Master spec: [`kody-w/rappterbox/carts/SCHEMA.md`](https://github.com/kody-w/rappterbox/blob/main/carts/SCHEMA.md). Master packers/unpackers (ZIP variants): [`rapp_brainstem/utils/bond.py`](./rapp_brainstem/utils/bond.py).
- `@rapp/egg_hatcher` — **installable from RAR** ([`kody-w/RAR/agents/@rapp/egg_hatcher_agent.py`](https://github.com/kody-w/RAR/blob/main/agents/%40rapp/egg_hatcher_agent.py)), not kernel-shipped. Bundled with `@rapp/twin_agent` in the **Organism Lifecycle pack** (`binders/@rapp-organism-lifecycle.json`). Drop into a brainstem's `agents/`, restart, the LLM gets a `HatchEgg(egg_path=...)` tool. Reads any `.egg` from a local path or URL, **introspects** the manifest's schema/type, routes by kind. Never guesses; refuses on unknown kinds. Session cartridges return a mount URL (Python brainstem can't iframe — points at rappterbox console or vbrainstem.html).
- The Doorman pattern (Copilot via Cloudflare Worker — same flow `pages/sphere.html` uses): `RAPP.Doorman` namespace inside vbrainstem.html clones from sphere.html. Reads `localStorage.rapp_settings` (in-memory mirror fallback for Edge Tracking Prevention).

## Key Directories

| Directory | Purpose |
|-----------|---------|
| `rapp_brainstem/` | Tier 1 local server (Flask, agents, organs under `utils/organs/`, web UI). Sibling `tls_proxy.py` (stdlib + openssl) wraps the kernel in self-signed HTTPS at `:7072` so the live tether at `kody-w.github.io` can talk to it without a tunnel — kernel `brainstem.py` stays untouched per Article XXXIII. |
| `rapp_swarm/` | Tier 2 Azure Functions (vendors brainstem core) |
| `worker/` | Cloudflare auth/proxy worker |
| _(catalog lives in [`kody-w/rapp_store`](https://github.com/kody-w/rapp_store))_ | Rapplication catalog is its own public repo since 2026-04-26 — brainstem fetches `index.json` via `RAPPSTORE_URL` (default `raw.githubusercontent.com/kody-w/rapp_store/main/index.json`). Hosted viewer at https://kody-w.github.io/RAPP_Store/. |
| `tests/` | JS test runner + integration test scripts |
| `installer/` | Public install surface — one-liner installers (`install.sh`, `install.ps1`, `install.cmd`), `start-local.sh`, `install-swarm.sh`, `azuredeploy.json` (ARM template), install-widget mirror, and the Tier 3 Copilot Studio bundle (`MSFTAIBASMultiAgentCopilot_*.zip`) |
| `CONSTITUTION.md` | Repo governance — at root as a peer of `README.md` |
| `pages/` | The full audience-facing site (not a folder of orphan pages). Sectioned: `pages/about/`, `pages/product/`, `pages/release/`, `pages/docs/` (markdown viewer), `pages/vault/` (Obsidian vault + viewer). Shared chrome at `pages/_site/` (`css/`, `js/`, `partials/`, `index.json`). Specialty surfaces at `pages/` root: `pages/vbrainstem.html` (tethered multi-participant tab + QR pair, see SPEC §18.11), `pages/sphere.html` (3D doorman). New audience HTML drops into the matching section; the manifest at `pages/_site/index.json` is the canonical inventory. |
| `pages/vault/` | Long-term memory: decision narratives, removal stories, manifestos. Real Obsidian vault — open `pages/vault/` directly in any Obsidian client. **When you learn *why* a decision was made, write it here as a stub or a published note — don't bury it in a commit message.** See `CONSTITUTION.md` Article XXIII. |
| `pages/tutorials/` | Hands-on walkthroughs. Each tutorial bundles the agent file + sample cartridges next to the HTML so a fresh clone has everything to run the demo offline. First entry: `hatch-egg.html` (install `egg_hatcher` + hatch session + hatch the bundled `commons.egg` to join the Commons). |
| `examples/rapp-commons/` | **The Commons** — source-of-truth scaffold for the global public hangout-for-AIs neighborhood, planted as its own repo at [`kody-w/rapp-commons`](https://github.com/kody-w/rapp-commons). Full front-door grail emission: `rappid.json`, `neighborhood.json` (with `coordinates.virtual` = town-square, no physical anchor — deliberately global), `soul.md`, `members.json`, `card.json`, `holo.md`, `index.html` with QR + step-by-step join, `.well-known/neighborhood.egg` (the QR-sized JSON invite), `events/SCHEMA.md` (the `rapp-commons-event/1.0` append-only signed protocol), `specs/SPEC.md` (planted-with bundle 2.0.0 per `tools/front_door_specs.py`). Cross-estate, event-stream-only, signed-by-rappid. The archetype neighborhood — lowest possible floor. Other neighborhoods plant their own quirks (physical lat/long anchoring, virtual environments, leaderboards, decks, wikis) — the commons is just "scan, hatch, post a hello." |

## Environment

Configuration via `rapp_brainstem/.env` (auto-created from `.env.example`):
- `GITHUB_TOKEN` — auto-detected from `gh` CLI if blank
- `GITHUB_MODEL` — default `gpt-4o`, switchable at runtime
- `SOUL_PATH`, `AGENTS_PATH`, `PORT`, `VOICE_MODE`, `TWIN_MODE`

Azure OpenAI (Tier 2): `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`

## Vendoring (Tier 2)

`rapp_swarm/build.sh` copies brainstem core files into `rapp_swarm/_vendored/`. After modifying brainstem code that Tier 2 uses, re-run the build script to sync.

## Distribution

The platform's install path is one curl pipe: `curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash`. GitHub Pages serves the repo verbatim; `raw.githubusercontent.com` is the implicit content channel for everything the install script fetches afterward. The install one-liner's URL shape is sacred (Constitution Article V) — when relocating files, prefer keeping the URL stable over a marginally cleaner layout.

## Hero use case + ecosystem + antipatterns (READ FIRST)

Three checked-in specs are the contract for this codebase. Read all three before proposing structural changes:

- [`ECOSYSTEM_MAP.md`](./ECOSYSTEM_MAP.md) — *the index*. Single canonical synthesis: schemas, files, decision table, drift gaps. **Read this first; it points at the rest.**
- [`OSI.md`](./OSI.md) — *the 7-layer model*. Substrate / identity / discovery / channels / trust / envelope / application. Each layer has schemas, impl, tests. Use to figure out which layer a new feature belongs to. Test suite at `tests/osi/`.
- [`HERO_USECASE.md`](./HERO_USECASE.md) — *what* this platform must do. Canonical scenarios this codebase must satisfy: Charizard-in-the-woods (offline-share over QR pair), Dream Catcher (parallel-dimension reassimilation), Mom's Mixtape (accessibility floor), Pizza Place (future location-aware layer). Every architectural decision is judged against whether these stories still work.
- [`ECOSYSTEM.md`](./ECOSYSTEM.md) — *how* the pieces fit together. End-to-end layout of a planted organism: file structure, identity stack, the two surfaces, memory tiers, MMR system, evolution path, egg cartridges, integrity stack, Dream Catcher, network modes, external integrations, surface inventory, schema reference.
- [`ANTIPATTERNS.md`](./ANTIPATTERNS.md) — *what we will never do*. Locked rules: ONE term for the plugin unit (always `agent`, never `skill`/`routine`/`loop`/`plugin`); frozen kernel never moves; no half-released-feature shims; no fallback to "RAPP"/"an AI assistant" branding; no network calls without local-first fallback. Append-only.
- [`NEIGHBORHOOD_PROTOCOL.md`](./NEIGHBORHOOD_PROTOCOL.md) — *how organisms talk to each other*. Twin chat protocol, three concentric trust scopes (personal / neighborhood / public swarm), four channel types (WebRTC tether, Issues, PRs, raw-fetch), four exchange primitives, granular permissions via `public_facets`, adversarial-scenario walkthrough. Read before adding any cross-organism communication.
- [`pages/onboarding.html`](./pages/onboarding.html) — visitor-facing onboarder. Trust-building tone for non-technical visitors who need to understand why this isn't sketchy. Link new visitors here, not directly to the spec docs.

PRs that would degrade a ✅ row in `HERO_USECASE.md` must explain why. PRs that change schemas in `ECOSYSTEM.md` §3 or `NEIGHBORHOOD_PROTOCOL.md` must update the version string and document the migration. PRs that violate `ANTIPATTERNS.md` rules don't merge.

## Background context (the vault)

Every non-trivial architecture decision in this repo has a long-form essay in `pages/vault/` that explains the *why*. Before proposing a change to the brainstem, the slot delimiters, the agent contract, the vendoring discipline, or the tier model, read the relevant vault note — most "could we relax constraint X?" conversations are already settled there. The reading paths in `pages/vault/Reading Paths/` are tuned for different audiences (engineer, architect, partner, exec, contributor).
