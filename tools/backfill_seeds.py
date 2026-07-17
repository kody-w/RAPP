"""Read-only migration planner for historical planted doors.

This target has no authenticated RAPP/1 section 13.3 authorization verifier.
The former backfill implementation silently minted a replacement identity and
wrote it when strict parsing failed. That path is retired: this module now
inspects, classifies, and plans only. It never mints, writes, or proposes a
replacement rappid.
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "tools"))

from door_address import (  # noqa: E402
    InvalidRappidError,
    door_from_rappid,
    parse_legacy_for_migration,
)
from rapp1_core import parse_rappid, strict_loads  # noqa: E402
from rapp1_core.errors import IdentityError  # noqa: E402


PLAN_SCHEMA = "rapp-backfill-plan/2.0"

SEEDS = [
    ("kody-w", "echo-brainstem", "twin", "Echo"),
    ("kody-w", "lumen-brainstem", "twin", "Lumen"),
    ("kody-w", "tide-brainstem", "twin", "Tide"),
    ("kody-w", "sim-demo-twin", "twin", "Sim Demo Twin"),
    ("kody-w", "twin", "twin", "Twin"),
    ("kody-w", "twin-private", "twin", "Twin (private)"),
    ("kody-w", "kody-twin", "twin", "Kody Twin"),
    ("kody-w", "wildhaven-ai-homes-twin", "twin", "Wildhaven AI Homes Twin"),
    ("kody-w", "pkstop-the-bean", "neighborhood", "Pkstop — The Bean"),
    ("kody-w", "pkstop-national-mall", "neighborhood", "Pkstop — National Mall"),
    (
        "kody-w",
        "pkstop-central-park-bandshell",
        "neighborhood",
        "Pkstop — Central Park Bandshell",
    ),
    (
        "kody-w",
        "pkstop-santa-monica-pier",
        "neighborhood",
        "Pkstop — Santa Monica Pier",
    ),
    (
        "kody-w",
        "pkstop-pike-place-market",
        "neighborhood",
        "Pkstop — Pike Place Market",
    ),
    ("kody-w", "rapp-test-neighbor", "neighborhood", "RAPP Test Neighbor"),
    ("kody-w", "sim-art-collective", "neighborhood", "Sim Art Collective"),
    (
        "kody-w",
        "microsoft-se-team-neighborhood",
        "neighborhood",
        "Microsoft SE Team",
    ),
]


def _gh(args: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(
        ["gh", *args], capture_output=True, text=True, check=False
    )
    return result.returncode, result.stdout, result.stderr


def _raw_fetch(owner: str, repo: str, path: str) -> tuple[int, bytes]:
    result, output, _ = _gh(
        ["api", f"/repos/{owner}/{repo}/contents/{path}"]
    )
    if result != 0:
        return 404, b""
    try:
        response = json.loads(output)
        if type(response) is not dict:
            raise ValueError("GitHub content response must be an object")
        encoded = response.get("content", "").replace("\n", "")
        return 200, base64.b64decode(encoded, validate=True) if encoded else b""
    except (ValueError, TypeError):
        return 502, b""


def _file_exists_in_repo(owner: str, repo: str, path: str) -> bool:
    code, _ = _raw_fetch(owner, repo, path)
    return code == 200


def _classify_identity(value: Any) -> dict[str, Any]:
    if type(value) is not str:
        return {
            "classification": "invalid",
            "original": value,
            "error": "rappid must be a string",
        }
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


def _owner_action(
    plan: dict[str, Any], identity: dict[str, Any], reason: str
) -> dict[str, Any]:
    plan.update(
        {
            "status": "OWNER_ACTION_REQUIRED",
            "identity": identity,
            "reason": reason,
            "actions": [],
            "required-actions": [
                "authenticate the section 13 registry from the owner anchor",
                "verify the applicable section 13.3 authorization",
                "perform any lawful identity or metadata migration outside this tool",
            ],
        }
    )
    return plan


def plan_for_seed(
    owner: str, repo: str, kind: str, display_name: str
) -> dict[str, Any]:
    """Return a read-only plan for one source repository."""

    plan: dict[str, Any] = {
        "schema": PLAN_SCHEMA,
        "repo": f"{owner}/{repo}",
        "display-name": display_name,
        "requested-kind": kind,
        "write-permitted": False,
        "authorization-verifier": "UNAVAILABLE",
        "proposed-rappid": None,
        "actions": [],
        "guidance": "RAPP1_STATUS.md",
    }
    code, body = _raw_fetch(owner, repo, "rappid.json")
    if code != 200 or not body:
        plan.update(
            {
                "status": "UNREACHABLE",
                "reason": f"rappid.json unavailable (HTTP {code})",
                "identity": {"classification": "unavailable"},
            }
        )
        return plan

    try:
        record = strict_loads(body)
        if type(record) is not dict:
            raise ValueError("rappid.json must be an object")
    except (TypeError, ValueError) as exc:
        return _owner_action(
            plan,
            {"classification": "invalid-record", "error": str(exc)},
            "strict identity record parsing failed",
        )

    identity = _classify_identity(record.get("rappid"))
    if identity["classification"] != "exact-rapp1":
        return _owner_action(
            plan,
            identity,
            "identity is not exact RAPP/1; silent reminting is prohibited",
        )
    if identity["owner"] != owner or identity["slug"] != repo:
        return _owner_action(
            plan,
            identity,
            "identity owner/slug does not match the source repository",
        )
    if record.get("kind") != kind:
        return _owner_action(
            plan,
            identity,
            "identity record kind does not match the requested seed kind",
        )
    try:
        door_from_rappid(identity["rappid"], identity_record=record)
    except InvalidRappidError as exc:
        return _owner_action(
            plan,
            identity,
            f"identity record is not a valid door: {exc}",
        )

    required_files = (
        ("facets.json", "Door URL Set section 9"),
        (".nojekyll", "Pages publishing requirement"),
        ("members.json", "Door URL Set section 8"),
        ("README.md", "human-readable description"),
    )
    for path, reason in required_files:
        if not _file_exists_in_repo(owner, repo, path):
            plan["actions"].append(
                {"path": path, "operation": "owner-managed-add", "reason": reason}
            )
    plan["identity"] = identity
    plan["status"] = "PLAN_REQUIRED" if plan["actions"] else "NO_ACTION"
    return plan


def patch_parents(
    seeds: list[tuple[str, str, str, str]],
    operator_rappid: str,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Plan parent-pointer owner actions without mutating any repository."""

    del dry_run
    report: dict[str, Any] = {
        "schema": PLAN_SCHEMA,
        "operation": "plan-parent-pointers",
        "write-permitted": False,
        "authorization-verifier": "UNAVAILABLE",
        "operator-rappid": operator_rappid,
        "results": [],
    }
    try:
        operator = parse_rappid(operator_rappid)
    except IdentityError as exc:
        report.update(
            {
                "status": "OWNER_ACTION_REQUIRED",
                "error": str(exc),
            }
        )
        return report

    for owner, repo, _kind, _display_name in seeds:
        row: dict[str, Any] = {
            "repo": f"{owner}/{repo}",
            "write-permitted": False,
        }
        if operator.owner != owner:
            row.update(
                {
                    "status": "OWNER_ACTION_REQUIRED",
                    "reason": "operator owner does not match source owner",
                }
            )
            report["results"].append(row)
            continue
        code, body = _raw_fetch(owner, repo, "rappid.json")
        try:
            record = strict_loads(body) if code == 200 and body else None
            if type(record) is not dict:
                raise ValueError("identity record unavailable or invalid")
            identity = parse_rappid(record.get("rappid"))
            if (identity.owner, identity.slug) != (owner, repo):
                raise ValueError("identity does not match source repository")
        except (IdentityError, TypeError, ValueError) as exc:
            row.update(
                {
                    "status": "OWNER_ACTION_REQUIRED",
                    "reason": str(exc),
                }
            )
        else:
            if record.get("parent_rappid") == operator_rappid:
                row["status"] = "NO_ACTION"
            else:
                row.update(
                    {
                        "status": "OWNER_ACTION_REQUIRED",
                        "reason": (
                            "parent change requires authenticated owner action"
                        ),
                        "planned-parent-rappid": operator_rappid,
                    }
                )
        report["results"].append(row)

    report["status"] = (
        "OWNER_ACTION_REQUIRED"
        if any(row["status"] == "OWNER_ACTION_REQUIRED" for row in report["results"])
        else "NO_ACTION"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="deprecated alias; planning is always read-only",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="retired write mode; always refused before repository access",
    )
    parser.add_argument("--only", default="", help="restrict by repository name")
    parser.add_argument("--owner", default="", help="restrict by source owner")
    parser.add_argument(
        "--patch-parents",
        default="",
        help="plan parent-pointer owner actions without writing",
    )
    args = parser.parse_args(argv)

    if args.apply:
        print(
            json.dumps(
                {
                    "schema": PLAN_SCHEMA,
                    "status": "RETIRED",
                    "write-permitted": False,
                    "error": "backfill apply mode is retired",
                    "guidance": "RAPP1_STATUS.md",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 3

    seeds = SEEDS
    if args.only:
        seeds = [seed for seed in seeds if seed[1] == args.only]
    if args.owner:
        seeds = [seed for seed in seeds if seed[0] == args.owner]
    if not seeds:
        print("error: no seeds matched filter", file=sys.stderr)
        return 2

    if args.patch_parents:
        report = patch_parents(seeds, args.patch_parents)
    else:
        plans = [plan_for_seed(*seed) for seed in seeds]
        report = {
            "schema": PLAN_SCHEMA,
            "status": (
                "OWNER_ACTION_REQUIRED"
                if any(
                    plan["status"] in ("OWNER_ACTION_REQUIRED", "UNREACHABLE")
                    for plan in plans
                )
                else (
                    "PLAN_REQUIRED"
                    if any(plan["status"] == "PLAN_REQUIRED" for plan in plans)
                    else "NO_ACTION"
                )
            ),
            "write-permitted": False,
            "plans": plans,
        }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "NO_ACTION" else 3


if __name__ == "__main__":
    sys.exit(main())
