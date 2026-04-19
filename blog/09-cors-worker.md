# Cloudflare Workers as the CORS bandage

The virtual brainstem has a problem most static-site projects don't: it needs to call APIs that explicitly refuse to talk to browsers. GitHub Copilot's `api.individual.githubcopilot.com` doesn't set CORS headers, on purpose, because it was designed for the IDE plugins and not for arbitrary web pages. The device-code OAuth endpoint at `github.com/login/device/code` doesn't set CORS either.

Three options for a static site facing this:

1. Tell users to install a browser extension that disables CORS. (Bad. Asking users to weaken their browser is a non-starter.)
2. Run a backend server. (Bad. Now we're not a static site anymore. Now there's an ops surface.)
3. Run a Cloudflare Worker. (What we did.)

A Worker is a few hundred lines of JS that runs on Cloudflare's edge. The free tier is generous enough that this whole project's worker traffic costs literally zero dollars per month. It has no cold start in any meaningful sense. Deploy is `wrangler deploy`. Logs come for free.

The worker, `rapp-auth.kwildfeuer.workers.dev`, exposes a small set of endpoints that all do roughly the same thing: take a request from the browser, set the right auth headers, forward to the upstream API, copy the response back with permissive CORS headers.

```js
export default {
  async fetch(request, env, ctx) {
    if (request.method === 'OPTIONS') return cors(new Response(null, { status: 204 }));

    const url = new URL(request.url);
    if (url.pathname === '/api/copilot/chat') {
      const upstream = url.searchParams.get('endpoint') || COPILOT_DEFAULT;
      return cors(await proxyChat(request, upstream));
    }
    if (url.pathname === '/api/auth/device') return cors(await deviceStart(env));
    if (url.pathname === '/api/auth/device/poll') return cors(await devicePoll(request, env));
    if (url.pathname === '/api/copilot/token') return cors(await exchangeForCopilot(request));
    if (url.pathname === '/api/copilot/models') return cors(await cachedModels(env, ctx));
    return cors(new Response('not found', { status: 404 }));
  },
};
```

The endpoints in plain English:

- `/api/auth/device` — start GitHub's device-code flow, get a `user_code` and verification URL.
- `/api/auth/device/poll` — poll for the user completing the OAuth approval.
- `/api/copilot/token` — exchange the long-lived `ghu_…` token for a short-lived Copilot session bearer.
- `/api/copilot/chat` — proxy chat completions, since direct calls would 403.
- `/api/copilot/models` — proxy the model catalog, with edge caching to avoid rate limits.

CORS is whitelisted to `https://kody-w.github.io` and a few localhost ports. Edge cache (`caches.default`) keeps model-catalog responses warm for an hour, which dropped a noticeable rate-limit problem to zero.

Critical detail that's easy to miss: secrets (`GH_CLIENT_ID`, `GH_CLIENT_SECRET`) live in `wrangler secret put` env vars, never in the worker source. Browser code never sees them. The worker is the only piece that can complete the OAuth exchange because it's the only piece holding the secret.

The result: a static GitHub Pages site authenticates real users with GitHub, calls real Copilot models, persists nothing server-side, and pays nothing for the privilege. The Worker is the smallest possible "backend" — a single file's worth of code that does exactly one job: bridge the CORS gap.

If you're building anything that runs in a browser and needs to call non-CORS APIs, this is the pattern. Cloudflare Workers, Deno Deploy, AWS Lambda function URLs, Vercel Edge Functions — pick your provider, the shape is the same.
