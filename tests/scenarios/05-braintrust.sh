#!/usr/bin/env bash
# Scenario 5 — Project Braintrust (federated research with bibliography).
#
# Simulates the full flow:
#   1. Operator A drops a research request
#   2. Three contributors each query THEIR own library
#   3. Each posts a contribution with provenance
#   4. Synthesizer merges into a bibliography-annotated report
#   5. Cite agent verifies the citation graph
#   6. "Neighborhood adapts to who's home" — drop one contributor, re-synthesize, ship
#
# Run:
#     bash tests/scenarios/05-braintrust.sh
#     bash tests/scenarios/05-braintrust.sh --dry-run

source "$(dirname "$0")/_lib.sh"
scenario_parse_args "$@"

heading "Scenario 5 — Project Braintrust (federated research)"
note "Seed: $SEEDS_DIR/braintrust-template"
note "Mode: kind=braintrust, visibility=private-workspace, neighborhood-adapts-to-whats-home"

SEED="$SEEDS_DIR/braintrust-template"

# 1. Seed structure
if [ ! -f "$SEED/neighborhood.json" ]; then
  step_fail "seed missing"; scenario_summary
fi
step_pass "seed present"

KIND=$(python3 -c "import json; print(json.load(open('$SEED/neighborhood.json'))['kind'])")
if [ "$KIND" = "braintrust" ]; then
  step_pass "kind = braintrust"
else
  step_fail "expected kind=braintrust, got $KIND"
fi

VIS=$(python3 -c "import json; print(json.load(open('$SEED/neighborhood.json'))['visibility'])")
if [ "$VIS" = "private-workspace" ]; then
  step_pass "visibility = private-workspace"
else
  step_fail "expected visibility=private-workspace, got $VIS"
fi

# Stage three contributor libraries in a tmpdir + a working seed copy.
TMP=$(mktemp -d -t rapp-scenario-05-XXXXXX)
trap 'rm -rf "$TMP"' EXIT
cp -R "$SEED" "$TMP/seed"
WORKSEED="$TMP/seed"

# Three "contributor libraries" — three operators with different stores.
mkdir -p "$TMP/lib-kody/notes" "$TMP/lib-rappter1/notes" "$TMP/lib-bill/notes"

cat > "$TMP/lib-kody/notes/master-plan.md" <<'EOF'
# RAPP Master Plan
The platform's load-bearing principle is: use everyone else's hardware to run the network.
GitHub is the substrate; agents are the only extension; kernel sacred.
EOF

cat > "$TMP/lib-rappter1/notes/neighborhood-protocol.md" <<'EOF'
# Neighborhood Protocol
GitHub collaborator status is the trust anchor. Operators federate via
cached membership; rosters reconcile from the live API on each sync.
The network adapts to who is home.
EOF

cat > "$TMP/lib-bill/notes/se-team-design.md" <<'EOF'
# SE Team Hood Design
A neighborhood for an SE team should let each member contribute their own
agents while preserving operator identity through the federation. The
braintrust pattern lets contributors query their own libraries and report
back with provenance.
EOF

# 2. braintrust_request — create a research request
heading "Step 2 — braintrust_request (open new request)"
REQ_KW='{"topic":"How does the RAPP network adapt to absent contributors?","requester_login":"kody-w","requester_rappid":"cc1ae0f4-8a61-4c36-b096-f075984350a3","deadline_hours":24,"min_quorum":2,"library_kinds_requested":["files","memory"]}'
REQ_OUT=$(run_agent_direct "$WORKSEED" "agents/braintrust_request_agent.py" "BraintrustRequestAgent" "$REQ_KW")
echo "$REQ_OUT" | head -25
REQUEST_ID=$(echo "$REQ_OUT" | python3 -c "import json,sys; print(json.load(sys.stdin)['request']['request_id'])")
if [ -n "$REQUEST_ID" ]; then
  step_pass "braintrust_request returned request_id=$REQUEST_ID"
else
  step_fail "braintrust_request did not return a request_id"
fi

# 3. library_query — each contributor's library returns findings
heading "Step 3 — library_query against three contributor libraries"
for who in kody rappter1 bill; do
  RESULT=$(LIBRARY_PATHS="$TMP/lib-$who/notes" run_agent_direct "$WORKSEED" "agents/library_query_agent.py" "LibraryQueryAgent" '{"topic":"network adapt absent contributors libraries"}')
  COUNT=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['findings_count'])")
  if [ "$COUNT" -ge 1 ]; then
    step_pass "library_query for @$who returned $COUNT finding(s)"
  else
    step_fail "library_query for @$who returned 0 findings (expected ≥1)"
  fi
