# Credential Configuration Reference

Quick reference for all credential configuration options and formats.

## Configuration Locations

### Browser Storage (Default)
**File**: None (stored in browser localStorage)
**Key**: `shared-ai-config`
**Scope**: Per browser, shared across all apps
**Persistence**: Until cache cleared

### Environment Variables
**File**: None (system environment)
**Example**:
```bash
export AZURE_FUNCTION_KEY="your-key"
export AZURE_TEXT_TO_SPEECH_KEY="your-key"
```

### .env File
**File**: `localFirstTools/.env`
**Example**:
```
AZURE_FUNCTION_KEY=your-key
AZURE_TEXT_TO_SPEECH_KEY=your-key
```
**Important**: Add `.env` to `.gitignore`

### Configuration File
**File**: `localFirstTools/data/config/utility_apps_config.json`
**Scope**: Global application configuration
**Note**: Use `.env` or environment variables instead

## Credential Fields Reference

### Azure Function Key
| Property | Value |
|----------|-------|
| **Name** | `functionKey` or `AZURE_FUNCTION_KEY` |
| **Type** | String |
| **Length** | ~88 characters |
| **Format** | Base64-like string |
| **Example** | `IzSz9vX0pQ1m...==` |
| **Source** | Azure Portal > Function App > Function Keys |
| **Scope** | Function App access |
| **TTL** | Indefinite until regenerated |

### Azure TTS Key
| Property | Value |
|----------|-------|
| **Name** | `azureTTSKey` or `AZURE_TEXT_TO_SPEECH_KEY` |
| **Type** | String |
| **Length** | ~32 characters |
| **Format** | Hex/alphanumeric |
| **Example** | `a1b2c3d4e5f6g7h8...` |
| **Source** | Azure Portal > Cognitive Services > Keys |
| **Scope** | Text-to-Speech API access |
| **TTL** | Indefinite until regenerated |

### Application GUID
| Property | Value |
|----------|-------|
| **Name** | `guid` or `defaultGuid` |
| **Type** | String (UUID format) |
| **Length** | 36 characters |
| **Format** | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| **Example** | `c0p110t0-aaaa-bbbb-cccc-123456789abc` |
| **Source** | Application assigned or user-defined |
| **Scope** | User context tracking |
| **TTL** | Indefinite (user-specific) |

## JSON Configuration Format

### Minimal Configuration
```json
{
  "endpoints": {
    "prod": {
      "name": "Production",
      "url": "https://example.azurewebsites.net/api/function",
      "key": "YOUR_FUNCTION_KEY_HERE",
      "active": true
    }
  }
}
```

### Full Configuration
```json
{
  "_schema": "ai-config-v1",
  "endpoints": {
    "prod": {
      "id": "prod",
      "name": "Production Bot",
      "url": "https://azfbusinessbot.azurewebsites.net/api/businessinsightbot_function",
      "key": "YOUR_FUNCTION_KEY_HERE",
      "guid": "c0p110t0-aaaa-bbbb-cccc-123456789abc",
      "active": true,
      "provider": "azure"
    },
    "dev": {
      "id": "dev",
      "name": "Development Bot",
      "url": "http://localhost:7071/api/businessinsightbot_function",
      "key": "",
      "guid": "dev-user-guid",
      "active": false,
      "provider": "local"
    }
  },
  "speech": {
    "azureTTSKey": "YOUR_AZURE_TEXT_TO_SPEECH_KEY_HERE",
    "azureTTSRegion": "eastus",
    "ttsVoiceName": "en-US-JennyNeural",
    "ttsProvider": "azure",
    "speechRecognitionLang": "en-US",
    "enableSpeech": true
  },
  "llm": {
    "provider": "azure",
    "model": "gpt-4",
    "temperature": 0.7,
    "maxTokens": 2000,
    "systemPrompt": "You are a helpful assistant."
  },
  "apiKeys": {
    "openai": "",
    "anthropic": "",
    "azure": "YOUR_FUNCTION_KEY_HERE",
    "google": ""
  },
  "preferences": {
    "theme": "dark",
    "autoSave": true,
    "voiceEnabled": true,
    "notifications": true
  },
  "metadata": {
    "version": "1.0.0",
    "exportDate": "2025-11-23T00:00:00.000Z",
    "appName": "business-insights-bot"
  }
}
```

