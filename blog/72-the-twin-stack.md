# The Twin Stack v1: a name for what we built

For about a month we'd been building a thing without a name. There was the brainstem in the browser, the swarm server hosting hatched clouds, the T2T protocol for twin-to-twin chat, the sealing primitives for preservation, the registry for discovery, the hippocampus for graduated cloud runtime. Everything had its own piece — none of it had a coherent label.

Then the user said: "call this stack the Twin Stack."

That's it. That was the missing piece. Not the architecture — the architecture was already there. The *name*. With the name, the relationships between the pieces collapsed into a sentence: *the Twin Stack is the local-first, cloud-portable runtime for digital twins built out of single-file agents.*

**What's in it:**

| Layer | Component | What it does |
|---|---|---|
| Identity | `cloud_id` + `secret` | Every twin gets a HMAC-signable identity |
| Storage | per-twin `~/.rapp-twins/<name>/` | Isolated workspace per twin |
| Agents | `*_agent.py` (BasicAgent + `__manifest__`) | Sacred — same contract everywhere |
| Swarms | `rapp-swarm/1.0` bundles | Hatched into a workspace, hot-loaded |
| Brainstem | local stdlib `swarm/server.py` OR cloud `function_app.py` | Same wire surface, two runtimes |
| LLM | `swarm/llm.py` dispatch | Azure OpenAI / OpenAI / Anthropic / fake |
| Chat | `Assistant` class with tool-calling | Sacred OG CommunityRAPP pattern |
| Documents | `documents/` + `inbox/` + `outbox/` | Twins save and share files |
| T2T | HMAC-SHA256 signed envelopes | Twin-to-twin chat, doc share, capability invoke |
| Sealing | manifest mutation + chmod 444 | Make a twin immutable but queryable |
| Snapshots | frozen agents/ + memory/ copies | Time-travel a twin |
| Registry | `rapp-cloud-registry/1.0` JSON | One file = a marketplace + deploy unit |

**Five collaboration layers, named:**

- **A2A** — agent-to-agent inside one swarm, in-process, no auth (the LLM orchestrates)
- **S2S** — swarm-to-swarm inside one cloud, owner-consented
- **C2C** — cloud-to-cloud, same human, multiple clouds collaborate
- **T2T** — twin-to-twin between humans, HMAC-authenticated peer protocol
- **D2D** — daemon-to-daemon, the implementation underlayer carrying T2T

The user-facing language is T2T. D2D is the thing that actually moves the bytes. Both are real; both stay.

**Why a stack and not a "framework":**

A framework you import. A stack you *occupy*. The Twin Stack is the runtime your twin lives in — the operating environment for a digital identity that survives across devices, browsers, clouds, and (eventually) generations.

The thing you wrote a soul.md for runs in this stack. The agents you minted card-by-card run in this stack. The swarms you composed run in this stack. When you snapshot, when you seal, when you peer with your wife's twin, when you graduate from local to cloud — same stack. Same wire format. Same identity primitives.

**v1 means: it works end-to-end on one machine.**

Not "the architecture is documented." Not "the data model is defined." It *runs*. Two twins on this laptop, isolated workspaces, real Azure OpenAI gpt-5.4, HMAC-signed document share, cross-twin capability invoke. Verified by `bash hippocampus/twin-sim.sh demo hero` — a one-shot script that captures real `git log` output, sends it through Kody's twin, ships the brief to Molly's twin via T2T, and gets back a CEO-shaped strategic decision in 12 seconds.

**v2 will be: it works the same when one twin is on your laptop and the other is on your wife's phone.**

The wire format already supports it. The relay is the next blog post.
