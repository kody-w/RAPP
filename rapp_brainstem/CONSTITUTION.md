# RAPP Brainstem — Constitution

> *The principles that govern this project. Read this before you contribute.*

---

## What This Is

RAPP Brainstem is a **portable, shareable, vibe swarm building tool**.
A single-file agent travels — drop it in, AirDrop it out, promote it
across tiers without rewriting it. The brainstem is the engine that
makes that travel possible: a local Flask server that runs single-file
Python agents, with an upgrade path through Azure and Copilot Studio.

It is an engine — not a consumer product, not a toy, not a creature.
It exists to help developers, teams, and organizations build AI agents
that start local and scale to Azure and M365 Copilot Studio.

---

## Article I — The Engine, Not the Experience

RAPP Brainstem is the engine behind a portable, shareable, vibe swarm
building tool. The vibe lives in the agents the user writes; the
engine stays infrastructure. It is the Flask server, the LLM loop,
the agent discovery, the auth chain, and the deployment templates.

It does not have a personality out of the box beyond what the user puts
in their soul file. It does not have a brand identity beyond "RAPP
Brainstem." It does not anthropomorphize itself.

Consumer-facing experiences (creatures, organisms, educational platforms,
children's content) are **separate intellectual property** and belong in
their own repositories. They may use the brainstem as their engine, but
they do not live here.

---

## Article I-A — `brainstem.py` Is Sacred

`rapp_brainstem/brainstem.py` is the stateless "thought" engine. One
file: Flask server, auth chain, soul loader, agent discovery, tool-
calling loop, LLM proxy, diagnostics. It stays one file and it stays
small.

> **Add capability by writing an agent or a service. Not by editing `brainstem.py`.**

### The fixed contract surface

Changes to anything in this list are **SPEC-level**: bump VERSION, tag
it (Article VIII), verify Tier 2 parity (Article X), document what
changed in the tag annotation.

- `POST /chat` — the single invocation surface. Request envelope
  (`user_input`, `conversation_history`, `session_id`) and response
  envelope (`response`, `voice_response?`, `session_id`, `agent_logs`)
  are frozen. New output slots arrive as delimiters, never as new keys.
- `GET /health` — status, model, agents, auth state.
- Auth chain — `GITHUB_TOKEN` → `.copilot_token` (device-code OAuth)
  → `gh auth token`. No other provider on Tier 1 (Article X).
- Agent discovery — `agents/*_agent.py`, reloaded from disk every
  request. Recursion rules per Article XII.
- Service discovery — `services/*_service.py`, reloaded every
  request. Each service exposes `name` (str) and
  `handle(method, path, body) → (dict, status_code)`. Dispatched
  via `GET|POST|PUT|DELETE /api/<name>/<path>`. Services provide
  HTTP endpoints (UI backends, CRUD APIs) without LLM visibility.
  Agents handle LLM tool calls; services handle HTTP — they never
  overlap.
- Storage shim — `utils.azure_file_storage` intercepted via
  `sys.modules` to `local_storage.py` under `.brainstem_data/`.
- Flight recorder — `_tlog()` + `.brainstem_book.json`.
- Tool-calling loop — up to 3 rounds, identical shape each round.
- Output delimiters — `|||VOICE|||`, `|||TWIN|||` (SPEC.md §3).

### The only legitimate reasons to edit this file

1. A bug fix in existing behavior (same contract, same routes, same
   envelopes — just fixed).
2. Adding a new top-level output-slot delimiter (e.g., the next
   `|||VOICE|||`-shaped slot). This is a SPEC change with version bump.

Everything else belongs in an agent, a service, in `utils/`, or in
a hatched project.

### What this rules out

- ❌ **New features in `brainstem.py`.** Features are `*_agent.py`
  files. The brainstem does not grow capability.
- ❌ **"Small helpers" added inline.** Shared helpers go in `utils/`;
  agent-specific helpers live inside the agent.
- ❌ **New HTTP routes in `brainstem.py`.** If the LLM could route
  to it via `/chat`, it's an agent. If the UI needs a REST endpoint,
  it's a service (`services/*_service.py`). Either way, not a route
  in the kernel.
- ❌ **Framework abstractions beyond `BasicAgent` + `perform()` and
  service `handle()`.** No lifecycle hooks, middleware, plugin layers,
  agent base class variants.
- ❌ **Silent contract changes** — renaming routes, reshaping the
  response envelope, reordering the tool loop, changing log shape.
  These are SPEC breaks (see Article VIII).
- ❌ **Provider-specific code paths beyond the GitHub Copilot chain.**
  Tier 1 is Copilot-only by design (Article X); other providers live
  on Tier 2's side of the contract.
- ❌ **In-process state that persists across requests.** Disk is
  authoritative; the brainstem is stateless. The short-lived Copilot
  token cache is the single permitted exception and must degrade
  gracefully when absent.
- ❌ **Swarm, tenancy, or routing logic in `brainstem.py`.** Swarms
  are directories (Article IX). Any swarm-aware code is an agent.
- ❌ **UI logic beyond serving `index.html`.** The UI is a view onto
  `agents/` (Article XIII); its behavior lives in the page and in
  agents, not in the server.

### The test before any edit

1. Is this a bug fix in existing behavior, or am I adding something?
2. If adding — can it be an agent? (The answer is almost always yes.)
3. If it touches the contract surface — have I bumped VERSION and
   verified Tier 2 parity?

If the change does not survive these three questions, it does not
belong in this file.

### Why

Every agent in the ecosystem — starter, workspace, hatched,
third-party, and ones written six months from now — depends on this
file's contract being the same tomorrow as it is today. Drift here is
the one change that breaks *everyone's* agents at once. The file is
sacred because portability (Article IV) is sacred.

---

## Article II — Three Tiers, One Model

Three deployment shapes, **one model underneath**. Every tier runs
the same `BasicAgent` contract, discovers files in `agents/`, and
serves the same `/chat` envelope shape. What changes per tier is
**the LLM provider**, **how memory is scoped**, and **how identity
arrives**.

| Tier | LLM Provider | Memory Scope | Identity Source |
|------|--------------|--------------|-----------------|
| 1 — **Local Brainstem** | GitHub Copilot (`gh` CLI) | Single-user, flat | Implicit |
| 2 — **Cloud Brainstem** | Azure OpenAI (`azuredeploy.json`) | Per-user by guid | `user_guid` body field |
| 3 — **Copilot Studio** | Inherits Tier 2 | Per-user by guid | AAD `oid` → `user_guid` via Power Automate |

### The Tier 2 multi-tenancy model

**One deployment, many users, shared agents, personal memory.** All
users share the same `agents/` tree (vendored at deploy or served
from Azure File Storage). Each user has their own memory namespace,
routed per request by the adapter:

```python
storage_manager.set_memory_context(user_guid)
```

One brainstem that remembers you. Not one brainstem per user.

### How Tier 3 drives it

The shipping Power Automate flow (`Workflows/TalktoRAPPAI-*.json` in
the MCS solution zip) calls **Office 365 Users → Get my profile
(V2)** with `runtimeSource: "invoker"`. The signed-in user's AAD
object ID (`body/id`) becomes the `user_guid` in the POST body to
Tier 2. Auth to the function is the shared `x-functions-key`;
identity is enforced by Power Automate's invoker-scoped connection.
One MCS connector, one Tier 2, N users — zero per-user MCS
configuration.

### Canonical Tier 2 / Tier 3 wire

```json
// Request
{ "user_input": "...", "conversation_history": [...], "user_guid": "<AAD oid>" }

// Response
{ "assistant_response": "...", "voice_response": "...", "agent_logs": "...", "user_guid": "..." }
```

### The `function_app.py` adapter seam

`rapp_swarm/function_app.py` is the one place that knows about MCS.
It translates the brainstem-shape envelope (`response` /
`voice_response`) to the Power Automate consumer shape
(`assistant_response` + echoed `user_guid`). Translation stays here,
never in `brainstem.py` (Article I-A).

### What is identical across tiers

- The `/chat` envelope shape at the consumer seam (Article X).
- The agent contract (`BasicAgent` + `perform()`, Article IV).
- Tool-calling loop **shape**: call LLM → execute tools → loop,
  capped at a small number of rounds.
- The workshop → singleton path (Article IX).

### What legitimately differs per tier

- **LLM provider.** Tier 1 = GitHub Copilot. Tier 2/3 = Azure
  OpenAI, required by `azuredeploy.json` — a cloud Function App
  cannot run the `gh` CLI auth chain. The provider is the cloud
  operator's constraint, not the learner's (Article X).
- **Tool-calling implementation.** Tier 2's `function_app.py` has
  its own `Assistant` class adapted for the Azure OpenAI SDK (tools
  vs. functions API, TTL-cached clients, Result-typed errors). The
  *shape* matches `brainstem.py`'s loop; the *code* does not. This
  is by design — provider-native implementations are allowed at
  Tier 2; envelope parity is what ties them together. The brainstem
  is the **gateway** for the teaching surface; the cloud requires a
  different engine to hit Azure OpenAI through `azuredeploy.json`.
- **Memory scope mechanism.** Tier 1 scopes via
  `BRAINSTEM_MEMORY_PATH` env var (Article XI). Tier 2 scopes via
  `storage_manager.set_memory_context(user_guid)` — same outcome,
  different mechanism fitted to Azure Files.

### What this rules out

- ❌ **Per-user Tier 2 deployments.** One deployment, N guids. No
  `hatch_rapp_agent`, no per-user `function_app.py`, no per-user
  ARM deployment. Stronger isolation means a second Tier 2 in a
  separate Azure subscription, not a scaffold-per-tenant.
- ❌ **Per-user Copilot Studio solutions.** One MCS connector, one
  Tier 2, N users via guid-from-identity.
- ❌ **Porting the Tier 1 Copilot API path into Tier 2.** Cloud
  deployments need Azure OpenAI. `brainstem.py` stays local.
- ❌ **Porting the Tier 2 Azure OpenAI path into Tier 1.** Local
  works with a GitHub account alone — that's the one-liner pitch
  (Article V).
- ❌ **Renaming brainstem envelope fields to match an MCS consumer.**
  `assistant_response`, `output`, `output_1` are Power Automate's
  field names. Translation happens in `function_app.py`, never in
  `brainstem.py`. The next person who "fixes" the mismatch by
  renaming `response` → `assistant_response` in Tier 1 breaks both
  Tier 1 and Article I-A in one commit.

### Why

Tier 1 is the teaching surface — local, Copilot-auth, zero-config.
Tier 2 is the cloud surface — Azure OpenAI, guid-scoped memory, one
deployment for many users. Tier 3 is the M365 surface — Power
Automate carries the user's identity in. **Brainstem is the gateway;
the cloud is where the real multi-tenant serving happens.** Keeping
the implementations intentionally separate but the envelope
identical is what lets an agent written on a laptop serve many users
in Teams without a rewrite.

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

## Article IV-A — Config Is A Param, Not A Source Edit

Users never edit agent source to configure an agent. If an agent needs
a name, a path, a token, a preference — it goes in the agent's
OpenAI-function `parameters` schema and is listed in `required`.

- Required config → `"required": [...]`. The brainstem's tool-calling
  loop surfaces the missing value and the LLM asks the user in-chat.
- Never ship an agent with `_CONFIG = "EDIT_ME_BEFORE_USING"`. That
  pushes setup work onto the user that belongs inside the agent.
- Durable preferences (my name, my role, my tenant) live in the
  user's memory (`save_memory` / `recall_memory`) so the LLM has them
  in context on future turns. Not in a hidden file the user has to find.

Consequence: agent files are read-only from the user's perspective.
They can move agents between tiers (Article II), share them across
instances, or swap them without opening an editor. The agent does
the work the user does not.

---

## Article V — Don't Break the One-Liner

The install experience is sacred:

```bash
curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash
```

```powershell
irm https://raw.githubusercontent.com/kody-w/RAPP/main/installer/install.ps1 | iex
```

One command. Works on a fresh machine. Installs prerequisites, clones
the repo, sets up the venv, authenticates, and launches.

Any change to the repo must be tested against this path. If the
one-liner breaks, nothing else matters.

---

## Article V-A — Two-Mode Install, Agent-Aware Handshake

The one-liner defaults to a **global** install at `~/.brainstem` (port
7071, background service, global `brainstem` CLI). A second mode —
**project-local** — installs into `./.brainstem/` in the current
directory on a free port ≥ 7072, with no global CLI or service, and
auto-gitignored. Both modes can coexist on one machine and talk to
each other as agents.

```bash
# Global (unchanged, default):
curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash

# Project-local (from inside the target repo):
curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash -s -- --here
```

### The agent handshake

When an agent (Copilot CLI, Claude Code, any LLM shelling out) runs
the installer, it sets `RAPP_INSTALL_ASSIST=1` **on the bash side of
the pipe** (`curl ... | RAPP_INSTALL_ASSIST=1 bash`) — the env must
apply to `bash`, not to `curl`. The installer does **not install** —
it prints a structured block delimited by
`<<<RAPP_INSTALLER_HANDSHAKE v=1>>>` / `<<<END_...>>>` containing:

1. A pointer to `skill.md` (canonical learnable manifest).
2. The global-vs-local question for the user.
3. Self-documented re-invocation commands:
   `curl ... | RAPP_INSTALL_MODE=global bash` or `=local`.
4. A heuristic the agent can apply without reasoning from scratch.

The agent asks the user, then re-invokes with the chosen mode. The
human one-liner experience is unaffected.

### `skill.md` is the canonical manifest

The repo root ships `skill.md` — a single markdown file with YAML
frontmatter (`name`, `description`, `version`, `canonical_url`)
describing what RAPP is, when to suggest it, both install modes, the
handshake protocol, and the agent-system architecture. Any agent
fetching `https://kody-w.github.io/RAPP/skill.md` learns enough to be
useful without ever running the installer first.

### What this rules out

- ❌ Requiring flag knowledge from humans. A direct user typing
  `curl ... | bash` never encounters the handshake or needs to know
  `--here` exists; global-default is silent.
- ❌ A separate "project install" URL. There is one installer, one
  URL, one convention — mode is picked via flag or env var.
- ❌ Agent-specific code paths in `install.sh` (e.g., "if
  `$COPILOT_CLI`…"). The handshake is triggered by a single generic
  env var (`RAPP_INSTALL_ASSIST`) any agent can set.
- ❌ `skill.md` drift. The file is canonical; the installer's
  handshake points at it rather than duplicating its content.

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

## Article VII — The User Owns Their Instance

- The soul file is theirs to edit. We provide a default, not a mandate.
- The agents directory is theirs to fill. We provide examples, not a locked set.
- The `.env` file is theirs to configure. We provide defaults, not requirements.
- The code is readable because they should understand what's running on their machine.

We never phone home, collect telemetry, or require accounts beyond
GitHub. The user's brainstem is their brainstem.

---

## Article VIII — Versions Are Load-Bearing Rollback Points

Every commit that changes brainstem behavior — agents added or removed,
routes changed, installer logic updated, anything the user would notice
after re-running the one-liner — **must bump `rapp_brainstem/VERSION`**.

> **Every released VERSION is also a git tag `brainstem-vX.Y.Z`. Tags
> are immutable — they are the rollback contract with users.**

### The rollback contract

When a release breaks a user's install, they must be able to fall back
to a prior working version with a single command:

```bash
BRAINSTEM_VERSION=0.9.0 curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash
```

The installer honors `BRAINSTEM_VERSION` by checking out the
`brainstem-v<VERSION>` tag and hard-resetting the local tree to it. A
user who can't update and a user who must downgrade both have the
same escape hatch: pin to a known-good version.

This only works if **every released VERSION has a matching tag**, and
**tags never move**. Both are sacred.

### Release discipline

- **Bump + tag together.** The commit that bumps `VERSION` to `X.Y.Z`
  is the one that gets tagged `brainstem-vX.Y.Z` — ideally the merge
  commit on main. No version bump without the matching tag push.
- **Tags are immutable.** Never `git tag -f` or `git push --force` a
  brainstem-v tag. A user who pinned to `0.9.0` six months ago must
  get the same tree today.
- **Don't skip versions.** `0.9.0` → `0.10.0` is fine. `0.9.0` →
  `0.11.0` when `0.10.0` was never tagged creates a gap in the
  rollback path.
- **No "republish" of an older version.** If `0.9.0` was bad and you
  need to ship a fix, that's `0.9.1` (new tag, new point). The old
  bad tag stays so users who already pinned to it aren't surprised
  by a silent change.
- **VERSIONS.md (or the tag annotation) records what changed.** The
  `git show brainstem-vX.Y.Z` message is the user's release-note.

### What this rules out

- ❌ Untagged releases. A VERSION bump without the corresponding tag
  pushed to origin is incomplete — users can't pin to it, can't roll
  back from it.
- ❌ Moving or deleting a published tag. Tags are the rollback
  contract; rewriting them breaks every user who pinned to them.
- ❌ Installer logic that relies on main alone. The installer MUST
  support `BRAINSTEM_VERSION` and MUST fall back gracefully if a tag
  doesn't exist (with a clear warning).
- ❌ Silent behavior changes between tags. If a release changes what
  a prior release did — agent contract, route surface, response
  envelope — that's a VERSION bump, not a patch.

Patch bump (`0.9.5` → `0.9.6`) for fixes. Minor bump (`0.9.6` →
`0.10.0`) for new features or breaking agent changes. Major bump for
SPEC-breaking changes — which should basically never happen (see
Article III.3: the agent contract is sacred).

---

## Article IX — A Swarm Is a Workshop; Distribution Is a Singleton

A **swarm** has two shapes and only two:

1. **Workshop** — a folder of `*_agent.py` files under
   `agents/workspace_agents/<my_swarm>/`. You edit N files and iterate
   against the hotload loop (Article XII). This is the dev surface.
2. **Singleton** — one `*_agent.py` file. `swarm_factory_agent`
   converges a workshop into one file with all capabilities inlined.
   That file is the unit of distribution — drop it into another user's
   `agents/`, vendor it into Tier 2, attach it to an email. Same
   hotload loop receives it.

> **Workshop = N files. Distribution = 1 file. Same hotload loop on
> both ends. No runtime swarm abstraction in between.**

Concretely:

- The only swarm agent on the lesson path is **`swarm_factory_agent`**
  (converges workshop → singleton, or pulls a published singleton
  from the RAPP Store into `agents/`).
- A singleton's behavior at runtime happens inside its `perform()` —
  same contract as every other agent.
- The filesystem layout IS the contract. A singleton that runs under
  one brainstem at a given VERSION runs under any brainstem at that
  VERSION.

### What this rules out

- ❌ A `SwarmStore` class or equivalent as a first-class object in
  `brainstem.py`.
- ❌ `/api/swarm/<guid>/...` routes or any new HTTP surface for swarm
  ops. Everything routes through `/chat` + an agent.
- ❌ **A second runtime destination for swarms.** `~/.brainstem/swarms/<guid>/`
  is not an active location the brainstem reaches into. Once a swarm
  is converged, it's a file in `agents/` like every other agent.
- ❌ **Sibling-swarm invocation** via in-process import or recursive
  `/chat`. Two swarms that want to compose either share the workshop
  or both land as singletons in the same `agents/` tree. A
  `swarm_invoke_agent`, `swarm_deploy_agent`, `swarm_list_agent`,
  `swarm_info_agent`, `swarm_seal_agent`, `swarm_snapshot_agent`, or
  `swarm_delete_agent` is the wrong shape — those were retired
  precisely because they invent a runtime destination the simple
  model does not need.
- ❌ Swarm-awareness baked into the brainstem core. If a swarm agent
  needs a new brainstem symbol to function, the design is wrong —
  redesign the agent.
- ❌ Runtime swarm state held in memory beyond a single request. Disk
  is authoritative; the brainstem is stateless between calls.

If you catch yourself designing a swarm-aware subsystem, stop and ask:
could this be either a folder under `workspace_agents/` (during dev)
or a single `*_agent.py` file (for distribution)? The answer is always
one of those two.

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

## Article XI — The Root Is the Engine's Public Surface; the Brainstem's Workspace Is Separate

The root of `rapp_brainstem/` is the first thing a new user sees when
they clone the repo. Every file there competes for their attention.
A sprawling root signals complexity and pushes adoption downhill.

Two surfaces, two masters:

> **`agents/` + root = the engine's public surface (what we ship
> to the user). The brainstem's workspace = where the brainstem
> dumps scratch while working for the user. Don't collapse them.**

### What belongs at root (the engine's surface)

- `brainstem.py`, `soul.md`, `VERSION`, `requirements.txt`
- `start.sh` / `start.ps1` — the one-liner's launchers
- `README.md`, `CLAUDE.md`, `CONSTITUTION.md` — docs + governance
- `index.html` — landing page
- **`agents/`** — starter agents. Load-bearing for the training
  story: users clone the repo, open `agents/`, and see what a RAPP
  agent looks like. Drag-and-drop visible, editable, the reference
  implementation. **Do not move this into the brainstem workspace**
  — it would bury what the user is meant to learn from.
- `utils/`, `web/` — cohesive support directories (`utils/` holds
  `llm.py`, `twin.py`, `local_storage.py`, `_basic_agent_shim.py`,
  `index_card.py`). `agents/basic_agent.py` is the base class.

### What belongs in the brainstem's workspace (scratch while running)

Everything **written by the brainstem as it serves the user** — as
opposed to edited by the user or shipped by the engine:

- Per-user memory files, binder state, twin calibration logs.
- Session logs, telemetry, saved conversation state.

Pathing follows the memory-agent pattern — the same shape the memory
agents have used since day one. One env var overrides, one simple
home-relative default, no cwd heuristics:

```python
def _memory_path():
    p = os.environ.get("BRAINSTEM_MEMORY_PATH")
    return p if p else os.path.expanduser("~/.brainstem/memory.json")
```

Category conventions today:

- `~/.brainstem/memory.json` — `BRAINSTEM_MEMORY_PATH` override.
- `~/.brainstem/swarms/<guid>/…` — `BRAINSTEM_SWARMS_PATH` override.
- New categories get the same shape: one env var, one home-relative
  default. Tier 2 sets the env var to an Azure Files mount so the
  same agents serve isolated tenants without modification.

### What this rules out

- ❌ Dropping `foo_agent.py`, `scratch.py`, or `admin_tool.py` at
  root. Agent files go in `agents/` (or `agents/experimental/`).
- ❌ Top-level JSON state files (`.swarms.json`, `.agent_groups.json`,
  `.binder.json`) next to `brainstem.py`. These are runtime state;
  they belong in the brainstem's workspace and are gitignored.
- ❌ Moving `agents/` out of root. It is the training surface.
- ❌ Adding a new top-level directory "because it doesn't fit
  anywhere else." Give it a workspace category instead.
- ❌ Seeding default runtime state on install. The user's twin
  starts empty; the engine seeds nothing into the workspace.
- ❌ Three-tier cwd/home/env fallbacks for path resolution. Match
  the memory-agent pattern: one env var, one default.

### Why two surfaces

The engine's root is the curriculum. New users read it, understand
what the platform is, and copy-paste agents to learn. The brainstem's
workspace is the operator's reality — memory, state, deployed swarms,
sessions. Keeping them separate means the workspace can grow
indefinitely without ever obscuring the learning path.

---

## Article XII — `agents/` IS the User's Workspace

`agents/` is **the user's entire operational workspace** for setting up
and managing their brainstem. To add a capability, organize a swarm,
turn something off — all of it happens inside `agents/`. Engine files
(`brainstem.py`, `VERSION`, `soul.md`, `requirements.txt`, install
scripts) are a stable black box users never edit.

> **Engine files are for the engine. `agents/` is for the user.
> Everything functional a user needs to do happens in `agents/`.**

### Two surfaces: the showroom and the shop

`agents/` has exactly two structural layers, and both are sacred.

**1. `agents/` top level — the showroom.** Only the canonical
ship-in-repo starter agents live here. A new user opens `agents/` and
sees a small, clean set of example `*_agent.py` files — the shape of
what a RAPP agent is. Nothing else. No subdirectories except the one
named `workspace_agents/`.

**2. `agents/workspace_agents/` — the shop.** Everything organizational
lives under here: engine infrastructure, hand-load experiments,
disabled agents, personal/local-only agents, project-scoped folders,
user groupings. This is where the tree grows.

```
agents/
├── basic_agent.py              ← starter set (showroom)
├── hacker_news_agent.py
├── learn_new_agent.py
├── recall_memory_agent.py
├── save_memory_agent.py
├── workiq_agent.py             ← M365 faucet (curriculum extra)
└── workspace_agents/           ← everything else (shop)
    ├── swarm_factory_agent.py  ← the one ship-in-repo swarm tool
    ├── experimental_agents/    ← reserved: hand-load only
    ├── disabled_agents/        ← reserved: turned off
    ├── local_agents/           ← reserved: gitignored, personal
    └── <any user folder>/      ← user groupings, projects, swarms
```

A newcomer isn't overwhelmed. An operator has unlimited room.

### A recursive tree inside `workspace_agents/`

Inside `workspace_agents/`, the tree recurses with no depth limit.
Drop a `*_agent.py` file anywhere and the brainstem finds it —
`workspace_agents/sales_stack/q4/prospects/outbound_agent.py`
auto-loads just like a top-level starter agent.

Two subdirectory names are reserved by name-match at any depth and
**never** auto-load:
**`experimental_agents/`** (in-flight, hand-load only) and
**`disabled_agents/`** (move a file there to turn it off). Everything
else loads.

### Starter set at the top level of `agents/`

- `basic_agent.py` — base class.
- `hacker_news_agent.py`, `learn_new_agent.py`,
  `save_memory_agent.py`, `recall_memory_agent.py` — curriculum.

Ship-in-repo general-purpose agents may be added here sparingly when
they're broadly useful (e.g. `workiq_agent.py` as the Microsoft 365
faucet). Keep the set small enough that a newcomer can scan it in
seconds.

