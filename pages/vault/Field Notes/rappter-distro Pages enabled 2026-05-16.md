---
title: rappter-distro Pages enabled 2026-05-16
status: published
section: Field Notes
hook: The distro repo now has its own live Pages site at kody-w.github.io/rappter-distro/. Cross-repo linking pattern: source-tree links by default; upgradable to live URLs as the distro's Pages content stabilizes.
---

# rappter-distro Pages enabled 2026-05-16

> **Hook.** The distro repo now has its own live Pages site at `kody-w.github.io/rappter-distro/`. Cross-repo linking pattern: source-tree links by default; upgradable to live URLs as the distro's Pages content stabilizes.

## What happened

On 2026-05-16, GitHub Pages was enabled on the `kody-w/rappter-distro` repo via:

```bash
gh api -X POST /repos/kody-w/rappter-distro/pages \
    -F 'source[branch]=main' \
    -F 'source[path]=/'
```

The site started building immediately, served from `main` branch root. Live at:

- **https://kody-w.github.io/rappter-distro/**

## Why it matters

Before this, references in the kernel mirror to content in the distro (like the rapp-zoo Pokédex UI) had to use the github.com source tree URL — e.g., `https://github.com/kody-w/rappter-distro/tree/main/rapp-zoo`. Source-tree links work but don't render the actual page; visitors get GitHub's directory view instead of the live UI.

With Pages enabled, the rapp-zoo Pokédex (and any future distro pages) can be linked as live URLs:

- `https://kody-w.github.io/rappter-distro/rapp-zoo/` — the Pokédex itself
- `https://kody-w.github.io/rappter-distro/examples/rapp-commons/` — the reference neighborhood
- etc.

The distro's UI surfaces are now first-class web destinations, not just files in a repo.

## What stays as source-tree links

Not everything in the distro should be linked as a live page:

- **Python files** (`lib/bond.py`, `tools/holo_card_generator.py`) — source-tree links are the right form; Pages would render them as text but they're not meant to be browsed
- **Markdown docs** without HTML viewers (`MIGRATION_NOTES.md`) — source-tree links render the markdown view, which is what readers want
- **Internal infrastructure** (`distro.json`, `binders/*.json`) — source-tree is the right place; not consumer pages

For *interactive UIs* and *static HTML pages*, prefer live Pages URLs. For everything else, source-tree URLs.

## The cross-repo linking pattern

When the kernel mirror references content in the distro:

1. **Default to source-tree URLs** (`https://github.com/kody-w/rappter-distro/tree/main/<path>` for directories, `/blob/main/<path>` for files). They always work; they don't depend on Pages being enabled or built.
2. **Upgrade to live URLs case-by-case** for HTML pages that should render as interactive content. Maintain a mental list of which URLs are "page-style" vs "source-style."
3. **Never assume both forms work.** Source-tree URLs always work; Pages URLs only work if Pages is enabled, built, and the file is an HTML viewer.

## Implication for distros generally

When a new distro is built (the second one, the third one), enabling Pages on its repo should be part of its setup checklist:

```
- [ ] gh repo create kody-w/<distro-name> --public
- [ ] git push initial scaffold
- [ ] gh api -X POST /repos/kody-w/<distro-name>/pages -F 'source[branch]=main' -F 'source[path]=/'
- [ ] verify https://kody-w.github.io/<distro-name>/ renders
- [ ] update kernel hub (pages/kernel.html) to link to the new distro
```

The kernel mirror's `pages/kernel.html` "Related repos" section can then link to the distro's live face page, not just the source tree.

## See also

- [[2026-05-16 — Kernel-Distro Split]] — the larger context
- [[Distros as a Pattern]] — what makes a distro
- [[2026-05-16 — pages-kernel-html as the canonical hub]] — the kernel hub that links to distros
