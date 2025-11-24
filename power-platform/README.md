# Power Platform Integration

This directory contains Power Platform solution files for deploying RAPP agents to Microsoft Teams and Microsoft 365 Copilot.

## Solution Package

### MSFTAIBASMultiAgentCopilot_1_0_0_2.zip
Pre-configured Power Platform solution package for RAPP integration.

**Contents:**
- Copilot Studio bot configuration
- Power Automate flows for Azure Function integration
- Environment variables and connection references
- Custom connectors (if applicable)

## Quick Setup

### Prerequisites
- Power Platform license (or trial)
- Copilot Studio license (for M365 integration)
- Microsoft 365 license (for Teams and M365 Copilot)
- Deployed RAPP Azure Function (see main [README.md](/README.md))

### Installation Steps

1. **Download Solution** (if not already present)
   ```bash
   # Already included in this directory
   ls power-platform/MSFTAIBASMultiAgentCopilot_1_0_0_2.zip
   ```

2. **Import to Power Platform**
   - Navigate to [make.powerapps.com](https://make.powerapps.com)
   - Go to Solutions → Import solution
   - Upload the ZIP file
   - Click Next → Import
   - Wait for import to complete (2-5 minutes)

3. **Configure Power Automate Connection**
   - Open the imported solution
   - Find flow: "Talk to MAC (Migration Assessment Copilot)"
   - Edit HTTP action configuration:
     - URL: Your Azure Function URL
     - Headers: x-functions-key with your function key
   - Save and turn on the flow

4. **Configure Copilot Studio**
   - Navigate to [copilotstudio.microsoft.com](https://copilotstudio.microsoft.com)
   - Find imported bot: "Agent"
   - Verify Power Automate action connection
   - Test in Test pane

5. **Deploy to Teams/M365 Copilot**
   - In Copilot Studio, go to Channels
   - Select Microsoft Teams or Microsoft 365 Copilot
   - Follow deployment prompts
   - Share with users

## Finding Your Azure Function Details

**Function URL:**
- Azure Portal → Function App → Functions → `businessinsightbot_function` → Get Function URL
- Format: `https://<your-function-app>.azurewebsites.net/api/businessinsightbot_function`

**Function Key:**
- Azure Portal → Function App → Functions → `businessinsightbot_function` → Function Keys → Copy default key

## Documentation

For complete Power Platform integration guide, see:
- **Primary Guide**: [/docs/POWER_PLATFORM_INTEGRATION.md](/docs/POWER_PLATFORM_INTEGRATION.md)
- **CLAUDE.md Section**: [Power Platform Integration](/CLAUDE.md#power-platform-integration-optional)

## Troubleshooting

**401 Unauthorized Error:**
- Verify Function Key is correct
- Check Function App authentication settings
- Ensure CORS is configured properly

**Flow Fails to Execute:**
- Verify flow is turned ON
- Check connections are authenticated
- Review flow run history for errors

**Bot Doesn't Respond:**
- Test flow independently first
- Verify Copilot Studio topic is published
- Check Power Automate action is connected

For more troubleshooting guidance, see [/docs/TROUBLESHOOTING.md](/docs/TROUBLESHOOTING.md)

## Cost Considerations

**Power Platform:**
- ~$20/user/month for Power Apps + Copilot Studio
- Included in some Microsoft 365 E3/E5 licenses
- Trial available for development

**Azure Resources:**
- Function App: ~$5-10/month (Consumption plan)
- OpenAI: ~$0.01 per 1K tokens
- Storage: <$1/month for typical usage

**Total Estimated Cost:** $25-40/user/month for full integration
