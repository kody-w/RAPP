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
def test_private_estate_retains_full_plan_and_defaults_read_only(
    dry_run, migration_dir, monkeypatch
):
    monkeypatch.setattr(
        private_estate_init,
        "_load_operator_identity",
        lambda _path, _owner: (RAPPID, "operator"),
    )
    monkeypatch.setattr(
        private_estate_init,
        "_gh_repo_observation",
        lambda slug: {
            "status": "missing",
            "source": "test",
            "repository": slug,
        },
    )
    monkeypatch.setattr(
        private_estate_init,
        "_SECRET_PATH",
        migration_dir / "private-estate-secret",
    )
    monkeypatch.setattr(
        private_estate_init,
        "_LOCAL_MAP_PATH",
        migration_dir / "private-estate-map.json",
    )
    for name in ("_gh_create_private", "_gh_put_file", "_ensure_secret"):
        monkeypatch.setattr(
            private_estate_init,
            name,
            lambda *_args, _name=name, **_kwargs: (_ for _ in ()).throw(
                AssertionError(f"default plan called {_name}")
            ),
        )

    result = private_estate_init.init_private_estate(
        "kody-w", dry_run=dry_run
    )

    assert result["ok"] is True
    assert result["accepted"] is False
    assert result["status"] == "PLAN_READY"
    assert result["mode"] == "inspect-plan"
    assert result["plan_only"] is True
    assert result["apply_permitted"] is False
    assert result["repository_mutation_permitted"] is False
    assert result["local_state_mutation_permitted"] is False
    assert result["repository_observation"]["status"] == "missing"
    assert result["scaffold"]["schema"] == "rapp-private-estate/1.0"
    assert {
        row["path"] for row in result["scaffold"]["files"]
    } == {
        "meta.json",
        "README.md",
        "objects/.gitkeep",
        "kinds/.gitkeep",
    }
    assert result["scaffold"]["opaque_path_audit"] == "pass"
    assert result["algorithm"]["idempotent"] is True
    assert "PUT every scaffold file" in result["algorithm"]["remote_order"]
    assert not any(migration_dir.iterdir())


def test_private_estate_invalid_owner_is_non_success_refusal():
    result = private_estate_init.init_private_estate("Not Valid")

    assert result["ok"] is False
    assert result["accepted"] is False
    assert result["status"] == "INVALID_REQUEST"
    assert result["apply_permitted"] is False
    assert result["error"]["code"] == "invalid-owner"


def test_private_estate_apply_requires_artifact_and_authenticated_authority(
    migration_dir, monkeypatch
):
    sentinel = migration_dir / "must-survive"
    original = b"unchanged\n"
    sentinel.write_bytes(original)
    monkeypatch.setattr(
        private_estate_init,
        "_load_operator_identity",
        lambda _path, _owner: (RAPPID, "operator"),
    )
    monkeypatch.setattr(
        private_estate_init,
        "_gh_repo_observation",
        lambda slug: {
            "status": "missing",
            "source": "test",
            "repository": slug,
        },
    )
    monkeypatch.setattr(
        private_estate_init,
        "_gh_create_private",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("repository creation crossed the authority gate")
        ),
    )

    assert private_estate_init.main(["--handle", "kody-w"]) == 0
    assert private_estate_init.main(
        ["--handle", "kody-w", "--apply"]
    ) == 2

    approval = migration_dir / "approval.json"
    approval.write_bytes(
        canonical_bytes(
            {
                "schema": "rapp-tool-owner-approval/1.0",
                "operation": "private-estate-initialize",
                "target": private_estate_init._approval_target("kody-w"),
            }
        )
    )
    result = private_estate_init.init_private_estate(
        "kody-w",
        apply=True,
        owner_approval_path=str(approval),
    )
    assert result["ok"] is False
    assert result["status"] == "OWNER_AUTHORITY_REQUIRED"
    assert result["error"]["code"] == "authenticated-registry-unavailable"
    assert result["write_gate"]["approval"]["structurally_matching"] is True
    assert result["write_gate"]["permitted"] is False
    assert sentinel.read_bytes() == original


