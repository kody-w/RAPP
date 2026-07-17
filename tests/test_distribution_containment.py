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
    "installer/install.sh",
    "installer/install-swarm.sh",
    "installer/start-local.sh",
    "installer/integration_plant.sh",
    "rapp_brainstem/start.sh",
)
RETIRED_POWERSHELL_ENTRYPOINTS = (
    "install.ps1",
    "community_rapp/install.ps1",
    "deploy.ps1",
    "installer/install.ps1",
    "rapp_brainstem/start.ps1",
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


def test_unix_installer_fails_closed_without_an_incomplete_lock_path():
    source = (ROOT / "installer/install.sh").read_text(encoding="utf-8")
    assert "410 Gone" in source
    assert "No complete target-owned lock" in source
    assert "exit 78" in source
    for marker in (
        "git ",
        "pip ",
        "venv",
        "requirements.txt",
        "KERNEL_TAG",
        "sha256",
        "curl ",
    ):
        assert marker not in source


def test_installer_rejects_moved_tag_changed_agent_and_requirements():
    scratch = ROOT / f"tests/.rapp1-installer-attacks-{os.getpid()}"
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        fake_bin = scratch / "bin"
        fake_bin.mkdir(parents=True)
        for name in (
            "curl",
            "git",
            "pip",
            "python3",
            "python3.11",
            "python3.12",
            "python3.13",
        ):
            fake_tool = fake_bin / name
            fake_tool.write_text(
                (
                    "#!/usr/bin/env bash\n"
                    'printf "%s\\n" "${0##*/}" >> "$RAPP_TEST_SENTINEL"\n'
                    "exit 99\n"
                ),
                encoding="utf-8",
            )
            fake_tool.chmod(0o755)

        frozen = json.loads(
            (ROOT / "KERNEL_PIN.json").read_text(encoding="utf-8")
        )["kernel"]["frozen"]
        for attack in ("moved-tag", "changed-agent", "changed-requirements"):
            remote = scratch / attack
            for relative in frozen:
                destination = remote / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes((ROOT / relative).read_bytes())
            (remote / "rapp_brainstem/requirements.txt").write_text(
                "flask==3.1.0\n",
                encoding="utf-8",
            )
            if attack == "moved-tag":
                (remote / ".simulated-tag-target").write_text(
                    "attacker-controlled-commit\n",
                    encoding="utf-8",
                )
                (remote / "rapp_brainstem/agents/tag_payload_agent.py").write_text(
                    "raise RuntimeError('moved tag payload executed')\n",
                    encoding="utf-8",
                )
            elif attack == "changed-agent":
                (remote / "rapp_brainstem/agents/unlocked_agent.py").write_text(
                    "raise RuntimeError('unlocked agent executed')\n",
                    encoding="utf-8",
                )
            else:
                (remote / "rapp_brainstem/requirements.txt").write_text(
                    "unlocked-package @ https://example.invalid/moved.whl\n",
                    encoding="utf-8",
                )
            for relative, digest in frozen.items():
                assert _sha256(remote / relative) == digest

            home = scratch / f"home-{attack}"
            if attack != "moved-tag":
                shutil.copytree(remote, home / "src")
            before = {
                path.relative_to(remote): path.read_bytes()
                for path in remote.rglob("*")
                if path.is_file()
            }
            installed_before = {
                path.relative_to(home): path.read_bytes()
                for path in home.rglob("*")
                if path.is_file()
            }
            sentinel = scratch / f"{attack}-tool-was-invoked"
            environment = os.environ.copy()
            environment.update(
                {
                    "BRAINSTEM_HOME": os.fspath(home),
                    "PATH": os.pathsep.join(
                        (os.fspath(fake_bin), environment.get("PATH", ""))
                    ),
                    "RAPP_TEST_REMOTE_TREE": os.fspath(remote),
                    "RAPP_TEST_SENTINEL": os.fspath(sentinel),
                }
            )
            result = subprocess.run(
                ("bash", "installer/install.sh"),
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            assert result.returncode == 78, attack
            assert "410 Gone" in result.stderr, attack
            assert not sentinel.exists(), f"{attack}: installer invoked a tool"
            if attack == "moved-tag":
                assert not home.exists(), attack
            assert before == {
                path.relative_to(remote): path.read_bytes()
                for path in remote.rglob("*")
                if path.is_file()
            }, f"{attack}: simulated source bytes changed"
            assert installed_before == {
                path.relative_to(home): path.read_bytes()
                for path in home.rglob("*")
                if path.is_file()
            }, f"{attack}: installed source bytes changed"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


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
        if relative == "tests/test-t2t-removal.sh":
            source = path.read_text(encoding="utf-8")
            assert 'function_app.py refuses execution" "78"' in source
            assert "function_app.py reports 410 Gone" in source
            assert not re.search(r"(?m)^\s*(?:az|func)\b", source)
            continue
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
        assert "RAPP/installer/install.sh" not in source
        assert "No active installer" in source or "No installer command" in source
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


def test_cave_check_rejects_mutated_protected_headers():
    scratch = ROOT / f"tests/.rapp1-cave-headers-{os.getpid()}"
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        cave = scratch / "cave"
        (cave / "tools").mkdir(parents=True)
        shutil.copy2(
            ROOT / "cave/tools/build_super_rar.py",
            cave / "tools/build_super_rar.py",
        )
        shutil.copytree(ROOT / "cave/agents", cave / "agents")
        shutil.copytree(ROOT / "cave/cubbies", cave / "cubbies")
        (cave / "rapplications/rapp-installer").mkdir(parents=True)
        for directory in ("rar", "super-rar"):
            (cave / directory).mkdir()
            shutil.copy2(
                ROOT / f"cave/{directory}/index.json",
                cave / directory / "index.json",
            )

        command = (sys.executable, "cave/tools/build_super_rar.py", "--check")
        baseline = subprocess.run(
            command,
            cwd=scratch,
            text=True,
            capture_output=True,
            check=False,
        )
        assert baseline.returncode == 0, baseline.stdout + baseline.stderr

        mutations = (
            ("super-rar", "schema"),
            ("super-rar", "raw_url_prefix"),
            ("rar", "kind"),
            ("rar", "note"),
        )
        for directory, field in mutations:
            index = cave / directory / "index.json"
            original = index.read_bytes()
            document = json.loads(original)
            document[field] = f"mutated-{field}"
            index.write_text(
                json.dumps(document, indent=2) + "\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                command,
                cwd=scratch,
                text=True,
                capture_output=True,
                check=False,
            )
            assert result.returncode == 1, (directory, field, result.stdout)
            assert f"DRIFT: {directory}/index.json" in result.stdout
            index.write_bytes(original)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
