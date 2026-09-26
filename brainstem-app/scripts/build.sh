#!/usr/bin/env bash
# Builds the Brainstem app: the pinned Code - OSS fork plus the RAPP overlay in this folder.
# Everything it fetches or builds goes under .build/ (or --build-dir); nothing is installed globally.
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${BRAINSTEM_BUILD_DIR:-$APP_DIR/.build}"
UPSTREAM_JSON="$APP_DIR/UPSTREAM.json"
MODE=build
PLATFORM=""
PORT="${BRAINSTEM_WEB_PORT:-9888}"
RUN_TESTS=0

usage() {
	cat <<'EOF'
Usage: scripts/build.sh [mode] [options] [-- launcher arguments]

Modes (default: build = fetch, verify, overlay, install, compile):
  --dry-run             fetch and verify the pin, apply the overlay, and stop before installing
  --run                 build, then launch the desktop app with the fork's scripts/code.sh
  --web                 build, then serve it in a browser with the fork's scripts/code-server.sh
  --package <platform>  build, then package with the fork's gulp target vscode-<platform>-min
                        (for example darwin-arm64, darwin-x64, linux-x64, win32-x64)
Options:
  --test                run the Brainstem app tests after compiling
  --port <port>         port for --web (default 9888)
  --upstream-json <f>   use another pin file (tests)
  --build-dir <dir>     build somewhere other than brainstem-app/.build
EOF
}

die() { printf 'build.sh: %s\n' "$*" >&2; exit 1; }
START=$SECONDS
step() { STEP_NAME="$1"; STEP_START=$SECONDS; printf '\n== %s\n' "$1"; }
step_done() { printf '== %s: done in %ss\n' "$STEP_NAME" "$((SECONDS - STEP_START))"; }

while [ $# -gt 0 ]; do
	case "$1" in
		--dry-run) MODE=dry-run ;;
		--run) MODE=run ;;
		--web) MODE=web ;;
		--package) MODE=package; PLATFORM="${2:-}"; [ -n "$PLATFORM" ] || die "--package needs a platform, for example darwin-arm64"; shift ;;
		--test) RUN_TESTS=1 ;;
		--port) PORT="${2:-}"; shift ;;
		--upstream-json) UPSTREAM_JSON="$(cd "$(dirname "${2:?}")" && pwd)/$(basename "$2")"; shift ;;
		--build-dir) BUILD_DIR="${2:?}"; shift ;;
		-h|--help) usage; exit 0 ;;
		--) shift; break ;;
		*) usage >&2; die "unknown option $1" ;;
	esac
	shift
done
LAUNCH_ARGS=("$@")
mkdir -p "$BUILD_DIR"
BUILD_DIR="$(cd "$BUILD_DIR" && pwd)"
CHECKOUT="$BUILD_DIR/vscode"
LOGS="$BUILD_DIR/logs"
mkdir -p "$LOGS"

field() { sed -n "s/^[[:space:]]*\"$1\":[[:space:]]*\"\([^\"]*\)\".*/\1/p" "$UPSTREAM_JSON" | head -n 1; }
[ -f "$UPSTREAM_JSON" ] || die "no pin file at $UPSTREAM_JSON"
FORK="$(field fork)"
TAG="$(field tag)"
COMMIT="$(field commit)"
[ -n "$FORK" ] || die "UPSTREAM.json names no fork"
[[ "$TAG" =~ ^[0-9A-Za-z._-]+$ ]] || die "UPSTREAM.json tag '$TAG' is not a plain tag name"
[[ "$COMMIT" =~ ^[0-9a-f]{40}$ ]] || die "UPSTREAM.json commit must be a full 40-character commit id"

same_remote() { [ "${1%/}" = "${2%/}" ] || [ "${1%.git}" = "${2%/}" ] || [ "${1%/}" = "${2%.git}" ]; }

sha256() {
	if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d ' ' -f 1; else shasum -a 256 "$1" | cut -d ' ' -f 1; fi
}

fetch_pinned() {
	step "fetch $FORK at $TAG"
	if [ -d "$CHECKOUT/.git" ]; then
		local origin
		origin="$(git -C "$CHECKOUT" remote get-url origin)"
		same_remote "$origin" "$FORK" || die "refusing: $CHECKOUT was cloned from $origin, not $FORK; remove it to fetch again"
		if [ "$(git -C "$CHECKOUT" rev-parse HEAD)" != "$COMMIT" ]; then
			git -C "$CHECKOUT" fetch --quiet --force --depth 1 origin "+refs/tags/$TAG:refs/tags/$TAG"
			git -C "$CHECKOUT" -c advice.detachedHead=false checkout --quiet --force "refs/tags/$TAG"
		fi
	else
		git -c advice.detachedHead=false clone --quiet --depth 1 --branch "$TAG" --single-branch \
			--config core.autocrlf=false --config core.eol=lf "$FORK" "$CHECKOUT"
	fi
	local head
	head="$(git -C "$CHECKOUT" rev-parse HEAD)"
	[ "$head" = "$COMMIT" ] || die "refusing: $TAG of $FORK is $head, but UPSTREAM.json pins $COMMIT"
	echo "pinned commit verified: $head"
	step_done
}

