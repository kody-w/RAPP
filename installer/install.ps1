# kody-w/RAPP — thin grail re-fetcher (Mirror Spec compliant)
#
# This repo mirrors the grail kernel at kody-w/rapp-installer. The actual
# install logic lives in grail, so this script re-fetches grail's installer
# on every run. The mirror's installer cannot drift, because it does not
# *contain* the install logic.
#
#   irm https://raw.githubusercontent.com/kody-w/RAPP/main/installer/install.ps1 | iex
#
# To also hatch the rappter-distro (full-bodied organism), set $env:RAPP_WITH_RAPPTER = "1":
#   $env:RAPP_WITH_RAPPTER = "1"
#   irm https://raw.githubusercontent.com/kody-w/RAPP/main/installer/install.ps1 | iex
#
# Mirror Spec: https://kody-w.github.io/RAPP/pages/vault/Architecture/Mirror%20Spec

$ErrorActionPreference = "Stop"

$GrailInstallerUrl   = "https://raw.githubusercontent.com/kody-w/rapp-installer/main/install.ps1"
$RappterDistroUrl    = "https://raw.githubusercontent.com/kody-w/rappter-distro/main/install.sh"

# Run grail's installer
Invoke-Expression (Invoke-RestMethod -Uri $GrailInstallerUrl)

# Optionally hatch the rappter-distro on top
if ($env:RAPP_WITH_RAPPTER -eq "1") {
    Write-Host ""
    Write-Host "  RAPP_WITH_RAPPTER=1 -> hatching rappter-distro..."
    Write-Host ""
    # rappter-distro install.sh is bash; run it via WSL or Git Bash if available
    if (Get-Command bash -ErrorAction SilentlyContinue) {
        bash -c "curl -fsSL $RappterDistroUrl | bash"
    } else {
        Write-Host "  bash not found - install rappter-distro manually:"
        Write-Host "    curl -fsSL $RappterDistroUrl | bash"
    }
}
