# CORS Configuration for RAPP

## Overview

CORS (Cross-Origin Resource Sharing) is now **automatically configured** in all new Azure deployments using the ARM template (`azuredeploy.json`).

## What Was Fixed

### Problem
The web interface (`index.html`) was failing with CORS errors when trying to connect to the Azure Function:
```
Access to fetch at 'https://rapp-xxx.azurewebsites.net/...' has been blocked by CORS policy
```

### Root Causes
1. **Function Key Authentication**: The web interface was sending the key as `x-functions-key` header (incorrect)
2. **Missing CORS Configuration**: Azure Function didn't allow browser requests from different origins

### Solutions Applied

#### 1. Fixed index.html (✅ COMPLETED)
Changed all fetch calls to include the function key in the URL:
```javascript
// Before (BROKEN)
fetch(endpoint.url, {
  headers: { "x-functions-key": endpoint.key }
})

// After (FIXED)
const fullUrl = `${endpoint.url}?code=${endpoint.key}`;
fetch(fullUrl, {
  headers: { "Content-Type": "application/json" }
})
```

#### 2. Updated ARM Template (✅ COMPLETED)
Added CORS configuration to `azuredeploy.json`:
- **Default**: Allows all origins (`*`) for development
- **Customizable**: Can specify allowed domains for production
- **Automatic**: All new deployments have CORS enabled

## ARM Template Configuration

### Default Deployment (Allows All Origins)
```bash
az deployment group create \
  --resource-group YOUR_RG \
  --template-file azuredeploy.json
```
CORS will be configured as: `allowedOrigins: ["*"]`

### Production Deployment (Specific Domains)
```bash
az deployment group create \
  --resource-group YOUR_RG \
  --template-file azuredeploy.json \
  --parameters corsAllowedOrigins='["https://yourdomain.com","https://app.yourdomain.com"]'
```

## Manual CORS Configuration (Existing Deployments)

If you already deployed before this fix, update CORS manually:

### Option 1: Azure CLI
```bash
# Find your function app
az functionapp list --query "[].{name:name, resourceGroup:resourceGroup}" -o table

# Enable CORS for all origins (development)
az functionapp cors add \
  --name YOUR_FUNCTION_APP_NAME \
  --resource-group YOUR_RESOURCE_GROUP \
  --allowed-origins "*"

# OR enable CORS for specific domains (production)
az functionapp cors add \
  --name YOUR_FUNCTION_APP_NAME \
  --resource-group YOUR_RESOURCE_GROUP \
  --allowed-origins "https://yourdomain.com" "https://app.yourdomain.com"
```

### Option 2: Azure Portal
1. Go to [portal.azure.com](https://portal.azure.com)
2. Navigate to your Function App
3. Go to **API** → **CORS**
4. Add allowed origins:
   - Development: Add `*`
   - Production: Add specific domains (e.g., `https://yourdomain.com`)
5. Click **Save**

### Option 3: Use the Script
```bash
./fix-cors.sh
```

## Testing CORS

### Test with CLI (No CORS Required)
```bash
./rapp-cli.sh --message "Hello"
```
✅ Should work regardless of CORS configuration

### Test with Web Interface (CORS Required)
1. Open `index.html` in browser
2. Configure endpoint in Settings
3. Send a message
4. Check browser console (F12) for errors

**Expected Result**: ✅ Message sends successfully, no CORS errors

## Security Best Practices

### Development Environment
```json
{
  "corsAllowedOrigins": ["*"]
}
```
✅ Allows testing from any domain
⚠️ **NOT** for production use

### Production Environment
```json
{
  "corsAllowedOrigins": [
    "https://yourdomain.com",
    "https://app.yourdomain.com",
    "https://admin.yourdomain.com"
  ]
}
```
✅ Restricts access to specific domains
✅ Prevents unauthorized web apps from calling your API
✅ Recommended for production deployments

### Staging/Testing Environment
```json
{
  "corsAllowedOrigins": [
    "https://staging.yourdomain.com",
    "http://localhost:5500",
    "http://127.0.0.1:5500"
  ]
}
```
✅ Allows local development
✅ Allows staging domain
⚠️ Remove localhost entries before production

## Troubleshooting

### Issue: Still Getting CORS Errors After Fix

**Check 1: Verify CORS is Enabled**
```bash
az functionapp cors show --name YOUR_FUNCTION_APP --resource-group YOUR_RG
```

**Check 2: Check Browser Console**
Press F12 → Console tab → Look for:
- ❌ `Access to fetch at... has been blocked by CORS policy`
- ✅ `No CORS errors = CORS is working`

**Check 3: Verify URL Format**
Endpoint URL should NOT include `?code=` when saved in settings:
- ❌ `https://rapp-xxx.azurewebsites.net/api/function?code=KEY123` (incorrect)
- ✅ `https://rapp-xxx.azurewebsites.net/api/function` (correct)

The code is added automatically by the JavaScript fetch call.

**Check 4: Clear Browser Cache**
```
Chrome: Ctrl+Shift+Delete (Windows) / Cmd+Shift+Delete (Mac)
Edge: Ctrl+Shift+Delete
Safari: Cmd+Option+E
```

**Check 5: Try Incognito/Private Mode**
Sometimes cached CORS preflight requests cause issues.

### Issue: Function Key Not Working

**Check 1: Verify Key Format**
Function keys should be ~40-60 characters, alphanumeric with special characters:
- ✅ `xxXXxxXXxxXXxxXXxxXXxxXXxxXXxxXXxxXXxxXXxxXXxxXXxx==`
- ❌ `12345` (too short)

**Check 2: Get Fresh Key**
```bash
az functionapp function keys list \
  --name YOUR_FUNCTION_APP \
  --resource-group YOUR_RG \
  --function-name businessinsightbot_function
```

**Check 3: Test with CLI First**
```bash
./rapp-cli.sh --message "Test"
```
If CLI works but web doesn't, it's a CORS issue.

## Files Modified

1. **`index.html`** (lines 5171-5186, 5301-5317, 6310-6326)
   - Fixed function key authentication
   - Changed from header to URL query parameter

2. **`azuredeploy.json`** (lines 119-125, 322-325)
   - Added `corsAllowedOrigins` parameter
   - Configured CORS in Function App `siteConfig`

3. **`fix-cors.sh`** (new file)
   - Manual CORS configuration script for existing deployments

## Related Documentation

- [Azure Functions CORS Documentation](https://learn.microsoft.com/en-us/azure/azure-functions/functions-how-to-use-azure-function-app-settings#cors)
- [MDN CORS Guide](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [Azure ARM Template Reference](https://learn.microsoft.com/en-us/azure/templates/microsoft.web/sites)

## Summary

✅ **index.html** - Fixed to use correct authentication method
✅ **azuredeploy.json** - CORS automatically enabled for new deployments
✅ **fix-cors.sh** - Manual fix script for existing deployments
✅ **CORS-SETUP.md** - Complete documentation (this file)

**All future deployments will work out of the box!** 🎉
