# Security Configuration Guide

This document explains how to properly configure API keys and credentials for the localFirstTools applications.

## Important Security Notes

**NEVER commit secrets to version control!**

- All API keys and secrets have been replaced with placeholder values: `YOUR_[SERVICE]_KEY_HERE`
- A `.env.example` file has been provided as a template
- Use environment variables or secure configuration management for actual credentials
- GitHub will flag any real API keys committed to the repository

## Files That Contain Configuration Placeholders

The following files have been sanitized and now contain placeholder credentials:

1. **localFirstTools/apps/ai-tools/AI-HELLO-WORLD-README.md** (line 81, 64)
   - Azure TTS Key placeholder
   - Azure Function Key placeholder

2. **localFirstTools/apps/ai-tools/ai-token-quick-start.html** (lines 392, 399)
   - Azure Function Key placeholder
   - Azure Text-to-Speech Key placeholder

3. **localFirstTools/data/config/ai-config-example.json** (lines 18, 25, 42)
   - Production Bot API Key
   - Azure TTS Key
   - Generic Azure API Key

4. **localFirstTools/apps/ai-tools/apl2ai-watch-app.html** (line 439)
   - Azure Function Key placeholder

5. **localFirstTools/apps/ai-tools/aplai-direct-app.html** (line 923)
   - Azure Function Key placeholder

6. **localFirstTools/apps/ai-tools/aplai-unified-app.html** (line 869)
   - Azure Function Key placeholder

7. **localFirstTools/chrome-extension-build/apps/ai-tools/apl2ai-watch-app.html** (line 439)
   - Azure Function Key placeholder

8. **localFirstTools/chrome-extension-build/apps/ai-tools/aplai-unified-app.html** (line 869)
   - Azure Function Key placeholder

## Getting Your Credentials

### Azure Function Key

