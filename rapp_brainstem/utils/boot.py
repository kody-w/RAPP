#!/usr/bin/env python3
"""HTTP 410 tombstone for the retired target-owned boot launcher."""


def main() -> None:
    stderr = open(2, "w", closefd=False)
    try:
        print(
            "410 Gone: the target-owned legacy boot launcher is retired; "
            "see RAPP1_STATUS.md.",
            file=stderr,
        )
    finally:
        stderr.close()
    raise SystemExit(78)


if __name__ == "__main__":
    main()
