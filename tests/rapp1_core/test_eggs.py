from __future__ import annotations

import base64
import os
import shutil
import struct
from pathlib import Path

import pytest

from rapp1_core.canonical import canonical_bytes, strict_loads
from rapp1_core.egg import (
    ZIP_CENTRAL,
    ZIP_CENTRAL_SIGNATURE,
    ZIP_DOS_DATE,
    ZIP_DOS_TIME,
    ZIP_LOCAL,
    ZIP_LOCAL_SIGNATURE,
    ZIP_STORED,
    ZIP_UTF8_FLAG,
    EggError,
    _decode_zip,
    _encode_zip,
    _validate_extraction_path,
    _resolved_staging_path,
    accept_egg,
    extract_egg,
    inspect_egg,
    pack_egg,
    validate_egg_path,
)
from rapp1_core.hashing import EGG_FILE_SPACE, hash_bytes
from rapp1_core.trust import RegistryEvidence, TrustStatus

RID_ORG1 = "rappid:@kody-w/one:" + "1" * 64
RID_ORG2 = "rappid:@kody-w/two:" + "2" * 64
RID_RAPP = "rappid:@kody-w/application:" + "3" * 64
RID_SESSION = "rappid:@kody-w/session:" + "4" * 64
RID_NEIGHBORHOOD = "rappid:@kody-w/commons:" + "5" * 64
RID_ESTATE = "rappid:@kody-w/estate:" + "6" * 64
RID_OWNER = "rappid:@kody-w/owner:" + "7" * 64
UTC = "2026-07-16T22:41:23.842Z"


def _jws(kid: str = RID_OWNER) -> str:
    header = canonical_bytes(
        {"alg": "EdDSA", "b64": False, "crit": ["b64"], "kid": kid}
    )
    protected = base64.urlsafe_b64encode(header).rstrip(b"=").decode()
    signature = base64.urlsafe_b64encode(b"\x08" * 64).rstrip(b"=").decode()
    return f"{protected}..{signature}"


def _organism(rappid: str = RID_ORG1) -> bytes:
    return pack_egg(
        variant="organism",
        rappid=rappid,
        created_utc=UTC,
        payload={},
        files={"rappid.json": canonical_bytes({"rappid": rappid}), "soul.md": b"soul\n"},
    )


def _neighborhood() -> bytes:
    return pack_egg(
        variant="neighborhood",
        rappid=RID_NEIGHBORHOOD,
        created_utc=UTC,
        payload={"members": [RID_ORG1, RID_ORG2]},
        files={
            "kody-w--one.egg": _organism(RID_ORG1),
            "kody-w--two.egg": _organism(RID_ORG2),
        },
    )


def _manifest_and_files(egg: bytes) -> tuple[dict, list[tuple[str, bytes]]]:
    members = _decode_zip(egg)
    manifest = strict_loads(members[0].data)
    assert type(manifest) is dict
    return manifest, [(member.name, member.data) for member in members[1:]]


def test_all_six_variants_are_structurally_supported() -> None:
    organism = _organism()
    rapplication = pack_egg(
        variant="rapplication",
        rappid=RID_RAPP,
        created_utc=UTC,
        payload={},
        files={
            "agent.py": b"class Agent: pass\n",
            "rappid.json": b"{}",
            "state/data.json": b"{}",
            "ui.html": b"<main></main>",
        },
    )
    session = pack_egg(
        variant="session",
        rappid=RID_SESSION,
        created_utc=UTC,
        payload={"runtime": "python", "transcript": [{"role": "user"}]},
    )
    invite = pack_egg(
        variant="invite",
        rappid=RID_ESTATE,
        created_utc=UTC,
        payload={
            "target_rappid": RID_NEIGHBORHOOD,
            "target_url": "https://example.test/commons",
            "target_kind": "neighborhood",
        },
        sig=_jws(),
    )
    neighborhood = _neighborhood()
    estate = pack_egg(
        variant="estate",
        rappid=RID_ESTATE,
        created_utc=UTC,
        payload={"neighborhoods": [RID_NEIGHBORHOOD]},
        files={"kody-w--commons.egg": neighborhood},
    )
    eggs = (organism, rapplication, session, invite, neighborhood, estate)
    assert [inspect_egg(egg).manifest["variant"] for egg in eggs] == [
        "organism",
        "rapplication",
        "session",
        "invite",
        "neighborhood",
        "estate",
    ]
    assert all(inspect_egg(egg).structurally_valid for egg in eggs)
    assert all(not inspect_egg(egg).accepted for egg in eggs)


