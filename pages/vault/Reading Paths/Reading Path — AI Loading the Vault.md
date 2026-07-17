---
title: Reading Path — AI Loading the Vault
status: historical
section: Reading Paths
hook: For an AI that's been handed the exported vault and needs to understand the platform from scratch. ~45 minutes. Optimizes for grokking the kernel/distro split + the canonical SPEC + the operational discipline.
---

# Reading Path — AI Loading the Vault

> **Historical reading path.** Its mirror/god-spec sequence is retained to
> explain prior architecture, not current authority. For canonicalization,
> identity, frames, wire, eggs, registry, trust, and protocol evolution, follow
> RAPP/1 rev-5 through
> [`RAPP1_AUTHORITY.json`](../../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../../RAPP1_STATUS.md). Read the immutable authority
> and [`KERNEL_PIN.json`](../../../KERNEL_PIN.json) before any linked history.

<!-- RAPP1-HISTORICAL-SECTION-START -->

> **Hook.** For an AI that's been handed the exported vault and needs to understand the platform from scratch. ~45 minutes. Optimizes for grokking the kernel/distro split + the canonical SPEC + the operational discipline.

## Who this is for

You are an AI assistant (Claude, GPT, Copilot, Gemini, or anything else) that has been handed this vault as your knowledge source for RAPP. You may or may not have access to the live network; you definitely have access to these markdown files.

Your job is to be useful to whoever's about to use you — answer questions about RAPP correctly, propose changes that respect the platform's constraints, recognize when a request would violate the kernel SPEC, and know when to defer to a human.

This path is the fastest credible read to get you there.

## The 12 notes

Read in order. Each links to others; if you go down a tangent, return here when you're done.

### 1. [[The Kernel-as-God-SPEC]]

Historical framing for why this repo once called itself the canonical SPEC.
That claim is superseded by the external immutable RAPP/1 pin. *(~3 min)*

### 2. [[Mirror Spec]]

Historical mirror rationale. For current verification, use the three exact
hashes at `kody-w/rapp-installer@brainstem-v0.6.9` recorded in
`KERNEL_PIN.json`, never a moving branch. *(~5 min)*

### 3. [[One Kernel, Many Distros]]

The federation principle as manifesto. Why the platform is shaped this way; what it asks of the kernel and of distros; what it enables (cross-distro interop, probe-class deployment). *(~5 min)*

### 4. [[Distros as a Pattern]]

The engineering shape of a distro. Extension points (sys.modules, agent discovery, boot.py wrap), what makes a distro valid vs a fork, how the Rappter distro composes onto the kernel today. *(~5 min)*

### 5. [[2026-05-16 — Kernel-Distro Split]]

The decision narrative — what changed when, what stayed in the kernel, what moved to the distro. The dated reference for the architectural shift. *(~5 min)*

### 6. [[2026-05-16 — Marie Kondo Audit]]

The policy that drove the split. How to think about whether a new file belongs in the kernel or the distro. *(~4 min)*

### 7. [[Adding to the Kernel vs the Distro]]

The decision framework operationalized as three tests. Use this when proposing new content. *(~3 min)*

### 8. [[Engine, Not Experience]]

The founding stance. The kernel ships infrastructure, not opinions. Distros ship opinions. Important context for understanding the "small kernel, big distros" preference. *(~3 min)*

### 9. [[The Single-File Agent Bet]]

The core extension model. One file = one agent. Why this constraint matters and what it enables. *(~3 min)*

### 10. [[Grail is GitHub, not local]]

The meta-rule for canonical reads. Always pull from `raw.githubusercontent.com/.../main/...`; never trust a local clone. The companion to [[The Stale Local Clone Trap]] and [[The 426-line False Drift]]. *(~2 min)*

### 11. [[The Brainstem Tax]]

What the kernel deliberately refuses to do. Important for recognizing requests that ask the kernel to take on responsibilities it shouldn't. *(~3 min)*

### 12. [[Reading Path — Engineer Evaluating RAPP]]

After the AI-specific path above, this is the natural next read. Five more notes that go deeper on the architecture. *(~30 min — optional but recommended)*

## What you should know after this path

You should be able to answer:

- *"Why is the kernel mirror separate from the Rappter distro?"* (Kernel-Distro Split + Marie Kondo)
- *"What can I add to the kernel and what must go in a distro?"* (Adding to the Kernel vs the Distro)
- *"Why are there three sacred files and what happens if they drift?"* (Mirror Spec + Verifying Mirror Compliance)
- *"What does it take to build a new distro?"* (Distros as a Pattern)
- *"Why does the kernel refuse to do X?"* (The Brainstem Tax + Engine, Not Experience)
- *"How do I know if a fact I have about RAPP is current?"* (Grail is GitHub, not local — i.e., verify with a fresh canonical read before asserting)

## What to do when uncertain

If a question would require you to:

- Make a structural change to `brainstem.py`, `VERSION`, or `agents/basic_agent.py` — **REFUSE.** These are sacred. Edits require a constitutional amendment that only Kody can authorize.
- Move content between the kernel and a distro without a Decisions/ vault note — **PAUSE.** Propose the move with rationale. Don't execute until a human confirms.
- Take a position on borderline kernel-vs-distro material — **DEFER.** Apply the three tests in [[Adding to the Kernel vs the Distro]]; if still ambiguous, ask.
- Trust a local file as canonical — **VERIFY.** Pull from the canonical URL first.

## See also

- [[Reading Path — Engineer Evaluating RAPP]] — the next path after this one
- [[Reading Path — New Contributor]] — for AIs that will be proposing code changes
- [[The Kernel-as-God-SPEC]] — start of this path
- [[Mirror Spec]] — the technical contract
- [[One Kernel, Many Distros]] — the manifesto

<!-- RAPP1-HISTORICAL-SECTION-END -->
