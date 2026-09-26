# Builds the Brainstem app on Windows: the pinned Code - OSS fork plus the RAPP overlay in this folder.
# Everything it fetches or builds goes under .build\ (or -BuildDir); nothing is installed globally.
[CmdletBinding(PositionalBinding = $false)]
param(
	[switch]$DryRun,
	[switch]$Run,
	[switch]$Web,
	[string]$Package = '',
	[switch]$Test,
	[int]$Port = 9888,
	[string]$UpstreamJson = '',
	[string]$BuildDir = '',
	[Parameter(ValueFromRemainingArguments = $true)][string[]]$LaunchArgs = @()
)
$ErrorActionPreference = 'Stop'
$AppDir = Split-Path -Parent $PSScriptRoot
if (-not $BuildDir) { $BuildDir = if ($env:BRAINSTEM_BUILD_DIR) { $env:BRAINSTEM_BUILD_DIR } else { Join-Path $AppDir '.build' } }
if (-not $UpstreamJson) { $UpstreamJson = Join-Path $AppDir 'UPSTREAM.json' }
New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null
$BuildDir = (Resolve-Path $BuildDir).Path
$Checkout = Join-Path $BuildDir 'vscode'
$Logs = Join-Path $BuildDir 'logs'
New-Item -ItemType Directory -Force -Path $Logs | Out-Null
$Started = Get-Date

# A plain line on stderr: under ErrorActionPreference Stop, Write-Error would throw a wrapped, coloured record instead.
function Fail([string]$Message) { [Console]::Error.WriteLine("build.ps1: $Message"); exit 1 }
function Step([string]$Name) { $script:StepName = $Name; $script:StepStart = Get-Date; Write-Host "`n== $Name" }
function StepDone { Write-Host ("== {0}: done in {1:n0}s" -f $script:StepName, ((Get-Date) - $script:StepStart).TotalSeconds) }
function Invoke([string]$File, [string[]]$Arguments, [string]$Where = $Checkout) {
	Push-Location $Where
	try { & $File @Arguments; if ($LASTEXITCODE -ne 0) { Fail "$File $($Arguments -join ' ') exited with $LASTEXITCODE" } }
	finally { Pop-Location }
}

$pin = Get-Content -Raw $UpstreamJson | ConvertFrom-Json
if (-not $pin.fork) { Fail 'UPSTREAM.json names no fork' }
if ($pin.tag -notmatch '^[0-9A-Za-z._-]+$') { Fail "UPSTREAM.json tag '$($pin.tag)' is not a plain tag name" }
if ($pin.commit -notmatch '^[0-9a-f]{40}$') { Fail 'UPSTREAM.json commit must be a full 40-character commit id' }

Step "fetch $($pin.fork) at $($pin.tag)"
if (Test-Path (Join-Path $Checkout '.git')) {
	$origin = (git -C $Checkout remote get-url origin).Trim()
	if (($origin -replace '(\.git)?/?$', '') -ne ($pin.fork -replace '(\.git)?/?$', '')) { Fail "refusing: $Checkout was cloned from $origin, not $($pin.fork); remove it to fetch again" }
	if ((git -C $Checkout rev-parse HEAD).Trim() -ne $pin.commit) {
		git -C $Checkout fetch --quiet --force --depth 1 origin "+refs/tags/$($pin.tag):refs/tags/$($pin.tag)"
		git -C $Checkout -c advice.detachedHead=false checkout --quiet --force "refs/tags/$($pin.tag)"
	}
} else {
	git -c advice.detachedHead=false clone --quiet --depth 1 --branch $pin.tag --single-branch --config core.autocrlf=false --config core.eol=lf $pin.fork $Checkout
	if ($LASTEXITCODE -ne 0) { Fail 'git clone failed' }
}
$head = (git -C $Checkout rev-parse HEAD).Trim()
if ($head -ne $pin.commit) { Fail "refusing: $($pin.tag) of $($pin.fork) is $head, but UPSTREAM.json pins $($pin.commit)" }
Write-Host "pinned commit verified: $head"
StepDone

