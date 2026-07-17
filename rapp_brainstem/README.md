# Historical RAPP Brainstem Quickstart

> **Current RAPP/1 authority (rev-5).** For canonicalization, identity, frames,
> wire, eggs, registry, trust, and protocol evolution, follow
> [`RAPP1_AUTHORITY.json`](../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../RAPP1_STATUS.md). This quickstart describes the
> immutable `kody-w/rapp-installer@brainstem-v0.6.9` grail runtime; adapters
> must converge outside its pinned `brainstem.py`, `agents/basic_agent.py`, and
> `VERSION` bytes.

> **Whole-document disposition:** the install, quickstart, browser, API,
> catalog, and runtime guidance below is preserved grail-era history. This
> target does not ship or support it. The immutable tag is a byte pin, not an
> installation promise; current target-owned protocol work is the separate
> loopback pre-acceptance façade at `127.0.0.1:7073`. Target-owned `start.sh`,
> `start.ps1`, and `utils/boot.py` are HTTP-410 tombstones. Direct
> `brainstem.py` execution is retained only inside isolated immutable-byte
> tests, never as a public launch instruction.

<!-- RAPP1-HISTORICAL-SECTION-START -->

A local-first AI agent server. One dependency: a GitHub account with Copilot access.

The brainstem runs on your machine, uses GitHub Copilot as the LLM, auto-discovers agents from Python files, and exposes a chat API + web UI on `localhost:7071`. No API keys, no cloud setup, no config.

> **Looking for the wider context?** This README is the Tier 1 component quickstart. The repo-wide entry point is the [**Kernel hub**](https://kody-w.github.io/RAPP/pages/kernel.html) — canonical reading order for the whole platform (trilogy, law, specs, vault Reading Paths).

---

## Install

### Pinned grail checkout

**macOS / Linux:**
```bash
git clone --branch brainstem-v0.6.9 --depth 1 \
  https://github.com/kody-w/rapp-installer.git ~/.brainstem/src
cd ~/.brainstem/src/rapp_brainstem
python3 -m pip install -r requirements.txt
```

**Windows (PowerShell):**
```powershell
git clone --branch brainstem-v0.6.9 --depth 1 https://github.com/kody-w/rapp-installer.git "$HOME\.brainstem\src"
Set-Location "$HOME\.brainstem\src\rapp_brainstem"
py -m pip install -r requirements.txt
```

If the checkout already exists, fetch and detach at the same tag rather than
pulling a moving branch. Target-owned installers may add wrappers and adapters,
but they must preserve the three hashes in `KERNEL_PIN.json`.

---

## Quickstart

```bash
# 1. Authenticate with GitHub
gh auth login

# 2. Start the brainstem
cd ~/.brainstem/src/rapp_brainstem && python3 brainstem.py

# 3. Open the UI
open http://localhost:7071
```

If `gh` is not installed, the web UI at `localhost:7071` walks you through GitHub device-code login automatically.

---

## API Reference

### `POST /chat`

The main conversation endpoint. Sends user input through the LLM with tool-calling support. Up to 3 rounds of agent calls per request.

The current target is the exact RAPP/1 §8 contract. See `RAPP1_STATUS.md` for
the repository's implementation gap; do not treat legacy host extensions as
wire fields.

**Request:**
```json
{
  "user_input": "What's on Hacker News today?",
  "session_id": "optional-session-id",
  "idempotency_key": "optional-deduplication-key"
}
```

**Response:**
```json
{
  "response": "Here are today's top stories...",
  "agent_logs": ["[HackerNewsAgent] Fetched 10 stories"],
  "session_id": "abc-123"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `user_input` | string | **Required.** The user's message. |
| `session_id` | string | Optional. Returned in every response for continuity. |
| `idempotency_key` | string | Optional. Repeats return the original response without a duplicate turn. |

Success is HTTP 200 with exactly `response`, `agent_logs`, and `session_id`.
Malformed, refused, and unknown-session requests are HTTP 422 with exactly
`{"error":{"code":"<registered-code>","step":null}}` (or a §7.5 step string).

### `GET /health`

Returns server status, loaded agents, model, and auth state.

```json
{
  "status": "ok",
  "version": "0.1.0",
  "model": "gpt-4o",
  "soul": "./soul.md",
  "agents": ["HelloAgent", "HackerNewsAgent"],
  "copilot": "✓",
  "endpoint": "https://api.individual.githubcopilot.com"
}
```

Returns `"status": "unauthenticated"` (still 200) if the Copilot token is missing — the web UI detects this and shows the login overlay.

### `GET /version`

```json
{ "version": "0.1.0" }
```

### `GET /models`

Lists available models and the current selection.

```json
{
  "models": [
    {"id": "gpt-4.1", "name": "GPT-4.1"},
    {"id": "gpt-4o", "name": "GPT-4o"},
    {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
    {"id": "claude-sonnet-4", "name": "Claude Sonnet 4"}
  ],
  "current": "gpt-4o"
}
```

### `POST /models/set`

Switch the active model at runtime.

```json
{ "model": "gpt-4o-mini" }
```

### `POST /login`

Starts GitHub device-code OAuth. Returns a `user_code` and `verification_uri` for the user to enter at github.com/login/device.

### `POST /login/poll`

Polls for completed device-code authorization. Returns `{"status": "pending"}` until the user completes login, then `{"status": "ok"}`.

### `GET /login/status`

Returns current authentication status.

### `GET /`

Serves the built-in chat web UI.

---

## Configuration

All config is via environment variables in `.env` (auto-created from `.env.example` on first run).

| Variable | Default | Description |
|----------|---------|-------------|
| `GITHUB_TOKEN` | *auto-detected* | GitHub PAT or Copilot token. Auto-detected from `gh auth token` if blank. |
| `GITHUB_MODEL` | `gpt-4o` | LLM model. Changeable at runtime via `/models/set`. |
| `SOUL_PATH` | `./soul.md` | Path to the system prompt file. |
| `AGENTS_PATH` | `./agents` | Directory to discover `*_agent.py` files from. |
| `PORT` | `7071` | Server port. |

---

## Authentication

The brainstem uses GitHub Copilot's API — no OpenAI keys needed. It resolves a GitHub token through this chain (first match wins):

1. **`GITHUB_TOKEN` env var** — set in `.env` or your shell
2. **`.copilot_token` file** — saved automatically after device-code login
3. **`gh auth token` CLI** — if GitHub CLI is installed and authenticated

The GitHub token is exchanged for a short-lived Copilot API token (auto-refreshed, cached to disk across restarts). If the token expires and a refresh token is available, it auto-refreshes without user interaction.

**Device-code login (no `gh` needed):**

Open `localhost:7071` in a browser. If not authenticated, the UI shows a login overlay. Click "Sign in" → enter the code at `github.com/login/device` → done. The token persists across restarts.

---

## Writing Agents

Agents are Python files named `*_agent.py` in the `AGENTS_PATH` directory. Each agent extends `BasicAgent`, declares metadata (OpenAI function-calling schema), and implements `perform()`.

### Minimal example

```python
# agents/greeting_agent.py
from basic_agent import BasicAgent

class GreetingAgent(BasicAgent):
    def __init__(self):
        self.name = "GreetingAgent"
        self.metadata = {
            "name": self.name,
            "description": "Greets a user by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The person's name"}
                },
                "required": ["name"]
            }
        }
        super().__init__()

    def perform(self, name="", **kwargs):
        return f"Hello, {name}! Welcome to the brainstem."
