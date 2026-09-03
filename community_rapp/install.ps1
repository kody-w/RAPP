# CommunityRAPP — One-line installer for Windows (Hippocampus / Tier 2)
# Usage: irm https://raw.githubusercontent.com/kody-w/rapp-installer/main/community_rapp/install.ps1 | iex
#
# Creates a ready-to-run CommunityRAPP project with persistent memory,
# auto-discovered agents, and GitHub Copilot device-code auth through the UI.
# No API keys, no Azure account, no cloud services needed to start.

# RAPP_RESTORED_GATE_BEGIN
$RappRestoredTarget = "community_rapp/install.ps1"
$RappRestoredSourceCommit = "4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6"
$RappRestoredSourceBlob = "9a7bd84a25498bd68ec020bb7a552f7a68f732dd"
$RappKernelPinSha256 = "427a37cc914a279b9c32a2ab85be9a19a0046f10f9f503c088a2670b6646e21c"
function Write-RappRestoredPlan {
    $json = '{"schema":"rapp-restored-distribution-source/1.0","target":"' +
        $RappRestoredTarget + '","mode":"plan","source_commit":"' +
        $RappRestoredSourceCommit + '","source_blob":"' +
        $RappRestoredSourceBlob +
        '","kernel":"kody-w/rapp-installer@brainstem-v0.6.9","kernel_pin_sha256":"' +
        $RappKernelPinSha256 +
        '","apply_permitted":false,"reason":"authenticated-section-13-evidence-unavailable"}'
    [Console]::Out.WriteLine($json)
}
function Stop-RappRestored {
    param([string]$Message)
    [Console]::Error.WriteLine(
        ("410 Gone: {0}: {1} (RAPP1_STATUS.md)" -f $RappRestoredTarget, $Message)
    )
    return 78
}
function Test-RappRestoredKernelPin {
    param([string]$Path)
    if (-not $Path -or -not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $false
    }
    try {
        $hash = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
        $pin = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    } catch {
        return $false
    }
    $frozen = $pin.kernel.frozen
    return (
        $hash -eq $RappKernelPinSha256 -and
        $pin.kernel.grail -eq "kody-w/rapp-installer" -and
        $pin.kernel.tag -eq "brainstem-v0.6.9" -and
        $frozen.'rapp_brainstem/brainstem.py' -eq "a293dd9f11eef915bf15776f08c736faa60cb749820871b6753ea98233142a71" -and
        $frozen.'rapp_brainstem/agents/basic_agent.py' -eq "701488bc00d536a7b23295e7da99c62f24e9b00f233daa325886430c736b78eb" -and
        $frozen.'rapp_brainstem/VERSION' -eq "13eb74b44be6e3a85a0efa0dedf56aec05e9e50140e1c8bbc0d0fbd8097b0717"
    )
}
function Invoke-RappRestoredGate {
$RappGateArgs = @($args)
$RappMode = if ($RappGateArgs.Count) { [string]$RappGateArgs[0] } else { "plan" }
$RappGateArgs = if ($RappGateArgs.Count -gt 1) {
    @($RappGateArgs[1..($RappGateArgs.Count - 1)])
} else {
    @()
}
if ($RappMode -in @("plan", "--plan", "inspect", "--inspect", "check", "--check", "help", "--help", "-h")) {
    Write-RappRestoredPlan
    return 0
}
if ($RappMode -notin @("apply", "--apply", "run", "--run")) {
    return (Stop-RappRestored "explicit plan/check/inspect or gated --apply is required")
}
$RappValues = @{}
$RappAllowActiveEffects = $false
for ($index = 0; $index -lt $RappGateArgs.Count; $index++) {
    $option = [string]$RappGateArgs[$index]
    if ($option -eq "--allow-active-effects") {
        $RappAllowActiveEffects = $true
        continue
    }
    if ($option -notin @(
        "--target",
        "--kernel-pin",
        "--reviewed-dependency-injection",
        "--owner-approval",
        "--section13-evidence"
    )) {
        return (Stop-RappRestored "unsupported activation argument: $option")
    }
    $index++
    if ($index -ge $RappGateArgs.Count) {
        return (Stop-RappRestored "missing value for $option")
    }
    $RappValues[$option] = [string]$RappGateArgs[$index]
}
if (-not $RappAllowActiveEffects) {
    return (Stop-RappRestored "--allow-active-effects is required")
}
if ($RappValues["--target"] -ne $RappRestoredTarget) {
    return (Stop-RappRestored "target-specific approval target is missing or mismatched")
}
if (-not (Test-RappRestoredKernelPin $RappValues["--kernel-pin"])) {
    return (Stop-RappRestored "exact KERNEL_PIN.json for kody-w/rapp-installer@brainstem-v0.6.9 is required")
}
foreach ($requiredOption in @(
    "--reviewed-dependency-injection",
    "--owner-approval",
    "--section13-evidence"
)) {
    $requiredPath = [string]$RappValues[$requiredOption]
    if (-not $requiredPath -or -not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        return (Stop-RappRestored ($requiredOption + " evidence is required"))
    }
}
return (Stop-RappRestored "authenticated fresh section-13 evidence is unavailable")
}
function Test-RappRestoredStandaloneProcess {
    foreach ($processArgument in [Environment]::GetCommandLineArgs()) {
        if ($processArgument -ieq "-File") {
            return $true
        }
    }
    return $false
}
$RappGateCode = Invoke-RappRestoredGate
if (Test-RappRestoredStandaloneProcess) {
    exit $RappGateCode
}
$global:LASTEXITCODE = $RappGateCode
return
# RAPP_RESTORED_GATE_END
$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  RAPP Hippocampus - Local Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── Helpers ─────────────────────────────────────────────────

