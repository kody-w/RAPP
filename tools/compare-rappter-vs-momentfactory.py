#!/usr/bin/env python3
"""
compare-rappter-vs-momentfactory.py — head-to-head harness.

For each fixture moment in tests/fixtures/moments/:
  A. Invoke the PRIVATE rappter engine (one tick) with the moment as the
     active seed. Extract whatever post(s) appear in the resulting stream
     delta as Engine-A's output.
  B. POST the moment to the PUBLIC RAPP brainstem's MomentFactory rapplication.
     Extract the Drop as Engine-B's output.

Save side-by-side comparison artifacts to /tmp/comparison-cycle-N/.
Optionally call a Reviewer via the brainstem to score head-to-head and write
metrics/momentfactory-vs-rappter.json.

This harness is intentionally adapter-shaped. The rappter engine integration
is best-effort: if RAPPTER_ENGINE_DIR is not set or the engine is not
runnable from this machine, the harness writes a placeholder for Engine A
that the user can fill in by hand or wire up later.

Usage:
    python3 tools/compare-rappter-vs-momentfactory.py                # full run
    python3 tools/compare-rappter-vs-momentfactory.py --dry-run      # validate setup, no LLM calls
    python3 tools/compare-rappter-vs-momentfactory.py --cycle 1 --no-rappter
                                                       # only run Engine B (MomentFactory)
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

RAPP_ROOT = Path(__file__).resolve().parent.parent
FIXTURES  = RAPP_ROOT / "tests" / "fixtures" / "moments"

# Engine A — the private rappter tick/tock organism engine. Optional.
RAPPTER_DIR    = Path(os.environ.get("RAPPTER_ENGINE_DIR", str(Path.home() / "Projects" / "rappter")))
RAPPTERBOOK_DIR = Path(os.environ.get("RAPPTERBOOK_DIR",   str(Path.home() / "Projects" / "rappterbook")))


def list_fixtures() -> list[Path]:
    return sorted(FIXTURES.glob("*.json"))


# ── Engine A: rappter engine adapter ──────────────────────────────────

def engine_a_available() -> tuple[bool, str]:
    """Best-effort check whether the private rappter engine is runnable."""
    if not RAPPTER_DIR.exists():
        return False, f"RAPPTER_ENGINE_DIR does not exist at {RAPPTER_DIR}"
    if not (RAPPTER_DIR / "engine" / "prompts" / "frame.md").exists():
        return False, "engine/prompts/frame.md missing"
    if not RAPPTERBOOK_DIR.exists():
        return False, f"RAPPTERBOOK_DIR does not exist at {RAPPTERBOOK_DIR}"
    return True, "ready"


def engine_a_run(moment: dict) -> dict:
    """Adapter for the private rappter engine.

    The full integration would: inject the moment as the active seed in
    rappterbook/state/seeds.json, invoke one tick via the fleet harness,
    parse the resulting stream delta, and extract post(s).

    For now, this returns a placeholder shape so the harness can produce
    structurally complete comparison artifacts. Wire the real integration
    in when running locally with the engine warm.
    """
    ok, why = engine_a_available()
    if not ok:
        return {"engine": "rappter", "available": False, "reason": why,
                "post": None}
    # Placeholder — returning the structure the comparison expects.
    # A real implementation would shell out to engine/fleet/claude-infinite.sh
    # in single-tick mode after seeding state/seeds.json.
    return {"engine": "rappter", "available": True,
            "note": "Adapter is a stub — wire engine/fleet single-tick when running locally.",
            "post": {
                "title": "(rappter engine not invoked from this run)",
                "body":  "(placeholder — see RAPPTER_ENGINE_DIR docs)",
                "channel": "(unknown)",
            }}


# ── Engine B: MomentFactory via the local RAPP brainstem ──────────────

def brainstem_up(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/swarm/healthz", timeout=2) as r:
            return r.status == 200
    except (urllib.error.URLError, OSError):
        return False


def deploy_momentfactory(port: int) -> str:
    """Deploy the 8 source files as a swarm; return swarm_guid."""
    files = [
        "sensorium_agent.py",
        "significance_filter_agent.py",
        "hook_writer_agent.py",
        "body_writer_agent.py",
        "channel_router_agent.py",
        "card_forger_agent.py",
        "seed_stamper_agent.py",
        "moment_factory_agent.py",
    ]
    agents = [{"filename": f,
               "source": (RAPP_ROOT / "agents" / f).read_text()}
              for f in files]
    bundle = {
        "schema": "rapp-swarm/1.0",
        "name": "comparison-momentfactory",
        "soul": "head-to-head: MomentFactory vs rappter engine",
        "agents": agents,
    }
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/swarm/deploy",
        data=json.dumps(bundle).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())["swarm_guid"]


def engine_b_run(port: int, guid: str, moment: dict) -> dict:
    body = {"name": "MomentFactory",
            "args": {"source": moment["source"],
                     "source_type": moment["source_type"]}}
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/swarm/{guid}/agent",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=240) as r:
            j = json.loads(r.read())
        out = j.get("output", "{}")
        try:
            drop = json.loads(out)
        except json.JSONDecodeError:
            drop = {"raw_output": out}
        return {"engine": "momentfactory", "available": True, "drop": drop}
    except urllib.error.HTTPError as e:
        return {"engine": "momentfactory", "available": False,
                "error": f"HTTP {e.code}: {e.read().decode('utf-8')[:300]}"}
    except urllib.error.URLError as e:
        return {"engine": "momentfactory", "available": False, "error": str(e)}


# ── Orchestrator ──────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="validate paths/config; do not run engines")
    ap.add_argument("--cycle", type=int, default=1, help="comparison cycle number")
    ap.add_argument("--port", type=int, default=7188,
                    help="port to start a temporary RAPP brainstem on")
    ap.add_argument("--no-rappter", action="store_true",
                    help="skip Engine A (rappter engine)")
    ap.add_argument("--no-momentfactory", action="store_true",
                    help="skip Engine B (MomentFactory)")
    args = ap.parse_args()

    fixtures = list_fixtures()
    print(f"→ {len(fixtures)} fixture moments")

    out_dir = Path("/tmp") / f"comparison-cycle-{args.cycle}"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"→ writing to {out_dir}")

    a_ok, a_why = engine_a_available()
    print(f"→ Engine A (rappter):       {'AVAILABLE' if a_ok else 'unavailable'} — {a_why}")

    if args.dry_run:
        print("✓ dry-run: setup OK, no LLM calls made")
        return 0

    # Spin up a local brainstem if needed
    server_proc = None
    guid = None
    if not args.no_momentfactory:
        if brainstem_up(args.port):
            print(f"→ Engine B (MomentFactory): brainstem already running at :{args.port}")
        else:
            print(f"→ Engine B (MomentFactory): starting temp brainstem at :{args.port}")
            root = f"/tmp/rapp-comparison-cycle-{args.cycle}"
            subprocess.run(["rm", "-rf", root], check=False)
            server_proc = subprocess.Popen(
                ["python3", "-u", "swarm/server.py", "--port", str(args.port), "--root", root],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                cwd=RAPP_ROOT)
            time.sleep(2)
            if not brainstem_up(args.port):
                print(f"  ✗ brainstem failed to start; check logs")
                return 1
        guid = deploy_momentfactory(args.port)
        print(f"  ✓ deployed swarm {guid}")

    # Per-fixture comparison
    summaries = []
    try:
        for i, fx in enumerate(fixtures, 1):
            moment = json.loads(fx.read_text())
            mid = moment["moment_id"]
            print(f"\n[{i}/{len(fixtures)}] {mid} ({moment['source_type']})")

            a_out = None
            if not args.no_rappter:
                a_out = engine_a_run(moment)
            b_out = None
            if not args.no_momentfactory:
                b_out = engine_b_run(args.port, guid, moment)
                if b_out.get("available"):
                    drop = b_out.get("drop", {})
                    skipped = drop.get("skipped")
                    if skipped:
                        print(f"  B (MomentFactory): SKIPPED — {drop.get('skipped_reason','')}")
                    else:
                        print(f"  B (MomentFactory): hook = {drop.get('hook','')[:90]}")
                        print(f"                     channel = {drop.get('channel','')}")
                        print(f"                     significance = {drop.get('significance_score','')}")
                else:
                    print(f"  B (MomentFactory): FAILED — {b_out.get('error','unknown')}")

            comparison = {
                "moment_id": mid,
                "source_type": moment["source_type"],
                "expected_significance": moment.get("expected_significance"),
                "expected_channel_hint": moment.get("expected_channel_hint"),
                "engine_a_rappter": a_out,
                "engine_b_momentfactory": b_out,
            }
            (out_dir / f"{mid}.json").write_text(json.dumps(comparison, indent=2))
            summaries.append(comparison)
    finally:
        if server_proc:
            server_proc.terminate()
            try:
                server_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_proc.kill()

    # Summary scoreboard
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps({
        "cycle": args.cycle,
        "fixture_count": len(summaries),
        "engine_a_available": a_ok,
        "engine_b_drops_shipped": sum(
            1 for s in summaries
            if s["engine_b_momentfactory"]
            and s["engine_b_momentfactory"].get("available")
            and not s["engine_b_momentfactory"].get("drop", {}).get("skipped")
        ),
        "engine_b_drops_skipped": sum(
            1 for s in summaries
            if s["engine_b_momentfactory"]
            and s["engine_b_momentfactory"].get("available")
            and s["engine_b_momentfactory"].get("drop", {}).get("skipped")
        ),
    }, indent=2))
    print(f"\n✓ comparison cycle {args.cycle} complete — {summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