1. Go to **Azure Portal** (https://portal.azure.com)
2. Navigate to your **Function App**
3. Select **Functions** in the left sidebar
4. Click on your function (e.g., `businessinsightbot_function`)
5. Select **Code + Test** and view the **Function URL** dropdown
6. Copy the **default** function key
7. Replace `YOUR_AZURE_FUNCTION_KEY_HERE` with your actual key

### Azure Text-to-Speech (TTS) Key

1. Go to **Azure Portal**
2. Navigate to **Cognitive Services** or **Text to Speech**
3. Select your **Speech service** resource
4. Go to **Keys and Endpoint** in the left sidebar
5. Copy either **Key 1** or **Key 2**
6. Replace `YOUR_AZURE_TEXT_TO_SPEECH_KEY_HERE` with your actual key
7. Note the **Region** (e.g., `eastus`) - update this in your configuration

### Application GUID

The default GUID is a placeholder: `c0p110t0-aaaa-bbbb-cccc-123456789abc`

- You can use this default GUID for development
- For production, use a unique identifier for each user or application instance
- GUIDs are used to track user-specific context and preferences

## How to Use These Credentials

### Option 1: Browser localStorage (Development)

The AI tools store configuration in browser localStorage:

1. Open an app (e.g., `ai-config-hub.html`)
2. Click "➕ Add Endpoint"
3. Enter your credentials
4. Click "Activate"
5. Configuration is stored locally and shared across all apps

### Option 2: Environment Variables (Recommended for Deployment)

For production deployments, use environment variables:

```bash
export AZURE_FUNCTION_KEY="your-actual-key-here"
export AZURE_TEXT_TO_SPEECH_KEY="your-actual-key-here"
```

Then update your application code to read from environment:

```javascript
const CONFIG = {
    functionKey: process.env.AZURE_FUNCTION_KEY || 'YOUR_AZURE_FUNCTION_KEY_HERE',
    azureTTSKey: process.env.AZURE_TEXT_TO_SPEECH_KEY || 'YOUR_AZURE_TEXT_TO_SPEECH_KEY_HERE'
};
```

### Option 3: Secure Configuration File (.env)

1. Copy `.env.example` to `.env`
2. Fill in your actual credentials
3. Add `.env` to `.gitignore` (already done)
4. Load credentials at runtime:

```javascript
// For Node.js/server-side apps
require('dotenv').config();
const KEY = process.env.AZURE_FUNCTION_KEY;
```

## Security Best Practices

### DO:
- Use strong, unique API keys
- Rotate keys regularly (every 90 days recommended)
- Use different keys for dev, staging, and production
- Store keys in secure vaults (Azure Key Vault, HashiCorp Vault, etc.)
- Enable key expiration policies
- Monitor key usage in Azure Portal
- Use managed identities when possible
- Log and audit all key access

### DON'T:
- Commit `.env` files to version control
- Share API keys in Slack, email, or chat
- Use the same key for multiple environments
- Store keys in code comments
- Hardcode keys in production applications
- Share keys with external parties
- Use weak or predictable key names
- Leave old/unused keys active

## GitHub Security Alert Response

If GitHub detects a committed secret:

1. **Immediately revoke the key** in Azure Portal
2. **Generate a new key** to replace it
3. **Update all applications** with the new key
4. **Remove the commit** from history (if critical):
   ```bash
   git filter-branch --force --index-filter "git rm --cached -r secrets/" --prune-empty --tag-name-filter cat -- --all
   git push origin main --force
   ```
5. **Report to GitHub** if needed via their security form

## Configuration Examples

### Example: ai-config-hub.html Setup

```javascript
// This is how the app reads credentials from localStorage
const endpoint = {
    name: 'Production Bot',
    url: 'https://azfbusinessbot.azurewebsites.net/api/businessinsightbot_function',
    key: 'YOUR_AZURE_FUNCTION_KEY_HERE',  // Replace with actual key
    guid: 'c0p110t0-aaaa-bbbb-cccc-123456789abc',
    provider: 'azure'
};
```

### Example: Local Development

For local testing, you can use:
- Placeholder keys that won't work against real services
- Mock endpoints that return demo responses
- Disable real API calls in debug mode

```javascript
const isDevelopment = !endpoint.key.startsWith('YOUR_');
if (isDevelopment) {
    // Use mock responses
    return mockAIResponse(userMessage);
}
```

## Monitoring & Alerts

### Azure Portal Key Monitoring

1. Enable **Activity Log** monitoring in Azure Portal
2. Set up **Alerts** for:
   - Failed authentication attempts
   - Unusual access patterns
   - Key regeneration events
   - Concurrent key usage

### Application-Level Logging

The applications include connection testing:
- Click the "Config" button (⚙️) in any app
- Click "🧪 Test Connection" to verify credentials
- Check browser console for detailed error messages

## Troubleshooting

### "401 Unauthorized" Error
- Verify the API key is correct and not expired
- Check that the endpoint URL matches your Azure Function
- Ensure the key hasn't been regenerated

### "Invalid TTS Key" Error
- Confirm the TTS key is for the correct region
- Verify the key hasn't expired or been revoked
- Check that you copied the entire key (no truncation)

### "Connection Failed" Error
- Verify internet connectivity
- Check Azure Portal to ensure the service is running
- Review Azure Function App logs for errors
- Test the endpoint URL with curl/Postman

## Additional Resources

- **Azure Documentation**: https://docs.microsoft.com/azure/
- **Function Keys Guide**: https://docs.microsoft.com/azure/azure-functions/security-concepts
- **Cognitive Services Auth**: https://docs.microsoft.com/azure/cognitive-services/authentication
- **GitHub Secret Scanning**: https://docs.github.com/en/code-security/secret-scanning

## Questions or Issues?

If you discover a security issue:
1. **DO NOT** post it publicly
2. Contact the repository maintainers
3. Use GitHub's private security advisories
4. Allow time for a fix before public disclosure

---

**Last Updated**: 2025-11-23
**Status**: All API keys have been replaced with placeholders
**Next Review**: After any security incidents or monthly (whichever is sooner)
