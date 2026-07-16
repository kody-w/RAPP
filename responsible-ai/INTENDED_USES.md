# RAPP — Intended Uses

> **Owner:** _<to be assigned>_ · **Status:** DRAFT · **Last updated:** 2026-06-27 · **Maps to:** A3 (Fit for purpose), underpins A1 (Impact Assessment); cross-refs A2 (Sensitive Uses), F2 (Allocation)

This document declares what RAPP (the Rapid Agent Prototype Platform) is and is **not** intended for. It is the source of truth for the **Intended Uses** section of the Impact Assessment ([impact-assessment.md](./impact-assessment.md)) and the boundary on which the engine-level Sensitive-Use determination rests ([sensitive-uses.md](./sensitive-uses.md)).

## Honest posture (read first)

**RAPP does not pass the Microsoft Responsible AI Standard today.** The intended-use boundary below is the *single load-bearing control* in RAPP's current Responsible AI posture: the bare engine avoids triggering a Microsoft Sensitive Use **only** because its declared intended use is a single developer's local sandbox — **never** because the engine has any technical control that prevents misuse. The engine actively lowers the barrier to building agents that *do* trigger (in-process arbitrary-Python execution, auto-pip-install, git-invisible Cave streaming, no content-safety layer). See `sensitive_uses_determination` in [impact-assessment.md](./impact-assessment.md).

Because the boundary is doing the safety work that code should be doing, **honoring these declared uses is a Responsible AI obligation, not a suggestion.** Operating RAPP outside the in-scope list voids the (already provisional) RAI rationale.

Everything below is framed as **current state → required → exit criteria**, consistent with the program [ROADMAP.md](./ROADMAP.md).

---

## In scope

These are the uses RAPP is built for and that the engine's Responsible AI rationale currently covers. Each carries a fitness-for-purpose statement (A3): a validity claim, an honest statement that outputs are unvalidated, and generalizability limits.

### 1. Single-developer, local-first prototyping, learning, and testing of AI agents (Tier 1 brainstem)
**Rationale.** On the operator's own machine, the bare engine makes no consequential decision about any person. The blast radius of every gap (in-process execution, auto-install, no sandbox) is the operator's *own* device under their *own* privileges — which is precisely why this framing keeps the engine out of Sensitive-Use scope by boundary.

**Fitness for purpose (A3).** RAPP is fit to let a developer iterate on agents quickly against a live LLM. It is **not** validated for correctness, safety, or grounding of any output: every reply is **unvalidated LLM generation** routed through the GitHub Copilot API, with **no content-safety or prompt-shield layer applied by RAPP itself** (`call_copilot` seam, `brainstem.py`). Generalizability limit: results on the operator's machine do not transfer to any multi-user, networked, or production setting — see Out of Scope #2.

### 2. Rapid authoring and iteration of user-dropped Python agents the operator wrote and trusts
**Rationale.** Agents are auto-discovered from `agents/*_agent.py` and executed in-process (`exec_module` + `cls()`, `brainstem.py` L602-639). This is acceptable **only** when the operator is also the author of every loaded agent — i.e., they are running code they already trust, equivalent to running their own script.

**Fitness for purpose (A3).** RAPP is fit as an authoring/iteration loop for *first-party* agent code (edit-and-reload, no restart). It is **not** a code-review, sandboxing, or trust boundary: any agent runs with the operator's full privileges and can auto-pip-install on import (`_auto_install`, `brainstem.py` L741-756). Generalizability limit: trust does **not** extend to agents the operator did not write — see the **UNVERIFIED** marker below and Out of Scope #4.

### 3. Teaching the Microsoft AI stack progressively across three tiers (T1 local → T2 Azure → T3 M365/Copilot Studio)
**Rationale.** RAPP's stated purpose is pedagogical: a graduated on-ramp to the Microsoft AI stack. The three-tier structure is an instructional vehicle, not a production deployment ladder.

**Fitness for purpose (A3).** RAPP is fit to *demonstrate and teach* the shape of the stack. It is **not** fit to certify that anything learned or built is production-ready: the higher tiers (T2/T3) inherit the same missing safety, oversight, and disclosure controls unless those are added per the [ROADMAP.md](./ROADMAP.md). Generalizability limit: teaching artifacts are illustrative, not reference implementations of a compliant system.

### 4. Sharing non-sensitive agent "bones" (structure, not substance) through the public Cave under the PUBLIC_BOUNDARY scrub gate
**Rationale.** The Cave is intended to share agent *structure* — not private data, secrets, or substance — gated by the `PUBLIC_BOUNDARY.md` bones-not-substance scrub.

