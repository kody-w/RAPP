#!/usr/bin/env bash
# Scenario 9 — Distributed Code Review.
#
# A PR is reviewed by 5 specialist contributors (security / perf / a11y /
# style / business-logic). Each runs their own analysis. Synthesizer
# produces a bibliography of concerns, attributed to which specialist
# raised which point. Consensus determines merge-readiness.

source "$(dirname "$0")/_lib.sh"
scenario_parse_args "$@"

heading "Scenario 9 — Distributed Code Review"
note "Pattern: braintrust with 5 specialist library_query overrides"
note "Showcases: multi-perspective review attributed by reviewer specialty"

TMP=$(mktemp -d -t rapp-scenario-09-XXXXXX)
trap 'rm -rf "$TMP"' EXIT
WORKSEED="$TMP/code-review"
cp -R "$SEEDS_DIR/braintrust-template" "$WORKSEED"

# Five specialist libraries — each has guidance for their angle
for spec in security perf a11y style logic; do
  mkdir -p "$TMP/lib-$spec/notes"
  cat > "$TMP/lib-$spec/notes/checklist.md" <<EOF
# $spec checklist
- check input validation
- watch for $spec antipatterns
- verify $spec tests cover the change
EOF
done

# 1. Open review request
REQ_KW='{"topic":"PR #42 — refactor checkout flow","requester_login":"author","deadline_hours":24,"min_quorum":3}'
REQ_OUT=$(run_agent_direct "$WORKSEED" "agents/braintrust_request_agent.py" "BraintrustRequestAgent" "$REQ_KW")
REQUEST_ID=$(echo "$REQ_OUT" | python3 -c "import json,sys; print(json.load(sys.stdin)['request']['request_id'])")
step_pass "code review request opened (id=$REQUEST_ID)"

# 2. Each specialist contributes from their perspective
declare -a CONTRIBS=()
for spec in security perf a11y style logic; do
  KW=$(python3 -c "import json; print(json.dumps({'request_id':'$REQUEST_ID','topic':'$spec checklist antipatterns tests','contributor_login':'$spec-bot','contributor_rappid':'fake-$spec'}))")
  C=$(LIBRARY_PATHS="$TMP/lib-$spec/notes" run_agent_direct "$WORKSEED" "agents/braintrust_contribute_agent.py" "BraintrustContributeAgent" "$KW")
  INNER=$(echo "$C" | python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin)['contribution']))")
  CONTRIBS+=("$INNER")
  HAS=$(echo "$INNER" | python3 -c "import json,sys; print(len(json.loads(sys.stdin.read())['findings']))")
  if [ "$HAS" -ge 1 ]; then
    step_pass "@$spec-bot raised $HAS concern(s)"
  else
    step_fail "@$spec-bot raised no concerns (suspicious)"
  fi
done

# 3. Synthesize — the bibliography becomes the multi-angle review
CONTRIBS_JSON=$(printf '[%s]' "$(IFS=,; echo "${CONTRIBS[*]}")")
SYN_KW=$(python3 -c "import json,sys; print(json.dumps({'request_id':'$REQUEST_ID','topic':'PR #42 — refactor checkout flow','contributions':json.loads(sys.argv[1]),'synthesizer_login':'lead','min_quorum':3}))" "$CONTRIBS_JSON")
SYN_OUT=$(run_agent_direct "$WORKSEED" "agents/braintrust_synthesize_agent.py" "BraintrustSynthesizeAgent" "$SYN_KW")
STATUS=$(echo "$SYN_OUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status'))")
if [ "$STATUS" = "ok" ]; then
  step_pass "synthesized review with all 5 specialists ($STATUS)"
else
  step_fail "synthesis: $STATUS"
fi

# 4. Cite agent verifies all 5 perspectives are represented
SLUG=$(echo "$SYN_OUT" | python3 -c "import json,sys; r=json.load(sys.stdin); print(r['report']['report_path'].replace('reports/','').replace('/report.md',''))")
CITE=$(run_agent_direct "$WORKSEED" "agents/braintrust_cite_agent.py" "BraintrustCiteAgent" "{\"report_slug\":\"$SLUG\"}")
PER=$(echo "$CITE" | python3 -c "import json,sys; print(len(json.load(sys.stdin)['per_contributor']))")
if [ "$PER" -eq 5 ]; then
  step_pass "all 5 specialist perspectives in bibliography"
else
  step_fail "bibliography only has $PER perspectives (expected 5)"
fi

heading "Why this matters"
cat <<'EOF'
  Code review at quality. Five specialists, five libraries, five separate
  perspectives — all bound together with provenance ("the security
  concern was raised by @security-bot citing checklist.md"). The PR
  author sees a unified review, but every concern is attributable. No
  more "the AI flagged this" — you see WHICH agent flagged WHAT and WHY.
EOF

scenario_summary
