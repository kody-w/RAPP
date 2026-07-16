# Responsible AI — RAPP

> **Owner:** _<to be assigned>_ · **Status:** DRAFT · **Last updated:** 2026-06-27
> **Maps to:** A1–A5 · T1–T3 · F1–F3 · RS1–RS3 · PS1–PS2 · I1 (Microsoft Responsible AI Standard v2 + GenAI supplement)

This directory is the Responsible AI (RAI) bundle for **RAPP — the Rapid Agent Prototype Platform**. It documents how RAPP measures against the [Microsoft Responsible AI Standard v2](https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/microsoft/final/en-us/microsoft-brand/documents/Microsoft-Responsible-AI-Standard-General-Requirements.pdf) (six principles, 17 Goals) and its Generative-AI supplement.

---

## Honest posture (read this first)

**RAPP is not RAI-signed-off today. This bundle is the documented path to a defensible posture — not a claim of compliance.**

RAPP today is a local-first single-developer engine that, by design, executes arbitrary in-process Python on every `/chat` turn ([`brainstem.py` exec_module L616-618 / cls() instantiation L602-639](../rapp_brainstem/brainstem.py)), auto-pip-installs packages whose names can derive from untrusted agent code ([`_auto_install` L741-756](../rapp_brainstem/brainstem.py)), streams unsigned, git-invisible agents from the public Cave ([`cave_agent.py` L153-214](../cave/agents/cave_agent.py)), binds `0.0.0.0` with wildcard CORS ([CORS L36, bind L1544](../rapp_brainstem/brainstem.py)), exfiltrates free-text to a world-readable repo via the public diagnostics path ([`/diagnostics/report` L1413-1523](../rapp_brainstem/brainstem.py)), and adds **no content-safety or prompt-injection layer of its own**. It also has **no completed Impact Assessment, no Sensitive-Uses determination, and no Transparency Note** — the gating governance artifacts the Standard requires. Tier-1 inference does run through the GitHub/Microsoft Copilot API (which applies its own upstream filtering), but that layer is unconfigurable, unevidenced, blind to agent-injected system prompts, and does not gate local tool execution — so it cannot satisfy the Standard on RAPP's behalf. Every document here is framed as **current state → required → exit criteria**, and the P0 items below are hard blockers, not aspirations.

A grounding note carried forward honestly: the Microsoft GenAI requirements are **not** published as a numbered public clause list, and the Standard's sub-clauses are referenced **by role**, not quoted verbatim (the official PDF would not extract cleanly). We map GenAI obligations by intent and to the publicly documented Azure AI Foundry operationalization rather than to fabricated IDs.

---

## P0 blockers at a glance

These are the only true blockers to an RAI sign-off. Nothing downstream can be evidenced until they land. Full detail in [`impact-assessment.md`](./impact-assessment.md) and [`ROADMAP.md`](./ROADMAP.md) (Phase P0).

| # | Blocker | Goal | Doc |
|---|---------|------|-----|
| 1 | No RAI Impact Assessment — the Standard's gating artifact is absent | A1 | [impact-assessment.md](./impact-assessment.md) |
| 2 | No Sensitive-Uses determination, screening, or reporting path | A2 | [sensitive-uses.md](./sensitive-uses.md) |
| 3 | No Transparency Note | T2 | [TRANSPARENCY_NOTE.md](./TRANSPARENCY_NOTE.md) |
| 4 | No content-safety / harm-classification layer at the `/chat` seam | RS1, GenAI | [THREAT_MODEL.md](./THREAT_MODEL.md) |
| 5 | No Prompt Shields / jailbreak + indirect-injection defense over the system-prompt surface | RS1, GenAI | [THREAT_MODEL.md](./THREAT_MODEL.md) |
| 6 | No sandbox — arbitrary agent code runs in-process with full user privileges | PS2 | [THREAT_MODEL.md](./THREAT_MODEL.md) |
| 7 | Auto pip-install of attacker-derived package names (RCE / dependency-confusion) | PS2 | [THREAT_MODEL.md](./THREAT_MODEL.md) |
| 8 | Cave-streamed agents are git-invisible, unsigned, trust-on-first-use | PS2, A2 | [THREAT_MODEL.md](./THREAT_MODEL.md) |
| 9 | `0.0.0.0` bind + wildcard CORS + unauthenticated mutating/debug endpoints | PS2 | [THREAT_MODEL.md](./THREAT_MODEL.md) |
| 10 | No disclosure that prompts are sent to GitHub/Microsoft Copilot; "local-first" copy misleads | PS1, T3 | [TRANSPARENCY_NOTE.md](./TRANSPARENCY_NOTE.md) |
| 11 | Public-issue diagnostics path exfiltrates free-text PII to a world-readable repo | PS1 | [THREAT_MODEL.md](./THREAT_MODEL.md) |

