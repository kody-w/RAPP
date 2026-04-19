# The control plane sketch — provisioning brainstems at fleet scale

We have a script. `hippocampus/provision-twin-lite.sh` takes a name, calls `az`, and roughly two minutes later there is a brainstem in the cloud. Resource group, storage account, Function App on Consumption, env keys applied, code published, URL printed. We run it from a laptop. We watch the output. We copy the URL into the onboard page. We do this once per twin.

This post is the next step. We have not built it. We are sketching it the way `blog/49-relay-design.md` sketched the relay — settled enough to ship in a week if the pull arrives, banked until then.

**The current state.**

`provision-twin-lite.sh` is a single-twin tool. Idempotent, honest, works. Fine for development and the first few dozen twins. Not fine for a hundred thousand.

A human runs it. A human watches it. A human reads the URL out of the terminal and pastes it into the next thing. Ten thousand brainstems by hand is an absurd quantity of human attention; a million is a category error.

We knew this when we wrote `blog/86-per-twin-fa-scaling-unit.md`. The per-twin Function App is the right scaling unit — each twin gets its own ~200-instance ceiling, no noisy-neighbor contention, clean teardown via `az group delete`. What we left unsaid was the orchestration question. If the unit of scale is one Function App per twin, who calls `az` ten thousand times?

That is the gap the control plane fills.

**What the control plane is.**

A single REST service that brokers brainstem provisioning and lifecycle. It receives create, list, and delete requests. It manages a worker pool that runs the actual provisioning calls — `az` today, `gcloud` or `kubectl` or whatever tomorrow. It returns a brainstem URL when one is ready.

It does not host brainstems. It does not route chat traffic. It does not hold memory or conversations or secrets. It is a thin orchestration layer that knows how to ask a cloud provider to make a brainstem appear, and how to remember which brainstems exist for which owners. Everything else stays where `blog/29-swarm-server-no-llm.md` put it — credentials with the human, execution with the data. The same principle that kept the swarm server out of the LLM business keeps the control plane out of the chat business.

**The wire surface (sketch).**

Five endpoints. We are deliberately starting smaller than the swarm server's surface, because the cardinality is different — control plane traffic is "twin lifecycle events," not "every chat message."

```
POST   /api/cp/brainstems              → create one (returns job_id, async)
GET    /api/cp/brainstems/{job_id}     → poll provisioning status
GET    /api/cp/brainstems/{cloud_id}   → fetch URL once provisioned
DELETE /api/cp/brainstems/{cloud_id}   → tear down
GET    /api/cp/health                  → fleet stats
```

The split between `job_id` and `cloud_id` matters. Provisioning is asynchronous and slow; the create call returns immediately with a job handle, the caller polls until the job resolves to a real `cloud_id`. Once that happens, the `cloud_id` is the durable name — the same name that survives in the database, the same name a future delete call uses.

Fleet stats on `/health` are the operator's dashboard in JSON form: total provisioned, currently active, currently provisioning, errored. Enough to know whether things are healthy without a separate metrics stack.

**The data shape.**

One row per brainstem. Small.

```
cloud_id        text primary key   -- twin-kody-a3f1c9
owner           text               -- github:wildfeuer05
region          text               -- eastus2
runtime_target  text               -- azure-consumption-py311
deploy_ref      text               -- git sha or bundle hash
status          text               -- provisioning|active|errored|deleted
url             text               -- https://twin-kody-a3f1c9.azurewebsites.net
created_at      timestamptz
last_seen       timestamptz
```

That is the schema. Postgres if we want it ready for ten million rows. SQLite-on-Litestream if we want it ready for a hundred thousand and operationally trivial. A JSON file on disk if we want it ready for the first thousand twins and we are honest that we will swap it out before the second thousand.

Same principle as everything else in the repo: pick the storage that matches the cardinality you actually have, not the cardinality you imagine.

**The worker pool.**

N workers polling a queue. Each worker takes one provisioning job, calls `bash hippocampus/provision-twin-lite.sh <name>` as a subprocess, captures the URL, updates the row, returns. Idempotent — if a worker dies mid-job, the queue retries; the script itself already tolerates re-running on an existing resource group.

Provisioning takes minutes. The queue holds work that is safe to retry. No clever scheduling, no priority queue, no preemption. A list of pending jobs and a small pool of processes that pick the next one. This is where the control plane is allowed to feel boring — the interesting part is the wire contract above; the execution underneath is just `subprocess.run` against a shell script we already shipped.

**Why no Kubernetes.**

Because the unit of scale is not a container. It is a Function App.

Each twin's brainstem runs on Azure Consumption (or Cloud Run, or Lambda, depending on the runtime target). The cloud provider's own scheduler handles request-level scaling — exactly the property `blog/86-per-twin-fa-scaling-unit.md` celebrates. One twin, one Function App, one independent scaling pool. We do not run pods. We do not need a control loop reconciling desired state against actual state at the request level; the cloud provider's scheduler is already the control loop.

The control plane only orchestrates lifecycle: create, list, delete. It does not orchestrate request routing, because routing is per-twin URL — `https://twin-kody-a3f1c9.azurewebsites.net` is the route, and DNS handles the rest. A Kubernetes operator that could theoretically scale to a million pods is the wrong shape for a problem where the unit of scale was never a pod.

**What we would build first (MVP).**

A single-binary Go service or a single-file Python service exposing the five endpoints. SQLite for the row-per-brainstem table. One to three worker processes that shell out to the existing `provision-twin-lite.sh`. The swarm server runs on stdlib `BaseHTTPRequestHandler` and that is plenty for chat-shaped traffic — control-plane traffic is quieter.

Total: five hundred to eight hundred lines, including schema, queue, and wire handlers. The provisioning script is the load-bearing part. We do not rewrite it. The control plane is a thin shell around something we have already debugged in production-shaped conditions.

**What we would defer.**

Auth, in the first cut. Trusted single-tenant deployment — the control plane runs on a machine the operator owns, and the only caller is the operator's tooling. GitHub OAuth comes when there is a second operator.

Billing. We are provisioning Function Apps onto whatever Azure subscription the operator wired in. Per-tenant billing is a real product question; it is not a control plane question yet.

Multi-cloud. Start with Azure because that is what the script targets today. Cloud Run and Lambda runtime targets are a column in the schema we leave nullable until they matter.

HA worker pool. A single worker on a single VM is fine for the first ten thousand twins; that is one twin every couple of minutes for fourteen days of continuous provisioning, which is more headroom than we will use before we want to rewrite the worker layer anyway.

**The lesson from cycle-3.**

Even the control plane is "ship the smallest workable thing." A five-hundred-line service that can provision ten thousand twins one at a time is more shippable than a Kubernetes operator that could theoretically provision a million but takes six weeks to write. The same principle that produced the rapplication produces the control plane.

We will build it when the pull arrives. The shape is settled enough that the build is a week of work, not a quarter. Banked.
