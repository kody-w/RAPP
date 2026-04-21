#!/bin/bash
# rapp_swarm/build.sh — vendor brainstem core dependencies → _vendored/
# so the Function App is a self-contained deploy unit.
#
# Run before `func azure functionapp publish` (or before `func start`
# inside this directory):
#
#     bash rapp_swarm/build.sh
#
# function_app.py imports from the vendor tree: llm.py (provider
# dispatch), twin.py (calibration helpers), _basic_agent_shim.py (so
# agents can `from agents.basic_agent import BasicAgent` unmodified).
# Starter + swarm-management agents are also copied so Tier 2 has the
# same default agent surface as Tier 1.

set -e
cd "$(dirname "$0")"

ROOT="$(cd .. && pwd)"
DEST=_vendored

echo "▶ Vendoring rapp_brainstem core into rapp_swarm/$DEST/"
rm -rf "$DEST"
mkdir -p "$DEST"
mkdir -p "$DEST/agents"

# Support modules live under utils/ (Article XVI — root stays minimal).
# Vendor the utils/ tree so function_app.py's `from utils.llm import …`
# and `from utils import twin` resolve inside _vendored/.
mkdir -p "$DEST/utils"
for src in llm.py twin.py _basic_agent_shim.py; do
    if [ -f "$ROOT/rapp_brainstem/utils/$src" ]; then
        cp "$ROOT/rapp_brainstem/utils/$src" "$DEST/utils/$src"
        echo "  ✓ utils/$src"
    else
        echo "  ⚠ missing: utils/$src"
    fi
done

# Package markers for the vendor tree.
[ -f "$DEST/__init__.py" ]       || touch "$DEST/__init__.py"
[ -f "$DEST/utils/__init__.py" ] || touch "$DEST/utils/__init__.py"

# Agent tree — per CONSTITUTION Article XVII / XII, agents/ is a
# user-organized tree. Vendor it recursively, mirroring Tier 1's shape,
# but skip the two subdirs that never auto-load in either tier:
# experimental_agents/ and disabled_agents/. __pycache__ is also skipped.
rsync -a \
    --exclude='__pycache__' \
    --exclude='experimental_agents' \
    --exclude='disabled_agents' \
    "$ROOT/rapp_brainstem/agents/" "$DEST/agents/"
echo "  ✓ agents/ tree ($(find "$DEST/agents" -name '*_agent.py' | wc -l | tr -d ' ') agent files)"

echo "▶ Done. Function App is ready to publish."
echo "    cd rapp_swarm && func azure functionapp publish <APP_NAME> --build remote"
