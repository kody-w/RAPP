#!/usr/bin/env bash
# Assert the target-owned planter is a side-effect-free HTTP 410 retirement.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLANT="$ROOT/installer/plant.sh"

for executable in "$PLANT" "$ROOT/installer/integration_plant.sh"; do
    test -x "$executable"
    bash -n "$executable"
    set +e
    OUTPUT="$(cd "$ROOT" && bash "$executable" 2>&1)"
    STATUS=$?
    set -e
    if [ "$STATUS" -ne 78 ]; then
        echo "FAIL: $(basename "$executable") returned $STATUS; expected 78" >&2
        exit 1
    fi
    case "$OUTPUT" in
        *"410 Gone"*) ;;
        *)
            echo "FAIL: $(basename "$executable") has no 410 notice" >&2
            printf '%s\n' "$OUTPUT" >&2
            exit 1
            ;;
    esac
done

case "$(bash "$PLANT" 2>&1 || true)" in
    *RAPP1_STATUS.md*) ;;
    *) echo "FAIL: planter retirement notice has no status guidance" >&2; exit 1 ;;
esac

if grep -Eq \
    'GRAIL_RAW=|write_index_html|rapp-frame/|brainstem-egg/|gh repo create|git push|curl |Invoke-WebRequest' \
    "$PLANT" "$ROOT/installer/integration_plant.sh"; then
    echo "FAIL: retired planter still contains a producer or side-effect path" >&2
    exit 1
fi

for route in \
    installer/plant.html \
    installer/plant_qr.html \
    installer/seed.html \
    pages/metropolis/plant-from-discord.html
do
    grep -qi "HTTP 410" "$ROOT/$route" || {
        echo "FAIL: $route is not a 410 tombstone" >&2
        exit 1
    }
    if grep -Eqi '<script|<iframe|<form|fetch\(|plant\.sh' "$ROOT/$route"; then
        echo "FAIL: $route retains an executable caller" >&2
        exit 1
    fi
done

if grep -q 'plant-from-discord' "$ROOT/pages/metropolis/index.html"; then
    echo "FAIL: metropolis still links the retired caller" >&2
    exit 1
fi

echo "plant retirement: shell and browser callers return 410 with no producer path"
