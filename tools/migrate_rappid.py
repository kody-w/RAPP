"""Produce a non-authoritative rappid migration plan without writing.

No authenticated RAPP/1 section 13.3 authorization verifier exists in this
repository. Consequently this tool never rewrites ``rappid.json``, never lifts
kind from a legacy string, and never synthesizes a replacement or re-anchor.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from door_address import (  # noqa: E402
    InvalidRappidError,
    parse_legacy_for_migration,
)
from rapp1_core import parse_rappid, strict_loads  # noqa: E402
from rapp1_core.errors import IdentityError  # noqa: E402
from rapp1_core.identity import validate_owner, validate_slug  # noqa: E402


PLAN_SCHEMA = "rapp-rappid-migration-plan/1.0"


def _location(owner: str | None, slug: str | None) -> dict[str, str] | None:
    if owner is None or slug is None:
        return None
    try:
        return {"owner": validate_owner(owner), "slug": validate_slug(slug)}
    except IdentityError:
        return None


def _classify(value: Any) -> dict[str, Any]:
    if type(value) is not str or not value:
        return {"classification": "missing-or-non-string", "original": value}
    try:
        parsed = parse_rappid(value)
    except IdentityError:
        try:
            observation = parse_legacy_for_migration(value)
        except InvalidRappidError as exc:
            return {
                "classification": "invalid",
                "original": value,
                "error": str(exc),
            }
        return {
            "classification": "legacy-quarantined",
            "observation": observation.as_dict(),
        }
    return {
        "classification": "exact-rapp1",
        "rappid": str(parsed),
        "owner": parsed.owner,
        "slug": parsed.slug,
    }


def plan_record(
    data: dict[str, Any], owner: str | None = None, slug: str | None = None
) -> dict[str, Any]:
    """Return a plan that contains no proposed identity and permits no write."""

    if type(data) is not dict:
        raise TypeError("identity record must be an object")
    current = _classify(data.get("rappid"))
    parent = _classify(data.get("parent_rappid"))
    record_kind = data.get("kind") if type(data.get("kind")) is str else None
    exact = current["classification"] == "exact-rapp1"
    requested_location = _location(owner, slug)
    context_matches = (
        exact
        and requested_location is not None
        and current["owner"] == requested_location["owner"]
        and current["slug"] == requested_location["slug"]
    )
    parent_requires_action = (
        data.get("parent_rappid") is not None
        and parent["classification"] != "exact-rapp1"
    )
    owner_action = not exact or not context_matches or parent_requires_action

    return {
        "schema": PLAN_SCHEMA,
        "status": "OWNER_ACTION_REQUIRED" if owner_action else "NO_ACTION",
        "write-permitted": False,
        "authorization-verifier": "UNAVAILABLE",
        "requested-location": requested_location,
        "context-binding": (
            "MATCH"
            if context_matches
            else "OWNER_SLUG_MISMATCH_OR_UNAVAILABLE"
        ),
        "identity": current,
        "parent-identity": parent,
        "record-kind": record_kind,
        "legacy-string-kind-authoritative": False,
        "proposed-rappid": None,
        "required-actions": (
            [
                "authenticate a fresh section 13 registry from an out-of-band owner anchor",
                "verify the applicable section 13.3 authorization and continuity proof",
                "issue the lawful re-anchor or re-genesis record before any identity write",
            ]
            if owner_action
            else []
        ),
        "guidance": "RAPP1_STATUS.md",
    }


def plan_file(
    path: str | Path, owner: str | None = None, slug: str | None = None
) -> dict[str, Any]:
    value = strict_loads(Path(path).read_bytes())
    if type(value) is not dict:
        raise ValueError("rappid.json must contain an object")
    return plan_record(value, owner, slug)


def _infer_location(repo_dir: Path) -> tuple[str, str] | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_dir), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    url = result.stdout.strip().removesuffix(".git")
    for prefix in (
        "https://github.com/",
        "http://github.com/",
        "git@github.com:",
        "ssh://git@github.com/",
    ):
        if url.startswith(prefix):
            parts = url[len(prefix) :].split("/")
            if len(parts) != 2:
                return None
            location = _location(parts[0].lower(), parts[1].lower())
            if location is None:
                return None
            return location["owner"], location["slug"]
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("repo_dir", help="repository containing rappid.json")
    parser.add_argument("--owner", help="location evidence for the plan")
    parser.add_argument("--slug", help="location evidence for the plan")
    args = parser.parse_args(argv)

    repo = Path(args.repo_dir)
    path = repo / "rappid.json"
    if not path.is_file():
        print(f"no rappid.json in {repo}", file=sys.stderr)
        return 2
    inferred = _infer_location(repo)
    owner = args.owner or (inferred[0] if inferred is not None else None)
    slug = args.slug or (inferred[1] if inferred is not None else None)
    try:
        plan = plan_file(path, owner, slug)
    except (OSError, TypeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "schema": PLAN_SCHEMA,
                    "status": "INVALID_INPUT",
                    "write-permitted": False,
                    "error": str(exc),
                    "guidance": "RAPP1_STATUS.md",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps(plan, indent=2, sort_keys=True))
    return 0 if plan["status"] == "NO_ACTION" else 3


if __name__ == "__main__":
    sys.exit(main())
