from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
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
import ecosystem_audit  # noqa: E402
import ecosystem_contract  # noqa: E402
import holo_card_generator  # noqa: E402
import private_estate_init  # noqa: E402
import rebuild_estate  # noqa: E402
import sniff_network  # noqa: E402


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


@pytest.mark.parametrize("dry_run", [False, True])
def test_private_estate_is_always_non_success_plan_only(dry_run):
    result = private_estate_init.init_private_estate(
        "kody-w", dry_run=dry_run
    )

    assert result["ok"] is False
    assert result["accepted"] is False
    assert result["status"] == "OWNER_AUTHORITY_REQUIRED"
    assert result["mode"] == "plan-only"
    assert result["plan_only"] is True
    assert result["apply_permitted"] is False
    assert result["repository_mutation_permitted"] is False
    assert result["local_state_mutation_permitted"] is False
    assert result["error"]["code"] == "authenticated-registry-unavailable"
    assert result["candidate_plan"]["owner_review_required"] is True
    assert result["candidate_plan"]["executable"] is False
    for forbidden in (
        "private_estate_commitment",
        "repo_created",
        "files_written",
        "next_step",
    ):
        assert forbidden not in result


def test_private_estate_invalid_owner_is_non_success_refusal():
    result = private_estate_init.init_private_estate("Not Valid")

    assert result["ok"] is False
    assert result["accepted"] is False
    assert result["status"] == "INVALID_REQUEST"
    assert result["apply_permitted"] is False


def test_private_estate_cli_never_writes_or_returns_success(migration_dir):
    sentinel = migration_dir / "must-survive"
    original = b"unchanged\n"
    sentinel.write_bytes(original)

    assert private_estate_init.main(["--handle", "kody-w"]) == 1
    assert private_estate_init.main(
        ["--handle", "kody-w", "--dry-run"]
    ) == 1
    assert private_estate_init.main(
        ["--handle", "kody-w", "--verify-commitment"]
    ) == 1
    assert sentinel.read_bytes() == original


def test_private_estate_source_has_no_live_mutation_implementation():
    source = (
        ROOT / "tools" / "private_estate_init.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "subprocess",
        "urllib.request",
        "secrets.token_bytes",
        "write_bytes(",
        "write_text(",
        ".mkdir(",
        "repo\", \"create",
        "\"PUT\"",
    ):
        assert forbidden not in source


def test_network_sniff_is_unverified_publication_observation(monkeypatch):
    monkeypatch.setattr(
        sniff_network,
        "fetch_seed",
        lambda _url: {
            "schema": "rapp-network-seed/1.0",
            "operators": ["kody-w"],
        },
    )
    monkeypatch.setattr(
        sniff_network,
        "fetch_beacon_at_url",
        lambda _url: {
            "schema": "rapp-network-beacon/1.1",
            "operator_rappid": RAPPID,
            "estate_url": "https://example.invalid/estate.json",
            "grail_url": "https://example.invalid/grail",
            "minted_at": UTC,
            "protocol": {"implements": ["article-xlviii"]},
            "private_estate_pointer": "https://example.invalid/private",
            "private_estate_commitment": "claimed-only",
            "private_door_count": 4,
            "discovery": {"indexable": True, "federation_hints": []},
        },
    )
    monkeypatch.setattr(
        sniff_network,
        "fetch_estate_at_url",
        lambda _url: {
            "created": [{"rappid": "published"}],
            "member": [{"rappid": "published"}, {"rappid": "published"}],
        },
    )

    result = sniff_network.sniff_via_raw()

    assert result["ok"] is False
    assert result["accepted"] is False
    assert result["status"] == "UNVERIFIED"
    assert result["authority_state"] == "unverified-observation"
    assert result["rapp_protocol_authority"] is False
    assert result["observation_complete"] is True
    assert result["published_door_claim_count"] == 3
    observation = result["observations"][0]
    assert observation["accepted"] is False
    assert observation["status"] == "UNVERIFIED"
    assert observation["verification"]["section_13_authenticated"] is False
    assert observation["verification"]["freshness_verified"] is False
    assert observation["published_created_claim_count"] == 1
    assert observation["published_member_claim_count"] == 2
    assert observation["published_private_door_claim_count"] == 4
    for inferred_field in (
        "compliance",
        "created_count",
        "member_count",
        "has_private_extension",
    ):
        assert inferred_field not in observation


def test_network_sniff_apply_flag_refuses_default_state_write(
    migration_dir, monkeypatch
):
    result = sniff_network._unverified_envelope("raw", [], [])
    monkeypatch.setattr(sniff_network, "sniff_via_raw", lambda **_kwargs: result)
    monkeypatch.setenv("HOME", str(migration_dir))

    assert sniff_network.main(["--via", "raw", "--apply", "--json"]) == 1
    assert result["apply_refused"] is True
    assert not (migration_dir / ".brainstem" / "network-sniff.json").exists()


