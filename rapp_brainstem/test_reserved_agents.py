"""Tests for utils/reserved_agents/ + lifecycle_organ.

Reserved agents are first-party lifecycle code shipped *with* the kernel
but explicitly NOT auto-discovered by the agents/*_agent.py glob. They're
invoked on demand by the lifecycle organ, which is the LLM's only
surface for triggering kernel-level operations (upgrade, etc).

Run:   python3 -m pytest rapp_brainstem/test_reserved_agents.py -v
"""

from __future__ import annotations

import glob
import importlib.util
import json
import os
import sys
import tempfile

import pytest


HERE = os.path.dirname(os.path.abspath(__file__))
RESERVED_DIR = os.path.join(HERE, "utils", "reserved_agents")
ORGANS_DIR = os.path.join(HERE, "utils", "organs")
AGENTS_DIR = os.path.join(HERE, "agents")


def _load_module(filepath: str, name: str):
    """Load a Python file as a module without polluting sys.modules permanently."""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    spec = importlib.util.spec_from_file_location(name, filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ── Discovery tests ──────────────────────────────────────────────────────

def test_reserved_agents_dir_exists():
    """The reserved_agents directory must exist as the staging area."""
    assert os.path.isdir(RESERVED_DIR), f"missing: {RESERVED_DIR}"


def test_reserved_agents_has_init():
    """__init__.py is required so reserved_agents is importable as a package."""
    init = os.path.join(RESERVED_DIR, "__init__.py")
    assert os.path.isfile(init), f"missing: {init}"


def test_reserved_agents_NOT_picked_up_by_kernel_glob():
    """Kernel agent loader uses agents/*_agent.py — reserved agents must be invisible."""
    pattern = os.path.join(AGENTS_DIR, "*_agent.py")
    discovered = [os.path.basename(p) for p in glob.glob(pattern)]
    # If any file from reserved_agents/ leaked into the agents/ glob, fail.
    reserved_files = [
        os.path.basename(p)
        for p in glob.glob(os.path.join(RESERVED_DIR, "*_agent.py"))
    ]
    assert reserved_files, "reserved_agents/ has no *_agent.py files yet"
    for rf in reserved_files:
        assert rf not in discovered, (
            f"reserved agent {rf} leaked into kernel discovery"
        )


# ── upgrade_agent contract ───────────────────────────────────────────────

@pytest.fixture
def upgrade_agent():
    """Import via package path so monkeypatch in tests reaches the same module
    the agent's internal calls resolve against."""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import utils.reserved_agents.upgrade_agent as mod
    cls = getattr(mod, "UpgradeAgent", None)
    assert cls is not None, "upgrade_agent.py must export class UpgradeAgent"
    return cls()


def test_upgrade_agent_follows_basic_contract(upgrade_agent):
    """Reserved agents must follow the same BasicAgent single-file contract."""
    assert hasattr(upgrade_agent, "name") and upgrade_agent.name
    assert hasattr(upgrade_agent, "metadata") and isinstance(upgrade_agent.metadata, dict)
    assert "description" in upgrade_agent.metadata
    assert "parameters" in upgrade_agent.metadata
    assert callable(upgrade_agent.perform)


def test_upgrade_agent_check_returns_version_shape(upgrade_agent, monkeypatch):
    """action=check returns JSON with current_version, latest_version, needs_upgrade."""
    # Stub the remote-fetch so we don't hit the network in tests.
    import utils.reserved_agents.upgrade_agent as ua_mod
    monkeypatch.setattr(ua_mod, "_fetch_remote_version", lambda: "9.9.9")
    raw = upgrade_agent.perform(action="check")
    payload = json.loads(raw)
    assert "current_version" in payload
    assert "latest_version" in payload
    assert "needs_upgrade" in payload
    assert payload["latest_version"] == "9.9.9"


def test_upgrade_agent_apply_without_confirm_refuses(upgrade_agent):
    """action=apply WITHOUT confirm=True returns a refusal mentioning confirm."""
    raw = upgrade_agent.perform(action="apply")
    payload = json.loads(raw)
    assert payload.get("ok") is False
    assert "confirm" in (payload.get("error") or "").lower() or \
           "confirm" in (payload.get("hint") or "").lower()


def test_upgrade_agent_unknown_action(upgrade_agent):
    """Unknown action returns ok=false with an error."""
    raw = upgrade_agent.perform(action="nuke-everything")
    payload = json.loads(raw)
    assert payload.get("ok") is False
    assert "unknown" in (payload.get("error") or "").lower() or \
           "invalid" in (payload.get("error") or "").lower()


# ── lifecycle_organ contract ─────────────────────────────────────────────

@pytest.fixture
def lifecycle_organ():
    path = os.path.join(ORGANS_DIR, "lifecycle_organ.py")
    assert os.path.isfile(path), f"missing: {path}"
    return _load_module(path, "_test_lifecycle_organ")


def test_lifecycle_organ_has_name_and_handle(lifecycle_organ):
    """Organ contract: module exports `name` (str) + `handle(method, path, body)`."""
    assert getattr(lifecycle_organ, "name", None) == "lifecycle"
    assert callable(getattr(lifecycle_organ, "handle", None))


def test_lifecycle_organ_catalog_lists_upgrade(lifecycle_organ):
    """GET / returns a catalog including upgrade_agent's metadata."""
    result, status = lifecycle_organ.handle("GET", "", {})
    assert status == 200
    assert isinstance(result, dict)
    assert "agents" in result
    names = [a.get("name") for a in result["agents"]]
    assert "upgrade_brainstem" in names or any("upgrade" in (n or "") for n in names)


def test_lifecycle_organ_upgrade_check_no_confirm(lifecycle_organ, monkeypatch):
    """POST /upgrade with action=check returns version data, no confirm needed."""
    import utils.reserved_agents.upgrade_agent as ua_mod
    monkeypatch.setattr(ua_mod, "_fetch_remote_version", lambda: "9.9.9")
    result, status = lifecycle_organ.handle("POST", "upgrade", {"action": "check"})
    assert status == 200
    assert "current_version" in result
    assert "latest_version" in result


def test_lifecycle_organ_upgrade_apply_requires_confirm(lifecycle_organ, monkeypatch):
    """POST /upgrade with action=apply WITHOUT confirm:true returns a dry-run refusal."""
    import utils.reserved_agents.upgrade_agent as ua_mod
    monkeypatch.setattr(ua_mod, "_fetch_remote_version", lambda: "9.9.9")
    result, status = lifecycle_organ.handle("POST", "upgrade", {"action": "apply"})
    # Either 400 (rejected at organ level) or 200 with ok=false (rejected at agent level).
    assert status in (200, 400)
    if status == 200:
        assert result.get("ok") is False


def test_lifecycle_organ_unknown_route(lifecycle_organ):
    """Unknown route returns 404 with an error."""
    result, status = lifecycle_organ.handle("POST", "nuclear-launch", {})
    assert status == 404
    assert "error" in result


def test_lifecycle_organ_logs_calls(lifecycle_organ, monkeypatch, tmp_path):
    """Every organ call appends to lifecycle.log under HOME/.brainstem/."""
    monkeypatch.setenv("HOME", str(tmp_path))
    # Reload the organ module so it picks up the new HOME for log path resolution.
    # (Or the organ should resolve HOME on each call — that's fine too.)
    lifecycle_organ.handle("GET", "", {})
    log_path = os.path.join(str(tmp_path), ".brainstem", "lifecycle.log")
    assert os.path.isfile(log_path), f"lifecycle.log not written at {log_path}"
    content = open(log_path).read()
    assert content.strip(), "lifecycle.log is empty after a call"