## .env File Format

```env
# Azure Function Configuration
AZURE_FUNCTION_ENDPOINT=https://azfbusinessbot.azurewebsites.net/api/businessinsightbot_function
AZURE_FUNCTION_KEY=YOUR_AZURE_FUNCTION_KEY_HERE

# Azure Text-to-Speech Configuration
AZURE_TEXT_TO_SPEECH_KEY=YOUR_AZURE_TEXT_TO_SPEECH_KEY_HERE
AZURE_TEXT_TO_SPEECH_REGION=eastus

# Application Settings
APP_GUID=c0p110t0-aaaa-bbbb-cccc-123456789abc
APP_NAME=AplAI
APP_VERSION=2.0.0

# Optional: Other AI Provider Keys
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=

# Speech Configuration
TTS_VOICE_NAME=en-US-JennyNeural
SPEECH_RECOGNITION_LANGUAGE=en-US
SPEECH_ENABLED=true

# LLM Configuration
LLM_PROVIDER=azure
LLM_MODEL=gpt-4
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000

# User Preferences
THEME=dark
AUTO_SAVE=true
NOTIFICATIONS=true
VOICE_ENABLED=true

# Development Settings
DEBUG_MODE=false
LOG_LEVEL=info
```

## Environment Variables (Node.js/JavaScript)

### Reading from .env
```javascript
require('dotenv').config();

const config = {
  functionKey: process.env.AZURE_FUNCTION_KEY,
  ttsSpeechKey: process.env.AZURE_TEXT_TO_SPEECH_KEY,
  region: process.env.AZURE_TEXT_TO_SPEECH_REGION,
  model: process.env.LLM_MODEL
};
```

### Reading from System Environment
```javascript
const config = {
  functionKey: process.env.AZURE_FUNCTION_KEY || 'YOUR_AZURE_FUNCTION_KEY_HERE',
  ttsSpeechKey: process.env.AZURE_TEXT_TO_SPEECH_KEY || 'YOUR_AZURE_TEXT_TO_SPEECH_KEY_HERE'
};
```

### In Browser (Client-side)
Note: Never expose secrets in client-side code. Use localStorage or a secure backend instead.

```javascript
// Load from localStorage
const configString = localStorage.getItem('shared-ai-config');
const config = JSON.parse(configString);
const activeEndpoint = Object.values(config.endpoints).find(e => e.active);
```

## Configuration Methods Comparison

| Method | Security | Sharing | Setup | Production |
|--------|----------|---------|-------|------------|
| **Config Hub (localStorage)** | Medium | Easy | 1 min | No |
| **.env file** | High | File | 2 min | No |
| **Environment variables** | High | Script | 2 min | Yes |
| **Azure Key Vault** | Very High | Portal | 10 min | Yes |
| **GitHub Secrets** | High | CI/CD | 3 min | Yes (CI/CD) |

## Setting Up Each Method

### Method 1: Config Hub (Easiest)
```
1. Open ai-config-hub.html
2. Click "➕ Add Endpoint"
3. Enter your credentials
4. Click "Activate"
5. Configuration saved to browser localStorage
```

### Method 2: .env File
```bash
1. Copy .env.example to .env
2. Edit .env with your credentials
3. Add .env to .gitignore
4. Load in your app: require('dotenv').config()
```

### Method 3: Export/Import JSON
```
1. In Config Hub, click "📤 Export Configuration"
2. Share JSON file with team
3. Team members click "📥 Import Configuration"
4. Enter their credentials
5. Configuration imported and activated
```

### Method 4: Environment Variables
```bash
# Linux/Mac
export AZURE_FUNCTION_KEY="your-key"
export AZURE_TEXT_TO_SPEECH_KEY="your-key"

# Windows PowerShell
[Environment]::SetEnvironmentVariable("AZURE_FUNCTION_KEY", "your-key", "User")
```