function Find-Python {
    foreach ($cmd in @("python3.11", "python3.12", "python311", "python312")) {
        $fullPath = Get-Command $cmd -ErrorAction SilentlyContinue
        if ($fullPath) {
            $ver = & $fullPath.Source --version 2>&1
            if ($ver -match "Python 3\.(11|12)") { return $fullPath.Source }
        }
    }
    # Try py launcher
    try {
        $ver = & py -3.11 --version 2>&1
        if ($ver -match "Python 3\.11") { return "py -3.11" }
    } catch {}
    try {
        $ver = & py -3.12 --version 2>&1
        if ($ver -match "Python 3\.12") { return "py -3.12" }
    } catch {}
    # Check standard install locations
    foreach ($p in @(
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "C:\Python311\python.exe",
        "C:\Python312\python.exe"
    )) {
        if (Test-Path $p) {
            $ver = & $p --version 2>&1
            if ($ver -match "Python 3\.(11|12)") { return $p }
        }
    }
    return $null
}

# ── Prerequisites ───────────────────────────────────────────
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

# Git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Git..." -ForegroundColor Yellow
    winget install Git.Git --accept-source-agreements --accept-package-agreements
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}
Write-Host "[OK] Git" -ForegroundColor Green

# Python
$PYTHON_CMD = Find-Python
if (-not $PYTHON_CMD) {
    Write-Host "Installing Python 3.11..." -ForegroundColor Yellow
    winget install Python.Python.3.11 --accept-source-agreements --accept-package-agreements
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    Start-Sleep -Seconds 3
    $PYTHON_CMD = Find-Python
    if (-not $PYTHON_CMD) {
        Write-Host "[X] Python 3.11+ required (3.13+ not supported). Install from https://python.org" -ForegroundColor Red
        exit 1
    }
}
$pyVer = if ($PYTHON_CMD -match "^py ") { & py $PYTHON_CMD.Substring(3) --version 2>&1 } else { & $PYTHON_CMD --version 2>&1 }
Write-Host "[OK] $pyVer" -ForegroundColor Green

