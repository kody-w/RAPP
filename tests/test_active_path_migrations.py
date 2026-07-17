from __future__ import annotations

import importlib.util
import shutil
import sys
import types
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from rapp1_core import canonical_bytes, pack_egg, parse_rappid, strict_loads
from rapp1_core.errors import CanonicalizationError, IdentityError
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


def _prepare_private_estate_init(migration_dir, monkeypatch):
    identity = migration_dir / "rappid.json"
    identity.write_bytes(canonical_bytes({"rappid": RAPPID, "kind": "operator"}))
    original_expanduser = private_estate_init.os.path.expanduser

    def expanduser(path):
        if path == "~/.brainstem/rappid.json":
            return str(identity)
        return original_expanduser(path)

    monkeypatch.setattr(private_estate_init.os.path, "expanduser", expanduser)
    monkeypatch.setattr(
        private_estate_init, "_SECRET_PATH", migration_dir / "secret"
    )
    monkeypatch.setattr(
        private_estate_init, "_LOCAL_MAP_PATH", migration_dir / "map.json"
    )
    monkeypatch.setattr(private_estate_init, "_gh_repo_exists", lambda slug: True)


def test_private_estate_put_failure_has_no_local_or_success_shape(
    migration_dir, monkeypatch
):
    _prepare_private_estate_init(migration_dir, monkeypatch)
    writes = []

    def put(_slug, path, _body, _message):
        writes.append(path)
        return (True, "written") if len(writes) == 1 else (False, "injected PUT failure")

    monkeypatch.setattr(private_estate_init, "_gh_put_file", put)
    monkeypatch.setattr(
        private_estate_init,
        "_gh_read_file",
        lambda *args: (_ for _ in ()).throw(
            AssertionError("failed PUT must stop before verification")
        ),
    )
    monkeypatch.setattr(
        private_estate_init,
        "_normalized_state_hash",
        lambda *args: (_ for _ in ()).throw(
            AssertionError("failed PUT must not compute a commitment")
        ),
    )
    monkeypatch.setattr(
        private_estate_init,
        "_ensure_secret",
        lambda: (_ for _ in ()).throw(
            AssertionError("failed PUT must not create local state")
        ),
    )

    result = private_estate_init.init_private_estate("kody-w")

    assert result["ok"] is False
    assert result["status"] == "PARTIAL_REMOTE_WRITE"
    assert result["publish_permitted"] is False
    assert [row["path"] for row in result["partial_remote_writes"]] == ["meta.json"]
    assert result["files_failed"][0]["path"] == "README.md"
    assert "recovery" in result
    assert "private_estate_commitment" not in result
    assert "next_step" not in result
    assert not (migration_dir / "secret").exists()
    assert not (migration_dir / "map.json").exists()


def test_private_estate_unverified_puts_have_no_local_or_success_shape(
    migration_dir, monkeypatch
):
    _prepare_private_estate_init(migration_dir, monkeypatch)
    monkeypatch.setattr(
        private_estate_init,
        "_gh_put_file",
        lambda _slug, _path, _body, _message: (True, "written"),
    )
    monkeypatch.setattr(
        private_estate_init,
        "_gh_read_file",
        lambda _slug, path: (
            (False, None, "injected verification failure")
            if path == "README.md"
            else (True, b"wrong bytes", "verified")
        ),
    )
    monkeypatch.setattr(
        private_estate_init,
        "_gh_list_tree_checked",
        lambda *args: (_ for _ in ()).throw(
            AssertionError("byte verification failure must stop before tree lookup")
        ),
    )
    monkeypatch.setattr(
        private_estate_init,
        "_normalized_state_hash",
        lambda *args: (_ for _ in ()).throw(
            AssertionError("unverified PUT must not compute a commitment")
        ),
    )
    monkeypatch.setattr(
        private_estate_init,
        "_ensure_secret",
        lambda: (_ for _ in ()).throw(
            AssertionError("unverified PUT must not create local state")
        ),
    )

    result = private_estate_init.init_private_estate("kody-w")

    assert result["ok"] is False
    assert result["status"] == "REMOTE_VERIFICATION_FAILED"
    assert result["publish_permitted"] is False
    assert len(result["partial_remote_writes"]) == 4
    assert result["verification_failures"]
    assert "private_estate_commitment" not in result
    assert "next_step" not in result
    assert not (migration_dir / "secret").exists()
    assert not (migration_dir / "map.json").exists()


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


def test_self_contained_lineage_loads_whole_record_like_strict_core(
    migration_dir,
):
    record = canonical_bytes(
        {
            "kind": "variant",
            "parent_rappid": f"rappid:@kody-w/rapp:{'b' * 64}",
            "rappid": RAPPID,
        }
    )
    identity = migration_dir / "rappid.json"
    identity.write_bytes(record)

    assert lineage_check._load_identity_record(identity) == strict_loads(record)


@pytest.mark.parametrize(
    "record",
    [
        b'{"kind":"variant","kind":"twin"}',
        b'{"bad":"\\ud800"}',
        b'{"bad":333333333.33333329}',
        b'{"bad":9007199254740993}',
        b'{"bad":' + (b"[" * 65) + b"null" + (b"]" * 65) + b"}",
    ],
)
def test_self_contained_lineage_rejects_whole_record_when_strict_core_does(
    migration_dir, record
):
    identity = migration_dir / "rappid.json"
    identity.write_bytes(record)

    with pytest.raises(CanonicalizationError):
        strict_loads(record)
    with pytest.raises((TypeError, ValueError)):
        lineage_check._load_identity_record(identity)


