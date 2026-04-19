# Same wire contract, three implementations

The brainstem talks to swarm endpoints over plain HTTP + JSON. There are exactly two endpoints in the wire contract:

```
POST /api/swarm/deploy        body: rapp-swarm/1.0 bundle    → {swarm_guid, swarm_url}
POST /api/swarm/{guid}/agent  body: {name, args, user_guid?}  → {status, output}
```

(Plus `GET /api/swarm/healthz` and `/api/swarm/{guid}/healthz` for inspection. Five lines if you count those.)

That contract is enough to build three completely different swarm endpoint implementations. We've shipped one and sketched two more.

**Implementation A: stdlib local (`swarm/server.py`).** Already shipped. ~300 lines of Python with `http.server.HTTPServer`. Persists swarms to `~/.rapp-swarm/swarms/`. No dependencies. Installs in 10 seconds via `install-swarm.sh`. This is the laptop / dev / single-machine story.

**Implementation B: Azure Functions (Tier 2 hippocampus).** Same wire contract, different backing storage. Persists swarms to Azure File Storage instead of local disk. Routes via the same `(swarm_guid, user_guid)` tuple but the path becomes a `memory/{guid}/...` blob path inside an Azure share. The agent execution code is shared with the local implementation — they both load `*_agent.py` files and call `perform()`. The difference is where the bytes live.

The OG community RAPP brainstem already has the underlying primitives (`AzureFileStorageManager`, `set_memory_context`). Wrapping them in a `/api/swarm/deploy` endpoint that writes agent files to a swarm namespace is small additional code on top.

**Implementation C: Cloudflare Worker + Durable Objects.** Edge-deployed swarm endpoint. Each swarm gets a Durable Object instance (DO) that holds its agents and routes calls. Agent execution would either:

- Call out to a separate Python runtime (a Workers-AI-style sandbox, or a small VM).
- Compile agents to JS via Pyodide running inside the worker (heavyweight but possible).
- Restrict swarm endpoints to non-Python "agents" (web fetches, simple computations) — a degraded mode that's still useful.

The C implementation is hypothetical right now. The interesting thing is: implementations A and B are concrete enough that we could build C without any wire-protocol changes. The brainstem doesn't know which it's talking to.

**What this buys:**

- **Brainstem doesn't change.** A user picks a swarm endpoint URL; whether that's `localhost:7080` (A), `https://my-swarm.azurewebsites.net` (B), or `https://my-swarm.workers.dev` (C) doesn't matter. Same `POST /api/swarm/deploy`.

- **Bundles are portable.** A swarm bundle generated for implementation A installs on B without changes. Same JSON, same agent files, same install path.

- **Implementations can specialize.** A is fast for one user with private data. B is right for teams sharing memory. C is right for "I want my swarm reachable from anywhere with low latency." User picks per use case.

**What it costs:**

- **Coordination.** Three implementations means three places to change behavior when the wire contract evolves. We try to keep the contract small for exactly this reason. (Two endpoints. Two HTTP verbs. One JSON schema.)

- **Capability divergence.** Implementation C might not be able to run arbitrary Python; A and B can. Users who want full capability have to know to pick the right backend. Documenting the matrix matters.

- **Testing.** Each implementation needs its own test suite verifying it speaks the contract correctly. We have one for A. We don't have one yet for B or C because we haven't built them.

**The principle:**

When you design a wire contract, design it so multiple backends can plausibly implement it. Don't bake in assumptions about storage layer, runtime, or scale. Two HTTP endpoints with JSON bodies and a tiny path namespace can carry an entire product. The implementations underneath get to be wildly different — local stdlib, cloud functions, edge workers — without any of them needing to know the others exist.

The brainstem doesn't care which swarm backend it's talking to. That's the whole point.
