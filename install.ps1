$ErrorActionPreference = "Stop"
[Console]::Error.WriteLine(@"
install.ps1: 410 Gone

The legacy root PowerShell installer is retired. It will not fetch a mutable
branch, rewrite pinned kernel bytes, or install an unsigned archive.
"@)
exit 78
