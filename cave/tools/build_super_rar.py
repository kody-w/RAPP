#!/usr/bin/env python3
"""
build_super_rar.py — (re)build the RAPP Cave's super-RAR + RAR indexes from the
cubbies on disk. The public-cave equivalent of the batcave god agent's
`super_rar rebuild` — extracted into a standalone, pure-stdlib tool so the cave
is a LIVING super-store, not a hand-maintained file.

The super-RAR is the super-store: EVERY kind across EVERY cubby (agents, organs,
senses, rapplications, neighborhoods, eggs) — one registry over the whole open
neighborhood. The RAR is the agent/rapplication registry with sha256 pins that
`cave load` verifies against before streaming a file into your brainstem.

USAGE
    python3 cave/tools/build_super_rar.py            # rebuild in place
    python3 cave/tools/build_super_rar.py --check    # verify the committed indexes are current (CI)

Run from anywhere; it locates the cave root relative to this file. Pure stdlib.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

# kind -> (anatomy subdir, glob) — identical to the batcave god agent's SUPER_RAR_KINDS
SUPER_RAR_KINDS = {
    "agent": ("agents", "*_agent.py"),
    "organ": ("organs", "*_organ.py"),
    "sense": ("senses", "*.py"),
    "rapplication": ("rapplications", "*"),
    "neighborhood": ("neighborhoods", "*"),
    "egg": ("eggs", "*.egg"),
}
CAVE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # cave/tools/.. -> cave/
CUBBIES = os.path.join(CAVE, "cubbies")
RAW_PREFIX = "https://raw.githubusercontent.com/kody-w/RAPP/main/cave"
RETIRED_PREPARED_RAPPLICATIONS = {"rapp-installer"}
RETIRED_CUBBY_AGENTS = {"rapp_installer_agent.py"}
NEIGHBORHOOD_RAPPID = (
    "rappid:@kody-w/rapp-cave:"
    "ca72ca0a3cb90c357fb09e38b02f85f09935cacbf61e94740c57f1eb30a73e0a"
)
SUPER_RAR_HEADER = {
    "schema": "rapp-super-rar/1.0",
    "neighborhood_rappid": NEIGHBORHOOD_RAPPID,
    "note": (
        "Historical Cave inventory. Only entries explicitly marked streamable "
        "may be fetched, and fetched bytes remain untrusted until their owning "
        "protocol verifies them. Retired installer agents, eggs, and prepared "
        "rapplications are inert evidence, not distribution paths."
    ),
    "raw_url_prefix": RAW_PREFIX,
}
RAR_HEADER = {
    "schema": "rapp-rar-index/1.1",
    "neighborhood_rappid": NEIGHBORHOOD_RAPPID,
    "rar_for": "kody-w/RAPP",
    "kind": "workspace",
    "raw_url_prefix": RAW_PREFIX,
    "note": (
        "Contained historical index. SHA-256 records identify retained bytes "
        "but do not authenticate them or authorize installation. Retired "
        "entries are not streamable."
    ),
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_file(p: str) -> str:
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _purpose(py_path: str) -> str:
    """First docstring line of a .py agent, for the registry blurb."""
    try:
        head = open(py_path, encoding="utf-8", errors="ignore").read(1200)
        m = re.search(r'"""(.+?)(?:\n|""")', head)
        return m.group(1).strip()[:140] if m else ""
    except OSError:
        return ""


def build_super_rar() -> list[dict]:
    """Every kind across every cubby — the super-store."""
    entries = []
    if not os.path.isdir(CUBBIES):
        return entries
    for handle in sorted(os.listdir(CUBBIES)):
        if handle.startswith((".", "_")):           # skip _template + hidden
            continue
        for kind, (sub, pat) in SUPER_RAR_KINDS.items():
            for p in sorted(glob.glob(os.path.join(CUBBIES, handle, sub, pat))):
                name = os.path.basename(p)
                if name.startswith(".") or name == "__pycache__":
                    continue
                retired = kind == "agent" and name in RETIRED_CUBBY_AGENTS
                e = {"kind": kind, "name": name, "cubby": handle,
                     "path": os.path.relpath(p, CAVE).replace(os.sep, "/"),
                     "streamable": kind == "agent" and not retired}
                if retired:
                    e["status"] = "retired"
                if os.path.isfile(p):
                    e["sha256"] = _sha256_file(p)
                    if p.endswith(".py"):
                        pr = _purpose(p)
                        if pr:
                            e["purpose"] = pr
                entries.append(e)
    return entries


def render_super_rar() -> dict:
    entries = build_super_rar()
    by_kind: dict[str, int] = {}
    for e in entries:
        by_kind[e["kind"]] = by_kind.get(e["kind"], 0) + 1
    return {
        **SUPER_RAR_HEADER,
        "built_at": _now(),
        "count": len(entries),
        "by_kind": by_kind,
        "entries": entries,
    }


def _manifest_name(py_path: str, default: str) -> tuple[str, bool]:
    """Pull @ns/name + required_by_tether out of a __manifest__ literal, cheaply."""
    try:
        head = open(py_path, encoding="utf-8", errors="ignore").read(2500)
        m = re.search(r'"name"\s*:\s*"(@[^"]+)"', head)
        name = m.group(1) if m else default
        req = bool(re.search(r'"required_by_tether"\s*:\s*[Tt]rue', head))
        return name, req
    except OSError:
        return default, False


def render_rar() -> dict:
    """The RAR: the cave's own participation agents + cubby agents (sha-pinned,
    streamable) + rapplications."""
    agents, rapps = [], []
    # neighborhood-level participation kit (cave/agents/) — the cave's own agents,
    # like the batcave's @rapp/rapp. These are what a member curls to drive the cave.
    for p in sorted(glob.glob(os.path.join(CAVE, "agents", "*_agent.py"))):
        base = os.path.basename(p)[:-len("_agent.py")]
        name, req = _manifest_name(p, f"@kody-w/{base}")
        agents.append({
            "name": name, "version": "1.0.0", "path": f"agents/{os.path.basename(p)}",
            "sha256": _sha256_file(p), "purpose": _purpose(p) or f"Cave participation agent: {base}.",
            "required_by_tether": req, "schema": "rapp-agent/1.0",
        })
    if os.path.isdir(CUBBIES):
        for handle in sorted(os.listdir(CUBBIES)):
            if handle.startswith((".", "_")):
                continue
            for p in sorted(glob.glob(os.path.join(CUBBIES, handle, "agents", "*_agent.py"))):
                rel = os.path.relpath(p, CAVE).replace(os.sep, "/")
                name = os.path.basename(p)
                retired = name in RETIRED_CUBBY_AGENTS
                entry = {
                    "name": f"@{handle}/{os.path.basename(p)[:-len('_agent.py')]}",
                    "version": "0.0.0-cubby", "path": rel, "sha256": _sha256_file(p),
                    "purpose": _purpose(p) or f"Cubby agent from @{handle} — stream via `cave load cubby={handle}`.",
                    "required_by_tether": False, "schema": "rapp-agent/1.0",
                }
                if retired:
                    entry.update({
                        "status": "retired",
                        "active_distribution": False,
                        "purpose": _purpose(p),
                    })
                agents.append(entry)
            for d in sorted(glob.glob(os.path.join(CUBBIES, handle, "rapplications", "*"))):
                if os.path.isdir(d):
                    rapps.append({
                        "name": f"@{handle}/{os.path.basename(d)}", "version": "0.0.0-cubby",
                        "path": os.path.relpath(d, CAVE).replace(os.sep, "/") + "/",
                        "purpose": f"Rapplication bundle from @{handle}.", "schema": "rapp-rapplication/1.0",
                    })
    # top-level neighborhood-flagship rapplications (e.g. the rapp-installer)
    for d in sorted(glob.glob(os.path.join(CAVE, "rapplications", "*"))):
        if os.path.isdir(d):
            name = os.path.basename(d)
            entry = {
                "name": f"@kody-w/{name}", "version": "0.0.0", "schema": "rapp-rapplication/1.0",
                "path": os.path.relpath(d, CAVE).replace(os.sep, "/") + "/",
            }
            if name in RETIRED_PREPARED_RAPPLICATIONS:
                entry.update({
                    "status": "retired",
                    "active_distribution": False,
                    "immutable_prepared_snapshot": True,
                    "purpose": (
                        f"Retired prepared snapshot: {name}. No bootstrap, "
                        "installation, or publication is authorized."
                    ),
                })
            else:
                entry["purpose"] = (
                    f"Cave flagship rapplication: {name}. Pull: curl -fsSL "
                    f"{RAW_PREFIX}/rapplications/{name}/bootstrap.sh | bash"
                )
            rapps.append(entry)
    return {
        **RAR_HEADER,
        "updated_at": _now(),
        "agents": agents,
        "rapps": rapps,
        "verification": {
            "schema": "rapp-rar-manifest/1.0",
            "scheme": "sha256",
            "_instructions": (
                "Re-compute sha256(file) for anything you stream and compare "
                "before installing."
            ),
        },
    }


def _write(path: str, obj: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)
        f.write("\n")


def main() -> None:
    check = "--check" in sys.argv
    targets = {
        os.path.join(CAVE, "super-rar", "index.json"): render_super_rar(),
        os.path.join(CAVE, "rar", "index.json"): render_rar(),
    }
    drift = False
    for path, obj in targets.items():
        new = json.dumps({k: v for k, v in obj.items() if k not in ("built_at", "updated_at")},
                         indent=2, sort_keys=True)
        old = ""
        if os.path.exists(path):
            cur = json.load(open(path))
            old = json.dumps({k: v for k, v in cur.items() if k not in ("built_at", "updated_at")},
                             indent=2, sort_keys=True)
        if new != old:
            drift = True
            print(f"{'DRIFT' if check else 'rebuilt'}: {os.path.relpath(path, CAVE)}")
        if not check:
            _write(path, obj)
    sr = targets[os.path.join(CAVE, "super-rar", "index.json")]
    print(f"super-RAR: {sr['count']} entries {sr['by_kind']}")
    if check and drift:
        print("super-RAR indexes are STALE — run `python3 cave/tools/build_super_rar.py`")
        sys.exit(1)
    if check:
        print("super-RAR indexes are current ✓")


if __name__ == "__main__":
    main()