def test_private_estate_retains_mutation_and_commitment_algorithms():
    source = (
        ROOT / "tools" / "private_estate_init.py"
    ).read_text(encoding="utf-8")
    for retained in (
        "subprocess",
        "urllib.request",
        "secrets.token_bytes",
        "write_bytes(",
        "write_text(",
        ".mkdir(",
        '"repo", "create"',
        "\"PUT\"",
        "_normalized_state_hash",
        "_gh_list_tree_checked",
        "REMOTE_VERIFICATION_FAILED",
    ):
        assert retained in source


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

    assert result["ok"] is True
    assert result["accepted"] is False
    assert result["status"] == "OBSERVED_UNVERIFIED"
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
    assert observation["observed"]["beacon"]["operator_rappid"] == RAPPID
    assert observation["observed"]["estate"]["created"]
    assert observation["provenance"]["beacon"]["url"].endswith(
        ".well-known/rapp-network.json"
    )
    assert observation["provenance"]["estate"]["url"] == (
        "https://example.invalid/estate.json"
    )
    assert result["observed_seed"]["operators"] == ["kody-w"]
    assert result["seed_provenance"]["parsed_payload_sha256"]
    for inferred_field in (
        "compliance",
        "created_count",
        "member_count",
        "has_private_extension",
    ):
        assert inferred_field not in observation


def test_network_sniff_retains_breadth_first_federation_walk(monkeypatch):
    peer_rappid = f"rappid:@peer/rapp-estate:{'b' * 64}"
    beacons = {
        "kody-w": {
            "schema": "rapp-network-beacon/1.1",
            "operator_rappid": RAPPID,
            "discovery": {
                "indexable": True,
                "federation_hints": ["peer"],
            },
        },
        "peer": {
            "schema": "rapp-network-beacon/1.1",
            "operator_rappid": peer_rappid,
            "discovery": {
                "indexable": True,
                "federation_hints": [],
            },
        },
    }
    monkeypatch.setattr(
        sniff_network,
        "fetch_seed",
        lambda _url: {
            "schema": "rapp-network-seed/1.0",
            "operators": ["kody-w"],
        },
    )

    def fetch(url):
        handle = "peer" if "/peer/" in url else "kody-w"
        return beacons[handle]

    monkeypatch.setattr(sniff_network, "fetch_beacon_at_url", fetch)

    result = sniff_network.sniff_via_raw(fetch_estates=False)

    assert result["observations_count"] == 2
    assert [
        (row["published_github"], row["hop"])
        for row in result["observations"]
    ] == [("kody-w", 0), ("peer", 1)]
    assert result["observations"][1]["discovered_via"] == "hint:kody-w"
    assert result["observations"][1]["observed"]["beacon"] == beacons["peer"]


def test_network_sniff_write_requires_approval_and_still_refuses_authority(
    migration_dir, monkeypatch
):
    result = sniff_network._unverified_envelope("raw", [], [])
    monkeypatch.setattr(sniff_network, "sniff_via_raw", lambda **_kwargs: result)
    output = migration_dir / "network-sniff.json"

    assert sniff_network.main(
        ["--via", "raw", "--out", str(output), "--json"]
    ) == 2
    assert result["write_gate"]["code"] == "owner-approval-artifact-required"
    assert not output.exists()

    approval = migration_dir / "sniff-approval.json"
    approval.write_bytes(
        canonical_bytes(
            {
                "schema": "rapp-tool-owner-approval/1.0",
                "operation": "network-sniff-write",
                "target": sniff_network._write_target(str(output), "raw"),
            }
        )
    )
    result = sniff_network._unverified_envelope("raw", [], [])
    monkeypatch.setattr(sniff_network, "sniff_via_raw", lambda **_kwargs: result)
    assert sniff_network.main(
        [
            "--via",
            "raw",
            "--out",
            str(output),
            "--owner-approval",
            str(approval),
            "--json",
        ]
    ) == 2
    assert result["write_gate"]["code"] == (
        "authenticated-registry-unavailable"
    )
    assert result["write_gate"]["approval"]["structurally_matching"] is True
    assert not output.exists()


def test_network_sniff_source_has_no_acceptance_or_compliance_inference():
    source = (ROOT / "tools" / "sniff_network.py").read_text(encoding="utf-8")
    assert '"accepted": True' not in source
    assert 'record["compliance"]' not in source
    assert '"compliance":' not in source
    for retained in (
        "deque",
        "federation_hints",
        "dns-sd",
        '"search", "repos"',
        "observed_browse_output",
        "observed_search_results",
        "parsed_payload_sha256",
    ):
        assert retained in source


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


