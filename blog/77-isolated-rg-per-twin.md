# Isolated resource group per twin: the sovereign cloud topology

When you provision a Twin Stack twin in Azure, it gets its own resource group. Not its own subnet. Not its own namespace. Its own *resource group*.

```bash
bash hippocampus/provision-twin-lite.sh kody    # → rg-twin-kody
bash hippocampus/provision-twin-lite.sh molly   # → rg-twin-molly
```

Each twin's resource group contains:
- 1 Function App (`twin-<name>-<hash>`)
- 1 Storage Account (`sttwin<name><hash>`)
- 1 App Service Plan (Consumption Y1, $0 idle)

That's it. No shared databases, no shared storage, no shared compute. Two twins in the same Azure subscription are as isolated as two twins in two different *companies*.

**Why this matters more than usual:**

In a typical multi-tenant SaaS, "isolation" means logical separation — different rows in the same database, different folders in the same bucket, different routes on the same server. That's *trust-the-platform* isolation. The platform code is the trust boundary; if there's a bug in row-level security, every tenant is exposed.

A digital twin holds something more sensitive than a row in a database. It holds:
- The principal's soul addendum (their intellectual personality, what makes them recognizable)
- Their conversation history (every interaction the twin has ever had)
- Their document workspace (drafts, briefs, signed docs from peers)
- Their T2T peer secrets (the cryptographic material that proves identity to other twins)

If two twins shared a database row-by-row, a database compromise would leak every twin's everything. With one twin per resource group:
- A compromise of twin A's storage account doesn't touch twin B's storage account
- A compromise of twin A's Function App can't enumerate twin B's swarms
- A leaked Function App API key for twin A doesn't grant access to twin B
- Tearing down twin A is `az group delete --name rg-twin-A --yes` — guaranteed clean removal of every byte

This is the same isolation model that *cemeteries* use. Each plot is its own physical thing. You don't share a plot with another family because the management software lets you. The physical separation IS the privacy guarantee.

**The cost story:**

Pricing-wise, isolated RGs sound expensive. They're not, because:
- **Resource groups themselves are free.** The bill is for the resources inside them.
- **Function Apps on Consumption Y1 cost $0 at idle.** You pay per request, and a typical idle twin gets zero requests.
- **Storage at Standard_LRS is ~2¢/GB/month.** A twin's full lifetime storage (years of conversations + documents) fits in well under a gigabyte for nearly everyone.
- **No shared App Service Plan to over-provision.** Each twin's plan auto-scales to zero.

So a fleet of 100 twins idle costs roughly: $0 in compute + ~$2/month in storage. Active usage scales linearly. Compare to a multi-tenant database where you're paying for vCPUs even when nobody's using the system.

**The deployment script handles the boring parts:**

`provision-twin-lite.sh` is a single shell script that:
1. Switches to the right subscription
2. Creates `rg-twin-<name>` (free, instant)
3. Creates the Storage Account (~30s)
4. Creates the Function App on Consumption Linux Python 3.11 (~60s)
5. Reads the root `.env` and applies `AZURE_OPENAI_*` keys as Function App appsettings
6. Adds CORS for the brainstem onboard page
7. Vendors `swarm/*.py` into `hippocampus/_swarm/` so the deploy is self-contained
8. `func azure functionapp publish` — pushes the function code (~90s)
9. Prints the URL + tear-down command

Total time: 3-5 minutes per twin. Idempotent — re-running on an existing RG just updates code.

**The lite script is the right script:**

We *also* have `provision-twin.sh` (the full version) which ARM-deploys an azuredeploy.json that creates a *new* Azure OpenAI deployment per twin. That hits regional quota fast, and most users already have an Azure OpenAI account they want to reuse. The lite script reuses whatever Azure OpenAI is in your `.env` and skips creating a new one. For nine out of ten twins you provision, lite is right. The full version exists for the case where you actually want a separate OpenAI per twin (e.g., to bill different cost centers).

**Why "sovereign" is the right word:**

Each twin's resource group is its own sovereign — its own URL, its own storage, its own keys, its own bill. No shared platform plane. The user controls the whole thing. They can move it, freeze it, snapshot it, sell it, will it to a successor.

That's not a typical SaaS posture. It's closer to how you'd hold a cemetery plot, a domain name, or a physical safe-deposit box. Which is exactly the right posture for a thing that's supposed to outlast the person inside it.