The four runtime-security items (6–9) are P0 because they **compound**: the Cave delivers untrusted code, auto-install executes it, no sandbox contains it, and no auth stops a remote LAN trigger. The chain is the blocker, not any single link.

One honest severity note: the agent-**execution** human-oversight gap (A5) is held at **P1**, not P0, because RAPP ships a minimal default agent set and is local-first/single-operator. It **escalates to P0 the moment any side-effecting agent** (T2/T3 deploy, Cave, file/git) lands in the default set.

---

## What each document is

| Document | Purpose | Primary Goals |
|----------|---------|---------------|
| [`README.md`](./README.md) | This index — bundle map, honest posture, P0 blockers, owner placeholder | — |
| [`ROADMAP.md`](./ROADMAP.md) | The phased remediation plan (P0 Govern/Contain/Disclose → P1 Harden → P2 Scale/Monitor → P3 Polish), each task tagged to a Goal ID with exit criteria | all |
| [`impact-assessment.md`](./impact-assessment.md) | The completed Microsoft RAI Impact Assessment Template v2 — the gating artifact: System Info across 3 tiers, Intended Uses, Adverse Impact (incl. RCE + Cave supply-chain), Data Requirements, Summary of Impact (harms→mitigations→Goal IDs), RS1.4 operational ranges, RS2.1 failure catalog | A1, A2, A3, A4, A5, RS1, RS2 |
| [`sensitive-uses.md`](./sensitive-uses.md) | The Sensitive-Uses determination memo — three triggers × (engine + agent classes), per-agent self-screen field, escalation/reporting path | A2 |
| [`INTENDED_USES.md`](./INTENDED_USES.md) | In-scope / out-of-scope / restricted uses for the engine and RAPP-built agents | A3, A1 |
| [`TRANSPARENCY_NOTE.md`](./TRANSPARENCY_NOTE.md) | Microsoft-format Transparency Note covering Tiers 1–3 — capabilities, intended/out-of-scope uses, limitations (no-safety-layer / auto-install / Cave / silent-fallback), data-flow disclosure, responsible-deployment guidance | T1, T2, T3, PS1 |
| [`THREAT_MODEL.md`](./THREAT_MODEL.md) | Security threat model + the containment design: agent isolation/sandbox, dependency allowlist, Cave provenance/signing, network/auth hardening, hardened diagnostics, content-safety + Prompt-Shields middleware | PS2, RS1, RS2 |
| [`TRACEABILITY.md`](./TRACEABILITY.md) | The RAI-to-Standard traceability matrix — every control/artifact mapped to its Goal ID; the living roadmap backbone | all |

### Sensitive-uses determination (the single largest exposure)

A two-level determination, restated from [`sensitive-uses.md`](./sensitive-uses.md):

