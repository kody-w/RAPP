# Agent Manager - Quick Start Guide

## 🚀 5-Minute Setup

### Step 1: Start the Function App

```bash
# Mac/Linux
./run.sh

# Windows
./run.ps1
```

Wait for the message: `Function app started successfully`

### Step 2: Open Agent Manager

Open your browser and navigate to:
```
http://localhost:7071/agent_manager.html
```

### Step 3: Select Agents

You'll see all available agents displayed as cards. Click on any agent card to enable/disable it.

**Quick Actions:**
- Click "✅ Select All" to enable all agents
- Click "❌ Deselect All" to disable all agents
- Click individual cards to toggle specific agents

### Step 4: Save Configuration

Click the **"💾 Save Configuration"** button to persist your changes.

Your configuration is now saved to Azure Storage and will be used for the current user GUID.

---

## 📋 Common Tasks

### Use a Preset Configuration

1. Look at the **Presets** section in the left sidebar
2. Click on any preset (e.g., "🛒 Customer Service")
3. The agents and settings will automatically update
4. Click "💾 Save Configuration" to persist

### Configure for a Different User

1. Enter a different GUID in the **User Context** input field at the top of the sidebar
2. Press Enter or click outside the field
3. The configuration for that user will load automatically
4. Make your changes and save

### Preview Agent Metadata

1. Click the **"Metadata Preview"** tab
2. You'll see the exact JSON metadata that will be sent to OpenAI
3. Click **"📋 Copy to Clipboard"** to copy the metadata

### Adjust Settings

1. Click the **"Settings"** tab
2. Configure options like:
   - Assistant Name
   - Business Type
   - Enable/Disable Upselling
   - Custom Instructions
3. Click **"💾 Save Settings"**

### View Statistics

1. Click the **"Statistics"** tab
2. See metrics like:
   - Total agents available
   - Currently selected agents
   - Number of presets
   - Category breakdown

---

## 🎯 Example Use Cases

### Customer Service Setup (1 minute)

**Scenario:** You're setting up a customer service bot for a fast food restaurant.

1. Click the **"🛒 Customer Service"** preset
2. Go to **"Settings"** tab
3. Set **Business Type** to "Fast Food"
4. Set **Enable Upselling** to "Yes"
5. Click **"💾 Save Settings"**
6. Click **"💾 Save Configuration"**

**Result:** Your bot now has memory, order verification, and upselling enabled!

### Analytics-Only Setup (30 seconds)

**Scenario:** You need a bot that only analyzes contracts and documents.

1. Click the **"📊 Analytics Suite"** preset
2. Click **"💾 Save Configuration"**

**Result:** Only contract analysis and prompt playground agents are enabled.

### Multi-User Testing (2 minutes)

**Scenario:** You want different configurations for testing vs. production.

**Testing User:**
1. Enter GUID: `test-user-guid`
2. Click "✅ Select All" to enable all agents
3. Save configuration

**Production User:**
1. Enter GUID: `prod-user-guid`
2. Click "🛒 Customer Service" preset
3. Save configuration

**Result:** You now have two separate configurations for different environments!

---

## 🔍 Understanding the Interface

### Sidebar (Left)

- **User Context**: Enter a user GUID to load/save configurations for that user
- **Presets**: Quick-access templates for common agent combinations

### Main Area (Right)

**Agents Tab:**
- Grid of all available agents
- Click cards to select/deselect
- Action buttons for bulk operations

**Metadata Preview Tab:**
- Shows OpenAI function metadata in JSON format
- Copy button for easy export

**Settings Tab:**
- Configure agent-specific settings
- Business type, upselling, custom instructions

**Statistics Tab:**
- Real-time metrics
- Agent counts and category breakdown

---

## 💡 Pro Tips

### 1. Test Before Saving

Select different agents and switch between tabs to see how the metadata changes before saving.

### 2. Use Presets as Starting Points

Click a preset to load a template, then customize by adding/removing specific agents.

### 3. Keep User GUIDs Organized

Use descriptive GUIDs for different purposes:
- `customer-service-team`
- `analytics-department`
- `demo-environment`
- `production-main`

### 4. Monitor Statistics

Check the Statistics tab regularly to ensure the right number of agents are enabled.

### 5. Copy Metadata for Documentation

Use the Metadata Preview tab to generate documentation about what your bot can do.

---

## 🐛 Troubleshooting

### "No agents available" message

**Fix:** Make sure the Azure Function is running (`./run.sh` or `./run.ps1`)

### Configuration doesn't save

**Fix:** Check that `local.settings.json` has a valid `AzureWebJobsStorage` connection string

### Preset doesn't apply

**Fix:** Refresh the page and try again. Ensure you have the latest presets loaded.

### Can't see metadata

**Fix:** Select at least one agent, then click the "🔄 Refresh Preview" button

---

## 📞 Next Steps

### Test Your Configuration

After saving, test your configuration by making a request to the main bot:

```bash
curl -X POST http://localhost:7071/api/businessinsightbot_function \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "Hello",
    "conversation_history": [],
    "user_guid": "your-user-guid-here"
  }'
```

### Create Custom Presets

Use the API to create your own presets:

```bash
curl -X POST "http://localhost:7071/api/agent_manager?action=save_preset" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Custom Setup",
    "description": "My specialized agent combination",
    "agents": ["context_memory_agent.py", "order_verification_agent.py"],
    "settings": {"enable_upsell": true}
  }'
```

### Learn More

- Read the full **AGENT_MANAGER_README.md** for advanced features
- Check **CLAUDE.md** for the overall project documentation
- Explore the API endpoints for programmatic control

---

## 🎉 You're Done!

You now have a fully configured agent management system. Start experimenting with different combinations to find what works best for your use case!

**Remember:**
- Configurations are per-user (GUID)
- Changes aren't applied until you click Save
- Presets are a great starting point
- You can always click "🔄 Reload" to revert unsaved changes

Happy agent managing! 🚀
