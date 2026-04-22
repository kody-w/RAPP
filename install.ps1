# RAPP Brainstem Installer for Windows
# Usage:
#   irm https://raw.githubusercontent.com/kody-w/RAPP/main/install.ps1 | iex
#
# Project-local install (scoped to current directory, own port, own agents,
# gitignored — runs alongside any global brainstem):
#   $env:BRAINSTEM_LOCAL = "1"
#   irm https://raw.githubusercontent.com/kody-w/RAPP/main/install.ps1 | iex
#
# or equivalent:
#   $env:RAPP_INSTALL_MODE = "local"; irm ... | iex
#
# AGENT HANDSHAKE: agents (Copilot CLI, Claude Code, etc.) running this
# installer set $env:RAPP_INSTALL_ASSIST = "1" and the script prints a
# structured prompt describing the two modes and exits. The agent then
# asks the user and re-invokes with $env:RAPP_INSTALL_MODE="global|local".
# Humans running the plain one-liner never see the handshake.
#
# Works on a factory Windows 11 install — auto-installs Python, Git, and GitHub CLI via winget.

$ErrorActionPreference = "Stop"

# ── Install mode: global (default) vs. project-local ────────────────
$LOCAL_MODE = $false
if ($env:BRAINSTEM_LOCAL -eq "1") { $LOCAL_MODE = $true }
switch ($env:RAPP_INSTALL_MODE) {
    "local"  { $LOCAL_MODE = $true }
    "global" { $LOCAL_MODE = $false }
}

# Agent-assist handshake: fire only if an agent asked for assist AND
# no explicit mode has been chosen yet.
$ModeChosen = $false
if ($LOCAL_MODE) { $ModeChosen = $true }
if ($env:RAPP_INSTALL_MODE) { $ModeChosen = $true }
if ($env:RAPP_INSTALL_ASSIST -eq "1" -and -not $ModeChosen) {
    @'
<<<RAPP_INSTALLER_HANDSHAKE v=1>>>

RAPP Brainstem — local-first AI agent server, powered by GitHub Copilot.
Full skill manifest (learnable context, agent protocol, architecture):
  https://kody-w.github.io/RAPP/skill.md
Fetch that once and cache it as your skill for rapp-brainstem.

QUESTION FOR THE USER — pick one of two install modes:

  GLOBAL (recommended default) — one brainstem for the whole machine.
    Installs at $env:USERPROFILE\.brainstem. Runs on port 7071. Has a
    `brainstem` CLI and auto-starts at logon.
    Re-invoke as:
      $env:RAPP_INSTALL_MODE = "global"; irm https://raw.githubusercontent.com/kody-w/RAPP/main/install.ps1 | iex

  LOCAL — project-scoped brainstem for the current directory.
    Installs at .\.brainstem\. Picks its own port (7072+). No global
    CLI, no background service. Gitignored automatically. Runs
    alongside the global brainstem if one exists.
    Re-invoke as (from the target project directory):
      $env:RAPP_INSTALL_MODE = "local"; irm https://raw.githubusercontent.com/kody-w/RAPP/main/install.ps1 | iex

HEURISTIC — if the user is inside a specific project or repo and
mentioned isolation, suggest LOCAL. Otherwise suggest GLOBAL.

NOTE — In PowerShell, set the env var as a statement BEFORE the `irm | iex`
(env must live in the session that runs iex, not just the web fetch).

<<<END_RAPP_INSTALLER_HANDSHAKE>>>
'@ | Write-Host
    exit 0
}

if ($LOCAL_MODE) {
    $BRAINSTEM_HOME = Join-Path (Get-Location).Path ".brainstem"
} else {
    $BRAINSTEM_HOME = "$env:USERPROFILE\.brainstem"
}
$BRAINSTEM_BIN = "$env:USERPROFILE\.local\bin"
$VENV_DIR = "$BRAINSTEM_HOME\venv"
$VENV_PY = "$VENV_DIR\Scripts\python.exe"
$REPO_URL = "https://github.com/kody-w/RAPP.git"
$REMOTE_VERSION_URL = "https://raw.githubusercontent.com/kody-w/RAPP/main/rapp_brainstem/VERSION"

function Print-Banner {
    Write-Host ""
    Write-Host "  🧠 RAPP Brainstem" -ForegroundColor Cyan
    Write-Host "  Local-first AI agent server" -ForegroundColor Gray
    Write-Host "  Powered by GitHub Copilot — no API keys needed" -ForegroundColor Gray
    Write-Host ""
}

function Compare-SemVer {
    param([string]$Local, [string]$Remote)
    $lParts = $Local.Split('.')
    $rParts = $Remote.Split('.')
    for ($i = 0; $i -lt [Math]::Max($lParts.Length, $rParts.Length); $i++) {
        $lv = if ($i -lt $lParts.Length) { [int]$lParts[$i] } else { 0 }
        $rv = if ($i -lt $rParts.Length) { [int]$rParts[$i] } else { 0 }
        if ($rv -gt $lv) { return 1 }   # remote is newer
        if ($rv -lt $lv) { return -1 }  # local is newer
    }
    return 0  # equal
}

