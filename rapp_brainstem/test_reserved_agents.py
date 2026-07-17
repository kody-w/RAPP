"""Retirement assertions for the removed reserved-agent capability path."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_reserved_agent_tree_remains_absent():
    assert not (ROOT / "rapp_brainstem/utils/reserved_agents").exists()


def test_lifecycle_organ_remains_absent():
    assert not (
        ROOT / "rapp_brainstem/utils/organs/lifecycle_organ.py"
    ).exists()


def test_default_agent_set_has_no_hidden_lifecycle_capability():
    agents = ROOT / "rapp_brainstem/agents"
    discovered = sorted(path.name for path in agents.glob("*_agent.py"))
    assert discovered == [
        "basic_agent.py",
        "context_memory_agent.py",
        "hacker_news_agent.py",
        "manage_memory_agent.py",
    ]
    assert all("upgrade" not in name for name in discovered)
