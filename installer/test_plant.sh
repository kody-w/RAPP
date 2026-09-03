#!/usr/bin/env bash
# Assert the target-owned planter preserves source behind safe defaults.

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
    if [ "$STATUS" -ne 0 ]; then
        echo "FAIL: $(basename "$executable") returned $STATUS; expected plan exit 0" >&2
        exit 1
    fi
    case "$OUTPUT" in
        *'"mode":"plan"'*'"apply_permitted":false'*) ;;
        *)
            echo "FAIL: $(basename "$executable") has no effect-free plan" >&2
            printf '%s\n' "$OUTPUT" >&2
            exit 1
            ;;
    esac
    grep -q 'RAPP_RESTORED_SOURCE_COMMIT=' "$executable"
    grep -q 'RAPP_RESTORED_HISTORICAL_SOURCE_BEGIN' "$executable"

    set +e
    REFUSAL="$(cd "$ROOT" && bash "$executable" --apply 2>&1)"
    REFUSAL_STATUS=$?
    set -e
    if [ "$REFUSAL_STATUS" -ne 78 ]; then
        echo "FAIL: $(basename "$executable") apply returned $REFUSAL_STATUS; expected 78" >&2
        exit 1
    fi
    case "$REFUSAL" in
        *"410 Gone"*RAPP1_STATUS.md*) ;;
        *) echo "FAIL: $(basename "$executable") apply refusal is incomplete" >&2; exit 1 ;;
    esac
done

grep -q 'write_index_html()' "$PLANT"
grep -q 'gh repo create' "$PLANT"
grep -q 'git push' "$PLANT"

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

echo "plant compatibility: shell callers preserve source with safe plans; browser routes preserve full local planning artifacts"