## Placeholder Values Reference

| Original | Placeholder | Length | Type |
|----------|------------|--------|------|
| Azure Function Key | `YOUR_AZURE_FUNCTION_KEY_HERE` | Variable | Placeholder |
| Azure TTS Key | `YOUR_AZURE_TEXT_TO_SPEECH_KEY_HERE` | Variable | Placeholder |
| Generic API Key | `YOUR_AZURE_FUNCTION_KEY_HERE` | Variable | Placeholder |

## Verification Checklist

Before deploying or sharing:

- [ ] All `YOUR_*_HERE` placeholders contain real values
- [ ] API keys are not in version control (except .env.example)
- [ ] .env file is in .gitignore
- [ ] Credentials are not hardcoded in application files
- [ ] Environment variables are set correctly
- [ ] Test connection succeeds in Config Hub
- [ ] Chat/Voice apps return expected responses
- [ ] No sensitive data in commit messages

## Common Configuration Issues

### Issue: "401 Unauthorized"
**Cause**: Invalid or expired API key
**Solution**:
1. Verify key in Azure Portal
2. Regenerate key if needed
3. Update configuration with new key
4. Test connection

### Issue: "Connection Failed"
**Cause**: Wrong endpoint URL or network issue
**Solution**:
1. Verify URL matches Azure Function
2. Check internet connectivity
3. Test URL with curl/Postman first
4. Check Azure Portal app is running

### Issue: "Configuration Not Found"
**Cause**: localStorage cleared or wrong storage method
**Solution**:
1. Reconfigure in Config Hub
2. Or set environment variables
3. Or create .env file

### Issue: "Key Not Active"
**Cause**: Endpoint not marked as active
**Solution**:
1. Open Config Hub
2. Click on endpoint
3. Click "Activate"
4. Verify checkmark appears

## Security Best Practices

### DO
- ✅ Use strong, unique keys
- ✅ Rotate keys regularly (90 days)
- ✅ Different keys per environment
- ✅ Store in secure vaults for production
- ✅ Use environment variables
- ✅ Enable Azure alerts
- ✅ Audit key usage
- ✅ Use managed identities when possible

### DON'T
- ❌ Commit credentials to git
- ❌ Share keys in Slack/email
- ❌ Reuse keys across environments
- ❌ Hardcode in application files
- ❌ Log or display keys
- ❌ Use weak or predictable names
- ❌ Leave old keys active
- ❌ Share with external parties

## Azure Portal Navigation Quick Links

**Get Function Key**:
Azure Portal → Function App → Functions → [Function Name] → Function Keys → Copy

**Get TTS Key**:
Azure Portal → Cognitive Services → Text to Speech → Keys and Endpoint → Copy Key 1 or 2

**Get Region**:
Azure Portal → Cognitive Services → Text to Speech → Keys and Endpoint → Region dropdown

**Monitor Usage**:
Azure Portal → Resource → Monitoring → Metrics → API Calls

**Set Alerts**:
Azure Portal → Resource → Alerts → New Alert Rule → Configure conditions

## Testing Your Configuration

### Test Connection
```javascript
fetch(endpoint.url, {
  method: 'POST',
  headers: {
    'x-functions-key': endpoint.key,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    user_input: 'Test message',
    conversation_history: []
  })
}).then(r => r.json()).then(data => console.log(data));
```

### Test TTS
```javascript
const synth = window.speechSynthesis;
const utterance = new SpeechSynthesisUtterance('Hello world');
synth.speak(utterance);
```

### Using Config Hub
1. Open ai-config-hub.html
2. Click ⚙️ Config
3. Click 🧪 Test Connection
4. Should show ✅ Connected

## Support Resources

- **Quick Start**: See CREDENTIALS-QUICKSTART.md
- **Security Guide**: See SECURITY-CREDENTIALS.md
- **Configuration Template**: See .env.example
- **Technical Details**: See PII_SCRUBBING_REPORT.md

---

**Last Updated**: November 23, 2025
**Version**: 1.0.0
**Status**: All API keys secured and documented
