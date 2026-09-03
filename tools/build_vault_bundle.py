#!/usr/bin/env python3
"""Render or verify the self-contained public vault content bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VAULT = ROOT / "pages" / "vault"
MANIFEST = VAULT / "manifest.json"
OUTPUT = VAULT / "content-bundle.json"


def render() -> str:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    runtime = manifest.get("runtime_content", {})
    if runtime.get("bundle") != OUTPUT.name:
        raise ValueError("manifest does not select content-bundle.json")
    if runtime.get("network_fallback") is not False:
        raise ValueError("manifest permits a network content fallback")

    notes: dict[str, dict[str, object]] = {}
    for entry in manifest["notes"]:
        path = entry["path"]
        source = VAULT / path
        raw = source.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if entry.get("bytes") != len(raw) or entry.get("sha256") != digest:
            raise ValueError(f"manifest hash drift: {path}")
        notes[path] = {
            "bytes": len(raw),
            "sha256": digest,
            "content": raw.decode("utf-8"),
        }

    value = {
        "schema": "rapp-vault-content-bundle/1.0",
        "record_kind": "immutable-checked-in-vault-content",
        "network_fallback": False,
        "note_count": len(notes),
        "notes": notes,
    }
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--render", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        expected = render()
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
        print(error)
        return 1

    if args.render:
        print(expected, end="")
        return 0
    if args.write:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=OUTPUT.parent,
            delete=False,
        ) as handle:
            handle.write(expected)
            temporary = Path(handle.name)
        temporary.replace(OUTPUT)
        print(f"wrote {OUTPUT.relative_to(ROOT)}")
        return 0
    if not OUTPUT.is_file():
        print(f"{OUTPUT.relative_to(ROOT)} is missing")
        return 1
    if OUTPUT.read_text(encoding="utf-8") != expected:
        print(f"{OUTPUT.relative_to(ROOT)} is stale")
        return 1
    print(f"{OUTPUT.relative_to(ROOT)} is current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
