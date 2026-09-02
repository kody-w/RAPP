#!/usr/bin/env python3
"""Retired Metropolis activity harvester.

The former scheduled browser-catalog updater is retained at its known path as
an inert compatibility tombstone. Historical snapshots remain in git; this
entrypoint performs no network request and writes no repository files.
"""

from __future__ import annotations

import json


RESULT = {
    "status": "gone",
    "code": "metropolis-activity-harvester-retired",
    "accepted": False,
    "message": (
        "The pre-acceptance Metropolis browser catalog and live-presence "
        "harvester are retired. See RAPP1_STATUS.md."
    ),
}


def main() -> int:
    print(json.dumps(RESULT, sort_keys=True))
    return 78


if __name__ == "__main__":
    raise SystemExit(main())
