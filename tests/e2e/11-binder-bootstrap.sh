#!/usr/bin/env bash
# Binder bootstrap test (Constitution Article XXV — distros & RAPPSTORE_URL).
#
# Verifies the start.sh → binder bootstrap path end-to-end:
#   - clean state (no services/ dir, no bootstrap.json)
#   - run a sandboxed brainstem with start.sh
#   - confirm binder lands in services/
#   - confirm bootstrap.json records reachability + install
#   - confirm /api/binder responds with installed list
#   - confirm /health includes the bootstrap block reflecting the install
#
# This proves that a fresh brainstem on a fresh machine self-installs its
# package manager from RAPPstore on first launch, with no manual steps.
set -euo pipefail
cd "$(dirname "$0")/../.."

PORT="${PORT:-7084}"
SANDBOX=/tmp/rapp-e2e-bootstrap
PID_FILE=/tmp/rapp-e2e-bootstrap.pid
LOG=/tmp/rapp-e2e-bootstrap.log

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

# Build a clean sandbox copy of the brainstem source (no .copilot_*,
# no .brainstem_data, no services/). start.sh should bootstrap binder.
echo "▶ Building sandbox at $SANDBOX..."
rm -rf "$SANDBOX"
mkdir -p "$SANDBOX"
cp -r rapp_brainstem/* "$SANDBOX/"
# Borrow auth so /chat works after bootstrap (the test of /api/binder
# itself doesn't need auth, but we want a valid run).
for AUTH_SRC in "$HOME/.brainstem/src/rapp_brainstem" "$HOME/.brainstem"; do
    if [ -f "$AUTH_SRC/.copilot_session" ]; then
        cp "$AUTH_SRC/.copilot_session" "$SANDBOX/.copilot_session"
        cp "$AUTH_SRC/.copilot_token"   "$SANDBOX/.copilot_token" 2>/dev/null || true
        break
    fi
done
# Ensure the sandbox is genuinely fresh
rm -rf "$SANDBOX/services" "$SANDBOX/.brainstem_data"

# Run start.sh — this is what bootstraps binder
echo "▶ Running start.sh on :$PORT (this triggers the bootstrap)..."
( cd "$SANDBOX" && PORT=$PORT ./start.sh ) > "$LOG" 2>&1 &
echo $! > "$PID_FILE"

for i in $(seq 1 30); do
    curl -sf "http://localhost:$PORT/health" >/dev/null 2>&1 && break
    sleep 1
    if [ "$i" = "30" ]; then
        echo "FAIL: brainstem did not come up"
        tail -30 "$LOG"
        exit 1
    fi
done

# ── 1. binder_service.py landed in services/ ─────────────────────────
if [ ! -f "$SANDBOX/services/binder_service.py" ]; then
    echo "FAIL: services/binder_service.py was not created by bootstrap"
    echo "--- start.sh log:"
    tail -20 "$LOG"
    exit 1
fi
echo "PASS: binder_service.py landed in services/"

# ── 2. bootstrap.json was written ────────────────────────────────────
if [ ! -f "$SANDBOX/.brainstem_data/bootstrap.json" ]; then
    echo "FAIL: .brainstem_data/bootstrap.json was not written"
    exit 1
fi
REACHABLE=$(python3 -c 'import json; print(json.load(open("'$SANDBOX'/.brainstem_data/bootstrap.json"))["rapp_store_reachable"])')
INSTALLED=$(python3 -c 'import json; print(json.load(open("'$SANDBOX'/.brainstem_data/bootstrap.json"))["binder_installed"])')
if [ "$REACHABLE" != "True" ]; then
    echo "FAIL: bootstrap.json says rapp_store_reachable=$REACHABLE (network issue?)"
    cat "$SANDBOX/.brainstem_data/bootstrap.json"
    exit 1
fi
if [ "$INSTALLED" != "True" ]; then
    echo "FAIL: bootstrap.json says binder_installed=$INSTALLED"
    cat "$SANDBOX/.brainstem_data/bootstrap.json"
    exit 1
fi
echo "PASS: bootstrap.json records reachable=true, installed=true"

# ── 3. /api/binder responds 200 with installed list ──────────────────
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
    echo "$BODY"
    exit 1
fi
echo "PASS: /api/binder returns 200 with installed key"

# ── 4. /health bootstrap block reflects the install ──────────────────
HEALTH_BS=$(curl -s "http://localhost:$PORT/health" | python3 -c 'import sys,json; b=json.load(sys.stdin).get("bootstrap",{}); print(b.get("rapp_store_reachable"), b.get("binder_installed"))')
if [ "$HEALTH_BS" != "True True" ]; then
    echo "FAIL: /health bootstrap not reflecting install: '$HEALTH_BS'"
    exit 1
fi
echo "PASS: /health bootstrap block reports reachable+installed"

echo "✅ Binder bootstrap test passed"