use_node() {
	local want os arch dir name base downloads expected
	want="$(tr -d '[:space:]v' < "$CHECKOUT/.nvmrc")"
	[[ "$want" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die ".nvmrc holds '$want', not a Node version"
	if command -v node >/dev/null 2>&1 && [ "$(node -v)" = "v$want" ]; then
		return
	fi
	case "$(uname -s)" in Darwin) os=darwin ;; Linux) os=linux ;; *) die "on Windows use scripts/build.ps1" ;; esac
	case "$(uname -m)" in arm64|aarch64) arch=arm64 ;; x86_64|amd64) arch=x64 ;; *) die "no Node build for $(uname -m)" ;; esac
	dir="$BUILD_DIR/node/v$want-$os-$arch"
	if [ ! -x "$dir/bin/node" ]; then
		step "fetch Node $want (the version .nvmrc pins)"
		name="node-v$want-$os-$arch.tar.xz"
		base="https://nodejs.org/dist/v$want"
		downloads="$BUILD_DIR/node/downloads"
		mkdir -p "$downloads"
		curl -fsSL "$base/SHASUMS256.txt" -o "$downloads/SHASUMS256-v$want.txt"
		curl -fsSL "$base/$name" -o "$downloads/$name"
		expected="$(awk -v n="$name" '$2 == n { print $1 }' "$downloads/SHASUMS256-v$want.txt")"
		[ -n "$expected" ] && [ "$(sha256 "$downloads/$name")" = "$expected" ] || die "Node $want failed its checksum"
		rm -rf "$dir.partial"
		mkdir -p "$dir.partial"
		tar -xJf "$downloads/$name" -C "$dir.partial" --strip-components 1
		mv "$dir.partial" "$dir"
		step_done
	fi
	export PATH="$dir/bin:$PATH"
}

apply_overlay() {
	step "apply the Brainstem overlay"
	git -C "$CHECKOUT" checkout --quiet --force -- .
	git -C "$CHECKOUT" clean -fdq -- extensions/rapp
	local web=()
	if [ "$MODE" = web ]; then
		web=(--webview-port "$((PORT + 1))")
	fi
	rm -f "$BUILD_DIR/overlay-report.json"
	node "$APP_DIR/scripts/apply-overlay.mjs" --checkout "$CHECKOUT" --expect-commit "$COMMIT" --report "$BUILD_DIR/overlay-report.json" "${web[@]+"${web[@]}"}"
	[ -s "$BUILD_DIR/overlay-report.json" ] || die "the overlay did not report; refusing to build without it"
	step_done
}

fingerprint() {
	local files=("$@") out=""
	for f in "${files[@]}"; do out="$out $(sha256 "$f")"; done
	printf '%s %s%s' "$COMMIT" "$(node -v)" "$out"
}