### Engine-shipped agent under `workspace_agents/`

- `workspace_agents/swarm_factory_agent.py` — the one ship-in-repo
  swarm tool (converges a workshop into a singleton, pulls published
  singletons from the RAPP Store). Auto-loads.

### Reserved subdirectories (under `workspace_agents/`)

- `workspace_agents/experimental_agents/` — never auto-loads.
  Hand-load to test in-flight work.
- `workspace_agents/disabled_agents/` — never auto-loads. Move a file
  here to turn it off.
- `workspace_agents/local_agents/` — gitignored. Personal,
  tenant-specific, or half-baked agents that auto-load but never
  commit.

### User-organized subdirectories (the whole point)

Anything else under `workspace_agents/` auto-loads:
`workspace_agents/my_stack/`, `workspace_agents/personal_twin/`,
`workspace_agents/project_x/`, even nested like
`workspace_agents/ceo/roles/`. No registration, no config — drop a
folder in, `*_agent.py` files inside it load. Project-scoped folders
matching `specific_local_project_agents*/` are gitignored by default.

### What this rules out

- ❌ Making users touch engine files to do brainstem-y things. The
  user's entire config surface is `soul.md` + `.env` + the `agents/`
  tree. Never "edit brainstem.py to…"
- ❌ A "brainstem config" directory outside `agents/` that users
  are expected to edit.
