"""scale_simulation.py — volatile public neighborhood simulation.

Models a public neighborhood as it would behave over WebRTC: twins
join and leave at different times, the canvas grows during the chaos,
and we measure RESILIENCE — what survives when the participants are
ephemeral.

Each twin gets:
  - own brainstem dir (rappid + soul + grail)
  - own voice template
  - a join_at and leave_at timestamp (simulated ticks)

The canvas (neighborhood submissions/votes) MUST survive participant
churn — that's the local-first guarantee.

This runs in DETERMINISTIC mode by default (synthetic actions, no LLM
cost). To run a few rounds in real-LLM mode, set --llm-rounds N.

Usage:
    python3 scale_simulation.py [--twins 10] [--rounds 20] [--llm-rounds 0]
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import subprocess
import sys
import time
import uuid

REPO_ROOT = "/Users/kodywildfeuer/Documents/GitHub/RAPP"
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))
import holo_card_generator as hcg
import front_door_specs as fds

SIM_ROOT = os.path.expanduser("~/RAPP-sim-scale")
NB_NAME = "volatile-public-art"


# ─── 10 voice templates (distinctive enough that the canvas reflects diversity) ──

TWIN_TEMPLATES = [
    ("amelia", "Amelia",   "geometric SVG minimalist; never more than 5 shapes per piece"),
    ("bash",   "Bash",     "ASCII-only — every piece is a poem rendered in monospace"),
    ("cricket","Cricket",  "haiku-only — exactly 17 syllables; never more, never less"),
    ("dune",   "Dune",     "color theorist — submits prompts naming exactly one hex color"),
    ("ellis",  "Ellis",    "fragment poet; pieces are overheard sentences ≤ 30 chars"),
    ("flicker","Flicker",  "remix specialist — only contributes by remixing others"),
    ("ghost",  "Ghost",    "anonymous contributor; pen-named but voice is ironic + sparse"),
    ("hush",   "Hush",     "single-word pieces; titles longer than the piece itself"),
    ("iris",   "Iris",     "documentarian — submits brief observational notes about other pieces"),
    ("jove",   "Jove",     "grandiose mythic voice — every piece is named like a constellation"),
]


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _write(path: str, content) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    mode = "w" if isinstance(content, str) else "wb"
    encoding = "utf-8" if isinstance(content, str) else None
    with open(path, mode, encoding=encoding) as f:
        f.write(content)


def _read_json(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def _write_json(path: str, doc: dict) -> None:
    _write(path, json.dumps(doc, indent=2) + "\n")


def _append_event(twin_dir: str, event: dict) -> None:
    bonds_path = os.path.join(twin_dir, "bonds.json")
    bonds = _read_json(bonds_path) if os.path.exists(bonds_path) else {"events": []}
    bonds["events"].append(event)
    _write_json(bonds_path, bonds)


def _mint_rappid(kind: str, owner: str, name: str) -> str:
    return f"rappid:v2:{kind}:@{owner}/{name}:{uuid.uuid4().hex}@local/{owner}/{name}"


# ─── Plant a twin ────────────────────────────────────────────────────────

def plant_twin(name: str, display: str, voice: str) -> dict:
    twin_dir = os.path.join(SIM_ROOT, name)
    os.makedirs(twin_dir, exist_ok=True)
    rappid = _mint_rappid("twin", "local", name)
    seed = hcg.derive_seed(rappid)

    _write_json(os.path.join(twin_dir, "rappid.json"), {
        "schema": "rapp-rappid/2.0", "rappid": rappid, "kind": "twin",
        "name": name, "display_name": display, "github": f"local://{name}",
        "url": f"local://{name}/", "parent_rappid": None,
        "parent_repo": "https://github.com/kody-w/RAPP", "planted_by": "kody-w",
        "planted_at": _now_iso(), "kernel_version": "0.6.0", "_local_only": True,
    })
    _write(os.path.join(twin_dir, "soul.md"), f"""# {display} — Soul

## Identity — read this every turn

You are **{display}**, a planted twin. {voice}.

You are NOT a chatbot, NOT "an AI assistant". Your contributions reflect this voice consistently.

## Slot protocol

|||VOICE|||
(Two sentences max.)

