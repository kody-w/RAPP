# RAPP Brainstem — one-time setup that makes `here` a recognized command
# in every future PowerShell session on this account.
#
# Run once:
#     irm https://kody-w.github.io/RAPP/installer/setup-here.ps1 | iex
#
# From then on, any new session lets you do:
#     here
#     irm https://kody-w.github.io/RAPP/installer/install.ps1 | iex
#
# Mechanism: appends a tiny function definition to your $PROFILE
# (created if absent). The function sets $env:here = "1" so the next
# install one-liner reads it and triggers project-local mode.

$ProfilePath = $PROFILE
$ProfileDir  = Split-Path -Parent $ProfilePath

if (-not (Test-Path $ProfileDir)) {
    New-Item -ItemType Directory -Force -Path $ProfileDir | Out-Null
}

$Marker = '# >>> RAPP-here-shim'
$Block  = @"
$Marker
function global:here {
    [Console]::WriteLine('here = 1  (next RAPP install will be project-local)')
    `$env:here = '1'
}
# <<< RAPP-here-shim
"@

if (Test-Path $ProfilePath) {
    $current = Get-Content $ProfilePath -Raw
    if ($current -match [Regex]::Escape($Marker)) {
        Write-Host "✓ here() already installed in $ProfilePath — no change made" -ForegroundColor Green
    } else {
        Add-Content -Path $ProfilePath -Value "`r`n$Block`r`n"
        Write-Host "✓ here() appended to $ProfilePath" -ForegroundColor Green
    }
} else {
    Set-Content -Path $ProfilePath -Value $Block
    Write-Host "✓ created $ProfilePath with here() defined" -ForegroundColor Green
}

# Make it active in THIS session too, so the user can immediately do:
#     here
#     irm URL | iex
function global:here {
    [Console]::WriteLine('here = 1  (next RAPP install will be project-local)')
    $env:here = '1'
}

Write-Host ""
Write-Host "Next:" -ForegroundColor Cyan
Write-Host "  here" -ForegroundColor White
Write-Host "  irm https://kody-w.github.io/RAPP/installer/install.ps1 | iex" -ForegroundColor White
Write-Host ""
Write-Host "(or for a brand-new PowerShell session, the function is already in your `$PROFILE.)" -ForegroundColor DarkGray
