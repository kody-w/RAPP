# RAPP — Transparency Note

> **Owner:** \<to be assigned\> · **Status:** DRAFT · **Last updated:** 2026-06-27 · **Maps to:** T1, T2, T3 (with cross-references to A3, RS1, RS2, PS1, PS2)

---

## About this document

Microsoft publishes [Transparency Notes](https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/openai/transparency-note) to help people understand how an AI technology works, the choices system owners can make that influence behavior, and the importance of thinking about the whole system — including people, data, and the surrounding environment. This document follows that structure for **RAPP (Rapid Agent Prototype Platform)**.

> **HONEST POSTURE — read first.** RAPP does **not** currently meet the Microsoft Responsible AI Standard v2. This Transparency Note is itself one of the P0 governance artifacts required to reach a defensible posture. It is published **before** the technical mitigations it describes are in place, so that anyone evaluating, deploying, or extending RAPP understands the real limitations **today**. Where this note says "no safety layer," "executes unreviewed code," or "sends your conversation to GitHub/Microsoft," those statements describe the **current shipped behavior**, not an aspiration. See the [Impact Assessment](./impact-assessment.md) and [Roadmap](./ROADMAP.md) for the path from current state to required state.

This Transparency Note covers all three RAPP tiers. It carries an owner and a last-updated date, and is subject to review on every `VERSION` bump and at least annually (see [Roadmap](./ROADMAP.md), Phase P3).

**Grounding caveat.** This note maps RAPP to the publicly documented Microsoft Responsible AI Standard v2 (six principles; Goals A1–A5, T1–T3, F1–F3, RS1–RS3, PS1–PS2, I1) and to Microsoft's Generative AI requirements. The GenAI requirements are **not** published as a numbered public clause list; references to them here are by intent (content/abuse filtering, Prompt Shields, metaprompt & grounding, pre-release red-teaming, abuse monitoring, AI-content disclosure), mapped to the publicly documented Azure AI Foundry operationalization. Standard sub-clauses (e.g., RS1.4, A5.1) are referenced by role, not quoted verbatim, because the official Standard PDF did not extract cleanly in sourcing.

---

## What is RAPP?

RAPP is a **local-first AI agent platform** that teaches the Microsoft AI stack through three progressive tiers. Its philosophy is *"engine, not experience"* — it is developer infrastructure for prototyping AI agents, not a finished consumer product.

At its core, RAPP is a thin server that:
1. Loads a system prompt (`soul.md`),
2. Auto-discovers user-authored Python "agents" from an `agents/` directory,
3. Sends the conversation plus tool definitions to a large language model,
4. Executes any tool calls the model requests by running the corresponding agent's Python code, and
5. Loops (up to three rounds) before returning a reply.

| Tier | Name | What it is | Where inference happens |
|------|------|-----------|-------------------------|
| **1** | **Brainstem** (local) | A single-file Flask server (`brainstem.py`, ~1100 lines) on `localhost:7071` | **GitHub Copilot API** (Microsoft/GitHub-hosted) |
| **2** | **Spinal Cord** (Azure) | Azure Functions + Azure OpenAI | **Azure OpenAI** (your Azure tenant) |
| **3** | **Nervous System** (M365) | Copilot Studio + Microsoft Teams | **Microsoft 365 / Copilot Studio** |

Each tier is self-contained; users advance when they choose to. **RAPP itself is not a model.** It orchestrates third-party foundation models (GitHub Copilot, Azure OpenAI, Microsoft 365 Copilot) and runs user-written code around them. The responsible-AI characteristics of the underlying models are governed by those providers' own Transparency Notes; this note covers the **layer RAPP adds**.

---

## Capabilities

RAPP provides:

