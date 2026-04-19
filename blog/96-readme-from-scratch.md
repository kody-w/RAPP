# RAPP

> A local-first stack for **single-file AI agents**. One `*_agent.py`, one `perform()`, one metadata dict. Zero build steps. Zero frameworks.

[![spec](https://img.shields.io/badge/spec-v1.1-blue)](./SPEC.md)
[![license](https://img.shields.io/badge/license-open--bones%2C%20closed--soul-lightgrey)](./blog/58-open-bones-close-body.md)
[![status](https://img.shields.io/badge/v1-frozen-green)](./SPEC.md)

---

## Overview

**RAPP** is a three-tier stack for running AI agents on your own machine, in your browser, or on Azure — with the same single file moving across all three. The unit of work is a `*_agent.py` file. The brainstem is the LLM loop that calls those files as tools. Everything else (swarm hosting, the mobile PWA, OS tether, the book factory, `.egg` snapshots) is built around preserving that contract.

**It is not** a framework, a platform with an SDK to learn, or a hosted service. There is no `pip install rapp`. The agents are the API.

---

## Quick start

```bash
git clone https://github.com/kody-w/RAPP.git
cd RAPP
bash start-local.sh
```

Browser opens to `http://127.0.0.1:8000/brainstem/mobile/`. Bring your own OpenAI-compatible key.

Requires `python3`. Nothing else.

---

## What you get

- **Brainstem** — the LLM loop, in HTML/JS, with hot-loaded agents as tools
- **`agents/`** — a starter binder (basic, dice, hacker news, save/recall memory, book factory, editor crew, CEO/risk personas, list files…)
- **Twin simulator** — the browser brainstem at functional parity with the local Flask one
- **Mobile PWA** — installable, offline-capable chat surface
- **T2T (Tier-2 Tether)** — bridge that gives agents real OS access on the host machine
- **`.egg` snapshots** — sealed, byte-equal twin captures (see post 82)
- **Book factory** — chained editor/persona agents that ship a finished book end-to-end

---

## Architecture

Three tiers, one contract:

1. **Tier 1** — local brainstem (laptop / phone PWA), agents run in-process
2. **Tier 2** — hippocampus / swarm endpoint, agents run server-side, multi-tenant by GUID
3. **Tier 3** — federation: swarms calling swarms with consent

The same `*_agent.py` runs unchanged on all three. See [post 72 — The Twin Stack](./blog/72-the-twin-stack.md).

---

## Components

| Path | One-liner |
|------|-----------|
| `agents/` | The single-file agents. The unit of contribution. |
| `swarm/` | GUID-routed multi-tenant agent host (stdlib `http.server` only) |
| `brainstem/` | Browser brainstem + mobile PWA + onboard hatch + card binder |
| `hippocampus/` | Tier-2 twin: ARM template + Deploy-to-Azure button |
| `tether/` | Local OS-access bridge for `tether_required` agents |
| `tools/` | Build scripts (e.g. `build-bookfactoryagent.py` — singleton bundler) |
| `tests/` | Node + browser test runner for the v1 contract |
| `blog/` | 89 posts of field notes — the working memory of the project |

---

## Run a test

```bash
node tests/run-tests.mjs
```

No deps. Exercises agent parsing, manifest extraction, seed/mnemonic round-trips, card↔`agent.py` byte equality, SHA-256 tamper detection, binder JSON round-trip, multi-agent `data_slush` chains, and twin file presence.

Or open `tests/index.html` in a browser for the same suite.

---

## Build the singleton

The book factory ships as one fat `*_agent.py` containing the whole editor crew. Rebuild it from its parts:

```bash
python3 tools/build-bookfactoryagent.py
```

Output: `agents/book_factory_agent.py` — a single file, drop-in loadable into any RAPP brainstem.

---

## Read more

- **[Blog index](./blog/index.md)** — 89 posts, organized by theme
- **[`SPEC.md`](./SPEC.md)** — the frozen v1 contract; the sacred tenet lives in §0
- **[Post 72 — The Twin Stack](./blog/72-the-twin-stack.md)** — how the three tiers fit together
- **[Post 75 — The hero demo](./blog/75-the-hero-demo.md)** — what to show someone in 60 seconds
- **[Post 89 — The double-jump loop](./blog/89-double-jump-loop.md)** — Claude and BookFactory improving each other generation by generation

---

## License

Open bones, closed body, sold soul. The contract, the brainstem reference impl, and the agent base class are open. Specific tuned souls and curated registries are not. The reasoning is in **[post 58 — Open the bones, close the body, sell the soul](./blog/58-open-bones-close-body.md)**.

If you fork: keep the v1 agent contract intact. Everything else is yours.

---

## Contributing

**`agent.py` is the unit of contribution.**

The simplest possible PR is one new file in `agents/` that:

1. Subclasses `BasicAgent` (from `agents/basic_agent.py`)
2. Defines `name`, `metadata`, and `perform(**kwargs)`
3. Adds a docstring at the top — that's your skill markdown

That's it. No registration step. No manifest to edit. The brainstem discovers it on next reload. If your agent needs OS access, set `tether_required = True` and it'll route through `tether/` automatically.

PRs welcome for new agents. PRs that break the v1 contract are not — open an issue first.

---

*Memorialized 2026-04-17. v1 is frozen. The single-file `*_agent.py` is sacred.*
