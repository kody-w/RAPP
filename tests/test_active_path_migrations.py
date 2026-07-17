from __future__ import annotations

import importlib.util
import shutil
import sys
import types
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from rapp1_core import canonical_bytes, pack_egg, parse_rappid
from rapp1_core.errors import IdentityError
from rapp_brainstem.utils import boot, lineage_check
from rapp_brainstem.utils.lineage_check import check_lineage


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from import_peer_egg import import_egg, inspect_peer_egg  # noqa: E402
import private_estate_init  # noqa: E402
import rebuild_estate  # noqa: E402


RAPPID = f"rappid:@kody-w/offline-peer:{'a' * 64}"
UTC = "2026-07-16T22:41:23.842Z"


@pytest.fixture
def migration_dir():
    root = ROOT / "tests" / ".active-path-migration-test-data"
    path = root / str(uuid.uuid4())
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
        try:
            root.rmdir()
        except OSError:
            pass


def _structural_egg() -> bytes:
    return pack_egg(
        variant="organism",
        rappid=RAPPID,
        created_utc=UTC,
        payload={},
        files={
            "rappid.json": canonical_bytes({"rappid": RAPPID}),
            "soul.md": b"offline peer\n",
        },
    )


def test_peer_import_is_unverified_and_has_no_side_effects(migration_dir):
    egg = migration_dir / "peer.egg"
    egg.write_bytes(_structural_egg())
    destination = migration_dir / "imported"

    result = import_egg(egg, destination)

    assert result["operation"] == "import"
    assert result["ok"] is False
    assert result["imported"] is False
    assert result["status"] == "UNVERIFIED"
    assert result["trust-status"] == "UNVERIFIED"
    assert result["error"]["code"] == "authenticated-registry-unavailable"
    assert result["inspection"]["structurally-valid"] is True
    assert not destination.exists()
    assert list(migration_dir.iterdir()) == [egg]


def test_peer_inspection_never_reports_success_or_imports(migration_dir):
    egg = migration_dir / "peer.egg"
    egg.write_bytes(_structural_egg())

    result = inspect_peer_egg(egg)

    assert result["operation"] == "inspect"
    assert result["ok"] is False
    assert result["imported"] is False
    assert result["status"] == "UNVERIFIED"
    assert result["inspection"]["structurally-valid"] is True
    assert list(migration_dir.iterdir()) == [egg]


def test_legacy_peer_egg_is_invalid_without_writes(migration_dir):
    egg = migration_dir / "legacy.egg"
    egg.write_bytes(b'{"schema":"brainstem-egg/2.2-organism"}')

    result = import_egg(egg, migration_dir / "imported")

    assert result["ok"] is False
    assert result["imported"] is False
    assert result["status"] == "INVALID"
    assert result["inspection"]["structurally-valid"] is False
    assert list(migration_dir.iterdir()) == [egg]


