# RAPP Repository Structure

Last Updated: 2025-11-24

## Directory Layout

```
RAPP/
├── README.md                      # Main project documentation
├── CLAUDE.md                      # Claude Code development guide
├── REPOSITORY_STRUCTURE.md        # This file - repository organization guide
│
├── agents/                        # Agent implementations (auto-loaded)
│   ├── basic_agent.py            # Base agent class
│   ├── context_memory_agent.py   # Memory retrieval agent
│   ├── manage_memory_agent.py    # Memory storage agent
│   ├── github_agent_library_manager.py
│   └── ... (custom agents)
│
├── utils/                         # Utility modules
│   └── azure_file_storage.py     # Azure Storage integration
│
├── docs/                          # Documentation site (GitHub Pages)
│   ├── README.md                 # Documentation index
│   ├── index.html                # GitHub Pages landing page
│   ├── index.md                  # GitHub Pages content
│   ├── ARCHITECTURE.md           # System architecture guide
│   ├── API_REFERENCE.md          # API documentation
│   ├── AGENT_DEVELOPMENT.md      # Agent development guide
│   ├── DEPLOYMENT.md             # Deployment instructions
│   ├── GETTING_STARTED.md        # Quick start guide
│   ├── POWER_PLATFORM_INTEGRATION.md
│   ├── SECURITY.md               # Security best practices
│   ├── TROUBLESHOOTING.md        # Common issues and solutions
│   ├── agent_manager_static.html # Static agent manager
│   ├── agent_manifest.json       # Agent metadata cache
│   ├── proactive-insights.html   # ProactiveInsights demo
│   ├── images/                   # Documentation images
│   └── guides/                   # Comprehensive guides
│       ├── README.md             # Guides index
│       ├── AGENT_MANAGER_README.md
│       ├── AGENT_MANAGER_QUICKSTART.md
│       ├── AGENT_MANAGER_DYNAMIC_GUIDE.md
│       ├── AGENT_STORE_STATIC.md
│       ├── ADD_OS_TO_CHAT.md
│       ├── COLLABORATIVE_OS_INTEGRATION.md
│       ├── COLLABORATIVE_OS_SUMMARY.md
│       ├── DATA_LOADING_PATTERN.md
│       ├── DEMO_PROACTIVE_INSIGHTS.md
│       ├── DND_PLAYER_GUIDE.md
│       ├── DOCUMENTATION_COMPLETE.md
│       ├── DOCUMENTATION_STRUCTURE.md
│       ├── FRONTEND_QUICKSTART.md
│       ├── GITHUB_PAGES_SETUP.md
│       ├── GITHUB_PAGES_DEPLOYMENT.md
│       ├── MIGRATION_SUMMARY.md
│       ├── ORDER_VERIFICATION_AGENT_README.md
│       ├── PII_SCRUBBING_REPORT.md
│       ├── PROMPT_PLAYGROUND_GUIDE.md
│       ├── STATIC_MIGRATION_COMPLETE.md
│       ├── UPDATE_SUMMARY.md
│       └── API_KEYS_REMOVAL_SUMMARY.md
│
├── demos/                         # Demo files and examples
│   ├── README.md                 # Demos index
│   ├── demo_enterprise_orchestrator.py
│   ├── demo_orchestrator_standalone.py
│   ├── demo_order_agent.py
│   ├── test_order_agent.py
│   ├── dnd_visual_game.html
│   └── dnd_visual_game_ENHANCED.html
│
├── tools/                         # Development and maintenance tools
│   ├── README.md                 # Tools documentation
│   ├── generate_agent_catalog.py # Agent catalog generator
│   ├── agent_catalog_generated.js
│   └── test_agent_store_urls.sh
│
├── power-platform/               # Power Platform integration
│   ├── README.md                 # Power Platform setup guide
│   └── MSFTAIBASMultiAgentCopilot_1_0_0_2.zip
│
├── AI-Agent-Templates/           # Agent library and templates
│   ├── README.md                 # Agent templates documentation
│   ├── agent_stacks/             # Organized by industry/function
│   │   ├── b2b_sales_stacks/
│   │   ├── customer_service_stacks/
│   │   ├── financial_services_stacks/
│   │   └── ... (12+ categories)
│   └── DEMO_SYSTEM.md
│
├── localFirstTools/              # Local-first development tools
│   ├── index.html                # Tools gallery
│   ├── apps/                     # Tool applications
│   └── scripts/                  # Utility scripts
│
├── .claude/                      # Claude Code agent definitions
│   └── agents/
│       ├── 343-guilty-spark.md   # Repository steward agent
│       └── m365-demo-builder.md  # M365 demo builder agent
│
├── .github/                      # GitHub configuration
│   └── workflows/                # CI/CD workflows
│
├── .venv/                        # Python virtual environment (gitignored)
├── __pycache__/                  # Python cache (gitignored)
│
├── function_app.py               # Azure Functions entry point
├── host.json                     # Azure Functions host config
├── functions.json                # Azure Functions bindings
├── requirements.txt              # Python dependencies
│
├── index.html                    # Main web chat interface
├── manifest.json                 # Web app manifest
├── agent_manifest.json           # Agent metadata cache
│
├── azuredeploy.json              # Azure ARM template
├── deploy.sh                     # Deployment script
├── setup.sh                      # Local setup script
├── run.sh                        # Local development server (Mac/Linux)
│
├── local.settings.json           # Local config (gitignored, auto-generated)
├── local.settings.json.example   # Config template
├── .env.example                  # Environment variables template
│
├── .gitignore                    # Git ignore rules
├── .gitattributes                # Git attributes
└── .funcignore                   # Azure Functions ignore rules
```