- **Conversational orchestration** — a single `/chat` endpoint that composes `soul.md`, conversation history, per-agent `system_context()` text, and (optionally) injected `<memory>` into a system prompt, then calls the configured model with tool definitions (`brainstem.py` system-prompt assembly L906–919).
- **Auto-discovered, hot-reloaded agents** — any file matching `agents/*_agent.py` is loaded fresh on every request and exposed to the model as a callable tool. Agents are ordinary Python classes that run **in-process** (`exec_module` + class instantiation, `brainstem.py` L616–618, L602–639). Edit and test without restart.
- **Tool-calling loop** — the model can invoke agents, receive their string output, and continue, up to three rounds (`run_tool_calls`, L854–884, L924–939).
- **Local memory** — `ManageMemory` / `ContextMemory` agents persist and re-inject context across turns via a local JSON store under `~/.brainstem/`.
- **Provider abstraction with fallback** — if the configured model is unavailable, RAPP **silently falls back** to an alternate provider/model (e.g., across `gpt-4o` / `claude-sonnet-4` / `gpt-3.5-turbo`) without telling the user which model actually answered (`brainstem.py` L802–818).
- **Community sharing via the Cave** — agents can be shared as structural "bones" (not substance) through a public Cave, gated by the `PUBLIC_BOUNDARY.md` scrub. Cave-streamed agents are fetched and executed locally.
- **Progressive deployment** — helper agents promote a prototype from Tier 1 to Tier 2 (Azure) and Tier 3 (M365/Copilot Studio).
- **A built-in web UI** (`index.html`) and a **headless HTTP API** (the primary integration surface), plus an optional voice mode.

RAPP's deliberate **strengths** worth noting: no telemetry and no accounts by default (CONSTITUTION Article VII), a single `/chat` chokepoint (one place to add safety), a `confirm:true` lifecycle handshake (CONSTITUTION Article IX) that is the seed for human-in-the-loop control, sha256 pins and a protected kernel-agent set, and the `rappid` lineage keypair already present in the ecosystem (a hook for real signing).

---

## Intended uses

RAPP is intended for **single-developer, local-first prototyping, learning, and testing of AI agents on the operator's own machine**, and for teaching the Microsoft AI stack progressively across the three tiers.

In-scope uses:

- **Local prototyping and iteration** of AI agents that the operator themselves wrote and trusts (Tier 1 brainstem).
- **Rapid authoring** of user-dropped Python agents for experimentation and learning.
- **Teaching the Microsoft AI stack** progressively across Tier 1 (local), Tier 2 (Azure Functions / Azure OpenAI), and Tier 3 (M365 / Copilot Studio).
- **Sharing non-sensitive agent "bones"** (structure, not substance) through the public Cave under the `PUBLIC_BOUNDARY` scrub gate.

These intended uses assume a **trusted single operator on their own hardware**, running **agents they wrote or have reviewed**, with **independent human verification** of any output before it is relied upon.

---

## Out-of-scope uses

The following uses are **not supported** and are unsafe with RAPP **as shipped today**. Some are absolute (out of scope by design); others are **restricted** (permitted only with the documented governance and consent gates described in [sensitive-uses.md](./sensitive-uses.md) and the [Impact Assessment](./impact-assessment.md)).

**Out of scope — do not use RAPP for:**

- **Any consequential or high-stakes decision about a person** — hiring, lending/credit, healthcare, housing, legal status, benefits eligibility. RAPP output is **unvalidated LLM generation with no fitness-for-purpose evidence**.
- **Production, multi-tenant, or untrusted-network deployment** of the Tier-1 brainstem as shipped. It executes arbitrary in-process Python and binds `0.0.0.0` (see Limitations).
- **Relying on RAPP output as accurate, grounded, or safety-filtered** without independent human verification. **RAPP adds no content-safety or prompt-shield layer of its own.**
- **Running third-party / Cave-streamed agent code as if it were reviewed or trusted.** It is unsigned, git-invisible, and unsandboxed.

**Restricted — only with documented review, consent, and the Sensitive-Use screen ([sensitive-uses.md](./sensitive-uses.md)):**

- Building or deploying any agent that makes **allocative decisions about people** (Goal F2) without a documented fairness review and Sensitive-Use screening.
- **Companion / digital-twin / "Holographic Moments" agents** that foster emotional reliance, give medical/financial guidance, or control physical devices (Sensitive-Use trigger 2 — physical/psychological injury).
- **Profiling, surveillance, biometric, or content-moderation agents** (Sensitive-Use trigger 3 — human rights).
- The **digital-twin / proxy persona that "speaks AS the owner in first person"** to peers — restricted to contexts carrying a non-overridable *"AI projection of \<owner\>, not \<owner\>"* disclosure (Tier 3).
- **Auto-pip-install** of packages whose names derive from untrusted agent code, and **non-loopback network binding** — restricted to explicit opt-in with consent.

