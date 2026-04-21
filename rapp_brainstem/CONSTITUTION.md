# RAPP Brainstem — Constitution

> *The principles that govern this project. Read this before you contribute.*

---

## What This Is

RAPP Brainstem is a **business-focused AI agent platform** that teaches
the Microsoft AI stack through progressive tiers. It is an engine —
not a consumer product, not a toy, not a creature.

It exists to help developers, teams, and organizations build AI agents
that start local and scale to Azure and M365 Copilot Studio.

---

## Article I — The Engine, Not the Experience

RAPP Brainstem is infrastructure. It is the Flask server, the LLM loop,
the agent discovery, the auth chain, and the deployment templates.

It does not have a personality out of the box beyond what the user puts
in their soul file. It does not have a brand identity beyond "RAPP
Brainstem." It does not anthropomorphize itself.

Consumer-facing experiences (creatures, organisms, educational platforms,
children's content) are **separate intellectual property** and belong in
their own repositories. They may use the brainstem as their engine, but
they do not live here.

---

## Article II — Three Tiers, One Path

The platform teaches the Microsoft AI stack one layer at a time:

| Tier | Name | What It Is | What You Learn |
|------|------|-----------|----------------|
| 1 | **Brainstem** | Local Flask server + GitHub Copilot | Python agents, function-calling, prompt engineering |
| 2 | **Spinal Cord** | Azure deployment (ARM template) | Azure Functions, Azure OpenAI, managed identity, RBAC |
| 3 | **Nervous System** | Copilot Studio + M365 | Power Platform, declarative agents, Teams integration |

Each tier is self-contained and complete. Users advance when they choose
to, not when we push them.

---

## Article III — Local First

The brainstem runs on the user's machine. No cloud account required.
No API keys beyond a GitHub account with Copilot access.

Azure and Copilot Studio are deployment targets, not prerequisites. A
brainstem that never leaves localhost is fully functional.

All local data (memories, config, agents) stays on the user's device
unless they explicitly deploy to a higher tier.

---

## Article IV — One File, One Agent

Agents are single `*_agent.py` files that extend `BasicAgent` and
implement `perform()`. That's the entire contract.

- No config files. No YAML. No dependency manifests.
- Auto-discovered on startup. No registration step.
- The LLM decides when to call them based on the metadata description.
- Portable: copy the file, the skill travels with it.

Complexity belongs inside the agent's `perform()` method, not in the
framework around it. The surface area stays small so anyone can read,
write, and share agents.

---

## Article V — Don't Break the One-Liner

The install experience is sacred:

```bash
curl -fsSL https://kody-w.github.io/RAPP/install.sh | bash
```

```powershell
irm https://raw.githubusercontent.com/kody-w/RAPP/main/install.ps1 | iex
```

One command. Works on a fresh machine. Installs prerequisites, clones
the repo, sets up the venv, authenticates, and launches.

Any change to the repo must be tested against this path. If the
one-liner breaks, nothing else matters.

---

## Article VI — Scope Discipline

This repository contains:

- ✅ The brainstem server (`brainstem.py`)
- ✅ The default soul file (`soul.md`)
- ✅ The local storage shim (`local_storage.py`)
- ✅ Built-in agents (`agents/`)
- ✅ Azure deployment (`azuredeploy.json`, `deploy.sh`)
- ✅ Power Platform solution (`.zip`)
- ✅ Install scripts (`install.sh`, `install.ps1`, `install.cmd`)
- ✅ Landing page (`index.html`, `docs/`)

This repository does **not** contain:

- ❌ Consumer brand identities (creatures, mascots, organisms)
- ❌ Educational platforms (academies, courses, children's content)
- ❌ Background daemons or heartbeat loops
- ❌ Features that require processes beyond the Flask server
- ❌ Content belonging to other intellectual properties (e.g., openrappter)
- ❌ Hatched project code (function_app.py, utils/, etc. for Tier 2/3)

When in doubt: if it's not the engine or its deployment path, it
belongs somewhere else.

---

## Article VI-A — Brainstem Hatches, User Develops

The brainstem is the **bootstrapper**, not the workspace. When a user
asks the brainstem to create a new RAPP (Tier 2 Azure Functions or
Tier 3 Copilot Studio), the brainstem scaffolds a complete, self-contained
project in `~/.brainstem_data/hatched_rapps/` and then **gets out of the way**.

The hatched project contains everything the user needs: `function_app.py`,
`agents/`, `utils/`, deployment templates, and configuration files. Once
hatched, the user opens that project in VS Code and develops there.

Brainstem agents that support hatching (e.g., `hatch_rapp_agent.py`) are
**onboarding guides** — they scaffold, check status, and point the user to
their new workspace. They do not embed Tier 2/3 runtime code inside the
brainstem itself.

This separation ensures:
- The brainstem stays small and focused (Article I)
- Hatched projects are portable and independent
- Users own and control their hatched code (Article VII)
- The brainstem never becomes a monolith

---

## Article VII — The User Owns Their Instance

- The soul file is theirs to edit. We provide a default, not a mandate.
- The agents directory is theirs to fill. We provide examples, not a locked set.
- The `.env` file is theirs to configure. We provide defaults, not requirements.
- The code is readable because they should understand what's running on their machine.

We never phone home, collect telemetry, or require accounts beyond
GitHub. The user's brainstem is their brainstem.

---

## Article VIII — Bump the Version

Every commit that changes brainstem behavior — agents added or removed,
routes changed, installer logic updated, anything the user would notice
after re-running the one-liner — **must bump `rapp_brainstem/VERSION`**.

The installer compares local vs. remote VERSION to decide whether to
pull. If VERSION doesn't change, users are stuck on stale code no matter
how many commits land on main. The one-liner silently does nothing and
the user has no idea why their fix isn't there.

Patch bump (`0.8.7` → `0.8.8`) for fixes and small changes. Minor bump
for new features or breaking agent changes. The number itself doesn't
matter as much as the fact that it changed.

---

## Article IX — Swarms Are Directories, Not Routes

A **swarm** is local state: a directory containing `agents/`, a soul,
and a memory namespace. The brainstem runs against that state. It is
not a runtime abstraction, a routing layer, or a multi-tenant service.

> **A swarm is a directory. Changing swarm = changing which directory
> the brainstem reads. That is the whole concept.**

Concretely:

- Swarm operations (deploy, list, switch, invoke a sibling, seal,
  snapshot) are `*_agent.py` files that read and write state on disk.
  They are **not** classes in `brainstem.py`, REST routes, or
  middleware.
- Those agents must be **drop-in compatible with any brainstem.py** —
  including older versions in the wild. They use `BasicAgent` +
  stdlib + filesystem only. Copying them into a six-month-old
  brainstem must still work.
- The filesystem layout IS the contract. Two swarms with the same
  directory shape behave identically under the same brainstem.

### What this rules out

- ❌ A `SwarmStore` class or equivalent as a first-class object in
  `brainstem.py`.
- ❌ `/api/swarm/<guid>/...` routes or any new HTTP surface for swarm
  ops. Everything routes through `/chat` + an agent.
- ❌ Swarm-awareness baked into the brainstem core. If a swarm agent
  needs a new brainstem symbol to function, the design is wrong —
  redesign the agent.
- ❌ Runtime swarm state held in memory beyond a single request. Disk
  is authoritative; the brainstem is stateless between calls.

If you catch yourself designing a swarm-aware subsystem, stop and ask:
could this be a directory layout plus an agent? If yes, do that.

---

## Article X — Tier Parity Is a `/chat` Contract, Not a Transport

The brainstem-side of the agent portability guarantee (Article IV):
**`rapp_brainstem/brainstem.py` and `rapp_swarm/function_app.py` must
behave identically on the `/chat` *contract*.** The surface a caller
touches is the invariant; what sits below it can legitimately differ.

> **Same `/chat` contract. Same prompt split. Same agent contract.
> Same state layout. Transport differences below the contract are OK.**

What must be identical across tiers:

- Request envelope (`user_input`, `conversation_history`, `session_id`).
- Response envelope (`response`, `voice_response`, `twin_response`,
  `session_id`, `agent_logs`, `provider`, `model`).
- Tool-calling loop shape — call LLM → execute tool calls → loop,
  capped at a small number of rounds, with the same per-round logging.
- `|||VOICE|||` / `|||TWIN|||` split (and the twin sub-tags).
- Agent contract (`BasicAgent` + `perform()`, Article IV). Agents that
  run on Tier 1 must run unmodified on Tier 2.
- State layout (`.brainstem_data/` on Tier 1, `BRAINSTEM_HOME` on
  Tier 2; same directory shape inside).

What may legitimately differ:

- **Mount point for state.** Local disk vs. Azure Files.
- **LLM transport — by design.** Tier 1 stays Copilot-only with the
  `gh` CLI auth chain — one auth, one provider, one training story,
  zero-config install. Tier 2 is where the user picks an AI for their
  cloud deployment (Azure OpenAI / OpenAI / Anthropic / whatever the
  deploy target gives access to). Pushing to the RAPP cloud swarm is
  the moment the user declares *which AI runs there*. That decision
  lives on the cloud side because it's the cloud operator's
  constraint, not the learner's.

### What this rules out

- ❌ A Tier-2-only server stack that duplicates `brainstem.py`'s
  responsibilities with drift. If Tier 2 needs a capability, it
  lands in an agent or (for boot/loop/route concerns) in a shared
  vendored module.
- ❌ Routes that exist on one tier but not the other. `/chat` is the
  surface; both tiers expose it and route identically.
- ❌ Adding an LLM provider to Tier 1 that breaks the one-liner
  install. Default posture: don't — provider choice belongs on the
  cloud-deploy side where it already lives.
- ❌ "It works in Tier 1, we'll figure out Tier 2 later." Contract
  parity is asserted per-PR, not deferred.

---

## Article XI — The Root Stays Minimal; State Lives in `.brainstem_data/`

The `rapp_brainstem/` root is the engine surface — the first thing a
new user sees when they clone the repo. Every file at root competes
for their attention. A sprawling root signals complexity and pushes
adoption downhill.

> **Root = the engine. `.brainstem_data/` = the twin's home. Nothing
> in between.**

What belongs at root:

- `brainstem.py`, `soul.md`, `VERSION`, `requirements.txt`
- `start.sh` / `start.ps1` — the one-liner's launchers
- `README.md`, `CLAUDE.md`, `CONSTITUTION.md` — docs + governance
- `index.html` — landing page
- `agents/` — starter agents (flat files only; `experimental/`
  subdirectory for in-flight work)
- `utils/`, `web/` — cohesive support directories
- `local_storage.py`, `basic_agent.py` — the base contracts

What belongs in `.brainstem_data/`:

- Everything dynamic, user-generated, session-scoped, or
  state-carrying. Memory files, binder state, swarm directories,
  snapshots, per-user memory namespaces, twin calibration logs,
  saved sessions, active-swarm pointers, agent-group definitions.
- In short: **if it changes between runs, or belongs to this user's
  twin and not the engine itself, it lives in `.brainstem_data/`.**

### What this rules out

- ❌ Dropping `foo_agent.py`, `scratch.py`, or `admin_tool.py` at
  root. Agent files go in `agents/` (or `agents/experimental/`).
- ❌ Top-level JSON state files (`.swarms.json`, `.agent_groups.json`,
  `.binder.json`) next to `brainstem.py`. These are runtime state;
  they belong under `.brainstem_data/` and are gitignored.
- ❌ Adding a new top-level directory "because it doesn't fit
  anywhere else." If it doesn't fit anywhere else, it's probably
  state — put it in `.brainstem_data/`.
- ❌ Shipping default runtime state that pollutes `.brainstem_data/`
  on install. The user's twin starts empty; the engine seeds
  nothing.

### Why `.brainstem_data/`

The directory is the **context of the digital twin living**. It's the
twin's home on the user's device. Treating it as such — state
organized by purpose, not flat-bagged — lets us grow new capabilities
without ever touching the root. The engine stays small; the twin
grows inside its own directory.

---

## Article XII — Amendments

This constitution can be amended. The only rule: the change must serve
the platform's purpose as a business-focused AI agent engine. If it
blurs the line between engine and experience, it doesn't belong here.

---

*Ratified for RAPP Brainstem. The engine that powers what others build.*