npm_env() {
	export npm_config_cache="$BUILD_DIR/npm-cache" npm_config_devdir="$BUILD_DIR/node-gyp"
	export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 PLAYWRIGHT_BROWSERS_PATH="$BUILD_DIR/playwright"
	export npm_config_update_notifier=false npm_config_fund=false npm_config_audit=false
	# When xcrun picks the Command Line Tools SDK but an older Xcode is selected, that Xcode's linker cannot
	# read the SDK; build native modules with the Command Line Tools' own toolchain instead.
	if [ "$(uname -s)" = Darwin ] && [ -z "${DEVELOPER_DIR:-}" ]; then
		case "$(xcrun --show-sdk-path 2>/dev/null || true)" in
			/Library/Developer/CommandLineTools/*)
				if [ "$(xcode-select -p 2>/dev/null || true)" != /Library/Developer/CommandLineTools ]; then
					export DEVELOPER_DIR=/Library/Developer/CommandLineTools
					echo "native modules: using the Command Line Tools toolchain, which matches its SDK"
				fi
				;;
		esac
	fi
}

install_deps() {
	local stamp="$CHECKOUT/node_modules/.brainstem-install" want
	want="$(fingerprint "$CHECKOUT/package.json" "$CHECKOUT/package-lock.json" "$CHECKOUT/build/npm/dirs.ts")"
	if [ -f "$stamp" ] && [ "$(cat "$stamp")" = "$want" ]; then
		echo "dependencies already installed for this pin"
		return
	fi
	step "install dependencies (npm ci, the fork's own install)"
	(cd "$CHECKOUT" && ELECTRON_SKIP_BINARY_DOWNLOAD=1 npm ci) 2>&1 | tee "$LOGS/install.log"
	printf '%s' "$want" > "$stamp"
	step_done
}

compile() {
	local stamp="$CHECKOUT/out/.brainstem-compile" want
	want="$(fingerprint "$APP_DIR/overlay.json" "$APP_DIR/product.json" "$APP_DIR/scripts/branding.mjs")"
	if [ -f "$stamp" ] && [ "$(cat "$stamp")" = "$want" ]; then
		step "compile the RAPP extension (the rest is already compiled for this pin)"
		(cd "$CHECKOUT" && npm run gulp compile-extension:rapp) 2>&1 | tee "$LOGS/compile-rapp.log"
	else
		step "compile (the fork's npm run compile)"
		(cd "$CHECKOUT" && npm run compile) 2>&1 | tee "$LOGS/compile.log"
		printf '%s' "$want" > "$stamp"
	fi
	step_done
}

# Electron's download cache follows HOME, so the steps that fetch Electron run with a home in .build.
in_electron_home() {
	mkdir -p "$BUILD_DIR/electron-home"
	(cd "$CHECKOUT" && HOME="$BUILD_DIR/electron-home" "$@")
}

run_tests() {
	step "test"
	node --test "$APP_DIR"/tests/*.test.mjs
	# The host's own JSON reader, which the app's reading of workspace files is held to.
	BRAINSTEM_TEST_TMP="$BUILD_DIR/test-tmp" BRAINSTEM_TEST_HOST_JSON="$CHECKOUT/out/vs/base/common/json.js" node --test "$CHECKOUT"/extensions/rapp/out/test/*.test.js
	step_done
}

fetch_pinned
if [ "$MODE" = dry-run ]; then
	if ! command -v node >/dev/null 2>&1 || [ "$(node -p 'process.versions.node.split(".")[0]')" -lt 18 ]; then
		use_node
	fi
	apply_overlay
	cat <<EOF

Dry run complete: $TAG of $FORK verified at $COMMIT and the overlay applied to
$CHECKOUT (report: $BUILD_DIR/overlay-report.json).
A build would next run, with Node $(tr -d '[:space:]v' < "$CHECKOUT/.nvmrc"): npm ci, then npm run compile.
EOF
	exit 0
fi

use_node
echo "node $(node -v), npm $(npm -v)"
apply_overlay
npm_env
install_deps
compile
if [ "$RUN_TESTS" = 1 ]; then
	run_tests
fi

case "$MODE" in
	run)
		step "launch (the fork's scripts/code.sh)"
		unset ELECTRON_SKIP_BINARY_DOWNLOAD
		in_electron_home npm run electron
		mkdir -p "$BUILD_DIR/user-data" "$BUILD_DIR/user-extensions"
		exec "$CHECKOUT/scripts/code.sh" --user-data-dir "$BUILD_DIR/user-data" --extensions-dir "$BUILD_DIR/user-extensions" "${LAUNCH_ARGS[@]+"${LAUNCH_ARGS[@]}"}"
		;;
	web)
		step "serve on http://127.0.0.1:$PORT (the fork's scripts/code-server.sh)"
		mkdir -p "$BUILD_DIR/server-data"
		TOKEN_FILE="$BUILD_DIR/web-token"
		(umask 077 && node -e "process.stdout.write(require('crypto').randomBytes(24).toString('hex'))" > "$TOKEN_FILE")
		node "$APP_DIR/scripts/webview-host.mjs" --root "$CHECKOUT/out/vs/workbench/contrib/webview/browser/pre" --port "$((PORT + 1))" &
		WEBVIEW_HOST=$!
		trap 'kill "$WEBVIEW_HOST" 2>/dev/null || true' EXIT
		echo "open http://127.0.0.1:$PORT/?tkn=$(cat "$TOKEN_FILE")"
		VSCODE_SKIP_PRELAUNCH=1 "$CHECKOUT/scripts/code-server.sh" --host 127.0.0.1 --port "$PORT" --connection-token-file "$TOKEN_FILE" \
			--accept-server-license-terms --disable-telemetry --disable-experiments --server-data-dir "$BUILD_DIR/server-data" \
			"${LAUNCH_ARGS[@]+"${LAUNCH_ARGS[@]}"}"
		;;
	package)
		step "package vscode-$PLATFORM-min (the fork's gulp target)"
		in_electron_home npm run gulp "vscode-$PLATFORM-min" 2>&1 | tee "$LOGS/package-$PLATFORM.log"
		rm -rf "$BUILD_DIR/Brainstem-$PLATFORM"
		mv "$BUILD_DIR/VSCode-$PLATFORM" "$BUILD_DIR/Brainstem-$PLATFORM"
		echo "packaged: $BUILD_DIR/Brainstem-$PLATFORM"
		step_done
		;;
esac
printf '\nbuild.sh: finished in %ss\n' "$((SECONDS - START))"
