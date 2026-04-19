# Per-swarm soul

The brainstem's system prompt — its "soul" — is canonical and global. Every chat turn uses the same SOUL constant compiled into the brainstem JS. Same XML structure (`<identity>`, `<agent_usage>`, etc.). Same persona, same rules, same tier-2 install one-liner. We pinned it on purpose: the two surfaces (local Python brainstem + virtual browser brainstem) share one canonical voice that can never drift.

But every swarm deploy bundle includes the soul:

```json
{
  "schema": "rapp-swarm/1.0",
  "name": "sales-swarm-9",
  "purpose": "B2B sales acceleration agents",
  "soul": "<soul>...the canonical SOUL...</soul>",
  "agents": [...]
}
```

Right now the swarm server *stores* the soul in the manifest but doesn't *use* it. Agents are executed individually via `/api/swarm/{guid}/agent` — there's no chat loop on the server side, no system prompt assembly happening. The soul is dead weight on disk.

What if it weren't?

**The proposal:**

Per-swarm soul means: when (eventually) the swarm server gains a `/api/swarm/{guid}/chat` endpoint that runs the full LLM loop server-side, it uses *the swarm's own soul* as the system prompt — not the brainstem's canonical soul, not whatever soul the caller injected.

So a "Sales swarm" deployed with a sales-flavored soul gets:
- `<identity>` declaring it's a sales-AI assistant.
- `<personality>` tuned to "concise, focused on commercial outcomes."
- `<knowledge>` specific to the company's product line.
- `<agent_usage>` rules unchanged (these are the universal honesty constraints).

A "Support swarm" deployed by the same user with a support-flavored soul gets:
- `<identity>` as a customer-support AI.
- Different `<personality>` tone.
- Different `<knowledge>` about support workflows.
- Same `<agent_usage>` rules.

Both swarms run on the same endpoint. They have different agents AND different personas. The system prompt is part of what makes them *the same swarm* across calls.

**Why this is interesting:**

Today, "deploying a swarm" is "deploying agents." With per-swarm soul, it's "deploying agents AND the persona that uses them." That's a much more complete unit. A swarm isn't just code; it's also voice, expertise, and the framing the LLM uses when calling its tools.

**What changes in the implementation:**

When the brainstem's Deploy modal builds a bundle, it includes the *current* soul. Today that's the canonical SOUL. With per-swarm soul, it could include user-customized text in addition to the SOUL_* core blocks. We'd reintroduce a textarea or a structured editor in the Deploy modal — but scoped to the SWARM, not to the brainstem's global setting. (See "Why we don't ship a soul.md editor anymore" — the scope difference is the key.)

The bundle's `soul` field becomes meaningful: it's THIS swarm's persona, baked in.

When (eventually) the swarm server gains `/api/swarm/{guid}/chat` that runs the LLM loop, it reads the manifest's `soul` and uses it as the system prompt. Different swarm, different soul, different conversation tone — even though the agents underneath might overlap.

**What stays canonical:**

The `<agent_usage>` rules. The honesty constraints — "NEVER pretend you've executed an agent," "ALWAYS trust the schema" — are universal. They prevent fabrication regardless of swarm. The bundle should include them by reference (not as something a user can edit), or the deploy step should automatically inject them on top of the user-provided soul.

We'd ship a "soul template" — a base XML structure with required blocks (`<agent_usage>`, `<response_format>`, `<boundaries>`) and optional blocks the user can customize (`<identity>`, `<personality>`, `<knowledge>`). The deploy modal's soul editor lets you write the optional blocks; we splice them into the required scaffolding.

**The future this unlocks:**

Once swarms have their own souls, you can deploy a swarm publicly and let other people chat with it. They get *your* soul-defined voice plus the agents you packaged. It's not "here's some agents you can call"; it's "here's a complete AI assistant for this domain, deployable in one click."

Imagine a "DevOps assistant" swarm: agents for AWS / Kubernetes / Datadog / PagerDuty, and a soul that says "you are a senior SRE who answers questions tersely and prefers data over speculation." Or a "writing coach" swarm with grammar / style / fact-check agents and a soul that says "you are a patient editor who flags issues without rewriting." The agents are the capabilities; the soul is the tone they're deployed with.

**Why we haven't built this yet:**

The swarm server doesn't currently run LLM loops (see "Why the swarm server doesn't make LLM calls"). Per-swarm soul only matters once it does. The work is two-step: first ship server-side LLM execution, then make the soul source-of-truth shift to the swarm's manifest.

When we build server-side chat, this is part of the same patch. Until then, the soul field in the bundle is reserved for this future. It's intentionally there, even though nothing reads it.

The bundle is more than a code drop. It's a complete deployable assistant. Adding the soul makes that explicit.
