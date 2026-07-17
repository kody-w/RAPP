#!/usr/bin/env python3
"""Fail-closed tombstone for the nonconformant release signer."""

import sys


def main() -> int:
    print(
        "sign_release.py: 410 Gone\n\n"
        "Legacy release signing is retired. This command will not create "
        "keys, signatures, attestations, or verification-shaped output.\n"
        "Maintainers: see RAPP1_STATUS.md.",
        file=sys.stderr,
    )
    return 78


if __name__ == "__main__":
    raise SystemExit(main())
