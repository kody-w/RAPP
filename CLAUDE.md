# CLAUDE.md

> **Current RAPP/1 authority (rev-5).** For canonicalization, identity, frames,
> wire, eggs, registry, trust, and protocol evolution, follow
> [`RAPP1_AUTHORITY.json`](./RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](./RAPP1_STATUS.md). Incompatible guidance below describes
> legacy runtime behavior or migration inputs, not current protocol. The
> `KERNEL_PIN.json` grail bytes remain read-only.

## Current repository instructions

1. Read `RAPP1_AUTHORITY.json` and `RAPP1_STATUS.md` first. The repository is
   structurally pinned to RAPP/1 rev-5 and is **not yet fully conformant**.
2. Never edit the three immutable grail bytes pinned to
   `kody-w/rapp-installer@brainstem-v0.6.9`, the prepared
   `cave/rapplications/rapp-installer/**` subtree, archives, or generated
   external mirrors.
3. The only target-owned synchronous protocol adapter is the loopback,
   pre-acceptance façade at `127.0.0.1:7073`. It imports no grail module and
   defaults to `inference-refused` until a reviewed adapter is explicitly
   injected. Its request contains required string `user_input` and optional
   strings `session_id` and `idempotency_key`; success contains exactly
   `response`, `agent_logs` (array), and `session_id`; refusal is HTTP 422 with
   exactly nested `error.code` and `error.step`.
4. Voice and Twin presentation derive locally from `response`. They add no
   request or response fields.
5. Tier 1/2/3, public installers, browser brainstems, Shortcuts, planting,
   catalogs, cave bootstraps, legacy egg hatching, and Commons samples are
   retired or pre-acceptance. Do not advertise, deploy, download, or invoke
   them from documentation. The target-owned legacy brainstem launchers are
   unconditional 410/exit-78 tombstones; direct immutable execution is
   isolated canonical test evidence only.
6. For structural/pre-acceptance validation run
   `python3 tests/run_rapp1_conformance.py`. Documentation-only work may first
   run `python3 tools/check_rapp1_docs.py`,
   `bash tests/e2e/08-html-pages.sh`, and `node tests/vault-check.mjs`.

## Historical repository guide (superseded)

