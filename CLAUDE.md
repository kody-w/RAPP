# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

1. **Single-file agents are the plugin system.** One file = one class = one `perform()` = one metadata dict. No build steps, no sibling imports, no frameworks.
2. **Single-file services are the HTTP extension system.** One file = `name` + `handle(method, path, body) → (dict, status)`. Dispatched via `/api/<name>/<path>`. Services serve UIs; agents serve LLMs. They never overlap.
3. **Agent-first rule.** Every rapplication MUST work fully through the agent alone. The service is always optional — it's a view, not the application.
4. **Brainstem stays light.** The kernel is `brainstem.py` + `basic_agent.py`. It provides agent discovery and service discovery — nothing else. New features → new agents or services, not brainstem changes.
5. **Delimited slots are fixed forever.** `|||VOICE|||` and `|||TWIN|||` never get repurposed or overloaded. New sub-capabilities use tags inside the slot.
6. **Tier portability guarantee.** An agent that runs in Tier 1 must run unmodified in Tier 2 & 3.

## Key Directories

| Directory | Purpose |
|-----------|---------|
| `rapp_brainstem/` | Tier 1 local server (Flask, agents, services, web UI) |
| `rapp_swarm/` | Tier 2 Azure Functions (vendors brainstem core) |
| `worker/` | Cloudflare auth/proxy worker |
| `rapp_store/` | Rapplication catalog (index.json + agent packages) |
| `tests/` | JS test runner + integration test scripts |
| `installer/` | Public install surface — one-liner installers (`install.sh`, `install.ps1`, `install.cmd`), `start-local.sh`, `install-swarm.sh`, `azuredeploy.json` (ARM template), install-widget mirror, and the Tier 3 Copilot Studio bundle (`MSFTAIBASMultiAgentCopilot_*.zip`) |
| `CONSTITUTION.md` | Repo governance — at root as a peer of `README.md` |
| `pages/` | The full audience-facing site (not a folder of orphan pages). Sectioned: `pages/about/`, `pages/product/`, `pages/release/`, `pages/docs/` (markdown viewer), `pages/vault/` (Obsidian vault + viewer). Shared chrome at `pages/_site/` (`css/`, `js/`, `partials/`, `index.json`). New audience HTML drops into the matching section; the manifest at `pages/_site/index.json` is the canonical inventory. |
| `pages/vault/` | Long-term memory: decision narratives, removal stories, manifestos. Real Obsidian vault — open `pages/vault/` directly in any Obsidian client. **When you learn *why* a decision was made, write it here as a stub or a published note — don't bury it in a commit message.** See `CONSTITUTION.md` Article XXIII. |

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

## Background context (the vault)

Every non-trivial architecture decision in this repo has a long-form essay in `pages/vault/` that explains the *why*. Before proposing a change to the brainstem, the slot delimiters, the agent contract, the vendoring discipline, or the tier model, read the relevant vault note — most "could we relax constraint X?" conversations are already settled there. The reading paths in `pages/vault/Reading Paths/` are tuned for different audiences (engineer, architect, partner, exec, contributor).
