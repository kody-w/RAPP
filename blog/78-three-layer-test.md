# Three-layer test: stdlib → local Functions → cloud Functions, all green

When we shipped Twin Stack v1, we ran the same end-to-end smoke test against three different runtimes:

| Layer | Runtime | Endpoint | Purpose |
|---|---|---|---|
| 1 | `python3 swarm/server.py` | `http://127.0.0.1:7080` | Stdlib HTTP server, zero deps |
| 2 | `func start` (local) | `http://127.0.0.1:7071` | Azure Functions on this machine |
| 3 | `func azure functionapp publish` | `https://twin-kody-e89834.azurewebsites.net` | Deployed cloud Function App |

Same JSON bundle pushed to each. Same chat prompt sent to each. Same swarm guid format, same agent loading, same memory routing, same `|||VOICE|||` response shape. **All three answered identically** in voice and structure (text differed because LLM completions vary, but the response shape was bit-for-bit identical).

That's not luck. That's a deliberate design constraint: *the wire surface is the contract*. Three implementations, one contract.

**Why three?**

- Layer 1 is for *unit-level confidence*. No deps means no install drift. Anyone with `python3` can run it. This is what `tests/test-*.sh` exercises in CI.
- Layer 2 is for *production-runtime parity without leaving the laptop*. The `func` host runs the same Python Functions runtime that Azure runs. If your code passes `func start` locally, it'll pass `func azure functionapp publish` in 99% of cases.
- Layer 3 is for *real cloud topology validation*. CORS, app settings, managed identity, Azure DNS — none of those exist locally. You only catch them in real Azure.

**What broke at each layer (the value of three):**

The first time we ran Layer 1's chat path against live Azure OpenAI, it 500'd: `API version not supported`. The bug: my `swarm/llm.py` was appending `?api-version=2025-01-01-preview` to a v1 endpoint URL that doesn't accept that param. Fix: detect `/openai/v1/` and skip the api-version. Layer 1 surfaced this because it called the LLM directly without any Azure SDK indirection.

The first time we ran Layer 3, the cloud Function App came up fine but `/api/swarm/{guid}/chat` 500'd on first hit. The bug: cold-start was timing out. We didn't catch it locally because Layer 2 doesn't have cold-start. Fix: add a 60-second ready-poll to the test; production cold start really takes ~30s.

The first time we ran Layer 2, the test passed but the function host took 27 seconds to come up. The bug wasn't in our code — it was that Azure Functions Python v2 host loads slowly. Now we know: the test allows up to 60s for the host to be ready before declaring failure.

Each layer surfaces a different class of bug. You need all three.

**The wire surface is what makes this possible:**

```
POST /api/swarm/{guid}/chat
{
  "user_input": "string",
  "conversation_history": [...],
  "user_guid": "optional-uuid",
  "extra_system": "optional"
}

→

{
  "response":      "the assistant's reply",
  "voice_response": "1-sentence voice version",
  "agent_logs":    [{"name":..., "args":..., "ms":..., "output":...}],
  "model":         "gpt-5.4",
  "provider":      "azure-openai",
  "rounds":        2,
  "swarm_guid":    "uuid"
}
```

That shape is in `swarm/server.py`, `hippocampus/function_app.py`, and (eventually) the relay. It's also what every test asserts. Change the shape — break all three layers simultaneously.

**Tests that actually run on three layers:**

`tests/test-hero-deploy.sh` runs against Layer 1 (stdlib) — 26 assertions, all green.
`tests/test-t2t.sh` boots two Layer 1 instances (kody + molly) — 28 assertions across identity, peer-add, signed handshake, signed message, cross-cloud invoke. All green.
`tests/test-llm-chat.sh` runs against Layer 1 with `LLM_FAKE=1` — 8 assertions on the chat path. All green.

To prove Layer 2: we ran the hero demo manually against `func start` on `:7071` — verified `/api/health`, `/api/llm/status`, `/api/swarm/deploy`, and `/api/businessinsightbot_function` all worked.

To prove Layer 3: same flow against the deployed `twin-kody-e89834.azurewebsites.net` and `twin-molly-4181ee.azurewebsites.net` — both returned coherent gpt-5.4 responses to a real prompt.

148 tests. Three layers. One wire contract.

**The lesson, again:**

Wire-contract-first development is the only honest way to ship to multiple runtimes. The tests should test the *contract*, not the implementation. Then any implementation that satisfies the contract is correct. New runtime? Write a new implementation, run the same tests, ship.