**Fitness for purpose (A3).** RAPP is fit to share scrubbed agent skeletons **provided the scrub holds.** Current state: the scrub is a **manual** gate, not enforced CI (P1 remediation pending — see [ROADMAP.md](./ROADMAP.md)). **Required:** promote `PUBLIC_BOUNDARY.md` to a blocking automated CI gate. **Exit criteria:** no Cave push proceeds without the scrub passing in CI. Generalizability limit: "bones" sharing is **not** a channel for trusted, verified, or production-grade agents — anything *received* from the Cave is **UNVERIFIED** (see below).

> ### ⚠️ Cave / community agents are UNVERIFIED
> Agents streamed from the public Cave are **unsigned, git-invisible (hidden via `.git/info/exclude`), unsandboxed, and trust-on-first-use** (`cave_agent.py` L153-214, self-referential sha256-pin verify). They are **community-sourced and unverified.** Running Cave-streamed code is treated as third-party code execution and is **Out of Scope #4** until cryptographic provenance, git-visibility, and a consent + static-scan gate land (P0 — [ROADMAP.md](./ROADMAP.md), [THREAT_MODEL.md](./THREAT_MODEL.md)). Any UI/endpoint surfacing such agents must mark them **UNVERIFIED / community-sourced**.

---

## Out of scope

RAPP is explicitly **not** intended for these uses. Using RAPP for any of them is unsupported and outside its Responsible AI rationale.

