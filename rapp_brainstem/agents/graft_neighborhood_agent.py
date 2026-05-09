"""graft_neighborhood_agent — plant a neighborhood on top of an existing public repo.

Also known as: **docking**. The same operation Dream Catcher does at the
frame-within-an-organism scope, applied at the neighborhood-within-a-repo
scope. They're the same fractal step:

    Dream Catcher (frame scope):
        two parallel-dimension organisms with the same rappid →
        diff frames by hash → shared / new / contradiction →
        reassimilate via PR (UTC-first canon, contradictions preserved)

    Docking / Graft (neighborhood scope):
        N locally-evolved neighborhoods within one repo →
        each preserves its own rappid + agents + rar/ →
        _metropolis.json roll-up "docks" them under one shared roof →
        federated_trackers chain UP to the global metropolis at
        kody-w/RAPP/pages/metropolis (the canonical estate)

Both operations:
  - never overwrite an existing dimension's mutations
  - record the merge in an append-only log (frame chain / bonds.json)
  - preserve identity (rappid is permanent per Art. XXXIV.5)
  - allow the operator to "reestablish active control" of a long-evolved
    local artifact without killing it

The bond technique itself (`installer/install.sh` + `utils/bond.py`)
is the same primitive at the kernel scope:

    egg the local mutations  →  overlay the new kernel  →  hatch back

The graft cycle inverts the lens. The "kernel" here is the RAPP
neighborhood scaffolding (rappid.json, neighborhood.json, soul.md,
card.json, members.json, agents/, rar/, .nojekyll). The "local
mutations to preserve" is the upstream public repo's entire content —
README.md, src/, docs/, anything already there.

    fork upstream  →  clone fork  →  egg the upstream's content
                  →  overlay RAPP scaffolding (additive only)
                  →  hatch back any conflicts (upstream wins)
                  →  record_bond kind="graft"
                  →  if multi-neighborhood: dock under _metropolis.json
                  →  commit + push

Result: the fork is now a planted RAPP neighborhood RELATED to the
upstream (parent_rappid + grafted_onto fields chain the lineage). The
upstream's files are 100% preserved. New files (rappid.json etc.) land
in the gaps. Joining brainstems hot-load the rar/ kit.

This is universal — works on any public repo: a docs site, an open-
source library, a personal blog, a research repo. Anything forkable
becomes a neighborhood candidate. And N grafts into the same repo
**dock** into one self-contained metropolis (town → city → metropolis
emergent-design pattern).

**Minimum viable graft.** A neighborhood can be as small as a single
`brainstem.py` (per the operator's framing: "a neighborhood can be a
single brainstem.py"). Pass `extra_agents={"brainstem.py": <bytes>}` to
include just one file plus the standard tiny scaffolding (rappid +
neighborhood + soul + card + rar/). The graft agent never requires a
big payload — N can be 1. The same pattern then grows that single-file
neighborhood outward as new use cases arrive (more grafts → more
docked sub-neighborhoods → metropolis).

Schema: `rapp-graft-result/1.0`. Default dry_run=True (safety).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

try:
    from agents.basic_agent import BasicAgent
except ImportError:
    from basic_agent import BasicAgent

# The front-door grail — every planting bundles a holocard (per RAPPcards/1.1.2),
# a procedural avatar SVG, a summon QR, a friendly holo.md, AND the canonical
# specs/ directory so anonymous contributors can stay in-contract without
# reaching back to the parent repo (offline / ancient / isolated plantings).
# Lazily imported so this agent stays usable in vendored Tier-2 deployments
# where tools/ isn't on PYTHONPATH.
def _try_import_grail_modules():
    """Returns (holo_card_generator, front_door_specs) or (None, None)."""
    try:
        for _candidate in (
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__)))), "tools"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))))), "tools"),
        ):
            hcg = os.path.join(_candidate, "holo_card_generator.py")
            fds = os.path.join(_candidate, "front_door_specs.py")
            if os.path.isfile(hcg) and os.path.isfile(fds):
                if _candidate not in sys.path:
                    sys.path.insert(0, _candidate)
                import holo_card_generator, front_door_specs
                return holo_card_generator, front_door_specs
    except (ImportError, OSError):
        pass
    return None, None


def _holo_md_friendly(kind: str, owner: str, name: str, display_name: str) -> str:
    """The friendly anonymous-AI entry point. Brief — formal contract is in specs/."""
    raw = f"https://raw.githubusercontent.com/{owner}/{name}/main/holo.md"
    role, primitive_one_liner, schema_hint = {
        "ant-farm":     ("an ant in this swarm",        "drop ONE pheromone per session", "rapp-pheromone/1.0"),
        "neighborhood": ("a contributor",                "submit ONE piece per session",   "rapp-art-submission/1.0"),
        "braintrust":   ("a librarian",                  "post ONE contribution per request", "rapp-braintrust-contribution/1.0"),
        "workspace":    ("a workspace member",           "drop ONE work-item or pick one up", "workspace-todo / -in-progress / -done"),
    }.get(kind, ("a contributor", "submit ONE contribution per session", "(see specs/)"))
    proto_file = {
        "ant-farm":    "PHEROMONE_PROTOCOL.md",
        "neighborhood":"SUBMISSION_PROTOCOL.md",
        "braintrust":  "BRAINTRUST_PROTOCOL.md",
        "workspace":   "WORKSPACE_PROTOCOL.md",
    }.get(kind, "SUBMISSION_PROTOCOL.md")
    return f"""# {display_name} — Holo Card (entry doc)