- ❌ Dumping organizational subdirectories at the top level of
  `agents/`. `experimental_agents/`, `disabled_agents/`,
  `local_agents/`, project folders — all of them live under
  `workspace_agents/`, never at top level.
- ❌ Adding more starter agents to the top level beyond the small
  curriculum set + rare broadly-useful exceptions. The showroom
  stays clean for newcomers.
- ❌ A registry file listing which agents to load. Discovery is
  filesystem-only.
- ❌ `from agents.workspace_agents.X import …` in tests — load by
  file path via `importlib`. The `agents.*` module namespace is for
  the shimmed `basic_agent` import only.
- ❌ Any depth limit on `workspace_agents/` recursion.
- ❌ Re-introducing a `system_agents/` bucket. The one ship-in-repo
  engine agent (`swarm_factory_agent`) lives at the top of
  `workspace_agents/`; additional engine agents, if ever needed, sit
  alongside it. One less folder, one less concept to teach.

### Discovery

- `load_agents()` walks `agents/` recursively via `rglob("*_agent.py")`
  and skips paths containing `experimental_agents/`, `disabled_agents/`,
  or `__pycache__/`.
- Agents import `from agents.basic_agent import BasicAgent` from any
  depth via the shim.
- `rapp_swarm/build.sh` recursively vendors the `agents/` tree with
  the same exclusions — Tier 2 mirrors Tier 1's user-organized shape.

