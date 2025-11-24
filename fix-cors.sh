#!/bin/bash
# Script to fix CORS for RAPP Azure Function

FUNCTION_APP_NAME="rapp-jfduxek5c2pts"

echo "🔧 Fixing CORS for Azure Function: $FUNCTION_APP_NAME"
echo ""

# Get resource group
RESOURCE_GROUP=$(az functionapp list --query "[?name=='$FUNCTION_APP_NAME'].resourceGroup" -o tsv 2>/dev/null)

if [ -z "$RESOURCE_GROUP" ]; then
    echo "❌ Could not find function app. Please make sure you're logged into the correct Azure subscription."
    echo ""
    echo "Run this command to login:"
    echo "  az login"
    echo ""
    echo "Then list your subscriptions:"
    echo "  az account list --output table"
    echo ""
    echo "Set the correct subscription:"
    echo "  az account set --subscription <SUBSCRIPTION_ID>"
    exit 1
fi

echo "✅ Found function app in resource group: $RESOURCE_GROUP"
echo ""

# Configure CORS to allow all origins (or specify your domain)
echo "🌐 Configuring CORS..."
az functionapp cors add \
    --name "$FUNCTION_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --allowed-origins "*"

if [ $? -eq 0 ]; then
    echo "✅ CORS configured successfully!"
    echo ""
    echo "Current CORS settings:"
    az functionapp cors show --name "$FUNCTION_APP_NAME" --resource-group "$RESOURCE_GROUP"
else
    echo "❌ Failed to configure CORS"
    exit 1
fi

echo ""
echo "🎉 All done! Your web interface should now work."
echo ""
echo "⚠️  Note: For production, replace '*' with your specific domain:"
echo "   az functionapp cors remove --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP --allowed-origins '*'"
echo "   az functionapp cors add --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP --allowed-origins 'https://yourdomain.com'"
