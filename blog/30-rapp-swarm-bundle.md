# `rapp-swarm/1.0`: a portable swarm bundle

When you click "Deploy as Swarm" in the brainstem, what gets generated is one JSON file: `<swarm-name>.swarm.json`. The whole swarm — every agent, the system soul, the manifest — is in there. You can email it. Drop it on a thumb drive. Send it through Slack. Anywhere with a swarm endpoint listening at `/api/swarm/deploy` will install it.

Here's the schema (`rapp-swarm/1.0`):

```json
{
  "schema": "rapp-swarm/1.0",
  "name": "sales-swarm-9",
  "purpose": "B2B sales acceleration agents (account intel + deal progression)",
  "created_at": "2026-04-19T03:14:00.000Z",
  "created_by": "wildfeuer05",
  "soul": "<soul>...the canonical RAPP soul...</soul>",
  "agent_count": 9,
  "agents": [
    {
      "filename": "account_intelligence_agent.py",
      "name": "AccountIntelligence",
      "display_name": "Account Intelligence",
      "description": "360° account briefings ...",
      "source": "import json\nfrom agents.basic_agent import BasicAgent\n\n__manifest__ = {...}\n\nclass AccountIntelligenceAgent(BasicAgent):\n    ...",
      "sha256": "48010aaae45ac5e099bea276e3b90b10ee9e2e6ab03722f59f423c0d0034cc0c"
    },
    ...
  ]
}
```

Three properties you'd want from any "deployable bundle" format and what we did about them:

**Self-contained.** Every agent's `.py` source is in the bundle, verbatim. The receiver doesn't need to fetch anything else from any registry. Drop the JSON on an air-gapped server with a swarm runtime and it works. The trade is that bundles are bigger than "just a list of agent names" — but agents are small text files, and a typical 9-agent bundle is ~50KB. Fine.

**Versioned.** The top-level `schema: "rapp-swarm/1.0"` field lets future swarm endpoints recognize "this is the format we know how to install." When we ship `1.1` (with packs, or per-swarm configuration, or whatever), endpoints can keep accepting `1.0` bundles indefinitely while also accepting newer ones.

**Auditable.** Each agent ships its own SHA-256. The receiving endpoint can verify "this agent file matches its declared hash." More importantly, two bundles claiming to deploy the same agent have provably-different content if the hashes differ. You can grep your bundles for a known-bad agent hash and find every swarm that has it.

**What's NOT in the bundle:**

- **Memory.** The bundle is what the swarm *does*, not what it *remembers*. Memory is per-tenant, accumulated over time, not transferable as part of an agent definition. (You can deploy the same swarm twice and the two instances start with empty memory.)

- **Per-tenant config.** The soul is the canonical one; we don't ship a per-user system prompt. (See "Why we don't ship a soul.md editor" — same logic.)

- **Credentials.** The swarm endpoint doesn't make LLM calls (see "Why the swarm server doesn't make LLM calls"), so there are no credentials to bundle in the first place.

**Three ways to install a bundle:**

```bash
# 1. Direct push from the brainstem (Settings → Deploy as Swarm → Push to endpoint)
# Brainstem POSTs the bundle JSON to /api/swarm/deploy

# 2. Curl from disk (anywhere)
curl -X POST http://localhost:7080/api/swarm/deploy \
     -H 'Content-Type: application/json' \
     --data-binary @sales-swarm-9.swarm.json

# 3. Brainstem's "Download bundle" → manual sneakernet → curl on the destination
```

All three end up writing the same files to the same directory layout on the swarm server (`swarms/{guid}/agents/*.py`, `swarms/{guid}/manifest.json`).

**Why one file vs. one zip:**

We considered a zip with one .py per file. Decided against it because:

- JSON is browser-native. A bundle generated in the browser can be `JSON.stringify`-ed and uploaded with no extra dependencies. Zip needs a library.
- Inspectability. `cat sales-swarm-9.swarm.json | jq .agents[0].source` shows you the agent's code. With a zip you'd have to extract first.
- One file is one file. Email-attachable, gist-pasteable, version-controllable as a single line.

The cost is that the source code is a JSON-escaped string with `\n` for newlines. Editors like VS Code render that fine; humans reading raw JSON don't. We accept the tradeoff because the audience for raw bundle inspection is small and the audience for "drop a bundle into Slack" is everyone.

A bundle is a swarm in transit. The server is what makes it run. Two formats, one wire.
