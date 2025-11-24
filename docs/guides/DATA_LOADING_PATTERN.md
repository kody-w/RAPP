# Data Loading Pattern - GitHub Pages Architecture

## Overview

The AI-Agent-Templates repository uses a **dynamic data loading pattern** that keeps the HTML file clean and loads agent data from external sources. This prevents committing large data dumps directly in the HTML.

## Architecture: Two-Tier Loading Strategy

### Tier 1: Manifest.json (Primary)

The system **first attempts to load from manifest.json**:

```javascript
async loadFromManifest() {
  try {
    // Load directly from GitHub raw URL (works without server)
    const manifestUrl = `https://raw.githubusercontent.com/${this.GITHUB_REPO}/${this.BRANCH}/manifest.json`;
    const response = await fetch(manifestUrl);

    if (!response.ok) {
      console.warn("Manifest file not found at GitHub");
      return false;
    }

    const manifest = await response.json();
    console.log(`Loaded manifest version ${manifest.version}, generated at ${manifest.generated}`);

    // Load all agents from manifest
    this.agents = manifest.agents;
    return true;
  } catch (error) {
    console.error("Failed to load manifest:", error);
    return false;
  }
}
```

**Benefits:**
- Single HTTP request loads all agent metadata
- Fast loading (one file vs many API calls)
- Works on GitHub Pages (static hosting)
- Manifest is generated automatically by `update_manifest.py`

### Tier 2: Raw URL Loading (Fallback)

If manifest.json fails, the system **falls back to direct GitHub raw URLs**:

```javascript
async loadAgents() {
  try {
    this.showLoading(true);

    // Try to load from manifest first
    const manifestLoaded = await this.loadFromManifest();

    if (!manifestLoaded) {
      // Fallback to raw URL loading (no API, no rate limits!)
      console.warn("Manifest not available, falling back to raw URL loading");
      const singularAgents = await this.loadAgentsViaRawUrls();
      const stackAgents = await this.loadStacksViaRawUrls();
      this.agents = [...singularAgents, ...stackAgents];
    }

    // Sort and display agents
    this.sortAgents();
    this.renderAgents();
  } catch (error) {
    console.error("Failed to load agents:", error);
    this.showError("Failed to load agents from GitHub");
  }
}
```

**Benefits:**
- Robust fallback mechanism
- Loads directly from GitHub repository structure
- No rate limits (uses raw URLs, not GitHub API)
- Self-healing if manifest.json is missing

## manifest.json Generation

The `update_manifest.py` script scans the repository and generates a consolidated manifest:

```python
#!/usr/bin/env python3
"""
Generate manifest.json from AI-Agent-Templates metadata
"""
import json
import os
from pathlib import Path

def generate_manifest():
    agents = []
    base_path = Path("AI-Agent-Templates/agent_stacks")

    # Scan all agent stacks
    for category_dir in base_path.iterdir():
        if not category_dir.is_dir():
            continue

        # Find all metadata.json files
        for metadata_file in category_dir.rglob('metadata.json'):
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
                agents.append({
                    'id': metadata.get('id'),
                    'name': metadata.get('name'),
                    'category': metadata.get('category'),
                    'description': metadata.get('description'),
                    'tags': metadata.get('tags', []),
                    'version': metadata.get('version', '1.0.0'),
                    'author': metadata.get('author', 'RAPP'),
                    'path': str(metadata_file.parent.relative_to(base_path))
                })

    # Generate manifest
    manifest = {
        'version': '2.0',
        'generated': datetime.now().isoformat(),
        'totalAgents': len(agents),
        'agents': agents
    }

    # Write to file
    with open('manifest.json', 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"✅ Generated manifest with {len(agents)} agents")

if __name__ == '__main__':
    generate_manifest()
