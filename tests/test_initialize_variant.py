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
