#!/usr/bin/env bash

set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE="$ROOT/rapp_swarm/twin-egg.sh"

set +e
OUTPUT="$(bash "$SOURCE" pack --out should-not-exist.egg 2>&1)"
STATUS=$?
set -e

if [ "$STATUS" -ne 78 ]; then
    echo "expected retirement exit 78, got $STATUS" >&2
    exit 1
fi
case "$OUTPUT" in
    *"410 Gone"*RAPP1_STATUS.md*) ;;
    *)
        echo "retirement notice is incomplete: $OUTPUT" >&2
        exit 1
        ;;
esac
if [ -e "$ROOT/should-not-exist.egg" ] || [ -e "should-not-exist.egg" ]; then
    echo "retired executable created an artifact" >&2
    exit 1
fi
if grep -Eq 'cmd_(pack|unpack)|zipfile|extractall' "$SOURCE"; then
    echo "legacy egg implementation remains reachable" >&2
    exit 1
fi

echo "twin egg retirement: fail-closed with no artifact"
