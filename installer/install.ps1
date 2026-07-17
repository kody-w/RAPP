$ErrorActionPreference = "Stop"
[Console]::Error.WriteLine(@"
installer/install.ps1: 410 Gone

The Windows installer is retired until a target-owned implementation can
verify the exact KERNEL_PIN tag and all frozen hashes without rewriting them.
No download or installation was attempted.
"@)
exit 78
