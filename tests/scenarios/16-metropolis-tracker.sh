#!/usr/bin/env bash
# Scenario 16 — retired Metropolis directory containment.

source "$(dirname "$0")/_lib.sh"
scenario_parse_args "$@"

heading "Scenario 16 — Historical Metropolis containment"
note "Preserves legacy directory evidence without publishing a live catalog"

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
  step_pass "README preserves the old protocol inside a current retirement boundary"
else
  step_fail "README lacks historical or authority boundaries"
fi

heading "Step 4 — Scheduled publication is gone"
if [ ! -e "$WORKFLOW" ]; then
  step_pass "no scheduled workflow can republish activity"
else
  step_fail "scheduled Metropolis writer still exists"
fi

heading "Step 5 — Known harvester path is an inert tombstone"
set +e
HARVEST_OUTPUT="$(python3 "$HARVESTER" 2>&1)"
HARVEST_RC=$?
set -e
if [ "$HARVEST_RC" -eq 78 ] \
  && echo "$HARVEST_OUTPUT" | grep -q "metropolis-activity-harvester-retired"; then
  step_pass "harvester refuses with exit 78 and a machine-readable reason"
else
  step_fail "harvester did not refuse safely (rc=$HARVEST_RC)"
fi

heading "Why this matters"
cat <<'EOF'
  The legacy directory and its invalid identities remain inspectable, but no
  schedule, registration path, live-presence writer, or trust claim can turn
  the snapshot back into a current catalog.
EOF

scenario_summary
