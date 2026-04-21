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

# Python modules the function app imports directly.
for src in llm.py twin.py _basic_agent_shim.py; do
    if [ -f "$ROOT/rapp_brainstem/$src" ]; then
        cp "$ROOT/rapp_brainstem/$src" "$DEST/$src"
        echo "  ✓ $src"
    else
        echo "  ⚠ missing: $src"
    fi
done

# Package marker for the vendor directory itself.
[ -f "$DEST/__init__.py" ] || touch "$DEST/__init__.py"

# Starter + swarm-management agents — shipped with the engine so Tier 2
# has the same default agent surface as Tier 1 on first boot. Users'
# own agents land in BRAINSTEM_HOME/agents/ and take precedence.
if [ -d "$ROOT/rapp_brainstem/agents" ]; then
    for src in "$ROOT/rapp_brainstem/agents"/*.py; do
        [ -f "$src" ] || continue
        cp "$src" "$DEST/agents/"
    done
    echo "  ✓ agents/*.py ($(ls "$DEST/agents/" | wc -l | tr -d ' ') files)"
fi

echo "▶ Done. Function App is ready to publish."
echo "    cd rapp_swarm && func azure functionapp publish <APP_NAME> --build remote"
