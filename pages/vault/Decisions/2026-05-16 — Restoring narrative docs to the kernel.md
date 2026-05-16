---
title: 2026-05-16 — Restoring narrative docs to the kernel
status: published
section: Decisions
hook: MASTER_PLAN, ECOSYSTEM, HERO_USECASE, NEIGHBORHOOD_PROTOCOL, OSI, ANTIPATTERNS, ECOSYSTEM_MAP — these are kernel-spec narrative, not distro narrative. They belong with the kernel because they describe the kernel.
---

# 2026-05-16 — Restoring narrative docs to the kernel

> **Hook.** MASTER_PLAN, ECOSYSTEM, HERO_USECASE, NEIGHBORHOOD_PROTOCOL, OSI, ANTIPATTERNS, ECOSYSTEM_MAP — these are kernel-spec narrative, not distro narrative. They belong with the kernel because they describe the kernel.

## The miss

In the first diet pass (commit `b4f3e31`), the root-level narrative docs got migrated to the distro along with the genuine accretion. The reasoning: *"they're not in grail, so they're not kernel."*

That conflated *being-in-grail* with *being-about-the-kernel*. They're not the same thing. Grail is a frozen reference implementation; the narrative docs are how the kernel explains itself to the world. Both serve the kernel; neither needs to live in grail.

Kody's correction was implicit in the broader instruction to restore T2/T3 and the deploy artifacts — once "kernel = full SPEC narrative + reference implementations", the narrative docs obviously belong with the kernel.

Commit `4f6c14b` restored them.

## What was restored

| File | What it is |
|---|---|
| `MASTER_PLAN.md` | First-principles north star. *"Use everyone else's hardware to run the network."* |
| `HERO_USECASE.md` | Canonical scenarios — Charizard-in-the-woods, Dream Catcher, Mom's Mixtape, Pizza Place |
| `ECOSYSTEM.md` | End-to-end layout of a planted organism |
| `ECOSYSTEM_MAP.md` | Single canonical synthesis with authority order + schema registry |
| `NEIGHBORHOOD_PROTOCOL.md` | Wire spec for multi-participant coordination |
| `OSI.md` | RAPP mapped to 7-layer stack |
| `ANTIPATTERNS.md` | Locked rules; append-only |
| `LEXICON.md` | Two vocabularies (human / developer) + the 1:1 mapping |
| `SURVIVAL.md` | What survives if the network breaks / GitHub goes dark / hardware dies |
| `DEFINITION_OF_DONE.md` | Verification checklist |
| `COMMERCIAL.md` | License thresholds |
| `TRADEMARK.md` | Claimed marks |
| `TEMPLATE.md` | Doc template standard |
| `pitch-playbook.html` | Adoption engine (see [[2026-05-16 — Why pitch-playbook stays in the kernel]]) |

## The principle

**The kernel mirror is the god SPEC repo. All documentation about what the kernel is, why it exists, how it should behave, who should adopt it, and what its constitutional constraints are — that's kernel material.**

Distros may have their own narrative (Rappter has its own "why hatch the distro" face paragraph in the rappter-distro README). But the *kernel's own narrative* lives with the kernel.

Practical test for borderline narrative docs:

- *Is this doc explaining a kernel-level concept?* → kernel
- *Is this doc explaining a distro-specific feature?* → that distro

The test failure mode in the first pass was conflating *"this doc is about the larger Rappter platform"* with *"this doc belongs in the Rappter distro."* The larger platform IS the kernel; the Rappter distro is one expression of it.

## See also

- [[2026-05-16 — Kernel-Distro Split]] — the larger context
- [[2026-05-16 — Marie Kondo Audit]] — the policy that drove the first pass
- [[The Kernel-as-God-SPEC]] — the architectural frame that justifies keeping the narrative
- [[2026-05-16 — T2 and T3 belong in the kernel]] — sibling correction
