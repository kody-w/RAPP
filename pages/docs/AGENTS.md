# AGENTS.md — RAPP Codebase Instructions

> **Current RAPP/1 authority (rev-5).** For canonicalization, identity, frames,
> wire, eggs, registry, trust, and protocol evolution, follow
> [`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../RAPP1_STATUS.md). The single-file agent contract is
> a product extension rule; it does not override the pinned protocol.

## Project

RAPP (Rapid Agent Prototype Platform) — a three-tier AI agent architecture built around **single-file agents**. Local Flask brainstem (Tier 1), Azure Functions cloud (Tier 2), Copilot Studio enterprise (Tier 3).

Read the pinned authority and status above before architectural changes.
[`SPEC.md`](./SPEC.md) is a superseded local v1 artifact, useful only for
history and bounded migration. Read the root Constitution—especially Article
LV—for repository governance.

## The Sacred Tenet

> **The single-file `*_agent.py` is sacred.** One file. One class. One `perform()`. One metadata dict. Zero build steps. Zero frameworks.

Everything in this repo exists to serve the single-file agent. If a change breaks this contract, the change is wrong.

**Notable application agents:** `manage_memory_agent.py` +
`context_memory_agent.py`, `hacker_news_agent.py`, `egg_hatcher_agent.py`, and
`twin_agent.py`. The existing hatcher's schema/type routing is legacy
migration behavior, not current egg acceptance. A conformant hatcher dispatches
the registered RAPP/1 §9 `variant` only after all §9.3 checks.

The retired `rapp-egg/2.0` scale switch is historical implementation
inventory. Current portable units use the ratified RAPP/1 §9 variants; do not
emit `manifest.scale` or treat an unknown scale as a current extension point.

## Commands

```bash
# Start brainstem (macOS/Linux — creates venv, installs deps, runs on :7071)
cd rapp_brainstem && ./start.sh

# Direct run (assumes deps installed)
python rapp_brainstem/brainstem.py

# Install dependencies
pip3 install -r rapp_brainstem/requirements.txt

# Run all tests (Node 18+, no deps)
node tests/run-tests.mjs

# Run brainstem unit tests
cd rapp_brainstem && python3 -m pytest test_local_agents.py -v

# Deploy Cloudflare worker
cd worker && npx wrangler deploy
```

No linter, type checker, or build step is configured.

## Architecture

```
rapp_brainstem/        Tier 1 — local Flask server (:7071) + browser UI
  brainstem.py         Entry point: all routes, agent loading, Copilot API, tool-calling loop
  soul.md              System prompt loaded every request
  agents/              Auto-discovered *_agent.py files (flat only — experimental/ excluded)
  web/                 Browser UI served at /
  local_storage.py     Local shim for Azure File Storage (JSON files under .brainstem_data/)
  twin.py              Digital twin calibration (probe/judgment cycle)

rapp_swarm/            Tier 2 — Azure Functions cloud deployment
  function_app.py      Same logic as brainstem.py, multi-backend LLM support
  provision-twin.sh    ARM template provisioning

rapp_store/            Rapplication catalog + source agents + singleton artifacts
  index.json           Store manifest (schema: rapp-store/1.0)
  <name>/manifest.json Per-rapplication manifest
  <name>/source/       Multi-file authoring surface
  <name>/singleton/    Collapsed single-file artifact (the shipped unit)
  <name>/eggs/         Stateful snapshots (.egg files)

worker/                Cloudflare Worker — stateless auth proxy for browser clients
tests/                 Node + browser test suite for the v1 contract
```

## Writing Agents

Create `agents/<thing>_agent.py` — the brainstem auto-discovers it on every request (no restart needed).

**Required contract:**
1. Filename: `*_agent.py` in `agents/` (flat directory only)
2. Class extending `BasicAgent` with `self.name` and `self.metadata` (OpenAI function-calling schema)
3. `perform(**kwargs) -> str` returning JSON with `{"status": "success|error", ...}`
4. Optional: `data_slush` key in return for chaining to next agent
5. Optional: `system_context() -> str` to inject text into system prompt every turn
6. Optional: `__manifest__` dict at module level for RAR registry membership

**Agents MUST NOT:** require a build step, import sibling agents, depend on anything beyond `BasicAgent`, or mutate runtime global state.

**Agents MAY:** make HTTP calls, shell out, write files, call other LLMs, declare pip deps (auto-installed at import).

See [rapp_brainstem/agents/hacker_news_agent.py](rapp_brainstem/agents/hacker_news_agent.py) as a reference implementation.

## Critical Rules

- **Never modify the immutable grail bytes:** `brainstem.py`,
  `agents/basic_agent.py`, and `VERSION`, pinned to
  `kody-w/rapp-installer@brainstem-v0.6.9`. New capabilities are agents behind
  the exact RAPP/1 §8 `/chat` boundary.
- **Delimited slots are permanent.** `|||VOICE|||` = TTS line. `|||TWIN|||` = digital twin. New sub-capabilities go as tags inside existing slots, not new delimiters. See Article II.
- **Portability guarantee:** an agent that runs in Tier 1 must run unmodified in Tier 2 and Tier 3. Shims go in the runtime, never in agent files.
- **`agents/experimental/`** exists for agents excluded from auto-loading.
- **The local SPEC is superseded.** Protocol evolution follows RAPP/1 §12
  total migration and retirement, not perpetual v1 compatibility.

## Auth Chain

`GITHUB_TOKEN` env → `.copilot_token` file (device-code OAuth) → `gh auth token` CLI. The GitHub token is exchanged for a short-lived Copilot API token, cached with auto-refresh.

This is application authentication to GitHub/Copilot, not RAPP protocol trust.
RAPP artifacts use §§10/13 signatures, key succession, revocation, and the
signed registry.

## Storage Shim

Agents import `from utils.azure_file_storage import AzureFileStorageManager` — brainstem intercepts via `sys.modules` and provides a local JSON-file implementation under `.brainstem_data/`. This enables transparent Tier 1 → Tier 2 migration.

## Environment

Configuration via `.env` (auto-created by `start.sh`):
- `GITHUB_TOKEN` — auto-detected from `gh` CLI if blank
- `GITHUB_MODEL` — default `gpt-4o`, switchable at runtime via `/models/set`
- `SOUL_PATH`, `AGENTS_PATH`, `PORT`, `VOICE_MODE`, `TWIN_MODE`

## Rapplications

A rapplication collapses multiple cooperating agents into a single deployable file via the "double-jump loop." Multi-file source in `rapp_store/<name>/source/`, shipped singleton in `rapp_store/<name>/singleton/`. Build with `python3 rapp_store/<name>/tools/build.py`.

## Tests

Tests verify: agent parsing, manifest extraction, seed/mnemonic round-trips, card↔agent.py byte equality, SHA-256 tamper detection, binder JSON round-trip, multi-agent chain via `data_slush`, and digital-twin file presence. Run with `node tests/run-tests.mjs` or open `tests/index.html` in a browser.
