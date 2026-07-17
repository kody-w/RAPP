$ErrorActionPreference = "Stop"
[Console]::Error.WriteLine(@"
deploy.ps1: 410 Gone

Target-owned Tier 2 provisioning is retired. No Azure login, resource group,
deployment, Function App, storage account, or model resource was created.
"@)
exit 78