def test_self_contained_lineage_rejects_canonical_expansion_over_mib(
    migration_dir,
):
    prefix = b'{"kind":"variant","numbers":['
    numbers = b",".join([b"1e20"] * 50_000)
    suffix = (
        b'],"parent_rappid":"rappid:@kody-w/rapp:'
        + (b"b" * 64)
        + b'","rappid":"rappid:@kody-w/offline-peer:'
        + (b"a" * 64)
        + b'"}'
    )
    record = prefix + numbers + suffix
    record += b" " * (260_215 - len(record))
    assert len(record) == 260_215
    identity = migration_dir / "rappid.json"
    identity.write_bytes(record)

    with pytest.raises(CanonicalizationError):
        strict_loads(record)
    with pytest.raises(ValueError, match="canonical-size upper bound"):
        lineage_check._load_identity_record(identity)


def test_self_contained_lineage_preserves_raw_record_bound(migration_dir):
    identity = migration_dir / "rappid.json"
    identity.write_bytes(
        b'{"kind":"variant"}'
        + b" " * lineage_check.MAX_IDENTITY_RECORD_BYTES
    )

    with pytest.raises(ValueError, match="exceeds 1 MiB"):
        lineage_check._load_identity_record(identity)


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


def test_boot_launcher_is_an_unconditional_410_tombstone(capfd):
    assert not hasattr(boot, "_guard")
    with pytest.raises(SystemExit) as refusal:
        boot.main()
    assert refusal.value.code == 78
    assert "410 Gone" in capfd.readouterr().err


def test_boot_launcher_has_no_import_or_execution_path():
    source = Path(boot.__file__).read_text(encoding="utf-8")
    for marker in (
        "import ",
        "lineage_check",
        "brainstem.py",
        "subprocess",
        "os.",
        "sys.",
        "exec",
    ):
        assert marker not in source


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


@pytest.mark.parametrize(
    ("failed_phase", "expected_phase"),
    [
        ("repositories", "repository-listing"),
        ("memberships", "code-search"),
    ],
)
def test_rebuild_incomplete_discovery_refuses_apply_and_preserves_estate(
    migration_dir, monkeypatch, failed_phase, expected_phase
):
    existing = migration_dir / "estate.json"
    original = b'{"existing":"estate must survive byte-for-byte"}\n'
    existing.write_bytes(original)

    if failed_phase == "repositories":
        monkeypatch.setattr(
            rebuild_estate,
            "discover_created",
            lambda *args: ([], [], ["injected repository API failure"]),
        )
        monkeypatch.setattr(
            rebuild_estate,
            "discover_memberships",
            lambda *args: (_ for _ in ()).throw(
                AssertionError("fatal repository discovery must stop rebuild")
            ),
        )
    else:
        monkeypatch.setattr(
            rebuild_estate, "discover_created", lambda *args: ([], [], [])
        )
        monkeypatch.setattr(
            rebuild_estate,
            "discover_memberships",
            lambda *args: ([], [], ["injected code-search failure"]),
        )

    result = rebuild_estate.rebuild("kody-w", RAPPID)
    assert result["ok"] is False
    assert result["status"] == "DISCOVERY_INCOMPLETE"
    assert result["phase"] == expected_phase
    assert result["apply_permitted"] is False

    original_expanduser = rebuild_estate.os.path.expanduser
    monkeypatch.setattr(
        rebuild_estate.os.path,
        "expanduser",
        lambda path: (
            str(existing)
            if path == "~/.brainstem/estate.json"
            else original_expanduser(path)
        ),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "rebuild_estate.py",
            "--handle",
            "kody-w",
            "--operator-rappid",
            RAPPID,
            "--apply",
        ],
    )

    assert rebuild_estate.main() == 1
    assert existing.read_bytes() == original


def test_rebuild_valid_empty_discovery_is_not_a_failure(monkeypatch):
    monkeypatch.setattr(
        rebuild_estate, "discover_created", lambda *args: ([], [], [])
    )
    monkeypatch.setattr(
        rebuild_estate, "discover_memberships", lambda *args: ([], [], [])
    )

    result = rebuild_estate.rebuild("kody-w", RAPPID)

    assert result["ok"] is True
    assert result["created"] == []
    assert result["member"] == []


def test_repository_listing_distinguishes_valid_empty_from_api_failure(
    monkeypatch,
):
    monkeypatch.setattr(
        rebuild_estate, "_gh_get_json", lambda path: {"login": "kody-w"}
    )
    monkeypatch.setattr(
        rebuild_estate, "_gh", lambda args: (0, "[]", "")
    )

    assert rebuild_estate._list_handle_repos("kody-w") == ([], [])

    monkeypatch.setattr(
        rebuild_estate,
        "_gh",
        lambda args: (1, "", "injected GitHub API failure"),
    )
    repos, errors = rebuild_estate._list_handle_repos("kody-w")
    assert repos == []
    assert errors