```

### How discovery works

1. On every `/chat` request, the brainstem scans `AGENTS_PATH` for `*_agent.py` files (top-level only — subdirectories are excluded).
2. Each file is loaded and inspected for classes with a `perform()` method.
3. Matching classes are instantiated and registered as OpenAI function-calling tools.
4. The LLM decides when to call them based on the `description` in `metadata`.

**Stateless by design:** Agents load fresh every request. Edit a file, hit the endpoint, see the change. No restart needed.

### Agent conventions

- File must be named `*_agent.py` (e.g., `crm_agent.py`, `search_agent.py`)
- Class must have `self.name`, `self.metadata`, and `perform()` 
- `perform()` must accept `**kwargs` to handle extra arguments gracefully
- Return a string — that's what the LLM sees as the tool result
- The `description` field is what the LLM reads to decide when to call your agent — be specific

### Auto-installing dependencies

If your agent imports a package that isn't installed, the brainstem auto-installs it via pip and retries. Common mappings are built in (`bs4` → `beautifulsoup4`, `PIL` → `Pillow`, etc.).

### Using local storage

Agents that import `utils.azure_file_storage` get a local shim automatically. This means agents written for the Azure deployment work locally without modification.

```python
from utils.azure_file_storage import AzureFileStorageManager

class MyAgent(BasicAgent):
    def __init__(self):
        self.storage = AzureFileStorageManager(share_name="mydata")
        # ...

    def perform(self, **kwargs):
        data = self.storage.read_json()    # reads from .brainstem_data/
        self.storage.write_json({"key": "value"})
        return "Done"