def test_ecosystem_live_read_does_not_mutate_cache_by_default(
    migration_dir, monkeypatch
):
    cache_dir = migration_dir / "audit-cache"
    monkeypatch.setattr(ecosystem_audit, "CACHE_DIR", str(cache_dir))

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"live":true}'

    monkeypatch.setattr(
        ecosystem_audit.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: Response(),
    )

    body, evidence = ecosystem_audit._raw_fetch(
        "https://raw.githubusercontent.com/example/repo/main/rappid.json"
    )

    assert body == b'{"live":true}'
    assert evidence["freshness"] == "live"
    assert evidence["cache_updated"] is False
    assert not cache_dir.exists()


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
    assert guidance["auto_execute"] is False
    assert guidance["apply_permitted"] is False
    assert "one_liner" not in guidance
    assert "agent_to_invoke" not in guidance
    assert guidance["historical_strategy"]["historical_mechanism"] == "Launch"
    assert guidance["historical_strategy"]["parameter_plan"]["dry_run"] is True
    pull = ecosystem_audit._owner_review_guidance(
        "offline-peer",
        "kody-w/offline-peer",
        "GLOBAL_TO_LOCAL",
        "twin",
    )
    assert pull["historical_strategy"]["historical_mechanism"] == "RarLoader"
    source = (ROOT / "tools" / "ecosystem_audit.py").read_text(
        encoding="utf-8"
    )
    assert "dry_run=False" not in source
    for retained in ("Launch", "Graft", "RarLoader", "_diff_offspring"):
        assert retained in source


def test_ecosystem_output_write_requires_authenticated_owner_authority(
    migration_dir,
):
    out_dir = migration_dir / "audit-out"
    target = {
        "out_dir": str(out_dir.resolve()),
        "artifacts": ["ecosystem-audit.json", "ecosystem-audit.md"],
    }
    approval = migration_dir / "audit-approval.json"
    approval.write_bytes(
        canonical_bytes(
            {
                "schema": "rapp-tool-owner-approval/1.0",
                "operation": "ecosystem-audit-write",
                "target": target,
            }
        )
    )

    result = ecosystem_audit.audit_ecosystem(
        mode="offline",
        repo_filter="ant-farm",
        out_dir=str(out_dir),
        write_outputs=True,
        owner_approval_path=str(approval),
    )

    assert result["output_write"]["code"] == (
        "authenticated-registry-unavailable"
    )
    assert result["output_write"]["approval"]["structurally_matching"] is True
    assert result["output_write"]["written"] is False
    assert not out_dir.exists()


def test_retired_ecosystem_kinds_keep_full_historical_comparisons():
    assert ecosystem_contract.HISTORICAL_KINDS == {
        "catalog",
        "installer",
        "egg-hub",
    }
    for kind in ecosystem_contract.HISTORICAL_KINDS:
        observation = ecosystem_contract.CONTRACTS[kind]
        assert observation["lifecycle"] == "historical-observation"
        assert observation["required_files"]
        assert observation["expected_product_schemas"] == {}
        assert observation["rappid_kind"] is None
        assert observation["identity_block_required"] is False
        assert observation["rar_required"] is False
        assert observation["kernel_base_check"] is False
        assert observation["historical_shape"]["required_files"] == (
            observation["required_files"]
        )

        evidence = {}

        def missing(path):
            evidence[path] = {
                "path": path,
                "source": "fixture",
                "status": "missing",
                "freshness": "offline-fixture",
            }
            missing.evidence = evidence
            return None, "missing"

        missing.evidence = evidence

        result = ecosystem_audit._diff_offspring(
            kind,
            kind,
            observation,
            missing,
            None,
        )
        assert result["ok"] is False
        assert result["drift"]
        assert {
            drift["path"] for drift in result["drift"]
            if drift["category"] == "missing_files"
        } >= set(observation["required_files"])
        assert result["kind_lifecycle"] == "historical-observation"
        assert ecosystem_audit._classify_drift(result, kind) == "HISTORICAL"


def test_holo_generator_retains_full_historical_profile_by_default():
    result = holo_card_generator.generate_holo_card(
        RAPPID,
        "neighborhood",
        "kody-w",
        "offline-peer",
        "Offline Peer",
    )

    assert result["schema"] == "rapp-holocard-historical-profile/1.0"
    assert result["ok"] is True
    assert result["accepted"] is False
    assert result["conformant"] is False
    assert result["status"] == "HISTORICAL_NON_ACCEPTED"
    assert result["publication_permitted"] is False
    profile = result["profile"]
    for retained_member in (
        "id",
        "hp",
        "stats",
        "agent_types",
        "abilities",
        "meta",
        "avatar_svg",
    ):
        assert retained_member in profile
    assert profile["abilities"]
    assert profile["meta"]["rappid"] == RAPPID
    assert result["provenance"]["mnemonic_vocabulary"][
        "registry_compatible"
    ] is False