done

# 4. braintrust_contribute — package findings as contributions
heading "Step 4 — braintrust_contribute (each contributor packages findings)"
declare -a CONTRIBS=()
for who in kody rappter1 bill; do
  KW=$(printf '{"request_id":"%s","topic":"How does the RAPP network adapt to absent contributors?","contributor_login":"%s","contributor_rappid":"fake-rappid-%s"}' "$REQUEST_ID" "$who" "$who")
  CONTRIB=$(LIBRARY_PATHS="$TMP/lib-$who/notes" run_agent_direct "$WORKSEED" "agents/braintrust_contribute_agent.py" "BraintrustContributeAgent" "$KW")
  CONTRIB_INNER=$(echo "$CONTRIB" | python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin)['contribution']))")
  CONTRIBS+=("$CONTRIB_INNER")
  HAS_FINDINGS=$(echo "$CONTRIB_INNER" | python3 -c "import json,sys; print(len(json.loads(sys.stdin.read())['findings']))")
  if [ "$HAS_FINDINGS" -ge 1 ]; then
    step_pass "@$who contribution packaged with $HAS_FINDINGS finding(s)"
  else
    step_fail "@$who contribution had no findings"
  fi
done

# 5. braintrust_synthesize — merge into report
heading "Step 5 — braintrust_synthesize (3 contributors home, quorum met)"
CONTRIBS_JSON=$(printf '[%s]' "$(IFS=,; echo "${CONTRIBS[*]}")")
SYN_KW=$(python3 -c "import json,sys; print(json.dumps({'request_id':'$REQUEST_ID','topic':'How does the RAPP network adapt to absent contributors?','contributions':json.loads(sys.argv[1]),'synthesizer_login':'kody-w','synthesizer_rappid':'cc1ae0f4-8a61-4c36-b096-f075984350a3','min_quorum':2}))" "$CONTRIBS_JSON")
SYN_OUT=$(run_agent_direct "$WORKSEED" "agents/braintrust_synthesize_agent.py" "BraintrustSynthesizeAgent" "$SYN_KW")
echo "$SYN_OUT" | head -25
SYN_STATUS=$(echo "$SYN_OUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status'))")
if [ "$SYN_STATUS" = "ok" ]; then
  step_pass "synthesis ok with 3 contributors home"
else
  step_fail "synthesis status: $SYN_STATUS"
fi

REPORT_PATH=$(echo "$SYN_OUT" | python3 -c "import json,sys; r=json.load(sys.stdin); print(r['report']['report_path'])")
if [ -f "$WORKSEED/$REPORT_PATH" ] && grep -q "Bibliography" "$WORKSEED/$REPORT_PATH"; then
  step_pass "report.md written with Bibliography section"
else
  step_fail "report.md missing or has no Bibliography section"
fi

CITATION_COUNT=$(echo "$SYN_OUT" | python3 -c "import json,sys; r=json.load(sys.stdin); print(r['report']['citation_count'])")
if [ "$CITATION_COUNT" -ge 3 ]; then
  step_pass "report has $CITATION_COUNT citations (≥3 — one per contributor)"
else
  step_fail "report has only $CITATION_COUNT citations (expected ≥3)"
fi

# 6. braintrust_cite — verify the citation graph
heading "Step 6 — braintrust_cite (verify report citations)"
SLUG=$(echo "$REPORT_PATH" | sed 's|reports/||;s|/report.md||')
CITE_KW=$(printf '{"report_slug":"%s"}' "$SLUG")
CITE_OUT=$(run_agent_direct "$WORKSEED" "agents/braintrust_cite_agent.py" "BraintrustCiteAgent" "$CITE_KW")
echo "$CITE_OUT" | head -20
PER_CONTRIB=$(echo "$CITE_OUT" | python3 -c "import json,sys; print(len(json.load(sys.stdin)['per_contributor']))")
if [ "$PER_CONTRIB" -eq 3 ]; then
  step_pass "cite agent confirms 3 distinct contributors in bibliography"
else
  step_fail "cite agent saw $PER_CONTRIB contributors (expected 3)"
fi

