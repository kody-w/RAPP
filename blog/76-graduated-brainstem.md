# The graduated brainstem: function_app.py is sacred

The OG community RAPP has a `function_app.py`. It's an Azure Functions Python v2 entrypoint that mounts a single endpoint (`/api/businessinsightbot_function`), loads `*_agent.py` files from an `agents/` folder, runs an `Assistant` class chat loop with tool-calling, and returns a `|||VOICE|||`-split response. About 1100 lines, single file, very direct.

We didn't replace this. We *graduated* it.

The new `hippocampus/function_app.py` keeps every sacred piece of the OG:
- Same `BasicAgent` contract (`agents.basic_agent` import, `metadata` dict, `perform()` method)
- Same `/api/health` endpoint shape
- Same `/api/businessinsightbot_function` route name (Copilot Studio still calls it)
- Same `/api/trigger/copilot-studio` direct-invoke shape
- Same `Assistant` class pattern with `_prepare_messages()`, `_execute_agent()`, `run()`
- Same `|||VOICE|||` split for the dual response (formatted + colleague-over-cubicle-wall)
- Same `DEFAULT_USER_GUID = "c0p110t0-aaaa-bbbb-cccc-123456789abc"` sentinel
- Same `<identity>` / `<shared_memory_output>` / `<specific_memory_output>` / `<agent_usage>` / `<response_format>` system prompt structure

What it adds: *swarm awareness*. Each request can specify a `swarm_guid` in the body. That selects WHICH swarm's agents and memory drive THAT request. One Function App can host any number of swarms — each isolated, each hot-loaded per call. The `Assistant` constructor takes a `swarm_guid` and loads only that swarm's tool set.

```python
class Assistant:
    def __init__(self, swarm_guid, user_guid=None):
        self.swarm_guid = swarm_guid
        self.user_guid = user_guid or DEFAULT_USER_GUID
        manifest = STORE.get_manifest(swarm_guid) or {}
        self.soul = (manifest.get("soul") or "").strip()
        self.agents = STORE.load_agents(swarm_guid)  # ← per-swarm hot-load
        self.tools = [self._agent_to_tool(a) for a in self.agents.values()]
```

Same `Assistant`. Same wire shape going in, same wire shape coming out. Just parameterized.

**Why "sacred"?**

A pattern is sacred when changing it breaks downstream consumers you can't see. The OG `function_app.py` shape has clients in production:
- The Copilot Studio bot framework (Microsoft's no-code AI platform) calls `businessinsightbot_function` with a specific JSON shape and expects a specific JSON shape back
- The brainstem's web UI calls the same shape locally
- Custom Power Automate flows call `trigger/copilot-studio` for direct agent invocation
- Anyone who deployed the OG repo to their own Azure Functions has tooling pointed at these routes

If we'd renamed the route to `/api/twinstack/chat`, every one of those would break. We kept the route. We added new routes (`/api/swarm/{guid}/chat`, `/api/swarm/deploy`, `/api/t2t/*`) alongside the originals. Old clients see the old shape. New clients see the new shape. Both work against the same Function App.

**The pattern, generalized:**

When you graduate a working system to a new architecture, the rule is: **add, don't replace.** The new endpoints don't compete with the old ones — they sit alongside them. The data model gets richer (`swarm_guid` becomes a request dimension) but the OG shape still resolves correctly when `swarm_guid` is omitted (we default to the only-hosted-swarm if there's exactly one).

Backward compatibility is not just "the old API still works." It's "the old API still works *and* it benefits from the new infrastructure transparently." A request to `/api/businessinsightbot_function` today routes through the new swarm-aware code path, gets per-swarm memory isolation, gets sealing/snapshot guarantees, gets capability-gated T2T invocation possibilities — all without the caller knowing anything changed.

**Same wire, three implementations:**

The `swarm/server.py` (local stdlib) and `hippocampus/function_app.py` (Azure Functions) speak the same wire surface. So does the planned cross-device relay. A bundle that deploys to one deploys to all. A test against one passes against all (we have 148 tests proving it).

That's the `function_app.py` graduation: not "we rewrote the cloud brainstem." More like *we rewrote the room around it without moving the sacred furniture*.
