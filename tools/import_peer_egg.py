"""Fail-closed RAPP/1 peer egg inspection and authenticated import.

Structural inspection never establishes trust. Import requires a fresh,
authenticated section 13 registry supplied by a caller that verified it out of
band. This repository has no such registry, so the CLI's default import mode
returns ``UNVERIFIED`` and performs no writes.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rapp1_core import (  # noqa: E402
    RegistryEvidence,
    accept_egg,
    extract_egg,
    inspect_egg,
    parse_rappid,
)
from rapp1_core.egg import EggInspection  # noqa: E402
from rapp1_core.errors import EggError  # noqa: E402


RESULT_SCHEMA = "rapp-peer-egg-result/1.0"


def _read_egg(path: str | Path) -> tuple[Path, bytes] | dict[str, Any]:
    egg = Path(path).expanduser()
    try:
        if not egg.is_file():
            raise FileNotFoundError
        return egg, egg.read_bytes()
    except (FileNotFoundError, OSError) as exc:
        return {
            "schema": RESULT_SCHEMA,
            "operation": "read",
            "ok": False,
            "imported": False,
            "status": "INVALID",
            "trust-status": "UNVERIFIED",
            "error": {
                "code": "egg-unreadable",
                "message": f"egg is not a readable file: {egg}",
            },
            "guidance": "RAPP1_STATUS.md",
        }


def _result(
    operation: str,
    inspection: EggInspection,
    *,
    status: str | None = None,
    error: dict[str, str] | None = None,
    destination: Path | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": RESULT_SCHEMA,
        "operation": operation,
        "ok": False,
        "imported": False,
        "status": status or inspection.trust_status.value,
        "trust-status": inspection.trust_status.value,
        "inspection": inspection.as_dict(),
        "guidance": "RAPP1_STATUS.md",
    }
    if error is not None:
        result["error"] = error
    if destination is not None:
        result["destination"] = str(destination)
    return result


def inspect_peer_egg(egg_path: str | Path) -> dict[str, Any]:
    """Report strict structural status without accepting or importing."""

    loaded = _read_egg(egg_path)
    if isinstance(loaded, dict):
        loaded["operation"] = "inspect"
        return loaded
    _, data = loaded
    inspection = inspect_egg(data)
    status = "UNVERIFIED" if inspection.structurally_valid else "INVALID"
    return _result("inspect", inspection, status=status)


def import_egg(
    egg_path: str | Path,
    destination: str | Path | None = None,
    *,
    registry: RegistryEvidence | None = None,
) -> dict[str, Any]:
    """Accept through the strict core before extracting.

    The CLI never supplies ``registry``. Programmatic callers may supply only
    registry evidence they authenticated independently; the core still refuses
    stale, signed-but-unverified, or structurally invalid eggs.
    """

    loaded = _read_egg(egg_path)
    if isinstance(loaded, dict):
        loaded["operation"] = "import"
        return loaded
    _, data = loaded
    acceptance = accept_egg(data, registry=registry)
    if not acceptance.accepted:
        error = {
            "code": (
                acceptance.error_code
                if not acceptance.structurally_valid and acceptance.error_code
                else "authenticated-registry-unavailable"
            ),
            "message": (
                acceptance.error
                if not acceptance.structurally_valid and acceptance.error
                else "import requires fresh authenticated RAPP/1 registry evidence"
            ),
        }
        return _result(
            "import",
            acceptance,
            status=(
                acceptance.trust_status.value
                if acceptance.structurally_valid
                else "INVALID"
            ),
            error=error,
        )

    assert acceptance.manifest is not None
    if destination is None:
        identity = parse_rappid(acceptance.manifest["rappid"])
        destination_path = (
            Path.home()
            / ".brainstem"
            / "peers"
            / f"{identity.owner}--{identity.slug}"
        )
    else:
        destination_path = Path(destination).expanduser()

    try:
        extracted = extract_egg(data, destination_path, registry=registry)
    except EggError as exc:
        return _result(
            "import",
            acceptance,
            status="IMPORT_REFUSED",
            error={"code": exc.code, "message": str(exc)},
            destination=destination_path,
        )

    result = _result(
        "import",
        acceptance,
        status="VERIFIED",
        destination=extracted,
    )
    result["ok"] = True
    result["imported"] = True
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("egg", help="path to a received RAPP/1 egg")
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="strict structural report only; never accept or import",
    )
    parser.add_argument(
        "--into",
        help="future authenticated extraction destination (default: peer path)",
    )
    args = parser.parse_args(argv)

    result = (
        inspect_peer_egg(args.egg)
        if args.inspect
        else import_egg(args.egg, args.into)
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if result.get("imported") is True:
        return 0
    return 2 if result.get("status") == "INVALID" else 3


if __name__ == "__main__":
    sys.exit(main())
