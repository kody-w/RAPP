from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIVE_INVENTORY = ROOT / "tests/rapp1-live-surface-inventory.json"

RETIRED_SHELL_ENTRYPOINTS = (
    "install.sh",
    "install.command",
    "docs/install.sh",
    "docs/install.command",
    "community_rapp/install.sh",
    "deploy.sh",
    "installer/install-swarm.sh",
    "installer/start-local.sh",
    "installer/integration_plant.sh",
)
RETIRED_POWERSHELL_ENTRYPOINTS = (
    "install.ps1",
    "community_rapp/install.ps1",
    "deploy.ps1",
    "installer/install.ps1",
)
RETIRED_CMD_ENTRYPOINTS = (
    "install.cmd",
    "docs/install.cmd",
    "installer/install.cmd",
)
RETIRED_BROWSER_ROUTES = (
    "installer/plant.html",
    "installer/plant_qr.html",
    "installer/seed.html",
    "pages/metropolis/plant-from-discord.html",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_live_surface_inventory_uses_dynamic_counts_and_required_categories():
    inventory = json.loads(LIVE_INVENTORY.read_text(encoding="utf-8"))
    assert inventory["schema"] == "rapp1-live-surface-inventory/1.0"
    assert set(inventory["categories"]) == {
        "installer",
        "marketing",
        "containment",
        "browser",
        "wire",
    }
    assert "git ls-files" in inventory["count_policy"]
    for category, paths in inventory["categories"].items():
        assert paths, f"empty live inventory category: {category}"
        for relative in paths:
            assert (ROOT / relative).is_file(), f"stale {category} path: {relative}"


def test_unix_installer_fetches_only_exact_tag_and_verifies_kernel_pin():
    source = (ROOT / "installer/install.sh").read_text(encoding="utf-8")
    pin = json.loads((ROOT / "KERNEL_PIN.json").read_text(encoding="utf-8"))
    assert pin["kernel"]["tag"] == "brainstem-v0.6.9"
    assert f'KERNEL_TAG="{pin["kernel"]["tag"]}"' in source
    for relative, digest in pin["kernel"]["frozen"].items():
        assert f"{digest} {relative}" in source
    assert "--single-branch --branch \"$KERNEL_TAG\"" in source
    assert "verify_kernel \"$STAGE_DIR\"" in source
    assert "verify_kernel \"$SRC_DIR\"" in source
    assert "origin/main" not in source
    assert "/main/" not in source
    assert "PIN_REF=\"main\"" not in source
    assert "BRAINSTEM_FORCE_KERNEL_REFRESH" not in source
    assert not re.search(r"\bcp\b[^\n]*(brainstem\.py|basic_agent\.py|VERSION)", source)


def _installed_kernel_fixture(name: str) -> tuple[Path, dict[str, bytes]]:
    home = ROOT / f"tests/.rapp1-installer-{name}-{os.getpid()}"
    shutil.rmtree(home, ignore_errors=True)
    frozen = json.loads((ROOT / "KERNEL_PIN.json").read_text(encoding="utf-8"))[
        "kernel"
    ]["frozen"]
    expected = {}
    for relative in frozen:
        data = (ROOT / relative).read_bytes()
        destination = home / "src" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        expected[relative] = data
    return home, expected


def test_unix_installer_verify_only_preserves_existing_pinned_bytes():
    home, expected = _installed_kernel_fixture("verify")
    try:
        environment = os.environ.copy()
        environment["BRAINSTEM_HOME"] = os.fspath(home)
        result = subprocess.run(
            ("bash", "installer/install.sh", "--verify-only"),
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert "pinned bytes were not rewritten" in result.stdout
        for relative, data in expected.items():
            assert (home / "src" / relative).read_bytes() == data
    finally:
        shutil.rmtree(home, ignore_errors=True)


def test_unix_installer_verify_only_fails_closed_on_pin_drift():
    home, _ = _installed_kernel_fixture("drift")
    try:
        version = home / "src/rapp_brainstem/VERSION"
        version.write_bytes(version.read_bytes() + b"tamper")
        environment = os.environ.copy()
        environment["BRAINSTEM_HOME"] = os.fspath(home)
        result = subprocess.run(
            ("bash", "installer/install.sh", "--verify-only"),
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 78
        assert "Pinned file hash mismatch: rapp_brainstem/VERSION" in result.stderr
        assert version.read_bytes().endswith(b"tamper")
    finally:
        shutil.rmtree(home, ignore_errors=True)


def test_retired_shell_entrypoints_are_side_effect_free_410s():
    forbidden = (
        "curl ",
        "git clone",
        "git fetch",
        "git push",
        "mktemp",
        "/tmp/",
        "function_app.py",
    )
    for relative in RETIRED_SHELL_ENTRYPOINTS:
        path = ROOT / relative
        assert path.stat().st_mode & stat.S_IXUSR
        source = path.read_text(encoding="utf-8")
        for marker in forbidden:
            assert marker not in source, f"{relative} retains side effect: {marker}"
        assert not re.search(
            r"(?m)^\s*(?:curl|gh|az|func|npm|pip)\b",
            source,
        ), f"{relative} retains an executable side-effect command"
        result = subprocess.run(
            ("bash", relative),
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 78
        assert "410 Gone" in result.stderr


def test_windows_installers_fail_closed_without_mutable_fetch_or_newline_escape():
    forbidden = (
        "Invoke-WebRequest",
        "Invoke-RestMethod",
        "raw.githubusercontent.com",
        "/main/",
        "git clone",
        "Start-Process",
        "function_app.py",
    )
    for relative in RETIRED_POWERSHELL_ENTRYPOINTS:
        data = (ROOT / relative).read_bytes()
        source = data.decode("utf-8")
        assert "410 Gone" in source
        assert "exit 78" in source
        assert b"\\n" not in data
        assert b"\r" not in data
        for marker in forbidden:
            assert marker not in source, f"{relative} retains {marker}"
    for relative in RETIRED_CMD_ENTRYPOINTS:
        source = (ROOT / relative).read_text(encoding="utf-8")
        assert "410 Gone" in source
        assert "exit /b 78" in source
        assert "powershell" not in source.lower()
        assert "http" not in source.lower()


def test_tier2_deployment_descriptors_and_callers_create_nothing():
    for relative in ("azuredeploy.json", "installer/azuredeploy.json"):
        descriptor = json.loads((ROOT / relative).read_text(encoding="utf-8"))
        assert descriptor == {
            "schema": "rapp-retired-deployment/1.0",
            "status": "410 Gone",
            "retired": True,
            "provisioning_allowed": False,
            "resources": [],
            "guidance": (
                "RAPP1_STATUS.md"
                if relative == "azuredeploy.json"
                else "../RAPP1_STATUS.md"
            ),
        }
    inventory = json.loads(LIVE_INVENTORY.read_text(encoding="utf-8"))
    callers = set(inventory["categories"]["installer"])
    callers.update(inventory["categories"]["containment"])
    for relative in callers:
        path = ROOT / relative
        if relative == "rapp_swarm/RAPP1_DEPLOYMENT_GUARD.json":
            guard = json.loads(path.read_text(encoding="utf-8"))
            assert guard["status"] == "retired"
            assert guard["rapp1_packaging_allowed"] is False
            continue
        if path.suffix.lower() in {".sh", ".ps1", ".cmd", ".json"}:
            assert "function_app.py" not in path.read_text(
                encoding="utf-8"
            ), f"legacy function remains reachable from {relative}"


def test_retired_archive_manifest_pins_bytes_without_active_publication():
    manifest = json.loads(
        (ROOT / "installer/RETIRED_ARTIFACTS.json").read_text(encoding="utf-8")
    )
    assert manifest["status"] == "retired"
    assert manifest["publication_allowed"] is False
    assert manifest["repacking_allowed"] is False
    assert manifest["power_archive"]["signature_status"] == "unsigned"
    assert manifest["power_archive"]["active_download_allowed"] is False
    records = [
        *manifest["power_archive"]["copies"],
        *manifest["immutable_eggs"],
    ]
    assert len(records) == 7
    for record in records:
        path = ROOT / record["path"]
        assert path.stat().st_size == record["bytes"]
        assert _sha256(path) == record["sha256"]


def test_owned_distribution_pages_publish_neither_tier2_nor_power_archive():
    for relative in ("index.html", "installer/index.html"):
        source = (ROOT / relative).read_text(encoding="utf-8")
        assert "install-swarm.sh" not in source
        assert "azuredeploy.json" not in source
        assert "install.ps1" not in source
        assert not re.search(
            r"<a\b[^>]*\bhref=[\"'][^\"']*MSFTAIBASMultiAgentCopilot",
            source,
            flags=re.IGNORECASE,
        )
        assert "no active download link" in source


def test_plant_browser_callers_are_static_410s():
    forbidden = (
        "<script",
        "<iframe",
        "<form",
        "<button",
        "fetch(",
        "localstorage",
        "github.com",
        "plant.sh",
    )
    for relative in RETIRED_BROWSER_ROUTES:
        source = (ROOT / relative).read_text(encoding="utf-8").lower()
        assert "http 410" in source
        assert "rapp1_status.md" in source
        for marker in forbidden:
            assert marker not in source, f"{relative} retains caller marker: {marker}"
    metropolis = (ROOT / "pages/metropolis/index.html").read_text(encoding="utf-8")
    assert "plant-from-discord" not in metropolis


def test_cave_indexes_classify_prepared_installer_as_retired():
    rar = json.loads((ROOT / "cave/rar/index.json").read_text(encoding="utf-8"))
    installer = next(
        entry for entry in rar["rapps"] if entry["name"] == "@kody-w/rapp-installer"
    )
    assert installer["status"] == "retired"
    assert installer["active_distribution"] is False
    assert installer["immutable_prepared_snapshot"] is True
    assert "pull:" not in installer["purpose"].lower()
    assert "curl " not in installer["purpose"].lower()
    result = subprocess.run(
        (sys.executable, "cave/tools/build_super_rar.py", "--check"),
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
