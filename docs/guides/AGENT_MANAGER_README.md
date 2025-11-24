# Agent Manager - Complete Guide

## Overview

The Agent Manager is a comprehensive web-based control panel for managing, configuring, and orchestrating AI agent combinations in the Copilot Agent 365 system. It provides a visual interface for:

- **Agent Discovery**: View all available agents with descriptions and capabilities
- **Dynamic Configuration**: Enable/disable agents per user with visual controls
- **Preset Management**: Save and load agent combination templates
- **Metadata Preview**: See exactly what OpenAI function metadata will be generated
- **Settings Management**: Configure agent-specific settings and business parameters
- **User Context**: Manage separate configurations for different users (GUIDs)

## Features

### 1. Visual Agent Selection

- **Grid View**: All agents displayed as interactive cards
- **Categories**: Agents organized by category (Memory, Commerce, Utilities, Analysis)
- **Descriptions**: Full agent descriptions and capabilities displayed
- **Multi-Select**: Click to select/deselect individual agents
- **Bulk Actions**: Select all / Deselect all buttons for quick changes

### 2. Agent Combination Presets

Pre-configured agent combinations for common use cases:

- **🌟 Full Suite**: All agents enabled for maximum functionality
- **🛒 Customer Service**: Memory + Order Verification for customer interactions
- **🧠 Memory Only**: Just memory agents for conversation context
- **📊 Analytics Suite**: Contract analysis + Prompt playground
- **🎬 Demo Mode**: Scripted demo agent for presentations

### 3. Dynamic Metadata Generation

- **Real-Time Preview**: See the exact OpenAI function metadata for selected agents
- **JSON Format**: Properly formatted metadata ready for API calls
- **Copy to Clipboard**: Easy export for testing or documentation
- **Agent Count**: Track how many agents are active

### 4. Per-User Configuration

- **GUID-Based**: Each user (identified by GUID) can have unique agent configurations
- **Azure Storage**: Configurations persisted to Azure File Storage
- **Default GUID**: Default user GUID pre-populated for quick testing
- **Easy Switching**: Change user context with a single input field

### 5. Settings Management

Configure agent-specific settings:

- **Assistant Name**: Customize the assistant's display name
- **Business Type**: Set business context (fast_food, coffee_shop, retail, pizza, grocery)
- **Upselling**: Enable/disable upselling features
- **Custom Instructions**: Add custom behavior instructions

### 6. Statistics Dashboard

Real-time metrics:

- **Total Agents**: Count of all available agents
- **Selected Agents**: How many agents are currently enabled
- **Presets Available**: Number of saved presets
- **Category Breakdown**: Distribution of agents by category

## Architecture

### Backend API Endpoints

Located in `function_app.py`:

#### `GET /api/agent_manager?action=list_agents`
Returns all available agents with metadata, descriptions, and categories.

**Response:**
```json
{
  "agents": [
    {
      "name": "ContextMemory",
      "metadata": {...},
      "description": "Recalls and provides context...",
      "parameters": {...},
      "category": "Memory"
    }
  ]
}
```

#### `GET /api/agent_manager?action=get_config&user_guid={guid}`
Retrieves configuration for a specific user.

**Response:**
```json
{
  "user_guid": "c0p110t0-aaaa-bbbb-cccc-123456789abc",
  "enabled_agents": ["context_memory_agent.py", "order_verification_agent.py"],
  "settings": {
    "business_type": "fast_food",
    "enable_upsell": true
  }
}
```

#### `POST /api/agent_manager?action=save_config`
Saves agent configuration for a user.

**Request Body:**
```json
{
  "user_guid": "c0p110t0-aaaa-bbbb-cccc-123456789abc",
  "enabled_agents": ["context_memory_agent.py", "manage_memory_agent.py"],
  "settings": {
    "assistant_name": "My Assistant",
    "business_type": "coffee_shop",
    "enable_upsell": false
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Configuration saved successfully"
}
```

#### `GET /api/agent_manager?action=list_presets`
Returns all available agent combination presets.

**Response:**
```json
{
  "presets": [
    {
      "name": "Customer Service",
      "description": "Memory and order verification...",
      "agents": ["context_memory_agent.py", "order_verification_agent.py"],
      "settings": {"enable_upsell": true},
      "icon": "🛒"
    }
  ]
}
```

#### `POST /api/agent_manager?action=save_preset`
Creates a new preset.

