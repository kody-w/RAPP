# RAPP v1 — Specification

> **Memorialized:** 2026-04-17
> **Status:** Frozen. v1 is the canonical reference. All future versions must remain backwards-compatible with the v1 agent contract.
> **Live at:** [kody-w.com](https://kody-w.com) · [kody-w.github.io/RAPP](https://kody-w.github.io/RAPP/)

---

## 0. The Sacred Tenet

> **The single-file `*_agent.py` is sacred.**
>
> One file. One class. One `perform()` method. One JSON schema.
> Zero build steps. Zero frameworks. Zero ceremony.
>
> An agent that requires more than a single Python file is not a RAPP agent.

Everything else in this specification — the brainstem, the cloud tier, Copilot Studio, federation, soul files, sources panels, ARM templates — exists **to serve the single-file agent**. If a future feature breaks this contract, the feature is wrong.

This is the inviolable law of RAPP v1. It is what makes a 14-year-old able to ship an agent on day one, and what makes an enterprise able to ship the same file to 500,000 seats on day 100.

---

## 1. Identity

| Field | Value |
|-------|-------|
| **Name** | RAPP (Rapid Agent Platform Protocol) |
| **Version** | 1.0.0 |
| **Layers** | Brainstem · Hippocampus (CommunityRAPP) · Copilot Studio harness |
| **License** | Open source where applicable; Microsoft solutions follow Power Platform terms |
| **Reference Implementation** | [kody-w/rapp-installer](https://github.com/kody-w/rapp-installer) |
| **Cloud Backend Reference** | [kody-w/CommunityRAPP](https://github.com/kody-w/CommunityRAPP) |
| **Copilot Studio Bundle** | `MSFTAIBASMultiAgentCopilot_1_0_0_5.zip` |
| **Custom Domain** | kody-w.com |

---

## 2. The Three Tiers

RAPP v1 is exactly three tiers. No more, no less. Each tier is independently runnable — you do not need tier N to use tier N-1.

### Tier 1 — Brainstem (local)

A Flask server that loads a system prompt (`soul.md`), discovers `*_agent.py` files in an `agents/` directory, and exposes a `/chat` endpoint that performs LLM tool-calling against GitHub Copilot's models API.

| Property | Value |
|----------|-------|
| **Runtime** | Python 3.11+ |
| **Port** | 7071 (default) |
| **LLM** | GitHub Copilot (`gpt-4o` default) via GitHub Models API |
| **Auth** | `gh auth login` device code flow — no API keys |
| **Storage** | Local filesystem (`local_storage.py` shim) |
| **Layout** | `~/.brainstem/src/rapp_brainstem/{brainstem.py, soul.md, agents/, .env}` |
| **Install** | `curl -fsSL https://kody-w.github.io/rapp-installer/install.sh \| bash` |
| **Run** | `brainstem` |

### Tier 2 — Hippocampus / CommunityRAPP (cloud)

A persistent, multi-tenant, Entra-authenticated Azure deployment of the brainstem. Same agent contract, same `/chat` semantics, but with Azure OpenAI as the backend, Azure Storage for memory, App Insights for telemetry, and an ARM template for one-click deploy.

| Property | Value |
|----------|-------|
| **Runtime** | Azure Functions (Python 3.11) |
| **LLM** | Azure OpenAI (GPT-4o deployment) |
| **Auth** | Entra ID (managed identity, RBAC) |
| **Storage** | Azure Storage Account |
| **Telemetry** | Application Insights |
| **Deploy** | `azuredeploy.json` ARM template — Deploy-to-Azure button |
| **Install (project scaffold)** | `curl -fsSL .../community_rapp/install.sh \| bash` |
| **Per-user surface** | `~/rapp-projects/<project>/` — isolated venv + agents + storage |
| **Auth flow** | GitHub device code, in-chat |

### Tier 3 — Copilot Studio harness (enterprise)

A Power Platform solution (`MSFTAIBASMultiAgentCopilot_1_0_0_5.zip`) that imports into Copilot Studio, wires the agent to a Function App URL, and publishes the agent into Microsoft Teams and M365 Copilot. Same agent contract, distributed across an organization.

| Property | Value |
|----------|-------|
| **Format** | Power Platform unmanaged solution `.zip` |
| **Container** | Copilot Studio (Microsoft 365) |
| **Surfaces** | Teams, M365 Copilot, Web chat |
| **Wiring** | Function App URL from Tier 2 |
| **Install** | Import solution → set Function App URL → publish |

---

## 3. The Agent Contract (The Sacred Spec)

This is the most important section of this document. **Every RAPP-compatible runtime in v1 must accept agents that conform to this contract, and only this contract.**

### 3.1 File

A single Python file, named `<thing>_agent.py`, placed in an `agents/` directory.

### 3.2 Class

A subclass of `BasicAgent` with:

```python
from basic_agent import BasicAgent

class WeatherAgent(BasicAgent):
    def __init__(self):
        self.name = "Weather"
        self.metadata = {
            "name": self.name,
            "description": "Gets the weather for a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"}
                },
                "required": ["city"]
            }
        }
        super().__init__()

    def perform(self, city="", **kwargs):
        return f"It's sunny in {city}!"
```

### 3.3 The four required attributes

| Attribute | Type | Purpose |
|-----------|------|---------|
| `self.name` | `str` | Tool name surfaced to the LLM |
| `self.metadata` | `dict` | OpenAI-style function-calling JSON schema |
| `super().__init__()` | call | Registers the agent with the runtime |
| `def perform(self, **kwargs) -> str` | method | The tool body — receives the schema's `properties` as kwargs and returns a string |

### 3.4 What an agent MUST NOT do

- Must NOT require a build step.
- Must NOT depend on a framework other than `basic_agent.BasicAgent`.
- Must NOT import sibling files within the same `agents/` directory (each agent is independent).
- Must NOT mutate the runtime's global state outside what `perform()` returns.
- Must NOT require runtime configuration that is not in `self.metadata` or environment variables.

### 3.5 What an agent MAY do

- Make outbound HTTP requests, hit databases, call other LLMs, shell out, write files, send mail.
- Declare pip dependencies at the top of the file. The runtime auto-installs missing deps when the file is loaded.
- Read environment variables for secrets. The runtime injects the host environment into the agent process.
- Return Markdown-formatted strings. The chat UI renders Markdown.

### 3.6 Discovery rules

- Any file matching the glob `agents/*_agent.py` is loaded at startup.
- Files added at runtime via the **Sources** panel (a remote GitHub repo URL) are hot-loaded into the same `agents/` directory.
- Discovery is by filename suffix only — there is no manifest file.
- One file = one agent. There is no multi-agent file.

### 3.7 The portability guarantee

**An agent file that runs in Tier 1 must run unmodified in Tier 2 and Tier 3.**

This is the single hardest requirement in the entire RAPP spec, and it is the requirement that gives RAPP its value. A `weather_agent.py` you write on your laptop today must:

- Run locally against `localhost:7071` (Tier 1)
- Deploy unchanged to your CommunityRAPP Function App (Tier 2)
- Be invoked from Microsoft Teams via Copilot Studio (Tier 3)

If a future change to the spec, the runtime, or the cloud backend breaks this guarantee, the change is rejected. v1 is frozen on this point.

---

## 4. The Soul File

A single Markdown file (`soul.md`) that defines the agent's personality, voice, and operating constraints. Loaded at startup as the system prompt.

| Property | Value |
|----------|-------|
| **Format** | Markdown |
| **Path** | `./soul.md` (override with `SOUL_PATH` env var) |
| **Loaded** | Once at server start; reload via `/health` recycle |
| **Per-tenant** | One soul per brainstem instance. No per-conversation soul mutation in v1. |

The soul is sacred too, but in a softer way: it is the "you" of the agent. The collection of `*_agent.py` files is the "what you can do." The soul is the "who you are." Together they form the tenant.

---

## 5. The HTTP Surface

The brainstem exposes exactly five endpoints in v1. Tiers 2 and 3 must implement at least `/chat` and `/health` with identical request/response shapes.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/chat` | POST | `{"user_input": str, "conversation_history": list, "session_id": str}` → assistant response |
| `/health` | GET | Status, model, loaded agents, token state |
| `/login` | POST | Start GitHub device code OAuth flow (Tier 1 only) |
| `/models` | GET | List available models |
| `/repos` | GET | List connected agent repos (Sources) |

Future versions MAY add endpoints. They MUST NOT change the shape of these five.

---

## 6. Configuration Surface

The full v1 configuration. Every variable has a sensible default. A zero-config install must work.

| Variable | Default | Tier | Description |
|----------|---------|------|-------------|
| `GITHUB_TOKEN` | auto-detected via `gh` CLI | 1 | GitHub PAT or Copilot token |
| `GITHUB_MODEL` | `gpt-4o` | 1 | GitHub Models id |
| `SOUL_PATH` | `./soul.md` | 1, 2 | Path to the soul file |
| `AGENTS_PATH` | `./agents` | 1, 2 | Path to the agents directory |
| `PORT` | `7071` | 1 | Server port |
| `AZURE_OPENAI_ENDPOINT` | n/a | 2 | Azure OpenAI resource endpoint |
| `AZURE_OPENAI_DEPLOYMENT` | n/a | 2 | GPT-4o deployment name |
| `STORAGE_CONNECTION` | n/a | 2 | Azure Storage connection string |

---

## 7. Tenancy Model

> **One tenant = one soul + one agents directory.**

A tenant in RAPP v1 is the smallest unit of identity. It consists of:

1. A `soul.md` system prompt
2. An `agents/` directory of one or more `*_agent.py` files
3. A persistent storage location (filesystem in Tier 1, Storage Account in Tier 2)

A brainstem instance hosts exactly one tenant in v1. A CommunityRAPP project is one tenant per project directory. A Copilot Studio agent is one tenant per imported solution.

**Multi-tenancy is achieved by deploying multiple instances, not by partitioning a single instance.** This is intentional. It keeps the data model boring, the security model trivial, and the failure domain small.

---

## 8. Federation (informational)

RAPP v1 does not standardize federation. However, the spec acknowledges three patterns observed in the wild:

- **Source federation** — pulling agent files from remote GitHub repos via the Sources panel. Sanctioned by v1.
- **Tier handoff** — a Tier 1 brainstem calling a Tier 2 CommunityRAPP `/chat` endpoint as a sub-agent. Sanctioned by v1.
- **Cross-tenant calls** — one tenant invoking another tenant's `/chat`. Permitted but not standardized; treat the other tenant as a remote HTTP API.

Future versions will address federation more directly. v1's stance is: do not constrain a pattern that is still being discovered.

---

## 9. Versioning Policy

RAPP v1 is **frozen**. The agent contract (Section 3), the HTTP surface (Section 5), and the configuration surface (Section 6) will not change in any v1.x.y release.

A change to any of those sections requires a major version bump (RAPP v2). v2 is permitted to break compatibility, but a v2 runtime SHOULD ship a compatibility shim that runs v1 agents unmodified — because **the agent file is sacred**.

| Change | Allowed in v1 patches? |
|--------|------------------------|
| Bug fixes in Tier 1/2/3 implementations | Yes |
| New optional configuration variables | Yes |
| New optional HTTP endpoints | Yes |
| New tier (e.g. mobile) provided it implements the contract | Yes |
| Changes to the agent class signature | **No** — v2 only |
| Changes to `/chat` request or response shape | **No** — v2 only |
| Removing any required attribute on `BasicAgent` | **No** — v2 only |

---

## 10. The Digital Twin

This specification, the landing page at [kody-w.com](https://kody-w.com), and the [archive/engine](https://github.com/kody-w/RAPP/tree/archive/engine) branch of this repo together form the **digital twin** of RAPP v1.

The twin is intentionally static. It is not a running system; it is a memorial of a running system, captured at the moment v1 was declared frozen. Its job is to outlive the running system — to make sure that any future runtime, in any future language, on any future cloud, can be checked against this document and judged compliant or not.

The twin has three parts:

1. **`index.html`** — the experiential twin. What a visitor sees and tries.
2. **`SPEC.md`** *(this file)* — the contractual twin. What an implementer must obey.
3. **`archive/engine` branch** — the genetic twin. The actual code that ran when v1 shipped.

If the experiential twin and the contractual twin ever disagree, the contractual twin wins. If the contractual twin and the genetic twin disagree, the contractual twin still wins — because the genetic twin is one implementation of many possible v1-compliant implementations, and the contract is the platform.

---

## 11. The Closing Statement

RAPP v1 is small on purpose. It is three tiers, five endpoints, one file per agent, one soul per tenant. Everything else is convenience.

The reason RAPP exists is to make agent development feel like writing a Python script in 2014 — open a file, write a function, run it. Everything cloud, everything enterprise, everything multi-surface, has to fit around that feeling, not on top of it.

The sacred tenet, restated:

> **The single-file `*_agent.py` is sacred.**
> Protect it. Future versions will be judged by whether the file you wrote on your laptop today still runs unchanged on whatever runs RAPP next.

— *Memorialized 2026-04-17 at the moment v1 was declared frozen.*
