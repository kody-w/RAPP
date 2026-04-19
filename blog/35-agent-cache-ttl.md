# The 5-min TTL agent cache

Hot reload is a great development experience and a terrible production default. The community RAPP brainstem hits this exactly:

```python
_cached_agents = None
_cached_agents_lock = threading.Lock()
_cached_agents_created_at = None
AGENTS_CACHE_TTL_SECONDS = 5 * 60  # 5 minutes

def _get_cached_agents(force_refresh=False):
    """Get agents with caching to avoid reloading on every request."""
    global _cached_agents, _cached_agents_created_at
    with _cached_agents_lock:
        needs_refresh = (
            force_refresh
            or _cached_agents is None
            or _cached_agents_created_at is None
            or (time.time() - _cached_agents_created_at) >= AGENTS_CACHE_TTL_SECONDS
        )
        if needs_refresh:
            _cached_agents = load_agents_from_folder()
            _cached_agents_created_at = time.time()
        return _cached_agents.copy()
```

Five minutes of cache. After that, the next request triggers a fresh `load_agents_from_folder()` — which walks the disk, imports each `*_agent.py`, instantiates the class, builds the dict. It also re-pulls Azure File Share agents from the cloud, which is the slower piece (each agent file is a separate HTTP GET against blob storage).

**Why not always-cached?**

You drop a new agent file into `agents/`. With infinite cache, the brainstem never sees it — you have to restart the process. That's annoying in development and a real pain in production where restart means dropping in-flight requests.

**Why not no-cache?**

Loading agents on every request is expensive. Imports cascade — agents pull in `requests`, `pyyaml`, `azure-functions`, sometimes `pandas`. A 50-agent install is hundreds of milliseconds of import work per request. Multiply by traffic and you've burned your CPU on `import time` for nothing.

**Why 5 minutes specifically?**

It's the right number for "active development feels responsive without being silly." If you add a new agent and refresh the chat, you'll probably wait less than 5 minutes before testing it. If you're a user who hasn't touched the agents directory in hours, you don't need cache invalidation — your existing agents are still in place. 5 minutes gives both: fast iteration during dev, no churn during steady-state.

The value is configurable but never has been. Five minutes has been right for everyone we've talked to.

**The lock matters.**

`threading.Lock()` around the cache check + populate prevents the thundering-herd problem. Without it, two requests arriving exactly at the TTL boundary both decide "needs refresh," both call `load_agents_from_folder()`, both pay the import cost. With the lock, one wins, the other waits, then both get the same fresh cache.

The lock is held only during the cache check and the (rare) refresh. Normal cache hits release the lock immediately, so the lock isn't a throughput bottleneck.

**`.copy()` on return.**

Important detail: the function returns `_cached_agents.copy()`, not the cached dict directly. Callers occasionally mutate the dict (some test code, some plugin code). If they mutated the cached object directly, they'd corrupt the cache for everyone else. The copy is cheap (it's a dict of references, not deep) and isolates callers.

**The reset escape hatch:**

```python
def _reset_agents_cache():
    """Reset the agents cache to force reload on next request."""
    global _cached_agents, _cached_agents_created_at
    with _cached_agents_lock:
        _cached_agents = None
        _cached_agents_created_at = None
```

For the cases where 5 minutes is too long — e.g., after deploying a new agent via API — the brainstem can call `_reset_agents_cache()` to invalidate immediately. The next request loads fresh.

**The pattern generalizes:**

TTL caches are the right answer when:
- Underlying data changes occasionally, not constantly.
- Loading is expensive enough that per-request loading is wasteful.
- Stale data is acceptable for short durations.
- You have a clear "cache bust" trigger for explicit invalidation.

Agents fit this perfectly. Models, registries, source repos — anything you read from disk or network as part of normal request handling — usually fit too.

5 minutes isn't magic. It's the right answer to "how long can a user accept staleness?" for almost everything. Start there. Tune only if you have a real reason.
