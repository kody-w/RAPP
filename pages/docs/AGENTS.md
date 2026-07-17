# AGENTS.md — RAPP Codebase Instructions

> **Current RAPP/1 authority (rev-5).** For canonicalization, identity, frames,
> wire, eggs, registry, trust, and protocol evolution, follow
> [`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../RAPP1_STATUS.md). The single-file agent contract is
> a product extension rule; it does not override the pinned protocol.

## Project

RAPP is a source repository centered on single-file application agents and
RAPP/1 conformance. The historical Tier 1/2/3 product model is not a current
shipment: Azure Functions, Copilot Studio, and browser surfaces remain retired
or pre-acceptance artifacts.

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
# Prove the target-owned legacy launcher is contained (expected: exit 78)
bash rapp_brainstem/start.sh

# Run the authoritative structural/pre-acceptance gate
python3 tests/run_rapp1_conformance.py

# Install dependencies
pip3 install -r rapp_brainstem/requirements.txt

# Run all tests (Node 18+, no deps)
node tests/run-tests.mjs

# Run brainstem unit tests
cd rapp_brainstem && python3 -m pytest test_local_agents.py -v

```

Do not deploy the contained worker from this document. No linter, type checker,
or build step is configured.

## Architecture

```
rapp_brainstem/        Immutable historical source plus loopback refusal facade
  brainstem.py         Immutable runtime evidence; directly invoked only by isolated tests
  start.sh/.ps1        Target-owned HTTP-410 launcher tombstones
  utils/boot.py        Target-owned HTTP-410 boot tombstone
  soul.md              System prompt loaded every request
  agents/              Auto-discovered *_agent.py files (flat only — experimental/ excluded)
  web/                 Retired browser-source artifact; not a live product
  local_storage.py     Local shim for Azure File Storage (JSON files under .brainstem_data/)
  twin.py              Digital twin calibration (probe/judgment cycle)

rapp_swarm/            Retired Azure/Tier-2 source; not a shipped deployment
  function_app.py      Historical cloud adapter
  provision-twin.sh    Historical provisioning script; do not run

rapp_store/            Legacy catalog/source inventory; not a live store
  index.json           Historical store manifest (schema: rapp-store/1.0)
  <name>/manifest.json Per-rapplication manifest
  <name>/source/       Multi-file authoring surface
  <name>/singleton/    Historical collapsed build artifact
  <name>/eggs/         Retired legacy snapshots

worker/                Retired browser-auth proxy source; not deployed here
tests/                 Canonical RAPP/1 core/static gates + retired fixtures
```

## Historical Agent Shape

The immutable historical source auto-discovered
`agents/<thing>_agent.py` on each request. The shape below is retained for
source/test work; it does not authorize starting the retired server or adding
an agent to the production facade.

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
- **Voice/Twin stay local.** Presentation is derived locally from the exact
  §8 success `response` string. It adds no response fields and does not change
  the refusal object. Historical delimiters are not protocol slots.
- **No cross-tier shipment claim:** Tier 2/3 portability was an aspiration,
  not a current guarantee.
- **`agents/experimental/`** exists for agents excluded from auto-loading.
- **The local SPEC is superseded.** Protocol evolution follows RAPP/1 §12
  total migration and retirement, not perpetual v1 compatibility.

## Historical Auth Chain

The immutable historical source used `GITHUB_TOKEN` env → `.copilot_token`
file (device-code OAuth) → `gh auth token` CLI, then cached a short-lived
Copilot API token. The production facade launcher does not import or use that
chain and defaults to `inference-refused`.

This is application authentication to GitHub/Copilot, not RAPP protocol trust.
RAPP artifacts use §§10/13 signatures, key succession, revocation, and the
signed registry.

## Storage Shim

Contained source may intercept
`from utils.azure_file_storage import AzureFileStorageManager` and use local
JSON under `.brainstem_data/`. That shim does not establish transparent cloud
migration or a shipped Tier 2.

## Environment

The immutable historical source read `.env`, but the retired target-owned
launchers neither create nor consume it:
- `GITHUB_TOKEN` — auto-detected from `gh` CLI if blank
- `GITHUB_MODEL` — default `gpt-4o`, switchable at runtime via `/models/set`
- `SOUL_PATH`, `AGENTS_PATH`, `PORT`, `VOICE_MODE`, `TWIN_MODE`

## Rapplications

Historical rapplication tooling collapsed multi-file source into singleton
artifacts. Those outputs and the legacy catalog are retained inventory, not a
current deployable or installable product. Current distribution acceptance
requires the complete RAPP/1 §9 `rapplication` variant checks.

## Tests

The current dependency-free core/static checks run with
`node tests/run-tests.mjs`. The former browser parity suite depended on a
removed `rapp.js` implementation and is retained only as non-executable
migration evidence under `tests/fixtures/legacy-conformance/`.
