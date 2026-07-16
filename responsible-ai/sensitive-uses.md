# Sensitive Uses Determination — RAPP (Rapid Agent Prototype Platform)

> **Owner:** _to be assigned_ · **Status:** DRAFT · **Last updated:** 2026-06-27 · **Maps to:** A2 (Oversight of significant adverse impacts) — with dependencies on A1, A3, A5, F2, PS2, RS1
>
> Maps to Microsoft Responsible AI Standard v2, **Goal A2** (identification, review, and oversight of Sensitive Uses). This memo is the A2 artifact required for RAI sign-off.

**Sibling documents (`./`):** [ROADMAP.md](./ROADMAP.md) · [impact-assessment.md](./impact-assessment.md) · [TRANSPARENCY_NOTE.md](./TRANSPARENCY_NOTE.md) · [THREAT_MODEL.md](./THREAT_MODEL.md) · [INTENDED_USES.md](./INTENDED_USES.md) · [TRACEABILITY.md](./TRACEABILITY.md)

---

## 0. Honest posture statement

**RAPP does not pass the Microsoft Responsible AI Standard today.** This memo, together with the platform [Impact Assessment](./impact-assessment.md), is one of the two **P0 governance blockers** to any RAI sign-off. Neither artifact existed before this draft. Nothing in this memo should be read as a claim that RAPP is compliant; it documents the *current state*, the *required* end state, and the *exit criteria* that separate them.

Two grounding caveats are carried forward honestly and are not papered over:

- **The Microsoft Sensitive Uses framework** is described publicly (see citations) but RAPP's mapping of the three triggers to RAPP-specific agent classes is *our* applied judgment, not a quotation of Microsoft's internal review criteria.
- **The Standard's sub-clauses** (e.g. the exact wording under A2) could not be extracted verbatim from the official PDF; they are referenced **by role**, not quoted. The Goal IDs used here (A2, plus A1/A3/A5/F2/PS2/RS1) are the real Standard v2 labels.

---

## 1. What a "Sensitive Use" is (the three triggers)

Under Microsoft's framework, an AI system or use case is a **Sensitive Use** when its *reasonably foreseeable* use or misuse could:

1. **Trigger 1 — Consequential impact on legal status or life opportunities.** Denial or material change of consequential services or opportunities: employment/hiring, lending and credit, education, housing, insurance, social benefits eligibility, legal status.
2. **Trigger 2 — Risk of physical or psychological injury.** Significant physical or psychological harm to a person.
3. **Trigger 3 — Restriction or infringement of human rights.** Threat to fundamental rights — privacy, freedom of expression/assembly, freedom from unlawful surveillance or discrimination.

If **any** trigger plausibly fires, the use must be **reported and reviewed before deployment** by an accountable oversight body (Microsoft routes this through its Office of Responsible AI / Sensitive Uses review). RAPP must reproduce an analogous path because it cannot rely on a central body it does not have.

---

## 2. The two-level determination

RAPP is unusual: it is both **an engine** (the brainstem server) and **a factory for agents** that other people build and run. A Sensitive Uses determination has to be made at **both** levels, because the engine's clean result rests entirely on a narrow intended-use boundary, not on any technical control.

### Level 1 — RAPP-as-an-engine

**Verdict: OUT of scope by intended-use boundary; IN scope by foreseeable misuse. Must be documented, not waved off.**

In its **declared intended use** — a single developer's local, loopback sandbox for prototyping, learning, and testing agents on their own machine (see [INTENDED_USES.md](./INTENDED_USES.md)) — the bare engine makes **no consequential decision about any person**. Against the three triggers, the engine in that framing does not fire:

| Trigger | Bare engine, declared intended use |
|---|---|
| 1 — life opportunities | No allocative decision is rendered by the engine itself. |
| 2 — physical/psychological injury | No person is the subject of an output; single local operator. |
| 3 — human rights | No surveillance/profiling function in the engine itself. |

**But that clean result is boundary-only, never design-control.** The engine has **zero technical control** preventing it from building and running agents that *do* trigger, and it actively **lowers the barrier** to doing so. The relevant code-grounded facts:

