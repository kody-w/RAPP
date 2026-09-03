#!/usr/bin/env python3
"""Fail-closed private-estate initialization plan.

The former implementation created and populated a GitHub repository and then
wrote local secret state from an unauthenticated local identity record. That
behavior is retired. Publication and local identity are not owner authority
under RAPP/1 section 13.

This target-owned entry point is intentionally plan-only. It performs no
GitHub calls, creates no repository, writes no files, mints no secret, and
never emits a success-shaped initialization or commitment result. Historical
implementation details remain available in git history rather than through a
live mutation path.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from rapp1_core.errors import IdentityError  # noqa: E402
from rapp1_core.identity import validate_owner  # noqa: E402


REFUSAL_SCHEMA = "rapp-owner-authority-refusal/1.0"
REFUSAL_CODE = "authenticated-registry-unavailable"
REFUSAL_STATUS = "OWNER_AUTHORITY_REQUIRED"


def _invalid_request(operation: str, detail: str) -> dict:
    return {
        "schema": REFUSAL_SCHEMA,
        "operation": operation,
        "ok": False,
        "accepted": False,
        "status": "INVALID_REQUEST",
        "mode": "plan-only",
        "plan_only": True,
        "apply_permitted": False,
        "repository_mutation_permitted": False,
        "local_state_mutation_permitted": False,
        "error": {
            "code": "invalid-request",
            "detail": detail,
        },
    }


def _authority_refusal(
    github_handle: str,
    *,
    operation: str,
    requested_mode: str,
) -> dict:
    try:
        owner = validate_owner(github_handle)
    except (IdentityError, TypeError) as exc:
        return _invalid_request(operation, f"invalid exact owner: {exc}")

    slug = f"{owner}/rapp-estate-private"
    return {
        "schema": REFUSAL_SCHEMA,
        "operation": operation,
        "ok": False,
        "accepted": False,
        "status": REFUSAL_STATUS,
        "mode": "plan-only",
        "requested_mode": requested_mode,
        "plan_only": True,
        "apply_permitted": False,
        "repository_mutation_permitted": False,
        "local_state_mutation_permitted": False,
        "target": {
            "owner": owner,
            "repository": slug,
        },
        "error": {
            "code": REFUSAL_CODE,
            "detail": (
                "No authenticated, fresh RAPP/1 section-13 registry rooted in "
                "an out-of-band estate-owner anchor is available to authorize "
                "this operation."
            ),
        },
        "candidate_plan": {
            "status": "owner-review-required",
            "owner_review_required": True,
            "executable": False,
            "steps": [
                "Authenticate a fresh section-13 registry from the estate-owner anchor.",
                (
                    "Verify an owner-authorized record that names this exact "
                    f"operation and target repository {slug}."
                ),
                (
                    "Use a separately reviewed implementation that preserves "
                    "the authority evidence and produces an explicit adoption receipt."
                ),
            ],
        },
    }


def init_private_estate(github_handle: str, dry_run: bool = False) -> dict:
    """Return a non-executable owner-authority plan; never initialize state."""
    return _authority_refusal(
        github_handle,
        operation="private-estate-initialize",
        requested_mode="legacy-dry-run" if dry_run else "legacy-apply",
    )


def verify_commitment(github_handle: str) -> dict:
    """Refuse commitment acceptance without authenticated fresh authority."""
    return _authority_refusal(
        github_handle,
        operation="private-estate-commitment-verify",
        requested_mode="observation",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--handle",
        required=True,
        help="GitHub handle named by the requested candidate plan",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="legacy flag; the tool is always plan-only and always refuses apply",
    )
    parser.add_argument(
        "--verify-commitment",
        action="store_true",
        help="request a non-accepting commitment observation plan",
    )
    args = parser.parse_args(argv)

    if args.verify_commitment:
        result = verify_commitment(args.handle)
    else:
        result = init_private_estate(args.handle, dry_run=args.dry_run)

    print(json.dumps(result, indent=2))
    return 1


if __name__ == "__main__":
    sys.exit(main())