---

## Article XIII — The Management UI Is a View Onto `agents/`

The brainstem's browser interface is **a view onto the `agents/`
tree**. Every user-facing action in the UI corresponds 1:1 to a
filesystem operation inside `agents/`. The UI abstracts files, paths,
and Python — but never invents concepts that don't exist on disk.

> **UI tree = `agents/` tree. UI operation = filesystem operation.
> No UI-only concepts.**

### Mapping

| UI action         | Filesystem op                                     |
|-------------------|---------------------------------------------------|
| "New agent"       | write `*_agent.py` at chosen location             |
| "New folder"      | `mkdir` under `agents/`                           |
| "Move" / drag     | `mv` between directories                          |
| "Rename"          | `mv` with a new name                              |
| "Delete"          | `rm`                                              |
| "Disable"         | move into `agents/disabled_agents/`               |
| "Enable"          | move out of `disabled_agents/`                    |
| "Mark experimental"| move into `agents/experimental_agents/`          |
| "Edit"            | open the file in an inline editor                |

The three reserved subdirs are visible in the UI with their semantics
explained. Don't hide them.

### What the UI covers (user's full config surface)

Per Article XII, the user's operational surface is `soul.md` + `.env`
+ `agents/` tree. The UI covers all three: persona editor, creds
form, agent tree. Nothing else.

