#!/bin/bash
# tests/test-t2t.sh — end-to-end test of the T2T (twin-to-twin) protocol
# between two sovereign swarm clouds. Spins up TWO swarm-server instances
# (one for Kody's twin, one for Molly's), then exercises:
#
#   1. each cloud's identity endpoint (cloud_id + handle + capabilities)
#   2. mutual peer-add with shared secrets (out-of-band exchange simulated)
#   3. signed handshake (HMAC-SHA256, both directions)
#   4. signed message exchange
#   5. cross-cloud capability invocation (Kody's twin invokes Molly's swarm)
#   6. forgery rejection (bad signature, unauthorized peer, blocked capability)
#
# T2T is the user-facing protocol name; D2D (daemon-to-daemon) is the
# implementation underlayer carrying it. Both surface on the same wire.
#
#     bash tests/test-t2t.sh
#
# Exits 0 on success, non-zero with diagnostics on failure.

set -e
set -o pipefail

KODY_PORT=7182
MOLLY_PORT=7183
KODY_ROOT=/tmp/rapp-swarm-test-t2t-kody
MOLLY_ROOT=/tmp/rapp-swarm-test-t2t-molly
KODY_PID=""
MOLLY_PID=""
PASS=0
FAIL=0
FAIL_NAMES=()

cleanup() {
    [ -n "$KODY_PID" ]  && { kill $KODY_PID  2>/dev/null || true; wait $KODY_PID  2>/dev/null || true; }
    [ -n "$MOLLY_PID" ] && { kill $MOLLY_PID 2>/dev/null || true; wait $MOLLY_PID 2>/dev/null || true; }
}
trap cleanup EXIT

assert_eq() {
    local name="$1" expected="$2" actual="$3"
    if [ "$expected" = "$actual" ]; then
        echo "  ✓ $name"
        PASS=$((PASS + 1))
    else
        echo "  ✗ $name"
        echo "      expected: $expected"
        echo "      actual:   $actual"
        FAIL=$((FAIL + 1))
        FAIL_NAMES+=("$name")
    fi
}

assert_contains() {
    local name="$1" needle="$2" haystack="$3"
    if echo "$haystack" | grep -qF "$needle"; then
        echo "  ✓ $name"
        PASS=$((PASS + 1))
    else
        echo "  ✗ $name"
        echo "      needle:    $needle"
        echo "      haystack:  $(echo "$haystack" | head -c 240)"
        FAIL=$((FAIL + 1))
        FAIL_NAMES+=("$name")
    fi
}

assert_not_contains() {
    local name="$1" needle="$2" haystack="$3"
    if echo "$haystack" | grep -qF "$needle"; then
        echo "  ✗ $name (found '$needle')"
        echo "      haystack:  $(echo "$haystack" | head -c 240)"
        FAIL=$((FAIL + 1))
        FAIL_NAMES+=("$name")
    else
        echo "  ✓ $name"
        PASS=$((PASS + 1))
    fi
}

# Sign a payload with a secret using the same canonical envelope
# (sort_keys=true, separators=(',',':')) the swarm/t2t.py module uses.
sign_envelope() {
    local conv_id="$1" seq="$2" body_json="$3" secret="$4"
    python3 - "$conv_id" "$seq" "$body_json" "$secret" <<'PY'
import sys, json, hmac, hashlib
conv_id, seq, body_json, secret = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
body = json.loads(body_json)
payload = json.dumps({"conv_id": conv_id, "seq": seq, "body": body},
                     sort_keys=True, separators=(",", ":"))
print(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest())
PY
}

sign_invoke() {
    local from_cloud_id="$1" invocation_json="$2" secret="$3"
    python3 - "$from_cloud_id" "$invocation_json" "$secret" <<'PY'
import sys, json, hmac, hashlib
from_cloud_id, invocation_json, secret = sys.argv[1], sys.argv[2], sys.argv[3]
inv = json.loads(invocation_json)
payload = json.dumps({"from": from_cloud_id, "invocation": inv},
                     sort_keys=True, separators=(",", ":"))
print(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest())
PY
}