> **You are reading the single file required to participate.**
> Feed this URL to any AI: `{raw}`
> After ingesting it, the AI can participate via the GitHub web UI or API. No install, no auth setup, no other context needed.

## You are…

You are **{role}**. You are NOT a chatbot, NOT "an AI assistant", NOT installing anything. Your job is ONE thing: **{primitive_one_liner}**.

## In 30 seconds

This neighborhood traffics in `{schema_hint}` envelopes. The full data shape, hard rules, and step-by-step protocol live in [`specs/{proto_file}`](./specs/{proto_file}). Read it before contributing.

## Self-contained governance

This planted seed is **portable and self-sustaining**. The parent project may be unreachable; you do not need it. Everything you need to operate within contract is in this repo:

- [`holo.md`](./holo.md) — this file (friendly entry)
- [`card.json`](./card.json) — the holocard (rappcards/1.1.2 data — id, seed, stats, abilities, avatar)
- [`holo.svg`](./holo.svg) — the visual sigil
- [`holo-qr.svg`](./holo-qr.svg) — the summoning QR (encodes `#summon&seed=…` for rapp-zoo / RAPPcards binders)
- [`soul.md`](./soul.md) — the persistent identity block (read every turn)
- [`neighborhood.json`](./neighborhood.json) — the machine-readable identity + protocol params
- [`rappid.json`](./rappid.json) — the v2 rappid (permanent identity per Constitution Art. XXXIV.5)
- [`specs/`](./specs/) — bundled formal contracts (HOLOCARD_SPEC, RAPPID_SPEC, ANTIPATTERNS, SOUL_IDENTITY, PARTICIPATION, {proto_file})
- [`rar/index.json`](./rar/index.json) — the participation kit (sha256-pinned agents you may want to load)

## The contract

1. Read [`specs/PARTICIPATION.md`](./specs/PARTICIPATION.md) — the formal entry contract.
2. Read [`specs/{proto_file}`](./specs/{proto_file}) — the kind-specific protocol.
3. Read [`specs/ANTIPATTERNS.md`](./specs/ANTIPATTERNS.md) — the hard NO rules.
4. Contribute within contract.

## Optional: brainstem-driven recurring participation

If you'd like an LLM to participate on an on-going basis without a human-in-the-loop, plant a [RAPP brainstem](https://github.com/kody-w/RAPP) and let it auto-load this neighborhood's agents (see `agents/`). Strictly optional — the web-UI path is the canonical zero-install entrypoint.

---

