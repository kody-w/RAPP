#!/usr/bin/env bash
# tests/features/F10-ecosystem-audit.sh — Bond Pulse drift detector conformance.
#
# Verifies tools/ecosystem_audit.py + tools/ecosystem_contract.py:
#   1. Both modules parse cleanly
#   2. Contract self-check: 9 kinds, no internal issues
#   3. Offline run reports invalid metropolis and fixture rappids
#   4. Synthetic drift detection — fake metropolis index with bare-UUID rappid
#      flagged as rappid_drift
#   5. Fixture/source identity must exactly match metropolis identity
#   6. Schema shape: rapp-ecosystem-audit/1.0 envelope has every required key
#   7. --repo filter narrows scope to one offspring
#   8. --no-write doesn't touch pages/_audit/
#   9. Outputs land at pages/_audit/ when --out-dir is given

source "$(dirname "$0")/../osi/_lib.sh"

osi_layer_intro "F10 — Ecosystem audit (Bond Pulse drift detector)" \
                "tools/ecosystem_audit.py + tools/ecosystem_contract.py"

CONTRACT="$REPO_ROOT/tools/ecosystem_contract.py"
AUDIT="$REPO_ROOT/tools/ecosystem_audit.py"
SANDBOX=$(osi_sandbox "rapp-feature-F10")
trap "osi_cleanup_dir '$SANDBOX'" EXIT

heading "Step 1 — Contract + audit modules present and parse"
if [ -f "$CONTRACT" ] && python3 -c "import ast; ast.parse(open('$CONTRACT').read())" 2>/dev/null \
   && [ -f "$AUDIT" ] && python3 -c "import ast; ast.parse(open('$AUDIT').read())" 2>/dev/null; then
  step_pass "ecosystem_contract.py + ecosystem_audit.py both parse"
else
  step_fail "one of the audit modules missing or has syntax errors"
fi

