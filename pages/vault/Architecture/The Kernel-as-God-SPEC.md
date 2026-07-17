---
title: The Kernel-as-God-SPEC
status: historical
section: Architecture
hook: Historical kernel-as-spec framing, superseded by the external immutable RAPP/1 rev-5 authority pin.
---

# The Kernel-as-God-SPEC

> **SUPERSEDED authority framing — historical record only.** This repository is
> not the “god SPEC” and `rapp-god` is non-authoritative. For canonicalization,
> identity, frames, wire, eggs, registry, trust, and protocol evolution, follow
> RAPP/1 rev-5 through
> [`RAPP1_AUTHORITY.json`](../../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../../RAPP1_STATUS.md). The standard is pinned to
> commit `6723c7add2aed36bb68992fc71a56b0a4bd5ad81`; the grail is pinned by
> [`KERNEL_PIN.json`](../../../KERNEL_PIN.json), never a moving branch.

<!-- RAPP1-HISTORICAL-SECTION-START -->

> **Hook.** The kernel repo's purpose isn't to be a runtime; it's to be the canonical SPEC repo every distro reads from. Implementations can live anywhere; the kernel's job is unification.

## The framing

After the [[2026-05-16 — Kernel-Distro Split]], `kody-w/RAPP` is no longer trying to be "the place where everything lives." Its job is now narrower and more durable:

> **Historical claim (retired):** RAPP was described as the god SPEC repo.
> Current protocol authority is the immutable external RAPP/1 pin above.

Practically: every distro — Rappter, future-minimal, future-research, future-enterprise — reads its kernel-level reference material from this one repo. The Constitution, the trilogy (MASTER_PLAN / HERO_USECASE / ECOSYSTEM), the law (ANTIPATTERNS / DEFINITION_OF_DONE), the spec (`pages/docs/SPEC.md`), the network protocol spec (`specs/SPEC.md`), the lexicon, the survival matrix, the kernel tree map, the vault.

When two distros disagree about behavior, they don't argue with each other. They read this repo.

## Why this matters

A platform that has multiple distros also has multiple opinions about what's "the right way" to compose features on top of the kernel. Without a shared SPEC, those opinions diverge — one distro thinks twins live in `lib/twin.py`, another puts them in `cells/twin/`, a third has no twins at all. The kernel SPEC is the answer to *"how does an organism find itself across distros?"* — by reading the same SPEC text everywhere.

This is also why the Constitution can be amended in place (with dated notes) rather than forked. Article XXXVIII.4 was amended to reflect rapp-zoo's new home in the Rappter distro; the article body — the interface contract for "the universal control plane" — stayed unchanged. Distros that ship their own zoo-like UI honor the same article.

## What this implies for what stays in RAPP

If a doc is *about the kernel*, it stays in RAPP, regardless of whether grail ships it. If a tool is *referenced by the kernel SPEC as load-bearing*, it stays. If a file is *grail-canonical*, it stays. If a page is *kernel adoption surface* (pitch, onboarding, anatomy diagram), it stays.

If a doc is *about one particular distro's implementation choices*, it belongs in that distro. The kernel SPEC names the interface; the distro implements it.

## What this implies for the SPEC itself

The SPEC must be:

- **Implementation-agnostic where possible.** Article XXXVIII.4 describes what the control plane must do, not what library it's built with.
- **Versioned + dated when amended.** The Constitution's article-numbered structure is intentional. New behavior gets a new article or a dated amendment note.
- **Historical federability idea.** Moving raw URLs were once proposed for
  reading local docs. They are not authority or verification paths.
- **Adoption-engine-friendly.** The pitch (`pitch-playbook.html`), onboarding, and audience-facing pages stay with the SPEC because they recruit the people who'll build against the SPEC.

## Anti-patterns this prevents

- **Kernel-as-Rappter-bloat.** Before the split, the kernel mirror was accumulating Rappter-specific narrative, Rappter-specific tools, the Rappter Pokédex. Distros could read it, but they were reading Rappter opinions disguised as SPEC.
- **Distro-as-SPEC.** A distro README that tries to be the canonical "what is RAPP" page competes with the actual SPEC. Distros should have a 1-paragraph "why hatch this distro" face and then defer to the kernel hub for the rest.
- **SPEC-via-grail.** Treating `kody-w/rapp-installer` as if it were the SPEC repo. Grail is the *frozen reference implementation*; the SPEC is everything around it that explains what the implementation must satisfy.

## See also

- [[2026-05-16 — Kernel-Distro Split]] — the split that produced this framing
- [[Distros as a Pattern]] — what a valid distro looks like
- [[Mirror Spec]] — the byte-identical-to-grail discipline that anchors the SPEC
- [[Engine, Not Experience]] — the founding stance compatible with this frame
- [`pages/kernel.html`](../../kernel.html) — the unified entry into the SPEC

<!-- RAPP1-HISTORICAL-SECTION-END -->