```

Locally, data is stored in `.brainstem_data/` as JSON files. In Azure, the same imports use Azure File Storage.

---

## The Soul File

The soul file (`soul.md`) is loaded as the system prompt for every conversation. It defines your AI's personality, knowledge, and behavior.

```markdown
# soul.md
You are Aria, a sharp-witted assistant for Contoso's sales team.
Always respond in 2-3 sentences. Use data from the CRM agent when available.
Never share customer PII in responses.
```

Point `SOUL_PATH` in `.env` to your own file. The brainstem code never changes — only the soul does.

---

## Project Structure

```
rapp_brainstem/
├── brainstem.py          # The server — auth, agents, tool-calling loop, all endpoints
├── basic_agent.py        # Base class all agents extend
├── local_storage.py      # Local shim for Azure File Storage
├── soul.md               # Default system prompt (replace with your own)
├── VERSION               # Semver string, read at startup
├── index.html            # Built-in chat web UI
├── start.sh              # macOS/Linux startup script
├── start.ps1             # Windows startup script
├── requirements.txt      # Python dependencies (flask, requests, python-dotenv)
├── .env.example          # Config template
├── .env                  # Your config (auto-created, gitignored)
├── .brainstem_data/      # Local storage data (gitignored)
├── .copilot_token        # Saved GitHub token (gitignored)
├── .copilot_session      # Cached Copilot API token (gitignored)
├── agents/               # Agent auto-discovery directory
│   ├── hello_agent.py    # Example agent
│   └── experimental/     # Subdirectory — NOT auto-loaded
└── test_local_agents.py  # Test suite
```

---

## Running Tests

```bash
cd rapp_brainstem
python3 -m pytest test_local_agents.py -v
```

Run a single test:
```bash
python3 -m pytest test_local_agents.py::TestLocalStorage::test_write_and_read -v
```

---

## Immutable version pin

`VERSION` is one of the three grail bytes pinned to
`kody-w/rapp-installer@brainstem-v0.6.9`. Do not edit it, compare it to a
moving branch, or auto-upgrade it. A future grail change requires an explicit
authority event; ordinary RAPP/1 convergence belongs in target-owned adapters,
validators, migrations, and retirement policy.

- **Inspect the runtime value:** `curl -s localhost:7071/version`
- **Verify authority and hashes:** follow `RAPP1_AUTHORITY.json`,
  `KERNEL_PIN.json`, and `RAPP1_STATUS.md`

---

## Architecture

```
                ┌─────────────────────────────────────────────┐
                │              brainstem.py                    │
                │                                             │
  POST /chat ──►│  1. Load soul.md (system prompt)            │
                │  2. Discover *_agent.py files                │
                │  3. Register agents as OpenAI tools          │
                │  4. Call Copilot API with messages + tools   │
                │  5. If tool_calls → run agents → loop (×3)  │
                │  6. Return final response                    │
                │                                             │
                │  Auth: GitHub token → Copilot API token      │
                │  Storage: .brainstem_data/ (local JSON)      │
                └─────────────────────────────────────────────┘
```

**Key design decisions:**
- **Stateless agent loading** — agents load fresh every request, no cache. Edit and test without restarting.
- **Local-only discovery** — only `*_agent.py` files in the top-level `agents/` directory. Subdirectories are excluded.
- **Import shims** — `utils.azure_file_storage` and `utils.dynamics_storage` are shimmed to `local_storage.py` so Azure agents work locally unchanged.
- **No API keys** — uses GitHub Copilot's token exchange. Your Copilot subscription is the AI engine.

---

## Troubleshooting

**"Not authenticated" / login overlay shows:**
- Run `gh auth login` and restart, OR
- Use the device-code login in the web UI at `localhost:7071`

**Agent not loading:**
- File must be named `*_agent.py` and be in the top-level `agents/` directory (not a subdirectory)
- Class must have a `perform()` method
- Check terminal output for `[brainstem] Failed to load` errors

**"Failed to get Copilot API token":**
- Verify your GitHub account has Copilot access
- Try `gh auth token` — if it returns nothing, re-run `gh auth login`
- Delete `.copilot_token` and `.copilot_session` to force re-auth

**Port already in use:**
- Change `PORT` in `.env`, or kill the existing process on 7071

**Health check:**
```bash
curl -s localhost:7071/health | python3 -m json.tool
```

<!-- RAPP1-HISTORICAL-SECTION-END -->
