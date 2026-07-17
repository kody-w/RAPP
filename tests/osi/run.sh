#!/usr/bin/env bash
# Compatibility entrypoint: RAPP/1 has one authoritative local runner.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ARGS=()
for arg in "$@"; do
    case "$arg" in
        --offline)
            # The canonical runner is always offline.
            ;;
        --help|-h)
            exec python3 "$ROOT/tests/run_rapp1_conformance.py" --help
            ;;
        *)
            echo "Unsupported legacy OSI selector: $arg" >&2
            echo "Use python3 tests/run_rapp1_conformance.py --list" >&2
            exit 2
            ;;
    esac
done

exec python3 "$ROOT/tests/run_rapp1_conformance.py" "${ARGS[@]}"
