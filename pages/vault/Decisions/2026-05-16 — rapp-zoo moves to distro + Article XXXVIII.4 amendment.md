---
title: 2026-05-16 — rapp-zoo moves to distro + Article XXXVIII.4 amendment
status: published
section: Decisions
hook: The Pokédex moves from the kernel mirror to the Rappter distro. Constitution Article XXXVIII.4 amended with a dated note. The principle: the SPEC defines the control-plane interface; distros provide implementations.
---

# 2026-05-16 — rapp-zoo moves to distro + Article XXXVIII.4 amendment

> **Hook.** The Pokédex moves from the kernel mirror to the Rappter distro. Constitution Article XXXVIII.4 amended with a dated note. The principle: the SPEC defines the control-plane interface; distros provide implementations.

## What moved and why

`rapp-zoo/` is the local-first Pokédex UI — drag-drop egg import, deterministic SVG sprites per organism, three bundled starters (workday / playtime / journal), localStorage for metadata, IndexedDB for blobs. Single-file static page hosted via GitHub Pages.

It had been moved into the kernel repo on 2026-05-02 "to keep the federation simpler" (per the old Article XXXVIII.6). On 2026-05-16, during the Marie Kondo audit, the question came up: *"why is rapp-zoo a part of the kernel and not the distro?"*

The right answer was: it shouldn't be. The Pokédex consumes `.egg` cartridges; eggs are organism-layer (`bond.py`, `egg.py`, `lineage.py` all live in the distro's `lib/`). A UI for managing organism collections is organism-layer UX, not kernel SPEC. Marie Kondo: distro.

Commit `0c981c9` removed `rapp-zoo/` from the kernel mirror. Commit `eb0e220` in the distro added it.

## The constitutional conflict

Article XXXVIII.4 was titled *"The user's universal control plane: rapp-zoo"* and explicitly named rapp-zoo as the canonical UI living in the kernel repo. Moving it violated the article as written.

The amendment, added in commit `32b2497`:

> *"Amended 2026-05-16: rapp-zoo now lives in [`kody-w/rappter-distro/rapp-zoo/`](https://github.com/kody-w/rappter-distro/tree/main/rapp-zoo), not in this kernel-mirror repo. The Pokédex UI is organism-layer UX (it composes onto a brainstem; the brainstem doesn't need it to function) and per the kernel/distro split adopted on 2026-05-16, organism-layer features live in the Rappter distro. The kernel SPEC (this article) is unchanged; only the canonical location of the implementation moved. Any distro can ship its own zoo-like control plane; Rappter's is the reference implementation."*

The article body — the conceptual model of the zoo as "the Game Boy", the table mapping Pokémon analogs to RAPP analogs, the rules that the zoo MUST follow the canonical shape (agent + organ + UI bundle) and MUST render holocards through the same card model — all of that stayed. It's the SPEC. What changed is the *location of the reference implementation*, not the contract.

## The general principle (now codified)

**The kernel SPEC defines control-plane interfaces. Distros provide implementations.**

A SPEC that says "*the user needs a universal control plane that does X, Y, Z and looks like the Game Boy*" can name a reference implementation without requiring that implementation to live in the kernel repo. Other distros are free to ship their own control plane satisfying the same SPEC — a minimal terminal-only variant, an enterprise admin console, a museum-style installation. The kernel doesn't care which one is hatched on top.

The Rappter distro happens to be the reference implementation for now. If a community-built distro ships a competing zoo with different ergonomics, both honor the SPEC.

## Constitutional amendment process

This sets a precedent for how SPEC articles get amended when the kernel-distro split forces a move:

1. **Move the implementation** (cp from kernel to distro, delete from kernel)
2. **Amend the article in-place** with a dated blockquote at the top — explaining what moved, when, and why
3. **Leave the body of the article unchanged** — the SPEC text is still authoritative for what the implementation must do
4. **Update outbound references** (in this case: README, CLAUDE, ECOSYSTEM_MAP, kernel.html, ~21 files of broken links)

The Constitution is sacred per its own rules, but "sacred" means *amended via deliberate dated notes that preserve history*, not *never edited*.

## See also

- [[2026-05-16 — Kernel-Distro Split]] — the split that drove the move
- [[2026-05-16 — Marie Kondo Audit]] — the policy that surfaced the question
- [[The Kernel-as-God-SPEC]] — the principle that the kernel defines, distros implement
- [`CONSTITUTION.md` Article XXXVIII.4](../../CONSTITUTION.md) — the amended article
