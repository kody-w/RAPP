#!/usr/bin/env bash
# Scenario 15 — Offline Neighborhood Snapshot + Dream Catcher Reassimilation.
#
# A complete neighborhood is packed as an egg. A brainstem takes the egg
# offline, hatches it locally, runs in its own dimension (accumulates new
# state), and when the connection returns, Dream Catcher merges the
# divergent dimension back into the canonical neighborhood.
#
# This is the LOCAL-FIRST NEIGHBORHOOD pattern: the substrate adapts to
# zero connectivity. The neighborhood is portable; offline isn't a
# degraded mode, it's a first-class one.

source "$(dirname "$0")/_lib.sh"
scenario_parse_args "$@"

heading "Scenario 15 — Offline Neighborhood Snapshot + Dream Catcher"
note "Pattern: neighborhood-as-egg → hatched offline → reassimilated via Dream Catcher"
note "Showcases: local-first neighborhoods. Offline is first-class, not degraded."

TMP=$(mktemp -d -t rapp-scenario-15-XXXXXX)
trap 'rm -rf "$TMP"' EXIT

# 1. The "global" canonical neighborhood (think: GitHub-hosted)
GLOBAL="$TMP/global"
mkdir -p "$GLOBAL"
cp -R "$SEEDS_DIR/braintrust-template/." "$GLOBAL/"
step_pass "global neighborhood staged"

# 2. PACK the neighborhood as an egg with a frame log capturing current state
EGG="$TMP/neighborhood.egg"
cat > "$GLOBAL/frames.json" <<EOF
{
  "schema": "rapp-frame-log/1.0",
  "stream_id": "neighborhood:dd06b965",
  "frames": [
    {"frame_n": 1, "utc": "2026-05-08T00:00:00Z", "kind": "neighborhood_planted", "payload": {"by": "kody-w"}}
  ]
}
EOF
(cd "$GLOBAL" && zip -qr "$EGG" .)
SHA=$(shasum -a 256 "$EGG" | awk '{print $1}')
step_pass "neighborhood packed to $EGG (sha256 ${SHA:0:12}...) with frame log"

# 3. HATCH the egg on a fully-disconnected device (no GitHub access)
OFFLINE="$TMP/offline-device"
mkdir -p "$OFFLINE"
(cd "$OFFLINE" && unzip -q "$EGG")
if [ -f "$OFFLINE/neighborhood.json" ] && [ -f "$OFFLINE/frames.json" ]; then
  step_pass "offline device hatched the neighborhood (incl. frame log)"
else
  step_fail "offline hatch failed"
fi

# 4. Mark this as a parallel dimension — append a new frame on the offline copy
python3 - "$OFFLINE/frames.json" <<'PY'
import json, sys, time
p = sys.argv[1]
log = json.load(open(p))
log["dimension"] = "offline-2026-05-08-laptop"
log["frames"].append({
    "frame_n": 2,
    "utc": "2026-05-08T01:00:00Z",
    "kind": "decision_logged",
    "payload": {"by": "kody-w", "decision": "Offline addition: trial X"}
})
log["frames"].append({
    "frame_n": 3,
    "utc": "2026-05-08T02:00:00Z",
    "kind": "memory_added",
    "payload": {"body": "Offline insight: degradation should be invisible to UX"}
})
json.dump(log, open(p, "w"), indent=2)
PY
OFFLINE_FRAMES=$(python3 -c "import json; print(len(json.load(open('$OFFLINE/frames.json'))['frames']))")
if [ "$OFFLINE_FRAMES" -eq 3 ]; then
  step_pass "offline dimension accumulated 2 new frames (total 3)"
else
  step_fail "offline frame log unexpected: $OFFLINE_FRAMES"
fi

# 5. Re-establish connection — DREAM CATCHER merge global + offline frames
#    UTC-first canon; non-contradicting frames layer on; contradictions preserved.
MERGED="$TMP/merged-frames.json"
python3 - "$GLOBAL/frames.json" "$OFFLINE/frames.json" "$MERGED" <<'PY'
import json, sys
global_log = json.load(open(sys.argv[1]))
offline_log = json.load(open(sys.argv[2]))

# Index by (utc, frame_n) — the PK
def key(f): return (f["utc"], f["frame_n"])
combined = {}
for f in global_log["frames"]:
    combined[key(f)] = f
contradictions = []
for f in offline_log["frames"]:
    k = key(f)
    if k in combined:
        if combined[k] != f:
            contradictions.append({"pk": k, "global": combined[k], "offline": f})
    else:
        combined[k] = f

merged = {
    "schema": "rapp-frame-log/1.0",
    "stream_id": global_log["stream_id"],
    "frames": sorted(combined.values(), key=lambda f: (f["utc"], f["frame_n"])),
    "contradictions": contradictions,
    "merged_dimensions": [global_log.get("dimension", "canon"), offline_log.get("dimension", "?")],
}
json.dump(merged, open(sys.argv[3], "w"), indent=2)
PY
MERGED_COUNT=$(python3 -c "import json; print(len(json.load(open('$MERGED'))['frames']))")
if [ "$MERGED_COUNT" -eq 3 ]; then
  step_pass "Dream Catcher merged 3 frames (1 from canon + 2 from offline dimension, no conflicts)"
else
  step_fail "merged frame count unexpected: $MERGED_COUNT"
fi

CONTRADICTIONS=$(python3 -c "import json; print(len(json.load(open('$MERGED'))['contradictions']))")
if [ "$CONTRADICTIONS" -eq 0 ]; then
  step_pass "no contradictions (offline added genuinely new frames, no conflict)"
else
  step_pass "$CONTRADICTIONS contradictions preserved (alternate-dimension data)"
fi

# 6. Verify offline-mode could ALSO run agents while disconnected
PING=$(NEIGHBORHOOD_SEED_DIR="$OFFLINE" python3 - <<'PY'
import importlib.util, json, os, sys
sys.path.insert(0, os.environ["NEIGHBORHOOD_SEED_DIR"])
spec = importlib.util.spec_from_file_location("intro", os.path.join(os.environ["NEIGHBORHOOD_SEED_DIR"], "agents/braintrust_request_agent.py"))
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
out = mod.BraintrustRequestAgent().perform(topic="What works offline?", requester_login="kody-w")
print(out)
PY
)
if echo "$PING" | grep -q "request_id"; then
  step_pass "offline brainstem can still create new requests against the hatched neighborhood"
else
  step_fail "offline brainstem could not create requests"
fi

heading "Why this matters"
cat <<'EOF'
  This is the local-first neighborhood pattern made concrete:

    1. Pack:   any neighborhood → portable .egg with frames + state
    2. Hatch:  any brainstem can run that .egg fully offline
    3. Run:    the offline dimension accumulates its own frames (work
               continues; the neighborhood is "all the way home")
    4. Merge:  Dream Catcher re-folds the offline dimension into the
               canonical neighborhood when connection returns; UTC-first
               canon, contradictions preserved as alternate-dimension data

  Offline isn't a "degraded mode" — it's first-class. A brainstem that
  hatched a neighborhood-egg in the woods is JUST AS REAL as one connected
  to GitHub, until they meet again at which point both histories merge.
  This is what "use what is home, don't worry about what isn't" looks
  like when the home includes time itself.
EOF

scenario_summary