def test_json_and_zip_outputs_are_byte_deterministic() -> None:
    kwargs = {
        "variant": "session",
        "rappid": RID_SESSION,
        "created_utc": UTC,
        "payload": {"runtime": "python", "transcript": []},
    }
    first = pack_egg(**kwargs)
    second = pack_egg(**kwargs)
    assert first == second == canonical_bytes(strict_loads(first))
    assert _organism() == _organism()


def test_zip_local_and_central_metadata_are_exact() -> None:
    egg = _organism()
    (
        local_signature,
        needed,
        local_flags,
        local_method,
        local_time,
        local_date,
        _,
        _,
        _,
        _,
        local_extra,
    ) = ZIP_LOCAL.unpack_from(egg, 0)
    central_offset = egg.index(struct.pack("<I", ZIP_CENTRAL_SIGNATURE))
    central = ZIP_CENTRAL.unpack_from(egg, central_offset)
    assert local_signature == ZIP_LOCAL_SIGNATURE
    assert needed == 20
    assert local_flags == ZIP_UTF8_FLAG
    assert local_method == ZIP_STORED
    assert (local_time, local_date, local_extra) == (ZIP_DOS_TIME, ZIP_DOS_DATE, 0)
    assert central[3] == ZIP_UTF8_FLAG
    assert central[4] == ZIP_STORED
    assert (central[5], central[6], central[11]) == (
        ZIP_DOS_TIME,
        ZIP_DOS_DATE,
        0,
    )


def test_duplicate_zip_members_are_refused() -> None:
    manifest, files = _manifest_and_files(_organism())
    duplicate = _encode_zip(
        [("manifest.json", canonical_bytes(manifest)), files[0], files[0], files[1]]
    )
    report = inspect_egg(duplicate)
    assert not report.structurally_valid
    assert report.error_code == "duplicate-zip-member"


@pytest.mark.parametrize("which", ["local", "central"])
def test_missing_utf8_flag_in_either_header_is_refused(which: str) -> None:
    egg = bytearray(_organism())
    if which == "local":
        struct.pack_into("<H", egg, 6, 0)
    else:
        central_offset = egg.index(struct.pack("<I", ZIP_CENTRAL_SIGNATURE))
        struct.pack_into("<H", egg, central_offset + 8, 0)
    report = inspect_egg(egg)
    assert not report.structurally_valid
    assert report.error_code == "invalid-zip-metadata"


def test_wrong_method_epoch_and_entry_order_are_refused() -> None:
    egg = bytearray(_organism())
    struct.pack_into("<H", egg, 8, 8)
    assert inspect_egg(egg).error_code == "invalid-zip-metadata"

    egg = bytearray(_organism())
    struct.pack_into("<H", egg, 10, 1)
    assert inspect_egg(egg).error_code == "invalid-zip-metadata"

    manifest, files = _manifest_and_files(_organism())
    wrong_order = _encode_zip([files[0], ("manifest.json", canonical_bytes(manifest)), files[1]])
    assert inspect_egg(wrong_order).error_code == "manifest-not-first"