$want = (Get-Content -Raw (Join-Path $Checkout '.nvmrc')).Trim().TrimStart('v')
if ($want -notmatch '^\d+\.\d+\.\d+$') { Fail ".nvmrc holds '$want', not a Node version" }
$current = (Get-Command node -ErrorAction SilentlyContinue)
if (-not $current -or (& node -v).Trim() -ne "v$want") {
	$arch = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { 'arm64' } else { 'x64' }
	$nodeDir = Join-Path $BuildDir "node\v$want-win-$arch"
	if (-not (Test-Path (Join-Path $nodeDir 'node.exe'))) {
		Step "fetch Node $want (the version .nvmrc pins)"
		$downloads = Join-Path $BuildDir 'node\downloads'
		New-Item -ItemType Directory -Force -Path $downloads | Out-Null
		$name = "node-v$want-win-$arch.zip"
		$base = "https://nodejs.org/dist/v$want"
		Invoke-WebRequest -UseBasicParsing "$base/SHASUMS256.txt" -OutFile (Join-Path $downloads "SHASUMS256-v$want.txt")
		Invoke-WebRequest -UseBasicParsing "$base/$name" -OutFile (Join-Path $downloads $name)
		$expected = (Get-Content (Join-Path $downloads "SHASUMS256-v$want.txt") | Where-Object { $_ -match "\s$([regex]::Escape($name))$" }) -replace '\s.*$', ''
		$actual = (Get-FileHash -Algorithm SHA256 (Join-Path $downloads $name)).Hash.ToLowerInvariant()
		if (-not $expected -or $actual -ne $expected) { Fail "Node $want failed its checksum" }
		$partial = "$nodeDir.partial"
		if (Test-Path $partial) { Remove-Item -Recurse -Force $partial }
		Expand-Archive -Path (Join-Path $downloads $name) -DestinationPath $partial
		Move-Item (Join-Path $partial "node-v$want-win-$arch") $nodeDir
		Remove-Item -Recurse -Force $partial
		StepDone
	}
	$env:PATH = "$nodeDir;$env:PATH"
}

Step 'apply the Brainstem overlay'
git -C $Checkout checkout --quiet --force -- .
git -C $Checkout clean -fdq -- extensions/rapp
$overlayArgs = @((Join-Path $AppDir 'scripts\apply-overlay.mjs'), '--checkout', $Checkout, '--expect-commit', $pin.commit, '--report', (Join-Path $BuildDir 'overlay-report.json'))
if ($Web) { $overlayArgs += @('--webview-port', "$($Port + 1)") }
$report = Join-Path $BuildDir 'overlay-report.json'
if (Test-Path $report) { Remove-Item -Force $report }
Invoke node $overlayArgs $AppDir
if (-not (Test-Path $report) -or (Get-Item $report).Length -eq 0) { Fail 'the overlay did not report; refusing to build without it' }
StepDone

if ($DryRun) {
	Write-Host "`nDry run complete: $($pin.tag) of $($pin.fork) verified at $($pin.commit) and the overlay applied to $Checkout."
	Write-Host "A build would next run, with Node ${want}: npm ci, then npm run compile."
	exit 0
}

$env:npm_config_cache = Join-Path $BuildDir 'npm-cache'
$env:npm_config_devdir = Join-Path $BuildDir 'node-gyp'
$env:PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD = '1'
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $BuildDir 'playwright'
$env:npm_config_update_notifier = 'false'
$env:npm_config_fund = 'false'
$env:npm_config_audit = 'false'

function Fingerprint([string[]]$Files) {
	$hashes = $Files | ForEach-Object { (Get-FileHash -Algorithm SHA256 $_).Hash.ToLowerInvariant() }
	"$($pin.commit) $((& node -v).Trim()) $($hashes -join ' ')"
}

$installStamp = Join-Path $Checkout 'node_modules\.brainstem-install'
$installWant = Fingerprint @((Join-Path $Checkout 'package.json'), (Join-Path $Checkout 'package-lock.json'), (Join-Path $Checkout 'build\npm\dirs.ts'))
if (-not (Test-Path $installStamp) -or (Get-Content -Raw $installStamp) -ne $installWant) {
	Step "install dependencies (npm ci, the fork's own install)"
	$env:ELECTRON_SKIP_BINARY_DOWNLOAD = '1'
	Invoke npm.cmd @('ci')
	Remove-Item Env:\ELECTRON_SKIP_BINARY_DOWNLOAD
	Set-Content -NoNewline -Path $installStamp -Value $installWant
	StepDone
}

