#!/usr/bin/env bash
# loop_orchestrator.sh — one full cycle of the autonomous loop.
#
# Each invocation:
#   1. Tick Bill   (1 LLM call → 1 action: submit/vote/remix/observe-only)
#   2. Tick Alice  (1 LLM call → 1 action)
#   3. Observe     (no LLM — pure filesystem read + ecosystem pulse)
#   4. Print summary; exit
#
# Designed to be installed in cron or launchd. Recommended cadence:
#   */20 * * * *  /Users/<you>/RAPP-sim/loop_orchestrator.sh >> /tmp/rapp-sim.log 2>&1
#
# Cost: 2 LLM calls per cycle. ~$0.01–$0.05/cycle on Sonnet/Opus depending on prompt size.
#
# ENV:
#   TICK_MODE=auto|fake  — default 'auto' (real LLM); set to 'fake' for cron smoke tests
#   ECOSYSTEM_PULSE=1    — also include ecosystem drift in the observation
#
set -euo pipefail
SIM=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
MODE=${TICK_MODE:-auto}
PULSE_FLAG=""
[ "${ECOSYSTEM_PULSE:-0}" = "1" ] && PULSE_FLAG="--with-ecosystem-pulse"

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
log() { echo "[$(ts)] $*"; }

log "=== orchestrator cycle start (mode=$MODE) ==="

for twin in bill-brainstem alice-brainstem; do
  log "tick → $twin"
  if ! python3 "$SIM/tick_twin.py" --twin "$twin" --mode "$MODE"; then
    log "  tick failed for $twin (continuing)"
  fi
done

log "observe"
python3 "$SIM/observe.py" $PULSE_FLAG --quiet
log "  → see ~/RAPP-sim/observations/latest.json"

# Show the brief summary at the end of cycle
LATEST="$SIM/observations/latest.json"
if [ -f "$LATEST" ]; then
  python3 -c "
import json
o = json.load(open('$LATEST'))
m = o['measured']
print(f\"  state: {m['total_submissions']}sub / {m['total_votes']}vote / {m['remix_count']}remix / {m['contributor_count']}contrib\")
adj = o.get('adjustments', [])
if adj:
    print(f\"  ⚠️  {len(adj)} adjustment(s) suggested:\")
    for a in adj:
        print(f\"    [{a['severity']}] {a['kind']}: {a['next_step'][:100]}\")
else:
    print(f\"  ✓ in line with north star\")
"
fi

log "=== cycle complete ==="