1. **RAPP-as-an-engine** is **out of scope by intended-use boundary, but in scope by foreseeable misuse.** In its declared use (one developer's local sandbox) the bare engine makes no consequential decision about a person — but that clean result rests entirely on the narrow framing; the engine has zero technical control preventing it from building/running agents that *do* trigger, and it actively lowers the barrier. Under Microsoft's foreseeable-misuse doctrine the owner must still complete a platform-level Impact Assessment, declare Restricted Uses, and run a Sensitive-Uses consultation.
2. **RAPP-built agents** are where real Sensitive Uses live — plausible agents grounded in the project's own ecosystem trigger **all three**: a resume/lending agent → trigger 1 (employment/credit); a companion / digital-twin / "Holographic Moments" emotional-reliance, device-control, or medical/financial-guidance agent → trigger 2 (psychological/physical injury); a profiling/surveillance/content-moderation agent → trigger 3 (human rights). The obligation is pushed down to each builder via a **mandatory per-agent Sensitive-Use self-screen + escalation path**, exercised **before** deployment.

---

## Accountable owner

**Owner: _<to be assigned>_.** Every artifact in this bundle requires a named, accountable RAI owner before it can move from `DRAFT` to reviewed. Naming this owner is part of P0 (Impact Assessment task, A1/A2). Until then, no document here may be cited as evidence of compliance.

---

## How this connects to governance and the release gate

- **CONSTITUTION.md** ([`../CONSTITUTION.md`](../CONSTITUTION.md)) is RAPP's governance spine. P0 requires a CONSTITUTION amendment declaring the **Restricted Uses + Sensitive Uses policy** and wiring the **RAI sign-off as an explicit release gate** (A2/A3). This bundle builds on existing constitutional strengths that are genuine hooks for RAI controls: Article VII (no-telemetry / no-accounts privacy-by-default), Article IX (Twin-Offers / User-Accepts — the handshake to extend to the execution loop for A5), the lifecycle `confirm:true` pattern, Article XXXIII (kernel-DNA approval + `KERNEL_AGENTS` protection — a hook for real signing), and the `PUBLIC_BOUNDARY.md` bones-not-substance scrub gate ([`../cave/specs/PUBLIC_BOUNDARY.md`](../cave/specs/PUBLIC_BOUNDARY.md)).

- **VERSION release gate.** `main` is production and the install one-liners pull from it, so `main` must always be RAI-truthful. The P0 governance artifacts are wired into the release ritual: every `VERSION` bump triggers a transparency / Impact-Assessment review, and a **reassessment is mandatory on any change to the execution, auth, or streaming surface** (and at least annually). Each artifact carries an owner + last-updated + change log so the program does not drift between releases (P3, A1 reassessment).

The fastest credible path to a defensible posture: **P0** produces the three governance artifacts (Impact Assessment, Sensitive Uses, Transparency Note), contains the RCE/supply-chain surface, puts a safety + disclosure layer on `/chat`, and fixes the public-exfil path. Those are the only true blockers; **P1–P3** are hardening, scale, and polish that the P0 artifacts will themselves schedule.

---

## Key references

- [Microsoft Responsible AI Standard v2 — General Requirements (six principles + 17 Goals)](https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/microsoft/final/en-us/microsoft-brand/documents/Microsoft-Responsible-AI-Standard-General-Requirements.pdf)
- [Microsoft RAI Impact Assessment Template](https://blogs.microsoft.com/wp-content/uploads/prod/sites/5/2022/06/Microsoft-RAI-Impact-Assessment-Template.pdf) · [Guide](https://blogs.microsoft.com/wp-content/uploads/prod/sites/5/2022/06/Microsoft-RAI-Impact-Assessment-Guide.pdf)
- [Microsoft's framework for building AI systems responsibly (Sensitive Uses overview)](https://blogs.microsoft.com/on-the-issues/2022/06/21/microsofts-framework-for-building-ai-systems-responsibly/)
- [Azure OpenAI Transparency Note](https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/openai/transparency-note) · [Azure AI Content Safety](https://learn.microsoft.com/en-us/azure/ai-services/content-safety/overview) · [Prompt Shields](https://learn.microsoft.com/en-us/azure/ai-services/content-safety/concepts/jailbreak-detection)
- [Azure AI Foundry — AI Red Teaming Agent](https://learn.microsoft.com/en-us/azure/foundry/concepts/ai-red-teaming-agent) · [Microsoft PyRIT](https://www.microsoft.com/en-us/security/blog/2024/02/22/announcing-microsofts-open-automation-framework-to-red-team-generative-ai-systems/)
