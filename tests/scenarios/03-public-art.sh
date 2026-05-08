#!/usr/bin/env bash
# Scenario 3 — Public art collective neighborhood.
#
# Verifies the public-only visibility pattern: anyone reads, granted
# neighbors contribute. Exercises the four collective agents (submit,
# curate, vote, remix) directly to confirm they return well-formed
# envelopes with the right next-step URLs.
#
# Run:
#     bash tests/scenarios/03-public-art.sh
#     bash tests/scenarios/03-public-art.sh --dry-run

source "$(dirname "$0")/_lib.sh"
scenario_parse_args "$@"

heading "Scenario 3 — Public art collective"
note "Seed: $SEEDS_DIR/public-art-collective"
note "Mode: public visibility (no private companion)"

SEED="$SEEDS_DIR/public-art-collective"

# 1. Seed exists
if [ ! -f "$SEED/neighborhood.json" ]; then
  step_fail "seed missing"; scenario_summary
fi
step_pass "seed present"

# 2. Visibility is "public" (standalone)
VIS=$(python3 -c "import json; print(json.load(open('$SEED/neighborhood.json'))['visibility'])")
if [ "$VIS" = "public" ]; then
  step_pass "visibility = public (standalone, no companion)"
else
  step_fail "expected visibility=public, got $VIS"
fi

# 3. No private companion declared
PC=$(python3 -c "import json; print(json.load(open('$SEED/neighborhood.json')).get('private_companion'))")
if [ "$PC" = "None" ] || [ -z "$PC" ]; then
  step_pass "private_companion is null (public-only)"
else
  step_fail "private_companion should be null but was: $PC"
fi

# 4. art_curate_agent on empty seed returns count=0
heading "Step 4 — art_curate (empty submissions)"
CURATE=$(run_agent_direct "$SEED" "agents/art_curate_agent.py" "ArtCurateAgent" "{}")
echo "$CURATE" | head -10
if echo "$CURATE" | grep -q '"count": 0'; then
  step_pass "art_curate returns count=0 on fresh seed"
else
  step_fail "art_curate did not return count=0"
fi

# 5. art_submit_agent drafts a submission
heading "Step 5 — art_submit (draft new piece)"
SUBMIT_KW='{"title":"Pixel Sunrise","contributor_login":"rappter1","kind":"ascii","content":":-)\\n>>=>>"}'
SUBMIT=$(run_agent_direct "$SEED" "agents/art_submit_agent.py" "ArtSubmitAgent" "$SUBMIT_KW")
echo "$SUBMIT" | head -15
if echo "$SUBMIT" | grep -q '"step_1_url"' && echo "$SUBMIT" | grep -q '"step_2_url"'; then
  step_pass "art_submit returns two-file PR draft URLs"
else
  step_fail "art_submit envelope missing step URLs"
fi

# 6. art_vote_agent generates a vote envelope
heading "Step 6 — art_vote (cast a vote)"
VOTE_KW='{"submission_slug":"pixel-sunrise","voter_login":"kody-w","reaction":"heart","comment":"clean composition"}'
VOTE=$(run_agent_direct "$SEED" "agents/art_vote_agent.py" "ArtVoteAgent" "$VOTE_KW")
echo "$VOTE" | head -15
if echo "$VOTE" | grep -q '"open_vote_issue"'; then
  step_pass "art_vote returns vote-issue envelope"
else
  step_fail "art_vote envelope unexpected"
fi

# 7. art_remix_agent forks an existing slug
heading "Step 7 — art_remix (fork a piece)"
REMIX_KW='{"original_slug":"pixel-sunrise","remixer_login":"alex","new_title":"Pixel Sunset","new_content":":-(\\n<<=<<"}'
REMIX=$(run_agent_direct "$SEED" "agents/art_remix_agent.py" "ArtRemixAgent" "$REMIX_KW")
echo "$REMIX" | head -15
if echo "$REMIX" | grep -q '"remix_of": "pixel-sunrise"'; then
  step_pass "art_remix preserves remix_of lineage"
else
  step_fail "art_remix did not record remix_of"
fi

heading "What to test by hand for autonomous collab"
cat <<EOF
  1. Push the seed:
       cd $SEED
       git init -b main && git add . && git commit -m "Plant Public Art Collective"
       gh repo create kody-w/public-art-collective --public --source . --push
       gh api -X POST /repos/kody-w/public-art-collective/pages -f source.branch=main -f source.path=/

  2. Add a co-contributor (rappter1):
       gh api -X PUT /repos/kody-w/public-art-collective/collaborators/rappter1 -f permission=push

  3. From each operator's brainstem, subscribe + run agents autonomously to:
       - submit a piece (PR opens; self-merge or wait for review)
       - vote on others' pieces
       - remix a piece

  The collective grows without coordination — exactly the autonomous-collab pattern.
EOF

scenario_summary