def test_tutorial_hatcher_always_refuses_without_reading(migration_dir):
    sentinel = migration_dir / "must-not-be-read.egg"
    sentinel.write_bytes(b"not an egg")
    agents = types.ModuleType("agents")
    basic_agent = types.ModuleType("agents.basic_agent")

    class BasicAgent:
        def __init__(self, *args, **kwargs):
            pass

    basic_agent.BasicAgent = BasicAgent
    path = ROOT / "pages" / "tutorials" / "egg_hatcher_agent.py"
    spec = importlib.util.spec_from_file_location("retired_egg_hatcher", path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(
        sys.modules,
        {"agents": agents, "agents.basic_agent": basic_agent},
    ):
        assert spec.loader is not None
        spec.loader.exec_module(module)

    before = sentinel.read_bytes()
    result = module.EggHatcherAgent().perform(egg_path=str(sentinel))

    assert "410 Gone" in result
    assert "RAPP1_STATUS.md" in result
    assert sentinel.read_bytes() == before
    assert list(migration_dir.iterdir()) == [sentinel]
    assert "skill" not in path.read_text(encoding="utf-8").lower()


def test_private_estate_identity_loader_is_strict_and_uses_record_kind(
    migration_dir,
):
    identity = migration_dir / "rappid.json"
    identity.write_bytes(
        canonical_bytes({"rappid": RAPPID, "kind": "operator"})
    )
    assert private_estate_init._load_operator_identity(identity, "kody-w") == (
        RAPPID,
        "operator",
    )

    with pytest.raises(ValueError, match="does not match requested"):
        private_estate_init._load_operator_identity(identity, "bob")

    identity.write_bytes(canonical_bytes({"rappid": RAPPID, "kind": "twin"}))
    with pytest.raises(ValueError, match="must be 'operator'"):
        private_estate_init._load_operator_identity(identity, "kody-w")

    identity.write_bytes(
        b'{"rappid":"rappid:@kody-w/offline-peer:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",'
        b'"kind":"operator"}'
    )
    with pytest.raises(ValueError):
        private_estate_init._load_operator_identity(identity, "kody-w")


def test_private_estate_owner_mismatch_stops_before_side_effects(
    migration_dir, monkeypatch
):
    identity = migration_dir / "rappid.json"
    alice_rappid = f"rappid:@alice/offline-peer:{'a' * 64}"
    identity.write_bytes(
        canonical_bytes({"rappid": alice_rappid, "kind": "operator"})
    )
    original_expanduser = private_estate_init.os.path.expanduser

    def expanduser(path):
        if path == "~/.brainstem/rappid.json":
            return str(identity)
        return original_expanduser(path)

    monkeypatch.setattr(private_estate_init.os.path, "expanduser", expanduser)
    monkeypatch.setattr(
        private_estate_init,
        "_gh_repo_exists",
        lambda *args: (_ for _ in ()).throw(
            AssertionError("owner mismatch must stop before GitHub access")
        ),
    )

    result = private_estate_init.init_private_estate("bob", dry_run=True)

    assert result["ok"] is False
    assert "does not match requested GitHub handle" in result["error"]


def test_lineage_is_strict_and_reports_record_kind(migration_dir):
    identity = migration_dir / "rappid.json"
    parent = f"rappid:@kody-w/rapp:{'b' * 64}"
    identity.write_bytes(
        canonical_bytes(
            {
                "kind": "twin",
                "parent_rappid": parent,
                "rappid": RAPPID,
            }
        )
    )
    with patch(
        "rapp_brainstem.utils.lineage_check._repo_root",
        return_value=str(migration_dir),
    ), patch(
        "rapp_brainstem.utils.lineage_check._git_remote_owner_repo",
        return_value=None,
    ):
        result = check_lineage(str(migration_dir))
    assert result["status"] == "variant_initialized"
    assert result["kind"] == "twin"

    identity.write_bytes(
        b'{"kind":"variant","kind":"twin",'
        b'"parent_rappid":"rappid:@kody-w/rapp:'
        + b"b" * 64
        + b'","rappid":"rappid:@kody-w/offline-peer:'
        + b"a" * 64
        + b'"}'
    )
    with patch(
        "rapp_brainstem.utils.lineage_check._repo_root",
        return_value=str(migration_dir),
    ), patch(
        "rapp_brainstem.utils.lineage_check._git_remote_owner_repo",
        return_value=None,
    ):
        result = check_lineage(str(migration_dir))
    assert result["status"] == "lineage_mismatch"
    assert "unreadable rappid.json" in result["detail"]


@pytest.mark.parametrize(
    "value",
    [
        RAPPID,
        f"rappid:@{'a' * 39}/{'b' * 100}:{'c' * 64}",
        f"rappid:@{'a' * 40}/slug:{'c' * 64}",
        f"rappid:@owner/{'b' * 101}:{'c' * 64}",
        f"rappid:@Owner/slug:{'c' * 64}",
        f"rappid:@owner/slug:{'C' * 64}",
        f"rappid:@owner--bad/slug:{'c' * 64}",
        "rappid:v2:twin:@owner/slug:deadbeef",
        None,
    ],
)
def test_self_contained_lineage_identity_parser_matches_core(value):
    try:
        parsed = parse_rappid(value)
        expected = f"{parsed.owner}/{parsed.slug}"
    except (IdentityError, TypeError):
        expected = None
    assert lineage_check._rappid_owner_slug(value) == expected


def test_self_contained_lineage_location_parser_is_github_bound():
    valid = types.SimpleNamespace(
        returncode=0,
        stdout="https://github.com/Alice/Example.git\n",
    )
    with patch.object(lineage_check.subprocess, "run", return_value=valid):
        assert (
            lineage_check._git_remote_owner_repo(".")
            == "alice/example"
        )

    invalid = types.SimpleNamespace(
        returncode=0,
        stdout="https://example.invalid/alice/example.git\n",
    )
    with patch.object(lineage_check.subprocess, "run", return_value=invalid):
        with pytest.raises(ValueError, match="exact GitHub"):
            lineage_check._git_remote_owner_repo(".")


def test_boot_guard_fails_closed_when_lineage_import_fails():
    real_import = __import__

    def guarded_import(name, *args, **kwargs):
        if name == "lineage_check":
            raise ImportError("simulated missing guard")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=guarded_import):
        with pytest.raises(SystemExit) as refusal:
            boot._guard()
    assert refusal.value.code == 1


def test_boot_guard_fails_closed_on_invalid_lineage_status():
    module = types.ModuleType("lineage_check")
    module.check_lineage = lambda: {
        "status": "lineage_mismatch",
        "detail": "invalid identity",
    }
    with patch.dict(sys.modules, {"lineage_check": module}):
        with pytest.raises(SystemExit) as refusal:
            boot._guard()
    assert refusal.value.code == 1


def test_rebuild_never_derives_operator_identity_from_twin_kind(monkeypatch):
    candidate_rappid = f"rappid:@kody-w/kody-w-twin:{'d' * 64}"
    twin = {"rappid": candidate_rappid, "kind": "twin"}
    monkeypatch.setattr(rebuild_estate, "_raw_fetch_json", lambda *args: twin)
    assert rebuild_estate._try_conventional_repos("kody-w") == ""

    wrong_source = {"rappid": RAPPID, "kind": "operator"}
    monkeypatch.setattr(
        rebuild_estate, "_raw_fetch_json", lambda *args: wrong_source
    )
    assert rebuild_estate._try_conventional_repos("kody-w") == ""

    operator = {"rappid": candidate_rappid, "kind": "operator"}
    monkeypatch.setattr(
        rebuild_estate, "_raw_fetch_json", lambda *args: operator
    )
    assert (
        rebuild_estate._try_conventional_repos("kody-w")
        == candidate_rappid
    )
    source = (ROOT / "tools" / "rebuild_estate.py").read_text(encoding="utf-8")
    assert 'replace(":twin:", ":operator:"' not in source


def test_rebuild_operator_owner_mismatch_stops_before_discovery(monkeypatch):
    alice_rappid = f"rappid:@alice/offline-peer:{'a' * 64}"
    monkeypatch.setattr(
        rebuild_estate,
        "discover_created",
        lambda *args: (_ for _ in ()).throw(
            AssertionError("context mismatch must stop before discovery")
        ),
    )
    result = rebuild_estate.rebuild("bob", alice_rappid)
    assert result["ok"] is False
    assert "does not match requested GitHub handle" in result["error"]
