# What an `agent_pack.json` looks like

The RAR registry has a "stack" concept that's currently informal. The `account_intelligence_stack` contains nine related agents — Account Intelligence, Stakeholder Intelligence, Competitive Intelligence, Risk Assessment, etc. — that work together. Today they're just nine separate registry entries, installed individually. There's no way to say "give me the whole stack" in one click.

`agent_pack.json` is the proposed bundling format. A pack is a manifest pointing at agents that are designed to work together, with metadata about why they belong in the same group.

```json
{
  "schema": "rapp-pack/1.0",
  "name": "@aibast-agents-library/account_intelligence_stack",
  "display_name": "Account Intelligence Stack",
  "version": "1.2.0",
  "description": "Nine agents that together produce 360° account briefings — stakeholder mapping, competitive intel, deal risk, next-best-action.",
  "author": "AIBAST",
  "category": "b2b_sales",
  "agents": [
    "@aibast-agents-library/account_intelligence",
    "@aibast-agents-library/account_intelligence_orchestrator",
    "@aibast-agents-library/stakeholder_intelligence",
    "@aibast-agents-library/competitive_intelligence",
    "@aibast-agents-library/deal_tracking",
    "@aibast-agents-library/meeting_prep",
    "@aibast-agents-library/messaging",
    "@aibast-agents-library/risk_assessment",
    "@aibast-agents-library/action_prioritization"
  ],
  "orchestrator": "@aibast-agents-library/account_intelligence_orchestrator",
  "data_flow": "the orchestrator calls the specialists in parallel, merges their data_slush, and produces the briefing. Specialists can also be called individually."
}
```

Three keys do the actual work:

**`agents`** is the list of fully-qualified agent names. The brainstem looks each one up in its existing registry sources (RAR, custom repos), fetches the `.py` file, mints a card, adds to the binder. Same install path as today — just batched.

**`orchestrator`** names the one agent in the pack that's designed as the entry point. The LLM sees all the pack's agents in its tools list, but the orchestrator is the one with the "calls the others" pattern. UIs can highlight it (a star, a different card frame, a badge).

**`data_flow`** is human-readable. It's the README of the pack. When a user installs the pack, this is what they read to understand "what does this pack do, and how do its pieces fit together."

**Pack distribution:** packs live alongside agents in registry repos. RAR's `registry.json` already has the `_stack` field on each agent. Adding a `packs` array to the registry document gives the brainstem's Browse panel a "by pack" view alongside "by agent."

```json
{
  "schema": "rapp-registry/1.0",
  "agents": [...],
  "packs": [
    { "name": "@aibast/account_intelligence_stack", "agents": [...], ... },
    { "name": "@aibast/deal_progression_stack", "agents": [...], ... }
  ]
}
```

**Install UX:** the brainstem's Browse panel shows pack rows above agent rows. Click "Install pack" and we install every agent in the pack's `agents` list. The pack itself becomes a "tag" on each card so the user can filter the binder by pack later.

**Why this matters:**

138 agents in RAR is hard to navigate one row at a time. People want to ask "which agents do I need for B2B sales account work?" not "give me 138 rows sorted alphabetically." A pack is the answer to that question, written by the people who built the agents.

Packs also become the natural unit for swarms. Today you click "Deploy as Swarm" and you bundle whatever's in your binder. With packs, you could click "Deploy account_intelligence_stack as a swarm" and get a single-purpose swarm without manually curating the binder first.

This is on the "we should build it" side. Probably half a day's work end-to-end. Worth doing once we have a second registry consumer pulling from RAR — at one consumer, the cost of organizing pays for itself only weakly. At three or four, it's a real win.
