#!/usr/bin/env bash
# Scenario 11 — Apprentice / Mentor.
#
# A junior operator's brainstem watches a senior's brainstem (with
# consent). Each significant decision the senior logs becomes a learning
# record for the apprentice. Over time, the apprentice can suggest
# decisions before the senior makes them. Tests the observer pattern
# + frame-log composability.

source "$(dirname "$0")/_lib.sh"
scenario_parse_args "$@"

heading "Scenario 11 — Apprentice / Mentor"
note "Pattern: shared private-workspace where senior writes; apprentice reads + suggests"
note "Showcases: observer pattern + decision-record-as-training-signal"

TMP=$(mktemp -d -t rapp-scenario-11-XXXXXX)
trap 'rm -rf "$TMP"' EXIT
WORKSEED="$TMP/apprentice"
cp -R "$SEEDS_DIR/private-workspace-template" "$WORKSEED"

# 1. Senior bootstraps the workspace
SR=$(run_agent_direct "$WORKSEED" "agents/workspace_init_agent.py" "WorkspaceInitAgent" '{"purpose":"Senior + apprentice shared workspace. Apprentice observes; senior teaches by deciding.","founder_login":"senior"}')
if echo "$SR" | grep -q '"status": "ok"'; then
  step_pass "senior bootstraps workspace"
else
  step_fail "senior bootstrap failed"
fi

# 2. Senior makes 3 decisions; apprentice reads them all
for i in 1 2 3; do
  KW=$(python3 -c "import json; print(json.dumps({'title':'Decision $i','decided_by':'senior','decision':'Senior chose option A for case $i','why':'Pattern teaching: when X, prefer A over B because Y.'}))")
  D=$(run_agent_direct "$WORKSEED" "agents/workspace_decision_agent.py" "WorkspaceDecisionAgent" "$KW")
  if echo "$D" | grep -q '"status": "ok"'; then
    step_pass "senior decision $i recorded"
  else
    step_fail "senior decision $i failed"
  fi
done

# 3. Apprentice can read the full decision log
COUNT=$(ls "$WORKSEED/state/decisions/"*.md 2>/dev/null | wc -l | tr -d ' ')
# 1 bootstrap + 3 senior decisions = 4
if [ "$COUNT" -eq 4 ]; then
  step_pass "apprentice can read all 4 decision records"
else
  step_fail "expected 4 decisions, found $COUNT"
fi

# 4. Apprentice queries their library_query against the senior's decision log.
#    Use the braintrust seed as the agent host (its library_query is generic);
#    point LIBRARY_PATHS at the senior's decisions to make THAT the training corpus.
QUERY_KW='{"topic":"senior chose option teaching pattern decision"}'
QUERY=$(LIBRARY_PATHS="$WORKSEED/state/decisions" run_agent_direct "$SEEDS_DIR/braintrust-template" "agents/library_query_agent.py" "LibraryQueryAgent" "$QUERY_KW")
COUNT=$(echo "$QUERY" | python3 -c "import json,sys; print(json.load(sys.stdin)['findings_count'])")
if [ "$COUNT" -ge 3 ]; then
  step_pass "apprentice's library_query finds $COUNT decision records as training signal"
else
  step_fail "apprentice's library_query found $COUNT (expected ≥3)"
fi

heading "Why this matters"
cat <<'EOF'
  The decision log IS the training signal. The apprentice doesn't need
  to be in the room when the senior decides — they read the why on their
  own time. As the corpus grows, an apprentice library_query against the
  log returns the senior's prior reasoning on similar cases. Eventually
  the apprentice can SUGGEST: "based on @senior's prior decisions about X,
  this looks like another option-A case." Mentorship at async scale.
EOF

scenario_summary
