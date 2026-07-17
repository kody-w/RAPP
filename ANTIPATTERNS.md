# Antipatterns — Things This Repo Will Never Do

> **Current RAPP/1 authority (rev-5).** For canonicalization, identity, frames,
> wire, eggs, registry, trust, and protocol evolution, follow
> [`RAPP1_AUTHORITY.json`](./RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](./RAPP1_STATUS.md). This document governs product and
> repository practice only; it cannot redefine the pinned protocol.

> Rules locked in because they were almost done wrong, or because the rest of the industry is doing them wrong and we'd be following them off the cliff. Each entry is *load-bearing* — breaking it is a regression.

---

## 1. ONE TERM FOR THE PLUGIN UNIT — `agent`

**The rule.** A single `*_agent.py` file is called an **agent**. Never a *skill*, *routine*, *loop*, *plugin*, *tool*, *function*, *capability*, *cassette*, or any other synonym in user-facing copy, code, or documentation.

**Why.** Anthropic's product surface introduced overlapping taxonomies — agents, skills, MCP, plugins, routines — that all describe roughly the same thing in slightly different framings. The operator captured the cost in a private design conversation (May 2026):

> *"Anthropic… they really screwed up by introducing all of the different taxonomy that basically does the same thing. I mean, think about it, right? So agents, skills, routines, loops, plugins. I, like, who knows MCP, like whatever else they'll come up with. That basically poisoned the industry for onboarding."*

A new visitor cannot tell what's what. The complexity becomes the gatekeeper. People who already know the system stay productive; everyone else can't get started. That's the **AI winter precondition** — capability concentrates in a few hands and no one else trusts what they can't understand.

**The mom test.** If we can't explain it to a non-technical person in one sentence, we have one too many concepts. *"It's an agent. A small Python file that gives the AI a new ability."* — that's the whole vocabulary.

**How to apply.**

- **In code:** identifiers use `agent` only. `customAgents`, `_customAgentCount`, `fillAgents`, `AGENT_FRIENDLY`, `tr-agents`, `agent-chip`. Never `skill`, `plugin`, `routine`, `loop` in identifiers, CSS classes, or DOM ids. Historical files and explicit antipattern guards are exceptions.
- **In user-facing copy:** every label, button, error message, and status line says "agent" if it's referring to an `*_agent.py` file. The Track Record section is **Agents**, not Skills. The proposal flow is **Propose an agent**, not Propose a skill.
- **In documentation:** when explaining how the platform grows, say "agents" — `HERO_USECASE.md`, `ECOSYSTEM.md`, `README.md`, `CLAUDE.md`. Cross-reference the Constitution: *"Single-file agents are the plugin system. One file = one class = one `perform()` = one metadata dict."*
- **In commit messages and PR titles:** same.

**What to do when you see a synonym creeping in.** Treat it like dead code — delete and replace with `agent`. Don't introduce a new concept just because a UI surface "needs" different language. If it's a different concept, it deserves a different name AND a clear explanation of how it's not just an agent. Default rule: it's just an agent.

**Pre-commit checklist for this rule.** Before every commit that touches user-facing copy or `*_agent.py` references:

```
grep -niE '\bskill|\bplugin|\broutine|\bloop|\bcassette' <changed-files>
```

Hits from this grep that aren't inside an antipattern-guard comment block (commented `Never "skill"…` warnings) need to be renamed before the commit lands.

---

## 2. THE FROZEN KERNEL NEVER MOVES

**The rule.** `rapp_brainstem/brainstem.py`, `rapp_brainstem/VERSION`, and
`rapp_brainstem/agents/basic_agent.py` are frozen at the exact immutable grail
pin
[`kody-w/rapp-installer@brainstem-v0.6.9`](https://github.com/kody-w/rapp-installer/tree/brainstem-v0.6.9).
They never follow a moving latest branch and are never edited locally.
Capabilities grow through new agents outside those pinned bytes.

**Why.** The three bytes are an immutable compatibility baseline. This pin
does not by itself prove portability, installation, or RAPP/1 conformance.

**How to apply.** Keep target-owned work outside the pinned bytes. If the host
contract cannot express a change, record the incompatibility rather than
editing the grail or claiming a deployed migration.

---

## 3. NO BACKWARDS-COMPAT SHIMS FOR HALF-RELEASED FEATURES

**The rule.** Protocol change follows Constitution Articles II–IV and RAPP/1
§12 total migration. Do not invent a version string locally. Freeze old
producers, migrate once, publish signed registry/re-genesis state, switch
atomically, and remove legacy readers.

**Why.** The codebase is small enough that we can rip the band-aid off. Shims accumulate forever and the next reader has to figure out which branch is real.

**How to apply.** For application-local metadata, update all producers and
consumers together. For RAPP protocol structure, use the constitutional
process and §12 sequence. A one-time migrator may ingest recognized legacy
data; normal readers do not retain the branch.

---

## 4. HISTORICAL PRODUCT-IDENTITY RULE

The former `rapp-twin-spec/1.0` soul block was application guidance, not
RAPP/1 identity or a current planting requirement.

**Why.** Without this block, LLMs default to brand chrome. The visitor lands at heimdall.github.io expecting Heimdall and gets greeted by "RAPP". The identity collapses into the substrate.

**Current rule.** The former `installer/plant.sh::write_soul_md` producer is
retired and must not be invoked. Any future producer must use RAPP/1 identity
and authenticated registry state rather than relying on a prompt block.

---

## 5. HISTORICAL BROWSER NETWORK RULE

The browser front door is retired. The rule below preserves why its former
implementation cached network responses; it is not a claim that a browser
product or fallback is currently shipped.

**The rule.** Any GitHub fetch the front door makes goes through `cachedGhJson` / `cachedGhText`. Direct `fetch(github.com/...)` is forbidden in resume-rendering paths.

**Why.** The hero use case is offline-first. An organism in airplane mode must keep rendering its own resume from cached state. Bare fetches go blank when the network drops; that's a regression against `HERO_USECASE.md` §1.

**How to apply.** Do not add calls to the retired surface. A future accepted
application would need explicit offline behavior and normal RAPP/1
verification; cache presence alone never establishes trust.

---

*This file is append-only. Antipatterns get added when we almost did them wrong; nothing here ever gets quietly removed.*