<!-- RAPP1-HISTORICAL-SECTION-START -->

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Where to start reading.** The unified human-facing entry point is **[`pages/kernel.html`](https://kody-w.github.io/RAPP/pages/kernel.html)** — it surfaces every canon doc in canonical reading order with audience-specific Reading Paths. When you need to direct a human to the docs, point there. When *you* need to read, start with [`MASTER_PLAN.md`](./MASTER_PLAN.md), [`HERO_USECASE.md`](./HERO_USECASE.md), [`ECOSYSTEM.md`](./ECOSYSTEM.md), [`CONSTITUTION.md`](./CONSTITUTION.md), [`ANTIPATTERNS.md`](./ANTIPATTERNS.md) in that order.

## Project Overview

RAPP (Rapid Agent Prototype Platform) is a platform implementing a three-tier AI agent platform. Philosophy: "engine, not experience" — infrastructure only, no opinionated UI or workflows.

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
node tests/run-tests.mjs                                           # Current RAPP/1 core/static contract checks
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

At the protocol boundary, the request and response are exactly RAPP/1 §8:
required `user_input`, optional `session_id`/`idempotency_key`; HTTP 200 has
exactly `response`, `agent_logs`, `session_id`, and refusal is the exact 422
error shape.

1. Load `soul.md` (system prompt) + fresh-discover agents from `agents/`
2. Build OpenAI-format tool definitions from agent metadata
3. Call LLM via provider dispatch (GitHub Copilot API, Azure OpenAI, OpenAI, or Anthropic)
4. If LLM returns tool_calls → execute agent `.perform()` methods → loop (max 3 rounds Tier 1, 4 rounds Tier 2)
5. Split response on `|||VOICE|||` and `|||TWIN|||` delimiters
6. Return exactly response + `agent_logs` + `session_id`; telemetry remains
   internal and must not add a response member

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

This is provider/application authentication, not RAPP trust; authenticated
artifact acceptance follows §§10/13.

## Sacred Constraints (`pages/docs/SPEC.md` & `CONSTITUTION.md`)

These product-extension constraints remain inviolable where they do not
conflict with RAPP/1. Protocol evolution follows RAPP/1 §12 total migration and
retirement, not perpetual backwards compatibility:

1. **Single-file agents are the unit of extension.** One file = one class = one `perform()` = one metadata dict. No build steps, no sibling imports, no frameworks. (We say "agent" — never "skill"/"plugin"/"routine"/"loop". See [`ANTIPATTERNS.md`](./ANTIPATTERNS.md) §1.)
2. **Single-file organs are the application-view extension system.** One file
   = `name` + `handle(method, path, body) → (dict, status)`, dispatched via
   `/api/<name>/<path>`. These routes do not expand the RAPP wire. Legacy
   filenames are recognized only during bounded host migration, then retired.
3. **Agent-first rule.** Every rapplication MUST work fully through the agent alone. The organ is always optional — it's a view, not the application.
4. **Brainstem stays light.** The immutable grail is
   `kody-w/rapp-installer@brainstem-v0.6.9`; pinned `brainstem.py`,
   `agents/basic_agent.py`, and `VERSION` are never edited locally. New RAPP
   capabilities are agents behind §8; organs may add application views only.
5. **Delimited slots are application rendering, not wire members.**
   `|||VOICE|||` and `|||TWIN|||` may be interpreted inside the exact §8
   `response` string. They never authorize extra protocol fields, and any
   evolution remains subordinate to RAPP/1 §12.
6. **Tier portability guarantee.** An agent that runs in Tier 1 must run unmodified in Tier 2 & 3.
7. **Rapplications ARE organisms** ([Constitution Article XXXVII](./CONSTITUTION.md), shipped 2026-05-02). Same rappid format, same egg distribution, same bonding lifecycle, just different scope. "Rapplication" is a quality tier (graduated, has skin), not a structural type. All five catalog forms (organism / rapplication / variant / sense / bare agent) live on one address space.

## Identity & bonding (the organism layer)

Every locally-installed brainstem is intended to be its own digital organism.
For current identity, minting, preservation, and re-anchor rules use RAPP/1 §6;
the runtime paths below are implementation facts under migration and do not
authorize provisional emission or silent re-minting:

- `~/.brainstem/rappid.json` — legacy application identity record. Current
  identity is the RAPP/1 §6 rappid, minted once per organism (not per machine),
  reused on read, and changed only by a verifiable §6.3 re-anchor. Any
  `parent_rappid` is product-lineage metadata, not the trust root.
- `~/.brainstem/bonds.json` — append-only lineage log. Event kinds: `birth`, `bond` (kernel upgrade), `adoption` (legacy install retroactively given identity), `hatch` (egg arrived from elsewhere), `graft` (additive overlay onto an existing public repo via `graft_neighborhood_agent`), `launch` (LOCAL→GLOBAL push of the local brainstem to a target public repo via `launch_to_public_agent`), `rhythm` (Bond Pulse heartbeat — `bond_rhythm_agent` reconciling local + global on a beat).
- `~/.brainstem/.bond/last-pre-bond.egg` — recovery checkpoint, snapshot of organism state right before the last kernel overlay.
- **Historical bond cycle**: the legacy installer detected a remote `VERSION`
  and overlaid a kernel between egg/hatch operations. It must not change the
  three bytes pinned to `rapp-installer@brainstem-v0.6.9`; any future grail
  change requires an explicit authority event, while ordinary convergence
  belongs in target-owned adapters.
- **Legacy egg formats** (retired `brainstem-egg/*` migration inputs in
  `utils/bond.py`; current producers use RAPP/1 §9 `rapp/1-egg`):
  - `2.2-organism` — full instance cartridge (rappid + soul + .env + agents + organs + senses + services + .brainstem_data)
  - `2.2-rapplication` — single rapp cartridge (rappid + agent + UI + per-rapp state)
  - `2.1` — variant repo cartridge (templated brainstem clone)
- **CLI**: `brainstem identity` / `brainstem egg [out]` / `brainstem hatch <egg>`
- **Application views**: `GET /api/identity` and `/api/lineage` expose local
  records; they are not RAPP wire forms or substitutes for signed §13
  resolution.
- **Bond Pulse** ([vault/Decisions/2026-05-09 — Bond Pulse](./pages/vault/Decisions/2026-05-09%20%E2%80%94%20Bond%20Pulse%20%E2%80%94%20the%20on-going%20beat%20for%20the%20full%20organism.md)) — the on-going local↔global heartbeat for the FULL organism (global body = offspring repos; local body = `~/.brainstem/`). One pulse: `tools/ecosystem_audit.py` detects drift → `bond_rhythm_agent` classifies as LOCAL→GLOBAL push (suggest `Launch`/`Graft`) vs GLOBAL→LOCAL pull (suggest `RarLoader`) vs informational → records `kind="rhythm"` event → returns `rapp-rhythm-pulse/1.0`. Operator-mediated: SUGGESTS but never auto-executes. Connection-aware: gracefully degrades to local-only when offline; next pulse with connection catches the body up.

## Visual anatomy + Pokédex (where to send users to learn)

- [`pages/about/anatomy.html`](./pages/about/anatomy.html) — full visual diagram of an organism. DNA / soul / organs / senses / cells / memory / skin / egg with hover-to-highlight cards. Linked from the brainstem's settings panel as the canonical onboarding artifact.
- [`rapp-zoo/`](https://github.com/kody-w/rappter-distro/tree/main/rapp-zoo) — the local-first Pokédex. Three tabs (My collection / Starters / Discover), drag-drop egg import, deterministic SVG sprites per organism, three bundled starters (workday/playtime/journal). Single-file static page; localStorage holds metadata, IndexedDB holds blobs, the whole collection round-trips through one JSON for backup. **Lives in [kody-w/rappter-distro](https://github.com/kody-w/rappter-distro) as of 2026-05-16** — moved out of the kernel mirror so RAPP can be a god SPEC repo. CONSTITUTION Article XXXVIII.4 was amended accordingly.
- [`kody-w/RAPP_Store`](https://github.com/kody-w/RAPP_Store) `/api/v1/` —
  application discovery catalog. Entries and downloadable files are untrusted
  candidates until current RAPP/1 egg and signature verification succeeds.

## Historical vBrainstem + legacy `.egg` cartridges

The following records what shipped on 2026-05-10. The cited local SPEC is
superseded and these forms are migration inputs only; RAPP/1 §§8–9 govern
current wire and eggs.

- [`pages/vbrainstem.html`](./pages/vbrainstem.html) is a contained legacy
  browser surface. Its retired `brainstem-egg/2.3-session` export is not a
  current RAPP/1 egg.
- The legacy cartridge family (`brainstem-egg/2.2-organism`,
  `2.2-rapplication`, `2.3-session`, `2.3-neighborhood`, `2.3-estate`) and its
  external mirrors remain migration evidence, not authority.
- **Historical hatcher implementation:** `@rapp/egg_hatcher` was distributed
  through RAR and routed retired schema/type cartridges. Do not install or use
  it as current acceptance; a replacement must perform all §9.3 checks and
  dispatch only registered RAPP/1 `variant` values.
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
| `pages/tutorials/` | Historical tutorial archive. The retired hatch page and bundled legacy artifacts are migration evidence only; they are not advertised, downloadable acceptance inputs, or current RAPP/1 §9 guidance. |
| `examples/rapp-commons/` | Retired Commons scaffold history. Do not link, download, plant, or hatch its sample artifacts. The exact owner-only replacement and retirement work is recorded in `RAPP1_OWNER_ACTIONS.md` / `.json`. |

## Environment

Configuration via `rapp_brainstem/.env` (auto-created from `.env.example`):
- `GITHUB_TOKEN` — auto-detected from `gh` CLI if blank
- `GITHUB_MODEL` — default `gpt-4o`, switchable at runtime
- `SOUL_PATH`, `AGENTS_PATH`, `PORT`, `VOICE_MODE`, `TWIN_MODE`

Azure OpenAI (Tier 2): `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`

## Vendoring (Tier 2)

`rapp_swarm/build.sh` copies brainstem core files into `rapp_swarm/_vendored/`. After modifying brainstem code that Tier 2 uses, re-run the build script to sync.

## Distribution

The public product installer remains at
`curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash`.
GitHub Pages and raw URLs are transport, not structural authority. The
installer must preserve and verify the three exact
`rapp-installer@brainstem-v0.6.9` bytes; it may refresh target-owned adapters
but may not select a moving grail release.

## Hero use case + ecosystem + antipatterns (READ FIRST)

These checked-in product documents provide implementation context. They remain
subordinate to `RAPP1_AUTHORITY.json` and `RAPP1_STATUS.md`; read them before
proposing product changes, never as alternate protocol contracts:

- [`ECOSYSTEM_MAP.md`](./ECOSYSTEM_MAP.md) — *the product index*. Synthesis of
  declarations, files, decisions, and drift; never a protocol registry.
- [`OSI.md`](./OSI.md) — *the 7-layer model*. Substrate / identity / discovery / channels / trust / envelope / application. Each layer has schemas, impl, tests. Use to figure out which layer a new feature belongs to. Test suite at `tests/osi/`.
- [`HERO_USECASE.md`](./HERO_USECASE.md) — *what* this platform must do. Canonical scenarios this codebase must satisfy: Charizard-in-the-woods (offline-share over QR pair), Dream Catcher (parallel-dimension reassimilation), Mom's Mixtape (accessibility floor), Pizza Place (future location-aware layer). Every architectural decision is judged against whether these stories still work.
- [`ECOSYSTEM.md`](./ECOSYSTEM.md) — *how* the pieces fit together. End-to-end layout of a planted organism: file structure, identity stack, the two surfaces, memory tiers, MMR system, evolution path, egg cartridges, integrity stack, Dream Catcher, network modes, external integrations, surface inventory, schema reference.
- [`ANTIPATTERNS.md`](./ANTIPATTERNS.md) — *what we will never do*. Locked rules: ONE term for the plugin unit (always `agent`, never `skill`/`routine`/`loop`/`plugin`); frozen kernel never moves; no half-released-feature shims; no fallback to "RAPP"/"an AI assistant" branding; no network calls without local-first fallback. Append-only.
- [`NEIGHBORHOOD_PROTOCOL.md`](./NEIGHBORHOOD_PROTOCOL.md) — historical and
  application federation adapters. Current cross-organism interaction maps to
  the exact RAPP/1 §8 forms and §§10/13 trust.
- [`pages/onboarding.html`](./pages/onboarding.html) — visitor-facing onboarder. Trust-building tone for non-technical visitors who need to understand why this isn't sketchy. Link new visitors here, not directly to the spec docs.

PRs that would degrade a ✅ row in `HERO_USECASE.md` must explain why.
Application metadata may evolve with its owning docs. Protocol structure
changes only through the constitutional process, total §12 migration, and
signed §13 state—never by bumping a local version string.

## Background context (the vault)

Every non-trivial architecture decision in this repo has a long-form essay in `pages/vault/` that explains the *why*. Before proposing a change to the brainstem, the slot delimiters, the agent contract, the vendoring discipline, or the tier model, read the relevant vault note — most "could we relax constraint X?" conversations are already settled there. The reading paths in `pages/vault/Reading Paths/` are tuned for different audiences (engineer, architect, partner, exec, contributor).

<!-- RAPP1-HISTORICAL-SECTION-END -->