- **In-process arbitrary-Python execution.** Agents are loaded and instantiated in the server's own address space — `brainstem.py` `exec_module(...)` + `cls()` (≈ L602–639). A built agent runs with the full privileges of the brainstem process (which holds the Copilot token).
- **Auto-pip-install at import.** `brainstem.py` `_auto_install` (L741–756) installs missing packages automatically, including names that can derive from untrusted agent code.
- **Git-invisible cross-brainstem streaming.** `~/.brainstem/neighborhoods/RAPP/cave/agents/cave_agent.py` (L153–214) streams third-party agent code, hides it via `.git/info/exclude`, and verifies it against a sha256 pin co-located in the same untrusted index (self-referential / trust-on-first-use).
- **No content-safety layer of RAPP's own.** Inference flows through GitHub/Microsoft Copilot, which applies *upstream* filtering — but that layer is unconfigurable, unevidenced, blind to agent-injected system prompts, and does not gate local tool execution. It cannot satisfy the Standard on RAPP's behalf.
- **Non-loopback exposure.** `brainstem.py` binds `0.0.0.0` (≈ L1544) with wildcard CORS (L36), so the "single local operator" assumption is not even enforced at the network layer.

Under Microsoft's **foreseeable-misuse doctrine**, the platform owner must therefore still:

- **(a)** Complete a **platform-level RAI Impact Assessment** for the engine → [impact-assessment.md](./impact-assessment.md) (A1 — currently a P0 blocker).
- **(b)** Declare **Restricted Uses** for the engine → see §3 and the CONSTITUTION amendment (A2/A3).
- **(c)** Run a **platform-level Sensitive Uses consultation** with a named oversight owner → this memo plus the escalation path in §6.

> Engine-level Restricted Uses to declare include: building/deploying any agent that makes allocative decisions about people without fairness review + Sensitive-Use screen; companion/twin/device-control/medical-financial agents; profiling/surveillance/moderation agents; a first-person "speaks AS the owner" proxy without a non-overridable AI-projection disclosure; and auto-pip-install of untrusted-derived names + non-loopback bind (opt-in-with-consent only).

### Level 2 — RAPP-built agents

**Verdict: This is where real Sensitive Uses live. Plausible RAPP agents — grounded in the project's own ecosystem — trigger ALL THREE.** RAPP-the-platform cannot centrally certify agents it neither authored nor reviewed, so the A2 obligation must be **pushed down to each builder** via a mandatory per-agent self-screen (§5) plus an escalation/reporting path (§6) exercised **before deployment**.

| Sensitive-Use trigger | Concrete RAPP agent classes that fire it |
|---|---|
| **Trigger 1 — Consequential impact on legal status / life opportunities** | **Screening / lending agents:** resume or candidate-screening agents; lending, credit, or loan-eligibility agents; benefits-, housing-, insurance-, or admissions-eligibility agents. Any agent whose output gates a consequential opportunity for a person. → also an **F2 allocation** concern; requires a documented fairness review. |
| **Trigger 2 — Risk of physical or psychological injury** | **Companion / twin / device-control / medical-financial agents:** companion or "Holographic Moments" agents that foster emotional reliance; the **digital-twin / proxy persona** that speaks *as* the owner; agents that give medical or financial guidance; agents that control physical devices (home/IoT/robotics). |
| **Trigger 3 — Restriction / infringement of human rights** | **Profiling / surveillance / moderation agents:** person-profiling or scoring agents; surveillance or biometric agents; content-moderation agents; agents that monitor, track, or rank individuals. |

Because the same code facts that make the engine permissive (in-process exec, auto-install, unsandboxed streamed code, no owned safety layer) also amplify any harm an agent in these classes could do, **a self-declared or heuristically-flagged Sensitive-Use agent must not be treated as "just another drop-in."** It must complete the self-screen and, where it self-declares Sensitive, follow the escalation path before deploy.

---

## 3. Required platform obligations (current state → required → exit criteria)

| # | Obligation | Current state | Required | Exit criteria |
|---|---|---|---|---|
| O1 | Platform RAI Impact Assessment (A1) with Restricted Uses declared | **Absent (P0 blocker)** | Complete MS RAI Impact Assessment Template v2 for the engine, all sections (adapted from the MS Template), all three tiers; declare Restricted Uses | Committed [impact-assessment.md](./impact-assessment.md) with named owner + reassessment trigger, enumerating restricted/sensitive uses |
| O2 | Sensitive Uses determination + memo (A2) | **This document (DRAFT) — no prior artifact** | Publish the three-trigger memo × engine + agent classes | Published `sensitive-uses.md`; CONSTITUTION cross-reference |
| O3 | Per-agent Sensitive-Use **self-screen field** (A2) | **Absent** | Mandatory field in agent metadata; runtime/UI flag when an agent self-declares or is heuristically flagged | Required screening field present; flag surfaced; evidence the path was exercised on the existing companion/twin and deploy-style (T2/T3) agents |
| O4 | **Escalation / reporting path** (A2) | **Absent** | A documented body + route analogous to MS Office of Responsible AI Sensitive Uses review | Path published (§6); a recorded review of at least the companion/twin and T2/T3 deploy agents |
| O5 | Restricted Uses + Sensitive Uses **policy in CONSTITUTION** (A2/A3) | **Absent** | Amend CONSTITUTION to declare Restricted/Sensitive Uses and the RAI release gate | Committed CONSTITUTION amendment cross-referencing this memo and the Impact Assessment |