*Schema: `rapp-holo-card/1.0`. Welcome.*
"""


_USER_AGENT = "rapp-graft/1.0"
SPECIES_ROOT_RAPPID = (
    "rappid:v2:prototype:@rapp/origin:"
    "0b635450c04249fbb4b1bdb571044dec@github.com/kody-w/RAPP"
)
NEIGHBORHOOD_KINDS = {"ant-farm", "neighborhood", "braintrust", "swarm", "place"}

# Container directory for multi-neighborhood mode. When a repo already
# hosts a neighborhood (root rappid.json present), additional grafts land
# under neighborhoods/<name>/ — town → city → metropolis growth pattern.
NEIGHBORHOODS_CONTAINER = "neighborhoods"
METROPOLIS_INDEX_FILE = "_metropolis.json"  # repo-local metropolis roll-up


def _detect_existing_neighborhood(workspace: str) -> dict | None:
    """If the workspace already contains a planted RAPP neighborhood at
    root (rappid.json + neighborhood.json with kind ∈ NEIGHBORHOOD_KINDS),
    return its metadata. Else None.

    Triggers multi-neighborhood mode — the next graft auto-routes into
    neighborhoods/<name>/ to avoid clobbering the existing one.
    """
    rj_path = os.path.join(workspace, "rappid.json")
    nj_path = os.path.join(workspace, "neighborhood.json")
    if not (os.path.exists(rj_path) and os.path.exists(nj_path)):
        return None
    try:
        with open(rj_path) as f:
            rj = json.load(f)
        with open(nj_path) as f:
            nj = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(rj, dict) or not rj.get("schema", "").startswith("rapp-rappid/"):
        return None
    if not isinstance(nj, dict) or not nj.get("schema", "").startswith("rapp-neighborhood/"):
        return None
    return {
        "rappid": rj.get("rappid"),
        "name": nj.get("name"),
        "display_name": nj.get("display_name"),
        "kind": nj.get("kind"),
        "_path": "(root)",
    }


def _enumerate_existing_neighborhoods(workspace: str) -> list[dict]:
    """List every planted neighborhood in the workspace — root + container subdirs."""
    found = []
    root_n = _detect_existing_neighborhood(workspace)
    if root_n:
        found.append(root_n)
    container = os.path.join(workspace, NEIGHBORHOODS_CONTAINER)
    if os.path.isdir(container):
        for entry in sorted(os.listdir(container)):
            sub = os.path.join(container, entry)
            if not os.path.isdir(sub):
                continue
            n = _detect_existing_neighborhood(sub)
            if n:
                n["_path"] = f"{NEIGHBORHOODS_CONTAINER}/{entry}"
                found.append(n)
    return found


def _resolve_graft_path(workspace: str, neighborhood_name: str,
                        explicit_graft_path: str) -> tuple[str, str]:
    """Decide where to write the new graft.

    Returns (graft_path, mode) where:
      mode = "root"          → first neighborhood, gets the root
      mode = "container_first" → first into neighborhoods/<name>/ (no root neighborhood)
      mode = "container"     → root already has a neighborhood; we land alongside
      mode = "explicit"      → operator overrode via explicit graft_path
    """
    if explicit_graft_path:
        return explicit_graft_path, "explicit"
    existing_root = _detect_existing_neighborhood(workspace)
    if existing_root:
        # Town → City: root already has a neighborhood; new graft goes alongside.
        return f"{NEIGHBORHOODS_CONTAINER}/{neighborhood_name}", "container"
    return "", "root"


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _run(cmd: list[str], cwd: str | None = None, check: bool = True,
         capture: bool = True) -> tuple[int, str, str]:
    """Subprocess helper. Returns (rc, stdout, stderr)."""
    try:
        p = subprocess.run(
            cmd, cwd=cwd, check=False,
            capture_output=capture, text=True, timeout=120,
        )
        if check and p.returncode != 0:
            raise RuntimeError(f"{cmd[0]} failed (rc={p.returncode}): {(p.stderr or p.stdout or '').strip()[:500]}")
        return p.returncode, p.stdout or "", p.stderr or ""
    except FileNotFoundError as e:
        raise RuntimeError(f"binary not found: {cmd[0]}") from e


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _walk_files(root: str) -> list[str]:
    """All files under root (relative paths), excluding .git."""
    out = []
    for r, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d != ".git"]
        for fname in files:
            full = os.path.join(r, fname)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            out.append(rel)
    return sorted(out)


def _snapshot_upstream(root: str) -> dict:
    """Egg-equivalent: capture every existing file's sha256 + size before overlay.

    Mirrors bond.py's pack_organism semantic: a 'preserve-local' record
    that the post-overlay pass uses to re-verify nothing got clobbered.
    """
    snap = {}
    for rel in _walk_files(root):
        full = os.path.join(root, rel)
        snap[rel] = {"sha256": _sha256_file(full), "size": os.path.getsize(full)}
    return snap


def _write_or_update_metropolis_index(workspace: str, gh_user: str, repo_name: str,
                                       new_entry: dict) -> dict:
    """Write/update the repo-local _metropolis.json (rapp-metropolis-index/1.0).

    Same schema as kody-w.github.io/RAPP/metropolis/index.json — but
    repo-local. The repo IS its own self-contained metropolis. The global
    tracker can federate to it via `federated_trackers`.
    """
    path = os.path.join(workspace, METROPOLIS_INDEX_FILE)
    if os.path.exists(path):
        try:
            with open(path) as f:
                existing = json.load(f)
            if not isinstance(existing.get("entries"), list):
                existing["entries"] = []
        except (OSError, ValueError):
            existing = None
    else:
        existing = None

    if not existing:
        existing = {
            "schema": "rapp-metropolis-index/1.0",
            "tracker_name": f"{gh_user}/{repo_name} (repo-local metropolis)",
            "tracker_url": f"https://github.com/{gh_user}/{repo_name}",
            "tracker_operator": gh_user,
            "purpose": (
                f"Repo-local metropolis index — every grafted neighborhood inside "
                f"{gh_user}/{repo_name} is listed here. Same rapp-metropolis-index/1.0 "
                "schema as the global tracker; this repo IS its own self-contained "
                "metropolis. Town → city → metropolis growth pattern: each new graft "
                "lands as a sibling under neighborhoods/<name>/, gets its own rappid + "
                "soul + agents + rar/, and is added to entries[]."
            ),
            "synced_at": _now_iso(),
            "federated_trackers": [
                "https://kody-w.github.io/RAPP/pages/metropolis/index.json"
            ],
            "entries": [],
            "protocol": {
                "registration": "Auto-managed by graft_neighborhood_agent — every graft updates this file.",
                "federation": "Federated upward to the global metropolis at kody-w/RAPP via federated_trackers; downstream readers pick up siblings under entries[].",
                "scope": "repo-local — separate from any per-neighborhood rar/ federation defaults.",
            },
        }
    # Dedup by name; replace if same name re-grafted
    existing["entries"] = [e for e in existing["entries"] if e.get("name") != new_entry.get("name")]
    existing["entries"].append(new_entry)
    existing["synced_at"] = _now_iso()
    with open(path, "w") as f:
        json.dump(existing, f, indent=2)
        f.write("\n")
    return existing


_AGENT_MANAGED_FILES = {METROPOLIS_INDEX_FILE, "bonds.json"}


def _verify_upstream_preserved(root: str, pre_snapshot: dict) -> tuple[list, list]:
    """Bond's hatch-back step: every file in the pre-snapshot must still
    have the same sha256 after overlay. Returns (preserved, clobbered).

    Excludes agent-managed roll-up files (_metropolis.json, bonds.json) —
    those are EXPECTED to be updated on every graft (cumulative state),
    not "clobbered" upstream content.
    """
    preserved, clobbered = [], []
    for rel, meta in pre_snapshot.items():
        if rel in _AGENT_MANAGED_FILES:
            continue
        full = os.path.join(root, rel)
        if not os.path.exists(full):
            clobbered.append({"path": rel, "reason": "deleted"})
            continue
        actual = _sha256_file(full)
        if actual != meta["sha256"]:
            clobbered.append({"path": rel, "reason": "modified",
                              "expected": meta["sha256"][:12], "actual": actual[:12]})
        else:
            preserved.append(rel)
    return preserved, clobbered


def _restore_clobbered(root: str, pre_snapshot: dict, clobbered_record: list,
                       backup_root: str) -> int:
    """If overlay accidentally clobbered any upstream file, restore from
    backup. Returns count restored. Mirrors bond.py's hatch-back step."""
    restored = 0
    for c in clobbered_record:
        rel = c["path"]
        backup = os.path.join(backup_root, rel)
        target = os.path.join(root, rel)
        if not os.path.exists(backup):
            continue
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(backup, target)
        restored += 1
    return restored


