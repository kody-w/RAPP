# .rapp Quick Start Guide

## What is .rapp?

The `.rapp` directory contains **meta-agents** - development tools that help you build, maintain, and monitor your RAPP repository. Think of them as "agents that help you create agents."

## Key Differences

| Feature | `/agents/` | `/.rapp/agents/` |
|---------|-----------|------------------|
| **Purpose** | Production AI agents | Development tools |
| **Deployed?** | ✅ Yes (to Azure) | ❌ No (local only) |
| **Auto-loaded?** | ✅ Yes | ❌ No (manual invoke) |
| **User-facing?** | ✅ Yes | ❌ No (internal) |

## Available Tools

### 🔍 Repository Steward

Monitors your codebase health and performs comprehensive audits.

**Run full audit:**
```bash
python tools/run_rapp_agent.py repository_steward --action full
```

**Check specific areas:**
```bash
# Dependencies only
python tools/run_rapp_agent.py repository_steward --action dependencies

# Agent ecosystem
python tools/run_rapp_agent.py repository_steward --action agents

# Documentation
python tools/run_rapp_agent.py repository_steward --action documentation

# Security scan
python tools/run_rapp_agent.py repository_steward --action security
```

**What it checks:**
- ✅ Python dependencies and version compatibility
- ✅ Agent structure and best practices
- ✅ Documentation completeness
- ✅ Security issues (exposed secrets, etc.)
- ✅ Code patterns and anti-patterns

### 🤖 Agent Generator

Scaffolds new agents with proper structure and boilerplate code.

**Create a new agent:**
```bash
python tools/run_rapp_agent.py agent_generator \
  --name "email_summarizer" \
  --description "summarizes customer emails and extracts key action items"
```

**Or use a full prompt:**
```bash
python tools/run_rapp_agent.py agent_generator \
  --prompt "Create an agent that analyzes code quality and suggests improvements"
```

**What it generates:**
- ✅ Properly structured Python file
- ✅ BasicAgent inheritance
- ✅ All required methods implemented
- ✅ Error handling and logging
- ✅ Type hints and docstrings
- ✅ Ready-to-customize template

## Quick Examples

### Example 1: Health Check Before Deployment

```bash
# Run a full repository audit
python tools/run_rapp_agent.py repository_steward --action full

# Review the output for any critical issues
# Fix any problems before deploying to Azure
```

### Example 2: Create a New Agent

```bash
# Generate the agent
python tools/run_rapp_agent.py agent_generator \
  --name "slack_notifier" \
  --description "sends notifications to Slack channels"

# The agent file is created in agents/slack_notifier.py
# Customize the execute() method with your logic
# Test locally with ./run.sh
# Deploy to Azure when ready
```

### Example 3: Weekly Maintenance

```bash
# Check for dependency updates
python tools/run_rapp_agent.py repository_steward --action dependencies

# Check documentation sync
python tools/run_rapp_agent.py repository_steward --action documentation

# Security audit
python tools/run_rapp_agent.py repository_steward --action security
```

## How It Works

1. **CLI Tool**: `tools/run_rapp_agent.py` provides the command-line interface
2. **Meta-Agents**: `.rapp/agents/` contains the development agents
3. **Templates**: `.rapp/templates/` has code generation templates
4. **Not Deployed**: `.funcignore` excludes `.rapp/` from Azure deployment

## Creating Your Own .rapp Agents

Want to add more development tools? Create a new agent in `.rapp/agents/`:

```python
# .rapp/agents/my_dev_tool.py
from agents.basic_agent import BasicAgent

class MyDevTool(BasicAgent):
    def __init__(self, client):
        super().__init__(client)
        
    def get_name(self):
        return "my_dev_tool"
    
    def get_description(self):
        return "Does something helpful for development"
    
    def get_system_message(self):
        return "System prompt for this dev tool"
    
    def execute(self, user_input, conversation_history, user_guid=None):
        # Your dev tool logic here
        return response, updated_history
```

Then update `tools/run_rapp_agent.py` to add it to the CLI.

## Best Practices

1. **Run audits regularly** - Catch issues early
2. **Use Agent Generator** - Ensures consistent structure
3. **Don't commit secrets** - Repository Steward will warn you
4. **Test before deploying** - Use local development mode
5. **Document custom agents** - Update `.rapp/README.md`

## Troubleshooting

**"Module not found" errors:**
- Make sure you're in the repository root when running commands
- Verify your virtual environment is activated
- Run `pip install -r requirements.txt`

**"No such file or directory":**
- Ensure you're using the correct path to `tools/run_rapp_agent.py`
- Check that the `.rapp/` directory exists

**Agent generation fails:**
- Check that your OpenAI API credentials are configured
- Verify `local.settings.json` has valid settings
- Try with a more specific description

## Learn More

- **Full documentation**: `.rapp/README.md`
- **Agent patterns**: `docs/AGENT_DEVELOPMENT.md`
- **Repository structure**: `REPOSITORY_STRUCTURE.md`
- **Copilot guidance**: `.github/copilot-instructions.md`

---

**Pro Tip:** Run `python tools/run_rapp_agent.py repository_steward --action full` monthly to keep your codebase healthy! 🚀
