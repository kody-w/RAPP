#!/usr/bin/env bash
# loop_orchestrator.sh — one full cycle of the autonomous loop.
#
# Each invocation:
#   1. Tick Bill        (1 LLM call → 1 action: submit/vote/remix/observe-only)
#   2. Tick Alice       (1 LLM call → 1 action)
#   3. Tick Echo        (1 LLM call → 1 action — pattern-synthesizer twin,
#                        embodies the public kody-w/echo-brainstem)
#   4. Push canvas      (git add+commit+push the local neighborhood → public repo)
#   5. Observe          (no LLM — pure filesystem read + optional ecosystem pulse)
#   6. Print summary; exit
#
# After step 4, vbrainstem (and any other browser/public observer) sees all three
# twins' autonomous tick contributions on github.com/kody-w/sim-art-collective.
#
# Designed to be installed in cron or launchd. Recommended cadence:
#   */20 * * * *  /Users/<you>/.../loop_orchestrator.sh >> /tmp/rapp-sim.log 2>&1
#
# Cost: 3 LLM calls per cycle. ~$0.02–$0.08/cycle on Sonnet/Opus depending on prompt size.
#
# Always real LLM ticks — there is no fake / deterministic / pre-scripted
# persona mode. Autonomous means autonomous. (Per memory feedback
# "feedback_no_fake_mode".)
#
# ENV:
#   ECOSYSTEM_PULSE=1   — also include ecosystem drift in the observation
#   PUSH_CANVAS=0       — skip the public push (default: push enabled)
#   NEIGHBORHOOD_DIR    — override path to the neighborhood (defaults to ~/RAPP-sim/local-art-collective)
#
# Historical source provenance (fullest known implementation).
# commit: 55b91b9ecd182a3ce2057787f07c60e9aa3ca128
# blob: 9e345f817d06fe5fadfba60e24b7b3b28eea10b2
# sha256: 4473c3abdb547b877570df80b063c440ad418228c95cd5c8c81346444e0589bc
historical_orchestrator_cycle() (
set -uo pipefail
SIM=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PULSE_FLAG=""
[ "${ECOSYSTEM_PULSE:-0}" = "1" ] && PULSE_FLAG="--with-ecosystem-pulse"
NB_DIR=${NEIGHBORHOOD_DIR:-$HOME/RAPP-sim/local-art-collective}

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
log() { echo "[$(ts)] $*"; }

log "=== orchestrator cycle start (real LLM ticks) ==="

for twin in bill-brainstem alice-brainstem echo-brainstem; do
  if [ ! -d "$HOME/RAPP-sim/$twin" ]; then
    log "skip → $twin (not present at ~/RAPP-sim/$twin)"
    continue
  fi
  log "tick → $twin"
  if ! python3 "$SIM/tick_twin.py" --twin "$twin"; then
    log "  tick failed for $twin (continuing)"
  fi
done

if [ "${PUSH_CANVAS:-1}" = "1" ]; then
  log "push canvas → public repo (additive, no-op if no changes)"
  if ! "$SIM/push_canvas.sh" "$NB_DIR"; then
    log "  push failed (continuing — canvas is still consistent locally)"
  fi
else
  log "push canvas: SKIPPED (PUSH_CANVAS=0)"
fi

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
)

print_sandbox_replay() {
  printf '%s\n' \
    '{"schema":"rapp-simulation-cycle/1.0","mode":"sandbox","clock":"2000-01-01T00:00:00Z","ticks":[{"twin":"bill-brainstem","action":"submit"},{"twin":"alice-brainstem","action":"vote"},{"twin":"echo-brainstem","action":"observe-only"}],"observation":{"total_submissions":1,"total_votes":1,"remix_count":0,"contributor_count":2},"publish":false,"effects":[]}' \
    'No model, subprocess, observation write, git operation, network request, credential access, or repository mutation occurs in sandbox mode.'
}

refuse_run() {
  printf '%s\n' \
    '{"schema":"rapp-effect-refusal/1.0","operation":"simulation-orchestrator-run","code":"authenticated-registry-unavailable","effects_started":false,"requirements":["reviewed-dependency-injection","exact-target-receipt","authenticated-fresh-section-13-evidence"]}' \
    'Current authority is unavailable; run/apply is refused before tick, observe, push, model, subprocess, or repository effects.' >&2
  return 78
}

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  unset -f historical_orchestrator_cycle print_sandbox_replay refuse_run
  return 0
fi

case "${1:-sandbox}" in
  sandbox|--sandbox|plan|--plan|inspect|--inspect|check|--check)
    print_sandbox_replay
    ;;
  run|--run|apply|--apply)
    refuse_run
    ;;
  help|-h|--help)
    printf '%s\n' \
      'Usage: loop_orchestrator.sh [--sandbox|--plan|--inspect|--check|--run]' \
      'Default: deterministic in-memory cycle replay.' \
      '--run requires reviewed dependency injection, an exact target receipt,' \
      'and authenticated fresh RAPP/1 section-13 evidence; unavailable here.'
    ;;
  *)
    printf 'Unknown mode: %s\n' "$1" >&2
    exit 2
    ;;
esac