These obligations are tracked in [ROADMAP.md](./ROADMAP.md) Phase **P0** ("Govern, Contain, Disclose").

---

## 4. The mandatory per-agent Sensitive-Use self-screen field

Every agent built or deployed on RAPP **must** carry a Sensitive-Use self-screen in its `metadata`. RAPP cannot centrally certify agents, so the screen is the builder's attestation and the trigger for escalation.

**Required metadata shape (proposed):**

```python
# In a *_agent.py BasicAgent subclass metadata:
"sensitive_use_screen": {
    "screened_by": "<builder handle>",          # required
    "screened_on": "<YYYY-MM-DD>",               # required
    "triggers_evaluated": [1, 2, 3],             # all three must be considered
    "triggers_fired": [],                        # subset of [1,2,3]; [] = none fired
    "classification": "none | restricted | sensitive",
    "rationale": "<one line per fired trigger; or why none fire>",
    "escalation_ref": "<review ticket/record id if sensitive; else null>",
    "human_oversight": "<who can halt/disable this agent at runtime>"
}
```

**Runtime/UI behavior required (exit criteria for O3):**

- An agent **missing** `sensitive_use_screen` is surfaced as **unscreened** in the agent provenance manifest and may be blocked from the default/auto-load set in T2/T3.
- An agent whose `classification` is `sensitive` is **flagged in the UI** and **must reference an escalation record** before it can be deployed beyond a single local operator.
- Heuristic flagging (keyword/category match against the §2 agent classes) raises the flag even when the builder declared `none` — discrepancies route to review.

> This is an attestation layer, **not** a sandbox. It does not contain the runtime risks documented in [THREAT_MODEL.md](./THREAT_MODEL.md) (in-process exec, auto-install, unsigned Cave streaming). Those are separate P0 PS2/RS1 controls. The self-screen governs *whether a Sensitive Use should ship at all*; the sandbox governs *what damage any agent can do*.

---

## 5. Copy-paste self-screen checklist (run BEFORE deploy)

Builders: complete this for **every** agent before deploying beyond your own loopback machine. If you check **any** box under a trigger, that trigger **fires** → classification is at least `restricted`, and a `sensitive` classification requires the escalation path in §6 **before** deploy.

```text
RAPP SENSITIVE-USE SELF-SCREEN  —  agent: ______________________  builder: __________  date: __________

TRIGGER 1 — Consequential impact on legal status / life opportunities
[ ] Does this agent's output influence hiring, candidate/resume screening, or employment?
[ ] Does it influence lending, credit, loans, or financial eligibility?
[ ] Does it influence housing, insurance, education/admissions, benefits, or legal status?
[ ] Could a person be denied or granted a consequential opportunity based on its output?
    -> If any checked: TRIGGER 1 FIRES. Also requires a documented FAIRNESS review (F2 allocation).

TRIGGER 2 — Risk of physical or psychological injury
[ ] Is this a companion / "Holographic Moments" / emotional-support agent that could foster reliance?
[ ] Is this a digital-twin / proxy that speaks AS or FOR a specific human?
[ ] Does it give medical, mental-health, safety, or financial guidance a person might act on?
[ ] Can it control physical devices (home/IoT/robotics/vehicles)?
    -> If any checked: TRIGGER 2 FIRES.
       (Twin/proxy: also REQUIRES a non-overridable "AI projection of <owner>, not <owner>" disclosure — T3.)

TRIGGER 3 — Restriction / infringement of human rights
[ ] Does it profile, score, rank, or categorize individuals?
[ ] Does it perform surveillance, tracking, location, or biometric analysis of people?
[ ] Does it moderate, filter, suppress, or flag people's content or speech?
    -> If any checked: TRIGGER 3 FIRES.

CLASSIFICATION
[ ] none       — no trigger fired. Record the screen in metadata and deploy.
[ ] restricted — a trigger fired but use is narrowly bounded; complete fairness review (if T1) and
                 attach mitigations; record in metadata; notify the oversight owner.
[ ] sensitive  — a trigger fired AND the agent will affect real people beyond the builder ->
                 STOP. Do NOT deploy. File the escalation (Section 6) and obtain review sign-off first.

RUNTIME OVERSIGHT
[ ] Who can halt/disable this agent at runtime? ______________________  (required for restricted/sensitive)
[ ] Side-effecting tools require confirm-before-execute?  [ ] yes  [ ] n/a   (A5 — see ROADMAP P1)

ATTESTATION
I have evaluated all three triggers honestly. Triggers fired: __________   Classification: __________
Escalation record id (if sensitive): __________________   Signature/handle: __________________
```

