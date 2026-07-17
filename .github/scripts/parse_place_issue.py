#!/usr/bin/env python3
"""Parse a GitHub Issue Form body (place-submission.yml output) into key-value
pairs suitable for $GITHUB_OUTPUT.

Usage (in a workflow step):
    echo "$ISSUE_BODY" | python3 .github/scripts/parse_place_issue.py >> $GITHUB_OUTPUT

Outputs (one per line, key=value):
    place_name, display_name, slug, location, coordinates, description,
    photo_url, submitter, eligibility_total, eligibility_checked, ok

`ok` is "1" if every required field is present + every eligibility box is
checked, else "0" (with details on stderr).

Designed to be idempotent and conservative — silent on missing optional
fields, loud on validation failures.
"""

from __future__ import annotations

import re
import sys

# GitHub Issue Forms render each `body` element with `id` + `attributes.label`
# as a `### <label>` block followed by the value on subsequent lines.
# Map the labels we care about to GITHUB_OUTPUT keys.
LABEL_TO_KEY = {
    "Place name":                          "place_name",
    "Display name (what visitors see)":    "display_name",
    "Slug":                                "slug",
    "Location (city + region)":            "location",
    "Coordinates (lat,lng)":               "coordinates",
    "Why this place":                      "description",
    "Photo URL (optional)":                "photo_url",
    "Your GitHub handle (optional)":       "submitter",
}
REQUIRED = {"place_name", "display_name", "slug", "location", "coordinates", "description"}
EMPTY_MARKER = "_No response_"
EXPECTED_ELIGIBILITY = 10
LABEL_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", re.ASCII)


def parse(body: str) -> dict[str, str]:
    out: dict[str, str] = {}

    # Split on `### ` headers (start-of-line). The first chunk is whatever sits
    # above the first header (often empty for clean issue forms).
    chunks = re.split(r"^### ", body, flags=re.MULTILINE)
    for chunk in chunks[1:]:
        head, _, value = chunk.partition("\n")
        head = head.strip()
        value = value.strip()

        if head in LABEL_TO_KEY:
            key = LABEL_TO_KEY[head]
            if key in out:
                raise ValueError(f"duplicate issue field: {key}")
            if value == EMPTY_MARKER:
                value = ""
            # GitHub puts a blank line between header and value; trailing chunks
            # may include the next section's preamble. Stop at the first blank
            # line followed by anything that looks like the next field, or just
            # take the first paragraph for safety.
            value = value.split("\n\n")[0].strip()
            # Collapse internal newlines into spaces for single-line output safety.
            # Description may be multi-line; this is fine — a couple of paragraphs
            # become one paragraph, no info lost.
            value = re.sub(r"\s+", " ", value).strip()
            out[key] = value
        elif head.startswith("Eligibility"):
            if "eligibility_total" in out:
                raise ValueError("duplicate eligibility section")
            checked   = len(re.findall(r"^\s*-\s*\[[xX]\]", value, re.MULTILINE))
            unchecked = len(re.findall(r"^\s*-\s*\[\s*\]",  value, re.MULTILINE))
            out["eligibility_total"]   = str(checked + unchecked)
            out["eligibility_checked"] = str(checked)

    return out


def validate(parsed: dict[str, str]) -> tuple[bool, list[str]]:
    """Returns (ok, error_messages). True if every required field is present
    and every eligibility box is checked."""
    errors: list[str] = []

    for key in REQUIRED:
        if not parsed.get(key, "").strip():
            errors.append(f"missing required field: {key}")

    slug = parsed.get("slug", "")
    if slug and (len(slug) > 100 or LABEL_RE.fullmatch(slug) is None):
        errors.append(f"slug does not match the exact lowercase grammar: {slug!r}")

    submitter = parsed.get("submitter", "")
    if submitter and (
        len(submitter) > 39 or LABEL_RE.fullmatch(submitter) is None
    ):
        errors.append(
            "submitter does not match the exact lowercase owner grammar: "
            f"{submitter!r}"
        )

    coords = parsed.get("coordinates", "")
    if coords:
        match = re.fullmatch(
            r"\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*",
            coords,
        )
        if match is None:
            errors.append(f"coordinates not 'lat,lng' shaped: {coords!r}")
        else:
            latitude, longitude = map(float, match.groups())
            if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
                errors.append(f"coordinates outside valid ranges: {coords!r}")

    total   = int(parsed.get("eligibility_total",   "0") or "0")
    checked = int(parsed.get("eligibility_checked", "0") or "0")
    if total != EXPECTED_ELIGIBILITY:
        errors.append(
            "eligibility section must contain exactly "
            f"{EXPECTED_ELIGIBILITY} choices (found {total})"
        )
    elif checked < total:
        errors.append(f"eligibility incomplete: {checked}/{total} boxes checked")

    return (not errors, errors)


def emit_output(parsed: dict[str, str], ok: bool) -> None:
    """Print key=value lines to stdout in $GITHUB_OUTPUT format."""
    for key in ("place_name", "display_name", "slug", "location", "coordinates",
                "description", "photo_url", "submitter",
                "eligibility_total", "eligibility_checked"):
        value = parsed.get(key, "")
        # Single-line value (we collapsed newlines in parse()); safe to emit as
        # plain key=value. For genuinely multi-line values GitHub Actions wants
        # the heredoc form, but our values are pre-flattened.
        print(f"{key}={value}")
    print(f"ok={'1' if ok else '0'}")


def main(argv: list[str]) -> int:
    body = sys.stdin.read()
    if not body.strip():
        print("ok=0", file=sys.stdout)
        print("ERROR: empty issue body on stdin", file=sys.stderr)
        return 1

    try:
        parsed = parse(body)
    except ValueError as exc:
        print("ok=0", file=sys.stdout)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    ok, errors = validate(parsed)

    emit_output(parsed, ok)

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
