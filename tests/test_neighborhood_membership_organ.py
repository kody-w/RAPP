"""Retirement assertions for the removed neighborhood membership organ."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ORGAN = (
    ROOT
    / "rapp_brainstem"
    / "utils"
    / "organs"
    / "neighborhood_membership_organ.py"
)


def test_neighborhood_membership_organ_remains_absent():
    assert not ORGAN.exists()


def test_no_default_agent_reintroduces_membership_capability():
    agents = ROOT / "rapp_brainstem" / "agents"
    assert not any("neighborhood" in path.name for path in agents.glob("*.py"))


def test_retirement_is_in_the_protocol_test_inventory():
    inventory = (
        ROOT / "tests/fixtures/rapp1-retired-test-inventory.json"
    ).read_text(encoding="utf-8")
    assert "tests/test_neighborhood_membership_organ.py" in inventory
    assert "explicit_retirement_assertions" in inventory
