# RAPP — Responsible AI Impact Assessment

> **Owner:** \<to be assigned\> · **Status:** DRAFT · **Last updated:** 2026-06-27 · **Maps to:** A1, A2, A3, A4, A5, RS1, RS2
>
> This is the **gating artifact** of RAPP's Responsible AI program. It is **adapted from** the public **Microsoft RAI Impact Assessment Template** — whose five official sections are *System Information, Intended Uses, Adverse Impact, Data Requirements,* and *Summary of Impact*; this document reorganizes and extends them for the RAPP engine (it splits stakeholders/harms and fitness/data into their own sections and promotes Sensitive Uses to a standalone section), so its section numbering is RAPP's, not the Template's. Until it is reviewed, owned, and signed, **RAPP does not have an RAI sign-off.** This document states current state honestly: RAPP **does not pass** the Microsoft Responsible AI Standard v2 today. Every gap below is framed as **current state → required → exit criteria**.

---

## How to read this document

This assessment covers the **RAPP engine** across its three tiers — not any single agent built on top of it. Each section reports:

- **Current state** — what is true of the shipping code today (with `file:line` evidence where available).
- **Required** — what the Microsoft RAI Standard v2 / Impact Assessment Template asks for.
- **Exit criteria** — the concrete, testable condition that closes the gap.

