# Historical RAPP Master Plan

> **Current RAPP/1 authority (rev-5).** This plan governs strategy, but
> canonicalization, identity, frames, wire, eggs, registry, trust, and protocol
> evolution are governed by [`RAPP1_AUTHORITY.json`](./RAPP1_AUTHORITY.json)
> and the claim limits in [`RAPP1_STATUS.md`](./RAPP1_STATUS.md). Strategic
> intent never overrides the pinned byte-level standard.

> **Whole-document disposition:** this 2026-05-08 strategy is retained as
> history. Its planting, browser, Pages, offline sharing, hatching, network,
> and end-to-end proof statements are ambitions or retired product claims, not
> current operator instructions or shipped capabilities.

<!-- RAPP1-HISTORICAL-SECTION-START -->

> *"The world hasn't been ready so I've just been waiting and planning."*
> — the operator, 2026-05-08

This is the first-principles document. The Constitution governs the repo. The Hero Use Case proves the platform works. The Antipatterns lock what we will never do. **This file says what we are doing and why.** When the road forks and we don't know which way, we come back here.

It is published openly so future-us, future contributors, and anyone joining the network are reading the same north star. It is shipped under the same license as the rest of the project; per Constitution Article XXXV (License Stability), this can only be relaxed, never tightened.

---

## Master Plan, Part 1 — what we built

So, in short, the plan to date is:

1. **Build a kernel and freeze it.** The immutable grail is exactly
   `kody-w/rapp-installer@brainstem-v0.6.9`; its `brainstem.py`,
   `agents/basic_agent.py`, and `VERSION` bytes never follow moving latest and
   are never edited locally.

2. **Make agents the only unit of extension.** One file, one class, one `perform()`. Never plugins, skills, routines, loops, cassettes, capabilities, or any synonym. If you want to teach the AI something new, you write an `agent.py`. That is the entire vocabulary.

3. **Plant the AI as a public GitHub repo.** The repo IS the organism — its identity (`rappid`), its voice (`soul.md`), its body (`agents/`), its memory (`.brainstem_data/`), its skin (`index.html` + `doorman/`). All committed files. No server runs anywhere. GitHub Pages serves the surface; the visitor's browser runs the surface; the visitor's own GitHub Copilot subscription pays for the inference.

4. **Use eggs to share organisms device-to-device, even offline.** A current
   `.egg` follows RAPP/1 §9: `schema:"rapp/1-egg"`, a registered variant,
   domain-separated hashes, deterministic storage, and required signature
   verification. Two phones in the woods must still be able to trade one.
   **Historical context:** the 2026-05-10 five-kind family and the 2026-05-18
   `rapp-egg/2.0` scale design record earlier shipped approaches. Those schema
   strings are retired migration inputs, not current emission instructions.

5. **Use everyone else's hardware to run the network.** GitHub has already paid for the global CDN (`raw.githubusercontent.com`), the auth system (`gh auth`), the durable async mailbox (Issues), the consent gate (Pull Requests), and the edge endpoints (`<owner>.github.io/<repo>/`). We do not build a network. We use the one already running. Operators run brainstems on their own machines. The network is the union of those machines plus the public substrate they all share.

That is the platform.

## Master Plan, Part Deux — where this is going

So, in short, where this is going:

1. **Operators subscribe to many neighborhoods. The union is their estate.** A neighborhood is a community with a purpose — an SE Team, a knowledge guild, a family photo group, a local pizza place, a science working group. A user belongs to many. Their brainstem holds N subscriptions, and their personal `rappid` is the spine that runs through every one.

2. **Estates mesh through shared neighborhoods. The mesh is the metropolis.** Just like physical urban zoning is not declared top-down — it emerges from which communities which people join for which purposes — the AI metropolis emerges from which neighborhoods which operators subscribe to for which outcomes. We do not plan the city. We give it the substrate and the shape so it can build itself.

3. **Workflows that need privacy use the public gate / private companion
   split.** GitHub collaborator status may gate application content, but it is
   not the RAPP trust anchor. Authenticated protocol acceptance requires the
   signed, monotonic RAPP/1 §13 registry rooted in an out-of-band estate-owner
   rappid.

4. **AIs travel along the network in four modes.** *Cold* (the full organism
   cartridge moves), *Warm* (agents move while state stays home), *Soul*
   (parallel offline dimensions reconcile later), and *Message* (only a
   thought travels). Identity persists because RAPP/1 §6 mints its tail once
   and §13 records lawful trust and succession—not because a name or repo
   location derives identity.

5. **The user is in the loop async, not synchronous.** Agents do work in zones across the metropolis on behalf of their operator. Work products attribute back to the operator's `rappid`. Results land in the operator's estate inbox. The user checks back when they want to — the network does not stop because they went to bed. **The network is the engine. Once it has enough nodes, it builds itself out.**

## The single-sentence version

> **Use everyone else's hardware to run the network.**

Every other line of this document is a corollary.

## How to use this document

When the road forks and we don't know which way to go, **come back here**. Ask: which option preserves the master plan? Which option breaks it?

