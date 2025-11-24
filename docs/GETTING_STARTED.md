# Getting Started with Copilot Agent 365

This guide will help you deploy and run your AI assistant in under 5 minutes.

## 🎯 What You'll Accomplish

By the end of this guide, you'll have:
- ✅ Azure resources deployed (OpenAI, Storage, Function App)
- ✅ Local development environment configured
- ✅ AI assistant running both locally and in Azure
- ✅ Web chat interface ready to use

## 📋 Prerequisites

### Required
- **Azure Account** - [Get free trial](https://azure.microsoft.com/free/) (includes $200 credit)
- **Internet connection** - For Azure deployment and setup

### Operating System Specific

**Windows:**
- PowerShell (already included)
- Everything else auto-installs! ✨

**Mac/Linux:**
- Python 3.11: `brew install python@3.11` (Mac) or `apt-get install python3.11` (Linux)
- Git: `brew install git` (Mac) or `apt-get install git` (Linux)
- Node.js: `brew install node` (Mac) or from [nodejs.org](https://nodejs.org/)
- Azure Functions Core Tools: `npm install -g azure-functions-core-tools@4`

## 🚀 Step 1: Deploy to Azure (1 minute)

Click the button below to deploy all Azure resources:

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fkody-w%2FCopilot-Agent-365%2Fmain%2Fazuredeploy.json)

### What Gets Deployed

The deployment creates these resources:
- **Azure OpenAI Service** - GPT-4 model for AI processing
- **Azure Storage Account** - For conversation memory and agent storage
- **Azure Function App** - Serverless compute for your assistant
- **Application Insights** - Optional monitoring and diagnostics

### Deployment Process

1. Click the "Deploy to Azure" button above
2. Sign in to your Azure account
3. Fill in the required fields:
   - **Subscription**: Select your Azure subscription
   - **Resource Group**: Create new or use existing
   - **Region**: Choose a region (recommend: East US, West Europe, or Japan East)
   - **Project Name**: Give your project a unique name (e.g., "mycompany-ai-assistant")
4. Click **Review + Create**
5. Click **Create**

⏱️ **Deployment takes 3-5 minutes**. You'll see "Your deployment is complete" when finished.

## 📥 Step 2: Copy Setup Script (30 seconds)

After deployment completes:

1. Click the **"Outputs"** tab on the left sidebar

   ![Click Outputs Tab](images/afterTemplate1.png)

2. Find and copy the entire script value:
   - **Windows users**: Copy `windowsSetupScript`
   - **Mac/Linux users**: Copy `macLinuxSetupScript`

   ![Copy Script Value](images/afterTemplate2.png)

3. Save the script to a file:
   - **Windows**: Save as `setup.ps1`
   - **Mac/Linux**: Save as `setup.sh`

## 🔧 Step 3: Run Setup Script (2 minutes)

### Windows (PowerShell)

```powershell
# Navigate to where you saved the script
cd C:\Users\YourName\Downloads

# If you get a security error, run this first:
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser

# Run the setup script
.\setup.ps1
```

### Mac/Linux (Terminal)

```bash
# Navigate to where you saved the script
cd ~/Downloads

# Make it executable
chmod +x setup.sh

# Run the setup script
./setup.sh
```

### What the Script Does

The script automatically:
1. ✅ Installs Python 3.11 (if not found - Windows only)
2. ✅ Clones the Copilot-Agent-365 repository
3. ✅ Creates `local.settings.json` with YOUR Azure credentials
4. ✅ Sets up Python virtual environment
5. ✅ Installs all dependencies
6. ✅ Creates run scripts (`run.ps1`, `run.bat`, `run.sh`)

**Note**: The script includes your Azure credentials embedded securely - no manual configuration needed!

## ▶️ Step 4: Start Your Assistant (10 seconds)

### Windows

```powershell
cd Copilot-Agent-365
.\run.ps1
```

Or double-click `run.bat` in the folder.

### Mac/Linux

```bash
cd Copilot-Agent-365
./run.sh
```

You'll see output like:

```
Azure Functions Core Tools
Core Tools Version:       4.x.x
Function Runtime Version: 4.x.x

Functions:
  businessinsightbot_function: [POST] http://localhost:7071/api/businessinsightbot_function
```

## 💬 Step 5: Test Your Assistant

### Option 1: Web Chat Interface (Recommended)

1. Open `client/index.html` in your browser
2. Type a message: "Hello, what can you help me with?"
3. Get an instant AI-powered response!

### Option 2: Direct API Test

**PowerShell (Windows):**
```powershell
Invoke-RestMethod -Uri "http://localhost:7071/api/businessinsightbot_function" `
  -Method Post `
  -Body '{"user_input": "Hello", "conversation_history": []}' `
  -ContentType "application/json"
```

**curl (Mac/Linux):**
```bash
curl -X POST http://localhost:7071/api/businessinsightbot_function \
  -H "Content-Type: application/json" \
  -d '{"user_input": "Hello", "conversation_history": []}'
```

### Option 3: Test in Azure

The setup script outputs your Azure URL. Use it to test the deployed version:

```bash
# Your Azure URL looks like:
https://your-function-app.azurewebsites.net/api/businessinsightbot_function?code=YOUR_KEY
```

Test with curl or PowerShell (replace YOUR_URL):

```bash
curl -X POST "YOUR_URL" \
  -H "Content-Type: application/json" \
  -d '{"user_input": "Hello", "conversation_history": []}'
```

## ✅ Verify Everything Works

You should see a JSON response like:

```json
{
  "assistant_response": "Hello! I'm your AI assistant. I can help you with...",
  "voice_response": "Hello! I'm here to help.",
  "agent_logs": "Session initialized...",
  "user_guid": "c0p110t0-aaaa-bbbb-cccc-123456789abc"
}
```

## 🎉 Success! What's Next?

Your AI assistant is now running! Here are your next steps:

### 1. Customize Your Assistant

Edit personality in Azure Portal → Function App → Configuration:
- `ASSISTANT_NAME` - Change from "Copilot 365 Agent" to your preferred name
- `CHARACTERISTIC_DESCRIPTION` - Modify the assistant's personality and capabilities

### 2. Deploy to Microsoft Teams (Optional)

Want your team to use the assistant in Teams? Follow the [Power Platform Integration Guide](POWER_PLATFORM_INTEGRATION.md).

### 3. Create Custom Agents

Add specialized capabilities by creating custom agents. See [Agent Development Guide](AGENT_DEVELOPMENT.md).

### 4. Monitor Usage

Check Application Insights in Azure Portal for:
- Request volume and response times
- Error tracking
- Usage analytics

## 🛠️ Common Commands

### Start the Assistant
```bash
# Windows
.\run.ps1

# Mac/Linux
./run.sh
```

### Stop the Assistant
Press `Ctrl+C` in the terminal

### Update Dependencies
```bash
# Activate virtual environment first
# Windows
.venv\Scripts\activate

# Mac/Linux
source .venv/bin/activate

# Install/update packages
pip install -r requirements.txt
```

### Deploy Code Changes to Azure
```bash
# Login to Azure (first time only)
az login

# Deploy to Azure
func azure functionapp publish YOUR-FUNCTION-APP-NAME
```

## 🚨 Troubleshooting

### "Python 3.11 not found" (Windows)
Wait 2-3 minutes - the script auto-installs it! If it still fails, manually install from [python.org](https://www.python.org/downloads/).

### "func: command not found" (Mac/Linux)
Install Azure Functions Core Tools:
```bash
npm install -g azure-functions-core-tools@4
```

### "Port 7071 already in use"
Another process is using the port. Either stop it or change the port:
```bash
func start --port 7072
```

### "Module not found" errors
Reinstall dependencies:
```bash
# Activate virtual environment first
pip install -r requirements.txt --force-reinstall
```

### Setup script won't run
**Windows**: Allow script execution:
```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Mac/Linux**: Make script executable:
```bash
chmod +x setup.sh
```

For more issues, see the [Complete Troubleshooting Guide](TROUBLESHOOTING.md).

## 📚 Learn More

- **[Architecture Overview](ARCHITECTURE.md)** - Understand how the system works
- **[API Reference](API_REFERENCE.md)** - Complete API documentation
- **[Power Platform Integration](POWER_PLATFORM_INTEGRATION.md)** - Deploy to Teams
- **[Security Best Practices](SECURITY.md)** - Secure your deployment

## 💰 Cost Estimate

After free trial credits:
- **Function App**: ~$0 (free tier covers most usage)
- **Storage**: ~$5/month
- **OpenAI**: ~$0.01 per 1K tokens (pay-as-you-go)

**Total: ~$5/month + OpenAI usage**

For typical usage (100 conversations/day), expect **~$10-20/month total**.

## 🆘 Need Help?

- **Issues**: [Report bugs](https://github.com/kody-w/Copilot-Agent-365/issues)
- **Discussions**: [Ask questions](https://github.com/kody-w/Copilot-Agent-365/discussions)
- **Documentation**: [Browse all docs](index.md)

---

**Congratulations!** 🎉 You've successfully deployed your AI assistant. Enjoy building with Copilot Agent 365!
