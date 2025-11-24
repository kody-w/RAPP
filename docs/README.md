# Copilot Agent 365 - GitHub Pages

Live Demo: **https://kody-w.github.io/RAPP/**

## 🌐 GitHub Pages Deployment

This folder contains the static GitHub Pages deployment of the Copilot Agent 365 platform.

### What's Included

- **Landing Page** (`index.html`) - Main entry point showcasing the platform
- **Agent Manager** (`agent_manager_static.html`) - Interactive agent catalog viewer
- **Agent Manifest** (`agent_manifest.json`) - Auto-generated catalog of 8 agents

### Features

#### 🎛️ Agent Manager (Static Demo)
- View all 8 discovered AI agents
- Explore 6 categories (Memory, Commerce, Analytics, Development, Entertainment, Utilities)
- Try 9 auto-generated presets
- Preview OpenAI function metadata
- See agent capabilities and descriptions
- Filter by category
- Real-time statistics

**Note:** This is a demo mode. Full configuration save/load requires the Azure Function backend.

#### 💬 Chat Interface
Link to the full chat application with voice support and persistent memory.

#### 📚 Documentation
Links to comprehensive guides and API documentation.

## 🚀 Quick Start

### View Locally

```bash
# Serve the docs folder
cd docs
python3 -m http.server 8000

# Open in browser
open http://localhost:8000
```

### Deploy to GitHub Pages

1. **Enable GitHub Pages:**
   - Go to repository Settings → Pages
   - Source: Deploy from a branch
   - Branch: `main`
   - Folder: `/docs`
   - Save

2. **Access Your Site:**
   - URL: `https://<username>.github.io/<repository>/`
   - Example: `https://kody-w.github.io/RAPP/`

3. **Update Agent Catalog:**
   ```bash
   # Regenerate manifest from local agents
   python3 -m utils.agent_discovery

   # Copy to docs folder
   cp agent_manifest.json docs/

   # Commit and push
   git add docs/agent_manifest.json
   git commit -m "Update agent catalog"
   git push
   ```

## 📁 File Structure

```
docs/
├── index.html                      # Landing page
├── agent_manager_static.html       # Agent Manager (static)
├── agent_manifest.json             # Agent catalog
└── README.md                       # This file
```

## 🔄 Updating the Catalog

When you add new agents to `/agents`:

```bash
# 1. Discover agents
python3 -m utils.agent_discovery

# 2. Copy manifest
cp agent_manifest.json docs/

# 3. Commit
git add docs/agent_manifest.json
git commit -m "Update agent catalog: Added XYZ agent"
git push
```

GitHub Pages will automatically rebuild (takes 1-2 minutes).

## 🎨 Customization

### Update Landing Page

Edit `docs/index.html` to customize:
- Hero text and description
- Feature cards
- Statistics
- Links and navigation

### Update Agent Manager Theme

Edit `docs/agent_manager_static.html` styles:
- Change `--primary` color gradient
- Update card styles
- Modify layout breakpoints

### Add Custom Presets

Edit `agent_manifest.json` → `suggested_presets` array:

```json
{
  "suggested_presets": [
    {
      "name": "My Custom Preset",
      "description": "Description here",
      "agents": ["agent1.py", "agent2.py"],
      "settings": {},
      "icon": "🎯"
    }
  ]
}
```

## 🔗 Integration with Backend

For full functionality (save/load configurations), deploy the Azure Function:

```bash
# Deploy backend
./deploy.sh

# Update API endpoint in agent_manager.html
const API_BASE_URL = 'https://your-function-app.azurewebsites.net/api';
```

See [`CLAUDE.md`](../CLAUDE.md) for full deployment instructions.

## 📊 Current Agent Catalog

**8 Agents across 6 Categories:**

### 🧠 Memory (2 agents)
- **ContextMemory** - Conversation history and context recall
- **ManageMemory** - Fact and preference storage

### 🛒 Commerce (1 agent)
- **OrderVerification** - Order processing, error detection, upselling

### 📊 Analytics (1 agent)
- **ContractAnalysis** - Contract analysis and obligation extraction

### 🔧 Utilities (2 agents)
- **PromptPlayground** - Prompt engineering and A/B testing
- **ScriptedDemo** - Demo scenario execution

### 💻 Development (1 agent)
- **GitHubAgentLibrary** - Agent library management

### 🎮 Entertainment (1 agent)
- **DDDungeonMaster** - D&D 5e dungeon master with full mechanics

## 🌟 Features

### Landing Page
- ✅ Responsive design
- ✅ Animated statistics
- ✅ Feature cards
- ✅ Direct links to apps
- ✅ Mobile-optimized

### Agent Manager (Static)
- ✅ Interactive agent catalog
- ✅ Preset selection
- ✅ Metadata preview
- ✅ Category filtering
- ✅ Real-time statistics
- ✅ No backend required

## 🔒 Security Note

The static demo does not save configurations. All interactions are client-side only.

For production use with configuration persistence:
1. Deploy the Azure Function backend
2. Configure authentication
3. Use the full `agent_manager.html` (not the static version)

## 📖 Documentation

- [Quick Start Guide](../AGENT_MANAGER_QUICKSTART.md)
- [Full Documentation](../AGENT_MANAGER_README.md)
- [Dynamic Discovery](../AGENT_MANAGER_DYNAMIC_GUIDE.md)
- [Project Overview](../CLAUDE.md)

## 🚀 Next Steps

1. **View the live demo** → https://kody-w.github.io/RAPP/
2. **Try the Agent Manager** → Click "Open Agent Manager"
3. **Explore presets** → Test different agent combinations
4. **View metadata** → See OpenAI function schemas
5. **Deploy the backend** → Enable full functionality

## 💡 Pro Tips

1. **Bookmark the landing page** for quick access
2. **Use presets** to quickly configure agent combinations
3. **Check statistics** to see agent distribution
4. **Regenerate manifest** when you add new agents
5. **Customize themes** to match your brand

## 🎉 Success!

Your Agent Manager is now live on GitHub Pages! 🚀

Visit: **https://kody-w.github.io/RAPP/**

---

Built with ❤️ using Azure Functions, OpenAI GPT-4, and GitHub Pages
