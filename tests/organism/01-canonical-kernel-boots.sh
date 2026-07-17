#!/usr/bin/env bash
# Fixture: immutable kernel bytes remain directly testable in isolation.
#
# Asserts:
#   - PORT=0 lets the spawned kernel own its bind before /health is accepted
#   - /health returns unauthenticated with no ambient credentials
#   - /agents lists at least one *_agent.py file
#   - /version matches the VERSION file
#
# Reference: Constitution Article XXXIII §3 — drop-in replaceability is the test.

set -euo pipefail
cd "$(dirname "$0")/../.."

REPO_ROOT="$(pwd)"
BRAINSTEM_DIR="${RAPP1_BRAINSTEM_BOOT_DIR:-$REPO_ROOT/rapp_brainstem}"
BRAINSTEM_SCRIPT="$BRAINSTEM_DIR/brainstem.py"
WORK_DIR="${TMPDIR:-$REPO_ROOT/tests/.rapp1-work}/organism-01-$$"
mkdir -p "$WORK_DIR"
if [ -z "${RAPP1_BRAINSTEM_BOOT_DIR:-}" ]; then
    mkdir -p "$WORK_DIR/runtime"
    git archive --format=tar HEAD rapp_brainstem |
        tar -xf - -C "$WORK_DIR/runtime"
    BRAINSTEM_DIR="$WORK_DIR/runtime/rapp_brainstem"
    BRAINSTEM_SCRIPT="$BRAINSTEM_DIR/brainstem.py"
fi
TEST_HOME="$WORK_DIR/home"
mkdir -p "$TEST_HOME"
OFFLINE_GUARD="$REPO_ROOT/tests/offline_guard"
LOG="$WORK_DIR/brainstem.log"
PID_FILE="$WORK_DIR/brainstem.pid"
PORT=""
SERVER_PID=""

cleanup() {
    if [ -n "$SERVER_PID" ]; then
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
    rm -rf "$WORK_DIR"
}
trap cleanup EXIT

process_is_expected() {
    local command
    [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null || return 1
    command="$(ps -p "$SERVER_PID" -o command= 2>/dev/null)" || return 1
    case "$command" in
        *"$BRAINSTEM_SCRIPT"*) return 0 ;;
        *) return 1 ;;
    esac
}

discover_bound_port() {
    sed -nE \
        's#^.*Running on http://127\.0\.0\.1:([0-9]+).*$#\1#p' \
        "$LOG" 2>/dev/null | tail -n 1
}

boot_diagnostics() {
    local reason="$1"
    echo "FAIL: $reason" >&2
    echo "  bound port: ${PORT:-not discovered}" >&2
    echo "  python: $PYTHON" >&2
    echo "  brainstem: $BRAINSTEM_DIR" >&2
    if [ -n "$SERVER_PID" ]; then
        if kill -0 "$SERVER_PID" 2>/dev/null; then
            echo "  process: $SERVER_PID ($(ps -p "$SERVER_PID" -o command= 2>/dev/null || echo unknown))" >&2
        else
            echo "  process: $SERVER_PID (exited before readiness)" >&2
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
        if ! kill -0 "$SERVER_PID" 2>/dev/null; then
            boot_diagnostics "spawned kernel exited before readiness"
            return 1
        fi
        if [ -z "$PORT" ]; then
            PORT="$(discover_bound_port)"
        fi
        if [ -n "$PORT" ] && ! process_is_expected; then
            boot_diagnostics "spawned kernel changed identity before readiness"
            return 1
        fi
        if [ -n "$PORT" ] &&
            curl -fsS --connect-timeout 1 --max-time 1 \
                "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
            if ! process_is_expected; then
                boot_diagnostics "spawned kernel exited or changed identity after health response"
                return 1
            fi
            return 0
        fi
        sleep 0.2
    done
    boot_diagnostics "/health was not ready within ${timeout}s"
    return 1
}

PYTHON="${PYTHON:-$HOME/.brainstem/venv/bin/python}"
[ -x "$PYTHON" ] || PYTHON="$(command -v python3)"

echo "▶ testing immutable kernel evidence on an OS-assigned process-owned port (python: $PYTHON)"
( cd "$BRAINSTEM_DIR" && exec env -i \
    PATH="$PATH" HOME="$TEST_HOME" USERPROFILE="$TEST_HOME" \
    TMPDIR="$WORK_DIR" PYTHONPATH="$OFFLINE_GUARD" \
    RAPP1_OFFLINE=1 RAPP1_EXTERNAL_NETWORK=deny \
    PORT=0 PYTHONUNBUFFERED=1 \
    "$PYTHON" "$BRAINSTEM_SCRIPT" ) > "$LOG" 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"

wait_for_health
echo "  ready: pid=$SERVER_PID port=$PORT"

HEALTH="$(curl -s "http://127.0.0.1:$PORT/health")"
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
VERSION_API="$(curl -s "http://127.0.0.1:$PORT/version" | sed -n 's/.*"version":"\([^"]*\)".*/\1/p')"
[ "$VERSION_FILE" = "$VERSION_API" ] || {
    echo "FAIL: /version mismatch (file=$VERSION_FILE api=$VERSION_API)"
    exit 1
}

# /agents file listing must include at least basic_agent.py and one *_agent.py
AGENTS="$(curl -s "http://127.0.0.1:$PORT/agents")"
echo "$AGENTS" | grep -q "basic_agent.py" || {
    echo "FAIL: /agents listing missing basic_agent.py"
    exit 1
}
echo "$AGENTS" | grep -qE '_agent\.py' || {
    echo "FAIL: /agents listing has no *_agent.py files"
    exit 1
}

echo "✓ canonical kernel boots, /health ok, /version matches, /agents lists files"
