#!/bin/bash
# RAPP_RESTORED_SOURCE_COMMIT=925dee4a211965f2582e71a6d2ad75f60a54ea7d
# RAPP_RESTORED_SOURCE_BLOB=6455bd18e1e42e379b983dd325e2412d373b4ffa
# RAPP_RESTORED_TARGET=installer/start-local.sh
# RAPP_RESTORED_GATE_BEGIN
_RAPP_TARGET="installer/start-local.sh"
_RAPP_COMMIT="925dee4a211965f2582e71a6d2ad75f60a54ea7d"
_RAPP_BLOB="6455bd18e1e42e379b983dd325e2412d373b4ffa"
_RAPP_PIN_SHA256="427a37cc914a279b9c32a2ab85be9a19a0046f10f9f503c088a2670b6646e21c"
_rapp_plan() {
    printf '{"schema":"rapp-restored-distribution-source/1.0","target":"%s","mode":"plan","source_commit":"%s","source_blob":"%s","kernel":"kody-w/rapp-installer@brainstem-v0.6.9","kernel_pin_sha256":"%s","apply_permitted":false,"reason":"authenticated-section-13-evidence-unavailable"}\n' \
        "$_RAPP_TARGET" "$_RAPP_COMMIT" "$_RAPP_BLOB" "$_RAPP_PIN_SHA256"
}
_rapp_refuse() {
    printf '410 Gone: %s: %s (RAPP1_STATUS.md)\n' "$_RAPP_TARGET" "$1" >&2
    exit 78
}
_rapp_expect_line() {
    IFS= read -r _rapp_actual || return 1
    [ "$_rapp_actual" = "$1" ]
}
_rapp_expect_last_line() {
    _rapp_actual=""
    IFS= read -r _rapp_actual
    _rapp_status=$?
    [ "$_rapp_status" -ne 0 ] && [ "$_rapp_actual" = "$1" ]
}
_rapp_pin_matches() {
    [ -f "$1" ] || return 1
    {
        _rapp_expect_line '{' &&
        _rapp_expect_line '  "spec": "rapp-distro/1.0",' &&
        _rapp_expect_line '  "distro": "RAPP (the reference distro)",' &&
        _rapp_expect_line '  "kernel": {' &&
        _rapp_expect_line '    "grail": "kody-w/rapp-installer",' &&
        _rapp_expect_line '    "tag": "brainstem-v0.6.9",' &&
        _rapp_expect_line '    "frozen": {' &&
        _rapp_expect_line '      "rapp_brainstem/brainstem.py": "a293dd9f11eef915bf15776f08c736faa60cb749820871b6753ea98233142a71",' &&
        _rapp_expect_line '      "rapp_brainstem/agents/basic_agent.py": "701488bc00d536a7b23295e7da99c62f24e9b00f233daa325886430c736b78eb",' &&
        _rapp_expect_line '      "rapp_brainstem/VERSION": "13eb74b44be6e3a85a0efa0dedf56aec05e9e50140e1c8bbc0d0fbd8097b0717"' &&
        _rapp_expect_line '    }' &&
        _rapp_expect_line '  },' &&
        _rapp_expect_line '  "channel": "lts",' &&
        _rapp_expect_line "  \"note\": \"RAPP tracks the grail (kody-w/rapp-installer). Pinned at brainstem-v0.6.9, the grail's current kernel release — a deliberate distro bump from v0.6.0 ordered in kody-w/RAPP#83 (the grail feeds RAPP; RAPP's vendored copy tracks it). Verified byte-identical to the grail tag.\"" &&
        _rapp_expect_last_line '}' &&
        ! IFS= read -r _rapp_extra
    } < "$1"
}
_RAPP_MODE=${1:-plan}
[ "$#" -eq 0 ] || shift
case "$_RAPP_MODE" in
    plan|--plan|inspect|--inspect|check|--check|help|--help|-h)
        _rapp_plan
        exit 0
        ;;
    apply|--apply|run|--run) ;;
    *) _rapp_refuse "explicit plan/check/inspect or gated --apply is required" ;;
esac
_RAPP_ALLOW=0
_RAPP_REQUESTED_TARGET=""
_RAPP_PIN=""
_RAPP_INJECTION=""
_RAPP_APPROVAL=""
_RAPP_EVIDENCE=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --allow-active-effects) _RAPP_ALLOW=1; shift ;;
        --target|--kernel-pin|--reviewed-dependency-injection|--owner-approval|--section13-evidence)
            [ "$#" -ge 2 ] || _rapp_refuse "missing value for $1"
            _rapp_option=$1
            _rapp_value=$2
            shift 2
            case "$_rapp_option" in
                --target) _RAPP_REQUESTED_TARGET=$_rapp_value ;;
                --kernel-pin) _RAPP_PIN=$_rapp_value ;;
                --reviewed-dependency-injection) _RAPP_INJECTION=$_rapp_value ;;
                --owner-approval) _RAPP_APPROVAL=$_rapp_value ;;
                --section13-evidence) _RAPP_EVIDENCE=$_rapp_value ;;
            esac
            ;;
        *) _rapp_refuse "unsupported activation argument: $1" ;;
    esac
