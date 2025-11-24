# AI Configuration Manager

A standardized configuration system for all AI-enabled applications in the localFirstTools project.

## Overview

The AI Configuration Manager provides a unified way to manage API endpoints, TTS settings, LLM configurations, and API keys across all AI-enabled applications. It includes built-in import/export functionality for easy settings portability.

## Features

- **Multiple Endpoint Management**: Store and switch between different API endpoints
- **Speech Settings**: Configure Azure TTS, voice names, and speech recognition
- **LLM Configuration**: Model settings, temperature, max tokens, system prompts
- **API Key Storage**: Securely store keys for OpenAI, Anthropic, Azure, Google
- **Import/Export**: JSON-based configuration portability
- **Local Storage**: All settings persist in browser localStorage
- **Schema Validation**: Ensures configuration integrity

## Quick Start

### 1. Include the Manager in Your HTML App

Copy the entire content of `ai-config-manager.js` into your HTML file's `<script>` tag:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>My AI App</title>
</head>
<body>
    <!-- Your app UI -->
    <div id="ai-config-controls"></div>

    <script>
        // Paste the entire AIConfigManager class here
        class AIConfigManager {
            // ... (full code from ai-config-manager.js)
        }

        // Initialize
        const aiConfig = new AIConfigManager('my-app-name');
        window.aiConfigManager = aiConfig;

        // Create UI buttons
        createAIConfigUI(aiConfig, 'ai-config-controls');

        // Use the configuration
        const activeEndpoint = aiConfig.getActiveEndpoint();
        if (activeEndpoint) {
            console.log('API URL:', activeEndpoint.url);
            console.log('API Key:', activeEndpoint.key);
        }
    </script>
</body>
</html>
```

### 2. Basic Usage

```javascript
// Initialize the config manager
const aiConfig = new AIConfigManager('my-app-name');

// Get active endpoint
const endpoint = aiConfig.getActiveEndpoint();
if (endpoint) {
    fetch(endpoint.url, {
        headers: {
            'Authorization': `Bearer ${endpoint.key}`,
            'x-guid': endpoint.guid
        }
    });
}

// Get speech settings
const speech = aiConfig.getSpeechSettings();
console.log(speech.ttsVoiceName); // "en-US-JennyNeural"

// Get LLM settings
const llm = aiConfig.getLLMSettings();
console.log(llm.model); // "gpt-4"
console.log(llm.temperature); // 0.7
```

### 3. Managing Endpoints

```javascript
// Add a new endpoint
aiConfig.addEndpoint({
    name: 'Production Bot',
    url: 'https://api.example.com/bot',
    key: 'your-api-key',
    guid: 'your-guid',
    active: true,
    provider: 'azure'
});

// Set active endpoint
aiConfig.setActiveEndpoint('endpoint-id');

// Get all endpoints
const endpoints = aiConfig.getAllEndpoints();

// Remove endpoint
aiConfig.removeEndpoint('endpoint-id');
```

### 4. Update Settings

```javascript
// Update speech settings
aiConfig.updateSpeechSettings({
    ttsVoiceName: 'en-US-AriaNeural',
    enableSpeech: true
});

// Update LLM settings
aiConfig.updateLLMSettings({
    model: 'gpt-4-turbo',
    temperature: 0.8,
    maxTokens: 4000
});

// Set API keys
aiConfig.setAPIKey('openai', 'sk-...');
aiConfig.setAPIKey('anthropic', 'claude-...');

// Update preferences
aiConfig.updatePreferences({
    theme: 'dark',
    voiceEnabled: true
});
```

### 5. Import/Export

The manager automatically creates export/import buttons when you call `createAIConfigUI()`:

```javascript
// Create UI controls in a container
createAIConfigUI(aiConfig, 'settings-container');
```

Or programmatically:

```javascript
// Export configuration
aiConfig.exportConfig(); // Downloads JSON file

// Import from file event
aiConfig.importFromFile(fileInputEvent)
    .then(() => location.reload())
    .catch(error => console.error(error));