## File Categories

### Core Application Files (MUST stay in root)

These files are required in the root directory for Azure Functions to work:

- **function_app.py** - Azure Functions entry point (contains HTTP trigger definitions)
- **host.json** - Azure Functions runtime configuration
- **functions.json** - Function bindings configuration
- **requirements.txt** - Python dependencies for Azure Functions
- **local.settings.json** - Local development settings (gitignored)
- **index.html** - Main web interface (served as static file)

### Deployment Files (Root)

Required in root for deployment automation:

- **azuredeploy.json** - Azure Resource Manager template
- **deploy.sh** - Automated deployment script
- **setup.sh** - Post-deployment local setup
- **run.sh** - Local development server launcher

### Documentation (Root)

Primary documentation files that should remain accessible at repository root:

- **README.md** - Main project overview and quick start
- **CLAUDE.md** - Development guide for Claude Code
- **REPOSITORY_STRUCTURE.md** - This file

### Organized Subdirectories

**New in 2025-11-24 reorganization:**

#### /docs/guides/
Comprehensive documentation files moved from root to improve organization:
- All .md guide files except README.md and CLAUDE.md
- Agent manager documentation
- Integration guides
- Migration summaries
- Technical documentation

#### /demos/
Demo and example files:
- Python demo scripts
- HTML demo interfaces
- Test files

#### /tools/
Development utilities:
- Agent catalog generator
- Test scripts
- Build tools

#### /power-platform/
Microsoft Power Platform integration:
- Solution packages
- Setup documentation

## Navigation Guide

### For End Users

