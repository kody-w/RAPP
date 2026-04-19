# The agent dispatch order: tether → live → stub

When the brainstem decides to call an agent, it goes through three executors in order:

```js
async function runAgent(card, kwargs, upstreamSlush) {
  const name = parseAgentSource(card.source).name;

  if (state.tether.connected && state.tether.agents.includes(name)) {
    try { return await runAgentTethered(name, kwargs); }
    catch (e) { console.warn('tether failed, falling through', e); }
  }
  if (state.settings.execMode === 'live') {
    try { return await runAgentLive(card, kwargs, upstreamSlush); }
    catch (e) { return JSON.stringify({status:'error', message:`live exec failed: ${e.message}`}); }
  }
  return runAgentStub(card, kwargs, upstreamSlush);
}
```

Three layers:

1. **Tether.** If the user has a tether enabled and the local agent runtime exposes this agent name, call it. Real OS, real filesystem, real network — whatever the user's machine can do.
2. **Live (Pyodide).** If tether is unavailable or the agent isn't there, run the agent's `perform()` in-browser via Pyodide. Sandboxed Python — math, string manipulation, basic HTTP through `pyodide.http`. No filesystem, no subprocess.
3. **Stub.** If both above fail (or the user is in stub mode for offline / debug reasons), synthesize a deterministic plausible result. The chat keeps going; the model gets a "[stub]" marker so it can mention that the call wasn't real.

Three executors, ordered by preference. Each one knows how to handle the case where the next one needs to take over.

**Why fall through silently?**

The first version logged "tether failed" as a chat error and stopped. Users would see a red message in the chat and an unfinished response. That was wrong on two counts: the *user* hadn't done anything wrong (their tether might have just been turned off), and the request *could* be answered by the next layer. Surfacing the failure interrupted the conversation for no reason.

Now: tether failure logs to the console, falls through to live, request gets answered. If both tether AND live fail, the live executor returns its own structured error envelope which the model interprets and explains. The user sees a coherent reply either way.

**Why the order matters:**

Each layer is "more powerful but less available" than the next. Tether reaches the user's machine — most powerful, least always-on. Live reaches anything Pyodide can do — moderately powerful, requires the Pyodide load. Stub reaches nothing real — least powerful, always works. Falling through gives you "best available execution" without forcing the user to choose.

**The pattern is testable:**

```js
// Tether down, live up
state.tether = {connected: false, agents: []};
state.settings.execMode = 'live';
// → runAgentLive()

// Tether up but doesn't have the agent
state.tether = {connected: true, agents: ['Other']};
// → runAgentLive()

// Tether throws
state.tether = {connected: true, agents: ['MyAgent']};
runAgentTethered = async () => { throw new Error('500'); };
// → falls to runAgentLive()
```

Each layer is independently testable; the dispatch logic is the only thing that knows about all three.

**The general pattern: ordered fallback executors.**

This shape — "I have N implementations of the same operation, prefer them in order, fall through on failure" — shows up everywhere:

- Image loaders (try WebP, fall back to JPEG, fall back to PNG).
- Storage backends (memory cache, then Redis, then database).
- Network paths (try local LAN, fall back to VPN, fall back to public internet).
- LLM providers (try local Ollama, fall back to OpenAI).

The shared design is the same: each layer either succeeds, returns a sentinel "I can't help," or throws (which the caller catches). The dispatcher tries them in declared order and lets the first one that works satisfy the request.

Three rules for getting it right:

1. **Order matters.** Most-preferred first. Most-reliable last.
2. **Fall through on failure, not on absence.** If a layer is unavailable (tether disconnected), skip it. If it's available but throws, log and skip. Don't propagate the error to the caller until you've exhausted the fallbacks.
3. **Make the last layer infallible.** Stub mode is the safety net. It always returns *something*. The model gets to see a result and write a sensible reply. Without an infallible bottom layer, your user sees "request failed."

Three executors. One dispatch function. The user gets the most powerful answer available without choosing a backend.
