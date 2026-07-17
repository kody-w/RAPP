"""Retired legacy front-door specification generator."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from typing import NoReturn


EXIT_CONFIG = 78
RETIREMENT_MESSAGE = (
    "410 Gone: tools/front_door_specs.py generated legacy envelopes without "
    "RAPP/1 trust evidence and is retired."
)


def _retired() -> NoReturn:
    raise RuntimeError(RETIREMENT_MESSAGE)


def bundle_version() -> str:
    _retired()


def available_kinds() -> list[str]:
    _retired()


def normalize_kind(kind: str) -> str:
    del kind
    _retired()


def bundle_for_kind(
    kind: str,
    *,
    owner: str = "<owner>",
    name: str = "<name>",
    display_name: str = "<display-name>",
) -> dict[str, str]:
    del kind, owner, name, display_name
    _retired()


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    print(RETIREMENT_MESSAGE, file=sys.stderr)
    return EXIT_CONFIG


if __name__ == "__main__":
    raise SystemExit(main())