$compileStamp = Join-Path $Checkout 'out\.brainstem-compile'
$compileWant = Fingerprint @((Join-Path $AppDir 'overlay.json'), (Join-Path $AppDir 'product.json'), (Join-Path $AppDir 'scripts\branding.mjs'))
if ((Test-Path $compileStamp) -and (Get-Content -Raw $compileStamp) -eq $compileWant) {
	Step 'compile the RAPP extension (the rest is already compiled for this pin)'
	Invoke npm.cmd @('run', 'gulp', 'compile-extension:rapp')
} else {
	Step "compile (the fork's npm run compile)"
	Invoke npm.cmd @('run', 'compile')
	Set-Content -NoNewline -Path $compileStamp -Value $compileWant
}
StepDone

# Electron's download cache follows LOCALAPPDATA on Windows, so the steps that fetch Electron use one in .build.
function InElectronHome([string]$File, [string[]]$Arguments) {
	$saved = $env:LOCALAPPDATA
	$env:LOCALAPPDATA = Join-Path $BuildDir 'electron-home'
	New-Item -ItemType Directory -Force -Path $env:LOCALAPPDATA | Out-Null
	try { Invoke $File $Arguments } finally { $env:LOCALAPPDATA = $saved }
}

if ($Test) {
	Step 'test'
	Invoke node (@('--test') + (Get-ChildItem (Join-Path $AppDir 'tests\*.test.mjs')).FullName) $AppDir
	$env:BRAINSTEM_TEST_TMP = Join-Path $BuildDir 'test-tmp'
	# The host's own JSON reader, which the app's reading of workspace files is held to.
	$env:BRAINSTEM_TEST_HOST_JSON = Join-Path $Checkout 'out\vs\base\common\json.js'
	Invoke node (@('--test') + (Get-ChildItem (Join-Path $Checkout 'extensions\rapp\out\test\*.test.js')).FullName)
	StepDone
}

if ($Run) {
	Step "launch (the fork's scripts\code.bat)"
	InElectronHome npm.cmd @('run', 'electron')
	Invoke (Join-Path $Checkout 'scripts\code.bat') (@('--user-data-dir', (Join-Path $BuildDir 'user-data'), '--extensions-dir', (Join-Path $BuildDir 'user-extensions')) + $LaunchArgs)
} elseif ($Web) {
	Step "serve on http://127.0.0.1:$Port (the fork's scripts\code-server.bat)"
	$env:VSCODE_SKIP_PRELAUNCH = '1'
	$tokenFile = Join-Path $BuildDir 'web-token'
	$bytes = New-Object byte[] 24
	[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
	Set-Content -NoNewline -Path $tokenFile -Value (($bytes | ForEach-Object { $_.ToString('x2') }) -join '')
	$webviewHost = Start-Process -PassThru -NoNewWindow node -ArgumentList @((Join-Path $AppDir 'scripts\webview-host.mjs'), '--root', (Join-Path $Checkout 'out\vs\workbench\contrib\webview\browser\pre'), '--port', "$($Port + 1)")
	try {
		Write-Host "open http://127.0.0.1:$Port/?tkn=$(Get-Content -Raw $tokenFile)"
		Invoke (Join-Path $Checkout 'scripts\code-server.bat') (@('--host', '127.0.0.1', '--port', "$Port", '--connection-token-file', $tokenFile, '--accept-server-license-terms', '--disable-telemetry', '--disable-experiments', '--server-data-dir', (Join-Path $BuildDir 'server-data')) + $LaunchArgs)
	} finally {
		Stop-Process -Id $webviewHost.Id -ErrorAction SilentlyContinue
	}
} elseif ($Package) {
	Step "package vscode-$Package-min (the fork's gulp target)"
	InElectronHome npm.cmd @('run', 'gulp', "vscode-$Package-min")
	$out = Join-Path $BuildDir "Brainstem-$Package"
	if (Test-Path $out) { Remove-Item -Recurse -Force $out }
	Move-Item (Join-Path $BuildDir "VSCode-$Package") $out
	Write-Host "packaged: $out"
	StepDone
}
Write-Host ("`nbuild.ps1: finished in {0:n0}s" -f ((Get-Date) - $Started).TotalSeconds)
