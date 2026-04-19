# The investor one-pager

The deployment starts with two nearly boring shell commands:

```bash
bash hippocampus/provision-twin-lite.sh kody    # → rg-twin-kody
bash hippocampus/provision-twin-lite.sh molly   # → rg-twin-molly
```

A minute later, Azure has created two separate Function Apps, each in its own resource group, each with its own storage account, each on Consumption. Not two tenants inside one scaling pool. Two scaling pools. That detail matters because it shows what this company is actually building: not a novelty chatbot, but a system designed for permanent, independent digital twins that can be isolated and operated at the level of a person or family.

Here is the one-pager I would put in front of a Series A partner.

**The Ask**  
We are raising a Series A to turn an early technical and market insight into a real company. We do not have revenue yet. We have not announced a funded round. We are not claiming product-market fit. What we do have is a clear wedge, a pricing model with unusually large contract potential, and infrastructure built around the unit that matters: one twin, one stack, one customer relationship.

**Problem**  
Most software is priced and sold as utility: $10 to $30 per month, justified by daily convenience. But some products are not utilities. They are purchased because they create a lasting artifact whose value extends beyond the buyer: a biography, a memorial, a family archive, an endowment. Buyers in that market already spend real money—$5,000 for a cemetery plot, $25,000 to $250,000 for a commissioned biography, $50,000 to $500,000 for estate planning—because permanence and inheritance matter.

Digital twins that endure across generations sit in that second category, not the first. Most software companies benchmark against ChatGPT Plus or Notion and underprice by 100 to 1000 times.

**Insight**  
The core insight is that this should be sold with legacy pricing, not utility pricing. A digital twin meant for descendants is not a $20-per-month tool. It is closer to an heirloom than to a subscription.

That leads to a business model software rarely uses: one-time payment plus perpetual maintenance, funded by an endowment. The source math is simple:

- if customer endowment is $E$
- and conservative annual yield is 4%
- then perpetual service works when $E \times r \ge C$

If annual operating cost per twin is low and trending down—as storage and compute historically do—then a one-time capital contribution can fund long-lived service.

**Traction**  
The strongest evidence today is architectural, not commercial. The company has already made one important systems choice that many teams would postpone: every twin is provisioned as its own independent Azure scaling domain.

```bash
RG="rg-twin-${NAME}"
HASH=$(printf '%s' "$NAME" | shasum | cut -c1-6)
STORAGE_ACCT="sttwin${NAME}${HASH}"     # ≤24 chars, lowercase
APP_NAME="twin-${NAME}-${HASH}"
```

Per the source, each Function App can climb to roughly 200 concurrent instances on Azure Consumption. That means one twin’s traffic surge does not eat another twin’s capacity. At 10 twins, the company does not have one crowded app; it has 10 independent pools.

**Moat**  
The moat is not the model. It is the combination of category framing, pricing discipline, and infrastructure shape.

First, the category framing is unusual and defensible: compare against cemeteries, trusts, biographies, and endowments, not SaaS seats. Second, the pricing logic follows from the product’s actual value accrual: the audience is larger and longer-lived than the original buyer. Third, the per-twin deployment model creates operational isolation at the exact unit customers will purchase.

**Use of Funds**  
Series A capital should go to three things: converting the endowment model into a repeatable go-to-market motion, hardening the per-twin infrastructure for long-term operation, and building the customer experience around setup, governance, and permanence.

**Why Now**  
Now is the right time because the economics have changed. Storage and compute costs are low enough, and still declining, to make perpetual-service promises plausible. At the same time, people are more comfortable with AI-mediated interaction and more willing to preserve identity, memory, and family history in digital form.

**Risk**  
The biggest risks are straightforward. There is no revenue yet. There is no funded-round signal. There is no PMF claim. The market may agree with the philosophy and still resist the purchase motion. Endowment-backed software is intuitive in theory but still unproven as a scaled category. Those are real risks. They are also the reason this is a Series A question, not a late-stage one.
