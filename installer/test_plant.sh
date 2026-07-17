#!/usr/bin/env bash
# Assert the target-owned planter is a side-effect-free HTTP 410 retirement.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLANT="$ROOT/installer/plant.sh"

test -x "$PLANT"
bash -n "$PLANT"

set +e
OUTPUT="$(cd "$ROOT" && bash "$PLANT" 2>&1)"
STATUS=$?
set -e

if [ "$STATUS" -ne 78 ]; then
    echo "FAIL: retired planter returned $STATUS; expected 78" >&2
    exit 1
fi

case "$OUTPUT" in
    *"410 Gone"*RAPP1_STATUS.md*) ;;
    *)
        echo "FAIL: planter retirement notice is incomplete" >&2
        printf '%s\n' "$OUTPUT" >&2
        exit 1
        ;;
esac

if grep -Eq \
    'GRAIL_RAW=|write_index_html|rapp-frame/|brainstem-egg/|gh repo create|git push|curl |Invoke-WebRequest' \
    "$PLANT"; then
    echo "FAIL: retired planter still contains a producer or side-effect path" >&2
    exit 1
fi

echo "plant retirement: HTTP 410, exit 78, no producer path"
