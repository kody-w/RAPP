{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "functionAppName": {
      "type": "string",
      "defaultValue": "[concat('aibast-', uniqueString(resourceGroup().id))]",
      "metadata": {
        "description": "Name of the Function App (globally unique)"
      }
    },
    "storageAccountName": {
      "type": "string",
      "defaultValue": "[concat('st', uniqueString(resourceGroup().id))]",
      "maxLength": 24,
      "metadata": {
        "description": "Storage Account Name (3-24 characters, lowercase and numbers only)"
      }
    },
    "openAIServiceName": {
      "type": "string",
      "defaultValue": "[concat('openai-', uniqueString(resourceGroup().id))]",
      "metadata": {
        "description": "Name for the Azure OpenAI Service"
      }
    },
    "openAIModelName": {
      "type": "string",
      "defaultValue": "gpt-4o",
      "allowedValues": [
        "gpt-35-turbo",
        "gpt-4",
        "gpt-4-32k",
        "gpt-4o",
        "gpt-4o-mini"
      ],
      "metadata": {
        "description": "Azure OpenAI model to deploy"
      }
    },
    "openAISku": {
      "type": "string",
      "defaultValue": "S0",
      "allowedValues": ["S0"],
      "metadata": {
        "description": "SKU for Azure OpenAI Service"
      }
    },
    "openAIDeploymentCapacity": {
      "type": "int",
      "defaultValue": 10,
      "minValue": 1,
      "maxValue": 1000,
      "metadata": {
        "description": "Capacity for the OpenAI deployment in units of 1K TPM"
      }
    },
    "location": {
      "type": "string",
      "defaultValue": "[resourceGroup().location]",
      "allowedValues": [
        "eastus",
        "eastus2",
        "northcentralus",
        "southcentralus",
        "westus",
        "westus3",
        "canadacentral",
        "canadaeast",
        "australiaeast",
        "francecentral",
        "japaneast",
        "norwayeast",
        "swedencentral",
        "switzerlandnorth",
        "uksouth"
      ],
      "metadata": {
        "description": "Location for all resources (must support Azure OpenAI)"
      }
    },
    "assistantName": {
      "type": "string",
      "defaultValue": "AIBAST Agent",
      "metadata": {
        "description": "Display name for the AI assistant"
      }
    },
    "characteristicDescription": {
      "type": "string",
      "defaultValue": "Enterprise AI agent system with dynamic agent loading",
      "metadata": {
        "description": "Description of the assistant characteristics"
      }
    }
  },
  "variables": {
    "hostingPlanName": "[concat(parameters('functionAppName'), '-plan')]",
    "applicationInsightsName": "[concat(parameters('functionAppName'), '-insights')]",
    "fileShareName": "[concat('aibast-', uniqueString(resourceGroup().id))]",
    "blobContainerName": "[concat('app-package-', toLower(parameters('functionAppName')))]",
    "functionAppId": "[resourceId('Microsoft.Web/sites', parameters('functionAppName'))]",
    "storageAccountId": "[resourceId('Microsoft.Storage/storageAccounts', parameters('storageAccountName'))]",
    "openAIResourceId": "[resourceId('Microsoft.CognitiveServices/accounts', parameters('openAIServiceName'))]",
    "deploymentName": "gpt-deployment"
  },
  "resources": [
    {
      "type": "Microsoft.Storage/storageAccounts",
      "apiVersion": "2023-01-01",
      "name": "[parameters('storageAccountName')]",
      "location": "[parameters('location')]",
      "sku": {
        "name": "Standard_LRS"
      },
      "kind": "StorageV2",
      "properties": {
        "supportsHttpsTrafficOnly": true,
        "minimumTlsVersion": "TLS1_2",
        "allowBlobPublicAccess": false,
        "allowSharedKeyAccess": true,
        "networkAcls": {
          "bypass": "AzureServices",
          "defaultAction": "Allow"
        }
      }
    },
    {
      "type": "Microsoft.Storage/storageAccounts/blobServices",
      "apiVersion": "2023-01-01",
      "name": "[concat(parameters('storageAccountName'), '/default')]",
      "dependsOn": [
        "[variables('storageAccountId')]"
      ],
      "properties": {}
    },
    {
      "type": "Microsoft.Storage/storageAccounts/blobServices/containers",
      "apiVersion": "2023-01-01",
      "name": "[concat(parameters('storageAccountName'), '/default/', variables('blobContainerName'))]",
      "dependsOn": [
        "[resourceId('Microsoft.Storage/storageAccounts/blobServices', parameters('storageAccountName'), 'default')]"
      ],
      "properties": {
        "publicAccess": "None"
      }
    },
    {
      "type": "Microsoft.Storage/storageAccounts/fileServices",
      "apiVersion": "2023-01-01",
      "name": "[concat(parameters('storageAccountName'), '/default')]",
      "dependsOn": [
        "[variables('storageAccountId')]"
      ]
    },
    {
      "type": "Microsoft.Storage/storageAccounts/fileServices/shares",
      "apiVersion": "2023-01-01",
      "name": "[concat(parameters('storageAccountName'), '/default/', variables('fileShareName'))]",
      "dependsOn": [
        "[resourceId('Microsoft.Storage/storageAccounts/fileServices', parameters('storageAccountName'), 'default')]"
      ],
      "properties": {
        "shareQuota": 5120,
        "enabledProtocols": "SMB"
      }
    },
    {
      "type": "Microsoft.CognitiveServices/accounts",
      "apiVersion": "2024-06-01-preview",
      "name": "[parameters('openAIServiceName')]",
      "location": "[parameters('location')]",
      "sku": {
        "name": "[parameters('openAISku')]"
      },
      "kind": "OpenAI",
      "properties": {
        "customSubDomainName": "[parameters('openAIServiceName')]",
        "networkAcls": {
          "defaultAction": "Allow"
        },
        "publicNetworkAccess": "Enabled"
      }
    },
    {
      "type": "Microsoft.CognitiveServices/accounts/deployments",
      "apiVersion": "2024-06-01-preview",
      "name": "[concat(parameters('openAIServiceName'), '/', variables('deploymentName'))]",
      "dependsOn": [
        "[variables('openAIResourceId')]"
      ],
      "sku": {
        "name": "Standard",
        "capacity": "[parameters('openAIDeploymentCapacity')]"
      },
      "properties": {
        "model": {
          "format": "OpenAI",
          "name": "[parameters('openAIModelName')]",
          "version": "2024-08-06"
        },
        "versionUpgradeOption": "OnceNewDefaultVersionAvailable",
        "raiPolicyName": "Microsoft.Default"
      }
    },
    {
      "type": "Microsoft.Insights/components",
      "apiVersion": "2020-02-02",
      "name": "[variables('applicationInsightsName')]",
      "location": "[parameters('location')]",
      "kind": "web",
      "properties": {
        "Application_Type": "web",
        "Flow_Type": "Bluefield",
        "Request_Source": "rest"
      }
    },
    {
      "type": "Microsoft.Web/serverfarms",
      "apiVersion": "2023-12-01",
      "name": "[variables('hostingPlanName')]",
      "location": "[parameters('location')]",
      "sku": {
        "name": "FC1",
        "tier": "FlexConsumption"
      },
      "kind": "functionapp,linux",
      "properties": {
        "reserved": true,
        "maximumElasticWorkerCount": 100
      }
    },
    {
      "type": "Microsoft.Web/sites",
      "apiVersion": "2023-12-01",
      "name": "[parameters('functionAppName')]",
      "location": "[parameters('location')]",
      "kind": "functionapp,linux",
      "identity": {
        "type": "SystemAssigned"
      },
      "dependsOn": [
        "[resourceId('Microsoft.Web/serverfarms', variables('hostingPlanName'))]",
        "[variables('storageAccountId')]",
        "[resourceId('Microsoft.Insights/components', variables('applicationInsightsName'))]",
        "[variables('openAIResourceId')]",
        "[resourceId('Microsoft.CognitiveServices/accounts/deployments', parameters('openAIServiceName'), variables('deploymentName'))]",
        "[resourceId('Microsoft.Storage/storageAccounts/fileServices/shares', parameters('storageAccountName'), 'default', variables('fileShareName'))]",
        "[resourceId('Microsoft.Storage/storageAccounts/blobServices/containers', parameters('storageAccountName'), 'default', variables('blobContainerName'))]"
      ],
      "properties": {
        "serverFarmId": "[resourceId('Microsoft.Web/serverfarms', variables('hostingPlanName'))]",
        "httpsOnly": true,
        "functionAppConfig": {
          "deployment": {
            "storage": {
              "type": "blobContainer",
              "value": "[concat('https://', parameters('storageAccountName'), '.blob.core.windows.net/', variables('blobContainerName'))]",
              "authentication": {
                "type": "SystemAssignedIdentity"
              }
            }
          },
          "scaleAndConcurrency": {
            "maximumInstanceCount": 100,
            "instanceMemoryMB": 2048
          },
          "runtime": {
            "name": "python",
            "version": "3.11"
          }
        },
        "siteConfig": {
          "appSettings": [
            {
              "name": "AzureWebJobsStorage",
              "value": "[concat('DefaultEndpointsProtocol=https;AccountName=', parameters('storageAccountName'), ';EndpointSuffix=', environment().suffixes.storage, ';AccountKey=', listKeys(variables('storageAccountId'), '2023-01-01').keys[0].value)]"
            },
            {
              "name": "FUNCTIONS_EXTENSION_VERSION",
              "value": "~4"
            },
            {
              "name": "APPLICATIONINSIGHTS_CONNECTION_STRING",
              "value": "[reference(resourceId('Microsoft.Insights/components', variables('applicationInsightsName'))).ConnectionString]"
            },
            {
              "name": "AZURE_OPENAI_API_KEY",
              "value": "[listKeys(variables('openAIResourceId'), '2024-06-01-preview').key1]"
            },
            {
              "name": "AZURE_OPENAI_ENDPOINT",
              "value": "[reference(variables('openAIResourceId')).endpoint]"
            },
            {
              "name": "AZURE_OPENAI_API_VERSION",
              "value": "2024-08-01-preview"
            },
            {
              "name": "AZURE_OPENAI_DEPLOYMENT_NAME",
              "value": "[variables('deploymentName')]"
            },
            {
              "name": "AZURE_FILES_SHARE_NAME",
              "value": "[variables('fileShareName')]"
            },
            {
              "name": "ASSISTANT_NAME",
              "value": "[parameters('assistantName')]"
            },
            {
              "name": "CHARACTERISTIC_DESCRIPTION",
              "value": "[parameters('characteristicDescription')]"
            },
            {
              "name": "SCM_DO_BUILD_DURING_DEPLOYMENT",
              "value": "true"
            },
            {
              "name": "ENABLE_ORYX_BUILD",
              "value": "true"
            },
            {
              "name": "PYTHON_ENABLE_WORKER_EXTENSIONS",
              "value": "1"
            }
          ],
          "cors": {
            "allowedOrigins": ["*"],
            "supportCredentials": false
          },
          "use32BitWorkerProcess": false,
          "ftpsState": "FtpsOnly",
          "minTlsVersion": "1.2"
        }
      }
    },
    {
      "type": "Microsoft.Web/sites/basicPublishingCredentialsPolicies",
      "apiVersion": "2023-12-01",
      "name": "[concat(parameters('functionAppName'), '/scm')]",
      "dependsOn": [
        "[variables('functionAppId')]"
      ],
      "properties": {
        "allow": true
      }
    },
    {
      "type": "Microsoft.Web/sites/basicPublishingCredentialsPolicies",
      "apiVersion": "2023-12-01",
      "name": "[concat(parameters('functionAppName'), '/ftp')]",
      "dependsOn": [
        "[variables('functionAppId')]"
      ],
      "properties": {
        "allow": true
      }
    }
  ],
  "outputs": {
    "localSettingsJson": {
      "type": "string",
      "value": "[concat('{\n  \"IsEncrypted\": false,\n  \"Values\": {\n    \"AzureWebJobsStorage\": \"', concat('DefaultEndpointsProtocol=https;AccountName=', parameters('storageAccountName'), ';EndpointSuffix=', environment().suffixes.storage, ';AccountKey=', listKeys(variables('storageAccountId'), '2023-01-01').keys[0].value), '\",\n    \"FUNCTIONS_EXTENSION_VERSION\": \"~4\",\n    \"APPLICATIONINSIGHTS_CONNECTION_STRING\": \"', reference(resourceId('Microsoft.Insights/components', variables('applicationInsightsName'))).ConnectionString, '\",\n    \"AZURE_OPENAI_API_KEY\": \"', listKeys(variables('openAIResourceId'), '2024-06-01-preview').key1, '\",\n    \"AZURE_OPENAI_ENDPOINT\": \"', reference(variables('openAIResourceId')).endpoint, '\",\n    \"AZURE_OPENAI_API_VERSION\": \"2024-08-01-preview\",\n    \"AZURE_OPENAI_DEPLOYMENT_NAME\": \"', variables('deploymentName'), '\",\n    \"AZURE_FILES_SHARE_NAME\": \"', variables('fileShareName'), '\",\n    \"ASSISTANT_NAME\": \"', parameters('assistantName'), '\",\n    \"CHARACTERISTIC_DESCRIPTION\": \"', parameters('characteristicDescription'), '\",\n    \"FUNCTIONS_WORKER_RUNTIME\": \"python\",\n    \"PYTHON_ENABLE_WORKER_EXTENSIONS\": \"1\"\n  }\n}')]"
    },
    "windowsSetupScript": {
      "type": "string",
      "value": "[concat('# AIBAST Agent - Windows PowerShell Setup Script with Python 3.11\n# This script ensures Python 3.11 is installed (required for Azure Functions v4)\n# Save as setup.ps1 and run: .\\setup.ps1\n\nWrite-Host \"\" -ForegroundColor Cyan\nWrite-Host \"=================================================\" -ForegroundColor Cyan\nWrite-Host \"     AIBAST AGENT - AUTOMATED SETUP (v2.0)     \" -ForegroundColor Yellow\nWrite-Host \"=================================================\" -ForegroundColor Cyan\nWrite-Host \"\" -ForegroundColor Cyan\n\n# Step 1: Check for Python 3.11\nWrite-Host \"[1/6] Checking for Python 3.11...\" -ForegroundColor Green\n$pythonCommand = $null\n$pythonVersionPattern = \"3\\.11\\..*\"\n\n# Check if python3.11 is available\ntry {\n    $py311Version = python3.11 --version 2>&1\n    if ($py311Version -match $pythonVersionPattern) {\n        $pythonCommand = \"python3.11\"\n        Write-Host \"   Found: $py311Version\" -ForegroundColor Green\n    }\n} catch {}\n\n# If not found, check python or python3\nif (-not $pythonCommand) {\n    try {\n        $pyVersion = python --version 2>&1\n        if ($pyVersion -match $pythonVersionPattern) {\n            $pythonCommand = \"python\"\n            Write-Host \"   Found: $pyVersion\" -ForegroundColor Green\n        }\n    } catch {}\n}\n\nif (-not $pythonCommand) {\n    try {\n        $py3Version = python3 --version 2>&1\n        if ($py3Version -match $pythonVersionPattern) {\n            $pythonCommand = \"python3\"\n            Write-Host \"   Found: $py3Version\" -ForegroundColor Green\n        }\n    } catch {}\n}\n\n# If Python 3.11 not found, install it\nif (-not $pythonCommand) {\n    Write-Host \"   Python 3.11 not found. Installing...\" -ForegroundColor Yellow\n    \n    $pythonUrl = \"https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe\"\n    $pythonInstaller = \"$env:TEMP\\python-3.11.9-amd64.exe\"\n    \n    Write-Host \"   Downloading Python 3.11.9...\" -ForegroundColor Cyan\n    Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonInstaller\n    \n    Write-Host \"   Installing Python 3.11.9 (this may take 2-3 minutes)...\" -ForegroundColor Cyan\n    Start-Process -FilePath $pythonInstaller -Args \"/quiet InstallAllUsers=1 PrependPath=1 Include_test=0\" -Wait\n    \n    # Remove installer\n    Remove-Item $pythonInstaller\n    \n    # Refresh environment variables\n    $env:Path = [System.Environment]::GetEnvironmentVariable(\"Path\",\"Machine\") + \";\" + [System.Environment]::GetEnvironmentVariable(\"Path\",\"User\")\n    \n    # Check again\n    try {\n        $py311Version = python --version 2>&1\n        if ($py311Version -match $pythonVersionPattern) {\n            $pythonCommand = \"python\"\n            Write-Host \"   Successfully installed: $py311Version\" -ForegroundColor Green\n        } else {\n            Write-Host \"   Error: Python 3.11 installation failed\" -ForegroundColor Red\n            exit 1\n        }\n    } catch {\n        Write-Host \"   Error: Cannot find python command after installation\" -ForegroundColor Red\n        exit 1\n    }\n}\n\n# Step 2: Check for Git\nWrite-Host \"\" -ForegroundColor Cyan\nWrite-Host \"[2/6] Checking for Git...\" -ForegroundColor Green\ntry {\n    $gitVersion = git --version 2>&1\n    Write-Host \"   Found: $gitVersion\" -ForegroundColor Green\n} catch {\n    Write-Host \"   Git not found. Please install Git from: https://git-scm.com/download/win\" -ForegroundColor Red\n    Write-Host \"   After installing Git, re-run this script.\" -ForegroundColor Yellow\n    exit 1\n}\n\n# Step 3: Check for Azure Functions Core Tools\nWrite-Host \"\" -ForegroundColor Cyan\nWrite-Host \"[3/6] Checking for Azure Functions Core Tools...\" -ForegroundColor Green\ntry {\n    $funcVersion = func --version 2>&1\n    Write-Host \"   Found: Azure Functions Core Tools version $funcVersion\" -ForegroundColor Green\n} catch {\n    Write-Host \"   Azure Functions Core Tools not found. Installing via npm...\" -ForegroundColor Yellow\n    \n    # Check for npm\n    try {\n        $npmVersion = npm --version 2>&1\n        Write-Host \"   Found npm: $npmVersion\" -ForegroundColor Green\n        \n        Write-Host \"   Installing Azure Functions Core Tools (this may take 1-2 minutes)...\" -ForegroundColor Cyan\n        npm install -g azure-functions-core-tools@4 --unsafe-perm true\n        \n        $funcVersion = func --version 2>&1\n        Write-Host \"   Successfully installed: Azure Functions Core Tools version $funcVersion\" -ForegroundColor Green\n    } catch {\n        Write-Host \"   npm not found. Please install Node.js from: https://nodejs.org/\" -ForegroundColor Red\n        Write-Host \"   After installing Node.js, re-run this script.\" -ForegroundColor Yellow\n        exit 1\n    }\n}\n\n# Step 4: Clone repository\nWrite-Host \"\" -ForegroundColor Cyan\nWrite-Host \"[4/6] Cloning repository...\" -ForegroundColor Green\n\nif (Test-Path \"Copilot-Agent-365\") {\n    Write-Host \"   Repository already exists. Pulling latest changes...\" -ForegroundColor Yellow\n    cd Copilot-Agent-365\n    git pull\n    cd ..\n} else {\n    Write-Host \"   Cloning from GitHub...\" -ForegroundColor Cyan\n    git clone https://github.com/kody-w/Copilot-Agent-365.git\n}\n\ncd Copilot-Agent-365\n\n# Step 5: Create virtual environment and install dependencies\nWrite-Host \"\" -ForegroundColor Cyan\nWrite-Host \"[5/6] Setting up Python environment...\" -ForegroundColor Green\n\nif (Test-Path \".venv\") {\n    Write-Host \"   Virtual environment already exists.\" -ForegroundColor Yellow\n} else {\n    Write-Host \"   Creating virtual environment...\" -ForegroundColor Cyan\n    & $pythonCommand -m venv .venv\n}\n\nWrite-Host \"   Activating virtual environment...\" -ForegroundColor Cyan\n.\\.venv\\Scripts\\Activate.ps1\n\nWrite-Host \"   Installing dependencies...\" -ForegroundColor Cyan\n& $pythonCommand -m pip install --upgrade pip\n& $pythonCommand -m pip install -r requirements.txt\n\n# Step 6: Create local.settings.json with YOUR Azure values\nWrite-Host \"\" -ForegroundColor Cyan\nWrite-Host \"[6/6] Creating configuration file...\" -ForegroundColor Green\n\n$localSettings = @\"\n', parameters('localSettingsJson'), '\n\"@\n\n$localSettings | Out-File -FilePath \"local.settings.json\" -Encoding UTF8\nWrite-Host \"   Configuration file created: local.settings.json\" -ForegroundColor Green\n\n# Create run script\n$runScript = @\"\n# Quick run script - Use this to start your function app anytime\nWrite-Host \"Starting Azure Functions...\" -ForegroundColor Green\n.venv\\Scripts\\Activate.ps1\nfunc start\n\"@\n\n$runScript | Out-File -FilePath \"run.ps1\" -Encoding UTF8\nWrite-Host \"   Run script created: run.ps1\" -ForegroundColor Green\n\n# Success message\nWrite-Host \"\" -ForegroundColor Cyan\nWrite-Host \"=================================================\" -ForegroundColor Green\nWrite-Host \"          SETUP COMPLETE - YOU''RE READY!         \" -ForegroundColor Yellow\nWrite-Host \"=================================================\" -ForegroundColor Green\nWrite-Host \"\" -ForegroundColor Cyan\nWrite-Host \"To start your AI assistant:\" -ForegroundColor White\nWrite-Host \"\" -ForegroundColor Cyan\nWrite-Host \"   1. Run: .\\run.ps1\" -ForegroundColor Yellow\nWrite-Host \"   2. Open client/index.html in your browser\" -ForegroundColor Yellow\nWrite-Host \"   3. Start chatting with your AI!\" -ForegroundColor Yellow\nWrite-Host \"\" -ForegroundColor Cyan\nWrite-Host \"Azure Function Endpoint:\" -ForegroundColor White\nWrite-Host \"   Local:  http://localhost:7071/api/businessinsightbot_function\" -ForegroundColor Cyan\nWrite-Host \"   Azure:  ', reference(variables('functionAppId')).defaultHostName, '/api/businessinsightbot_function\" -ForegroundColor Cyan\nWrite-Host \"\" -ForegroundColor Cyan')]"
    },
    "macLinuxSetupScript": {
      "type": "string",
      "value": "[concat('#!/bin/bash\n# AIBAST Agent - Mac/Linux Setup Script with Python 3.11\n# Save this as setup.sh and run: bash setup.sh\n\nset -e\n\nRED=\"\\033[0;31m\"\nGREEN=\"\\033[0;32m\"\nYELLOW=\"\\033[1;33m\"\nCYAN=\"\\033[0;36m\"\nNC=\"\\033[0m\"\n\necho -e \"${CYAN}\"\necho \"=================================================\"\necho \"     AIBAST AGENT - AUTOMATED SETUP (v2.0)     \"\necho \"=================================================\"\necho -e \"${NC}\"\n\n# Step 1: Check for Python 3.11\necho -e \"${GREEN}[1/6] Checking for Python 3.11...${NC}\"\nPYTHON_CMD=\"\"\n\nif command -v python3.11 &> /dev/null; then\n    PYTHON_VERSION=$(python3.11 --version)\n    echo -e \"${GREEN}   Found: $PYTHON_VERSION${NC}\"\n    PYTHON_CMD=\"python3.11\"\nelif command -v python3 &> /dev/null; then\n    PYTHON_VERSION=$(python3 --version)\n    if [[ $PYTHON_VERSION == *\"3.11\"* ]]; then\n        echo -e \"${GREEN}   Found: $PYTHON_VERSION${NC}\"\n        PYTHON_CMD=\"python3\"\n    fi\nelif command -v python &> /dev/null; then\n    PYTHON_VERSION=$(python --version)\n    if [[ $PYTHON_VERSION == *\"3.11\"* ]]; then\n        echo -e \"${GREEN}   Found: $PYTHON_VERSION${NC}\"\n        PYTHON_CMD=\"python\"\n    fi\nfi\n\nif [ -z \"$PYTHON_CMD\" ]; then\n    echo -e \"${RED}   Python 3.11 not found${NC}\"\n    echo -e \"${YELLOW}   Please install Python 3.11:${NC}\"\n    echo -e \"${YELLOW}   Mac:   brew install python@3.11${NC}\"\n    echo -e \"${YELLOW}   Linux: sudo apt-get install python3.11 python3.11-venv${NC}\"\n    exit 1\nfi\n\n# Step 2: Check for Git\necho -e \"${GREEN}[2/6] Checking for Git...${NC}\"\nif command -v git &> /dev/null; then\n    GIT_VERSION=$(git --version)\n    echo -e \"${GREEN}   Found: $GIT_VERSION${NC}\"\nelse\n    echo -e \"${RED}   Git not found${NC}\"\n    echo -e \"${YELLOW}   Please install Git:${NC}\"\n    echo -e \"${YELLOW}   Mac:   brew install git${NC}\"\n    echo -e \"${YELLOW}   Linux: sudo apt-get install git${NC}\"\n    exit 1\nfi\n\n# Step 3: Check for Azure Functions Core Tools\necho -e \"${GREEN}[3/6] Checking for Azure Functions Core Tools...${NC}\"\nif command -v func &> /dev/null; then\n    FUNC_VERSION=$(func --version)\n    echo -e \"${GREEN}   Found: Azure Functions Core Tools version $FUNC_VERSION${NC}\"\nelse\n    echo -e \"${YELLOW}   Azure Functions Core Tools not found. Installing via npm...${NC}\"\n    \n    if command -v npm &> /dev/null; then\n        NPM_VERSION=$(npm --version)\n        echo -e \"${GREEN}   Found npm: $NPM_VERSION${NC}\"\n        \n        echo -e \"${CYAN}   Installing Azure Functions Core Tools...${NC}\"\n        sudo npm install -g azure-functions-core-tools@4 --unsafe-perm true\n        \n        FUNC_VERSION=$(func --version)\n        echo -e \"${GREEN}   Successfully installed: Azure Functions Core Tools version $FUNC_VERSION${NC}\"\n    else\n        echo -e \"${RED}   npm not found${NC}\"\n        echo -e \"${YELLOW}   Please install Node.js from: https://nodejs.org/${NC}\"\n        exit 1\n    fi\nfi\n\n# Step 4: Clone repository\necho -e \"${GREEN}[4/6] Cloning repository...${NC}\"\n\nif [ -d \"Copilot-Agent-365\" ]; then\n    echo -e \"${YELLOW}   Repository already exists. Pulling latest changes...${NC}\"\n    cd Copilot-Agent-365\n    git pull\n    cd ..\nelse\n    echo -e \"${CYAN}   Cloning from GitHub...${NC}\"\n    git clone https://github.com/kody-w/Copilot-Agent-365.git\nfi\n\ncd Copilot-Agent-365\n\n# Step 5: Create virtual environment and install dependencies\necho -e \"${GREEN}[5/6] Setting up Python environment...${NC}\"\n\nif [ -d \".venv\" ]; then\n    echo -e \"${YELLOW}   Virtual environment already exists.${NC}\"\nelse\n    echo -e \"${CYAN}   Creating virtual environment...${NC}\"\n    $PYTHON_CMD -m venv .venv\nfi\n\necho -e \"${CYAN}   Activating virtual environment...${NC}\"\nsource .venv/bin/activate\n\necho -e \"${CYAN}   Installing dependencies...${NC}\"\n$PYTHON_CMD -m pip install --upgrade pip\n$PYTHON_CMD -m pip install -r requirements.txt\n\n# Step 6: Create local.settings.json with YOUR Azure values\necho -e \"${GREEN}[6/6] Creating configuration file...${NC}\"\n\ncat > local.settings.json << ''EOF''\n', parameters('localSettingsJson'), '\nEOF\n\necho -e \"${GREEN}   Configuration file created: local.settings.json${NC}\"\n\n# Create run script\ncat > run.sh << ''RUNEOF''\n#!/bin/bash\n# Quick run script - Use this to start your function app anytime\necho \"Starting Azure Functions...\"\nsource .venv/bin/activate\nfunc start\nRUNEOF\n\nchmod +x run.sh\necho -e \"${GREEN}   Run script created: run.sh${NC}\"\n\n# Success message\necho -e \"${CYAN}\"\necho \"=================================================\"\necho \"          SETUP COMPLETE - YOU''RE READY!         \"\necho \"=================================================\"\necho -e \"${NC}\"\necho -e \"${WHITE}To start your AI assistant:${NC}\"\necho -e \"${CYAN}\"\necho -e \"${YELLOW}   1. Run: ./run.sh${NC}\"\necho -e \"${YELLOW}   2. Open client/index.html in your browser${NC}\"\necho -e \"${YELLOW}   3. Start chatting with your AI!${NC}\"\necho -e \"${CYAN}\"\necho -e \"${WHITE}Azure Function Endpoint:${NC}\"\necho -e \"${CYAN}   Local:  http://localhost:7071/api/businessinsightbot_function${NC}\"\necho -e \"${CYAN}   Azure:  ', reference(variables('functionAppId')).defaultHostName, '/api/businessinsightbot_function${NC}\"\necho -e \"${CYAN}\"')]"
    },
    "setupInstructions": {
      "type": "string",
      "value": "🚀 COMPLETE SETUP INSTRUCTIONS - Python 3.11 Compatible:\n\n📱 FOR WINDOWS (PowerShell):\n1. Copy the entire 'windowsSetupScript' value above\n2. Save as 'setup.ps1' on your computer\n3. Open PowerShell as Administrator\n4. If you get a security error, run: Set-ExecutionPolicy RemoteSigned -Scope CurrentUser\n5. Run: .\\setup.ps1\n6. Wait 2-5 minutes for automatic installation\n7. After setup completes, run: .\\run.ps1\n8. Open client/index.html in your browser\n\n🍎 FOR MAC/LINUX (Terminal):\n1. Copy the entire 'macLinuxSetupScript' value above\n2. Save as 'setup.sh' on your computer\n3. Open Terminal\n4. Make it executable: chmod +x setup.sh\n5. Run: ./setup.sh\n6. Wait 2-5 minutes for automatic installation\n7. After setup completes, run: ./run.sh\n8. Open client/index.html in your browser\n\n✅ WHAT THIS DOES AUTOMATICALLY:\n• Checks for Python 3.11 (installs if missing on Windows)\n• Checks for Git (prompts to install if missing)\n• Checks for Azure Functions Core Tools (installs if missing)\n• Clones the repository from GitHub\n• Creates Python virtual environment\n• Installs all dependencies\n• Creates local.settings.json with YOUR Azure credentials\n• Creates run scripts for easy startup\n\n🎯 YOUR AZURE RESOURCES:\n• Function App: [parameters('functionAppName')]\n• Storage Account: [parameters('storageAccountName')]\n• OpenAI Service: [parameters('openAIServiceName')]\n• File Share: [variables('fileShareName')]\n\n📚 IMPORTANT NOTES:\n• Python 3.11 is REQUIRED for Azure Functions v4\n• Windows script auto-installs Python 3.11 if not found\n• Mac/Linux requires manual Python 3.11 installation\n• All Azure settings are pre-configured in the script\n• No manual editing required!\n\n💡 NEED HELP?\n• GitHub: https://github.com/kody-w/Copilot-Agent-365\n• Issues: https://github.com/kody-w/Copilot-Agent-365/issues"
    },
    "functionAppName": {
      "type": "string",
      "value": "[parameters('functionAppName')]"
    },
    "functionAppUrl": {
      "type": "string",
      "value": "[concat('https://', reference(variables('functionAppId')).defaultHostName)]"
    },
    "functionEndpoint": {
      "type": "string",
      "value": "[concat('https://', reference(variables('functionAppId')).defaultHostName, '/api/businessinsightbot_function')]"
    },
    "storageAccountName": {
      "type": "string",
      "value": "[parameters('storageAccountName')]"
    },
    "fileShareName": {
      "type": "string",
      "value": "[variables('fileShareName')]"
    },
    "openAIServiceName": {
      "type": "string",
      "value": "[parameters('openAIServiceName')]"
    },
    "openAIEndpoint": {
      "type": "string",
      "value": "[reference(variables('openAIResourceId')).endpoint]"
    },
    "openAIApiKey": {
      "type": "string",
      "value": "[listKeys(variables('openAIResourceId'), '2024-06-01-preview').key1]"
    },
    "storageAccountKey": {
      "type": "string",
      "value": "[listKeys(variables('storageAccountId'), '2023-01-01').keys[0].value]"
    },
    "resourceGroupName": {
      "type": "string",
      "value": "[resourceGroup().name]"
    },
    "deploymentCommand": {
      "type": "string",
      "value": "[concat('az functionapp deployment source config-zip --resource-group ', resourceGroup().name, ' --name ', parameters('functionAppName'), ' --src function-app.zip')]"
    },
    "repositoryUrl": {
      "type": "string",
      "value": "https://github.com/kody-w/Copilot-Agent-365"
    },
    "troubleshooting": {
      "type": "string",
      "value": "🔧 TROUBLESHOOTING GUIDE:\n\n❌ If you see 'Key based authentication is not permitted':\n1. Go to Azure Portal → Your Storage Account\n2. Click 'Configuration' under Settings\n3. Find 'Allow storage account key access'\n4. Make sure it's set to 'Enabled'\n5. Click 'Save' at the top\n6. Wait 1-2 minutes for the change to propagate\n7. Try running your function again\n\n❌ If Python 3.11 installation fails (Windows):\n1. Download manually: https://www.python.org/downloads/\n2. Install with 'Add Python to PATH' checked\n3. Re-run setup.ps1\n\n❌ If Azure Functions Core Tools fails to install:\n1. Install Node.js first: https://nodejs.org/\n2. Run: npm install -g azure-functions-core-tools@4 --unsafe-perm true\n3. Re-run the setup script\n\n✅ The ARM template is configured correctly with 'allowSharedKeyAccess: true'\n✅ If issues persist, check Azure Portal for any policy restrictions on your subscription"
    },
    "allFixesApplied": {
      "type": "string",
      "value": "✅ ALL FIXES APPLIED:\n1. ✅ Storage account configured with 'allowSharedKeyAccess: true'\n2. ✅ Flex Consumption plan configured correctly\n3. ✅ Python 3.11 runtime specified\n4. ✅ All necessary app settings included\n5. ✅ Setup scripts auto-detect and install Python 3.11\n6. ✅ Complete troubleshooting guide included\n7. ✅ Network ACLs set to Allow with AzureServices bypass\n8. ✅ System-assigned managed identity enabled\n\n⚠️ IMPORTANT: If you still see key-based authentication errors after deployment:\n- Check your Azure subscription for any policies that block shared key access\n- Verify in Azure Portal → Storage Account → Configuration → 'Allow storage account key access' is Enabled\n- Some enterprise subscriptions have org-level policies that override this setting"
    }
  }
}