---

## Limitations

These are the **current, real limitations** of RAPP. They are stated plainly because most are not yet mitigated. Each maps to a Goal in the Microsoft RAI Standard and to a remediation phase in the [Roadmap](./ROADMAP.md). See also the [Threat Model](./THREAT_MODEL.md).

### 1. No content-safety or prompt-shield layer of RAPP's own (RS1 / GenAI filtering) — **P0**
RAPP applies **no** harm-classification on user input, on injected context, or on model output, and **no** jailbreak or indirect-prompt-injection detection over its system-prompt surface. Tier-1 inference does run through the GitHub Copilot API, which applies Microsoft/GitHub's **own** upstream content filtering and abuse monitoring on the completion — so RAPP is *not* at literal zero protection — but that layer is **upstream, unconfigurable, unevidenced, blind to agent-injected system prompts, and does not gate local tool execution**. It cannot satisfy the Standard on RAPP's behalf. A successful prompt injection is especially dangerous here because it can **escalate to local code execution** via the tool loop plus auto-install.

### 2. Auto-pip-install of unreviewed packages at agent import (PS2) — **P0**
When an agent imports a missing package, RAPP **automatically `pip install`s it** (`_auto_install`, `brainstem.py` L741–756). Package names can derive from untrusted agent code, creating remote-code-execution, dependency-confusion, and typosquatting exposure. There is no allowlist, hash pinning, or approval step today.

### 3. Cave-streamed, unsigned, git-invisible third-party code (PS2 + A2) — **P0**
Agents streamed from the public Cave are executed locally **without cryptographic provenance**. They are made **invisible to git** via `.git/info/exclude` and verified only against a **self-referential sha256 pin from the same untrusted index** (`cave_agent.py` L153–214). This is trust-on-first-use with no out-of-band trust root and no static safety scan before execution.

### 4. No sandbox — arbitrary agent code runs in-process with full user privileges (PS2) — **P0**
Every `/chat` request can run agent Python **in the same process that holds your Copilot credentials**, with full access to your files, environment, and network (`exec_module` + `cls()`, L602–639). A malicious or buggy agent can read `.copilot_token` / `.copilot_session` / `.env` and make arbitrary outbound calls. The blast radius is your entire user account.

### 5. Network exposure: `0.0.0.0` bind + wildcard CORS + unauthenticated mutating/debug endpoints (PS2) — **P0**
The server binds `0.0.0.0` (`brainstem.py` L1544) with wildcard CORS (`L36`), and state-changing routes (e.g. `/agents/import`, `/agents` DELETE, `/models/set`) plus a `/debug/auth` endpoint are reachable without local authentication or CSRF protection. On an untrusted LAN this allows a remote party to import and run an agent.

### 6. Your conversation is sent to GitHub / Microsoft Copilot — "local-first" can mislead (PS1 / T3) — **P0**
Despite "local-first / lives on your hardware" framing, **Tier-1 inference does not happen on your device.** Your conversation, history, `soul.md`, each agent's `system_context()`, and any injected `<memory>` are sent to the **GitHub Copilot API (Microsoft/GitHub)** for completion. Tier 2 sends to **Azure OpenAI**; Tier 3 to **Microsoft 365 Copilot**. See *Data, privacy & security* below.

### 7. Silent model fallback across providers (T1 / T2 / RS2 / F1) — **P1/P2**
If the configured model is unavailable, RAPP silently substitutes another provider/model and **does not report which model actually answered** (L802–818). This changes accuracy, safety, and fairness characteristics without disclosure.

### 8. LLM hallucination and unvalidated output (A3 / RS2) — inherent
Like all LLM-backed systems, RAPP can produce **confident, fluent, and wrong** output. RAPP performs **no groundedness checking** on memory-grounded answers and makes **no fitness-for-purpose claim**. All output is unvalidated generation and must be independently verified before reliance.

### 9. Public diagnostics path can exfiltrate free-text PII (PS1) — **P0**
The `/diagnostics/report` path (`brainstem.py` L1413–1523) can post a free-text user description plus context to a **world-readable** repository with only a partial scrub. Personal information typed into a report may become public.

