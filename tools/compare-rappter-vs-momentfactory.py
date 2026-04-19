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


def engine_a_run(moment: dict, invoke: bool = False, timeout_sec: int = 240) -> dict:
    """Adapter for the private rappter tick/tock organism engine.

    Two modes:
      • dry / preview (default) — describe exactly what would be invoked.
        Cheap, deterministic, no LLM calls.
      • --invoke-rappter — actually queue the moment as a seed, run one tick
        via the fleet harness, parse the resulting stream-delta files for new
        posts. Costs LLM calls and ~2-4 minutes per moment.

    Seed-injection contract:
      • <RAPPTERBOOK_DIR>/state/seeds.json — moment becomes the active seed
      • bash <RAPPTER_DIR>/engine/fleet/claude-infinite.sh runs ONE frame
      • <RAPPTERBOOK_DIR>/state/stream_deltas/frame-N-*.json holds the result
      • Posts pulled from delta.posts_created
    """
    ok, why = engine_a_available()
    if not ok:
        return {"engine": "rappter", "available": False, "reason": why,
                "post": None}

    rb_state   = RAPPTERBOOK_DIR / "state"
    seeds_path = rb_state / "seeds.json"
    deltas_dir = rb_state / "stream_deltas"

    if not invoke:
        return {
            "engine": "rappter",
            "available": True,
            "mode": "preview",
            "would_inject_into": str(seeds_path),
            "would_run":         f"bash {RAPPTER_DIR}/engine/fleet/claude-infinite.sh "
                                  "--streams 1 --hours 0.05 --interval 60",
            "would_read_from":   str(deltas_dir),
            "post":              None,
            "note": "Re-run with --invoke-rappter to actually fire the engine and harvest posts.",
        }

    # Live invocation
    seeds_path.parent.mkdir(parents=True, exist_ok=True)
    seeds = json.loads(seeds_path.read_text()) if seeds_path.exists() else {"active": None, "queue": []}
    seed_id = f"comparison-{moment['moment_id']}-{int(time.time())}"
    seed_entry = {
        "id":        seed_id,
        "text":      moment["source"],
        "context":   f"injected by RAPP head-to-head harness; source_type={moment['source_type']}",
        "source":    "compare-rappter-vs-momentfactory",
        "tags":      ["harness", moment["source_type"]],
        "queued_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
    }
    seeds["active"] = {**seed_entry, "frames_active": 0,
                       "experiment": "head-to-head", "frame": 1, "max_frames": 1}
    seeds_path.write_text(json.dumps(seeds, indent=2))

    before = set(p.name for p in deltas_dir.glob("frame-*.json")) if deltas_dir.exists() else set()
    cmd = ["bash", str(RAPPTER_DIR / "engine" / "fleet" / "claude-infinite.sh"),
           "--streams", "1", "--hours", "0.05", "--interval", "60"]
    try:
        proc = subprocess.run(
            cmd, cwd=str(RAPPTER_DIR), capture_output=True, text=True,
            timeout=timeout_sec,
            env={**os.environ, "RAPPTERBOOK_PATH": str(RAPPTERBOOK_DIR)})
        invoke_status = proc.returncode
        invoke_stderr = (proc.stderr or "")[-500:]
    except subprocess.TimeoutExpired:
        return {"engine": "rappter", "available": True, "mode": "live",
                "error": f"engine timeout after {timeout_sec}s",
                "seed_id": seed_id, "post": None}

    after = set(p.name for p in deltas_dir.glob("frame-*.json")) if deltas_dir.exists() else set()
    new_files = sorted(after - before)
    posts = []
    for fn in new_files:
        try:
            delta = json.loads((deltas_dir / fn).read_text())
        except (OSError, json.JSONDecodeError):
            continue
        for p in delta.get("posts_created", []) or []:
            posts.append({
                "title":      p.get("title"),
                "body":       (p.get("body", "") or "")[:1500],
                "channel":    p.get("channel"),
                "by":         p.get("agent_id"),
                "frame":      delta.get("frame"),
                "delta_file": fn,
            })

    return {
        "engine": "rappter",
        "available": True,
        "mode": "live",
        "seed_id": seed_id,
        "invoke_status": invoke_status,
        "invoke_stderr_tail": invoke_stderr,
        "new_delta_files": new_files,
        "post_count": len(posts),
        "posts": posts,
    }


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
               "source": (RAPP_ROOT / "rapplications" / "momentfactory" / "source" / f).read_text()}
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
    ap.add_argument("--invoke-rappter", action="store_true",
                    help="actually fire the rappter engine (default: preview only)")
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
                ["python3", "-u", "rapp_brainstem/brainstem.py", "--port", str(args.port), "--root", root],
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
                a_out = engine_a_run(moment, invoke=args.invoke_rappter)
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