@pytest.mark.parametrize(
    ("location", "offset", "encoding"),
    [
        ("local", 4, "<H"),
        ("central", 4, "<H"),
        ("central", 6, "<H"),
        ("central", 36, "<H"),
        ("central", 38, "<I"),
    ],
)
def test_mutated_zip_versions_and_attributes_are_refused(
    location: str, offset: int, encoding: str
) -> None:
    egg = bytearray(_organism())
    base = (
        0
        if location == "local"
        else egg.index(struct.pack("<I", ZIP_CENTRAL_SIGNATURE))
    )
    struct.pack_into(encoding, egg, base + offset, 1)
    report = inspect_egg(egg)
    assert not report.structurally_valid
    assert report.error_code == "invalid-zip-metadata"


def test_archive_set_and_manifest_contents_order_are_exact() -> None:
    manifest, files = _manifest_and_files(_organism())
    extra = _encode_zip(
        [("manifest.json", canonical_bytes(manifest))]
        + files
        + [("extra.txt", b"x")]
    )
    assert inspect_egg(extra).error_code == "archive-member-mismatch"

    manifest["contents"] = list(reversed(manifest["contents"]))
    by_name = dict(files)
    reversed_archive = _encode_zip(
        [("manifest.json", canonical_bytes(manifest))]
        + [(entry["path"], by_name[entry["path"]]) for entry in manifest["contents"]]
    )
    assert inspect_egg(reversed_archive).error_code == "unsorted-contents"


def test_zip_slip_paths_and_duplicate_manifest_paths_are_refused() -> None:
    for path in (
        "../escape",
        "/absolute",
        "a\\b",
        "a/./b",
        "a//b",
        "e\u0301.txt",
    ):
        manifest = {
            "schema": "rapp/1-egg",
            "variant": "organism",
            "rappid": RID_ORG1,
            "created_utc": UTC,
            "contents": [
                {"path": path, "hash": hash_bytes(EGG_FILE_SPACE, b"x")}
            ],
            "payload": {},
            "sig": None,
        }
        egg = _encode_zip(
            [("manifest.json", canonical_bytes(manifest)), (path, b"x")]
        )
        assert inspect_egg(egg).error_code == "invalid-egg-path"

    manifest, files = _manifest_and_files(_organism())
    manifest["contents"].append(dict(manifest["contents"][0]))
    duplicate = _encode_zip(
        [("manifest.json", canonical_bytes(manifest))] + files
    )
    assert inspect_egg(duplicate).error_code == "duplicate-content-path"


@pytest.mark.parametrize(
    "conflicting_files",
    [
        {"a": b"parent", "a/b": b"child"},
        {"state/data": b"parent", "state/data/child": b"child"},
        {"manifest.json/child": b"reserved-child"},
    ],
)
def test_ancestor_and_manifest_path_conflicts_never_become_viable(
    conflicting_files: dict[str, bytes]
) -> None:
    files = {
        "rappid.json": b"{}",
        "soul.md": b"soul",
        **conflicting_files,
    }
    with pytest.raises(EggError) as packed:
        pack_egg(
            variant="organism",
            rappid=RID_ORG1,
            created_utc=UTC,
            payload={},
            files=files,
        )
    assert packed.value.code == "path-prefix-conflict"

    paths = sorted(files, key=lambda value: value.encode("utf-8"))
    manifest = {
        "schema": "rapp/1-egg",
        "variant": "organism",
        "rappid": RID_ORG1,
        "created_utc": UTC,
        "contents": [
            {"path": path, "hash": hash_bytes(EGG_FILE_SPACE, files[path])}
            for path in paths
        ],
        "payload": {},
        "sig": None,
    }
    raw = _encode_zip(
        [("manifest.json", canonical_bytes(manifest))]
        + [(path, files[path]) for path in paths]
    )
    inspected = inspect_egg(raw)
    assert not inspected.structurally_valid
    assert inspected.error_code == "path-prefix-conflict"
    accepted = accept_egg(
        raw, registry=RegistryEvidence(authenticated=True, fresh=True)
    )
    assert not accepted.structurally_valid
    assert not accepted.accepted


