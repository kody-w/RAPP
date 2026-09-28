#!/usr/bin/env python3
"""autopilot_exhaust.py — rapp/1 frame exhaust for autopilot sessions.

Every autonomous UI-driving session leaves a deterministic, hash-chained
trail of frames — one frame per action, written BEFORE conclusions are drawn
from it. When something breaks, the exhaust names the exact frame: what was
driven, with what input, what came back, and everything that led there.

    frames:  ~/.rapp/autopilot/<session>/frames.jsonl
             one rapp-autopilot-frame/1 per line
    session: ~/.rapp/autopilot/<session>/session.json
             one rapp-autopilot-session/1 manifest

rapp/1 discipline (RAPP1_AUTHORITY.json): canonical JSON is sorted-keys,
compact separators; a frame's `id` is sha256(canonical frame sans id)[:12];
`prev` is the prior frame's id, so the chain is tamper-evident and a frame
cites its whole history. `verify` re-folds the chain and refuses drift.

Usage:
    autopilot_exhaust.py start   --intent "..." [--surface URL] → prints session id
    autopilot_exhaust.py frame   --session S --action A [--target T]
                                 [--input I] [--observed O] [--outcome ok|fail]
                                 [--note N]                    → prints frame id
    autopilot_exhaust.py close   --session S --outcome pass|fail [--note N]
    autopilot_exhaust.py verify  --session S                   → exits non-zero on drift
    autopilot_exhaust.py show    --session S                   → human-readable trail
"""

import argparse
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone

HOME = os.path.expanduser(os.environ.get("RAPP_AUTOPILOT_HOME", "~/.rapp/autopilot"))
FRAME_SCHEMA = "rapp-autopilot-frame/1"
SESSION_SCHEMA = "rapp-autopilot-session/1"


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _frame_id(frame: dict) -> str:
    body = {k: v for k, v in frame.items() if k != "id"}
    return hashlib.sha256(_canonical(body).encode()).hexdigest()[:12]


def _session_dir(session: str) -> str:
    d = os.path.join(HOME, session)
    if not os.path.isdir(d):
        sys.exit(f"no such autopilot session: {session}")
    return d


def _frames_path(session: str) -> str:
    return os.path.join(_session_dir(session), "frames.jsonl")


def _read_frames(session: str):
    path = _frames_path(session)
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def cmd_start(a):
    session = f"ap-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    d = os.path.join(HOME, session)
    os.makedirs(d, exist_ok=True)
    manifest = {
        "schema": SESSION_SCHEMA,
        "session": session,
        "started_at": _now(),
        "intent": a.intent,
        "surface": a.surface,
        "actor": a.actor,
        "host": os.uname().nodename.split(".")[0],
        "status": "open",
    }
    with open(os.path.join(d, "session.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print(session)
    return session


def cmd_frame(a):
    frames = _read_frames(a.session)
    frame = {
        "schema": FRAME_SCHEMA,
        "session": a.session,
        "seq": len(frames),
        "at": _now(),
        "action": a.action,
        "target": a.target,
        "input": a.input,
        "observed": a.observed,
        "outcome": a.outcome,
        "note": a.note,
        "prev": frames[-1]["id"] if frames else None,
    }
    frame["id"] = _frame_id(frame)
    with open(_frames_path(a.session), "a") as f:
        f.write(_canonical(frame) + "\n")
    print(frame["id"])
    return frame["id"]


def cmd_close(a):
    d = _session_dir(a.session)
    frames = _read_frames(a.session)
    with open(os.path.join(d, "session.json")) as f:
        manifest = json.load(f)
    manifest.update(status="closed", outcome=a.outcome, note=a.note,
                    closed_at=_now(), frames=len(frames),
                    head=frames[-1]["id"] if frames else None)
    with open(os.path.join(d, "session.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    fails = [fr for fr in frames if fr.get("outcome") == "fail"]
    print(f"{a.session}: {a.outcome} · {len(frames)} frame(s), {len(fails)} fail(s)")
    for fr in fails:
        print(f"  ✗ frame {fr['seq']} [{fr['id']}] {fr['action']} {fr.get('target') or ''}: "
              f"{fr.get('observed') or fr.get('note') or ''}")


def cmd_verify(a):
    frames = _read_frames(a.session)
    prev = None
    for fr in frames:
        if _frame_id(fr) != fr.get("id") or fr.get("prev") != prev:
            sys.exit(f"exhaust drift at seq {fr.get('seq')} — chain broken, do not trust "
                     "frames from here on")
        prev = fr["id"]
    print(f"{a.session}: {len(frames)} frame(s), chain intact")


def cmd_show(a):
    for fr in _read_frames(a.session):
        mark = {"ok": "·", "fail": "✗"}.get(fr.get("outcome"), "?")
        print(f"{mark} {fr['seq']:>3} [{fr['id']}] {fr['at']} {fr['action']}"
              f" {fr.get('target') or ''}"
              + (f"\n      in:  {fr['input']}" if fr.get("input") else "")
              + (f"\n      out: {fr['observed']}" if fr.get("observed") else "")
              + (f"\n      — {fr['note']}" if fr.get("note") else ""))


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start")
    s.add_argument("--intent", required=True)
    s.add_argument("--surface", default=None)
    s.add_argument("--actor", default="claude-autopilot")
    s = sub.add_parser("frame")
    s.add_argument("--session", required=True)
    s.add_argument("--action", required=True)
    s.add_argument("--target", default=None)
    s.add_argument("--input", default=None)
    s.add_argument("--observed", default=None)
    s.add_argument("--outcome", default="ok", choices=["ok", "fail"])
    s.add_argument("--note", default=None)
    s = sub.add_parser("close")
    s.add_argument("--session", required=True)
    s.add_argument("--outcome", required=True, choices=["pass", "fail"])
    s.add_argument("--note", default=None)
    s = sub.add_parser("verify")
    s.add_argument("--session", required=True)
    s = sub.add_parser("show")
    s.add_argument("--session", required=True)
    a = p.parse_args()
    {"start": cmd_start, "frame": cmd_frame, "close": cmd_close,
     "verify": cmd_verify, "show": cmd_show}[a.cmd](a)


if __name__ == "__main__":
    main()
