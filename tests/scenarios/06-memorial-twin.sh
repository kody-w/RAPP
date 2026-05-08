#!/usr/bin/env bash
# Scenario 6 — Memorial Twin.
#
# A planted organism continues after its operator is gone. The neighborhood
# is the family/community that maintains the voice. New memories are
# additive (people contribute stories); the organism's soul stays canonical.
# Demonstrates: persistent identity beyond operator lifetime, additive-only
# memory contribution, multi-contributor curatorship.

source "$(dirname "$0")/_lib.sh"
scenario_parse_args "$@"

heading "Scenario 6 — Memorial Twin"
note "Pattern: planted organism + private-workspace neighborhood for community curation"
note "Showcases: identity persists beyond operator; family contributes additive memories"

TMP=$(mktemp -d -t rapp-scenario-06-XXXXXX)
trap 'rm -rf "$TMP"' EXIT
SEED_BASE="$SEEDS_DIR/private-workspace-template"
WORKSEED="$TMP/memorial"
cp -R "$SEED_BASE" "$WORKSEED"

# 1. Customize: rename to memorial twin
python3 - "$WORKSEED" <<'PY'
import json, sys
p = sys.argv[1] + "/neighborhood.json"
n = json.load(open(p))
n["name"] = "memorial-twin-grandma-rose"
n["display_name"] = "Memorial Twin — Rose Wildfeuer (1932-2026)"
n["kind"] = "memorial"
n["purpose"] = "Family contributes stories + memories that grow Rose's twin voice over time. Original soul.md is canonical and never edited; memories are additive only."
n["membership_policy"]["additive_only"] = True
n["membership_policy"]["original_soul_immutable"] = True
json.dump(n, open(p, "w"), indent=2)
PY
step_pass "memorial neighborhood configured (kind=memorial, additive-only policy)"

# 2. Bootstrap with workspace_init — first decision is "why this exists"
INIT_KW='{"purpose":"Preserve Rose'\''s voice. Family adds stories; her soul is canonical.","founder_login":"kody-w"}'
INIT=$(run_agent_direct "$WORKSEED" "agents/workspace_init_agent.py" "WorkspaceInitAgent" "$INIT_KW")
if echo "$INIT" | grep -q '"status": "ok"'; then
  step_pass "founder bootstrap decision logged"
else
  step_fail "founder bootstrap failed"
fi

# 3. Three family members each log an additive memory as a decision narrative
for who in dad aunt-may cousin-kayla; do
  KW=$(python3 -c "import json; print(json.dumps({'title':'Story from $who','decided_by':'$who','decision':'$who remembers Rose loved sourdough Sundays','why':'Capture before the memory fades.'}))")
  OUT=$(run_agent_direct "$WORKSEED" "agents/workspace_decision_agent.py" "WorkspaceDecisionAgent" "$KW")
  if echo "$OUT" | grep -q '"status": "ok"'; then
    step_pass "@$who contributed an additive memory"
  else
    step_fail "@$who memory contribution failed"
  fi
done

# 4. Verify all 4 decisions exist + are append-only (not overwritten)
COUNT=$(ls "$WORKSEED/state/decisions/"*.md 2>/dev/null | wc -l | tr -d ' ')
if [ "$COUNT" -eq 4 ]; then
  step_pass "all 4 contributions persisted (1 founder + 3 family)"
else
  step_fail "expected 4 contributions, found $COUNT"
fi

# 5. Invite agent prepares the gh command for adding a 4th family member
INV_KW='{"github_login":"uncle-tom","permission":"push","reason":"family curator"}'
INV=$(run_agent_direct "$WORKSEED" "agents/workspace_invite_agent.py" "WorkspaceInviteAgent" "$INV_KW")
if echo "$INV" | grep -q "uncle-tom"; then
  step_pass "invite agent composes gh command for 4th family member"
else
  step_fail "invite agent envelope unexpected"
fi

heading "Why this matters"
cat <<'EOF'
  Memorial twins are the test case for: identity that persists beyond its
  operator, additive-only contribution semantics (no edits to canonical
  soul), and multi-curator governance. Same primitives the platform already
  has; the additive-only flag is the only new policy. Bill's SE Team can
  use the same pattern for "decisions our team has made over the decade"
  — write-once, never lose-context.
EOF

scenario_summary
