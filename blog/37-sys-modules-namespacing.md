# Per-call module loading via `sys.modules` namespacing

The swarm server hosts many swarms. Two swarms can have agent files with the same name. Maybe they both have a `notifier_agent.py`, but swarm A's notifier hits Slack and swarm B's notifier hits Discord. Different code, same filename.

Python's import machinery is fundamentally a cache. `import notifier_agent` once and the module is in `sys.modules['notifier_agent']` forever — subsequent imports return the cached object. If swarm A loads first, then swarm B asks for its `notifier_agent`, the import resolves to swarm A's cached module. Bug.

The fix is to give each swarm's modules unique names in `sys.modules`:

```python
modname = f"swarm_{swarm_guid.replace('-', '_')}_{path.stem}"
spec = importlib.util.spec_from_file_location(modname, str(path))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
```

Swarm A's `notifier_agent.py` becomes `sys.modules['swarm_abc_def_123_notifier_agent']`. Swarm B's becomes `sys.modules['swarm_xyz_abc_456_notifier_agent']`. They're separate entries; loading one doesn't affect the other.

We don't use `importlib.import_module` at all for per-swarm agents. That's the convenient API but it relies on `sys.path` to find files, which means name collisions. `spec_from_file_location` is the right hammer when you want to control:

- **What name the module is registered under** (so collisions can't happen).
- **Where the source actually lives** (so we don't pollute `sys.path` with every swarm's directory).

**The collision avoidance is at module-name level, not file-path level.** Two modules can share a *file path* and still be separate modules in `sys.modules` if they have different names. We don't actually load them from the same path — each swarm has its own files — but the principle holds: `sys.modules` is keyed by name, not by file. Take that key into your own hands.

**Caching, but per-swarm:**

The swarm store caches loaded agent instances by `swarm_guid`:

```python
self._loaded_agents = {}  # swarm_guid -> {agent_name: instance}

def load_agents(self, swarm_guid):
    if swarm_guid in self._loaded_agents:
        return self._loaded_agents[swarm_guid]
    # ... load ...
    self._loaded_agents[swarm_guid] = agents
    return agents
```

First call to a swarm: load all its agents from disk, instantiate, cache by swarm GUID. Subsequent calls: return the cached dict. Cache invalidated when the swarm is re-deployed (new bundle replaces old) or removed.

This gives each swarm its own loaded-agents dict, completely separate from other swarms'. Memory usage scales linearly with the number of distinct swarms that have been called recently. (We don't currently evict, because swarm counts are small. If they got large, an LRU per-swarm-GUID would be straightforward to add.)

**Why not separate processes per swarm?**

You could run one Python process per swarm. Maximum isolation. No shared `sys.modules` to worry about. But:

- Process startup is expensive (Python imports, runtime warmup).
- Memory overhead is non-trivial per process — even a small Python process is 30-50MB.
- Coordinating "which port does this swarm listen on" requires either a port-allocator or a reverse-proxy.

For collaborative-multi-tenant use (your team's swarms, your customers' swarms under your control), in-process isolation via `sys.modules` namespacing + cached agent instances is enough. For *hostile*-multi-tenant (random internet users deploying possibly-malicious code), you'd want the OS-level isolation that processes / containers / sandboxes give you. We're not in the latter scenario.

**The principle:**

Python's module system is mostly opaque defaults. When defaults bite — like "modules are global by name, not by file path" — the right move is usually to take control of the part that's biting (here, the module name) without abandoning the rest of the import machinery. `importlib.util.spec_from_file_location` is the underused tool for exactly this.

Also: when you find yourself wanting to spin up a process just to get isolation, ask whether the *thing you want isolated* is actually the process state. If it's just module-table state, you can isolate that without paying for a whole process.

One server. Many swarms. No collisions. ~10 lines of `importlib.util` plumbing.
