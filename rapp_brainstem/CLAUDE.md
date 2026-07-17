# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the **brainstem component** in this repo.

> **Current RAPP/1 authority (rev-5).** For canonicalization, identity, frames,
> wire, eggs, registry, trust, and protocol evolution, follow
> [`RAPP1_AUTHORITY.json`](../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../RAPP1_STATUS.md). The
> `kody-w/rapp-installer@brainstem-v0.6.9` `brainstem.py`,
> `agents/basic_agent.py`, and `VERSION` bytes are read-only; incompatible
> behavior below is migration input, not current protocol.

## Current component instructions

- Do not edit `brainstem.py`, `agents/basic_agent.py`, or `VERSION`; verify
  them against `kody-w/rapp-installer@brainstem-v0.6.9`.
- The port-7071 application is contained legacy source, not a shipped local
  product, browser UI, installer, catalog, or hatcher. `start.sh`, `start.ps1`,
  and `utils/boot.py` are unconditional 410/exit-78 tombstones; direct
  immutable execution is isolated canonical test evidence only.
- Current target-owned synchronous work uses the loopback pre-acceptance
  façade at `127.0.0.1:7073`. Its launcher imports no grail module and defaults
  to `inference-refused` until a reviewed adapter is explicitly injected:
  required string `user_input`; optional strings `session_id` and
  `idempotency_key`; exact success members `response`, `agent_logs` (array),
  and `session_id`; exact HTTP 422 nested `error.code`/`error.step`.
- Voice and Twin derive locally from `response` and add no fields.
- Validate through `python3 tests/run_rapp1_conformance.py`; passing remains
  structural/pre-acceptance only.

## Historical component guide (superseded)

<!-- RAPP1-HISTORICAL-SECTION-START -->

> **For repo-wide guidance** (canon, governance, reading order across the whole platform) start at the [**Kernel hub**](https://kody-w.github.io/RAPP/pages/kernel.html) or the root [`CLAUDE.md`](../CLAUDE.md). This file (`rapp_brainstem/CLAUDE.md`) is scoped to the Tier 1 Brainstem itself.

## Project Overview

RAPP Brainstem is a local-first AI agent server. It's a Flask app that proxies conversation through the GitHub Copilot API with automatic tool-calling via user-defined agents. Single dependency: a GitHub account with Copilot access. Runs on port 7071.

Philosophy: "engine, not experience" — infrastructure only, no opinionated UI or workflows (see CONSTITUTION.md).

## Commands

```bash
# Start server
./start.sh                # macOS/Linux (creates venv, installs deps, runs)
python brainstem.py       # Direct run (assumes deps installed)

# Install dependencies
pip3 install -r requirements.txt

# Run all tests
python3 -m pytest test_local_agents.py -v

# Run a single test
python3 -m pytest test_local_agents.py::TestLocalStorage::test_write_and_read -v
```

No build step, linter, or type checker is configured.

## Architecture

**Entry point:** `brainstem.py` — a single-file Flask server (~1100 lines) that handles auth, chat, agent orchestration, and the web UI.

**Request flow (POST /chat):**
The external contract is exactly RAPP/1 §8: required `user_input`, optional
`session_id` and `idempotency_key`, exact HTTP 200/422 bodies.

1. Load `soul.md` (system prompt) and fresh-discover agents from `agents/`
2. Build OpenAI-format tool definitions from agent metadata
3. Call GitHub Copilot API with system prompt + conversation history + tools
4. If the LLM returns tool calls, execute agent `.perform()` methods and loop (up to 3 rounds)
5. Return exactly `response`, `agent_logs` (array), and `session_id`

**Agent system:**
- Auto-discovered via glob `agents/*_agent.py` (flat directory only — `agents/experimental/` is intentionally excluded)
- Each agent is a Python class extending `BasicAgent` with `metadata` (OpenAI function schema) and `perform(**kwargs)` method
- Optional `system_context()` injects text into the system prompt every turn
- Agents are reloaded from disk on every request — edit and test without restart
- Missing pip dependencies are auto-installed at import time

**Local storage shim** (`local_storage.py`): Agents import `from utils.azure_file_storage import AzureFileStorageManager` — brainstem intercepts via `sys.modules` and provides a local JSON-file implementation under `.brainstem_data/`. This enables transparent migration to Azure later.

**Auth chain:** `GITHUB_TOKEN` env var → `.copilot_token` file (device-code OAuth) → `gh auth token` CLI. The GitHub token is exchanged for a short-lived Copilot API token, cached in `.copilot_session` with auto-refresh.

Provider auth is not RAPP protocol trust; §§10/13 govern artifact signatures,
keys, revocation, and registry resolution.

## Key Files

| File | Purpose |
|------|---------|
| `brainstem.py` | Main server: all routes, agent loading, Copilot API integration |
| `basic_agent.py` | Base class for agents (also copied to `agents/basic_agent.py`) |
| `local_storage.py` | Local shim for Azure File Storage |
| `soul.md` | Default system prompt loaded every request |
| `index.html` | Built-in web UI served at `/` |
| `VERSION` | Semantic version string (currently 0.4.0) |
| `CONSTITUTION.md` | Governance doc defining what belongs in this repo |
| `utils/bond.py` | Legacy transitional egg packer/unpacker. Its retired `brainstem-egg/2.x` inputs are migration material only; current eggs are RAPP/1 §9 `rapp/1-egg` variants. |

## Kernel-shipped agents (the minimum, not the menu)

The base install ships ONLY: `basic_agent.py`, `context_memory_agent.py`, `manage_memory_agent.py`, `learn_new_agent.py`, `swarm_factory_agent.py`, `hacker_news_agent.py`. Everything else lives in RAR (`kody-w/RAR`) and is installed on demand once the operator is ready.

Notably **not** kernel — installable from RAR:
- `@rapp/twin_agent` + `@rapp/egg_hatcher` — the Organism Lifecycle pack (`binders/@rapp-organism-lifecycle.json`). Install when you need to host sub-twins or hatch .egg cartridges (organism / rapplication / session / neighborhood / estate).
- `@kody/workiq_agent` — Microsoft 365 access (emails, calendar, Teams, SharePoint/OneDrive). Install when you have a workiq CLI + Entra ID login.

Past installs that have these three under `agents/` keep working — discovery is flat-glob; they just aren't shipped on a fresh brainstem anymore.

## Writing Agents

Agents must:
- Live in `agents/` with filename matching `*_agent.py`
- Define a class extending `BasicAgent` with `metadata` dict (OpenAI function-calling schema) and `perform(**kwargs)` returning a string
- Use `self.metadata["description"]` to tell the LLM when to invoke the agent

The `agents/experimental/` subdirectory exists for agents that should not be auto-loaded.

## Environment

Configuration via `.env` (auto-created from `.env.example` by `start.sh`):
- `GITHUB_TOKEN` — auto-detected from `gh` CLI if blank
- `GITHUB_MODEL` — default `gpt-4o`, switchable at runtime via `/models/set`
- `SOUL_PATH`, `AGENTS_PATH`, `PORT`, `VOICE_MODE`

<!-- RAPP1-HISTORICAL-SECTION-END -->
