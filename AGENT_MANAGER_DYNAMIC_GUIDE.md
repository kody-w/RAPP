# Dynamic Agent Manager - Extensible System

## 🎯 What We Built

An **auto-discovering, self-organizing agent management system** that dynamically builds itself from your local agent files. NO hardcoded agent lists, NO manual categorization, NO static configurations.

## ✨ Key Features

### 1. **Automatic Agent Discovery**

The system scans your `/agents` folder and automatically:
- ✅ Discovers all agent files
- ✅ Extracts metadata without importing (no dependency errors)
- ✅ Parses agent names, descriptions, parameters
- ✅ Reads docstrings and file documentation
- ✅ Identifies capabilities from parameter schemas

### 2. **Intelligent Auto-Categorization**

Agents are automatically categorized using keyword analysis:

**Currently Detected Categories:**
- 🧠 **Memory** (2 agents) - Context & memory management
- 🛒 **Commerce** (1 agent) - Order verification & upselling
- 🔧 **Utilities** (2 agents) - Demos & playground tools
- 💻 **Development** (1 agent) - GitHub agent library
- 🎮 **Entertainment** (1 agent) - D&D Dungeon Master
- 📊 **Analytics** (1 agent) - Contract analysis

The system uses keyword matching to intelligently assign categories based on:
- Agent name
- Description content
- Parameter names
- File content

### 3. **Auto-Generated Presets**

The system automatically creates presets:

**Generated Presets:**
1. 🌟 **Full Suite** - All agents enabled
2. 🧠 **Memory Suite** - All memory agents
3. 🔧 **Utilities Suite** - All utility agents
4. 🛒 **Commerce Suite** - All commerce agents
5. 💻 **Development Suite** - All development agents
6. 🎮 **Entertainment Suite** - All entertainment agents
7. 📊 **Analytics Suite** - All analytics agents
8. 🛒 **Customer Service** - Memory + Commerce combined
9. ⭐ **Essential** - Core memory agents only

### 4. **Dynamic Manifest Generation**

Run the discovery anytime to regenerate the manifest:

```bash
python3 -m utils.agent_discovery
```

**Output:** `agent_manifest.json` with complete agent catalog

##  How It Works

### Static Analysis (No Imports Required)

The system uses **regex pattern matching and AST parsing** to extract agent information WITHOUT importing the files. This means:

- ✅ No dependency errors
- ✅ No module import issues
- ✅ Works offline
- ✅ Fast scanning
- ✅ Safe to run anytime

### Extraction Process

For each `.py` file in `/agents`:

1. **Parse agent name**: `self.name = 'AgentName'`
2. **Parse metadata dict**: `self.metadata = {…}`
3. **Extract file docstring**: Module-level documentation
4. **Extract class docstring**: Class-level documentation
5. **Parse parameters**: From metadata dictionary
6. **Infer category**: Keyword matching algorithm
7. **Extract tags**: AI, ML, API, Storage, etc.
8. **Identify dependencies**: From import statements

### Example: OrderVerification Agent

**Discovered Information:**
```json
{
  "name": "OrderVerification",
  "filename": "order_verification_agent.py",
  "class_name": "OrderVerificationAgent",
  "category": "Commerce",
  "tags": ["analytics", "ai", "service", "customer", "storage", "database", "data"],
  "file_docstring": "Voice Order Verification & Upsell Agent\nPROBLEM SOLVED: Employees experience mental fatigue...",
  "use_cases": ["Drive-thru", "phone orders", "counter service", "conversational commerce"]
}
```

## 🚀 How to Use

### 1. Add a New Agent

Just drop a new agent file in `/agents`:

```python
# /agents/my_new_agent.py
from agents.basic_agent import BasicAgent

class MyNewAgent(BasicAgent):
    def __init__(self):
        self.name = 'MyNew'
        self.metadata = {
            "name": self.name,
            "description": "Does something amazing with AI and data",
            "parameters": {
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "Input data"}
                },
                "required": ["input"]
            }
        }
        super().__init__(self.name, self.metadata)

    def perform(self, **kwargs):
        return "Result"
```

### 2. Regenerate Manifest

```bash
python3 -m utils.agent_discovery
```

**Output:**
```
📦 Total Agents: 9  (was 8)
📁 Total Categories: 7  (new category auto-detected)
⚙️ Total Presets: 10  (new preset auto-generated)
```

### 3. Reload Agent Manager

Open `http://localhost:7071/agent_manager.html`

**Your new agent appears automatically:**
- In the correct category
- With the right description
- In relevant presets
- Ready to use

## 📋 Current Agent Inventory

### Discovered Agents (8)

