# .rapp Directory

This directory contains repository-specific RAPP agents that are designed for development, maintenance, and management of this codebase. These agents are separate from the production agents in `/agents/` and are intended for internal use.

## Purpose

The `.rapp` directory serves as a meta-layer for:
- **Repository Management**: Agents that help maintain and organize the codebase
- **Development Tools**: Agents that assist with development workflows
- **Quality Assurance**: Agents that perform code reviews, testing, and validation
- **Documentation**: Agents that generate or maintain project documentation

## Structure

```
.rapp/
├── README.md                    # This file
├── agents/                      # Repository-specific agents
│   ├── repository_steward.py   # Repository health monitoring and maintenance
│   ├── agent_generator.py      # Scaffolds new agents from templates
│   └── documentation_sync.py   # Keeps docs in sync with code
└── templates/                   # Templates for code generation
    └── agent_template.py        # Base template for new agents
```

## Agent Categories

### Repository Management Agents
- **Repository Steward**: Monitors codebase health, dependencies, and best practices
- **Security Auditor**: Checks for security issues, exposed secrets, vulnerabilities
- **Dependency Manager**: Manages Python dependencies and version conflicts

### Development Tool Agents
- **Agent Generator**: Creates new agents from templates with proper structure
- **Test Generator**: Generates unit tests for agents
- **Migration Assistant**: Helps migrate agents between versions

### Quality Assurance Agents
- **Code Reviewer**: Analyzes code for patterns, anti-patterns, and improvements
- **Documentation Validator**: Ensures documentation matches implementation
- **Integration Tester**: Tests agent interactions and workflows

## Usage

### Loading .rapp Agents

These agents are NOT auto-loaded by `function_app.py`. They are designed to be invoked directly:

```python
# Import and use directly in development scripts
from .rapp.agents.repository_steward import RepositorySteward
from .rapp.agents.agent_generator import AgentGenerator

# Initialize with OpenAI client
client = AzureOpenAI(...)
steward = RepositorySteward(client)

# Execute agent operations
report = steward.execute("Audit repository health", [], user_guid)
```

### CLI Integration

You can create CLI wrappers in `/tools/` to invoke `.rapp` agents:

```bash
# Example: Run repository health check
python tools/run_rapp_agent.py repository_steward --action health_check

# Example: Generate a new agent
python tools/run_rapp_agent.py agent_generator --name "my_new_agent" --description "..."
```

## Difference from /agents/

| Feature | `/agents/` | `/.rapp/agents/` |
|---------|-----------|------------------|
| Purpose | Production AI agents | Development/maintenance tools |
| Auto-loaded | Yes, by `function_app.py` | No, manually invoked |
| Deployment | Deployed to Azure | Local development only |
| API Access | Via HTTP endpoint | Direct Python import |
| User-facing | Yes | No (internal use) |

## Best Practices

1. **Keep .rapp agents focused**: Each agent should have a specific maintenance or development purpose
2. **Document thoroughly**: Since these are dev tools, clear documentation is essential
3. **Test before using**: These agents can modify code, so test carefully
4. **Version control**: Commit .rapp agents to share dev tools across the team
5. **Don't deploy**: `.rapp/` should be in `.funcignore` to prevent Azure deployment

## Adding New .rapp Agents

1. Create a new Python file in `.rapp/agents/`
2. Inherit from `BasicAgent` for consistency
3. Implement the standard agent interface
4. Add documentation to this README
5. Optionally create a CLI wrapper in `/tools/`

## Example: Creating a New .rapp Agent

```python
# .rapp/agents/my_dev_agent.py
from agents.basic_agent import BasicAgent

class MyDevAgent(BasicAgent):
    def __init__(self, client):
        super().__init__(client)
        self.client = client
    
    def get_name(self):
        return "my_dev_agent"
    
    def get_description(self):
        return "Development agent that does X, Y, Z"
    
    def get_system_message(self):
        return """You are a development assistant for the RAPP platform.
        Your role is to help with [specific task].
        Always follow RAPP coding patterns and best practices."""
    
    def execute(self, user_input, conversation_history, user_guid=None):
        # Development agent logic here
        # Can access file system, run analysis, generate code, etc.
        return response, updated_history
```

## Security Note

Since `.rapp` agents can modify code and access the file system:
- Review agent code before execution
- Use version control to track changes
- Test in isolated environments first
- Don't expose .rapp agents via the API endpoint
- Add `.rapp/` to `.funcignore` to prevent deployment

---

For questions or suggestions about `.rapp` agents, see `docs/AGENT_DEVELOPMENT.md` or open an issue.