done
[ "$_RAPP_ALLOW" -eq 1 ] || _rapp_refuse "--allow-active-effects is required"
[ "$_RAPP_REQUESTED_TARGET" = "$_RAPP_TARGET" ] || _rapp_refuse "target-specific approval target is missing or mismatched"
_rapp_pin_matches "$_RAPP_PIN" || _rapp_refuse "exact KERNEL_PIN.json for kody-w/rapp-installer@brainstem-v0.6.9 is required"
[ -f "$_RAPP_INJECTION" ] || _rapp_refuse "reviewed dependency injection evidence is required"
[ -f "$_RAPP_APPROVAL" ] || _rapp_refuse "target-specific owner approval is required"
[ -f "$_RAPP_EVIDENCE" ] || _rapp_refuse "authenticated fresh section-13 evidence is required"
_rapp_refuse "authenticated fresh section-13 evidence is unavailable"
# RAPP_RESTORED_GATE_END
# RAPP_RESTORED_HISTORICAL_SOURCE_BEGIN
#!/bin/bash
# start-local.sh — RAPP local-first launcher.
#
# Boots the full local-first stack on this machine:
#   • Static file server on :8000  (serves the mobile PWA + onboard page)
#   • Optional: swarm server on :7080 (run with --swarm)
#
# For OS-access (tether) endpoints, run the brainstem separately — it serves
# the rapp-tether/1.0 wire shape on :7071. See rapp_brainstem/start.sh.
#
# Then opens the mobile PWA in your default browser.
#
# Stops everything cleanly on Ctrl-C.
#
# Usage:
#     ./start-local.sh                    # static + open PWA
#     ./start-local.sh --swarm            # also start the local swarm server
#     ./start-local.sh --no-open          # don't open browser
#     ./start-local.sh --port 9000        # static server port (default 8000)
#
# Requirements: python3 (already on every Mac/Linux). NOTHING ELSE.

set -e
cd "$(dirname "$0")"

PORT=8000
SWARM_PORT=7080
START_SWARM=0
OPEN_BROWSER=1

while [ $# -gt 0 ]; do
    case "$1" in
        --swarm)      START_SWARM=1 ;;
        --no-open)    OPEN_BROWSER=0 ;;
        --port)       PORT="$2"; shift ;;
        --help|-h)
            grep '^#' "$0" | sed 's/^# \?//'
            exit 0 ;;
        *) echo "unknown flag: $1"; exit 2 ;;
    esac
    shift
done

PIDS=()
cleanup() {
    echo ""
    echo "▶ Stopping local services…"
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    echo "  Stopped. State preserved in IndexedDB (browser) and ~/.rapp-twins/ (filesystem)."
}
trap cleanup EXIT INT TERM

# ── Static file server (serves the mobile PWA + everything in repo) ────

echo "▶ Static file server on :$PORT"
lsof -ti:"$PORT" 2>/dev/null | xargs -r kill -9 2>/dev/null
python3 -m http.server "$PORT" >/tmp/rapp-static.log 2>&1 &
PIDS+=($!)

# ── Optional swarm server (multi-tenant local hosting) ────────────────

if [ "$START_SWARM" = "1" ] && [ -f rapp_brainstem/brainstem.py ]; then
    echo "▶ Swarm server on :$SWARM_PORT"
    lsof -ti:"$SWARM_PORT" 2>/dev/null | xargs -r kill -9 2>/dev/null
    python3 rapp_brainstem/brainstem.py --port "$SWARM_PORT" --root ~/.rapp-swarm >/tmp/rapp-swarm.log 2>&1 &
    PIDS+=($!)
fi

# ── Wait for static server to be ready (it boots fast) ─────────────────
sleep 1

URL="http://127.0.0.1:$PORT/rapp_brainstem/web/mobile/"

cat <<EOF

════════════════════════════════════════════════════════════════
  ✓ RAPP LOCAL-FIRST STACK RUNNING
════════════════════════════════════════════════════════════════

  📱 Mobile PWA:        $URL
  🌐 Onboard hatch:     http://127.0.0.1:$PORT/rapp_brainstem/web/onboard/
  🧠 Brainstem (OG):    http://127.0.0.1:$PORT/brainstem/
EOF

if [ "$START_SWARM" = "1" ]; then
    echo "  🐝 Swarm endpoint:    http://127.0.0.1:$SWARM_PORT/api/swarm/healthz"
fi

cat <<EOF

  Logs (tail to debug):
    tail -f /tmp/rapp-static.log
EOF
[ "$START_SWARM"  = "1" ] && echo "    tail -f /tmp/rapp-swarm.log"

cat <<EOF

  Ctrl-C to stop everything cleanly.

════════════════════════════════════════════════════════════════

EOF

if [ "$OPEN_BROWSER" = "1" ]; then
    if command -v open >/dev/null;     then open "$URL"
    elif command -v xdg-open >/dev/null; then xdg-open "$URL"
    fi
fi

# Wait forever (until Ctrl-C → cleanup trap)
wait