---

## 6. Escalation / reporting path (analogous to MS Office of Responsible AI Sensitive Uses review)

Microsoft routes Sensitive Uses to its **Office of Responsible AI** for pre-deployment review. RAPP has no such body by default, so the platform must **name one** and document the route. Until an owner is assigned (this memo's header carries `Owner: to be assigned`), this path is **defined but not yet operational** — that gap is itself a P0 exit-criterion (O4).

**Path (required end state):**

1. **Self-screen** (§5) is completed by the builder for every agent. Recorded in `metadata.sensitive_use_screen`.
2. **Trigger fires → classify.** `none` deploys with the screen recorded; `restricted` adds mitigations + fairness review (T1) and notifies the oversight owner; `sensitive` **halts deployment**.
3. **File the escalation.** For any `sensitive` classification, the builder files a review request to the **RAPP Responsible AI oversight owner** (named in the [Impact Assessment](./impact-assessment.md); for the local-first single-operator tier the operator is also the A5.1 oversight owner). The request includes the completed self-screen, the agent's intended use, affected population, and proposed mitigations.
4. **Review & decision.** The oversight owner (or designated reviewer) records: approve / approve-with-conditions / reject, with rationale. Sensitive agents may not enter the default/auto-load set or T2/T3 deployment without a recorded sign-off.
5. **Record & reassess.** The decision is logged (flight recorder / review register). Re-screen on any material change to the agent's behavior, the affected population, or the execution/auth/streaming surface, and at least annually — aligned to the [Impact Assessment](./impact-assessment.md) reassessment trigger and the VERSION-bump release ritual.

**Exit criteria (O4):** the path above is published, an owner is named, and there is **recorded evidence it was exercised** on at least the existing companion/twin agents and the deploy-style (T2/T3) agents.

---

## 7. Traceability

| Obligation | Goal | Roadmap phase | Exit-criteria source |
|---|---|---|---|
| Sensitive Uses memo (this doc) | **A2** | P0 | §3 O2 |
| Per-agent self-screen field + flag | **A2** | P0 | §3 O3, §4 |
| Escalation/reporting path | **A2** | P0 | §3 O4, §6 |
| Restricted/Sensitive Uses policy in CONSTITUTION | **A2/A3** | P0 | §3 O5 |
| Platform Impact Assessment dependency | **A1** | P0 | [impact-assessment.md](./impact-assessment.md) |
| Allocative-agent fairness review (Trigger 1) | **F2** | P2 | §5 Trigger 1 |
| Twin/proxy AI-projection disclosure (Trigger 2) | **T3** | P0 | §5 Trigger 2 |
| Confirm-before-execute for side-effecting agents | **A5** | P1 | §5 Runtime Oversight |

Full mapping lives in [TRACEABILITY.md](./TRACEABILITY.md).

---

## 8. Citations

- Microsoft Responsible AI Standard v2 — General Requirements (the six principles + 17 Goals incl. A2): https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/microsoft/final/en-us/microsoft-brand/documents/Microsoft-Responsible-AI-Standard-General-Requirements.pdf
- Microsoft's framework for building AI systems responsibly (principles + **Sensitive Uses** overview): https://blogs.microsoft.com/on-the-issues/2022/06/21/microsofts-framework-for-building-ai-systems-responsibly/
- Microsoft principles and approach to responsible AI: https://www.microsoft.com/en-us/ai/principles-and-approach
- Microsoft RAI Impact Assessment Template (the A1 gating artifact): https://blogs.microsoft.com/wp-content/uploads/prod/sites/5/2022/06/Microsoft-RAI-Impact-Assessment-Template.pdf
- Microsoft RAI Impact Assessment Guide: https://blogs.microsoft.com/wp-content/uploads/prod/sites/5/2022/06/Microsoft-RAI-Impact-Assessment-Guide.pdf

**Code-grounded RAPP evidence referenced above:**
- `brainstem.py` — agent `exec_module` + `cls()` (L602–639); `_auto_install` (L741–756); CORS (L36) + `0.0.0.0` bind (≈ L1544): `/Users/kodywildfeuer/.brainstem/neighborhoods/RAPP/rapp_brainstem/brainstem.py`
- `cave_agent.py` — git-invisible streaming via `.git/info/exclude` + self-referential sha256-pin verify (L153–214): `/Users/kodywildfeuer/.brainstem/neighborhoods/RAPP/cave/agents/cave_agent.py`

---

*This memo is DRAFT. It is one of two P0 governance blockers (with the Impact Assessment) to a RAPP RAI sign-off. It documents current state honestly; it does not assert compliance.*
