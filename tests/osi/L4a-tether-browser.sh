#!/usr/bin/env bash
# tests/osi/L4a-tether-browser.sh
#
# Historical source restored from:
#   commit 6bd45f00981959a3fdfcc64fb32608533aae5021
#   git blob 7de9e16faf90e0601c66b1091a73cffa907c56f7
#
# The full two-browser PeerJS tether suite remains in browser/, but the
# canonical default is an offline-safe skip. This launcher never installs or
# downloads Playwright, Chromium, PeerJS, or any other dependency.

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BROWSER_DIR="$HERE/browser"

if [ "${RAPP_OSI_BROWSER_EXTERNAL:-0}" != "1" ]; then
  printf '%s\n' \
    'SKIP L4a browser tether: external PeerJS/Chromium execution is disabled by default.' \
    'Set RAPP_OSI_BROWSER_EXTERNAL=1 only with explicitly supplied local dependencies.'
  exit 0
fi

if ! command -v node >/dev/null 2>&1; then
  printf '%s\n' 'L4a browser tether: supplied node executable is required.' >&2
  exit 2
fi

if [ -z "${RAPP_PEERJS_BUNDLE:-}" ] || [ ! -f "$RAPP_PEERJS_BUNDLE" ]; then
  printf '%s\n' \
    'L4a browser tether: RAPP_PEERJS_BUNDLE must name an existing local PeerJS browser bundle.' \
    >&2
  exit 2
fi

if [ -z "${RAPP_CHROMIUM_EXECUTABLE:-}" ] || [ ! -x "$RAPP_CHROMIUM_EXECUTABLE" ]; then
  printf '%s\n' \
    'L4a browser tether: RAPP_CHROMIUM_EXECUTABLE must name an existing executable.' \
    >&2
  exit 2
fi

if [ -z "${RAPP_PEERJS_BROKER_HOST:-}" ]; then
  printf '%s\n' \
    'L4a browser tether: RAPP_PEERJS_BROKER_HOST is required for an explicit external run.' \
    >&2
  exit 2
fi

if [ "${RAPP_PEERJS_BROKER_SECURE:-}" != "true" ] \
  && [ "${RAPP_PEERJS_BROKER_SECURE:-}" != "false" ]; then
  printf '%s\n' \
    'L4a browser tether: RAPP_PEERJS_BROKER_SECURE must be exactly true or false.' \
    >&2
  exit 2
fi

cd "$BROWSER_DIR"
exec node "$BROWSER_DIR/L4a-tether.spec.mjs"
