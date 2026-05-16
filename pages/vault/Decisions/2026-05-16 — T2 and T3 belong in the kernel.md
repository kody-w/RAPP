---
title: 2026-05-16 — T2 and T3 belong in the kernel
status: published
section: Decisions
hook: First instinct during the diet was to move Tier 2 (Azure Functions) and Tier 3 (Copilot Studio) to the distro. Wrong instinct — the three-tier Stack IS the kernel's identity, and grail itself ships the deploy artifacts at its root.
---

# 2026-05-16 — T2 and T3 belong in the kernel

> **Hook.** First instinct during the diet was to move Tier 2 (Azure Functions) and Tier 3 (Copilot Studio) to the distro. Wrong instinct — the three-tier Stack IS the kernel's identity, and grail itself ships the deploy artifacts at its root.

## The wrong move + the correction

In commit `b4f3e31` (the first diet pass), I migrated `rapp_swarm/` (T2) and `worker/` + `MSFTAIBASMultiAgentCopilot_*.zip` (T3) to the distro. The reasoning at the time: the bare brainstem (T1) is the "real" kernel; T2 and T3 are downstream deployment patterns.

Kody pushed back:

> *"t2/t3 was always apart of the kernel..."*

Verified against grail (the actual kody-w/rapp-installer repo's main branch on GitHub, not a local clone). Grail ships at its root:

- `azuredeploy.json` — ARM template for the Tier 2 Function App
- `deploy.sh`, `deploy.ps1` — Azure deploy scripts
- `MSFTAIBASMultiAgentCopilot_1_0_0_5.zip` — the Tier 3 Power Platform solution
- `install.sh`, `install.ps1`, `install.cmd`, `install.command` — universal installers
- `community_rapp/` — community-side install surface

T2 and T3 deploy artifacts are grail-canonical. They're part of what the kernel is — *"the kernel is the brainstem PLUS the deploy artifacts that take it from a laptop to Azure to Copilot Studio."*

Commit `4f6c14b` restored everything.

## Why this is the right answer

The platform's brand and adoption story IS the three-tier Stack. *"Local-first AI agents that grow into the Microsoft enterprise stack one tier at a time. Brainstem → Swarm → Copilot Studio."* If you strip T2 and T3 out, the kernel mirror is no longer pitching what RAPP actually is — it's pitching a Flask server.

Operationally, the deploy artifacts are tiny (~kilobytes for ARM templates and shell scripts) and the Python implementation in `rapp_swarm/` is the reference for how to deploy the agent contract on Functions. Both are tightly coupled to the kernel SPEC; both should be where the SPEC is.

The mental model: **the kernel = T1 brainstem + T2 deploy contract + T3 enterprise bundle.** The distro = organism-layer features that compose on top of any tier.

## What this implies for future moves

When considering whether to move a file from the kernel to the distro, three quick tests:

1. **Does grail ship it?** — if yes, it stays. (Grail is authoritative.)
2. **Is it part of the three-tier Stack narrative?** — if yes, it stays.
3. **Is it deploy infrastructure for any tier?** — if yes, it stays.

The Cloudflare `worker/` for the OAuth bridge is a slightly fuzzier case (it's not strictly in grail, but it's load-bearing for the "Copilot OAuth without credentials" pitch that the three-tier narrative implies). Per Kody's call, it stays.

## See also

- [[Why Three Tiers, Not One]] — the founding decision behind the three-tier shape
- [[2026-05-16 — Marie Kondo Audit]] — the policy that surfaced the question
- [[Grail is GitHub, not local]] — the meta-lesson about reading authoritative content from authoritative sources
- [[2026-05-16 — Kernel-Distro Split]] — the larger split this clarifies
