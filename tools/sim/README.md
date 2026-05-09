# tools/sim/ — multi-AI local-first simulation harness

Runs **two or more grail-compliant brainstems** against **one local-first
neighborhood** continuously and autonomously. Each twin is driven by its
own isolated `claude` CLI session (or any other LLM CLI you can pin to a
working directory). Operator-mediated by design — the script proposes,
disposes within sandboxed local writes only.

The point: prove that the holocard / specs / encounter-protocol grail
actually works for autonomous AI participation, surface drift between
*observed* and *expected*, and let the operator self-correct the
ecosystem.

## Files

| File | Purpose |
|---|---|
| `plant_two_brainstems.py` | One-shot: plant Bill + Alice + a local neighborhood (full grail each), then run a 4-round demo simulation. |
| `tick_twin.py` | One autonomous tick for ONE twin. Calls `claude` CLI in a fresh isolated session pinned to the twin's directory. Twin proposes ONE action (submit / vote / remix / observe-only); the script validates + executes locally. |
| `observe.py` | Pure-filesystem observer (no LLM call). Compares simulation state to `expected.json`, surfaces concrete adjustment suggestions. Optional `--with-ecosystem-pulse` folds in BondRhythm drift detection for the whole RAPP offspring set. |
| `expected.json` | The "what we are trying to do" — north-star metrics + antipatterns to check for. The observer reads this. |
| `loop_orchestrator.sh` | One full cycle: tick Bill → tick Alice → observe → print summary. Designed for cron. |
| `scale_simulation.py` | 10-twin volatile public neighborhood — twins join + leave at staggered times, some "hard-leave" (rm -rf brainstem dir, simulating WebRTC peer disconnection). Proves canvas survives churn. |

## Quick start (Tier 1)

```bash
# 1. Plant Bill + Alice + local neighborhood; run a 4-round demo
python3 ~/Documents/GitHub/RAPP/tools/sim/plant_two_brainstems.py

# 2. One real LLM tick per twin (one fresh `claude` CLI session each)
python3 ~/Documents/GitHub/RAPP/tools/sim/tick_twin.py --twin bill-brainstem --mode auto
python3 ~/Documents/GitHub/RAPP/tools/sim/tick_twin.py --twin alice-brainstem --mode auto

# 3. Observe state vs. expected
python3 ~/Documents/GitHub/RAPP/tools/sim/observe.py

# 4. One full cycle (the cron unit)
~/Documents/GitHub/RAPP/tools/sim/loop_orchestrator.sh
```

## Continuous + autonomous (cron)

Install one cron entry to make the loop self-driving:

```bash
# Tick + observe every 20 min
crontab -e
# add:
*/20 * * * *  /Users/<you>/Documents/GitHub/RAPP/tools/sim/loop_orchestrator.sh >> /tmp/rapp-sim.log 2>&1
```

Cost: each cycle = 2 LLM calls (Bill + Alice). At ~$0.01–$0.05 per cycle on
Claude Sonnet/Opus, that's under $5/day at the 20-min cadence.

For a higher-frequency / lower-cost mode, set `TICK_MODE=fake` in the env
before the cron entry runs — that switches to deterministic action picking
(no LLM, but still exercises the full grail surface):

```cron
*/5 * * * *  TICK_MODE=fake /Users/<you>/.../loop_orchestrator.sh >> /tmp/rapp-sim.log 2>&1
```

## What the observer flags

`observe.py` reads `expected.json` and surfaces SPECIFIC next-step
suggestions for the operator:

| Drift | Suggestion |
|---|---|
| `low-participation` (< 2 contributors) | Run another tick |
| `low-canvas` (< N submissions) | Run more ticks |
| `twin-idle` (> max idle seconds) | Tick that twin specifically |
| `grail-incomplete` (missing files) | Re-run the planter |
| `voices-too-similar` (Jaccard > threshold) | Operator should diverge `soul.md` content |
| `antipattern-violation` (forbidden phrases) | Hard-fix immediately |
| `ecosystem-drift` (BondRhythm pulse fired) | Inspect via `tools/ecosystem_audit.py` |

The observer **never auto-applies adjustments** — operator-mediated per
ANTIPATTERNS §9.

## Volatile public-neighborhood test

Simulates a WebRTC-style neighborhood with 10 twins joining + leaving at
staggered times. Some twins "hard-leave" (their brainstem dir is removed
mid-simulation, modeling a peer that went offline). The canvas should
survive — that's the local-first guarantee.

```bash
python3 ~/Documents/GitHub/RAPP/tools/sim/scale_simulation.py --twins 10 --rounds 20
```

Expected output: 80+ actions, 0 broken remix lineage links, canvas
preserves all submissions + votes even from hard-left peers.

## How it integrates with the grail

Each twin produced by `plant_two_brainstems.py` is **fully grail-compliant**:

- `card.json` per RAPPcards/1.1.2 (id, seed via BLAKE2b-64, hp/stats, agent_types, abilities, embedded `avatar_svg`)
- `holo.md` — anonymous-AI entry doc
- `holo.svg` + `holo-qr.svg`
- `soul.md` — distinct voice block
- `rappid.json` — v2 format, locally-minted
- `bonds.json` — append-only event log
- `specs/` — full bundled contracts (HOLOCARD_SPEC, RAPPID_SPEC, ANTIPATTERNS, SOUL_IDENTITY, PARTICIPATION, TWIN_PROTOCOL)

The neighborhood is the same — full grail with `SUBMISSION_PROTOCOL.md`
in `specs/`. When a twin's `claude` session reads `holo.md` + the specs,
it has everything it needs to participate in-contract — no parent-repo
lookup, no live network call.

## What this proves

1. **Grail-driven autonomy:** an LLM that's never seen RAPP can read a
   neighborhood's `holo.md` + `specs/<KIND>_PROTOCOL.md` and contribute
   correctly on the first try. Demonstrated — Bill's first real-LLM tick
   produced an in-voice vote with the correct schema.
2. **Bidirectional encounter:** twins ship their own holocard + specs;
   neighborhoods ship theirs. Both sides self-describe.
3. **Local-first survival:** canvas persists when peers vanish. 10-twin
   simulation: 3 hard-leaves, 0 lost submissions, 0 broken remix links.
4. **Self-correcting ecosystem:** observer surfaces concrete next steps
   when reality drifts from `expected.json`. Operator-mediated.
5. **Cost-efficient continuous operation:** ~2 LLM calls per cycle =
   under $5/day at 20-min cadence. Operator can flip to fake mode for
   high-frequency local testing.