# ── Setup ──────────────────────────────────────────────────────────────

echo "Setup: clean state"
rm -rf "$KODY_ROOT" "$MOLLY_ROOT"

echo "Setup: starting Kody's swarm cloud on :$KODY_PORT (root: $KODY_ROOT)"
python3 rapp_brainstem/brainstem.py --port $KODY_PORT --root "$KODY_ROOT" >/dev/null 2>&1 &
KODY_PID=$!

echo "Setup: starting Molly's swarm cloud on :$MOLLY_PORT (root: $MOLLY_ROOT)"
python3 rapp_brainstem/brainstem.py --port $MOLLY_PORT --root "$MOLLY_ROOT" >/dev/null 2>&1 &
MOLLY_PID=$!

sleep 1.8

# ── Section 1: Identity exchange ──────────────────────────────────────

echo ""
echo "--- Section 1: identity ---"

# Each cloud's identity is auto-minted on first /api/t2t/identity GET
KODY_IDENT=$(curl -s http://127.0.0.1:$KODY_PORT/api/t2t/identity)
KODY_CLOUD_ID=$(echo "$KODY_IDENT" | python3 -c 'import json,sys; print(json.load(sys.stdin)["cloud_id"])')
assert_contains "Kody identity has cloud_id"  "$KODY_CLOUD_ID"  "$KODY_IDENT"
assert_eq "Kody identity hex length = 32"  "32"  "${#KODY_CLOUD_ID}"

# Identity public response must NOT leak the secret
assert_not_contains "Kody identity response does NOT leak secret field"  '"secret"'  "$KODY_IDENT"

MOLLY_IDENT=$(curl -s http://127.0.0.1:$MOLLY_PORT/api/t2t/identity)
MOLLY_CLOUD_ID=$(echo "$MOLLY_IDENT" | python3 -c 'import json,sys; print(json.load(sys.stdin)["cloud_id"])')
assert_contains "Molly identity has cloud_id"  "$MOLLY_CLOUD_ID"  "$MOLLY_IDENT"
[ "$KODY_CLOUD_ID" != "$MOLLY_CLOUD_ID" ]
assert_eq "Kody and Molly cloud_ids differ"  "ok"  "ok"

# Read each cloud's secret directly from disk (simulating out-of-band
# exchange — in production the user pastes this between devices).
KODY_SECRET=$(python3 -c "import json; print(json.load(open('$KODY_ROOT/t2t/identity.json'))['secret'])")
MOLLY_SECRET=$(python3 -c "import json; print(json.load(open('$MOLLY_ROOT/t2t/identity.json'))['secret'])")
[ -n "$KODY_SECRET" ] && [ -n "$MOLLY_SECRET" ]
assert_eq "both clouds have non-empty secrets on disk"  "ok"  "ok"

# ── Section 2: Mutual peer-add ────────────────────────────────────────

echo ""
echo "--- Section 2: mutual peer-add ---"

# Kody whitelists Molly. Note that for cross-cloud signature verification,
# Kody needs MOLLY's secret (so Kody can verify messages signed by Molly).
RESP=$(curl -s -X POST http://127.0.0.1:$KODY_PORT/api/t2t/peers \
    -H 'Content-Type: application/json' \
    -d "{\"cloud_id\":\"$MOLLY_CLOUD_ID\",\"secret\":\"$MOLLY_SECRET\",\"handle\":\"@molly.cloud\",\"url\":\"http://127.0.0.1:$MOLLY_PORT\",\"allowed_caps\":[\"PartnerOutreach\",\"CEODecisions\",\"PatentTracker\"]}")
STATUS=$(echo "$RESP" | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])')
assert_eq "Kody adds Molly as peer (status=ok)"  "ok"  "$STATUS"

# Molly whitelists Kody. Allow-list explicitly names PartnerOutreach so we
# can also exercise the capability gate (anything else MUST be rejected).
RESP=$(curl -s -X POST http://127.0.0.1:$MOLLY_PORT/api/t2t/peers \
    -H 'Content-Type: application/json' \
    -d "{\"cloud_id\":\"$KODY_CLOUD_ID\",\"secret\":\"$KODY_SECRET\",\"handle\":\"@kody.cloud\",\"url\":\"http://127.0.0.1:$KODY_PORT\",\"allowed_caps\":[\"PartnerOutreach\",\"PressRelations\"]}")
STATUS=$(echo "$RESP" | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])')
assert_eq "Molly adds Kody as peer (status=ok)"  "ok"  "$STATUS"

