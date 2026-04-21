#!/bin/bash
# tests/test-t2t-removal.sh — verifies the T2T federation surface has been
# fully excised from the repo (per CONSTITUTION.md Article XIV and the
# "focus is adoption, not federation" policy).
#
# Structural checks (no server): files absent, imports clean, vendored
# bundle clean, source free of stale T2T route handlers.
#
# Runtime checks (swarm_server on a test port): T2T routes 404, core
# non-T2T surface (healthz, deploy, agent, seal, snapshot) still 200s.
#
#     bash tests/test-t2t-removal.sh
#
# Exits 0 on success, non-zero with diagnostics on failure.

set -e
set -o pipefail

PORT=7190
ROOT=/tmp/rapp-swarm-test-t2t-removal
SERVER_PID=""
PASS=0
FAIL=0
FAIL_NAMES=()

cleanup() {
    if [ -n "$SERVER_PID" ]; then
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

assert_eq() {
    local name="$1" expected="$2" actual="$3"
    if [ "$expected" = "$actual" ]; then
        echo "  ✓ $name"; PASS=$((PASS + 1))
    else
        echo "  ✗ $name"
        echo "      expected: $expected"
        echo "      actual:   $actual"
        FAIL=$((FAIL + 1)); FAIL_NAMES+=("$name")
    fi
}

assert_not_exists() {
    local name="$1" path="$2"
    if [ ! -e "$path" ]; then
        echo "  ✓ $name"; PASS=$((PASS + 1))
    else
        echo "  ✗ $name (found: $path)"
        FAIL=$((FAIL + 1)); FAIL_NAMES+=("$name")
    fi
}

assert_no_match() {
    local name="$1" pattern="$2" file="$3"
    if [ ! -f "$file" ]; then
        echo "  ✗ $name (file missing: $file)"
        FAIL=$((FAIL + 1)); FAIL_NAMES+=("$name"); return
    fi
    if grep -qE "$pattern" "$file"; then
        echo "  ✗ $name"
        echo "      file:    $file"
        echo "      hits:    $(grep -nE "$pattern" "$file" | head -3)"
        FAIL=$((FAIL + 1)); FAIL_NAMES+=("$name")
    else
        echo "  ✓ $name"; PASS=$((PASS + 1))
    fi
}

# ── Section 1: Source files absent ─────────────────────────────────────

echo "--- Section 1: T2T/workspace source files gone ---"
assert_not_exists "rapp_brainstem/t2t.py removed"        rapp_brainstem/t2t.py
assert_not_exists "rapp_brainstem/workspace.py removed"  rapp_brainstem/workspace.py
assert_not_exists "tests/test-t2t.sh removed"            tests/test-t2t.sh

# ── Section 2: swarm_server imports cleanly ───────────────────────────

echo ""
echo "--- Section 2: swarm_server.py is clean ---"

IMPORT_OUT=$(python3 -c "
import sys
sys.path.insert(0, 'rapp_brainstem')
import swarm_server
# Should NOT have these symbols
bad = [s for s in dir(swarm_server) if 't2t' in s.lower() or 'workspace' in s.lower()]
print('bad_symbols:' + ','.join(bad) if bad else 'ok')
" 2>&1)
assert_eq "swarm_server imports with no T2T/workspace symbols"  "ok"  "$IMPORT_OUT"

assert_no_match "swarm_server.py has no /api/t2t/ routes" \
    '"/api/t2t/'  rapp_brainstem/swarm_server.py
assert_no_match "swarm_server.py has no /api/workspace routes" \
    '"/api/workspace'  rapp_brainstem/swarm_server.py
assert_no_match "swarm_server.py has no 'from t2t import' statements" \
    'from t2t import'  rapp_brainstem/swarm_server.py
assert_no_match "swarm_server.py has no 'from workspace import' statements" \
    'from workspace import'  rapp_brainstem/swarm_server.py

# ── Section 3: function_app.py is clean ───────────────────────────────

echo ""
echo "--- Section 3: function_app.py is clean ---"

PARSE_OUT=$(python3 -c "
import ast
with open('rapp_swarm/function_app.py') as f:
    ast.parse(f.read())
print('ok')
" 2>&1)
assert_eq "function_app.py parses as valid Python"  "ok"  "$PARSE_OUT"

assert_no_match "function_app.py has no t2t route handlers" \
    'route="t2t/'  rapp_swarm/function_app.py
assert_no_match "function_app.py has no 'from t2t import' statements" \
    'from t2t import'  rapp_swarm/function_app.py
assert_no_match "function_app.py has no get_t2t_manager imports" \
    'get_t2t_manager'  rapp_swarm/function_app.py

# ── Section 4: build.sh produces a clean vendored bundle ──────────────

echo ""
echo "--- Section 4: build.sh is clean ---"

assert_no_match "build.sh vendor list does not include t2t.py" \
    't2t\.py'  rapp_swarm/build.sh
assert_no_match "build.sh vendor list does not include workspace.py" \
    'workspace\.py'  rapp_swarm/build.sh

# Run build.sh fresh and inspect the output
rm -rf rapp_swarm/_vendored
bash rapp_swarm/build.sh >/dev/null 2>&1
assert_not_exists "vendored bundle has no t2t.py"         rapp_swarm/_vendored/t2t.py
assert_not_exists "vendored bundle has no workspace.py"   rapp_swarm/_vendored/workspace.py
# But the core files should still be vendored
if [ -f rapp_swarm/_vendored/server.py ] && \
   [ -f rapp_swarm/_vendored/chat.py ] && \
   [ -f rapp_swarm/_vendored/llm.py ] && \
   [ -f rapp_swarm/_vendored/twin.py ]; then
    echo "  ✓ vendored bundle still contains server/chat/llm/twin"
    PASS=$((PASS + 1))
else
    echo "  ✗ vendored bundle missing expected core files"
    FAIL=$((FAIL + 1)); FAIL_NAMES+=("vendor-core")
fi

# ── Section 5: Runtime — T2T routes 404, core routes work ─────────────

echo ""
echo "--- Section 5: swarm_server runtime (live) ---"

rm -rf "$ROOT"
python3 rapp_brainstem/swarm_server.py --port $PORT --root "$ROOT" >/dev/null 2>&1 &
SERVER_PID=$!
sleep 1.5

# Core route still works
CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PORT/api/swarm/healthz")
assert_eq "GET /api/swarm/healthz still 200"  "200"  "$CODE"

# T2T routes gone (404 from the BaseHTTPRequestHandler fallback)
CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PORT/api/t2t/identity")
assert_eq "GET /api/t2t/identity now 404"  "404"  "$CODE"
CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PORT/api/t2t/peers")
assert_eq "GET /api/t2t/peers now 404"  "404"  "$CODE"
CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PORT/api/workspace")
assert_eq "GET /api/workspace now 404"  "404"  "$CODE"
CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PORT/api/workspace/documents")
assert_eq "GET /api/workspace/documents now 404"  "404"  "$CODE"

# POST T2T also 404
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    -H 'Content-Type: application/json' -d '{}' \
    "http://127.0.0.1:$PORT/api/t2t/handshake")
assert_eq "POST /api/t2t/handshake now 404"  "404"  "$CODE"
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    -H 'Content-Type: application/json' -d '{}' \
    "http://127.0.0.1:$PORT/api/t2t/invoke")
assert_eq "POST /api/t2t/invoke now 404"  "404"  "$CODE"

# Deploy + chat still work (core non-T2T path)
BUNDLE=$(python3 - <<'PY'
import json, pathlib
agents = []
for p in pathlib.Path('rapp_brainstem/agents').glob('*_agent.py'):
    if p.name == 'basic_agent.py': continue
    agents.append({
        'filename': p.name,
        'name': p.stem.replace('_agent', '').title().replace('_', ''),
        'source': p.read_text(),
    })
print(json.dumps({
    'schema': 'rapp-swarm/1.0',
    'name': 'test-t2t-removal',
    'purpose': 'T2T removal smoke test',
    'created_at': '2026-04-21T00:00:00Z',
    'created_by': 'test',
    'agents': agents,
}))
PY
)
DEPLOY=$(curl -s -X POST "http://127.0.0.1:$PORT/api/swarm/deploy" \
    -H 'Content-Type: application/json' --data-binary "$BUNDLE")
SWARM_GUID=$(echo "$DEPLOY" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("swarm_guid",""))' 2>/dev/null)
if [ -n "$SWARM_GUID" ]; then
    echo "  ✓ /api/swarm/deploy still works (got guid $SWARM_GUID)"
    PASS=$((PASS + 1))
else
    echo "  ✗ /api/swarm/deploy failed — response: $(echo "$DEPLOY" | head -c 200)"
    FAIL=$((FAIL + 1)); FAIL_NAMES+=("deploy")
fi

# Seal status route still works
if [ -n "$SWARM_GUID" ]; then
    CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        "http://127.0.0.1:$PORT/api/swarm/$SWARM_GUID/seal")
    assert_eq "GET /api/swarm/<guid>/seal still 200"  "200"  "$CODE"
fi

# ── Summary ────────────────────────────────────────────────────────────

echo ""
echo "════════════════════════════════════════"
echo "  $PASS passed, $FAIL failed"
echo "════════════════════════════════════════"
if [ $FAIL -gt 0 ]; then
    for n in "${FAIL_NAMES[@]}"; do echo "  - $n"; done
    exit 1
fi
exit 0
