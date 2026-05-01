#!/usr/bin/env bash
# Fixture #1: canonical kernel's bare `from local_storage import ...`
# must resolve via a kernel-sibling shim, not by editing the kernel.
#
# Asserts:
#   - rapp_brainstem/local_storage.py exists at the kernel's directory level
#   - it re-exports AzureFileStorageManager from utils.local_storage
#   - the shim resolves cleanly under the same Python sys.path the kernel sets up
#
# Reference: pages/vault/Fixtures/Fixture 01 — Canonical Kernel local_storage Drop-In.md

set -euo pipefail
cd "$(dirname "$0")/../.."

SHIM="rapp_brainstem/local_storage.py"
IMPL="rapp_brainstem/utils/local_storage.py"

# 1. The shim must exist as a kernel sibling (NOT in utils/ or anywhere mutable).
[ -f "$SHIM" ] || { echo "FAIL: $SHIM does not exist (kernel-sibling shim missing)"; exit 1; }

# 2. The implementation must remain in utils/.
[ -f "$IMPL" ] || { echo "FAIL: $IMPL missing (the actual implementation is gone)"; exit 1; }

# 3. The shim must re-export AzureFileStorageManager.
grep -q "AzureFileStorageManager" "$SHIM" || {
    echo "FAIL: $SHIM does not mention AzureFileStorageManager"
    exit 1
}

# 4. The shim must NOT reach into the mutation surface (e.g., import from agents/, body_functions/).
grep -qE "from (agents|utils\.body_functions|utils\.services)" "$SHIM" && {
    echo "FAIL: shim imports from mutation surface — it must only reach into kernel-adjacent code"
    exit 1
}

# 5. The kernel itself must NOT have been edited to add sys.path manipulation
#    around the local_storage import. (The whole point of the shim is that the
#    kernel stays unchanged.)
grep -E "sys\.path\.insert.*utils_dir" rapp_brainstem/brainstem.py && {
    echo "FAIL: kernel was edited to add sys.path.insert — that defeats the additive-shim discipline"
    exit 1
}

# 6. With brainstem_dir on sys.path, the bare import must resolve.
PYTHON="${PYTHON:-$HOME/.brainstem/venv/bin/python}"
[ -x "$PYTHON" ] || PYTHON="$(command -v python3)"

OUT="$("$PYTHON" -c "
import sys
sys.path.insert(0, 'rapp_brainstem')
from local_storage import AzureFileStorageManager
print('OK', AzureFileStorageManager.__module__)
" 2>&1)"

echo "  $OUT"
echo "$OUT" | grep -q "^OK utils.local_storage$" || {
    echo "FAIL: bare import did not resolve to utils.local_storage"
    exit 1
}

echo "✓ fixture 01: kernel-sibling local_storage.py shim resolves cleanly"
