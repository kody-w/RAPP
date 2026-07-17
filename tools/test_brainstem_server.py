"""Historical federation-server fixture; intentionally non-executable."""

from __future__ import annotations

import sys
from collections.abc import Sequence


EXIT_CONFIG = 78
RETIREMENT_MESSAGE = (
    "410 Gone: tools/test_brainstem_server.py is a non-executable historical "
    "fixture and must not emit legacy chat envelopes."
)


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    print(RETIREMENT_MESSAGE, file=sys.stderr)
    return EXIT_CONFIG


if __name__ == "__main__":
    raise SystemExit(main())
