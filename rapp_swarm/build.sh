#!/bin/bash
# rapp_swarm/build.sh — vendor rapp_brainstem/ → rapp_swarm/_vendored/
# so the Function App is a self-contained deploy unit.
#
# Run before `func azure functionapp publish` (or before `func start`
# inside this directory).
#
#     bash rapp_swarm/build.sh

set -e
cd "$(dirname "$0")"

ROOT="$(cd .. && pwd)"
DEST=_vendored

echo "▶ Vendoring rapp_brainstem core into rapp_swarm/$DEST/"
rm -rf "$DEST"
mkdir -p "$DEST"

# Copy each Python module the function app imports.
# function_app.py still imports as `server` (back-compat alias).
for src in swarm_server.py llm.py chat.py t2t.py _basic_agent_shim.py twin.py; do
    if [ -f "$ROOT/rapp_brainstem/$src" ]; then
        dest="$src"
        [ "$src" = "swarm_server.py" ] && dest="server.py"
        cp "$ROOT/rapp_brainstem/$src" "$DEST/$dest"
        echo "  ✓ $src → $dest"
    fi
done

# Make it a package
[ -f "$DEST/__init__.py" ] || touch "$DEST/__init__.py"

echo "▶ Done. Function App is ready to publish."
echo "    cd rapp_swarm && func azure functionapp publish <APP_NAME> --build remote"
