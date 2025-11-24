# .rapp Directory - Development Meta-Agents

## ✅ Setup Complete!

The `.rapp` directory has been successfully established with repository-specific development agents.

## What's Included

### 📁 Directory Structure

```
.rapp/
├── README.md          # Comprehensive documentation
├── QUICKSTART.md      # Quick start guide (you are here)
├── agents/            # Meta-agents for development
│   ├── __init__.py
│   ├── repository_steward.py  # Health monitoring & audits
│   └── agent_generator.py     # Agent scaffolding tool
└── templates/
    └── agent_template.py      # Base template for new agents
```

### 🛠️ Available Tools

1. **Repository Steward** - Repository health monitoring
   - Dependency audits
   - Code pattern analysis
   - Documentation validation
   - Security checks

2. **Agent Generator** - Scaffolds new agents with proper structure

### 🚀 Quick Test

Run this command to verify everything works:

```bash
python3 tools/run_rapp_agent.py repository_steward --action dependencies
```

You should see output like:
```
🔍 Running Repository Steward - DEPENDENCIES audit
================================================================================
📦 DEPENDENCY AUDIT
✓ Found 55 dependencies in requirements.txt
...
```

### 📖 Documentation

- **Full docs**: `.rapp/README.md`
- **Quick start**: `.rapp/QUICKSTART.md`
- **Copilot guidance**: `.github/copilot-instructions.md`
- **Repository structure**: `REPOSITORY_STRUCTURE.md`

### 🔧 Key Features

- ✅ Not deployed to Azure (excluded in `.funcignore`)
- ✅ Version controlled (tracked in git)
- ✅ CLI tool ready (`tools/run_rapp_agent.py`)
- ✅ No API keys needed for static analysis
- ✅ Extensible - add your own meta-agents

### 🎯 Next Steps

1. **Run a full audit:**
   ```bash
   python3 tools/run_rapp_agent.py repository_steward --action full
   ```

2. **Generate your first agent:**
   ```bash
   python3 tools/run_rapp_agent.py agent_generator \
     --name "my_agent" \
     --description "does something useful"
   ```

3. **Read the docs:**
   - `.rapp/QUICKSTART.md` - Usage examples
   - `.rapp/README.md` - Complete documentation

### 💡 Pro Tips

- Run `repository_steward --action security` before commits
- Use `agent_generator` to ensure consistent code structure
- Check `.rapp/README.md` for adding custom meta-agents
- These tools run locally - no deployment needed!

---

**Setup Date:** November 24, 2025  
**Status:** ✅ Fully Functional  
**Tested:** ✅ All components verified