def test_file_tampering_is_refused_even_with_valid_zip_crc() -> None:
    manifest, files = _manifest_and_files(_organism())
    changed = [(name, b"tampered" if name == "soul.md" else data) for name, data in files]
    egg = _encode_zip([("manifest.json", canonical_bytes(manifest))] + changed)
    report = inspect_egg(egg)
    assert not report.structurally_valid
    assert report.error_code == "content-hash-mismatch"


def test_nested_rappid_mismatch_is_refused() -> None:
    child = _organism(RID_ORG2)
    filename = "kody-w--one.egg"
    manifest = {
        "schema": "rapp/1-egg",
        "variant": "neighborhood",
        "rappid": RID_NEIGHBORHOOD,
        "created_utc": UTC,
        "contents": [
            {"path": filename, "hash": hash_bytes(EGG_FILE_SPACE, child)}
        ],
        "payload": {"members": [RID_ORG1]},
        "sig": None,
    }
    egg = _encode_zip(
        [("manifest.json", canonical_bytes(manifest)), (filename, child)]
    )
    report = inspect_egg(egg)
    assert not report.structurally_valid
    assert report.error_code == "sub-egg-mismatch"


def test_nested_tampering_is_checked_recursively() -> None:
    child_manifest, child_files = _manifest_and_files(_organism())
    child_files[1] = (child_files[1][0], b"changed")
    invalid_child = _encode_zip(
        [("manifest.json", canonical_bytes(child_manifest))] + child_files
    )
    filename = "kody-w--one.egg"
    parent_manifest = {
        "schema": "rapp/1-egg",
        "variant": "neighborhood",
        "rappid": RID_NEIGHBORHOOD,
        "created_utc": UTC,
        "contents": [
            {
                "path": filename,
                "hash": hash_bytes(EGG_FILE_SPACE, invalid_child),
            }
        ],
        "payload": {"members": [RID_ORG1]},
        "sig": None,
    }
    parent = _encode_zip(
        [
            ("manifest.json", canonical_bytes(parent_manifest)),
            (filename, invalid_child),
        ]
    )
    report = inspect_egg(parent)
    assert not report.structurally_valid
    assert report.error_code == "invalid-sub-egg"


def test_rapplication_layout_and_invite_signature_are_strict() -> None:
    with pytest.raises(EggError):
        pack_egg(
            variant="rapplication",
            rappid=RID_RAPP,
            created_utc=UTC,
            payload={},
            files={"rappid.json": b"{}", "agents/agent.py": b""},
        )
    with pytest.raises(EggError, match="sig"):
        pack_egg(
            variant="invite",
            rappid=RID_ESTATE,
            created_utc=UTC,
            payload={
                "target_rappid": RID_ESTATE,
                "target_url": "https://example.test",
                "target_kind": "estate",
            },
        )
    with pytest.raises(EggError):
        pack_egg(
            variant="invite",
            rappid=RID_ESTATE,
            created_utc=UTC,
            payload={
                "target_rappid": RID_ESTATE,
                "target_url": "https://example.test",
                "target_kind": "estate",
            },
            sig="not-base64..not-base64",
        )


def test_signed_egg_remains_unverified_without_authenticated_key_verification() -> None:
    invite = pack_egg(
        variant="invite",
        rappid=RID_ESTATE,
        created_utc=UTC,
        payload={
            "target_rappid": RID_ESTATE,
            "target_url": "https://example.test",
            "target_kind": "estate",
        },
        sig=_jws(),
    )
    structural = inspect_egg(invite)
    assert structural.structurally_valid
    assert not structural.accepted
    assert structural.trust_status is TrustStatus.UNVERIFIED
    claimed_registry = RegistryEvidence(
        authenticated=True,
        fresh=True,
        registered_egg_variants={"invite"},
    )
    accepted = accept_egg(invite, registry=claimed_registry)
    assert not accepted.accepted
    assert accepted.trust_status is TrustStatus.UNVERIFIED
    stale_claim = accept_egg(
        invite,
        registry=RegistryEvidence(
            authenticated=True,
            fresh=False,
            registered_egg_variants={"invite"},
        ),
    )
    assert not stale_claim.accepted
    assert stale_claim.trust_status is TrustStatus.UNVERIFIED


