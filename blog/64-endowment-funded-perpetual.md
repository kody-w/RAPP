# The endowment-funded perpetual service

Cemeteries fund perpetual care via an endowment. Universities fund perpetual scholarships via an endowment. Public libraries, public radio, family foundations — endowments everywhere. The model is centuries old: contribute capital once, invest conservatively, the yield funds the service forever.

It's a model software hasn't really used. SaaS funds itself via subscription — keep paying, keep service. Stop paying, stop service. There's no SaaS-equivalent of "pay once, served forever."

There could be. There should be, for the right product shapes.

**When endowment funding makes sense:**

The conditions:
1. **Long-tail value with declining marginal cost.** Storage costs decline; compute costs decline; ongoing operations get cheaper per-unit over time.
2. **Per-customer cost much lower than per-customer payment.** If hosting one customer costs $10/year and a customer paid $1,500 once, the $1,500 invested at 4% yields $60/year — six times the operating cost. Comfortable margin.
3. **The product has lasting use beyond the original buyer.** The buyer's descendants, the buyer's institution, the buyer's audience continue to derive value. So perpetual operation has perpetual customers, not just a perpetual cost.
4. **The buyer values the perpetuity itself.** Cemetery plots are bought BECAUSE they last forever. Memorial endowments same. The customer's payment is partly for the operation and partly for the *promise of permanence*. They'd pay less if perpetuity weren't part of the offer.

If your product has all four conditions, endowment funding is on the table.

**The math:**

Assume:
- Customer pays endowment: $E (one-time)
- Endowment investment yield: $r$ per year (4% conservative)
- Annual operating cost per customer: $C
- Optional ongoing subscription while customer is alive: $S/year

For perpetual operation after the principal stops paying subscription:

Yield = E × r per year.
Required: E × r ≥ C
So: E ≥ C / r

If C = $10/year and r = 4%, E ≥ $250.
If C = $80/year, E ≥ $2,000.
If C = $1,000/year, E ≥ $25,000.

The endowment scales with operating cost. Storage + compute is cheap, so the floor is low. Operations involving humans (curator support, family-council facilitation) drive cost up, requiring larger endowments — which is why higher-tier products cost more.

**Storage trends help:**

Storage prices halve every 3-5 years. Compute per-query similarly trends down. So an endowment sized today against current operating cost has BUILT-IN headroom for the future. Year 50 operating cost is dramatically lower than year 1 operating cost; the endowment yield (constant in real terms with conservative investment) covers it with growing surplus.

This is the key insight that makes the model work for software: the operational cost decreases over time, while the endowment principal compounds (or at minimum maintains real value). The math gets *better* as time passes, not worse.

**What you must commit to:**

If you're going to take endowment money for "perpetual" service, you have to actually deliver perpetual service. The contract — explicit or implicit — is that the endowment is held in conservative trust to fund the service for the customer's intended timeframe (often "as long as I have descendants").

That means:

1. **Endowment principal is segregated.** Not in the operating account. Customers' endowments fund customers' service, not next quarter's marketing budget. Audited annually.

2. **Investment policy is publicly stated.** Conservative bond ladder, broad-market index allocation, or similar. Customers should know exactly how their endowment is being managed.

3. **Operating cost is transparent.** What does it cost per year to host a sealed twin? Customers should be able to verify the math themselves.

4. **Exhaustion safeguards are documented.** What happens if cost ever projects to exceed yield? Supplemental contribution? Tier downgrade? Sunset notice? Tell the customer up front.

5. **Successor of the operator is provisioned.** If the company goes under, the endowed services should transfer to a successor operator (potentially via a structured fund, like the way historic-building preservation trusts work). Bake this into the operating agreement.

This is what makes the endowment model trustworthy. Without these guardrails, "perpetual" is marketing copy. With them, it's an actual commitment.

**The trust precedent:**

Cemetery operators, university endowments, family foundations — all of these have well-developed legal and operational frameworks for managing perpetual obligations against time-decreasing cost. We're not inventing the model; we're applying a centuries-old model to software. The legal structure (perpetual trusts, restricted endowments) is mature.

**Why most software startups can't do this:**

Most SaaS products fail condition 3 (lasting use beyond original buyer) or condition 4 (buyer values perpetuity). For Slack, perpetuity isn't valuable — the team using Slack today might not exist in 100 years. For Notion, perpetuity isn't valuable — your project notes from 2026 won't matter to anyone in 2126. The product surface doesn't justify the model.

Products that DO justify it: digital twins / preservation services. Memorial sites. Genealogical archives. Historical-figure interrogability. Long-running creative collaborations. Family-office-style multi-generational tooling.

If your product is any of these, the endowment model is a structural advantage. Subscription-funded competitors will have to keep selling forever; you sell once and run forever.

**The cash-flow shape:**

| Time | Subscription model | Endowment model |
|---|---|---|
| Year 1 | $X (start of subscription stream) | $E (one-time large payment) |
| Year 5 | 5×$X cumulative | $E + 5 years of yield - 5 years of cost |
| Year 50 | 50×$X cumulative if customer still paying | $E + 50 years of compounding surplus |
| Year 100 | 0 (customer long gone) | $E + 100 years of perpetually growing surplus |

At year 100, the subscription model has zero from this customer (they're dead). The endowment model still has the principal (intact in real terms) plus 100 years of compounded surplus from yield exceeding declining operating cost.

**The lesson:**

Endowment funding is a real, mature, trust-tested model that software has barely explored. It only works for products with the four conditions, but when those conditions are met, it produces unusual unit economics: perpetual customer relationships, perpetual revenue per customer (in expected value), perpetual lock-in.

If you're building anything with multi-generational use, model both subscription and endowment options. The endowment math probably works better for everyone — your customer prefers paying once for permanence; you prefer the larger upfront payment; the operating-cost decline curve is on your side.

Sell perpetuity to people who actually want perpetuity. Charge accordingly.