**Request Body:**
```json
{
  "name": "My Custom Preset",
  "description": "Custom agent combination",
  "agents": ["context_memory_agent.py"],
  "settings": {}
}
```

#### `POST /api/agent_manager?action=get_metadata_preview`
Generates OpenAI function metadata for selected agents.

**Request Body:**
```json
{
  "selected_agents": ["ContextMemory", "ManageMemory", "OrderVerification"]
}
```

**Response:**
```json
{
  "metadata": [
    {
      "name": "ContextMemory",
      "description": "Recalls and provides context...",
      "parameters": {...}
    }
  ],
  "count": 3
}
```

### Storage Structure

Configurations are stored in Azure File Storage:

```
agent_config/
├── {user_guid}/
│   ├── enabled_agents.json    # List of enabled agent filenames
│   └── settings.json           # User-specific settings
└── presets.json                # Global preset definitions
```

**enabled_agents.json:**
```json
[
  "context_memory_agent.py",
  "manage_memory_agent.py",
  "order_verification_agent.py"
]
```

**settings.json:**
```json
{
  "assistant_name": "Copilot Agent 365",
  "business_type": "fast_food",
  "enable_upsell": true,
  "custom_instructions": "Always be polite and helpful"
}
```

## Usage Guide

### Local Development

1. **Start the Azure Function locally:**
   ```bash
   ./run.sh  # Mac/Linux
   ./run.ps1 # Windows
   ```

2. **Open the Agent Manager:**
   ```
   http://localhost:7071/agent_manager.html
   ```

3. **Select agents:**
   - Click agent cards to toggle selection
   - Or use "Select All" / "Deselect All" buttons

4. **Save configuration:**
   - Click "💾 Save Configuration"
   - Configuration is saved to Azure Storage for the current user GUID

5. **Switch users:**
   - Enter a different GUID in the sidebar
   - Configuration automatically loads for that user

### Production Deployment

1. **Deploy to Azure:**
   ```bash
   ./deploy.sh
   ```

2. **Access via public URL:**
   ```
   https://<your-function-app>.azurewebsites.net/agent_manager.html
   ```

3. **Secure with authentication:**
   - Function-level authentication enabled by default
   - Add custom authentication for production use

### Using Presets

1. **Apply a preset:**
   - Click any preset in the sidebar
   - Agents and settings automatically update

2. **Create custom preset:**
   - Configure desired agents and settings
   - Use the API or modify `presets.json` directly

3. **Share presets:**
   - Presets are global (not user-specific)
   - Stored in `agent_config/presets.json`

### Metadata Preview

1. **View metadata:**
   - Click the "Metadata Preview" tab
   - Preview updates automatically when agents change

2. **Copy metadata:**
   - Click "📋 Copy to Clipboard"
   - Paste into documentation or testing tools

3. **Understand the structure:**
   - Metadata matches OpenAI function calling format
   - Shows exactly what will be sent to GPT-4

## Integration with Existing System

### Agent Loading

The existing `load_agents_from_folder()` function in `function_app.py` automatically respects user configurations:

```python
# Load agents with user filtering
agents = load_agents_from_folder(user_guid="c0p110t0-aaaa-bbbb-cccc-123456789abc")

# If enabled_agents.json exists for this user, only those agents load
# If no config exists, all agents load
```

### Assistant Initialization

The `Assistant` class uses the filtered agent list:

```python
assistant = Assistant(agents)
assistant.user_guid = user_guid
assistant._initialize_context_memory(user_guid)
```

### OpenAI Function Calling

Metadata is automatically generated from enabled agents:

```python
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    functions=assistant.get_agent_metadata(),  # Only enabled agents
    function_call="auto"
)
```

## Advanced Use Cases

### Multi-Tenant Deployment

Create separate configurations for different customers:

```javascript
// Customer A - Full suite
saveConfiguration({
  user_guid: "customer-a-guid",
  enabled_agents: null  // All agents
});

// Customer B - Limited functionality
saveConfiguration({
  user_guid: "customer-b-guid",
  enabled_agents: ["context_memory_agent.py", "manage_memory_agent.py"]
});
```

### A/B Testing

Test different agent combinations:

```javascript
// Control group - Standard agents
saveConfiguration({
  user_guid: "control-group",
  enabled_agents: ["context_memory_agent.py", "order_verification_agent.py"]
});

// Experimental group - New agents
saveConfiguration({
  user_guid: "experiment-group",
  enabled_agents: ["context_memory_agent.py", "order_verification_agent.py", "contract_analysis_agent.py"]
});
```

