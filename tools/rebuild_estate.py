#!/usr/bin/env python3
"""Fail-closed estate-rebuild planning entry point.

The retired implementation treated GitHub publication and code-search results
as sufficient input to reconstruct and apply an estate. Published material is
only an unverified observation; it does not establish identity, membership, or
owner authorization under RAPP/1 sections 10 and 13.

This module performs no local discovery, GitHub calls, repository walks, code
searches, or file writes. ``--apply`` and ``--out`` are retained only so old
invocations receive an explicit non-success refusal instead of mutating state.
Historical discovery logic remains available in git history, not as live code.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from rapp1_core import parse_rappid  # noqa: E402
from rapp1_core.errors import IdentityError  # noqa: E402
from rapp1_core.identity import validate_owner  # noqa: E402


REFUSAL_SCHEMA = "rapp-owner-authority-refusal/1.0"
REFUSAL_CODE = "authenticated-registry-unavailable"
REFUSAL_STATUS = "OWNER_AUTHORITY_REQUIRED"


def _invalid_request(detail: str) -> dict:
    return {
        "schema": REFUSAL_SCHEMA,
        "operation": "estate-rebuild",
        "ok": False,
        "accepted": False,
        "status": "INVALID_REQUEST",
        "mode": "plan-only",
        "plan_only": True,
        "apply_permitted": False,
        "local_state_mutation_permitted": False,
        "error": {
            "code": "invalid-request",
            "detail": detail,
        },
    }


def rebuild(
    handle: str,
    operator_rappid: str = "",
    on_progress=None,
    *,
    requested_apply: bool = False,
    requested_out: str = "",
) -> dict:
    """Return an owner-reviewed candidate plan and refuse discovery/apply."""
    try:
        owner = validate_owner(handle)
    except (IdentityError, TypeError) as exc:
        return _invalid_request(f"invalid exact handle: {exc}")

    candidate_identity = None
    if operator_rappid:
        try:
            parsed = parse_rappid(operator_rappid)
        except (IdentityError, TypeError) as exc:
            return _invalid_request(f"operator rappid invalid: {exc}")
        if parsed.owner != owner:
            return _invalid_request(
                "operator rappid owner does not match requested GitHub handle"
            )
        candidate_identity = str(parsed)

    if callable(on_progress):
        on_progress(
            "authenticated fresh section-13 authority unavailable; "
            "refusing discovery and apply"
        )

    return {
        "schema": REFUSAL_SCHEMA,
        "operation": "estate-rebuild",
        "ok": False,
        "accepted": False,
        "status": REFUSAL_STATUS,
        "mode": "plan-only",
        "plan_only": True,
        "apply_permitted": False,
        "local_state_mutation_permitted": False,
        "requested_apply": bool(requested_apply),
        "requested_out": requested_out or None,
        "target": {
            "owner": owner,
            "candidate_operator_rappid": candidate_identity,
        },
        "error": {
            "code": REFUSAL_CODE,
            "detail": (
                "No authenticated, fresh RAPP/1 section-13 registry rooted in "
                "an out-of-band estate-owner anchor is available. GitHub "
                "publication and code search cannot authorize an estate rebuild."
            ),
        },
        "candidate_plan": {
            "status": "owner-review-required",
            "owner_review_required": True,
            "executable": False,
            "steps": [
                "Authenticate the current section-13 registry and estate-owner anchor.",
                (
                    "Resolve the operator identity, succession, and revocation "
                    "state from that authenticated registry."
                ),
                (
                    "Collect publication data only as source-labelled, freshness-"
                    "preserving observations; do not infer membership from publication."
                ),
                (
                    "Present the resulting candidate estate for owner review and "
                    "require an explicit adoption receipt before any local write."
                ),
            ],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--handle",
        required=True,
        help="GitHub handle named by the requested candidate plan",
    )
    parser.add_argument(
        "--operator-rappid",
        default="",
        help="unverified candidate identity; never accepted from this tool",
    )
    parser.add_argument(
        "--out",
        default="",
        help="legacy flag; no output file is written",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="legacy flag; apply is always refused",
    )
    args = parser.parse_args(argv)

    result = rebuild(
        args.handle,
        args.operator_rappid,
        requested_apply=args.apply,
        requested_out=args.out,
    )
    print(json.dumps(result, indent=2))
    return 1


if __name__ == "__main__":
    sys.exit(main())