def test_network_sniff_source_has_no_acceptance_or_compliance_inference():
    source = (ROOT / "tools" / "sniff_network.py").read_text(encoding="utf-8")
    assert '"accepted": True' not in source
    assert 'record["compliance"]' not in source
    assert '"compliance":' not in source


def test_ecosystem_cache_fallback_is_explicitly_stale(
    migration_dir, monkeypatch
):
    cache_dir = migration_dir / "audit-cache"
    monkeypatch.setattr(ecosystem_audit, "CACHE_DIR", str(cache_dir))
    url = "https://raw.githubusercontent.com/example/repo/main/rappid.json"
    ecosystem_audit._cache_put(url, b'{"cached":true}')

    def unavailable(*_args, **_kwargs):
        raise ecosystem_audit.urllib.error.URLError("offline")

    monkeypatch.setattr(
        ecosystem_audit.urllib.request, "urlopen", unavailable
    )

    body, evidence = ecosystem_audit._raw_fetch(url)

    assert body == b'{"cached":true}'
    assert evidence["source"] == "cache"
    assert evidence["status"] == "stale"
    assert evidence["freshness"] == "stale"
    assert "raw.githubusercontent.com" not in evidence["source"]
    assert evidence["cache_age_seconds"] >= 0


def test_online_ecosystem_evidence_unavailable_is_incomplete_and_nonzero(
    migration_dir, monkeypatch
):
    metropolis = migration_dir / "metropolis.json"
    metropolis.write_text(
        json.dumps(
            {
                "schema": "rapp-metropolis-index/1.0",
                "tracker_url": "https://example.invalid/metropolis",
                "entries": [
                    {
                        "name": "offline-peer",
                        "kind": "twin",
                        "neighborhood_rappid": RAPPID,
                        "gate_repo": "kody-w/offline-peer",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        ecosystem_audit,
        "_fetch_offspring_file",
        lambda _repo, path: (
            None,
            {
                "url": f"https://example.invalid/{path}",
                "source": "none",
                "status": "unavailable",
                "freshness": "unavailable",
                "detail": "injected outage",
            },
        ),
    )

    result = ecosystem_audit.audit_ecosystem(
        mode="online",
        metropolis_index_path=str(metropolis),
        write_outputs=False,
    )

    assert result["ok"] is False
    assert result["status"] == "EVIDENCE_INCOMPLETE"
    assert result["evidence_complete"] is False
    assert result["incomplete_count"] == 1
    assert result["offspring"][0]["evidence_complete"] is False
    assert result["offspring"][0]["evidence_issues"]

    monkeypatch.setattr(
        ecosystem_audit, "audit_ecosystem", lambda **_kwargs: result
    )
    assert ecosystem_audit.main(
        ["--online", "--no-write", "--lenient"]
    ) == 2


def test_ecosystem_guidance_is_owner_reviewed_and_non_executable():
    guidance = ecosystem_audit._owner_review_guidance(
        "offline-peer",
        "kody-w/offline-peer",
        "LOCAL_TO_GLOBAL",
        "twin",
    )

    assert guidance is not None
    assert guidance["status"] == "owner-review-required"
    assert guidance["owner_review_required"] is True
    assert guidance["executable"] is False
    assert "one_liner" not in guidance
    assert "agent_to_invoke" not in guidance
    source = (ROOT / "tools" / "ecosystem_audit.py").read_text(
        encoding="utf-8"
    )
    for forbidden in ("dry_run=False", "Launch", "Graft", "RarLoader"):
        assert forbidden not in source


def test_retired_ecosystem_kinds_are_inert_historical_observations():
    assert ecosystem_contract.HISTORICAL_KINDS == {
        "catalog",
        "installer",
        "egg-hub",
    }
    for kind in ecosystem_contract.HISTORICAL_KINDS:
        observation = ecosystem_contract.CONTRACTS[kind]
        assert observation["lifecycle"] == "historical-observation"
        assert observation["required_files"] == []
        assert observation["expected_product_schemas"] == {}
        assert observation["rappid_kind"] is None
        assert observation["identity_block_required"] is False
        assert observation["rar_required"] is False
        assert observation["kernel_base_check"] is False
        assert observation["historical_shape"]

        result = ecosystem_audit._diff_offspring(
            kind,
            kind,
            observation,
            lambda _path: (_ for _ in ()).throw(
                AssertionError("historical observation must not fetch")
            ),
            None,
        )
        assert result["ok"] is True
        assert result["kind_lifecycle"] == "historical-observation"


def test_holo_generator_is_explicitly_nonconformant_tombstone():
    result = holo_card_generator.generate_holo_card(
        RAPPID,
        "neighborhood",
        "kody-w",
        "offline-peer",
        "Offline Peer",
    )

    assert result["schema"] == "rapp-holocard-historical-observation/1.0"
    assert result["ok"] is False
    assert result["accepted"] is False
    assert result["conformant"] is False
    assert result["status"] == "RETIRED_NONCONFORMANT"
    assert result["output_permitted"] is False
    assert result["owner_review_required"] is True
    for conformant_member in (
        "id",
        "hp",
        "stats",
        "agent_types",
        "abilities",
        "meta",
        "avatar_svg",
    ):
        assert conformant_member not in result


def test_holo_generator_source_never_emits_claimed_registry_schema():
    source = (ROOT / "tools" / "holo_card_generator.py").read_text(
        encoding="utf-8"
    )
    assert '"schema":       "rappcards/1.1.2"' not in source
    assert '"schema": "rappcards/1.1.2"' not in source
    check = holo_card_generator._self_check()
    assert check["ok"] is False
    assert check["self_check_passed"] is True
    assert check["accepted"] is False
    assert check["conformant"] is False


def test_mirror_drift_uses_exact_pin_and_never_overwrites(
    migration_dir, monkeypatch
):
    script = ROOT / "tests" / "mirror-drift.sh"
    source = script.read_text(encoding="utf-8")
    assert "KERNEL_PIN.json" in source
    assert "brainstem-v0.6.9" in source
    assert "/main" not in source
    assert "Restore with:" not in source
    assert "\n    cp " not in source
    assert "Do not overwrite immutable bytes" in source

    pin = json.loads((ROOT / "KERNEL_PIN.json").read_text(encoding="utf-8"))
    frozen = pin["kernel"]["frozen"]
    before = {
        path: (ROOT / path).read_bytes()
        for path in frozen
    }

    fake_bin = migration_dir / "bin"
    fake_bin.mkdir()
    fake_curl = fake_bin / "curl"
    fake_curl.write_text(
        """#!/usr/bin/env python3
import os
import sys

prefix = "https://raw.githubusercontent.com/kody-w/rapp-installer/brainstem-v0.6.9/"
url = sys.argv[-1]
if not url.startswith(prefix):
    raise SystemExit(f"unexpected URL: {url}")
path = url[len(prefix):]
with open(os.path.join(os.environ["RAPP_TEST_ROOT"], path), "rb") as handle:
    sys.stdout.buffer.write(handle.read())
""",
        encoding="utf-8",
    )
    fake_curl.chmod(0o755)
    monkeypatch.setenv(
        "PATH", f"{fake_bin}{os.pathsep}{os.environ['PATH']}"
    )
    monkeypatch.setenv("RAPP_TEST_ROOT", str(ROOT))

    completed = subprocess.run(
        ["bash", str(script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert "rapp-installer@brainstem-v0.6.9" in completed.stdout
    assert {
        path: (ROOT / path).read_bytes()
        for path in frozen
    } == before


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


def test_rebuild_operator_owner_mismatch_is_invalid_refusal():
    alice_rappid = f"rappid:@alice/offline-peer:{'a' * 64}"
    result = rebuild_estate.rebuild("bob", alice_rappid)

    assert result["ok"] is False
    assert result["accepted"] is False
    assert result["status"] == "INVALID_REQUEST"
    assert "does not match requested" in result["error"]["detail"]


def test_rebuild_is_non_success_plan_without_publication_discovery():
    result = rebuild_estate.rebuild("kody-w", RAPPID)

    assert result["ok"] is False
    assert result["accepted"] is False
    assert result["status"] == "OWNER_AUTHORITY_REQUIRED"
    assert result["mode"] == "plan-only"
    assert result["plan_only"] is True
    assert result["apply_permitted"] is False
    assert result["local_state_mutation_permitted"] is False
    assert result["error"]["code"] == "authenticated-registry-unavailable"
    assert result["candidate_plan"]["owner_review_required"] is True
    assert result["candidate_plan"]["executable"] is False
    assert "created" not in result
    assert "member" not in result


def test_rebuild_apply_and_out_flags_never_write(migration_dir):
    existing = migration_dir / "estate.json"
    original = b'{"existing":"estate must survive byte-for-byte"}\n'
    existing.write_bytes(original)

    assert rebuild_estate.main(
        [
            "--handle",
            "kody-w",
            "--operator-rappid",
            RAPPID,
            "--apply",
            "--out",
            str(existing),
        ],
    ) == 1
    assert existing.read_bytes() == original


def test_rebuild_source_has_no_live_discovery_or_write_implementation():
    source = (ROOT / "tools" / "rebuild_estate.py").read_text(encoding="utf-8")
    for forbidden in (
        "subprocess",
        "urllib.request",
        "gh search",
        "write_bytes(",
        "write_text(",
        ".mkdir(",
        "os.makedirs",
    ):
        assert forbidden not in source
