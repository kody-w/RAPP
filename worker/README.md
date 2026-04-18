# rapp-auth — Cloudflare Worker

Tiny zero-state worker that lets the browser-only RAPP Virtual Brainstem talk to GitHub:

| Endpoint | Purpose |
|---|---|
| `POST /api/auth/token` | OAuth code → token exchange (the one step that needs `client_secret`, which can't live in the browser). |
| `GET /api/models` | Proxies `https://models.github.ai/catalog/models` and adds CORS headers. The upstream doesn't send `Access-Control-Allow-Origin` to GitHub Pages, so we relay through here. |
| `GET /api/user` | Optional convenience proxy for `https://api.github.com/user` (consistent surface; browser can call upstream directly too). |
| `GET /healthz` | Liveness probe. |

The whole thing is one file: [`worker.js`](./worker.js). ~120 lines, no deps.

## Setup (one time, ~3 minutes)

1. **Register a GitHub OAuth App** dedicated to the RAPP brainstem.
   - GitHub → Settings → Developer settings → **OAuth Apps** → **New OAuth App**
   - **Application name:** `RAPP Virtual Brainstem`
   - **Homepage URL:** `https://kody-w.github.io/RAPP/`
   - **Authorization callback URL:** `https://kody-w.github.io/RAPP/brainstem/`
   - Click **Register application**
   - Copy the **Client ID**
   - Click **Generate a new client secret** → copy that too

2. **Deploy the worker.**

   ```bash
   cd worker
   npx wrangler login                            # one-time, opens a browser
   npx wrangler secret put GH_CLIENT_ID          # paste the client id
   npx wrangler secret put GH_CLIENT_SECRET      # paste the client secret
   npx wrangler deploy
   ```

   Wrangler prints something like `https://rapp-auth.<your-subdomain>.workers.dev`.

3. **Wire it into the brainstem.** Open `brainstem/index.html` and update the two
   constants at the top of the inline script:

   ```js
   const AUTH_CLIENT_ID  = '<paste the OAuth App Client ID>';
   const AUTH_WORKER_URL = 'https://rapp-auth.<your-subdomain>.workers.dev';
   ```

   Commit + push. Done.

## Notes

- The worker holds **no user state** — it doesn't store tokens, doesn't log requests, doesn't have a database. It's just a stateless courier.
- The OAuth code exchange happens once per sign-in. The resulting GitHub token then talks **directly** from the browser to `https://models.github.ai/inference/chat/completions` — no proxy in the chat path.
- The catalog proxy edge-caches for 5 minutes (`cf: { cacheTtl: 300 }`) so most browser loads return instantly from Cloudflare without hitting GitHub.
- `ALLOWED_ORIGINS` in `worker.js` whitelists `https://kody-w.github.io` plus localhost. Add your fork's origin if you're hosting elsewhere.

## Why a dedicated worker?

The existing `rappterbook-auth` worker also does OAuth, but bundling RAPP behind it would couple two unrelated apps. Keeping `rapp-auth` isolated means: (1) RAPP can rotate its client secret without touching rappterbook, (2) different OAuth scopes and callback URLs per app, (3) the worker code stays small and auditable.
