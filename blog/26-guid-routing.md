# GUID routing on one endpoint: many tenants, no Kubernetes

The community RAPP brainstem has one wire-level move that does most of its multi-tenancy work:

```python
self.storage_manager.set_memory_context(user_guid)
```

Before each request handles memory, the storage manager swaps its `current_memory_path` to point at that user's namespace: `memory/{user_guid}/user_memory.json`. After the call, it switches back. Same agent code, N users isolated by directory.

The swarm server takes the same idea and adds a second axis. Now there are *two* GUIDs per request: `swarm_guid` (which collection of agents are loaded?) and `user_guid` (whose memory inside that collection?). The disk layout is just the cross-product:

```
~/.rapp-swarm/swarms/
  <swarm_a_guid>/
    agents/*.py                   ← swarm A's bundle
    manifest.json                 ← swarm A's name, soul, etc.
    memory/
      shared/memory.json          ← anonymous calls to swarm A
      <user_x_guid>/memory.json   ← user X talking to swarm A
      <user_y_guid>/memory.json   ← user Y talking to swarm A
  <swarm_b_guid>/
    agents/*.py                   ← swarm B's bundle (different agents!)
    manifest.json
    memory/
      shared/memory.json
      <user_x_guid>/memory.json   ← user X talking to swarm B (separate from A)
```

**Two swarms can have completely different agent sets.** Swarm A is the sales swarm with HackerNews + LeadScorer + EmailDrafter. Swarm B is the ops swarm with PagerDuty + Datadog + Runbook. They live in the same server process, in different directories, with different tool surfaces.

**The same user has different memory in each swarm.** User X's preferences in the sales swarm don't bleed into the ops swarm. The model never sees one swarm's memory while serving the other.

The whole isolation story is two GUIDs and a path concatenation. There's no namespaces concept, no tenant table in a database, no Kubernetes pod per swarm. There's just `swarms/<a>/memory/<x>/memory.json` and `swarms/<b>/memory/<x>/memory.json` being different files.

**How a request gets routed:**

```python
def execute(self, swarm_guid, agent_name, args, user_guid):
    agents = self.load_agents(swarm_guid)        # cached after first load
    agent = agents.get(agent_name)
    mem_path = self.memory_path(swarm_guid, user_guid)
    mem_path.parent.mkdir(parents=True, exist_ok=True)
    os.environ["BRAINSTEM_MEMORY_PATH"] = str(mem_path)
    try:
        return {"status": "ok", "output": agent.perform(**args)}
    finally:
        os.environ.pop("BRAINSTEM_MEMORY_PATH", None)
```

Agent files don't know about swarms. They don't know there are other tenants. They read and write `BRAINSTEM_MEMORY_PATH` like a regular env-var-configured file. The server swaps the env var around each call. The agent contract is unchanged.

**Why this scales:**

A swarm endpoint hosting 100 swarms with 50 users each (5000 memory namespaces) is just 5000 small JSON files on disk. No database. No connection pool. No cluster. The only shared state is the loaded-agent cache (one entry per swarm, evicted by LRU if you wanted; we currently never evict because agent counts are small).

Throughput is bounded by Python's stdlib HTTP server (a few hundred req/s on a laptop). For chat-shaped workloads — every agent call comes from one user typing into a UI somewhere — that's enough for thousands of concurrent users.

When it stops being enough, you switch to Azure Functions with Azure File Storage instead of local disk. Same path layout. Same env var. Same agent code. The wire contract stays `/api/swarm/deploy` and `/api/swarm/{guid}/agent`. Your laptop and the cloud become interchangeable backends.

GUID routing on one endpoint is not a workaround for not having Kubernetes. It's the right primitive for tenant isolation in the chat-shaped problem we're actually solving.
