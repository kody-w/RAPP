---
title: 2026-05-16 — Why pitch-playbook stays in the kernel
status: published
section: Decisions
hook: The adoption-engine exception to Marie Kondo. Sales material that drives adoption of the kernel itself is load-bearing for the kernel's mission, even though it doesn't look like "kernel SPEC."
---

# 2026-05-16 — Why pitch-playbook stays in the kernel

> **Hook.** The adoption-engine exception to Marie Kondo. Sales material that drives adoption of the kernel itself is load-bearing for the kernel's mission, even though it doesn't look like "kernel SPEC."

## The almost-mistake

During the Marie Kondo audit, `pitch-playbook.html` looked like an obvious candidate to move to the Rappter distro. It's a sales pitch — 6 slides framing RAPP as an *adoption layer* on top of whatever AI tools your team already pays for. Not a SPEC. Not a tier-implementation file. Not grail-canonical.

By the Marie Kondo policy, it should go.

It was moved to the distro in commit `b4f3e31`. Then this came back:

> *"yeah but without the pitch playbook the kernel never gets adopted..."*

It got restored in the same conversation. Worth writing down why so the next audit doesn't make the same call.

## Why the pitch is kernel-load-bearing

A kernel without adoption is academically interesting and operationally dead. Every kernel decision — sacred file count, version freeze cadence, three-tier Stack design, mirror spec — is in service of a thesis: *if this kernel exists and is small enough to grok, agents and AI tools will be built against it*. The pitch is what makes that thesis testable. Without the pitch, the kernel can't recruit the people who'd write agents for it.

The Marie Kondo policy says "*does it bring the kernel joy?*" The right answer for the pitch is *yes* — because the kernel's job is to be adopted, not to be technically pristine. A repo that perfectly mirrors grail but has no front door to walk through is a tomb, not a kernel.

## The general principle

**The kernel includes everything required for the kernel to be adopted at scale, even if it's not technical SPEC material.**

Specifically:

- The pitch (`pitch-playbook.html`)
- The audience-facing landing (`index.html`, `pages/index.html`)
- The kernel hub (`pages/kernel.html`)
- The 60-second onboarding (`pages/onboarding.html`)
- The narrative docs that pull readers from "what is this?" to "I want to install" (MASTER_PLAN, HERO_USECASE, ECOSYSTEM)
- The vault prose that justifies the design decisions to the kind of reader who needs to see the reasoning before betting on the platform

These are not "nice to haves." They are part of the kernel's mission surface. Removing any of them weakens adoption.

## What this does NOT justify

The exception is narrow. It does not let through:

- Distro-specific marketing for a particular distro (e.g., "why the Rappter distro is the best distro") — that belongs in the distro's README, not the kernel
- Sales material for downstream services (consulting, enterprise support) — that lives wherever the service lives
- Pitch material that contradicts the kernel SPEC — that breaks the contract the pitch is selling

The test: *is this pitch about the kernel itself?* If yes, it stays. If it's about a layer on top of the kernel, it moves to that layer's repo.

## Other adoption-engine candidates that pass the test

By the same logic, the following also belong in the kernel mirror even though they're not strictly SPEC:

- `pages/about/anatomy.html` — visual diagram of an organism. Pitches the architecture to first-time visitors.
- `pages/onboarding.html` — 60-second walkthrough. Same role for operators.
- `pages/about/*` (leadership, partners, process, security) — trust-building content. Removes adoption friction for cautious enterprise buyers.
- The vault's `Reading Paths/` — guided reads for different audiences (exec / engineer / architect / partner / new contributor). Same job as the pitch, slower pace.

All of these stay in the kernel mirror.

## See also

- [[2026-05-16 — Marie Kondo Audit]] — the policy this is an exception to
- [[2026-05-16 — Kernel-Distro Split]] — the split this clarifies
- [[Engine, Not Experience]] — the founding stance that *doesn't* mean "no adoption surface"
