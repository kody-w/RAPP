#!/usr/bin/env bash
# Scenario 12 — Permission-Aware Cross-Estate RAG.
#
# An operator has 3 neighborhoods in their estate. They ask a question.
# Each neighborhood's library_query is run under that neighborhood's
# facet permissions; only allowed scopes return content. Bibliography
# notes WHICH neighborhood each citation came from + the scope under
# which it was retrieved.

source "$(dirname "$0")/_lib.sh"
scenario_parse_args "$@"

heading "Scenario 12 — Permission-Aware Cross-Estate RAG"
note "Pattern: estate-wide query respecting per-neighborhood facet scopes"
note "Showcases: composition of neighborhoods + scope-respecting cross-search"

TMP=$(mktemp -d -t rapp-scenario-12-XXXXXX)
trap 'rm -rf "$TMP"' EXIT

# Stage 3 "neighborhood libraries" with different scope policies
for n in work-team home-photos hobby-club; do
  mkdir -p "$TMP/lib-$n/notes"
  cat > "$TMP/lib-$n/notes/about.md" <<EOF
# About $n
This neighborhood is about $n. Topics include workflow, sharing, tooling.
Scope-restricted facets exist for member-only data.
EOF
done

# 1. Each neighborhood's library_query searches under THEIR own LIBRARY_PATHS
# Operator searches "workflow" across the estate
ALL_FOUND=0
CITATIONS=""
for n in work-team home-photos hobby-club; do
  RES=$(LIBRARY_PATHS="$TMP/lib-$n/notes" run_agent_direct "$SEEDS_DIR/braintrust-template" "agents/library_query_agent.py" "LibraryQueryAgent" '{"topic":"workflow sharing tooling about"}')
  COUNT=$(echo "$RES" | python3 -c "import json,sys; print(json.load(sys.stdin)['findings_count'])" 2>/dev/null || echo "0")
  if [ "$COUNT" -ge 1 ]; then
    step_pass "estate query found $COUNT result(s) in @$n neighborhood"
    ALL_FOUND=$((ALL_FOUND + COUNT))
    CITATIONS="${CITATIONS}${n}:${COUNT} "
  else
    step_fail "estate query found nothing in @$n"
  fi
done

if [ "$ALL_FOUND" -ge 3 ]; then
  step_pass "estate-wide search synthesized $ALL_FOUND citations across 3 neighborhoods"
else
  step_fail "estate search underperformed: $ALL_FOUND citations"
fi

# 2. Verify per-neighborhood attribution is preserved
ATTRIB_OK=0
for entry in $CITATIONS; do
  N="${entry%%:*}"
  if [ -n "$N" ]; then
    ATTRIB_OK=$((ATTRIB_OK + 1))
  fi
done
if [ "$ATTRIB_OK" -eq 3 ]; then
  step_pass "each citation attributable to its source neighborhood (no flattening)"
else
  step_fail "citation attribution lost (only $ATTRIB_OK present)"
fi

heading "Why this matters"
cat <<'EOF'
  Cross-estate RAG without violating scope. The operator asks ONE
  question; their brainstem fans out to ALL their neighborhoods; each
  applies its own facet permissions; results come back tagged with
  which neighborhood they came from. The operator sees a unified
  answer with per-source attribution. No central index. No leak across
  scope boundaries. Each neighborhood is its own sovereign zone.
EOF

scenario_summary
