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
BRAINSTEM_VERSION=0.9.0 curl -fsSL https://kody-w.github.io/RAPP/install.sh | bash
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
- Deployed sibling swarms (`swarms/<guid>/…`), snapshots, sealed
  markers, active-swarm pointers.
- Hatched project scaffolds (Article VI-A).

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

### A recursive, user-organized tree

`agents/` is a **recursive tree** with no depth limit. Drop a `*_agent.py`
file anywhere under it and the brainstem finds it. Subdirectories can
contain subdirectories —
`agents/sales_stack/q4/prospects/outbound_agent.py` auto-loads just
like `agents/outbound_agent.py`.

Two subdirectory names are reserved and **never** auto-load:
**`experimental_agents/`** (in-flight, hand-load only) and
**`disabled_agents/`** (move a file there to turn it off). Everything
else under `agents/` loads.

### Starter set at the top level of `agents/`

- `basic_agent.py` — base class.
- `hacker_news_agent.py`, `learn_new_agent.py`,
  `save_memory_agent.py`, `recall_memory_agent.py` — curriculum.

A new user opens `agents/` and sees exactly these five — the shape of
what a RAPP agent is. Don't dump more at the top level; use a subdir.

### Engine-provided subdirectories (convention, not magic)

- `agents/system_agents/` — engine infrastructure (swarm factory +
  swarm-management agents today). Auto-loads because it's under
  `agents/`.
- `agents/experimental_agents/` — never auto-loads. Hand-load to
  test in-flight work.
- `agents/disabled_agents/` — never auto-loads. Move a file here to
  turn it off.

### User-organized subdirectories (the whole point)

Anything else under `agents/` auto-loads: `agents/my_stack/`,
`agents/personal_twin/`, `agents/project_x/`, even nested like
`agents/ceo/roles/`. No registration, no config — drop a folder in,
`*_agent.py` files inside it load.

### What this rules out

- ❌ Making users touch engine files to do brainstem-y things. The
  user's entire config surface is `soul.md` + `.env` + the `agents/`
  tree. Never "edit brainstem.py to…"
- ❌ A "brainstem config" directory outside `agents/` that users
  are expected to edit.
- ❌ Dumping more than the five starter files at the top level of
  `agents/`. Infrastructure goes in `system_agents/`; user groupings
  go in user-named subdirs (arbitrarily deep).
- ❌ A registry file listing which agents to load. Discovery is
  filesystem-only.
- ❌ `from agents.system_agents.X import …` in tests — load by file
  path via `importlib`. The `agents.*` module namespace is for the
  shimmed `basic_agent` import only.
- ❌ Any depth limit on `agents/` recursion.

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
- ❌ Hiding `system_agents/`, `experimental_agents/`, or
  `disabled_agents/` from the tree view.

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
- Reserved folders (`system_agents/`, `experimental_agents/`,
  `disabled_agents/`) hidden.
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

## Article XIX — Amendments

This constitution can be amended. The only rule: the change must serve
the platform's purpose as a business-focused AI agent engine. If it
blurs the line between engine and experience, it doesn't belong here.

---

*Ratified for RAPP Brainstem. The engine that powers what others build.*
