#!/usr/bin/env python3
"""Embed pages/about/prompts.json into pages/about/prompts.html.

The HTML works with either an embedded data block or a fetch(prompts.json)
fallback — embedding makes the file self-contained for offline / file://
viewing. Re-run after editing prompts.json:

    python3 tools/embed_prompts.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "pages" / "about" / "prompts.json"
HTML = ROOT / "pages" / "about" / "prompts.html"

MARKER_START = '<script id="prompts-data" type="application/json">'
MARKER_END = "</script>"


def render_embedded(payload: dict, html: str) -> str:
    """Return the HTML with its prompt data block replaced."""
    i = html.find(MARKER_START)
    if i == -1:
        raise ValueError(f"no embed marker {MARKER_START!r}")
    j = html.find(MARKER_END, i)
    if j == -1:
        raise ValueError("no closing </script> after embed marker")
    new_block = MARKER_START + "\n" + json.dumps(payload, indent=2) + "\n"
    return html[:i] + new_block + html[j:]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if prompts.html is stale without writing it",
    )
    arguments = parser.parse_args(argv)
    if not DATA.exists():
        print(f"missing {DATA}", file=sys.stderr)
        return 1
    if not HTML.exists():
        print(f"missing {HTML}", file=sys.stderr)
        return 1

    payload = json.loads(DATA.read_text())
    html = HTML.read_text()
    try:
        expected = render_embedded(payload, html)
    except ValueError as error:
        print(f"{error} in {HTML}", file=sys.stderr)
        return 1
    if arguments.check:
        if expected != html:
            print(
                f"{HTML.relative_to(ROOT)} is stale; "
                "run python3 tools/embed_prompts.py",
                file=sys.stderr,
            )
            return 1
        print(f"{HTML.relative_to(ROOT)} prompt data is current")
        return 0

    HTML.write_text(expected, encoding="utf-8")
    print(
        f"embedded {len(payload['prompts'])} prompts "
        f"into {HTML.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
