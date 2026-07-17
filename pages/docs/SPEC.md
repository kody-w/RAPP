# RAPP v1 — Specification

> **SUPERSEDED PROTOCOL DOCUMENT — historical product/agent contract only.**
> For canonicalization, identity, frames, wire, eggs, registry, trust, and
> protocol evolution, the current authority is RAPP/1 rev-5 via
> [`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../RAPP1_STATUS.md). Nothing below is current
> instruction for emitting or accepting protocol artifacts. Preserve these
> dated examples as migration history; RAPP/1 §12 requires total migration and
> retirement rather than perpetual backwards compatibility.
>
> **Scope:** the **single-file agent contract**. What `perform()` takes, what it returns, how metadata travels, the delimited slots (`|||VOICE|||`, `|||TWIN|||`). The agent API. **Not** the network protocol — for that read [`specs/SPEC.md`](../../specs/SPEC.md). See [`specs/README.md`](../../specs/README.md) for the spec-directory map.
>
> **Memorialized:** 2026-04-17
> **Historical status:** Frozen on 2026-04-17; superseded for protocol matters
> by RAPP/1 rev-5.
> **Companion doctrine:** [Single File Agents — rappterhub](https://kody-w.github.io/rappterhub/single-file-agents.html)
> **Live at:** [kody-w.github.io/RAPP](https://kody-w.github.io/RAPP/)

---

## 0. The Sacred Tenet

> **The single-file `*_agent.py` is sacred.**
>
> 🧬 **The file IS the agent IS the documentation IS the contract.**
>
> One file. One class. One `perform()` method. One metadata dict.
> Zero build steps. Zero frameworks. Zero ceremony.
> Zero drift between what the skill says and what the code does.
>
> An agent that requires more than a single Python (or TypeScript) file is not a RAPP agent.

Everything else in this specification — the brainstem, the cloud tier, Copilot Studio, federation, soul files, sources panels, ARM templates, RAR, data sloshing — exists **to serve the single-file agent**. If a future feature breaks this contract, the feature is wrong.

This is the inviolable law of RAPP v1. It is what makes a 14-year-old able to ship an agent on day one, and what makes an enterprise able to ship the same file to 500,000 seats on day 100.

---

## 0.1 The Companion Tenet — The Wire Is Forever

> **`/chat` is the only wire. It is time-travel safe by construction.**
>
> ⏳ **A v0 brainstem unearthed from a backup, a probe, or a frozen Docker image still talks to the latest brainstem without a single code change on either side.**
>
> One endpoint. Same envelope. Same default behavior. Forever.
>
> A brainstem from a year ago, ten years ago, or eons from now is a peer of any brainstem shipping today. Neither one is "compatible" because compatibility was never the question — they speak the same wire because the wire is the same wire.

The whole stack is engineered so this stays true:

- **Schema evolution is additive-only** (Constitution Article XXV). New fields may appear; existing fields never get renamed, removed, or repurposed.
- **Both response keys are emitted forever** — `response` AND `assistant_response` carry the same value. The CA365 lineage (`Copilot-Agent-365`, `CommunityRAPP`, `rapp_swarm`) shipped `assistant_response` first; `rapp_brainstem` later used `response`. Both keys land in every response so neither lineage has to know the other exists.
- **`DEFAULT_USER_GUID = "c0p110t0-aaaa-bbbb-cccc-123456789abc"`** is the same string in every implementation, since the original CA365. It is intentionally invalid hex — that invalidity is the contract; never "fix" it.
- **No peer mode, no handshake mode, no special routing.** Agents and humans hit the same code path. There is no protocol negotiation step that an old brainstem could fail at.
- **The LLM in the middle absorbs version drift.** Whatever shape an old brainstem returns, a modern asker's LLM can read. Whatever shape a modern asker sends, an old brainstem's LLM can interpret. The wire's job is to deliver the chat — meaning is the LLM's job.

If a future change would break a brainstem from the past, the change is wrong — even if it would make today's code cleaner. **The long tail of brainstems in the wild is the customer.**

---

## 1. Why Single File Agents

### 1.1 The problem with skills alone

Every major AI agent framework has arrived at the same idea: **skills** — a Markdown file describing what an agent should do. Skills are portable, human-readable, shareable. But they have a fundamental flaw:

> ⚠️ **Skills are not deterministic.**

A skill tells an AI _what_ to do. It does not tell it _how_. You are trusting the model to interpret, implement, and execute correctly — every single time. It won't.

The industry progression is predictable and has already played out:

1. **Skills launch.** "Just write Markdown and the AI does it!"
2. **Quality issues emerge.** The same skill produces different results each run.
3. **Plugins get added.** "OK, let the skill call deterministic code." Now there are two files.
4. **Security surfaces.** Malicious skills appear. No contract, no structure — freeform text the AI trusts blindly.
5. **Convergence.** You need documentation AND code AND a contract, in one portable unit.

RAPP v1 is the convergence point. A **Single File Agent** is exactly what it sounds like: one file containing everything an agent needs to exist — its documentation, its metadata contract, and its deterministic code.

### 1.2 The three layers in one file

| Layer | What it is | Who reads it |
|-------|-----------|--------------|
| 📋 **Metadata contract** | Native `dict` / `object` — name, description, parameters, JSON schema. Versionable. | The LLM orchestrator, the runtime, CI. |
| 📖 **Markdown docs** | The "skill" — what it does, how to use it, examples, edge cases. | Humans AND AI. |
| ⚙️ **Executable code** | Deterministic `perform()` — same input, same output. Testable, auditable. | The runtime, test suites. |

All three layers live in a single `.py` or `.ts` file. There is no separation to manage, no files to keep in sync, no drift between what the skill says and what the code does.

---

## 2. The Five Principles

A RAPP v1 agent, in any language, MUST satisfy all five.

### 2.1 🎯 Deterministic

An agent's `perform()` does the same thing every time for the same inputs. **The AI orchestrator decides _when_ to call it — the agent decides _how_ to execute.** This is the load-bearing architectural split of RAPP: probabilistic selection, deterministic execution.

### 2.2 📦 Self-Describing

The file contains its own documentation, its own contract, and its own implementation. Drop it anywhere and it works. No external manifest. No companion files. No `AGENT.md`. No `package.json` per-agent. No YAML sidecar.

### 2.3 🔒 Bounded

The metadata dict defines exactly what parameters the agent accepts. The code defines exactly what it does with them. There are no surprises — **an agent can't go through doors it wasn't given.** The schema is the lock and the key.

### 2.4 🧬 Evolvable

Single file agents can be generated, molted, and versioned through natural language. "Make my news agent also include Reddit." The agent evolves — the contract stays clean. The meta-agent `LearnNew` creates new single file agents from prose and hot-loads them immediately.

### 2.5 🔗 Chainable

Agents output `data_slush` — curated signals from live results that feed into the next agent's context automatically. No LLM interpreter is needed between steps. This is how deterministic execution composes at scale.

---

## 3. Identity

| Field | Value |
|-------|-------|
| **Name** | RAPP (Rapid Agent Platform Protocol) |
| **Version** | 1.0.0 |
| **Layers** | Brainstem · Swarm · Copilot Studio harness |
| **Registry** | [RAR — RAPP Agent Registry](https://kody-w.github.io/RAR) |
| **Rapplication Store** | [`rapp_store/`](./rapp_store/) in this repo — catalog (`index.json`), marketplace UI (`index.html`), sources + eggs per rapplication |
| **Doctrine** | Single File Agents |
| **Reference Implementation** | [kody-w/RAPP](https://github.com/kody-w/RAPP) — one repository, two tier directories (`rapp_brainstem/`, `rapp_swarm/`) plus the Tier 3 Copilot Studio bundle as a download under `installer/` |
| **Copilot Studio Bundle** | `installer/MSFTAIBASMultiAgentCopilot_1_0_0_5.zip` |
| **Doctrine Blog** | [kody-w.github.io](https://kody-w.github.io/) (tagged `rapp`) |
| **Roadmap** | [`ROADMAP.md`](./ROADMAP.md) — post-v1 directions that must honor the v1 contract |

---

## 4. The Three Tiers

RAPP v1 is exactly three tiers. Each tier is independently runnable — you do not need tier N to use tier N-1. **The same single file agent runs on all three.**

### Tier 1 — Brainstem (local)

| Property | Value |
|----------|-------|
| **Runtime** | Python 3.11+ |
| **Port** | 7071 (default) |
| **LLM** | GitHub Copilot (`gpt-4o` default) |
| **Auth** | `gh auth login` device code — no API keys |
| **Storage** | Local filesystem (`local_storage.py` shim) |
| **Layout** | `~/.brainstem/src/rapp_brainstem/{brainstem.py, soul.md, agents/, .env}` |
| **Install** | `curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh \| bash` |
| **Run** | `brainstem` |

### Tier 2 — Swarm (cloud)

| Property | Value |
|----------|-------|
| **Runtime** | Azure Functions (Python 3.11) |
| **LLM** | Azure OpenAI (GPT-4o deployment) |
| **Auth** | Entra ID (managed identity, RBAC) |
| **Storage** | Azure Storage Account |
| **Telemetry** | Application Insights |
| **Source** | [`rapp_swarm/`](./rapp_swarm/) — `function_app.py`, `host.json`, ARM template, provision scripts |
| **Deploy** | `installer/azuredeploy.json` ARM template — Deploy-to-Azure button |
| **Install** | `curl -fsSL https://kody-w.github.io/RAPP/installer/install-swarm.sh \| bash` |
| **Wire shape** | Same `/chat` surface as Tier 1; the local brainstem also speaks `rapp-tether/1.0` on :7071 so any Tier 1 is a valid Tier 2 endpoint for dev. |

### Tier 3 — Copilot Studio harness (enterprise)

| Property | Value |
|----------|-------|
| **Format** | Power Platform unmanaged solution `.zip` |
| **Container** | Copilot Studio (Microsoft 365) |
| **Surfaces** | Teams, M365 Copilot, Web chat |
| **Wiring** | Function App URL from Tier 2 |
| **Install** | Import solution → set Function App URL → publish |

---

## 5. The Agent Contract (The Sacred Spec)

This is the most important section of this document. **Every RAPP-compatible runtime in v1 must accept agents that conform to this contract, and only this contract.**

> 🚨 **Nothing else is required to be a RAPP agent.** No `__manifest__`, no `@publisher/slug`, no version, no category, no registry membership. Those are layered on by RAR (§12) for agents that want to be *registered*. A file that satisfies this section alone — `BasicAgent`, `name`, `metadata`, `perform()` — is a fully valid RAPP v1 agent and MUST be executable by any v1-compliant runtime.

### 5.1 Python form

A single file, named `<thing>_agent.py`, placed in an `agents/` directory:

```python
import json
from openrappter.agents.basic_agent import BasicAgent

class WeatherPoetAgent(BasicAgent):
    def __init__(self):
        self.name = 'WeatherPoet'
        self.metadata = {
            "name": self.name,
            "description": "Fetches weather and writes haiku poetry",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "City name to get weather for"}
                },
                "required": []
            }
        }
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        query = kwargs.get('query', '')
        weather = self.fetch_weather(query)
        haiku = self.compose_haiku(weather)
        return json.dumps({
            "status": "success",
            "haiku": haiku,
            "data_slush": {"mood": weather["condition"], "temp_f": weather["temp"]}
        })
```

### 5.2 TypeScript form

Same pattern, same clarity — no YAML, no static strings to parse:

```typescript
export class ShellAgent extends BasicAgent {
  constructor() {
    const metadata: AgentMetadata = {
      name: 'Shell',
      description: 'Execute shell commands and file operations',
      parameters: {
        type: 'object',
        properties: { command: { type: 'string', description: 'Shell command to execute' } },
        required: []
      }
    };
    super('Shell', metadata);
  }

  async perform(kwargs: Record<string, unknown>): Promise<string> {
    // this.context → enriched by data sloshing
    ...
  }
}
```

### 5.3 The four required attributes

| Attribute | Type | Purpose |
|-----------|------|---------|
| `self.name` / `this.name` | `str` | Tool name surfaced to the LLM |
| `self.metadata` / constructor `metadata` | `dict` / `object` | OpenAI-style function-calling JSON schema |
| `super().__init__(name, metadata)` | call | Registers the agent with the runtime |
| `perform(**kwargs) -> str` | method | The tool body — receives the schema's `properties` and returns a string |

### 5.4 The `data_slush` output convention

An agent's `perform()` SHOULD return a JSON string shaped like:

```json
{
  "status": "success",
  "<payload_key>": "<human-facing result>",
  "data_slush": { "<signal_key>": "<curated value for next agent>" }
}
```

`data_slush` is the bridge between agents. It feeds directly into the next agent's `self.context` in a chain, with zero LLM interpretation required between steps. This is how deterministic execution composes.

### 5.5 What an agent MUST NOT do

- Must NOT require a build step.
- Must NOT depend on a framework other than `BasicAgent`.
- Must NOT import sibling files within the same `agents/` directory (each agent is independent).
- Must NOT mutate the runtime's global state outside what `perform()` returns.
- Must NOT require runtime configuration that is not in `self.metadata` or environment variables.

### 5.6 What an agent MAY do

- Make outbound HTTP requests, hit databases, call other LLMs, shell out, write files, send mail.
- Declare pip (or npm) dependencies at the top of the file. The runtime auto-installs missing deps when the file is loaded.
- Read environment variables for secrets. The runtime injects the host environment.
- Return Markdown-formatted strings. The chat UI renders Markdown.
- Return structured JSON with a `data_slush` field for chaining.

### 5.7 Discovery rules

- Any file matching `agents/*_agent.py` (or `*Agent.ts`) is loaded at startup.
- Files added at runtime via the **Sources** panel (a remote GitHub repo URL) are hot-loaded.
- Discovery is by filename suffix only — there is no manifest file.
- One file = one agent. There is no multi-agent file.

### 5.8 The portability guarantee

**An agent file that runs in Tier 1 must run unmodified in Tier 2 and Tier 3.**

This is the single hardest requirement in the entire RAPP spec, and it is the requirement that gives RAPP its value. A `weather_agent.py` you write on your laptop today must:

- Run locally against `localhost:7071` (Tier 1)
- Deploy unchanged to your RAPP Swarm Function App (Tier 2)
- Be invoked from Microsoft Teams via Copilot Studio (Tier 3)

If a future change to the spec, the runtime, or the cloud backend breaks this guarantee, the change is rejected. v1 is frozen on this point.

---

## 6. Implicit Context: Data Sloshing

Every single file agent inherits **data sloshing** — automatic context enrichment before `perform()` runs. The agent wakes up already knowing:

| Layer | What it knows | Where it's surfaced |
|-------|---------------|---------------------|
| ⏰ **Temporal** | Time of day, day of week, fiscal period, urgency signals | `self.context.temporal` |
| 🧠 **Memory** | Relevant past interactions surfaced by overlap | `self.context.memory` |
| 🎯 **Query** | Specificity, ownership hints, temporal references | `self.context.query` |
| 👤 **Behavioral** | User's technical level, brevity preference | `self.context.behavioral` |
| 🧊 **Upstream slush** | Live signals from the previous agent in a chain | `self.context.slush` |

The agent doesn't ask for this context. It doesn't configure it. It's just _there_, in `self.context`, before the first line of `perform()` executes. This is what makes the pattern biological — the agent wakes up oriented, not blank.

---

## 7. The Soul File

A single Markdown file (`soul.md`) that defines the agent's personality, voice, and operating constraints. Loaded at startup as the system prompt.

| Property | Value |
|----------|-------|
| **Format** | Markdown |
| **Path** | `./soul.md` (override with `SOUL_PATH` env var) |
| **Loaded** | Once at server start; reload via `/health` recycle |
| **Per-tenant** | One soul per brainstem instance. No per-conversation soul mutation in v1. |

The soul is sacred too, but softer: it is the "you" of the agent. The collection of `*_agent.py` files is the "what you can do." The soul is the "who you are." Together they form the tenant.

---

## 8. The HTTP Surface

The brainstem exposes exactly five endpoints in v1. Tiers 2 and 3 MUST implement at least `/chat` and `/health` with identical request/response shapes.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/chat` | POST | The wire. See full envelope below. |
| `/health` | GET | Status, model, loaded agents, token state, bootstrap status |
| `/login` | POST | Start GitHub device code OAuth flow (Tier 1 only) |
| `/models` | GET | List available models |
| `/repos` | GET | List connected agent repos (Sources) |

Future versions MAY add endpoints. They MUST NOT change the shape of these five (Constitution Article XXV: additive-only schema evolution).

### `/chat` envelope (sacred — see Constitution Article XXV)

**Request** (POST `/chat`, `Content-Type: application/json`):

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `user_input` | str | yes | — | The message |
| `conversation_history` | list | no | `[]` | Prior turns as `{role, content}` |
| `session_id` | str (GUID) | no | auto-mint | Per-conversation; echoed in response |
| `user_guid` | str (GUID) | no | `DEFAULT_USER_GUID` | Caller identity. See below. |

**Response** (200 OK):

| Field | Type | Notes |
|-------|------|-------|
| `response` | str | Assistant reply |
| `assistant_response` | str | **Same value as `response`** — both keys forever |
| `voice_response` | str | When `VOICE_MODE` enabled |
| `twin_response` | str | When `TWIN_MODE` enabled |
| `session_id` | str | Echoed |
| `user_guid` | str | Echoed |
| `agent_logs` | str | Newline-joined |
| `voice_mode` / `twin_mode` | bool | Current server flags |

Both `response` and `assistant_response` are emitted with identical content. The `rapp_brainstem` lineage historically used `response`; the CA365 lineage (`Copilot-Agent-365`, `CommunityRAPP`, `rapp_swarm`) historically used `assistant_response`. Both keys are present in every response so clients of either lineage land on the data they expect.

### `user_guid` — caller identity

Every caller (human, agent, peer brainstem, MCP client) has a `user_guid`. The kernel does not treat any value specially — there is no peer mode, no handshake mode, no special routing. Whoever is calling, they are uniformly a "user" from the wire's perspective.

The default value is **intentionally invalid hex**:

```
DEFAULT_USER_GUID = "c0p110t0-aaaa-bbbb-cccc-123456789abc"
```

The `p` and `l` in `c0p110t0` spell "copilot" while making the string un-parseable as a real UUID. This is a security feature inherited from CA365: the default can never collide with a real identity, gets rejected by UUID-validating columns, and shows up unmistakably in logs as "no real user context." Memory shims route it to shared global memory.

**On Tier 1** (single-operator local machine): `user_guid` is silent. Humans at the keyboard never need to think about it; the default routes to shared memory which IS "your" memory because you ARE the user.

**On Tier 2** (multi-tenant cloud): callers identify themselves so memory is isolated per identity.

Same wire either way. Same default behavior either way.

---

## 9. Configuration Surface

Every variable has a sensible default. A zero-config install must work.

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

## 10. Tenancy Model

> **One tenant = one soul + one agents directory.**

A tenant in RAPP v1 is the smallest unit of identity. It consists of:

1. A `soul.md` system prompt
2. An `agents/` directory of one or more single file agents
3. A persistent storage location (filesystem in Tier 1, Storage Account in Tier 2)

A brainstem instance hosts exactly one tenant in v1. A RAPP Swarm project is one tenant per project directory. A Copilot Studio agent is one tenant per imported solution.

**Multi-tenancy is achieved by deploying multiple instances, not by partitioning a single instance.** This is intentional. It keeps the data model boring, the security model trivial, and the failure domain small.

---

## 11. Agent Generation (Molt)

The pattern gets more powerful when agents generate other agents. The `LearnNew` meta-agent creates single file agents from natural language:

> 💬 _"Learn a new agent that fetches Hacker News stories and summarizes the top 5"_

`LearnNew` generates a complete single file agent — metadata, documentation, and working code — writes it to the `agents/` directory, and hot-loads it for immediate use. Because the output is a single file with a deterministic contract, generated agents are:

- **Publishable** — push directly to RAR (no separate manifest to write)
- **Testable** — standard unit tests against `perform()`
- **Auditable** — read one file to understand everything the agent can do
- **Moltable** — evolve through feedback: "add Reddit sources" → new generation, same contract

This is evolution inside the system. The contract stays constant; the capabilities compound.

---

## 12. RAR — The RAPP Agent Registry

> Referenced, not twinned. RAR lives at [kody-w/RAR](https://github.com/kody-w/RAR) and is the canonical reference registry implementation of the v1 single file agent contract.

**RAR** (RAPP Agent Registry) is the reference package registry for v1. It is to single file agents what npm is to JavaScript packages — but local-first, single-file, and offline-capable. No `node_modules`. No build step. No server required. `git clone` the registry and you have everything — it works from `file://`, in a cabin, with no internet.

### 12.0 The critical distinction — RAPP agent vs. RAR agent

**A RAPP agent is not a RAR agent.** They are two different things, and the agent file is sacred in both senses — but the registry adds requirements on top of §5 that a plain RAPP agent does not need to satisfy.

| Capability | **RAPP agent** (§5 contract) | **RAR-registered agent** (§12) |
|------------|:----------------------------:|:------------------------------:|
| Extends `BasicAgent` | ✅ Required | ✅ Required |
| `self.name` | ✅ Required | ✅ Required |
| `self.metadata` (function-calling schema) | ✅ Required | ✅ Required |
| `perform(**kwargs) -> str` | ✅ Required | ✅ Required |
| File named `*_agent.py` in `agents/` | ✅ Required | ✅ Required |
| `__manifest__` dict at module scope | ❌ **Not required** | ✅ Required |
| `schema: "rapp-agent/1.0"` tag | ❌ Not required | ✅ Required |
| `@publisher/slug` package identity | ❌ Not required | ✅ Required |
| Semver `version` | ❌ Not required | ✅ Required |
| Category + tags + quality tier | ❌ Not required | ✅ Required |
| `requires_env` declared explicitly | ❌ Not required | ✅ Required |
| File lives at `agents/@publisher/slug.py` | ❌ Not required | ✅ Required |
| `snake_case` everywhere | ❌ Recommended | ✅ Required |
| Passes `rapp_sdk.py validate` | ❌ Not required | ✅ Required |
| Passes `rapp_sdk.py test` (contract tests) | ❌ Not required | ✅ Required |
| Runs in a brainstem (Tier 1/2/3) | ✅ Yes | ✅ Yes |
| Appears in `registry.json` | ❌ No | ✅ Yes |
| Has a card, seed, incantation | ❌ No | ✅ Yes |
| Resolvable from 7-word incantation | ❌ No | ✅ Yes |

**Read this two ways.** Looking left: the sacred tenet is preserved — a `weather_agent.py` with just `BasicAgent`, `name`, `metadata`, and `perform()` is a valid, runnable RAPP v1 agent. Drop it in `agents/`, it works, anywhere. Zero registry awareness required. Looking right: to be **registered** in RAR — to be installable by `rapp_sdk.py install`, to have a card, to be resolvable by seed or incantation, to appear in `registry.json` — the file must additionally carry the `__manifest__` dict and pass the SDK's validators.

**The manifest is the cost of admission to RAR. It is not the cost of being a RAPP agent.**

This distinction is load-bearing for v1:

- A developer can write and run agents **forever** without ever touching the registry. The file stays sacred. The contract stays clean.
- A developer who wants to **share** their agent pays the manifest tax once: add ~10 lines of `__manifest__`, submit, done. The file is still one file. The manifest lives inside the file. No separate package.json.
- A runtime that loads an agent MUST NOT require the manifest to execute it. Runtimes that only execute manifest-bearing files are non-compliant with §5.

> **The agent.py is sacred. The registry is sanctioned. The registry does not get to redefine what a RAPP agent is.**

### 12.1 Canonical facts

| Field | Value |
|-------|-------|
| **Repo** | [kody-w/RAR](https://github.com/kody-w/RAR) |
| **Site** | [kody-w.github.io/RAR](https://kody-w.github.io/RAR) |
| **Registry index** | [`registry.json`](https://raw.githubusercontent.com/kody-w/RAR/main/registry.json) |
| **Machine API manifest** | [`api.json`](https://raw.githubusercontent.com/kody-w/RAR/main/api.json) |
| **AI skill interface** | [`skill.md`](https://raw.githubusercontent.com/kody-w/RAR/main/skill.md) |
| **SDK (zero-dep, single-file)** | [`rapp_sdk.py`](https://raw.githubusercontent.com/kody-w/RAR/main/rapp_sdk.py) |
| **Agent template** | [`template_agent.py`](https://raw.githubusercontent.com/kody-w/RAR/main/template_agent.py) |
| **Agent base class** | `BasicAgent` (`@rapp/basic_agent`) |
| **Package path** | `agents/@publisher/slug.py` |
| **Naming** | `snake_case` everywhere — filenames, manifest names, dependencies. No dashes. |

### 12.2 The `__manifest__` schema (RAR-only)

> Reminder: this section defines requirements for **registry-bound** agents, not for all RAPP agents. See §12.0.

RAR-registered agents carry an embedded `__manifest__` dict at module scope, tagged `"schema": "rapp-agent/1.0"`. The manifest is the sole difference between a runnable RAPP agent and a registerable RAR agent. Because the manifest lives inside the same file, the sacred tenet (§0) is preserved: one file, one agent, one contract — now with an optional registry header.

```python
__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "@publisher/slug",            # package id — snake_case slug
    "version": "1.0.0",                   # semver
    "display_name": "Human-Facing Name",
    "description": "One sentence.",
    "author": "Your Name",
    "tags": ["keyword1", "keyword2"],
    "category": "general",                # one of the 19 canonical categories
    "quality_tier": "community",          # community | verified | official
    "requires_env": [],                   # env vars the agent needs
}
```

### 12.3 The SDK surface

`rapp_sdk.py` is a zero-dependency single file. Every command supports `--json` for machine orchestration.

| Command | Purpose |
|---------|---------|
| `new @pub/slug` | Scaffold agent from template |
| `validate path.py` | Validate the manifest + contract |
| `test path.py` | Run contract tests |
| `submit path.py` | Submit to RAR (auto-registers binder if needed) |
| `card resolve NAME\|SEED\|INCANTATION` | Resolve a card from name, 64-bit seed, or 7-word incantation |
| `card words NAME` | Get the 7-word incantation for any agent |
| `egg forge @a @b @c` | Compress a set of agents into a shareable string |
| `egg hatch STRING` | Reconstruct agents from a compact egg string |

### 12.4 Sanctioned extensions (v1-compatible)

RAR introduces four concepts that are **sanctioned but optional** under v1. An implementation is v1-compliant without any of them; implementations that adopt them inherit the following definitions:

- **Card** — a visual, collectible projection of an agent file (types, stats, abilities, art). Every agent has at most one card.
- **Seed** — a deterministic 64-bit number that reconstructs the full card offline. The card's entire visual state can be rebuilt from the seed alone.
- **Incantation** — the 7-word English phrase that maps 1:1 to a seed (e.g. `TWIST MOLD BEQUEST VALOR LEFT ORBIT RUNE`). Speakable via the Web Speech API; the binder listens and the card self-assembles.
- **Binder** — a personal card collection. Offline via IndexedDB + localStorage. Mobile-first, PWA-capable. Export/import as `binder.json`.
- **Egg** — a compact serialization format that encodes a set of agents into a shareable string. Forge on one device, hatch on another.

These extensions exist to serve the sacred tenet from a different angle: if the file is the agent, then a seed is the file, and an incantation is the seed. Portability all the way down to seven spoken words.

### 12.5 How it composes with v1

| v1 concept | RAR instance |
|------------|--------------|
| Sacred tenet — single file agent | Every RAR package is exactly one `.py` file |
| Self-describing (§2.2) | The `__manifest__` lives inside the file |
| Bounded (§2.3) | The manifest `parameters` schema is the lock |
| Evolvable (§2.4) | `version` bump + resubmit = molt |
| Chainable (§2.5) | `data_slush` flows through chains in a binder |
| The three tiers (§4) | A RAR agent installs into any of the three |
| `BasicAgent` (§5.1) | RAR's `@rapp/basic_agent` is the reference base |
| Agent generation (§11) | `rapp_sdk.py new` scaffolds; `LearnNew` generates in-brainstem |

### 12.6 Submission path (one command)

```bash
# Fetch the SDK
curl -O https://raw.githubusercontent.com/kody-w/RAR/main/rapp_sdk.py

# Scaffold + submit
python rapp_sdk.py new @yourname/my_cool_agent
python rapp_sdk.py submit agents/@yourname/my_cool_agent.py
```

The SDK validates, auto-registers the publisher's binder on first submit, opens a staging PR, and — once approved — the forge mints the card into `registry.json`. Updates are a `version` bump plus a resubmit.

### 12.7 Registry as compliance oracle

The registry is sanctioned by v1 as the canonical distribution channel and the de-facto compliance oracle. An agent that validates under `rapp_sdk.py validate` is, by definition, a valid RAPP v1 agent. If a runtime accepts an agent from the registry and cannot execute it, the runtime is non-compliant — not the agent.

---

## 13. Federation (informational)

RAPP v1 does not standardize federation. However, the spec acknowledges three patterns observed in the wild:

- **Source federation** — pulling agent files from remote GitHub repos via the Sources panel. Sanctioned.
- **Tier handoff** — a Tier 1 brainstem calling a Tier 2 RAPP Swarm `/chat` endpoint as a sub-agent. Sanctioned.
- **Cross-tenant calls** — one tenant invoking another tenant's `/chat`. Permitted but not standardized; treat the other tenant as a remote HTTP API.
- **Chain composition** — agents piping `data_slush` to one another. Standardized (Section 5.4).

Future versions will address federation more directly. v1's stance: do not constrain a pattern still being discovered.

---

## 14. Versioning Policy

RAPP v1 is **frozen**. The agent contract (Section 5), the HTTP surface (Section 8), the configuration surface (Section 9), and the `data_slush` convention (Section 5.4) will not change in any v1.x.y release.

A change to any of those sections requires a major version bump (RAPP v2). v2 is permitted to break compatibility, but a v2 runtime SHOULD ship a compatibility shim that runs v1 agents unmodified — because **the agent file is sacred**.

| Change | Allowed in v1 patches? |
|--------|------------------------|
| Bug fixes in Tier 1/2/3 implementations | Yes |
| New optional configuration variables | Yes |
| New optional HTTP endpoints | Yes |
| New tier (e.g. mobile) that implements the contract | Yes |
| New languages with their own `BasicAgent` base class | Yes, if they satisfy the Five Principles |
| Changes to the agent class signature | **No** — v2 only |
| Changes to `/chat` request or response shape | **No** — v2 only |
| Removing any required attribute on `BasicAgent` | **No** — v2 only |
| Breaking the `data_slush` shape | **No** — v2 only |
| Making `__manifest__` a §5 requirement (registry bleeding into contract) | **No** — v2 only, and strongly discouraged |

---

## 15. The Roadmap (already playing out)

The AI ecosystem is currently living through this progression. RAPP v1 is already at step 5.

1. ✅ **Skills** — flat text files. Mainstream. (Already commoditized.)
2. 🔄 **Plugins** — deterministic code called by skills. Arriving now across every vendor.
3. 🔜 **Unified format** — skill + plugin + contract merged into one file. _This is the single file agent._
4. 🔜 **Agent registries** — sharing and installing. _This is [RAR](https://kody-w.github.io/RAR)._
5. 🔜 **Agent generation** — AI creating agents that create agents. _This is LearnNew + molt._

RAPP is not predicting this. RAPP is the artifact left behind from running this loop in production for over a year.

Post-v1 direction lives in [`ROADMAP.md`](./ROADMAP.md). Roadmap items MUST honor the v1 contract — they extend, never replace.

---

## 16. The Digital Twin (memorial, not companion)

> Not to be confused with the **digital twin companion** feature in `ROADMAP.md` — that is an in-product surface. This section is about the spec itself as a static twin of the v1 system.


This specification, the landing page at [kody-w.github.io/RAPP](https://kody-w.github.io/RAPP/), the [`archive/engine`](https://github.com/kody-w/RAPP/tree/archive/engine) branch of this repo, and the canonical [Single File Agents doctrine page](https://kody-w.github.io/rappterhub/single-file-agents.html) together form the **digital twin** of RAPP v1.

The twin is intentionally static. It is not a running system; it is a memorial of a running system, captured at the moment v1 was declared frozen. Its job is to outlive the running system — so any future runtime, in any future language, on any future cloud, can be checked against this document and judged compliant or not.

The twin has four parts:

1. **`index.html`** — the experiential twin. What a visitor sees and tries.
2. **`SPEC.md`** *(this file)* — the contractual twin. What an implementer must obey.
3. **Single File Agents doctrine** — the philosophical twin. Why the contract has the shape it has.
4. **`archive/engine` branch** — the genetic twin. The code that ran when v1 shipped.

**Tie-break order:** if they disagree, SPEC wins over doctrine, doctrine wins over index, index wins over engine. The contract is the platform; the engine is one implementation of many.

---

## 17. The Closing Statement

RAPP v1 is small on purpose. Three tiers. Five endpoints. One file per agent. One soul per tenant. Five principles. One registry. Everything else is convenience.

The reason RAPP exists is to make agent development feel like writing a Python script in 2014 — open a file, write a function, run it. Everything cloud, everything enterprise, everything multi-surface, has to fit around that feeling, not on top of it.

The sacred tenet, restated:

> 🧬 **The file IS the agent IS the documentation IS the contract.**
>
> **The single-file `*_agent.py` is sacred.**
> Protect it. Future versions will be judged by whether the file you wrote on your laptop today still runs unchanged on whatever runs RAPP next.

_Memorialized 2026-04-17, at the moment v1 was declared frozen._

---

## 18. Post-v1 Addenda (v1-compatible)

> **Added 2026-04-24 (brainstem v0.12.x).** This section documents extensions
> layered on top of v1 without breaking any frozen clause. Nothing here
> rewrites §0 through §17. §14 Versioning Policy governs what is allowed:
> new optional configuration variables, new optional HTTP endpoints, new
> implementations of the existing tiers. Every item below fits in one of
> those buckets.
>
> **If an addendum contradicts an earlier section, §18 does not win — the
> addendum is wrong and should be retracted.** The v1 contract is the
> oracle; §18 is a changelog, not an override.

### 18.0 Why this section exists

Between the 2026-04-17 memorialization and today, the reference
implementation shipped real deployments at all three tiers. A handful of
discipline decisions and implementation patterns emerged that deserve
explicit record without mutating the frozen contract.

### 18.1 `brainstem.py` is sacred (companion to §0)

v1's sacred tenet (§0) declares the **agent file** sacred. Post-v1 practice
has added a **companion** rule: the reference brainstem entry point
(`rapp_brainstem/brainstem.py`) is sacred at the **platform** layer. Both
rules coexist; neither subsumes the other.

- §0 protects the *unit of distribution*: one file, portable, self-documenting.
- §18.1 protects the *engine that runs the units*: one file, stable contract, no drift.

Legitimate edits to `brainstem.py` are bug fixes in existing behavior, or
adding a new top-level output-slot delimiter (the class of change that
produced `|||VOICE|||` and `|||TWIN|||`). Everything else belongs in an
agent or in a utility module — **never** in the engine.

The anti-patterns called out explicitly:

- New features added inline to the engine.
- New HTTP routes that duplicate what an agent could do.
- Silent contract changes — renaming a route, reshaping a response
  envelope, reordering the tool loop. Those are SPEC-level changes
  (§14) and require a version bump and a migration note.

### 18.2 Tier 2 adapter seam: `user_guid` dispatch + envelope translation

Tier 2 in practice serves many tenants from a single Function App
deployment. The mechanism is a body-field dispatch token:

```json
POST /api/businessinsightbot_function
{
  "user_input":            "<string>",
  "conversation_history":  "<array>",
  "user_guid":             "<AAD oid / tenant identity>"
}
```

`user_guid` scopes memory and any per-tenant state. The adapter seam
(`rapp_swarm/function_app.py`) calls `storage_manager.set_memory_context(
user_guid)` per request, then invokes the same agent contract (§5).

**Compatibility with §8.** Tier 1's `/chat` (with `session_id`) is
untouched. Tier 2 adds `/api/businessinsightbot_function` as a **new
optional HTTP endpoint**, sanctioned by §14. Tier 1 clients continue to
work against Tier 1 brainstems unchanged.

**Envelope translation at the seam.** Tier 1 returns `response` /
`voice_response` / `agent_logs`. The shipping Copilot Studio / Power
Automate consumer expects `assistant_response` / `voice_response` /
`agent_logs` / echoed `user_guid`. The translation happens in
`function_app.py` only. **The brainstem envelope is never reshaped.**
Any future MCS consumer with different field names gets its translation
in the adapter, not in the core.

### 18.3 Tier 3 identity flow

The Power Automate flow that ships with the Copilot Studio solution bundle
(§4 Tier 3) uses the Office 365 Users connector's
**`Get my profile (V2)`** on `runtimeSource: "invoker"` — the signed-in
M365 user. `body/id` (the AAD object ID) becomes the `user_guid` in the
body sent to Tier 2. Auth to the function app is the shared function key;
identity is guaranteed by Power Automate's invoker-scoped connection.

**No per-user Copilot Studio solution.** One connector, one Tier 2
deployment, N users via identity-from-invoker.

### 18.4 Tenancy clarification (v1-compatible reading of §10)

§10 reads correctly at Tier 1: *one brainstem instance hosts exactly one
tenant.* That is still true of a local brainstem on a developer's laptop.

Tier 2 in v1.12 partitions a single Function App deployment by
`user_guid`. Each guid sees its own memory namespace; the shared
`agents/` tree is the same for all tenants. **This does not contradict
§10** because:

- The v1 agent contract (§5) is unchanged — agents don't know which
  tenant invoked them.
- The `/chat` request/response shape at the *contract* surface is
  unchanged. Tier 2 adds a *new route* (§18.2) that carries the
  dispatch field; the original route still honors the original shape.
- The data model stays boring: one `user_guid` = one memory namespace.
  No shared mutable state between tenants.

Stronger isolation (regulated tenants, air-gapped customers) is achieved
by deploying a second Tier 2 instance — still one codebase, guid-routed
within each deployment.

### 18.5 Workshop → Singleton (Article IX companion to §11)

§11 describes agent *generation* from natural language via the `LearnNew`
meta-agent. v1.12 formalized a companion verb for **distribution**:

- **Workshop** — a folder of `*_agent.py` files under
  `agents/workspace_agents/<my_swarm>/` where a user iterates against
  the hotload loop.
- **Singleton** — one `*_agent.py` file produced by
  `swarm_factory_agent.py`, containing the inlined capabilities of the
  entire workshop.

The singleton is the **unit of distribution**. Drop it into any other
brainstem's `agents/` and it runs unchanged. This is the §0 sacred
tenet applied to composed swarms: one file remains the unit — whether
that file started life as a single hand-authored agent or as the
converged output of a workshop.

The retired sibling-swarm invocation family (`swarm_invoke`,
`swarm_deploy`, `swarm_list`, `swarm_info`, `swarm_seal`,
`swarm_snapshot`, `swarm_delete`) is **explicitly not part of the
spec**. Swarms at the user layer are a directory of agents during
development and a singleton file at distribution. No runtime swarm
registry, no orchestration protocol, no invocation API.

### 18.6 Audience one-pagers (distinct from the pitch deck)

The reference implementation ships a family of single-slide HTML pages —
one URL per audience — at `kody-w.github.io/RAPP/`:

| Audience | URL |
|----------|-----|
| General / platform | `one-pager.html` |
| Leadership / exec | `leadership.html` |
| Sellers / enablement (process) | `process.html` |
| Partners receiving handoffs | `partners.html` |
| "What can this build?" | `use-cases.html` |
| Top-4 objections | `faq-slide.html` |
| Security / compliance | `security.html` |

These are content, not contract. They carry no normative weight in this
SPEC; they're listed so implementers can find canonical phrasing of the
platform's positioning.

The platform also ships a long-form companion to these pages — the **vault**
at `pages/vault/` (Obsidian-compatible) and the `pages/vault/index.html` viewer. The
vault holds the *why* behind decisions: founding principles, removal
stories, architecture trade-offs, twin/UX philosophy. It is the canonical
home for accumulated wisdom under Constitution Article XXIII. Implementers
who want to understand *why* the audience pages claim what they claim
should read the corresponding vault notes:

| Topic | Vault note |
|-------|------------|
| The "engine, not experience" framing | `pages/vault/Founding Decisions/Engine, Not Experience.md` |
| Why three tiers, what each can't do | `pages/vault/Founding Decisions/Why Three Tiers, Not One.md` |
| The single-file agent constraint | `pages/vault/Founding Decisions/The Single-File Agent Bet.md` |
| The 60-min workshop pacing | `pages/vault/Process/60 Minutes to a Working Agent.md` |
| Self-documenting partner handoff | `pages/vault/Process/Self-Documenting Handoff.md` |
| The anti-pitch / honest tradeoffs | `pages/vault/Positioning/What You Give Up With RAPP.md` |
| Sequential, not versus, vs Copilot Studio | `pages/vault/Positioning/RAPP vs Copilot Studio.md` |

### 18.7 Version history under v1

v1 is still v1. Every release since 2026-04-17 is a v1.x.y patch:

| Version | Tag | Summary |
|---------|-----|---------|
| 0.12.1 | `brainstem-v0.12.1` | UI backport to v0.6.0 classic chrome; Tier 2 deploy-pipeline fixes. |
| 0.12.0 | `brainstem-v0.12.0` | Three-tier adapter seam landed; sacred brainstem article; workshop→singleton framing; 17 agents retired. |
| 0.11.x | `brainstem-v0.11.*` | Workspace_agents pattern, project-local install, agent handshake, positioning polish. |

Rollback contract is preserved: every tag is immutable,
`BRAINSTEM_VERSION=x.y.z` is the one-command rollback.

### 18.8 Full-Stack Rapplications: the Agent-First Extension Model

§0 declares the single-file agent sacred. §18.1 declares `brainstem.py`
sacred. Together they define the **kernel**: the engine and the unit it
runs. Everything built on top of the kernel is an **extension**.

v0.12.2 formalized two extension points — one existing, one new:

| Extension | Contract | Drop-in directory | LLM-visible? |
|-----------|----------|-------------------|-------------|
| **Agent** | `metadata` dict + `perform(**kwargs) → str` | `agents/` | Yes — tool in the tool-calling loop |
| **Service** | `name` str + `handle(method, path, body) → (dict, int)` | `services/` | No — HTTP only |

**Agents** are the primary interface. They work through any LLM that
speaks tool calls: brainstem `/chat`, Copilot Studio, Claude, GPT, or
any future AI. The agent IS the application.

**Services** are the optional HTTP layer. They expose REST endpoints
for web UIs, external system integrations, or machine-to-machine
communication. Services read/write the same storage as agents — they
are a view, not a second source of truth.

A **rapplication** is the atomic installable unit:

- MUST include at least one `*_agent.py` (the agent-first rule).
- MAY include one `*_service.py` (the optional HTTP layer).
- Both files are single-file, zero-dependency, portable across tiers.
- Install = drop files into `agents/` and `services/`.
  Uninstall = delete them. No config, no migration, no cleanup.

#### The kernel boundary

The kernel (`brainstem.py` + `basic_agent.py`) provides exactly two
discovery mechanisms — one for agents, one for services — and never
grows beyond them. All capability lives in the extensions:

```
┌─────────────────────────────────────────┐
│            brainstem.py (kernel)         │
│  ┌──────────────┐  ┌────────────────┐   │
│  │ Agent        │  │ Service        │   │
│  │ Discovery    │  │ Discovery      │   │
│  │ agents/*.py  │  │ services/*.py  │   │
│  └──────┬───────┘  └───────┬────────┘   │
│         │                  │            │
│   POST /chat          GET|POST|PUT|DELETE│
│   (LLM tool loop)     /api/<name>/<path>│
└─────────┼──────────────────┼────────────┘
          │                  │
    ┌─────▼──────┐    ┌──────▼──────┐
    │  Any LLM   │    │  Any UI /   │
    │  Any AI    │    │  Any client │
    │  Any tier  │    │  Any system │
    └────────────┘    └─────────────┘
```

#### The agent-first rule

> **The agent is the API. The service is a view.**

A rapplication MUST be fully functional through `perform()` alone. A
user talking to any AI — on their phone, in a terminal, through
Copilot Studio — gets the complete rapplication without a browser.
The service adds convenience (drag-and-drop, charting, webhooks) but
never gates capability.

This is what makes RAPP rapplications portable across every AI surface
that exists today and every one that will exist tomorrow.

#### Compatibility with v1

- **§0 (Sacred Tenet):** Agents are still single-file. Services are
  also single-file. The unit of distribution is unchanged.
- **§5 (Agent Contract):** `metadata` + `perform()` is untouched.
  Services have their own contract (`name` + `handle()`), never mixed.
- **§8 (HTTP Surface):** The five frozen endpoints are unchanged.
  Service dispatch (`/api/<name>/<path>`) is a new optional endpoint
  sanctioned by §14.
- **§10 (Tenancy):** Services share the tenant's storage namespace,
  same as agents. No new tenancy model.

#### Catalog categories for full-stack rapplications

| Category | Pattern | Example |
|----------|---------|---------|
| `workspace` | Agent manages data, service serves UI | Kanban |
| `integration` | Agent queries events, service ingests them | Webhook |
| `analytics` | Agent logs/queries metrics, service serves charts | Dashboard |

### 18.9 Version history under v1 (continued)

| Version | Tag | Summary |
|---------|-----|---------|
| 0.12.2 | `brainstem-v0.12.2` | Agent-first rapplication platform: service discovery in kernel, factory-clean brainstem, 7 RAPPstore rapplications, VibeBuilder, twin mode, rapplication SDK, Constitution Article XX, vBrainstem standalone catalog, installer fixes. |
| 0.15.x | `brainstem-v0.15.x` | Egg-cartridge unification (§18.10) + vBrainstem tether (§18.11): five-variant `.egg` family (organism / rapplication / session / neighborhood / estate), kernel `egg_hatcher_agent.py` with introspection-based routing, public tethered surface at `pages/vbrainstem.html` (QR pair → WebRTC data channel → multi-participant transcript with Coordinator-twin-driven workflow demo). Session cartridges round-trip through the rappterbox console iframe. Patent: WH-2026-002 §7.21 (private). |

---

### 18.10 The `.egg` cartridge family — unified portable container

> **Added 2026-05-10.** The `.egg` cartridge is the **single sneakernet primitive** across the RAPP ecosystem. Anything portable between brainstems is an egg cartridge, identified by its schema kind. Same `.egg` extension, same rappzoo Pokédex shelf, same drag-drop UX. Adding a new portable artifact kind = adding a row to this table.

#### 18.10.1 The cartridge family table

| Schema | Kind | Container | Payload shape | Hatcher route → destination | Status |
|---|---|---|---|---|---|
| `brainstem-egg/2.2-organism` | `organism` | ZIP | rappid + soul + .env + agents + organs + senses + services + .brainstem_data | hatch into `~/.rapp/twins/<rappid>/` (full instance) | shipping |
| `brainstem-egg/2.2-rapplication` | `rapplication` | ZIP | rappid + agent.py + UI + per-rapp state | install as a planted rapp under host brainstem | shipping |
| `brainstem-egg/2.3-session` | `session` | JSON | rappid + runtime payload (HTML/JS) + transcript + participants | mount in rappterbox console iframe (or `pages/vbrainstem.html` standalone) | shipping |
| `brainstem-egg/2.3-neighborhood` | `neighborhood` | ZIP | rappid + neighborhood.json + members.json + agents/ + rapplications/ + ses/ + soul.md + CONSTITUTION.md + rar/index.json | mint a new GitHub repo (or local mirror) acting as a neighborhood gate (public-substrate form) | planned (this row is the *public-substrate* form: a GitHub-resident gate); shipping equivalent for local-substrate LAN snapshots is `rapp-egg/2.0 scale=neighborhood` — see §18.10.5 and [`NEIGHBORHOOD_EGG_SPEC.md`](./NEIGHBORHOOD_EGG_SPEC.md) |
| `brainstem-egg/2.3-estate` | `estate` | ZIP | public discovery surface + private "bones" repo pointer + sealed PII pointer | re-anchor the operator's whole multi-tier identity on a new substrate | planned |

The full cartridge spec lives at [`kody-w/rappterbox/carts/SCHEMA.md`](https://github.com/kody-w/rappterbox/blob/main/carts/SCHEMA.md). Master packers/unpackers for the ZIP variants live at [`rapp_brainstem/utils/bond.py`](https://github.com/kody-w/RAPP/blob/main/rapp_brainstem/utils/bond.py). The session variant is JSON-only because its payload is structurally one runtime + one transcript (no directory tree to compress).

#### 18.10.2 Routing discipline — `egg_hatcher_agent.py`

The kernel agent at [`rapp_brainstem/agents/egg_hatcher_agent.py`](https://github.com/kody-w/RAPP/blob/main/rapp_brainstem/agents/egg_hatcher_agent.py) is the canonical hatcher. Drop into any brainstem, restart, the LLM gets a `HatchEgg(egg_path=...)` tool. The hatcher accepts a local file path OR a URL, opens the cartridge, **introspects** `manifest.schema` / `manifest.type`, and dispatches:

```
organism / rapplication  → utils.bond.hatch_*
session                  → returns mount URL (rappterbox console / vbrainstem.html)
                           — Python brainstem can't iframe; tells the operator
neighborhood             → manual GitHub-mint instructions (auto on roadmap)
estate                   → manual substrate-migration instructions (auto on roadmap)
unknown                  → REFUSES, never destructive fallback
```

**The hatcher never guesses.** Unknown cartridge kinds get a clear "I don't know how to hatch this" reply with the cartridge family table; never a silent or destructive fallback.

#### 18.10.3 Compatibility with §8 (HTTP Surface)

The egg cartridge family lives at the **storage / transport layer**, not the HTTP layer. No new `/chat`-style endpoints are introduced. The hatcher is invoked via the existing tool-call surface (`/chat` → LLM → tool_call → `HatchEgg(...)`) — same dispatch any v1 agent uses. §8's frozen endpoints are untouched.

#### 18.10.4 Compatibility with §0 (Sacred Tenet)

The hatcher itself is a **single-file agent** that conforms to §5. It satisfies the agent contract (`name`, `metadata`, `perform()`) and travels via §0's distribution unit. The cartridge family is the *output* of agents (when packing) and the *input* (when hatching) — agents themselves remain the unit.

#### 18.10.5 The `rapp-egg/2.0` multi-scale schema (additive extension)

> **Added 2026-05-18.** Beyond the v1 agent contract, agents and aggregates may be packaged and distributed as `rapp-egg/2.0` cartridges. An egg's `manifest.json` declares its `scale`, which determines the hatch path. The generic single-file hatcher `twin_egg_hatcher_agent.py` (RAR: `@kody/twin_egg_hatcher`, public mirror: [`kody-w/twin-egg-hatcher`](https://github.com/kody-w/twin-egg-hatcher)) introspects the manifest and dispatches per scale. This is a strict superset of §18.10.1 — every existing cartridge kind has a corresponding `scale`, and the table is extensible without touching the v1 agent contract.

| `scale` | Hatches into | Notes |
|---|---|---|
| `agent` | host brainstem's `agents/` | One single-file `*_agent.py`, the §5 unit. |
| `twin` | `~/.rapp/twins/<hash>/` | A child brainstem identity (`rappid.json` + `soul.md` + `agents/`). Federated by the kernel's `twin_agent.py`. |
| `brainstem` | a fresh `~/.brainstem/` install | A full kernel instance — the §0/§4 Tier 1 unit. |
| `neighborhood` | `~/.rapp/neighborhoods/<hash>/` (legacy local mirror) OR — for snapshot-style federation eggs — local + peer assets per [`NEIGHBORHOOD_EGG_SPEC.md`](./NEIGHBORHOOD_EGG_SPEC.md) §8 | Roster + shared agents + gate (per [Part Deux §1–§3 of the Master Plan](../../MASTER_PLAN.md)).  Snapshot/hatch implementation shipping 2026-05-18: [[Neighborhood Egg — Snapshot and Hatch]]; matched-pair agents `NeighborhoodSnapshot` + `NeighborhoodRun` (canonical home [`kody-w/rappLocalFirstFleet`](https://github.com/kody-w/rappLocalFirstFleet)).  Two hatch targets: `in-place` (SSH-push peers) and `local-simulate` (extract peers into `~/.rapp/simulated/<peer>/twins/`). |
| `swarm` | a Tier 2 Function App | The cloud deployment unit (§4 Tier 2). |
| `factory` | a multi-tenant brainstem cluster | Aggregate of swarms; planned. |
| `industry` | a federation of factories | Cross-org aggregate; planned. |
| `estate` | a re-anchored multi-tier operator identity | Substrate migration (per §18.10.1 estate row). |

See [[The Federated Twin Egg Hatcher Pattern]] for the worked end-to-end pattern (the four-twin AIBAST federation: Heimdall, @kody-w, Bots in Blazers, AIBAST). The v1 agent contract (§5) and the wire contract (§0.1) are untouched — `rapp-egg/2.0` is a packaging/distribution layer that sits *above* the agent file, not inside it.

---

### 18.11 vBrainstem — multi-participant browser-tab session primitive

> **Added 2026-05-10.** The vBrainstem is a public web surface at [`pages/vbrainstem.html`](https://github.com/kody-w/RAPP/blob/main/pages/vbrainstem.html) (live: `https://kody-w.github.io/RAPP/pages/vbrainstem.html`) that hosts a multi-participant collaboration session inside one browser tab. Two devices pair via QR + WebRTC; both screens stay synced; an autonomous Coordinator twin can drive a structured workflow on the operator's behalf. The session is a `brainstem-egg/2.3-session` cartridge per §18.10 — exportable, replayable, transferable.

#### 18.11.1 Roles + transport stack

| Layer | Choice | Why |
|---|---|---|
| Signaling | PeerJS public broker (`peerjs.com`) via CDN `unpkg.com/peerjs@1.5.4` | Free, hosted, cross-network, no infra to deploy. Replaceable later by self-hosted signaling without changing the rest. |
| Data channel | WebRTC ordered reliable | Built into PeerJS. DTLS-SRTP encrypted. Broker drops out after handshake. |
| Identity (per session) | ECDSA P-256 keypair generated in-browser | Public key fingerprint embedded in the QR; safety-code derivation lets users eyeball-MITM-check before chat starts |
| QR rendering | `qrious` (canvas, explicit pixel size) | The earlier qrcode-generator with `scalable: true` produced a 0×0 SVG; qrious draws into a real `<canvas>` |

**Two roles:** `host` (Mac, no URL params — owns the LLM dispatch) and `guest` (phone, URL has `?pair=ID&fp=FINGERPRINT` — observer + input source, relays chat through the host over WebRTC). Joiners never need their own LLM access.

#### 18.11.2 LLM backend selection

vBrainstem has three exchangeable LLM backends, all behind the same internal `Doorman.chat({ system, history, message })` API:

| Param | Backend | Notes |
|---|---|---|
| *(default)* | Local kernel at `http://localhost:7071/chat` | Best for tab-based collab — real `/chat` with full agent tool routing, no Copilot subscription gate. Joiner (phone) relays LLM calls through the host. |
| `?brainstem=<URL>` | Custom local kernel | Use a different port or a remote brainstem under operator control. |
| `?copilot=1` | GitHub Copilot via [`worker/`](https://github.com/kody-w/RAPP/blob/main/worker/) (Doorman) | No localhost dependency. Uses Pyodide-loaded Python agents in-browser as tools (HackerNews, ManageMemory, ContextMemory). Same `RAPP.Doorman` namespace as `pages/sphere.html` (§4 Tier 1 with no localhost). Requires active Copilot subscription on the GitHub account. |

The page-side Pyodide loader fetches `basic_agent.py` + the canonical agents from `raw.githubusercontent.com/kody-w/RAPP/main/rapp_brainstem/agents/` and runs them in-browser when in `?copilot=1` mode. Same agent contract (§5); same `metadata` → OpenAI tool def mapping.

#### 18.11.3 The Coordinator persona

A new role tag joins `operator` / `twin` / `observer`: **`coordinator`**. The Coordinator is the operator's autonomous twin — it issues operator-shaped messages on the operator's behalf so the operator can watch a workflow execute on both screens without typing. The bundled debate-demo workflow ("Reporter fetches HN top story → DebaterA argues for → DebaterB argues against → Editor synthesizes a 5-line newsletter") is driven entirely by the Coordinator.

The Coordinator is one of N participants in the cartridge's `participants[]` array — not a special construct. Other workflows can substitute different driver personas without code changes.

#### 18.11.4 Transcript-as-state + cartridge round-trip

Every event (operator input, twin response, demo-step marker, agent tool dispatch, mic interjection) is appended to the transcript, broadcast over the data channel, and persisted to `localStorage` keyed by session id. Reload hydrates from the cache. **The transcript IS the saved state** — there's no separate "save game" record because every action that produced state is in the transcript.

"Export cart" packs the live page (HTML+JS verbatim, sha256-pinned) + transcript + participants into a `brainstem-egg/2.3-session` cartridge. Drop the resulting `.egg` into the rappterbox console (or back into vbrainstem.html via a future hatch path) → the session reanimates at the captured event index.

#### 18.11.5 Storage edge case — Edge Tracking Prevention

Edge with Tracking Prevention enabled silently blocks `localStorage` on origins it heuristically classifies. The vBrainstem detects this at boot via a probe (`isStorageBlocked()`) and falls back to an in-memory mirror of the auth settings (`_memSettings`) so the session works for the tab lifetime even when localStorage is unavailable. Tradeoff: token doesn't persist across reloads on Edge with strict TP. Page surfaces a yellow warning when the condition is detected, with the exact path to add an exception (Edge → Privacy → Tracking Prevention → exceptions → add `kody-w.github.io`).

#### 18.11.6 Compatibility with v1

- **§5 (Agent Contract):** Untouched. The Pyodide-loaded agents are exactly v1 single-file agents (HackerNewsAgent, ManageMemoryAgent, ContextMemoryAgent — same files used by Tier 1).
- **§8 (HTTP Surface):** Default backend hits the unchanged Tier 1 `/chat` endpoint. No new endpoints required.
- **§4 (Three Tiers):** vBrainstem is *not* a fourth tier — it's a presentation surface. The actual LLM tier remains Tier 1 (local), Tier 2 (cloud), or the Doorman path (which is a Tier 1-equivalent backed by Copilot). The cartridge round-trip means a session captured against any tier replays in any tier.
- **§14 (Versioning):** New optional URL params (`?pair`, `?fp`, `?brainstem`, `?copilot`) per "new optional configuration variables." No breaking changes.

#### 18.11.7 Cross-reference

Patent context (private, not for public spec): WH-2026-002 §7.21 covers the cartridge-as-workflow-session-with-embedded-runtime; §7.22 covers recursive iframe sub-tether (planned); §7.23 covers multi-participant browser-tab with operator-mic priority intervention. See [`kody-w/wildhaven-ceo/legal/patent/WH-2026-002-rappterbox-claim-cluster.md`](https://github.com/kody-w/wildhaven-ceo/blob/main/legal/patent/WH-2026-002-rappterbox-claim-cluster.md) (collaborator-gated).

---

_§18 added 2026-04-24; §18.10–§18.11 added 2026-05-10. Future addenda
append below this line only; edits to §0 through §17 are v2 work._

---

### 18.12 Companion documents — the rest of the picture

> **Added 2026-05-10.** SPEC.md is the **agent contract + tier model**. The system has grown around it. This index points at the load-bearing companion documents and the Constitutional articles shipped since SPEC was memorialized — so any reader landing on the god spec can find what the god spec deliberately doesn't cover.

#### 18.12.1 Architecture-level companion docs (root-of-repo)

| Doc | Purpose | When to read it |
|---|---|---|
| [`HERO_USECASE.md`](https://github.com/kody-w/RAPP/blob/main/HERO_USECASE.md) | The canonical scenarios the platform must satisfy: Charizard-in-the-woods (offline pair), Dream Catcher (parallel-dimension reassimilation), Mom's Mixtape, Pizza Place. Status table per scenario. | Before proposing any structural change — every PR is judged against whether ✅ rows still pass. |
| [`ECOSYSTEM.md`](https://github.com/kody-w/RAPP/blob/main/ECOSYSTEM.md) | End-to-end layout of a planted organism: file structure, identity stack, surfaces, memory tiers, MMR, evolution, eggs, integrity, Dream Catcher, network modes, surface inventory. | When you need the architecture-level "how does the whole thing fit together." |
| [`ECOSYSTEM_MAP.md`](https://github.com/kody-w/RAPP/blob/main/ECOSYSTEM_MAP.md) | Single canonical synthesis: schemas, files, decision table, drift gaps. The index that points at the rest. | First — it points at all other specs. |
| [`OSI.md`](https://github.com/kody-w/RAPP/blob/main/OSI.md) | The 7-layer model: substrate / identity / discovery / channels / trust / envelope / application. Each layer has schemas, impl files, tests. | When figuring out which layer a new feature belongs to. |
| [`ANTIPATTERNS.md`](https://github.com/kody-w/RAPP/blob/main/ANTIPATTERNS.md) | What we will never do. Locked rules: ONE term for the plugin unit (always `agent`), frozen kernel never moves, no half-released-feature shims, no fallback to "RAPP"/"AI assistant" branding, no network calls without local-first fallback. Append-only. | Before proposing a refactor that adds a new term or changes an established convention. |
| [`NEIGHBORHOOD_PROTOCOL.md`](https://github.com/kody-w/RAPP/blob/main/NEIGHBORHOOD_PROTOCOL.md) | Twin chat protocol, three concentric trust scopes (personal / neighborhood / public swarm), four channel types (WebRTC tether, Issues, PRs, raw-fetch), four exchange primitives, granular permissions, adversarial walkthrough. | Before adding any cross-organism communication. |
| [`SUBSTRATE_FEDERATION.md`](https://github.com/kody-w/RAPP/blob/main/SUBSTRATE_FEDERATION.md) | How organisms talk across substrates (GitHub ↔ GitLab ↔ Codeberg ↔ LAN-mesh ↔ AirDrop). Egg cartridges as the substrate-agnostic transport. | When considering anything that assumes "GitHub is the substrate." |
| [`SURVIVAL.md`](https://github.com/kody-w/RAPP/blob/main/SURVIVAL.md) | Disaster-recovery, kernel rebirth, lineage continuity. What it takes for a planted organism to survive substrate loss / kernel deprecation / operator absence. | When making changes that affect long-term durability. |
| [`MASTER_PLAN.md`](https://github.com/kody-w/RAPP/blob/main/MASTER_PLAN.md) | The strategic plan — what's coming next, in what order, why. | For roadmap context (not contractual; subject to change). |

#### 18.12.2 Other specs in `pages/docs/`

| Spec | Authority | Cross-reference |
|---|---|---|
| [`ESTATE_SPEC.md`](https://github.com/kody-w/RAPP/blob/main/pages/docs/ESTATE_SPEC.md) | The two-tier estate (public discovery + private bones), substrate-agnostic identity continuity. Authority for door catalog + rappid-as-global-address. | Article XLVI, Article XLVIII |
| [`PUBLIC_PRIVATE_BOUNDARY.md`](https://github.com/kody-w/RAPP/blob/main/pages/docs/PUBLIC_PRIVATE_BOUNDARY.md) | The three-tier estate (public discovery / private bones / on-device PII). PII never in repo by default; four explicit override paths. Workbench primitive. | Article XLVIII, Article XLIX |
| [`rapplication-sdk.md`](https://github.com/kody-w/RAPP/blob/main/pages/docs/rapplication-sdk.md) | Rapplication best practices: agent-first rule, sneakernet portability invariant (2 files, drag+chat, no shell commands, docstring-as-readme). | §5, §18.5–§18.8 |
| [`AGENTS.md`](https://github.com/kody-w/RAPP/blob/main/pages/docs/AGENTS.md) | Detailed agent authoring guide. Companion to §5. | §5 |
| [`VERSIONS.md`](https://github.com/kody-w/RAPP/blob/main/pages/docs/VERSIONS.md) | Schema version registry. | §14 |
| [`skill.md`](https://github.com/kody-w/RAPP/blob/main/pages/docs/skill.md) | Universal "feed me to any AI" onboarding runbook. The 6-step new-citizen path. | §12 (RAR) |
| [`ROADMAP.md`](https://github.com/kody-w/RAPP/blob/main/pages/docs/ROADMAP.md) | Per-version near-term plans. | §15 |
| [`SUBSTRATE_FEDERATION.md`](https://github.com/kody-w/RAPP/blob/main/pages/docs/SUBSTRATE_FEDERATION.md) | (Same content as root-level — the doc moved during reorganization; both paths work.) | Article XLVII.5 |
| [`TWIN_LIFECYCLE_SPEC.md`](https://github.com/kody-w/RAPP/blob/main/pages/docs/TWIN_LIFECYCLE_SPEC.md) | Operator-level twin lifecycle: `active / archived / purged` states, disk layout, agent verbs (`archive`, `unarchive`, `purge`, `list_archived`, `list_purged`), tombstone schemas, snapshot interactions, estate-wide fanout. | Article XLIX.3, §18.13 |

#### 18.12.3 Constitutional articles shipped after SPEC was memorialized

SPEC.md was frozen 2026-04-17. The Constitution kept moving. Articles XL–XLIX codify primitives that the agent contract (§5) and tier model (§4) take for granted but don't themselves explain.

| Article | Title | What it codifies |
|---|---|---|
| XL | Secure-First Plant, Operator-Curated Promotion Later | Plant defaults to private; operator promotes to public via deliberate action. |
| XLI | The Operator's Experience Is Conversation | Never a token, never a terminal. The brainstem speaks plain English. |
| XLII | The Virtual Brainstem Is For Mobile Users | Doorman page (`rapp_brainstem/utils/web/index.html`) carries Tier 1 to mobile via GitHub Raw + Issues + PeerJS, no install. |
| XLIII | Voice In, Voice Out | TTS+STT is a hard requirement at Tier 1, not a feature. The `\|\|\|VOICE\|\|\|` slot is sacred. |
| XLIV | Neighborhood Collaboration Is Local-First, Cross-Device-Transparent | The "Doorbell" pattern — one operator's organism notifies another's without a server in between. |
| XLV | The Sphere Is The Front Door | `pages/sphere.html` — implicit doorman summon via 3D sphere tap. Voice-first. |
| XLVI | Rappid Is The Global Address (Estate Is The Door Catalog) | Every organism has one address; estate maps addresses to URLs by string parsing. |
| XLVII | Discoverability Without A Central Registry | Publishing IS the signal. Substrate-agnostic federation (XLVII.5). |
| XLVIII | Public Discovery, Private Substance — the Two-Tier Estate Is Mandatory | Tightened to three-tier in `PUBLIC_PRIVATE_BOUNDARY.md` — PII never in repo by default. |
| XLIX | A Twin Is A Persistent AI Presence With An Address And A Workbench | Twin lifecycle (mint → bond → fork → die), workbench primitive, sibling-peek. Operator-housekeeping refinement in §18.13 + `TWIN_LIFECYCLE_SPEC.md`. |

#### 18.12.4 What SPEC.md deliberately does NOT cover

The god spec stays narrow on purpose. Each of these is real platform surface, fully documented elsewhere, and intentionally NOT pulled into SPEC:

- Egg packing/unpacking semantics (→ `rapp_brainstem/utils/bond.py` + §18.10 family table)
- Identity migration and operator key custody (→ `ESTATE_SPEC.md`, `SURVIVAL.md`)
- LAN federation (Bonjour, AirDrop hand-offs) (→ `SUBSTRATE_FEDERATION.md`, Article XLVII.5)
- Cross-organism trust scopes / exchange primitives (→ `NEIGHBORHOOD_PROTOCOL.md`)
- The OSI 7-layer mapping (→ `OSI.md`)
- Holocard schema, RAR sealing, Binder ECDSA wallet (→ `pages/vault/Architecture/`)
- Rappterbox console (the iframe-mount surface for session cartridges) (→ `kody-w/rappterbox/`)
- Patent claim language (→ `kody-w/wildhaven-ceo/legal/patent/`, collaborator-gated)

Reading order if you're new and just landed on SPEC.md: SPEC § 0–5 (the contract) → `HERO_USECASE.md` (what must work) → `ECOSYSTEM_MAP.md` (the index) → `OSI.md` (the layer model) → drill into specific specs as needed.

---

### 18.13 Twin operator lifecycle (active / archived / purged)

> **Added 2026-05-19.** Operator-housekeeping refinement of Constitution Article XLIX.3 (`mint → bond → fork → die`). XLIX.3 establishes the philosophical states; this section names the disk layout and agent verbs that let an operator manage a twin estate cleanly across many twins on many machines. "Die" in XLIX.3 corresponds to `purge` here. `archive` is a new operator-level intermediate state — a twin set aside, body preserved, reversible — that XLIX.3 implicitly allows but doesn't formalize. Full schemas in [`TWIN_LIFECYCLE_SPEC.md`](https://github.com/kody-w/RAPP/blob/main/pages/docs/TWIN_LIFECYCLE_SPEC.md). Narrative in [`pages/vault/Architecture/Twin Lifecycle — Active, Archived, Purged.md`](https://github.com/kody-w/RAPP/blob/main/pages/vault/Architecture/Twin%20Lifecycle%20%E2%80%94%20Active%2C%20Archived%2C%20Purged.md).

#### 18.13.1 States and disk layout

| State | Disk location | In default `list` | In default snapshot eggs | Reversible |
|---|---|---|---|---|
| `active` | `~/.rapp/twins/<hash>/` | yes | yes | n/a |
| `archived` | `~/.rapp/twins/.archive/<hash>/` (workspace intact + `archived.json`) | no (`list_archived`) | no (`include_archived=true`) | yes (`unarchive`) |
| `purged` | `~/.rapp/twins/.purged/<hash>.json` (tombstone only; body removed) | no (`list_purged`) | never | NO |

Transitions: `active → archived → purged`. No direct `active → purged`; archive is the safety rail.

#### 18.13.2 Scanner rule (companion to §5 discovery)

`_scan_twins()` in `twin_agent.py` MUST skip any direct child of `~/.rapp/twins/` whose name starts with `.`. This formalizes the dotdir convention (`.archive/`, `.purged/`, `.cache/`, `.staging/` are all reserved at zero cost) and fixes a latent bug where the historical `.trash/` stub appeared as a phantom twin in `Twin action=list`.

#### 18.13.3 Agent verbs (Twin agent)

| Action | Form | Notes |
|---|---|---|
| `archive` | single (`rappid_uuid`) or bulk (`filter` + `confirm`) | Bulk is dry-run unless `confirm=true`. Running twins are stopped first; no `force` flag. |
| `unarchive` | single only | Does not auto-boot. |
| `purge` | single only | Requires `confirm=true`. Only valid on already-archived twins. Irreversible. |
| `list_archived` | — | Enumerates `.archive/` with tombstone metadata. |
| `list_purged` | — | Enumerates `.purged/` ledger. |

Filter clauses: `kind`, `name_prefix`, `name_regex`, `stopped_for_days`, `exclude_kinds`. Conjunctive. Unknown clauses MUST be rejected (no silent skip).

#### 18.13.4 Tombstone schema

`archived.json` (schema `rapp-twin-tombstone/1.0`) is written into the archived workspace. `.purged/<hash>.json` (schema `rapp-twin-purged/1.0`) is written when a twin is purged. The purge ledger is the local-brainstem realization of Constitution XLIX.3's required tombstone. Full schemas in `TWIN_LIFECYCLE_SPEC.md` §4 and §5.

#### 18.13.5 Snapshot / hatch interactions

- `NeighborhoodSnapshot` default: active only. Opt-in `include_archived=true` packs `.archive/`. `.purged/` ledgers never travel.
- `NeighborhoodRun.hatch` default: restore active only. Opt-in `restore_archived=true` lays archived entries into the target host's `.archive/` without auto-unarchive.
- Egg manifest's `twins[]` array gains `lifecycle: "active" | "archived"` per entry. Missing field reads as `"active"` (backwards-compatible with pre-2026-05-19 eggs).

#### 18.13.6 Estate-wide fanout

`Fleet action=archive_estate` composes `Twin action=archive` against every peer in `~/.rapp/peers.json` via the existing SSH carrier from `NeighborhoodRun`. Dry-run by default. No atomic rollback — partial archive is recoverable because archive is reversible. No estate-wide `unarchive` or `purge` in v1.0; those stay deliberate per-host.

#### 18.13.7 Consistency with prior specs

- **Constitution Article XLIX.3:** elaborates rather than contradicts. "Die" = `purge`. Tombstone requirement is satisfied by `.purged/<hash>.json`.
- **Article XLVII:** preserved. The rappid of a purged twin remains globally addressable; purging removes the local body, not the substrate identity.
- **§18.10 (egg cartridge family):** snapshot eggs gain an opt-in flag without changing the schema family.
- **Article XLI (Conversation):** all verbs flow through `/chat` in natural language. No new HTTP endpoints, no slash commands.

#### 18.13.8 Migration

Implementations encountering a legacy `~/.rapp/twins/.trash/<hash>/` dir SHOULD migrate it to `~/.rapp/twins/.archive/<hash>/` with a synthesized `archived.json` (`archived_by: "migration"`). The historical empty `.trash/` stub MAY be removed.
