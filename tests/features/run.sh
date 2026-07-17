#!/usr/bin/env bash
# Compatibility entrypoint: legacy product feature tests are not RAPP/1 gates.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
case "${1:-}" in
    "")
        exec python3 "$ROOT/tests/run_rapp1_conformance.py"
        ;;
    --offline)
        exec python3 "$ROOT/tests/run_rapp1_conformance.py"
        ;;
    --help|-h)
        exec python3 "$ROOT/tests/run_rapp1_conformance.py" --help
        ;;
    *)
        echo "Unsupported legacy feature-suite option: $1" >&2
        echo "Run individual product fixtures explicitly when needed." >&2
        exit 2
        ;;
esac