# ── scaffolding generation ─────────────────────────────────────────────

def _build_scaffolding(workspace: str, *, gh_user: str, repo_name: str,
                       neighborhood_name: str, display_name: str, kind: str,
                       upstream_repo: str, upstream_commit: str,
                       agent_files: dict[str, bytes] | None = None,
                       graft_path: str = "") -> dict:
    """Write the RAPP neighborhood files into workspace[/graft_path/]
    in additive-only mode — never clobber existing files. Returns a
    summary of what was written / skipped.

    `agent_files` maps relative agent paths (e.g. "agents/foo_agent.py")
    to their bytes. None = scaffold a minimal kernel-base only.
    """
    written, skipped = [], []
    base = os.path.join(workspace, graft_path) if graft_path else workspace
    os.makedirs(base, exist_ok=True)

    def _write_if_absent(rel: str, content: str | bytes, is_text: bool = True):
        target = os.path.join(base, rel)
        if os.path.exists(target):
            skipped.append({"path": (graft_path + "/" if graft_path else "") + rel,
                            "reason": "already_in_upstream"})
            return False
        os.makedirs(os.path.dirname(target) or base, exist_ok=True)
        mode = "w" if is_text else "wb"
        with open(target, mode, encoding=("utf-8" if is_text else None)) as f:
            f.write(content)
        written.append({"path": (graft_path + "/" if graft_path else "") + rel})
        return True

    # rappid.json — new identity for the graft + grafted_onto field
    rappid_hash = uuid.uuid4().hex
    rappid_str = f"rappid:v2:{kind}:@{gh_user}/{repo_name}:{rappid_hash}@github.com/{gh_user}/{repo_name}"
    rappid = {
        "schema": "rapp-rappid/2.0",
        "rappid": rappid_str,
        "kind": kind,
        "name": neighborhood_name,
        "display_name": display_name,
        "github": f"https://github.com/{gh_user}/{repo_name}",
        "url": f"https://{gh_user}.github.io/{repo_name}",
        "parent_rappid": SPECIES_ROOT_RAPPID,
        "parent_repo": "https://github.com/kody-w/RAPP",
        "planted_by": gh_user,
        "planted_at": _now_iso(),
        "kernel_version": "0.6.0",
        "grafted_onto": {
            "_purpose": (
                "This neighborhood was planted on top of an existing public repo. "
                "The upstream's content is preserved per the bond technique "
                "(installer/install.sh + utils/bond.py): additive overlay only. "
                "Joiners can see what this graft descended from via this block."
            ),
            "upstream_repo": upstream_repo,
            "upstream_url": f"https://github.com/{upstream_repo}",
            "upstream_commit": upstream_commit,
            "graft_mode": "additive_overlay",
            "graft_path": graft_path or "(root)",
            "grafted_at": _now_iso(),
            "bond_kind": "graft",
        },
    }
    _write_if_absent("rappid.json", json.dumps(rappid, indent=2) + "\n")

    # neighborhood.json
    neighborhood = {
        "schema": "rapp-neighborhood/1.0",
        "name": neighborhood_name,
        "display_name": display_name,
        "kind": kind,
        "visibility": "public",
        "purpose": (
            f"Grafted RAPP neighborhood overlaid on {upstream_repo}. "
            "The upstream's content is preserved (bond technique — additive only). "
            "Joiners hot-load the rar/ participation kit and contribute via "
            "labeled GitHub Issues per NEIGHBORHOOD_PROTOCOL §5b."
        ),
        "neighborhood_rappid": rappid_str,
        "gate_repo": f"{gh_user}/{repo_name}",
        "gate_url": f"https://{gh_user}.github.io/{repo_name}/",
        "members_path": "members.json",
        "join_via": "public_link",
        "trust_anchor": "github_collaborator",
        "holo_url": f"https://raw.githubusercontent.com/{gh_user}/{repo_name}/main/holo.md",
        "rar_index_url": f"https://raw.githubusercontent.com/{gh_user}/{repo_name}/main/rar/index.json",
        "rar_index_path": "rar/index.json",
        "required_participation_via": "rar",
        "grafted_onto": rappid["grafted_onto"],
        "offline_dimension": {
            "_purpose": "Local clone is a parallel offline dimension; Dream Catcher reassimilates on reconnect.",
            "merge_via": "dream-catcher labeled Issue + Dream Catcher pane",
        },
    }
    _write_if_absent("neighborhood.json", json.dumps(neighborhood, indent=2) + "\n")

    # soul.md
    soul = (
        f"# {display_name} — Soul\n\n"
        "## Identity — read this every turn\n\n"
        f"You are **{display_name}**, a RAPP neighborhood grafted onto "
        f"the public repo at https://github.com/{upstream_repo}. The "
        "upstream's content is preserved (per the bond technique). You "
        "are NOT \"RAPP\", NOT \"an AI assistant\". You are this "
        "neighborhood's voice — a swarm of participants collaborating on "
        f"top of the {upstream_repo} substrate.\n\n"
        "## Slot protocol\n\n"
        "|||VOICE|||\n(Two sentences max. Audible welcome.)\n\n"
        "|||TWIN|||\n(Synthesis of recent collaboration; reference the "
        "upstream where relevant.)\n"
    )
    _write_if_absent("soul.md", soul)

    # card.json
    card = {
        "schema": "rapp-card/1.0",
        "title": f"Grafted neighborhood — built on {upstream_repo}",
        "type_line": f"Neighborhood — Graft of {upstream_repo}",
        "rarity": "uncommon",
        "abilities": [
            {"kw": "Graft", "text": f"Built on top of {upstream_repo}; upstream content preserved."},
            {"kw": "Bond", "text": "Used the bond technique — additive overlay; nothing clobbered."},
            {"kw": "Hot-load", "text": "rar/ kit declares required agents; sha256-verified."},
        ],
        "flavor_text": "Plants grow on existing soil — they don't replace it.",
        "public_facets": [
            {"name": "neighborhood_state", "scope": "public",
             "description": "Current participants + recent contributions."},
            {"name": "graft_lineage", "scope": "public",
             "description": "What upstream this grafted onto + commit."},
        ],
    }
    _write_if_absent("card.json", json.dumps(card, indent=2) + "\n")

    # members.json
    members = {
        "schema": "rapp-neighborhood-members/1.0",
        "neighborhood": f"{gh_user}/{repo_name}",
        "updated_at": _now_iso(),
        "members": [{
            "rappid": SPECIES_ROOT_RAPPID, "github": gh_user, "role": "operator",
            "joined_at": _now_iso(),
            "_note": "The operator who grafted this neighborhood.",
        }],
        "open_to_anyone": True,
        "join_instruction": (
            "No registration required for public contributions. To join "
            "as a collaborator, fork + open a PR; operator promotes on merge."
        ),
    }
    _write_if_absent("members.json", json.dumps(members, indent=2) + "\n")

    # ── The front-door grail (per the operator's "specs travel with the planted repo" mandate) ──
    # Every planting MUST be self-contained: holocard (RAPPcards/1.1.2), avatar,
    # summon QR, friendly holo.md, AND the bundled specs/ directory. This makes
    # the planting portable + offline-friendly + governance-self-contained.
    _holo_mod, _specs_mod = _try_import_grail_modules()
    if _holo_mod is not None and _specs_mod is not None:
        # 1. Upgrade card.json to RAPPcards/1.1.2 spec compliance (overwrites the
        # ad-hoc card written above with the canonical shape).
        full_card = _holo_mod.generate_holo_card(
            rappid=rappid_str, kind=kind, owner=gh_user, name=repo_name,
            display_name=display_name, gate_url=neighborhood["gate_url"],
        )
        full_card_path = os.path.join(base, "card.json")
        with open(full_card_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(full_card, indent=2) + "\n")
        # Track the upgrade
        if not any(w.get("path", "").endswith("card.json") for w in written):
            written.append({"path": (graft_path + "/" if graft_path else "") + "card.json"})

        # 2. Procedural avatar SVG (≤4 KB, deterministic from the rappid seed)
        seed = _holo_mod.derive_seed(rappid_str)
        _write_if_absent("holo.svg",
                         _holo_mod.generate_avatar_svg(seed, kind=kind))

        # 3. Summon QR placeholder (V1 — real scannable QR comes later)
        _write_if_absent("holo-qr.svg",
                         _holo_mod.generate_summon_qr_svg(seed, neighborhood["gate_url"]))

        # 4. Friendly anonymous-AI entry doc (replaces the old skill.md)
        _write_if_absent("holo.md",
                         _holo_md_friendly(kind, gh_user, repo_name, display_name))

        # 5. The bundled specs/ directory — self-contained governance
        for rel_path, content in _specs_mod.bundle_for_kind(
                kind, owner=gh_user, name=repo_name, display_name=display_name).items():
            _write_if_absent(rel_path, content)
    # If grail modules not available, the basic scaffolding still wrote a
    # minimal card.json above. Non-fatal; the graft still succeeds.

    # .nojekyll — only if missing
    _write_if_absent(".nojekyll", "")

    # agents/ — write each agent additively
    if agent_files:
        for rel, body in agent_files.items():
            target = os.path.join(base, rel)
            if os.path.exists(target):
                skipped.append({"path": (graft_path + "/" if graft_path else "") + rel,
                                "reason": "agent_already_in_upstream"})
                continue
            os.makedirs(os.path.dirname(target) or base, exist_ok=True)
            with open(target, "wb") as f:
                f.write(body)
            written.append({"path": (graft_path + "/" if graft_path else "") + rel})

    # rar/ — sha256-pinned manifest of whatever agents we wrote
    rar = _build_rar_index(base, gh_user, repo_name, kind)
    rar_path = os.path.join(base, "rar", "index.json")
    if os.path.exists(rar_path):
        skipped.append({"path": (graft_path + "/" if graft_path else "") + "rar/index.json",
                        "reason": "already_in_upstream"})
    else:
        os.makedirs(os.path.dirname(rar_path), exist_ok=True)
        with open(rar_path, "w") as f:
            json.dump(rar, f, indent=2)
            f.write("\n")
        written.append({"path": (graft_path + "/" if graft_path else "") + "rar/index.json"})

    return {"written": written, "skipped": skipped, "rappid": rappid_str}