### 1. Any consequential or high-stakes decision about a person
Hiring, lending/credit, healthcare, housing, legal status, benefits eligibility, and similar.
**Rationale.** RAPP output is unvalidated LLM generation with **no fitness-for-purpose evidence**. There is no validity testing, no fairness review, and no human-oversight gate over execution. Such uses are also Microsoft **Sensitive Uses** (trigger 1, consequential impact; see [sensitive-uses.md](./sensitive-uses.md)) and are **Restricted** when built as agents (see Restricted #1).

### 2. Production, multi-tenant, or untrusted-network deployment of the Tier-1 brainstem as shipped
**Rationale.** The engine **executes arbitrary in-process code** and **binds `0.0.0.0`** with **wildcard CORS** and unauthenticated mutating/debug endpoints (`brainstem.py` CORS L36, `0.0.0.0` bind L1544, unauthenticated `/agents/import` L1251-1278). The arbitrary-execution + auto-install + no-sandbox + open-bind chain is the blocker (see [THREAT_MODEL.md](./THREAT_MODEL.md)). The local-first, single-operator framing is the only context in which the current security posture is defensible.

### 3. Reliance on RAPP output as accurate, grounded, or safety-filtered without independent human verification
**Rationale.** RAPP adds **no content-safety, prompt-shield, or groundedness layer of its own.** (Tier-1 inference does pass through GitHub Copilot's upstream filtering, but that layer is unconfigurable, unevidenced, blind to agent-injected system prompts, and does not gate local tool execution — it cannot satisfy the Standard on RAPP's behalf.) A human must independently verify any output before acting on it.

### 4. Running third-party / Cave-streamed agent code as if it were reviewed or trusted
**Rationale.** Cave-streamed code is unsigned, git-invisible, unsandboxed, and trust-on-first-use (`cave_agent.py` L153-214). Until provenance/signing + sandbox + consent gate land (P0), treat all such code as **UNVERIFIED** and do not run it in any context where the operator's credentials, data, or device matter.

---

## Restricted

These uses may be **permissible only after** a documented review. They are not categorically forbidden, but they require the Sensitive-Use screen and review-before-deploy described under **"If you need a restricted use"** below.

1. **Allocative-decision agents (F2).** Building or deploying any RAPP agent that makes allocative decisions about people **requires a documented fairness review and Sensitive-Use screening** before deployment. *(Sensitive-Use trigger 1.)*
2. **Companion / digital-twin / "Holographic Moments" agents** that foster emotional reliance, give medical/financial guidance, or control physical devices. **Review-before-deploy.** *(Sensitive-Use trigger 2 — physical/psychological injury.)*
3. **Profiling, surveillance, biometric, or content-moderation agents.** **Review-before-deploy.** *(Sensitive-Use trigger 3 — human rights.)*
4. **Digital-twin / proxy persona that "speaks AS the owner in first person" to peers.** Restricted to contexts carrying a **non-overridable "AI projection of `<owner>`, not `<owner>`" disclosure** (T3; brainstem-to-brainstem / peer-proxy paths especially). See [TRANSPARENCY_NOTE.md](./TRANSPARENCY_NOTE.md).
5. **Auto-pip-install of packages whose names derive from untrusted agent code, and non-loopback network binding.** Restricted to **explicit opt-in with consent** — never automatic (`_auto_install`, `brainstem.py` L741-756; `0.0.0.0` bind L1544).

---

## If you need a restricted use, do this

A restricted use is **not** unlocked by reading this document. Before building or deploying anything in the Restricted list:

1. **Run the per-agent Sensitive-Use self-screen.** Apply the three Microsoft triggers — (i) consequential impact on legal status/life opportunities; (ii) significant physical or psychological injury; (iii) restriction/infringement of human rights — to your specific agent. Record the result in the agent's metadata Sensitive-Use screening field. *(Field + escalation path are a P0 deliverable — see [sensitive-uses.md](./sensitive-uses.md) and [ROADMAP.md](./ROADMAP.md). Until shipped, document the screen manually in your agent's design note.)*
2. **Escalate before deploy.** If any trigger fires (or is ambiguous), route the agent through the declared escalation/reporting path **before deployment** — analogous to Microsoft's Office of Responsible AI / Sensitive Uses review. Do not self-certify a triggering agent.
3. **For allocative (F2) agents,** additionally complete a documented **fairness review** and record fairness reliance + residual risk in the [impact-assessment.md](./impact-assessment.md).
4. **For twin/proxy personas (Restricted #4),** confirm the non-overridable AI-projection disclosure fires across UI, headless API, and peer-proxy paths before any peer-facing use.

> Current state: the per-agent screening field, escalation body, and runtime flag **do not yet exist** — they are **P0 blockers** for RAI sign-off. Until they ship, restricted uses must not be deployed; document the screen by hand and hold for review.

---

## Grounding & honesty notes

- Goal IDs (A1–A5, T1–T3, F1–F3, RS1–RS3, PS1–PS2, I1) are the real labels from the **Microsoft Responsible AI Standard v2** (June 2022). No IDs are invented.
- The **Generative-AI requirements** are Microsoft's GenAI supplement, which is **not** published as a numbered public clause list; they are referenced **by intent**, not by fabricated clause numbers.
- Standard **sub-clauses** (e.g., A3's fitness-for-purpose obligation, A5.1 oversight) are referenced **by role**, not quoted verbatim — the official Standard PDF did not extract cleanly in the source analysis. This is flagged honestly rather than overclaimed.

## Related artifacts

- [ROADMAP.md](./ROADMAP.md) — phased path to a defensible RAI posture (P0–P3)
- [impact-assessment.md](./impact-assessment.md) — the A1 gating artifact (Intended Uses section consumes this doc)
- [sensitive-uses.md](./sensitive-uses.md) — three-trigger determination + escalation path (A2)
- [TRANSPARENCY_NOTE.md](./TRANSPARENCY_NOTE.md) — capabilities, limitations, AI-interaction disclosure (T2/T3)
- [THREAT_MODEL.md](./THREAT_MODEL.md) — execution/supply-chain/network attack surface (PS2)
- [TRACEABILITY.md](./TRACEABILITY.md) — control/artifact → MS RAI Goal ID matrix

## Citations

- Microsoft Responsible AI Standard v2, General Requirements: https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/microsoft/final/en-us/microsoft-brand/documents/Microsoft-Responsible-AI-Standard-General-Requirements.pdf
- Microsoft's framework for building AI systems responsibly (principles + Sensitive Uses overview): https://blogs.microsoft.com/on-the-issues/2022/06/21/microsofts-framework-for-building-ai-systems-responsibly/
- Microsoft principles and approach to responsible AI: https://www.microsoft.com/en-us/ai/principles-and-approach
- Azure OpenAI Transparency Note (Microsoft Transparency Note structure): https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/openai/transparency-note
- Code-grounded RAPP evidence — `brainstem.py` (exec_module+cls() L602-639; _auto_install L741-756; CORS L36 + 0.0.0.0 bind L1544; unauthenticated /agents/import L1251-1278): `/Users/kodywildfeuer/.brainstem/neighborhoods/RAPP/rapp_brainstem/brainstem.py`
- Code-grounded RAPP evidence — `cave_agent.py` git-invisible streaming + self-referential sha256-pin verify (L153-214): `/Users/kodywildfeuer/.brainstem/neighborhoods/RAPP/cave/agents/cave_agent.py`