# 7. NEIGHBORHOOD ADAPTS TO WHO'S HOME — drop one contributor, re-synthesize
heading "Step 7 — Adapt-to-whats-home (1 contributor offline, quorum=2)"
PARTIAL_CONTRIBS=("${CONTRIBS[0]}" "${CONTRIBS[1]}")  # bill goes offline
CONTRIBS_JSON2=$(printf '[%s]' "$(IFS=,; echo "${PARTIAL_CONTRIBS[*]}")")
SYN_KW2=$(python3 -c "import json,sys; print(json.dumps({'request_id':'$REQUEST_ID','topic':'How does the RAPP network adapt to absent contributors?','contributions':json.loads(sys.argv[1]),'synthesizer_login':'kody-w','min_quorum':2}))" "$CONTRIBS_JSON2")
SYN_OUT2=$(run_agent_direct "$WORKSEED" "agents/braintrust_synthesize_agent.py" "BraintrustSynthesizeAgent" "$SYN_KW2")
SYN_STATUS2=$(echo "$SYN_OUT2" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status'))")
if [ "$SYN_STATUS2" = "ok" ]; then
  step_pass "synthesis ok with 2 contributors home (quorum exactly met — bill is gone, neighborhood adapts)"
else
  step_fail "synthesis status with 2 home: $SYN_STATUS2 (expected ok)"
fi

# 8. Below quorum — defer
heading "Step 8 — Below quorum returns deferred (1 contributor, min_quorum=2)"
SOLO_CONTRIBS=("${CONTRIBS[0]}")
CONTRIBS_JSON3=$(printf '[%s]' "$(IFS=,; echo "${SOLO_CONTRIBS[*]}")")
SYN_KW3=$(python3 -c "import json,sys; print(json.dumps({'request_id':'$REQUEST_ID','topic':'How does the RAPP network adapt to absent contributors?','contributions':json.loads(sys.argv[1]),'synthesizer_login':'kody-w','min_quorum':2}))" "$CONTRIBS_JSON3")
SYN_OUT3=$(run_agent_direct "$WORKSEED" "agents/braintrust_synthesize_agent.py" "BraintrustSynthesizeAgent" "$SYN_KW3")
SYN_STATUS3=$(echo "$SYN_OUT3" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status'))")
if [ "$SYN_STATUS3" = "deferred" ]; then
  step_pass "below-quorum returns deferred (won't ship sub-quorum without force)"
else
  step_fail "below-quorum status: $SYN_STATUS3 (expected deferred)"
fi

# 9. Force-quorum ships anyway
heading "Step 9 — force_quorum=true ships with whats home"
SYN_KW4=$(python3 -c "import json,sys; print(json.dumps({'request_id':'$REQUEST_ID','topic':'How does the RAPP network adapt to absent contributors?','contributions':json.loads(sys.argv[1]),'synthesizer_login':'kody-w','min_quorum':2,'force_quorum':True}))" "$CONTRIBS_JSON3")
SYN_OUT4=$(run_agent_direct "$WORKSEED" "agents/braintrust_synthesize_agent.py" "BraintrustSynthesizeAgent" "$SYN_KW4")
SYN_STATUS4=$(echo "$SYN_OUT4" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status'))")
if [ "$SYN_STATUS4" = "ok" ]; then
  step_pass "force_quorum ships with what's home (1 contributor)"
else
  step_fail "force_quorum status: $SYN_STATUS4 (expected ok)"
fi

heading "What to test by hand"
cat <<EOF
  1. Plant the braintrust:
       cd $SEED
       git init -b main && git add . && git commit -m "Plant Project Braintrust"
       gh repo create kody-w/<braintrust-name> --private --source . --push

  2. Add contributors (each becomes a librarian):
       gh api -X PUT /repos/kody-w/<braintrust>/collaborators/rappter1 -f permission=push
       gh api -X PUT /repos/kody-w/<braintrust>/collaborators/<bill> -f permission=push

  3. Each contributor's brainstem subscribes:
       brainstem join https://github.com/kody-w/<braintrust>

  4. Each contributor optionally drops a richer library_query_agent.py into their
     personal agents/ directory (overrides the default — knows about their
     vault / Notion / private repos / RAG index).

  5. Drop a request:
       (via brainstem chat) "open a braintrust request: how does X work?"

  6. Other contributors' brainstems pick it up via braintrust_contribute_agent
     and post their findings as Issue comments. (Phase 2 will auto-poll;
     Phase 1 is on-demand.)

  7. Run synthesize after deadline / quorum:
       (via brainstem chat) "synthesize the report for request <id>"

  8. Review + merge the PR. Final report lives at reports/<slug>/report.md.

  9. The neighborhood adapts to who's home — re-run synthesis any time;
     if a contributor was removed or never showed, the report still ships
     with what was contributed by present members.
EOF

scenario_summary
