#!/usr/bin/env bash
#
# Mirror Spec drift check.
# Verifies that this repo's kernel files are byte-identical to grail
# (kody-w/rapp-installer). A drifted kernel breaks offline interop and
# the platform's central promise.
#
# See pages/vault/Architecture/Mirror Spec.md
#
set -e

GRAIL_RAW="https://raw.githubusercontent.com/kody-w/rapp-installer/main"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

FILES=(
    "rapp_brainstem/brainstem.py"
    "rapp_brainstem/VERSION"
    "rapp_brainstem/agents/basic_agent.py"
)

failed=0
for f in "${FILES[@]}"; do
    if diff <(curl -fsSL "$GRAIL_RAW/$f") "$REPO_ROOT/$f" >/dev/null 2>&1; then
        echo "OK    $f"
    else
        echo "DRIFT $f"
        failed=1
    fi
done

if [ "$failed" = "1" ]; then
    echo ""
    echo "Mirror has drifted from grail. Restore with:"
    echo "  cp ~/Documents/GitHub/Rappter/rapp-installer/rapp_brainstem/brainstem.py rapp_brainstem/"
    echo "  cp ~/Documents/GitHub/Rappter/rapp-installer/rapp_brainstem/VERSION rapp_brainstem/"
    echo "  cp ~/Documents/GitHub/Rappter/rapp-installer/rapp_brainstem/agents/basic_agent.py rapp_brainstem/agents/"
    exit 1
fi