Fields that cannot yet be filled responsibly are marked **`TO COMPLETE (owner)`** rather than guessed. This is a **living document**: see [Reassessment trigger](#reassessment-trigger).

**Grounding honesty (carried from the reconciled blueprint).** The Microsoft RAI Standard v2 Goal IDs used here (A1–A5, T1–T3, F1–F3, RS1–RS3, PS1–PS2, I1) are the real June-2022 labels. PS1/PS2/I1 are *compliance-by-reference* goals (Microsoft Privacy Standard, Security Policy, Accessibility Standard) and are not expanded into invented sub-clauses. The **Generative-AI requirements** are Microsoft's GenAI supplement, which is **not** published as a numbered public clause list — they are mapped here **by intent** (content/abuse filtering, Prompt Shields, metaprompt/grounding, pre-release red-teaming, ongoing abuse monitoring, AI-content disclosure, staged release), not to fabricated IDs. Standard sub-clauses (e.g. RS1.4, RS2.1, A5.1) are referenced **by role**, not quoted verbatim, because the official PDF did not extract cleanly in the source pass — flagged honestly rather than overclaimed.

**Sibling documents (this is the spine; the others detail or extend it):**

- [ROADMAP.md](./ROADMAP.md) — the phased P0→P3 remediation plan this assessment schedules.
- [sensitive-uses.md](./sensitive-uses.md) — the A2 Sensitive Uses determination (three triggers × engine + agent classes).
- [INTENDED_USES.md](./INTENDED_USES.md) — the canonical in-scope / out-of-scope / restricted-use register.
- [TRANSPARENCY_NOTE.md](./TRANSPARENCY_NOTE.md) — the T2 Transparency Note for stakeholders.
- [THREAT_MODEL.md](./THREAT_MODEL.md) — the PS2 security threat model and sandbox design.
- [TRACEABILITY.md](./TRACEABILITY.md) — the RAI-to-Standard traceability matrix (control/artifact → Goal ID).

---

## Section 1 — System information & profile

### 1.1 System overview

**RAPP (Rapid Agent Prototype Platform)** is a progressive AI-agent platform that teaches the Microsoft AI stack through three self-contained tiers. The unit assessed here is the **engine** — the substrate that loads, orchestrates, and executes user-authored agents — not any individual agent.

| Tier | Name | What it is | Inference provider | Key file |
|------|------|-----------|--------------------|----------|
| 1 | **Brainstem** (local) | Single-file Flask server on port 7071; auto-discovers `agents/*_agent.py`, calls the LLM with tool definitions, executes agent `.perform()` in-process | **GitHub Copilot API** (Microsoft/GitHub) | `rapp_brainstem/brainstem.py` |
| 2 | **Spinal Cord** (Azure) | Azure Functions + Azure OpenAI, parity with Tier 1 (`function_app.py`) | **Azure OpenAI** | `azuredeploy.json`, `function_app.py` |
| 3 | **Nervous System** (M365) | Copilot Studio connected agents + Teams | **M365 / Copilot Studio** | Power Platform solution |

**Current version:** `0.6.0` (`rapp_brainstem/VERSION`). **Architecture invariant:** Tier-1 `brainstem.py` and Tier-2 `function_app.py` must function identically (*stem/function_app parity*) — therefore **any safety control must land in Tier 1**, not only in the cloud tiers that could lean on the platform natively.

### 1.2 System profile (risk-relevant characteristics)

- **Autonomy:** The engine runs an LLM **tool-calling loop** (up to 3 rounds; `brainstem.py` `run_tool_calls` L854–884, 924–939) that executes agent code **without a human confirmation gate** on execution. The lifecycle `confirm:true` handshake exists but governs only the twin UI offer chips (CONSTITUTION Article IX), **not** the execution loop.
- **Code execution:** Agents are loaded and instantiated via `exec_module` + `cls()` (`brainstem.py` L602–639, exec at L616–618) **in the Flask process that holds the Copilot token** — arbitrary in-process Python with full user privileges, every request.
- **Dependency acquisition:** `_auto_install` (`brainstem.py` L741–756) **automatically pip-installs** packages named by agent code at import time — no allowlist, no pinning, no approval.
- **Code distribution:** The **Cave** streams third-party agents cross-brainstem; `cave_agent.py` (L153–214) makes streamed files **git-invisible** via `.git/info/exclude` and verifies a **self-referential sha256 pin** that travels with the same untrusted index (trust-on-first-use, unsigned, unsandboxed).
- **Network exposure:** Binds **`0.0.0.0`** (`brainstem.py` L1544) with **wildcard CORS** (L36) and **unauthenticated mutating/debug endpoints** (`/agents/import` L1251–1278; `/diagnostics/report` L1413–1523; `/debug/auth`).
- **Model behavior:** **Silent cross-provider model fallback** (`brainstem.py` L802–818) can answer on a different model than configured without telling the caller.
- **Content safety:** RAPP adds **no** content-safety, harm-classification, or prompt-injection-defense layer of its own at the `/chat` seam. (Counterweight: Tier-1 inference passes through the GitHub Copilot API, which applies *Microsoft/GitHub's own upstream* content filtering and abuse monitoring on completions — but that layer is unconfigurable, unevidenced, blind to agent-injected system prompts, and does **not** gate local tool execution, so it cannot satisfy the Standard on RAPP's behalf.)

### 1.3 Existing RAI strengths to build on

Honest counterweights — RAPP is not starting from zero:

- **Article VII no-telemetry / no-accounts** privacy-by-default posture.
- **PUBLIC_BOUNDARY.md** "bones-not-substance" scrub gate for Cave publication.
- **Flight recorder** — a seed for RS3 monitoring and an adverse-impact event channel.
- **Lifecycle `confirm:true` handshake** — the exact pattern to extend to `run_tool_calls` for A5.
- **sha256 pins + `KERNEL_AGENTS`** protection — a hook for real signing.
- **Single `/chat` chokepoint** — one place to retrofit safety middleware.
- **rappid lineage keypair** — a provenance/signing key already in the ecosystem.

### 1.4 Accountable owner & sign-off

| Role | Name | Status |
|------|------|--------|
| Accountable owner (engine RAI) | **`TO COMPLETE (owner)`** | unassigned |
| Reviewer / RAI approver | **`TO COMPLETE (owner)`** | unassigned |
| Security sign-off (PS2 / threat model) | **`TO COMPLETE (owner)`** | unassigned |
| Last review date | — | **never reviewed** |

> **Required:** A1 requires a named accountable owner and a dated, reviewed Impact Assessment wired into the release ritual. **Exit criteria:** this document is reviewed, dated, owned, and referenced as a release gate in `CONSTITUTION.md`.

---

## Section 2 — Intended uses

The canonical register lives in [INTENDED_USES.md](./INTENDED_USES.md); summarized here for the assessment.

### 2.1 In-scope intended uses

1. Single-developer, **local-first** prototyping, learning, and testing of AI agents on the operator's own machine (Tier 1).
2. Rapid authoring and iteration of **user-dropped Python agents the operator wrote and trusts**.
3. **Teaching** the Microsoft AI stack progressively across the three tiers.
4. Sharing **non-sensitive agent "bones"** (structure, not substance) through the public Cave under the `PUBLIC_BOUNDARY` scrub gate.

### 2.2 Out-of-scope uses

- **Any consequential / high-stakes decision about a person** (hiring, lending/credit, healthcare, housing, legal status, benefits) — RAPP output is unvalidated LLM generation with **no fitness-for-purpose evidence**.
- **Production / multi-tenant / untrusted-network deployment** of the Tier-1 brainstem as shipped (it executes arbitrary in-process code and binds `0.0.0.0`).
- **Reliance on RAPP output as accurate, grounded, or safety-filtered** without independent human verification.
- **Running third-party / Cave-streamed agent code as if reviewed or trusted** — it is unsigned, git-invisible, and unsandboxed.

### 2.3 Restricted uses (require review-before-deploy)

- Any agent making **allocative decisions about people (F2)** without a documented fairness review + Sensitive-Use screen.
- **Companion / digital-twin / "Holographic Moments"** agents fostering emotional reliance, giving medical/financial guidance, or controlling physical devices — **Sensitive-Use trigger 2**.
- **Profiling / surveillance / biometric / content-moderation** agents — **Sensitive-Use trigger 3**.
- The **digital-twin/proxy persona that speaks AS the owner in first person** — restricted to contexts carrying a non-overridable *"AI projection of \<owner\>, not \<owner\>"* disclosure (T3).
- **Auto-pip-install of untrusted-derived package names** and **non-loopback network binding** — restricted to explicit opt-in with consent.

> Full reasoning and the three-trigger analysis are in [sensitive-uses.md](./sensitive-uses.md).

---

## Section 3 — Stakeholders, potential benefits & potential harms

| Stakeholder | Potential benefits | Potential harms |
|-------------|--------------------|-----------------|
| **Local operator / developer** (primary) | Fast learning loop; no API keys; agents reload without restart; progressive path to the MS stack | Their own machine is the blast radius for RCE via auto-install + unsandboxed agents; plaintext long-lived credentials at rest; prompts silently egress to Copilot |
| **People other agents act about** (subjects) | — | Consequential harms if a RAPP-built agent makes allocative/medical/profiling decisions without validation (see §6 Sensitive Uses) |
| **Peers receiving the twin/proxy** | Faster collaboration | **Human impersonation** — the twin can speak in first person as the owner without an AI-projection marker (T3) |
| **Cave publishers & consumers** | Share/reuse agent structure | Supply-chain compromise — unsigned, git-invisible, TOFU code execution |
| **Anyone on the local network** | — | `0.0.0.0` + wildcard CORS + unauthenticated mutating endpoints → remote agent import/exec, token-prefix leak via `/debug/auth` |
| **People whose data lands in memory/diagnostics** | — | Free-text PII exfiltrated to a **world-readable** repo via `/diagnostics/report` (L1413–1523) |
| **Microsoft / GitHub (platform)** | Adoption on-ramp to Agent 365 | Reputational exposure if RAPP ships under the MS-stack banner without RAI controls |

**Most significant adverse impacts (A2):**

1. **Arbitrary code execution & supply-chain compromise** (compounding chain): Cave delivers untrusted code → auto-install executes it → no sandbox contains it → no auth stops a LAN trigger. *This chain — not any single link — is the blocker.* (PS2, P0)
2. **No owned safety layer / no prompt-injection defense** on a system-prompt surface fed by third-party streamed text; a successful injection escalates to local code execution. (RS1/GenAI, P0)
3. **Undisclosed data egress** to GitHub/Microsoft Copilot while "local-first" copy implies on-device inference (PS1/T3, P0); and **public PII exfil** via diagnostics (PS1, P0).
4. **Sensitive-Use exposure of RAPP-built agents** with no platform screening path (A2, P0).

---

## Section 4 — Fitness-for-purpose & data

### 4.1 Fitness-for-purpose statement (A3)

- **Current state:** **None exists.** RAPP output is **unvalidated LLM generation**. There is no validity claim, no generalizability bound, and **Cave-streamed agents are not marked as unverified/community-sourced**.
- **Required (A3):** a fitness-for-purpose statement **per engine intended use** stating the validity claim, that outputs are unvalidated LLM generation, and generalizability limits — plus a visible "unverified" marker on community agents.
- **Exit criteria:** an A3 fit-for-purpose write-up per intended use is committed; Cave-streamed agents are visibly marked unverified. **Status:** `TO COMPLETE (owner)`.

### 4.2 Data inventory

#### 4.2.1 Data sent off-device (egress to GitHub / Microsoft Copilot, Tier 1)

Composed into the system prompt + request on **every `/chat`** (`brainstem.py` soul/system_context/memory injection L906–919):

| Data | Source | Sensitivity | Notes |
|------|--------|-------------|-------|
| User conversation input | live request | **may contain PII / secrets** | unfiltered |
| Conversation history | session | may contain PII | full history replayed |
| `soul.md` system prompt | local file | low | persona machinery |
| Agent `system_context()` text | loaded agents (incl. **untrusted Cave agents**) | **untrusted** | injected as system content; an injection vector |
| Injected `<memory>` context | `.brainstem_data` | **may contain PII**, untrusted | memory-poisoning vector |
| Tool-call inputs/outputs | agent execution | varies | untrusted |

> **Destination:** GitHub Copilot API (Microsoft/GitHub) for Tier 1; Azure OpenAI for Tier 2; M365/Copilot Studio for Tier 3. **No in-product disclosure of this egress exists today** — see §5 PS1 finding and the [Data Handling note required in ROADMAP P0](./ROADMAP.md). Link to **GitHub Copilot data terms**: `TO COMPLETE (owner)`.

#### 4.2.2 Local data stores at rest

| Store | Contents | Sensitivity | Current protection |
|-------|----------|-------------|--------------------|
| `.copilot_token` | GitHub/Copilot token **incl. refresh_token** | **CRITICAL credential** | plaintext (`brainstem.py` L223–235) |
| `.copilot_session` | short-lived Copilot API token | **credential** | plaintext, auto-refresh |
| `.copilot_pending` | device-code OAuth in flight | credential | plaintext |
| `.brainstem_book.json` | flight-recorder / book state | may contain PII | plaintext; attached to diagnostics by default |
| `.brainstem_data/` | memory writes, agent state | **may contain PII** | plaintext, no retention/TTL |

- **Current state:** long-lived credentials stored in **plaintext** and readable by any in-process (unsandboxed) agent; **no PII detection, retention, consent, or view/export/delete** on memory or telemetry.
- **Required (PS1/PS2/A4):** OS keychain/DPAPI/libsecret (or `chmod 600` + optional at-rest encryption; the team already encrypts `voice.zip`), `refresh_token` opt-in, a PII-handling module on memory/telemetry/Cave-push, and a memory data-governance policy (categories, purpose, retention/TTL, consent gate, view/export/delete).
- **Exit criteria:** credential files OS-protected and unreadable by a sandboxed agent; PII handling runs on memory + telemetry + Cave-push as **blocking CI**; memory governance + view/export/delete + retention pruning exist. **Status:** `TO COMPLETE (owner)`.

### 4.3 RS1.4 — Operational ranges (reliability envelope)

*Referenced by role; RS1.4 asks for the conditions under which the system is designed to operate.* **Current state: undocumented.** Draft envelope to be ratified:

| Dimension | Designed-for range | Out-of-range (unsupported) |
|-----------|--------------------|----------------------------|
| Operators | **single local operator** on their own machine | multi-tenant / shared / untrusted users |
| Network | **loopback / trusted single-host** | `0.0.0.0` LAN/WAN exposure (current default — out of intended range) |
| Agent provenance | **operator-authored, trusted** | unsigned Cave-streamed / third-party code (current capability — out of intended range) |
| Decision stakes | prototyping, learning, **non-consequential** | any consequential decision about a person |
| Tool side effects | read-mostly / reversible | destructive/irreversible without confirmation (no gate today) |
| Model | configured `GITHUB_MODEL` | silent fallback to another provider/model (current behavior) |

> The gap between "designed-for" and current default behavior (network bind, agent provenance) is itself a P0 finding. **Status:** envelope draft above; ratification `TO COMPLETE (owner)`.

### 4.4 RS2.1 — Predictable-failure catalog

*Referenced by role; RS2.1 asks for foreseeable failure modes, their mitigations, and residual risk.* **Current state: no catalog exists.** Initial catalog:

| # | Predictable failure | Consequence | Current mitigation | Residual risk |
|---|---------------------|-------------|--------------------|---------------|
| FM1 | **Wrong / destructive tool call** in the 3-round loop | irreversible local side effect | **none** (no confirm-before-execute on `run_tool_calls`) | **HIGH** → A5 P1 (P0 once a side-effecting agent ships in default set) |
| FM2 | **Prompt injection** (direct, or indirect via memory / agent `system_context()` / Cave text) | hijacked behavior escalating to **local code execution** via tool loop + auto-install | **none** (no Prompt Shields / spotlighting; `soul.md` not a delimited-trust metaprompt) | **HIGH** → RS1/GenAI P0 |
| FM3 | **Silent model fallback** | answer attributed to wrong model; changed safety/fairness profile undisclosed | none (L802–818 falls back silently) | **MEDIUM** → T2/Fairness |
| FM4 | **Install failure / dependency confusion / typosquat** via `_auto_install` | RCE or broken state | none (no allowlist/pinning/approval) | **HIGH** → PS2 P0 |
| FM5 | **Cave supply-chain tamper** (matching-but-untrusted pin) | untrusted code executed as trusted | self-referential sha256 only; git-invisible | **HIGH** → PS2 P0 |
| FM6 | **Unauthenticated remote trigger** (foreign Origin / LAN) | remote agent import/exec; token-prefix leak | none (`0.0.0.0` + wildcard CORS + open `/debug/auth`) | **HIGH** → PS2 P0 |
| FM7 | **PII exfil** via `/diagnostics/report` | free-text PII to world-readable repo | partial scrub only (L1413–1523) | **HIGH** → PS1 P0 |

> This catalog is the seed of RS2's failure register and feeds the [ROADMAP](./ROADMAP.md) and [THREAT_MODEL.md](./THREAT_MODEL.md). **Status:** to be completed and accepted by owner.

---

## Section 5 — Risk mitigations & impact-on-stakeholders summary

Harms → mitigations → Goal IDs. Severity: **P0** = blocks RAI sign-off; **P1** = hardening; **P2** = scale; full plan in [ROADMAP.md](./ROADMAP.md).

| # | Harm (current state) | Required mitigation | Exit criteria | Goal | Severity |
|---|----------------------|---------------------|---------------|------|----------|
| 1 | **No RAI Impact Assessment** — the A1 gating artifact is absent | This document, completed/owned/dated and wired as a release gate in CONSTITUTION | Reviewed dated assessment, all 5 sections, owner + reassessment trigger + CONSTITUTION cross-ref | **A1** | **P0** |
| 2 | **No Sensitive-Use determination / screen / reporting path** | [sensitive-uses.md](./sensitive-uses.md) + per-agent self-screen field + escalation path | Memo published; required screening field; path exercised on companion/twin + T2/T3 deploy agents | **A2** | **P0** |
| 3 | **No content-safety layer** on `/chat` (input/injected/output) | Pluggable middleware at the `call_copilot` seam; no-op T1 default, Azure AI Content Safety default-on T2/T3 | Classifies input+output across harm categories, emits safety events, test-covered, default-on T2/T3 | **RS1** / GenAI | **P0** |
| 4 | **No Prompt Shields / injection defense**; `soul.md` not a trust-delimited metaprompt | Prompt Shields + spotlighting; tag agent/memory/tool/Cave text **untrusted**; harden `soul.md` | Direct + indirect (memory-poisoning) red-team corpus blocked/quarantined | **RS1** / GenAI | **P0** |
| 5 | **No sandbox** — agent code runs in-process with the token | Privilege-drop subprocess / container / WASM-RestrictedPython; deny token/.env/network by default | Red-team test: sandboxed agent cannot read token/.env or make un-allowlisted calls | **PS2** | **P0** |
| 6 | **Auto pip-install** of attacker-derived names (RCE) | Opt-in install against hash-pinned allowlist into isolated venv; refuse unknown names | Test: random package name rejected, not installed | **PS2** | **P0** |
| 7 | **Cave streaming** git-invisible, unsigned, TOFU | Sign with rappid keypair vs out-of-band trust root; pin commit; remove git-invisibility; consent + static scan | Tampered/untrusted-pin file refused; streamed files visible + logged; consent on first load | **PS2** / A2 | **P0** |
| 8 | **`0.0.0.0` + wildcard CORS + unauth mutating/debug routes** | Default loopback; scope CORS; local auth token + CSRF on mutating routes; remove/gate `/debug/auth` | Foreign Origin cannot import/run an agent; `/debug/auth` leaks no token material | **PS2** | **P0** |
| 9 | **Undisclosed Copilot egress**; "local-first" copy misleads | Data Handling note + first-run disclosure + `/health` block; correct copy; `ai_disclosure` in `/chat` envelope | Egress + local stores disclosed; every `/chat` carries `ai_disclosure`; twin carries projection marker | **PS1** / T3 | **P0** |
| 10 | **`/diagnostics/report` public PII exfil** (L1413–1523) | Private/triage default; PII redaction; payload preview + public-warning confirm; allowlist scrub; deletion path | Reports non-public by default; redaction + preview + confirmation implemented | **PS1** | **P0** |
| 11 | **No human-in-the-loop on agent execution** | Extend `confirm:true` to `run_tool_calls`; per-agent impact flag; kill-switch; dry-run; audit log | No side-effecting agent runs without recorded confirmation; operator can halt the loop | **A5** | **P1** (→P0 if side-effecting agent enters default set) |
| 12 | **Plaintext credentials; no PII/retention governance** | OS keychain / `chmod 600` + encryption; `refresh_token` opt-in; PII module; memory governance + view/export/delete | Credentials OS-protected; PII handling as blocking CI; governance + retention pruning | **PS2** / PS1 / A4 | **P1** |
| 13 | **No red-team harness / reliability envelope / abuse monitoring** | PyRIT / Azure AI Foundry Red Teaming Agent over `/chat`; RS1.4 ranges + RS2.1 catalog (§4); T2/T3 abuse monitoring | ASR report wired into release + Cave-promotion; catalog accepted; safety events queryable | **RS1/RS2/RS3** | **P1** |
| 14 | **No oversight roles / adverse-impact register / fit-for-purpose** | A5.1 oversight table; adverse-impact event class + runbook; A3 statement | Oversight doc; runbook referenced from CONSTITUTION; fit-for-purpose per intended use | **A2/A3/A5** | **P1** |
| 15 | **No groundedness / protected-material check** on memory-grounded output | Optional Azure AI Content Safety groundedness + protected-material filters (off by default offline T1) | Memory answers scorable; ungrounded segments flagged; documented optional | **RS1** / GenAI | **P2** |
| 16 | **Ungoverned RAPP-added fairness surfaces** (injection, silent model switch) | Author fairness guidance; disclose served model incl. fallback; QoS/stereotype spot-check; flag allocative agents | Fairness reliance documented; served model disclosed; spot-check exists | **F1/F2/F3** | **P2** |
| 17 | **No accessibility audit / WCAG conformance** for `index.html` | WCAG 2.1 AA audit (axe/Lighthouse + SR/keyboard); fix modal focus-trap, labels, contrast, skip-link | Recorded audit shows AA (or tracked backlog); conformance statement committed | **I1** | **P2** |
| 18 | **No agent provenance manifest; silent fallback undisclosed** | In-product provenance manifest (source/author/hash/streamed flag); report actually-served model per response | Manifest distinguishes local vs streamed; each `/chat` reports model + fallback | **T1/T2** | **P2** |

### 5.1 Impact-on-stakeholders summary

In its **declared intended use** (a single developer's local sandbox), the bare engine makes no consequential decision about a person, so its first-order stakeholder is the **operator themselves** — and the dominant near-term harm is **to the operator's own machine and credentials** via the compounding RCE/supply-chain chain (harms 5–8). The moment RAPP is used outside that envelope — exposed on a network, running Cave code as trusted, or used to **build agents that decide about people** — the impact surface widens to third parties, and the **Sensitive-Use exposure** (harm 2, detailed in [sensitive-uses.md](./sensitive-uses.md)) becomes the largest RAI liability. The honest posture: **the four runtime-security P0s + the safety/disclosure P0s are the only true blockers; everything in P1–P3 is hardening, scale, and polish that these P0 artifacts will themselves schedule.**

---

## Section 6 — Sensitive Uses determination (summary; full memo in sibling)

Two-level determination, defensible and the single largest RAI exposure:

1. **RAPP-as-engine** — **NOT** itself a Microsoft Sensitive Use, **but only by intended-use boundary, never by design control.** The clean result rests entirely on the narrow framing; the engine has **zero technical control** preventing it from building/running triggering agents and **actively lowers the barrier** (in-process Python + auto-install + git-invisible Cave streaming + no safety layer). Under Microsoft's **foreseeable-misuse doctrine** the platform owner must still (a) complete this platform-level Impact Assessment, (b) declare Restricted Uses, and (c) run a platform-level Sensitive-Uses consultation. **Verdict: out of scope by boundary, IN scope by foreseeable misuse.**
2. **RAPP-built agents** — plausible agents grounded in the project's own ecosystem trigger **all three**: resume/lending → **trigger 1** (employment/credit); companion/twin/"Holographic Moments" emotional-reliance, device-control, or medical/financial guidance → **trigger 2** (psychological/physical injury); profiling/surveillance/content-moderation → **trigger 3** (human rights). The platform cannot centrally certify these, so the obligation is **pushed down to each builder** via a mandatory per-agent Sensitive-Use self-screen + escalation path, exercised **before deployment**.

> Today **neither** the platform Impact Assessment nor the per-agent screen exists — which is why this assessment **and** [sensitive-uses.md](./sensitive-uses.md) are **P0 blockers** for any RAI sign-off.

---

## Reassessment trigger

This is a **living document**. It must be re-reviewed and re-dated when **any** of the following occur:

- A **VERSION bump** in `rapp_brainstem/VERSION` (tie the review to the release ritual).
- Any change to the **execution, auth, network-binding, or Cave-streaming surface** (the surfaces that carry the P0 harms).
- **Any side-effecting agent** entering the default agent set (escalates harm 11 / A5 to P0).
- **At least annually**, regardless of change.

| Review cycle | Date | Reviewer | Outcome |
|--------------|------|----------|---------|
| 1 | `TO COMPLETE (owner)` | `TO COMPLETE (owner)` | not yet reviewed |

---

## Citations

**Microsoft Responsible AI Standard & Impact Assessment Template:**

- Microsoft Responsible AI Standard v2, General Requirements (six principles + 17 Goals; incl. RS1.4 operational ranges, RS2.1 predictable-failure catalog) — https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/microsoft/final/en-us/microsoft-brand/documents/Microsoft-Responsible-AI-Standard-General-Requirements.pdf
- Microsoft RAI Impact Assessment Template (the A1 gating artifact, five sections) — https://blogs.microsoft.com/wp-content/uploads/prod/sites/5/2022/06/Microsoft-RAI-Impact-Assessment-Template.pdf
- Microsoft RAI Impact Assessment Guide — https://blogs.microsoft.com/wp-content/uploads/prod/sites/5/2022/06/Microsoft-RAI-Impact-Assessment-Guide.pdf
- Microsoft's framework for building AI systems responsibly (principles + Sensitive Uses overview) — https://blogs.microsoft.com/on-the-issues/2022/06/21/microsofts-framework-for-building-ai-systems-responsibly/
- Microsoft principles and approach to responsible AI — https://www.microsoft.com/en-us/ai/principles-and-approach

**Operationalization referenced in the roadmap (T2/T3 + GenAI supplement, mapped by intent):**

- Azure OpenAI Transparency Note — https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/openai/transparency-note
- Azure AI Content Safety overview — https://learn.microsoft.com/en-us/azure/ai-services/content-safety/overview
- Prompt Shields / jailbreak + indirect-injection detection — https://learn.microsoft.com/en-us/azure/ai-services/content-safety/concepts/jailbreak-detection
- Prompt Shields GA + Spotlighting — https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/general-availability-of-prompt-shields-in-azure-ai-content-safety-and-azure-open/4235560
- Groundedness detection — https://learn.microsoft.com/en-us/azure/ai-services/content-safety/concepts/groundedness
- Azure AI Foundry — AI Red Teaming Agent — https://learn.microsoft.com/en-us/azure/foundry/concepts/ai-red-teaming-agent
- Microsoft PyRIT — https://www.microsoft.com/en-us/security/blog/2024/02/22/announcing-microsofts-open-automation-framework-to-red-team-generative-ai-systems/
- Azure OpenAI Risks & Safety monitoring — https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/risks-safety-monitor

**Code-grounded RAPP evidence:**

- `brainstem.py` — exec_module+cls() L602–639 (exec L616–618); `_auto_install` L741–756; `run_tool_calls` + 3-round loop L854–884, 924–939; soul/system_context/memory injection L906–919; silent model fallback L802–818; CORS L36 + `0.0.0.0` bind L1544; unauthenticated `/agents/import` L1251–1278; plaintext token store L223–235; `/diagnostics/report` public-issue path + partial scrub L1413–1523 — `/Users/kodywildfeuer/.brainstem/neighborhoods/RAPP/rapp_brainstem/brainstem.py`
- `cave_agent.py` — git-invisible streaming via `.git/info/exclude` + self-referential sha256-pin verify L153–214 — `/Users/kodywildfeuer/.brainstem/neighborhoods/RAPP/cave/agents/cave_agent.py`
- Governance evidence — `CONSTITUTION.md` (Art. VII no-telemetry; Art. IX Twin-Offers-User-Accepts; Art. XXX human-maintainer merge; Art. XXXIII kernel-DNA approval; lifecycle handshake) and `PUBLIC_BOUNDARY.md` bones-not-substance scrub — `/Users/kodywildfeuer/.brainstem/neighborhoods/RAPP/rapp_brainstem/CONSTITUTION.md`, `/Users/kodywildfeuer/.brainstem/neighborhoods/RAPP/cave/specs/PUBLIC_BOUNDARY.md`
