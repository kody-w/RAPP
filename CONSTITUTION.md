# RAPP — Constitution

> The principles that govern this repo. Read this before you change code.

[SPEC.md](./SPEC.md) is the wire contract. This is the authoring discipline
that keeps the wire contract shippable for a decade.

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
`~/.brainstem/rappid.json`. The schema is `rapp-rappid/2.0`; the
`rappid` field carries the unified v2-format string described in the
canonical spec at `pages/vault/Architecture/Rappid.md`:

```json
{
  "schema": "rapp-rappid/2.0",
  "rappid": "rappid:v2:<kind>:@<publisher>/<slug>:<hash>@<home_vault_url>",
  "parent_rappid": "<rappid in v2 format of the master that birthed this org>",
  "parent_repo": "https://github.com/kody-w/RAPP",
  "parent_commit": "<git SHA at birth>",
  "born_at": "<ISO timestamp>",
  "host": "<short machine identifier, opaque>"
}
```

**Format unification (ratified 2026-04-30).** There is exactly one
rappid format: the v2 unified specification. A draft `1.1` schema with
bare-UUID rappids existed briefly during April 2026; existing UUIDs
(notably the species root's `0b635450-c042-49fb-b4b1-bdb571044dec`)
were preserved by being placed in the hash field of the v2 string
(dashes stripped). No rappid was lost in the migration. **No future
article shall introduce parallel formats** — see `pages/vault/Architecture/Rappid.md`
for the antipattern principle. The species tree is one tree, and one
identifier system traverses it.

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
`rappid:v2:prototype:@rapp/origin:0b635450c04249fbb4b1bdb571044dec@github.com/kody-w/RAPP`,
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

**`rappid.json` — schema `rapp-rappid/1.1`** carries an `attestation`
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
rappid:v2:<kind>:@<publisher>/<slug>:<identity-hash>@<home_vault_url>
```

where `<identity-hash>` is the truncated cryptographic hash of the master public key. This is the unified rappid format described in Article XXXIV.1 and the canonical spec at `pages/vault/Architecture/Rappid.md`. The same format serves every organism kind in the species tree.

### XXXVI.2 — One format, one species tree

Per the unified rappid spec at `pages/vault/Architecture/Rappid.md` (ratified 2026-04-30), there is **one rappid format**, used by every organism in the species tree regardless of kind. The format is described in Article XXXIV.1 and the canonical spec; this article does not introduce a parallel format.

The differences between organism kinds (`prototype` / `kernel-variant` / `organism` / `twin` / `swarm` / `rapplication` / `agent`) are encoded as the `<kind>` field of the rappid string. The cryptographic backing (master keypair, signed root.json) is opt-in per organism — present for organisms operating cross-substrate identity (this article's domain), absent for code-only organisms (Article XXXIV's draft domain). **The same string format describes both cases.**

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

*Ratified for the RAPP platform. The engine stays small so the agents
can be everything. The species stays one so the variants can be many.
The license never closes once opened. The estate persists so the
organism can be everywhere.*
