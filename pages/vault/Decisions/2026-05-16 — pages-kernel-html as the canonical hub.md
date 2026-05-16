---
title: 2026-05-16 — pages/kernel.html as the canonical hub
status: published
section: Decisions
hook: One unified entry point at kody-w.github.io/RAPP/pages/kernel.html that surfaces the canon in canonical reading order. Doesn't duplicate content — just navigates. Cascaded into every front-door doc via the shared header partial + per-page explicit links.
---

# 2026-05-16 — pages/kernel.html as the canonical hub

> **Hook.** One unified entry point at `kody-w.github.io/RAPP/pages/kernel.html` that surfaces the canon in canonical reading order. Doesn't duplicate content — just navigates. Cascaded into every front-door doc via the shared header partial + per-page explicit links.

## The problem this solves

Before 2026-05-16, a first-time visitor landed on `kody-w.github.io/RAPP/`, got an install one-liner, and then had to figure out where to go from there. Some docs lived at repo root (MASTER_PLAN, CONSTITUTION), some under `pages/docs/`, some in the Obsidian vault, some on per-component READMEs. A new contributor wanting *"the canonical reading order"* had to assemble it from grep results.

The vault's existing `Reading Paths/` directory had the right idea but was three clicks deep from the landing page. The kernel-as-Linux-kernel framing (clarified in [[2026-05-16 — Kernel-Distro Split]]) made it obvious that the kernel deserved a single canonical "face" page distinct from the install pitch.

## What the hub contains

`pages/kernel.html` is a static HTML page using the existing `pages/_site/` chrome. Organized into seven sections:

1. **The trilogy** — MASTER_PLAN → HERO_USECASE → ECOSYSTEM (read in order)
2. **The law** — CONSTITUTION, ANTIPATTERNS, DEFINITION_OF_DONE, ECOSYSTEM_MAP
3. **Reference** — SURVIVAL, LEXICON, KERNEL_TREE, NEIGHBORHOOD_PROTOCOL, OSI, COMMERCIAL
4. **The specs** — pages/docs/SPEC.md, ROADMAP, ESTATE_SPEC, rapplication-sdk, skill.md, **plus Network Protocol Spec + Network-citizen skill** (added during the SPEC disambiguation)
5. **Reading Paths** — the vault's 5 existing curated sequences surfaced as cards (Exec / Engineer / Architect / Partner / New Contributor)
6. **The vault** — index + Architecture + Decisions entry points
7. **The kernel tree** — KERNEL_TREE.md + rappid.json + Mirror Spec
8. **Related repos** — grail, rappter-distro, RAR, rapp_store

Every card links to the authoritative doc. Nothing is duplicated; the hub is pure navigation.

## How it cascades

Adoption surface is in two layers:

**Shared header partial** (`pages/_site/partials/header.html`): added "Kernel" as the first nav item. Cascades to every page that loads the partial via `site.js` (`#site-header` div) — about 14 pages auto-get the link without per-page editing.

**Inline-nav pages** (12 pages with hand-written navs that don't load the partial): explicit per-page edit. Each got a Kernel link in its nav, cta-row, breadcrumb, or pill row depending on the page's existing layout. List of touched pages: `index.html` (root), `blog.html`, `release-notes.html`, `docs/index.html`, `docs/tutorial.html`, `pages/about/{ecosystem, prompts}.html`, `pages/tutorials/hatch-egg.html`, `pages/metropolis/{index, plant-from-discord}.html`, `pages/product/vs.html`, `pages/share/invention-backlog/index.html`.

**404.html**: Kernel is now the primary CTA. A wrong URL still lands on the canonical entry.

**Forward-link from canon docs**: README.md, CLAUDE.md, KERNEL_TREE.md, ECOSYSTEM_MAP.md, pages/vault/README.md, pages/docs/README.md, rapp_brainstem/README.md, rapp_brainstem/CLAUDE.md — all point at the hub from their tops.

**Distro repo**: rappter-distro README has a backlink to the hub for the canonical reading order.

## Slide decks and specialty surfaces — explicitly NOT touched

Per Kody's instruction: *"DON'T CHANGE ANY OF THE SLIDES for their original links."*

Left alone: `pitch-playbook.html`, `pages/rappid-deck.html`, `pages/rappid-onepager.html`, `pages/sphere.html`, `pages/vbrainstem.html`, `pages/tether.html`, `pages/summon.html`, `pages/lobby.html`, `pages/chat.html`, `pages/grail-brainstem/index.html`, `pages/vbrainstem/index.html`, `pages/product/unsolved.html`.

These either are slide presentations with carefully-curated original links or are interactive specialty surfaces whose nav is part of their UX. The hub is reachable from anywhere else; specialty surfaces stay specialty.

## See also

- [[2026-05-16 — Kernel-Distro Split]] — the framing that made the hub obviously necessary
- [[Reading Path — AI Loading the Vault]] — the audience that benefits most from a single canonical entry
- [`pages/kernel.html`](../../kernel.html) — the page itself
