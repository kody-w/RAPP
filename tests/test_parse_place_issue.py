from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github" / "scripts" / "parse_place_issue.py"
SPEC = importlib.util.spec_from_file_location("parse_place_issue", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def issue_body(*, slug: str = "pkstop-town-square", submitter: str = "alice") -> str:
    checks = "\n".join(f"- [x] eligibility {index}" for index in range(10))
    return f"""### Place name
Town Square

### Display name (what visitors see)
Town Square

### Slug
{slug}

### Location (city + region)
Example, Maryland

### Coordinates (lat,lng)
39.0,-77.0

### Why this place
A durable public gathering place.

### Photo URL (optional)
_No response_

### Your GitHub handle (optional)
{submitter}

### Eligibility — every box must be checked
{checks}
"""


def test_exact_lowercase_place_fields_validate():
    parsed = MODULE.parse(issue_body())
    assert MODULE.validate(parsed) == (True, [])
    assert parsed["slug"] == "pkstop-town-square"
    assert parsed["submitter"] == "alice"


@pytest.mark.parametrize(
    "slug",
    [
        "Pkstop-town-square",
        "pkstop_town_square",
        "-pkstop",
        "pkstop-",
        "pkstop--town",
        "pkstop.town",
    ],
)
def test_non_exact_slug_is_rejected(slug):
    parsed = MODULE.parse(issue_body(slug=slug))
    ok, errors = MODULE.validate(parsed)
    assert ok is False
    assert any("exact lowercase grammar" in error for error in errors)


@pytest.mark.parametrize("submitter", ["@alice", "Alice", "alice_dev", "alice--dev"])
def test_non_exact_submitter_is_rejected(submitter):
    parsed = MODULE.parse(issue_body(submitter=submitter))
    ok, errors = MODULE.validate(parsed)
    assert ok is False
    assert any("owner grammar" in error for error in errors)


def test_duplicate_fields_and_incomplete_eligibility_fail_closed():
    with pytest.raises(ValueError, match="duplicate issue field"):
        MODULE.parse(issue_body() + "\n### Slug\nother\n")

    parsed = MODULE.parse(issue_body().replace("- [x] eligibility 9\n", ""))
    ok, errors = MODULE.validate(parsed)
    assert ok is False
    assert any("exactly 10 choices" in error for error in errors)


def test_workflow_has_no_legacy_planter_or_log_scraping():
    workflow = (
        ROOT / ".github" / "workflows" / "plant-approved-place.yml"
    ).read_text(encoding="utf-8")
    assert "installer/plant.sh" not in workflow
    assert "grep -o" not in workflow
    assert "/tmp" not in workflow
    assert "PLANT_PAT" not in workflow
    assert "strict structured result" in workflow
    assert "exit 78" in workflow
    assert workflow.index("Validate issue body before side effects") < workflow.index(
        "Fail closed before planting"
    )