def test_resigning_does_not_change_egg_hash() -> None:
    payload = {
        "target_rappid": RID_ESTATE,
        "target_url": "https://example.test",
        "target_kind": "estate",
    }
    first = pack_egg(
        variant="invite",
        rappid=RID_ESTATE,
        created_utc=UTC,
        payload=payload,
        sig=_jws(),
    )
    replacement_signature = base64.urlsafe_b64encode(b"\x09" * 64).rstrip(b"=").decode()
    second_sig = _jws().rsplit(".", 1)[0] + "." + replacement_signature
    second = pack_egg(
        variant="invite",
        rappid=RID_ESTATE,
        created_utc=UTC,
        payload=payload,
        sig=second_sig,
    )
    assert first != second
    assert inspect_egg(first).egg_hash == inspect_egg(second).egg_hash


def test_unsigned_egg_needs_fresh_registry_evidence_for_acceptance() -> None:
    egg = _organism()
    assert not accept_egg(egg).accepted
    stale = accept_egg(
        egg, registry=RegistryEvidence(authenticated=True, fresh=False)
    )
    assert not stale.accepted and stale.trust_status is TrustStatus.STALE
    empty_registry = accept_egg(
        egg,
        registry=RegistryEvidence(authenticated=True, fresh=True),
    )
    assert not empty_registry.accepted
    assert empty_registry.trust_status is TrustStatus.UNVERIFIED
    wrong_variant = accept_egg(
        egg,
        registry=RegistryEvidence(
            authenticated=True,
            fresh=True,
            registered_egg_variants={"invite"},
        ),
    )
    assert not wrong_variant.accepted
    verified = accept_egg(
        egg,
        registry=RegistryEvidence(
            authenticated=True,
            fresh=True,
            registered_egg_variants={"organism"},
        ),
    )
    assert verified.accepted and verified.trust_status is TrustStatus.VERIFIED
    assert verified.checks[-1].status.value == "PASS"


def test_nested_egg_requires_every_recursive_variant_registration() -> None:
    neighborhood = _neighborhood()
    structural = inspect_egg(neighborhood)
    assert structural.egg_variants == (
        "neighborhood",
        "organism",
        "organism",
    )

    incomplete_registry = RegistryEvidence(
        authenticated=True,
        fresh=True,
        registered_egg_variants={"neighborhood"},
    )
    refused = accept_egg(neighborhood, registry=incomplete_registry)
    assert not refused.accepted
    assert refused.trust_status is TrustStatus.UNVERIFIED
    assert "organism" in refused.checks[-1].detail

    work = Path.cwd() / f".rapp1-nested-registry-{os.getpid()}"
    shutil.rmtree(work, ignore_errors=True)
    try:
        with pytest.raises(EggError) as error:
            extract_egg(
                neighborhood,
                work / "neighborhood",
                registry=incomplete_registry,
            )
        assert error.value.code == "egg-not-accepted"
        assert not work.exists()
    finally:
        shutil.rmtree(work, ignore_errors=True)

    complete_registry = RegistryEvidence(
        authenticated=True,
        fresh=True,
        registered_egg_variants={"neighborhood", "organism"},
    )
    verified = accept_egg(neighborhood, registry=complete_registry)
    assert verified.accepted
    assert verified.trust_status is TrustStatus.VERIFIED


def test_registered_egg_variant_evidence_is_immutable() -> None:
    variants = {"organism"}
    registry = RegistryEvidence(
        authenticated=True,
        fresh=True,
        registered_egg_variants=variants,
    )
    variants.clear()

    assert registry.registered_egg_variants == frozenset({"organism"})
    with pytest.raises(AttributeError):
        registry.registered_egg_variants.add("invite")