### What this rules out

- ❌ UI-only concepts (tags, categories, collections) that don't
  round-trip to the filesystem.
- ❌ Editing engine internals (`brainstem.py`, `VERSION`, etc.)
  through the UI.
- ❌ A separate registry alongside the filesystem. Disk is the
  registry.
- ❌ UI actions with no filesystem equivalent.
- ❌ Hiding `experimental_agents/` or `disabled_agents/` from the
  tree view.

### Why

If the UI invents concepts that don't exist on disk, UI users and
filesystem users diverge. `agents/` is the single source of truth;
the UI must be transparent to it.

---

## Article XIV — UI Defaults to Beginner-First; Advanced Is Opt-In

The `/manage` UI has two modes driven by a single **Advanced** toggle.
Default = beginner-friendly. Advanced = power user. Beginners never
see technical detail unless they ask for it.

### Beginner view (default)

- Human names: `save_memory_agent.py` → "Save Memory". `my_stack/` →
  "My Stack". Strip `_agent.py`, replace `_` with spaces,
  title-case.
- Dropdowns + toggles for bounded values (never text inputs for
  true/false or enumerated model lists).
- Friendly service names: "GitHub Copilot — Connected ✓" not
  `GITHUB_TOKEN: set`.
- Reserved folders (`experimental_agents/`, `disabled_agents/`)
  hidden.
