#!/usr/bin/env python3
"""Fail-closed tombstone for the retired wildcard TLS proxy."""

import sys


def main() -> int:
    print(
        "tls_proxy.py: 410 Gone\n\n"
        "The wildcard proxy to the immutable tool-capable grail is retired. "
        "It will not generate keys, bind a listener, forward routes, add CORS "
        "headers, or expose the legacy /chat endpoint.\n"
        "Use only the loopback pre-acceptance facade documented in "
        "rapp_brainstem/RAPP1_FACADE.md.",
        file=sys.stderr,
    )
    return 78


if __name__ == "__main__":
    raise SystemExit(main())