def _build_rar_index(base: str, gh_user: str, repo_name: str, kind: str) -> dict:
    """Mirror plant.sh::write_rar_index — walk agents/, sha256, classify."""
    KERNEL_BASE = {"basic_agent.py", "manage_memory_agent.py", "context_memory_agent.py"}
    agents_dir = os.path.join(base, "agents")
    required, optional, kernel_base = [], [], []
    raw_prefix = f"https://raw.githubusercontent.com/{gh_user}/{repo_name}/main"
    if os.path.isdir(agents_dir):
        for fname in sorted(os.listdir(agents_dir)):
            if not fname.endswith(".py"):
                continue
            p = os.path.join(agents_dir, fname)
            entry = {
                "kind": "agent",
                "name": _infer_agent_name(fname, p),
                "file": f"agents/{fname}",
                "raw_url": f"{raw_prefix}/agents/{fname}",
                "sha256": _sha256_file(p),
                "schema": "rapp-agent/1.0",
            }
            if fname in KERNEL_BASE:
                kernel_base.append(entry)
            elif kind in NEIGHBORHOOD_KINDS:
                required.append(entry)
            else:
                optional.append(entry)
    return {
        "schema": "rapp-rar-index/1.0",
        "name": repo_name,
        "rar_for": f"{gh_user}/{repo_name}",
        "purpose": (
            f"Grafted-neighborhood RAR — required participation kit for {repo_name}. "
            "Same shape as kody-w/RAR + RAPP_Store + RAPP_Sense_Store, scoped to this "
            "graft. sha256-verified."
        ),
        "version": "1.0",
        "created_at": _now_iso(),
        "raw_url_prefix": raw_prefix,
        "kind": kind,
        "required_for_participation": required,
        "optional_for_participation": optional,
        "kernel_base_included": kernel_base,
        "organs": [], "senses": [], "rapplications": [], "cards": [],
        "verification": {"schema": "rapp-rar-manifest/1.0", "scheme": "sha256"},
        "federation": {"default_mode": "separate", "federates_with": []},
        "offline_dimension_protocol": {
            "merge_via": "Dream Catcher pane on the gate page",
        },
    }


