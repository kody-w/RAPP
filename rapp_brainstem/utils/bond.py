"""utils/bond.py — the egg bond cycle for rapplication-scope eggs.

An egg is a zip. A rapplication egg (schema brainstem-egg/2.x-rapplication)
carries, at most:

    manifest.json               the egg's own manifest (schema, rapp_id, name…)
    agents/<name>_agent.py      the chat face — hot-loaded on the next turn
    organs/<name>_organ.py      optional HTTP organ
    rapp_ui/<rapp_id>/…         the SKIN — every rapplication ships a custom UI;
                                the brainstem serves it at /rapp_ui/<rapp_id>/
                                and the default chat injects it on top of itself
    data/…                      optional state seeds → .brainstem_data/
    soul/…                      optional souls (counted, kept beside the skin)
    rappid.json                 optional identity record, kept beside the skin

unpack_rapplication() restores each part into a brainstem src tree and returns
{ok, rapp_id, restored: {agent, organ, ui, data, soul}, errors}. Every member
path is confined to its destination — an egg never chooses a path outside it.
"""

import io
import json
import os
import zipfile

SCHEMA_RAPP = "brainstem-egg/2.2-rapplication"
# Accepted family: any 2.x rapplication egg unpacks; 2.2 is what we emit.
_SCHEMA_PREFIX = "brainstem-egg/2."
_SCHEMA_SUFFIX = "-rapplication"


def inspect_egg(blob: bytes) -> dict:
    """Read only the manifest — the peek before the bond."""
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        return json.loads(z.read("manifest.json"))


def _rapplication_schema(schema: str) -> bool:
    return schema == SCHEMA_RAPP or (
        schema.startswith(_SCHEMA_PREFIX) and schema.endswith(_SCHEMA_SUFFIX)
    )


def _confine(root: str, *parts: str) -> str:
    """Resolve a destination inside root, refusing traversal outright."""
    dest = os.path.realpath(os.path.join(root, *parts))
    root = os.path.realpath(root)
    if dest != root and not dest.startswith(root + os.sep):
        raise ValueError(f"egg member escapes its destination: {'/'.join(parts)}")
    return dest


def unpack_rapplication(blob: bytes, src: str, overwrite_state: bool = False) -> dict:
    """Restore a rapplication egg into the brainstem src tree at `src`."""
    result = {"ok": False, "rapp_id": None,
              "restored": {"agent": 0, "organ": 0, "ui": 0, "data": 0, "soul": 0},
              "errors": []}
    try:
        z = zipfile.ZipFile(io.BytesIO(blob))
    except Exception as e:
        result["errors"].append(f"not a zip egg: {e}")
        return result
    try:
        manifest = json.loads(z.read("manifest.json"))
    except Exception as e:
        result["errors"].append(f"no readable manifest: {e}")
        return result
    schema = str(manifest.get("schema") or "")
    if not _rapplication_schema(schema):
        result["errors"].append(f"schema {schema!r} is not a rapplication egg")
        return result
    rapp_id = str(manifest.get("rapp_id") or manifest.get("id") or "").strip()
    if not rapp_id or any(c in rapp_id for c in "/\\.."):
        result["errors"].append(f"manifest has no safe rapp_id: {rapp_id!r}")
        return result
    result["rapp_id"] = rapp_id

    skin_root = os.path.join(src, ".brainstem_data", "rapp_ui", rapp_id)
    for info in z.infolist():
        name = info.filename
        if info.is_dir() or name == "manifest.json":
            continue
        parts = name.split("/")
        if any(p in ("", ".", "..") for p in parts):
            result["errors"].append(f"refused member path: {name}")
            continue
        data = z.read(info)
        try:
            if parts[0] == "agents" and len(parts) == 2 and parts[1].endswith(".py"):
                dest = _confine(os.path.join(src, "agents"), parts[1])
                kind = "agent"
            elif parts[0] == "organs" and len(parts) == 2 and parts[1].endswith(".py"):
                dest = _confine(os.path.join(src, "organs"), parts[1])
                kind = "organ"
            elif parts[0] == "rapp_ui":
                # rapp_ui/<any-id>/… lands under THIS egg's rapp_id — an egg
                # cannot write into another rapplication's skin
                dest = _confine(skin_root, *parts[2:] if len(parts) > 2 else parts[1:])
                kind = "ui"
            elif parts[0] == "data":
                dest = _confine(os.path.join(src, ".brainstem_data"), *parts[1:])
                if os.path.exists(dest) and not overwrite_state:
                    continue  # state belongs to this device; eggs never clobber it
                kind = "data"
            elif parts[0] in ("soul", "souls"):
                dest = _confine(skin_root, ".soul", *parts[1:])
                kind = "soul"
            elif name == "rappid.json":
                dest = _confine(skin_root, ".rappid.json")
                kind = "ui"
            else:
                continue  # unknown members are ignored, never written
        except ValueError as e:
            result["errors"].append(str(e))
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(data)
        result["restored"][kind] += 1

    # The manifest lands beside the skin so the chat page's dock can name the
    # rapplication and find its agent without re-opening the egg.
    if result["restored"]["ui"] or result["restored"]["agent"]:
        os.makedirs(skin_root, exist_ok=True)
        with open(os.path.join(skin_root, ".manifest.json"), "w") as f:
            json.dump(manifest, f, indent=2)

    result["ok"] = not result["errors"]
    return result