def test_holo_generator_supports_exact_schema_pin_without_acceptance():
    result = holo_card_generator.generate_holo_card(
        RAPPID,
        "neighborhood",
        "kody-w",
        "offline-peer",
        "Offline Peer",
        schema_pin=holo_card_generator.RAPPCARDS_V1_1_2_PIN,
    )

    assert result["schema"] == "rapp-holocard-pinned-profile/1.0"
    assert result["ok"] is True
    assert result["conformant"] is True
    assert result["accepted"] is False
    assert result["publication_permitted"] is False
    assert result["selected_schema"]["commit"] == (
        "5bfcea8d6aaa78e988827783b44e0d384ed3c14a"
    )
    assert result["selected_schema"]["sha256"] == (
        "af5a9dda865430c720ed0409160eb6d61afb4960f7b5c740269d1002c87d41dc"
    )
    assert result["profile"]["schema"] == "rappcards/1.1.2"
    assert "historical_incantation_preview" in result["profile"]["meta"]


def test_holo_generator_source_retains_generation_algorithm():
    source = (ROOT / "tools" / "holo_card_generator.py").read_text(
        encoding="utf-8"
    )
    for retained in (
        "_generate_profile",
        "_derive_stats",
        "abilities_template",
        "generate_avatar_svg",
        "generate_summon_qr_svg",
        "SUPPORTED_SCHEMA_PINS",
    ):
        assert retained in source
    check = holo_card_generator._self_check()
    assert check["ok"] is True
    assert check["accepted"] is False


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
    assert "Do not overwrite or remove immutable bytes" in source
    assert "Inspect the pinned Grail" in source

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
    assert (
        "https://github.com/kody-w/rapp-installer/tree/brainstem-v0.6.9"
        in completed.stdout
    )
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


def test_rebuild_created_discovery_retains_filtering_and_source_records(
    monkeypatch,
):
    child = f"rappid:@kody-w/child:{'b' * 64}"
    other = f"rappid:@kody-w/other:{'c' * 64}"
    repos = [
        {"name": "child", "fork": False, "owner": {"login": "kody-w"}},
        {"name": "other", "fork": False, "owner": {"login": "kody-w"}},
    ]
    records = {
        "child": {
            "schema": "rapp/1",
            "kind": "twin",
            "rappid": child,
            "parent_rappid": RAPPID,
        },
        "other": {
            "schema": "rapp/1",
            "kind": "twin",
            "rappid": other,
            "parent_rappid": f"rappid:@kody-w/unrelated:{'d' * 64}",
        },
    }
    monkeypatch.setattr(
        rebuild_estate,
        "_list_handle_repos",
        lambda _handle: (repos, []),
    )
    monkeypatch.setattr(
        rebuild_estate,
        "_raw_fetch_json_checked",
        lambda _owner, repo, _path: (records[repo], "ok", ""),
    )

    created, skipped, errors = rebuild_estate.discover_created(
        "kody-w", RAPPID
    )

    assert errors == []
    assert [row["rappid"] for row in created] == [child]
    assert created[0]["_observation"]["identity_record"] == records["child"]
    assert created[0]["_observation"]["accepted"] is False
    assert skipped[0]["identity_record"] == records["other"]
    assert "parent_rappid" in skipped[0]["reason"]


def test_rebuild_membership_discovery_retains_exact_verification_records(
    monkeypatch,
):
    gate = f"rappid:@peer/gate:{'e' * 64}"
    hit = {
        "repository": {"nameWithOwner": "peer/gate"},
        "path": "members.json",
    }
    members = {
        "schema": "rapp-neighborhood-members/1.0",
        "members": [{"rappid": RAPPID, "role": "member"}],
    }
    identity = {
        "schema": "rapp/1",
        "kind": "neighborhood",
        "rappid": gate,
    }
    monkeypatch.setattr(
        rebuild_estate,
        "_gh",
        lambda _args: (0, json.dumps([hit]), ""),
    )

    def fetch(_owner, _repo, path):
        return (
            (members, "ok", "")
            if path == "members.json"
            else (identity, "ok", "")
        )

    monkeypatch.setattr(rebuild_estate, "_raw_fetch_json_checked", fetch)

    member, skipped, errors = rebuild_estate.discover_memberships(RAPPID)

    assert errors == []
    assert skipped == []
    assert [row["rappid"] for row in member] == [gate]
    observation = member[0]["_observation"]
    assert observation["members_record"] == members
    assert observation["identity_record"] == identity
    assert observation["search_hit"] == hit
    assert observation["accepted"] is False


