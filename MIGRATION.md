# Migration: v1.7 → v1.8

This release consolidates the directory layout to align with `rapp-installer` and bakes the binder into the brainstem as a first-class API. **Net: less moving parts.**

## Folder moves

| Before                              | After                                              |
|-------------------------------------|----------------------------------------------------|
| `swarm/server.py`                   | `rapp_brainstem/brainstem.py`                      |
| `swarm/{chat,llm,t2t,workspace,_basic_agent_shim}.py` | `rapp_brainstem/{chat,llm,t2t,workspace,_basic_agent_shim}.py` |
| `hippocampus/function_app.py`       | `community_rapp/function_app.py`                   |
| `hippocampus/{twin-egg,twin-sim,provision-twin,build}.sh` | `community_rapp/{...}.sh`                          |
| `hippocampus/_swarm/` (vendored swarm) | `community_rapp/_vendored/` (vendored brainstem)  |
| `brainstem/{index.html,rapp.js,mobile,onboard}` | `rapp_brainstem/web/{index.html,rapp.js,mobile,onboard}` |
| `agents/basic_agent.py` etc.        | `rapp_brainstem/agents/*` (system defaults only)  |
| `agents/persona_*` etc.             | `rapplications/bookfactory/source/`                |
| `agents/sensorium_*` etc.           | `rapplications/momentfactory/source/`              |
| `agents/bookfactory_agent.py`       | `rapplications/bookfactory/singleton/bookfactory_agent.py` |
| `agents/momentfactory_agent.py`     | `rapplications/momentfactory/singleton/momentfactory_agent.py` |

**Removed** (no longer needed):
- `swarm/` — superseded by `rapp_brainstem/`
- `hippocampus/` — superseded by `community_rapp/`
- `brainstem/` (the JS frontend dir) — superseded by `rapp_brainstem/web/`
- `agents/` at top-level — system defaults moved into `rapp_brainstem/agents/`

## API additions: the binder is in the brainstem

The brainstem now exposes `/api/binder/*` alongside `/api/swarm/*`, `/api/workspace/*`, `/api/llm/*`, `/api/t2t/*`. Per-twin binder state lives at `<root>/.binder.json` (schema `rapp-binder/1.0`). Installation materializes a singleton from `rapplications/<name>/singleton/` into `<root>/agents/`. Hot-load + execute happens in-process via `/api/binder/agent` (no swarm GUID needed).

| Method | Path                              | Purpose                                                |
|--------|-----------------------------------|--------------------------------------------------------|
| GET    | `/api/binder`                     | Show installed rapplications for this twin             |
| GET    | `/api/binder/catalog`             | Proxy local `store/index.json`                          |
| POST   | `/api/binder/install`             | `{id}` → materialize singleton + record install        |
| DELETE | `/api/binder/installed/{id}`      | Remove file + record                                   |
| POST   | `/api/binder/sync`                | Re-materialize from `.binder.json`                     |
| POST   | `/api/binder/agent`               | `{name, args}` → execute installed rapplication        |

SHA-256 mismatch on install is rejected — pinned hashes from the catalog must match the file on disk.

## Routes that haven't changed yet

`/api/swarm/*` is intact. The `swarm` naming will sunset in v2.0 (a separate hard cutover where `/api/swarm/*` → `/api/brainstem/*`). For now, the directory move is enough.

## Test count

| Suite                       | v1.8 result |
|-----------------------------|-------------|
| `test-rapplication-store.sh`| 5/5         |
| `test-rarbookworld-publish.sh` | 4/4 (sectioned)|
| `test-momentfactory.sh`     | 20/20       |
| `test-binder.sh` (new)      | 18/18       |
| `test-bookfactory-v2.sh`    | 19/19       |
| `test-twin-egg.sh`          | 15/15       |
| `test-sealing-snapshot.sh`  | 23/23       |
| `test-llm-chat.sh`          | 8/8         |
| `run-tests.mjs`             | 63/63       |
| **Total**                   | **175 assertions, 0 failed** |

## What's next (v2.0)

1. Hard-cutover `/api/swarm/*` → `/api/brainstem/*` (no aliases — aliases are tech debt).
2. Merge `rapp_brainstem/brainstem.py.legacy-chat-flask` (the rapp-installer-style `/chat` route + Copilot OAuth) into `rapp_brainstem/brainstem.py`. One brainstem with both deploy/GUID and `/chat` flows.
3. Delete `rapp_brainstem/brainstem.py.legacy-chat-flask` once merged.
