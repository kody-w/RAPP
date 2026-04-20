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
- ❌ Central memory features. Memory is `manage_memory_agent.py` + its
  storage shim. Never an in-core dict.
- ❌ A "plugin system" for things that are not agents. Single file
  agents are the plugin system.
- ❌ New tags, subfields, or conventions added to the response body to
  carry auxiliary data. Put them INSIDE an existing slot as tags the
  server strips — this is how `<probe/>`, `<calibration/>`, and
  `<telemetry>` all live inside `|||TWIN|||`.

---

## Article II — Delimited Slots Are a Fixed Resource

Once a slot exists, it belongs to that thing **forever**. Never repurpose.
Never overload. If the twin grows a new sub-capability, it lives as a tag
inside `|||TWIN|||` — the slot is the twin's entire real estate.

Concretely:

- `|||VOICE|||` — only TTS line. Not a "short summary." Not "voice OR
  hint." Just the out-loud sentence.
- `|||TWIN|||` — the digital twin's turn. Everything twin-related
  (commentary, probes, calibration, telemetry, future signals) lives
  **inside** this block as either natural-language text or XML-style
  tags the server strips before render.

Slots get added **rarely** and **never** get removed in a minor version.
v2 is the only place a slot can be retired.

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

## Article III — Capabilities Are Files

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
curl -fsSL https://kody-w.github.io/RAPP/install.sh | bash
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
- ✅ `rapp_store/` — the rapplication catalog, sources, and eggs
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

## Article XIV — Amendments

This constitution can be amended. The only rule: amendments must preserve
Article I — **the brainstem stays light**. Any change that loads
responsibility into `brainstem.py` / `function_app.py` which could be
served by a `*_agent.py` or a tag-inside-a-slot change is rejected.

A constitution amendment is itself a brainstem-level decision. It
deserves the same "is this really necessary?" bar as adding a new
`|||<SLOT>|||`.

---

*Ratified for the RAPP monorepo. The engine stays small so the agents
can be everything.*