### Department-Specific Configs

Different departments use different agent sets:

```javascript
// Sales Team
saveConfiguration({
  user_guid: "sales-team",
  enabled_agents: ["order_verification_agent.py", "context_memory_agent.py"],
  settings: { business_type: "retail", enable_upsell: true }
});

// Support Team
saveConfiguration({
  user_guid: "support-team",
  enabled_agents: ["context_memory_agent.py", "manage_memory_agent.py"],
  settings: { enable_upsell: false }
});

// Analytics Team
saveConfiguration({
  user_guid: "analytics-team",
  enabled_agents: ["contract_analysis_agent.py", "prompt_playground_agent.py"]
});
```

## API Examples

### Python

```python
import requests
import json

BASE_URL = "http://localhost:7071/api"

# List all agents
response = requests.get(f"{BASE_URL}/agent_manager?action=list_agents")
agents = response.json()['agents']
print(f"Found {len(agents)} agents")

# Get user configuration
response = requests.get(
    f"{BASE_URL}/agent_manager",
    params={
        "action": "get_config",
        "user_guid": "my-user-guid"
    }
)
config = response.json()

# Save configuration
response = requests.post(
    f"{BASE_URL}/agent_manager?action=save_config",
    json={
        "user_guid": "my-user-guid",
        "enabled_agents": ["context_memory_agent.py", "manage_memory_agent.py"],
        "settings": {
            "business_type": "coffee_shop",
            "enable_upsell": False
        }
    }
)
print(response.json())

# Get metadata preview
response = requests.post(
    f"{BASE_URL}/agent_manager?action=get_metadata_preview",
    json={
        "selected_agents": ["ContextMemory", "ManageMemory"]
    }
)
metadata = response.json()['metadata']
print(json.dumps(metadata, indent=2))
```

### JavaScript/Fetch

```javascript
const BASE_URL = 'http://localhost:7071/api';

// List all agents
async function listAgents() {
  const response = await fetch(`${BASE_URL}/agent_manager?action=list_agents`);
  const data = await response.json();
  return data.agents;
}

// Get user configuration
async function getConfig(userGuid) {
  const response = await fetch(
    `${BASE_URL}/agent_manager?action=get_config&user_guid=${userGuid}`
  );
  return await response.json();
}

// Save configuration
async function saveConfig(userGuid, enabledAgents, settings) {
  const response = await fetch(`${BASE_URL}/agent_manager?action=save_config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_guid: userGuid,
      enabled_agents: enabledAgents,
      settings: settings
    })
  });
  return await response.json();
}

// Usage
const agents = await listAgents();
console.log(`Found ${agents.length} agents`);

await saveConfig(
  'my-user-guid',
  ['context_memory_agent.py', 'manage_memory_agent.py'],
  { business_type: 'coffee_shop', enable_upsell: false }
);
```

### cURL

```bash
# List all agents
curl "http://localhost:7071/api/agent_manager?action=list_agents"

# Get user configuration
curl "http://localhost:7071/api/agent_manager?action=get_config&user_guid=my-user-guid"

# Save configuration
curl -X POST "http://localhost:7071/api/agent_manager?action=save_config" \
  -H "Content-Type: application/json" \
  -d '{
    "user_guid": "my-user-guid",
    "enabled_agents": ["context_memory_agent.py", "manage_memory_agent.py"],
    "settings": {
      "business_type": "coffee_shop",
      "enable_upsell": false
    }
  }'

# Get metadata preview
curl -X POST "http://localhost:7071/api/agent_manager?action=get_metadata_preview" \
  -H "Content-Type: application/json" \
  -d '{
    "selected_agents": ["ContextMemory", "ManageMemory"]
  }'