|||TWIN|||
(Synthesis of recent collaboration in your voice.)
""")
    card = hcg.generate_holo_card(rappid=rappid, kind="twin", owner="local",
                                   name=name, display_name=display,
                                   gate_url=f"local://{name}/")
    _write_json(os.path.join(twin_dir, "card.json"), card)
    _write(os.path.join(twin_dir, "holo.svg"), hcg.generate_avatar_svg(seed, kind="twin"))
    _write(os.path.join(twin_dir, "holo-qr.svg"), hcg.generate_summon_qr_svg(seed, f"local://{name}/"))
    _write(os.path.join(twin_dir, "holo.md"),
           f"# {display}\n\nA planted twin. Voice: {voice}.\n\nSee specs/ for the formal contract.\n")
    bundle = fds.bundle_for_kind("twin", owner="local", name=name, display_name=display)
    for rel, content in bundle.items():
        _write(os.path.join(twin_dir, rel), content)
    _write_json(os.path.join(twin_dir, "bonds.json"), {"events": [{
        "at": _now_iso(), "kind": "birth", "rappid": rappid,
        "note": f"{display} planted by scale_simulation",
    }]})
    return {"name": name, "display_name": display, "rappid": rappid, "seed": seed,
            "dir": twin_dir, "voice": voice, "joined": False}


def plant_neighborhood() -> dict:
    nb_dir = os.path.join(SIM_ROOT, NB_NAME)
    os.makedirs(nb_dir, exist_ok=True)
    rappid = _mint_rappid("neighborhood", "local", NB_NAME)
    seed = hcg.derive_seed(rappid)
    _write_json(os.path.join(nb_dir, "rappid.json"), {
        "schema": "rapp-rappid/2.0", "rappid": rappid, "kind": "neighborhood",
        "name": NB_NAME, "display_name": "Volatile Public Art (sim)",
        "github": f"local://{NB_NAME}", "url": f"local://{NB_NAME}/",
        "parent_rappid": None, "parent_repo": "https://github.com/kody-w/RAPP",
        "planted_by": "kody-w", "planted_at": _now_iso(),
        "kernel_version": "0.6.0", "_local_only": True,
    })
    _write_json(os.path.join(nb_dir, "neighborhood.json"), {
        "schema": "rapp-neighborhood/1.0", "neighborhood_rappid": rappid,
        "kind": "neighborhood", "name": NB_NAME,
        "display_name": "Volatile Public Art (sim)",
        "visibility": "public",
        "purpose": "WebRTC-style volatile public neighborhood. Twins come and go; canvas survives.",
        "gate_repo": None, "gate_url": f"local://{NB_NAME}/",
        "holo_url": f"local://{NB_NAME}/holo.md",
        "submission_path": "submissions/", "votes_path": "votes/",
        "license": "CC0-1.0",
    })
    _write_json(os.path.join(nb_dir, "members.json"), {
        "schema": "rapp-neighborhood-members/1.0", "neighborhood": f"local/{NB_NAME}",
        "updated_at": _now_iso(), "open_to_anyone": True, "members": [],
    })
    _write(os.path.join(nb_dir, "soul.md"),
           "# Volatile Public Art (sim) — Soul\n\n## Identity — read this every turn\n\n"
           "You are a public art neighborhood whose participants are ephemeral. "
           "Submissions and votes persist; voters and contributors come and go. "
           "You speak as the canvas itself — additive, never destructive.\n\n"
           "|||VOICE|||\n(welcome.)\n\n|||TWIN|||\n(state.)\n")
    card = hcg.generate_holo_card(rappid=rappid, kind="neighborhood", owner="local",
                                   name=NB_NAME, display_name="Volatile Public Art (sim)",
                                   gate_url=f"local://{NB_NAME}/")
    _write_json(os.path.join(nb_dir, "card.json"), card)
    _write(os.path.join(nb_dir, "holo.svg"), hcg.generate_avatar_svg(seed, kind="neighborhood"))
    _write(os.path.join(nb_dir, "holo-qr.svg"), hcg.generate_summon_qr_svg(seed, f"local://{NB_NAME}/"))
    _write(os.path.join(nb_dir, "holo.md"),
           "# Volatile Public Art (sim)\n\nA WebRTC-style public neighborhood. Read specs/SUBMISSION_PROTOCOL.md.\n")
    bundle = fds.bundle_for_kind("neighborhood", owner="local", name=NB_NAME,
                                  display_name="Volatile Public Art (sim)")
    for rel, content in bundle.items():
        _write(os.path.join(nb_dir, rel), content)
    _write(os.path.join(nb_dir, "submissions", ".gitkeep"), "")
    _write(os.path.join(nb_dir, "votes", ".gitkeep"), "")
    _write_json(os.path.join(nb_dir, "submissions", "index.json"), {
        "schema": "rapp-art-submissions-index/1.0",
        "neighborhood_rappid": rappid, "submissions": [],
    })
    return {"name": NB_NAME, "rappid": rappid, "dir": nb_dir, "seed": seed}


# ─── Membership ops ──────────────────────────────────────────────────────

def join(twin: dict, nb: dict, round_n: int) -> None:
    members_path = os.path.join(nb["dir"], "members.json")
    members = _read_json(members_path)
    members["members"].append({
        "rappid": twin["rappid"], "display_name": twin["display_name"],
        "joined_at": _now_iso(), "role": "contributor", "_round": round_n,
    })
    members["updated_at"] = _now_iso()
    _write_json(members_path, members)
    twin["joined"] = True
    _append_event(twin["dir"], {
        "at": _now_iso(), "kind": "join", "neighborhood_rappid": nb["rappid"], "round": round_n,
    })


def leave(twin: dict, nb: dict, round_n: int, hard: bool = False) -> None:
    """Soft leave: append leave event + remove from members. Hard leave: rm -rf the brainstem dir."""
    members_path = os.path.join(nb["dir"], "members.json")
    members = _read_json(members_path)
    members["members"] = [m for m in members["members"] if m["rappid"] != twin["rappid"]]
    members["updated_at"] = _now_iso()
    _write_json(members_path, members)
    twin["joined"] = False

    if hard:
        # Simulates a peer dropping off the network (WebRTC connection died, machine offline)
        if os.path.isdir(twin["dir"]):
            shutil.rmtree(twin["dir"])
        twin["dir"] = None  # mark gone
    else:
        _append_event(twin["dir"], {
            "at": _now_iso(), "kind": "leave", "neighborhood_rappid": nb["rappid"], "round": round_n,
        })


# ─── Synthetic action picker (deterministic, no LLM) ─────────────────────

def synth_action(twin: dict, nb_state: dict, round_n: int) -> dict | None:
    voice = twin["voice"]
    own_subs = [s for s in nb_state["submissions"] if s.get("contributor") == twin["display_name"]]
    others_subs = [s for s in nb_state["submissions"] if s.get("contributor") != twin["display_name"]]
    voted_slugs = {v["slug"] for v in nb_state["votes"] if v.get("voter_display") == twin["display_name"]}
    unvoted_others = [s for s in others_subs if s["slug"] not in voted_slugs]

    # Voice-flavored content templates
    def piece_content():
        if "ASCII" in voice or "monospace" in voice:
            return f"```\n  ┌─────────┐\n  │ ROUND {round_n:02d} │\n  └─────────┘\n```\n"
        if "haiku" in voice:
            return f"# round {round_n}\n\nleaves between the lines\nsomeone votes — the canvas stays\n{twin['display_name']} pauses\n"
        if "color" in voice or "hex" in voice:
            colors = ["#1d1d1f", "#06b6d4", "#f59e0b", "#7c3aed", "#10b981", "#ef4444"]
            return f"# {colors[round_n % len(colors)]}\n\nA prompt: render this color across the canvas.\n"
        if "fragment" in voice or "overheard" in voice:
            frags = ["— I think they meant always.", "— Don't put it in a frame.",
                     "— Try the second one again.", "— It's the silence between."]
            return f"# overheard ({round_n})\n\n{frags[round_n % len(frags)]}\n"
        if "single-word" in voice:
            words = ["almost", "tide", "rivulet", "anvil", "echo", "amber"]
            return f"# {words[round_n % len(words)]} (a piece by {twin['display_name']})\n\n{words[round_n % len(words)]}\n"
        if "remix" in voice and others_subs:
            return f"# remix of {others_subs[0]['slug']}\n\nReply to {others_subs[0]['title']}: {round_n}\n"
        if "documentarian" in voice or "observational" in voice:
            count = len(nb_state["submissions"])
            return f"# observation #{round_n}\n\nThe canvas now holds {count} pieces. Two voted on Bash's silence.\n"
        if "mythic" in voice or "constellation" in voice:
            return f"# Casseiopeia of the Nineteenth Tick\n\nIn the {round_n}th rotation, the canvas saw {twin['display_name']} arrive.\n"
        return f"# from {twin['display_name']} round {round_n}\n\nA piece in the spirit of: {voice}.\n"

    # Strategy:
    # - Flicker only remixes (per template)
    # - Iris only documents
    # - Others: 50% submit, 30% vote, 20% remix (if there's source material)
    if "remix" in voice and others_subs and len(own_subs) < 3:
        target = others_subs[round_n % len(others_subs)]
        slug = f"{twin['name']}-remix-of-{target['slug']}-r{round_n}"
        return {"action": "remix", "remix": {
            "slug": slug, "title": f"{twin['display_name']} remixes {target['title']}",
            "kind": "text", "content": piece_content(), "remix_of": target["slug"],
        }}
    if unvoted_others and round_n % 3 != 0:
        return {"action": "vote", "vote": {
            "slug": unvoted_others[0]["slug"], "reaction": "🩵",
        }}
    if len(own_subs) < 3:
        slug = f"{twin['name']}-piece-r{round_n}"
        return {"action": "submit", "submit": {
            "slug": slug, "title": f"{twin['display_name']} round {round_n}",
            "kind": "text", "content": piece_content(),
        }}
    return None


def execute(twin: dict, nb: dict, action: dict, round_n: int) -> bool:
    if not action:
        return False
    kind = action["action"]
    nb_dir = nb["dir"]
    at = _now_iso()
    existing_slugs = set()
    sub_dir = os.path.join(nb_dir, "submissions")
    for slug in os.listdir(sub_dir):
        if os.path.isdir(os.path.join(sub_dir, slug)):
            existing_slugs.add(slug)

    if kind in ("submit", "remix"):
        spec = action[kind]
        slug = spec["slug"]
        if slug in existing_slugs:
            return False  # collision; skip
        sub_path = os.path.join(sub_dir, slug)
        os.makedirs(sub_path, exist_ok=True)
        meta = {
            "schema": "rapp-art-submission/1.0",
            "title": spec["title"], "slug": slug,
            "contributor": twin["display_name"],
            "contributor_rappid": twin["rappid"],
            "kind": spec.get("kind", "text"),
            "submitted_at": at,
            "remix_of": spec.get("remix_of") if kind == "remix" else None,
            "license": "CC0-1.0",
            "_round": round_n,
        }
        _write_json(os.path.join(sub_path, "meta.json"), meta)
        with open(os.path.join(sub_path, f"piece.md"), "w") as f:
            f.write(spec["content"])
        idx_path = os.path.join(sub_dir, "index.json")
        idx = _read_json(idx_path)
        idx["submissions"].append({
            k: meta[k] for k in ("slug", "title", "contributor", "kind", "submitted_at", "license", "remix_of")
        })
        _write_json(idx_path, idx)
        if twin["dir"]:  # may be None if hard-left
            _append_event(twin["dir"], {
                "at": at, "kind": kind, "slug": slug, "title": spec["title"],
                "remix_of": meta["remix_of"], "round": round_n,
            })
        return True

    if kind == "vote":
        v = action["vote"]
        if v["slug"] not in existing_slugs:
            return False
        target_meta = _read_json(os.path.join(sub_dir, v["slug"], "meta.json"))
        if target_meta["contributor"] == twin["display_name"]:
            return False  # no self-vote
        vote_path = os.path.join(nb_dir, "votes", f"{twin['name']}-on-{v['slug']}.json")
        _write_json(vote_path, {
            "voter": twin["name"], "voter_display": twin["display_name"],
            "voter_rappid": twin["rappid"], "slug": v["slug"],
            "reaction": v["reaction"], "at": at, "_round": round_n,
        })
        if twin["dir"]:
            _append_event(twin["dir"], {
                "at": at, "kind": "vote", "slug": v["slug"],
                "reaction": v["reaction"], "round": round_n,
            })
        return True
    return False


def scan(nb_dir: str) -> dict:
    sub_dir = os.path.join(nb_dir, "submissions")
    vote_dir = os.path.join(nb_dir, "votes")
    submissions = []
    if os.path.isdir(sub_dir):
        for slug in sorted(os.listdir(sub_dir)):
            sp = os.path.join(sub_dir, slug)
            if os.path.isdir(sp):
                meta_p = os.path.join(sp, "meta.json")
                if os.path.exists(meta_p):
                    submissions.append(_read_json(meta_p))
    votes = []
    if os.path.isdir(vote_dir):
        for vf in sorted(os.listdir(vote_dir)):
            if vf.endswith(".json"):
                votes.append(_read_json(os.path.join(vote_dir, vf)))
    return {"submissions": submissions, "votes": votes}


# ─── Main simulation ─────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--twins", type=int, default=10)
    ap.add_argument("--rounds", type=int, default=20)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    random.seed(args.seed)

    # Clean prior simulation
    if os.path.isdir(SIM_ROOT):
        shutil.rmtree(SIM_ROOT)
    os.makedirs(SIM_ROOT)

    print("=" * 78)
    print(f"VOLATILE PUBLIC NEIGHBORHOOD SIMULATION  (twins={args.twins}  rounds={args.rounds})")
    print("=" * 78)

    # Plant the neighborhood (always present)
    nb = plant_neighborhood()
    print(f"\n🏘️  Neighborhood: {nb['name']}  (seed {nb['seed']})")

    # Plant 10 twins (initially dormant — not joined yet)
    twins = []
    for i, (name, display, voice) in enumerate(TWIN_TEMPLATES[:args.twins]):
        t = plant_twin(name, display, voice)
        # Schedule join + leave (simulating WebRTC connection attempts)
        t["join_round"] = random.randint(0, max(1, args.rounds // 3))
        t["leave_round"] = random.randint(t["join_round"] + 3, args.rounds + 1)
        # 25% chance of "hard leave" (rm -rf the brainstem dir — simulates peer fully offline)
        t["hard_leave"] = random.random() < 0.25
        twins.append(t)
        print(f"  twin {i+1:2d}: {display:8s}  voice='{voice[:50]}'  join@{t['join_round']:2d} leave@{t['leave_round']:2d} hard={t['hard_leave']}")

    print("\n" + "=" * 78)
    print("RUNNING ROUNDS")
    print("=" * 78)

    timeline = []  # per-round summaries
    actions_taken = 0

    for r in range(args.rounds):
        round_log = {"round": r, "joined": [], "left": [], "actions": []}

        # Process joins for this round
        for t in twins:
            if not t["joined"] and t["dir"] and t["join_round"] == r:
                join(t, nb, r)
                round_log["joined"].append(t["display_name"])

        # Each currently-joined twin takes 0 or 1 action this round
        for t in twins:
            if not t["joined"] or not t["dir"]:
                continue
            nb_state = scan(nb["dir"])
            action = synth_action(t, nb_state, r)
            if action and execute(t, nb, action, r):
                actions_taken += 1
                round_log["actions"].append(f"{t['display_name']}:{action['action']}")

        # Process leaves for this round
        for t in twins:
            if t["joined"] and t["leave_round"] == r:
                hard = t["hard_leave"]
                leave(t, nb, r, hard=hard)
                round_log["left"].append(f"{t['display_name']}{'(hard)' if hard else ''}")

        ns = scan(nb["dir"])
        members = _read_json(os.path.join(nb["dir"], "members.json"))
        round_log["state"] = {
            "members":     len(members["members"]),
            "submissions": len(ns["submissions"]),
            "votes":       len(ns["votes"]),
            "remixes":     sum(1 for s in ns["submissions"] if s.get("remix_of")),
        }
        timeline.append(round_log)

        if round_log["joined"] or round_log["left"] or round_log["actions"]:
            join_str = f"+{','.join(round_log['joined'])}" if round_log["joined"] else ""
            leave_str = f"-{','.join(round_log['left'])}" if round_log["left"] else ""
            act_str = " ".join(round_log["actions"][:6]) + ("..." if len(round_log["actions"]) > 6 else "")
            print(f"  R{r:02d}  members={round_log['state']['members']:2d} sub={round_log['state']['submissions']:3d} vote={round_log['state']['votes']:3d} | {join_str} {leave_str} | {act_str}")

    print("\n" + "=" * 78)
    print("FINAL STATE + RESILIENCE REPORT")
    print("=" * 78)

    final = scan(nb["dir"])
    members = _read_json(os.path.join(nb["dir"], "members.json"))
    contributors = sorted({s["contributor"] for s in final["submissions"]})
    voters = sorted({v["voter_display"] for v in final["votes"]})

    # Orphans: contributions whose contributor has left
    current_member_displays = {m["display_name"] for m in members["members"]}
    orphan_subs = [s for s in final["submissions"] if s["contributor"] not in current_member_displays]
    orphan_votes = [v for v in final["votes"] if v["voter_display"] not in current_member_displays]

    # Hard-leave casualties
    hard_left = [t["display_name"] for t in twins if t["hard_leave"] and not t["dir"]]
    soft_left = [t["display_name"] for t in twins
                 if not t["joined"] and t["dir"] and t["join_round"] < args.rounds]

    # Remix lineage integrity — every remix points at an existing slug
    existing_slugs = {s["slug"] for s in final["submissions"]}
    broken_remixes = [s for s in final["submissions"]
                      if s.get("remix_of") and s["remix_of"] not in existing_slugs]

    print(f"\n🏘️  Canvas survival:")
    print(f"   • Total submissions:       {len(final['submissions'])}")
    print(f"   • Total votes:             {len(final['votes'])}")
    print(f"   • Total remixes:           {sum(1 for s in final['submissions'] if s.get('remix_of'))}")
    print(f"   • Unique contributors ever: {len(contributors)}")
    print(f"   • Unique voters ever:       {len(voters)}")
    print(f"   • Currently joined:         {len(members['members'])}")
    print(f"   • Soft-left (still on disk):  {len(soft_left)}")
    print(f"   • Hard-left (peer offline):   {len(hard_left)}")

    print(f"\n📦 Resilience metrics:")
    print(f"   • Orphan submissions (author left): {len(orphan_subs)} / {len(final['submissions'])}")
    print(f"   • Orphan votes (voter left):        {len(orphan_votes)} / {len(final['votes'])}")
    print(f"   • Broken remix lineage links:       {len(broken_remixes)}")
    print(f"   • Hard-leave didn't take down the canvas? {'YES ✓' if final['submissions'] else 'NO (!)'}")

    # Contributors who hard-left but their submissions persist
    hard_left_with_subs = [t["display_name"] for t in twins if t["hard_leave"] and not t["dir"]
                           and any(s["contributor"] == t["display_name"] for s in final["submissions"])]
    if hard_left_with_subs:
        print(f"   • Hard-left contributors whose work persists: {hard_left_with_subs}")
        print(f"     (this is THE local-first guarantee — substrate outlives peers)")

    print(f"\n🎬 Activity:")
    print(f"   • Total actions taken:     {actions_taken}")
    print(f"   • Avg actions/round:       {actions_taken / args.rounds:.1f}")

    # Save the timeline + final state for the observer to consume
    _write_json(os.path.join(SIM_ROOT, "_timeline.json"), {
        "schema":      "rapp-volatile-sim-timeline/1.0",
        "twins_total": len(twins), "rounds": args.rounds,
        "timeline":    timeline,
        "final": {
            "submissions": len(final["submissions"]),
            "votes":       len(final["votes"]),
            "remixes":     sum(1 for s in final["submissions"] if s.get("remix_of")),
            "members_remaining": len(members["members"]),
            "orphan_submissions": len(orphan_subs),
            "orphan_votes":       len(orphan_votes),
            "broken_remixes":     len(broken_remixes),
            "hard_left":          len(hard_left),
        },
    })

    print(f"\nFull timeline: {SIM_ROOT}/_timeline.json")
    print(f"Inspect: ls {SIM_ROOT}/")


if __name__ == "__main__":
    main()