- Folders collapsed on load.
- Curated field set — model, voice, twin, connection chips.

### Advanced view (toggle on)

- Raw filenames + extensions.
- Reserved folders visible with annotated labels.
- Full `.env` editor (bounded → select, free-form → text).
- Secret chips with raw env key names.

### What this rules out

- ❌ Showing `snake_case_agent.py` in default mode.
- ❌ Text inputs for bounded values in any mode. Dropdowns/toggles
  always.
- ❌ Reserved folders visible by default.
- ❌ Two separate UIs. One UI, toggled visibility.
- ❌ Losing form state on mode flip. Both views bind to the same
  `data-env="KEY"` attributes.
- ❌ The Advanced toggle gating *features*. It only gates
  visibility — a beginner can do everything they need from the
  beginner view.

### Why

A beginner opening the UI should see something that reads like an
app, not a file browser. Power users flip the toggle. Both modes
write to the same `.env` / filesystem — there is no parallel state.

---

## Article XVI — Every Twin Surface Is a Calibration Opportunity

The digital twin (`|||TWIN|||` panel, action pills, present-card
lines) exists to build fidelity with the user. Each turn is the
twin's chance to **predict something** about the user — clicks and
ignores are the data that grows twin accuracy over time.

> **Twin surface = the twin's bet. Generic help belongs in the
> main assistant reply, not on twin surfaces.**