### 10. No human-in-the-loop stop control over agent execution (A5) — **P1**
The `confirm:true` lifecycle handshake (CONSTITUTION Article IX) governs only twin-UI offer chips, **not** the `run_tool_calls` execution loop. There is currently no confirm-before-execute, kill-switch, or dry-run for side-effecting tools. This is held at P1 *only* because RAPP ships a minimal default agent set on a single operator's machine — it **escalates to P0** the moment any side-effecting agent (T2/T3 deploy, Cave, file/git) lands in the default set.

### 11. No accessibility conformance for the web UI (I1) — **P2**
`index.html` has not passed a WCAG audit (no modal focus-trapping, sparse ARIA/labels). The headless API and beginner-first defaults are the recommended path until remediation lands.

### 12. No pre-release red-team harness or defined reliability envelope (RS1.4 / RS2.1 / RS3) — **P1**
There is no repeatable adversarial evaluation gating releases or Cave promotion, and no documented operational-range / predictable-failure catalog.

---

## How to deploy and use RAPP responsibly

Until the [Roadmap](./ROADMAP.md) P0 mitigations land, treat RAPP as a **trusted-operator local sandbox** and follow these practices:

1. **Keep it loopback and local.** Do not expose the Tier-1 server on an untrusted network. If you must bind beyond `127.0.0.1`, treat it as a deliberate, consented exception and firewall it.
2. **Only run agents you wrote or have read.** Treat every agent — especially Cave-streamed ones — as **untrusted code that runs as you**. Read it before it runs. Do not auto-load community agents into a machine with secrets you care about.
3. **Independently verify all output.** RAPP applies no safety filter of its own and the model can hallucinate. Never rely on output for a consequential decision about a person — that use is out of scope.
4. **Assume your conversation leaves the device.** Do not enter data into RAPP that you would not send to GitHub Copilot / Azure OpenAI / Microsoft 365 Copilot. Review the relevant provider data terms.
5. **Do not build Sensitive-Use agents without the screen.** If your agent could affect a person's opportunities, safety, or rights, complete the per-agent [Sensitive-Use screening](./sensitive-uses.md) and escalation **before** deploying.
6. **Disclose AI interaction.** If you put RAPP in front of other people — especially via the twin/proxy persona — ensure it is clearly identified as AI, and never let it speak *as* a human without the *"AI projection of \<owner\>"* marker.
7. **Watch the diagnostics path.** Do not submit `/diagnostics/report` with personal data until the private-default + redaction fix lands; preview any payload.
8. **Prefer the platform tiers for anything beyond a sandbox.** Tier 2/3 inherit Azure / M365 platform safety, abuse monitoring, and identity controls that Tier 1 does not have. Do not promote a prototype to production without the controls in the [Roadmap](./ROADMAP.md) and the [Impact Assessment](./impact-assessment.md).

For the per-tier responsible-deployment requirements and the current-state → required → exit-criteria for each gap, see the [Impact Assessment](./impact-assessment.md) and [Roadmap](./ROADMAP.md).

---

## Data, privacy & security

**What is sent off-device, and to whom.** RAPP does not perform on-device inference. Each turn sends to a third-party model provider:

| Tier | Inference provider | What leaves the device |
|------|--------------------|------------------------|
| 1 (Brainstem) | **GitHub Copilot API** (Microsoft/GitHub) | The composed prompt: user input, conversation history, `soul.md`, each loaded agent's `system_context()`, and any injected `<memory>` |
| 2 (Spinal Cord) | **Azure OpenAI** (your Azure tenant) | The same composed prompt, to your Azure resource |
| 3 (Nervous System) | **Microsoft 365 Copilot / Copilot Studio** | Conversation routed through your M365 tenant |

Governed by the provider's own terms — review the GitHub Copilot, Azure OpenAI, and Microsoft 365 Copilot data terms for retention, training-use, and abuse-monitoring policies. A first-run in-product disclosure and a `data_disclosure` block on `/health` are required P0 deliverables and may not yet be present.

**What is stored locally** (under `~/.brainstem/`):

- `.copilot_token` / `.copilot_session` / `.copilot_pending` — GitHub/Copilot credentials and short-lived session, currently stored **in plaintext at rest** (`brainstem.py` L223–235). Protect the directory; do not run untrusted agents that could read these.
- `.brainstem_book.json` and `.brainstem_data/` — local memory and runtime state, including anything `ManageMemory` persists.
- Agent source under `agents/` — including any Cave-streamed agents (which are additionally hidden from git).