```

**Workflow:**
1. Developer adds new agent stack with `metadata.json`
2. Run `python update_manifest.py` to regenerate manifest
3. Commit both the agent files AND the updated manifest.json
4. GitHub Pages automatically serves the updated manifest

## Why Not Embed Data in HTML?

### ❌ Embedding Data (What We DON'T Do)

```javascript
// DON'T: Embed large arrays in HTML
const sampleAgents = [
  { id: 'agent1', name: 'Agent 1', ... },
  { id: 'agent2', name: 'Agent 2', ... },
  // ... 78+ agents embedded = 50KB+ of JavaScript
];
```

**Problems:**
- HTML file becomes massive (100KB+)
- Every page load downloads all data
- Hard to maintain (manual updates required)
- Git diffs become huge and unreadable
- Cache invalidation issues

### ✅ Dynamic Loading (What We DO)

```javascript
// DO: Load data dynamically from external source
async loadAgents() {
  const manifestUrl = `https://raw.githubusercontent.com/${GITHUB_REPO}/${BRANCH}/manifest.json`;
  const response = await fetch(manifestUrl);
  const manifest = await response.json();
  this.agents = manifest.agents;
}
```

**Benefits:**
- ✅ HTML stays lean (~50KB vs 150KB+)
- ✅ Data cached separately (better performance)
- ✅ Easy to update (regenerate manifest)
- ✅ Clean git diffs
- ✅ Scales to hundreds of agents

## Current State Analysis

### AI-Agent-Templates/index.html
✅ **Correct pattern** - No embedded data, loads from manifest.json

### RAPP/agent_store.html
❌ **Anti-pattern** - Has embedded `sampleAgents` array with 78 agents

**Lines 901-1916** contain hardcoded agent data:
```javascript
const sampleAgents = [
  {
    id: 'permit-license-management',
    name: 'Permit & License Management Agent Stack',
    category: 'Energy',
    // ... 78 more agents embedded
  },
  // ...
];
```

## Recommended Fix for agent_store.html

### Option 1: Use Manifest Pattern (Recommended)

1. **Generate manifest.json** from your agent stacks:
   ```bash
   python tools/generate_agent_catalog.py --output manifest.json
   ```

2. **Update agent_store.html** to load from manifest:
   ```javascript
   async loadAgentCatalog() {
     try {
       const manifestUrl = `https://raw.githubusercontent.com/${GITHUB_CONFIG.owner}/${GITHUB_CONFIG.repo}/${GITHUB_CONFIG.branch}/manifest.json`;
       const response = await fetch(manifestUrl);
       const manifest = await response.json();
       agents = manifest.agents;
       console.log(`✅ Loaded ${agents.length} agents from manifest`);
     } catch (error) {
       console.error('Failed to load manifest:', error);
       // Optional: fallback to embedded data
       agents = sampleAgents;
     }
   }
   ```

3. **Remove embedded sampleAgents array** (or keep as fallback)

### Option 2: Keep Embedded Data as Fallback Only

If you want offline capability:

```javascript
// Minimal fallback data (just structure, no full list)
const fallbackAgents = [
  { id: 'sample', name: 'Loading...', category: 'General', shortDescription: 'Loading agents from GitHub...' }
];

async loadAgentCatalog() {
  // Show loading state with fallback
  agents = fallbackAgents;
  renderAgents();

  try {
    // Load from manifest
    const response = await fetch('manifest.json');
    const manifest = await response.json();
    agents = manifest.agents;
  } catch (error) {
    // If manifest fails, load full embedded data
    agents = await import('./agent_catalog_fallback.js').then(m => m.sampleAgents);
  }

  renderAgents();
}
```

## GitHub Pages Deployment

### Files Committed to Repo

```
RAPP/
├── agent_store.html          # Lean HTML (~50KB)
├── manifest.json             # Generated agent catalog (~20KB)
├── AI-Agent-Templates/       # Agent source code
│   └── agent_stacks/         # All agent implementations
├── generate_agent_catalog.py # Manifest generator
└── .github/
    └── workflows/
        └── update-manifest.yml # Auto-generate on push
```

### Automated Manifest Generation (Optional)

Create `.github/workflows/update-manifest.yml`:

```yaml
name: Update Agent Manifest

on:
  push:
    paths:
      - 'AI-Agent-Templates/agent_stacks/**'
      - 'generate_agent_catalog.py'

jobs:
  update-manifest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Generate Manifest
        run: |
          python tools/generate_agent_catalog.py --output manifest.json

      - name: Commit Manifest
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add manifest.json
          git commit -m "chore: auto-update agent manifest" || exit 0
          git push
```

**Benefits:**
- Manifest automatically updates when agents change
- No manual intervention required
- Always stays in sync with agent stacks

## Summary

| Aspect | Embedded Data | Manifest Pattern |
|--------|---------------|------------------|
| HTML Size | ❌ Large (150KB+) | ✅ Small (50KB) |
| Load Speed | ❌ Slower | ✅ Faster (cached) |
| Maintenance | ❌ Manual | ✅ Automated |
| Git Diffs | ❌ Huge | ✅ Clean |
| Scalability | ❌ Limited | ✅ Unlimited |
| Offline Support | ✅ Works offline | ⚠️ Needs fallback |

## Best Practice

**For RAPP agent_store.html:**

1. Generate `manifest.json` from agent metadata
2. Load from manifest.json as primary source
3. Keep minimal embedded fallback for offline scenarios
4. Automate manifest generation in CI/CD
5. Deploy both HTML and manifest to GitHub Pages

This pattern allows GitHub Pages to serve a dynamic, scalable agent marketplace without bloating the HTML file or requiring a backend server.
