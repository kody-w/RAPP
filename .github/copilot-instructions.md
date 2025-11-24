# GitHub Copilot Instructions for RAPP

## Project Overview

RAPP (Rapid Agent Prototyping Platform/Pattern) is an Azure Functions-based AI agent framework with OpenAI-compatible API integration. It features modular agent architecture, persistent memory using Azure File Storage, multi-user conversation support, and optional Microsoft 365 integration.

## Core Technologies

- **Runtime**: Python 3.11 (Azure Functions v4)
- **Framework**: Azure Functions (HTTP triggers)
- **AI Integration**: Azure OpenAI / OpenAI / OpenAI-compatible APIs
- **Storage**: Azure File Storage (conversation memory, agent state)
- **Deployment**: Azure (primary), local development supported
- **Optional**: Power Platform, Copilot Studio, Microsoft Teams integration

## Architecture Patterns

### Agent System

- **Base Class**: `agents/basic_agent.py` - All custom agents inherit from `BasicAgent`
- **Auto-loading**: Agents in `agents/` directory are automatically discovered and loaded
- **Agent Structure**: Each agent must implement `__init__`, `get_name()`, `get_description()`, `execute()`, `get_system_message()`
- **Conversation Context**: Agents receive full conversation history and user input in `execute()` method

### Memory System

- **User-specific Memory**: Isolated per user GUID
- **Shared Memory**: Cross-user knowledge base
- **Storage Pattern**: JSON files in Azure File Storage (`utils/azure_file_storage.py`)
- **Default User**: `DEFAULT_USER_GUID = "c0p110t0-aaaa-bbbb-cccc-123456789abc"`

### Function App Structure

- **Entry Point**: `function_app.py` - Main Azure Functions handler
- **HTTP Trigger**: `businessinsightbot_function` endpoint
- **Request Format**: JSON with `user_input`, `conversation_history`, optional `user_guid`
- **Response Format**: JSON with `response`, `agent_used`, `conversation_history`, `tokens_used`

## Development Guidelines

### When Creating New Agents

```python
# Template structure for new agents in agents/ directory
from agents.basic_agent import BasicAgent

class YourAgent(BasicAgent):
    def __init__(self, client):
        super().__init__(client)
        # Agent-specific initialization
    
    def get_name(self):
        return "agent_name"  # Used for routing
    
    def get_description(self):
        return "Clear description of what this agent does"
    
    def get_system_message(self):
        return "System prompt for the AI model"
    
    def execute(self, user_input, conversation_history, user_guid=None):
        # Agent logic here
        return response_text, updated_history
```

### Agent Naming Conventions

- **File naming**: `snake_case_agent.py`
- **Class naming**: `PascalCaseAgent`
- **Agent name (routing)**: `snake_case` (returned by `get_name()`)
- **Location**: Place all agents in `agents/` directory for auto-discovery

### Environment Variables

Required in `local.settings.json` (local) or Azure App Settings (production):
- `OPENAI_API_TYPE`: "azure" or "openai"
- `OPENAI_API_KEY`: API key
- `OPENAI_API_ENDPOINT`: Azure OpenAI endpoint or OpenAI base URL
- `OPENAI_DEPLOYMENT_NAME`: Model deployment name
- `OPENAI_API_VERSION`: API version (Azure only)
- `AZURE_STORAGE_CONNECTION_STRING`: For conversation memory

### Testing Patterns

**Local API Testing:**
```bash
# Start local server
./run.sh  # Mac/Linux
# or
.\run.ps1  # Windows

# Test endpoint
curl -X POST http://localhost:7071/api/businessinsightbot_function \
  -H "Content-Type: application/json" \
  -d '{"user_input": "Hello", "conversation_history": []}'
```

**Agent Testing:**
- Create test files in `demos/` directory
- Use pattern: `test_<agent_name>.py` or `demo_<feature>.py`
- Import agent directly for unit testing

### File Organization

- `agents/` - Production agent implementations (auto-loaded, deployed to Azure)
- `.rapp/` - Development/meta-agents for repo management (NOT deployed)
  - `.rapp/agents/` - Repository steward, agent generator, etc.
  - `.rapp/templates/` - Code generation templates
- `utils/` - Shared utilities (storage, helpers)
- `docs/` - Documentation (GitHub Pages source)
- `demos/` - Example implementations and tests
- `tools/` - Development and maintenance scripts (includes CLI for .rapp agents)
- `power-platform/` - Microsoft 365 integration assets
- `AI-Agent-Templates/` - Pre-built agent library organized by use case

### Code Style

- **Message handling**: Always use `ensure_string_content()` for message normalization
- **Error handling**: Wrap agent operations in try/except, return user-friendly messages
- **Logging**: Use `logging.info()`, `logging.error()` for debugging (Azure Application Insights)
- **JSON parsing**: Use `safe_json_loads()` from utils for robust parsing
- **Type hints**: Preferred for function parameters and returns

### Memory Operations

