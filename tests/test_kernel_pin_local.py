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


def test_repository_local_pin_has_canonical_shape():
    results, errors = verifier.verify_local_pin()
    assert errors == []
    assert results == []
    pin = json.loads((ROOT / "kernel.json").read_text(encoding="utf-8"))
    assert pin["sha"] == "0e43ee580e78c150b1c59002456822d2e779388e"
    assert pin["version"] == "0.6.16"
    assert pin["kernel_blob"] == "3f7102ff508c813bb6494511fc32a421a633e418"


def test_local_pin_verifier_rejects_vendored_byte_drift():
    scratch = ROOT / "tests/.rapp1-local-pin-test"
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        frozen = scratch / "kernel.bin"
        frozen.parent.mkdir(parents=True)
        frozen.write_bytes(b"changed")
        expected = hashlib.sha256(b"expected").hexdigest()
        pin = {
            "kernel": "kody-w/rapp-installer",
            "sha": "0" * 40,
            "version": "0.0.0",
            "path": "kernel.bin",
            "kernel_blob": "1" * 40,
            "vendored": {"kernel.bin": expected},
        }
        pin_path = scratch / "kernel.json"
        pin_path.write_text(json.dumps(pin), encoding="utf-8")

        _, errors = verifier.verify_local_pin(scratch, pin_path)

        assert len(errors) == 1
        assert errors[0].startswith("vendored byte mismatch: kernel.bin:")
        assert frozen.read_bytes() == b"changed"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_local_pin_verifier_has_no_network_client():
    source = VERIFIER_PATH.read_text(encoding="utf-8")
    for forbidden in ("urllib", "requests", "urlopen", "http://", "https://"):
        assert forbidden not in source
