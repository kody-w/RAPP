# Rapplication SDK

> Build apps that any AI can drive. Agent-first, single-file, zero-config.

## What is a rapplication?

A rapplication is the installable unit in the RAPP ecosystem. It's one or two files:

1. **Agent file** (required) — `*_agent.py`. The primary interface. Any LLM that speaks tool calls can drive it: brainstem chat, Copilot Studio, Claude, GPT, or anything that comes next.
2. **Service file** (optional) — `*_service.py`. HTTP endpoints for web UIs, webhooks, or machine-to-machine integrations. Reads/writes the same data as the agent.

Install = drop files in. Uninstall = delete them. Nothing else.

## The agent-first rule

> **The agent is the API. The service is a view.**

Every rapplication MUST work fully through `perform()` alone. The service is always optional — if removing it breaks the agent, the design is wrong.

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

That's it. Next `/chat` request discovers it. No restart, no config, no registration.

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