heading "Step 2 — Contract self-check: ≥7 kinds, no internal issues"
python3 - "$CONTRACT" <<'PY' && step_pass "contract is internally consistent" || step_fail "contract failed self-check"
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location("ecosystem_contract", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
chk = m._self_check()
assert chk["ok"], f"issues: {chk['issues']}"
assert chk["authority_state"] == "product-local-observation"
assert chk["rapp_protocol_authority"] is False
assert chk["kind_count"] >= 7, f"too few kinds: {chk['kind_count']}"
for required in ("neighborhood", "ant-farm", "twin", "workspace", "braintrust", "catalog", "template"):
    assert required in chk["kinds"], f"missing kind: {required}"
print("OK")
PY

heading "Step 3 — Audit emits valid rapp-ecosystem-audit/1.0 envelope"
python3 - "$AUDIT" <<'PY' && step_pass "audit envelope shape matches schema" || step_fail "envelope shape wrong"
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location("ecosystem_audit", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
audit = m.audit_ecosystem(mode="offline", write_outputs=False)
assert audit["schema"] == "rapp-ecosystem-audit/1.0"
assert audit["authority_state"] == "product-local-observation"
assert audit["rapp_protocol_authority"] is False
for key in ("audited_at", "mode", "metropolis_url", "offspring_count", "drift_count",
            "by_kind", "offspring", "summary", "next_actions", "ok"):
    assert key in audit, f"missing key: {key}"
print("OK")
PY

heading "Step 4 — Offline run reports every invalid metropolis/fixture rappid"
python3 - "$AUDIT" <<'PY' && step_pass "invalid metropolis and fixture rappids are drift" || step_fail "invalid identity was hidden or skipped"
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location("ecosystem_audit", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
audit = m.audit_ecosystem(mode="offline", write_outputs=False)
drifted = [o for o in audit["offspring"] if not o.get("skipped") and not o["ok"]]
assert audit["drift_count"] == audit["offspring_count"], drifted
assert all(
    any(d["category"] == "rappid_drift" for d in o["drift"])
    for o in drifted
), drifted
ant_farm = next(o for o in drifted if o["name"] == "ant-farm")
assert any("__MINTED_AT_PLANT__" in d["detail"] for d in ant_farm["drift"])
assert any(
    d["path"] == "pages/metropolis/index.json#neighborhood_rappid"
    for d in ant_farm["drift"]
)
print("OK")
PY

heading "Step 5 — Synthetic drift detection: bare-UUID rappid → rappid_drift"
mkdir -p "$SANDBOX/synthetic-fixtures/test-bad-seed"
cat > "$SANDBOX/synthetic-fixtures/test-bad-seed/rappid.json" <<'JSON'
{"schema": "rapp/1", "rappid": "869ea057-4755-47ec-80df-54551ecf8581", "kind": "neighborhood"}
JSON
cat > "$SANDBOX/synthetic-metropolis.json" <<'JSON'
{
  "schema": "rapp-metropolis-index/1.0",
  "tracker_name": "synthetic-test",
  "tracker_url": "file:///offline/synthetic",
  "synced_at": "2026-05-09T00:00:00Z",
  "entries": [
    {"schema": "rapp-metropolis-entry/1.0", "name": "test-bad",
     "kind": "neighborhood", "neighborhood_rappid": "869ea057-4755-47ec-80df-54551ecf8581",
     "gate_repo": "fake/test-bad", "visibility": "public"}
  ]
}
JSON
python3 - "$AUDIT" "$SANDBOX/synthetic-metropolis.json" "$SANDBOX/synthetic-fixtures" <<'PY' && step_pass "bare-UUID rappid correctly flagged as rappid_drift" || step_fail "synthetic drift not detected"
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location("ecosystem_audit", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
audit = m.audit_ecosystem(
    mode="offline",
    metropolis_index_path=sys.argv[2],
    fixtures_dir=sys.argv[3],
    write_outputs=False,
)
assert audit["drift_count"] >= 1, f"expected drift; got {audit['drift_count']}"
test_bad = next(o for o in audit["offspring"] if o["name"] == "test-bad")
categories = {d["category"] for d in test_bad.get("drift", [])}
assert "rappid_drift" in categories, f"expected rappid_drift in {categories}"
assert any(
    "section 6.1" in d["detail"]
    for d in test_bad["drift"]
    if d["category"] == "rappid_drift"
), test_bad["drift"]
print("OK")
PY

heading "Step 6 — Fixture/source identity must match metropolis identity"
mkdir -p "$SANDBOX/mismatch-fixtures/mismatch-seed"
cat > "$SANDBOX/mismatch-fixtures/mismatch-seed/rappid.json" <<'JSON'
{"schema":"rapp/1","rappid":"rappid:@test/source:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","kind":"neighborhood"}
JSON
cat > "$SANDBOX/mismatch-metropolis.json" <<'JSON'
{
  "schema": "rapp-metropolis-index/1.0",
  "tracker_name": "mismatch-test",
  "tracker_url": "file:///offline/mismatch",
  "entries": [
    {"schema": "rapp-metropolis-entry/1.0", "name": "mismatch",
     "kind": "neighborhood",
     "neighborhood_rappid": "rappid:@test/metropolis:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
     "gate_repo": "test/mismatch", "visibility": "public"}
  ]
}
JSON
python3 - "$AUDIT" "$SANDBOX/mismatch-metropolis.json" "$SANDBOX/mismatch-fixtures" <<'PY' && step_pass "fixture/source mismatch is rappid drift" || step_fail "fixture/source mismatch was hidden"
import importlib.util, sys
spec = importlib.util.spec_from_file_location("ecosystem_audit", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
audit = m.audit_ecosystem(
    mode="offline",
    metropolis_index_path=sys.argv[2],
    fixtures_dir=sys.argv[3],
    write_outputs=False,
)
item = audit["offspring"][0]
assert not item["ok"]
assert any(
    d["category"] == "rappid_drift"
    and "does not exactly match" in d["detail"]
    for d in item["drift"]
), item["drift"]
print("OK")
PY

heading "Step 7 — --repo filter narrows scope to one offspring"
python3 - "$AUDIT" <<'PY' && step_pass "--repo filter narrows to one offspring" || step_fail "filter broken"
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location("ecosystem_audit", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
audit = m.audit_ecosystem(mode="offline", repo_filter="ant-farm", write_outputs=False)
assert audit["offspring_count"] == 1, f"expected 1; got {audit['offspring_count']}"
assert audit["offspring"][0]["name"] == "ant-farm"
print("OK")
PY

heading "Step 8 — write_outputs=True lands files at out_dir"
mkdir -p "$SANDBOX/audit-out"
python3 - "$AUDIT" "$SANDBOX/audit-out" <<'PY' && step_pass "ecosystem-audit.{md,json} written to out_dir" || step_fail "outputs not written"
import importlib.util, json, os, sys
spec = importlib.util.spec_from_file_location("ecosystem_audit", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
m.audit_ecosystem(mode="offline", out_dir=sys.argv[2], write_outputs=True)
assert os.path.exists(os.path.join(sys.argv[2], "ecosystem-audit.json"))
assert os.path.exists(os.path.join(sys.argv[2], "ecosystem-audit.md"))
md = open(os.path.join(sys.argv[2], "ecosystem-audit.md")).read()
assert "Bond Pulse" in md, "markdown report missing Bond Pulse header"
assert "rapp-ecosystem-audit/1.0" in md
print("OK")
PY

heading "Step 9 — CLI: --no-write prints JSON to stdout, doesn't touch pages/_audit/"
OUT=$(python3 "$AUDIT" --offline --no-write 2>/dev/null)
if printf "%s" "$OUT" | python3 -c "import json, sys; d=json.loads(sys.stdin.read()); assert d['schema']=='rapp-ecosystem-audit/1.0'; assert isinstance(d['offspring'], list); print('OK')" 2>/dev/null | grep -q OK; then
  step_pass "--no-write prints valid JSON envelope on stdout"
else
  step_fail "--no-write output invalid"
fi

heading "Step 10 — local-only identity drift is never hidden by fixtures"
python3 - "$AUDIT" <<'PY' && step_pass "local-only mismatch is explicit drift" || step_fail "local-only mismatch was treated as clean"
import importlib.util, sys
spec = importlib.util.spec_from_file_location("ecosystem_audit", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
audit = m.audit_ecosystem(
    mode="offline", repo_filter="local-only-test", write_outputs=False
)
assert audit["offspring_count"] == audit["drift_count"] == 1
item = audit["offspring"][0]
assert not item["ok"] and not item.get("skipped")
assert any(
    d["path"] == "pages/metropolis/index.json#neighborhood_rappid"
    for d in item["drift"]
)
assert any("does not exactly match" in d["detail"] for d in item["drift"])
print("OK")
PY
python3 "$AUDIT" --offline --no-write --repo local-only-test >/dev/null 2>&1
if [ $? -ne 0 ]; then
  step_pass "local-only invalid/mismatched identity exits non-zero"
else
  step_fail "local-only identity drift exited 0"
fi
python3 "$AUDIT" --offline --no-write >/dev/null 2>&1
RC=$?
if [ "$RC" -ne 0 ]; then
  step_pass "known invalid fixture rappid exits non-zero (rc=$RC)"
else
  step_fail "invalid fixture rappid drift but exit was 0"
fi

scenario_summary