**Privacy posture.** By default RAPP collects **no telemetry and requires no accounts** (CONSTITUTION Article VII) — a genuine privacy strength. However, there is currently **no PII detection or retention/TTL governance** over memory and no enforced redaction on the diagnostics path, and the `PUBLIC_BOUNDARY` scrub gate is a manual rather than a blocking CI control. A memory data-governance policy (categories, purpose, retention, consent, view/export/delete) is a required deliverable (A4/PS1; [Roadmap](./ROADMAP.md) P1).

**Security posture.** As shipped, RAPP runs unreviewed code in-process with your privileges, auto-installs packages, streams unsigned third-party code, and exposes mutating endpoints without auth. **Do not treat the Tier-1 server as a security boundary.** The full analysis, trust boundaries, and required isolation design are in the [Threat Model](./THREAT_MODEL.md) and [Impact Assessment](./impact-assessment.md).

---

## Learn more

**Microsoft Responsible AI references**

- [Microsoft Responsible AI Standard v2 — General Requirements](https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/microsoft/final/en-us/microsoft-brand/documents/Microsoft-Responsible-AI-Standard-General-Requirements.pdf) (the six principles and 17 Goals)
- [Microsoft principles and approach to responsible AI](https://www.microsoft.com/en-us/ai/principles-and-approach)
- [Microsoft's framework for building AI systems responsibly](https://blogs.microsoft.com/on-the-issues/2022/06/21/microsofts-framework-for-building-ai-systems-responsibly/) (principles + Sensitive Uses overview)
- [Azure OpenAI Transparency Note](https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/openai/transparency-note) (the format model for this document)
- [Microsoft RAI Impact Assessment Template](https://blogs.microsoft.com/wp-content/uploads/prod/sites/5/2022/06/Microsoft-RAI-Impact-Assessment-Template.pdf) and [Guide](https://blogs.microsoft.com/wp-content/uploads/prod/sites/5/2022/06/Microsoft-RAI-Impact-Assessment-Guide.pdf)
- [Azure AI Content Safety — overview](https://learn.microsoft.com/en-us/azure/ai-services/content-safety/overview) and [Prompt Shields](https://learn.microsoft.com/en-us/azure/ai-services/content-safety/concepts/jailbreak-detection)
- [Prompt Shields GA + Spotlighting](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/general-availability-of-prompt-shields-in-azure-ai-content-safety-and-azure-open/4235560)
- [Azure AI Content Safety — groundedness detection](https://learn.microsoft.com/en-us/azure/ai-services/content-safety/concepts/groundedness)
- [Azure AI Foundry — AI Red Teaming Agent](https://learn.microsoft.com/en-us/azure/foundry/concepts/ai-red-teaming-agent) and [Microsoft PyRIT](https://www.microsoft.com/en-us/security/blog/2024/02/22/announcing-microsofts-open-automation-framework-to-red-team-generative-ai-systems/)
- [Azure OpenAI Risks & Safety monitoring](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/risks-safety-monitor)

**Sibling RAPP responsible-AI documents** (in this directory)

- [Impact Assessment](./impact-assessment.md) — the gating A1 artifact (adapted from the MS Template, all three tiers)
- [Sensitive Uses determination](./sensitive-uses.md) — three triggers × engine + agent classes, with escalation path (A2)
- [Intended Uses](./INTENDED_USES.md) — full in-scope / out-of-scope / restricted matrix
- [Threat Model](./THREAT_MODEL.md) — security trust boundaries and isolation design (PS2)
- [Roadmap](./ROADMAP.md) — current state → required → exit criteria, phased P0–P3
- [Traceability Matrix](./TRACEABILITY.md) — every control/artifact mapped to its MS RAI Goal ID

---

*This Transparency Note is a living document. It is reviewed on every `VERSION` bump and at least annually, and whenever the execution, authentication, model-routing, or streaming surfaces change. Current status: **DRAFT** — RAPP does not yet meet the Microsoft Responsible AI Standard v2; this note exists to tell the truth about the current state while the [Roadmap](./ROADMAP.md) mitigations are implemented.*