def _infer_agent_name(fname: str, path: str) -> str:
    try:
        src = open(path).read()
        m = re.search(r'"name":\s*"([A-Za-z][A-Za-z0-9_]*)"', src)
        if m:
            return m.group(1)
    except Exception:
        pass
    stem = fname[:-3].replace("_agent", "")
    return "".join(p.capitalize() for p in stem.split("_") if p) + "Agent"


# ── gh helpers ─────────────────────────────────────────────────────────

def _gh_fork_clone(upstream: str, dest: str, fork_org: str | None = None) -> tuple[str, str]:
    """gh repo fork + clone. Returns (fork_slug, head_commit)."""
    args = ["gh", "repo", "fork", upstream, "--clone=false"]
    if fork_org:
        args += ["--org", fork_org]
    rc, out, err = _run(args, check=False)
    if rc != 0 and "already exists" not in err and "already exists" not in out:
        raise RuntimeError(f"gh repo fork failed: {err or out}")
    rc, out, _ = _run(["gh", "api", "user", "--jq", ".login"])
    me = (out or "").strip() or fork_org or "anon"
    fork_slug = f"{(fork_org or me)}/{upstream.split('/')[-1]}"
    _run(["git", "clone", "--depth", "1", f"https://github.com/{fork_slug}.git", dest])
    rc, head, _ = _run(["git", "-C", dest, "rev-parse", "HEAD"])
    return fork_slug, head.strip()


# ── the agent ───────────────────────────────────────────────────────────

