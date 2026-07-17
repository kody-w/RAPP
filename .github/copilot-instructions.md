# Copilot Instructions — RAPP Brainstem

> **Current RAPP/1 authority (rev-5).** For canonicalization, identity, frames,
> wire, eggs, registry, trust, and protocol evolution, follow
> [`RAPP1_AUTHORITY.json`](../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../RAPP1_STATUS.md). Runtime facts below do not redefine
> protocol. The `KERNEL_PIN.json` bytes from
> `kody-w/rapp-installer@brainstem-v0.6.9` are read-only.

## Current instructions

- Treat this checkout as experimental source, not a shipped three-tier
  platform. Azure, Copilot Studio, browser UI, installer, catalog, Shortcut,
  planting, and legacy egg/hatch paths are retired or pre-acceptance.
- Never edit the immutable grail bytes, prepared cave installer subtree,
  archives, generated external mirrors, or owner-authorized identity/trust
  records.
- The target-owned loopback façade is `127.0.0.1:7073`. Its §8 request is
  required string `user_input` plus optional strings `session_id` and
  `idempotency_key`; success is exactly `response`, `agent_logs` (array), and
  `session_id`; refusal is HTTP 422 with nested `error.code` and `error.step`.
  Its launcher imports no grail module and defaults to `inference-refused`
  until a reviewed adapter is explicitly injected. Voice and Twin derive
  locally from `response` and add no wire fields.
- `rapp_brainstem/start.sh`, `start.ps1`, and `utils/boot.py` are unconditional
  410/exit-78 tombstones. Direct immutable `brainstem.py` execution is allowed
  only inside the isolated canonical evidence fixtures.
- Run `python3 tests/run_rapp1_conformance.py` for the authoritative
  structural/pre-acceptance gate. A pass does not close the owner-action
  blockers in `RAPP1_STATUS.md`.

## Historical implementation guide (superseded)

<!-- RAPP1-HISTORICAL-SECTION-START -->

## Architecture

RAPP Brainstem is a progressive AI agent platform using a biological metaphor (see `CONSTITUTION.md` for architectural principles):

1. **Brainstem** (`rapp_brainstem/`) — The core. A local-first Flask server (Python 3.11) using GitHub Copilot's API for LLM inference. No API keys needed — just `gh auth login`. This is where all development happens.
2. **Spinal Cord** (`azuredeploy.json`, `deploy.sh`) — Azure deployment. ARM template creates Function App, Azure OpenAI, Storage, App Insights. All Entra ID auth.
3. **Nervous System** (`MSFTAIBASMultiAgentCopilot_*.zip`) — Power Platform solution for Copilot Studio. Connects the Azure Function to Teams and M365 Copilot.

Everything else in the repo root (install scripts, index.html, docs/) is
onboarding infrastructure. `community_rapp/` contains non-runtime host
onboarding manifests, not RAPP agents or capabilities.

### Brainstem internals

`brainstem.py` is the single-file server containing auth, agent orchestration, the tool-calling loop, and all HTTP endpoints.

**Tool-calling loop** (`/chat`): Builds messages from soul + memory + conversation history, then runs up to **3 rounds** of LLM calls. Each round checks for `tool_calls` in the response, executes matching agents via `run_tool_calls()`, appends tool results, and loops. Falls back to `gpt-4o` if the configured model fails.

**Agent auto-discovery**: `load_agents()` globs `*_agent.py` in `AGENTS_PATH`, dynamically imports each file, finds classes with a `perform` method (excluding `BasicAgent` itself), and instantiates them. Each agent's `to_tool()` generates its OpenAI function-calling schema.

**Import shims**: `_register_shims()` injects fake `sys.modules` so agents written for the cloud (CommunityRAPP) work locally:
- `utils.azure_file_storage` → `local_storage.AzureFileStorageManager`
- `utils.dynamics_storage` → same local shim (aliased as `DynamicsStorageManager`)
- `utils.storage_factory` → returns a `LocalStorageManager` instance
- `agents.basic_agent` → the local `basic_agent.py`

**Auto-pip-install**: When loading an agent hits `ModuleNotFoundError`, `_extract_package_name()` maps import names to pip packages via `_PIP_MAP` (e.g., `bs4` → `beautifulsoup4`, `PIL` → `Pillow`), auto-installs, and retries once.

**Memory agents**: `ManageMemory` and `ContextMemory` get special treatment — the LLM-invented `user_guid` arg is stripped before calling `perform()`. The `/chat` handler auto-injects `<memory>` context from `ContextMemory` into the system prompt if that agent is loaded.

**Auth chain** (in priority order):
1. `GITHUB_TOKEN` env var
2. `.copilot_token` file (JSON with `access_token` + `refresh_token` + `saved_at`)
3. `gh auth token` CLI (skips `gho_` tokens — they lack Copilot access)
4. Device code OAuth flow via `/login` endpoint