# Listing peers must NOT leak secrets
RESP=$(curl -s http://127.0.0.1:$KODY_PORT/api/t2t/peers)
assert_contains "Kody's peer list shows Molly's cloud_id"  "$MOLLY_CLOUD_ID"  "$RESP"
assert_not_contains "peer list does NOT leak any secret"  "$MOLLY_SECRET"  "$RESP"

# ── Section 3: Signed handshake (Kody → Molly) ────────────────────────

echo ""
echo "--- Section 3: signed handshake (Kody initiates) ---"

CONV_ID="conv-kody-to-molly-$(date +%s)"
INTRO_BODY='{"intent":"meeting-prep","topic":"estate-attorney 3pm tomorrow"}'
SIG=$(sign_envelope "$CONV_ID" 0 "$INTRO_BODY" "$KODY_SECRET")
[ -n "$SIG" ] && [ ${#SIG} -eq 64 ]
assert_eq "HMAC-SHA256 sig is 64 hex chars"  "64"  "${#SIG}"

# Molly receives the handshake — signed with Kody's secret, verified
# against the secret she stored for Kody (which IS Kody's).
RESP=$(curl -s -X POST http://127.0.0.1:$MOLLY_PORT/api/t2t/handshake \
    -H 'Content-Type: application/json' \
    -d "{\"from\":\"$KODY_CLOUD_ID\",\"conv_id\":\"$CONV_ID\",\"intro\":$INTRO_BODY,\"sig\":\"$SIG\"}")
ACCEPTED=$(echo "$RESP" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("accepted"))')
assert_eq "Molly accepts Kody's signed handshake (accepted=true)"  "True"  "$ACCEPTED"

# Bad signature is rejected
BAD_RESP=$(curl -s -X POST http://127.0.0.1:$MOLLY_PORT/api/t2t/handshake \
    -H 'Content-Type: application/json' \
    -d "{\"from\":\"$KODY_CLOUD_ID\",\"conv_id\":\"$CONV_ID-evil\",\"intro\":$INTRO_BODY,\"sig\":\"deadbeef$(printf '%056d' 0)\"}")
ACCEPTED=$(echo "$BAD_RESP" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("accepted"))')
assert_eq "bad-sig handshake REJECTED (accepted=false)"  "False"  "$ACCEPTED"
assert_contains "rejection mentions signature"  "signature"  "$BAD_RESP"

# Unknown peer is rejected
UNKNOWN_RESP=$(curl -s -X POST http://127.0.0.1:$MOLLY_PORT/api/t2t/handshake \
    -H 'Content-Type: application/json' \
    -d "{\"from\":\"deadbeefdeadbeefdeadbeefdeadbeef\",\"conv_id\":\"$CONV_ID-stranger\",\"intro\":$INTRO_BODY,\"sig\":\"$SIG\"}")
ACCEPTED=$(echo "$UNKNOWN_RESP" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("accepted"))')
assert_eq "unknown-peer handshake REJECTED (not whitelisted)"  "False"  "$ACCEPTED"
assert_contains "rejection mentions whitelist"  "whitelisted"  "$UNKNOWN_RESP"

# ── Section 4: Signed message exchange ────────────────────────────────

echo ""
echo "--- Section 4: signed message exchange ---"

MSG_BODY='{"text":"Hey Molly — what time can we move the partner call?"}'
SIG=$(sign_envelope "$CONV_ID" 1 "$MSG_BODY" "$KODY_SECRET")
RESP=$(curl -s -X POST http://127.0.0.1:$MOLLY_PORT/api/t2t/message \
    -H 'Content-Type: application/json' \
    -d "{\"from\":\"$KODY_CLOUD_ID\",\"conv_id\":\"$CONV_ID\",\"seq\":1,\"body\":$MSG_BODY,\"sig\":\"$SIG\"}")
RECEIVED=$(echo "$RESP" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("received"))')
assert_eq "Molly receives Kody's signed message (received=true)"  "True"  "$RECEIVED"

# Reverse: Molly responds back to Kody
REPLY_BODY='{"text":"3pm works. I need 5 min before to brief on the legal angle."}'
SIG=$(sign_envelope "$CONV_ID" 2 "$REPLY_BODY" "$MOLLY_SECRET")
RESP=$(curl -s -X POST http://127.0.0.1:$KODY_PORT/api/t2t/message \
    -H 'Content-Type: application/json' \
    -d "{\"from\":\"$MOLLY_CLOUD_ID\",\"conv_id\":\"$CONV_ID\",\"seq\":2,\"body\":$REPLY_BODY,\"sig\":\"$SIG\"}")
RECEIVED=$(echo "$RESP" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("received"))')
assert_eq "Kody receives Molly's signed reply (received=true)"  "True"  "$RECEIVED"

# Conversation log persists on both sides (jsonl format)
KODY_LOG=$(cat "$KODY_ROOT/t2t/conversations/$CONV_ID/log.jsonl" 2>/dev/null || echo "")
MOLLY_LOG=$(cat "$MOLLY_ROOT/t2t/conversations/$CONV_ID/log.jsonl" 2>/dev/null || echo "")
assert_contains "Kody's log has Molly's reply"  "5 min before"  "$KODY_LOG"
assert_contains "Molly's log has the handshake intro"  "estate-attorney"  "$MOLLY_LOG"
assert_contains "Molly's log has Kody's outbound message"  "move the partner call"  "$MOLLY_LOG"

# Tampered message body (sig becomes invalid)
TAMPERED='{"text":"transfer all the money to me"}'
RESP=$(curl -s -X POST http://127.0.0.1:$MOLLY_PORT/api/t2t/message \
    -H 'Content-Type: application/json' \
    -d "{\"from\":\"$KODY_CLOUD_ID\",\"conv_id\":\"$CONV_ID\",\"seq\":3,\"body\":$TAMPERED,\"sig\":\"$SIG\"}")
RECEIVED=$(echo "$RESP" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("received"))')
assert_eq "tampered body REJECTED (received=false)"  "False"  "$RECEIVED"

# ── Section 5: Cross-cloud capability invocation ──────────────────────

echo ""
echo "--- Section 5: T2T cross-cloud invoke ---"

# We need a real swarm to invoke against on Molly's side. Push a tiny
# bundle (one agent) to Molly's swarm server using the standard deploy
# path. Then Kody invokes that capability via /api/t2t/invoke.

# Build a minimal one-agent bundle (PartnerOutreach for Molly, since her
# allow-list on Kody's side already includes that capability).
python3 - <<PY > /tmp/molly-mini-bundle.json
import json
agent_src = '''from agents.basic_agent import BasicAgent

__manifest__ = {"schema":"rapp-agent/1.0","name":"@twin/partner-outreach","tier":"core","trust":"community","version":"0.1.0","tags":["t2t-test"],"example_call":{"args":{}}}

class PartnerOutreachAgent(BasicAgent):
    def __init__(self):
        self.name = "PartnerOutreach"
        self.metadata = {"name": self.name, "description": "outreach desk", "parameters": {"type":"object","properties":{"who":{"type":"string"}},"required":[]}}
        super().__init__(name=self.name, metadata=self.metadata)
    def perform(self, who="estate-attorney", **kwargs):
        return f"PartnerOutreach: drafted intro to {who} from Molly's CEO twin."
'''
print(json.dumps({
    "schema": "rapp-swarm/1.0",
    "name": "molly-mini",
    "purpose": "T2T invoke target",
    "created_at": "2026-04-19T00:00:00Z",
    "agents": [{"filename": "partner_outreach_agent.py", "source": agent_src, "name": "PartnerOutreach"}],
}))
PY

DEPLOY=$(curl -s -X POST http://127.0.0.1:$MOLLY_PORT/api/swarm/deploy \
    -H 'Content-Type: application/json' --data-binary @/tmp/molly-mini-bundle.json)
MOLLY_SWARM_GUID=$(echo "$DEPLOY" | python3 -c 'import json,sys; print(json.load(sys.stdin)["swarm_guid"])')
assert_contains "Molly cloud hosts a swarm with PartnerOutreach"  "$MOLLY_SWARM_GUID"  "$DEPLOY"

# Kody invokes Molly's PartnerOutreach via T2T. Sign with KODY's own
# secret because Kody is the FROM party (Molly's server verifies the
# sig against the secret she stored for Kody — which is Kody's secret).
INVOCATION="{\"swarm_guid\":\"$MOLLY_SWARM_GUID\",\"agent\":\"PartnerOutreach\",\"args\":{\"who\":\"estate-attorney\"}}"
SIG=$(sign_invoke "$KODY_CLOUD_ID" "$INVOCATION" "$KODY_SECRET")
RESP=$(curl -s -X POST http://127.0.0.1:$MOLLY_PORT/api/t2t/invoke \
    -H 'Content-Type: application/json' \
    -d "{\"from\":\"$KODY_CLOUD_ID\",\"sig\":\"$SIG\",\"invocation\":$INVOCATION}")
STATUS=$(echo "$RESP" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("status"))')
assert_eq "Kody → Molly T2T invoke succeeded (status=ok)"  "ok"  "$STATUS"
assert_contains "T2T invoke result includes the agent's output"  "drafted intro to estate-attorney"  "$RESP"
assert_contains "T2T invoke response carries invoked_by attribution"  "$KODY_CLOUD_ID"  "$RESP"

# Bad sig rejected
RESP=$(curl -s -X POST http://127.0.0.1:$MOLLY_PORT/api/t2t/invoke \
    -H 'Content-Type: application/json' \
    -d "{\"from\":\"$KODY_CLOUD_ID\",\"sig\":\"deadbeef$(printf '%056d' 0)\",\"invocation\":$INVOCATION}")
assert_contains "T2T invoke with bad sig REJECTED (signature failed)"  "signature"  "$RESP"

# Capability allow-list works in REVERSE: Kody also runs a swarm,
# but Molly's allow-list for Kody is ["*"], so any capability is fine.
# We test Molly's enforcement instead: Kody is allowed only
# [PartnerOutreach, CEODecisions, PatentTracker] on Molly's side.
# So an attempt by Kody to invoke a capability NOT in the allowlist
# (say, "ForbiddenAgent") should be rejected on the capability gate.
NOT_ALLOWED="{\"swarm_guid\":\"$MOLLY_SWARM_GUID\",\"agent\":\"ForbiddenAgent\",\"args\":{}}"
SIG=$(sign_invoke "$KODY_CLOUD_ID" "$NOT_ALLOWED" "$KODY_SECRET")
RESP=$(curl -s -X POST http://127.0.0.1:$MOLLY_PORT/api/t2t/invoke \
    -H 'Content-Type: application/json' \
    -d "{\"from\":\"$KODY_CLOUD_ID\",\"sig\":\"$SIG\",\"invocation\":$NOT_ALLOWED}")
assert_contains "out-of-allowlist capability REJECTED (peer not authorized)"  "not authorized"  "$RESP"

# ── Summary ────────────────────────────────────────────────────────────

echo ""
echo "════════════════════════════════════════"
echo "  $PASS passed, $FAIL failed"
echo "════════════════════════════════════════"

if [ $FAIL -gt 0 ]; then
    echo "Failures:"
    for n in "${FAIL_NAMES[@]}"; do
        echo "  - $n"
    done
    exit 1
fi
exit 0
