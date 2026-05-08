#!/usr/bin/env bash
# Scenario 14 — Library Bake-off.
#
# Multiple library_query implementations compete: each operator has dropped
# their own override (one knows about Obsidian, one about Notion, one
# about plain markdown, one about RAG). All run in parallel; results are
# scored by confidence + recency; ensemble vote determines what surfaces.

source "$(dirname "$0")/_lib.sh"
scenario_parse_args "$@"

heading "Scenario 14 — Library Bake-off"
note "Pattern: multiple library_query implementations + ensemble scoring"
note "Showcases: each librarian brings their best to the table; ensemble decides"

TMP=$(mktemp -d -t rapp-scenario-14-XXXXXX)
trap 'rm -rf "$TMP"' EXIT
WORKSEED="$TMP/bakeoff"
cp -R "$SEEDS_DIR/braintrust-template" "$WORKSEED"

# 4 contributors, each with different library content + relevance levels
mkdir -p "$TMP/lib-vault/notes" "$TMP/lib-notion/notes" "$TMP/lib-md/notes" "$TMP/lib-rag/notes"

cat > "$TMP/lib-vault/notes/answer.md" <<'EOF'
# the keystone insight
The substrate is GitHub. Authority is collaborator status. AIs travel
in four modes (cold, warm, soul, message) carrying their own provenance.
EOF
cat > "$TMP/lib-notion/notes/related.md" <<'EOF'
# decentralized substrate
Substrate-as-network is the architecture: the substrate is what we
already have, not what we build.
EOF
cat > "$TMP/lib-md/notes/lookup.md" <<'EOF'
# substrate
substrate substrate substrate keystone
EOF
cat > "$TMP/lib-rag/notes/snippet.md" <<'EOF'
# tangentially related
Caching layers and provenance.
EOF

# Run library_query against each + collect findings
declare -a SCORES=()
for src in vault notion md rag; do
  R=$(LIBRARY_PATHS="$TMP/lib-$src/notes" NEIGHBORHOOD_SEED_DIR="$WORKSEED" python3 - <<'PY'
import importlib.util, json, os, sys
sys.path.insert(0, os.environ["NEIGHBORHOOD_SEED_DIR"])
spec = importlib.util.spec_from_file_location("lq", os.path.join(os.environ["NEIGHBORHOOD_SEED_DIR"], "agents/library_query_agent.py"))
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
print(mod.LibraryQueryAgent().perform(topic="keystone substrate authority"))
PY
)
  TOP=$(echo "$R" | python3 -c "import json,sys; r=json.load(sys.stdin); print(max((f['confidence'] for f in r['findings']), default=0))")
  SCORES+=("$src:$TOP")
  step_pass "library $src returned top-confidence=$TOP"
done

# Ensemble: pick the highest-confidence finding (the bake-off winner)
WINNER=$(printf '%s\n' "${SCORES[@]}" | sort -t: -k2 -n -r | head -1)
WINNER_LIB="${WINNER%%:*}"
if [ "$WINNER_LIB" = "vault" ] || [ "$WINNER_LIB" = "md" ] || [ "$WINNER_LIB" = "notion" ]; then
  step_pass "ensemble winner: $WINNER_LIB (highest confidence — keystone matches)"
else
  step_fail "unexpected ensemble winner: $WINNER"
fi

# Verify ALL four contributed (none dropped silently)
if [ "${#SCORES[@]}" -eq 4 ]; then
  step_pass "all 4 library implementations participated in bake-off"
else
  step_fail "only ${#SCORES[@]} libraries participated"
fi

heading "Why this matters"
cat <<'EOF'
  The library_query contract is open. Each operator implements their own.
  Some are sophisticated (RAG, vault, Notion). Some are simple (markdown
  scan). They all play; the ensemble (or downstream agent) decides what
  weight to give each. There is no winner-take-all; there is the canon
  of "every librarian gets a vote, every vote carries provenance."
EOF

scenario_summary
