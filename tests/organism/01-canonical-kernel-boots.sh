#!/usr/bin/env bash
# Fixture: the canonical kernel must boot from a fresh repo checkout.
#
# Asserts:
#   - PORT=<free> python brainstem.py exits cleanly to /health
#   - /health returns unauthenticated with no ambient credentials
#   - /agents lists at least one *_agent.py file
#   - /version matches the VERSION file
#
# Reference: Constitution Article XXXIII §3 — drop-in replaceability is the test.

set -euo pipefail
cd "$(dirname "$0")/../.."

REPO_ROOT="$(pwd)"
BRAINSTEM_DIR="${RAPP1_BRAINSTEM_BOOT_DIR:-$REPO_ROOT/rapp_brainstem}"
WORK_DIR="${TMPDIR:-$REPO_ROOT/tests/.rapp1-work}/organism-01-$$"
mkdir -p "$WORK_DIR"
LOG="$WORK_DIR/brainstem.log"
PID_FILE="$WORK_DIR/brainstem.pid"

# Pick a free port
PORT=""
for p in 7080 7081 7082 7083 7084 7085 7086 7087; do
    if ! lsof -i ":$p" -sTCP:LISTEN >/dev/null 2>&1; then
        PORT="$p"; break
    fi
done
[ -n "$PORT" ] || { echo "FAIL: no free port in 7080-7087"; exit 1; }

cleanup() {
    if [ -f "$PID_FILE" ]; then
        kill "$(cat "$PID_FILE")" 2>/dev/null || true
    fi
    rm -rf "$WORK_DIR"
}
trap cleanup EXIT

boot_diagnostics() {
    local reason="$1"
    echo "FAIL: $reason" >&2
    echo "  port: $PORT" >&2
    echo "  python: $PYTHON" >&2
    echo "  brainstem: $BRAINSTEM_DIR" >&2
    if [ -f "$PID_FILE" ]; then
        local pid
        pid="$(cat "$PID_FILE")"
        if kill -0 "$pid" 2>/dev/null; then
            echo "  process: $pid (running but not ready)" >&2
        else
            echo "  process: $pid (exited before readiness)" >&2
        fi
    fi
    echo "--- brainstem log tail ---" >&2
    tail -80 "$LOG" >&2 2>/dev/null || echo "(no log output)" >&2
}

wait_for_health() {
    local timeout="${RAPP1_BOOT_TIMEOUT_SECONDS:-30}"
    case "$timeout" in
        ''|*[!0-9]*|0)
            boot_diagnostics "invalid RAPP1_BOOT_TIMEOUT_SECONDS=$timeout"
            return 1
            ;;
    esac
    local started=$SECONDS
    while (( SECONDS - started < timeout )); do
        if curl -fsS --connect-timeout 1 --max-time 1 \
            "http://localhost:$PORT/health" >/dev/null 2>&1; then
            return 0
        fi
        if ! kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
            boot_diagnostics "kernel exited before /health became ready"
            return 1
        fi
        sleep 0.2
    done
    boot_diagnostics "/health was not ready within ${timeout}s"
    return 1
}

PYTHON="${PYTHON:-$HOME/.brainstem/venv/bin/python}"
[ -x "$PYTHON" ] || PYTHON="$(command -v python3)"

echo "▶ booting canonical kernel on :$PORT (python: $PYTHON)"
( cd "$BRAINSTEM_DIR" && exec env PORT="$PORT" "$PYTHON" brainstem.py ) > "$LOG" 2>&1 &
echo $! > "$PID_FILE"

wait_for_health

HEALTH="$(curl -s "http://localhost:$PORT/health")"
echo "  /health: $HEALTH"

# The canonical offline runner must never discover developer credentials.
echo "$HEALTH" | grep -q '"status":"unauthenticated"' || {
    echo "FAIL: /health discovered ambient credentials"
    exit 1
}

# /health must list agents (non-empty)
echo "$HEALTH" | grep -qE '"agents":\[' || {
    echo "FAIL: /health missing agents key"
    exit 1
}
echo "$HEALTH" | grep -qE '"agents":\[\]' && {
    echo "FAIL: /health agents list is empty (no *_agent.py files discovered)"
    exit 1
}

# /version must match VERSION file
VERSION_FILE="$(cat "$BRAINSTEM_DIR/VERSION" | tr -d '[:space:]')"
VERSION_API="$(curl -s "http://localhost:$PORT/version" | sed -n 's/.*"version":"\([^"]*\)".*/\1/p')"
[ "$VERSION_FILE" = "$VERSION_API" ] || {
    echo "FAIL: /version mismatch (file=$VERSION_FILE api=$VERSION_API)"
    exit 1
}

# /agents file listing must include at least basic_agent.py and one *_agent.py
AGENTS="$(curl -s "http://localhost:$PORT/agents")"
echo "$AGENTS" | grep -q "basic_agent.py" || {
    echo "FAIL: /agents listing missing basic_agent.py"
    exit 1
}
echo "$AGENTS" | grep -qE '_agent\.py' || {
    echo "FAIL: /agents listing has no *_agent.py files"
    exit 1
}

echo "✓ canonical kernel boots, /health ok, /version matches, /agents lists files"
