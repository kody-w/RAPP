#!/usr/bin/env bash
# Scenario 10 — Time Capsule.
#
# An organism state is sealed today with a release date in the future.
# When the date passes, the time-capsule agent unseals + activates the
# bundle. Tests: future-dated artifact, deferred activation, awakening
# protocol via comparing now vs sealed_until_utc.

source "$(dirname "$0")/_lib.sh"
scenario_parse_args "$@"

heading "Scenario 10 — Time Capsule"
note "Pattern: a sealed bundle with sealed_until_utc that unlocks on/after that date"
note "Showcases: scheduled releases, futures-marketing, posthumous publishing, etc."

TMP=$(mktemp -d -t rapp-scenario-10-XXXXXX)
trap 'rm -rf "$TMP"' EXIT
CAPSULES="$TMP/capsules"
mkdir -p "$CAPSULES"

# 1. Seal a capsule for the FUTURE — should NOT unseal
FUTURE=$(date -u -v+1H +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u -d "+1 hour" +"%Y-%m-%dT%H:%M:%SZ")
cat > "$CAPSULES/future.json" <<EOF
{
  "schema": "rapp-time-capsule/1.0",
  "sealed_at": "2026-05-08T00:00:00Z",
  "sealed_by": "kody-w",
  "sealed_until_utc": "$FUTURE",
  "payload": {
    "kind": "memory",
    "body": "Reveal the secret roadmap on launch day."
  }
}
EOF

# 2. Seal a capsule for the PAST — should unseal
PAST="2026-01-01T00:00:00Z"
cat > "$CAPSULES/past.json" <<EOF
{
  "schema": "rapp-time-capsule/1.0",
  "sealed_at": "2025-12-01T00:00:00Z",
  "sealed_by": "kody-w",
  "sealed_until_utc": "$PAST",
  "payload": {
    "kind": "memory",
    "body": "This message becomes public on Jan 1 2026."
  }
}
EOF
step_pass "two capsules staged (one past, one future)"

# 3. The check-and-release "agent" — pure-python, demonstrates the pattern
RELEASED=$(python3 - "$CAPSULES" <<'PY'
import json, os, sys, time
from datetime import datetime
capsules_dir = sys.argv[1]
now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
released = []
for fn in sorted(os.listdir(capsules_dir)):
    if not fn.endswith(".json"):
        continue
    with open(os.path.join(capsules_dir, fn)) as f:
        c = json.load(f)
    until = c.get("sealed_until_utc", "")
    if until <= now:
        released.append(fn)
print(json.dumps(released))
PY
)

if echo "$RELEASED" | grep -q "past.json" && ! echo "$RELEASED" | grep -q "future.json"; then
  step_pass "past capsule released; future capsule still sealed"
else
  step_fail "release policy unexpected: $RELEASED"
fi

# 4. The release should be idempotent — re-running doesn't re-release
RELEASED2=$(python3 - "$CAPSULES" <<'PY'
import json, os, sys, time
capsules_dir = sys.argv[1]
now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
released = []
for fn in sorted(os.listdir(capsules_dir)):
    if not fn.endswith(".json"):
        continue
    with open(os.path.join(capsules_dir, fn)) as f:
        c = json.load(f)
    if c.get("sealed_until_utc", "") <= now:
        released.append(fn)
print(json.dumps(released))
PY
)
if [ "$RELEASED" = "$RELEASED2" ]; then
  step_pass "release check is idempotent (same answer twice)"
else
  step_fail "release check not idempotent"
fi

heading "Why this matters"
cat <<'EOF'
  Time capsules are how an organism schedules its own future moves.
  Posthumous statements, surprise releases, deferred memory-reveal,
  scheduled handoffs. The pattern is just "compare sealed_until_utc to
  now, release iff <=". Same shape as soul travel + Dream Catcher's
  UTC-first canon — temporal ordering is already a first-class concept
  in the platform.
EOF

scenario_summary