**Getting Started:**
1. Read [/README.md](/README.md) - Project overview and deployment
2. Visit [GitHub Pages Docs](https://kody-w.github.io/RAPP/) - Live demos and guides
3. Open [/index.html](/index.html) - Chat interface

**Learning RAPP:**
- [/docs/GETTING_STARTED.md](/docs/GETTING_STARTED.md) - First steps
- [/docs/ARCHITECTURE.md](/docs/ARCHITECTURE.md) - How it works
- [/docs/guides/DEMO_PROACTIVE_INSIGHTS.md](/docs/guides/DEMO_PROACTIVE_INSIGHTS.md) - Feature demo

### For Developers

**Development Setup:**
1. Read [/CLAUDE.md](/CLAUDE.md) - Development guide
2. Check [/docs/AGENT_DEVELOPMENT.md](/docs/AGENT_DEVELOPMENT.md) - Create agents
3. Review [/docs/API_REFERENCE.md](/docs/API_REFERENCE.md) - API docs

**Common Tasks:**
- **Add new agent**: Create in `/agents/` directory
- **Run locally**: `./run.sh`
- **Deploy to Azure**: `./deploy.sh`
- **Generate agent catalog**: `python tools/generate_agent_catalog.py`

**Architecture Documentation:**
- [/docs/ARCHITECTURE.md](/docs/ARCHITECTURE.md) - System design
- [/docs/guides/DATA_LOADING_PATTERN.md](/docs/guides/DATA_LOADING_PATTERN.md) - Data patterns
- [/docs/TROUBLESHOOTING.md](/docs/TROUBLESHOOTING.md) - Common issues

### For Power Platform Integration

**Setup Guides:**
1. [/docs/POWER_PLATFORM_INTEGRATION.md](/docs/POWER_PLATFORM_INTEGRATION.md) - Complete guide
2. [/power-platform/README.md](/power-platform/README.md) - Quick setup
3. [/docs/guides/COLLABORATIVE_OS_INTEGRATION.md](/docs/guides/COLLABORATIVE_OS_INTEGRATION.md) - M365 integration

**Solution Package:**
- [/power-platform/MSFTAIBASMultiAgentCopilot_1_0_0_2.zip](/power-platform/MSFTAIBASMultiAgentCopilot_1_0_0_2.zip)

### For Contributors

**Documentation:**
- [/docs/guides/DOCUMENTATION_STRUCTURE.md](/docs/guides/DOCUMENTATION_STRUCTURE.md) - Doc organization
- [/docs/guides/GITHUB_PAGES_SETUP.md](/docs/guides/GITHUB_PAGES_SETUP.md) - Pages deployment

**Migration Guides:**
- [/docs/guides/MIGRATION_SUMMARY.md](/docs/guides/MIGRATION_SUMMARY.md) - Recent changes
- [/docs/guides/STATIC_MIGRATION_COMPLETE.md](/docs/guides/STATIC_MIGRATION_COMPLETE.md) - Static migration

## Recent Changes (2025-11-24)

### Repository Cleanup and Organization

**Moved to `/docs/guides/`:**
- 22 markdown documentation files
- Agent manager guides
- Integration documentation
- Migration and update summaries

**Moved to `/demos/`:**
- Demo Python scripts (enterprise orchestrator, order agent)
- Interactive HTML demos (D&D games)
- Test files

**Moved to `/tools/`:**
- `generate_agent_catalog.py` - Agent catalog generator
- `agent_catalog_generated.js` - Generated catalog
- Test scripts

**Moved to `/power-platform/`:**
- Power Platform solution ZIP file
- Added comprehensive setup guide

**Updated References:**
- All documentation references to `generate_agent_catalog.py` now point to `tools/generate_agent_catalog.py`
- Created README.md in each new directory for navigation
- Updated .gitignore to preserve Power Platform solution files

**Files Removed from Root:**
- Duplicate HTML files (already existed in `/docs/`)
- 22 documentation .md files (now in `/docs/guides/`)

## Benefits of New Structure

**Improved Organization:**
- Root directory contains only essential operational files
- Documentation organized by purpose in `/docs/guides/`
- Demo files separated from production code
- Development tools isolated in `/tools/`

**Better Maintainability:**
- Clear separation of concerns
- Easier to find relevant files
- Reduced root directory clutter
- Better git diff readability

**Enhanced Navigation:**
- README.md files in each directory
- Clear directory purposes
- Logical file grouping
- Comprehensive cross-references

**Preserved Functionality:**
- Azure Functions structure intact
- All imports still work
- Deployment scripts unchanged
- No breaking changes to functionality

## Validation

All critical functionality verified:
- ✅ function_app.py imports successfully
- ✅ Agent loading paths unchanged
- ✅ Azure Functions structure preserved
- ✅ Documentation references updated
- ✅ Tool scripts accessible with new paths
- ✅ Git tracking maintained for all files

## See Also

- [Main README](/README.md) - Project overview
- [Claude Development Guide](/CLAUDE.md) - Development instructions
- [Documentation Index](/docs/README.md) - Full documentation
- [Guides Index](/docs/guides/README.md) - Comprehensive guides
- [Demos Index](/demos/README.md) - Demo files
- [Tools Index](/tools/README.md) - Development tools
