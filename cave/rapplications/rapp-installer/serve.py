#!/usr/bin/env python3
"""Fail-closed tombstone for the retired cave installer runtime."""

from __future__ import annotations

import sys


MESSAGE = """serve.py: 410 Gone

The target-owned cave installer runtime is retired. It will not start a
server, import a kernel, or expose direct agent execution.

Maintainers: see RAPP1_STATUS.md before restoring a runtime.
"""


def main() -> int:
    print(MESSAGE, file=sys.stderr)
    return 78


if __name__ == "__main__":
    raise SystemExit(main())
