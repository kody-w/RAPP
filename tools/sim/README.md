# tools/sim/ - restored simulation harness

The complete historical simulation algorithms are retained below as data
exhaust. Current no-flag operation is deterministic and local:

```bash
python3 tools/sim/plant_two_brainstems.py
python3 tools/sim/tick_twin.py
python3 tools/sim/observe.py
bash tools/sim/loop_orchestrator.sh
bash tools/sim/push_canvas.sh
```

Those commands only inspect, plan, or replay in memory. They do not call a
model, read credentials, launch a subprocess, write a repository or simulation
tree, bind a port, package an artifact, or publish. Candidate RAPP chat is
routed only through `http://127.0.0.1:7073/chat`.

Effectful `--run` / `--apply` modes require all three of:

1. reviewed dependency injection for every effect boundary;
2. an exact `rapp-effect-target-receipt/1.0` matching the operation and target;
3. fresh authenticated RAPP/1 section-13 evidence rooted in the independently
   distributed owner anchor.

This checkout cannot authenticate the third prerequisite, so current effect
modes refuse before invoking their injected executor.

## Exact source provenance

| Path | Fullest source commit | Blob | SHA-256 |
|---|---|---|---|
| `README.md` | `05f75bd40dd37f4590da6ebab28110d9a4b4094a` | `9a966032e0c167ab26393f2ac784b6f676d76e27` | `ada367799ca3a84c4b4d3275d4317357f2611b6113ae696f3ddbf0bcbf8d9a9b` |
| `loop_orchestrator.sh` | `55b91b9ecd182a3ce2057787f07c60e9aa3ca128` | `9e345f817d06fe5fadfba60e24b7b3b28eea10b2` | `4473c3abdb547b877570df80b063c440ad418228c95cd5c8c81346444e0589bc` |
| `observe.py` | `55b91b9ecd182a3ce2057787f07c60e9aa3ca128` | `5539942887c866bfd0cdc087ad68cf77a0c39b8f` | `b2f29a703daa82d5d738df2b31f2915a874dfae373dfa043d2a31b890c7c54db` |
| `plant_two_brainstems.py` | `40f00e1e669d4cd4bb97e2947a0b79739a9ba701` | `aa15a82542aadee01afda555e7e3ac64e3e9436e` | `676364e8d62d49965e3e1c588ef1352448a8e77491e9d21cfed110b3454a18f3` |
| `push_canvas.sh` | `8d089dc459f156fb214316db3383e2d95355261d` | `31f09a46735aa0d058bd55fab22dc6a55d921698` | `734670eaa877b78e3f913d2abc3235baab17ddb358d94181abc89c8ca367e88e` |
| `tick_twin.py` | `05f75bd40dd37f4590da6ebab28110d9a4b4094a` | `70e1e36890238745729117d6d029640f06262d66` | `2e1016a842336d7b5e2eff50d6d05b5ad6da33fd1590936ac18d24f6ee6d5405` |

## Historical implementation guide

# tools/sim/ - multi-AI local-first simulation harness

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