function Check-ForUpgrade {
    $versionFile = "$BRAINSTEM_HOME\src\rapp_brainstem\VERSION"

    if (-not (Test-Path $versionFile)) { return $true }

    $localVersion = (Get-Content $versionFile -Raw).Trim()

    try {
        $remoteVersion = (Invoke-WebRequest -Uri $REMOTE_VERSION_URL -UseBasicParsing -TimeoutSec 10).Content.Trim()
    } catch {
        Write-Host "  [!] Could not check remote version — upgrading anyway" -ForegroundColor Yellow
        return $true
    }

    Write-Host "  Local version:  $localVersion" -ForegroundColor Cyan
    Write-Host "  Remote version: $remoteVersion" -ForegroundColor Cyan

    if ($localVersion -eq $remoteVersion) {
        Write-Host ""
        Write-Host "  [OK] Already up to date (v$localVersion)" -ForegroundColor Green
        Write-Host ""
        return $false
    }

    $cmp = Compare-SemVer -Local $localVersion -Remote $remoteVersion
    if ($cmp -eq 1) {
        Write-Host "  [..] Upgrade available: $localVersion -> $remoteVersion" -ForegroundColor Yellow
        return $true
    }

    Write-Host ""
    Write-Host "  [OK] Already up to date (v$localVersion)" -ForegroundColor Green
    Write-Host ""
    return $false
}

function Install-WithWinget {
    param([string]$PackageId, [string]$Name)
    Write-Host "  [..] Installing $Name via winget..." -ForegroundColor Yellow
    winget install --id $PackageId --accept-source-agreements --accept-package-agreements --silent 2>&1 | Out-Null
    # Refresh PATH for this session
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}

function Check-Prerequisites {
    Write-Host "Checking prerequisites..."

    # winget (ships with Windows 11)
    try {
        winget --version 2>&1 | Out-Null
    } catch {
        Write-Host "  [X] winget not found — this installer requires Windows 10 1709+ or Windows 11" -ForegroundColor Red
        exit 1
    }

    # Git
    $gitOk = $false
    try {
        $gitVersion = git --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK] $gitVersion" -ForegroundColor Green
            $gitOk = $true
        }
    } catch {}
    if (-not $gitOk) {
        Install-WithWinget "Git.Git" "Git"
        try {
            git --version 2>&1 | Out-Null
            Write-Host "  [OK] Git installed" -ForegroundColor Green
        } catch {
            Write-Host "  [X] Git install failed — install manually from https://git-scm.com" -ForegroundColor Red
            exit 1
        }
    }

    # Python 3.11+
    $pythonOk = $false
    $pythonCmd = $null

    # Try multiple python command names (python3 first on some systems, then python)
    foreach ($cmd in @("python3", "python")) {
        try {
            $out = & $cmd --version 2>&1
            if ($LASTEXITCODE -eq 0 -and $out -match "Python 3\.(\d+)") {
                $minor = [int]$Matches[1]
                if ($minor -ge 11) {
                    Write-Host "  [OK] $out" -ForegroundColor Green
                    $pythonOk = $true
                    $pythonCmd = $cmd
                    break
                }
            }
        } catch {}
    }

    if (-not $pythonOk) {
        # Disable Windows App Execution Aliases that shadow real python
        # These stubs print "Python was not found" and prevent detection
        $aliasDir = "$env:LOCALAPPDATA\Microsoft\WindowsApps"
        foreach ($stub in @("python.exe", "python3.exe")) {
            $stubPath = Join-Path $aliasDir $stub
            if (Test-Path $stubPath) {
                try {
                    $target = (Get-Item $stubPath).Target
                    if (-not $target) {
                        # It's an App Execution Alias stub — rename it out of the way
                        Rename-Item $stubPath "$stub.disabled" -ErrorAction SilentlyContinue
                        Write-Host "  [..] Disabled Windows Store python stub" -ForegroundColor Yellow
                    }
                } catch {}
            }
        }

        Install-WithWinget "Python.Python.3.11" "Python 3.11"

        # winget installs to a known path — add it explicitly
        $pyBase = "$env:LOCALAPPDATA\Programs\Python\Python311"
        if (Test-Path $pyBase) {
            $env:Path = "$pyBase;$pyBase\Scripts;$env:Path"
        }
        # Also refresh from registry
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

        # Verify the REAL python is now reachable
        $pythonOk = $false
        foreach ($cmd in @("python3", "python")) {
            try {
                $out = & $cmd --version 2>&1
                if ($LASTEXITCODE -eq 0 -and $out -match "Python 3\.(\d+)") {
                    Write-Host "  [OK] $out installed" -ForegroundColor Green
                    $pythonOk = $true
                    $pythonCmd = $cmd
                    break
                }
            } catch {}
        }

        # Last resort: try the known install path directly
        if (-not $pythonOk) {
            $directPy = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
            if (Test-Path $directPy) {
                $out = & $directPy --version 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "  [OK] $out installed (direct path)" -ForegroundColor Green
                    $pythonOk = $true
                    $pythonCmd = $directPy
                }
            }
        }

        if (-not $pythonOk) {
            Write-Host "  [X] Python install failed — install from https://python.org" -ForegroundColor Red
            Write-Host "      Make sure to check 'Add Python to PATH' during install" -ForegroundColor Yellow
            exit 1
        }
    }

    # Store the working python command for later use
    $script:PythonExe = $pythonCmd

    # GitHub CLI (optional but recommended)
    try {
        gh --version 2>&1 | Out-Null
        Write-Host "  [OK] GitHub CLI installed" -ForegroundColor Green
    } catch {
        Write-Host "  [..] Installing GitHub CLI..." -ForegroundColor Yellow
        Install-WithWinget "GitHub.cli" "GitHub CLI"
        try {
            gh --version 2>&1 | Out-Null
            Write-Host "  [OK] GitHub CLI installed" -ForegroundColor Green
        } catch {
            Write-Host "  [!] GitHub CLI not installed (optional — you can authenticate later)" -ForegroundColor Yellow
        }
    }
}