Copilot API tokens are exchanged from the GitHub token, cached in memory (with 60s expiry buffer) and on disk. A `refresh_token` flow allows automatic re-auth without user interaction.

**Model compatibility**: `_NO_TOOL_CHOICE_MODELS` auto-detects models with `o1` in their ID — these don't support the `tool_choice` parameter. Claude models work but return multi-choice responses (text and tool_calls in separate choices); `call_copilot()` merges these into a single choice automatically.

## Running & Testing

```bash
# Start the brainstem server (creates venv at ~/.brainstem/venv if needed)
cd rapp_brainstem && ./start.sh    # port 7071

# Run tests
cd rapp_brainstem && python3 -m pytest test_local_agents.py -v

# Run a single test
python3 -m pytest test_local_agents.py::TestLocalStorage::test_write_and_read -v

# Run a single test class
python3 -m pytest test_local_agents.py::TestShimRegistration -v

# Health check
curl -s localhost:7071/health | python3 -m json.tool
```

No linter or type-checker is configured.

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Serves `index.html` (chat UI) |
| `/chat` | POST | RAPP/1 §8: required `user_input`; optional `session_id`, `idempotency_key` |
| `/health` | GET | Status, model, loaded agents, token state |
| `/login` | POST | Start GitHub device code OAuth flow |
| `/login/poll` | POST | Poll for completed device code auth |
| `/login/status` | GET | Check current auth state |
| `/models` | GET | List available models |
| `/models/set` | POST | Change the active model |
| `/agents` | GET | List agent files with loaded agent names |
| `/agents/import` | POST | Upload an agent `.py` file |
| `/agents/export/<filename>` | GET | Download an agent `.py` file |
| `/agents/<filename>` | DELETE | Remove an agent `.py` file |
| `/voice` | GET | Voice mode status |
| `/voice/toggle` | POST | Toggle voice mode |
| `/voice/config` | GET | Read voice config from encrypted `voice.zip` |
| `/voice/config` | POST | Save voice config to encrypted `voice.zip` |
| `/voice/export` | POST | Export `voice.zip` for download |
| `/voice/import` | POST | Import `voice.zip` from upload |
| `/version` | GET | Server version (reads `VERSION` file) |
| `/debug/auth` | GET | Auth diagnostics |

Only `/chat` is the RAPP synchronous wire. The other routes are
application-local UI/administration surfaces and do not add protocol
capabilities. See RAPP/1 §8 for the exact 200 and 422 response bodies.

## Writing Agents

Agents extend `BasicAgent` (`agents/basic_agent.py`) with `name`, `metadata` (OpenAI function schema), and `perform()`:

```python
from basic_agent import BasicAgent

class MyAgent(BasicAgent):
    def __init__(self):
        self.name = "MyAgent"
        self.metadata = {
            "name": self.name,
            "description": "Description the LLM reads to decide when to call this.",
            "parameters": {
                "type": "object",
                "properties": {"param1": {"type": "string", "description": "..."}},
                "required": ["param1"]
            }
        }
        super().__init__()

    def perform(self, param1="", **kwargs):
        return f"Result: {param1}"
```

- File must be named `*_agent.py` in the agents directory (subdirectories like `experimental/` are not auto-discovered)
- `perform()` must accept `**kwargs` — the LLM may pass unexpected args
- `to_tool()` on `BasicAgent` converts `metadata` to OpenAI function-calling format
- Agents importing `AzureFileStorageManager` get the local shim automatically
- For storage, use `from utils.azure_file_storage import AzureFileStorageManager` — the shim handles local vs cloud
- Return a string from `perform()` — this becomes the tool result the LLM sees

## Key Conventions

- **Python 3.11** target runtime; venv at `~/.brainstem/venv`
- **No API keys** for local dev — GitHub Copilot token exchange handles auth
- **Config via `.env`** — `GITHUB_TOKEN`, `GITHUB_MODEL`, `SOUL_PATH`, `AGENTS_PATH`, `PORT`, `VOICE_ZIP_PASSWORD` (see `.env.example`)
- **Local-first storage**: `local_storage.py` stores to `.brainstem_data/` on disk, mirroring the CommunityRAPP Azure File Storage layout (`shared_memories/memory.json` for shared, `memory/{guid}/user_memory.json` for per-user)
- **Soul file** (`soul.md`): System prompt loaded as the first message in every conversation. Users customize by editing it or pointing `SOUL_PATH` to their own
- **Host-onboarding runbook**: the non-runtime `skill.md` uses YAML
  frontmatter, autonomous execution steps, ⏸️ pause points for user input, and
  state saved to `~/.config/brainstem/state.json`. It is not a RAPP agent or
  protocol capability.
- **Single-file server**: All server logic lives in `brainstem.py` — auth, routing, LLM calls, agent orchestration. Keep it that way.

<!-- RAPP1-HISTORICAL-SECTION-END -->
