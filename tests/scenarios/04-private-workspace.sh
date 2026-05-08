#!/usr/bin/env bash
# Scenario 4 — Private workspace (Bill's pattern).
#
# Verifies the private-workspace standalone visibility: solo-then-shared,
# no public face, founder controls collaborator admission via gh CLI.
# Tests the four workspace agents (init, decision, invite, inbox).
#
# Run:
#     bash tests/scenarios/04-private-workspace.sh
#     bash tests/scenarios/04-private-workspace.sh --dry-run

source "$(dirname "$0")/_lib.sh"
scenario_parse_args "$@"

heading "Scenario 4 — Private workspace template"
note "Seed: $SEEDS_DIR/private-workspace-template"
note "Mode: private-workspace visibility (no gate)"

SEED="$SEEDS_DIR/private-workspace-template"

# 1. Seed exists + visibility right
if [ ! -f "$SEED/neighborhood.json" ]; then
  step_fail "seed missing"; scenario_summary
fi
step_pass "seed present"

VIS=$(python3 -c "import json; print(json.load(open('$SEED/neighborhood.json'))['visibility'])")
if [ "$VIS" = "private-workspace" ]; then
  step_pass "visibility = private-workspace"
else
  step_fail "expected visibility=private-workspace, got $VIS"
fi

GR=$(python3 -c "import json; print(json.load(open('$SEED/neighborhood.json')).get('gate_repo'))")
if [ "$GR" = "None" ] || [ -z "$GR" ]; then
  step_pass "gate_repo is null (no public face)"
else
  step_fail "gate_repo should be null"
fi

# Use a tmp copy so we don't dirty the template's state/ on every run.
TMP=$(mktemp -d -t rapp-scenario-04-XXXXXX)
TMPSEED="$TMP/private-workspace-template"
cp -R "$SEED" "$TMPSEED"
trap 'rm -rf "$TMP"' EXIT

# 2. workspace_init writes 0001 decision
heading "Step 2 — workspace_init (bootstrap)"
INIT_KW='{"purpose":"Solo workspace for testing the private-only pattern. Founder operates alone until ready to share.","founder_login":"kody-w"}'
INIT=$(run_agent_direct "$TMPSEED" "agents/workspace_init_agent.py" "WorkspaceInitAgent" "$INIT_KW")
echo "$INIT" | head -8
if echo "$INIT" | grep -q '"status": "ok"' && [ -f "$TMPSEED/state/decisions/0001-why-this-workspace.md" ]; then
  step_pass "workspace_init wrote 0001-why-this-workspace.md"
else
  step_fail "workspace_init did not write 0001"
fi

# 2b. workspace_init is idempotent
INIT2=$(run_agent_direct "$TMPSEED" "agents/workspace_init_agent.py" "WorkspaceInitAgent" "$INIT_KW")
if echo "$INIT2" | grep -q '"status": "noop"'; then
  step_pass "workspace_init idempotent on second run"
else
  step_fail "workspace_init should be noop on second run"
fi

# 3. workspace_decision logs a follow-up
heading "Step 3 — workspace_decision (log a choice)"
DEC_KW='{"title":"Pin the schema set","decided_by":"kody-w","decision":"All workspace artifacts use rapp-* schemas, no ad-hoc shapes.","why":"Schema discipline is what keeps the network composable across decades.","alternatives_rejected":"Ad-hoc per-workspace JSON shapes — too easy to drift."}'
DEC=$(run_agent_direct "$TMPSEED" "agents/workspace_decision_agent.py" "WorkspaceDecisionAgent" "$DEC_KW")
echo "$DEC" | head -8
if echo "$DEC" | grep -q '"number": 2' && [ -f "$TMPSEED/state/decisions/0002-pin-the-schema-set.md" ]; then
  step_pass "workspace_decision wrote 0002 with auto-numbering"
else
  step_fail "workspace_decision did not write 0002"
fi

# 4. workspace_invite composes the gh api command
heading "Step 4 — workspace_invite (gh api command for grant)"
INV_KW='{"github_login":"rappter1","permission":"push","reason":"first external collaborator on the test workspace"}'
INV=$(run_agent_direct "$TMPSEED" "agents/workspace_invite_agent.py" "WorkspaceInviteAgent" "$INV_KW")
echo "$INV" | head -10
if echo "$INV" | grep -q "gh api -X PUT /repos" && echo "$INV" | grep -q "/collaborators/rappter1"; then
  step_pass "workspace_invite composes the gh api command"
else
  step_fail "workspace_invite envelope missing gh command"
fi

# 5. workspace_inbox reads (initially empty)
heading "Step 5 — workspace_inbox (empty)"
mkdir -p "$TMPSEED/state/inbox"
INB=$(run_agent_direct "$TMPSEED" "agents/workspace_inbox_agent.py" "WorkspaceInboxAgent" "{}")
echo "$INB" | head -8
if echo "$INB" | grep -q '"count": 0'; then
  step_pass "workspace_inbox returns count=0 when empty"
else
  step_fail "workspace_inbox should return count=0"
fi

# 5b. Drop a fake inbox item, re-read
cat > "$TMPSEED/state/inbox/2026-05-08T00:00:00Z-rappter1.json" <<'JSON'
{"schema":"rapp-workspace-inbox-item/1.0","from_login":"rappter1","from_rappid":"1ae2561a-1832-45c4-a1b1-984d79b13c1f","kind":"federate-result","summary":"Test async result from rappter1's brainstem.","utc":"2026-05-08T00:00:00Z"}
JSON
INB2=$(run_agent_direct "$TMPSEED" "agents/workspace_inbox_agent.py" "WorkspaceInboxAgent" "{}")
if echo "$INB2" | grep -q '"count": 1' && echo "$INB2" | grep -q '"from_login": "rappter1"'; then
  step_pass "workspace_inbox surfaces a dropped-in item attributed to rappter1"
else
  step_fail "workspace_inbox did not surface the test item"
fi

heading "What to test by hand for the solo-then-shared flow"
cat <<EOF
  1. Plant your private workspace:
       cd $SEED
       git init -b main && git add . && git commit -m "Plant private workspace"
       gh repo create kody-w/<your-workspace-name> --private --source . --push

  2. Use it solo. Run workspace_init / workspace_decision agents from your brainstem
     to bootstrap your decision log. No collaborators yet.

  3. When ready to add the first collaborator (e.g. rappter1):
       Ask workspace_invite to compose the command, then run it:
         gh api -X PUT /repos/kody-w/<workspace>/collaborators/rappter1 -f permission=push

  4. They accept the invite + their brainstem subscribes. Workspace agents auto-mount;
     they show up in your members.json on next reconcile.
EOF

scenario_summary