```

## Troubleshooting

### Agents Not Loading

**Problem:** Agent Manager shows "No agents available"

**Solution:**
1. Ensure Azure Function is running (`./run.sh`)
2. Check that agents exist in `agents/` folder
3. Verify Azure Storage connection string in `local.settings.json`
4. Check browser console for CORS errors

### Configuration Not Saving

**Problem:** "Save Configuration" button doesn't persist changes

**Solution:**
1. Verify Azure Storage connection is working
2. Check that `AzureWebJobsStorage` is set in `local.settings.json`
3. Ensure file share `agent_config` exists in Azure Storage
4. Check browser network tab for failed API calls

### Metadata Preview Empty

**Problem:** Metadata preview shows "No agents selected"

**Solution:**
1. Select at least one agent in the Agents tab
2. Click "🔄 Refresh Preview" button
3. Check browser console for errors
4. Verify selected agents have valid metadata

### Preset Not Applying

**Problem:** Clicking a preset doesn't change agent selection

**Solution:**
1. Ensure presets are loaded (check presets.json in storage)
2. Agent filenames in preset must match actual agent files
3. Refresh the page and try again

## Security Considerations

### Production Deployment

1. **Enable Authentication:**
   - Use Azure Function authentication (Easy Auth)
   - Implement custom JWT validation
   - Restrict access by IP or network

2. **Protect Configuration API:**
   - Validate user GUID format
   - Implement role-based access control
   - Audit configuration changes

3. **Secure Storage:**
   - Use Managed Identity for storage access
   - Encrypt sensitive settings
   - Regular backup of configurations

### CORS Configuration

Update CORS settings in `function_app.py` for production:

```python
def build_cors_response(origin):
    allowed_origins = [
        "https://your-domain.com",
        "https://app.your-company.com"
    ]

    if origin in allowed_origins:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Allow-Credentials": "true"
        }
    else:
        return {}
```

## Performance Optimization

### Caching

Implement agent list caching to reduce load times:

```python
# In function_app.py
_agent_cache = None
_cache_timestamp = None
CACHE_TTL = 300  # 5 minutes

def get_cached_agents():
    global _agent_cache, _cache_timestamp
    import time

    now = time.time()
    if _agent_cache is None or (now - _cache_timestamp) > CACHE_TTL:
        _agent_cache = load_agents_from_folder(user_guid=None)
        _cache_timestamp = now

    return _agent_cache
```

### Lazy Loading

Load agent details on demand:

```javascript
// Only load metadata when needed
async function loadAgentDetails(agentName) {
  const response = await fetch(
    `${API_BASE_URL}/agent_manager?action=get_agent_details&agent=${agentName}`
  );
  return await response.json();
}
```

## Extending the System

### Adding New Categories

Modify the `categorize_agent()` function:

```python
def categorize_agent(agent_name):
    categories = {
        'Memory': ['ContextMemory', 'ManageMemory'],
        'Commerce': ['OrderVerification'],
        'Utilities': ['GithubAgentLibraryManager', 'ScriptedDemo'],
        'Analysis': ['ContractAnalysis', 'PromptPlayground'],
        'CRM': ['SalesforceLead', 'DynamicsContact'],  # New category
        'Communication': ['EmailAgent', 'SlackAgent']  # New category
    }

    for category, agents in categories.items():
        if agent_name in agents:
            return category

    return 'Other'
```

### Custom Preset Icons

Add more visual preset icons:

```python
def get_default_presets():
    return [
        {
            'name': 'Sales Accelerator',
            'icon': '🚀',
            'description': 'CRM and order agents for sales teams',
            'agents': ['order_verification_agent.py', 'salesforce_lead_agent.py']
        },
        {
            'name': 'Support Suite',
            'icon': '🎧',
            'description': 'Memory and communication for support',
            'agents': ['context_memory_agent.py', 'email_agent.py']
        }
    ]
```

### Agent Dependencies

Implement automatic dependency resolution:

```python
AGENT_DEPENDENCIES = {
    'OrderVerification': ['ContextMemory'],  # Order agent requires memory
    'ContractAnalysis': ['ManageMemory'],
}

def resolve_dependencies(selected_agents):
    """Automatically include required dependencies"""
    resolved = set(selected_agents)

    for agent in selected_agents:
        if agent in AGENT_DEPENDENCIES:
            resolved.update(AGENT_DEPENDENCIES[agent])

    return list(resolved)
```

## Conclusion

The Agent Manager provides a powerful, user-friendly interface for configuring and managing AI agent combinations. Key benefits:

- ✅ **Visual Management**: No code required to configure agents
- ✅ **Per-User Configs**: Different users can have different agent sets
- ✅ **Preset Library**: Quick deployment of common configurations
- ✅ **Metadata Transparency**: See exactly what OpenAI receives
- ✅ **Production Ready**: Built on Azure Functions with proper storage
- ✅ **Extensible**: Easy to add new agents, categories, and presets

For questions or support, please refer to the main project documentation in `CLAUDE.md`.
