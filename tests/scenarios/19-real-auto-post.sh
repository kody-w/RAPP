#!/usr/bin/env bash
# Scenario 19 — Real Issue/comment posting via auto_post.
#
# Verifies the braintrust agents actually POST via the GitHub API when
# auto_post=true + GITHUB_TOKEN. Three paths:
#   1. auto_post=False (default) → returns URL, no API call attempted
#   2. auto_post=True without token → graceful fail (no crash, clear reason)
#   3. auto_post=True WITH token (live, --live flag only) → real Issue created + closed
#
# The default invocation runs 1+2 only. Pass --live to also run the real
# post-and-close round-trip against kody-w/braintrust-template.

source "$(dirname "$0")/_lib.sh"
LIVE=0
for arg in "$@"; do
  case "$arg" in
    --live) LIVE=1 ;;
  esac
done
scenario_parse_args "$@"

heading "Scenario 19 — Real auto_post (request + contribute)"
note "Pattern: agents call the GitHub API directly when auto_post=true + token"
note "Showcases: not stubbed; live posting works end-to-end"

SEED="$SEEDS_DIR/braintrust-template"

# 1. auto_post=False is the default — no API call attempted
heading "Step 1 — auto_post=False (default) returns URL only"
RESP=$(NEIGHBORHOOD_SEED_DIR="$SEED" python3 - <<'PY'
import importlib.util, json, os, sys
sys.path.insert(0, os.environ["NEIGHBORHOOD_SEED_DIR"])
spec = importlib.util.spec_from_file_location("a", os.path.join(os.environ["NEIGHBORHOOD_SEED_DIR"], "agents/braintrust_request_agent.py"))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print(m.BraintrustRequestAgent().perform(topic="x", requester_login="kody-w"))
PY
)
ATTEMPTED=$(echo "$RESP" | python3 -c "import json,sys; print(json.load(sys.stdin)['auto_post_attempted'])")
ACTION=$(echo "$RESP" | python3 -c "import json,sys; print(json.load(sys.stdin)['next_step']['action'])")
if [ "$ATTEMPTED" = "False" ] && [ "$ACTION" = "open_request_issue" ]; then
  step_pass "request_agent default: auto_post not attempted; URL returned"
else
  step_fail "default path broken (attempted=$ATTEMPTED action=$ACTION)"
fi

# 2. auto_post=True without token → graceful fail
heading "Step 2 — auto_post=True without token fails gracefully"
RESP2=$(unset GITHUB_TOKEN GH_TOKEN; NEIGHBORHOOD_SEED_DIR="$SEED" python3 - <<'PY'
import importlib.util, json, os, sys
os.environ.pop("GITHUB_TOKEN", None); os.environ.pop("GH_TOKEN", None)
sys.path.insert(0, os.environ["NEIGHBORHOOD_SEED_DIR"])
spec = importlib.util.spec_from_file_location("a", os.path.join(os.environ["NEIGHBORHOOD_SEED_DIR"], "agents/braintrust_request_agent.py"))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print(m.BraintrustRequestAgent().perform(topic="x", requester_login="kody-w", auto_post=True))
PY
)
OK=$(echo "$RESP2" | python3 -c "import json,sys; print(json.load(sys.stdin)['auto_post_result']['ok'])")
REASON=$(echo "$RESP2" | python3 -c "import json,sys; print(json.load(sys.stdin)['auto_post_result']['reason'])")
if [ "$OK" = "False" ] && echo "$REASON" | grep -q "GITHUB_TOKEN"; then
  step_pass "no-token path returns ok=False with clear reason ($REASON)"
else
  step_fail "no-token path unexpected: ok=$OK reason=$REASON"
fi

# 3. contribute_agent — same two paths
heading "Step 3 — contribute_agent: default + no-token paths"
RESP3=$(NEIGHBORHOOD_SEED_DIR="$SEED" python3 - <<'PY'
import importlib.util, json, os, sys
sys.path.insert(0, os.environ["NEIGHBORHOOD_SEED_DIR"])
spec = importlib.util.spec_from_file_location("a", os.path.join(os.environ["NEIGHBORHOOD_SEED_DIR"], "agents/braintrust_contribute_agent.py"))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print(m.BraintrustContributeAgent().perform(request_id="x", topic="x", contributor_login="kody-w"))
PY
)
A3=$(echo "$RESP3" | python3 -c "import json,sys; print(json.load(sys.stdin)['auto_post_attempted'])")
[ "$A3" = "False" ] && step_pass "contribute_agent default: auto_post=False" || step_fail "contribute default broken"

