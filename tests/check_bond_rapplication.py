#!/usr/bin/env python3
"""Exercise the rapplication egg bond cycle (utils/bond.py).

The bond is a trust boundary: an egg is foreign bytes, and unpack must
confine every member to its destination, land the skin where the brainstem
serves it, and refuse traversal outright. One happy path, one hostile path.
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "rapp_brainstem"))

from utils import bond  # noqa: E402

FAILURES = []


def check(name: str, cond: bool) -> None:
    print(("  ok " if cond else "FAIL ") + name)
    if not cond:
        FAILURES.append(name)


def make_egg(members: dict, manifest: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("manifest.json", json.dumps(manifest))
        for name, data in members.items():
            z.writestr(name, data)
    return buf.getvalue()


MANIFEST = {
    "schema": bond.SCHEMA_RAPP,
    "type": "rapplication",
    "rapp_id": "demo",
    "name": "Demo",
    "agent_filename": "demo_agent.py",
    "has_skin": True,
}

# ── happy path: agent + skin land where the brainstem expects them ──
with tempfile.TemporaryDirectory() as src:
    egg = make_egg({
        "agents/demo_agent.py": "# agent\n",
        "rapp_ui/demo/index.html": "<!doctype html><title>Demo</title>",
        "rappid.json": "{}",
    }, MANIFEST)
    check("inspect_egg reads the manifest",
          bond.inspect_egg(egg)["rapp_id"] == "demo")
    r = bond.unpack_rapplication(egg, src)
    check("unpack succeeds", r["ok"] and r["rapp_id"] == "demo")
    check("agent lands in agents/",
          (Path(src) / "agents" / "demo_agent.py").is_file())
    check("skin lands under .brainstem_data/rapp_ui/<id>/",
          (Path(src) / ".brainstem_data" / "rapp_ui" / "demo" / "index.html").is_file())
    check("manifest lands beside the skin for the chat page's dock",
          (Path(src) / ".brainstem_data" / "rapp_ui" / "demo" / ".manifest.json").is_file())

# ── hostile paths: traversal refused, wrong schema refused, state kept ──
with tempfile.TemporaryDirectory() as src:
    evil = make_egg({"agents/../../evil.py": "boom"}, MANIFEST)
    r = bond.unpack_rapplication(evil, src)
    check("a traversing member is refused", not r["ok"] and r["errors"])
    check("nothing escaped the tree",
          not (Path(src).parent / "evil.py").exists())

    skinjack = make_egg({"rapp_ui/other/index.html": "<html>"}, MANIFEST)
    r = bond.unpack_rapplication(skinjack, src)
    check("an egg cannot write another rapplication's skin path",
          (Path(src) / ".brainstem_data" / "rapp_ui" / "demo" / "index.html").is_file()
          and not (Path(src) / ".brainstem_data" / "rapp_ui" / "other").exists())

    wrong = make_egg({}, dict(MANIFEST, schema="brainstem-egg/2.1"))
    check("an organism-scope egg is refused by the rapplication bond",
          not bond.unpack_rapplication(wrong, src)["ok"])

    state = Path(src) / ".brainstem_data" / "kept.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text('{"mine": true}')
    clobber = make_egg({"data/kept.json": '{"mine": false}'}, MANIFEST)
    bond.unpack_rapplication(clobber, src)
    check("device state survives an egg (no overwrite by default)",
          json.loads(state.read_text())["mine"] is True)

print()
if FAILURES:
    print(f"BOND CHECK: {len(FAILURES)} failure(s)")
    sys.exit(1)
print("BOND CHECK: all pass")
