#!/usr/bin/env bash
# UI smoke: brainstem serves /, HTML parses, and current UI handlers are present.
set -euo pipefail
cd "$(dirname "$0")/../.."

BRAINSTEM_DIR="${RAPP1_BRAINSTEM_BOOT_DIR:-$(pwd)/rapp_brainstem}"
PYTHON="${PYTHON:-python3}"
if [ -x "$HOME/.brainstem/venv/bin/python" ]; then
    PYTHON="$HOME/.brainstem/venv/bin/python"
fi
PORT="${PORT:-$("$PYTHON" - <<'PY'
import socket
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
)}"
WORK_DIR="${TMPDIR:-$(pwd)/tests/.rapp1-work}/ui-smoke-$$"
mkdir -p "$WORK_DIR"
PID_FILE="$WORK_DIR/brainstem.pid"
LOG="$WORK_DIR/brainstem.log"
HTML="$WORK_DIR/index.html"

cleanup() {
    if [ -f "$PID_FILE" ]; then
        kill "$(cat "$PID_FILE")" 2>/dev/null || true
        rm -f "$PID_FILE"
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
            boot_diagnostics "brainstem exited before /health became ready"
            return 1
        fi
        sleep 0.2
    done
    boot_diagnostics "/health was not ready within ${timeout}s"
    return 1
}

if curl -sf "http://localhost:$PORT/health" >/dev/null 2>&1; then
    echo "FAIL: refusing to reuse ambient server on :$PORT" >&2
    exit 1
fi
echo "▶ Starting isolated brainstem on :$PORT..."
( cd "$BRAINSTEM_DIR" && exec env PORT="$PORT" "$PYTHON" brainstem.py ) > "$LOG" 2>&1 &
echo $! > "$PID_FILE"
wait_for_health

HEALTH="$(curl -sf "http://localhost:$PORT/health")" || {
    boot_diagnostics "/health failed after readiness"
    exit 1
}
echo "$HEALTH" | grep -q '"status":"unauthenticated"' || {
    echo "FAIL: isolated brainstem discovered ambient credentials: $HEALTH" >&2
    exit 1
}

echo "▶ GET / ..."
HTTP=$(curl -s -o "$HTML" -w "%{http_code}" "http://localhost:$PORT/")
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

# ── Current chrome markers ────────────────────────────────────────────

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

echo "▶ Checking current chrome markers..."
check_marker "header RAPP Brainstem title"           'RAPP Brainstem'
check_marker "status indicator element"              'id="status-text"|status-dot|class="status"'
check_marker "model-select dropdown"                 'model-select'
check_marker "footer tag present"                    '<footer'
check_marker "Export toolbar link"                   'exportChat\(\)'
check_marker "Import toolbar link"                   'chat-import'
check_marker "Clear toolbar link"                   'clearChat\(\)|Clear'
check_marker "Get Help link (diagnostics report)"    'reportToAdmin\(\)|Get Help'
check_marker "Send button"                           'id="send"|onclick="send\(\)"|Send'

# ── Current feature wiring ────────────────────────────────────────────

echo "▶ Checking current feature handlers are wired..."
check_marker "voice toggle endpoint"                 '/voice/toggle'
check_marker "voice config endpoint"                 '/voice/config'
check_marker "models list endpoint"                  '/models'
check_marker "agents API endpoint"                   '/agents'
check_marker "diagnostics export"                    '/diagnostics|exportBook'
check_marker "starter prompts"                       'starter-btn'

echo "✅ UI smoke test passed"
