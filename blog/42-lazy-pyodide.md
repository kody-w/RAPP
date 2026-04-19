# Lazy Pyodide: 10MB only when you need it

Pyodide is the Python runtime that runs in a browser. Compiled with Emscripten, it's a few-MB WASM bundle plus a stdlib distribution. The brainstem uses it to run agents (`*_agent.py` files) directly in the page — no server needed, no Python install needed, the user's browser is the runtime.

That's the good news. The bad news: Pyodide is about 10MB on first load. For users who never call an agent (they're just chatting, no tool use), making them download 10MB of WASM up front would be cruel. So we don't.

```js
async function ensurePyodide() {
  if (state.pyodide) return state.pyodide;
  if (state.pyodideLoading) return state.pyodideLoading;
  state.pyodideLoading = (async () => {
    // Inject the loader script tag.
    await new Promise(r => {
      const s = document.createElement('script');
      s.src = 'https://cdn.jsdelivr.net/pyodide/v0.27.5/full/pyodide.js';
      s.onload = r;
      document.head.appendChild(s);
    });
    state.pyodide = await window.loadPyodide();
    return state.pyodide;
  })();
  return state.pyodideLoading;
}
```

Three properties:

**Lazy.** No `<script>` tag for Pyodide in the HTML. No download until `ensurePyodide()` is called for the first time. The brainstem boots, signs the user in, lets them chat with the model, and Pyodide is still untouched if no agent has fired.

**Promise-shared.** The first call sets `state.pyodideLoading` to the in-flight promise. Subsequent calls before the load finishes await the same promise. No double-loading, no race condition.

**Cached.** Once loaded, `state.pyodide` holds the runtime; future calls return immediately. The 10MB cost is paid once per session.

The first agent call has measurable latency — about 3-5 seconds on a fast connection while the WASM loads. The user sees a "loading Pyodide" indicator in the chat. After that, agent calls are fast (the runtime is warm, agents import in milliseconds).

**Could we do better?**

Yes, with prefetching. We could trigger `ensurePyodide()` in the background after a sign-in event, on the assumption that "anyone signing in is likely to use agents soon." Cost: 10MB even for users who only chat. Benefit: zero-latency first agent call.

Decision: don't prefetch. The penalty for a chat-only user (paying 10MB they'll never use) is worse than the penalty for an agent-first user (paying 5 seconds the first time). Most user sessions are chat-heavy and tool-light; the few seconds of first-tool latency is acceptable.

**The fallback when Pyodide is slow / fails:**

The agent dispatch order (tether → live → stub) provides a safety valve. If `ensurePyodide()` somehow fails — bad network, blocked CDN, browser without WASM support — the live executor returns an error envelope and the stub layer (or the tether, if available) takes over. The chat keeps working; tool calls just degrade.

**The pattern generalizes:**

For any expensive runtime / library / SDK that's *conditionally* needed:

- Don't ship it in your initial bundle.
- Hide the load behind a `ensureX()` function with a promise lock.
- Cache the result.
- Have a fallback path for when the load fails.

This is the same pattern as image lazy-loading, code-splitting in webpack, dynamic imports in modern bundlers. The principle is older than any of those tools: the cost of *might-need* is a tax on every user who *doesn't* need it. Defer until proven necessary.

**A note on CDN choice:**

We load from `cdn.jsdelivr.net`. Other options were unpkg, the official Pyodide CDN, and self-hosting. jsDelivr won because:

- Free, fast, globally cached.
- Versions are pinnable in the URL.
- Doesn't 404 randomly the way unpkg occasionally does.
- Self-hosting 10MB on GitHub Pages is fine but slow (no CDN behind it).

If jsDelivr ever gets unreliable we'll mirror to a Cloudflare R2 bucket or similar. Until then, the path of least resistance is right.

10MB is a lot. Loading it lazily makes it free for users who don't need it and bearable for users who do. The latency is real; the alternative — making everyone pay up front — is worse.
