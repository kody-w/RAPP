#!/usr/bin/env bash

set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE="$ROOT/rapp_swarm/twin-egg.sh"

set +e
OUTPUT="$(bash "$SOURCE" pack --out should-not-exist.egg 2>&1)"
STATUS=$?
set -e

if [ "$STATUS" -ne 78 ]; then
    echo "expected pre-acceptance refusal exit 78, got $STATUS" >&2
    exit 1
fi
case "$OUTPUT" in
    *'"schema":"rapp-effect-refusal/1.0"'*'"effects_started":false'*) ;;
    *)
        echo "effect refusal is incomplete: $OUTPUT" >&2
        exit 1
        ;;
esac
if [ -e "$ROOT/should-not-exist.egg" ] || [ -e "should-not-exist.egg" ]; then
    echo "retired executable created an artifact" >&2
    exit 1
fi
grep -q 'Historical source provenance' "$SOURCE"
grep -q 'da6cb94985c9525b681bc20c2926656bdfdad565' "$SOURCE"
grep -q 'cmd_pack()' "$SOURCE"
grep -q 'cmd_unpack()' "$SOURCE"
grep -q 'zipfile' "$SOURCE"

echo "twin egg preservation: full source retained; unauthenticated pack is effect-free"