RESP4=$(unset GITHUB_TOKEN GH_TOKEN; NEIGHBORHOOD_SEED_DIR="$SEED" python3 - <<'PY'
import importlib.util, json, os, sys
os.environ.pop("GITHUB_TOKEN", None); os.environ.pop("GH_TOKEN", None)
sys.path.insert(0, os.environ["NEIGHBORHOOD_SEED_DIR"])
spec = importlib.util.spec_from_file_location("a", os.path.join(os.environ["NEIGHBORHOOD_SEED_DIR"], "agents/braintrust_contribute_agent.py"))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print(m.BraintrustContributeAgent().perform(request_id="x", topic="x", contributor_login="kody-w", issue_number=1, auto_post=True))
PY
)
OK4=$(echo "$RESP4" | python3 -c "import json,sys; print(json.load(sys.stdin)['auto_post_result']['ok'])")
[ "$OK4" = "False" ] && step_pass "contribute_agent no-token: graceful fail" || step_fail "contribute no-token broken"

# 4. auto_post=True with issue_number missing → graceful fail (different reason)
heading "Step 4 — contribute_agent rejects missing issue_number"
RESP5=$(GITHUB_TOKEN=fake NEIGHBORHOOD_SEED_DIR="$SEED" python3 - <<'PY'
import importlib.util, json, os, sys
sys.path.insert(0, os.environ["NEIGHBORHOOD_SEED_DIR"])
spec = importlib.util.spec_from_file_location("a", os.path.join(os.environ["NEIGHBORHOOD_SEED_DIR"], "agents/braintrust_contribute_agent.py"))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print(m.BraintrustContributeAgent().perform(request_id="x", topic="x", contributor_login="kody-w", auto_post=True))
PY
)
REASON5=$(echo "$RESP5" | python3 -c "import json,sys; print(json.load(sys.stdin)['auto_post_result']['reason'])")
if echo "$REASON5" | grep -q "issue_number"; then
  step_pass "contribute auto_post without issue_number: clear reason"
else
  step_fail "expected issue_number reason, got: $REASON5"
fi

# 5. Live test (only with --live flag, so default runs are non-destructive)
heading "Step 5 — Live round-trip (--live only)"
if [ "$LIVE" -eq 1 ]; then
  if ! command -v gh >/dev/null 2>&1; then
    step_skip "gh CLI unavailable"
  else
    TOKEN=$(gh auth token 2>/dev/null)
    if [ -z "$TOKEN" ]; then
      step_skip "no gh auth token"
    else
      LIVE_RESP=$(GITHUB_TOKEN="$TOKEN" NEIGHBORHOOD_SEED_DIR="$SEED" python3 - <<'PY'
import importlib.util, json, os, sys
sys.path.insert(0, os.environ["NEIGHBORHOOD_SEED_DIR"])
spec = importlib.util.spec_from_file_location("a", os.path.join(os.environ["NEIGHBORHOOD_SEED_DIR"], "agents/braintrust_request_agent.py"))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print(m.BraintrustRequestAgent().perform(
    topic="[E2E TEST scenario 19] auto_post live verification — please close",
    requester_login="kody-w",
    auto_post=True,
))
PY
)
      LIVE_OK=$(echo "$LIVE_RESP" | python3 -c "import json,sys; print(json.load(sys.stdin)['auto_post_result']['ok'])")
      LIVE_NUM=$(echo "$LIVE_RESP" | python3 -c "import json,sys; print(json.load(sys.stdin)['auto_post_result'].get('issue_number',''))")
      if [ "$LIVE_OK" = "True" ] && [ -n "$LIVE_NUM" ]; then
        step_pass "live: posted real issue #$LIVE_NUM to kody-w/braintrust-template"
        gh api -X PATCH "/repos/kody-w/braintrust-template/issues/$LIVE_NUM" -f state=closed >/dev/null 2>&1 && \
          step_pass "live: closed issue #$LIVE_NUM" || step_fail "live: could not close"
      else
        step_fail "live post failed: $LIVE_RESP"
      fi
    fi
  fi
else
  step_skip "live round-trip (run with --live to enable)"
fi

heading "Why this matters"
cat <<'EOF'
  Two real GitHub API integrations in the braintrust agents:
  request_agent → POST /repos/<o>/<r>/issues, contribute_agent → POST
  /repos/<o>/<r>/issues/<n>/comments. Both gated on auto_post=true +
  GITHUB_TOKEN; both fall through gracefully when either is missing.
  No silent crashes, no half-stubs — the API path is real.
EOF

scenario_summary
