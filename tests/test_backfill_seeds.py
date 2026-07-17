from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import backfill_seeds  # noqa: E402


def _record(rappid: str, kind: str = "twin") -> bytes:
    return json.dumps(
        {"schema": "rapp/1", "rappid": rappid, "kind": kind},
        separators=(",", ":"),
    ).encode()


def test_legacy_identity_is_owner_action_without_mint_or_write(monkeypatch):
    legacy = f"rappid:@alice/example:{'a' * 32}"
    monkeypatch.setattr(
        backfill_seeds,
        "_raw_fetch",
        lambda *args: (200, _record(legacy)),
    )

    def unexpected_probe(*args):
        raise AssertionError("legacy identity must stop before file probes")

    monkeypatch.setattr(
        backfill_seeds, "_file_exists_in_repo", unexpected_probe
    )
    plan = backfill_seeds.plan_for_seed(
        "alice", "example", "twin", "Example"
    )

    assert plan["status"] == "OWNER_ACTION_REQUIRED"
    assert plan["write-permitted"] is False
    assert plan["proposed-rappid"] is None
    assert plan["identity"]["classification"] == "legacy-quarantined"
    assert plan["actions"] == []

    source = (ROOT / "tools" / "backfill_seeds.py").read_text()
    assert "uuid4" not in source
    assert "def _put_file" not in source


def test_source_identity_context_mismatch_requires_owner_action(monkeypatch):
    alice_identity = f"rappid:@alice/example:{'b' * 64}"
    monkeypatch.setattr(
        backfill_seeds,
        "_raw_fetch",
        lambda *args: (200, _record(alice_identity)),
    )
    monkeypatch.setattr(
        backfill_seeds,
        "_file_exists_in_repo",
        lambda *args: (_ for _ in ()).throw(
            AssertionError("mismatched identity must stop before file probes")
        ),
    )

    plan = backfill_seeds.plan_for_seed(
        "bob", "example", "twin", "Example"
    )

    assert plan["status"] == "OWNER_ACTION_REQUIRED"
    assert "does not match the source repository" in plan["reason"]
    assert plan["actions"] == []


def test_exact_matching_identity_produces_read_only_plan(monkeypatch):
    identity = f"rappid:@alice/example:{'c' * 64}"
    monkeypatch.setattr(
        backfill_seeds,
        "_raw_fetch",
        lambda *args: (200, _record(identity)),
    )
    monkeypatch.setattr(
        backfill_seeds, "_file_exists_in_repo", lambda *args: False
    )

    plan = backfill_seeds.plan_for_seed(
        "alice", "example", "twin", "Example"
    )

    assert plan["status"] == "PLAN_REQUIRED"
    assert plan["write-permitted"] is False
    assert plan["proposed-rappid"] is None
    assert {action["path"] for action in plan["actions"]} == {
        "facets.json",
        ".nojekyll",
        "members.json",
        "README.md",
    }


def test_apply_mode_refuses_before_repository_access(monkeypatch, capsys):
    monkeypatch.setattr(
        backfill_seeds,
        "_raw_fetch",
        lambda *args: (_ for _ in ()).throw(
            AssertionError("retired apply mode must not read repositories")
        ),
    )

    status = backfill_seeds.main(["--apply"])
    result = json.loads(capsys.readouterr().out)

    assert status == 3
    assert result["status"] == "RETIRED"
    assert result["write-permitted"] is False
