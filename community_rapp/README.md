# Hippocampus — Twin Stack on Azure Functions

`hippocampus/` is the deployed cloud estate for a hatched twin. Same wire surface as the local `swarm/server.py` (deploy/agent/seal/snapshot/T2T) plus an LLM-driven `/api/chat` that mirrors the OG community RAPP's `businessinsightbot_function` shape.

## Layout

```
hippocampus/
  function_app.py             ← Azure Functions Python v2 entrypoint
  host.json                   ← runtime config (extension bundle 4.x)
  requirements.txt            ← azure-functions
  local.settings.json.example ← copy → local.settings.json for `func start`
  build.sh                    ← vendors ../swarm/* into ./_swarm/
  provision-twin.sh           ← one-shot Azure deploy per twin
  index.html                  ← static landing page (existing)
```

## One-time per twin: provision an isolated cloud

Each twin gets its **own resource group**, **own Function App**, **own Azure OpenAI**, **own storage** — all in the same subscription/tenant.

```bash
# Kody's twin
bash hippocampus/provision-twin.sh kody

# Molly's twin
bash hippocampus/provision-twin.sh molly
```

Defaults (override with env vars):

| Var               | Default                                                  |
|-------------------|----------------------------------------------------------|
| `SUBSCRIPTION_ID` | `3d0e6986-1b31-4189-a394-b3289d54efb0` (VS Enterprise)    |
| `LOCATION`        | `eastus2`                                                |
| `OPENAI_LOCATION` | `eastus2`                                                |
| `OPENAI_MODEL`    | `gpt-4o`                                                 |
| `OPENAI_DEPLOYMENT` | same as model                                          |

What it does:

1. `az login` (if needed) → set subscription
2. Creates `rg-twin-<name>` resource group
3. ARM-deploys `azuredeploy.json` (Function App + Storage + OpenAI + RBAC)
4. Layers root `.env` keys onto Function App app settings
5. Vendors the swarm core into `_swarm/`
6. `func azure functionapp publish` — pushes `function_app.py` live
7. Prints health-check + chat URLs

Tear-down (when you're done):

```bash
az group delete --name rg-twin-kody --yes --no-wait
```

## After provisioning

The Function App is empty. Hatch the twin's cloud into it:

1. Open `https://kody-w.github.io/RAPP/brainstem/onboard/`
2. Set the endpoint to the Function App URL printed at the end of provisioning
3. Click `Kody's Founder-Engineer Twin` (or `Molly's CEO Twin`) → **🚀 Push to endpoint**

The twin is now live. Try it:

```bash
curl -X POST "https://<APP_NAME>.azurewebsites.net/api/chat" \
    -H 'Content-Type: application/json' \
    -d '{"user_input":"What should I focus on this week?"}'
```

## Local dev

```bash
# Vendor swarm core, install deps, start the function host
bash hippocampus/build.sh
cp hippocampus/local.settings.json.example hippocampus/local.settings.json
# (paste your AZURE_OPENAI_API_KEY into local.settings.json)
cd hippocampus && func start
```

## Wire surface

All routes prefixed with `/api/`:

| Method  | Path                                        | What it does                          |
|---------|---------------------------------------------|---------------------------------------|
| POST    | `chat`                                      | LLM-driven chat (defaults to single hosted swarm) |
| POST    | `businessinsightbot_function`               | OG CommunityRAPP wire compat          |
| GET     | `swarm/healthz`                             | List swarms + LLM provider status     |
| GET     | `swarm/{guid}/healthz`                      | Per-swarm info                        |
| POST    | `swarm/deploy`                              | Hatch a `rapp-swarm/1.0` bundle       |
| POST    | `swarm/{guid}/agent`                        | Single-agent call                     |
| POST    | `swarm/{guid}/chat`                         | LLM-driven chat against this swarm    |
| GET/POST | `swarm/{guid}/seal`                        | Seal status / seal it                 |
| POST    | `swarm/{guid}/snapshot`                     | Create snapshot                       |
| GET     | `swarm/{guid}/snapshots`                    | List snapshots                        |
| POST    | `swarm/{guid}/snapshots/{snap}/agent`       | Read-only agent call against snapshot |
| GET/POST | `t2t/identity`, `t2t/peers`, `t2t/handshake`, `t2t/message`, `t2t/invoke` | Twin-to-twin protocol |
| GET     | `llm/status`                                | Which LLM provider is wired           |

## Why a hippocampus and not a brainstem?

`brainstem/` is the browser-side runtime — autonomic, reactive, lives on the user's device.
`hippocampus/` is the **memory + reflection** runtime — runs in the cloud, hosts long-running swarms, persists conversations, and answers when called.

Local-first by default; this is the optional cloud surface for twins that need to be reachable from anywhere.
