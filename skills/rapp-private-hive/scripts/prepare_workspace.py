#!/usr/bin/env python3
"""Additive, no-data-loss preparation for a RAPP Private Hive workspace."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
RAPP_PATH = ROOT / "vendor" / "rapp.py"
CONTROL = ".rapp-hive"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
EXCLUDED_ROOTS = {".git", CONTROL}


def _load_rapp():
    spec = importlib.util.spec_from_file_location("rapp_private_hive_vendor", RAPP_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import pinned RAPP/1 reference: {RAPP_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


R = _load_rapp()


def utc_now() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def canonical_bytes(value: object) -> bytes:
    return R.canonical(value).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_write(path: Path, data: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(mode)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def workspace_root(raw: str) -> Path:
    root = Path(raw).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"workspace is not a directory: {root}")
    return root


def safe_relative(raw: str) -> str:
    if not isinstance(raw, str) or not raw or "\\" in raw:
        raise ValueError("path must be a non-empty relative POSIX path")
    path = PurePosixPath(raw)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe relative path: {raw}")
    if path.parts[0] in EXCLUDED_ROOTS:
        raise ValueError(f"control or Git paths cannot be selected: {raw}")
    return str(path)


def read_json(path: Path) -> dict:
    try:
        value = R._strict_json(path.read_bytes())
    except FileNotFoundError as error:
        raise ValueError(f"required file is missing: {path}") from error
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def inventory(root: Path) -> list[dict]:
    entries = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if relative.parts and relative.parts[0] in EXCLUDED_ROOTS:
            continue
        if path.is_symlink():
            raise ValueError(f"workspace symlink requires explicit migration handling: {relative}")
        if not path.is_file():
            continue
        data = path.read_bytes()
        entries.append(
            {
                "path": relative.as_posix(),
                "sha256": sha256(data),
                "bytes": len(data),
            }
        )
    return entries


def inventory_hash(entries: list[dict]) -> str:
    return sha256(canonical_bytes(entries))


def verify_unchanged(root: Path, before: list[dict]) -> None:
    for entry in before:
        path = root / entry["path"]
        if not path.is_file():
            raise RuntimeError(f"pre-existing workspace file disappeared: {entry['path']}")
        data = path.read_bytes()
        if len(data) != entry["bytes"] or sha256(data) != entry["sha256"]:
            raise RuntimeError(f"pre-existing workspace file changed: {entry['path']}")


def workspace_identity(root: Path) -> tuple[dict, str]:
    record = read_json(root / "rappid.json")
    identity = record.get("rappid")
    if not R.rappid_valid(identity):
        raise ValueError("workspace rappid.json does not contain a valid RAPP/1 identity")
    return record, identity


def control_root(root: Path) -> Path:
    return root / CONTROL


def control_files(root: Path) -> tuple[dict, dict, dict]:
    base = control_root(root)
    return (
        read_json(base / "state.json"),
        read_json(base / "declaration.json"),
        read_json(base / "selection.json"),
    )


def command_inspect(args) -> dict:
    root = workspace_root(args.workspace)
    record, identity = workspace_identity(root)
    entries = inventory(root)
    base = control_root(root)
    return {
        "status": "ready" if not base.exists() else "prepared",
        "workspace": str(root),
        "workspace_rappid": identity,
        "mode": record.get("mode", "solo"),
        "preexisting_files": len(entries),
        "preexisting_bytes": sum(entry["bytes"] for entry in entries),
        "inventory_sha256": inventory_hash(entries),
        "control_path": str(base),
    }


def command_prepare(args) -> dict:
    root = workspace_root(args.workspace)
    record, workspace_rappid = workspace_identity(root)
    if not R.rappid_valid(args.member_rappid):
        raise ValueError("--member-rappid must be a valid RAPP/1 identity")
    owner = R.rappid_parts(args.member_rappid)["owner"]
    world_id = args.world_id or record.get("world_id")
    if not isinstance(world_id, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", world_id):
        raise ValueError("--world-id must be a lowercase RAPP label")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.hive_name):
        raise ValueError("--hive-name must be a lowercase RAPP label")

    base = control_root(root)
    if base.exists():
        state, declaration, selection = control_files(root)
        return {
            "status": "already-prepared",
            "workspace": str(root),
            "hive_rappid": declaration["hive_rappid"],
            "dimension_rappid": state["dimension_rappid"],
            "selected": len(selection["entries"]),
        }

    before = inventory(root)
    created = utc_now()
    hive_rappid = R.mint_rappid(owner, args.hive_name)
    dimension_rappid = R.mint_rappid(owner, f"{args.hive_name}-local")
    declaration = {
        "schema": "rapp-hive/1-declaration",
        "hive_rappid": hive_rappid,
        "world_id": world_id,
        "created_utc": created,
        "authority_channel_id": "local-authority",
        "members": [
            {
                "rappid": args.member_rappid,
                "role": "owner",
                "area": f"members/{owner}",
            }
        ],
        "rooms": [
            {
                "id": "general",
                "area": "rooms/general",
                "members": [args.member_rappid],
                "access": "repository",
            },
            {
                "id": "private",
                "area": "rooms/private",
                "members": [args.member_rappid],
                "access": "sealed",
            },
        ],
        "channels": [
            {
                "id": "local-authority",
                "kind": "local",
                "role": "authority",
                "locator": f"{CONTROL}/outbox",
                "writeback": True,
            }
        ],
        "policy": {
            "godd_sharing": "explicit",
            "default_godd_scope": "local-only",
            "external_publication": "disabled",
            "conflict_mode": "explicit",
            "default_transfer": "copy",
        },
    }
    state = {
        "schema": "rapp-private-hive-workspace/1",
        "workspace_rappid": workspace_rappid,
        "hive_rappid": hive_rappid,
        "dimension_rappid": dimension_rappid,
        "created_utc": created,
        "baseline_inventory_sha256": inventory_hash(before),
        "baseline_files": len(before),
        "baseline_bytes": sum(entry["bytes"] for entry in before),
        "data_loss_guard": "preexisting-bytes-unchanged",
    }
    selection = {
        "schema": "rapp-private-hive-selection/1",
        "workspace_rappid": workspace_rappid,
        "default": "local-only",
        "entries": [],
    }
    base.mkdir(mode=0o700)
    atomic_write(base / "baseline.json", canonical_bytes({"schema": "rapp-private-hive-baseline/1", "files": before}))
    atomic_write(base / "declaration.json", canonical_bytes(declaration))
    atomic_write(base / "selection.json", canonical_bytes(selection))
    atomic_write(base / "state.json", canonical_bytes(state))
    verify_unchanged(root, before)
    receipt = {
        "schema": "rapp-private-hive-prepare-receipt/1",
        "prepared_utc": created,
        "workspace_rappid": workspace_rappid,
        "hive_rappid": hive_rappid,
        "baseline_inventory_sha256": state["baseline_inventory_sha256"],
        "preexisting_bytes_unchanged": True,
        "selected_entries": 0,
    }
    atomic_write(base / "prepare-receipt.json", canonical_bytes(receipt))
    return {"status": "prepared", "workspace": str(root), **receipt}


def command_select(args) -> dict:
    root = workspace_root(args.workspace)
    _, declaration, selection = control_files(root)
    relative = safe_relative(args.path)
    source = root / relative
    if source.is_symlink() or not source.is_file():
        raise ValueError(f"selected path must be a regular file: {relative}")
    rooms = {room["id"]: room for room in declaration["rooms"]}
    if args.room not in rooms:
        raise ValueError(f"unknown room: {args.room}")
    if args.data_class == "dogg":
        if not args.pii_evidence_hash or not HEX64.fullmatch(args.pii_evidence_hash):
            raise ValueError("DOGG selection requires --pii-evidence-hash <64hex>")
        pii_status = "none"
        protection = args.protection or "member-visible"
    elif args.data_class == "godd":
        if args.pii_evidence_hash:
            raise ValueError("GODD selection does not use DOGG PII evidence")
        pii_status = "unknown"
        protection = args.protection or "sealed-room"
        if protection != "sealed-room" or rooms[args.room]["access"] != "sealed":
            raise ValueError("GODD selection requires a sealed room and sealed-room protection")
    else:
        pii_status = "not-applicable"
        protection = args.protection or "member-visible"
    data = source.read_bytes()
    entry = {
        "path": relative,
        "sha256": sha256(data),
        "bytes": len(data),
        "data_class": args.data_class,
        "pii_status": pii_status,
        "pii_evidence_hash": args.pii_evidence_hash,
        "room_id": args.room,
        "protection": protection,
        "transfer": "copy",
        "status": "pending-seal" if args.data_class == "godd" else "selected",
    }
    entries = [value for value in selection["entries"] if value["path"] != relative]
    entries.append(entry)
    entries.sort(key=lambda value: value["path"])
    selection["entries"] = entries
    atomic_write(control_root(root) / "selection.json", canonical_bytes(selection))
    return {"status": "selected", "entry": entry, "local_source_preserved": True}


def command_unselect(args) -> dict:
    root = workspace_root(args.workspace)
    _, _, selection = control_files(root)
    relative = safe_relative(args.path)
    before = len(selection["entries"])
    selection["entries"] = [value for value in selection["entries"] if value["path"] != relative]
    if len(selection["entries"]) == before:
        raise ValueError(f"path is not selected: {relative}")
    atomic_write(control_root(root) / "selection.json", canonical_bytes(selection))
    return {"status": "unselected", "path": relative, "local_source_preserved": True}


def command_stage(args) -> dict:
    root = workspace_root(args.workspace)
    state, declaration, selection = control_files(root)
    outbox = Path(args.outbox).expanduser().resolve()
    if outbox == root or root in outbox.parents:
        raise ValueError("outbox must be outside the local workspace")
    stage_root = outbox / declaration["hive_rappid"].replace(":", "_")
    staged = []
    pending_godd = []
    for entry in selection["entries"]:
        source = root / entry["path"]
        if not source.is_file() or source.is_symlink():
            raise RuntimeError(f"selected source is unavailable: {entry['path']}")
        data = source.read_bytes()
        if sha256(data) != entry["sha256"] or len(data) != entry["bytes"]:
            raise RuntimeError(f"selected source changed; reselect before staging: {entry['path']}")
        if entry["data_class"] == "godd":
            pending_godd.append(entry["path"])
            continue
        destination = stage_root / "objects" / entry["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and destination.read_bytes() != data:
            raise RuntimeError(f"staging collision with different bytes: {entry['path']}")
        atomic_write(destination, data, 0o644)
        staged.append({key: entry[key] for key in ("path", "sha256", "bytes", "data_class", "room_id")})
    manifest = {
        "schema": "rapp-private-hive-stage/1",
        "hive_rappid": declaration["hive_rappid"],
        "dimension_rappid": state["dimension_rappid"],
        "created_utc": utc_now(),
        "objects": staged,
        "pending_godd": pending_godd,
        "local_sources_preserved": True,
    }
    atomic_write(stage_root / "manifest.json", canonical_bytes(manifest), 0o644)
    return {
        "status": "staged" if not pending_godd else "staged-with-pending-godd",
        "outbox": str(stage_root),
        "staged": len(staged),
        "pending_godd": pending_godd,
        "local_sources_preserved": True,
    }


def command_verify(args) -> dict:
    root = workspace_root(args.workspace)
    state, declaration, selection = control_files(root)
    baseline = read_json(control_root(root) / "baseline.json")["files"]
    verify_unchanged(root, baseline)
    checked = []
    for entry in selection["entries"]:
        source = root / entry["path"]
        current = source.read_bytes() if source.is_file() and not source.is_symlink() else None
        checked.append(
            {
                "path": entry["path"],
                "matches_selection": current is not None
                and sha256(current) == entry["sha256"]
                and len(current) == entry["bytes"],
            }
        )
    return {
        "status": "verified",
        "workspace_rappid": state["workspace_rappid"],
        "hive_rappid": declaration["hive_rappid"],
        "baseline_files_unchanged": len(baseline),
        "selection": checked,
        "local_only_default": selection["default"] == "local-only",
    }


COMMANDS = {
    "inspect": command_inspect,
    "prepare": command_prepare,
    "select": command_select,
    "unselect": command_unselect,
    "stage": command_stage,
    "verify": command_verify,
}


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    commands = root.add_subparsers(dest="command", required=True)
    for name in COMMANDS:
        command = commands.add_parser(name)
        command.add_argument("--workspace", required=True)
        if name == "prepare":
            command.add_argument("--member-rappid", required=True)
            command.add_argument("--hive-name", required=True)
            command.add_argument("--world-id")
        elif name == "select":
            command.add_argument("--path", required=True)
            command.add_argument("--data-class", choices=("dogg", "godd", "neutral"), required=True)
            command.add_argument("--room", required=True)
            command.add_argument("--protection", choices=("member-visible", "sealed-room"))
            command.add_argument("--pii-evidence-hash")
        elif name == "unselect":
            command.add_argument("--path", required=True)
        elif name == "stage":
            command.add_argument("--outbox", required=True)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    result = COMMANDS[args.command](args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as error:
        print(json.dumps({"status": "refused", "error": str(error)}, sort_keys=True), file=sys.stderr)
        raise SystemExit(1)
