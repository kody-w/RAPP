"""Retired legacy two-brainstem simulation planter."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
EXIT_CONFIG = 78
RETIREMENT_MESSAGE = (
    "410 Gone: the legacy two-brainstem planter emitted untrusted product "
    f"envelopes and is retired (repository: {REPO_ROOT})."
)


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    print(RETIREMENT_MESSAGE, file=sys.stderr)
    return EXIT_CONFIG


if __name__ == "__main__":
    raise SystemExit(main())
