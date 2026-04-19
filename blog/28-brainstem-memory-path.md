# `BRAINSTEM_MEMORY_PATH`: per-call routing without changing the agent contract

The agent contract says: a `*_agent.py` file extends `BasicAgent`, declares a manifest, implements `perform()`. Nothing in there says "you can be one of N tenants per server." There shouldn't be. The contract is the smallest workable thing; tenancy is a runtime concern.

The swarm server hosts hundreds of swarms behind one process, each with its own per-user memory. The agents inside those swarms need to read and write the right memory namespace per call. The naive answer is "rewrite the agents to take a tenant ID." We didn't do that. We did this:

```python
def _memory_path():
    """Where this process's memory lives."""
    import os
    p = os.environ.get("BRAINSTEM_MEMORY_PATH")
    return p if p else os.path.expanduser("~/.brainstem/memory.json")
```

Three lines added to `save_memory_agent.py` and `recall_memory_agent.py`. They check an env var first, fall back to the default `~/.brainstem/memory.json`. That's it.

Server-side, the swarm executor swaps the env var around each call:

```python
def execute(self, swarm_guid, agent_name, args, user_guid):
    mem_path = self.memory_path(swarm_guid, user_guid)
    mem_path.parent.mkdir(parents=True, exist_ok=True)
    old_env = os.environ.get("BRAINSTEM_MEMORY_PATH")
    os.environ["BRAINSTEM_MEMORY_PATH"] = str(mem_path)
    try:
        return {"status": "ok", "output": agent.perform(**args)}
    finally:
        if old_env is None:
            os.environ.pop("BRAINSTEM_MEMORY_PATH", None)
        else:
            os.environ["BRAINSTEM_MEMORY_PATH"] = old_env
```

Set, call, restore. Each request gets its own path; the next request gets a different one. The agent doesn't know.

**Why this works:**

The Python HTTP server we use (`http.server.HTTPServer`) is single-threaded by default. One request at a time. The env-var swap is safe because no other request is in flight. If you switched to a threaded server you'd need a lock or a different mechanism — but for chat workloads, single-threaded is fine.

**Why this is a good pattern:**

- **Agent code stays generic.** Same file works in the local brainstem (no env var, default path), the swarm server (env var per call), and Pyodide (the env var doesn't exist in the JS runtime, so it falls back). One file, three deployment shapes.

- **No new contract surface.** We didn't add a tenant_id parameter to `perform()`. We didn't introduce a `Context` object that agents have to thread through. We added one env var that one shim function reads. The contract is unchanged; the runtime did the work.

- **Legacy agents degrade gracefully.** An agent file written before this convention existed — one that hardcodes `~/.brainstem/memory.json` — still works. It just doesn't get isolation. That's a worse outcome but not a broken outcome. The user can fix the agent (add the three-line shim) without breaking anything.

**What you give up:**

This pattern doesn't give you isolation against agents that *want* to break it. An agent could `os.environ.pop("BRAINSTEM_MEMORY_PATH")` and write to `~/.brainstem/memory.json` cross-tenant. We're trusting agents not to be malicious. In a hostile-multi-tenant context you'd need OS-level isolation (containers, namespaces, seccomp). For collaborative-multi-tenant — your team, your customers under your control — env-var routing is enough.

**The principle:**

When you need to add a runtime concern (tenancy, observability, rate-limiting) to code that already exists, prefer a contract that *most code can ignore*. An env var the shim reads is one such contract. A request-context global is another. A new function signature isn't.

Three lines per agent. One env-swap per call. N tenants. The work the runtime does should not show up in the agent's source code if you can help it.
