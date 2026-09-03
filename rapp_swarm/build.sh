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

# Historical source provenance (fullest known implementation).
# commit: 7bcc3d24ab3759605630625225fd190612c3d594
# blob: ddcdf06751f7100511d53ba1e6a84c8ac6b803f9
# sha256: 9f9a786d61f623e001923b89f6b83ca85549452a58dc41e357120c0afb157fb9
historical_build() (
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
        echo "  ✓ utils/$src (brainstem)"
    else
        echo "  ⚠ missing: utils/$src"
    fi
done

# Tier-2 cloud-specific utils (Azure File Storage, Azure OpenAI error
# types, Result[T,E] types, local filesystem fallback). Live in
# rapp_swarm/utils/ because they are NOT Tier 1 concerns — brainstem
# has no Azure-SDK dependencies.
if [ -d utils ]; then
    for src in utils/*.py; do
        [ -f "$src" ] || continue
        base=$(basename "$src")
        cp "$src" "$DEST/utils/$base"
        echo "  ✓ utils/$base (tier-2)"
    done
fi

# Package markers for the vendor tree.
[ -f "$DEST/__init__.py" ]       || touch "$DEST/__init__.py"
[ -f "$DEST/utils/__init__.py" ] || touch "$DEST/utils/__init__.py"

# Agent tree — per CONSTITUTION Article XVII / XII, agents/ is a
# user-organized tree. Vendor it recursively, mirroring Tier 1's shape,
# but skip the two subdirs that never auto-load in either tier:
# experimental_agents/ and disabled_agents/. __pycache__ is also skipped.
if command -v rsync &>/dev/null; then
    rsync -a \
        --exclude='__pycache__' \
        --exclude='experimental_agents' \
        --exclude='disabled_agents' \
        "$ROOT/rapp_brainstem/agents/" "$DEST/agents/"
else
    # Fallback for systems without rsync (Windows/Git Bash)
    cp -R "$ROOT/rapp_brainstem/agents/"* "$DEST/agents/" 2>/dev/null || true
    rm -rf "$DEST/agents/__pycache__" "$DEST/agents/experimental_agents" "$DEST/agents/disabled_agents" 2>/dev/null || true
fi
echo "  ✓ agents/ tree ($(find "$DEST/agents" -name '*_agent.py' | wc -l | tr -d ' ') agent files)"

# Services tree — drop-in HTTP endpoints (swarms, binder, etc.)
# Same discovery pattern as agents: services/*_service.py.
if [ -d "$ROOT/rapp_brainstem/services" ]; then
    mkdir -p "$DEST/services"
    cp "$ROOT/rapp_brainstem/services"/*_service.py "$DEST/services/" 2>/dev/null || true
    echo "  ✓ services/ tree ($(find "$DEST/services" -name '*_service.py' 2>/dev/null | wc -l | tr -d ' ') service files)"
fi

# function_app.py's load_agents_from_folder() does `os.listdir("./agents")`
# relative to function_app.py's directory. Copy (not symlink) the
# vendored agent tree to that sibling path — `func azure functionapp
# publish` zips the deploy tree and symlinks don't always survive.
rm -rf agents
cp -R _vendored/agents agents
echo "  ✓ agents/ (copy for function_app.py lookup + Azure deploy zip)"

# Same for services — copy to root for function_app.py lookup.
if [ -d _vendored/services ]; then
    rm -rf services
    cp -R _vendored/services services
    echo "  ✓ services/ (copy for function_app.py lookup + Azure deploy zip)"
fi

echo "▶ Done. Function App is ready to publish."
echo "    cd rapp_swarm && func azure functionapp publish <APP_NAME> --build remote"
)

print_plan() {
    printf '%s\n' \
        '{"schema":"rapp-swarm-build-plan/1.0","mode":"plan","source":"rapp_brainstem","destination":"rapp_swarm/_vendored","historical_source_commit":"7bcc3d24ab3759605630625225fd190612c3d594","effects":[],"accepted":false}' \
        'No files are copied, removed, packaged, or published in plan mode.'
}

refuse_apply() {
    printf '%s\n' \
        '{"schema":"rapp-effect-refusal/1.0","operation":"swarm-vendor-build","code":"authenticated-registry-unavailable","effects_started":false,"requirements":["reviewed-dependency-injection","exact-target-receipt","authenticated-fresh-section-13-evidence"]}' \
        'Current authority is structural only; build application is refused before rm, mkdir, cp, rsync, or packaging.' >&2
    return 78
}

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
    unset -f historical_build print_plan refuse_apply
    return 0
fi

case "${1:-plan}" in
    plan|--plan|inspect|--inspect|check|--check)
        print_plan
        ;;
    apply|--apply|run|--run)
        refuse_apply
        ;;
    help|-h|--help)
        printf '%s\n' \
            'Usage: build.sh [--plan|--inspect|--check|--apply]' \
            'Default: deterministic read-only vendoring plan.' \
            '--apply requires reviewed dependency injection, an exact target receipt,' \
            'and authenticated fresh RAPP/1 section-13 evidence; unavailable here.'
        ;;
    *)
        printf 'Unknown mode: %s\n' "$1" >&2
        exit 2
        ;;
esac