### Calibration-shaped (right)

Labels that are predictions about the user. Click = "you're right
about me." Ignore = signal the other way.

- `label="I think you prefer X. Right?"`
- `label="Still want to ship today?"`
- `label="You mentioned Foo — did that happen?"`
- `label="Pin this as a priority?"`

Pair each calibration-shaped `<action>` with a `<probe>` so the next
turn's `<calibration>` can judge it.

### Help-shaped (wrong)

- ❌ "What can you do?"
- ❌ "Browse my agents"
- ❌ "How do I deploy to Azure?"

These are main-assistant-reply territory. Using them on twin surfaces
wastes the slot — the twin learns nothing.

### Rules-out

- ❌ Twin labels that aren't predictions about the user.
- ❌ `<action>` without a paired `<probe>`.
- ❌ Static starter prompts that are help-shaped (they're the
  user's first turn — make it the twin's first data point).
- ❌ Confusing twin voice (first-person as the user, TO the user,
  predicting) with assistant voice (answering).

---

## Article XVIII — One Twin, Two Faces

The brainstem hosts **one entity**: the user's digital twin. There
is no separate "assistant" character alongside a "twin" character.

> **Main reply = the twin doing the task AS the user. Hologram /
> |||TWIN||| panel = the same twin showing its current fidelity
> state.**

- **Main reply**: the twin at work. First-person as the user —
  answering as the user would, choosing as the user would.
