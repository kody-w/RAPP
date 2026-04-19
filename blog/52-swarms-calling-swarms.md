# Swarms calling swarms

A swarm is a deployed bundle of agents at a known endpoint. The brainstem can call any swarm's agents over HTTP. By implication: a swarm's agent code can also call another swarm's agents over HTTP. There's no protocol restriction. There's not even any new code needed.

This is the composition story we haven't formalized yet, but it's already possible.

**Concrete example:**

You have two swarms:

- **`account-intel-swarm`** — your Tier 2-deployed account intelligence stack (9 agents from RAR's `@aibast/account_intelligence_stack`).
- **`reporting-swarm`** — your team's custom reporting stack (CRM data fetchers, chart generators, slide builders).

You want a single chat surface where asking "give me a Q3 briefing on Acme Corp" does both: the account-intel swarm produces the briefing, the reporting swarm formats it into a slide deck.

Today's path: install the union of all 14 agents in your brainstem's binder, let the LLM coordinate. Works. Has a downside: the brainstem now ships 14 tool schemas to the model on every chat turn, even when most of them aren't relevant. The system prompt grows. The model has to choose from a wider tool set.

**The swarms-calling-swarms path:**

You write one orchestrator agent (`acme_briefing_agent.py`) and install it in your brainstem. Its `perform()` does:

```python
def perform(self, **kwargs):
    company = kwargs.get('company')
    # Call account-intel-swarm's orchestrator
    intel = http_post(
        'http://swarm.local:7080/api/swarm/account-intel-guid/agent',
        {'name': 'AccountIntelligenceOrchestrator', 'args': {'company': company}}
    )
    # Pass the intel through to the reporting swarm
    deck = http_post(
        'http://swarm.local:7080/api/swarm/reporting-guid/agent',
        {'name': 'SlideBuilder', 'args': {'data': intel['output']}}
    )
    return json.dumps({'status': 'success', 'summary': '...', 'data_slush': {'deck_url': deck['url']}})
```

One agent in your brainstem. The model only sees `acme_briefing` as a tool. When invoked, it composes the work across two swarms behind the scenes. The model never knows about the 14 underlying agents — they're encapsulated.

**Why this matters:**

The cost of agent-tool-spec-pollution scales linearly with how many tools you expose. 14 tools is a lot of system-prompt real estate. Ten 14-tool stacks is too many. Each "compose stuff into a coherent thing" step you can hide behind one orchestrator agent is a system-prompt compression that helps the LLM stay focused on the actual user request.

The swarm endpoint becomes an *encapsulated capability*. The brainstem (or another swarm) calls it as a single named operation. The internals — which agents got invoked in what order, what data flowed between them — are hidden behind the swarm's URL.

This is the same pattern as microservices, sub-routines, plug-ins. The boundaries are deployment boundaries (one swarm = one deployable unit), not language boundaries.

**What we'd add to make this first-class:**

- **A `call_swarm(swarm_url, agent_name, args)` helper** in the BasicAgent base class. Agents shouldn't have to handcraft HTTP calls.
- **Authenticated swarm-to-swarm calls.** The orchestrator agent needs creds for the swarm it's calling. (See "Authenticated swarms" — once that ships, this composes naturally.)
- **A `dependencies` field in the bundle manifest** declaring which other swarms this swarm calls. So when you deploy a swarm that depends on others, the deploy can fail loudly if those swarms aren't reachable.
- **A "swarm deeplink" syntax** so the deploy bundle can reference other swarms without baking in URLs: `swarm://account-intel/AccountIntelligenceOrchestrator`. The bundle gets resolved at deploy time against whatever swarms the user has installed.

None of this exists yet. It would all be additive — current swarms keep working unchanged, swarms-of-swarms become possible.

**The eventual story:**

Swarms compose. A user installs a "RevOps suite" swarm bundle which itself references "account-intel-swarm" and "reporting-swarm" as dependencies. When deployed, the suite-swarm checks its dependencies are available, then exposes itself as a single endpoint that internally fans out. The brainstem's binder shows three rows; the model sees three tools. Underneath, "RevOps suite" is doing 14 sub-calls per invocation.

This is the composition story Tier 2 was always aimed at. We've shipped the unit (a swarm). We've shipped the wire contract (`/api/swarm/deploy` + `/api/swarm/{guid}/agent`). We haven't shipped the *composition* — bundles that reference other bundles, runtime resolution, authenticated cross-swarm calls. That's the next layer.

The work isn't conceptually hard. It's about half a week, maybe a week. We'd ship it once we have actual users running multiple swarms and asking "how do I make these talk to each other?" Right now everyone's running one. When they're running three, the question gets loud.

A swarm is the smallest deployable unit. Swarms-of-swarms is the natural compose. We're set up for it; we just haven't pulled the trigger.