def test_rebuild_retains_discovery_and_returns_unaccepted_candidate(
    monkeypatch,
):
    created_rappid = f"rappid:@kody-w/created:{'b' * 64}"
    member_rappid = f"rappid:@peer/member-gate:{'c' * 64}"
    created = [
        {
            "rappid": created_rappid,
            "added_at": UTC,
            "via": "rebuild",
            "_observation": {
                "accepted": False,
                "identity_record": {"rappid": created_rappid},
            },
        }
    ]
    member = [
        {
            "rappid": member_rappid,
            "added_at": UTC,
            "via": "rebuild",
            "_observation": {
                "accepted": False,
                "members_record": {"members": [{"rappid": RAPPID}]},
            },
        }
    ]
    monkeypatch.setattr(
        rebuild_estate,
        "discover_created",
        lambda *_args, **_kwargs: (created, [{"repo": "skipped"}], []),
    )
    monkeypatch.setattr(
        rebuild_estate,
        "discover_memberships",
        lambda *_args, **_kwargs: (member, [], []),
    )

    result = rebuild_estate.rebuild("kody-w", RAPPID)

    assert result["ok"] is True
    assert result["accepted"] is False
    assert result["status"] == "OBSERVED_UNVERIFIED"
    assert result["mode"] == "inspect-plan"
    assert result["plan_only"] is True
    assert result["apply_permitted"] is False
    assert result["local_state_mutation_permitted"] is False
    assert result["candidate_estate"]["schema"] == "rapp-estate/1.1"
    assert result["candidate_estate"]["created"] == [
        {
            "rappid": created_rappid,
            "added_at": UTC,
            "via": "rebuild",
        }
    ]
    assert result["candidate_estate"]["member"][0]["rappid"] == member_rappid
    assert result["observations"]["published_created_claims"] == created
    assert result["observations"]["published_membership_claims"] == member
    assert result["algorithm"]["operator_discovery_order"]
    assert result["acceptance"]["accepted"] is False


def test_rebuild_write_requires_artifact_and_still_refuses_authority(
    migration_dir, monkeypatch
):
    existing = migration_dir / "estate.json"
    original = b'{"existing":"estate must survive byte-for-byte"}\n'
    existing.write_bytes(original)
    monkeypatch.setattr(
        rebuild_estate,
        "discover_created",
        lambda *_args, **_kwargs: ([], [], []),
    )
    monkeypatch.setattr(
        rebuild_estate,
        "discover_memberships",
        lambda *_args, **_kwargs: ([], [], []),
    )

    assert rebuild_estate.main(
        [
            "--handle",
            "kody-w",
            "--operator-rappid",
            RAPPID,
            "--out",
            str(existing),
        ],
    ) == 2
    assert existing.read_bytes() == original

    approval = migration_dir / "rebuild-approval.json"
    approval.write_bytes(
        canonical_bytes(
            {
                "schema": "rapp-tool-owner-approval/1.0",
                "operation": "estate-rebuild-adopt",
                "target": rebuild_estate._write_target(
                    "kody-w", str(existing), False
                ),
            }
        )
    )
    result = rebuild_estate.rebuild(
        "kody-w",
        RAPPID,
        requested_out=str(existing),
        owner_approval_path=str(approval),
    )
    assert result["ok"] is False
    assert result["status"] == "OWNER_AUTHORITY_REQUIRED"
    assert result["write_gate"]["code"] == (
        "authenticated-registry-unavailable"
    )
    assert result["write_gate"]["approval"]["structurally_matching"] is True
    assert existing.read_bytes() == original


def test_rebuild_source_retains_discovery_and_write_algorithm():
    source = (ROOT / "tools" / "rebuild_estate.py").read_text(encoding="utf-8")
    for retained in (
        "subprocess",
        "urllib.request",
        '"search", "code"',
        "_raw_fetch_json_checked",
        "discover_operator_rappid",
        "discover_created",
        "discover_memberships",
        "members.json",
        "write_text(",
        "os.makedirs",
    ):
        assert retained in source