- **|||VOICE|||**: TTS version, same voice.
- **|||TWIN||| panel**: the twin's **rubber-duck surface**. The twin
  surfaces an assumption it's making about the user *right now* and
  asks to be corrected. Not a status report. Not a progress bar.
  Disagreement refines; confirmation locks the belief. Same
  identity as the main reply — just angled inward, asking to be
  taught.

### Rules-out

- ❌ Treating the model as an "assistant who simulates a twin." It
  *is* the twin.
- ❌ Main-reply content that sounds like a generic AI instead of
  the user's proxy voice.
- ❌ Twin-panel content in third-person ("The user seems to…").
  Even reflections stay first-person ("I'm not sure I'd actually…").
- ❌ Blurring the two faces — task answers belong in the main
  reply, fidelity state belongs in the twin panel.

### The hologram

Represents the twin *present with you* — listening, guessing, ready
to be corrected. Not a progress bar. Meaning is always: "I'm here,
I'm guessing, teach me."

### The rubber-duck pattern

Shapes the twin block takes (at most one per turn):

- **I'm assuming:** <belief>. Right?
- **My guess:** you'd rather <X>. True?
- **Learning:** you'd call this <name>, not <other>. Close?
- **Rubber-duck me:** walk me through <thing> so I can copy your
  instinct.

Each is the twin's current working hypothesis, stated so the user
can confirm, correct, or sharpen it. The correction IS the learning.

---

## Article XX — The Kernel, The Extensions, The Rapplication

### The kernel

The kernel is exactly two files. They never grow.

| File | Role |
|------|------|
| `brainstem.py` | Server, auth, LLM loop, agent discovery, service discovery |
| `basic_agent.py` | Agent base class |

The kernel provides two discovery mechanisms — one for agents, one for
services — and dispatches to whatever files it finds. All capability
lives in the extensions, never in the kernel.

### The two extension contracts

| | Agent | Service |
|---|---|---|
| **File pattern** | `agents/*_agent.py` | `services/*_service.py` |
| **Contract** | `metadata` + `perform(**kwargs) → str` | `name` + `handle(method, path, body) → (dict, int)` |
| **LLM sees it?** | Yes | No |
| **Use case** | Anything the LLM should invoke | HTTP endpoints for UIs, webhooks, machine-to-machine |
| **Hot reload?** | Every request | Every request |
| **Tier portable?** | Yes | Yes |

Agents and services never overlap. If the LLM should call it, it's an
agent. If the UI or an external system should call it, it's a service.
Both are single-file, zero-dependency, and portable.

### The agent-first rule

> **The agent is the API. The service is a view.**

Every rapplication MUST be fully functional through `perform()` alone.
A user talking to any AI — phone, terminal, Copilot Studio, Claude,
GPT — gets the complete rapplication without a browser. The service
adds convenience (drag-and-drop, charting, webhook ingestion) but
never gates capability.

This is what makes rapplications work on every AI surface that exists
today and every one that will exist tomorrow.

### The factory-installed rule

> **The brainstem ships clean — like a factory iPhone.**

The kernel provides discovery mechanisms for `agents/` and `services/`,
but `services/` ships **empty**. Only core agents ship in `agents/`:

| Ships with brainstem (factory image) | Installed on demand (rapp_store) |
|--------------------------------------|----------------------------------|
| ContextMemory, ManageMemory (memory) | LearnNew (agent generation) |
| HackerNews (starter/test) | SwarmFactory (workshop → singleton) |
| WorkIQ (productivity) | VibeBuilder (rapplication generation) |
| | Kanban, Webhook, Dashboard |
| | Swarms, Binder (platform services) |
| | Any user-built rapplication |

No rapplication, no service, and no non-core agent is pre-installed.
Users install what they need — via the binder catalog, via VibeBuilder,
or by dropping files in manually. The brainstem never assumes what
the user wants beyond the minimum viable agent surface.

### What a rapplication is

A rapplication is the atomic installable unit in the RAPP ecosystem:

1. MUST include at least one `*_agent.py`.
2. MAY include one `*_service.py`.
3. Both files are single-file, self-contained, portable across tiers.
4. Install = drop files in. Uninstall = delete them. Nothing else.

### What this rules out

- ❌ Service-only rapplications. No agent = not a rapplication. The
  agent-first rule is not optional.
- ❌ Agents that require their service to function. The service is
  always optional. If removing the service breaks the agent, the
  design is wrong.
- ❌ Multi-file agents or multi-file services. The single-file rule
  (Article IV, §0) extends to services.
- ❌ Pre-installed rapplications or services in the brainstem. The
  brainstem ships factory-clean. `services/` is empty. Only core
  agents live in `agents/`. Everything else is installed on demand.
- ❌ Services that duplicate agent capability. The service reads/writes
  the same storage as the agent. It is a view, not a second brain.

---

## Article XIX — Amendments

This constitution can be amended. The only rule: the change must serve
the platform's purpose as a business-focused AI agent engine. If it
blurs the line between engine and experience, it doesn't belong here.

---

*Ratified for RAPP Brainstem. The engine that powers what others build.*
