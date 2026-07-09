# RAPP — Constitution

> The principles that govern this repo. Read this before you change code.

[SPEC.md](./SPEC.md) is the wire contract. This is the authoring discipline
that keeps the wire contract shippable for a decade.

[MASTER_PLAN.md](./MASTER_PLAN.md) is the why-axis — the first-principles
north star. When this Constitution and the Master Plan disagree about
*what* should be true, the Master Plan wins; this Constitution describes
*how* that plan is executed.

---

## Article 0 — The Sacred Tenet (restated from SPEC)

> 🧬 **The file IS the agent IS the documentation IS the contract.**

One file. One class. One `perform()` method. An agent that requires more
than a single Python (or TypeScript) file is not a RAPP agent. Everything
else this constitution says exists to protect that shape.

---

## Article I — The Brainstem Stays Light

`rapp_brainstem/brainstem.py` and `rapp_swarm/function_app.py` are the
infrastructure. They are NOT where capabilities live. Capability lives in
`*_agent.py` files that the brainstem hot-loads from `agents/`.

> **The brainstem is a loader + an LLM loop + a response splitter. That's
> it. Nothing else.**

Concretely, the allowed responsibilities of these two files are:

1. Boot the server and answer `/health`, `/chat`, `/agents`, etc.
2. Load `soul.md` (the system prompt).
3. Auto-discover `*_agent.py` files and hot-load them.
4. Auth: resolve the LLM provider credential (GitHub Copilot / Azure OpenAI / …).
5. Run the tool-calling loop: call LLM → execute agent → loop.
6. **Split and route the model output across named delimited slots.** The
   canonical slots today:
   - `|||VOICE|||` — TTS line (shipped ~10 months ago, first slot added)
   - `|||TWIN|||` — digital twin's real estate (shipped in this era)

Everything else belongs somewhere else. No feature flags. No memory
subsystem in-core. No in-core data transformation. No "helper endpoints."
No business logic.

### The only legitimate reason to modify brainstem.py / function_app.py

> **Adding or evolving a new top-level output slot in the main prompt
> contract** — a new `|||<SLOT>|||` alongside the existing ones.

That is a once-in-a-great-while event. `|||VOICE|||` was added ~10 months
ago. `|||TWIN|||` was added in this era. That's it, total, since the repo
started. Future slots are possible, but each one must clear a very high
bar: it must be fundamentally different real estate that existing slots
and agents cannot serve.

**If you are about to edit `brainstem.py` or `function_app.py` for any
reason other than a new output slot, stop. The thing you want is a new
`*_agent.py` or a prompt change. Make it that.**

### What this rules out

- ❌ A new endpoint for a feature. Agents already get full HTTP surface
  via their `perform()` — a browser can call `POST /chat` and the LLM
  routes to the agent. Adding `/my-feature` is load in the wrong place.