function Install-Brainstem {
    Write-Host ""
    Write-Host "Installing RAPP Brainstem..."

    if (-not (Test-Path $BRAINSTEM_HOME)) {
        New-Item -ItemType Directory -Force -Path $BRAINSTEM_HOME | Out-Null
    }

    if (Test-Path "$BRAINSTEM_HOME\src\.git") {
        # Smart update — preserve soul, agents, config
        $LocalVer = "0.0.0"
        $VerFile = "$BRAINSTEM_HOME\src\rapp_brainstem\VERSION"
        if (Test-Path $VerFile) { $LocalVer = (Get-Content $VerFile -Raw).Trim() }
        try { $RemoteVer = (Invoke-WebRequest -Uri $REMOTE_VERSION_URL -UseBasicParsing -TimeoutSec 5).Content.Trim() } catch { $RemoteVer = "0.0.0" }

        Write-Host "  Local:  v$LocalVer"
        Write-Host "  Remote: v$RemoteVer"

        if ($LocalVer -eq $RemoteVer) {
            Write-Host "  [OK] Already up to date (v$LocalVer)" -ForegroundColor Green
        } else {
            Write-Host "  Upgrading v$LocalVer -> v$RemoteVer..."
            $Backup = "$env:TEMP\brainstem-upgrade-$(Get-Random)"
            New-Item -ItemType Directory -Force -Path $Backup | Out-Null

            # Backup user files
            $AgentsDir = "$BRAINSTEM_HOME\src\rapp_brainstem\agents"
            $SoulFile = "$BRAINSTEM_HOME\src\rapp_brainstem\soul.md"
            $EnvFile = "$BRAINSTEM_HOME\src\rapp_brainstem\.env"
            if (Test-Path $SoulFile) { Copy-Item $SoulFile "$Backup\soul.md" }
            if (Test-Path $EnvFile) { Copy-Item $EnvFile "$Backup\.env" }
            if (Test-Path $AgentsDir) { Copy-Item "$AgentsDir\*.py" "$Backup\" -ErrorAction SilentlyContinue }
            Write-Host "  [OK] Backed up soul, agents, config" -ForegroundColor Green

            # Pull latest
            Push-Location "$BRAINSTEM_HOME\src"
            try { git stash --quiet 2>&1 | Out-Null } catch {}
            try { git pull --quiet 2>&1 | Out-Null } catch {}
            Pop-Location
            Write-Host "  [OK] Framework updated" -ForegroundColor Green

            # Restore user files
            if (Test-Path "$Backup\soul.md") { Copy-Item "$Backup\soul.md" $SoulFile -Force }
            if (Test-Path "$Backup\.env") { Copy-Item "$Backup\.env" $EnvFile -Force }
            Get-ChildItem "$Backup\*.py" -ErrorAction SilentlyContinue | ForEach-Object {
                if ($_.Name -notin @("basic_agent.py", "__init__.py")) {
                    Copy-Item $_.FullName "$AgentsDir\$($_.Name)" -Force
                }
            }
            Remove-Item -Recurse -Force $Backup -ErrorAction SilentlyContinue
            Write-Host "  [OK] Upgrade complete: v$LocalVer -> v$RemoteVer" -ForegroundColor Green
        }
    } else {
        if (Test-Path "$BRAINSTEM_HOME\src") {
            Remove-Item -Recurse -Force "$BRAINSTEM_HOME\src" -ErrorAction SilentlyContinue
        }
        Write-Host "  Cloning repository..."
        git clone --quiet $REPO_URL "$BRAINSTEM_HOME\src" 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  [X] Failed to clone repository" -ForegroundColor Red
            exit 1
        }
    }
    Write-Host "  [OK] Source code ready" -ForegroundColor Green
}

function Setup-Venv {
    # Create/repair the venv. Using a fixed absolute path here means the
    # Scheduled Task can invoke python without relying on PATH resolution.
    if (Test-Path $VENV_PY) {
        try {
            & $VENV_PY -c "import sys; sys.exit(0)" 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  [OK] Virtual environment OK" -ForegroundColor Green
                return
            }
        } catch {}
        Write-Host "  [!] Virtual environment broken, recreating..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force $VENV_DIR -ErrorAction SilentlyContinue
    }

    $py = if ($script:PythonExe) { $script:PythonExe } else { "python" }
    Write-Host "  Creating virtual environment..."
    & $py -m venv $VENV_DIR 2>&1 | Out-Null
    if (-not (Test-Path $VENV_PY)) {
        & $py -m ensurepip 2>&1 | Out-Null
        & $py -m venv $VENV_DIR 2>&1 | Out-Null
    }
    if (-not (Test-Path $VENV_PY)) {
        Write-Host "  [X] Failed to create virtual environment" -ForegroundColor Red
        exit 1
    }
    & $VENV_PY -m pip install --upgrade pip --quiet 2>&1 | Out-Null
    Write-Host "  [OK] Virtual environment ready" -ForegroundColor Green
}

