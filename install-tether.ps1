# RAPP Tether Installer (Windows)
# Usage: iwr https://kody-w.github.io/RAPP/install-tether.ps1 -useb | iex
#
# Companion to install.ps1 (the full local brainstem). Sets up
# tether/server.py — a stdlib-only Python HTTP server that exposes your
# local *_agent.py files to the virtual brainstem at
# https://kody-w.github.io/RAPP/brainstem/. No venv, no pip, no OAuth.

$ErrorActionPreference = "Stop"

$TetherHome = Join-Path $env:USERPROFILE ".brainstem-tether"
$TetherBin  = Join-Path $env:USERPROFILE ".local\bin"
$RepoUrl    = "https://github.com/kody-w/RAPP.git"

function Print-Banner {
    Write-Host ""
    Write-Host "  RAPP Tether" -ForegroundColor Cyan
    Write-Host "  Local agents, browser AI."
    Write-Host "  Routes virtual-brainstem agent calls to this machine."
    Write-Host ""
}

function Find-Python {
    foreach ($cmd in @("python3", "python", "py")) {
        try {
            $ver = & $cmd -c 'import sys; print(f"{sys.version_info.major}{sys.version_info.minor:02d}")' 2>$null
            if ($LASTEXITCODE -eq 0 -and [int]$ver -ge 308) { return $cmd }
        } catch {}
    }
    return $null
}

function Ensure-Repo {
    if (Test-Path (Join-Path $TetherHome ".git")) {
        Write-Host "  Updating $TetherHome..."
        git -C $TetherHome fetch --quiet origin main 2>&1 | Out-Null
        git -C $TetherHome reset --hard --quiet origin/main 2>&1 | Out-Null
    } else {
        Write-Host "  Cloning $RepoUrl -> $TetherHome..."
        if (Test-Path $TetherHome) { Remove-Item -Recurse -Force $TetherHome }
        git clone --quiet --depth 1 $RepoUrl $TetherHome
    }
}

function Install-CLI {
    param([string]$PythonCmd)

    New-Item -ItemType Directory -Force -Path $TetherBin | Out-Null
    $cliPath = Join-Path $TetherBin "brainstem-tether.cmd"
    $serverPath = Join-Path $TetherHome "tether\server.py"
    $agentsPath = Join-Path $TetherHome "agents"

    @"
@echo off
REM RAPP Tether launcher — runs tether\server.py with the bundled agents.
REM Edit %USERPROFILE%\.brainstem-tether\agents\ to add your own *_agent.py
REM files, then re-run brainstem-tether to pick them up.
"$PythonCmd" "$serverPath" --agents "$agentsPath" %*
"@ | Set-Content -Encoding ASCII $cliPath

    # Add to user PATH if missing
    $userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
    if ($userPath -notlike "*$TetherBin*") {
        [Environment]::SetEnvironmentVariable("PATH", "$TetherBin;$userPath", "User")
        $env:PATH = "$TetherBin;$env:PATH"
    }
}

function Main {
    Print-Banner

    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Write-Host "  git is required but not installed." -ForegroundColor Red
        Write-Host "  Install git from https://git-scm.com/ and re-run."
        exit 1
    }

    $py = Find-Python
    if (-not $py) {
        Write-Host "  Python 3.8+ is required but not found." -ForegroundColor Red
        Write-Host "  Install Python from https://python.org and re-run."
        exit 1
    }
    Write-Host "  Python: $py ($(& $py --version 2>&1))"

    Ensure-Repo
    Install-CLI -PythonCmd $py

    Write-Host ""
    Write-Host "==================================================="
    Write-Host "  + RAPP Tether installed!" -ForegroundColor Green
    Write-Host "==================================================="
    Write-Host ""
    Write-Host "  CLI:    brainstem-tether"
    Write-Host "  Repo:   $TetherHome"
    Write-Host "  Agents: $TetherHome\agents\"
    Write-Host ""
    Write-Host "  Launching tether server now..." -ForegroundColor Cyan
    Write-Host ""
    & (Join-Path $TetherBin "brainstem-tether.cmd")
}

Main