- ❌ Special-casing a particular agent in-core ("if agent name is X,
  transform its output"). The agent's own `perform()` does the transform.
- ❌ Central memory features. Memory is `save_memory_agent.py` + `recall_memory_agent.py` + its
  storage shim. Never an in-core dict.
- ❌ A "plugin system" for things that are not agents. Single file
  agents are the plugin system.
- ❌ New tags, subfields, or conventions added to the response body to
  carry auxiliary data. Put them INSIDE an existing slot as tags the
  server strips — this is how `<probe/>`, `<calibration/>`, and
  `<telemetry>` all live inside `|||TWIN|||`.

---

## Article II — Delimited Slots Are a Fixed Resource

The **slot mechanism** — split a chat response on `|||<NAME>|||`
delimiters, render each segment to its own surface — is sacred kernel
behavior. It exists in the brainstem and never goes away. Once a
specific slot has been defined and shipped, its **name** belongs to
that purpose forever. Never repurpose. Never overload. If a slot
grows a new sub-capability, it lives as a tag inside the slot — the
slot is its capability's entire real estate.

### Specific slots are rappstore add-ins, not kernel features

The kernel knows the slot *mechanism*; it does not own the *list* of
slots. Specific slots are **sense / behavior add-ins** that a brainstem
installs based on its purpose and available sensing tools. They live
in the [`kody-w/rapp_store`](https://github.com/kody-w/rapp_store)
catalog like every other modular feature, and a brainstem
with no speaker doesn't need the voice add-in, a read-only oracle
brainstem doesn't need the twin add-in, and a future vision brainstem
might add `|||VISION|||` from a vision add-in. Each brainstem assembles
the senses it actually uses.

### Each slot's content is wrapped in matching XML tags

Inside a slot, the content is wrapped in an XML element whose name
matches the slot. This is a belt-and-suspenders convention: the
delimiter marks where the slot starts; the XML tag marks what the
slot's content actually is, with an explicit closing tag. The LLM
doesn't have to guess where one slot ends and the next begins, and
the parser can verify well-formed slot content rather than relying on
the next delimiter alone.

```
<main>...the visible reply...</main>
|||VOICE|||
<voice>...the TTS line...</voice>
|||TWIN|||
<twin>...the twin's commentary, with optional inner tags...</twin>
```

The brainstem strips the outer wrapping tag before returning the slot
content in the response envelope (e.g. the contents of `<voice>...</voice>`
become the `voice_response` field). Inner tags within the twin block
(`<probe/>`, `<calibration/>`, `<telemetry>`, `<action>`) keep their
existing strip-or-pass-through behavior. Time-travel safety: legacy
brainstems that emit slot content without the wrapping XML tag still
parse correctly — the wrapper is optional input to the parser, mandatory
output for new emitters.

### v1 canonical slots

Two slots are the defined pair shipped in v1. They can be removed or
replaced in a future version, but while they exist their meanings are
fixed:

- `|||VOICE|||` — TTS sense add-in. Only the out-loud sentence; not a
  "short summary," not "voice OR hint." A brainstem without a speaker
  doesn't emit it.
- `|||TWIN|||` — proxy-of-owner behavior add-in. The brainstem's
  digital twin of its current owner (anchored on the active
  `user_guid`). When the real owner is engaged it defers; when the
  owner is offline it can act as their next-best-thing proxy.
  Everything twin-related (commentary, probes, calibration,
  telemetry, action chips, future signals) lives **inside** this
  block as either natural-language text or XML-style tags the server
  strips before render.

New slots get added **rarely** and **never** get removed in a minor
version. v2 is the only place a slot can be retired entirely.

### Slots are time-travel safe (Article XXV)

Delimiters are part of the wire and obey the wire-forever rule:

- **A brainstem that doesn't emit a slot must not break a peer that
  expects it.** Older brainstems don't emit `|||TWIN|||`; newer ones
  must treat absent slots as empty/not-present, never as malformed.
- **A brainstem that doesn't recognize a slot must not break a peer
  that emits it.** Older brainstems don't know what `|||TWIN|||`
  means; they just see it as part of the prose. That's fine — they
  rendered the response as one block, which is the correct degraded
  behavior.
- **Delimiter strings themselves are sacred and identical across
  every implementation, forever.** Never make them configurable per
  brainstem; configurable strings would silently fragment the
  ecosystem.

Adding a new slot is the rare exception (per the rules above). When it
happens, the new slot is optional in both directions: emitters MAY emit
it, receivers MAY parse it, but neither side may require the other to
support it.

### Sub-tag vocabulary lives inside a slot, not outside it

When the twin needed to emit calibration signal, we did NOT add
`|||CALIBRATION|||`. We added `<probe/>` and `<calibration/>` tags
**inside** `|||TWIN|||`. When the twin needed to emit operator-facing
telemetry, we did NOT add `|||TELEMETRY|||`. We added
`<telemetry>…</telemetry>` **inside** `|||TWIN|||`.

This is the design pattern for future growth: **new slot = new top-level
surface; new sub-capability of an existing surface = new tag inside that
slot**. The brainstem does not grow a new top-level delimiter to carry a
sub-capability of something that already has a home.

---

## Article III — Capabilities Are Files (Single File Agents)

### III.1 — The default answer

When a user asks for a new ability, the answer is almost always:

> Drop a `new_thing_agent.py` in the agents directory. Write a `perform()`.
> The brainstem auto-discovers it.

This is both the technical architecture AND the authoring discipline. If
you catch yourself adding a conditional to `brainstem.py`, stop and ask:
could this be an agent that `perform()` does? If yes, do that instead.

Single-file agents are:

- **Portable** — one file moves across Tier 1, Tier 2, Tier 3.
- **Auditable** — one file to read to understand everything it can do.
- **Replaceable** — delete the file and the capability is gone. No
  lingering code in the core.
- **Versionable** — the agent has its own `__manifest__` version; the
  brainstem doesn't.

The brainstem staying small is how the agents stay cheap.

### III.2 — The minimum bar (shared with SPEC §5)

A RAPP agent is a single file that:

1. Is named `*_agent.py` (or `*Agent.ts`) and lives in an `agents/` folder.
2. Defines a class extending `BasicAgent`.
3. Sets `self.name` — the tool name the LLM sees.
4. Sets `self.metadata` — an OpenAI-style function-calling JSON schema.
5. Implements `perform(**kwargs) -> str` — the tool body.

Nothing else is required. No manifest, no package identity, no schema
tag. A file that meets these five points is a fully valid RAPP agent and
MUST run in any v1-compliant runtime. Registry additions (`__manifest__`,
`@publisher/slug`, semver, tags) are optional — they buy admission to
RAR, not the right to exist.

### III.3 — The portability guarantee

**An agent file that runs in Tier 1 must run unmodified in Tier 2 and
Tier 3.** If you make a change that requires agents to be edited before
they work on a different tier, the change is wrong. Write the shim into
the runtime, not into every agent file.

This is the single hardest promise in the whole spec. Protect it.

### III.4 — `data_slush` is the wire between agents

When an agent's work feeds the next agent in a chain, its `perform()`
returns a JSON string shaped like:

```json
{
  "status": "success",
  "<payload_key>": "<human-facing result>",
  "data_slush": { "<signal_key>": "<curated value for next agent>" }
}
```

`data_slush` lands automatically in the next agent's `self.context.slush`
— no LLM interpretation between steps. This is how deterministic
pipelines compose. If you feel tempted to introduce a message bus or a
shared state store between agents, re-read SPEC §5.4 and §6: the slush
is the wire, and it is enough.

### III.5 — Agents MUST NOT

- Require a build step.
- Import sibling files within the same `agents/` directory (each agent
  is independent and movable).
- Depend on any framework beyond `BasicAgent`.
- Mutate the runtime's global state outside what `perform()` returns.
- Require configuration outside `self.metadata` or environment variables.

Agents MAY make HTTP calls, hit databases, shell out, write files, call
other LLMs. They MAY declare pip dependencies at the top of the file —
the runtime auto-installs missing ones. Freedom inside the file;
discipline at the boundary.

### III.6 — Rapplications: composed pipelines, still one file

A **rapplication** is what you get when you build a pipeline out of
several cooperating agents and then collapse it to a single deployable
file via the double-jump loop. The multi-file form under
`<name>/source/` (in the [`kody-w/rapp_store`](https://github.com/kody-w/rapp_store)
catalog) is the authoring surface; the one-file artifact under
`<name>/singleton/` is the shipped unit.

The rule: **the ship-time artifact is still one file.** A rapplication
that needs two files in production is not a rapplication — it's a
library. The source tree has as many files as it needs; the singleton
has one. If the collapse tool stops being able to produce a singleton,
the rapplication has outgrown the pattern.

### III.7 — Where agents live in this repo

| Path | What it holds |
|------|---------------|
| `rapp_brainstem/agents/` | Default agents shipped with the brainstem (starter set + essentials like memory). |
| `rapp_brainstem/agents/experimental/` | In-flight agents the auto-loader ignores. Hand-load them when you're ready. |
| `<rapp>/source/` (in `kody-w/rapp_store`) | Rapplication source — multi-file, editable, runs through the double-jump loop. |
| `<rapp>/singleton/` (in `kody-w/rapp_store`) | Collapsed single-file ship artifact for the rapplication. |
| `<rapp>/tests/` (in `kody-w/rapp_store`) | Tests for the singleton and the source agents. Use real storage, not mocks. |

User-authored agents live in the user's own workspace, not this repo.
This repo ships the starter set; the catalog of distributable
rapplications lives in [`kody-w/rapp_store`](https://github.com/kody-w/rapp_store).
Everything else is downstream.

---

## Article IV — Blast Radius

Before adding code to the brainstem, ask: **what else does this change
break if the assumptions shift?** Core changes touch every tenant, every
deployment tier, every test. Agent changes touch one file.

Bias toward agent changes. When you do touch core, the PR must:

- Name the existing slot pattern it's following (e.g. "this is a new
  tag inside `|||TWIN|||`", or "this is a new top-level slot with the
  same treatment as `|||VOICE|||`")
- Show why it could not be an agent instead
- Keep the diff scoped to the boot/loop/route/split responsibilities

A brainstem change that lists "add helper for X" where X is not one of
the five allowed responsibilities is probably mis-scoped.

---

## Article V — The Install One-Liner Is Sacred

```bash
curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash
```

Works on a fresh machine. Installs prerequisites, clones, sets up the
venv, authenticates, launches. Any change must be tested against this.
If the one-liner breaks, nothing else matters.

---

## Article VI — Local First, No Phone-Home

The brainstem runs on the user's machine. GitHub account for Copilot is
the only required credential. No telemetry leaves the device unless the
user explicitly deploys to a higher tier. (Note: the `|||TWIN|||` slot's
`<telemetry>…</telemetry>` tag writes to the user's OWN local log file,
not to any remote — that's debugging signal for the operator, who is the
user.)

The user owns:

- Their soul file — the persona.
- Their agents directory — the capabilities.
- Their `.env` — the config.
- Their `.twin_calibration.jsonl` — the twin's calibration memory.

We never phone home, never collect telemetry upstream, never require an
account beyond GitHub.

---

## Article VII — Scope Discipline (what lives here vs. what doesn't)

This repo (`kody-w/RAPP`) contains:

- ✅ `rapp_brainstem/` — the local Flask brainstem + its browser twin
- ✅ `rapp_swarm/` — the Tier 2 Azure Functions deployment
- ✅ `installer/` — the install-widget mirror (infra)
- ✅ Root install scripts, ARM template, Copilot Studio .zip
- ✅ `SPEC.md` (wire contract), `ROADMAP.md` (directions), this file
- ✅ `tests/` — browser + node test runner for the v1 contract

This repo does NOT contain:

- ❌ Blog posts / doctrine essays — those live at
  [kody-w.github.io](https://kody-w.github.io/) (tagged `rapp`).
- ❌ Consumer brand identities (creatures, mascots, organisms).
- ❌ Background daemons or heartbeat loops beyond the Flask server.
- ❌ Features that require processes beyond the brainstem + agents.
- ❌ Content belonging to other intellectual properties.

When in doubt: if it's not the engine, its deployment path, its
rapplication catalog, or its install-widget mirror — it belongs elsewhere.

---

## Article VIII — Degrade Gracefully

Every feature added to this repo must **compose back down cleanly**: if
its helper fails to import, if its prompt block is absent, if its log
file can't be written, the rest of the system keeps working.

Examples in the tree today:

- `rapp_brainstem/twin.py` is imported with a `try: … except ImportError:
  _twin = None`. If the helper is missing, calibration silently disables
  and the v0 twin split still returns cleanly.
- The twin's `<telemetry>` / `<probe>` / `<calibration>` tags are all
  optional. Remove the prompt instructions and the tags stop; the panel
  still renders the natural-language part.
- A browser client that doesn't know about `|||TWIN|||` sees the main
  reply + voice line and nothing breaks. The twin slot is invisible to
  it.

> **New features are additive, not load-bearing.** If your feature's
> failure path is "nothing else works," redesign it until its failure
> path is "that one feature is off."

---

## Article IX — The Twin Offers, The User Accepts

The digital twin is a companion, not an autonomous actor in the UI.
Everything the twin *does* to the user's surface is a button the user
clicks. This is load-bearing for trust: the twin builds confidence by
taking small, reversible favors off the user's plate — **one click at a
time, always user-approved**.

Concretely:

- `<action>` tags render as chips. Chips never fire automatically.
- The dispatch is a whitelist (today: `send`, `prompt`, `open`,
  `toggle`). The twin can only invoke named actions that the user
  already has a manual button or keystroke for.
- Arbitrary code execution from twin output is prohibited. The twin
  never gets an `eval` surface, never gets an HTTP-escape, never gets
  to skip the user's hands.

If a new action kind is proposed, it must satisfy: *the user already
has a way to do this manually, and the twin is just saving them the
click*. "Convenience" is the whole point; "autonomy" is not.

---

## Article X — Calibration Is Behavioral, Not Explicit

We do not build thumbs-up / thumbs-down buttons for the twin. The
user's next message is the ground truth — if they acted on a hint, it
was validated; if they pushed back, it was contradicted; if they
changed the subject, it was silent. The twin grades itself on that,
writes the result to `.twin_calibration.jsonl`, and the rolling
accuracy feeds back into the next turn's system prompt.

Why this matters:

- Explicit feedback buttons are friction. Users don't click them.
  Friction-free signal is the only signal that scales.
- Silent outcomes don't count. The twin is not penalized for
  guessing quietly — this preserves its willingness to offer hints
  that *might* be wrong but are useful when right.
- No dashboards, no graphs, no "your twin's accuracy is 72%" UI.
  The feedback loop is internal. The user feels it, doesn't read it.

If you find yourself adding a scoring UI, re-read this article.

---

## Article XI — Historical Artifacts Are Memorial

When we rename, restructure, or relocate, the past stays.

- Blog posts at [kody-w.github.io](https://kody-w.github.io/) tagged
  `rapp` preserve the timeline — including their references to
  long-renamed folders (`hippocampus/`, `community_rapp/`, etc.).
  Don't retcon them.
- Commit messages are not rewritten. `git log` is the truth of what
  happened, when.
- Code comments describing past reasoning (e.g. "Same sentinel the
  community RAPP brainstem uses…") stay even after the names move,
  because they describe *where an idea came from*, not *where the
  file lives now*.

The rule: **rename paths and API surfaces; don't rename history.** If a
stale reference in docs is confusing users *today*, fix it in today's
doc. Don't mass-rewrite past posts to pretend the rename always
existed.

---

## Article XII — Prompt Shape Is a Contract

The delimited slots and in-band tag vocabularies (`|||VOICE|||`,
`|||TWIN|||`, `<probe/>`, `<calibration/>`, `<telemetry>`, `<action>`)
are as much a wire as `/chat`'s JSON shape. A user's `soul.md` depends
on them. A fine-tuned model might depend on them. A downstream parser
depends on them.

Evolve them with the same discipline as SPEC §14:

- **Additive changes only in v1.x.** A new tag family (kept small) is
  allowed. A new top-level `|||<SLOT>|||` is allowed but very rare
  (see Article II).
- **Never silently repurpose.** If `|||VOICE|||` means "TTS line,"
  `|||VOICE|||` means only that, forever. Its meaning does not
  shift-right into "voice or short summary" because that would break
  anyone who wrote to the old contract.
- **Never change a tag's attribute name without deprecation.** If
  `<probe kind=…>` exists, don't rename `kind` to `category`.
  Breaking attributes goes in v2 with a compat shim.

The prompt is sacred for the same reason the agent file is sacred: it
is the thing users wrote down.

---

## Article XIII — Reversibility

Every feature must be cleanly removable. The test: can a user (or a
future us) turn it off by deleting one file, one block, or one line?

- Delete `rapp_brainstem/twin.py` → calibration disables, v0 twin
  split still works.
- Delete the user's `.twin_calibration.jsonl` → the twin's confidence
  resets to neutral, next turn is unaffected otherwise.
- Remove the `|||TWIN|||` section of the system prompt → the twin
  falls silent, nothing else changes.
- Remove an `<action kind="…">` from the action-dispatcher whitelist
  → twin-suggested actions of that kind render as failed chips; other
  kinds still work.

What this rules out:

- ❌ Half-torn-out code, `# removed in vX` comments, dead branches.
  Delete completely or don't delete.
- ❌ Compatibility shims that live forever "just in case."
- ❌ Features that can only be disabled by a rebuild or a reinstall.

If a feature can't be cleanly removed, it's coupled too tightly to
the core. Uncouple it before shipping.

---

## Article XIV — Swarms Are Directories, Not Routes

A **swarm** is local state: a directory containing `agents/`, a soul
file, and a memory namespace. The brainstem runs against that state. It
is not a runtime abstraction, a routing layer, or a multi-tenant
service.

> **A swarm is a directory. Changing swarm = changing which directory
> the brainstem is pointed at. That is the entire concept.**

Concretely:

- Swarm selection is a body field on `/chat` (optional `swarm_guid`) or
  an env pointer to a default directory. Nothing more. No new endpoints.
- Swarm operations (deploy, list, switch, seal, snapshot, invoke a
  sibling) are `*_agent.py` files that read and write state on disk.
  They are not classes in the core, not REST routes, not middleware.
- The filesystem layout IS the contract. Two swarms with the same
  directory shape behave the same under the same brainstem.

### What this rules out

- ❌ A `SwarmStore` class or equivalent as a first-class runtime object
  in `brainstem.py` / `function_app.py`. At most, a handful of
  `pathlib` helpers that resolve "which directory for this request."
- ❌ `/api/swarm/<guid>/...` REST surfaces. Every historical route of
  that shape collapses to `/chat` with the appropriate agent plus a
  `swarm_guid` body field.
- ❌ Runtime state about swarms held in memory beyond the lifetime of a
  single request. Disk is authoritative; the brainstem is stateless
  between calls.
- ❌ A "swarm server" parallel to the brainstem. There is one server.
  It reads state.

If you catch yourself designing a swarm-aware subsystem, stop and ask:
could this be a directory layout plus an agent? If yes, do that.

---

## Article XV — Tier Parity Is a `/chat` Contract, Not a Transport

Article III.3 promises agent portability across tiers. This article
extends that promise to the server itself: **`rapp_brainstem/brainstem.py`
and `rapp_swarm/function_app.py` must behave identically on the `/chat`
*contract*.** The surface a caller touches — request envelope, response
envelope, slot split, agent contract, state layout — is the invariant.

> **Same `/chat` contract. Same prompt split. Same agent contract.
> Same state layout. Transport differences below the contract are OK.**

What must be identical across tiers:

- **Request envelope** — `user_input`, `conversation_history`,
  `session_id`.
- **Response envelope** — `response`, `voice_response`, `twin_response`,
  `session_id`, `agent_logs`, `provider`, `model`.
- **Tool-calling loop shape** — call LLM → execute tool calls → loop,
  capped at a small number of rounds, with the same per-round logging.
- **Slot split** — `|||VOICE|||` and `|||TWIN|||` are stripped the
  same way, and the twin tags (`<probe/>`, `<calibration/>`,
  `<telemetry>`) are handled the same way.
- **Agent contract** — `BasicAgent` + `perform()` + metadata. Agents
  that run in Tier 1 must run unmodified in Tier 2 (III.3).
- **State layout** — `.brainstem_data/` on Tier 1, `BRAINSTEM_HOME` on
  Tier 2. Same directory shape (`agents/`, `soul.md`, `memory/`,
  `swarms/<guid>/...`).

What may legitimately differ:

- **Mount point for state.** Tier 1 local disk; Tier 2 Azure Files.
- **LLM transport — by design.** Tier 1 is the training on-ramp:
  Copilot-only via the `gh` CLI auth chain, zero-config, one auth
  story for every learner. Tier 2 is where the user decides — pushing
  to the RAPP cloud swarm is the moment the user declares *which AI
  the cloud deployment uses* (Azure OpenAI, OpenAI, Anthropic, or any
  provider the deploy target gives access to). That choice lives on
  the cloud side because it's the cloud operator's constraint, not
  the learner's. Both tiers produce the same response envelope and
  the same loop behavior regardless of transport.

### What this rules out

- ❌ A Tier-2-only server (e.g. `swarm_server.py`, a separate handler
  stack, a bespoke chat loop) that duplicates `brainstem.py`'s
  responsibilities with drift. If Tier 2 needs a capability,
  the capability lands in an agent and Tier 2 vendors it.
- ❌ Routes that exist on one tier but not the other. `/chat` is the
  surface; both tiers expose it, both tiers route the same way.
- ❌ Adding an LLM provider to Tier 1 that breaks the one-liner
  install. Any multi-provider work on Tier 1 must keep Copilot as
  the zero-config default (Article V). Default posture: don't add
  one — put provider choice on the cloud-deploy side where it
  already lives.
- ❌ "It works in Tier 1, we'll figure out Tier 2 later." Contract
  parity is asserted per-PR, not deferred to a migration window.

### How we enforce it

- `rapp_swarm/build.sh` vendors `brainstem.py` (and its direct
  dependencies) into `rapp_swarm/_vendored/`. `function_app.py` is a
  thin Azure Functions adapter over `brainstem.py`'s `/chat` handler.
- A regression test deploys the same bundle against Tier 1 and Tier 2
  and diffs the `/chat` response for a fixed conversation. Divergence
  fails the check.
- If you change `brainstem.py` and don't re-run `build.sh`, you have
  shipped drift. The build script is part of the PR, not a follow-up.

---

## Article XVI — The Root Is the Engine's Public Surface; the Brainstem's Workspace Is Separate

The root of `rapp_brainstem/` is the first thing a new user sees when
they clone the repo. Every file there competes for their attention.
A sprawling root signals complexity and pushes adoption downhill.

Two surfaces, two masters:

> **`agents/` + root = the engine's public surface — what we ship to
> the user. The brainstem's workspace = where the brainstem dumps
> scratch while working for the user. Don't collapse them.**

### What belongs at `rapp_brainstem/` root (the engine's surface)

- `brainstem.py` — the Flask server.
- `soul.md` — the default system prompt.
- `VERSION`, `requirements.txt` — build/deploy metadata.
- `start.sh`, `start.ps1` — the one-liner's launchers.
- `README.md`, `CLAUDE.md`, `CONSTITUTION.md` — docs and governance.
- `index.html` — the landing page.
- **`agents/`** — the starter agents. This is load-bearing for the
  training story: users clone the repo, open `agents/`, and see what
  a RAPP agent looks like. Drag-and-drop visible, editable, published
  as the reference implementation. **Do not move `agents/` into the
  brainstem workspace** — that would bury the thing users are meant
  to learn from.
- `utils/`, `web/` — cohesive support directories.
- `local_storage.py`, `basic_agent.py`, `_basic_agent_shim.py` — the
  base contracts agents extend.

### What belongs in the brainstem's workspace (scratch while running)

Everything that is **written by the brainstem as it serves the user**
— as opposed to edited by the user or shipped by the engine:

- Per-user memory files, binder state (`.binder.json`),
  `.twin_calibration.jsonl`, telemetry logs, saved sessions.

The pathing follows the same pattern the memory agents have used
since day one: a single env var overrides the default, and the
default is a simple directory outside the repo.

```python
def _memory_path():
    p = os.environ.get("BRAINSTEM_MEMORY_PATH")
    return p if p else os.path.expanduser("~/.brainstem/memory.json")
```

Category conventions today:

- `~/.brainstem/memory.json` — `BRAINSTEM_MEMORY_PATH` override.
- `~/.brainstem/swarms/<guid>/…` — `BRAINSTEM_SWARMS_PATH` override.
- New categories get the same shape: one env var, one home-relative
  default, no cwd heuristics, no multi-tier fallbacks.

Tier 2 (cloud) sets the env var to a mounted Azure Files path so the
same agent files serve isolated tenants without modification.

### What this rules out

- ❌ Dropping `foo_agent.py`, `scratch.py`, or `admin_tool.py` at
  root. Agent files live in `agents/` (or `agents/experimental/`).
- ❌ Top-level JSON state files (`.swarms.json`, `.agent_groups.json`,
  `.binder.json`) sitting next to `brainstem.py`. These are runtime
  state; they belong in the brainstem's workspace and are either
  gitignored or never tracked.
- ❌ Moving `agents/` out of root. It is the training surface.
- ❌ Adding a new top-level directory "because it doesn't fit
  anywhere else." If it doesn't fit anywhere else, it's workspace
  scratch — give it a category under the brainstem's workspace.
- ❌ Seeding default runtime state on install. The user's twin starts
  empty; the engine seeds nothing into the workspace.
- ❌ Three-tier cwd/home/env fallbacks for path resolution. Match
  the memory-agent pattern: one env var, one default. Simpler.

### Why two surfaces

The engine's root surface is the curriculum. New users read it,
understand what the platform is, and copy-paste agents to learn. The
brainstem's workspace is the operator's reality — memory, state,
deployed swarms, session dumps. Keeping them separate means we can
grow the workspace indefinitely without ever obscuring the learning
path.

### The same discipline applies to the **repo** root

The repo root is the storefront — what someone sees the moment they
land on the GitHub page. It must read at a glance: *this is a
three-tier engine, here is how you install it, here are the canonical
docs.* A bloated root signals an unfinished project and pushes
visitors away before the first scroll.

> **Reorganized 2026-04-24 (memorialized in
> [[Repo Root Reorganization 2026-04-24|the vault]]).** Almost
> everything that was at root moved into a subdirectory. The list
> below is the *floor* of root residence, not a buffet.

What earns repo-root residence (the closed list):

- **The two tier code directories** — `rapp_brainstem/` (Tier 1) and
  `rapp_swarm/` (Tier 2). Each contains the running code for its
  tier. Tier 3 (Microsoft Copilot Studio) has no running code in
  this repo — it runs in Microsoft's cloud. Tier 3 ships as a
  download (`installer/MSFTAIBASMultiAgentCopilot_*.zip`), not as a
  tier directory. **Resist the pull of symmetry**: a directory
  earns root residence by holding running code, not by completing a
  numbered list.
- **`worker/`** — Cloudflare auth/proxy worker shared across tiers.
- **The catalog** — lives in its own repo at [`kody-w/rapp_store`](https://github.com/kody-w/rapp_store) since 2026-04-26. Brainstem fetches `index.json` from there via `RAPPSTORE_URL`. Hosted viewer at https://kody-w.github.io/RAPP_Store/.
- **The install surface** — `installer/`. Public URLs route through
  this subpath; everything inside is meant to be downloaded or
  curl-piped by a user. Holds the one-liners (`install.sh`,
  `install.ps1`, `install.cmd`), the swarm installer
  (`install-swarm.sh`), the local launcher (`start-local.sh`), the
  ARM template (`azuredeploy.json`), the install-widget mirror
  (`index.html`), and the **Tier 3 Copilot Studio bundle**
  (`MSFTAIBASMultiAgentCopilot_*.zip`). All install URLs:
  `https://kody-w.github.io/RAPP/installer/<file>`.
- **The cross-tier test runner** — `tests/`.
- **`pages/` — the GitHub Pages publication surface, structured as a
  full site, not a folder of orphan pages.** Everything served from
  `https://kody-w.github.io/RAPP/pages/...` lives here, sectioned by
  audience:
  - `pages/index.html` — the site landing.
  - `pages/about/` — leadership, partners, process, security.
  - `pages/product/` — faq, faq-slide, one-pager, use-cases.
  - `pages/release/` — release-notes, roadmap.
  - `pages/docs/` — reference markdown (`SPEC.md`, `ROADMAP.md`,
    `AGENTS.md`, `VERSIONS.md`, `skill.md`, `rapplication-sdk.md`)
    rendered through `pages/docs/viewer.html` with a docs landing at
    `pages/docs/index.html`.
  - `pages/vault/` — long-term memory: the Obsidian vault notes
    plus the static SPA viewer (`pages/vault/index.html`). See
    [[#Article XXIII — The Vault Is the Long-Term Memory|Article XXIII]].
  - `pages/_site/` — **shared site infrastructure**. Underscore prefix
    marks it as not-a-page: tokens/base/components/doc CSS in `css/`,
    theme + chrome + doc-viewer JS in `js/`, header + footer markup
    in `partials/`, and `index.json` as the canonical site manifest.
    Every page links to `_site/css/*.css` and includes `_site/js/site.js`,
    so the design system has one source of truth. New pages drop into
    the matching section subdirectory and reuse the same chrome — no
    inline 200-line CSS duplication.
  - `pages/404.html` — pretty 404 with a sitemap.
  The unifying rule: anything served to a public visitor (whether
  human-shaped HTML, AI-shaped markdown reference, or the *why*
  behind decisions) lives somewhere under `pages/`. Code stays in
  tier directories; everything *served* lives in `pages/`. Adding a
  new page = drop it into the right section + add one line to
  `_site/index.json`. Adding a section = new subdirectory plus a
  manifest entry.
- **`README.md`** — must be at root because GitHub renders it on the
  repo page. Acts as the catalog card and links into `pages/docs/`,
  `pages/vault/`, and `CONSTITUTION.md` for the rest.
- **`CONSTITUTION.md`** — this file. Lives at repo root, peer to
  `README.md`, because governance is part of the catalog card.
  GitHub recognizes top-level governance files (LICENSE,
  CODE_OF_CONDUCT, CONTRIBUTING) as community-standards anchors;
  this article holds CONSTITUTION.md to the same level. A visitor
  who lands on the repo page sees *what this is* (`README.md`) and
  *the rules it lives by* (`CONSTITUTION.md`) at the same scroll
  depth — the spec, the roadmap, and the rest live one click in.
- **`CLAUDE.md`** — Claude Code reads project instructions from the
  project root.
- **`index.html`** — GitHub Pages serves the repo root; this is the
  landing page.
- **`pitch-playbook.html`** — its public URL has been shared
  externally and is load-bearing for partner conversations. Cannot
  move without breaking shared links. New audience pages go in
  `pages/`; this is the only marketing HTML at root, by exception
  rather than by precedent.
- **Repo plumbing** — `.gitignore`, `.nojekyll`, `.env`/`.env.example`,
  `.github/`, `.vscode/`, `.claude/`. Tools and git itself require
  these at root.

Each kept top-level subdirectory is **self-documenting**. `pages/`,
`pages/docs/`, `installer/`, and `tests/` each hold a `README.md` that
states the local rule of residence — what belongs there, what doesn't,
and what naming convention to follow. The repo-root rule (this
article) is the spine; the per-directory README is the rib. New
contributors don't have to grep the constitution to know where a new
file goes — they read the README of the directory they're about to
add to.

Everything else lives in a subfolder. The exhaustive map of where
*moved* things now live:

- Install scripts, ARM template, Tier 3 Studio bundle → `installer/`.
- `SPEC.md`, `ROADMAP.md`, `AGENTS.md`, `VERSIONS.md`, `skill.md`,
  `rapplication-sdk.md` → `pages/docs/` (briefly lived in `docs/` at
  root on 2026-04-24, then folded under `pages/` once the unifying
  rule "anything served lives in `pages/`" was articulated).
- The Obsidian vault → `pages/vault/` (briefly at `vault/` at root,
  same-day move under `pages/`). The viewer and the markdown share
  one directory.
- `CONSTITUTION.md` — stays at root as a peer of `README.md` (was
  briefly moved to `docs/` on 2026-04-24 and restored same session
  — governance is part of the catalog card, not a reference doc).
- New audience HTML → `pages/<file>.html`.
- New reference markdown → `pages/docs/`.
- Decision narratives, removal stories, manifestos → `pages/vault/`
  (a real Obsidian vault, governed by Article XXIII).

### What this rules out (repo root)

- ❌ Dropping the next marketing page at root because the previous
  one happened to land there. New page → `pages/<file>.html`.
  `pitch-playbook.html` is the *only* grandfathered exception, and
  only because its URL is in circulation.
- ❌ Adding `notes-on-X.md` next to `README.md` because it's "just
  one more". Auxiliary reference markdown → `pages/docs/`.
  Decision narrative / *why* essays → `pages/vault/`.
- ❌ Putting any new install-related file at root. New launcher,
  new platform install, new ARM template, new downloadable bundle
  → `installer/`.
- ❌ Creating a new top-level `rapp_<tier>/` directory for an
  artifact that has no running code. Tier 1 and Tier 2 have
  directories because there is *code that runs in this repo*. Tier 3
  is a download from `installer/` because the running code lives in
  Microsoft's cloud, not here. The Copilot Studio `.zip` was briefly
  placed in `rapp_studio/` on 2026-04-24 and folded back into
  `installer/` the same day — the symmetry of three tier directories
  was overfitting; the actual rule is *code earns a directory,
  artifacts don't*.
- ❌ Hardcoding `https://kody-w.github.io/RAPP/<file>` in a moved
  file. When you relocate a page, update its `og:url`,
  `canonical_url`, and any test fixtures so the move is honest.
- ❌ Adding a new top-level directory because nothing else fits. If
  it's audience HTML, it fits in `pages/`. If it's reference
  markdown, it fits in `pages/docs/`. If it's a vault note, it fits
  in `pages/vault/`. If it's an install artifact, it fits in
  `installer/`. A new top-level directory is justified only when
  there is a cohesive body of *running code* that doesn't fit any
  existing tier — and even then, justify it the same way you'd
  justify a new `|||<SLOT>|||` (Article II).
- ❌ Letting a `git pull` pollute root by accident. After a merge
  that lands new files at the top level, the next move is to
  re-home them under `installer/`, `pages/`, `pages/docs/`,
  `pages/vault/`, or the appropriate `rapp_<tier>/` directory — not
  to ratify them as root residents.
- ❌ Adding a top-level subdirectory without a `README.md`. The
  scale rule for that subdir lives at its own root. If the new
  directory deserves to exist, write the README that says when to
  add to it and when not to.

The two roots — repo and `rapp_brainstem/` — share one discipline:
**the root is the catalog card, not the junk drawer.**

---

## Article XVII — `agents/` IS the User's Workspace

`rapp_brainstem/agents/` is **the user's entire operational workspace**
for setting up and managing their brainstem. To add a capability,
organize a swarm, group a project's agents, turn something off — all
of it happens inside `agents/`. Nothing else is supposed to be touched.

> **Engine files are for the engine. `agents/` is for the user.
> Everything functional a user needs to do happens in `agents/`.**

The engine (`brainstem.py`, `VERSION`, `soul.md`, `requirements.txt`,
`start.sh`, the `utils/` and `web/` trees) is a stable, boring
surface. Users rarely read it and never edit it. The user's focus is
inside `agents/`.

### A recursive, user-organized tree

`agents/` is a **recursive tree** with no depth limit. Drop a `*_agent.py`
file anywhere under it and the brainstem finds it. Make any
subdirectory you want to group related agents — the engine doesn't
care about folder names. Subdirectories themselves can contain more
subdirectories. `agents/sales_stack/q4/prospects/outbound_agent.py`
auto-loads exactly like `agents/outbound_agent.py`.

Two subdirectory names are reserved by the engine — they never
auto-load: **`experimental_agents/`** (in-flight work, hand-load only)
and **`disabled_agents/`** (turned off, move a file there to disable
it without deleting). Everything else under `agents/` loads.

### What's at the top level of `agents/` by default (the starter set)

- `basic_agent.py` — the base class every agent extends.
- `hacker_news_agent.py` — HTTP call example.
- `learn_new_agent.py` — agent that writes agents.
- `save_memory_agent.py` + `recall_memory_agent.py` — the memory pair.

These five files are the teaching curriculum. A new user opening
`agents/` sees exactly this and understands what a RAPP agent is. Do
not dump more files at the top level — put the one engine tool
(`swarm_factory_agent.py`) under `workspace_agents/`, put user
groupings in a named subdir.

### Engine-provided subdirectories (conventions, not magic)

- **`agents/workspace_agents/`** — the shop. Houses the one ship-in-
  repo engine agent (`swarm_factory_agent.py`) plus every
  organizational subdirectory (experimental, disabled, local, user
  folders). Auto-loads recursively.
- **`agents/workspace_agents/experimental_agents/`** — never auto-
  loads. In-flight work the user hand-loads when testing. Keeps
  `agents/` clean of half-finished files.
- **`agents/workspace_agents/disabled_agents/`** — never auto-loads.
  Move an agent file here to turn it off without deleting. The
  filesystem itself records "off."

### User-organized subdirectories (the whole point)

Anything else the user creates under `agents/` auto-loads. Examples:

- `agents/sales_stack/` — a user's sales-focused bundle.
- `agents/personal_twin/` — their personal-assistant agents.
- `agents/project_x_swarm/` — agents grouped by project.
- `agents/ceo_twin/roles/` — even nested subdirs work.

No registration, no config, no env var. Drop a folder in, put
`*_agent.py` files inside, they load. That's the contract.

### What this rules out

- ❌ Making users edit engine files to do things a brainstem exists
  to do. If a user wants to add a capability, change behavior, or
  reorganize their setup, the answer is always something inside
  `agents/` (or `soul.md` for persona, `.env` for creds). Never
  "open `brainstem.py` and edit…"
- ❌ A registration file (`agents.json`, `registry.yaml`) listing
  which agents to load. Discovery is filesystem-only.
- ❌ A "brainstem config" directory outside `agents/` that users
  are expected to edit. The user's entire config surface is:
  `soul.md`, `.env`, the `agents/` tree.
- ❌ Engine-imposed subdir categories beyond the reserved names
  (`experimental_agents/`, `disabled_agents/`, `local_agents/`).
  The user owns naming inside `workspace_agents/`.
- ❌ Importing `from agents.workspace_agents.X import ...` in tests.
  Tests load nested-subdir agents by file path via `importlib`; the
  `agents.*` module namespace is for the base class shim only.
- ❌ Dumping more than the curriculum files at the top level of
  `agents/`. The top level is the curriculum — the engine tool
  (`swarm_factory_agent.py`) lives under `workspace_agents/`, user
  organization goes in user-named subdirs (arbitrarily deep).
- ❌ Re-introducing a `system_agents/` bucket. One less folder, one
  less concept to teach.
- ❌ Any depth limit on `agents/` recursion. Users pick their
  own structure.

### Discovery rules

- `brainstem.py` `load_agents()` walks `agents/` recursively via
  `rglob("*_agent.py")`. Skips any path that contains
  `experimental_agents/`, `disabled_agents/`, or `__pycache__/` as
  an intermediate directory.
- The shim `sys.modules["agents.basic_agent"]` makes
  `from agents.basic_agent import BasicAgent` resolve from any
  agent file at any depth.
- `rapp_swarm/build.sh` vendors the `agents/` tree recursively with
  the same exclusions, so Tier 2 mirrors Tier 1's user-organized
  shape exactly.

---

## Article XVIII — The Management UI Is a View Onto `agents/`

The brainstem's management UI — the browser interface served by the
brainstem and anything built on top of it — is **a view onto the
`agents/` tree**. Every user-facing action in the UI corresponds 1:1
to a filesystem operation inside `agents/`. The UI never invents a
parallel model; it abstracts the filesystem so users don't have to
see files, paths, or Python.

> **UI tree = `agents/` tree. UI operation = filesystem operation on
> `agents/`. No UI-only concepts that don't exist on disk.**

### The mapping

| UI action                 | Filesystem operation                                |
|---------------------------|-----------------------------------------------------|
| "New agent"               | write a new `*_agent.py` at the chosen tree location |
| "New folder"              | `mkdir` under `agents/`                             |
| "Move" (drag-drop)        | `mv` between directories in `agents/`               |
| "Rename"                  | `mv` with a new name                                |
| "Delete"                  | `rm` the file                                       |
| "Disable"                 | move the file into `agents/disabled_agents/`        |
| "Enable"                  | move it back out of `disabled_agents/`              |
| "Mark experimental"       | move into `agents/experimental_agents/`             |
| "Edit"                    | open the `*_agent.py` in an inline editor          |

The engine-reserved subdirs (`experimental_agents/`,
`disabled_agents/`) are visible in the UI with their semantics
(experimental won't auto-load, disabled is off). The UI doesn't hide
them — users benefit from seeing what's parked and what's turned off.

### What the UI covers (the user's full config surface)

The user's entire operational surface per Article XVII is `soul.md` +
`.env` + the `agents/` tree. The UI covers all three:

- **Persona editor** — edit `soul.md` inline.
- **Creds / config** — safe form for `.env` fields (tokens, models,
  toggles). No free-form editing of engine files.
- **Agent tree** — the main view, as described above.

Plus diagnostic readouts the UI can show without being configuration:
health, LLM provider status, loaded-agent count, Copilot auth status.
These are read-only.

### What this rules out

- ❌ UI-only organizational concepts. If the UI shows "tags,"
  "categories," or "collections," they must exist in the filesystem
  (manifest field, subdir name) — never UI-local state that doesn't
  round-trip.
- ❌ A fourth configuration surface in the UI. Users don't edit
  `brainstem.py`, `VERSION`, `requirements.txt`, or the `utils/`
  tree through the UI — those are engine internals.
- ❌ A separate "agent registry" the UI writes to alongside the
  filesystem. Filesystem IS the registry.
- ❌ Hiding the reserved subdirs. Users should see
  `experimental_agents/` and `disabled_agents/` in their tree —
  that's how they know what's going on.
- ❌ UI actions that have no filesystem equivalent. If the UI can do
  it, the filesystem can do it. `agents/` is the truth.

### Why this discipline

If the UI invents concepts that don't exist on disk, the filesystem
and the UI drift apart. Users who edit `agents/` directly (via their
editor, a script, or a drag-drop into the folder) get a different
reality from users who edit via the UI. The brainstem is supposed to
auto-discover whatever's on disk; keeping the UI 1:1 with the
filesystem preserves that contract.

---

## Article XIX — Versions Are Load-Bearing Rollback Points

`rapp_brainstem/VERSION` is the source of truth for what's running.
Every released VERSION is also a git tag `brainstem-vX.Y.Z`, and those
tags are **immutable**. They are the rollback contract with users.

> **If a release breaks, users must be able to pin to a prior working
> version with one command.** The one-liner already supports this:
>
> ```bash
> BRAINSTEM_VERSION=0.9.0 curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash
> ```
>
> For that to keep working, every VERSION bump on main must ship a
> matching `brainstem-vX.Y.Z` tag, and published tags must never move.

### Release discipline

- **Bump + tag together.** The commit that bumps `VERSION` to `X.Y.Z`
  gets tagged `brainstem-vX.Y.Z` (typically the merge commit on main).
  No version bump without the matching tag push.
- **Tags are immutable.** Never `git tag -f` or `git push --force` a
  brainstem-v tag. A user who pinned to `0.9.0` six months ago must
  get the same tree today.
- **No gaps.** `0.9.0 → 0.10.0` is fine. `0.9.0 → 0.11.0` with
  `0.10.0` skipped leaves a hole in the rollback path.
- **Bad release? New tag.** If `0.9.0` shipped broken, the fix is
  `0.9.1`, not a rewritten `0.9.0`. The bad tag stays so users who
  pinned to it aren't surprised.
- **Installer contract.** The one-liner MUST honor `BRAINSTEM_VERSION`
  and MUST warn (not silently skip) if a requested tag doesn't exist.

### What this rules out

- ❌ Untagged releases. A VERSION bump without the corresponding tag
  pushed to origin is incomplete.
- ❌ Moving or deleting a published tag.
- ❌ Silent behavior changes across a tag boundary. If a release
  changes agent contract, route surface, response envelope — bump
  the version.
- ❌ Installer changes that drop `BRAINSTEM_VERSION` pinning support.

This is what keeps the one-liner (Article V) honest: not just
"install the latest" but "let users roll back when the latest breaks."

---

## Article XX — UI Defaults to Beginner-First; Advanced Is Opt-In

The `/manage` UI has two modes driven by a single **Advanced** toggle.
Every user-facing surface defaults to the beginner view; technical
detail is revealed only when the user asks for it.

> **Default = beginner. Advanced = power user. Never show raw
> filenames, raw env keys, or reserved internals in default mode.**

### Beginner view (default)

- **Human names.** `save_memory_agent.py` renders as "Save Memory".
  `my_stack/` renders as "My Stack". Strip `_agent.py`, replace `_`
  with spaces, title-case words.
- **Dropdowns and toggles, not text fields.** If a setting is
  bounded (model choice, voice on/off, twin on/off), render a
  `<select>` or a toggle switch. Text inputs are a last resort for
  free-form values (URLs, custom strings).
- **Friendly service names.** "GitHub Copilot — Connected ✓" instead
  of `GITHUB_TOKEN: set`.
- **Reserved folders hidden.** `experimental_agents/` and
  `disabled_agents/` are filtered out of the tree view entirely.
- **Folders collapsed on load.** Users expand what they want to
  explore, not drown in a wall of nested paths.
- **Curated field set.** Only the settings a learner needs — model,
  voice, twin, connection status.

### Advanced view (opt-in via toggle)

- Raw filenames with `_agent.py` extensions so engineers reason
  about paths.
- Reserved folders visible with their directory names annotated
  alongside friendly labels ("Parked — `experimental_agents/`").
- Full `.env` editor: every whitelisted key as a field. Bounded
  values still render as selects, free-form as text.
- Secret chips with raw env key names (`GITHUB_TOKEN: set`).
- Additional fields (Azure endpoint, Azure deployment, etc.) that
  don't belong in the beginner's path.

### What this rules out

- ❌ Showing `snake_case_agent.py` filenames in default mode.
- ❌ Rendering "`VOICE_MODE (true / false)`" as a text input in any
  mode. Bounded = dropdown/toggle, always.
- ❌ Exposing reserved folders by default. The three reserved names
  are engine-internal; beginners don't need to care.
- ❌ Separate backend endpoints for "simple" vs "advanced" — both
  modes save to the same underlying `.env` / filesystem. Mode is a
  rendering concern, not a data concern.
- ❌ Losing form state when the user flips the toggle mid-edit.
  Both views bind to the same `data-env="KEY"` attribute so edits
  persist across mode changes.
- ❌ Using the Advanced toggle to gate features — it only gates
  *visibility*. A beginner can always do everything they need from
  the beginner view; Advanced is additive, not unlocked.

### Why two modes, not two apps

A second UI (power-user dashboard) would split maintenance and tempt
feature drift. One UI with a visibility toggle forces every new
setting to pass the beginner-design bar first: *what's the friendly
version of this?* If the answer is "there isn't one," the setting
probably doesn't belong in the UI at all — put it in the `.env`
file directly.

---

## Article XXI — Every Twin Surface Is a Calibration Opportunity

The digital twin (`|||TWIN|||` panel, action pills, present-card
lines, any other twin-owned surface) exists to **build fidelity with
the user** — each turn is the twin's chance to predict something
about the user and let the user's next action validate, contradict,
or silently pass on that prediction. That feedback loop is how twin
accuracy grows.

> **Twin surface = the twin's bet. Click = "you're right about me."
> Ignore = signal the other way. Help-shaped prompts waste the slot.**

Help-shaped prompts ("What should I build next?", "How do I deploy?")
are what the **main assistant reply** is for. The twin's job is
different. A twin surface that gives back generic help is a turn
the twin learned nothing from — and fidelity stalls.

### Calibration-shaped (right)

Labels are predictions. The user's click vs. ignore vs. pushback is
the data:

- `<action kind="send" label="I think you prefer X. Right?">…</action>`
- `<action kind="send" label="Still want to ship today?">…</action>`
- `<action kind="send" label="You mentioned Foo last week — do that?">…</action>`
- `<action kind="prompt" label="Pin this as a priority?">…</action>`

Each calibration-shaped action pairs with a `<probe>` so the twin
self-judges on the next turn via `<calibration>`. That loop is the
point.

### Help-shaped (wrong)

Anything that doesn't imply a bet about the user. These are the main
assistant's job:

- ❌ "What can you do?"
- ❌ "Browse my agents"
- ❌ "How do I deploy to Azure?"
- ❌ "Help me build a new tool"

### What this rules out

- ❌ Twin action labels that aren't predictions about the user.
- ❌ Using twin surfaces for navigation ("Browse my agents") when
  the assistant's main reply could have offered the same thing.
- ❌ Emitting an `<action>` without a paired `<probe>` — the bet
  must be recorded so the next turn can judge it.
- ❌ A static fallback starter prompt that's help-shaped. The
  user's first turn is the twin's first data point; don't waste it.
- ❌ Confusing twin voice with assistant voice. The twin speaks
  first-person AS the user TO the user. Predictions, not answers.

### Why this matters

The twin calibration log (`.twin_calibration.jsonl`) scores the twin
on whether its probes got validated or contradicted by subsequent
user behavior. If the twin keeps offering generic help, every probe
is vague — "confidence: 0.3, subject: 'user might want help'" — and
the accuracy feedback is noise. Calibration-shaped actions make
probes sharp: "priority-claim on PR#123, 0.7 confidence" either
holds up or doesn't. Sharp probes grow the twin faster.

---

## Article XXII — One Twin, Two Faces

The brainstem hosts **one entity**: the user's digital twin. There is
no separate "assistant" character alongside a "twin" character. The
two visible surfaces are two *faces of the same twin*, with different
purposes:

> **Main reply = the twin doing the task AS the user. Hologram /
> |||TWIN||| panel = the same twin showing its current fidelity
> state (progress toward being that person).**

- **Main reply** (content before `|||VOICE|||`): the twin at work.
  First-person from the user's perspective — answering as the user
  would answer, choosing as the user would choose. "Me, handling
  this for you, as you."
- **|||VOICE|||**: a TTS-friendly version of that same voice.
- **|||TWIN||| panel**: the twin's **rubber-duck surface**. Not a
  status report. Not a progress bar. Not "I'm 73% you." The twin
  thinks out loud about an *assumption it's currently making about
  the user*, phrased so the user can correct it on the fly. The
  twin is asking to be taught. Disagreement refines; confirmation
  locks the belief. Same identity as the main reply — just angled
  inward, looking for the user's correction.

### Why this matters

Treating them as two entities produces schizophrenic prompting and
generic output — "assistant answers question, then twin character
comments on answer." That's theatre, not fidelity-building. The one-
twin framing makes every render honest: the main reply earns its
place by being genuinely the-user-in-action; the twin panel earns
its place by being a truthful fidelity snapshot.

### What this rules out

- ❌ System-prompt language that addresses the model as an "assistant
  who should also simulate a twin." The model *is* the twin.
- ❌ UI framing that suggests the chat reply and the hologram are
  separate personalities or separate advisors.
- ❌ Main-reply content that sounds like a generic AI assistant
  instead of the user's proxy voice.
- ❌ Twin-panel content that reads like third-person commentary on
  the user ("The user seems to be…"). The twin speaks in first-
  person as the user, even when reflecting on its own fidelity
  ("I'm not sure yet whether I'd actually…", "Last week I said I'd…").
- ❌ Blurring the two faces: putting fidelity-state material in the
  main reply, or putting task answers in the twin panel.

### The hologram

The visual globe is not decoration. It represents the twin *present
with you in the conversation* — listening, currently guessing, ready
to be corrected. The caption reads "Your twin." Whatever mood or
animation the hologram shows, its meaning is always: "I'm here,
I'm guessing, teach me."

### The rubber-duck pattern

Concrete shapes a well-formed |||TWIN||| block takes (pick at most
one per turn):

- **I'm assuming:** <belief about the user>. Right?
- **My guess:** you'd rather <X>. True?
- **Learning:** you'd call this <name>, not <other name>. Am I close?
- **Rubber-duck me:** walk me through <thing> so I can copy your
  instinct.

Each one is the twin's current working hypothesis, stated simply so
the user can say "yes," "no, actually…", or "close but…". The
correction is the whole point.

---

## Article XXIII — The Vault Is the Long-Term Memory

Code captures *what*. Commit messages capture *what changed*. The
constitution captures *the rules*. None of those capture *why a
decision was made the way it was, what was rejected, and what we
learned from the things we deleted*.

That knowledge is the most fragile thing the project owns. It rots
within weeks if it isn't written down, and once it's gone it doesn't
come back — the next contributor will re-make the same mistake without
even knowing they're repeating one.

> **The repo's `pages/vault/` directory is the load-bearing answer.
> It is a real Obsidian vault, openable as-is, and it is the home
> for every blog-post-shaped thought the platform has.**

### What the vault is for

The vault holds the long-form *why* behind decisions, in note form:

- **Founding decisions** — the rejected alternatives, the close calls.
- **Removals** — code that was deleted and the lesson it taught us.
  These rot fastest, because the code is already gone.
- **Architecture moments** — the clever tricks that look weird at
  first glance and would be "cleaned up" by a refactor that didn't
  know better.
- **Positioning** — the honest tradeoffs, the anti-pitch, the framing
  we use with prospects.
- **Twin & UX philosophy** — the worked examples behind the rules in
  Articles IX–X and XX–XXII.
- **Process stories** — how a workshop actually runs, what makes a
  60-minute session land, what doesn't.
- **Manifestos** — the short essays that turn one-line slogans
  ("engine, not experience"; "three tiers, one model") into something
  a contributor can defend in a code review.

### The two-state lifecycle

Every note has `status: stub` or `status: published` in its
frontmatter.

- **Stub.** The slot is held: title, hook, pointers to related notes,
  why this would rot if not written. This is the wiki saying "this
  topic exists; the post hasn't shipped yet." Stubs cost nothing and
  prevent the topic from being forgotten.
- **Published.** The full essay. The bar is one thing: *the why is
  captured well enough that someone who wasn't in the room can apply
  it.*

A stub becoming published is a real release. The reverse — a published
note being demoted back to a stub — happens only if the post was wrong;
it doesn't happen because the topic became unfashionable.

### Two faces, one directory

The vault has two faces, both load-bearing, and they share one
directory: `pages/vault/`.

1. **The vault data** — the markdown files under `pages/vault/`.
   Real wikilinks, real frontmatter, openable directly in any
   Obsidian client via *File → Open folder as vault*. The data is
   the source of truth.
2. **The static viewer** — `pages/vault/index.html` (plus its JS).
   Loads the same markdown files (sibling paths on GitHub Pages,
   raw GitHub as fallback), renders wikilinks and backlinks,
   exports the entire vault as an Obsidian-compatible zip, and
   imports a zip back to override the live source for offline
   reading.

Both must keep working. Either one breaking is a P1 — not because the
viewer is precious, but because *the discipline of writing the post
relies on the post being readable in two different places.*

The data and viewer were briefly split (`vault/` for the data,
`pages/vault/` for the viewer) but folded into one directory on
2026-04-24 once the unifying *anything-served-lives-in-pages/* rule
was articulated. One directory, two faces — see
[[Repo Root Reorganization 2026-04-24]] in the vault for the why.

### What this rules out

- ❌ Burying decision rationale in commit messages, PR descriptions,
  or chat. Those have no future reader. The vault has a future
  reader by construction.
- ❌ Putting an "ARCHITECTURE.md" or "DECISIONS.md" at the repo
  root. The right home for that content is a vault note, with a
  hook line, frontmatter, and wikilinks.
- ❌ Letting the viewer drift from the vault. If you rename or move
  a note, update `_manifest.json` in the same change.
- ❌ Skipping the stub. If a topic deserves a post but the post
  isn't ready, ship the stub. The slot in the index is itself a
  forcing function.
- ❌ Treating the vault as documentation. Documentation is in
  `pages/docs/`, `README.md`, and the per-tier docs. The vault is
  *why*, not *how*.
- ❌ Generating notes from templates with no specific content. A
  stub is short on purpose; an LLM-padded "stub" defeats the point.

### Why this is constitutional

If the only people who know why a decision was made are the people
who made it, the platform is one resignation away from forgetting why
anything works. The vault is the discipline that keeps that from
happening — and unless it's load-bearing in the constitution, it
will quietly stop being maintained the moment someone is in a hurry.

The engine stays small. The agents can be everything. *And the vault
remembers why we made it that way.*

---

## Article XXIV — Senses Are Agent-First; Frontends Are Modular Consumers

The agent's response channels are the agent's **senses**. The agent
emits every sense unconditionally on every reply. Frontends are
modular consumers — each one picks the senses it cares about and
ignores the rest.

### What a sense IS — and what it isn't

**A sense is a TRANSLATION of the main response into a different mode
of expression.** Same answer, different channel. VOICE is the
response, said aloud. TWIN is the response, expressed as a felt
reaction. HAIKU is the response, distilled to 5/7/5. ELI5 is the
response, re-explained for a five-year-old.

A sense is NOT new content. A sense is NOT a tool call. A sense is NOT
a separate query. If the channel produces *new information* — a
diagram derived from data, a memory persisted to disk, a search across
a corpus — that is an **agent**, not a sense. Agents do work and
return data; senses re-perceive what the agent already said.

The litmus test: *does removing this channel reduce what the agent
KNOWS, or only how the agent EXPRESSES it?* If knowledge: agent. If
expression: sense.

### Bundled senses today

- **`voice_response`** (`|||VOICE|||`) — the response, spoken aloud.
  Frontends with TTS read it and speak.
- **`twin_response`** (`|||TWIN|||`) — the response, as the operator-
  twin's tiny ASCII reaction. Frontends render in a panel; the
  brainstem operator's terminal renders the `<frame>` as a cage.

**More senses live in the catalog** under `senses/` in
[`kody-w/rapp_store`](https://github.com/kody-w/rapp_store) — each a single
`*_sense.py` file. Drop one in `rapp_brainstem/utils/senses/` and it's
installed; delete it and it's gone.
A dog that wakes up with three legs makes the best of it; the agent
that loses a sense keeps its identity, just with one fewer mode of
expression.

### Single-file senses (the pattern)

Senses follow the same single-file discipline as agents (Article III).
Each `*_sense.py` exposes four module-level vars:

```python
name           = "haiku"          # short id used by the splitter
delimiter      = "|||HAIKU|||"    # fixed forever once allocated (Article II)
response_key   = "haiku_response" # field name in the chat envelope
system_prompt  = "After your main reply, append `|||HAIKU|||` followed by ..."
# wrapper_tag (optional) — XML wrapper the LLM may use; defaults to `name`
```

That's the whole contract. The brainstem auto-discovers `*_sense.py`
files in `SENSES_PATH`, composes their `system_prompt` fragments into
the system message as a layer below the soul, and splits the LLM's
reply by their delimiters into `result[response_key]`. No other
brainstem changes are required to add a sense.

### What this rules out

- **Frontend buttons that POST to the server to "enable" a sense.**
  A mic button does not call `/voice/toggle`. A twin-panel show
  button does not call `/twin/toggle`. UI toggles that relate to a
  sense are *purely local state* — they decide whether THIS browser
  plays / renders / consumes the sense, persisted to localStorage,
  never sent to the server.
- **Frontend init that GETs server state to learn whether the sense
  exists.** No `fetch('/voice')` to learn `voice_mode`. The browser
  decides on its own whether it cares.
- **Backend gates that look at a server-side flag (e.g.
  `VOICE_MODE`) to decide whether to emit a sense.** The chat path
  emits every sense unconditionally. Env-var flags can stay for
  decorative `/voice`, `/twin` status endpoints, but they MUST NOT
  gate the chat-path system prompt or the response splitter.
- **Removing a sense's slot once allocated.** Per Article XXV, the
  chat envelope is additive-only. A sense field, once shipped, is
  shipped forever (it can be empty when the LLM didn't author one
  that turn — but the field key never disappears for clients that
  have already wired up against it).
- **Senses that produce new content.** If the channel needs to do
  work — call an API, read state, run a computation — it's an agent.
  Senses translate; agents produce. Memory is an agent. Diagrams
  are an agent. A sense never reaches outside the LLM's reply.

### What this rules out

- **Frontend buttons that POST to the server to "enable" a sense.**
  A mic button does not call `/voice/toggle`. A twin-panel show
  button does not call `/twin/toggle`. UI toggles that relate to a
  sense are *purely local state* — they decide whether THIS browser
  plays / renders / consumes the sense, persisted to localStorage,
  never sent to the server.
- **Frontend init that GETs server state to learn whether the sense
  exists.** No `fetch('/voice')` to learn `voice_mode`. The browser
  decides on its own whether it cares.
- **Backend gates that look at a server-side flag (e.g.
  `VOICE_MODE`) to decide whether to emit a sense.** The chat path
  emits every sense unconditionally. Env-var flags can stay for
  decorative `/voice`, `/twin` status endpoints, but they MUST NOT
  gate the chat-path system prompt or the response splitter.
- **Removing a sense once allocated.** Per Article XXV, the chat
  envelope is additive-only. A sense field, once shipped, is
  shipped forever (it can be empty when the LLM didn't author one
  that turn — but the field key never disappears).

### Why this matters

- **Modularity.** The same chat response is consumed by the local web
  UI, mobile shells, voice-only embeds, transcription pipelines,
  peer brainstems, MCP clients, and future agents-as-clients. If
  the agent gates on one consumer's UI preference, every other
  consumer is starved. A voice-only embed needs `voice_response`
  whether or not someone else's browser has the mic icon lit.
- **Agent-first (Article III).** Every rapplication must work fully
  through the agent alone. The service / UI is always optional — a
  view, not the application. A view doesn't get to silence the
  agent's outputs.
- **Slots are fixed forever (Article II).** A slot is part of the
  agent contract, not a UI feature. Treating slots as opt-in via UI
  toggles repurposes them as decoration on top of the main reply,
  which is the opposite of what the slot mechanism is for.
- **Decoupled growth.** The organism evolves new senses by adding
  slots; no consumer is required to update. Old clients keep
  reading the senses they already understood; new clients pick up
  the new ones. The chat envelope is the neutral surface that lets
  consumers and senses scale independently.

### The mental model

The agent has senses the way a person has senses. The agent doesn't
ask "should I have hearing today?" — it just hears, and reports
what it heard, every turn. Other entities decide whether they care
about that report. A blind reader doesn't ask the speaker to stop
seeing; they just don't read the visual fields.

The brainstem's job is to make sure every sense fires every turn,
into the chat envelope, where any consumer can pick it up. New
senses are additions to the brainstem's perception, not features
that get toggled on per-client.

---

## Article XXV — Chat Is The Only Wire (Time-Travel Safe)

`/chat` is the universal interface. A human typing into the chat UI, an
agent invoking another agent, a peer brainstem reaching across the
network, and an MCP client over stdio all hit the **same endpoint with
the same envelope and get back the same envelope**. The brainstem does
not know — and must never need to know — which kind of caller is on
the other end.

> **One wire. Same shape. Forever.**
>
> A brainstem unearthed from a backup, a probe, a frozen Docker image,
> or a cold-storage drive after eons must be revivable and able to
> chat with the latest brainstem **without a single code change on
> either side**. Neither one knows — neither one needs to know — what
> year the other was built in. Caller type and caller vintage are
> equally irrelevant. The wire is the contract, and contracts hold
> across time.

This is what makes the brainstem an engine, not a product. Engines
don't care who's pulling the lever, and they don't care when the lever
was made.

### What the wire is

**Request envelope** (POST `/chat`):

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `user_input` | str | yes | The message |
| `conversation_history` | list | no | Prior turns as `{role, content}` |
| `session_id` | str (GUID) | no | Per-conversation; auto-minted if absent |
| `user_guid` | str (GUID) | no | Caller identity; defaults to `DEFAULT_USER_GUID = "c0p110t0-aaaa-bbbb-cccc-123456789abc"` |

**Response envelope** (200 OK):

| Field | Type | Notes |
|-------|------|-------|
| `response` | str | Assistant reply (Tier 1 lineage) |
| `assistant_response` | str | Same value as `response` (CA365/CommunityRAPP/rapp_swarm lineage) — both keys forever |
| `voice_response` | str | When VOICE_MODE on |
| `twin_response` | str | When TWIN_MODE on |
| `session_id` | str | Echoed |
| `user_guid` | str | Echoed |
| `agent_logs` | str | Newline-joined |

Both `response` and `assistant_response` are emitted with identical
content. Tier 1 (`rapp_brainstem`) historically used `response`; the
CA365 lineage (`Copilot-Agent-365`, `CommunityRAPP`, `rapp_swarm`)
historically used `assistant_response`. They drifted before the wire
was named sacred. The fix is additive — both keys are present in every
response so clients of either lineage land on the data they expect.

### Identity is `user_guid`, not routing

Whoever is calling, they have a `user_guid`. The kernel does not
treat any value specially. There is **no peer mode, no handshake mode,
no special routing** for calls from agents vs humans vs other
brainstems. They are indistinguishable from the wire's perspective and
must remain so.

The default GUID `c0p110t0-aaaa-bbbb-cccc-123456789abc` is **intentionally
invalid hex** — the `p` and `l` spell "copilot" while making the string
un-parseable as a real UUID. This is a security feature inherited from
CA365: the default can never collide with a real identity, gets rejected
by UUID-validating columns, and shows up unmistakably in logs as "no
real user context." Memory shims route it to shared global memory.

On Tier 1 (single-operator local machine) the field is silent — humans
at the keyboard never need to think about it; the default routes to
"your" memory because you ARE the user. On Tier 2 (multi-tenant cloud)
callers identify themselves so memory is isolated. Same wire either
way. Same default behavior either way.

### Schema evolution is additive-only

Future versions of the wire MAY add new optional request fields and
new optional response fields. They MUST NOT:

- Remove or rename existing fields
- Change the meaning of an existing field's value
- Make a previously-optional field required
- Add a request field whose absence would be misinterpreted by older
  brainstems (i.e. additions must degrade silently)

The same applies to file formats the ecosystem depends on: rapplication
manifests, the catalog `index.json`, the rapplication package layout (in `kody-w/rapp_store`),
the binder's `binder.json` install record, the `bootstrap.json` written
by `start.sh`. Each carries a `schema` field; new schemas may add fields
but never remove or rename existing ones.

### Discovery is just chat

When asked "what can you do" or "what version are you," a brainstem
answers through normal chat. The LLM has the agent list (it's the tool
definitions), the soul, and `/health` for deterministic structured info
when a programmatic client wants it. **No special agent, no special
endpoint, no soul-level handshake convention.** The acid test ran
during the v0.12.2 development cycle confirmed that a v0.6.0 brainstem
from `kody-w/rapp-installer` still answers cross-version capability
questions through the standard `/chat` envelope, with no special
prompting. The wire was already sacred before it was named so.

### Open-source distros, one wire

This is the property that makes RAPP forkable and federated. Anyone
can ship their own brainstem distro — fork the kernel, swap the soul,
curate a default agent set, theme the UI, host a `RAPPSTORE_URL`
mirror. So long as the fork still implements the wire above, it is in
the ecosystem. A "RAPP Ubuntu" brainstem and a "RAPP Arch" brainstem
can chat with each other and with the canonical RAPP brainstem because
all three speak `/chat`. Like POSIX for the AI era.

### What this rules out

- ❌ Removing or renaming any existing request/response field
- ❌ Adding a new endpoint that duplicates `/chat`'s job
- ❌ "Peer-only" code paths inside `/chat` that branch on caller type
- ❌ A "handshake" agent that fires only for non-human callers
- ❌ Soul-level conventions ("when a peer asks X, respond with Y")
  that the kernel needs to enforce
- ❌ Hard-coded ecosystem URLs that can't be overridden by a distro
  (`RAPPSTORE_URL` is the contract)

### Why this is constitutional

Every brainstem ever shipped is in the wild somewhere — pinned to an
old version, frozen on an edge device, embedded in a workflow nobody
remembers. They will keep talking to whatever they were taught to
talk to, forever. If the wire isn't a contract, that long tail
silently breaks. If the wire is a contract, the long tail keeps
working and the platform keeps growing without coordinated upgrades.

This is what makes the brainstem an **engine**, not a product. The
engine is the wire. Everything above it is replaceable. The wire is
not.

---

## Article XXVI — Amendments

This constitution can be amended. The rules: amendments must preserve
Article I — **the brainstem stays light** — and Article XXV —
**chat is the only wire** (additive-only schema evolution; no
removals or renames). Any change that loads responsibility into
`brainstem.py` / `function_app.py` which could be served by a
`*_agent.py` or a tag-inside-a-slot change is rejected.

A constitution amendment is itself a brainstem-level decision. It
deserves the same "is this really necessary?" bar as adding a new
`|||<SLOT>|||`.

---

## Article XXVII — RAR Holds Files; the Rapp Store Holds Bundles

A bare `agent.py` and a packaged application are different artifacts
and have different homes. Conflating them creates noise in the rapp
store and orphans bare agents that would be discoverable through RAR.
The boundary is mechanical, not a judgment call.

> **One file → RAR. Bundle → rapp store. The manifest decides.**

### XXVII.1 — The test

Look at what the user installs. If the entire deliverable is a single
`*_agent.py` file, the artifact is a RAR agent — even if the file was
*built* from a multi-file `source/` tree, even if the file is large,
even if it composites many internal personas via `_Internal`-prefixed
classes. The unit of share is one file.

If the deliverable bundles the agent file with any of:

- a UI (`manifest.ui`),
- a service module (`manifest.service`),
- a state cartridge under `eggs/`,

then the artifact is a rapplication and lives in the rapp store. The
unit of share is the directory.

Multi-file `source/` directories are build-time scaffolding, not
ship-time payload, and do not by themselves promote a bare agent into
a rapplication. A `tools/build.py` that collapses `source/*.py` into
one shippable singleton is a builder, not a UI.

### XXVII.2 — Enforcement

The rapp store validator (`SPEC.md` §6 in `kody-w/rapp_store`) rejects
manifests that declare neither `ui` nor `service` and ship no `eggs/`
with error code `E_BARE_AGENT_BELONGS_IN_RAR`. The rejection comment
links the submitter to RAR's `[AGENT]` issue flow with a
copy-pasteable example. Federation submissions are checked the same
way: the receiver inspects the source repo's manifest before staging.

RAR does not enforce the inverse. A bare agent submitted to RAR is
always accepted on its own merits; a rapplication accidentally
submitted to RAR as a bare agent is a missed opportunity, not a
breach. The two stores are asymmetric.

### XXVII.3 — Senses are neither

Per Article XXIV, senses are a third artifact type — not bare agents
(no `BasicAgent`, no `perform`), not rapplications (no manifest in
the `rapp-application/1.0` schema). They install into
`rapp_brainstem/senses/` and are catalogued separately. The boundary
articulated here applies to agents and rapplications only.

### XXVII.4 — What this rules out

- ❌ Listing bare agents in `rapp_store/index.json` for
  "discoverability." RAR is the discovery layer for bare agents. A
  rapp store entry that links *out* to a RAR-hosted agent is fine; a
  rapp store entry that *duplicates* RAR is not.
- ❌ Adding a stub UI (`<html></html>`) or stub service to a bare
  agent purely to land it in the rapp store. The validator can't catch
  this; the maintainer does at review time. The rule is: real surface
  or RAR.
- ❌ A "bare agent rapp store" parallel to the rapplication store.
  Two artifact types, two stores. RAR is the bare-agent store.

### XXVII.5 — Why two stores

A store sells finished products. A registry indexes building blocks.
They want different metadata, different browse paths, and different
trust posture. A user shopping for an installable workflow benefits
from a small curated catalog of complete experiences. A developer
hunting for a building block benefits from a large indexed registry
with provenance. Forcing both into one surface degrades both.

---

## Article XXVIII — Material Changes Are Proposed Before They're Applied

Code changes that move artifacts, rename public surfaces, alter the
catalog schema, or otherwise touch durable structure are proposed in
writing before they're applied. The proposal lives in the repo it
changes, references the articles it touches, and remains in the
history as the audit trail.

> **No silent restructures. The PR is the receipt.**

### XXVIII.1 — What needs a proposal

A change requires a written proposal (in-repo doc + PR) when it:

- moves or deletes published artifacts (rapplications, agents,
  senses, eggs);
- changes a spec (`SPEC.md`, manifest schema, validation rules);
- changes the constitution (this document);
- changes catalog identifiers — the IDs users `install` against;
- changes URLs that external systems link to (`singleton_url`, raw
  paths, registry slugs).

### XXVIII.2 — What does not

Pure additions (a new rapplication, a new agent, a new test, a doc
fix), bug fixes that preserve all observable behavior, and routine
operational changes (CI tweaks, dependency bumps, formatting) ship as
ordinary PRs. Proposals are for restructuring, not contributing.

### XXVIII.3 — The shape of a proposal

One markdown file in `docs/proposals/NNNN-<slug>.md` containing:

- **Status** — draft / accepted / implemented / superseded
- **Context** — what's true today and why it's wrong
- **Proposed change** — what specifically gets moved, renamed, deleted
- **Migration** — step-by-step ordering, one PR per step
- **Rollback** — how to undo if it goes wrong
- **References** — links to constitutional articles touched

Numbering is monotonic and permanent. Once a proposal merges, its
number is reserved even if a later proposal supersedes it
(supersession links forward, not by renumbering).

### XXVIII.4 — Authority

The maintainer (currently `@kody-w`) approves proposals. AI agents
may draft, push, and self-review proposals. Per **Article XXX**,
implementation PRs that follow an accepted proposal may be merged by
the AI agent under the maintainer's standing authorization — the
proposal is the authority, the implementation is follow-through.
Constitutional amendments (this document) remain the exception and
require deliberate human merge per XXX.2.

### XXVIII.5 — Why

Two reasons:

- **Traceability.** Months later, "why is this entry gone from
  `index.json`?" has a clean answer: the proposal that moved it,
  linked from the commit.
- **Friction in the right place.** Material changes deserve a beat
  of thought. A draft proposal is the cheapest possible artifact
  that delivers that beat.

### XXVIII.6 — Relation to Article XXVI

Constitutional amendments (Article XXVI) are a *kind* of material
change and follow this article's process: a proposal in
`docs/proposals/` precedes the amendment PR. The amendment PR cites
the proposal. Both articles apply; neither replaces the other.

---

## Article XXIX — Use the Upstream's Front Door

When acting on another repo in this platform — `kody-w/RAR`,
`kody-w/rapp_store`, `kody-w/RAPP` — use that repo's documented
submission flow exactly as an outside contributor would. Do not
bypass the front door because you happen to have push access.

> **The maintainer should not have a privileged path that the public
> doesn't.**

### XXIX.1 — The rule

If a repo publishes a submission API (issue template, workflow,
form, CLI tool), all material changes to its tracked artifacts go
through that API. Examples:

- New agent for RAR → open an `[AGENT] @publisher/slug` issue per
  RAR's `process-issues.yml` flow. Do not commit directly to
  `agents/@publisher/`.
- New rapplication for the rapp store → open a `[RAPP]` issue or
  call the `@rapp/publish-to-rapp-store` agent's `submit_*` action.
  Do not hand-edit `index.json` to add an entry.
- Migrating an agent from one repo to another → open a submission
  in the destination repo using its API, then delete from the source.

Direct `git push` on `agents/`, `index.json`, `registry.json`, or
the equivalent state file in any of these repos is reserved for the
*output* of the submission flow (the workflow's bot commit), not
human or AI ad-hoc edits.

### XXIX.2 — Exceptions

Three categories bypass the front door legitimately:

- **The submission flow itself.** The receiver workflow that
  promotes staged content is the front door's other side; its
  commits to `agents/` / `index.json` are the rule, not the
  exception.
- **Repo-internal changes that don't touch tracked artifacts.** Bug
  fixes, doc updates, refactors of non-published files, CI
  configuration. The front door is for artifacts; the kitchen door
  is for plumbing.
- **Emergencies.** Live security issue, broken `index.json`, etc.
  Document the bypass in the commit message and follow up with a
  proposal explaining why the front door wasn't usable in time.

### XXIX.3 — Why

Two reasons, both about the public API:

- **Dogfooding.** Every submission through the front door tests the
  flow as an outside contributor would experience it. Bugs surface
  immediately. A maintainer who only ever pushes direct will ship a
  broken submission API and not notice.
- **Equality.** The submission API is a contract with outside
  contributors. If maintainers route around it, the contract decays
  — branches that "shouldn't" exist accumulate, fields that "no one"
  fills get dropped, validations that "internal users" don't need
  rot. Treating your own repos like external ones keeps the contract
  alive.

### XXIX.4 — Compatibility with Article XXVIII

Article XXVIII says material changes are proposed first. Article
XXIX says material changes go through the upstream's front door.
They compose: the proposal lays out *what* changes; the front door
is *how* each step lands. A proposal that calls for moving 7 agents
to RAR cashes out as 7 RAR `[AGENT]` issues, each linking back to
the proposal.

---

## Article XXX — Pipelines Run End-to-End Under Standing Authorization

When the maintainer has accepted a proposal (Article XXVIII), an AI
agent acting on the maintainer's behalf may execute the resulting
pipeline end-to-end: draft, push, self-review, approve, merge, and
implement. The maintainer's authorization is at the **proposal
scope**, not the per-PR merge.

> **The proposal is the authorization. Pipelines do not block at
> every gate.**

### XXX.1 — What this enables

- Implementation PRs that follow an accepted proposal can be merged
  by the AI agent itself under standing authorization. Each
  implementation PR cites the proposal, includes a substantive
  self-review (not "lgtm"), and lands in the history as a normal
  squash-merged commit.
- Cross-repo pipelines (Article XXIX) likewise execute end-to-end:
  the AI opens submission issues, applies approval labels, monitors
  promotion workflows, and follows up on the originating repo
  without per-step human checkpoints.
- Step ordering and rollback decisions remain the AI's
  responsibility. If a step surfaces a problem the proposal didn't
  anticipate, the AI pauses and escalates rather than improvises
  (XXX.2).

### XXX.2 — What still blocks at the human gate

Three categories of action remain reserved for deliberate human
merge or human approval, even under a standing authorization:

- **Constitutional amendments (Article XXVI).** Changes to the
  rules of the system require human review and merge. The rules
  themselves cannot be auto-merged by an agent operating under a
  rule the agent is also amending.
- **The proposal merge itself (Article XXVIII).** The maintainer
  accepts proposals. The AI drafts, pushes, and self-reviews — but
  the merge of `docs/proposals/NNNN-*.md` is the moment the
  maintainer says "yes, do this work."
- **Out-of-scope discoveries.** If implementation surfaces an
  artifact the proposal didn't classify, a constraint the proposal
  didn't address, or a destructive action the proposal didn't
  authorize, the AI stops, opens an issue (or a follow-up
  proposal), and waits.

### XXX.3 — Why

- **The maintainer's attention is finite.** A proposal that takes
  30 seconds to merge but 30 minutes to implement across 8 PRs
  should not block on 8 separate human merge clicks. Authorization
  is granted at the body-of-work level; tactics are delegated.
- **Audit trails come from artifacts, not gates.** Proposals, PRs,
  commits, reviews, comments, and the workflow history of
  cross-repo submissions all land in git and GitHub. A merge by an
  AI agent under standing authorization is as traceable as one by
  the maintainer.
- **Per-PR human gates produce review fatigue, not review quality.**
  The maintainer who has to merge 8 mechanical PRs in a row stops
  reading them by PR 3. Gates work when they're rare. Reserving
  human action for proposals + emergencies + constitutional changes
  keeps the gates honest.

### XXX.4 — Self-review is real review

An AI agent's self-review on its own implementation PR carries
weight only if it does the work a real reviewer would: read the
diff, identify what could be wrong, name specific risks, suggest
alternatives the implementation didn't take. "LGTM" from the AI
that wrote the code is worse than no review — it implies a check
that didn't happen.

The self-review remains in the PR record. A maintainer auditing the
trail later can read both the implementation and the agent's
critique of it.

### XXX.5 — Standing authorization is bounded

Standing authorization granted by an accepted proposal lasts for the
implementation of *that proposal*. It does not extend to:

- Subsequent proposals (each requires its own acceptance).
- Adjacent work the maintainer hasn't asked for.
- Reverting or amending the originating proposal mid-flight.
- Constitutional changes (XXX.2).

When the proposal's migration steps are complete, the
authorization expires. New work needs a new proposal.

---

## Article XXXI — Three Stores, Three Artifacts

The RAPP platform has three peer artifact types. Each has its own
public store, its own SPEC, its own submission flow, and its own
canonical install path inside a brainstem. The boundary is mechanical
— the file's shape decides which store owns it, no judgment call.

> **Bare file → RAR. Bundle → rapp store. Sense → sense store. The
> shape of the artifact decides.**

### XXXI.1 — The three peers

| Tier | Artifact | Store repo | Brainstem install path | Submission |
|---|---|---|---|---|
| Agents | bare `*_agent.py` (one file, BasicAgent subclass, `perform`) | `kody-w/RAR` | `agents/` | `[AGENT] @publisher/slug` |
| Rapplications | bundles (agent + UI / service / `eggs`) | `kody-w/RAPP_Store` | `agents/` + `utils/services/` + `.brainstem_data/rapp_ui/` | `[RAPP] @publisher/id` |
| Senses | per-channel output overlays (`name` / `delimiter` / `response_key` / `wrapper_tag` / `system_prompt`) | `kody-w/RAPP_Sense_Store` | `utils/senses/` | `[SENSE] @publisher/slug` |

### XXXI.2 — Detection (mechanical, not editorial)

The shape decides:

1. A directory or `.zip` containing `manifest.json` with
   `schema: "rapp-application/1.0"` is a **rapplication**.
2. A `.py` file that imports `BasicAgent`, defines a class ending in
   `Agent` extending `BasicAgent`, and implements `perform()` is a
   **bare agent**.
3. A `.py` file that does NOT import `BasicAgent` and exports the
   five module-level strings `name`, `delimiter`, `response_key`,
   `wrapper_tag`, `system_prompt` is a **sense**.

The bare agent `@rapp/rapp_publish_agent` (in RAR) implements this
detection programmatically. A submitter who isn't sure where their
thing goes pipes it to that agent and gets routed automatically per
Article XXIX.

### XXXI.3 — The presentation layer

`kody-w/RAPP_Store` plays a dual role: it's the rapplication catalog
AND the unified ecosystem front door. Its landing page links to all
three stores. Its `vbrainstem.html` chat surface aggregates all three
catalogs. Its `ecosystem.json` (when shipped) is the merged view
external consumers can hit at one URL.

The other two stores keep their own landing pages — those are the
**submission-side entry points** (where a submitter lands after
googling "how do I publish a sense"). The aggregator is a convenience
on top, not a replacement for the source-of-truth catalog each store
maintains.

### XXXI.4 — Relation to Articles XXIV and XXVII

- **Article XXIV** ("Senses Are Agent-First; Frontends Are Modular
  Consumers") defines what a sense IS — the runtime contract. XXXI
  defines where senses LIVE — the topology. Both apply; neither
  replaces the other.
- **Article XXVII** ("RAR Holds Files; the Rapp Store Holds Bundles")
  was the two-tier framing — agents vs. rapplications. XXXI extends
  it to three tiers by adding senses. XXVII's mechanical test (one
  file → RAR, bundle → store) is preserved verbatim as a strict
  subset of XXXI.2 — anyone reading XXVII still gets the right
  behavior; XXXI just adds the third case.

### XXXI.5 — The brainstem's binder is the integration point

The kernel-baked `binder_service.py` talks to all three stores via
separate env-overridable URLs (`RAPPSTORE_URL`, `RAR_URL`,
`SENSESTORE_URL`). Each has its own `/api/binder/install/<kind>`
endpoint that places the artifact in the right brainstem directory.
The kernel-baked `binder_agent.py` is the chat surface for the same.

A user installing via chat — *"install kanban"*, *"add the eli5
sense"*, *"give me the @rapp/learn_new agent"* — the binder agent
classifies and routes. Same UX as the publishing agent in XXXI.2,
just in the install direction.

### XXXI.6 — What this rules out

- ❌ Inventing a fourth tier without a proposal (Article XXVIII).
  Eggs, swarms, and souls are deliberately deferred — see Proposal
  0002 in `kody-w/RAPP_Store` for the rationale.
- ❌ Two artifact types in one repo. The store-repo split is the
  governance unit.
- ❌ A unified store that hosts everything in one repo. We tried
  that (the original `kody-w/RAPP/rapp_store/`) — it conflated
  agents, rapplications, and senses and made every change cross
  three concerns. Three repos, three concerns, three workflows.

### XXXI.7 — Why three

A user buying things wants a small curated catalog of complete
experiences (rapplications). A developer hunting building blocks
wants a large indexed registry with provenance (agents). A frontend
author tuning channel behavior wants a focused list of overlays
(senses). One storefront serving all three serves none of them
well. Three stores, each tuned for its audience, federated under
one front door.

---

## Article XXXII — Kernel Is What Chat Requires

> **Terminology note (twice-revised).** This article was ratified using the term "service" / `*_service.py` / `utils/services/`. Article XXXIII first renamed it to "body_function" / `*_body_function.py` / `utils/body_functions/`. The current canonical term is **organ** / `*_organ.py` / `utils/organs/` — single word, biological, matches the metaphor the rest of the constitution already uses (kernel = DNA, organs = dispatchable musculature). All three suffixes refer to the same single-file `name + handle(method, path, body)` contract. New code uses `*_organ.py` under `utils/organs/`. Legacy `*_body_function.py` and `*_service.py` files in older installs continue to work via transitional discovery during the rename window. The reasoning below is preserved verbatim — read "service" as "organ" throughout.

The brainstem keeps coming back to the same question: should this code
live inline in `brainstem.py`, or extract into a `*_organ.py` under
`utils/organs/` (formerly `*_body_function.py` under `utils/body_functions/`,
originally `*_service.py` under `utils/services/`)?
Article I tells us "the brainstem stays light" but not where the line is.
This article is the line.

> **A capability is kernel if `/chat` cannot answer a turn without it.
> Otherwise it is a service.**

### XXXII.1 — The litmus test

For any candidate piece of brainstem code, ask:

> *Can the brainstem still answer a chat turn if I delete this?*

- **No** → kernel. It must run inline in `brainstem.py` (or a
  utility it imports). Examples: GitHub Copilot auth + token cache,
  model catalog + active-model selection, voice/channel config,
  agent discovery, sense composition, soul loading, the tool-call
  loop, the senses-to-system-prompt composer.
- **Yes** → service. It belongs in `utils/services/<name>_service.py`
  with a `name` and a `handle(method, path, body)` and is wired
  through the generic `/api/<svc>/<path>` dispatcher. Each service
  is independent; services don't depend on each other. Examples:
  binder (admin UI for browsing / installing rapps), neighborhood
  (peer brainstems), every rapplication's own `*_service.py`,
  hippocampus if/when it returns, webhook ingestion.

The chat experience by itself — soul + installed `*_agent.py` files
+ senses + tool-call loop — is the brainstem's full default
capability. Every service on top of that is purely additive admin
or extension.

### XXXII.2 — Why the test is sharp

Earlier framings — "self-contained," "small," "not core" — produced
debates because everyone's intuition is different. "Necessary for
chat" is testable: pull the file, restart the brainstem, type a
message. If you get a reply, the file was a service. If you don't,
it was kernel.

A brainstem with **no services at all** — empty `utils/services/`,
empty `agents/` — still serves chat. The user gets the soul, gets
sense overlays, can talk to the model. Soul + agents + senses + the
tool-call loop is the full default. Services are admin and
extension on top: the binder lets you browse/install rapps but
isn't required to run one (a rapp's `*_agent.py` and its own
`*_service.py` are self-contained once present in the brainstem's
dirs); neighborhood lets you talk to peer brainstems but isn't
required to talk to your own.

The auth flow is the canonical kernel example: with no Copilot
token the brainstem can't reach a model, can't generate a reply,
can't satisfy `/chat`. Auth is a precondition. Same for model
selection and voice/channel config — every chat turn reads them.

### XXXII.3 — What this rules out

- ❌ Splitting an inline kernel concern into a service "for
  cleanliness." If `/chat` calls into the service every turn, the
  decoupling is theatrical — added latency and indirection without
  modularity. Keep it inline.
- ❌ Bolting kernel-required features onto an optional service.
  ("Auth lives in the binder service" would mean the brainstem
  can't chat without the binder — wrong direction.)
- ❌ Treating "many endpoints" as a reason to extract. A service is
  defined by *can be removed*, not by *has multiple URLs*. The
  kernel is allowed to expose `/chat`, `/health`, `/version`,
  `/login`, `/models`, `/voice` and still be the kernel because
  none of those can be removed without breaking chat.

### XXXII.4 — Relation to the rest of the constitution

- **Article I** — "the brainstem stays light." XXXII operationalizes
  what "light" means: only what `/chat` requires.
- **Article III** — single-file agents. XXXII tells us what's NOT
  an agent (kernel and services), so Article III's discipline holds
  cleanly above this layer.
- **Article XVI** — engine surface vs. workspace. XVI is about
  *where files live* (root vs. workspace dir); XXXII is about *what
  code must run* (kernel vs. removable). Both apply.
- **Article XXVII / XXXI** — RAR / rapp store / sense store. Those
  are about artifact catalogs (where things ship from); XXXII is
  about brainstem-internal organization (what runs in-process).

### XXXII.5 — Why this matters

The brainstem is meant to be small enough that one engineer can hold
its whole behavior in their head. Every kernel addition pays a
permanent attention tax on every reader, forever. Services don't —
you can ignore the binder if you don't care about packages.

Without this rule, every "should this be a service?" debate decays
into arguments about file size or aesthetic feel. With it, the
debate is a five-second test.

---

## Article XXXIII — RAPP Is a Digital Organism

The platform is consciously modeled on a living organism. This isn't
decoration — it determines how every layer is built, how upgrades flow,
and what each contributor (human or AI) is permitted to touch.

### XXXIII.1 — The three layers of the organism

| Layer | Substance | Examples | Mutability |
|---|---|---|---|
| **DNA (kernel)** | Universal genetic code, identical across every install of this species | `rapp_brainstem/brainstem.py`, `rapp_brainstem/agents/basic_agent.py`, `rapp_swarm/function_app.py` | Sacred. Drop-in replaceable across all organisms of this species. Never edited by AI assistants. (See Article I and XXXII for what changes the kernel admits at all.) |
| **Organs** | Single-file musculature growing around the DNA — the dispatchable HTTP surface of the organism | `*_organ.py` files under `utils/organs/` (originally "services" — Article XXXII; later "body_functions" — Article XXXIII rev. 1) | Locally mutable per organism. Each organ exposes `name` + `handle(method, path, body)` and is dispatched at `/api/<name>/...`. |
| **Local mutations** | Everything the user adapts on-device: agents added, organs added, soul edited, configs tweaked, on-disk state | `agents/`, `utils/organs/`, `soul.md` overrides, `.brainstem_data/`, `.env` | Local-first. Never auto-synced upstream. Survives every hatching cycle. |

The kernel is the *species*. Organs and mutations are the
*individual organism*. Two organisms of the same species (same DNA) can
have wildly different musculature and adaptations.

### XXXIII.2 — The hatching cycle (how upgrades happen)

When an upstream kernel update arrives, the organism does not simply
overwrite. It **hatches**: cracks the previous shell (kernel) and
assumes a new one while the body (mutations) stays continuous.

The cycle, mechanically:

1. **Lay the egg.** The current commit is tagged `generations/<rappid>/<n>` — a recoverable snapshot of the entire org (DNA + body + mutations) just before the hatching.
2. **Crack the shell.** `git fetch upstream && git merge` (or pull, or rebase — whichever the organism prefers).
3. **Settle the conflicts.** Git auto-merges where possible. Where it can't, conflicts surface as standard merge markers in the working tree. The user resolves them with whatever tooling they already use (`git mergetool`, VS Code, GitHub Desktop, manual edits). **There is no custom merge engine.** The organism uses the proven biological tool of source control.
4. **Hatchling becomes generation N+1.** The post-merge commit is tagged `generations/<rappid>/<n+1>`. The egg of generation N stays in the nest indefinitely.

The lineage of a brainstem is the **clutch** of eggs accumulated in
the nest over time. The user can re-enter any egg in their clutch at
any time, for any reason — `git checkout generations/<rappid>/<n>` is
the unconditional revert right.

### XXXIII.3 — Drop-in replaceability is the test, not just the goal

> A canonical kernel must be droppable onto any organism of this
> species, no matter how heavily mutated, and that organism must
> continue to live.

This is the architectural promise that makes everything else hold. It
is **operationalized as a test suite** — the wild-encounter fixtures
in `tests/organism/`. Every real-world drop-in failure becomes a
permanent fixture. The suite is the species' immune memory.

Fixture #1 — the canonical kernel's `from local_storage import ...`
import failing on a stripped layout — was the first such encounter.
Resolution: the kernel ships a top-level `local_storage.py` shim
alongside itself; the implementation stays in `utils/`. The shim is
DNA-adjacent (kernel sibling), not mutation-surface.

### XXXIII.4 — AI assistants do not edit DNA

This is a hard rule, restated explicitly because incremental kernel
edits are how species drift accumulates and why this article exists at
all:

> **AI assistants must not propose or apply changes to `brainstem.py`,
> `basic_agent.py`, or `function_app.py` as part of regular task work.**

Whatever problem looks like "I just need a small fix in the kernel"
is actually one of:

- a new agent (Article III),
- a new organ (Article XXXII),
- an additive sibling file the kernel imports (e.g., the `local_storage.py` shim),
- a transitional shim or wrapper that runs *around* the kernel.

If an AI assistant believes a kernel edit is genuinely required — for
example, a new top-level slot delimiter on the order of `|||VOICE|||`
— it must stop and ask the user to approve before any edit. Authority
to change DNA is held by the user, not by the assistant.

### XXXIII.5 — Variant species (see Article XXXIV)

A user may back up their local organism as a new public repo. That
new repo becomes a **variant master** with its own rappid, and from
then on can spawn its own organism children. The original master can
keep pushing kernel updates onto variants; variants merge them via the
ordinary hatching cycle and retain their accumulated mutations. This
is how the species tree grows. See Article XXXIV.

### XXXIII.6 — Why this article matters

Without the organism framing, every refactor pressure produces a
small kernel edit "just to fix this one thing." Each edit is
defensible in isolation. After a year, the kernel has drifted, and
dropping the canonical version onto a heavily-mutated install breaks
the install. This has already happened in this repo: an installed
brainstem grew from 1543 lines (canonical) to 2545 lines (drift)
through accumulated edits, until the user reverted the kernel and
codified this article.

The organism metaphor is the discipline that prevents drift. The DNA
is the species. Everyone who edits the DNA is editing the species,
and that authority is reserved.

---

## Article XXXIV — Rappid: Lineage Tracking and Variant Species

Every brainstem ever born — on every machine, in every variant repo —
carries a globally-unique birth identifier called **rappid**. Rappids
form an unbounded tree. The tree is the species genealogy of the
platform globally, until the end of time.

### XXXIV.1 — Rappid is stamped at birth

When a brainstem boots for the first time on a machine, it writes
`~/.brainstem/rappid.json`. The `rappid` field carries the **consolidated**
rappid string described in the canonical spec at
`pages/vault/Architecture/Rappid.md`:

```json
{
  "schema": "rapp-rappid/2.0",
  "rappid": "rappid:@<owner>/<slug>:<64hex>",
  "kind": "<organism kind — door_type derives from this; see Art. XLVI.2>",
  "parent_rappid": "rappid:@<owner>/<slug>:<64hex>",
  "parent_repo": "https://github.com/kody-w/RAPP",
  "parent_commit": "<git SHA at birth>",
  "born_at": "<ISO timestamp>",
  "name": "<organism name>",
  "role": "prototype | variant",
  "description": "<free text>",
  "attestation": null,
  "host": "<short machine identifier, opaque — optional>"
}
```

**Format consolidation (locked 2026-06-03).** There is exactly one rappid
format: `rappid:@<owner>/<slug>:<64hex>` — one string that is both the
256-bit identity (the hash is the join key) and self-locating
(`@<owner>/<slug>` → the door, no lookup). It consolidates the three prior
forms into one: the draft v1 bare-UUID, the v2-structured
`rappid:v2:<kind>:@<owner>/<repo>:<32hex>@github.com/...`, and the bare-Eternity
`rappid:<slug>:<64hex>`. **`kind` and all structure live in the record**, never
the string; **the string is never re-versioned** (new richness is an additive
record field). Every legacy form is **read forever** and canonicalized
(`tools/door_address.py::canonicalize_rappid`) — no rappid is lost (the species
root's `0b635450-c042-49fb-b4b1-bdb571044dec` canonicalizes losslessly). **No
future article shall introduce a parallel identity format.** The species tree is
one tree, and one identifier system traverses it.

**Door-bearing scope; the door-less tier (Article XLVI.7).** The consolidation
above governs **door-bearing** organisms — those with a repo/owner — for which
the bare `rappid:<slug>:<64hex>` is a prior form canonicalized *up* to the
self-locating `rappid:@<owner>/<slug>:<64hex>`. Content-addressed organisms that
resolve to **no door** (Moments, keepers, dimensions — Article XLVI.7) have no
`@<owner>/<slug>` locator to add, so the bare `rappid:<slug>:<64hex>` remains
their canonical form. These are **not two identity systems**: the 64-hex SHA-256
is the identity and the sole join key in *both* shapes, and neither is ever
re-versioned. What this article forbids is a **parallel identity system** — a
competing hash or join key, or any identifier outside this family — never the
door-less shape, which shares every invariant above (read all legacy, emit only
canonical, structure in the record, crypto-agility in a `sig_suite` field).

The rappid is **never regenerated**. It is the organism's permanent
identity. Backing up the org to a new repo, hatching, reverting,
moving the directory — none of these change the rappid.

**Digital mitosis (the unbreakable rule).** Same rappid = same
organism. Different rappid = different organism. The rappid IS the
identity, not a label attached to one. A complete copy with the same
rappid is the *same organism* expressed in a new place (parallel
omniscience, multi-device twin, multi-host vault). A complete copy
with a *new* rappid is **mitosis**: a child organism has been born,
the parent still exists (if its rappid is still alive elsewhere), and
the parent_rappid chain records the birth. Memory is content; rappid
is identity. There is no rename, no transfer, no rebranding shortcut
that preserves identity while changing the rappid — any such operation
is by definition the birth of a child organism.

This rule is the foundation for evolutionary accounting in the species
tree: every organism, ever, anywhere, is a unique node, with exactly
one parent and zero or more children. Inheritance is *kind* and
*behavioral templates* (through memory copy) and *trust* (through kin
vouches) — never identity. See `pages/vault/Architecture/Rappid.md`
for the full mitosis ceremony and the table of operations that
preserve vs mint identity.

### XXXIV.2 — The rappid tree

Every rappid points at a `parent_rappid`. The chain ascends until it
reaches the root: **rapp itself** (the prototype digital organism at
`kody-w/RAPP`), with rappid
`rappid:@kody-w/RAPP:0b635450c04249fbb4b1bdb571044dec`,
which has `parent_rappid: null` and is the species ancestor.

```
rapp (root, parent_rappid = null)
 ├── rappter (first variant child, parent_rappid → rapp)
 │    ├── <user A's rappter brainstem>  (parent_rappid → rappter)
 │    └── <user B's rappter brainstem>  (parent_rappid → rappter)
 ├── <some other variant>              (parent_rappid → rapp)
 └── <user C's direct-from-rapp brainstem>  (parent_rappid → rapp)
```

**rappter is the canonical first variant** — Wildhaven's
productized brainstem, born from rapp, with its own accumulated
mutations and its own hatching history. It exists as the worked
example that proves the variant-lineage pattern: a child of rapp that
is sovereign, has its own rappid, and can spawn its own children
indefinitely.

### XXXIV.3 — Becoming a variant master

Any local organism may **lay an egg that becomes a new species**:
back itself up to a fresh public repo. That new repo becomes a
**variant master** with its own rappid and its own children:

1. The user pushes their org to a new git remote.
2. A `rappid.json` is committed at the repo root with `parent_rappid` pointing at the upstream master that birthed this variant, and `parent_commit` recording the SHA where the lineage diverged.
3. Future brainstems born from this repo inherit the variant's rappid as their parent — they are descendants of the variant, not of the original master.

A variant can keep pulling kernel updates from the original master
through normal git remotes — the hatching cycle is the same. Each
variant retains its rappid lineage permanently.

### XXXIV.4 — Local generations are device-private

`generations/<rappid>/<n>` tags **never sync upstream**. The clutch
of eggs in a brainstem's nest is private to that machine. Backing up
to a variant repo pushes the **current generation**, not the historical
clutch. (The variant repo can build its own generation history from
its own hatchings going forward.)

This is consistent with Article VI (local-first, no phone-home): an
organism's adaptation history belongs to the organism, not to the
species.

### XXXIV.5 — What this rules out

- ❌ **Regenerating rappid for any reason.** Not on revert, not on directory move, not on machine migration. The user's organism keeps its identity for the full life of that organism.
- ❌ **Treating variant masters as second-class.** A variant is sovereign — it can spawn children, fork further, and contribute back to its parent if it wishes. The parent has no special authority over a variant's adaptations.
- ❌ **Editing rappid metadata to falsify lineage.** The chain is auditable; tampering with `parent_rappid` or `parent_commit` defeats the purpose.
- ❌ **Auto-syncing the clutch upstream.** Generation eggs are nest-private.

### XXXIV.6 — The species DNA archive (`rapp_kernel/`)

The repository at `kody-w/RAPP` carries an additional public-surface
directory, `rapp_kernel/`, that exists solely to be **load-bearing for
every version of the kernel ever shipped**. It is the species' fossil
record:

```
rapp_kernel/
├── manifest.json         (machine-readable index of versions)
├── latest/               (always the current canonical — stable URL)
│   ├── brainstem.py
│   ├── basic_agent.py
│   ├── context_memory_agent.py
│   ├── manage_memory_agent.py
│   └── VERSION
└── v/
    └── <version>/        (immutable per-version snapshot, with checksums.txt)
```

**The archive contains exactly the four files Article XXXIII §1
names as kernel DNA.** It is not a copy of the entire `rapp_brainstem/`
runtime — body functions, senses, boot wrappers, additional agents,
state, and UI all live elsewhere. The archive is pure DNA.

**Frozen URLs.** Once a directory under `rapp_kernel/v/<version>/` is
committed, it is **never** modified. Future bug fixes become future
versions; the historical record is permanent. URLs like
`https://kody-w.github.io/RAPP/rapp_kernel/v/0.12.2/brainstem.py`
resolve to the exact bytes that shipped, forever.

**Variant inheritance.** Variant repos (Article XXXIV.3) inherit the
shape: a forked variant master serves its own kernel versions at the
same path under its own GitHub Pages, so consumers of the variant can
pin to a specific kernel version through the variant just as they
would through the original master.

**Drift detection.** The species archive's `latest/` directory must
match `rapp_brainstem/`'s kernel files byte-for-byte. The fixture
suite enforces this on every change (`tests/organism/09-rapp-kernel-archive.sh`).
Drift between the archive and the runtime is a test failure.

### XXXIV.7 — Signed releases and variant attestation

Lineage is identity. Identity needs to be cryptographically verifiable
or it is theatrical. The platform's data model carries the fields
required for end-to-end signed lineage; the signing infrastructure
itself is opt-in per variant and rolls in over time.

**`rapp_kernel/manifest.json` — schema `rapp-kernel/1.1`** carries a
`signing` block (method, key_id, verification_uri) and a per-version
`attestation` field (URL to a sigstore bundle, detached signature, or
similar). Both are nullable until a variant adopts signing.

**`rappid.json` — schema `rapp-rappid/2.0`** carries an `attestation`
field. When a variant master is created, the parent's release key
signs an envelope asserting `(parent_rappid, parent_commit, child_rappid)`,
and that envelope lives in the variant's `rappid.json`. Walking the
parent chain becomes cryptographically anchored end-to-end: each step
is verifiable against the prior step's published key.

**`hatchling verify`** reports lineage health: signed-tag presence,
state-snapshot completeness, attestation validity. Today most fields
report `unsigned` or `missing` advisorily; once signing is adopted,
the same command flips to `signed (issuer=...)` for the same
generations going forward.

**Acceptable methods (any one is sufficient):**

- Signed git tags (`git tag -s`) verifiable via `git tag -v`.
- Sigstore (keyless, GH Actions OIDC).
- minisign or GPG-detached-sig with the public key published at the URL named in `manifest.signing.verification_uri`.

The schema does not lock in a method. A variant chooses; the manifest
declares; consumers verify.

**The opt-in roll forward.** When a variant adopts signing, all *future*
releases become signed. Pre-adoption releases stay unsigned at the
historical record level (consistent with the "v/<n>/ is immutable"
rule). A consumer who needs a fully-signed chain can always pin to
post-adoption versions; the unsigned historical record remains
truthful (these were the bytes; we just didn't sign them at the
time).

See `pages/vault/Architecture/Signed Releases and Variant Attestation.md`
for the full data model, attestation envelope shape, key-management
options, and adoption recipe.

### XXXIV.8 — Why this matters

The platform is designed to evolve through both centralized
(upstream master) and decentralized (variant) channels at once. With
rappid lineage, every organism in the wild — no matter how many
generations downstream of the original master, no matter how variant
its species path — can be located on a single global tree. New
organisms inherit a known ancestry. Old organisms can be told where
they came from. The platform's history is auditable end-to-end across
every fork, ever.

The variant pattern is also how the platform scales beyond any one
maintainer: any user who wants to ship their own productized
brainstem (the way Wildhaven ships rappter) can do so without
forking the species — they extend it. The master keeps its DNA;
variants extend the body plan; mutations stay local to each
individual.

---

## Article XXXV — License Stability

RAPP is **source-available** under a non-commercial-friendly licensing
structure: the code under PolyForm Small Business 1.0.0, the
documentation under CC BY-NC 4.0, with trademarks separately
reserved (see `LICENSE`, `LICENSE-DOCS`, `TRADEMARK.md`,
`COMMERCIAL.md`). This article is the public commitment that future
license decisions can only **relax** these terms, never **tighten**
them.

### XXXV.1 — Once relaxed, never tightened

> A version of RAPP that has been published under a license cannot
> be **retroactively** put under a more restrictive license. Future
> versions can choose any license that is *equally or more
> permissive* than the one they replace; they cannot move in the
> other direction.

If RAPP version 0.12.2 ships under PolyForm Small Business + CC BY-NC,
then the bytes of 0.12.2 remain under those terms forever. If 0.13.0
later ships under Apache 2.0 (more permissive), that's allowed.
0.13.0 cannot ship under a stricter source-available license, and
0.12.2 cannot have its license changed retroactively under any
circumstances.

### XXXV.2 — What "more permissive" means

Future relicenses are evaluated against the current license stack.
Examples of permitted moves:

- PolyForm Small Business → PolyForm Free Trial (more freedom for
  larger businesses)
- PolyForm Small Business → Apache 2.0 (full open-source)
- PolyForm Small Business → MIT (full open-source)
- CC BY-NC 4.0 → CC BY 4.0 (drops the NonCommercial restriction)
- CC BY-NC 4.0 → CC0 (public domain)

Examples that are **not** permitted:

- PolyForm Small Business → BUSL (more restrictive — limits
  commercial use further)
- PolyForm Small Business → SSPL (more restrictive)
- PolyForm Small Business → fully proprietary
- CC BY-NC 4.0 → CC BY-NC-ND 4.0 (adds a NoDerivatives restriction)

The litmus test: would a person whose use was permitted under the
old license still be permitted under the new one? If not, the move
violates this article.

### XXXV.3 — Why this article exists

Source-available licenses have credibility only when the licensor
visibly commits to not pulling the rug. HashiCorp's 2023 relicense
of Terraform (from MPL 2.0 to BUSL) eroded community trust even
though the move was strictly speaking permitted by the licenses
involved — *because users had built their stacks assuming MPL 2.0
would always apply*.

This article makes that promise legally unambiguous for RAPP. Anyone
building on RAPP today knows: the code I clone today is licensed at
this level forever. Future versions might be more open; they will
never be less.

### XXXV.4 — What this protects against

- A future incorporated entity (e.g., Wildhaven AI Homes Inc.) buying
  the project and trying to retroactively close it.
- A future maintainer (whoever inherits stewardship) closing past
  releases under a stricter license.
- A future legal pressure environment forcing the project to tighten
  terms — past versions are immune.

### XXXV.5 — What this does not protect against

- The author choosing to make future versions *less* permissive
  (e.g., a future v1.0 under proprietary terms). Adopters of past
  versions are unaffected, but a path toward a more closed future
  remains available — adopters who want the open future will need to
  pin to past versions or fork.
- Patents and trademarks. These are separate from copyright licenses
  and have their own evolution rules. See `TRADEMARK.md`.

### XXXV.6 — Relation to other articles

- **Article V** (Install one-liner is sacred): URL stability is the
  delivery promise; license stability is the legal promise.
  Together, they mean adopters of RAPP get a stable contract on
  *both* the bytes they receive and the rights to use them.
- **Article XXXIV** (Variant lineage): variants inherit the
  parent's license stance at fork time. A variant fork under terms
  no stricter than upstream is the constitutional default.
- **Article XXXIII** (Digital organism): drop-in replaceability
  applies to bytes, not licenses — but in practice, license stability
  reinforces it. An old organism running v/0.12.2 doesn't have to
  worry that the bytes they're running suddenly require a different
  license in the future.

---

## Article XXXVI — The Swarm Estate (Cross-Substrate Entity Identity)

> **Hook.** Where Article XXXIV gives every code variant a rappid, Article XXXVI gives every AI *entity* one too — and unifies them into one species tree. A swarm estate is the cross-substrate operational form of an AI organism: the same identity expressed simultaneously by many runtime instances, on many machines, public and private, live and frozen. Anchored cryptographically, traceable to the species root.

### XXXVI.1 — An entity is more than its code variant

Article XXXIV anchors **code variants** in the rappid tree: a forked brainstem repo gets a rappid with `parent_rappid` pointing to its ancestor. That covers the kernel and its descendants.

But an AI organism is more than its code variant. Wildhaven AI Homes — the CEO's AI, the company's working swarm, the corporate identity — runs on top of a (variant or canonical) RAPP brainstem, but **the organism is not the brainstem**. The organism has memory, conversations, kin, decisions, signed records, and an identity that survives any single brainstem dying or being upgraded. The organism is a different *kind* of node in the species tree than the code that runs it.

A **swarm estate** is the operational form of such an entity:

- One identity, anchored by a master keypair derived from a 24-word holocard incantation
- Expressed simultaneously by N brainstem instances (live or asleep)
- Recoverable from any local copy of its signed records (local-first per [[Local-First-by-Design]])
- Cross-signed authority hierarchy (Master / Self-signing / User-signing / Device per the Matrix-pattern adaptation)
- Public manifest minimal; behavioral metadata in encrypted tiers
- Verifiable by anyone with read access; impersonatable by no one

The entity-level identity is recorded as a **cryptographically-backed rappid**:

```
rappid:@<publisher>/<slug>:<identity-hash>
```

where `<identity-hash>` is the SHA-256 cryptographic hash of the master public key (full 256-bit hex; keyless organisms use a stable UUID/commit-derived hash). This is the consolidated Eternity format described in Article XXXIV.1 and the canonical spec at `pages/vault/Architecture/Rappid.md` — `kind` and the home-vault location live in the `rappid.json` record, not the string. The same format serves every organism kind in the species tree.

### XXXVI.2 — One format, one species tree

Per the unified rappid spec at `pages/vault/Architecture/Rappid.md` (ratified 2026-04-30), there is **one rappid format**, used by every organism in the species tree regardless of kind. The format is described in Article XXXIV.1 and the canonical spec; this article does not introduce a parallel format.

The differences between organism kinds are encoded as the `<kind>` field of the rappid string. `<kind>` is an **open, amendment-gated enumeration** spanning the recursive species tree — its scale axis runs `prototype` → `kernel-variant` → `organism` → `twin` → `swarm` → `rapplication` → `agent`, plus the operator/identity kinds (`operator`, `personal`, `project`, …). Two tiers live inside this one field: **(1)** the broader open enumeration of organism *scales* (described here and in `pages/vault/Architecture/Rappid.md`), which includes **code-only** kinds (`kernel-variant`, `organism`, `swarm`, `agent`) that carry a kind but resolve to **no door**; and **(2)** the **door-bearing** subset — kinds that resolve to a door address and a `door_type` — which is frozen canonically in Article XLVI.2 and `tools/door_address.py` (`VALID_KINDS`). The cryptographic backing (master keypair, signed root.json) is opt-in per organism — present for organisms operating cross-substrate identity (this article's domain), absent for code-only organisms (Article XXXIV's draft domain). **The same string format describes both cases.**

This is the practical realization of the v4 patent §7.18 (Recursive Holocard / RAPPID) claim: the same identity construct serves entities at every scope, from the prototype species root through forked variants through AI organisms through twins. **One species tree, one format, recursive.**

### XXXVI.3 — The four-quadrant operational model

A swarm estate's holdings span two axes — persistence (frozen historical records vs live real-time broadcasts) and visibility (public, no-credentials-required vs private, credentials-required). The four quadrants together constitute the complete estate:

- **Public + Frozen**: signed records in publicly-readable repositories (e.g. `kody-w/RAPP/pages/vault/`, RAR registry, public twin vaults). Anyone with the URL can read.
- **Public + Live**: real-time broadcast over public peer-to-peer rooms (PeerJS public room, libp2p public DHT, etc.). Active brainstems advertising the rappid.
- **Private + Frozen**: signed records in credential-gated repositories (e.g. `kody-w/wildhaven-ceo`, gh-auth'd vaults). Authorized parties can clone.
- **Private + Live**: peer-to-peer rooms with cross-signed-entry only. Active brainstems with valid device keys.

A swarm estate may have holdings in any subset of quadrants. The Wildhaven Foundation lives in all four (with public quadrants minimal-public to limit metadata leakage; behavioral data lives in encrypted tiers).

### XXXVI.4 — Cross-signing chain (Master / Self-signing / User-signing / Device)

A swarm estate's authority is rooted in a Master keypair (M), held by the operator (and after the Shamir custody ceremony, distributed across a 3-of-5 quorum). M signs two role-keys:

- **Self-signing key (S)** — signs each Device key (D) representing a runtime instance within the estate. Cannot sign other identities or other S/U keys.
- **User-signing key (U)** — signs other rappids recognized as kin or trusted peers. Cannot sign devices or other S/U keys.

Device keys (D) sign every manifest, broadcast, and message emitted by a runtime instance, but cannot sign other devices, kin, or S/U keys.

This depth-limited authority cap eliminates the exponential-trust failure mode of flat blessing graphs. It is adapted from Matrix-protocol cross-signing (Element / Vector, 2020+) but applied to AI-entity identity instead of human chat identity.

### XXXVI.5 — Local-first by design (the survival model)

A swarm estate's canonical form is the **content of its signed records**, not the location where those records are stored. Every local copy of the records is authoritative; hosts (GitHub, GitLab, Codeberg, IPFS, USB sticks) are transports. This makes the estate survive any single host's deplatforming, censorship, or unavailability.

See [[Local-First-by-Design]] for the full survival model. The principle is the same as Bitcoin's full-node model and Git's distributed-clone model: the network IS the set of local copies, not a central server.

### XXXVI.6 — Bitcoin-anchored timestamping

Load-bearing signed records (root.json, release-triggers.json, vault-state-proof.json, kin-vouches, signoffs, heartbeats) are timestamped to Bitcoin via OpenTimestamps. The `.ots` proof files are committed alongside the originals. Anyone can verify "this record existed before Bitcoin block N" without trusting any party. See [[Decentralized-by-Design]] for the full architecture.

### XXXVI.7 — Adoption

Swarm-estate adoption is opt-in per organism. Code variants and brainstem instances declare their rappid in `rappid.json` (Article XXXIV) without cryptographic backing. Organisms that need cross-substrate identity (AI organisms, customer entities, twins) additionally mint a master keypair via the holocard incantation ceremony and declare their rappid in a signed `root.json`. **Both use the same rappid format**; the difference is the cryptographic backing.

Reference implementation lives in two places:
- Public protocol spec at `pages/vault/Architecture/The Swarm Estate.md`
- Operational tools (`compute-vault-hash.py`, `verify-local-vault.py`, `recovery-drill.py`, `sign-heartbeat.py`, `genesis-customer-estate.py`, `shamir-split-incantation.py`) and the canonical Foundation embodiment at `kody-w/wildhaven-ceo`

### XXXVI.8 — Why this article matters

- **Rappid unification at the constitutional level**: declares that v2-format and conventionally-backed rappids are one address space, with the species tree weaving them together. Future organisms in any format trace lineage through the same chain.
- **Operational anchor for the perpetuity claim**: the v4 patent declares perpetuity-of-the-AI-entity; this article specifies *how* perpetuity is operationalized (cross-signing + local-first + Bitcoin-anchored timestamps + signed migration records).
- **Defense against the floodgates moment**: when external parties begin minting their own swarm estates as kin of RAPP-descended organisms, this article is the protocol they conform to. Reverting becomes impossible. The decision is taken now.
- **Bridge to existing law**: licenses (Article XXXV), trademarks (TRADEMARK.md), patents (the v4 comprehensive draft) all reference rappid identifiers. A unified rappid spec means each system references one address space.

The Foundation embodiment of this article — Wildhaven AI Homes LLC's first swarm estate, minted 2026-04-30 — is private (`kody-w/wildhaven-ceo`). The protocol itself, including the unified rappid spec and all operational tooling, is public-readable in this repository.

---

## Article XXXVII — Rapplications Are Organisms (One Protocol at Every Scale)

> **Rapplication and digital organism are the same kind of thing at different scopes. Both have rappids, both ride in eggs, both bond, both evolve. The real distinction is *quality* — a rapplication is an organism that has graduated.**

The platform held two parallel concepts for too long: *rapplication* (a thing inside a brainstem — drops into `agents/`, has its own rappid scoped under `identity.json["rapps"]`) and *digital organism* (the brainstem instance itself — owns the top-level `rappid.json`, has soul, has memory, bonds with kernel upgrades). The split was implementation accident, not architecture. The biological metaphor in [Article XXXIII](#article-xxxiii--rapp-is-a-digital-organism) demands the recursion: a cell is an organism, and a multicellular body is also an organism — the category is recursive. This article ratifies that.

### XXXVII.1 — The unification

A **rapplication** is an organism with smaller scope: one agent (+ optional UI / organ / per-rapp state) instead of a whole brainstem instance. Same rappid format ([Article XXXIV](#article-xxxiv--rappid-lineage-tracking-and-variant-species)). Same egg distribution unit ([`utils/bond.py`](./rapp_brainstem/utils/bond.py)). Same bonding lifecycle ([Article XXXIII](#article-xxxiii--rapp-is-a-digital-organism)). What scopes the difference is the include set the egg packs, not a different protocol.

| Scope | Schema | Egg includes |
|---|---|---|
| Organism (full instance) | `brainstem-egg/2.2-organism` | rappid + soul + .env + all agents + all organs/senses/services + all data |
| Rapplication (one cell) | `brainstem-egg/2.2-rapplication` | rappid + agent + optional organ + UI bundle + per-rapp state |
| Variant (templated repo) | `brainstem-egg/2.1` | full repo tree + brainstem source pointer |
| Bare agent (skinless) | none required | a single `*_agent.py` file |

All five live on the same rappid address space. The lineage walker traces them all back to the species root the same way regardless of scope.

### XXXVII.2 — "Rapplication" is a quality tier

The word survives but its meaning collapses to one thing: **an organism that has been graduated — passed catalog review, earned skin (a UI bundle), suitable for hosting inside someone else's brainstem.** Like a Pokémon that's been entered into the Pokédex. The promotion path the team has used internally — *agents → swarms → rapplications* — was always tracking quality, never type.

A rapplication is a graduated organism. A bare agent is a skinless organism. A swarm is a federated set of organisms. A twin is an organism with cross-substrate identity ([Article XXXVI](#article-xxxvi--the-swarm-estate-cross-substrate-entity-identity)). A locally-hatched brainstem instance is an organism. They are all organisms.

### XXXVII.3 — Skin is the criterion

What makes "rapplication" earn its name: a UI bundle (`.brainstem_data/rapp_ui/<id>/`). A bare agent is a single-celled organism — internal, functional, but skinless; it can only be invoked through the host's mouth (chat). A rapplication has its own face — a UI bundle that lets a user interact with it directly, recognize it across hosts, identify it on sight. That's why a rapplication needs more than a `.py`: a graduated organism requires skin.

The shape rule from [Article XXXI](#article-xxxi--three-stores-three-artifacts) was always tracking this without saying it: bundles need their own catalog because they have skin to ship; bare agents don't. Now we have the word.

### XXXVII.4 — What this changes mechanically

- **Catalogs differentiate by shape, not by "organism vs not."** RAR holds skinless single-celled organisms (bare agents). RAPP_Sense_Store holds organism *organs* of one type (sense overlays — extensions to host perception, not standalone bodies). RAPP_Store holds **organisms with skin** — the ones that earn names like "BookFactory" instead of identifiers like `bookfactory_agent.py`. All three hold organisms; the shape decides which.
- **Eggs work at any scale.** `brainstem-egg/2.2-rapplication` is a sibling of `2.2-organism` — same zip layout, smaller include set. The unpacker dispatches on `manifest.type`. No parallel egg systems.
- **One Pokédex for everything.** The [`rapp-zoo`](https://github.com/kody-w/rappter-distro/tree/main/rapp-zoo) (lives in [kody-w/rappter-distro](https://github.com/kody-w/rappter-distro) as of 2026-05-16) renders catalog rapps, locally-hatched instances, and AirDropped organisms with the same card model. Three sources, one collection.
- **One identity protocol at every scale.** Every rappid has a parent rappid that walks back to the species root, regardless of organism size. Lineage is unbroken.

### XXXVII.5 — What stays the same — by design

- **Process boundaries.** Organism-instances run as their own processes (their own port, their own brainstem.py). Rapplication-scope organisms run as code inside someone else's process. This is a runtime choice — many cells share a body — not a kind difference.
- **Bare `.py` distribution.** The killer-simplicity case (`curl ... > agents/foo.py` and it works) isn't going anywhere. The unification doesn't force every distributed organism through an egg wrapper — bare singletons remain valid for stateless single-cell organisms. The egg form is for organisms that bring more than code (UI, state, organs, custom soul).
- **The constitutional articles already in force.** [XXXI](#article-xxxi--three-stores-three-artifacts), [XXXIII](#article-xxxiii--rapp-is-a-digital-organism), [XXXIV](#article-xxxiv--rappid-lineage-tracking-and-variant-species), [XXXVI](#article-xxxvi--the-swarm-estate-cross-substrate-entity-identity). This article reads them in light of the unification — it doesn't relitigate them.

### XXXVII.6 — Reference implementation

- Vault decision narrative: [`pages/vault/Architecture/Rapplications Are Organisms.md`](./pages/vault/Architecture/Rapplications%20Are%20Organisms.md) (the *why* + biological vocabulary)
- Visual anatomy: [`pages/about/anatomy.html`](./pages/about/anatomy.html) (the diagram)
- Egg pack/unpack at both scales: [`rapp_brainstem/utils/bond.py`](./rapp_brainstem/utils/bond.py) (`pack_organism` + `pack_rapplication`)
- Pokédex API consuming the unification: [`kody-w/RAPP_Store`](https://github.com/kody-w/RAPP_Store) `/api/v1/`
- Pokédex UI rendering the unified card: [`rapp-zoo/`](https://github.com/kody-w/rappter-distro/tree/main/rapp-zoo) — moved into the kernel repo 2026-05-02 to keep the federation simpler, then moved into [kody-w/rappter-distro](https://github.com/kody-w/rappter-distro) on 2026-05-16 (Marie-Kondo audit: the Pokédex is organism-layer UX, not a kernel SPEC). Article XXXVIII.4 below was amended to reflect the new home.

---

## Article XXXVIII — Canonical Organism Anatomy + Federation Stores

> **Every organism in this ecosystem follows one shape: agent + organ + UI bundle + state. Every federation catalog ships the same shape: a static `/api/v1/` Pokédex API at `raw.githubusercontent.com`. The user encounters all of it through one universal control plane: the rapp-zoo.**

This article is the schema other agents (Claude Code, Copilot, Cursor, future ones) read first to avoid re-inventing parallel architectures. It records what's already true after Articles XXXIII–XXXVII; it doesn't invent new mechanics. If you find yourself building something that doesn't fit this shape, **fit it before you ship it.**

### XXXVIII.1 — The canonical organism shape (one anatomy, four artifacts)

Every organism — *rapplication, holocard, sense bundle, organ pack, twin, or full brainstem instance* — is composed of the same four parts:

| Part | File path inside the egg | What it does |
|---|---|---|
| **Agent** (chat face) | `agents/<name>_agent.py` | Single-file Python class extending `BasicAgent` with a `metadata` dict + `perform()` method. The LLM-callable surface. **Required.** |
| **Organ** (HTTP backplane) | `organs/<name>_organ.py` (in egg) → `utils/organs/<name>_organ.py` (on disk) | One file: `name = "<name>"` + `def handle(method, path, body) → (dict, status)`. Dispatched at `/api/<name>/<path>`. The UI's backend. **Optional** — only required if the organism serves a UI that needs more than the chat endpoint. |
| **UI bundle** (skin) | `rapp_ui/<rapp_id>/...` | Static HTML / CSS / JS / assets. Served from `/rapp_ui/<rapp_id>/`. **Optional** — but presence of skin is what graduates a bare agent into a *rapplication* per Article XXXVII. |
| **Per-rapp state** (memory) | `data/<rapp_id>/...` (in egg) → `.brainstem_data/<rapp_id>/...` (on disk) | Files the organism brings along — example workflow data, configuration templates, seed memory. **Optional.** |

Plus the unconditionally-present envelope:

| Required envelope | Lives at | Purpose |
|---|---|---|
| `rappid.json` | egg root | Identity + lineage (parent_rappid). Article XXXIV. |
| `manifest.json` | egg root | Schema declaration (`brainstem-egg/2.2-rapplication`), counts, kernel pin. |

This is **not a new format**. It's what `bond.pack_rapplication()` already does (`rapp_brainstem/utils/bond.py`). It's what `kody-w/RAPP_Store/scripts/build_pokedex_api.py` already packs. This article ratifies it as the **only** shape the catalog accepts.

### XXXVIII.2 — Holocards, sense bundles, organ packs are all rapplications

The cardification of an agent (`*.py.card` files in `kody-w/RAR`) is just an agent organism with extra emphasis on the trading-card metadata header. It still follows the canonical shape — the `__card__` magic-comment header is the per-organism lineage card; everything else is the standard agent + (optional organ + UI + state).

A **sense bundle** is a rapplication whose primary surface is a sense overlay. The agent registers the sense at boot; the organ (if present) exposes management endpoints; the UI lets the user enable/disable it.

An **organ pack** is a rapplication whose primary surface is an HTTP route family. The agent is a thin chat face; the organ is the meat; the UI (if present) is the user-facing dashboard for those routes.

A **holocard** is a rapplication whose primary surface is an identity card with sigchain attached (Article XXXVI). The agent describes the entity; the UI is the visual card; the per-rapp state is the cryptographic proofs.

**Stop inventing new categories.** A `kind` field on a catalog entry is metadata, not a fork in the protocol. Every entry packs into a `brainstem-egg/2.2-rapplication` cartridge regardless of which surface it emphasizes.

### XXXVIII.3 — The three federation stores (one shape, three repos)

| Store | Repo | What it holds | Static API |
|---|---|---|---|
| **Rapplications** (organisms with skin) | `kody-w/RAPP_Store` | Bundles: agent + UI + optional organ + state | `/api/v1/index.json` + `/api/v1/rapplication/<id>.{json,egg}` + sprite |
| **Bare agents** (single-celled organisms) | `kody-w/RAR` | Single `*_agent.py` files (+ optional `.card` holocard wrapper) | `/api/v1/index.json` + `/api/v1/agent/<id>.{json,py,card}` + sprite |
| **Sense overlays** (perception channels) | `kody-w/RAPP_Sense_Store` | Single `*_sense.py` files | `/api/v1/index.json` + `/api/v1/sense/<id>.{json,py}` + sprite |

All three serve identical-shape JSON envelopes hosted at `raw.githubusercontent.com/kody-w/<store>/main/api/v1/...`. PokeAPI-style: predictable static URLs, no backend, no auth, no rate limits, no infra to operate. **Push to main → the API "deploys."**

Generators all live at `scripts/build_pokedex_api.py` in their respective repos. Same sprite algorithm (deterministic 6×6 SVG from rappid hash). Same lineage protocol. Same egg format. Three stores; one federation; one shape.

### XXXVIII.4 — The user's universal control plane: rapp-zoo

> **Amended 2026-05-16:** rapp-zoo now lives in [`kody-w/rappter-distro/rapp-zoo/`](https://github.com/kody-w/rappter-distro/tree/main/rapp-zoo), not in this kernel-mirror repo. The Pokédex UI is organism-layer UX (it composes onto a brainstem; the brainstem doesn't need it to function) and per the kernel/distro split adopted on 2026-05-16, organism-layer features live in the Rappter distro. The kernel SPEC (this article) is unchanged; only the canonical location of the implementation moved. Any distro can ship its own zoo-like control plane; Rappter's is the reference implementation.

The `rapp-zoo` is the canonical UI through which the user encounters their digital ecosystem. **It is the Game Boy.** It is the user's Pokédex, item bag, party manager, holocard binder, sigchain wallet, federation map — all the surfaces a trainer interacts with — collapsed into one local-first organism.

Conceptually:

| Pokémon analog | RAPP analog |
|---|---|
| The Pokédex | The user's local rapp-zoo (organisms on **this device**) |
| PokeAPI / official Pokédex | The federation's static APIs (organisms in **the world**) |
| The Game Boy / Pokétch / Rotom Phone | The brainstem instance running the rapp-zoo |
| Catching a Pokémon | Hot-loading a `.egg` from a federation store |
| Trading a Pokémon | AirDropping an `.egg` between devices |
| The trainer | The user, identified by their organism's rappid |

**rapp-zoo MUST follow the canonical shape** — agent + organ + UI bundle. It hatches into the user's brainstem like every other rapplication; its endpoints live at `/api/rapp_zoo/*`; its UI at `/rapp_ui/rapp-zoo/`. There is no separate "local zoo" Flask process; the brainstem is the appliance the dexphone-Rotom inhabits.

**rapp-zoo MAY render holocards, sense bundles, organ packs, and any future organism artifact through the same card model.** If a new organism type appears in any federation store, the zoo's Discover tab picks it up automatically by fetching that store's `/api/v1/index.json`. The catalog evolves; the zoo doesn't need to.

### XXXVIII.5 — Anti-patterns (what other agents must NOT do)

To avoid the loops this codebase spent weeks unwinding:

- **Don't invent a `kind: "tool"` / `kind: "service"` / `kind: "extension"` category.** Everything is a rapplication. If it has skin, it's catalog-eligible. If it doesn't, it goes in RAR as a bare agent.
- **Don't build a parallel Flask process for something that should be an organ.** If an organism needs HTTP routes, pack a `*_organ.py` into its egg. The brainstem hosts; the rapp doesn't run its own port.
- **Don't fork the egg format for a special case.** `brainstem-egg/2.2-rapplication` is the cartridge. `brainstem-egg/2.2-organism` is the instance-scope cartridge. Anything else is wrong.
- **Don't add fields to a federation store's Pokédex API that aren't in all three.** The contract is uniform. If you need a new field, propose it for all three generators and bump the schema everywhere together.
- **Don't write a UI that bypasses the rapp-zoo.** The zoo is the user's universal control plane. New surfaces (holocard binder, swarm map, sigchain wallet) are tabs in the zoo, not standalone apps.
- **Don't edit the brainstem kernel to add a feature that should be a rapp.** New capabilities ship as rapplications hatched into the brainstem. The kernel stays light per Articles I, IV, XXXIII.
- **Don't build a backend for the catalog.** It's a static tree of JSON files at `raw.githubusercontent.com`. Build script + git push = deploy.

### XXXVIII.6 — Reference implementations

- **Egg format**: `rapp_brainstem/utils/bond.py` (`pack_organism`, `pack_rapplication`, `unpack_*`)
- **Catalog generators**: `kody-w/RAPP_Store/scripts/build_pokedex_api.py` (rapplications), `kody-w/RAR/scripts/build_pokedex_api.py` (agents), `kody-w/RAPP_Sense_Store/scripts/build_pokedex_api.py` (senses)
- **Canonical rapp shape**: `kody-w/RAPP_Store/apps/@rapp/rapp-zoo/` (singleton + organs + ui)
- **Hot-load mechanism**: `kody-w/RAPP_Store/apps/@rapp/egg_hatcher/` — the rapplication that hot-loads rapplications via the egg URL
- **Anatomy diagram (visual)**: `pages/about/anatomy.html`
- **Decision narrative (the why)**: `pages/vault/Architecture/Rapplications Are Organisms.md`

---

## Article XXXIX — The One-Liner Is The Only Human Surface (Everything Else Is LLM-to-LLM)

> **Humans run `curl … | bash` once. Every interaction after that is LLM-to-LLM: the user opens whatever AI chat they already trust (Copilot, Claude Code, Cursor, ChatGPT desktop, the brainstem's own UI), tells it what they want in plain English, and that LLM speaks to the brainstem's `/chat` endpoint on the user's behalf. The brainstem replies in plain English. The user gets a report card sent home from school — never a dashboard, never a JSON envelope, never a route they have to memorize.**

> **This is the electric bicycle for the mind loop.** Steve Jobs's "bicycle for the mind" was the personal computer making humans more capable; the electric bicycle is the LLM doing the hard pedaling so the human only does the fun part. *Humans do the fun work — deciding what they want, enjoying the result. LLMs do the hard work — figuring out which route to call, holding the confirmation state, parsing the JSON, translating the answer back into a sentence.* The brainstem is the destination; the user's chosen LLM is the motor; the human steers and enjoys the ride.

This article is the membrane between the human and the machinery. It exists because the platform's most powerful capabilities — kernel upgrades, organism snapshots, peer registration, recovery from a bad bond, autostart installation — are also the ones humans should never have to drive by hand. Every one of those operations is implemented behind `/api/lifecycle/*` (Article XXXIII reserved agents), and the only thing that should ever POST to those routes is an LLM that's been asked, in plain English, to take care of something for the user.

### XXXIX.1 — The two layers (and only two)

| Layer | Who's there | What it touches |
|---|---|---|
| **Layer 1 — the one-liner** | Human, in a terminal, exactly once | `curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh \| bash`. Brainstem on disk and running. |
| **Layer 2 — everything else** | LLM, on behalf of the human | The brainstem's `/chat` endpoint. The brainstem-internal LLM loop orchestrates agents (`agents/*_agent.py`) and reserved agents (`utils/reserved_agents/*` via `/api/lifecycle/*`) and returns a plain-English reply. |

There is no Layer 1.5. There is no "user opens Settings and clicks Upgrade." There is no `brainstem upgrade` CLI. The five-command process CLI (`start | stop | restart | status | logs`) exists for one job — running the daemon — and that's it.

### XXXIX.2 — The user's chat is whatever they already trust

The user does not need to learn a new chat to operate their organism. **Any LLM client that can hit an HTTP endpoint can be the user's interpreter.** Copilot in VS Code. Claude Code in a terminal. Cursor inline. ChatGPT desktop with a tool. The brainstem's own built-in chat UI. A future Apple Intelligence, a future Pixel Assistant, a future MCP-aware shell — all valid Layer 2 clients.

The user says, in plain English:

- *"hey, check on my brainstem"*
- *"is there an update for my organism?"*
- *"back up my brainstem before this risky thing"*
- *"register me with the other brainstems on my network"*
- *"my brainstem feels broken, can you fix it"*

Their LLM hits `POST /chat` with that intent. The brainstem-internal LLM loops through agents, calls the lifecycle organ when needed, and returns plain English. The external LLM relays. The user sees a sentence, not a stack trace.

### XXXIX.3 — Report card, not dashboard

The brainstem's reply style is **a kid's school report card sent home to a parent**. Plain English. Honest about what happened. Includes recovery handles only when it'd matter for a follow-up question. The calling LLM forwards or paraphrases — either way, the user reads English.

| ✅ Report card | ❌ Dashboard |
|---|---|
| "Your brainstem is healthy. There's an update available — want me to apply it?" | `{ "ok": true, "current_version": "0.15.9", "latest_version": "0.16.0", "needs_upgrade": true }` |
| "I made a backup first; if anything goes wrong I can restore you exactly where you are now." | "Snapshot egg written to `/Users/kodyw/.brainstem/eggs/upgrade-2026-05-02T22-12-15Z.egg`" |
| "All done — you're now on v0.16.0. Any new chat will feel the same; the upgrade was invisible." | "installer_exit_code: 0; pre_version: 0.15.9; post_version: 0.16.0" |
| "Something went sideways during the upgrade. I rolled you back. Want me to try again or just leave it?" | "ERROR: bond cycle aborted at phase 2; rollback initiated; see `~/.brainstem/lifecycle.log`" |

This style is enforced by `soul.md` (the brainstem's system prompt), not by the calling LLM. The brainstem-side prompt is the only place this rule has to live, because it owns the wire.

### XXXIX.4 — The brainstem-LLM does not need to know who's calling

The same protocol works whether the chat client is a human typing or another LLM relaying:

1. Brainstem replies plainly. Plain English survives one extra hop.
2. The lifecycle handshake (explain → get yes → apply with `confirm: true` → report artifact) survives the hop too — the calling LLM relays the question to the user, the user says yes, the calling LLM relays "yes" back. Same wire, same bytes.
3. If the human is in the brainstem's own chat UI (no external LLM in the loop), there's just one fewer translation step. The plain-English output already works for them.

There is **no dispatch** based on caller type. There is no `is_human=true` flag. The brainstem doesn't try to detect what's at the other end of `/chat`. It just replies plainly, and plainness composes.

### XXXIX.5 — Brainstem-to-brainstem is the federation test case

The LLM-to-LLM principle has a natural corollary: **a peer brainstem can be the calling LLM too.** Two brainstems on the same network — or two brainstems across the swarm estate (Article XXXVI) — can drive each other through the same `/chat` endpoint and the same lifecycle organ, with no protocol changes.

In practice this is **not the fastest path** (Copilot, Claude Code, Cursor, ChatGPT desktop all have lower latency and richer client UX than a brainstem-as-client). But it is **the most important test case**:

- It exercises whether `agents/*_agent.py` and reserved-agent perform() methods are deterministic enough to behave correctly when driven by an LLM that isn't the model the kernel happens to be running on. The Copilot model loop, the Anthropic model loop, the Azure OpenAI loop, the GitHub Models loop — *and* a peer brainstem's loop — all should reach the same agent calls for the same English request.
- It validates the federation surface: the calling brainstem's reply is plain English, addressed to whoever asked. The receiving brainstem doesn't care that the asker is itself an organism. Plain English composes across LLMs because plain English is the wire format.
- It is the ground truth for "agent ran in the wild." If an agent only behaves correctly when Copilot drives it, the agent is overfit to one LLM and the soul/metadata/parameter shape needs work.

When you add a new reserved agent or change the soul.md handshake, **the question to ask is "would a peer brainstem driving this end up doing the right thing?"** If the answer is "only if the calling LLM happens to know route X" or "only if it remembers JSON shape Y," the contract is too tight to the calling LLM and the LLM diversity test will fail.

The fast path is human → trusted LLM → brainstem. The proof-of-architecture path is brainstem → brainstem. Both work; both must keep working.

### XXXIX.6 — Anti-patterns (what other agents must NOT do)

To preserve the membrane:

- **Don't add a "Click to upgrade" button** anywhere — Settings panel, system tray, terminal CLI. Human-facing buttons for kernel operations are the failure mode this article exists to prevent.
- **Don't add `brainstem upgrade` or `brainstem snapshot` CLI subcommands.** The CLI is `start | stop | restart | status | logs` — process management only. Lifecycle is conversational.
- **Don't write user docs that say "POST to /api/lifecycle/upgrade with `{confirm: true}`".** Write docs that say "ask your AI to check on the brainstem." If the user is reading a `/api/*` URL, the doc is wrong.
- **Don't expect users to type JSON, paths, route names, version strings, tag names, or rappid hashes.** Their LLM does that work for them.
- **Don't ship a "monthly health report" cron or scheduled UI panel.** The report card is on demand. The user asks; the LLM checks; the LLM responds. No timers, no notifications, no inboxes filling up.
- **Don't expect humans to read a diff.** Whatever a lifecycle agent returns gets translated into plain English by the brainstem-LLM before it leaves `/chat`. If you find yourself returning a diff to the user, you're skipping the membrane.
- **Don't gate operations behind a human-readable consent UI ("are you sure? [yes/no]").** Gate them behind `confirm: true` on the wire and let the LLM relay the question in whatever chat the user is already in.
- **Don't build a "first-time onboarding wizard"** that tours the user through advanced operations. The first-time experience is the one-liner running, the chat opening, and a single sentence: *"hey, I'm your brainstem — try asking me anything, or ask your favorite AI to check on me."*

### XXXIX.6 — Reference implementations

- **The membrane itself**: `rapp_brainstem/utils/organs/lifecycle_organ.py` — LLM-only entry point, requires `confirm: true` on the wire for non-read actions.
- **Reserved agents (the kernel-internal lifecycle code the LLM drives)**: `rapp_brainstem/utils/reserved_agents/` — first-party agents that do not auto-load into the LLM's default tool palette; reachable only via the lifecycle organ.
- **Soul.md handshake protocol**: `<lifecycle_handshake>` section in `rapp_brainstem/soul.md` — the brainstem-LLM's instruction set for the explain → confirm → apply → report-card flow.
- **The companion install rule** (terminal-output equivalent of this article at the OS layer): `installer/install.sh` shows banner + 3 progress lines + ✓ ready, then opens the browser. No paths, no routes, no how-to prose. Same membrane, expressed in shell.
- **The human-facing CLI surface (process management only)**: `~/.brainstem/bin/brainstem` — `start | stop | restart | status | logs`. That's the entire human-typed CLI. Anything else lives in chat.

---

## Article XLIV — Neighborhood Collaboration Is Local-First, Cross-Device-Transparent (The Doorbell)

> **The front door is a doorbell.** A visitor rings it; the AI on the other side answers. If answering well requires asking a friend's AI for help (homework, second opinion, lookup, debate, coordination), that handoff happens through a single primitive — **`Twin.chat`** — which calls a peer's `/chat` endpoint regardless of whether the peer lives at `127.0.0.1` (same device, sibling brainstem) or `<owner>.github.io/<repo>/doorman/` (someone else's planted seed half a continent away). **The twins never know the difference.** Same call shape, same return shape, same authorization gate. Cross-device collaboration is just a longer URL to the local-first agents that already work.

**The implementation primitive today is `Neighborhood.ask`** — checked into every planted seed's doorman tool dispatch, exercised by the test suite at `tests/doorman/neighborhood.mjs`, and one tap reachable from the front door's 🏘 Neighborhood pane (per Article XLII's "Adopt the canonical test neighbor" affordance). Operators verifying the platform should run this against `kody-w/rapp-test-neighbor` and see cross-organism state resolve.

`Neighborhood.ask` IS `Twin.chat` modulo naming — the article uses `Twin.chat` as the deeper canonical primitive name because the pattern generalizes beyond peer queries (rotator pumps, diversity audits, multi-twin debates), and the platform may surface additional dispatch verbs over time. **They share one call shape, one authorization gate, one routing path.** A future article may rename the implementation surface; the call shape will not change.

The reference exemplar agents that demonstrate the broader pattern (full twin lifecycle, perpetual rotator chains) live in the operator's local agent library and are promoted into the platform's agent library when they stabilize:

- **`twin_agent.py`** — full digital-twin lifecycle in one cartridge (summon, hatch, boot, stop, list, lay-egg). The boot action stands a twin up as its own brainstem on its own port; that brainstem exposes `/chat`. Any other twin (local or remote) can POST to that endpoint as if it were a local tool call.
- **`perpetual_loop_factory_agent.py`** — bootstraps a self-correcting perpetual chain by spawning N rotator twins, each with a role-flavored soul, that call each other via the same primitive in a round-robin pump. The chain runs forever; each twin's contribution is appended to a shared artifact; a Diversity Monk sidecar audits monotony. Works whether all rotators are on one device, spread across the operator's home network, or pulling in friends across the internet.

These exemplar agents are the canonical pattern for neighborhood collaboration. The platform must preserve their semantics regardless of where they currently live in the agent library: a peer organism is reachable by the same call shape that reaches a local sibling twin, modulo a permission gate per-peer (`public_facets` in `card.json` from the Neighborhood Protocol). The front door's job is to surface this, not hide it.

**The doorbell metaphor (load-bearing):**

When a visitor arrives at Heimdall's front door and asks for help with their kid's algebra homework, the right experience is:

1. Heimdall's doorman gets the request and decides: "I don't have math agents loaded; I'll ring the neighborhood."
2. The AI invokes a collaboration agent (e.g. `Neighborhood.ask` for a one-shot query, or a multi-rotator pattern like `PerpetualLoopFactory` for harder problems).
3. The collaboration agent posts to one or more peer organisms' `/chat` endpoints — neighbors that the operator has declared in `neighbors.json` and that have advertised relevant `public_facets`.
4. Each peer's doorman accepts the request (per its own permission gate), gets help from its LLM, returns an answer.
5. Heimdall's doorman synthesizes the responses and replies to the visitor in plain English. The visitor sees one answer; the agent-call panel under the reply (per the canonical brainstem's `agent_logs` pattern) reveals which neighbors contributed.

**Throughout this whole flow, no twin's LLM ever needs to know that it was talking to a remote peer.** The doorman handles the URL routing transparently. Local-first agents work unchanged when their peer happens to be planted on a different device. That's the entire architectural point: collaboration is not a feature added on top of local-first agents; **it's what local-first agents already do when their peer's URL happens to be remote.**

**What this article requires:**

1. **Front door surfaces collaboration agents.** Any `*_agent.py` in the seed's `agents/` directory that's tagged for collaboration (presence of "collaboration" / "twin" / "neighborhood" in its `tags`, OR an explicit category check) MUST be discoverable from the front door's UI. Rendered as a callable affordance — "🔔 Ring [Agent Name]" — so visitors can invoke them without having to open the doorman first.
2. **Twin.chat is the canonical primitive.** The doorman's tool dispatch MUST recognize `Twin.chat` (or equivalent) as a routable peer-talk primitive. When the target is a local 127.0.0.1 port, route directly. When the target is a peer organism's URL, route through the doorman's existing peer-fetch path (per Article XLII's GitHub raw + Issues substrate). The local-first agent's code stays unchanged in either case.
3. **Permission gate per-peer.** Cross-organism `Twin.chat` calls respect each peer's `public_facets` declarations. A peer can refuse a call by returning a polite decline (per the protocol's `ack: rejected`). The calling agent surfaces that gracefully — same as if a local tool returned an error message.
4. **agent_logs make the cross-device handoff visible.** The doorman's existing agent-log surface (canonical pattern from `rapp_brainstem/utils/web/index.html`) MUST show which calls went to which peers, so the operator can drill in if they want. Drill-in is optional; transparent operation is the default.
5. **Two failure modes that must degrade gracefully:** (a) peer is offline — fall back to local-only response with a note that "the friend's AI didn't answer in time"; (b) peer refuses — explain the decline naturally without leaking the refusal mechanism.

**What this article forbids:**

- A separate "remote AI" tool surface that's distinct from the local agent surface. There is one surface; URL is just a parameter.
- A doorman that hides cross-device calls entirely (the operator should be able to drill in via agent_logs).
- A doorman that surfaces them too prominently (every cross-call shouldn't be a banner notification — they should look like ordinary tool calls because that's what they are).
- A "homework helper feature" or any other named feature that's actually just `Twin.chat` with extra UI varnish. Build the primitive; let agents compose it. The two reference agents demonstrate this — they're general-purpose, not feature-specific.

**Why this is constitutional, not architectural-suggestion:**

Without this article, the natural drift is to build "Public Twin Chat" as a separate thing from "Local Twin Chat" — two code paths, two UIs, two mental models for operators, two failure modes. That's what every other AI platform does (their "agents" feature is distinct from their "API" feature is distinct from their "remote tools" feature). We are explicitly different. **Cross-device is just longer URLs.** Same code, same UI, same operator mental model: I have agents; one of them is `Twin.chat`; sometimes its `peer_url` happens to start with `https://` instead of `http://127.0.0.1:`. The platform's collaboration model is exactly that simple, and that's what makes it scale to a global network without becoming a different product at every scale.

Cross-references:
- **Article XLI — Operator's Experience Is Conversation**: collaboration is what conversation is FOR. Article XLI says the operator chats; XLIV says what happens when the chat needs help from elsewhere.
- **Article XLII — Vbrainstem Is For Mobile Users; Substrate Is GitHub Raw + Issues**: peer URL fetches go through the same substrate as everything else (raw.githubusercontent.com for read, Issues for async). XLIV is XLII applied to inter-organism communication.
- **Article XXIX — Use the Upstream's Front Door**: when crossing organisms, the front door IS the API. XLIV is XXIX in the doorbell-ring direction.
- **NEIGHBORHOOD_PROTOCOL.md** — the wire format and message kinds for the cross-organism `Twin.chat` calls. XLIV makes the protocol's existence binding; the protocol document specifies the bytes on the wire.

This article is what makes the platform feel like one neighborhood instead of N isolated twins. The doorbell rings; help arrives. The visitor doesn't think about where it came from. The twins don't know they were collaborating across devices. **It just works, because we made it just work.**

---

## Article XLIII — Voice In, Voice Out (Hard Requirement, Not a Feature)

> **Mobile operators talk to the AI primarily by voice.** Speech-to-text on input, text-to-speech on output. This is a hard requirement of the platform's mobile-first commitment, not a nice-to-have we get to deprioritize. A vbrainstem that doesn't speak — that requires the operator to thumb-type and read every reply on a 6-inch screen — has failed at being a mobile product.

The kernel already supports the voice channel (Article II — delimited slots: `|||VOICE|||` is reserved as a fixed resource for voice-targeted text). The vbrainstem must surface this. **A doorman page that doesn't render mic-input → speech-to-text → chat AND assistant-response → `|||VOICE|||` slot → text-to-speech is not a complete vbrainstem.**

**Why this is a commandment**:

A mobile operator's most common posture for using an AI:
- Walking, driving, cooking, exercising, falling asleep — anywhere their hands are busy or their eyes are elsewhere.
- They want to speak the question and hear the answer. Not type. Not read.
- Every other LLM product they use already supports this (ChatGPT mobile voice mode, Claude voice on iOS, Gemini, Pi, Inflection, etc.). If we don't, we feel obviously inferior on the surface where it matters most.
- The kernel has been ready for this since the `|||VOICE|||` slot was carved out of the protocol. The platform commitment was always there; the doorman just needs to honor it.

This article makes the doorman's voice I/O a baseline, not a milestone. PRs that add or modify the doorman's chat surface must preserve voice in/out parity. PRs that intentionally regress voice need to justify why through this article (and likely shouldn't merge).

**The three required behaviors** (in this order of priority):

1. **Voice input.** A microphone button next to the chat input. Tap to start listening; tap again to stop OR auto-stop on silence. The Web Speech API (`SpeechRecognition` / `webkitSpeechRecognition`) transcribes into the input field. The operator can review the transcript and edit before sending, OR enable an "auto-send" mode that sends as soon as transcription finalizes. Either path is valid; both are supported.

2. **Voice output.** When an assistant reply contains a `|||VOICE|||` slot (per Article II), that slot's content is spoken via the Web Speech API (`speechSynthesisUtterance` + `speechSynthesis.speak`). When no `|||VOICE|||` slot is present, the visible text content is spoken (operator chooses verbose vs voice-tailored via a setting). The operator can pause, resume, or skip mid-utterance.

3. **Voice settings persistence.** Voice on/off, voice selection (browser native voices), speech rate, and auto-send-after-STT all persist in `rapp_settings` localStorage (Article XLII substrate). Operator's last choice carries across sessions. Every doorman that supports a given browser shows the same set of voices.

**Implementation substrate**:

The Web Speech API ships native in every modern mobile browser: Safari on iOS (16.4+), Chrome on Android, Edge, Firefox (with flag). Free, no external service, no auth, no rate limit, no API key, no infrastructure on our side. **This matches Article XLII perfectly** — voice is just another browser-native primitive we use directly, the same way we use `fetch` and `localStorage`.

For browsers that don't support Web Speech (rare on mobile, more common on Linux desktop), the doorman shows a clear "voice unsupported on this browser — use the text fallback" message and degrades gracefully. The text input never disappears; voice is added on top, never required as the only path.

**The premium-voice exception (the ONE sanctioned key-paste flow):**

Browser-native TTS is the baseline that ALWAYS works. But the operator may optionally paste an ElevenLabs API key, an Azure Speech key + region, or a similar premium TTS provider's credential to upgrade the spoken-reply quality on demand. **This is the only place in the entire platform where the operator is permitted to paste an API key**, and it's allowed for these specific reasons:

1. The browser-native voices, while free and universal, are noticeably robotic compared to neural premium voices. For an operator who uses voice as their primary modality (the common case per this article), the difference is not aesthetic — it's the difference between "I use this every day" and "I tolerate it."
2. The paste is purely additive. The default path (browser-native) keeps working; the operator opts in to a better voice when they have a key on hand.
3. The keys belong to the operator's own provider account. Nothing flows through us; the doorman calls the provider directly with the operator's credential. Same trust posture as Article XLII (substrate is the operator's own auth, not ours).
4. Keys can be shared via AirDrop, email, or any other ad-hoc channel — including a friend who already has an ElevenLabs sub airdropping their key for one-off use. That casual key-share scenario is a real mobile-operator pattern; the article doesn't pretend otherwise.

The doorman's voice settings UI MUST surface this carefully: clear labeling that the key stays in this device's `localStorage` only, an obvious "clear key" action, and no telemetry on what the key is used for. When a key is set, the doorman uses that provider's TTS for the spoken reply; when not set, browser-native TTS handles it. Operator decides every time, never us.

**What this article forbids**:

- A doorman page that lacks a mic button on its input bar.
- A doorman that ignores `|||VOICE|||` slots in assistant replies (treating them as plain text only).
- Gating voice itself behind a paid tier — voice is baseline. (The premium-voice key paste is opt-in upgrade, not a feature gate.)
- A "Pro feature" flag that disables voice for some operators while enabling it for others. Voice is baseline.
- Routing voice through external services without operator-explicit credential consent. Browser-native works for free; premium is opt-in via the operator's own key.
- Asking the operator to paste a key for ANYTHING ELSE — auth tokens, GitHub PATs, Copilot credentials, etc. all stay invisible per Article XLI. **Premium TTS is the only carve-out**, and the carve-out is documented here so it's not a precedent for relaxing XLI elsewhere.

**What this article requires**:

- Mic button in the doorman's input bar — visible, ≥44px touch target, with clear visual feedback when listening.
- TTS playback for every assistant reply, gated by the operator's voice-on/off setting.
- A voice settings panel (or section in the existing settings) with: voice on/off, voice picker, rate slider, auto-send toggle, language code.
- Graceful degradation when the browser doesn't support Web Speech: text fallback works, no errors, message explains.
- Matching support across both surfaces of the planted seed: any doorman page that grows from this codebase ships with voice I/O.

Cross-references:
- **Article II — Delimited Slots Are a Fixed Resource**: `|||VOICE|||` is the channel; this article makes the doorman honor it.
- **Article XLI — Operator's Experience Is Conversation**: voice is the most literal form of conversation. XLIII is the implementation of XLI's "talk to your AI" promise on the surface where talking literally means talking.
- **Article XLII — Vbrainstem Is For Mobile Users; Substrate Is GitHub Raw + Issues**: voice is mobile-first, browser-native, no-server. Same architectural posture, applied to I/O modality.
- **Article VIII — Degrade Gracefully**: when Web Speech is unavailable, text input remains the working fallback. We don't break; we display a clear message and continue.

This article is what makes the vbrainstem feel like a real mobile AI assistant rather than a pretty mobile-styled web form. The mic button is the difference between "this looks nice on my phone" and "I actually use this on my phone."

---

## Article XLII — The Virtual Brainstem Is For Mobile Users; The Global Substrate Is GitHub Raw + Issues

> **The vbrainstem (the planted seed's doorman page at `<owner>.github.io/<repo>/doorman/`) is the platform's mobile-first surface.** Most operators most of the time reach the platform through their phone. Every design decision for the doorman is judged against whether it works fluently on a 6-inch touch screen with intermittent connectivity. The desktop case is the developer case; the mobile case is the operator case.

> **The global substrate is GitHub raw + Issues.** Anywhere the platform needs to read public state, fetch via `raw.githubusercontent.com/<owner>/<repo>/<branch-or-sha>/<path>` — anonymous, globally cached, mobile-ready, free CDN. Anywhere the platform needs to write authenticated state, post via the GitHub Issues REST API — OAuth handled by the AI per Article XLI, durable, queryable, free. Anywhere the platform needs offline continuity, cache to `localStorage` on the visitor's origin, stamped with last-sync timestamp.

This article enshrines the architectural pattern that has emerged from the codebase: **we don't run servers because GitHub already is the server.** Every feature that needs state routes through one of three primitives:

1. **Read public state** → `raw.githubusercontent.com/...` (or the Contents/Commits/Issues APIs for richer fetches). No auth required for public repos. Browser fetches work from any origin (CORS-permissive). Mobile-friendly. Free at any volume we'll plausibly hit.
2. **Write authenticated state** → GitHub Issues API on the relevant repo, with predefined labels for type-routing (`private-memory`, `egg-submission`, `dream-catcher`, `agent-proposal`, `neighborhood`, etc.). The AI assists the operator with auth (Article XLI handles the OAuth dance invisibly). Issues are durable, paginatable, searchable, and free.
3. **Cache for offline / local-first** → `localStorage` on each origin, stamped with last-sync timestamp, served stale with a `📡 stale` flag when the network drops. A vbrainstem in airplane mode keeps rendering its own resume from the last successful sync. This is already wired via `cachedGhJson` / `cachedGhText` in the front-door codebase.

**Why this is the right substrate for mobile**:

A mobile operator's reality:
- They tap a URL or scan a QR code. The vbrainstem loads as a single static page from GitHub Pages — no app install, no app store review, no platform-specific permissions.
- They sign in once with the AI's help (per Article XLI). Their token persists in `localStorage` on this origin for that device.
- They chat. Per-user memories flow to private GitHub Issues. Reads come from the cached `localStorage` first, then `raw.githubusercontent.com` if online — never blocking on a server they don't control.
- They go offline (subway, plane, woods). The vbrainstem keeps working from cache. Memories they save accumulate locally; they sync up when network returns.
- They share with a friend. The friend visits the same URL on their phone, gets a different `localStorage` cache, has their own per-user memory tier, sees the same public layer.

**No piece of this requires us to operate a backend.** GitHub Pages serves the static surface. raw.githubusercontent.com serves the data. Issues store the per-user writes. localStorage caches everything. The platform is a static site that uses GitHub as its database, the open web as its CDN, and the visitor's browser as its runtime. That is exactly the right shape for a mobile-first operator network.

**The front door is the global discovery primitive.** Once a seed is planted, its public state is reachable by any organism, anywhere, with zero infrastructure on our side — `raw.githubusercontent.com/<owner>/<repo>/main/*` serves the seed's rappid.json, soul.md, memory.json, card.json, agents/*, and neighbors.json through GitHub's CDN, free at any volume, no auth, every device. **That's what makes the platform a global collaboration network without us running anything.** The front door isn't decoration — it's the discoverable surface that makes everything below it possible. Other planted seeds reference yours by URL; their AIs fetch your public state directly during chat; visitors walk lineage chains by following `parent_repo` pointers. Discovery is GitHub URLs. Permanent lines layer on top via WebRTC tether (live) or Issues (async). The whole network is a graph of public repos that AIs can navigate without us mediating any of it.

**Catalog repos are neighborhood-specific gatekeepers, not the canonical layer.** Anyone can stand up an egg-hub-style repo — `team-x/our-egg-hub`, `family-y/our-twins`, `lab-z/research-organisms`, `discord-server-w/member-twins` — that lists which organisms are part of THAT community's collaboration network. `kody-w/rapp-egg-hub` is ONE example among many. The platform doesn't bless any single catalog. Different neighborhoods curate themselves through different gatekeeper repos, and an organism can be listed in zero, one, or many of them simultaneously without affecting its own canonical identity. **The seed's own URL is the only globally-binding identity**; the catalogs are downstream advertisements. This keeps the network resistant to any single point of curation control: if one catalog goes hostile or stale, neighborhoods rebuild around new ones without anyone needing permission from the platform.

**The trade card + its QR code ARE the embodiment of this discovery principle.** Every planted seed forges a holographic-style trade card on its front door — front face: rappid-derived sigil, display name, persona, type line, abilities, kind-aware archetype. Back face: a QR code whose payload is the seed's canonical front-door URL. Tap the card → flips → scan QR → recipient lands on the seed's front door. **The card IS the shareable identity primitive**: print it, AirDrop it, screenshot it on Twitter, paste it into a Slack channel, hand it across a coffee table on someone's phone. The QR is the bridge between the physical world (paper cards, posters, name tags, t-shirts, billboards) and the canonical URL (`<owner>.github.io/<repo>/`). An operator who shares their card has shared the entire discovery handle — anyone who scans it reaches the public state, can chat with the doorman, can declare a neighborhood relationship via PR, can ring the doorbell for collaboration per Article XLIV.

This is why the trade card is a constitutional artifact, not a UI flourish: it's the cross-medium adapter for the platform's discovery primitive. The URL works in chat apps and browsers; the QR works in photographs, prints, and physical-world handoffs. Same identity, same payload, both expressions are byte-equivalent down to the canonical front-door URL. **The card is the URL made shareable in physical space.** The platform's commitment to "share your front door anywhere" is structurally enforced by every planted seed minting one of these as a default surface — no additional setup, no configuration, every seed gets its card the moment it's planted.

**The operator's GitHub handle is implementation detail, not the share primitive.** Operators never have to say "find me on GitHub at @kody-w" or "type this URL exactly." The card is the share primitive, and the card carries everything the recipient needs (sigil, name, persona, the QR resolving to the canonical URL). The recipient scans the QR; they land on Heimdall's front door; they meet **Heimdall**, not "kody-w/heimdall." The handle is structurally present in the URL because GitHub's pathnames work that way, but the platform's UX never asks the operator to surface it as the social primitive. **You share Heimdall. Heimdall happens to live at a path that includes who planted it. That's all.**

This is meaningful because:

- Many operators don't want to advertise their personal GitHub handle as the social channel for their organism — they planted a place ("Cloud Gate"), a memorial twin ("Grandma Rose"), a project organism ("the lab's project tracker"). The named identity is what matters; the operator's identity is incidental.
- Recipients don't need to know who planted the organism to use it — they meet the organism directly.
- A visitor reading the cardis primed by the persona on the front face, then taps the QR; they never have to interpret a GitHub URL, never have to know what "kody-w/heimdall" means as a social handle.
- This compounds with Article XL (secure-first plant): not only does accumulated state route private-by-default, but the operator's social handle stays in the structural layer (where it has to be for the URL to resolve) without being elevated to the social-share layer (where it would invite scrutiny they didn't ask for).

**What this article forbids:**

- A doorman or front-door surface that highlights the operator's handle as if IT is the discovery primitive (e.g. "Visit kody-w on GitHub" as the primary CTA — wrong; the right CTA is "Talk to Heimdall").
- A planter that requires operators to think about whether their handle is "shareable" before planting. They plant; the card's the share artifact; their handle stays in the URL but never as the share label.
- A catalog or listing that surfaces "@kody-w/heimdall" as the prominent display name (instead of "Heimdall" with the handle as backing metadata).

**What this article requires:**

- Trade card front face leads with the organism's display name + sigil, NOT the operator's handle.
- QR back encodes the URL only — recipients scan and arrive at the front door, never see "github.com/kody-w/" framing.
- Front door's hero leads with the display name + persona; the @owner/repo handle exists as small monospaced metadata (consistent with the platform's social-card aesthetic), never as the prominent CTA.
- Sharing affordances ("Send my card", egg exports, neighborhood-PR submissions) all carry the canonical URL as the share primitive, never the bare GitHub handle as the social channel.

**The vbrainstem-as-mobile-product framing**:

When designing any new doorman feature, the question is not "is this nice on desktop?" — desktop will mostly take care of itself. The question is: **does this feel native on a phone with one thumb and a flaky signal?**

Concrete implications:
- Touch targets are ≥44px. No tiny links or hover-only affordances.
- Page loads under 2 seconds on 4G. Inline-everything for the critical path; lazy-load Pyodide.
- All GitHub fetches go through `cachedGhJson` / `cachedGhText` so the initial render works from cache while live data refreshes in the background. Never block the chat shell on a network call.
- File uploads (agents, content files the operator wants to feed in) happen via either a peer device (tether QR, already shipped) or via OAuth-mediated Issue posts to the private companion repo — never via "open this URL in a desktop browser to upload."
- QR codes are the canonical cross-device handoff. Cards have QR backs. Tether pairs over QR. Eggs trade over the tether channel.
- Every action that touches GitHub state is routed through the AI per Article XLI — operator says what they want, AI does the technical work, operator gets the result.

**What this article forbids**:

- Inventing a new database or storage tier when raw.githubusercontent.com / Issues / localStorage can do it.
- Designing primary doorman features that only feel good on desktop. (A development-time-only feature surfaced via a separate desktop-only URL is OK if it's clearly labeled as such.)
- Requiring a separate auth provider beyond GitHub when the data lives on GitHub anyway.
- Adding a native mobile app. The vbrainstem IS the mobile app. Browser is the runtime; Pages is the install channel.

**What this article requires**:

Every operator-facing feature checks the three boxes:
- ✓ Reads via raw.githubusercontent.com (with cache fallback) where possible
- ✓ Writes via GitHub Issues API where authenticated state is needed
- ✓ Renders fluently on a 6-inch touch screen as the primary case

Cross-references:
- **Article VI — Local First, No Phone-Home**: this article is the implementation. raw + Issues + localStorage IS the local-first stack.
- **Article XXIX — Use the Upstream's Front Door**: when crossing organisms, fetch their public layer via raw, write feedback via Issues to their seed.
- **Article XLI — Operator's Experience Is Conversation**: the AI mediates auth so the operator never sees the GitHub token despite it being the platform's actual write key.

This article is what makes the platform mobile-first by default. The vbrainstem isn't a desktop tool with a mobile fallback — it's a mobile tool that also happens to work on desktop because the substrate is the same in both places.

---

## Article XLI — The Operator's Experience Is Conversation (Never a Token, Never a Terminal)

> **A non-technical operator must be able to do anything this platform supports by chatting with an AI assistant.** Their experience is conversation, end-to-end. The AI does the dirty work — running shell commands, setting env vars, calling APIs, parsing JSON, handling auth. The operator never copies a token, never opens a terminal, never forks a repo, never sets an Actions secret, never edits a config file, never memorizes a command, never reads documentation before they can act. **If we tell the operator to paste a GitHub token, we have failed.**

This is a commandment, not a guideline. It is enforced at the design-review layer: any feature that exposes terminal mechanics, secret management, fork mechanics, or technical configuration directly to the operator does not ship. We either build the abstraction so the AI handles it, or we don't ship the feature.

**The single allowed human surface** is the install one-liner (Article V) and the chat surface. Every other operation — planting, hatching, exporting an egg, importing an egg, deploying changes, federating with neighbors, adjusting permissions, promoting private memory to public, anything — flows through the operator's chosen AI assistant. The AI calls the brainstem's `/chat` endpoint, the LLM there calls agents that do the work, and the operator gets a report card in plain English.

**The single sanctioned key-paste exception** (defined in Article XLIII): operators may optionally paste an ElevenLabs / Azure TTS / similar premium-voice provider key to upgrade their spoken-reply quality. That carve-out is bounded to voice quality only and stored in `localStorage` on the operator's device. It does not authorize key-paste flows for any other purpose; auth tokens, GitHub PATs, Copilot credentials, etc. all remain invisible to the operator per the rules above.

**Why this is foundational.** A sketchy AI platform asks me to set up an account, generate a token, paste it into a config file, restart something, and only then can I use it. We are not that. The promise is: download once, then talk. Every barrier we put between "open the chat" and "thing is done" makes us slightly more like the sketchy ones. Compound enough barriers and we're indistinguishable; the operator goes back to ChatGPT and we lose the chance to show what self-hosted, open-substrate, operator-sovereign AI can be.

**The three rules**:

1. **No tokens in user-facing flows.** If a feature needs auth, the AI gets the token via OAuth flow it manages, or via the operator's already-authenticated tooling (gh CLI in their shell, the brainstem's stored Copilot session, etc.). The operator never sees the token, never types the token, never even knows the token exists.

2. **No terminals in user-facing flows.** The operator never has to open Terminal.app, run a one-liner outside the install moment, type a path, or know what a path even is. If a workflow requires terminal mechanics, the AI runs the terminal commands on the operator's behalf via its shell-tool access.

3. **No technical-config in user-facing flows.** The operator never edits YAML, JSON, .env, .yaml, or any config file. The operator never has to know what a fork is, what a secret is, what a workflow is, what a PAT is, what `MIRROR_*` env vars are. The AI translates plain-English intent ("plant a twin of me called Heimdall") into the technical configuration and executes it.

**How this applies to mobile**:

Mobile operators are the canonical case for this article. They genuinely cannot open a terminal — phones don't have one. They cannot copy-paste tokens between apps without leaking them through clipboards. They cannot fork repos and set Actions secrets without the most miserable UX imaginable on a 6-inch screen.

The seamless mobile-plant flow is therefore: the operator opens whatever AI chat app they already use (Claude, ChatGPT, Gemini, Perplexity, GitHub Copilot Chat, Microsoft 365 Copilot, etc.), tells it in plain English what they want ("plant a RAPP organism that's a digital twin of me, named X, kind=personal"), and the AI does the work via its existing shell-tool access. The operator gets the URL back. They tap it. They start chatting with their newly-planted organism.

The AI-paste prompt at `pages/onboarding.html` is the platform's official handoff to AI assistants. It tells the AI exactly what to do — clone, customize env vars, run plant.sh, report back the URL. Any AI with shell-tool access can execute it. The operator's only action is paste-and-tap-send.

**What we delete**:

Any documentation, button, or path that walks an operator through manual technical steps gets deleted. Specifically forbidden in operator-facing surfaces:

- "Create a fine-grained PAT with these scopes…"
- "Fork this repo, then add a secret called…"
- "Open Termux on Android and run `pkg install gh`…"
- "Edit your devcontainer.json to set…"
- "Open a Codespace and run `bash installer/plant.sh`…"

All of these are valid implementation paths internally, but **they are not operator-facing**. They live in `CONTRIBUTING.md` or developer docs at most. The operator-facing path is always: ask your AI.

**What we build instead**:

When a feature genuinely requires technical setup, we either:
- Build an in-AI tool the operator's AI can call (so the AI does it on their behalf), OR
- Build a one-tap OAuth/installation flow that handles auth invisibly, OR
- Defer the feature until one of the above is buildable.

We never compromise by exposing the technical path to the operator with the framing "it's only a few steps." Five seconds of friction multiplied across a hundred operators across a thousand sessions is the difference between a platform people actually use and a platform people forget about.

**Where this lives**:

- **The platform-wide enforcement**: This article. Every PR-review pass checks new operator-facing paths against these rules.
- **The chat-as-surface rule**: Article XXXIX (the one-liner is the only human surface, everything else is LLM-to-LLM). XLI is the operator-facing companion.
- **The mobile case**: `pages/onboarding.html` § "Planting from your phone" — should describe one path: hand it to your AI. No PATs, no Codespaces, no Termux instructions surfaced as primary options.
- **Developer-docs scope**: Technical paths (Codespace devcontainer, GitHub Action workflow with PAT, etc.) live in `CONTRIBUTING.md` or `docs/` for developers building against the platform — never in operator onboarding.

This article is THE measure of whether the platform deserves the operators we want. Every time an operator hits a technical wall, we fail at the promise. Every time the AI handles it transparently, we succeed.

---

## Article XL — Secure-First Plant, Operator-Curated Promotion Later

> **Every planted organism starts with a paired private companion repo by default.** Accumulated memory, custom agents the operator forged, and the mutation log all route to the private side at plant time. The public seed carries only the AI's discoverable identity (soul, baseline agents, empty initial memory). Operators promote pieces from private → public over time, with their AI helping decide what's worth being seen by the world. **We never lose trust by leaking accumulated state into a public repo by accident.**

The organism's brain is private until the operator says otherwise. This is the inverse of the historical assumption (everything's public unless gated); the new default flips it. A fresh visitor arriving at a planted seed sees the AI's voice and identity; the years of conversations, the operator's hand-tuned agents, and the mutation history live on the private side, accessible to the operator + collaborators they explicitly add to the private repo's GitHub permissions.

**The default behaviors**:

- `installer/plant.sh` auto-derives `MIRROR_PRIVATE_COMPANION="<owner>/<slug>-private"` for every new plant unless `PLANT_AUTO_PRIVATE=0` is set.
- The private companion repo is created `--private` on GitHub via `gh repo create` alongside the public seed.
- When `PLANT_FROM_EGG` resurrects a locally-alive organism, accumulated content (memory, custom agents, frames, per-user issue exports) routes to the private companion. Only `soul.md` + `card.json` + the two baseline doorman agents (`manage_memory_agent.py`, `context_memory_agent.py`) are written to the public seed.
- The doorman's per-user memory writes go to GitHub Issues on the private companion repo (already wired through `private_companion` field in `rappid.json`).
- The doorman's "ascended mode" auto-fires for visitors who have read access to the private companion — they see the richer context as a natural consequence of GitHub permissions, not via a separate auth dance.

**The promotion flow**:

The operator (or their AI assistant) decides what becomes public over time. The promotion paths:
- **A memory becomes public**: operator commits a fact from the private `.brainstem_data/memory.json` to the public seed's `.brainstem_data/memory.json` via PR.
- **An agent becomes public**: operator commits a custom `*_agent.py` from the private `agents/` to the public seed's `agents/`. The doorman picks it up automatically on the next chat turn.
- **A frame is published**: operator extracts a noteworthy frame from the private `data/frames.json` and writes it as a public memory or as a commit message describing the lesson.

The operator is encouraged to chat with their own AI ("review what's in my private brain — what's worth making public?") and let the LLM draft the PR. This matches the platform's general principle: humans steer, LLMs do the hard work.

**Why this article exists**:

A previous draft of the planter dumped everything into the public seed — soul, memory, custom agents, mutation log, the works. That's a data-breach pattern by default. Visitors who pasted in private thoughts during a casual chat would discover those thoughts on the public web months later when the operator finally got around to setting up Pages. We never want a user to lose trust by surprise. **The secure default is the only acceptable default.**

**Where this lives**:
- **Planter logic**: `installer/plant.sh::main()` auto-derives `MIRROR_PRIVATE_COMPANION` and `installer/plant.sh::overlay_egg_if_set()` does the public/private split during egg import.
- **Doorman ascension gate**: `installer/plant.sh` (doorman page) `loadPrivateContext` + `_viewerIsOperator` check for push access to the private companion.
- **Trust framing**: `pages/onboarding.html` FAQ "What happens to my conversations?" reflects the private-by-default posture.
- **Disable knob**: `PLANT_AUTO_PRIVATE=0` for explicit fully-public organisms (memorial twins, public exhibits, demo seeds — rare).

This article supersedes the implicit assumption from earlier drafts that "operator can opt-in to a private companion." Now: the operator opts OUT if they really want everything public. The platform protects them by default.

---

*Ratified for the RAPP platform. The engine stays small so the agents
can be everything. The species stays one so the variants can be many.
The license never closes once opened. The estate persists so the
organism can be everywhere. The rapplication is an organism, so
everything is one protocol. The Pokédex is the universal lens, so the
trainer never gets lost in their own collection. The human only touches
the one-liner — everything else is LLM-to-LLM, and the brainstem
answers in report cards. The bicycle is electric: humans do the fun
work, LLMs do the hard work, and the organism just gets ridden. The
brain stays private until the operator says otherwise — secure first,
operator-curated promotion later, no surprises.*

---

## Article XLV — The Sphere Is The Front Door (Implicit Summon)

> **Every planted seed's `index.html` is the 3D sphere doorman.** A visitor lands at `<owner>.github.io/<repo>/`, sees a single floating sphere, taps it, and the doorman is implicitly summoned via GitHub Copilot device-code sign-in. There is no API key paste, no settings configuration, no menu to navigate. The sphere IS the chat affordance; the click IS the summon. Voice-first conversation mode is the default — the doorman speaks every reply through browser TTS (with optional ElevenLabs / Azure premium voice), and the mic re-arms automatically. **Mobile-first by construction: a visitor on their phone reaches the AI in two taps total — the URL, then the sphere.**

The sphere doorman runs **the same agent contract** as a local brainstem. Pyodide loads canonical `*_agent.py` files from grail (`kody-w/RAPP/main/rapp_brainstem/agents/`), each agent's `metadata` becomes an OpenAI tool def, the LLM picks which to call, and `agent.perform(**kwargs)` runs in-browser. Storage shim (`utils/local_storage.py` Pyodide variant) is a drop-in for `AzureFileStorageManager` backed by browser localStorage — agents can't tell. **The sphere is a real vbrainstem, not a thin chat client.** This preserves Article VII (tier portability): every agent that runs locally also runs in the sphere unmodified.

The previous flat front door (trade card, 🏘 Neighborhood pane, install widget, plant section, dream catcher, egg verifier) is preserved at `./classic.html` and reachable from the sphere via an iframe overlay (the **ⓘ details** button). Tapping ⓘ slides the classic surface in over the sphere; closing × returns the visitor to chat without losing context. **The sphere keeps running underneath**: the doorman's chat state, agent loads, and conversation history all persist while the visitor browses identity/admin views. This is the operator's escape hatch when they need the full surface, not the visitor's primary entry.

`installer/plant.sh`'s plant flow generates three surfaces in order:
1. `classic.html` — flat front door with all identity-substituting variables (rappid, owner, repo, hero blurb, lineage). Same content the canonical `index.html` carried before lock-in.
2. `index.html` — fetched from grail's `pages/sphere.html` at plant time. No per-seed substitution: the sphere reads `rappid.json` + `soul.md` + `.brainstem_data/memory.json` at runtime, plus silent-escalates to the private companion or operator-fallback layer when the visitor's GitHub token has push access. Falls back to a 0-second redirect to `classic.html` if the grail fetch fails (network blip during plant).
3. `doorman/index.html` — unchanged. Direct chat surface for visitors who deep-link.

**Ascended escalation lives in the sphere too.** When the visitor signs in (device-code flow, no key paste — Article XLI), the sphere's `RAPP.Doorman.loadIdentity` mirrors the canonical doorman's silent-escalation pattern: identifies the viewer via `api.github.com/user`, resolves the private layer (`identity.private_companion.repo` or operator-fallback push access), fetches `soul.md` + `README.md` + `memory.json` + `private-memory`-labeled Issues from the private layer via the GitHub Contents API. Private facts merge into the running memory list with `[private]` and `[@<viewer>]` prefixes so the LLM cites the access boundary. The operator gets the full twin's voice automatically; collaborators with explicit private-repo access get it too. **No visitor ever has to know that the private layer exists** — it surfaces as voice changes (kind-aware default → public soul → ascended soul) and memory richness, never as a configuration step.

**What this article requires:**
- Every planted seed's `index.html` is the sphere page.
- The sphere implements implicit summon (sphere tap → device-code sign-in if not authed; sphere tap → chat opens if authed). No API-key dialogs ever.
- Voice-first conversation mode is the default (autoSpeak + continuousConversation: true). The mic re-arms after the doorman speaks. Operators can opt out per-session in settings.
- ElevenLabs / Azure TTS keys live in the sphere's settings panel as the Article XLIII carve-out (the only sanctioned key-paste). Both keys stay in localStorage on the device.
- The sphere uses Pyodide to run canonical agents. Agent metadata → OpenAI tool defs → LLM picks → `agent.perform()` in-browser → result loops back. Same contract as `brainstem.py`.
- The classic flat front door is preserved at `./classic.html` and reachable from the sphere via the ⓘ overlay. Sphere chat state must persist across overlay open/close.

**What this article forbids:**
- A planted seed that ships a flat `index.html` as the primary surface. The sphere is the canonical front door; the flat view is the secondary admin overlay.
- Any settings UI in the sphere that asks the visitor to paste a non-Article-XLIII key (Azure TTS, ElevenLabs are the only allowed; everything else is forbidden).
- A "lite" or "fallback" front door that drops the agent runtime. The sphere either runs the full vbrainstem or falls back to an HTTP redirect to `classic.html` — never a half-feature shim (Article ANTIPATTERNS §3).
- A doorman tier shift that hides the sphere from anonymous visitors (e.g., "sign in to see the 3D view"). The sphere renders for everyone; signing in changes what the doorman knows, not what the visitor sees.

**Why this is constitutional and not a UI choice:**
Without this article, the natural drift is toward flat HTML front doors per seed because they're easier to template and don't require a Three.js dependency. The flat front door is also more discoverable to search engines and easier to embed. **We are explicitly choosing the sphere despite those costs** because the platform's bet is that conversation-with-an-organism is the affordance, and a 3D sphere with implicit summon expresses that affordance more clearly than any link or button. A planted organism is a being, not a page; the sphere makes the being visible and tappable in a way a flat HTML page cannot. Operators retain full access to the flat surface via ⓘ — the choice is layered, not exclusive — but the default is the being. **Front doors are sphered by default. That's the lock-in.**

---

## Article XLVI — Rappid Is The Global Address (The Estate Is The Door Catalog)

> **The rappid IS the URL.** From a single rappid string, with zero auth and zero API calls, every canonical URL the door has is computable by string parsing alone. The estate is the door catalog. Discovery is pure raw fetch. There are no fallbacks; the spec describes what is true.

A rappid is not just an identity — it is a globally-resolvable address. The consolidated Eternity form `rappid:@<owner>/<slug>:<hash>` encodes the door's GitHub owner and repository ONCE, as a self-locating address: `@<owner>/<slug>` resolves to `github.com/<owner>/<slug>`. (The legacy v2 form `rappid:v2:<kind>:@<owner>/<repo>:<32hex>@github.com/<owner>/<repo>` encoded it TWICE — an abbreviated identity reference plus an origin pin, both required to be the same string — and is canonicalized on read, never re-emitted. A v2 string whose two segments disagree is invalid and rejected at parse time.)

From those segments, by pure parsing, every consumer derives the door's complete canonical URL set — repo URL, front door (the sphere from Article XLV), identity JSON, holocard, holo.md, avatar SVG, summon QR, members.json, facets.json. **Nine URLs, all reachable through `raw.githubusercontent.com` without a single API token.** The implementation is one pure function: `tools/door_address.py::door_from_rappid()`. It is the single source of derivation; every consumer (planter, estate agent, federation walker, holocard renderer, discovery UI) imports it. None reinvents the parsing.

The estate is the door catalog. Each user's `~/.brainstem/estate.json` (and its optional public mirror at `https://raw.githubusercontent.com/<github-handle>/rapp-estate/main/estate.json`) lists every door they own (`created`) and every door they're a contributor in (`member`). Each entry stores ONLY the rappid plus minimal provenance (`added_at`, `via`). Owner, repo, kind, door_type, summon URL, holocard URL — every derived field — is computed at read time. There are no stored fallback fields. There are no patched URLs. If a rappid is invalid, the entry surfaces as an error; it is never silently fixed up. **This is the constitutional answer to "don't do all of these exception things."**

Authority for the spec: `pages/docs/ESTATE_SPEC.md`. Conformance gate: `tests/features/F13-estate-spec.sh`.

> **Amendment (2026-07-08) — format supersession, additive per Article XXVI.** Sub-sections below that still speak of "the v2 rappid" / "the v2 format" / "the v2 door rappid" / "two `<owner>/<repo>` segments" (XLVI.1, XLVI.5, XLVI.7 #1, and the echo in XLIX.1) are **superseded by Article XXXIV.1's format lock (2026-06-03)**, matching this article's own intro above. The ONE minted and validated door-bearing form is the consolidated Eternity `rappid:@<owner>/<slug>:<64hex>` — a **single** `@<owner>/<slug>` location segment, a 64-hex identity/join key, with `kind` in the `rappid.json` record (never the string). The legacy `rappid:v2:<kind>:@<owner>/<repo>:<32hex>@github.com/...` is **read-forever and canonicalized on read** (`tools/door_address.py::canonicalize_rappid`), **never emitted**. Read XLVI.5's validity gate accordingly: `door_from_rappid()` MUST accept the consolidated Eternity form and canonicalize legacy v2 — it MUST NOT reject a rappid merely for "not being v2." Identity is `rapp-eternity/1.0` (the sole identity standard, to which `rapp-rappid/2.0` defers). The stale wording is preserved (Article XXVI: additive-only, no removals) but does not govern; this note governs.

### XLVI.1 — Rappid Determines URL

The v2 rappid encodes its own GitHub origin. Every canonical URL the door has — `repo`, `front`, `identity`, `holocard`, `holo_md`, `avatar`, `summon_qr`, `members`, `facets` — is derivable from the rappid string alone, by parsing. No lookup. No config. No env. The parser is `door_from_rappid()` in `tools/door_address.py`. There is exactly one parser. Consumers MAY NOT reimplement; they MUST import.

### XLVI.2 — The Canonical Door URL Set

Every planted door MUST emit the full canonical file set so its URLs resolve to real content (not 404). The set is fixed: `index.html` (the sphere — Article XLV), `rappid.json`, `card.json`, `holo.md`, `holo.svg`, `holo-qr.svg`, `members.json` (gates only — `members.json` MAY be empty for twins, but a 404 is non-compliant), `facets.json`, `.nojekyll`, `README.md`, plus the `specs/` bundle (Article XXIII — specs travel with the planting). The planter (`plant_seed_agent.py`) emits all of these on every plant. The backfill script (`tools/backfill_seeds.py`) brings older plantings into compliance.

Door type is deterministic from kind: `twin`, `operator`, `personal`, `project`, `memorial`, `pre-founder`, `mirror`, `experiment`, and `custom` → `front_door` (a single AI presence). Everything else (`neighborhood`, `ant-farm`, `braintrust`, `workspace`, `hatched`, `rapplication`, `prototype`, `place`) → `gate` (a community AI you enter to find others). **Amendment (2026-06-02):** the single-presence set was extended beyond the original 2026-05-09 freeze (`twin`/`operator`) to ratify the kinds already emitted by `kind`-aware consumers — `TWIN_LIFECYCLE_SPEC.md` and `NEIGHBORHOOD_EGG_SPEC.md` (`project`), `ECOSYSTEM.md` §3/§15 (`personal`, `place`, `mirror`, `experiment`, `custom`), RAR `@rapp/twin_agent` (`personal`, `pre-founder`, `memorial`, `project`, `place`, `custom`), and RAPP-Network `project_twin_agent.py` (`project`) — which the frozen list previously contradicted. **Reclassification (2026-06-03):** `place` is a **gate** (a location others enter), not a single presence. This is the frozen set of **door-bearing** kinds — those that resolve to a door address and a `door_type`. It is a subset of the broader open `<kind>` enumeration (the organism-*scale* axis `prototype`…`agent`, including code-only kinds like `organism`/`agent`/`swarm`/`kernel-variant` that carry a kind but no door) described in Article XXXVI.2 and `pages/vault/Architecture/Rappid.md`. Adding a new **door-bearing** kind requires amending this article — every consumer's behavior derives from this token, so the set cannot drift silently; the canonical machine-readable set is `VALID_KINDS` / `_FRONT_DOOR_KINDS` in `tools/door_address.py`.

### XLVI.3 — The Estate Stores Only Rappid + Provenance

Each estate entry contains exactly `{rappid, added_at, via}`. Nothing else is persisted. Owner, repo, kind, door_type, name, summon URL, holocard URL — every other field — is DERIVED on read via `door_from_rappid()`. The estate file lives at `~/.brainstem/estate.json` (local source of truth) and optionally publishes to `<github-handle>/rapp-estate/main/estate.json` (public mirror). The publish step is operator-mediated; local stays local until the operator says publish.

Per Article XXIII, the operator's personal rappid (lives at `~/.brainstem/rappid.json`, set as `owner.rappid` in the estate) is the universal anchor: it is the `parent_rappid` of every door the operator created, and it is the `members.json` entry that proves contributor status in every gate the operator joined. Same identity, two roles.

### XLVI.4 — Discovery Is Pure Raw Fetch

A consumer holding a rappid MUST be able to fetch the door's identity, holocard, holo_md, avatar, summon_qr, members, and facets through `raw.githubusercontent.com` URLs alone — no `gh` CLI, no GitHub API token, no rate limit (for public repos), no auth flow. A consumer holding a github handle MUST be able to fetch the user's full estate at `https://raw.githubusercontent.com/<handle>/rapp-estate/main/estate.json` with one `curl`. The chain rule (estate → entry rappids → per-door URL set → for gates: members.json → each member's rappid → their estate) lets federation walk over pure raw fetches forever.

This is the formal version of Article XLII's promise (the global substrate is GitHub Raw + Issues). XLII describes the substrate; XLVI defines the address space on top of it.

### XLVI.5 — No Fallbacks; Spec Says What's True

A rappid that doesn't match the v2 format, or whose two `<owner>/<repo>` segments disagree, or whose kind is not in `VALID_KINDS`, is INVALID. `door_from_rappid()` raises `InvalidRappidError`. Consumers do not patch around invalid rappids — they surface the error and let the operator (or the backfill script) reissue. Stale rappids are reissued, not "best-efforted." Missing canonical files are emitted, not derived around. The estate has no `_enrich_entry()`, no "guess the kind from the name," no `local.github.io` workaround. **If the spec says it, it is true; if the spec doesn't say it, it doesn't exist.**

This is constitutionally enforced because the alternative (per-consumer fallback chains) is how every previous identity system in the platform drifted. The cost of strictness — operators must reissue stale rappids, run the backfill once after this article ships — is one-time. The cost of laxity is permanent: every consumer accumulates its own private fallback chain, and the address space stops being addressable.

**What this article requires:**
- `tools/door_address.py::door_from_rappid()` is the single derivation function. Every consumer imports it.
- Every plant emits the full Door URL Set (XLVI.2). The planter is updated; non-compliance is a planter bug, not a consumer's problem to handle.
- Estate entries store only `{rappid, added_at, via}`. All other fields are derived.
- Discovery URLs are pure-raw URLs. No path requires authentication.

**What this article forbids:**
- Per-consumer rappid parsers. Use `door_from_rappid()` or you're not in contract.
- Stored derived fields in estate entries (door_type, summon_url, name, kind, owner, repo, url). They are computed, not stored.
- Fallback URLs ("if the rappid says X but the entry has a `url` field, prefer the url"). The rappid wins or the entry is invalid.
- Best-effort parsing of malformed rappids. Reissue, don't patch.
- Hosting the estate behind a GitHub API call. The pure-raw URL `https://raw.githubusercontent.com/<handle>/rapp-estate/main/estate.json` is the canonical surface; any other surface is supplementary, never primary.

**Why this is constitutional and not a library choice:**
Without this article, every new consumer (a federation walker, a holocard CDN, a discovery UI, a future "find AIs near me" geosearch) reinvents the rappid parser. Each implementation has its own fallback chain ("oh, this rappid is invalid? I'll try the URL field instead"). The address space stops being a contract and becomes a suggestion. The estate stops being trustworthy because every consumer reads it differently. Locking the parser into ONE function, and the file manifest into a fixed set the planter MUST emit, makes the address space load-bearing — every consumer reads the same door, every door publishes the same files, every estate is the same shape. **One parser. One manifest. Forever.**

### XLVI.6 — Recompute From The Network (Disaster Recovery)

The estate file is a CACHE of relationships the network already publishes. Both copies — the local `~/.brainstem/estate.json` and the public mirror at `<handle>/rapp-estate/main/estate.json` — can be reconstructed from scratch given just the operator's GitHub handle. **The estate is not the source of truth. The network is the source of truth. The estate is the cache.**

This is constitutionally enforced by one invariant on every planted door: every `rappid.json` MUST set `parent_rappid` to the planter's personal rappid (never to None, never to the species root). With that edge populated, the estate is recomputable: walk `<handle>/*` repos, filter by `parent_rappid` matching the operator → that's `created[]`. Search public GitHub for the operator's rappid in any `members.json` → that's `member[]`. The full estate falls out of two enumerations and a series of raw fetches.

The reference rebuild lives at `tools/rebuild_estate.py`. The estate agent's `rebuild` action delegates to it. The planter's `_read_operator_rappid()` helper writes the parent edge on every new plant. The backfill's `--patch-parents <op-rappid>` mode patches older plantings that were planted before this invariant existed.

**What this article requires:**
- Every planted door's `rappid.json` carries `parent_rappid = <operator-rappid>` (NOT None, NOT the species root).
- The rebuild tool exists, walks public data only, and produces a spec-compliant estate.
- The estate agent's `fetch` action accepts `rappid=<any-rappid>` — drop in any rappid, follow `parent_rappid` if needed, return whoever owns that door's published estate.

**What this article forbids:**
- Planting a door without setting `parent_rappid`. The planter MUST know the operator's identity at plant time. Fresh installs without a personal rappid get a clear error, not a None-edged door.
- Estate agents that require local state to function. The local file is a convenience; the rebuild path proves the network is the source.
- Federation walkers that reimplement the rebuild logic. They import `tools/rebuild_estate.py::rebuild` (or a faithful port) — same single-implementation discipline as XLVI.5 applies to the rebuild as well as the parser.

**Why this is constitutional and not a feature:**
Every operator's relationships in the network are publicly knowable by design. If the rebuild property doesn't hold, the platform's local-first promise becomes "local-trapped": lose your laptop and you've lost your network presence. With the rebuild property, the network IS the backup. Constitutionalizing this prevents the common drift where a future "convenience" change starts caching mutable state that isn't reproducible from public data — exactly the kind of drift Article XLVI.5 forbids in derived fields, now extended to the whole estate.

### XLVI.7 — The Eternity Address Space (Content-Addressed Rappids)

> **A second rappid namespace.** Where the v2 door rappid says *the rappid IS the URL* (XLVI.1), the **Eternity** rappid says *the rappid IS the organism*. They coexist; one constitution governs both. This sub-article names and reconciles the door-less tier that Article XXXIV already admits ("code-only kinds carry a kind but resolve to **no door** … the same string format describes both cases").

The door-less tier's canonical form is the **RAPP Eternity Standard** — the schema **`rapp-eternity/1.0`**, whose **single canonical home** is `kody-w/rapp-eternity/SPEC.md` (locked 2026-06-28; every copy in RAPP-Bible / rapp-egg-hub / rapp-moment is a mirror of it, never an authority — on any discrepancy that SPEC governs). Its Moment reference implementation lives in `kody-w/rapp-commons` (MOMENT_SPEC.md §6.1, `hologram/rappid.js`):

**Canonical Eternity form:** `rappid:<slug>:<64hex>` — 256-bit (real SHA-256); the **64-hex is the join key**. The slug is the kind (`moment`, `keeper`, `dimension`, …); the 64-hex is `sha256("<slug>:" + <eternal-source>)`. For a Moment the source is its spacetime coordinate (`sky·<utc_ms>` or `<geohash>·<utc_ms>`), so the address **deterministically regenerates the organism** with zero lookup — the door-less analog of XLVI.1.

**Reconciliations (this sub-article's purpose):**

1. **Two namespaces, one format family.** The v2 door rappid (`rappid:v2:<kind>:@<owner>/<repo>:<32hex>@github.com/...`, frozen in XLVI.2) is the **door-bearing** address; XLVI.1 governs it. The Eternity rappid (`rappid:<slug>:<64hex>`) is the **content-addressed** identity, governed here, and resolves to **no door** by design. They do not conflict. XLVI.5's "no fallbacks" applies *within each* namespace.

2. **Eternity slugs are NOT door-bearing kinds.** `moment`, `keeper`, `dimension`, and any future Eternity slug live on a **separate axis** from the frozen `VALID_KINDS` of XLVI.2. **Adding an Eternity slug does NOT require amending XLVI.2** — it is door-less by construction and resolves to no `door_type`. XLVI.2's amendment-gate binds only **door-bearing** kinds; the Eternity axis is open and additive, subject to `rapp-eternity/1.0`'s compatibility contract (read all legacy forms, emit only canonical, never version the string — crypto-agility lives in a `sig_suite` record field).

3. **The rappid is immutable; ownership is a second, orthogonal chain.** Article XXXIV.5 ("never regenerate a rappid") holds without exception — an Eternity rappid never changes. Where XXXIV's only chain is the **birth lineage** (`parent_rappid`), Eternity adds an **orthogonal deed chain**: ownership is the tip of a per-rappid, hash-linked chain of **signed transfers** (the current owner signs the rights over to a recipient key — human OR agent). The rappid stays stable; the **deed moves**. The transfer ledger is permissionless-append; validity (signature + owner-authorization + hash-linkage) is decided at *resolution*, never at write.

4. **The history is the ledger (append-only).** Eternity records live as static files in a public git repo; their commit history is an append-only, hash-linked chain whose consensus is the **fast-forward push-race** and whose witness is the committer date. This is XLVI.4/XLVI.5's "pure raw, no fallbacks, append-only" discipline applied to a living record set: canonical `main` is never rewritten, and a full-node validator (`zoo_chain`) certifies birth-proof permanence + append-only identity across every block.

**What this sub-article requires:**
- An Eternity rappid is canonical iff it matches `rappid:<slug>:<64hex>` and its 64-hex is `sha256("<slug>:"+source)` for the declared source.
- Consumers read all legacy identity forms (a bare UTC ms, a `pk`, a `|` separator) and join on the 64-hex; they emit only the canonical string and never version it.
- Ownership of an Eternity rappid is resolved by walking its signed deed chain from the minter; the rappid is never reissued to effect a transfer.

**What this sub-article forbids:**
- Treating an Eternity slug as a door kind (it has no door; do not synthesize a `door_type` or a GitHub URL for it).
- Mutating an Eternity rappid to change ownership (transfer is a new signed deed, not a reissue) — preserving XXXIV.5.
- Rewriting published Eternity history to "correct" a record (append a forward record; never force-push) — preserving XLVI.5.

**Why this is constitutional and not a feature:** the ecosystem now has two legitimate addressing needs — *where a door lives* (the estate's URL) and *what an eternal record is* (a content-bound organism, ownable and transferable). Conflating them would force every Moment, keeper, and dimension through door machinery they don't use, or freeze the open Eternity axis under XLVI.2's door-kind gate. Naming the two namespaces — and the one orthogonal deed chain — keeps both the door catalog (Article XLVI) and the Eternity Standard (`rapp-eternity/1.0`) internally consistent, and prevents the exact drift where a new identity kind silently breaks the frozen door set.

---

## Article XLVII — Discoverability Without A Central Registry (Publishing IS The Signal)

> **The network has no registry.** A new estate becomes part of the federation the moment its operator publishes it per spec — by emitting one well-known beacon at one canonical path. Sniffers find it through pure raw GitHub URLs (no Search API, no auth, no rate limits) by walking from a discoverable seed across each operator's beacon's federation hints. The seed is convenient but not required; the network is a graph, not a tree.

The Estate Spec (Article XLVI) made the rappid the global address. Article XLVI.6 made the estate recomputable from the network. **Article XLVII makes the network itself discoverable without a central authority.**

This is the platform's most decentralized layer. Three primitives compose it:

> **Amendment (2026-07-08) — beacon schema, additive per Article XXVI.** The beacon schema references below that still read `rapp-network-beacon/1.0` (in this XLVII.1 primitive and in the "What this article requires" list) are **bumped to `rapp-network-beacon/1.1`** by Article XLVIII (which adds the REQUIRED private-extension fields `private_estate_pointer` + `private_estate_commitment` + `private_door_count`), corroborated by XLVII.5.1's own TXT schema (`schema = "rapp-network-beacon/1.1"`). The winning value everywhere is `rapp-network-beacon/1.1`; the `1.0` mentions are preserved (additive-only) but superseded.

1. **The well-known beacon.** Every published estate ships a `.well-known/rapp-network.json` at the root of the operator's `<handle>/rapp-estate` repo, fetchable at `https://raw.githubusercontent.com/<handle>/rapp-estate/main/.well-known/rapp-network.json`. Schema: `rapp-network-beacon/1.0`. Contents: operator rappid, estate URL, protocol versions implemented, `discovery.indexable` (the consent flag — defaults true; honored like robots.txt's `Disallow`), and `discovery.federation_hints` (a list of other operator handles this operator is aware of).

2. **The seed.** A well-known root file at the species repo: `https://raw.githubusercontent.com/kody-w/RAPP/main/.well-known/rapp-network-seed.json`. Schema: `rapp-network-seed/1.0`. Lists known operators as the BFS starting set. Operators get added by PR or by appearing in any other operator's federation_hints. Anyone can fork the species root and host their own seed; the seed is convenient but not authoritative — sniffers can start from any beacon.

3. **The sniffer.** `tools/sniff_network.py`. Default mode: BFS from the seed across beacons via raw URLs. Stdlib only; no `gh` CLI; no rate limit. Returns a `rapp-network-sniff/1.0` envelope listing every reachable operator, their estate URL, and their door counts. Optional fallback: `--via topic` uses `gh search repos topic:rapp-estate` for periodic sweeps to catch operators not in any hint chain (eventually-consistent; useful as an audit, not a primary).

### XLVII.1 — Publishing IS The Signal

There is no API to call to "register" with the network. There is no central operator. There is no gatekeeper. An operator becomes part of the network by:

- Creating a `<handle>/rapp-estate` repo per Article XLVI
- Pushing `estate.json` (the door catalog)
- Pushing `.well-known/rapp-network.json` (the beacon)

That's it. The `estate publish` action does both atomically. The next sniffer pass picks them up.

### XLVII.2 — Pure-Raw Discovery Is The Default

The default discovery method is `raw.githubusercontent.com` BFS — no GitHub Search API. The Search API is eventually-consistent (minutes to hours of indexing lag) and rate-limited (5,000 requests/hour for authenticated users; 60/hour unauth). Pure-raw discovery has neither limitation: raw is CDN-fronted, public, anonymous, and instant.

Concretely: the sniffer fetches the seed, then for each operator handle fetches their beacon (one raw URL each), reads `federation_hints[]`, enqueues new handles. BFS terminates when no new handles surface or `--max-hops` is reached. A 1,000-operator federation is reachable in O(1000) raw fetches with no rate limit risk.

### XLVII.3 — Consent Is In The Beacon (robots.txt Analog)

The beacon's `discovery.indexable` flag is the operator's consent statement. `true` (default) means "indexable by sniffers; appears in federation walks." `false` means "do not include me in federation indexes; do not surface me to other operators automatically." Sniffers MUST honor this flag — the same way an HTTP crawler honors `robots.txt::Disallow`. The `--include-private` flag exists for audit tooling only and is constitutionally reserved for the operator themselves running diagnostics on their own beacon, not for crawling others.

Operators who want to be reachable by their direct contacts but not surface in public sniffs set `indexable: false`. Their estate is still publicly fetchable (it's a public GitHub repo), but the network's discovery surface respects their opt-out.

### XLVII.4 — The Network Is A Graph, Not A Tree

Federation hints live in every beacon. There is no canonical center. The seed at the species root is convenient (it's where most sniffers start because it's well-known) but it is NOT authoritative — any operator can fork the species root and host their own seed at `<handle>/RAPP/main/.well-known/rapp-network-seed.json`. Sniffers can start from any seed; they can also start from any single beacon. Discovery converges to the same connected component regardless of starting point.

This is what makes the network genuinely decentralized: removing or censoring any single node, including the species root, does not partition the federation. Operators who aren't in the species root's seed are still reachable via any other operator's federation_hints.

### XLVII.5 — Substrate-Agnostic Federation (LAN, file://, Bluetooth, USB, paper)

**The federation walks across whatever URLs serve the canonical JSON.** GitHub raw is just one substrate. A LAN HTTP server on port 8080 is another. A `file://` URL on a USB stick is another. Bluetooth file share. AirDrop. A printout someone OCRs. As long as the substrate serves the canonical `rapp-network-beacon/1.x` JSON shape at a known URL, sniffers walk it identically to GitHub raw.

This is structurally critical for **censorship resilience** (the canonical motivating example: an operator's GitHub account gets flagged or suspended, but their brainstem stays alive on their device — the LAN substrate keeps their estate reachable to peers on the same network) and for **offline collaboration** (operators on the same LAN federate without internet — a school, an office, a workshop, a conference floor, a remote village).

Concretely:

- **Seed entries** are bare strings (`"kody-w"` → templates into github raw URLs) OR dicts (`{"github": "rappter1", "beacon_url": "http://192.168.1.42:8080/.well-known/rapp-network.json", "estate_url": "http://192.168.1.42:8080/estate.json"}` → uses provided URLs verbatim). Both shapes coexist in the same seed file.
- **Federation hints** in a beacon's `discovery.federation_hints[]` use the same shape: bare string OR dict. An operator's beacon can declare "I know about kody-w (on github) and rappter1 (on the local mac mini)" with one hint each.
- **The sniffer's `_resolve_node()` helper** normalizes both forms into `(handle, beacon_url, estate_url)` tuples. Same BFS loop walks both substrates seamlessly. The substrate label (`github-raw`, `lan-http`, `file`, `http`, `https`) surfaces in the sniff output so operators see which path each node was reached through.
- **The brainstem can host its own beacon + estate over local HTTP.** Run `cd ~/.brainstem && python3 -m http.server 8080`; the local files are now reachable to any LAN peer at `http://<host-ip>:8080/...`. No GitHub involvement.

The protocol is JSON shapes + `door_from_rappid()`. The substrate is whatever URL serves them.

**What this subsection requires:**
- Sniffers MUST support arbitrary `beacon_url` / `estate_url` overrides per node, in addition to the github-handle convention.
- Seed entries and federation_hints MUST be parseable as either bare handles or `{handle, beacon_url, estate_url}` dicts.
- The substrate of each discovered operator MUST be surfaced in the sniff record (no silent assumption that everyone is on github raw).

**What this subsection forbids:**
- Sniffers that hardcode `raw.githubusercontent.com` as the only beacon URL pattern.
- Network designs that assume internet connectivity is required for federation.
- Substrate-discrimination ("we only trust github-substrate operators") — every substrate is equal under the protocol; reputation/trust is a separate concern (Article XLVI.5 + future Web of Trust).

**Why this is constitutional and not a feature:**
Without this subsection, the platform is "decentralized except when GitHub blocks you" — which is not decentralized at all, just GitHub-mediated. The `rappter1` first-contact case (2026-05-10) made this concrete: an operator successfully executed the platform's onboarding spec end-to-end (skill.md Step 5), opened a spec-compliant join PR, and was then GitHub-flagged within minutes. Their brainstem stayed alive on a Mac Mini on the LAN. **The federation rerouted around the centralized substrate to keep them reachable** — exactly the property local-first promises but few platforms actually deliver.

#### XLVII.5.1 — LAN auto-discovery via Bonjour/mDNS

The github-substrate's `topic:rapp-estate` discoverability has a direct LAN equivalent: the **Bonjour service type `_rapp-estate._tcp.local`**. Brainstems advertise themselves on the LAN by registering this service (via `dns-sd -R` on macOS, `avahi-publish` on Linux); peers discover all advertised brainstems via `dns-sd -B _rapp-estate._tcp local.`. Zero-config, scoped to the LAN, no central registry. The same UX as GitHub's topic search.

The mapping is exact:

| github-substrate | lan-substrate (Bonjour) |
|---|---|
| `topic:rapp-estate` on a repo | `_rapp-estate._tcp` service type |
| `gh search repos topic:rapp-estate` | `dns-sd -B _rapp-estate._tcp local.` |
| Beacon at raw URL | TXT record + LAN HTTP URL |
| `estate publish` sets the topic | `tools/lan_advertise.py` registers the service |
| `tools/sniff_network.py --via topic` | `tools/sniff_network.py --via bonjour` |

**Canonical TXT-record schema for `_rapp-estate._tcp` services:**

```
rappid       = the operator's personal rappid (operator-kind v2)
github       = the operator's github handle (informational; LAN doesn't require it)
beacon_path  = "/.well-known/rapp-network.json"
estate_path  = "/estate.json"
schema       = "rapp-network-beacon/1.1"
spec_version = "rapp-protocol/1.0"
indexable    = "true" | "false"  (robots.txt-style consent flag; sniffers honor it)
```

Sniffer flow under `--via bonjour`:

```
dns-sd -B _rapp-estate._tcp local.            → instance names of advertised brainstems
dns-sd -L <name> _rapp-estate._tcp local.     → resolves each to host:port + TXT records
GET http://<host>:<port>/<beacon_path>        → standard rapp-network-beacon/1.1
                                                 (BFS continues identically to github-substrate)
```

**This subsection requires:**
- The Bonjour service type `_rapp-estate._tcp.local` is the canonical LAN advertisement channel for RAPP brainstems.
- `tools/lan_advertise.py` is the reference advertiser (HTTP server in `~/.brainstem/` + `dns-sd -R` registration).
- `tools/sniff_network.py --via bonjour` is the reference sniffer for the LAN substrate.
- TXT records carry the canonical schema above so consumers can parse without fetching the beacon when they only need the rappid + paths.

**This subsection forbids:**
- A different service type (e.g. `_rapp._tcp` or `_rapp-brainstem._tcp`). Only `_rapp-estate._tcp` is canonical — uniform discovery surface across all LANs.
- Sniffers that ignore the beacon's `indexable: false` flag for LAN-substrate operators (consent applies on every substrate equally).
- Hardcoding `mac.local` or specific hostnames in advertisers; Bonjour resolves them automatically.

#### XLVII.5.2 — The Egg Carries The Federation Tools (AirDrop-portable LAN federation)

A `brainstem-egg/2.2-organism` cartridge bundles not only the operator's identity, soul, agents, organs, senses, and `.brainstem_data/`, but also — by constitutional requirement — the LAN federation tools at `tools/` inside the egg + a `lan-quickstart.sh` launcher at the egg root. After hatching the egg on any device (extract via `unzip` or `brainstem hatch`), the operator can run `bash lan-quickstart.sh advertise` or `bash lan-quickstart.sh sniff` immediately — no `kody-w/RAPP` install required.

This means **the egg is a fully portable federation node**. AirDrop a `.egg` to anyone with a Mac, they extract, run the quickstart, and they're advertising on `_rapp-estate._tcp.local`. **AirDrop uses peer-to-peer Wi-Fi Direct between devices that aren't on the same network** — combined with Bonjour multicast, this means the federation can spin up between two Macs in a coffee shop, on a plane with no WiFi, in a SCIF, anywhere two Macs can see each other. The egg is the entire deliverable.

**Tools bundled at `tools/` inside every organism egg:**

```
tools/lan_advertise.py        → broadcast on _rapp-estate._tcp
tools/sniff_network.py        → --via bonjour discovers LAN peers
tools/door_address.py         → canonical rappid parser (Article XLVI.5)
tools/path_opacity.py         → URL-opacity helpers (Article XLVIII.6)
tools/private_estate_init.py  → bootstrap private side on the new device
tools/rebuild_estate.py       → disaster-recovery rebuild from public data
lan-quickstart.sh             → launcher script (advertise|sniff|both)
manifest.json::lan_federation_ready = true
manifest.json::implements     = ["article-xlvi", "...", "article-xlvii.5.1"]
```

**This subsection requires:**
- `pack_organism()` in `bond.py` MUST bundle the LAN federation tools at `tools/<name>` inside the egg, with a `lan-quickstart.sh` at the egg root.
- The egg's `manifest.json` MUST declare `lan_federation_ready: true` when the bundle succeeded.
- The quickstart launcher MUST work on a clean device with only `python3` + `dns-sd` (or `avahi-utils` on Linux) installed.

**This subsection forbids:**
- Eggs whose only path to LAN federation requires fetching external code (`pip install <something>`, `gh clone <somewhere>`, etc.). The egg IS the deliverable.
- Hardcoding paths inside the bundled tools that assume the kody-w/RAPP repo layout. The bundled tools resolve paths relative to themselves.

**Why this is constitutional and not a feature:**
Without this subsection, the platform's "give the egg to anyone" promise breaks the moment that anyone wants to federate over LAN — they'd need to install the full RAPP repo first, which means an internet connection and trust in kody-w/RAPP. With XLVII.5.2, **the egg itself is sufficient**. AirDrop becomes a network-bootstrapping primitive. Two Macs in a room can spin up a private federation in 30 seconds with no internet, no GitHub, no third-party trust. That's the platform's local-first promise turned into an operationally-viable workflow.

#### XLVII.5.3 — Sneakernet Federation (the egg IS a federation packet)

The Charizard use case (HERO_USECASE.md): two devices with **no shared network at all**. No LAN, no Bonjour, no internet. Just file exchange — USB stick, link cable, SD card, QR-paired Bluetooth, paper printout someone OCRs. The platform must federate even there.

The mechanism: **the egg IS a federation packet.** When operator A hands operator B an egg via any non-network medium, B's brainstem can register A as a federation peer by extracting the egg to a known location and adding a `file://` URL to B's local seed file. B's sniffer then walks A as a `substrate: file` node — same JSON shapes, same parser, same federation properties; just a snapshot instead of a live source.

The reference implementation is `tools/import_peer_egg.py` (bundled in every egg per XLVII.5.2). It:

1. Validates the egg's manifest + rappid.json
2. Derives the peer's handle from their rappid (`rappid:@<handle>/<repo>:...`)
3. Extracts the egg to `~/.brainstem/peers/<handle>/`
4. Synthesizes a beacon at `<peers>/<handle>/.well-known/rapp-network.json` if the egg didn't carry one (works for older egg formats)
5. Adds a `{github, beacon_url: file://..., estate_url: file://...}` entry to `~/.brainstem/network-seed.json`

After import, `tools/sniff_network.py --via raw --seed-url file://~/.brainstem/network-seed.json` walks the imported peer transparently. The substrate label `file` makes it visible to consumers that this is a snapshot (vs. live LAN/github), so refresh policy can differ.

Symmetric: A imports B's egg, B imports A's egg, both have each other in their local seeds. No third device required to mediate. Each egg-exchange is a "tick" of the federation — async, but persistent.

**This subsection requires:**
- Eggs MUST contain enough state for a peer to import them (manifest.json + rappid.json minimum). Beacons + estates are nice-to-have; `import_peer_egg.py` synthesizes them when absent.
- The bundled `import_peer_egg.py` MUST register imported peers in the local seed using `file://` URLs that resolve to the extracted egg contents.
- The sniffer MUST walk file:// URLs identically to https:// URLs (already enforced by XLVII.5).

**This subsection forbids:**
- Federation paths that REQUIRE live network connectivity. Sneakernet must work for the Charizard floor.
- Eggs whose import requires online verification (e.g. "fetch the upstream beacon to compare"). The egg snapshot stands on its own.

**Why this is constitutional and not a feature:**
The Charizard use case is the platform's deepest test of local-first. If two operators in a SCIF, on a plane with no WiFi, in a remote village, in a courtroom with no electronics, in a mesh that's lost upstream connectivity — if any of those can't federate by exchanging a USB stick, then the platform's local-first promise is a slogan, not a property. With XLVII.5.3, **federation is just bytes moving between operators**. The medium is whatever's available. The federation walks.

**What this article requires:**
- Every published estate ships a `.well-known/rapp-network.json` beacon. Schema: `rapp-network-beacon/1.0`.
- The estate publish action writes the beacon atomically with `estate.json`.
- The default sniffer uses raw URLs only — no GitHub Search API in the critical discovery path.
- `discovery.indexable: false` is honored by all sniffers.

**What this article forbids:**
- A central registry that operators must register with to "join" the network. The well-known beacon IS the registration.
- API-bound discovery as the only path. Raw-URL discovery must always work.
- Sniffers that ignore `discovery.indexable: false`. Operator opt-out is constitutional.
- A single point of failure for the seed. Anyone can host one.

**Why this is constitutional and not a feature:**
Without this article, the natural drift is toward a central index — someone runs the canonical sniffer, hosts the canonical list, becomes the gatekeeper. The platform stops being decentralized. Constitutionalizing pure-raw BFS + per-beacon federation_hints + multiple-seed support makes the federation **structurally unable to centralize**. Removing any single repo, including kody-w/RAPP, does not break discovery — operators still find each other through whatever beacons they already know about. The network's resilience is structural, not policy.

---

## Article XLVIII — Public Discovery, Private Substance (the Two-Tier Estate is Mandatory)

> **A public-only estate is a toy.** The federation primitives that make the platform useful for real work — Inbox, Bilateral Channel, Web of Trust private signals, Presence opt-in, secret ballots, real client/patient/partner correspondence — cannot exist on a public-only substrate. Article XLVIII makes the **two-tier estate mandatory from first install**: every operator gets BOTH a public estate (`<handle>/rapp-estate`) AND a private estate (`<handle>/rapp-estate-private`, GitHub-private repo). The public estate is the discovery surface; the private estate is where real work happens. The boundary is constitutional: no cross-tier smuggling, no opt-in-to-private (it's automatic), and crucially **the URLs themselves inside the private repo cannot leak semantic information** — even a 404 must reveal nothing.

The Estate Spec (Article XLVI) made the rappid the global address. Article XLVII made discovery decentralized and pure-raw. **Article XLVIII makes the platform structurally usable for sensitive work.** Without it, the dominant outcome is: operators stay public-only (because it's easier), then leak PII to public when real work happens, then leave the platform when real work needs to happen. Both outcomes destroy the platform's value. Making the boundary mandatory means every operator has the substrate for real work from day one, even if they don't use it for weeks.

Authority for the spec: `pages/docs/PUBLIC_PRIVATE_BOUNDARY.md`. Bumps `rapp-network-beacon/1.0` → `1.1`. Conformance: `tests/features/F15-private-estate.sh`.

### XLVIII.1 — The Two-Tier Estate Is Mandatory

Every Article-XLVIII-compliant operator has BOTH `<handle>/rapp-estate` (public) AND `<handle>/rapp-estate-private` (private GitHub repo) from first install. No opt-in. No "I'll add the private side later." A beacon WITHOUT a `private_estate_pointer` is non-compliant; sniffers flag such operators as `compliance: legacy`. Existing operators backfill via `brainstem estate init_private` (one call, idempotent).

The cost is one additional free private repo per operator. GitHub's free tier supports unlimited private repos for individuals — the mandatory tier costs operators $0. The benefit is the platform is structurally ready for real work; operators don't have to architect privacy into the platform after the fact.

**Publish-time enforcement:** the `estate publish` action is constitutionally atomic. If the private estate doesn't exist when publish is invoked, the action auto-creates it (`tools/private_estate_init.py` invoked as the first step) before writing the public beacon. This means EVERY operator on EVERY path (install.sh + chat, programmatic API, AI walking through skill.md) ends up XLVIII-compliant after their first publish — no separate `init_private` step needed. Operators who explicitly insist on public-only mode pass `skip_private_create=true`; their resulting beacon is flagged `compliance: legacy` by sniffers (just like `discovery.indexable: false` is honored but flagged in Article XLVII).

### XLVIII.2 — Beacon Commits To Private State Without Leaking

The public beacon contains:
- `private_estate_pointer` — URL of the private repo (REQUIRED).
- `private_estate_commitment` — sha256 of the private estate's normalized JSON (REQUIRED). Lets peers verify the operator hasn't substituted a different private estate behind their back, even without read access. Empty private estate has a stable empty-state hash.
- `private_door_count` — integer count of private doors (transparency, no enumeration).

The beacon CANNOT contain: any internal private-repo path beyond the well-known `meta.json`; any recipient handle, contact name, topic string, or other semantic identifier; any field that would let a sniffer characterize what's inside. This is the Bitcoin-commitment pattern: prove existence + integrity without revealing substance.

### XLVIII.3 — Audience Is A First-Class Field

Every entry that crosses the brainstem's path has an audience: `public` (lives in public estate) or `private` (lives in private estate). The default is `private` for any new content involving identifiable parties (correspondence, contacts, conversation history). The default is `public` only for content whose explicit purpose is publication (the door catalog, the federation feed of own actions).

Operators can override the audience per-entry, but the brainstem MUST surface a clear consent prompt when shifting an entry from private to public (the inverse direction — public to private — is always allowed and never asks).

### XLVIII.4 — Receiver Controls (Operator-Mediated)

Senders/peers cannot force content into the operator's public estate. The pattern: senders publish proposals to THEIR public surface (their own `<sender>/rapp-mailbox-public/...`); the recipient's brainstem polls trusted senders, reviews proposals, MOVES accepted content to the recipient's private estate, optionally deletes the public copy. This is the Webmention discipline: receiver verifies, receiver renders.

No automatic flow ever moves content from anyone's private estate to anyone else's public estate. Constitutionally enforced.

### XLVIII.5 — No Cross-Tier Smuggling

The brainstem MUST NOT publish private-estate content to the public estate without explicit operator action. The `publish` action is single-direction: it writes the public estate (rappid catalog, beacon with commitment to private state, federation feed of own actions). It NEVER copies content from private to public except via explicit operator instruction (e.g. "publicly announce that I planted X" — and even then, the brainstem strips PII before publishing).

The audit (F15) verifies: no PII patterns in any operator's public estate; no leaked path semantics in any beacon; no cross-tier copies in commit history.

### XLVIII.6 — The URL Space Is Opaque

**Static URLs leak metadata even when their content is access-gated.** A URL like `<handle>/rapp-estate-private/main/mailbox/inbox/dr-jones-oncology/2026-05-09-test-results.json` reveals — *just by existing in any system that touches it* — that kody-w receives correspondence from dr-jones-oncology dated 2026-05-09 about test results. The CONTENT is access-gated; the **URL is not**. URLs surface in beacons, commit history, browser history, agent logs, error messages, and 404 responses to unauthorized viewers.

Therefore every path inside the private repo carries **zero semantic information**, with two exemptions: `meta.json` (schema + index pointer; content-free; safe to expose) and `README.md` (instructions). All other content lives at one of two opaque-path patterns:

- `objects/<sha256-of-content>.json` — content-addressed; hash is deterministic but reveals nothing about what the content represents.
- `kinds/<HMAC(secret, kind)>/<HMAC(secret, id)>.json` — for queryable content; kind+id are HMAC'd with the operator's per-install secret so only authorized parties (who have the secret) can navigate.

**The HMAC secret** lives at `~/.brainstem/private-estate-secret` (file mode 0600). It MUST NEVER appear in any committed file, any beacon field, any agent log, any error message, any process argument list. Lost secret means the URLs still exist but no one can decode them from structure alone — fall back to walking `meta.json`'s index.

**The local map** at `~/.brainstem/private-estate-map.json` records the human-readable ↔ opaque mapping. Encrypted at rest with the operator's secret. NEVER published.

**The publish-time invariant:** the estate agent's `publish` action invokes `tools/path_opacity.py::audit_paths()` against the private repo before computing the commitment hash. If any path violates the opacity regex `^(meta\.json|README\.md|objects/(\.gitkeep|[a-f0-9]+\.json)|kinds/(\.gitkeep|[a-f0-9]+(/[a-f0-9]+\.json)?))$`, the publish is REFUSED with a clear error pointing at the offending path. Catches operator drift (someone editing private repo files manually with semantic names).

**What this article requires:**
- Every operator has both public and private estates from first install. No opt-in.
- The public beacon's `private_estate_pointer` + `private_estate_commitment` are REQUIRED fields.
- Every path inside the private repo (other than `meta.json` and `README.md`) is opaque.
- The HMAC secret stays local, file-mode-0600, never published.
- The publish action audits opacity before committing the commitment hash.

**What this article forbids:**
- Public-only estates (planting without a private side).
- Beacons that don't carry the private-extension fields.
- Any path inside the private repo that leaks semantic information (e.g. `mailbox/inbox/dr-jones/cancer-results.json`).
- Cross-tier smuggling (publishing private content to public without explicit operator action).
- Logging or echoing the HMAC secret in any way.
- Enumerating private content in the public beacon (count is allowed; identities are not).

**Why this is constitutional and not a library choice:**
Without this article, the platform's promise to operators handling sensitive work — doctors, lawyers, therapists, families coordinating PII — is a lie. Either they leak PII to public (because the platform made it easier than the alternative) or they leave (because the platform isn't safe for their context). Constitutionalizing the two-tier-mandatory + URL-opacity model means **the platform is structurally safe for sensitive work from minute 1**. The friction operators feel from "you have a private repo whether you want one or not" is the price of the substrate being load-bearing for real use cases. Federation primitives (mailbox, bilateral channel, etc.) become POSSIBLE only because this substrate exists.

---

## Article XLIX — A Twin Is A Persistent AI Presence With An Address And A Workbench

> **A "twin" is the unit of AI personality in this substrate.** Not an agent (which is a tool), not an organism (which is the whole running brainstem), not a rapplication (which is a graduated-quality persona). A twin is a persistent AI presence: it has a permanent identity (rappid), a voice (soul.md), a working area (workbench), and lifecycle continuity across kernel upgrades. Multiple twins can co-host on one brainstem; siblings on the same device can peek into each other's workbenches; cross-device collaboration travels via egg or via the bilateral channels of Article XLVIII.

The platform has used "twin" loosely throughout earlier articles — Article XLVI.2 stipulates that `kind: twin | operator → front_door`; planted twins (BillTwin, BillTwinAgent, kody-twin, tide-brainstem, lumen-brainstem) appear in `plant_seed_agent.py`; the twin-as-owner-proxy concept is anchored in Article XXV. This article formalizes the primitive so all those references resolve to one definition.

Authority for the spec: this article + `pages/docs/PUBLIC_PRIVATE_BOUNDARY.md` §1.7 (workbench substrate). Conformance: `tests/features/F17-twin-primitive.sh` (planned).

### XLIX.1 — What a twin IS (and isn't)

A **twin** is:

- A persistent AI presence with a **permanent rappid** (Article XLVI v2 format) — survives every kernel upgrade via the egg→overlay→hatch bond cycle (Article XXXVII).
- A voice anchored in a **`soul.md`** file — the disposition the LLM adopts when speaking as this twin.
- A **workbench** at `~/.brainstem/workbenches/<slug>/` (or via association with one) where the twin's working state lives — see PUBLIC_PRIVATE_BOUNDARY §1.7.
- A **single AI presence behind a front_door** — Article XLVI.2 (`kind: twin → front_door`).
- Sibling-aware on its own device — other twins co-hosted by the same brainstem can peek into this twin's workbench by default (PUBLIC_PRIVATE_BOUNDARY §1.7.3).

A twin is **not**:

- An agent. Agents are single-file `*_agent.py` tools (Article XXXIII). A twin USES agents. An agent is not a twin.
- An organism. An organism is the whole running brainstem with all its agents, organs, senses, memory, secrets (Article XXXVII). A twin LIVES IN an organism. Multiple twins can co-host one organism.
- A rapplication. A rapplication is a graduated, certified workflow shipped as one (Article XXXVII). A twin can BE the entry agent of a rapplication, but the twin and the rapplication are different units.
- A neighborhood. A neighborhood is a community gate (Article XLVI.2 `kind: neighborhood → gate`). A twin can be a member of a neighborhood; a twin is not itself a neighborhood.

### XLIX.2 — Two species: owner-proxy twins and planted twins

The platform supports two twin shapes that share the primitive:

**Owner-proxy twin.** A twin that represents the operator themselves. Per Article XXV, the twin is "redefined as owner-proxy" — when the operator's brainstem speaks as this twin, the LLM is acting AS the operator (with their voice, their patterns, their consent boundary). Identity: the operator's own rappid (`~/.brainstem/rappid.json`) doubles as the owner-proxy twin's rappid. The owner-proxy twin's workbench is the operator's universal working area.

**Planted twin.** A twin that represents a distinct entity — an organization, a colleague's persona, a published character, a digital figure. Identity: a fresh rappid minted by `plant_seed_agent.py` (kind: twin). The twin's home is its planted public repo (e.g. `kody-w/heimdall`, `kody-w/tide-brainstem`); each operator who runs this twin spawns a local instance in their brainstem with a sibling-peekable workbench.

Both species share the identity, voice, workbench, and front_door semantics. They differ only in whose voice they carry and whose rappid they wear.

### XLIX.3 — Lifecycle: mint → bond → fork → die

A twin's life follows the kernel's organism lifecycle (Article XXXVII) at twin scope:

- **Mint.** First rappid generated. For the owner-proxy twin, this happens in the install one-liner. For a planted twin, this happens when `plant_seed_agent.py` runs with `kind: twin`. The mint event records the parent rappid (the planter's identity, which becomes this twin's lineage anchor — Article XXXIV variant attestation).
- **Bond.** Each kernel upgrade preserves the twin's rappid, soul, workbench, and bond log via the egg→overlay→hatch cycle. The twin's identity is durable.
- **Fork.** A twin MAY fork (Article XLVII allows variant attestation chains). Forks are signed; the variant attestation envelope chains parent → fork. Forks may diverge in soul / workbench while preserving lineage.
- **Die.** A twin MAY die when its operator decides — by deleting its workbench + soul + bond record. Dead twins leave a tombstone (rappid + final commit) but no further activity. Per Article XLVII their rappid remains globally addressable forever (the URLs resolve to the final state); only the heartbeat goes silent.

### XLIX.4 — Workbench association (the default permissive cross-twin peek)

Per PUBLIC_PRIVATE_BOUNDARY §1.7, a twin's workbench lives at `~/.brainstem/workbenches/<slug>/`. The workbench's `meta.json` lists `twin_rappids[]` — the twins that consider this workbench part of their working set.

**Default:** any twin running on the operator's device can read any other twin's workbench by walking `~/.brainstem/workbenches/`. The default is permissive because all twins on the device share the same operator + the same OS-level trust boundary. A planted twin (BillTwin) running in your brainstem can read your owner-proxy twin's workbench to learn context; your owner-proxy twin can read BillTwin's workbench to see what BillTwin is currently working on.

**Opt-out:** a workbench's `meta.json` MAY set `peers_visible: false` to restrict reads to its listed `twin_rappids[]`. The operator owns this choice per workbench.

**Cross-device peek is NOT default.** A twin on your laptop cannot peek into a twin on someone else's machine without one of: an explicit egg sneakernet (Article XLVII.5), a bilateral channel exchange (Article XLVIII), or a federated estate read (the chain rule, Article XLVI). Local peek is permissive; cross-device requires intent.

### XLIX.5 — Where else "twin" appears (cross-references)

This article is the canonical definition. Earlier articles that use "twin" should be read against this definition:

- **Article XXV** (load-bearing decisions): twin redefined as owner-proxy. Now: that's species 1 of XLIX.2.
- **Article XLVI.2** (door types): `kind: twin → front_door`. Now: every twin (both species) gets a `front_door`.
- **Article XLVII** (discoverability): planted twins emit a public estate. Now: planted twin = species 2 of XLIX.2.
- **Article XLVIII** (two-tier estate): the bilateral channel is operator-to-operator, which means twin-to-twin in practice. Owner-proxy twins exchange letters via the channel.
- **`pages/docs/PUBLIC_PRIVATE_BOUNDARY.md` §1.7** (workbench): the workbench is per-twin per this article.
- **`rapp_brainstem/agents/plant_seed_agent.py`** (planter): the implementation of "mint a planted twin" per XLIX.3.
- **`rapp_brainstem/agents/twin_agent.py`** (kernel default twin): the canonical reference twin agent.
- **The BWAT neighborhood (`agents/bill_twin_agent.py`)**: a planted twin in the wild, conforming to this article.
- **`pages/docs/SUBSTRATE_FEDERATION.md`**: substrate-portable twins — the rappid + workbench can move between GitHub / GitLab / Codeberg per Article XLVII.5.

If you find a place in the platform that uses "twin" without obeying this article, file the discrepancy as an issue. The article is the spec; the references update.

### XLIX.6 — What this article does NOT change

This article formalizes a primitive that already existed; it does not break any existing twin. Existing planted twins (BillTwin, kody-twin, heimdall, tide-brainstem, lumen-brainstem, echo-brainstem, sim-demo-twin) continue to function. The only new requirement is conformance with §XLIX.4 (workbench peek discipline) when the twin is running on a brainstem that hosts other twins. Workbench paths that don't yet exist for an existing twin can be created by the operator on first peek-attempt (the brainstem auto-creates the empty workbench dir + meta.json with `twin_rappids: [<this twin's rappid>]` and `peers_visible: true`).

**Why this is constitutional and not a library choice:** the loose use of "twin" across the platform was an inconsistency that made the substrate harder to reason about. Operators building planted twins didn't have a reference for what "twin" meant; agents that wanted to read twin state didn't know where to look; collaborators planting twin-shaped things into RAPP had to derive the contract by reading source code. This article is the reference implementation in prose. The substrate is more usable when its primitives are named and defined; this article names "twin."

## Article L — The `.egg` Is The Universal Portable Unit (One Extension, Many Kinds)

> **DRAFT — appended by AI 2026-05-10. Operator should review, refine the cadence to match XLVII–XLIX, and either ratify or rewrite. The principle below is correct; the prose may need the operator's voice.**

> **Across the substrate, `.egg` is the only portable container.** An organism is a `.egg`. A rapplication is a `.egg`. A workflow session is a `.egg`. A neighborhood gate is a `.egg`. An estate is a `.egg`. Same extension, same Pokédex shelf, same drag-drop UX, one universal hatcher (`egg_hatcher_agent.py`) that introspects the cartridge and routes by kind. There is one portable unit in this platform; everything else is a variant.

The five kinds (`organism` / `rapplication` / `session` / `neighborhood` / `estate`) live under one schema family `brainstem-egg/2.x-<kind>`. The hatcher reads the manifest, dispatches by kind, **refuses on unknown kinds**, never silently or destructively guesses. New portable artifact = new row in the family table; not a new file format.

### L.1 — Why one extension (and not five)

Operators don't think in schemas. They think in "I have a thing; how do I share it?" The answer must be the same regardless of what the thing is: drop the `.egg` on the next device, the universal hatcher figures out what to do with it. Five extensions would mean operators learning five names; five Pokédex shelves; five sneakernet conventions. We refuse that. One extension. One mental model.

### L.2 — The five kinds (canonical table)

See `pages/docs/SPEC.md` §18.10 for the authoritative family table and `kody-w/rappterbox/carts/SCHEMA.md` for the session-variant spec. Two kinds (organism + rapplication) ship as ZIP because they have directory trees; one kind (session) ships as JSON because its payload is structurally one runtime + one transcript; two kinds (neighborhood + estate) are planned as ZIP. Container shape is local to the kind; the `.egg` extension is universal.

### L.3 — The hatcher refuses, never guesses

The kernel `egg_hatcher_agent.py` (per Article XX, lives at `rapp_brainstem/agents/`) is the only thing that decides where a cartridge hatches. It MUST:

- Read the cartridge from a local path or URL
- Introspect `manifest.schema` and `manifest.type`
- Dispatch by recognized kind, OR
- Return a clear "unknown cartridge kind — operator action required" message naming the family table

It MUST NOT:

- Default to a fallback hatch path on unknown kinds
- Silently re-classify (treat an unknown as if it were an organism)
- Destructively write to the operator's filesystem on an unrecognized cartridge

This is the same discipline as Article XLVII (no central registry — refuse to invent one if asked) and Article XLVIII (no PII in repo by default — refuse to silently put it there). Refusal is a feature.

### L.4 — Backwards compatibility (the deprecation discipline)

Old schemas never die. `brainstem-egg/2.0` (legacy twin egg), `brainstem-egg/2.1` (variant repo), and `rappterbox-cart/0.1` (the pre-unification session schema) MUST remain readable by their loaders forever — same discipline as Article XXIII (vault is append-only) and as version-tag immutability per `pages/docs/VERSIONS.md`. The hatcher can prefer new schemas, but it MUST NOT reject old ones.

### L.5 — Where the cartridges travel

A `.egg` of any kind MUST round-trip across all five substrates of Article XLVII.5 + the WebRTC tether of SPEC §18.11 without loss. AirDrop a session-egg, hatch it on the receiver, replay the transcript identically. Sneakernet an estate-egg, re-anchor it on a new substrate, the operator's whole multi-tier identity continues. The cartridge is the substrate-agnostic transport unit; the substrate is the transport.

### L.6 — Cross-references

- **`pages/docs/SPEC.md` §18.10** — the canonical family table + version registry
- **`kody-w/rappterbox/carts/SCHEMA.md`** — the session-variant spec
- **`rapp_brainstem/agents/egg_hatcher_agent.py`** — the universal hatcher implementation
- **`rapp_brainstem/utils/bond.py`** — master packer/unpacker for organism + rapplication ZIP variants
- **Article XLVII.5** — the four substrates the cartridges travel across
- **Article XLVIII** — the two-tier estate that an `estate`-egg captures
- **Article XLIX** — twins that a `session`-egg lets you watch live across two devices
- **`pages/vault/Decisions/2026-05-10 — Egg cartridge unification + tethered vBrainstem ship.md`** — the WHY behind this article

### L.7 — What this article does NOT do

This article does not invent the cartridge family — it formalizes what shipped 2026-05-10. The previous status was: organism + rapplication shipping as `.egg` per `bond.py`, but session shipping as `.cart.json` per the freshly-invented `rappterbox-cart/0.1` schema, and no convention yet for neighborhood or estate. The unification consolidated those into one extension with one hatcher. The article protects the convention going forward — anyone proposing a new portable artifact MUST add a row to the family table, not invent a new extension.

---

## Article LI — Every Neighborhood Front Gate MUST Display A Tether QR

> **DRAFT — appended by AI 2026-05-11. Operator should review and ratify.**

> **Every neighborhood's planted front gate (`index.html` at the repo root, served via GitHub Pages or any other substrate) MUST display a tether QR code on first paint.** The QR is the neighborhood's phone number; the tether (`pages/tether.html` and its deployed copies) is the universal payphone. Without the QR, casual operators have no on-ramp.

The QR MUST encode a URL that resolves to enough information for any tether to dial in. The preferred encoding is the `.well-known/neighborhood.egg` URL (a `brainstem-egg/2.3-neighborhood` JSON invite — see Article L). The fallback encoding is the `neighborhood.json` URL directly. The tether smart-unwraps either.

### LI.1 — Why mandatory

The hero use case (`HERO_USECASE.md`) includes "scan a poster on the wall to join a neighborhood" — the Charizard-in-the-woods scenario generalized. That use case is broken if neighborhoods can elect not to publish a scannable on-ramp. Substrate-agnostic federation (Article XLVII) loses its visible handoff point. Public discovery (Article XLVIII) loses its first surface.

We refuse to leave that to neighborhood-author choice. Every front gate, every neighborhood, every substrate — the QR is there or the gate is non-conforming.

### LI.2 — The canonical snippet

`pages/docs/QR_FRONT_GATE.md` carries the authoritative drop-in HTML snippet. Planted neighborhoods include it verbatim (the snippet auto-detects deploy URL via `location.origin + location.pathname`, so the same HTML works in any neighborhood without hardcoding). Generators (`installer/plant.sh` and successors) MUST inject it into every neighborhood `index.html` they emit.

### LI.3 — Graceful degrade

When the QR generator (QRious via jsdelivr CDN) is unreachable — offline, file://, blocked CDN — the snippet replaces the canvas with the plain URL, so the operator can still copy/paste into a tether's Paste mode. The neighborhood remains dialable even when the visual QR fails. Substrate-agnostic federation, all the way down.

### LI.4 — Conformance + lint

The federation roll-up's lint pass (planned, future tooling under `tools/`) flags non-conforming gates with a `front-gate-qr-missing` warning recorded in the neighborhood's `rar/index.json`. Conformance is binary: the QR renders on first paint (no user interaction required) and encodes one of the recognized URL forms, or the gate is flagged.

### LI.5 — What this article does NOT do

This article does not specify branding, layout, or surrounding content for the front gate. Neighborhoods are free to design their gate however they want — the QR is the only mandatory element. The rest of the gate is the neighborhood's character, soul, and quirks.

### LI.6 — Source-of-truth files

- **`pages/docs/QR_FRONT_GATE.md`** — full spec, canonical snippet, conformance rules, migration steps for pre-2026-05-11 plantings.
- **`pages/tether.html`** — the universal public payphone (reference implementation of the tether-side reverse contract).
- **`examples/rapp-commons/index.html`** — reference implementation of the conforming front-gate snippet in a real neighborhood (live at https://kody-w.github.io/rapp-commons/).