# Azure Functions Core Tools
if (-not (Get-Command func -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Azure Functions Core Tools..." -ForegroundColor Yellow
    winget install Microsoft.Azure.FunctionsCoreTools --accept-source-agreements --accept-package-agreements
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}
Write-Host "[OK] Azure Functions Core Tools" -ForegroundColor Green

# ── Project name ────────────────────────────────────────────

$ProjectName = $args[0]
if (-not $ProjectName) {
    Write-Host ""
    $ProjectName = Read-Host "Project name (e.g. my-project)"
    if (-not $ProjectName) { Write-Host "[X] Project name is required." -ForegroundColor Red; exit 1 }
}

if ($ProjectName -notmatch '^[a-z0-9][a-z0-9-]*$') {
    Write-Host "[X] Invalid name '$ProjectName'. Use lowercase letters, numbers, and hyphens." -ForegroundColor Red
    exit 1
}

$ProjectsDir = if ($env:RAPP_PROJECTS_DIR) { $env:RAPP_PROJECTS_DIR } else { Join-Path $HOME "rapp-projects" }
$ProjectDir = Join-Path $ProjectsDir $ProjectName

if (Test-Path $ProjectDir) {
    Write-Host "[X] Project '$ProjectName' already exists at $ProjectDir" -ForegroundColor Red
    exit 1
}

# ── Clone ───────────────────────────────────────────────────
Write-Host ""
Write-Host "Creating project '$ProjectName'..." -ForegroundColor Yellow

if (-not (Test-Path $ProjectsDir)) { New-Item -ItemType Directory -Path $ProjectsDir -Force | Out-Null }

Write-Host "Cloning CommunityRAPP..." -ForegroundColor Yellow
git clone --depth 1 --quiet https://github.com/kody-w/CommunityRAPP.git $ProjectDir
Write-Host "[OK] Cloned" -ForegroundColor Green

# ── Venv + deps ─────────────────────────────────────────────
Write-Host "Creating virtual environment..." -ForegroundColor Yellow
if ($PYTHON_CMD -match "^py ") {
    & py $PYTHON_CMD.Substring(3) -m venv "$ProjectDir\.venv"
} else {
    & $PYTHON_CMD -m venv "$ProjectDir\.venv"
}

Write-Host "Installing dependencies..." -ForegroundColor Yellow
& "$ProjectDir\.venv\Scripts\pip.exe" install -r "$ProjectDir\requirements.txt" --quiet 2>$null
Write-Host "[OK] Dependencies installed" -ForegroundColor Green

# ── Settings ────────────────────────────────────────────────
$template = Join-Path $ProjectDir "local.settings.template.json"
$settings = Join-Path $ProjectDir "local.settings.json"
if (Test-Path $template) { Copy-Item $template $settings }

# ── Port + start script ────────────────────────────────────
$Port = 7072
$Manifest = Join-Path $ProjectsDir ".hatchery.json"

if (Test-Path $Manifest) {
    try {
        $data = Get-Content $Manifest -Raw | ConvertFrom-Json
        $maxPort = ($data.projects.PSObject.Properties | ForEach-Object { $_.Value.port } | Sort-Object | Select-Object -Last 1)
        if ($maxPort -ge $Port) { $Port = $maxPort + 1 }
    } catch {}
}

@"
#!/usr/bin/env bash
cd "`$(dirname "`$0")"
source .venv/bin/activate
func start --port $Port
"@ | Set-Content "$ProjectDir\start.sh" -Encoding utf8NoBOM

@"
`$ErrorActionPreference = 'Stop'
Set-Location `$PSScriptRoot
.venv\Scripts\Activate.ps1
func start --port $Port
"@ | Set-Content "$ProjectDir\start.ps1" -Encoding utf8NoBOM

# Inject port into chat UI
$indexHtml = Join-Path $ProjectDir "index.html"
if (Test-Path $indexHtml) {
    $content = Get-Content $indexHtml -Raw
    $content = $content -replace '</head>', "<script>window.__RAPP_PORT__='$Port';</script></head>"
    Set-Content $indexHtml -Value $content -Encoding utf8NoBOM
}

# Remove hatchery/ (brainstem distribution only)
$hatcheryDir = Join-Path $ProjectDir "hatchery"
if (Test-Path $hatcheryDir) { Remove-Item -Recurse -Force $hatcheryDir }

# ── Business Mode UI ────────────────────────────────────────
$BizHtml = Join-Path $ProjectsDir "business.html"
if (-not (Test-Path $BizHtml)) {
    try {
        Invoke-WebRequest -Uri "https://raw.githubusercontent.com/kody-w/CommunityRAPP/main/business.html" -OutFile $BizHtml -UseBasicParsing
    } catch {}
}

# ── Update manifest ─────────────────────────────────────────
$Timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

if (Test-Path $Manifest) {
    $data = Get-Content $Manifest -Raw | ConvertFrom-Json
} else {
    $data = @{ projects = @{} }
}

$data.projects | Add-Member -NotePropertyName $ProjectName -NotePropertyValue @{
    path = $ProjectDir
    port = $Port
    created_at = $Timestamp
    python = $PYTHON_CMD
} -Force

$data | ConvertTo-Json -Depth 5 | Set-Content $Manifest -Encoding utf8NoBOM

# ── Done ────────────────────────────────────────────────────
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Project '$ProjectName' is ready!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Location:  $ProjectDir"
Write-Host "  Port:      $Port"
Write-Host "  Python:    $PYTHON_CMD"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host ""
Write-Host "  1. Start it:"
Write-Host "     cd $ProjectDir; .\start.ps1"
Write-Host ""
Write-Host "  2. Open the chat UI:"
Write-Host "     Start-Process `"$ProjectDir\index.html`""
Write-Host ""
Write-Host "  3. Send a message - the UI walks you through GitHub auth."
Write-Host "     No API keys needed."
Write-Host ""
if (Test-Path $BizHtml) {
    Write-Host "  4. Business Mode (multi-instance side-by-side):"
    Write-Host "     Start-Process `"$BizHtml`""
    Write-Host ""
}
Write-Host "  When you're ready for Azure:" -ForegroundColor White
Write-Host "     Edit $ProjectDir\local.settings.json"
Write-Host "     Then: func azure functionapp publish YOUR_APP --build remote"
Write-Host ""
