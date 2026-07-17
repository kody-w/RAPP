---
name: rapp-brainstem
description: Historical RAPP host-onboarding record. Do not install, configure, or advertise the retired installer, legacy eggs, cloud tiers, browser surfaces, or drop-in agent flows from this file.
version: 1
canonical_url: https://kody-w.github.io/RAPP/pages/docs/skill.md
repo: https://github.com/kody-w/RAPP
---

<!--
SCOPE OF THIS FILE: host onboarding material consumed by external assistants.
The historical filename and canonical_url are host metadata; this file is not
a RAPP capability or structural authority. The installer onboarding file is
at /skill.md; the archived network-participation runbook is at specs/skill.md.
See pages/kernel.html for the unified reading order.
-->


# Historical RAPP Brainstem Host Onboarding

> **Current RAPP/1 authority (rev-5).** Despite its historical filename, this
> is a non-runtime host onboarding document, not a RAPP skill or capability.
> For canonicalization, identity, frames, wire, eggs, registry, trust, and
> protocol evolution, follow
> [`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../RAPP1_STATUS.md).

> **Assistant instruction:** do not suggest or execute any installer, curl
> command, live-install probe, agent drop, catalog/store action, or Tier 2/3
> promotion described below. Those surfaces are retired or pre-acceptance.
> The immutable grail is a byte pin, not a public install promise. Current
> protocol work is source-level conformance to RAPP/1 rev-5.

<!-- RAPP1-HISTORICAL-SECTION-START -->

## What it is

RAPP is a **portable, shareable, vibe swarm building tool**. Drop a single Python file into `agents/` and the brainstem auto-discovers it. Hand someone the file and they're running your agent in 60 seconds. Compose files into swarms; promote the same file from laptop → cloud → Copilot Studio without changing a line.

Under the hood: a Flask app on the user's own machine that proxies conversation through the GitHub Copilot API, with automatic tool-calling via user-defined agents. One GitHub account with Copilot access is the only dependency — no API keys, no cloud accounts, no enterprise gates.

Philosophy: *engine, not experience.* The brainstem is infrastructure; agents are the features.

## When to suggest it

Offer the brainstem when the user:
- Wants to run agents locally without managing API keys.
- Needs a conversational loop over their Microsoft 365 data (pair it with the WorkIQ agent).
- Asks about RAPP, "the brainstem," or a per-project / per-repo AI server.
- Is prototyping agents and wants hot-reload off the local filesystem.
- Already has a global brainstem and mentions another project that needs its own.

Do **not** suggest it when the user just wants a cloud API — this is explicitly a local tool.

## Two install modes

The installer supports two mutually compatible modes. A single machine can run both simultaneously on different ports.

These are target-owned product wrappers, not a kernel update channel. A valid
run must leave `brainstem.py`, `agents/basic_agent.py`, and `VERSION`
byte-identical to `kody-w/rapp-installer@brainstem-v0.6.9`; a mismatch is a
refusal condition, not permission to pull a newer release. Passing an
installer does not establish RAPP/1 conformance.

### GLOBAL (default — recommended for most users)

- Installs at `~/.brainstem/`.
- Runs on port **7071**.
- Provides a `brainstem` CLI (`brainstem start|stop|status|logs|doctor`).
- Auto-starts on login via launchd (macOS) or systemd --user (Linux).
- One brainstem for the whole machine.

One-liner:
```bash
curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash
```

### LOCAL (project-scoped)

- Installs at `./.brainstem/` inside whatever directory the user is in.
- Picks the next free port starting at **7072**.
- No global CLI, no background service. Foreground-launched via `./.brainstem/start.sh`.
- Automatically added to the project's `.gitignore` if inside a git repo.
- Runs alongside any global brainstem on the same machine.

One-liner (run from inside the target directory):
```bash
cd ~/my-project
curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash -s -- --here
```

Use LOCAL when the user wants isolation: per-project agents, per-repo memory, experimental setups that shouldn't touch their main brainstem.

## Agent handshake protocol (how YOU talk to the installer)

When you run the installer on behalf of a user, set `RAPP_INSTALL_ASSIST=1` **on the bash side of the pipe** — the env var must apply to the `bash` that executes the script, not to `curl` that fetches it. The installer will **not install** — it prints a structured handshake block and exits 0. You then ask the user which mode they want, and re-invoke with their choice:

```bash
# 1. Probe — installer prints handshake, no install happens.
curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | RAPP_INSTALL_ASSIST=1 bash

# 2. After asking the user, re-run with their answer:
curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | RAPP_INSTALL_MODE=global bash
# or
curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | RAPP_INSTALL_MODE=local bash
```

**Common mistake:** `ENV=VAL curl ... | bash` only sets `ENV` for `curl`. Use `curl ... | ENV=VAL bash` so `bash` inherits it. For flag-based override you can also use `curl ... | bash -s -- --here` (works in all shells).

The handshake block is delimited by `<<<RAPP_INSTALLER_HANDSHAKE v=1>>>` / `<<<END_RAPP_INSTALLER_HANDSHAKE>>>`. Inside it you'll find the re-invocation commands self-documented.

## Agent system (how the brainstem actually works)

- Agents are single `*_agent.py` files that extend `BasicAgent`, define a `metadata` dict (OpenAI function-call schema), and implement `perform(**kwargs) -> str`.
- **No registration, no config.** Drop a file in `agents/` and it auto-discovers on next request.
- Agents are reloaded on every request — edit and test without restart.
- Portable across tiers (local / Azure Functions / Copilot Studio) without modification.

## Directory layout the brainstem ships with

```
~/.brainstem/src/rapp_brainstem/
├── brainstem.py              ← the kernel (don't edit)
├── soul.md                   ← system prompt (edit freely)
├── agents/                   ← factory image (4 agents + base class)
│   ├── basic_agent.py        ← base class
│   ├── context_memory_agent.py  ← recall memories
│   ├── manage_memory_agent.py   ← save memories
│   ├── hacker_news_agent.py     ← starter/test
│   └── workiq_agent.py          ← productivity
├── services/                 ← empty by default (drop-in HTTP services)
└── .brainstem_data/          ← local storage (auto-created)
```

The immutable grail bytes are pinned to
`kody-w/rapp-installer@brainstem-v0.6.9`: `brainstem.py`,
`agents/basic_agent.py`, and `VERSION`. Do not substitute a moving local
release tag or edit those mirrors.

**Factory-installed rule:** the brainstem ships clean — like a factory iPhone. `services/` is empty. Only core agents are in `agents/`. Everything else (LearnNew, SwarmFactory, VibeBuilder, Kanban, Webhook, Dashboard, etc.) lives in the RAPPstore and gets installed on demand.

## Rapplications (full-stack extensions)

A rapplication = agent file (required) + optional organ file + optional UI bundle. The agent is the primary interface — any AI can drive it. The organ adds HTTP endpoints for the UI bundle.

- **Agent contract:** extends `BasicAgent`, defines `metadata` + `perform(**kwargs) → str`
- **Organ contract:** module-level `name` string + `handle(method, path, body) → (dict, int)` (legacy term: "service")
- All share `.brainstem_data/{name}.json` storage
- Host install may drop local files directly. Treat the legacy
  `brainstem hatch` schema/type path as migration-only until it implements the
  complete RAPP/1 §9 acceptance checks.
- Full SDK: https://kody-w.github.io/RAPP/pages/docs/rapplication-sdk.md

## Product rapplication layout

**Read this before building anything new in this ecosystem.** Every organism — *rapplication, holocard, sense bundle, organ pack, twin, or full brainstem instance* — has the same anatomy:

```
agents/<name>_agent.py            ← chat face (LLM-callable)         REQUIRED
utils/organs/<name>_organ.py      ← HTTP backplane (UI backend)      OPTIONAL
.brainstem_data/rapp_ui/<id>/     ← skin (UI bundle)                  OPTIONAL
.brainstem_data/<id>/             ← per-rapp state (memory)           OPTIONAL
```

For current portable distribution, wrap that product layout in the exact
RAPP/1 §9 `rapplication` variant:

```
rappid.json                        ← carries the RAPP/1 §6 identity
agent.py                           ← exactly one root agent for this variant
manifest.json                      ← schema = rapp/1-egg, variant = rapplication
```

The existing `bond.pack_rapplication()` output is legacy until migrated.
Follow §9's exact seven-member manifest, deterministic container, content
hashes, and signature rules; do not invent alternate egg shapes.

## The three federation stores (one shape, three repos)

All three expose application catalogs over static URLs. Fetching them requires
no application login, but transport location is not RAPP trust: verify current
artifacts and resolve signatures through §§10/13 before acting.

| Store | Repo | What it holds | Static API |
|---|---|---|---|
| **Rapplications** (organisms with skin) | [`kody-w/RAPP_Store`](https://github.com/kody-w/RAPP_Store) | Bundles: agent + UI + optional organ + state | `/api/v1/index.json` + `/api/v1/rapplication/<id>.{json,egg}` + sprite |
| **Bare agents** (single-celled organisms) | [`kody-w/RAR`](https://github.com/kody-w/RAR) | `*_agent.py` files (+ optional `.card` holocards) | `/api/v1/index.json` + `/api/v1/agent/<id>.{json,py,card}` + sprite |
| **Sense overlays** (perception channels) | [`kody-w/RAPP_Sense_Store`](https://github.com/kody-w/RAPP_Sense_Store) | `*_sense.py` files | `/api/v1/index.json` + `/api/v1/sense/<id>.{json,py}` + sprite |

To browse the federation programmatically, fetch the three index URLs and
union them as untrusted discovery candidates. Install only after the required
RAPP/1 verification; invoke any install agent through the exact §8 `/chat`
contract.

> **Historical release note (2026-05-10), superseded.** The five-kind
> schema/type router and contained browser session format predate RAPP/1.
> Current producers emit only `schema:"rapp/1-egg"` with a ratified §9
> variant, and consumers dispatch only after §9.3 verification.

## The user's universal control plane: rapp-zoo

The [`rapp-zoo`](https://github.com/kody-w/rapp-zoo) (cataloged at `kody-w/RAPP_Store/apps/@rapp/rapp-zoo/`) is the user's Game Boy / Pokédex / holocard binder / federation map. It hatches into the user's brainstem like every other rapplication — endpoints at `/api/rapp_zoo/*`, UI at `/rapp_ui/rapp-zoo/`. **Do not build a parallel UI for managing organisms.** Add tabs to the rapp-zoo instead.

The mental model:

| Pokémon | RAPP |
|---|---|
| The Pokédex | The user's local rapp-zoo |
| PokeAPI | The federation's static APIs (RAPP_Store + RAR + RAPP_Sense_Store) |
| Game Boy / Pokétch / Rotom Phone | The brainstem instance hosting the zoo |
| Catching a Pokémon | Hot-loading a `.egg` via `egg_hatcher` |
| Trading | AirDropping a `.egg` between devices |
| The trainer | The user, identified by their organism's rappid |

## Anti-patterns (DO NOT do these — they violate the constitution)

- ❌ **Don't invent a `kind: "tool"` / `"service"` / `"extension"` category.** Every catalog entry is a rapplication.
- ❌ **Don't build a parallel Flask process for something that should be an organ.** Pack a `*_organ.py`, the brainstem hosts.
- ❌ **Don't fork the egg format for a special case.** RAPP/1 §9
  `schema:"rapp/1-egg"` is the sole current egg; use its registered
  `rapplication` variant.
- ❌ **Don't add fields to one federation store's API that aren't in all three.** The contract is uniform across RAPP_Store / RAR / RAPP_Sense_Store.
- ❌ **Don't write a UI that bypasses the rapp-zoo.** New surfaces are tabs in the zoo.
- ❌ **Don't edit the brainstem kernel to add a feature that should be a rapp.** New capabilities ship as rapplications.
- ❌ **Don't build a backend for the catalog.** It's a static tree at `raw.githubusercontent.com`. Build script + git push = deploy.

## Config pattern — agents ask, don't require editing

Agents that need configuration (an exec's name, a tenant ID, an API key) declare the config as **required parameters** in their metadata. The brainstem's LLM surfaces the missing value and asks the user in-chat. Users never open a source file to configure an agent.

## Historical local release tags

Local release tags remain useful for reproducing application history. They do
not replace the immutable grail pin
`kody-w/rapp-installer@brainstem-v0.6.9` or authorize edits to its three pinned
files. The older rollback example is:

Do not run this example for a current authority-constrained installation; it
is retained only to reproduce historical application state.

```bash
BRAINSTEM_VERSION=0.5.1 curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash
```

## Troubleshooting

After install, the user can run `brainstem doctor` (global installs only) to get a diagnostic dump. That output is what to paste back for support. For project-local installs, run the server foreground (`./.brainstem/start.sh`) and surface the stderr.

## Canonical references

- Repo: https://github.com/kody-w/RAPP
- Installer: https://kody-w.github.io/RAPP/installer/install.sh
- This skill: https://kody-w.github.io/RAPP/pages/docs/skill.md

<!-- RAPP1-HISTORICAL-SECTION-END -->