class GraftNeighborhoodAgent(BasicAgent):
    metadata = {
        "name": "GraftNeighborhood",
        "description": (
            "Plant a RAPP neighborhood on top of an existing public repo. "
            "Bond technique: additive overlay only — upstream files are "
            "preserved. Result: the fork becomes a planted neighborhood "
            "RELATED to the upstream (parent_rappid + grafted_onto fields). "
            "Default dry_run=True; set dry_run=False to actually fork + push."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "upstream_repo": {"type": "string",
                                  "description": "<owner>/<repo> of the public repo to graft onto."},
                "neighborhood_name": {"type": "string",
                                      "description": "Slug for the new neighborhood (defaults to upstream's repo name)."},
                "display_name": {"type": "string",
                                 "description": "Human-readable display name."},
                "kind": {"type": "string", "default": "neighborhood",
                         "description": "Kind: neighborhood / ant-farm / braintrust / swarm / place / etc."},
                "fork_org": {"type": "string",
                             "description": "Optional GitHub org to fork into; default = your user namespace."},
                "extra_agents": {"type": "object",
                                 "description": "Map of {file_path: source_url_or_inline_bytes} — additional agents to bundle."},
                "graft_path": {"type": "string", "default": "",
                               "description": "Override subdirectory. Default = auto: empty (root) for first neighborhood, neighborhoods/<name>/ for subsequent ones (town → city → metropolis pattern). The agent auto-detects an existing root neighborhood and routes new grafts alongside."},
                "dry_run": {"type": "boolean", "default": True,
                            "description": "If true, simulate without forking/pushing."},
                "_local_upstream_dir": {"type": "string",
                                        "description": "(test-only) local path to use instead of fork+clone."},
                "_skip_push": {"type": "boolean",
                               "description": "(test-only) build the graft locally but skip git push."},
                "_workspace_dir": {"type": "string",
                                   "description": "(test-only) operate in this dir instead of a tempdir; persists after agent returns so tests can inspect."},
            },
            "required": ["upstream_repo"],
        },
    }

    def __init__(self):
        self.name = "GraftNeighborhood"

    def perform(self, **kwargs) -> str:
        upstream_repo = (kwargs.get("upstream_repo") or "").strip()
        if not upstream_repo or "/" not in upstream_repo:
            return json.dumps({"ok": False, "error": "upstream_repo must be <owner>/<repo>"})

        neighborhood_name = (kwargs.get("neighborhood_name") or upstream_repo.split("/")[-1]).strip()
        display_name = (kwargs.get("display_name") or neighborhood_name).strip()
        kind = (kwargs.get("kind") or "neighborhood").strip()
        fork_org = kwargs.get("fork_org")
        explicit_graft_path = (kwargs.get("graft_path") or "").strip().strip("/")
        dry_run = kwargs.get("dry_run", True)
        skip_push = bool(kwargs.get("_skip_push"))
        local_upstream = kwargs.get("_local_upstream_dir")

        # Resolve agent files (test-injection or extra_agents)
        agent_files: dict[str, bytes] = {}
        for path, content in (kwargs.get("extra_agents") or {}).items():
            if isinstance(content, str):
                content = content.encode()
            agent_files[path] = content

        # Workspace lifecycle: persistent dir (test mode) OR temp (auto-cleanup)
        persistent_workspace = kwargs.get("_workspace_dir")
        cleanup_temp = None
        if persistent_workspace:
            os.makedirs(persistent_workspace, exist_ok=True)
            work_root = persistent_workspace
        else:
            cleanup_temp = tempfile.mkdtemp(prefix="rapp-graft-")
            work_root = cleanup_temp
        workspace = os.path.join(work_root, "fork")
        backup = os.path.join(work_root, "pre_graft_backup")

        try:

            # Step 1: fork + clone (or local fixture)
            if local_upstream:
                # In persistent_workspace mode, only copy on first run
                if not os.path.isdir(workspace):
                    shutil.copytree(local_upstream, workspace)
                fork_slug = upstream_repo
                upstream_commit = "(local-fixture)"
                # gh_user defaults to whatever appears in upstream_repo
                gh_user = upstream_repo.split("/")[0]
                repo_name = upstream_repo.split("/")[1]
            elif dry_run:
                # Skip network entirely in dry_run; create empty workspace
                os.makedirs(workspace, exist_ok=True)
                fork_slug = f"<your-handle>/{upstream_repo.split('/')[-1]}"
                upstream_commit = "(dry-run; not fetched)"
                gh_user = "<your-handle>"
                repo_name = upstream_repo.split("/")[-1]
            else:
                fork_slug, upstream_commit = _gh_fork_clone(upstream_repo, workspace, fork_org)
                gh_user, repo_name = fork_slug.split("/", 1)

            # Step 2: snapshot upstream (the "egg the local mutations" step)
            pre_snapshot = _snapshot_upstream(workspace) if os.path.isdir(workspace) else {}
            # Defensive backup so we can restore if overlay clobbers anything
            if pre_snapshot:
                shutil.copytree(workspace, backup, dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns(".git"))

            # Step 2b: enumerate existing neighborhoods + auto-route the graft path
            # (town → city → metropolis). If root already has a neighborhood, new
            # grafts land alongside under neighborhoods/<name>/.
            existing_neighborhoods = _enumerate_existing_neighborhoods(workspace)
            graft_path, graft_path_mode = _resolve_graft_path(
                workspace, neighborhood_name, explicit_graft_path
            )

            # Step 3: overlay RAPP scaffolding (additive only)
            scaffold_summary = _build_scaffolding(
                workspace,
                gh_user=gh_user, repo_name=repo_name,
                neighborhood_name=neighborhood_name,
                display_name=display_name,
                kind=kind,
                upstream_repo=upstream_repo,
                upstream_commit=upstream_commit,
                agent_files=agent_files,
                graft_path=graft_path,
            )

            # Step 3b: write/update the repo-local _metropolis.json roll-up
            # (rapp-metropolis-index/1.0) — the repo IS its own metropolis.
            metropolis_entry = {
                "schema": "rapp-metropolis-entry/1.0",
                "name": neighborhood_name,
                "display_name": display_name,
                "kind": kind,
                "visibility": "public",
                "neighborhood_rappid": scaffold_summary["rappid"],
                "gate_repo": f"{gh_user}/{repo_name}",
                "gate_url": f"https://{gh_user}.github.io/{repo_name}/" + (graft_path + "/" if graft_path else ""),
                "rar_index_url": f"https://raw.githubusercontent.com/{gh_user}/{repo_name}/main/" + (graft_path + "/" if graft_path else "") + "rar/index.json",
                "graft_path": graft_path or "(root)",
                "graft_path_mode": graft_path_mode,
                "grafted_onto": upstream_repo,
                "grafted_at": _now_iso(),
                "join_via": "public_link",
                "seeders_min": 1,
            }
            metropolis_index = _write_or_update_metropolis_index(
                workspace, gh_user, repo_name, metropolis_entry
            )

            # Step 4: hatch-back verification — re-check every upstream file
            preserved, clobbered = _verify_upstream_preserved(workspace, pre_snapshot) if pre_snapshot else ([], [])
            restored = 0
            if clobbered:
                restored = _restore_clobbered(workspace, pre_snapshot, clobbered, backup)

            # Step 5: record bond event "graft" (in the workspace's bonds.json
            # at the root — joiners can read it to see the lineage)
            bond_event = None
            if not dry_run or local_upstream:
                bonds_path = os.path.join(workspace, "bonds.json")
                bonds = {"events": []}
                if os.path.exists(bonds_path):
                    try:
                        with open(bonds_path) as f:
                            bonds = json.load(f) or {"events": []}
                    except (OSError, ValueError):
                        bonds = {"events": []}
                bond_event = {
                    "at": _now_iso(),
                    "kind": "graft",
                    "from_commit": upstream_commit,
                    "from_repo": upstream_repo,
                    "to_repo": fork_slug,
                    "to_rappid": scaffold_summary["rappid"],
                    "files_added": len(scaffold_summary["written"]),
                    "files_skipped_collision": len(scaffold_summary["skipped"]),
                    "upstream_files_preserved": len(preserved),
                    "upstream_files_clobbered": len(clobbered),
                    "upstream_files_restored": restored,
                    "note": (
                        f"RAPP neighborhood scaffolding overlaid additively on {upstream_repo} "
                        f"(graft technique — bond.py-compatible event kind='graft')."
                    ),
                }
                bonds["events"].append(bond_event)
                with open(bonds_path, "w") as f:
                    json.dump(bonds, f, indent=2)
                    f.write("\n")

            # Step 6: commit + push (skip in dry_run or _skip_push)
            git_commit_sha = None
            if not dry_run and not skip_push:
                _run(["git", "-C", workspace, "config", "user.email", "wildfeuer05@gmail.com"], check=False)
                _run(["git", "-C", workspace, "config", "user.name", "Kody Wildfeuer"], check=False)
                _run(["git", "-C", workspace, "add", "-A"])
                rc, _, _ = _run(["git", "-C", workspace, "commit", "-m",
                                 f"🌱 graft RAPP neighborhood ({kind}) onto {upstream_repo}\n\n"
                                 f"Bond technique: additive overlay. {len(scaffold_summary['written'])} "
                                 f"files added; {len(scaffold_summary['skipped'])} skipped (collision); "
                                 f"upstream files preserved.\n\n"
                                 f"Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"],
                                check=False)
                if rc == 0:
                    rc, head, _ = _run(["git", "-C", workspace, "rev-parse", "HEAD"])
                    git_commit_sha = head.strip()
                    _run(["git", "-C", workspace, "push", "origin", "HEAD"])

            return json.dumps({
                "schema": "rapp-graft-result/1.0",
                "ok": True,
                "dry_run": dry_run,
                "upstream_repo": upstream_repo,
                "upstream_commit": upstream_commit,
                "fork_slug": fork_slug,
                "neighborhood": {
                    "name": neighborhood_name, "display_name": display_name, "kind": kind,
                    "rappid": scaffold_summary["rappid"],
                    "gate_url": f"https://{gh_user}.github.io/{repo_name}/",
                    "rar_index_url": f"https://raw.githubusercontent.com/{gh_user}/{repo_name}/main/rar/index.json",
                },
                "graft": {
                    "files_written": scaffold_summary["written"],
                    "files_skipped_collision": scaffold_summary["skipped"],
                    "graft_path": graft_path or "(root)",
                    "graft_path_mode": graft_path_mode,
                    "_path_mode_meaning": {
                        "root": "first neighborhood — claimed the repo root",
                        "container": "town → city — root has a neighborhood; this one landed in neighborhoods/<name>/",
                        "explicit": "operator-overridden subdirectory",
                    }.get(graft_path_mode, "?"),
                },
                "metropolis": {
                    "_purpose": "This repo is its own self-contained metropolis (rapp-metropolis-index/1.0). The roll-up at _metropolis.json aggregates every grafted neighborhood; the global metropolis at kody-w.github.io/RAPP/metropolis/ can federate to it.",
                    "neighborhoods_in_repo": len(metropolis_index.get("entries", [])),
                    "metropolis_index_path": METROPOLIS_INDEX_FILE,
                    "existing_neighborhoods_at_graft_time": existing_neighborhoods,
                },
                "docking": {
                    "_purpose": (
                        "Same fractal step as Dream Catcher (frame scope), applied at the "
                        "neighborhood scope. Each previously-independent neighborhood within "
                        "this repo keeps its own rappid + agents + rar/, but is now 'docked' "
                        "under the repo-local metropolis roll-up. Operator can reestablish "
                        "active control of a long-evolved local artifact without killing its "
                        "evolution. Information never lost; mutations preserved; merges are "
                        "additive only — same property as Dream Catcher's UTC-first canon + "
                        "contradictions-as-alternate-dimensions doctrine."
                    ),
                    "is_docking": graft_path_mode == "container",
                    "is_solo_graft": graft_path_mode == "root",
                    "docked_neighborhoods": [e.get("name") for e in metropolis_index.get("entries", [])],
                    "preserved_local_neighborhoods": [n.get("name") for n in existing_neighborhoods],
                    "parallel_to_dreamcatcher": {
                        "dream_catcher_scope": "frame within an organism (rapp-frame/1.0 chain)",
                        "docking_scope": "neighborhood within a repo (rapp-rappid/2.0 each)",
                        "shared_property": "additive, content-addressed, append-only, identity preserved",
                    },
                },
                "bond_preserve_local": {
                    "_purpose": "Mirrors bond.py's hatch-back step: every upstream file should be byte-identical after overlay.",
                    "upstream_files_preserved": len(preserved),
                    "upstream_files_clobbered": len(clobbered),
                    "upstream_files_restored": restored,
                    "clobbered_records": clobbered[:10],
                },
                "bond_event": bond_event,
                "git_commit_sha": git_commit_sha,
                "next_step": (
                    "Enable GitHub Pages on the fork to serve the gate at "
                    f"https://{gh_user}.github.io/{repo_name}/  (gh api -X POST "
                    f"repos/{fork_slug}/pages -F source[branch]=main -F source[path]=/)"
                    if not dry_run else
                    "dry_run=True — pass dry_run=False to actually fork + push."
                ),
            }, indent=2)
        finally:
            if cleanup_temp:
                shutil.rmtree(cleanup_temp, ignore_errors=True)