function Run-PipInstall {
    $reqFile = "$BRAINSTEM_HOME\src\rapp_brainstem\requirements.txt"
    $py = if (Test-Path $VENV_PY) { $VENV_PY } elseif ($script:PythonExe) { $script:PythonExe } else { "python" }
    $proc = Start-Process -FilePath $py -ArgumentList "-m", "pip", "install", "-r", $reqFile -NoNewWindow -Wait -PassThru
    if ($proc.ExitCode -ne 0) {
        Start-Process -FilePath $py -ArgumentList "-m", "pip", "install", "-r", $reqFile, "--user" -NoNewWindow -Wait -PassThru | Out-Null
    }
}

function Check-PythonDeps {
    $py = if (Test-Path $VENV_PY) { $VENV_PY } elseif ($script:PythonExe) { $script:PythonExe } else { "python" }
    $proc = Start-Process -FilePath $py -ArgumentList "-c", "import flask, flask_cors, requests, dotenv" -NoNewWindow -Wait -PassThru
    return $proc.ExitCode -eq 0
}

function Setup-Dependencies {
    Write-Host ""
    Write-Host "Installing dependencies..."
    Push-Location "$BRAINSTEM_HOME\src\rapp_brainstem"
    Run-PipInstall
    if (-not (Check-PythonDeps)) {
        Write-Host "  [!] Some dependencies may not have installed correctly" -ForegroundColor Yellow
    }
    Pop-Location
    Write-Host "  [OK] Dependencies installed" -ForegroundColor Green
}

function Install-CLI {
    Write-Host ""
    Write-Host "Installing CLI..."

    if (-not (Test-Path $BRAINSTEM_BIN)) {
        New-Item -ItemType Directory -Force -Path $BRAINSTEM_BIN | Out-Null
    }
    $logDir = "$BRAINSTEM_HOME\logs"
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    }

    $py = if ($script:PythonExe) { $script:PythonExe } else { "python" }

    # PowerShell subcommand dispatcher — the authoritative wrapper.
    # Matches the macOS/Linux bash wrapper: start / stop / restart /
    # status / logs / doctor / run / open + default (start-then-open).
    $psContent = @'
# RAPP Brainstem CLI wrapper (Windows)
param([Parameter(Position=0)][string]$Command = 'default', [Parameter(ValueFromRemainingArguments=$true)][string[]]$Rest)
$BRAINSTEM_HOME = "$env:USERPROFILE\.brainstem"
$SRC            = "$BRAINSTEM_HOME\src\rapp_brainstem"
$VENV_PY        = "$BRAINSTEM_HOME\venv\Scripts\python.exe"
$LOG            = "$BRAINSTEM_HOME\logs\brainstem.log"
$URL            = "http://localhost:7071"
$TASK           = "RAPP-Brainstem"

function Test-ServiceInstalled {
    try { $null = Get-ScheduledTask -TaskName $TASK -ErrorAction Stop; return $true } catch { return $false }
}

