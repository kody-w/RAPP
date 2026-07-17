from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest

from rapp1_core import parse_rappid


ROOT = Path(__file__).resolve().parents[1]
PARENT_RAPPID = (
    "rappid:@kody-w/rapp:"
    "9a8f0a4b5a710e20f4d819a0f37d2a4c9f113b5e78fb3c29e70b54fff48a38f9"
)


@pytest.fixture
def variant_repo():
    parent = ROOT / "tests" / ".initialize-variant-test-data"
    repo = parent / str(uuid.uuid4())
    (repo / "installer").mkdir(parents=True)
    (repo / "rapp_brainstem" / "utils").mkdir(parents=True)
    shutil.copy2(
        ROOT / "installer" / "initialize-variant.sh",
        repo / "installer" / "initialize-variant.sh",
    )
    shutil.copy2(
        ROOT / "rapp_brainstem" / "utils" / "lineage_check.py",
        repo / "rapp_brainstem" / "utils" / "lineage_check.py",
    )
    fake_bin = repo / "test-bin"
    fake_bin.mkdir()
    fake_curl = fake_bin / "curl"
    fake_curl.write_text(
        "#!/bin/sh\n"
        "printf '%s\\n' "
        "'{\"sha\":\"1111111111111111111111111111111111111111\"}'\n",
        encoding="utf-8",
    )
    fake_curl.chmod(0o755)
    (repo / "rappid.json").write_text(
        json.dumps(
            {
                "schema": "rapp/1",
                "rappid": PARENT_RAPPID,
                "kind": "prototype",
                "parent_rappid": None,
                "description": "template",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    commands = (
        ["git", "init", "-q"],
        ["git", "config", "user.name", "RAPP Test"],
        ["git", "config", "user.email", "rapp-test@example.invalid"],
        ["git", "add", "."],
        ["git", "commit", "-q", "-m", "template"],
        [
            "git",
            "remote",
            "add",
            "origin",
            "https://github.com/alice/example-variant.git",
        ],
    )
    for command in commands:
        subprocess.run(command, cwd=repo, check=True)
    try:
        yield repo
    finally:
        shutil.rmtree(repo, ignore_errors=True)
        try:
            parent.rmdir()
        except OSError:
            pass


def _run(repo: Path, stdin: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["PATH"] = f"{repo / 'test-bin'}{os.pathsep}{env['PATH']}"
    return subprocess.run(
        ["bash", "installer/initialize-variant.sh"],
        cwd=repo,
        input=stdin,
        text=True,
        capture_output=True,
        env=env,
        check=False,
        timeout=30,
    )


def test_fresh_template_mints_once_and_rerun_reuses_bytes(variant_repo):
    first = _run(variant_repo, "Example Variant\n")
    assert first.returncode == 0, first.stderr + first.stdout
    identity_path = variant_repo / "rappid.json"
    first_bytes = identity_path.read_bytes()
    record = json.loads(first_bytes)
    parsed = parse_rappid(record["rappid"])
    assert (parsed.owner, parsed.slug) == ("alice", "example-variant")
    assert record["parent_rappid"] == PARENT_RAPPID
    assert record["kind"] == "prototype"
    assert record["role"] == "variant"

    second = _run(variant_repo, "yes\nDifferent Name\n")
    assert second.returncode == 0, second.stderr + second.stdout
    assert "Reusing mint-once identity" in second.stdout
    assert identity_path.read_bytes() == first_bytes


def test_realistic_root_template_scrubs_only_root_identity_evidence(variant_repo):
    template = json.loads((ROOT / "rappid.json").read_bytes())
    template.update(
        {
            "attestation": {
                "issuer": PARENT_RAPPID,
                "note": "root-only fixture evidence",
            },
            "_migration_commit": "unsigned-root-migration",
            "_reanchor_record": {"case": "upgrade"},
            "_root_provenance": {"commit": "root-only"},
            "_attestation_record": {"issuer": PARENT_RAPPID},
            "_product_note": "preserve this product metadata",
            "_product_provenance": "preserve product origin",
            "private_companion": "rapp-private",
            "product_metadata": {
                "theme": "charizard",
                "capabilities": ["local"],
            },
        }
    )
    (variant_repo / "rappid.json").write_text(
        json.dumps(template, indent=2) + "\n",
        encoding="utf-8",
    )

    result = _run(variant_repo, "Root Template Child\n")
    assert result.returncode == 0, result.stderr + result.stdout
    child = json.loads((variant_repo / "rappid.json").read_bytes())

    for key in (
        "_migrated_from",
        "_legacy_uuid",
        "_legacy_uuid_note",
        "_attestation_note",
        "_migration_commit",
        "_reanchor_record",
        "_root_provenance",
        "_attestation_record",
    ):
        assert key not in child
    assert child["attestation"] is None
    assert child["_product_note"] == "preserve this product metadata"
    assert child["_product_provenance"] == "preserve product origin"
    assert child["private_companion"] == "rapp-private"
    assert child["product_metadata"] == {
        "theme": "charizard",
        "capabilities": ["local"],
    }
    assert child["kind"] == template["kind"]
    assert child["description"] == template["description"]
    assert child["rappid"] != PARENT_RAPPID
    assert child["parent_rappid"] == PARENT_RAPPID
    assert child["role"] == "variant"


def test_sparse_lineage_guard_runs_without_core_or_site_packages(variant_repo):
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [
            "python3.11",
            "-I",
            "rapp_brainstem/utils/lineage_check.py",
        ],
        cwd=variant_repo,
        text=True,
        capture_output=True,
        env=env,
        check=False,
        timeout=10,
    )
    assert result.returncode == 1
    assert '"status": "variant_uninitialized"' in result.stdout
    assert "ModuleNotFoundError" not in result.stderr


def test_concurrent_initializers_mint_exactly_once(variant_repo):
    shim = variant_repo / "rapp1_core.py"
    shim.write_text(
        """
import hashlib
import time
import uuid


def mint_keyless_rappid(owner, slug):
    with open("mint-calls", "ab", buffering=0) as handle:
        handle.write(b"mint\\n")
    time.sleep(0.5)
    tail = hashlib.sha256(
        b"rapp/1:rappid\\n" + uuid.uuid4().bytes
    ).hexdigest()
    return f"rappid:@{owner}/{slug}:{tail}"
""".lstrip(),
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["PATH"] = (
        f"{variant_repo / 'test-bin'}{os.pathsep}{env['PATH']}"
    )
    command = ["bash", "installer/initialize-variant.sh"]
    first = subprocess.Popen(
        command,
        cwd=variant_repo,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    second = subprocess.Popen(
        command,
        cwd=variant_repo,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    assert first.stdin is not None and second.stdin is not None
    first.stdin.write("First Variant\n")
    first.stdin.close()
    second.stdin.write("Second Variant\n")
    second.stdin.close()

    assert first.wait(timeout=20) == 0
    assert second.wait(timeout=20) == 0
    assert first.stdout is not None and first.stderr is not None
    assert second.stdout is not None and second.stderr is not None
    first_output = first.stdout.read() + first.stderr.read()
    second_output = second.stdout.read() + second.stderr.read()

    identity = json.loads((variant_repo / "rappid.json").read_bytes())
    parsed = parse_rappid(identity["rappid"])
    assert (parsed.owner, parsed.slug) == ("alice", "example-variant")
    assert (variant_repo / "mint-calls").read_text().splitlines() == ["mint"]
    assert "Reusing mint-once identity" in first_output + second_output
    assert not list(variant_repo.glob(".rappid.json.initialize-*"))
    git_dir = subprocess.run(
        ["git", "rev-parse", "--absolute-git-dir"],
        cwd=variant_repo,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    assert not (Path(git_dir) / "rapp-initialize.lock").exists()
