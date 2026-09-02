#!/usr/bin/env bash
# Scenario 20 — retired cross-tracker federation containment.

source "$(dirname "$0")/_lib.sh"
scenario_parse_args "$@"

heading "Scenario 20 — Historical federation containment"
note "Retains the old merge fixture without authorizing network federation"

CANONICAL="$REPO_ROOT/pages/metropolis/index.json"
PEER="$REPO_ROOT/pages/metropolis/federated-demo.json"

heading "Step 1 — Both tracker records are historical refusals"
python3 - "$CANONICAL" "$PEER" <<'PY' \
  && step_pass "both records reject current protocol acceptance" \
  || step_fail "tracker records are not retired consistently"
import json
import sys

for path in sys.argv[1:]:
    data = json.load(open(path, encoding="utf-8"))
    assert data["status"] == "historical-retired", path
    assert data["accepted"] is False, path
    assert data["rapp_protocol_authority"] is False, path
    assert data["protocol"]["status"] == "retired", path
PY

heading "Step 2 — Cross-reference remains only as historical evidence"
python3 - "$CANONICAL" "$PEER" <<'PY' \
  && step_pass "the dated relationship is preserved without live merge authority" \
  || step_fail "historical federation evidence is malformed"
import json
import sys

canonical = json.load(open(sys.argv[1], encoding="utf-8"))
peer = json.load(open(sys.argv[2], encoding="utf-8"))
assert any("federated-demo.json" in value for value in canonical["federated_trackers"])
assert any("index.json" in value for value in peer["federated_trackers"])
assert "must not merge" in peer["protocol"]["merge_rule"].lower()
assert "historical" in canonical["protocol"]["federation"].lower()
PY

heading "Step 3 — No data record claims canonical tracker authority"
python3 - "$CANONICAL" "$PEER" <<'PY' \
  && step_pass "tracker metadata is non-authoritative" \
  || step_fail "a tracker still claims current authority"
import json
import sys

for path in sys.argv[1:]:
    data = json.load(open(path, encoding="utf-8"))
    active = " ".join(
        str(data.get(key, ""))
        for key in ("tracker_name", "purpose", "warning")
    ).lower()
    assert "canonical)" not in active
    assert "active rapp neighborhoods" not in active
    assert "protocol is the network" not in active
PY

heading "Why this matters"
cat <<'EOF'
  Audit and migration tools can still reproduce the legacy federation shape,
  while current clients receive an explicit refusal instead of a discoverable
  or mergeable network.
EOF

scenario_summary