| Agent | Category | Description |
|-------|----------|-------------|
| **ContextMemory** | 🧠 Memory | Recalls conversation history and context |
| **ManageMemory** | 🧠 Memory | Stores facts, preferences, and insights |
| **OrderVerification** | 🛒 Commerce | Verifies orders, catches errors, suggests upsells |
| **ContractAnalysis** | 📊 Analytics | Analyzes contracts and extracts obligations |
| **PromptPlayground** | 🔧 Utilities | Prompt engineering and A/B testing |
| **ScriptedDemo** | 🔧 Utilities | Executes scripted demonstrations |
| **GitHubAgentLibrary** | 💻 Development | Manages agent library integrations |
| **DDDungeonMaster** | 🎮 Entertainment | D&D 5e dungeon master with full mechanics |

### Categories (6)

- **Memory** - Context and memory management (2 agents)
- **Commerce** - Order processing and sales (1 agent)
- **Analytics** - Analysis and reporting (1 agent)
- **Utilities** - Tools and helpers (2 agents)
- **Development** - Code and deployment (1 agent)
- **Entertainment** - Games and interactive experiences (1 agent)

### Auto-Generated Presets (9)

All presets are dynamically generated based on discovered agents and their categories.

## 🔧 Extensibility

### Adding New Categories

The system auto-detects categories based on keywords. To add a new category, just create agents that match the keywords:

**Current Category Keywords:**
```python
{
    'Memory': ['memory', 'context', 'recall', 'remember', 'history'],
    'Commerce': ['order', 'purchase', 'payment', 'checkout', 'cart', 'upsell'],
    'Communication': ['email', 'message', 'notify', 'slack', 'teams', 'chat'],
    'Analytics': ['analyze', 'analytics', 'report', 'metrics', 'insights', 'contract'],
    'Document': ['document', 'pdf', 'file', 'upload', 'download'],
    'CRM': ['crm', 'salesforce', 'dynamics', 'customer', 'lead', 'contact'],
    'Automation': ['workflow', 'automate', 'schedule', 'trigger', 'pipeline'],
    'Development': ['code', 'github', 'git', 'deploy', 'build', 'test', 'library'],
    'Entertainment': ['game', 'dungeon', 'play', 'fun', 'interactive', 'dnd'],
    'Utilities': ['demo', 'playground', 'test', 'helper', 'utility', 'tool']
}
```

**Example: Adding a CRM Category**

Create an agent with CRM keywords:
```python
class SalesforceLeadAgent(BasicAgent):
    def __init__(self):
        self.name = 'SalesforceLead'
        self.metadata = {
            "description": "Manages Salesforce leads and customer contacts"
        }
```

**Result:** Automatically categorized as **CRM** and included in new **CRM Suite** preset.

### Custom Preset Logic

Edit `/utils/agent_discovery.py` to add custom preset generation:

```python
def _auto_generate_presets(self):
    # ... existing presets ...

    # Add custom preset logic
    crm_agents = self.categories.get('CRM', [])
    commerce_agents = self.categories.get('Commerce', [])

    if crm_agents and commerce_agents:
        combined = crm_agents + commerce_agents
        self.suggested_presets.append({
            'name': 'Sales Team',
            'description': 'CRM and commerce for sales operations',
            'agents': [self.discovered_agents[name]['filename'] for name in combined],
            'icon': '📈'
        })
```

## 💡 Advanced Features

### 1. Tag Extraction

Agents are automatically tagged based on content:

**Detected Tags:**
- `ai`, `ml`, `nlp`, `gpt`, `openai`
- `customer`, `service`, `support`
- `sales`, `marketing`, `analytics`
- `automation`, `workflow`, `integration`
- `data`, `storage`, `database`
- `api`, `webhook`, `rest`

### 2. Use Case Detection

The system automatically extracts use cases from docstrings:

**Pattern Recognition:**
- "Perfect for:"
- "Use cases:"
- "Ideal for:"
- "Best for:"

**Example Detection:**
```python
"""
Perfect for: Drive-thru, phone orders, counter service
"""
```

**Result:** Use cases = `["Drive-thru", "phone orders", "counter service"]`

### 3. Dependency Tracking

Automatically detects agent dependencies:

```python
from agents.context_memory_agent import ContextMemoryAgent
```

**Result:** Dependencies = `["ContextMemoryAgent"]`

### 4. Capability Inference

Capabilities are inferred from parameter schemas:

```python
"parameters": {
    "properties": {
        "customer_input": {"description": "What the customer said"},
        "business_type": {"description": "Type of business"}
    }
}
```

**Result:**
```
Capabilities:
- customer_input: What the customer said
- business_type: Type of business
```

## 🎨 Integration with Agent Manager UI

The HTML interface (`agent_manager.html`) can be updated to use the manifest:

### Load from Manifest

```javascript
// Instead of API call, load from manifest
async function loadAgents() {
    const response = await fetch('/agent_manifest.json');
    const manifest = await response.json();

    allAgents = Object.values(manifest.agents).map(agent => ({
        name: agent.name,
        description: agent.description || agent.file_docstring,
        category: agent.category,
        filename: agent.filename,
        metadata: agent.metadata,
        tags: agent.tags,
        use_cases: agent.use_cases
    }));

    renderAgents();
}

// Load presets from manifest
async function loadPresets() {
    const response = await fetch('/agent_manifest.json');
    const manifest = await response.json();

    presets = manifest.suggested_presets;
    renderPresets();
}
```

