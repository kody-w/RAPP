#!/usr/bin/env bash
# The kernel's stdout/stderr UTF-8 wrapper must engage on any non-Unicode
# terminal encoding — not just cp* (Windows codepages) but also gbk,
# shift_jis, euc-kr, ascii, etc. Without it, the startup banner's emoji
# (🧠) crashes on the print() with UnicodeEncodeError.
#
# Asserts:
#   - immutable kernel evidence boots under LC_ALL=C PYTHONUTF8=0
#   - PORT=0 gives the process an OS-assigned port
#   - /health responds within the boot window
#   - the startup banner's emoji is not what kills the process
#
# Reference: extends 95be0bc (cp-only wrapper) to all non-Unicode encodings.

set -euo pipefail
cd "$(dirname "$0")/../.."

BRAINSTEM_DIR="${RAPP1_BRAINSTEM_BOOT_DIR:-$(pwd)/rapp_brainstem}"
PYTHON="${PYTHON:-$HOME/.brainstem/venv/bin/python}"
[ -x "$PYTHON" ] || PYTHON="$(command -v python3)"

WORK_DIR="${TMPDIR:-$(pwd)/tests/.rapp1-work}/organism-06-$$"
mkdir -p "$WORK_DIR"
if [ -z "${RAPP1_BRAINSTEM_BOOT_DIR:-}" ]; then
    mkdir -p "$WORK_DIR/runtime"
    git archive --format=tar HEAD rapp_brainstem |
        tar -xf - -C "$WORK_DIR/runtime"
    BRAINSTEM_DIR="$WORK_DIR/runtime/rapp_brainstem"
fi
TEST_HOME="$WORK_DIR/home"
mkdir -p "$TEST_HOME"
OFFLINE_GUARD="$(pwd)/tests/offline_guard"
LOG="$WORK_DIR/brainstem.log"

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

discover_bound_port() {
    sed -nE \
        's#^.*Running on http://127\.0\.0\.1:([0-9]+).*$#\1#p' \
        "$LOG" 2>/dev/null | tail -n 1
}

echo "▶ testing immutable kernel evidence under LC_ALL=C PYTHONUTF8=0 on an OS-assigned port"
( cd "$BRAINSTEM_DIR" && \
    exec env -i PATH="$PATH" HOME="$TEST_HOME" USERPROFILE="$TEST_HOME" \
    TMPDIR="$WORK_DIR" PYTHONPATH="$OFFLINE_GUARD" \
    RAPP1_OFFLINE=1 RAPP1_EXTERNAL_NETWORK=deny \
    LC_ALL=C LANG=C PYTHONUTF8=0 PORT=0 "$PYTHON" brainstem.py ) > "$LOG" 2>&1 &
SERVER_PID=$!

for i in $(seq 1 30); do
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
        echo "FAIL: immutable kernel evidence exited before readiness"
        tail -30 "$LOG"
        exit 1
    fi
    PORT="$(discover_bound_port)"
    if [ -n "$PORT" ] && curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
        break
    fi
    sleep 0.5
    if [ "$i" = "30" ]; then
        echo "FAIL: immutable kernel evidence did not boot under ASCII locale in 15s"
        echo "--- log tail ---"
        tail -30 "$LOG"
        exit 1
    fi
done

# Verify the kernel actually printed its startup banner — the emoji line
# is the proof point (without the broadened wrapper, this would crash).
grep -q "RAPP Brainstem v" "$LOG" || {
    echo "FAIL: startup banner missing from log"
    tail -30 "$LOG"
    exit 1
}

# /health must answer
HEALTH="$(curl -s "http://127.0.0.1:$PORT/health")"
echo "$HEALTH" | grep -q '"status":"unauthenticated"' || {
    echo "FAIL: /health discovered ambient credentials"
    echo "  body: $HEALTH"
    exit 1
}

echo "✓ stdout wrapper engages on non-Unicode encodings; banner survives ASCII locale"
