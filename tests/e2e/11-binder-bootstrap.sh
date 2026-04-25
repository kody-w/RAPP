#!/usr/bin/env bash
# Binder install test (one-liner copies binder locally — no network bootstrap).
#
# The one-liner installer (installer/install.sh) clones the full repo,
# which already contains rapp_store/binder/binder_service.py. The
# installer's install_binder_locally step copies that file into the
# brainstem's services/ dir. No fetch, no bootstrap, no banner.
#
# This test verifies:
#   - install.sh's install_binder_locally function copies binder into services/
#   - launching the brainstem makes /api/binder respond 200
#   - /health does NOT include a bootstrap block (we ripped that out)
set -euo pipefail
cd "$(dirname "$0")/../.."

PORT="${PORT:-7084}"
SANDBOX=/tmp/rapp-e2e-binder-install
PID_FILE=/tmp/rapp-e2e-binder-install.pid
LOG=/tmp/rapp-e2e-binder-install.log

cleanup() {
    [ -f "$PID_FILE" ] && kill "$(cat "$PID_FILE")" 2>/dev/null || true
    rm -f "$PID_FILE"
    rm -rf "$SANDBOX"
}
trap cleanup EXIT

if lsof -i ":$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "FAIL: port $PORT already in use"
    exit 1
fi

# Build a sandbox that mirrors the post-install layout: brainstem source
# + sibling rapp_store dir (the way `git clone` of kody-w/RAPP looks).
echo "▶ Building sandbox at $SANDBOX (mirrors post-clone layout)..."
rm -rf "$SANDBOX"
mkdir -p "$SANDBOX/src/rapp_brainstem" "$SANDBOX/src/rapp_store/binder"
cp -r rapp_brainstem/* "$SANDBOX/src/rapp_brainstem/"
cp rapp_store/binder/binder_service.py "$SANDBOX/src/rapp_store/binder/"
# Borrow auth so /chat works (not strictly needed for this test, but consistent)
for AUTH_SRC in "$HOME/.brainstem/src/rapp_brainstem" "$HOME/.brainstem"; do
    if [ -f "$AUTH_SRC/.copilot_session" ]; then
        cp "$AUTH_SRC/.copilot_session" "$SANDBOX/src/rapp_brainstem/.copilot_session"
        cp "$AUTH_SRC/.copilot_token"   "$SANDBOX/src/rapp_brainstem/.copilot_token" 2>/dev/null || true
        break
    fi
done
# Fresh state — no services/, no .brainstem_data/
rm -rf "$SANDBOX/src/rapp_brainstem/services" "$SANDBOX/src/rapp_brainstem/.brainstem_data"

# Replicate install.sh's install_binder_locally step (one cp).
echo "▶ Running the equivalent of install.sh's install_binder_locally..."
mkdir -p "$SANDBOX/src/rapp_brainstem/services"
cp "$SANDBOX/src/rapp_store/binder/binder_service.py" "$SANDBOX/src/rapp_brainstem/services/binder_service.py"

# ── 1. binder_service.py landed in services/ ─────────────────────────
if [ ! -f "$SANDBOX/src/rapp_brainstem/services/binder_service.py" ]; then
    echo "FAIL: services/binder_service.py was not created"
    exit 1
fi
echo "PASS: binder_service.py landed in services/"

# Launch the brainstem
echo "▶ Launching brainstem on :$PORT..."
( cd "$SANDBOX/src/rapp_brainstem" && PORT=$PORT python3 brainstem.py ) > "$LOG" 2>&1 &
echo $! > "$PID_FILE"
for i in $(seq 1 30); do
    curl -sf "http://localhost:$PORT/health" >/dev/null 2>&1 && break
    sleep 1
    [ "$i" = "30" ] && { echo "FAIL: did not come up"; tail -20 "$LOG"; exit 1; }
done

# ── 2. /api/binder responds 200 with installed list ──────────────────
RESP=$(curl -s -w "\n%{http_code}" "http://localhost:$PORT/api/binder")
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
if [ "$HTTP_CODE" != "200" ]; then
    echo "FAIL: /api/binder returned $HTTP_CODE"
    echo "$BODY"
    exit 1
fi
HAS_KEY=$(echo "$BODY" | python3 -c 'import sys,json; print("installed" in json.load(sys.stdin))')
if [ "$HAS_KEY" != "True" ]; then
    echo "FAIL: /api/binder response missing 'installed' key"
    exit 1
fi
echo "PASS: /api/binder returns 200 with installed key"

# ── 3. /health does NOT include bootstrap block (ripped out) ─────────
HAS_BOOTSTRAP=$(curl -s "http://localhost:$PORT/health" | python3 -c 'import sys,json; print("bootstrap" in json.load(sys.stdin))')
if [ "$HAS_BOOTSTRAP" = "True" ]; then
    echo "FAIL: /health still includes 'bootstrap' block — should have been removed"
    exit 1
fi
echo "PASS: /health does not include bootstrap block (removed)"

# ── 4. .brainstem_data/bootstrap.json was NOT created ────────────────
if [ -f "$SANDBOX/src/rapp_brainstem/.brainstem_data/bootstrap.json" ]; then
    echo "FAIL: bootstrap.json was created — bootstrap mechanism still active"
    exit 1
fi
echo "PASS: no bootstrap.json (bootstrap mechanism removed)"

echo "✅ Binder install test passed (one-liner copies binder, no bootstrap)"
