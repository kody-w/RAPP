# Credentials Quick Start Guide

This is a quick reference for getting the AI tools up and running with your Azure credentials.

## 30-Second Setup

### Step 1: Get Your API Key
1. Go to https://portal.azure.com
2. Find your Function App
3. Click "Functions" → "businessinsightbot_function"
4. Click "Code + Test"
5. Click "Get Function URL" and copy the key

### Step 2: Open AI Config Hub
Open: `/apps/ai-tools/ai-config-hub.html`

### Step 3: Add Your Endpoint
1. Click "➕ Add Endpoint"
2. Name: "My Bot"
3. URL: `https://azfbusinessbot.azurewebsites.net/api/businessinsightbot_function`
4. Key: Paste your API key
5. Click "Activate"

### Step 4: Launch Apps
- Click "💬 Chat" or any other app
- It will now use your configuration

Done! Your configuration is saved in browser localStorage and shared across all apps.

## How to Get Each Credential

### Azure Function Key
**Portal Path**: Azure Portal > Function App > Functions > Function Keys
- Format: Long alphanumeric string
- Used by: All AI apps to call your Azure Function
- Where to put it: API Key field in Config Hub

### Azure TTS Key (Optional, for voice)
**Portal Path**: Azure Portal > Cognitive Services > Text to Speech > Keys
- Format: Long alphanumeric string
- Used by: Voice Hello World, AplAI Voice apps
- Where to put it: Settings → Configure Settings in Config Hub

### Application GUID
**Default**: `c0p110t0-aaaa-bbbb-cccc-123456789abc`
- Used to identify your user context
- You can use the default or create your own UUID
- Format: Standard UUID (8-4-4-4-12 characters)

## Three Ways to Configure

### Option 1: Browser Storage (Easiest for Development)
1. Open `ai-config-hub.html`
2. Add endpoint with your credentials
3. Click "Activate"
4. Configuration saved in browser localStorage
5. Works across all apps in the same browser

**Pros**: No files to manage, apps instantly share settings
**Cons**: Per-browser, lost if you clear cache

### Option 2: .env File (Best for Local Development)
1. Copy `.env.example` to `.env`
2. Fill in your actual credentials
3. Your app code reads from environment:
   ```javascript
   const key = process.env.AZURE_FUNCTION_KEY;
   ```

**Pros**: Version control safe (add .env to .gitignore), standardized format
**Cons**: Requires server/Node.js to read

### Option 3: Environment Variables (Production)
```bash
export AZURE_FUNCTION_KEY="your-actual-key"
export AZURE_TEXT_TO_SPEECH_KEY="your-tts-key"
```

Then in your code:
```javascript
const CONFIG = {
    functionKey: process.env.AZURE_FUNCTION_KEY,
    azureTTSKey: process.env.AZURE_TEXT_TO_SPEECH_KEY
};
```

**Pros**: Secure for production, works with CI/CD
**Cons**: Requires environment setup

## Verify Your Configuration Works

### Using Config Hub
1. Open `ai-config-hub.html`
2. Click "⚙️ Config"
3. Click "🧪 Test Connection"
4. Should show "✅ Connected successfully"

### Using Chat App
1. Open `ai-chat-hello-world.html`
2. Type a message
3. Should get a response from your Azure Function

### Using Voice App
1. Open `ai-voice-hello-world.html`
2. Click the microphone button
3. Speak your question
4. Should hear response

## Troubleshooting Quick Fixes

### "401 Unauthorized"
- ❌ Wrong API key
- ✅ Copy the key again from Azure Portal
- ✅ Make sure you have the full key (no truncation)

### "Connection Failed"
- ❌ Key not activated in Config Hub
- ✅ Open Config Hub and click "Activate" on your endpoint
- ✅ Check your internet connection

### "Invalid JSON"
- ❌ Configuration format is wrong
- ✅ Use Config Hub to create endpoint (handles formatting)
- ✅ Don't edit JSON manually

### "No Response"
- ❌ Function app might be paused
- ✅ Check Azure Portal that Function App is running
- ✅ Try the test connection in Config Hub

## Example Configurations

### Minimal Configuration (Just the Function)
```json
{
  "endpoints": {
    "prod": {
      "name": "My Bot",
      "url": "https://azfbusinessbot.azurewebsites.net/api/businessinsightbot_function",
      "key": "YOUR_KEY_HERE",
      "active": true
    }
  }
}
```

### Full Configuration (With Voice)
```json
{
  "endpoints": {
    "prod": {
      "name": "My Bot",
      "url": "https://azfbusinessbot.azurewebsites.net/api/businessinsightbot_function",
      "key": "YOUR_FUNCTION_KEY_HERE",
      "active": true
    }
  },
  "speech": {
    "azureTTSKey": "YOUR_TTS_KEY_HERE",
    "azureTTSRegion": "eastus",
    "ttsVoiceName": "en-US-JennyNeural"
  }
}
```

## Using Multiple Endpoints

You can configure multiple Azure Functions and switch between them:

1. Open Config Hub
2. Click "➕ Add Endpoint" for each Azure Function
3. Fill in name and key for each
4. Only one can be "active" at a time
5. Click any endpoint to make it active
6. All apps instantly switch to using that endpoint

## Sharing Configuration with Team

### Export Your Configuration
1. Open Config Hub
2. Click "📤 Export Configuration"
3. Downloads a JSON file
4. Share with team (safe - credentials needed anyway)

### Team Member Imports
1. Receive configuration JSON file
2. Open Config Hub
3. Click "📥 Import Configuration"
4. Select the JSON file
5. Prompts to enter actual credentials
6. Team member adds their own keys

## Advanced: Custom Applications

Create your own app that uses shared configuration:

```html
<script>
  // Load shared config from localStorage
  const configString = localStorage.getItem('shared-ai-config');
  const config = JSON.parse(configString);

  // Get active endpoint
  const activeEndpoint = Object.values(config.endpoints)
    .find(e => e.active);

  // Use it to call your API
  fetch(activeEndpoint.url, {
    method: 'POST',
    headers: {
      'x-functions-key': activeEndpoint.key,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ user_input: 'Hello' })
  });
</script>
```

## Need Help?

- **Getting Keys**: See `/localFirstTools/SECURITY-CREDENTIALS.md`
- **Detailed Setup**: See `/localFirstTools/SECURITY-CREDENTIALS.md`
- **Troubleshooting**: See `/localFirstTools/SECURITY-CREDENTIALS.md`
- **Report Issues**: GitHub Issues on this repository

---

**Status**: All API keys removed and secured
**Files to Edit**: Just the credentials in Config Hub
**No Code Changes Needed**: Apps work with configuration alone
