"""Retired autonomous simulation tick entrypoint."""

from __future__ import annotations

import sys
from collections.abc import Sequence


EXIT_CONFIG = 78
RETIREMENT_MESSAGE = (
    "410 Gone: tools/sim/tick_twin.py is retained only as a non-executable "
    "historical fixture."
)


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    print(RETIREMENT_MESSAGE, file=sys.stderr)
    return EXIT_CONFIG


if __name__ == "__main__":
    raise SystemExit(main())
