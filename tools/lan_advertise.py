#!/usr/bin/env python3
"""Fail-closed tombstone for retired LAN advertisement."""

import sys


def main() -> int:
    print(
        "lan_advertise.py: 410 Gone\n\n"
        "Legacy LAN advertisement is retired and will not publish a service "
        "or synthesize protocol records.\n"
        "Maintainers: see RAPP1_STATUS.md.",
        file=sys.stderr,
    )
    return 78


if __name__ == "__main__":
    raise SystemExit(main())
