---
title: KERNEL_TREE as a Map
status: historical
section: Architecture
hook: KERNEL_TREE.md is the file-by-file inventory of what's in this repo; pages/kernel.html is the narrative reading order. Different jobs, different audiences. Keep both up to date when grail changes.
---

# KERNEL_TREE as a Map

> **HISTORICAL VAULT NOTE — superseded current guidance.** The bounded body is
> a dated repository map, not a current authority or navigation source. For
> canonicalization, identity, frames, wire, eggs, registry, trust, and protocol
> evolution, follow RAPP/1 rev-5 through
> [`RAPP1_AUTHORITY.json`](../../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../../RAPP1_STATUS.md).

<!-- RAPP1-HISTORICAL-SECTION-START -->

> **Hook.** `KERNEL_TREE.md` is the file-by-file *inventory* of what's in this repo; `pages/kernel.html` is the narrative *reading order*. Different jobs, different audiences. Keep both up to date when grail changes.

## What each is

| Doc | Audience | Job |
|---|---|---|
| `KERNEL_TREE.md` (repo root) | A reader who wants to know *"what files does grail ship, and where are they in this mirror?"* | Inventory — every file at its grail path with what-it-does annotation, organized by tier / installer / Pages / community / specs / plumbing |
| `pages/kernel.html` (Pages hub) | A first-time visitor who wants to know *"what should I read in what order?"* | Narrative — the trilogy → law → reference → specs → Reading Paths, with cards linking to canonical docs |

They overlap (both list the major kernel surfaces) but serve different needs. A contributor auditing what should-be-where reaches for KERNEL_TREE. A new operator landing on the site reaches for kernel.html. Same canon, two views.

## Why KERNEL_TREE exists

Before 2026-05-16 there was no single document that enumerated grail's full file tree. The reader of the SPEC had to either `git clone kody-w/rapp-installer` and `ls -R` it, or piece the tree together from Constitution articles. KERNEL_TREE.md is the single canonical inventory, rebuilt explicitly so that:

1. The kernel mirror declares its scope by what it lists (everything in this map exists in the repo; nothing else does)
2. Anyone planning a move (kernel ↔ distro) has a baseline to argue against ("this file isn't in KERNEL_TREE because it's distro-only")
3. The Mirror Spec's drift-check is auditable file-by-file, not just for the three sacred files

## Why pages/kernel.html exists separately

KERNEL_TREE is dense reference. A new visitor doesn't want to read a table of 48 files; they want to know *where to start*. The hub presents the same canon in a guided way:

- **The trilogy** answers *"why does this exist?"* (MASTER_PLAN, HERO_USECASE, ECOSYSTEM)
- **The law** answers *"what are the rules?"* (CONSTITUTION, ANTIPATTERNS, DEFINITION_OF_DONE, ECOSYSTEM_MAP)
- **Reference** answers *"what do I look up?"* (SURVIVAL, LEXICON, KERNEL_TREE itself, OSI, NEIGHBORHOOD_PROTOCOL, COMMERCIAL)
- **The specs** answers *"what's the contract?"* (SPEC, ROADMAP, ESTATE_SPEC, rapplication-sdk, the network specs)
- **Reading Paths** answers *"how do I read for my role?"*
- **The vault** answers *"why was this decided?"*
- **The kernel tree** answers *"what's in here, exactly?"* (links to KERNEL_TREE.md)
- **Related repos** answers *"what else do I need?"*

## Keeping both up to date

When grail itself ships a new file (kernel evolution, which is rare), both docs need updating:

1. Update `KERNEL_TREE.md` to add the file with its annotation
2. Update `pages/kernel.html` if the new file affects the canonical reading order (most kernel-level additions don't; they're tracked in KERNEL_TREE only)
3. Update `tests/mirror-drift.sh` if the new file is one of the three sacred files (unlikely; today only 3 files are sacred)
4. Add a dated note to the Mirror Spec vault note if the structural pattern changes

When a file moves between kernel and distro (more common):

1. Move the file (cp to destination, rm from source)
2. Update KERNEL_TREE to reflect the new state
3. Add the move to the relevant kernel.html section if the file was surfaced as a card
4. Write a dated Decisions/ vault note explaining the why
5. Repoint inbound references in canon docs

## A note on duplication-by-design

KERNEL_TREE and kernel.html share most of their material. That's deliberate. A reader landing on either should be able to understand the platform's scope without needing the other. The cost is keeping two docs in sync; the benefit is that neither audience has to context-switch to the other doc.

If they ever drift, kernel.html (the narrative) wins for first-time readers; KERNEL_TREE (the inventory) wins for auditors and contributors. When in doubt, fix KERNEL_TREE first (it's the canonical inventory) and update kernel.html cards to match.

## See also

- [[Mirror Spec]] — the discipline KERNEL_TREE serves
- [[The Kernel-as-God-SPEC]] — the framing that justifies both docs
- [[2026-05-16 — pages-kernel-html as the canonical hub]] — the decision behind the hub
- [`KERNEL_TREE.md`](../../../KERNEL_TREE.md)
- [`pages/kernel.html`](../../kernel.html)

<!-- RAPP1-HISTORICAL-SECTION-END -->