| If a proposal asks for… | And it would… | Then |
|---|---|---|
| A kernel change | …add or modify lines in `brainstem.py` / `basic_agent.py` / `VERSION` | **Breaks Part 1 §1.** Reject. Write an agent or an organ instead. |
| A new abstraction between agents and the LLM | …introduce a "skill", "plugin", "routine", "loop" terminology | **Breaks Part 1 §2.** Reject. It is just an agent. |
| A central application server, marketplace, or signaling broker | …add infra beyond GitHub + PeerJS-handshake + the existing Cloudflare auth-proxy | **Breaks Part 1 §5.** Reject. This does not prohibit the required signed RAPP/1 §13 registry. |
| A trust shortcut | …treat `gh auth`, collaborator status, or an unsigned file as protocol authentication | **Breaks RAPP/1 §§10/13.** Reject. Verify the signed registry and anchored key succession. |
| A workflow that doesn't survive offline | …require live network for the user-visible operation | **Breaks Part Deux §4.** Reject. Soul travel + cached fallback is mandatory. |
| A design that requires every member online | …block the network when a peer is offline | **Breaks Part Deux §5.** Reject. Async loop-back is the user contract. |
| A feature flag, perpetual legacy shim, or "temporary" toggle | …leave dead code paths behind for half-released features | **Breaks RAPP/1 §12 and ANTIPATTERNS §3.** Reject. Migrate totally and retire the old form. |

Things this plan deliberately does **NOT** decide. They are intentionally left to operators:
- Which model runs in any given brainstem (BYO).
- Which domain or industry an organism specializes in (BYO).
- Which communities anyone joins (BYO).
- How anyone makes money on top of this (the commercial license is the boundary; everything above the boundary is yours).

## Why this plan, in this style

A roadmap goes stale in three months. A master plan compounds for decades. This is a plan for **the decisions we don't yet know we'll need to make** — written so future-us, future-Bill, future-rappter1, and the operator who shows up in 2034 are all reading the same north star.

It mirrors Tesla's "Master Plan, Part 1" (2006) and "Master Plan, Part Deux" (2016) on purpose: same shape, same brevity, same first-principles substrate. The reason that template works is that it forces clarity on the **mechanism** at every step. Each line is a verb. Each verb is the smallest move that unlocks the next. The plan is recoverable in a single sitting.

If we ever feel the need to write a Master Plan, Part Trois, that is a sign Parts 1 and Deux have either been completed or breached. Either is fine. Both deserve a public moment.

## Working examples to keep us honest

| Scenario | What it tests |
|---|---|
| Two phones in the woods trade an `.egg` and run agents offline | Part 1 §3, §4. Soul travel + offline mode. |
| Bill plants `kody-w/microsoft-se-team-neighborhood` (public gate) + private companion | Part Deux §3. Public/private split. |
| `rappter1` joins kody-w's neighborhood as an external collaborator | Part Deux §1, §3. Cross-org membership without a separate auth layer. |
| A query in zone A federates across online members; offline members reply via Issue when back | Part Deux §4, §5. Self-healing federation; async loop-back. |
| The metropolis topology view renders bridges between zones | Part Deux §2. The city builds itself; we just see it. |
| The AIBAST four-twin federation (Heimdall :7081, @kody-w :7082, Bots in Blazers :7083, AIBAST :7084) runs simultaneously on one machine — all four hatched from the same generic `twin_egg_hatcher_agent.py`, federated through one global brainstem's `Twin` agent | Part 1 §1, §4 + Part Deux §2. Multi-scale eggs + one hatcher + zero kernel patches — proof that the pattern works end-to-end. See [[The Federated Twin Egg Hatcher Pattern]]. |

These are the load-bearing scenarios. If any one of them stops working, the master plan has been breached and the breach must be repaired before merging.

## The first principles, at a glance

1. The kernel is sacred.
2. Agents are the only extension.
3. The repo is the organism.
4. Eggs are how AIs travel.
5. The substrate is GitHub.
6. Estates compose from neighborhoods.
7. Metropolises emerge from estates.
8. The user is in the loop async.
9. Local-first survives every degradation.
10. **Use everyone else's hardware to run the network.**

## What this plan inherits from elsewhere in this repo

This is the *why-axis*. The *how-axis* is documented in:

- [`CONSTITUTION.md`](./CONSTITUTION.md) — repo governance + sacred constraints
- [`HERO_USECASE.md`](./HERO_USECASE.md) — the canonical scenarios that prove the plan works
- [`ECOSYSTEM.md`](./ECOSYSTEM.md) — how the pieces fit together (file layout, schemas, surfaces, network modes)
- [`NEIGHBORHOOD_PROTOCOL.md`](./NEIGHBORHOOD_PROTOCOL.md) — historical and
  application federation adapters; RAPP/1 §8 is the current wire
- [`ANTIPATTERNS.md`](./ANTIPATTERNS.md) — what we will never do
- [`COMMERCIAL.md`](./COMMERCIAL.md) — the commercial layer on top of the free protocol
- [`TRADEMARK.md`](./TRADEMARK.md) — the wordmark + how it's used
- [`pages/vault/`](./pages/vault/) — long-form essays explaining the *why* behind major decisions

Within product strategy, this plan explains the why-axis. It never wins a
conflict with `RAPP1_AUTHORITY.json`, `RAPP1_STATUS.md`, or Constitution
Article LV.

---

*Master Plan published 2026-05-08 by Kody Wildfeuer.*
*Append-only — extensions are added; existing items are never repurposed. Breaking changes ship as Part Trois.*

<!-- RAPP1-HISTORICAL-SECTION-END -->
