# Open the bones, close the body, sell the soul

Most open-source-with-commercial-arm projects struggle with the boundary. What goes public? What stays private? When does upstreaming a feature compete with your paid product? When does keeping a feature private starve the community?

There's a clean three-layer answer that's worked across multiple successful companies (WordPress/Automattic, MongoDB/Atlas, GitLab open-core, HashiCorp/HashiCorp Cloud, Vercel/Next.js):

**Bones — the architecture and protocols.** Public. Permissively licensed.

**Body — the operational machinery, billing, governance, ops dashboards.** Private. Proprietary.

**Soul — the brand, trust, customer relationships, cultural position.** Not in any repo. The actual moat.

The bones are public because **standards are worth more than secrets**. If your wire protocol becomes the de facto standard, every implementation in the world strengthens your position. If you keep your wire protocol private, you compete on protocol-vs-protocol with whoever publishes theirs second. Open at the substrate.

The body is private because **the operations are the differentiation**. Everyone's swarm server can implement the sealing primitive (we shipped it open-source). Not everyone can run a cemetery-grade endowment-funded perpetual hosting service with curator support, family governance dashboards, multi-jurisdiction estate-attorney partnerships, and tier-aware Stripe billing. The protocols are the bones; this is the body. Keep it.

The soul is what people pay for. They pay because they trust YOU specifically — your brand, your team, your relationships — to preserve their grandfather's voice for 100 years. Forks of your bones can copy your protocols and even your operational patterns, but they can't copy the trust people have built with your brand. The soul accrues over time and is the deepest moat.

**The decision rule:**

> *Public if a developer would gain by reading it. Private if a competitor would gain by reading it.*

Apply this to every file. Not every commit. Not every feature. Every file.

A new agent for the open agent registry: developers gain. Public.

A pricing-tier capacity table: competitors gain. Private.

A new wire protocol for cross-system federation: developers gain (more so the more interoperable). Public.

A sales playbook for converting Heritage-tier free users to paid: competitors gain enormously. Private.

The protocol's reference implementation: developers gain. Public.

The reference implementation augmented with billing, tier enforcement, and governance: competitors gain. Private.

**The conflict cases:**

What about features that are clearly useful to the community AND helpful to competitors? Two examples:

**Sealing.** The sealing primitive (`POST /api/swarm/{guid}/seal`, manifest flag, OS-level read-only enforcement) is useful to anyone running a swarm server for any reason — preserving demos, archiving experiments, version-locking a deployment. Competitors building a twin-preservation product would also benefit. We shipped it public anyway because the operational layer above it (endowment, ceremony, family governance) is so much more substantial than the primitive that competitors get one drop of value while developers get a fundamental capability.

**Bundle deployment protocol.** Same calculation. Anyone deploying multi-tenant agent code benefits from the `rapp-swarm/1.0` JSON schema. Competitors would also benefit. Public — because once the format is canonical, *everyone deploys to our shape*, including future competitors. Standardization wins.

The pattern: when the primitive is a *protocol* and the product is a *service around the protocol*, ship the protocol open. The service can't be copied just by copying the protocol.

**What never goes public:**

- Pricing strategy (tier amounts, internal margin math)
- Sales playbooks (BDR scripts, qualification frameworks, competitive positioning against named alternatives)
- Customer lists, case studies (without permission), anything per-customer
- Curator operations playbooks
- Internal financial models, ARR, growth rates
- Founder/CEO pitch decks
- Post-mortem documents that name customers
- Active legal strategy / litigation prep
- Patent applications until filed (then "patent pending" is fine to state)

**What goes proudly public:**

- Architecture posts
- Postmortems (anonymized where appropriate)
- Protocol specs
- Reference implementations
- The "why we built it this way" engineering philosophy
- Patent NUMBERS once filed (creates competitive deterrence)

**The lesson:**

The fastest way to lose is to be confused about which layer you're competing on. If you think the protocol is your moat, you'll keep it private and watch a competitor publish theirs and win the standardization battle. If you think the brand is your moat, you'll act accordingly: ship the protocol open, build the brand intentionally, never confuse "code we wrote" with "value we provide."

Open the bones. Close the body. Sell the soul. The operational order matters: bones first (build the standard), body second (build the operations on top of your own standard), soul third (build the trust over years). Try to start at soul without bones underneath and you have a marketing campaign without a product. Try to start at bones without soul on top and you have a developer tool without a business.

This is the hardest thing about running an open-core company. It's also the highest-leverage thing.
