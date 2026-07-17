"""Historical Tier-2 fixture; intentionally not an executable entrypoint."""

from __future__ import annotations

import sys
from collections.abc import Sequence


EXIT_CONFIG = 78
RETIREMENT_MESSAGE = (
    "410 Gone: rapp_swarm/function_app.py is a non-executable historical "
    "fixture. Use the target-owned RAPP/1 facade; see ../RAPP1_STATUS.md."
)


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    print(RETIREMENT_MESSAGE, file=sys.stderr)
    return EXIT_CONFIG


if __name__ == "__main__":
    raise SystemExit(main())
