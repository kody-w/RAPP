#!/usr/bin/env bash
# Scenario 2 — Cross-device neighborhood (same operator, multiple machines).
#
# Verifies the membership organ's GitHub-mode flow against the
# microsoft-se-team-neighborhood seed. Solo-operator case: kody-w on
# machine A and kody-w on machine B both subscribe and see the same
# state. No third party in the loop.
#
# Run:
#     bash tests/scenarios/02-cross-device.sh
#     bash tests/scenarios/02-cross-device.sh --dry-run
#
# Prerequisites for live mode:
#   - The two seeds have been pushed to kody-w/microsoft-se-team-neighborhood
#     and kody-w/microsoft-se-team-neighborhood-private (see seeds README)
#   - `gh auth status` shows you logged in as kody-w
#   - Brainstem is running at ${BRAINSTEM_URL:-http://localhost:7071}

source "$(dirname "$0")/_lib.sh"
scenario_parse_args "$@"

heading "Scenario 2 — Cross-device, solo-operator"
note "Seed pair:  microsoft-se-team-neighborhood (gate) + -private (companion)"
note "Mode:       https:// (GitHub auth required for live)"

PUB_SEED="$SEEDS_DIR/microsoft-se-team-neighborhood"
PRV_SEED="$SEEDS_DIR/microsoft-se-team-neighborhood-private"

# 1. Both seeds present + coherent
if [ ! -f "$PUB_SEED/neighborhood.json" ] || [ ! -f "$PRV_SEED/neighborhood.json" ]; then
  step_fail "seed pair missing at $SEEDS_DIR/microsoft-se-team-neighborhood{,-private}"
  scenario_summary
fi
step_pass "seed pair present"

# 2. Cross-references match
PUB_RAPPID=$(python3 -c "import json; print(json.load(open('$PUB_SEED/neighborhood.json'))['neighborhood_rappid'])")
PRV_RAPPID=$(python3 -c "import json; print(json.load(open('$PRV_SEED/neighborhood.json'))['neighborhood_rappid'])")
if [ "$PUB_RAPPID" = "$PRV_RAPPID" ]; then
  step_pass "shared neighborhood_rappid: $PUB_RAPPID"
else
  step_fail "neighborhood_rappid mismatch (public=$PUB_RAPPID, private=$PRV_RAPPID)"
fi

# 3. Live subscription path
heading "Step 3 — Live subscription via GitHub mode"
GATE_URL="https://github.com/kody-w/microsoft-se-team-neighborhood"
if [ "$DRY_RUN" -eq 1 ]; then
  step_skip "skipping live GitHub subscription (--dry-run)"
elif ! brainstem_alive; then
  muted "no brainstem at ${BRAINSTEM_URL}"
  step_skip "live GitHub subscription (start brainstem first)"
elif ! command -v gh >/dev/null 2>&1; then
  muted "gh CLI not installed"
  step_skip "live GitHub subscription"
else
  ME=$(gh api user --jq .login 2>/dev/null || echo "")
  if [ -z "$ME" ]; then
    muted "gh auth not configured"
    step_skip "live GitHub subscription"
  else
    note "authed as @$ME"
    LIVE=$(curl -fsS -X POST "${BRAINSTEM_URL}/api/neighborhoods/join" \
      -H 'content-type: application/json' \
      -d "{\"gate_url\": \"$GATE_URL\"}" 2>/dev/null || true)
    echo "$LIVE" | head -20
    if echo "$LIVE" | grep -q '"joined": true'; then
      step_pass "subscribed live as @$ME"
    elif echo "$LIVE" | grep -q '"could not read neighborhood.json"'; then
      muted "neighborhood not yet pushed to GitHub (do: cd $PUB_SEED && git init && gh repo create ...)"
      step_skip "live GitHub subscription (seeds not pushed yet)"
    else
      step_fail "live subscription returned unexpected response"
    fi
  fi
fi

heading "What to test by hand for cross-device"
cat <<'EOF'
  Machine A (laptop):
    1. Pull the latest RAPP main: cd ~/RAPP && git pull origin main
    2. Push the seed pair (one-time, see installer/neighborhood-seeds/README.md)
    3. Start brainstem; subscribe:
         brainstem join https://github.com/kody-w/microsoft-se-team-neighborhood
    4. Verify roster:
         curl http://localhost:7071/api/neighborhoods/kody-w/microsoft-se-team-neighborhood-private/members

  Machine B (phone or other laptop):
    1. Install brainstem (one-liner)
    2. Same `gh auth login` as kody-w
    3. Same `brainstem join ...`
    4. Verify the same roster + the same neighborhood_rappid

  Both machines now hold the same subscription. Operator identity is the spine.
EOF

scenario_summary
