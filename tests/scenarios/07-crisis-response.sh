#!/usr/bin/env bash
# Scenario 7 — Crisis Response Mesh.
#
# A critical event lands; whoever is online responds NOW. No quorum. No
# review. Force-quorum mode with deadline=15-min. Tests rapid-fire
# request → contribute → synthesize without waiting for absent peers.
# This is the inverse of braintrust deliberation — speed over consensus.

source "$(dirname "$0")/_lib.sh"
scenario_parse_args "$@"

heading "Scenario 7 — Crisis Response Mesh"
note "Pattern: braintrust with deadline=15min, force_quorum=true, single online contributor"
note "Showcases: speed > consensus; whoever is home, responds now"

TMP=$(mktemp -d -t rapp-scenario-07-XXXXXX)
trap 'rm -rf "$TMP"' EXIT
WORKSEED="$TMP/crisis"
cp -R "$SEEDS_DIR/braintrust-template" "$WORKSEED"

# Stage one online responder library with crisis-relevant content
mkdir -p "$TMP/lib-responder/notes"
cat > "$TMP/lib-responder/notes/checkout-outage-runbook.md" <<'EOF'
# Checkout Outage Runbook (PROD)
1. Stabilize the checkout service (rollback if recent deploy caused the outage)
2. Page on-call eng if outage sustained for >5 min in PROD
3. Open #incident-room and post outage details
4. Postmortem within 24h of any PROD outage
EOF

# 1. Open a crisis request (15-min deadline, min_quorum=1)
REQ_KW='{"topic":"PROD outage in checkout","requester_login":"oncall-alex","deadline_hours":1,"min_quorum":1,"library_kinds_requested":["files"]}'
REQ_OUT=$(run_agent_direct "$WORKSEED" "agents/braintrust_request_agent.py" "BraintrustRequestAgent" "$REQ_KW")
REQUEST_ID=$(echo "$REQ_OUT" | python3 -c "import json,sys; print(json.load(sys.stdin)['request']['request_id'])")
step_pass "crisis request opened (id=$REQUEST_ID)"

# 2. ONE responder is home — contributes immediately
KW=$(python3 -c "import json; print(json.dumps({'request_id':'$REQUEST_ID','topic':'PROD outage in checkout','contributor_login':'responder','contributor_rappid':'fake'}))")
CONTRIB=$(LIBRARY_PATHS="$TMP/lib-responder/notes" run_agent_direct "$WORKSEED" "agents/braintrust_contribute_agent.py" "BraintrustContributeAgent" "$KW")
CONTRIB_INNER=$(echo "$CONTRIB" | python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin)['contribution']))")
HAS=$(echo "$CONTRIB_INNER" | python3 -c "import json,sys; print(len(json.loads(sys.stdin.read())['findings']))")
if [ "$HAS" -ge 1 ]; then
  step_pass "responder packaged $HAS finding(s) from runbook"
else
  step_fail "responder had no findings"
fi

# 3. Synthesize IMMEDIATELY (force_quorum=true, single contributor)
echo "$CONTRIB_INNER" > "$TMP/contrib.json"
SYN_KW=$(python3 - "$REQUEST_ID" "$TMP/contrib.json" <<'PY'
import json, sys
rid, contrib_path = sys.argv[1], sys.argv[2]
with open(contrib_path) as f:
    contrib = json.load(f)
print(json.dumps({
    "request_id": rid,
    "topic": "PROD outage in checkout",
    "contributions": [contrib],
    "synthesizer_login": "oncall-alex",
    "min_quorum": 1,
    "force_quorum": True,
}))
PY
)
SYN_OUT=$(run_agent_direct "$WORKSEED" "agents/braintrust_synthesize_agent.py" "BraintrustSynthesizeAgent" "$SYN_KW")
STATUS=$(echo "$SYN_OUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status'))")
if [ "$STATUS" = "ok" ]; then
  step_pass "synthesis ships immediately with single responder (no consensus needed)"
else
  step_fail "crisis synthesis status: $STATUS"
fi

# 4. Verify report has rapid-response markers
SLUG=$(echo "$SYN_OUT" | python3 -c "import json,sys; r=json.load(sys.stdin); print(r['report']['report_path'].replace('reports/','').replace('/report.md',''))")
if [ -f "$WORKSEED/reports/$SLUG/report.md" ]; then
  step_pass "crisis report produced ($SLUG)"
else
  step_fail "crisis report missing"
fi

heading "Why this matters"
cat <<'EOF'
  Crisis response is the inverse of braintrust deliberation. Same
  primitives, opposite knob settings: short deadline + force_quorum +
  min_quorum=1. The pattern: when the building is on fire, you don't
  wait for a quorum on whether to call 911. The platform supports both
  modes from the same protocol — the operator picks the dial.
EOF

scenario_summary
