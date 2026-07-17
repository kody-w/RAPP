#!/usr/bin/env bash
# Immutable evidence: directly exercise the pinned UI only in this isolated test.
set -euo pipefail
cd "$(dirname "$0")/../.."

BRAINSTEM_DIR="${RAPP1_BRAINSTEM_BOOT_DIR:-$(pwd)/rapp_brainstem}"
PYTHON="${PYTHON:-python3}"
if [ -x "$HOME/.brainstem/venv/bin/python" ]; then
    PYTHON="$HOME/.brainstem/venv/bin/python"
fi
BRAINSTEM_SCRIPT="$BRAINSTEM_DIR/brainstem.py"
PORT=""
WORK_DIR="${TMPDIR:-$(pwd)/tests/.rapp1-work}/ui-smoke-$$"
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
OFFLINE_GUARD="$(pwd)/tests/offline_guard"
PID_FILE="$WORK_DIR/brainstem.pid"
LOG="$WORK_DIR/brainstem.log"
HTML="$WORK_DIR/index.html"
SERVER_PID=""

cleanup() {
    if [ -n "$SERVER_PID" ]; then
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
        rm -f "$PID_FILE"
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
            boot_diagnostics "spawned brainstem exited before readiness"
            return 1
        fi
        if [ -z "$PORT" ]; then
            PORT="$(discover_bound_port)"
        fi
        if [ -n "$PORT" ] && ! process_is_expected; then
            boot_diagnostics "spawned brainstem changed identity before readiness"
            return 1
        fi
        if [ -n "$PORT" ] &&
            curl -fsS --connect-timeout 1 --max-time 1 \
                "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
            if ! process_is_expected; then
                boot_diagnostics "spawned brainstem exited or changed identity after health response"
                return 1
            fi
            return 0
        fi
        sleep 0.2
    done
    boot_diagnostics "/health was not ready within ${timeout}s"
    return 1
}

echo "▶ Starting isolated immutable evidence on an OS-assigned process-owned port..."
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

HEALTH="$(curl -sf "http://127.0.0.1:$PORT/health")" || {
    boot_diagnostics "/health failed after readiness"
    exit 1
}
echo "$HEALTH" | grep -q '"status":"unauthenticated"' || {
    echo "FAIL: isolated brainstem discovered ambient credentials: $HEALTH" >&2
    exit 1
}

echo "▶ GET / ..."
HTTP=$(curl -s -o "$HTML" -w "%{http_code}" "http://127.0.0.1:$PORT/")
if [ "$HTTP" != "200" ]; then
    echo "FAIL: / returned HTTP $HTTP"
    boot_diagnostics "GET / failed after readiness"
    exit 1
fi
BYTES=$(wc -c < "$HTML")
LINES=$(wc -l < "$HTML")
if [ "$BYTES" -lt 10000 ]; then
    echo "FAIL: / returned too-small body ($BYTES bytes)"
    exit 1
fi
echo "PASS: / → 200 ($BYTES bytes, $LINES lines)"

# HTML parse sanity — use python html.parser which catches gross errors
python3 - <<EOF || { echo "FAIL: HTML parse error"; exit 1; }
from html.parser import HTMLParser
import sys
class P(HTMLParser):
    def __init__(self):
        super().__init__(); self.err = None
    def error(self, msg): self.err = msg
p = P()
with open("$HTML") as f: p.feed(f.read())
if p.err:
    print(p.err); sys.exit(1)
EOF
echo "PASS: HTML parses cleanly"

# ── Retained historical chrome markers ───────────────────────────────

check_marker() {
    local label="$1"; local pattern="$2"
    if grep -qE "$pattern" "$HTML"; then
        echo "PASS: $label"
    else
        echo "FAIL: missing marker — $label"
        echo "  expected pattern: $pattern"
        exit 1
    fi
}

echo "▶ Checking retained historical chrome markers..."
check_marker "header RAPP Brainstem title"           'RAPP Brainstem'
check_marker "status indicator element"              'id="status-text"|status-dot|class="status"'
check_marker "model-select dropdown"                 'model-select'
check_marker "footer tag present"                    '<footer'
check_marker "Export toolbar link"                   'exportChat\(\)'
check_marker "Import toolbar link"                   'chat-import'
check_marker "Clear toolbar link"                   'clearChat\(\)|Clear'
check_marker "Get Help link (diagnostics report)"    'reportToAdmin\(\)|Get Help'
check_marker "Send button"                           'id="send"|onclick="send\(\)"|Send'

# ── Retained historical feature wiring ───────────────────────────────

echo "▶ Checking retained historical feature handlers..."
check_marker "voice toggle endpoint"                 '/voice/toggle'
check_marker "voice config endpoint"                 '/voice/config'
check_marker "models list endpoint"                  '/models'
check_marker "agents API endpoint"                   '/agents'
check_marker "diagnostics export"                    '/diagnostics|exportBook'
check_marker "starter prompts"                       'starter-btn'

echo "✅ Isolated immutable UI evidence passed"