// Import from JSON data
aiConfig.importConfig(jsonData);
```

## Configuration Schema

```json
{
  "_schema": "ai-config-v1",
  "_description": "Standardized AI configuration for localFirstTools applications",

  "endpoints": {
    "endpoint-id": {
      "id": "endpoint-id",
      "name": "Production Bot",
      "url": "https://api.example.com/bot",
      "key": "api-key-here",
      "guid": "guid-here",
      "active": true,
      "provider": "azure|openai|custom"
    }
  },

  "speech": {
    "azureTTSKey": "your-azure-tts-key",
    "azureTTSRegion": "eastus",
    "ttsVoiceName": "en-US-JennyNeural",
    "ttsProvider": "azure|web-speech",
    "speechRecognitionLang": "en-US",
    "enableSpeech": true
  },

  "llm": {
    "provider": "openai|anthropic|azure|custom",
    "model": "gpt-4",
    "temperature": 0.7,
    "maxTokens": 2000,
    "systemPrompt": "You are a helpful assistant"
  },

  "apiKeys": {
    "openai": "sk-...",
    "anthropic": "claude-...",
    "azure": "azure-key",
    "google": "google-key"
  },

  "preferences": {
    "theme": "dark|light",
    "autoSave": true,
    "voiceEnabled": true,
    "notifications": true
  },

  "metadata": {
    "exportDate": "2025-11-24T01:53:48.362Z",
    "version": "1.0.0",
    "appName": "my-app",
    "lastModified": "2025-11-24T01:53:48.362Z"
  }
}
```

## Complete Example App

See `apps/utilities/ai-config-demo.html` for a complete working example.

## Migration Guide

### Migrating Existing Apps

If you have an existing AI app with custom configuration:

1. **Identify your current config structure**
2. **Initialize AIConfigManager**
3. **Migrate your data**:

```javascript
// Old way
const oldConfig = JSON.parse(localStorage.getItem('old-config'));

// New way - initialize manager
const aiConfig = new AIConfigManager('my-app');

// Migrate endpoints
if (oldConfig.endpoints) {
    Object.values(oldConfig.endpoints).forEach(ep => {
        aiConfig.addEndpoint(ep);
    });
}

// Migrate speech settings
if (oldConfig.azureTTSKey) {
    aiConfig.updateSpeechSettings({
        azureTTSKey: oldConfig.azureTTSKey,
        ttsVoiceName: oldConfig.ttsVoiceName
    });
}

// Save
aiConfig.saveConfig();
```

## Best Practices

1. **Initialize Once**: Create one AIConfigManager instance per app
2. **Global Access**: Assign to `window.aiConfigManager` for global access
3. **Validate Endpoints**: Always check if an active endpoint exists before API calls
4. **Handle Errors**: Wrap API calls in try-catch blocks
5. **Security**: Never commit files with real API keys
6. **User Guidance**: Provide clear UI for endpoint configuration

## API Reference

### Constructor
- `new AIConfigManager(appName)` - Creates a new config manager instance

### Endpoints
- `addEndpoint(endpoint)` - Add or update an endpoint
- `removeEndpoint(endpointId)` - Remove an endpoint
- `setActiveEndpoint(endpointId)` - Set the active endpoint
- `getActiveEndpoint()` - Get the currently active endpoint
- `getAllEndpoints()` - Get all endpoints

### Settings
- `updateSpeechSettings(settings)` - Update speech configuration
- `getSpeechSettings()` - Get speech settings
- `updateLLMSettings(settings)` - Update LLM configuration
- `getLLMSettings()` - Get LLM settings
- `setAPIKey(provider, key)` - Set an API key
- `getAPIKey(provider)` - Get an API key
- `updatePreferences(prefs)` - Update user preferences
- `getPreferences()` - Get preferences

### Data Management
- `exportConfig()` - Export configuration as JSON file
- `importConfig(jsonData)` - Import configuration from JSON
- `importFromFile(event)` - Import from file input event
- `saveConfig()` - Save to localStorage
- `resetToDefaults()` - Reset to default configuration
- `getConfig()` - Get full configuration object

### UI Helpers
- `createAIConfigUI(aiConfig, containerId)` - Create import/export buttons

## Support

For issues or questions, check the main project README or create an issue in the GitHub repository.
