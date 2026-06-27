# bootstrap.ps1 — stand up the repo-independent RAPP brainstem from the PUBLIC
# RAPP Cave on Windows, in one command, touching the grail repo zero times.
# The cave is a PUBLIC front door: anyone can pull the egg with plain HTTPS —
# no GitHub auth, no collaborator gate.
# Compatible with Windows PowerShell 5.1 (the default shell) and PowerShell 7+.
#
# Public one-liner (anybody, anywhere):
#   irm https://kody-w.github.io/RAPP/cave/rapplications/rapp-installer/bootstrap.ps1 | iex
$ErrorActionPreference = "Stop"

# Public raw base (default) + Pages fallback. Both HTTPS only.
$EggUrlRaw   = if ($env:RAPP_CAVE_EGG_URL)       { $env:RAPP_CAVE_EGG_URL }       else { "https://raw.githubusercontent.com/kody-w/RAPP/main/cave/rapplications/rapp-installer/cubby-rapp-installer.egg" }
$EggUrlPages = if ($env:RAPP_CAVE_EGG_URL_PAGES) { $env:RAPP_CAVE_EGG_URL_PAGES } else { "https://kody-w.github.io/RAPP/cave/rapplications/rapp-installer/cubby-rapp-installer.egg" }
$EggName = "cubby-rapp-installer.egg"
$Port    = if ($env:PORT) { $env:PORT } else { "7077" }
$Work    = Join-Path $env:TEMP ("rapp-installer-" + [System.Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $Work | Out-Null
function Say($m) { Write-Host "[bootstrap] $m" -ForegroundColor Cyan }

# 1. prerequisites ----------------------------------------------------------
$Py = Get-Command python -ErrorAction SilentlyContinue
if (-not $Py) { $Py = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $Py) { throw "Python 3 not found. Install Python 3.11+ from https://python.org" }
Say "python OK ($($Py.Source))"

# 2. pull the egg from the public cave (plain HTTPS, BINARY-safe, no auth) ---
$Egg = Join-Path $Work $EggName
if ($EggUrlRaw -like "http://*" -or $EggUrlPages -like "http://*") { throw "refusing plaintext http:// egg URL (MITM risk) — use https://" }
Say "pulling $EggName from the public cave (no auth needed)…"
# NEVER use `>` for binary in PowerShell (it re-encodes and corrupts the zip).
# Invoke-WebRequest -OutFile writes raw bytes.
try {
  Invoke-WebRequest -Uri $EggUrlRaw -OutFile $Egg -UseBasicParsing -Headers @{ "User-Agent" = "rapp-installer-bootstrap" }
} catch {
  Say "raw fetch failed — falling back to the Pages mirror…"
  Invoke-WebRequest -Uri $EggUrlPages -OutFile $Egg -UseBasicParsing -Headers @{ "User-Agent" = "rapp-installer-bootstrap" }
}
if (-not (Test-Path $Egg) -or (Get-Item $Egg).Length -eq 0) {
  throw "could not fetch the egg from the public cave. Check your network and that the cave is published."
}
Say "egg: $((Get-Item $Egg).Length) bytes"

# 3. extract hatch.py from the egg via .NET (no python heredoc) --------------
$Hatch = Join-Path $Work "hatch.py"
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead($Egg)
try {
  $entry = $zip.GetEntry("cubby/rapplications/rapp-installer/hatch.py")
  if (-not $entry) { throw "hatch.py not found inside the egg" }
  [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $Hatch, $true)
} finally { $zip.Dispose() }
if (-not (Test-Path $Hatch)) { throw "could not extract hatch.py from the egg" }

# 4. hatch (build venv + lay down files), clean up, launch from the cubby -----
Say "hatching the egg → ~/.brainstem/cubbies/rapp-installer/ (grail untouched)…"
& $Py.Source $Hatch $Egg
if ($LASTEXITCODE -ne 0) { throw "hatch failed (exit $LASTEXITCODE)" }
$Cubby  = Join-Path $HOME ".brainstem\cubbies\rapp-installer"
$Serve  = Join-Path $Cubby "rapplications\rapp-installer\serve.py"
$VenvPy = Join-Path $HOME ".brainstem\venv\Scripts\python.exe"
if (-not (Test-Path $VenvPy)) { $VenvPy = $Py.Source }
if (-not (Test-Path $Serve)) { throw "hatch finished but serve.py missing at $Serve" }
Remove-Item -Recurse -Force $Work -ErrorAction SilentlyContinue
$env:PORT = $Port
Say "launching → http://localhost:$Port"
& $VenvPy $Serve
