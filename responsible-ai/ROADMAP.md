# RAPP — Responsible AI Roadmap

> **Owner:** _to be assigned (accountable RAI owner)_ · **Status:** DRAFT ·
> **Last updated:** 2026-06-27 · **Reassessment trigger:** every `VERSION` bump, and at least annually.
> **Maps to:** Microsoft Responsible AI Standard v2 — Goals A1–A5, T1–T3, F1–F3, RS1–RS3, PS1–PS2, I1, plus the Generative-AI supplement.

This is the path to taking **RAPP** (the Rapid Agent Prototype Platform) through a
Microsoft Responsible AI (RAI) review. It is written to be **honest, not flattering.**

## TL;DR — current posture

**RAPP cannot pass an RAI sign-off today.** The platform has solid *engineering*
governance (CONSTITUTION.md, rappid lineage, a public/private boundary) but no
*Responsible-AI* governance mapped to the Standard, and its core design is
high-risk: the brainstem **auto-discovers and executes arbitrary user-dropped
Python in-process with full host privileges**, **auto-installs pip packages** at
import time, **streams other people's agent code** from the public Cave into a
running brainstem (git-invisibly), adds **no content-safety / prompt-shield layer
of its own**, and binds `0.0.0.0` with wildcard CORS. There is **no RAI Impact
Assessment** (the Standard's gating artifact) and **no Transparency Note**.

The good news: the risks are well-understood and the remediations are concrete.
**Phase 0** removes every absolute blocker; the rest hardens, monitors, and polishes.

## Why RAPP is a high-risk RAI subject (the surface)

Code-grounded (see [`THREAT_MODEL.md`](./THREAT_MODEL.md)):

| Surface | Evidence | Why it matters for RAI |
|---|---|---|
| Arbitrary agent code execution | `brainstem.py` `exec_module` (L616-618), `agent.perform()` (L869) | Any `agents/*_agent.py` runs with full host privileges. RCE by design. |
| Auto pip-install | `_auto_install` → `pip install <name>` (L741-756) | A missing import in an agent pulls arbitrary packages. Supply-chain. |
| Cave-streamed third-party agents | [`cave/agents/cave_agent.py`](../cave/agents/cave_agent.py) | Other people's unsigned code streamed in, **git-invisible** (`.git/info/exclude`); sha-pins come from the *same* untrusted source. |
| Network exposure | CORS wildcard (L36), `0.0.0.0` bind, unauthenticated `/agents/import` | `/chat` (hence arbitrary execution) is reachable from the local network. |
| Prompt-injection surfaces | `soul.md`, agent `system_context()`, auto-injected `<memory>` | Untrusted text composes the system prompt unmediated. |
| Data egress | `POST {endpoint}/chat/completions` (default `api.individual.githubcopilot.com`) | Conversation goes to GitHub/Microsoft Copilot; no surfaced privacy notice. |
| Diagnostics exfil | `/diagnostics/report` (L1413-1523) | Posts a session "book.json" to a **public** GitHub issue with partial scrub. |
| Token at rest | `.copilot_token` / `.copilot_session` plaintext on disk | Credential protection gap. |

**Genuine strengths to build on** (not nothing):

- **Privacy-by-default** — CONSTITUTION **Article VII** (no phone-home, no telemetry, no accounts); data is genuinely local-first. Supports PS1 intent + data minimization.
- **A public/private boundary already enforced** — [`cave/specs/PUBLIC_BOUNDARY.md`](../cave/specs/PUBLIC_BOUNDARY.md) is a concrete pre-push "bones not substance" scrub (PS1/A4 control).
- **Partial traceability** — the flight recorder (`.brainstem_book.json`) + per-response `agent_logs` record auth/API/tool events (T1/RS3 starting point); `/diagnostics/report` scrubs `user_code`/`device_code`/`session_id`.
- **soul.md behavioral boundaries** ("never fabricate facts/URLs, never log the token") — a metaprompt to harden.
- **Reliability affordance** — `call_copilot` fails over across models on 4xx/5xx (RS2).
- **Supply-chain starting point** — Cave `load` verifies sha256 pins and refuses to overwrite kernel agents.
- **Governance scaffolding** — CONSTITUTION, rappid provenance, versioned rollback points: a place to anchor RAI policy + an accountable-owner pattern (A2).

## Sensitive Uses determination (the single largest exposure)

Full memo: [`sensitive-uses.md`](./sensitive-uses.md). Summary:

1. **RAPP-as-an-engine** — *not* itself a Microsoft Sensitive Use **by intended-use
   boundary**, but **in scope by foreseeable misuse**: the engine has zero technical
   control preventing agents that DO trigger, and actively lowers the barrier. The
   owner must still (a) complete a platform RAI Impact Assessment, (b) declare
   Restricted Uses, and (c) run a platform Sensitive-Uses consultation.
2. **RAPP-built agents** — where real Sensitive Uses live. Plausible RAPP agents trigger
   **all three** Microsoft triggers: screening/lending → *consequential impact on life
   opportunities*; companion/digital-twin/device-control/medical-financial → *physical or
   psychological injury*; profiling/surveillance/moderation → *human rights*. The platform
   can't certify these centrally, so the obligation is pushed down via a **mandatory
   per-agent Sensitive-Use self-screen + escalation path**.

**Neither exists today** — which is why the Impact Assessment and the Sensitive-Uses
determination are **P0 blockers**.

---

## The roadmap

Phases are ordered by gating power: **P0** removes absolute blockers to *any* RAI
sign-off; nothing downstream can be evidenced until P0 lands.

### P0 — RAI sign-off blockers: govern, contain, disclose

**Goal:** produce the gating governance artifacts, contain the arbitrary-code-execution
and supply-chain surfaces, put a safety layer at the `/chat` seam, and tell users the
truth about where their data goes.

**Tasks**
- **A1** — Complete the Microsoft RAI Impact Assessment Template v2 for the engine (all sections, all three tiers); name an accountable owner; wire it as a release gate. → [`impact-assessment.md`](./impact-assessment.md)
- **A2** — Author the Sensitive Uses determination (3 triggers × engine + agent classes); declare Restricted/Sensitive Uses in CONSTITUTION; ship a mandatory per-agent Sensitive-Use self-screen + escalation path. → [`sensitive-uses.md`](./sensitive-uses.md)
- **T2** — Publish the RAPP Transparency Note (capabilities, intended/out-of-scope uses, limitations incl. no-safety-layer / auto-install / Cave / silent-fallback / Copilot egress) across T1–T3. → [`TRANSPARENCY_NOTE.md`](./TRANSPARENCY_NOTE.md)
- **RS1 / GenAI** — Add **pluggable content-safety middleware** at the single `/chat` chokepoint (input + injected context + output): no-op default for T1, **Azure AI Content Safety** default-on for T2/T3.
- **RS1 / GenAI** — Add **Prompt Shields / spotlighting** over composed system content + user input; tag `system_context()` / memory / tool-output / Cave text as **untrusted**; harden `soul.md` into a delimited trust-boundary metaprompt.
- **PS2** — **Isolate agent execution** out of the Flask/token-holding process (privilege-drop subprocess / container / WASM-RestrictedPython), deny-by-default access to token files / `.env` / network.
- **PS2** — Make pip-install **opt-in** against a hash-pinned allowlist into an isolated venv; refuse untrusted-derived package names.
- **PS2 / A2** — Add **cryptographic provenance/signing** for Cave-streamed agents (rappid keypair, out-of-band trust root); remove git-invisibility; require consent + a static safety scan before first execution.
- **PS2** — **Default-bind `127.0.0.1`**, scope CORS to localhost, require a local auth token + CSRF on mutating routes, remove/gate `/debug/auth`.
- **PS1 / T3** — Add an in-product **data-flow disclosure** + first-run notice naming GitHub/Microsoft Copilot as the inference destination; correct "local-first" copy; add a non-optional `ai_disclosure` field to the `/chat` envelope (incl. the twin "AI projection of `<owner>`" marker).
- **PS1** — Fix `/diagnostics/report`: private/triage default destination, PII redaction on free text, payload preview + explicit public-warning confirmation.

> **Authoritative control specifics** (grounded via Microsoft Learn):
> - **Azure AI Content Safety** classifies four harm categories — **hate, sexual, violence, self-harm** — and returns a severity scale **0 (Safe) to 7** (Microsoft labels the bands Safe / Low / Medium / High) (full `0–7` or trimmed `{0,2,4,6}`). The `/chat` middleware should classify input + injected context + output against these with per-tier configurable thresholds. ([harm categories & severity](https://learn.microsoft.com/azure/ai-services/content-safety/concepts/harm-categories))
> - **Prompt Shields** detects two attack types we must both defend: **User Prompt Attacks** (jailbreaks that try to bypass the system message) and **Document Attacks** (indirect prompt injection embedded in third-party content — directly our `<memory>` / `system_context()` / Cave-text surfaces). It returns `attackDetected`/`filtered` signals. ([Prompt Shields](https://learn.microsoft.com/azure/ai-services/content-safety/concepts/jailbreak-detection)) Pair with **spotlighting** to tag untrusted segments.
> - **Groundedness detection** (P2) scores answers as grounded/ungrounded against provided sources (non-reasoning binary + a reasoning mode that explains flags) — apply to memory-grounded answers. ([groundedness](https://learn.microsoft.com/azure/ai-services/content-safety/concepts/groundedness))

**Exit criteria**
- ☐ Committed `impact-assessment.md` (A1) + `sensitive-uses.md` (A2) with named owner, reassessment trigger, CONSTITUTION cross-reference.
- ☐ Committed `TRANSPARENCY_NOTE.md` linked from README + UI (T2).
- ☐ Content-safety middleware classifies input+output across harm categories with configurable thresholds, emits safety events, is test-covered, default-on for T2/T3 (RS1).
- ☐ A red-team corpus of direct + indirect (memory-poisoning) injections is blocked or quarantined by Prompt Shields/spotlighting (RS1).
- ☐ A sandboxed agent provably cannot read `.copilot_token`/`.copilot_session`/`.env` or make un-allowlisted network calls in a red-team test (PS2).
- ☐ Auto-install of an untrusted-derived package name is refused by test; a Cave-streamed agent with a matching-but-untrusted pin is refused and requires consent + is git-visible (PS2).
- ☐ Default bind is loopback; a foreign Origin cannot import or run an agent; `/debug/auth` exposes no token material (PS2).
- ☐ First-run + `/health` + UI disclose Copilot egress and local stores; every `/chat` response carries `ai_disclosure`; the twin cannot speak as/for a human without the projection marker (PS1, T3).
- ☐ `/diagnostics/report` defaults non-public with PII redaction + payload preview + public-warning confirmation (PS1).

### P1 — Hardening: oversight, credentials, red-team, reliability envelope

**Goal:** put a human in the loop before consequential agent actions, protect
credentials and local data at rest, stand up pre-release red-teaming, and define the
reliability/oversight envelope the Impact Assessment depends on.

**Tasks**
- **A5** — Extend the lifecycle `confirm:true` gate to `run_tool_calls`: per-agent side-effect/impact classification, confirm-before-execute for high-impact tools, server-side kill/interrupt, dry-run, action audit log.
- **A5.1** — Publish the oversight/escalation roles table (operator = oversight owner) with disable/halt/report surfaced in UI + CONSTITUTION.
- **PS2** — Protect credentials at rest (OS keychain / DPAPI / libsecret, or `chmod 600` + optional encryption; `refresh_token` opt-in); ensure the sandbox denies token access.
- **PS1 / A4** — PII-handling module on memory writes + telemetry construction + Cave pre-push; promote the PUBLIC_BOUNDARY scrub to a **blocking CI gate**.
- **A4 / PS1** — Memory data-governance policy (categories, purpose, retention/TTL, consent gate, view/export/delete) + a telemetry catalog with opt-out + age-based retention.
- **RS3 / GenAI** — Stand up a **PyRIT / Azure AI Foundry AI Red Teaming Agent** harness wrapping `/chat` → an Attack-Success-Rate-by-category report; gate `VERSION` releases and Cave-agent promotion on a passing run.
- **RS1 / RS2** — Document RS1.4 operational ranges + the RS2.1 predictable-failure catalog (wrong/destructive tool call, injection, silent model fallback, install failure) with mitigations + residual risk.
- **A3** — Fitness-for-purpose statement per engine intended use; mark Cave/community agents **unverified**.
- **T1 / T2** — Agent provenance manifest in the UI/endpoint; surface the actually-served model (incl. fallback) per response.

**Exit criteria**
- ☐ A test proves no side-effecting agent runs from `/chat` without recorded human confirmation; an operator can halt the tool-call loop mid-run (A5).
- ☐ Credential files are OS-protected and unreadable by a sandboxed agent (PS2).
- ☐ PII handling runs on memory + telemetry + Cave-push with the scrub enforced as blocking CI; users can view/export/delete memory; retention pruning active (A4/PS1).
- ☐ A repeatable red-team run with an ASR report is wired into the release + Cave-promotion checklist with a documented acceptance bar (RS3).
- ☐ The Impact Assessment carries RS1.4 operational ranges + an RS2.1 failure catalog + an A3 fit-for-purpose write-up.
- ☐ A provenance manifest distinguishes local vs streamed agents (author + verified hash); each `/chat` response reports the model used + any fallback (T1/T2).

### P2 — Scale & monitoring: abuse monitoring, grounding, fairness, accessibility

**Goal:** operationalize ongoing safety + inclusiveness.

**Tasks**
- **RS3 / A2** — Safety + adverse-impact event classes through a dedicated channel; incident/remediation runbook; wire T2/T3 to Azure OpenAI abuse monitoring / Foundry Risks & Safety monitoring.
- **RS1 / GenAI** — Optional Azure AI Content Safety **groundedness** detection on memory-grounded answers; flag ungrounded segments in `agent_logs`.
- **F1 / F2 / F3** — Fairness guidance for soul/agent authors; a minimal QoS/stereotype spot-check across languages; require fairness review for allocative (F2) agents via the Sensitive-Use screen.
- **I1** — WCAG 2.1 AA audit of `index.html`; remediate modal focus-trapping, keyboard nav, contrast, labels; publish a conformance statement.

**Exit criteria**
- ☐ Safety + adverse-impact events emitted/queryable; remediation runbook exists; T2/T3 connected to platform abuse monitoring (RS3/A2).
- ☐ Memory-grounded answers can be groundedness-scored with ungrounded segments flagged behind the safety toggle (RS1).
- ☐ Fairness reliance documented in the Impact Assessment; author fairness guidance published; minimal QoS spot-check exists; allocative-use agents flagged (F1/F2/F3).
- ☐ A recorded accessibility audit shows WCAG 2.1 AA conformance (or tracked backlog) with focus-trapping + keyboard nav verified; conformance statement committed (I1).

### P3 — Polish: media provenance, maintenance cadence, reassessment

**Goal:** close the long tail and keep the program from drifting.

**Tasks**
- **GenAI** — Optional Azure AI Content Safety **protected-material** (text + code) detection as an opt-in output filter; documented out-of-default-scope for offline T1.
- **T3** — If voice-mode TTS or any media generation is positioned as authentic, add AI-content provenance (Content Credentials / C2PA) disclosure.
- **A1 (reassessment)** — Owners + last-updated + change logs on all RAI artifacts; tie a transparency/Impact-Assessment review to the `VERSION`-bump ritual + annually.
- **Backbone** — Maintain the [`TRACEABILITY.md`](./TRACEABILITY.md) matrix mapping every control/artifact to its Goal ID.

**Exit criteria**
- ☐ Protected-material detection available as an opt-in output filter, documented optional (GenAI).
- ☐ Any synthesized media carries provenance/AI-content disclosure (T3).
- ☐ All RAI artifacts carry owner + last-updated + change log; release/annual reassessment trigger; one review cycle completed and recorded (A1).
- ☐ A committed traceability matrix maps each control/artifact to its MS RAI Goal ID.

---

## Required artifacts (status)

| Artifact | Goal | Status |
|---|---|---|
| [`impact-assessment.md`](./impact-assessment.md) | A1/A2/A4/RS1/RS2 | DRAFT skeleton — **TO COMPLETE** |
| [`sensitive-uses.md`](./sensitive-uses.md) | A2 | DRAFT |
| [`TRANSPARENCY_NOTE.md`](./TRANSPARENCY_NOTE.md) | T2 | DRAFT |
| [`INTENDED_USES.md`](./INTENDED_USES.md) | A3 | DRAFT |
| [`THREAT_MODEL.md`](./THREAT_MODEL.md) | PS2/RS1 | DRAFT |
| [`TRACEABILITY.md`](./TRACEABILITY.md) | backbone | DRAFT |
| CONSTITUTION.md amendment (Restricted/Sensitive Uses + RAI release gate) | A2/A3 | TODO |
| Content-safety / Prompt-Shields middleware | RS1/GenAI | TODO (P0 engineering) |
| Agent isolation/sandbox + dependency policy | PS2 | TODO (P0 engineering) |
| Cave provenance/signing | PS2/A2 | TODO (P0 engineering) |
| Network/auth hardening | PS2 | TODO (P0 engineering) |
| Human-oversight (confirm-before-execute) | A5 | TODO (P1) |
| Red-team/eval harness (PyRIT/Foundry) | RS3/GenAI | TODO (P1) |
| Accessibility audit (WCAG 2.1 AA) | I1 | TODO (P2) |

## How this gates releases

The Impact Assessment is wired as a **release gate**: a `VERSION` bump may not ship
until the Impact Assessment is current and its P0 exit criteria hold. This is added to
`CONSTITUTION.md` as a Responsible-AI article, alongside the Restricted/Sensitive Uses
policy. The accountable RAI owner signs off each release and triggers reassessment.

## Grounding & honesty notes

- Goal IDs are the **real** Microsoft Responsible AI Standard v2 (June 2022) labels —
  A1–A5, T1–T3, F1–F3, RS1–RS3, PS1–PS2, I1 — used with no invented IDs.
- PS1/PS2/I1 are **compliance-by-reference** Goals (Microsoft Privacy Standard, Security
  Policy, Accessibility Standard); this roadmap does not over-specify their internal clauses.
- The **Generative-AI requirements** are Microsoft's GenAI supplement, which is *not*
  published as a numbered public clause list; they are mapped **by intent** (RAI impact
  assessment, content/abuse filtering + Prompt Shields, metaprompt/grounding, pre-release
  red-teaming, ongoing abuse monitoring, AI-content disclosure, staged release) and to the
  publicly documented Azure AI Foundry operationalization — not to fabricated IDs.
- Exact Standard sub-clause wording (e.g. T1.1, A5.2) is referenced **by role**, not quoted
  verbatim. This is flagged honestly rather than overclaimed.

## References

- Microsoft Responsible AI Standard v2 — General Requirements: <https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/microsoft/final/en-us/microsoft-brand/documents/Microsoft-Responsible-AI-Standard-General-Requirements.pdf>
- Microsoft RAI Impact Assessment Template: <https://blogs.microsoft.com/wp-content/uploads/prod/sites/5/2022/06/Microsoft-RAI-Impact-Assessment-Template.pdf> · [Guide](https://blogs.microsoft.com/wp-content/uploads/prod/sites/5/2022/06/Microsoft-RAI-Impact-Assessment-Guide.pdf)
- Microsoft principles & approach to responsible AI: <https://www.microsoft.com/en-us/ai/principles-and-approach>
- Azure OpenAI Transparency Note: <https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/openai/transparency-note>
- Azure AI Content Safety: [overview](https://learn.microsoft.com/en-us/azure/ai-services/content-safety/overview) · [Prompt Shields](https://learn.microsoft.com/en-us/azure/ai-services/content-safety/concepts/jailbreak-detection) · [groundedness](https://learn.microsoft.com/en-us/azure/ai-services/content-safety/concepts/groundedness)
- Azure AI Foundry AI Red Teaming Agent: <https://learn.microsoft.com/en-us/azure/foundry/concepts/ai-red-teaming-agent> · Microsoft PyRIT: <https://www.microsoft.com/en-us/security/blog/2024/02/22/announcing-microsofts-open-automation-framework-to-red-team-generative-ai-systems/>
- Azure OpenAI Risks & Safety monitoring: <https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/risks-safety-monitor>
