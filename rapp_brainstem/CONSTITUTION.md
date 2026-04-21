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

## Article X — Tier Parity Is a `/chat` Contract

The brainstem-side of the agent portability guarantee (Article IV):
**`rapp_brainstem/brainstem.py` and `rapp_swarm/function_app.py` must
behave identically on `/chat`.** The difference between tiers is where
state is mounted, not what the code does.

> **Same `/chat` loop. Same prompt split. Same agent contract. Same
> state layout. Different mount point for the state root.**

- Tier 1 mounts state on local disk (`~/.brainstem_data/` or
  `BRAINSTEM_HOME`).
- Tier 2 mounts state on Azure Files at `BRAINSTEM_HOME`.
- Tier 3 wraps the same `/chat` behind Copilot Studio.
- The tool-calling loop, provider dispatch, slot split, and agent
  discovery are byte-for-byte the same code path — enforced by
  vendoring from one source of truth, not by maintaining parallel
  implementations.

### What this rules out

- ❌ A Tier-2-only server stack that duplicates `brainstem.py`'s
  responsibilities with drift. If Tier 2 needs a capability, the
  capability lands in `brainstem.py` (or an agent) and Tier 2 vendors
  it.
- ❌ A Tier-1-only LLM provider path that Tier 2 has to re-implement.
  Provider dispatch is shared.
- ❌ Routes that exist on one tier but not the other. `/chat` is the
  surface; both tiers expose it and route identically.
- ❌ "It works in Tier 1, we'll figure out Tier 2 later." Tier parity
  is asserted per-PR, not deferred.

---

## Article XI — Amendments

This constitution can be amended. The only rule: the change must serve
the platform's purpose as a business-focused AI agent engine. If it
blurs the line between engine and experience, it doesn't belong here.

---

*Ratified for RAPP Brainstem. The engine that powers what others build.*
