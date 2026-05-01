#!/usr/bin/env bash
# Run every wild-encounter fixture in order. Exit non-zero if any fail.
set -uo pipefail
cd "$(dirname "$0")"

PASS=0
FAIL=0
for t in 0*.sh; do
    [ -f "$t" ] || continue
    echo "═══ $t"
    if bash "$t"; then
        PASS=$((PASS+1))
    else
        FAIL=$((FAIL+1))
        echo "✗ $t failed"
    fi
    echo
done

echo "─────────────────────"
echo "passed: $PASS  failed: $FAIL"
[ "$FAIL" = "0" ]
