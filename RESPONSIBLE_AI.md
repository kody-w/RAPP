# Responsible AI at RAPP

> **Status:** DRAFT · **Owner:** _to be assigned (accountable RAI owner)_ · **Last updated:** 2026-06-27

RAPP is a platform for building and running AI agents. That power carries
responsibility. This document is the front door to RAPP's Responsible AI program —
how we align with the **Microsoft Responsible AI Standard v2** (the six principles:
Accountability, Transparency, Fairness, Reliability & Safety, Privacy & Security,
Inclusiveness) and its generative-AI requirements.

## Honest posture

**RAPP is not RAI-signed-off today.** We say so plainly. RAPP's design is, by
intent, permissive: the brainstem executes arbitrary user-authored Python agents
in-process, auto-installs their dependencies, can stream other people's agents in
from the public Cave, and adds no content-safety layer of its own — it relies on the
underlying GitHub Copilot model. Those are exactly the surfaces a Responsible AI
review exists to gate.

The [**Responsible AI Roadmap**](./responsible-ai/ROADMAP.md) is the documented,
honest path from here to a defensible sign-off. **Phase 0** removes every absolute
blocker (the gating governance artifacts, containment of the code-execution and
supply-chain surfaces, a safety layer at the `/chat` seam, and truthful data-flow
disclosure); later phases harden, monitor, and polish.

## The Phase-0 blockers, at a glance

| Blocker | Principle |
|---|---|
| No RAI Impact Assessment (the Standard's gating artifact) | Accountability (A1) |
| No Sensitive Uses determination / per-agent screen | Accountability (A2) |
| No content-safety / prompt-shield layer — safety delegated to Copilot | Reliability & Safety (RS1) |
| Arbitrary code execution + auto-pip-install + `0.0.0.0`/wildcard-CORS | Privacy & Security (PS2) |
| Unsigned, git-invisible Cave-streamed third-party agents | Privacy & Security (PS2) |
| No data-flow disclosure (conversation goes to GitHub/Microsoft Copilot) | Privacy & Security / Transparency (PS1/T3) |
| No Transparency Note | Transparency (T2) |

## What's here

- [`responsible-ai/ROADMAP.md`](./responsible-ai/ROADMAP.md) — the phased plan (P0→P3) with tasks + measurable exit criteria mapped to Goal IDs. **Start here.**
- [`responsible-ai/INTENDED_USES.md`](./responsible-ai/INTENDED_USES.md) — in-scope / out-of-scope / restricted uses (A3).
- [`responsible-ai/impact-assessment.md`](./responsible-ai/impact-assessment.md) — the RAI Impact Assessment skeleton (A1) — **the gating artifact to complete.**
- [`responsible-ai/sensitive-uses.md`](./responsible-ai/sensitive-uses.md) — the Sensitive Uses determination + per-agent self-screen (A2).
- [`responsible-ai/TRANSPARENCY_NOTE.md`](./responsible-ai/TRANSPARENCY_NOTE.md) — capabilities, limitations, responsible deployment (T2).
- [`responsible-ai/THREAT_MODEL.md`](./responsible-ai/THREAT_MODEL.md) — the agent-execution + supply-chain + prompt-injection threat model (PS2/RS1).
- [`responsible-ai/TRACEABILITY.md`](./responsible-ai/TRACEABILITY.md) — the Goal-ID → control/artifact compliance board.

## How it connects to RAPP's governance

The Impact Assessment is wired as a **release gate** in
[`CONSTITUTION.md`](./CONSTITUTION.md): a `VERSION` bump may not ship until the
assessment is current and its P0 exit criteria hold, and the accountable RAI owner
signs off each release. RAPP's existing strengths — Article VII (privacy by default,
no telemetry/accounts), the [`PUBLIC_BOUNDARY.md`](./cave/specs/PUBLIC_BOUNDARY.md)
"bones not substance" scrub, rappid provenance/lineage, and the flight recorder —
are the foundation this program builds on.

## Reporting a concern

Found a safety, privacy, or misuse concern in RAPP or a RAPP-built agent? Open an
issue on this repo, or contact the accountable RAI owner (above). Sensitive-Use
concerns follow the escalation path in [`sensitive-uses.md`](./responsible-ai/sensitive-uses.md).