function Invoke-Start {
    if (Test-ServiceInstalled) {
        try { Start-ScheduledTask -TaskName $TASK; Write-Host "[OK] Service started ($TASK)" -ForegroundColor Green } catch { Write-Host "[!] Could not start task: $_" -ForegroundColor Yellow }
    } else {
        Write-Host "[!] No background task installed — running in foreground (Ctrl-C to stop)." -ForegroundColor Yellow
        Invoke-Run
    }
}
function Invoke-Stop {
    if (Test-ServiceInstalled) {
        try { Stop-ScheduledTask -TaskName $TASK -ErrorAction SilentlyContinue; Write-Host "[OK] Service stopped" -ForegroundColor Green } catch {}
    } else { Write-Host "[!] No background task installed." -ForegroundColor Yellow }
}
function Invoke-Restart { Invoke-Stop; Start-Sleep -Seconds 1; Invoke-Start }
function Invoke-Status {
    try {
        $r = Invoke-WebRequest -Uri "$URL/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        if ($r.StatusCode -eq 200) { Write-Host "[UP] Brainstem at $URL (HTTP 200)" -ForegroundColor Green; $r.Content.Substring(0, [Math]::Min(400,$r.Content.Length)) }
    } catch {
        Write-Host "[DOWN] Brainstem not responding at $URL" -ForegroundColor Red
    }
    Write-Host ""
    if (Test-ServiceInstalled) {
        $t = Get-ScheduledTask -TaskName $TASK
        $i = Get-ScheduledTaskInfo -TaskName $TASK
        Write-Host "Task: $TASK"
        Write-Host "  State: $($t.State)"
        Write-Host "  LastRunTime: $($i.LastRunTime)"
        Write-Host "  LastResult:  $($i.LastTaskResult)"
    } else { Write-Host "Task: (not installed — foreground-only)" }
}
function Invoke-Logs {
    if (Test-Path $LOG) { Get-Content -Path $LOG -Tail 200 -Wait } else { Write-Host "no log at $LOG" }
}
function Invoke-Run {
    Push-Location $SRC
    try { & $VENV_PY brainstem.py @Rest } finally { Pop-Location }
}
function Invoke-Open { Start-Process $URL }
function Invoke-Doctor {
    Write-Host "=== RAPP Brainstem doctor ==="
    Write-Host ""
    Write-Host "Install path: $BRAINSTEM_HOME"
    Write-Host "Source:       $SRC"
    Write-Host "Venv python:  $VENV_PY $(if (Test-Path $VENV_PY) { '(OK)' } else { '(MISSING)' })"
    $v = if (Test-Path "$SRC\VERSION") { (Get-Content "$SRC\VERSION" -Raw).Trim() } else { '?' }
    Write-Host "Version:      $v"
    Write-Host "Log file:     $LOG"
    Write-Host "OS:           Windows"
    Write-Host ""
    Write-Host "=== Task state ==="
    if (Test-ServiceInstalled) {
        $t = Get-ScheduledTask -TaskName $TASK; $i = Get-ScheduledTaskInfo -TaskName $TASK
        Write-Host "Task:        $TASK (present)"
        Write-Host "State:       $($t.State)"
        Write-Host "LastRunTime: $($i.LastRunTime)"
        Write-Host "LastResult:  $($i.LastTaskResult)"
    } else { Write-Host "Task: (not installed)" }
    Write-Host ""
    Write-Host "=== /health ==="
    try { (Invoke-WebRequest -Uri "$URL/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop).Content } catch { Write-Host "(unreachable)" }
    Write-Host ""
    Write-Host "=== Last 40 log lines ==="
    if (Test-Path $LOG) { Get-Content -Path $LOG -Tail 40 } else { Write-Host "(no log yet)" }
    Write-Host ""
    Write-Host "=== End doctor report ==="
}
function Show-Help {
@"
Usage: brainstem [COMMAND]

With no command, starts the service and opens the browser.

  start     Start the background Scheduled Task
  stop      Stop the Scheduled Task
  restart   Restart the Scheduled Task
  status    One-line health check + task state
  logs      Tail the service log
  doctor    Paste-to-support troubleshooting dump
  run       Run in the foreground (for debugging)
  open      Open http://localhost:7071 in your browser
  help      Show this message
"@
}

switch ($Command) {
    'start'   { Invoke-Start; break }
    'stop'    { Invoke-Stop; break }
    'restart' { Invoke-Restart; break }
    'status'  { Invoke-Status; break }
    'logs'    { Invoke-Logs; break }
    'doctor'  { Invoke-Doctor; break }
    'run'     { Invoke-Run; break }
    'open'    { Invoke-Open; break }
    { $_ -in @('help','-h','--help') } { Show-Help; break }
    'default' {
        Invoke-Start
        for ($i = 0; $i -lt 10; $i++) {
            try { if ((Invoke-WebRequest -Uri "$URL/health" -UseBasicParsing -TimeoutSec 1 -ErrorAction Stop).StatusCode -eq 200) { break } } catch {}
            Start-Sleep -Seconds 1
        }
        Invoke-Open
        break
    }
    default { Write-Host "Unknown command: $Command"; Show-Help; exit 1 }
}
'@
    Set-Content -Path "$BRAINSTEM_BIN\brainstem.ps1" -Value $psContent -Encoding UTF8

    # CMD wrapper invokes the PowerShell wrapper so `brainstem` works from
    # cmd.exe, PowerShell, Run dialog, shortcuts, everywhere.
    $cmdContent = @"
@echo off
powershell -ExecutionPolicy Bypass -NoProfile -File "$BRAINSTEM_BIN\brainstem.ps1" %*
"@
    Set-Content -Path "$BRAINSTEM_BIN\brainstem.cmd" -Value $cmdContent

    # Add to PATH if not already there
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($userPath -notlike "*$BRAINSTEM_BIN*") {
        [Environment]::SetEnvironmentVariable("Path", "$BRAINSTEM_BIN;$userPath", "User")
        $env:Path = "$BRAINSTEM_BIN;$env:Path"
        Write-Host "  Added to PATH" -ForegroundColor Green
    }

    Write-Host "  [OK] CLI installed" -ForegroundColor Green
}

function Install-Service {
    # Register a user-level Scheduled Task that runs the brainstem at
    # logon and restarts on failure. No admin needed. If registration
    # fails, Launch-Brainstem falls back to the old foreground-run path.
    Write-Host ""
    Write-Host "Installing background service..."
    $task = "RAPP-Brainstem"
    $py = "$BRAINSTEM_HOME\venv\Scripts\python.exe"
    $src = "$BRAINSTEM_HOME\src\rapp_brainstem"
    $log = "$BRAINSTEM_HOME\logs\brainstem.log"
    $errLog = "$BRAINSTEM_HOME\logs\brainstem.err.log"

    if (-not (Test-Path $py)) {
        Write-Host "  [!] Venv python missing, skipping service install" -ForegroundColor Yellow
        return
    }

    # Remove any prior task so the new config lands cleanly.
    try { Unregister-ScheduledTask -TaskName $task -Confirm:$false -ErrorAction SilentlyContinue } catch {}

    try {
        # ScheduledTasks native cmdlets are the right tool; no XML round-trip.
        # Redirect stdout/stderr through cmd.exe so logs land on disk the
        # same way launchd/systemd redirect StandardOutPath.
        $cmd = "cmd.exe"
        $cmdArgs = "/c `"`"$py`" brainstem.py 1>>`"$log`" 2>>`"$errLog`"`""
        $action = New-ScheduledTaskAction -Execute $cmd -Argument $cmdArgs -WorkingDirectory $src
        $trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
        $settings = New-ScheduledTaskSettingsSet `
            -AllowStartIfOnBatteries `
            -DontStopIfGoingOnBatteries `
            -RestartCount 999 `
            -RestartInterval (New-TimeSpan -Minutes 1) `
            -StartWhenAvailable `
            -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
            -Hidden
        $principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive
        $def = New-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "RAPP Brainstem — local-first AI agent server (user service)"
        Register-ScheduledTask -TaskName $task -InputObject $def -Force | Out-Null

        # Kick it off immediately.
        Start-ScheduledTask -TaskName $task
        Write-Host "  [OK] Background service installed (Scheduled Task: $task)" -ForegroundColor Green
    } catch {
        Write-Host "  [!] Could not install Scheduled Task: $_" -ForegroundColor Yellow
    }
}

function Wait-ForHealth {
    param([int]$TimeoutSec = 15)
    $url = "http://localhost:7071/health"
    for ($i = 0; $i -lt $TimeoutSec; $i++) {
        try {
            $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 1 -ErrorAction Stop
            if ($r.StatusCode -eq 200) { return $true }
        } catch {}
        Start-Sleep -Seconds 1
    }
    return $false
}

function Create-Env {
    $envFile = "$BRAINSTEM_HOME\src\rapp_brainstem\.env"
    $exampleFile = "$BRAINSTEM_HOME\src\rapp_brainstem\.env.example"
    if (-not (Test-Path $envFile) -and (Test-Path $exampleFile)) {
        Copy-Item $exampleFile $envFile
    }
}

function Launch-Brainstem {
    # Always pull latest before launching
    if (Test-Path "$BRAINSTEM_HOME\src\.git") {
        Push-Location "$BRAINSTEM_HOME\src"
        try { git pull --quiet 2>&1 | Out-Null } catch {}
        Pop-Location
    }

    $tokenFile = "$BRAINSTEM_HOME\src\rapp_brainstem\.copilot_token"
    $clientId = "Iv1.b507a08c87ecfe98"

    # Check if already authenticated
    $needsAuth = $true
    if (Test-Path $tokenFile) {
        try {
            $tokenData = Get-Content $tokenFile -Raw | ConvertFrom-Json
            $savedToken = $tokenData.access_token
            if ($savedToken) {
                $authPrefix = if ($savedToken.StartsWith("ghu_")) { "token" } else { "Bearer" }
                $headers = @{
                    "Authorization" = "$authPrefix $savedToken"
                    "Accept" = "application/json"
                    "Editor-Version" = "vscode/1.95.0"
                    "Editor-Plugin-Version" = "copilot/1.0.0"
                }
                try {
                    $checkResp = Invoke-WebRequest -Uri "https://api.github.com/copilot_internal/v2/token" -Headers $headers -UseBasicParsing -TimeoutSec 10 -ErrorAction SilentlyContinue
                    if ($checkResp.StatusCode -eq 200) {
                        Write-Host "  [OK] Already authenticated with GitHub Copilot" -ForegroundColor Green
                        $needsAuth = $false
                    }
                } catch {
                    Write-Host "  [..] Saved token expired — re-authenticating..." -ForegroundColor Yellow
                    Remove-Item $tokenFile -Force -ErrorAction SilentlyContinue
                }
            }
        } catch {
            Remove-Item $tokenFile -Force -ErrorAction SilentlyContinue
        }
    }

    if ($needsAuth) {
        Write-Host ""
        Write-Host "  Authenticating with GitHub Copilot..." -ForegroundColor Cyan
        Write-Host ""

        try {
            $deviceResp = Invoke-RestMethod -Uri "https://github.com/login/device/code" -Method Post -ContentType "application/x-www-form-urlencoded" -Body "client_id=$clientId" -Headers @{"Accept"="application/json"} -TimeoutSec 10

            $userCode = $deviceResp.user_code
            $deviceCode = $deviceResp.device_code
            $interval = if ($deviceResp.interval) { $deviceResp.interval } else { 5 }
            $verifyUri = $deviceResp.verification_uri

            if (-not $userCode -or -not $deviceCode) {
                Write-Host "  [!] Could not start auth — sign in at http://localhost:7071/login" -ForegroundColor Yellow
            } else {
                Write-Host "  ┌─────────────────────────────────────────┐"
                Write-Host "  │  Your code: " -NoNewline; Write-Host $userCode -ForegroundColor Cyan -NoNewline; Write-Host "                  │"
                Write-Host "  └─────────────────────────────────────────┘"
                Write-Host ""
                Write-Host "  Opening browser to authorize..."

                Start-Process $verifyUri
                Write-Host "  Waiting for authorization..."
                Write-Host ""

                for ($i = 0; $i -lt 60; $i++) {
                    Start-Sleep -Seconds $interval
                    try {
                        $pollResp = Invoke-RestMethod -Uri "https://github.com/login/oauth/access_token" -Method Post -ContentType "application/x-www-form-urlencoded" -Body "client_id=$clientId&device_code=$deviceCode&grant_type=urn:ietf:params:oauth:grant-type:device_code" -Headers @{"Accept"="application/json"} -TimeoutSec 10

                        if ($pollResp.access_token) {
                            $tokenJson = @{ access_token = $pollResp.access_token }
                            if ($pollResp.refresh_token) { $tokenJson.refresh_token = $pollResp.refresh_token }
                            $tokenJson | ConvertTo-Json | Set-Content $tokenFile

                            # Validate Copilot access
                            $authPrefix = if ($pollResp.access_token.StartsWith("ghu_")) { "token" } else { "Bearer" }
                            $headers = @{
                                "Authorization" = "$authPrefix $($pollResp.access_token)"
                                "Accept" = "application/json"
                                "Editor-Version" = "vscode/1.95.0"
                                "Editor-Plugin-Version" = "copilot/1.0.0"
                            }
                            try {
                                $copilotCheck = Invoke-WebRequest -Uri "https://api.github.com/copilot_internal/v2/token" -Headers $headers -UseBasicParsing -TimeoutSec 10 -ErrorAction SilentlyContinue
                                if ($copilotCheck.StatusCode -eq 200) {
                                    Write-Host "  [OK] Authenticated — Copilot access confirmed" -ForegroundColor Green
                                }
                            } catch {
                                $statusCode = $_.Exception.Response.StatusCode.value__
                                if ($statusCode -eq 403) {
                                    Write-Host ""
                                    Write-Host "  [X] This GitHub account does NOT have Copilot access." -ForegroundColor Red
                                    Write-Host ""
                                    Write-Host "  Either:"
                                    Write-Host "    1. Sign up for Copilot: " -NoNewline; Write-Host "https://github.com/github-copilot/signup" -ForegroundColor Cyan
                                    Write-Host "    2. Re-run this installer and sign in with a different account"
                                    Write-Host ""
                                    Remove-Item $tokenFile -Force -ErrorAction SilentlyContinue
                                } else {
                                    Write-Host "  [OK] Authenticated with GitHub" -ForegroundColor Green
                                }
                            }
                            break
                        }

                        $error_code = $pollResp.error
                        if ($error_code -eq "expired_token") {
                            Write-Host "  [!] Auth timed out — sign in at http://localhost:7071/login" -ForegroundColor Yellow
                            break
                        }
                        if ($error_code -ne "authorization_pending" -and $error_code -ne "slow_down" -and $error_code) {
                            Write-Host "  [!] Auth error: $error_code" -ForegroundColor Yellow
                            break
                        }
                    } catch {}
                }
            }
        } catch {
            Write-Host "  [!] Could not start auth — sign in at http://localhost:7071/login" -ForegroundColor Yellow
        }
    }

    # Launch the server
    Write-Host ""
    Write-Host "  Starting RAPP Brainstem..." -ForegroundColor Cyan
    Write-Host ""

    Push-Location "$BRAINSTEM_HOME\src\rapp_brainstem"

    # Ensure deps are installed (handles first-run failure or stale install)
    if (-not (Check-PythonDeps)) {
        Write-Host "  [..] Installing missing dependencies..." -ForegroundColor Yellow
        Run-PipInstall
    }

    # Stop any previously-running brainstem on port 7071 before Install-Service
    # tries to take the port. Matches install.sh auto-kill behavior.
    try {
        $conn = Get-NetTCPConnection -LocalPort 7071 -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($conn) {
            $existingPid = $conn.OwningProcess
            Write-Host "  [!] Port 7071 busy (PID $existingPid) — stopping it" -ForegroundColor Yellow
            Stop-Process -Id $existingPid -Force -ErrorAction SilentlyContinue
            Start-Sleep -Milliseconds 500
        }
    } catch {}

    # Install + start the background Scheduled Task. Non-technical users
    # never have to think about "running a server" again — it auto-starts
    # at logon and auto-restarts on crash.
    Install-Service

    # Give the task up to 15s to cold-boot. On success, pop the browser
    # and return. On failure, fall back to foreground exec so the user
    # still ends up with a working brainstem.
    if (Wait-ForHealth 15) {
        Start-Process "http://localhost:7071"
        Pop-Location
        Write-Host ""
        Write-Host "  [OK] Brainstem is running at http://localhost:7071" -ForegroundColor Green
        Write-Host "  It'll auto-start at logon and auto-restart if it crashes."
        Write-Host ""
        Write-Host "  Manage with: brainstem start|stop|restart|status|logs|doctor" -ForegroundColor Cyan
        Write-Host ""
        return
    }

    Write-Host "  [!] Background service didn't come up — running in foreground instead." -ForegroundColor Yellow
    Write-Host ""
    Start-Job -ScriptBlock { Start-Sleep -Seconds 3; Start-Process "http://localhost:7071" } | Out-Null

    $py = if (Test-Path $VENV_PY) { $VENV_PY } elseif ($script:PythonExe) { $script:PythonExe } else { "python" }
    & $py brainstem.py
    Pop-Location
}

# ── Project-local helpers (--here / RAPP_INSTALL_MODE=local) ─────────

function Find-FreePort {
    param([int]$StartPort = 7072)
    $lim = $StartPort + 50
    for ($p = $StartPort; $p -lt $lim; $p++) {
        $inUse = $false
        try {
            $conn = Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue
            if ($conn) { $inUse = $true }
        } catch {
            # Fallback if Get-NetTCPConnection unavailable (older Windows)
            try {
                $tcp = New-Object System.Net.Sockets.TcpClient
                $iar = $tcp.BeginConnect("127.0.0.1", $p, $null, $null)
                $iar.AsyncWaitHandle.WaitOne(100) | Out-Null
                if ($tcp.Connected) { $inUse = $true }
                $tcp.Close()
            } catch {}
        }
        if (-not $inUse) { return $p }
    }
    return $StartPort
}

function Write-LocalLauncher {
    param([int]$Port)
    $launcher = Join-Path $BRAINSTEM_HOME "start.ps1"
    $content = @"
# Project-local RAPP brainstem launcher.
# Auto-generated by install.ps1. Safe to re-generate.
`$Here = Split-Path -Parent `$MyInvocation.MyCommand.Path
`$Src = Join-Path `$Here 'src\rapp_brainstem'
`$VenvPy = Join-Path `$Here 'venv\Scripts\python.exe'
Set-Location `$Src
`$env:PORT = '$Port'
& `$VenvPy brainstem.py @args
"@
    $content | Set-Content -Path $launcher -Encoding UTF8
    Set-Content -Path (Join-Path $BRAINSTEM_HOME "PORT") -Value "$Port" -Encoding UTF8
}

function Update-ProjectGitignore {
    # If cwd is inside a git repo, add .brainstem/ to its .gitignore.
    try {
        $repoRoot = (git rev-parse --show-toplevel 2>$null | Out-String).Trim()
    } catch { return }
    if (-not $repoRoot) { return }
    $gi = Join-Path $repoRoot ".gitignore"
    $line = ".brainstem/"
    if (Test-Path $gi) {
        $existing = Get-Content $gi -ErrorAction SilentlyContinue
        if ($existing -contains $line) { return }
    }
    Add-Content -Path $gi -Value "`r`n# Project-local RAPP brainstem (install.ps1)"
    Add-Content -Path $gi -Value $line
    Write-Host "  [OK] added $line to .gitignore" -ForegroundColor Green
}

function Main-Local {
    Print-Banner
    Write-Host "  Installing project-local brainstem at $BRAINSTEM_HOME" -ForegroundColor Cyan
    Write-Host "  (runs alongside any global brainstem on :7071 — this one picks its own port)"
    Write-Host ""

    Check-Prerequisites
    Install-Brainstem
    Setup-Venv
    Setup-Dependencies
    Create-Env

    $port = Find-FreePort -StartPort 7072
    Write-LocalLauncher -Port $port
    Update-ProjectGitignore

    $installedVersion = ""
    $vf = "$BRAINSTEM_HOME\src\rapp_brainstem\VERSION"
    if (Test-Path $vf) { $installedVersion = (Get-Content $vf -Raw).Trim() }

    Write-Host ""
    Write-Host "===================================================" -ForegroundColor Cyan
    Write-Host "  [OK] RAPP Brainstem v$installedVersion installed (project-local)" -ForegroundColor Green
    Write-Host "===================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  To start this project's brainstem:"
    Write-Host "    .\.brainstem\start.ps1" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  It'll run at http://localhost:$port" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Your global brainstem (if installed) keeps running at :7071."
    Write-Host "  Both can run concurrently."
    Write-Host ""
}

function Main {
    if ($LOCAL_MODE) {
        Main-Local
        return
    }

    Print-Banner

    # Check if this is an upgrade of an existing install
    if (Test-Path "$BRAINSTEM_HOME\src\.git") {
        Write-Host "Checking for updates..."
        if (-not (Check-ForUpgrade)) {
            # Already up to date — still verify venv + deps + CLI before launch
            Check-Prerequisites
            Setup-Venv
            Setup-Dependencies
            Install-CLI
            Create-Env
            Launch-Brainstem
            return
        }
    }

    Check-Prerequisites
    Install-Brainstem
    Setup-Venv
    Setup-Dependencies
    Install-CLI
    Create-Env

    $installedVersion = ""
    $vf = "$BRAINSTEM_HOME\src\rapp_brainstem\VERSION"
    if (Test-Path $vf) { $installedVersion = (Get-Content $vf -Raw).Trim() }

    Write-Host ""
    Write-Host "===================================================" -ForegroundColor Cyan
    Write-Host "  [OK] RAPP Brainstem v$installedVersion installed!" -ForegroundColor Green
    Write-Host "===================================================" -ForegroundColor Cyan
    Write-Host ""

    Launch-Brainstem
}

Main