@pytest.mark.parametrize(
    "path",
    [
        "C:escape.txt",
        "C:/escape.txt",
        "state/data:alternate",
        "CON",
        "state/trailing.",
        "state/trailing ",
    ],
)
def test_structural_egg_paths_accept_all_relative_nfc_posix_names(
    path: str,
) -> None:
    assert validate_egg_path(path) == path


@pytest.mark.parametrize(
    "path",
    [
        "C:escape.txt",
        "C:/escape.txt",
        "state/data:alternate",
        "CON",
        "state/trailing.",
        "state/trailing ",
    ],
)
def test_windows_extraction_refuses_unrepresentable_structural_paths(
    path: str,
) -> None:
    with pytest.raises(EggError) as error:
        _validate_extraction_path(path, platform="nt")
    assert error.value.code == "unsafe-extraction-path"


def test_unknown_extraction_platform_fails_closed() -> None:
    with pytest.raises(EggError) as error:
        _validate_extraction_path("safe.txt", platform="unknown")
    assert error.value.code == "unsafe-extraction-path"


def test_posix_extraction_preserves_structurally_valid_special_names() -> None:
    if os.name != "posix":
        pytest.skip("special-name extraction is a POSIX-platform check")
    work = Path.cwd() / f".rapp1-posix-path-test-{os.getpid()}"
    shutil.rmtree(work, ignore_errors=True)
    try:
        egg = pack_egg(
            variant="organism",
            rappid=RID_ORG1,
            created_utc=UTC,
            payload={},
            files={
                "rappid.json": b"{}",
                "soul.md": b"soul",
                "state/data:alternate": b"colon",
                "CON": b"reserved elsewhere",
                "trailing.": b"dot",
                "trailing ": b"space",
            },
        )
        report = inspect_egg(egg)
        assert report.structurally_valid
        target = work / "hatched"
        extract_egg(
            egg,
            target,
            registry=RegistryEvidence(
                authenticated=True,
                fresh=True,
                registered_egg_variants={"organism"},
            ),
        )
        assert (target / "state/data:alternate").read_bytes() == b"colon"
        assert (target / "CON").read_bytes() == b"reserved elsewhere"
        assert (target / "trailing.").read_bytes() == b"dot"
        assert (target / "trailing ").read_bytes() == b"space"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_pack_egg_requires_nfc_producer_payload_keys_and_identifiers() -> None:
    with pytest.raises(EggError) as key_error:
        pack_egg(
            variant="organism",
            rappid=RID_ORG1,
            created_utc=UTC,
            payload={"nested": [{"Cafe\u0301": True}]},
            files={"rappid.json": b"{}", "soul.md": b"soul"},
        )
    assert key_error.value.code == "invalid-egg-payload"

    with pytest.raises(EggError) as identifier_error:
        pack_egg(
            variant="session",
            rappid=RID_SESSION,
            created_utc=UTC,
            payload={"runtime": "Cafe\u0301", "transcript": []},
        )
    assert identifier_error.value.code == "invalid-session-payload"


def test_egg_inspection_never_normalizes_existing_payload_keys() -> None:
    files = {"rappid.json": b"{}", "soul.md": b"soul"}
    manifest = {
        "schema": "rapp/1-egg",
        "variant": "organism",
        "rappid": RID_ORG1,
        "created_utc": UTC,
        "contents": [
            {"path": path, "hash": hash_bytes(EGG_FILE_SPACE, files[path])}
            for path in sorted(files, key=lambda value: value.encode("utf-8"))
        ],
        "payload": {"Cafe\u0301": True},
        "sig": None,
    }
    raw = _encode_zip(
        [("manifest.json", canonical_bytes(manifest))]
        + [
            (path, files[path])
            for path in sorted(files, key=lambda value: value.encode("utf-8"))
        ]
    )

    inspected = inspect_egg(raw)

    assert inspected.structurally_valid
    assert inspected.manifest is not None
    assert "Cafe\u0301" in inspected.manifest["payload"]
    assert "Café" not in inspected.manifest["payload"]


