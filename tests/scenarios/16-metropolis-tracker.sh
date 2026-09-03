#!/usr/bin/env bash
# Scenario 16 — safely adapted historical Metropolis directory.

source "$(dirname "$0")/_lib.sh"
scenario_parse_args "$@"

heading "Scenario 16 — Historical Metropolis adaptation"
note "Preserves the full directory and collector while defaulting to local evidence"

METRO_DIR="$REPO_ROOT/pages/metropolis"
INDEX="$METRO_DIR/index.json"
SNAPSHOT="$METRO_DIR/activity-snapshot.json"
README="$METRO_DIR/README.md"
HARVESTER="$REPO_ROOT/scripts/harvest-metropolis-activity.py"
WORKFLOW="$REPO_ROOT/.github/workflows/harvest-metropolis-activity.yml"

heading "Step 1 — Directory data is explicitly historical and unaccepted"
python3 - "$INDEX" "$SNAPSHOT" <<'PY' \
  && step_pass "index and activity snapshot refuse current acceptance" \
  || step_fail "Metropolis data is not fail-closed"
import json
import sys

for path in sys.argv[1:]:
    data = json.load(open(path, encoding="utf-8"))
    assert data["status"] == "historical-retired", path
    assert data["accepted"] is False, path
    warning = data["warning"].lower()
    assert "not live" in warning or "not a live" in warning, path

index = json.load(open(sys.argv[1], encoding="utf-8"))
assert index["rapp_protocol_authority"] is False
assert index["protocol"]["status"] == "retired"
assert index["protocol"]["registration"].startswith("Closed.")
PY

heading "Step 2 — Invalid legacy identities remain evidence, not reminted state"
python3 - "$INDEX" <<'PY' \
  && step_pass "legacy identity drift remains visible for migration review" \
  || step_fail "legacy identity evidence was hidden or rewritten"
import json
import re
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
strict = re.compile(r"^rappid:@[a-z0-9](?:[a-z0-9-]{0,38}[a-z0-9])?/[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?:[0-9a-f]{64}$")
legacy = [
    entry["neighborhood_rappid"]
    for entry in data["entries"]
    if entry.get("neighborhood_rappid")
    and not strict.fullmatch(entry["neighborhood_rappid"])
]
assert legacy, "expected preserved non-RAPP/1 identities"
PY

heading "Step 3 — Human documentation is bounded history"
if grep -q "RAPP1-HISTORICAL-SECTION-START" "$README" \
  && grep -q "RAPP1_AUTHORITY.json" "$README" \
  && grep -q "RAPP1_STATUS.md" "$README"; then
  step_pass "README preserves the old protocol inside a current historical boundary"
else
  step_fail "README lacks historical or authority boundaries"
fi

heading "Step 4 — Scheduled publication is gone"
if [ ! -e "$WORKFLOW" ]; then
  step_pass "no scheduled workflow can republish activity"
else
  step_fail "scheduled Metropolis writer still exists"
fi

heading "Step 5 — Harvester defaults to useful local inspection"
set +e
HARVEST_OUTPUT="$(python3 "$HARVESTER" 2>&1)"
HARVEST_RC=$?
PLAN_OUTPUT="$(python3 "$HARVESTER" --plan 2>&1)"
PLAN_RC=$?
BEFORE_HASH="$(python3 - "$SNAPSHOT" <<'PY'
import hashlib
import sys
print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())
PY
)"
ONLINE_OUTPUT="$(python3 "$HARVESTER" --online --write 2>&1)"
ONLINE_RC=$?
AFTER_HASH="$(python3 - "$SNAPSHOT" <<'PY'
import hashlib
import sys
print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())
PY
)"
set -e
if [ "$HARVEST_RC" -eq 0 ] \
  && echo "$HARVEST_OUTPUT" | grep -q "frozen-snapshots-valid" \
  && [ "$PLAN_RC" -eq 0 ] \
  && echo "$PLAN_OUTPUT" | grep -q '"status": "plan-only"' \
  && [ "$ONLINE_RC" -eq 78 ] \
  && echo "$ONLINE_OUTPUT" | grep -q "authenticated-collection-binding-required" \
  && [ "$BEFORE_HASH" = "$AFTER_HASH" ]; then
  step_pass "local check and plan work; online write refuses before mutation"
else
  step_fail "harvester adaptation violated its safe-default contract"
fi

heading "Why this matters"
cat <<'EOF'
  The full directory, collector algorithm, and invalid historical identities
  remain inspectable. Local check/plan modes stay useful while no schedule,
  registration path, live writer, or trust claim can turn the snapshots into
  a current catalog.
EOF

scenario_summary
