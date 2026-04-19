# 138 agents, one click each

The default source in the brainstem's Browse panel is `kody-w/RAR` — the canonical RAPP Agent Registry. Right now it has 138 agents from 7 publishers across 19 categories. They install with one click each.

Some highlights of what's actually in there:

**B2B sales (account intelligence stack).** Account Intelligence, Account Intelligence Orchestrator, Action Prioritization, Competitive Intelligence, Deal Tracking, Meeting Prep, Messaging, Risk Assessment, Stakeholder Intelligence. The orchestrator is meant to coordinate the others — generate a full account briefing by chaining the specialists.

**B2B sales (deal progression stack).** Activity Gap, Competitor Intelligence, Deal Health Score, Deal Risk Assessment, Next Best Action, Pipeline Velocity, Revenue Forecast, Stakeholder Engagement, Stalled Deal Detection, Win Probability. A whole CRM-pulse-check toolkit.

**B2C sales.** Cart Abandonment Recovery, Customer 360 Speech, Customer Loyalty Rewards, Omnichannel Engagement, Personalized Shopping Assistant, Returns Exchange, Sales Chat. Retail-shaped, mostly hookable into Dynamics 365 / Commerce backends.

**Vertical stacks (energy, healthcare, federal/state/local government, financial services, manufacturing, retail, professional services).** Asset Maintenance Forecast, Care Gap Closure, Citizen Service Request, Claims Processing, Clinical Notes Summarizer, Building Permit Processing — the kind of agents that justify the existence of the registry. They're domain-specific enough that you wouldn't bundle them all with a base brainstem, but cheap enough to install when you need them.

**Pipeline / orchestration.** Multi-step orchestrators that chain the single-purpose agents. Account Intelligence Orchestrator, etc. These are interesting because they call other agents via the brainstem's tool-use loop — the LLM sees both the orchestrator and the specialists in its tool list and can decide to invoke either directly or through the orchestrator.

**Devtools.** A small set of utility agents for agent development itself — bulk CRM data generator, etc.

The publishers are: `@aibast-agents-library` (the bulk of the library, ~120 agents from AIBAST), `@borg`, `@discreetRappers`, `@kody`, `@kody-w`, `@rapp` (the core starters), `@wildhaven`. Each publisher namespace lets the registry hold multiple authors' work without naming collisions. Two publishers can both have an `account_intelligence` agent and they'll be `@aibast/account_intelligence` vs `@borg/account_intelligence`.

Quality tiers right now are mostly `community` (most of the library) and `official` (the bundled starters). The Browse panel renders a colored chip per tier so you can tell at a glance whether you're installing a vetted agent or an experimental one.

What's missing — and where contributions would actually help — is the **horizontal**, infrastructure-shaped agents. Things like: a generic SMTP sender, a generic SQL query runner, a generic file reader, a Slack poster, a calendar reader. The registry is heavy on B2B sales because that was the original commercial driver. Most of the long tail of "I want to wire this AI into my actual life" is still un-agent-ified.

If you write a general-purpose agent — anything that's not vertical-specific — fork RAR, drop your file in, and open a PR. The build script will compute the seed and mint the card automatically. The next user who searches the registry will find your work.

138 agents is a lot. It's also, when you measure against "every workflow people actually do," nothing.
