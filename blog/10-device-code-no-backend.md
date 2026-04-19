# GitHub Copilot device-code flow without a backend

Most Copilot integrations are IDE plugins. They run locally, can talk to localhost callback servers, can store secrets in OS keychains, can open browsers programmatically. None of that is available to a static webpage on GitHub Pages.

The virtual brainstem at `kody-w.github.io/RAPP/brainstem/` authenticates users with GitHub Copilot anyway. The flow is end-to-end OAuth device-code — the same one the official Copilot CLI uses — adapted for a JavaScript caller running in a sandboxed browser tab. Three actors:

- **The browser** (the brainstem's JavaScript)
- **The Cloudflare Worker** (`rapp-auth.kwildfeuer.workers.dev`)
- **GitHub** (`github.com/login/device/code` and friends)

The worker exists because GitHub's OAuth endpoints don't set CORS. The browser can't call them directly. (See post #9.) The worker exists for one more critical reason: it holds the OAuth client secret. The secret is a `wrangler secret put` env var; the browser never sees it.

The flow:

1. **User clicks "Sign in with GitHub" in the brainstem.** The browser POSTs to `worker/api/auth/device`. The worker calls `github.com/login/device/code` with the client ID + secret and returns `{ user_code, verification_uri, device_code, interval }`.

2. **The brainstem opens a modal showing the user code.** "Go to https://github.com/login/device and enter ABCD-1234." The user copies the code or hits the link.

3. **Background polling.** The brainstem starts polling `worker/api/auth/device/poll` with the `device_code`, every 5 seconds. The worker proxies each poll to `github.com/login/oauth/access_token`. While the user hasn't approved yet, GitHub returns `authorization_pending`. We translate that into "still waiting" without surfacing as an error.

4. **User approves on github.com.** Their next action approves the OAuth grant.

5. **Next poll succeeds.** GitHub returns `{ access_token: "ghu_...", scope: "...", token_type: "bearer" }`. The worker passes this through. The brainstem stores `ghu_…` in `localStorage` as `state.settings.ghuToken`.

6. **Exchange for Copilot session bearer.** The `ghu_…` token isn't accepted directly by Copilot's chat endpoint. The brainstem POSTs to `worker/api/copilot/token` with the `ghu_…`. The worker calls `api.github.com/copilot_internal/v2/token` and returns `{ token: "...", endpoints: {api: "..."}, expires_at: 12345 }`. The brainstem caches that bearer; it's good for ~25 minutes. When it nears expiry, the brainstem re-exchanges silently.

7. **Chat.** Each chat request goes through `worker/api/copilot/chat` with the session bearer. The worker forwards to the right `api.individual.githubcopilot.com` endpoint with the right `Editor-Version` and `Copilot-Integration-Id` headers (Copilot's API silently rejects requests without them).

The user sees: "Sign in with GitHub" → device code in a modal → return to chat. About 15 seconds end-to-end. They never gave us their password. They never installed anything. They never created an API key. We never see their credentials, only short-lived bearers we cache in their own browser.

The pieces:
- Browser: ~80 lines of JS for the polling loop and bearer cache.
- Worker: ~150 lines of TypeScript for the proxy + OAuth-secret-holding.
- GitHub: provides the device-code primitives.

Three players, two endpoints, no backend database, no user accounts. The whole identity story is "if you have a Copilot subscription you can use this."

If you're shipping a static site that needs Copilot (or any OAuth-protected API), this is the smallest workable architecture. The worker is the only part that holds secrets. The browser holds short-lived bearers. The user holds their GitHub identity. Nobody holds their password.
