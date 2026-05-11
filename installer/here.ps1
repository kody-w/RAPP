# RAPP Brainstem — project-local installer shim (Windows / PowerShell).
#
# One-liner:
#     irm https://kody-w.github.io/RAPP/installer/here.ps1 | iex
#
# This file exists solely to give Windows users a one-URL, no-env-var,
# no-scriptblock-wrap form of the project-local install. It sets the
# `here` env var (which install.ps1 reads as a local-mode trigger) and
# then fetches and executes the real installer.
#
# Equivalent to:
#     $env:here=1
#     irm https://kody-w.github.io/RAPP/installer/install.ps1 | iex
#
# Equivalent to (legacy):
#     irm https://kody-w.github.io/RAPP/installer/install.ps1 | iex --here   # ← invalid PowerShell
#     curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash -s -- --here   # ← bash works
#
# Globally the recommended URL pair is symmetric:
#     irm https://kody-w.github.io/RAPP/installer/install.ps1 | iex   # global
#     irm https://kody-w.github.io/RAPP/installer/here.ps1     | iex   # local

$env:here = "1"
Invoke-RestMethod -Uri "https://kody-w.github.io/RAPP/installer/install.ps1" `
                  -UseBasicParsing | Invoke-Expression