```python
from utils.azure_file_storage import AzureFileStorageManager

# Initialize storage
storage = AzureFileStorageManager()

# User-specific memory (isolated)
storage.save_memory(user_guid, "memory_key", {"data": "value"})
memory = storage.load_memory(user_guid, "memory_key")

# Shared memory (cross-user)
storage.save_shared_memory("shared_key", {"data": "value"})
shared = storage.load_shared_memory("shared_key")
```

### Documentation Updates

- Update `docs/` when adding major features
- Update `REPOSITORY_STRUCTURE.md` when adding new directories
- Update `README.md` for setup/deployment changes
- Create guides in `docs/guides/` for complex features

### Deployment

- **Azure**: Use ARM template via "Deploy to Azure" button in README
- **Local Setup**: Run `setup.sh` (Mac/Linux) or `setup.ps1` (Windows)
- **Configuration**: Template auto-configures Azure resources and local settings

## Common Operations

### Adding a New Agent

**Manual approach:**
1. Create file in `agents/your_agent.py`
2. Inherit from `BasicAgent`
3. Implement required methods
4. No registration needed - auto-loaded on startup
5. Test locally, then deploy

**Using Agent Generator (recommended):**
```bash
python tools/run_rapp_agent.py agent_generator \
  --name "my_agent" \
  --description "summarizes customer emails"
```

This generates a fully-structured agent file with all boilerplate code.

### Modifying Function App Behavior

- Edit `function_app.py` for routing, orchestration, or core logic
- Changes apply to all agents system-wide
- Consider backward compatibility with existing agents

### Adding New Dependencies

1. Add to `requirements.txt`
2. Run `pip install -r requirements.txt` locally
3. Redeploy to Azure (dependencies installed automatically)

### Working with Conversation History

- Format: List of dicts with `role` and `content` keys
- Roles: `"system"`, `"user"`, `"assistant"`
- Always validate with `ensure_string_content()` before processing
- Return updated history from agent `execute()` method

## Security Considerations

- **API Keys**: Never commit to repository, use environment variables
- **User Isolation**: Always use `user_guid` for user-specific operations
- **Input Validation**: Sanitize user input before processing
- **PII Handling**: Be cautious with sensitive data in memory/logs

## Integration Points

### Power Platform (Optional)

- Power Automate can call Azure Function endpoint
- Copilot Studio uses declarative agents with manifest
- Teams integration via Power Platform connectors
- See `power-platform/` and `docs/POWER_PLATFORM_INTEGRATION.md`

### Azure Services

- **Azure Functions**: Core hosting platform
- **Azure File Storage**: Conversation memory and state
- **Azure OpenAI**: Preferred AI backend
- **Application Insights**: Logging and monitoring

## Development Tools (.rapp Directory)

The `.rapp/` directory contains meta-agents for development tasks:

### Repository Steward
Monitors codebase health, runs audits, checks dependencies:
```bash
python tools/run_rapp_agent.py repository_steward --action full
python tools/run_rapp_agent.py repository_steward --action dependencies
python tools/run_rapp_agent.py repository_steward --action security
```

### Agent Generator
Creates new agents from templates with proper structure:
```bash
python tools/run_rapp_agent.py agent_generator \
  --name "agent_name" \
  --description "what it does"
```

**Note:** `.rapp/` agents are NOT deployed to Azure (excluded in `.funcignore`)

## Troubleshooting

- Check logs in Azure Portal → Function App → Log Stream
- Verify environment variables in Configuration settings
- Test locally first with `./run.sh` before deploying
- Run repository health check: `python tools/run_rapp_agent.py repository_steward`
- Review `docs/TROUBLESHOOTING.md` for common issues

## Code Generation Tips

- Follow existing agent patterns in `agents/` directory
- Reuse utility functions from `utils/`
- Maintain consistent error handling and logging
- Test with various conversation history lengths
- Consider token limits when building prompts
- Use descriptive variable names and comments for complex logic

## Project-Specific Patterns

- **Agent Routing**: Based on `get_name()` return value, case-insensitive matching
- **Default Agent**: `BasicAgent` handles requests when no specific agent matches
- **Conversation State**: Maintained client-side, passed in each request
- **User Context**: GUID-based isolation, shared memories available across users
- **Streaming**: Not currently supported, full responses returned
- **Multi-agent**: Orchestrator pattern supported (see `enterprise_orchestrator_agent.py`)

## Key Files to Reference

- `function_app.py` - Core orchestration logic
- `agents/basic_agent.py` - Base agent class and patterns
- `utils/azure_file_storage.py` - Memory persistence patterns
- `CLAUDE.md` - Additional Claude Code-specific guidance
- `docs/AGENT_DEVELOPMENT.md` - Comprehensive agent development guide
- `docs/ARCHITECTURE.md` - System architecture details

---

When suggesting code changes, prioritize:
1. Compatibility with existing agent architecture
2. Proper error handling and user feedback
3. Efficient token usage in AI interactions
4. Clear documentation and comments
5. Testability and local development support