## 📊 Statistics & Analytics

The manifest includes statistics:

```json
{
  "statistics": {
    "total_agents": 8,
    "total_categories": 6,
    "total_presets": 9
  }
}
```

Use these for dashboards and monitoring.

## 🔄 Continuous Discovery

Set up automatic discovery:

### 1. Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Regenerate manifest before commit
python3 -m utils.agent_discovery

# Add manifest to commit
git add agent_manifest.json
```

### 2. CI/CD Integration

```yaml
# .github/workflows/agent-discovery.yml
name: Agent Discovery

on:
  push:
    paths:
      - 'agents/**/*.py'

jobs:
  discover:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run agent discovery
        run: python3 -m utils.agent_discovery
      - name: Commit manifest
        run: |
          git config user.name "Agent Discovery Bot"
          git add agent_manifest.json
          git commit -m "Update agent manifest [skip ci]"
          git push
```

### 3. Scheduled Discovery

```python
# Run discovery every hour
import schedule
import time

def run_discovery():
    from utils.agent_discovery import AgentDiscovery
    discovery = AgentDiscovery()
    discovery.discover_all_agents()
    discovery.export_manifest()

schedule.every().hour.do(run_discovery)

while True:
    schedule.run_pending()
    time.sleep(60)
```

## 🌍 Multi-Source Discovery

Extend to discover agents from multiple sources:

```python
class AgentDiscovery:
    def discover_all_sources(self):
        # Local filesystem
        self.discover_all_agents()

        # Azure File Storage
        self.discover_from_azure_storage()

        # GitHub repository
        self.discover_from_github()

        # NPM packages
        self.discover_from_npm()

        return self.get_agent_manifest()
```

## 📖 Documentation Generation

Generate documentation from the manifest:

```python
def generate_docs(manifest):
    """Generate markdown documentation from agent manifest"""

    docs = "# Agent Catalog\n\n"

    for category, agents in manifest['categories'].items():
        docs += f"## {category}\n\n"

        for agent_name in agents:
            agent = manifest['agents'][agent_name]
            docs += f"### {agent_name}\n\n"
            docs += f"{agent['description']}\n\n"

            if agent['capabilities']:
                docs += "**Capabilities:**\n"
                for cap in agent['capabilities']:
                    docs += f"- {cap}\n"
                docs += "\n"

    return docs
```

## 🎯 Next Steps

### 1. Enhanced Metadata Extraction

Improve the regex patterns to better extract metadata dictionaries:

```python
def _parse_metadata_dict(self, file_content):
    # Use more sophisticated AST parsing
    # Handle nested dictionaries
    # Support multiline strings
    pass
```

### 2. Add Web UI Updates

Update `agent_manager.html` to load from `agent_manifest.json` instead of API calls for faster performance.

### 3. Real-Time Discovery

Add file watchers to regenerate manifest when agent files change:

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class AgentFileHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('_agent.py'):
            discovery.discover_all_agents()
            discovery.export_manifest()
```

### 4. Agent Validation

Add validation to ensure agents meet quality standards:

```python
def validate_agent(agent_info):
    errors = []

    if not agent_info['description'] or len(agent_info['description']) < 20:
        errors.append("Description too short")

    if not agent_info['metadata']:
        errors.append("Missing metadata")

    if not agent_info['parameters']:
        errors.append("Missing parameters")

    return errors
```

## 🏆 Benefits

### For Developers

- ✅ **Zero Configuration**: Just add a file, it's auto-discovered
- ✅ **No Manual Updates**: Categories and presets auto-generate
- ✅ **Instant Feedback**: See your agent appear immediately
- ✅ **Safe to Run**: Static analysis, no imports required

### For Operations

- ✅ **Self-Documenting**: Manifest serves as documentation
- ✅ **Version Control**: Track agent changes over time
- ✅ **Easy Auditing**: See all agents at a glance
- ✅ **Deployment Ready**: Manifest can drive deployments

### For Users

- ✅ **Always Current**: UI always shows latest agents
- ✅ **Smart Presets**: Relevant combinations suggested
- ✅ **Easy Discovery**: Find agents by category or tag
- ✅ **Transparent**: See exact capabilities

## 📝 Summary

You now have a **fully dynamic, self-organizing agent management system** that:

1. ✨ **Auto-discovers** agents from local files
2. 🏷️ **Auto-categorizes** using intelligent keyword matching
3. 📦 **Auto-generates** presets for common use cases
4. 🚀 **Scales effortlessly** as you add more agents
5. 🔧 **Requires zero maintenance** - just add files and run

**No more hardcoded lists. No more manual updates. Just pure extensibility.**

---

**Run discovery now:**
```bash
python3 -m utils.agent_discovery
```

**View manifest:**
```bash
cat agent_manifest.json
```

**Start using:**
```bash
./run.sh
# Open http://localhost:7071/agent_manager.html
```
