# Per-twin Function App = independent scaling unit

The deployment starts with two nearly boring shell commands:

```bash
bash hippocampus/provision-twin-lite.sh kody    # → rg-twin-kody
bash hippocampus/provision-twin-lite.sh molly   # → rg-twin-molly
```

A minute later, Azure has done something more consequential than the old “sovereignty + billing isolation” framing suggested. It has created two separate Function Apps, each in its own resource group, each with its own storage account, each on Consumption. Not two tenants inside one scaling pool. Two scaling pools.

That distinction is the chapter.

We used to explain the per-twin topology in moral terms: privacy boundary, blast-radius control, clean deletion, separate billing. All true. The source even says it plainly in `blog/77-isolated-rg-per-twin.md`: “When you provision a Twin Stack twin in Azure, it gets its own resource group.” The script in `hippocampus/provision-twin-lite.sh` makes that concrete. It builds stable names, then creates exactly one resource group and one Function App per twin:

```bash
RG="rg-twin-${NAME}"
HASH=$(printf '%s' "$NAME" | shasum | cut -c1-6)
STORAGE_ACCT="sttwin${NAME}${HASH}"     # ≤24 chars, lowercase
APP_NAME="twin-${NAME}-${HASH}"

echo "▶ Ensuring $RG in $LOCATION"
az group create --name "$RG" --location "$LOCATION" \
    --tags "twin=$NAME" "stack=TwinStack" "owner=wildhaven-ai-homes" \
    --output none
```

What we understated was the systems consequence. On Azure Consumption, a Function App is not just an administrative container. It is an independent autoscaling unit. If one Function App can climb to roughly 200 concurrent instances, then one twin can get its own ~200-instance ceiling without competing with its neighbors. Kody’s traffic surge does not consume Molly’s headroom, because Molly is not another route in Kody’s app. She is another app.

At 10 twins, you do not have one application trying to fan out across a shared worker pool. You have 10 independent pools. The important constraint here is not a grand fleet-size multiplication exercise; it is that each twin is provisioned as its own scaling domain rather than as a tenant inside someone else’s burst budget.

The important word there is independent. We do not have evidence in the source for platform-wide quota behavior at very large fleet size, regional caps, subscription caps, or the operational friction of managing huge numbers of Azure resources. Those constraints are real, and they matter. But they are different constraints from the one most multi-tenant systems hit first, which is noisy-neighbor contention inside a shared compute tier. This design dodges that by construction.

In a conventional SaaS architecture, you spend real engineering effort trying to keep a user’s hot path close to that user’s state. You shard. You pin sessions. You partition queues. You debate whether to colocate compute with storage or add another caching layer to survive the distance. Here, the unit of deployment already matches the unit of identity. One twin, one Function App, one storage account.

That changes failure modes. A burst of work for one principal scales that principal’s app. A pathological loop harms that twin’s estate first. A teardown is still the same blunt command from the original topology:

`az group delete --name rg-twin-kody --yes --no-wait`

That is why “per-twin Function App” is the right mental model. Not a packaging choice. Not an Azure naming convention. An independent scaling unit.
