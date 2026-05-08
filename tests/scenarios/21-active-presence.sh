#!/usr/bin/env bash
# Scenario 21 — "Active in last 15 min" presence counter.
#
# Verifies the gate pages + metropolis directory all show a live presence
# counter derived from each repo's GitHub events stream. Anonymous API; no
# central service. Counter graceful-fails when offline / rate-limited
# (banner stays hidden, "—" in metropolis cell).

source "$(dirname "$0")/_lib.sh"
scenario_parse_args "$@"

heading "Scenario 21 — Live active-neighbors counter"
note "Pattern: GitHub events API → unique-actors-in-15m → presence badge"
note "Showcases: presence is observable signal, not assumed"

GATES=(
  "$SEEDS_DIR/microsoft-se-team-neighborhood/index.html"
  "$SEEDS_DIR/public-art-collective/index.html"
)

# 1. Each public gate has the presence banner element + fetch logic
heading "Step 1 — Public gates carry the presence widget"
for gate in "${GATES[@]}"; do
  if grep -q 'id="presence-banner"' "$gate" && grep -q "/events?per_page" "$gate"; then
    step_pass "$(basename $(dirname $gate)) gate has presence banner + events fetch"
  else
    step_fail "$(basename $(dirname $gate)) gate is missing presence widget"
  fi
done

# 2. Both gates use 15-min cutoff
heading "Step 2 — 15-min activity window"
for gate in "${GATES[@]}"; do
  if grep -qE "15 \* 60 \* 1000" "$gate"; then
    step_pass "$(basename $(dirname $gate)): 15-min cutoff present"
  else
    step_fail "$(basename $(dirname $gate)): 15-min cutoff missing"
  fi
done

# 3. Metropolis directory has Active 15m column + probeActiveCounts function
heading "Step 3 — Metropolis directory shows Active column"
METRO="$REPO_ROOT/pages/metropolis/index.html"
if grep -q "Active 15m" "$METRO" && grep -q "probeActiveCounts" "$METRO"; then
  step_pass "metropolis directory: Active 15m column + probe function wired"
else
  step_fail "metropolis directory missing presence wiring"
fi

# 4. Metropolis colspan stays consistent (7, after adding the column)
heading "Step 4 — Table layout coherent"
SPANS=$(grep -oE 'colspan="[0-9]+"' "$METRO" | sort -u)
if [ "$SPANS" = 'colspan="7"' ]; then
  step_pass "all colspan values are 7 (matches column count)"
else
  step_fail "colspan inconsistency: $SPANS"
fi

# 5. Private repos don't trigger an unauth'd events fetch (no rate-burn on private)
heading "Step 5 — Private entries skip the events fetch"
if grep -q '(e.visibility || "").startsWith("private")' "$METRO"; then
  step_pass "private entries early-return without API call"
else
  step_fail "private entries would still hit the API (rate-burn)"
fi

# 6. Anonymous events API works for the planted public repos (smoke test)
heading "Step 6 — Anonymous events API reachable for public neighborhoods"
if [ "$DRY_RUN" -eq 1 ]; then
  step_skip "live API check (--dry-run)"
else
  for slug in kody-w/microsoft-se-team-neighborhood kody-w/public-art-collective; do
    CODE=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 5 "https://api.github.com/repos/$slug/events?per_page=1" 2>/dev/null || echo "000")
    if [ "$CODE" = "200" ]; then
      step_pass "https://api.github.com/repos/$slug/events → 200 (public, anonymous)"
    elif [ "$CODE" = "403" ]; then
      step_skip "rate-limited (403); presence widget would degrade gracefully on the page"
    else
      step_fail "unexpected status $CODE"
    fi
  done
fi

heading "Why this matters"
cat <<'EOF'
  Presence is a real, observable signal — derived from GitHub's public
  events stream by counting unique actors active in the last 15 minutes.
  No central service. No new infra. Each gate page makes one anonymous
  API call on load; the metropolis makes N (one per public entry).
  Rate-limit / offline = banner hidden / cell shows "—". Master plan
  honored: graceful degradation, no single-point-of-failure beyond
  GitHub itself (which is the platform's chosen substrate anyway).
EOF

scenario_summary
