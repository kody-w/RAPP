#!/bin/bash
# hippocampus/build.sh — vendor swarm/ → hippocampus/_swarm/ so the
# Function App is a self-contained deploy unit.
#
# Run before `func azure functionapp publish` (or before `func start`
# inside this directory).
#
#     bash hippocampus/build.sh

set -e
cd "$(dirname "$0")"

ROOT="$(cd .. && pwd)"
DEST=_swarm

echo "▶ Vendoring swarm core into hippocampus/$DEST/"
rm -rf "$DEST"
mkdir -p "$DEST"

# Copy each Python module the function app imports
for f in server.py llm.py chat.py t2t.py _basic_agent_shim.py; do
    if [ -f "$ROOT/swarm/$f" ]; then
        cp "$ROOT/swarm/$f" "$DEST/$f"
        echo "  ✓ $f"
    fi
done

# Make it a package
[ -f "$DEST/__init__.py" ] || touch "$DEST/__init__.py"

echo "▶ Done. Function App is ready to publish."
echo "    cd hippocampus && func azure functionapp publish <APP_NAME> --build remote"
