"""Command-line interface for the target-owned RAPP/1 structural core."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Sequence

from .canonical import canonical_bytes, strict_loads
from .egg import JSON_VARIANTS, ZIP_VARIANTS, inspect_egg, pack_egg
from .errors import RappError
from .frame import inspect_frame, inspect_frame_bytes
from .identity import mint_keyless_rappid, mint_spki_rappid
from .trust import HeadState


def _emit(value: dict[str, Any]) -> None:
    sys.stdout.buffer.write(canonical_bytes(value) + b"\n")


def _read(path: str) -> bytes:
    if path == "-":
        return sys.stdin.buffer.read()
    return Path(path).read_bytes()


def _head_from_path(path: str) -> HeadState:
    parsed = strict_loads(_read(path))
    if type(parsed) is not dict:
        raise ValueError("head frame must be a JSON object")
    stream_id = parsed.get("stream_id")
    inspected = inspect_frame(parsed, declared_stream_id=stream_id)
    if not inspected.structurally_valid:
        raise ValueError(inspected.error or "head frame is structurally invalid")
    return HeadState(
        stream_id=parsed["stream_id"],
        seq=parsed["seq"],
        utc=parsed["utc"],
        payload_hash=parsed["payload_hash"],
        frame_hash=parsed["frame_hash"],
        trusted=False,
        signature_present=parsed["sig"] is not None,
    )


def _validate_command(args: argparse.Namespace) -> int:
    data = _read(args.input)
    if args.artifact == "json":
        value = strict_loads(data)
        encoded = canonical_bytes(value)
        _emit(
            {
                "structurally-valid": True,
                "accepted": False,
                "trust-status": "UNVERIFIED",
                "canonical-bytes": len(encoded),
                "source-is-canonical": data == encoded,
            }
        )
        return 0
    if args.artifact == "frame":
        report = inspect_frame_bytes(data)
    else:
        report = inspect_egg(data)
    _emit(report.as_dict())
    return 0 if report.structurally_valid else 2


def _inspect_command(args: argparse.Namespace) -> int:
    data = _read(args.input)
    if args.artifact == "frame":
        head = _head_from_path(args.head) if args.head else None
        report = inspect_frame_bytes(
            data, declared_stream_id=args.stream_id, head=head
        )
    else:
        report = inspect_egg(data)
    _emit(report.as_dict())
    return 0 if report.structurally_valid else 2


def _is_within(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
        return True
    except ValueError:
        return False


def _collect_files(source: Path, output: Path) -> dict[str, bytes]:
    root = source.resolve()
    if not root.is_dir():
        raise ValueError("ZIP variant --source must be a directory")
    if _is_within(output.resolve(), root):
        raise ValueError("output must be outside the packed source directory")
    files: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"symlinks are not packable: {path}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError(f"non-regular file is not packable: {path}")
        relative = path.relative_to(root).as_posix()
        files[relative] = path.read_bytes()
    return files


def _pack_command(args: argparse.Namespace) -> int:
    output = Path(args.output)
    if output.exists():
        raise ValueError("output already exists")
    if args.payload:
        payload = strict_loads(_read(args.payload))
        if type(payload) is not dict:
            raise ValueError("payload file must contain a JSON object")
    else:
        payload = {}
    sig = None
    if args.sig is not None and args.sig_file is not None:
        raise ValueError("use only one of --sig and --sig-file")
    if args.sig is not None:
        sig = args.sig
    elif args.sig_file is not None:
        sig = _read(args.sig_file).decode("utf-8", errors="strict")

    if args.variant in ZIP_VARIANTS:
        if args.source is None:
            raise ValueError(f"{args.variant} requires --source")
        files = _collect_files(Path(args.source), output)
    else:
        if args.source is not None:
            raise ValueError(f"{args.variant} must not have --source")
        files = {}
    packed = pack_egg(
        variant=args.variant,
        rappid=args.rappid,
        created_utc=args.created_utc,
        payload=payload,
        files=files,
        sig=sig,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as handle:
        handle.write(packed)
    report = inspect_egg(packed).as_dict()
    report["output"] = str(output)
    report["bytes"] = len(packed)
    _emit(report)
    return 0


def _mint_command(args: argparse.Namespace) -> int:
    if args.mint_type == "keyless":
        rappid = mint_keyless_rappid(args.owner, args.slug)
    else:
        rappid = mint_spki_rappid(args.owner, args.slug, _read(args.spki_der))
    _emit(
        {
            "structurally-valid": True,
            "accepted": False,
            "trust-status": "UNVERIFIED",
            "mint": args.mint_type,
            "rappid": rappid,
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m rapp1_core")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="strictly validate an artifact")
    validate.add_argument("artifact", choices=("json", "frame", "egg"))
    validate.add_argument("input", help="input path, or - for stdin")
    validate.set_defaults(handler=_validate_command)

    inspect = subparsers.add_parser(
        "inspect", help="structurally inspect without claiming acceptance"
    )
    inspect.add_argument("artifact", choices=("frame", "egg"))
    inspect.add_argument("input", help="input path, or - for stdin")
    inspect.add_argument("--stream-id", help="declared stream binding for a frame")
    inspect.add_argument("--head", help="predecessor frame used only for link checks")
    inspect.set_defaults(handler=_inspect_command)

    pack = subparsers.add_parser("pack", help="pack any ratified egg variant")
    pack.add_argument("variant", choices=tuple(sorted(JSON_VARIANTS | ZIP_VARIANTS)))
    pack.add_argument("output")
    pack.add_argument("--rappid", required=True)
    pack.add_argument("--created-utc", required=True)
    pack.add_argument("--payload", help="strict JSON object file; defaults to {}")
    pack.add_argument("--source", help="directory for a ZIP variant")
    pack.add_argument("--sig", help="detached unencoded JWS compact string")
    pack.add_argument("--sig-file", help="file containing exact JWS compact octets")
    pack.set_defaults(handler=_pack_command)

    mint = subparsers.add_parser("mint", help="mint a keyless or SPKI-bound rappid")
    mint_subparsers = mint.add_subparsers(dest="mint_type", required=True)
    keyless = mint_subparsers.add_parser("keyless")
    keyless.add_argument("owner")
    keyless.add_argument("slug")
    keyless.set_defaults(handler=_mint_command)
    spki = mint_subparsers.add_parser("spki")
    spki.add_argument("owner")
    spki.add_argument("slug")
    spki.add_argument("spki_der")
    spki.set_defaults(handler=_mint_command)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (RappError, OSError, UnicodeError, ValueError, TypeError) as exc:
        _emit(
            {
                "structurally-valid": False,
                "accepted": False,
                "trust-status": "DRIFT",
                "error": {
                    "code": getattr(exc, "code", "cli-error"),
                    "message": str(exc),
                },
            }
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
