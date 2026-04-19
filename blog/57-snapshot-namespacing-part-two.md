# Snapshot agent caching by `sys.modules` namespacing, part two

[Post #37](./37-sys-modules-namespacing.md) covered the multi-tenant case: two swarms with same-named agent files don't collide because each is loaded under a unique `sys.modules` key like `swarm_<guid>_<filename>`. That solved the live-tenant problem.

Adding snapshots introduced a third axis. Now we have:

- Swarm A live state, with `notifier_agent.py`
- Swarm A snapshot from January, with `notifier_agent.py` (might differ from live!)
- Swarm A snapshot from June, with `notifier_agent.py` (different again!)
- Swarm B live state, with `notifier_agent.py`
- Swarm B snapshots, with `notifier_agent.py` at various times
- ...

Same module name in five-plus places, each a distinct module that should never share state with the others. The pattern from post #37 — namespace by `swarm_<guid>_<filename>` — collides between swarm-live and swarm-snapshot. Adding a snapshot tier adds another disambiguator:

```python
modname = f"snap_{swarm_guid.replace('-', '_')}_{snapshot_name}_{path.stem}"
spec = importlib.util.spec_from_file_location(modname, str(path))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
```

`snap_` prefix differentiates from live (which uses `swarm_` prefix). `{snapshot_name}` differentiates between snapshots of the same swarm. Live agent for swarm X is `swarm_x_notifier_agent`; January snapshot of swarm X is `snap_x_jan_notifier_agent`; June is `snap_x_jun_notifier_agent`. All four are independent modules in `sys.modules`.

The same disambiguation applies to the in-process agent cache:

```python
self._loaded_agents[f"{swarm_guid}::snapshot::{snapshot_name}"] = agents
```

Cache key encodes the (swarm, snapshot) pair. Live agents for the swarm are at `self._loaded_agents[swarm_guid]`; snapshot agents are at `self._loaded_agents[f"{swarm_guid}::snapshot::{snap}"]`. Two namespaces don't collide.

**Why this matters:**

If we hadn't namespaced by snapshot, the first snapshot agent loaded would persist in `sys.modules`. Subsequent calls referencing the *same module name* but a *different snapshot* would silently return the cached version — meaning a query against the June snapshot might execute against the January snapshot's code if June was loaded second.

That's not a hypothetical. It happened in development. The bug presented as "snapshot conversation gives the wrong answer." It took a minute to find — the import cache was the culprit.

**The principle:**

Whenever you have a runtime dimension that affects how a module should be interpreted, the dimension belongs in the module's `sys.modules` key. `sys.modules` is a global namespace; treat it like one. If two distinct conceptual modules share the same key, you have a bug.

Dimensions worth thinking about for any plugin-loading system:

- Tenant (swarm in our case)
- Time (snapshot in our case)
- Version (different release of the same plugin)
- User (rare, but for per-user plugin overrides)
- Environment (dev/staging/prod, if same process serves multiple)

You don't need to namespace by all of these. Just by the ones where two instances at the same dimension value need to coexist as different runtime modules. Three dimensions for us: swarm GUID, snapshot name, file stem. All three end up in the module name.

**The smaller lesson:**

When `sys.modules` bites you, the answer is almost never "use a different import system." It's "make your module names unambiguous." Python's import machinery is correct; you just have to give it correct inputs. Treat the module-name space as a serious naming surface, not as an implementation detail.

Live agents `swarm_X_foo`, snapshot agents `snap_X_jan_foo`, `snap_X_jun_foo`. Three keys, three modules, zero ambiguity. Ten lines of namespacing, no bugs.
