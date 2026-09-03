#!/usr/bin/env bash
# Assert the target-owned planter is a side-effect-free retirement.

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
    grep -qi "rapp-history-source" "$ROOT/$route" || {
        echo "FAIL: $route has no historical source provenance" >&2
        exit 1
    }
    grep -qi "KERNEL_PIN.json" "$ROOT/$route" || {
        echo "FAIL: $route does not route installer context to the Grail pin" >&2
        exit 1
    }
    grep -qi "Content-Security-Policy" "$ROOT/$route" || {
        echo "FAIL: $route has no browser containment policy" >&2
        exit 1
    }
    if grep -qi "retired semantic tombstone" "$ROOT/$route"; then
        echo "FAIL: $route lost its historical body to a semantic tombstone" >&2
        exit 1
    fi
done

if ! grep -q 'plant-from-discord' "$ROOT/pages/metropolis/index.html"; then
    echo "FAIL: metropolis lost the restored mobile planning guide" >&2
    exit 1
fi

echo "plant compatibility: shell callers return 410; browser routes preserve full local planning artifacts"
