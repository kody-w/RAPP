[Console]::Error.WriteLine(@"
bootstrap.ps1: 410 Gone

The target-owned cave installer bootstrap is retired. It refuses to
download, hatch, import, or launch the legacy runtime. No fallback runs.

Maintainers: see RAPP1_STATUS.md before restoring a bootstrap path.
"@)

exit 78
