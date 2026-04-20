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

## Article VIII — Amendments

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
