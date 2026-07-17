from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from rapp1_core.identity import parse_rappid

RID = "rappid:@kody-w/cli:" + "9" * 64
UTC = "2026-07-16T22:41:23.842Z"


def _run(*args: str, input_bytes: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "rapp1_core", *args],
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_validate_output_never_conflates_structure_and_acceptance() -> None:
    result = _run("validate", "json", "-", input_bytes=b'{"b":1,"a":2}')
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output["structurally-valid"] is True
    assert output["accepted"] is False
    assert output["trust-status"] == "UNVERIFIED"
    assert output["source-is-canonical"] is False

    duplicate = _run("validate", "json", "-", input_bytes=b'{"a":1,"a":2}')
    assert duplicate.returncode == 2
    failure = json.loads(duplicate.stdout)
    assert failure["structurally-valid"] is False
    assert failure["accepted"] is False
    assert failure["trust-status"] == "DRIFT"


def test_keyless_mint_cli_emits_conformant_rappid() -> None:
    result = _run("mint", "keyless", "kody-w", "cli-minted")
    assert result.returncode == 0
    output = json.loads(result.stdout)
    parse_rappid(output["rappid"])
    assert output["mint"] == "keyless"
    assert output["accepted"] is False


def test_pack_and_inspect_session_cli() -> None:
    work = Path.cwd() / f".rapp1-cli-test-{os.getpid()}"
    shutil.rmtree(work, ignore_errors=True)
    try:
        work.mkdir()
        payload = work / "payload.json"
        payload.write_bytes(b'{"runtime":"python","transcript":[]}')
        egg = work / "session.egg"
        packed = _run(
            "pack",
            "session",
            str(egg),
            "--rappid",
            RID,
            "--created-utc",
            UTC,
            "--payload",
            str(payload),
        )
        assert packed.returncode == 0, packed.stdout + packed.stderr
        pack_report = json.loads(packed.stdout)
        assert pack_report["structurally-valid"] is True
        assert pack_report["accepted"] is False

        inspected = _run("inspect", "egg", str(egg))
        assert inspected.returncode == 0
        inspect_report = json.loads(inspected.stdout)
        assert inspect_report["variant"] == "session"
        assert inspect_report["accepted"] is False
        assert inspect_report["trust-status"] == "UNVERIFIED"
    finally:
        shutil.rmtree(work, ignore_errors=True)
