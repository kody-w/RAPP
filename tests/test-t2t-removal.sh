#!/bin/bash
# tests/test-t2t-removal.sh — verifies the T2T federation surface has been
# fully excised from the repo (per CONSTITUTION.md Article XIV and the
# "focus is adoption, not federation" policy).
#
# Structural checks: removed files stay absent, the retained vendored evidence
# stays free of T2T modules, and retired Tier 2 entrypoints refuse execution.
#
#     bash tests/test-t2t-removal.sh
#
# Exits 0 on success, non-zero with diagnostics on failure.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PASS=0
FAIL=0
FAIL_NAMES=()

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

tree_hash() {
    python3 - "$1" <<'PY'
import hashlib
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
digest = hashlib.sha256()
for path in sorted(item for item in root.rglob("*") if item.is_file()):
    digest.update(path.relative_to(root).as_posix().encode())
    digest.update(bytes([0]))
    digest.update(path.read_bytes())
    digest.update(bytes([0]))
print(digest.hexdigest())
PY
}

# ── Section 1: Source files absent ─────────────────────────────────────

echo "--- Section 1: T2T/workspace source files gone ---"
assert_not_exists "rapp_brainstem/t2t.py removed"        rapp_brainstem/t2t.py
assert_not_exists "rapp_brainstem/workspace.py removed"  rapp_brainstem/workspace.py
assert_not_exists "tests/test-t2t.sh removed"            tests/test-t2t.sh

# ── Section 2: swarm_server.py / chat.py entirely removed ─────────────

echo ""
echo "--- Section 2: swarm_server.py and chat.py entirely gone ---"

assert_not_exists "rapp_brainstem/swarm_server.py removed"  rapp_brainstem/swarm_server.py
assert_not_exists "rapp_brainstem/chat.py removed"          rapp_brainstem/chat.py

# ── Section 3: function_app.py is an inert tombstone ──────────────────

echo ""
echo "--- Section 3: function_app.py is an inert tombstone ---"

PARSE_OUT=$(python3 -c "
import ast
with open('rapp_swarm/function_app.py') as f:
    ast.parse(f.read())
print('ok')
" 2>&1)
assert_eq "function_app.py parses as valid Python"  "ok"  "$PARSE_OUT"

set +e
TOMBSTONE_OUT=$(python3 rapp_swarm/function_app.py 2>&1)
TOMBSTONE_RC=$?
set -e
assert_eq "function_app.py refuses execution" "78" "$TOMBSTONE_RC"
case "$TOMBSTONE_OUT" in
    *"410 Gone"*) echo "  ✓ function_app.py reports 410 Gone"; PASS=$((PASS + 1)) ;;
    *) echo "  ✗ function_app.py does not report 410 Gone"
       FAIL=$((FAIL + 1)); FAIL_NAMES+=("function_app.py 410 tombstone") ;;
esac

# ── Section 4: build.sh is inert and vendored evidence stays clean ────

echo ""
echo "--- Section 4: build.sh is clean ---"

assert_no_match "build.sh vendor list does not include t2t.py" \
    't2t\.py'  rapp_swarm/build.sh
assert_no_match "build.sh vendor list does not include workspace.py" \
    'workspace\.py'  rapp_swarm/build.sh

VENDORED_BEFORE="$(tree_hash rapp_swarm/_vendored)"
set +e
BUILD_OUT="$(bash rapp_swarm/build.sh 2>&1)"
BUILD_RC=$?
set -e
assert_eq "build.sh refuses execution" "78" "$BUILD_RC"
case "$BUILD_OUT" in
    *"410 Gone"*) echo "  ✓ build.sh reports 410 Gone"; PASS=$((PASS + 1)) ;;
    *) echo "  ✗ build.sh does not report 410 Gone"
       FAIL=$((FAIL + 1)); FAIL_NAMES+=("build.sh 410 tombstone") ;;
esac
assert_eq "build.sh leaves vendored evidence unchanged" \
    "$VENDORED_BEFORE" "$(tree_hash rapp_swarm/_vendored)"

assert_not_exists "vendored bundle has no t2t.py"         rapp_swarm/_vendored/t2t.py
assert_not_exists "vendored bundle has no workspace.py"   rapp_swarm/_vendored/workspace.py
assert_not_exists "vendored bundle has no server.py"      rapp_swarm/_vendored/server.py
assert_not_exists "vendored bundle has no chat.py"        rapp_swarm/_vendored/chat.py
# Core runtime deps live under utils/ in the vendor tree now
# (Article XVI — root stays minimal, support modules in utils/).
if [ -f rapp_swarm/_vendored/utils/llm.py ] && \
   [ -f rapp_swarm/_vendored/utils/twin.py ] && \
   [ -f rapp_swarm/_vendored/utils/_basic_agent_shim.py ]; then
    echo "  ✓ vendored bundle contains utils/llm + utils/twin + utils/_basic_agent_shim"
    PASS=$((PASS + 1))
else
    echo "  ✗ vendored bundle missing expected core files"
    FAIL=$((FAIL + 1)); FAIL_NAMES+=("vendor-core")
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
