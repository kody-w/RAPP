# Historical Rapplication SDK

> **Current RAPP/1 authority (rev-5).** For canonicalization, identity, frames,
> wire, eggs, registry, trust, and protocol evolution, follow
> [`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../RAPP1_STATUS.md). RAPP agents remain agents; their
> wire and distribution must use RAPP/1 §§8–9.

> **Whole-document disposition:** this SDK, its drop-to-install flow, service
> routes, cross-tier portability, store catalog, legacy egg pairing, and
> browser examples are not shipped current capabilities. They are preserved
> for migration and design history only. A future accepted rapplication must
> use the exact §8 façade and a verified §9 `rapplication` variant.

<!-- RAPP1-HISTORICAL-SECTION-START -->

## What is a rapplication?

A rapplication is the installable unit in the RAPP ecosystem. It's one or two files:

1. **Agent file** (required) — `*_agent.py`. The primary interface. Any LLM that speaks tool calls can drive it: brainstem chat, Copilot Studio, Claude, GPT, or anything that comes next.
2. **Service file** (optional) — `*_service.py`. Application-local HTTP views
   or adapter ingress for a UI. It is not an additional RAPP capability
   surface and must not bypass the agent, frames, or trust checks.

Install = drop files in. Uninstall = delete them. Nothing else.

> **Current distribution:** use the RAPP/1 §9 `rapplication` variant and its
> exact manifest, deterministic ZIP, integrity/viability checks, and applicable
> signature verification. The 2026-05-10 `brainstem-egg/2.2-rapplication` and
> `brainstem-egg/2.3-session` forms are retired migration inputs; the existing
> schema/type hatcher is not current acceptance authority.

## The agent-first rule

> **The agent is the API. The service is a view.**

Every rapplication MUST work fully through `perform()` alone. The service is always optional — if removing it breaks the agent, the design is wrong.

At a RAPP protocol boundary, synchronous capability invocation is the exact
§8 `POST /chat`; asynchronous work is a verified §7 frame. `/api/*` service
routes are application views/adapters only and never expand that wire.

## Quick start: build a rapplication in 5 minutes

### Step 1: The agent file

Create `my_thing_agent.py`:

```python
"""
my_thing_agent.py — A thing manager you can talk to.

Agent-first: works through any LLM with no UI required.
Storage: .brainstem_data/my_thing.json
"""

import json
import uuid
import os
from datetime import datetime
from agents.basic_agent import BasicAgent


__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "@rapp/my_thing",
    "version": "1.0.0",
    "display_name": "MyThing",
    "description": "Manages things through conversation.",
    "author": "you",
    "tags": ["your-tag", "rapplication"],
    "category": "general",
    "quality_tier": "community",
    "requires_env": [],
    "example_call": "Create a new thing called hello",
}


def _data_path():
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        ".brainstem_data", "my_thing.json"
    )


def _read():
    path = _data_path()
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {"things": {}}


def _write(data):
    path = _data_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


class MyThingAgent(BasicAgent):
    def __init__(self):
        self.name = "MyThing"
        self.metadata = {
            "name": self.name,
            "description": (
                "Manages things. Use this to create, list, update, or "
                "delete things."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["create", "list", "update", "delete"],
                        "description": "What to do.",
                    },
                    "item_id": {
                        "type": "string",
                        "description": "Thing ID (for update/delete).",
                    },
                    "name": {
                        "type": "string",
                        "description": "Name of the thing.",
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional description.",
                    },
                },
                "required": ["action"],
            },
        }
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        action = kwargs.get("action", "list")
        data = _read()

        if action == "create":
            name = kwargs.get("name", "Untitled")
            desc = kwargs.get("description", "")
            tid = str(uuid.uuid4())[:8]
            data["things"][tid] = {
                "name": name,
                "description": desc,
                "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
            _write(data)
            return json.dumps({"status": "ok", "summary": f'Created "{name}" (ID: {tid})'})

        if action == "list":
            if not data["things"]:
                return json.dumps({"status": "ok", "summary": "No things yet."})
            lines = [f"  - [{tid}] {t['name']}" for tid, t in data["things"].items()]
            return json.dumps({"status": "ok", "summary": "\n".join(lines)})

        if action == "update":
            tid = kwargs.get("item_id", "")
            if tid not in data["things"]:
                return json.dumps({"status": "error", "summary": f"Not found: {tid}"})
            if kwargs.get("name"):
                data["things"][tid]["name"] = kwargs["name"]
            if kwargs.get("description"):
                data["things"][tid]["description"] = kwargs["description"]
            _write(data)
            return json.dumps({"status": "ok", "summary": f"Updated {tid}"})

        if action == "delete":
            tid = kwargs.get("item_id", "")
            if tid not in data["things"]:
                return json.dumps({"status": "error", "summary": f"Not found: {tid}"})
            removed = data["things"].pop(tid)
            _write(data)
            return json.dumps({"status": "ok", "summary": f'Deleted "{removed["name"]}"'})

        return json.dumps({"status": "error", "summary": f"Unknown action: {action}"})
```

### Step 2: Drop it in

```
cp my_thing_agent.py ~/.brainstem/src/rapp_brainstem/agents/
```

That's it for host discovery. Next `/chat` request discovers it without local
plugin registration. This does not waive RAPP/1 §13 registration for any
protocol kind, variant, or error code the agent emits.

### Step 3 (optional): Add an HTTP service

Create `my_thing_service.py`:

```python
"""
my_thing_service.py — Optional HTTP layer for MyThing.

Reads/writes the same .brainstem_data/my_thing.json that
my_thing_agent.py uses. The agent works without this.
"""

import json
import os
import uuid
from datetime import datetime

name = "my_thing"

_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".brainstem_data"
)
_STATE_FILE = os.path.join(_DATA_DIR, "my_thing.json")


def _read():
    if os.path.exists(_STATE_FILE):
        with open(_STATE_FILE) as f:
            return json.load(f)
    return {"things": {}}


def _write(data):
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(_STATE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def handle(method, path, body):
    data = _read()

    # GET /api/my_thing — list all
    if method == "GET" and path == "":
        return data, 200

    # POST /api/my_thing/items — create
    if method == "POST" and path == "items":
        tid = str(uuid.uuid4())[:8]
        data["things"][tid] = {
            "name": body.get("name", "Untitled"),
            "description": body.get("description", ""),
            "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        _write(data)
        return {"status": "ok", "id": tid}, 201

    # PUT /api/my_thing/items/<id> — update
    if method == "PUT" and path.startswith("items/"):
        tid = path[len("items/"):]
        if tid not in data["things"]:
            return {"error": "not found"}, 404
        if "name" in body:
            data["things"][tid]["name"] = body["name"]
        if "description" in body:
            data["things"][tid]["description"] = body["description"]
        _write(data)
        return {"status": "ok"}, 200

    # DELETE /api/my_thing/items/<id>
    if method == "DELETE" and path.startswith("items/"):
        tid = path[len("items/"):]
        if tid not in data["things"]:
            return {"error": "not found"}, 404
        data["things"].pop(tid)
        _write(data)
        return {"status": "ok"}, 200

    return {"error": "not found"}, 404
```

Drop it in:

```
cp my_thing_service.py ~/.brainstem/src/rapp_brainstem/services/
```

Now `GET /api/my_thing` works alongside the agent.

## Contracts

### Agent contract

| Requirement | Details |
|-------------|---------|
| File pattern | `*_agent.py` |
| Location | `agents/` directory |
| Base class | Extends `BasicAgent` |
| `metadata` dict | OpenAI function-calling schema (name, description, parameters) |
| `perform(**kwargs)` | Returns a JSON string. The LLM reads this. |
| `__manifest__` dict | Optional. Registry metadata (name, version, tags, category). |
| `system_context()` | Optional. Returns text injected into system prompt every turn. |
| Dependencies | Zero external deps preferred. Missing pip packages auto-install at load time. |
| Discovery | Auto-discovered on every request. No registration. |

### Service contract

| Requirement | Details |
|-------------|---------|
| File pattern | `*_service.py` |
| Location | `services/` directory |
| `name` (module-level string) | URL namespace. `name = "kanban"` → `GET /api/kanban/...` |
| `handle(method, path, body)` | Returns `(dict, status_code)`. That's the entire contract. |
| Shared storage | Read/write the same `.brainstem_data/{name}.json` as the agent. |
| LLM visibility | None. Services are invisible to the LLM. |
| Discovery | Auto-discovered on every request. No registration. |

### Shared storage pattern

Both files use the same storage path:

```python
# In the agent (lives in agents/):
def _data_path():
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        ".brainstem_data", "my_thing.json"
    )

# In the service (lives in services/):
_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".brainstem_data"
)
_STATE_FILE = os.path.join(_DATA_DIR, "my_thing.json")
```

Both resolve to the same file. The agent is the source of truth; the service is a view.

## Rules

1. **Agent-first.** The agent MUST work without the service. Always.
2. **Single file.** One agent = one `.py` file. One service = one `.py` file. No multi-file rapplications.
3. **Zero config.** No `.env` edits, no registration, no build steps. Drop in and go.
4. **Portable.** The same agent file runs in Tier 1 (local brainstem), Tier 2 (Azure Functions), and Tier 3 (Copilot Studio) without modification.
5. **JSON in, JSON out.** `perform()` returns a JSON string. `handle()` returns a `(dict, int)` tuple. No exceptions.
6. **Shared storage.** Agent and service read/write the same `.brainstem_data/{name}.json`. Never two sources of truth.

## Best practice: agents drive both UI hydration AND chat

The same `*_agent.py` files that the brainstem hot-loads for `/chat` should be the **only** data source the rapplication's UI uses to hydrate. Two birds, one stone:

- **Through chat**, the operator says "show me X" and the LLM picks the agent, fills in args, calls `perform()`, returns a natural-language answer.
- **For UI hydration**, the rapplication calls the same `perform()` directly with **static, predetermined inputs** — bypassing the LLM entirely. One shot, deterministic, no follow-up questions, no token cost, no clarification rounds.

A "rapplication renderer" agent (e.g. `xyz_dashboard_render_agent.py`) is just a thin composition: it imports its sibling agents, calls them with hardcoded action + parameter dicts, assembles their JSON outputs, renders an HTML file to disk, and returns the path. The HTML is self-contained; the operator opens it in a browser. Re-run + refresh = updated state.

The pattern in code:

```python
def perform(self, **kwargs) -> str:
    # Static inputs — no LLM in the loop
    team = self._call("CustomerProjectPingerAgent",
                       "agents.customer_project_pinger_agent",
                       action="team_status")
    nudge = self._call("BillTwinAgent",
                        "agents.bill_twin_agent",
                        action="next_move")
    pm = self._call("BwatPmAgent", "agents.bwat_pm_agent",
                     action="status_report", lookback_days=7)

    html = self._render(team=team, nudge=nudge, pm=pm)
    out_path = os.path.expanduser("~/.bwat-data/<handle>/dashboard.html")
    open(out_path, "w").write(html)
    return json.dumps({"ok": True, "html_path": out_path,
                        "open_in_browser": f"file://{out_path}"})
```

Why this pattern is load-bearing:

- **Zero logic duplication.** The rapplication doesn't reimplement `team_status` — every fix to `CustomerProjectPinger` automatically improves the dashboard with no changes here.
- **Determinism.** Same inputs → same outputs every render. The UI is reliable in a way LLM-routed UIs cannot be.
- **Speed + cost.** No LLM call latency, no token spend per render.
- **Reuse for chat.** The same agents the rapplication composes are still callable through `/chat` — operators get conversational access to the exact same data the UI shows.

If your rapplication's UI duplicates logic that already lives in a brainstem agent, you're holding it wrong. Move the logic into the agent; have the rapplication call it.





### The docstring IS the readme (sacred)

**No separate `README.md`, `README.txt`, `INSTRUCTIONS.md`, `SETUP.md`, or any other accompanying documentation file in a sneakernet payload.** The bootstrap agent's top-level docstring is the readme. Adding a third file expands the payload past two files and breaks the invariant — there is no exception, including "but it's just a README."

The agent's docstring MUST contain:

1. **A human-readable section** at the top stating: "you received this file along with a `.egg`," followed by the literal two steps (drag this `.py` into your brainstem's `agents/` directory; send one chat command). The first thing a human opening the file in a text editor sees should be the entire setup procedure.

2. **An LLM-readable section** giving the LLM the same procedure plus the
   boundary rules it must honor (complete RAPP/1 §9.3 and applicable §§10/13
   verification—not SHA-256 alone—no `git commit` without consent, no shell
   commands suggested to the operator, no improvised extra steps). Any LLM
   shown the agent.py file should be able to drive setup without another
   protocol source.

3. **The complete mode reference** — every action argument the bootstrap agent accepts (`from_egg`, `from_repo`, `pack_egg`, `status`), with one-line descriptions of each.

This discipline forces the readme to live in the same file as the bootstrap code, so they cannot get out of sync. It also forces brevity: a docstring is not a place for marketing copy or aspirational design notes; it is the operator's literal instruction sheet.

A 4–6 KB docstring is a reasonable target. Smaller is better when possible. Anything materially over 10 KB suggests the docstring is reaching for the role of a manual; trim it back to the procedure.

If you find yourself wanting to add a `README.md` "just for one extra paragraph," you have two choices: (a) put the paragraph in the docstring, or (b) put it in a markdown file *inside* the .egg (where it gets unpacked into the receiver's workspace post-hatch and is no longer part of the sneakernet payload). Never a third file alongside the .py and .egg.

## Publishing to the RAPPstore



## The sneakernet portability invariant

**A portable artifact shared between operators consists of EXACTLY two files: one `agent.py` + one `.egg`. The receiver MUST be able to use it with two actions only — drag the `.py` into their brainstem's `agents/` directory, and chat one command. Anything else is not portable.**

This rule is non-negotiable. If your sharing flow requires the receiver to:

- Run a shell command (any: `cd`, `pip install`, `bash setup.sh`, `cp`)
- Edit a config file by hand
- Restart their brainstem
- Set environment variables
- Have a second tool installed beyond the brainstem itself
- Send a follow-up chat to "complete" the setup

…then your artifact is **not sneakernet-portable** and cannot be considered a portable neighborhood, rapplication, or workflow pack.

The bootstrap agent is responsible for everything past the drag-and-drop:

- Detecting the operator's handle (gh / env / arg)
- Unpacking the .egg / cloning the repo / starting from a template
- Verifying the complete RAPP/1 §9 manifest, contents, viability, and any
  applicable signature
- Installing all workflow agents into the brainstem
- Reusing the stored §6 rappid, or minting once per §6.2 only when identity is
  genuinely absent; never derive it from a name or silently re-mint
- Minting the operator's per-handle workspace (front door + local data dir)
- Recording the subscription
- Returning a single message that tells the operator the workflow is ready

ONE agent. ONE chat. Done.

The corollary is that the bootstrap agent is necessarily multi-mode — it handles every scenario the receiver might be in: airgapped (`from_egg`), online (`from_repo`), packing for re-share (`pack_egg`), readiness probe (`status`). There is no "offline bootstrap" vs "online bootstrap"; there is one bootstrap with mode arguments.




### The docstring IS the readme (sacred)

**No separate `README.md`, `README.txt`, `INSTRUCTIONS.md`, `SETUP.md`, or any other accompanying documentation file in a sneakernet payload.** The bootstrap agent's top-level docstring is the readme. Adding a third file expands the payload past two files and breaks the invariant — there is no exception, including "but it's just a README."

The agent's docstring MUST contain:

1. **A human-readable section** at the top stating: "you received this file along with a `.egg`," followed by the literal two steps (drag this `.py` into your brainstem's `agents/` directory; send one chat command). The first thing a human opening the file in a text editor sees should be the entire setup procedure.

2. **An LLM-readable section** giving the LLM the same procedure plus the
   boundary rules it must honor (complete RAPP/1 §9.3 and applicable §§10/13
   verification—not SHA-256 alone—no `git commit` without consent, no shell
   commands suggested to the operator, no improvised extra steps). Any LLM
   shown the agent.py file should be able to drive setup without another
   protocol source.

3. **The complete mode reference** — every action argument the bootstrap agent accepts (`from_egg`, `from_repo`, `pack_egg`, `status`), with one-line descriptions of each.

This discipline forces the readme to live in the same file as the bootstrap code, so they cannot get out of sync. It also forces brevity: a docstring is not a place for marketing copy or aspirational design notes; it is the operator's literal instruction sheet.

A 4–6 KB docstring is a reasonable target. Smaller is better when possible. Anything materially over 10 KB suggests the docstring is reaching for the role of a manual; trim it back to the procedure.

If you find yourself wanting to add a `README.md` "just for one extra paragraph," you have two choices: (a) put the paragraph in the docstring, or (b) put it in a markdown file *inside* the .egg (where it gets unpacked into the receiver's workspace post-hatch and is no longer part of the sneakernet payload). Never a third file alongside the .py and .egg.

## Publishing to the RAPPstore

### Directory structure

```
rapp_store/my_thing/
  my_thing_agent.py     ← the agent (required)
  my_thing_service.py   ← the service (optional)
  manifest.json         ← store metadata
```

### manifest.json

```json
{
  "schema": "rapp-application/1.0",
  "id": "my_thing",
  "name": "MyThing",
  "version": "1.0.0",
  "publisher": "@you",
  "manifest_name": "@rapp/my_thing",
  "summary": "One-line description.",
  "category": "general",
  "tags": ["your-tag", "rapplication"],
  "agent": "my_thing_agent.py",
  "service": "my_thing_service.py",
  "license": "BSD-style"
}
```

### Catalog entry (rapp_store/index.json)

```json
{
  "id": "my_thing",
  "name": "MyThing",
  "version": "1.0.0",
  "summary": "One-line description.",
  "category": "general",
  "tags": ["your-tag", "rapplication"],
  "manifest_name": "@rapp/my_thing",
  "singleton_filename": "my_thing_agent.py",
  "singleton_url": "https://raw.githubusercontent.com/.../my_thing_agent.py",
  "service_filename": "my_thing_service.py",
  "service_url": "https://raw.githubusercontent.com/.../my_thing_service.py",
  "produced_by": {"method": "agent-first", "source_files_collapsed": 2}
}
```

## The brainstem factory image

The brainstem ships clean — like a factory iPhone:

| Ships by default | Installed on demand |
|-----------------|-------------------|
| ContextMemory, ManageMemory (memory) | LearnNew (agent generation) |
| HackerNews (starter/test) | SwarmFactory (workshop → singleton) |
| WorkIQ (productivity) | VibeBuilder (rapplication generation) |
| | Kanban, Webhook, Dashboard |
| | Any rapplication you build |

`services/` is empty by default. The kernel has the discovery mechanism built in, ready for whatever the user installs.

## Architecture

```
brainstem.py (kernel — never changes)
├── Agent Discovery: agents/*_agent.py
│   └── LLM sees these as tools → perform() → JSON string
├── Service Discovery: services/*_service.py
│   └── HTTP dispatch → /api/<name>/<path> → handle() → (dict, int)
└── Both share: .brainstem_data/{name}.json

Any AI ──→ POST /chat ──→ LLM picks tools ──→ agent.perform()
Any UI ──→ GET /api/x  ──→ service.handle()
Both read/write the same .brainstem_data/ files.
```

## Examples in the RAPPstore

| Rapplication | Category | Agent does | Service adds |
|---|---|---|---|
| Kanban | workspace | Create/move/list tasks via chat | `/api/kanban/*` for drag-and-drop UIs |
| Webhook | integration | Query/summarize ingested events | `POST /api/webhook/ingest` for external systems |
| Dashboard | analytics | Log/query metrics via chat | `GET /api/dashboard/*` for charting UIs |
| VibeBuilder | platform | Generate new rapplications from natural language | (agent-only) |

<!-- RAPP1-HISTORICAL-SECTION-END -->