def test_resolved_staging_guard_contains_dotdot_and_symlinks() -> None:
    work = Path.cwd() / f".rapp1-path-guard-{os.getpid()}"
    shutil.rmtree(work, ignore_errors=True)
    try:
        stage = work / "stage"
        outside = work / "outside"
        stage.mkdir(parents=True)
        outside.mkdir()
        with pytest.raises(EggError, match="outside staging"):
            _resolved_staging_path(stage, "../outside/escape")
        assert not (outside / "escape").exists()

        link = stage / "link"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError:
            pytest.skip("platform does not permit symlink creation")
        with pytest.raises(EggError, match="outside staging"):
            _resolved_staging_path(stage, "link/escape")
        assert not (outside / "escape").exists()
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_verify_before_extract_and_staged_success() -> None:
    work = Path.cwd() / f".rapp1-core-test-{os.getpid()}"
    shutil.rmtree(work, ignore_errors=True)
    try:
        invalid_parent = work / "must-not-exist"
        with pytest.raises(EggError):
            extract_egg(b"not an egg", invalid_parent / "out")
        assert not invalid_parent.exists()

        work.mkdir()
        target = work / "hatched"
        with pytest.raises(EggError) as untrusted:
            extract_egg(_organism(), target)
        assert untrusted.value.code == "egg-not-accepted"
        assert not target.exists()

        with pytest.raises(EggError) as stale:
            extract_egg(
                _organism(),
                target,
                registry=RegistryEvidence(authenticated=True, fresh=False),
            )
        assert stale.value.code == "egg-not-accepted"
        assert not target.exists()

        registry = RegistryEvidence(
            authenticated=True,
            fresh=True,
            registered_egg_variants={"organism"},
        )
        extract_egg(_organism(), target, registry=registry)
        assert (target / "manifest.json").is_file()
        assert (target / "rappid.json").is_file()
        assert (target / "soul.md").read_bytes() == b"soul\n"
        assert not list(work.glob(".hatched.rapp1-stage-*"))
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_signed_root_or_nested_egg_never_extracts_without_crypto_verification() -> None:
    work = Path.cwd() / f".rapp1-signed-extract-{os.getpid()}"
    shutil.rmtree(work, ignore_errors=True)
    registry = RegistryEvidence(
        authenticated=True,
        fresh=True,
        registered_egg_variants={"organism", "neighborhood"},
    )
    try:
        work.mkdir()
        signed_root = pack_egg(
            variant="organism",
            rappid=RID_ORG1,
            created_utc=UTC,
            payload={},
            files={"rappid.json": b"{}", "soul.md": b"soul"},
            sig=_jws(),
        )
        with pytest.raises(EggError) as root_error:
            extract_egg(signed_root, work / "root", registry=registry)
        assert root_error.value.code == "signed-egg-unverified"
        assert not (work / "root").exists()

        signed_child = pack_egg(
            variant="organism",
            rappid=RID_ORG1,
            created_utc=UTC,
            payload={},
            files={"rappid.json": b"{}", "soul.md": b"soul"},
            sig=_jws(),
        )
        nested = pack_egg(
            variant="neighborhood",
            rappid=RID_NEIGHBORHOOD,
            created_utc=UTC,
            payload={"members": [RID_ORG1]},
            files={"kody-w--one.egg": signed_child},
        )
        with pytest.raises(EggError) as nested_error:
            extract_egg(nested, work / "nested", registry=registry)
        assert nested_error.value.code == "signed-egg-unverified"
        assert not (work / "nested").exists()
    finally:
        shutil.rmtree(work, ignore_errors=True)
