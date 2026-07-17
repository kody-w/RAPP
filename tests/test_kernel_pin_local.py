"""Regression tests for the offline-only kernel pin verifier."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = ROOT / "tests/check_kernel_pin_local.py"
spec = importlib.util.spec_from_file_location("check_kernel_pin_local", VERIFIER_PATH)
verifier = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = verifier
spec.loader.exec_module(verifier)


def test_repository_local_pin_matches_all_frozen_bytes():
    results, errors = verifier.verify_local_pin()
    assert errors == []
    assert {relative for relative, _, _ in results} == {
        "rapp_brainstem/brainstem.py",
        "rapp_brainstem/agents/basic_agent.py",
        "rapp_brainstem/VERSION",
    }


def test_local_pin_verifier_rejects_byte_drift():
    scratch = ROOT / "tests/.rapp1-local-pin-test"
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        frozen = scratch / "kernel.bin"
        frozen.parent.mkdir(parents=True)
        frozen.write_bytes(b"changed")
        expected = hashlib.sha256(b"expected").hexdigest()
        pin = {
            "spec": "rapp-distro/1.0",
            "kernel": {"frozen": {"kernel.bin": expected}},
        }
        pin_path = scratch / "KERNEL_PIN.json"
        pin_path.write_text(json.dumps(pin), encoding="utf-8")

        _, errors = verifier.verify_local_pin(scratch, pin_path)

        assert len(errors) == 1
        assert errors[0].startswith("frozen byte mismatch: kernel.bin:")
        assert frozen.read_bytes() == b"changed"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_local_pin_verifier_has_no_network_client():
    source = VERIFIER_PATH.read_text(encoding="utf-8")
    for forbidden in ("urllib", "requests", "urlopen", "http://", "https://"):
        assert forbidden not in source
