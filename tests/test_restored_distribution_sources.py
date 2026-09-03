from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PIN_SHA256 = "427a37cc914a279b9c32a2ab85be9a19a0046f10f9f503c088a2670b6646e21c"
FROZEN = {
    "rapp_brainstem/brainstem.py": "a293dd9f11eef915bf15776f08c736faa60cb749820871b6753ea98233142a71",
    "rapp_brainstem/agents/basic_agent.py": "701488bc00d536a7b23295e7da99c62f24e9b00f233daa325886430c736b78eb",
    "rapp_brainstem/VERSION": "13eb74b44be6e3a85a0efa0dedf56aec05e9e50140e1c8bbc0d0fbd8097b0717",
}

SOURCES = {
    "install.sh": (
        "25dc094994cf889f0907ea15c255000c07dbfcc9",
        "758b033579047fd1f78b9bae2967e282e3470882",
        ("check_for_upgrade()", "install_service()", "launch_brainstem()", "git reset --hard"),
    ),
    "install.ps1": (
        "cef3b9160f0ca6773d84ccc605e2d5d81369b2d9",
        "2fe5b2613af50d3535f38edd4531934041f524f6",
        (
            "function Check-ForUpgrade",
            "function Install-Service",
            "function Launch-Brainstem",
            "Register-ScheduledTask",
        ),
    ),
    "install.cmd": (
        "4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6",
        "03506ae1ab55d666f8fc47e9248afe4a54e15c72",
        ("powershell -ExecutionPolicy Bypass", "raw.githubusercontent.com", "pause"),
    ),
    "install.command": (
        "4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6",
        "6d444ac6e2303bc5cb694884ad9e4931be959048",
        ("curl -fsSL", "rapp-installer/install.sh", "bash"),
    ),
    "docs/install.sh": (
        "4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6",
        "477c67f57e832d2cfcf7f64b93909caa90c74fa2",
        (
            "check_for_upgrade()",
            "install_brainstem()",
            "launch_brainstem()",
            "login/device/code",
        ),
    ),
    "docs/install.cmd": (
        "4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6",
        "03506ae1ab55d666f8fc47e9248afe4a54e15c72",
        ("powershell -ExecutionPolicy Bypass", "raw.githubusercontent.com", "pause"),
    ),
    "docs/install.command": (
        "4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6",
        "6d444ac6e2303bc5cb694884ad9e4931be959048",
        ("curl -fsSL", "rapp-installer/install.sh", "bash"),
    ),
    "community_rapp/install.sh": (
        "4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6",
        "d35d686d3a7f60de4c99cc41bd16a7e0225d7a23",
        ("find_python()", "git clone", "business.html", "local.settings.json"),
    ),
    "community_rapp/install.ps1": (
        "4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6",
        "9a7bd84a25498bd68ec020bb7a552f7a68f732dd",
        ("function Find-Python", "git clone", "business.html", "local.settings.json"),
    ),
    "installer/install.sh": (
        "5f67e1e7a279e45e384a1673d09d1739936f72d9",
        "03ae42778a3fc9a49b9e76c719bcc1ada39c4cbc",
        (
            "check_for_upgrade()",
            "install_service()",
            "launch_brainstem()",
            "login/device/code",
        ),
    ),
    "installer/install.ps1": (
        "45d8e9fc6df2989d6c1c591613e30710f768ef1a",
        "aa2a471b16b4662a37a7dde67741f9feb12ac82f",
        (
            "function Check-ForUpgrade",
            "function Install-Service",
            "function Launch-Brainstem",
            "Start-Process",
        ),
    ),
    "installer/install.cmd": (
        "b4f3e31c1c30cfaf798728cec2de45dbfcfb3e25",
        "ac825ddd8894a221c69b70649c73ede9f238da1b",
        ("powershell -ExecutionPolicy Bypass", "raw.githubusercontent.com", "pause"),
    ),
    "installer/install-swarm.sh": (
        "925dee4a211965f2582e71a6d2ad75f60a54ea7d",
        "2c746543ee4a949adfa991d9bdc0fbd85a7f56ba",
        ("find_python()", "ensure_repo()", "install_cli()", "exec "),
    ),
    "installer/start-local.sh": (
        "925dee4a211965f2582e71a6d2ad75f60a54ea7d",
        "6455bd18e1e42e379b983dd325e2412d373b4ffa",
        ("cleanup()", "python3 -m http.server", "xdg-open", "kill -9"),
    ),
    "installer/integration_plant.sh": (
        "0e068b3cd7bb56add2b3a3e2eea6b9142905a574",
        "a191aae89a02bc53f516a6aaba549059fe18fc95",
        ("plant.sh", "gh api", "curl -fsS", "Pages"),
    ),
    "installer/hatchling": (
        "9bf771df8b308e11f681fc62a9d04a81450ceb03",
        "6d36fca3ed5939e8a08613288387bd5521aecc70",
        ("def cmd_stamp", "def cmd_hatch", "def cmd_reset", "tarfile.open"),
    ),
    "installer/plant.sh": (
        "f9102acd7c152ab99dce4fe75fcb0968cec3890b",
        "98ece1fa71980c0c5b353a85fb839b54f83c1c07",
        ("write_index_html()", "gh repo create", "git push", "brainstem-egg/"),
    ),
    "deploy.sh": (
        "4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6",
        "7cd17dc28c7650ff5919f3873c11585c80447df4",
        (
            "read_input()",
            "az group create",
            "az deployment group create",
            "rapp-deployment-outputs.json",
        ),
    ),
    "deploy.ps1": (
        "4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6",
        "4576b46aa246ea5ec50deed70af824b5928fd7f6",
        (
            "function Select-OpenAIRegion",
            "az group create",
            "az deployment group create",
            "rapp-deployment-outputs.json",
        ),
    ),
    "tools/sign_release.py": (
        "4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6",
        "9cad84a907496205492ee69b3cb2f3517fbeb85e",
        ("def cmd_keygen", "def cmd_sign", "def cmd_verify", "priv.sign"),
    ),
    "tools/lan_advertise.py": (
        "da4f78abdff5f2bc9ff9e1266ddbf0723cb20161",
        "d89e513c52ae849d541d3dafcb13ff7041889f5a",
        (
            "def _stage_beacon_locally",
            "def _start_http_server",
            "def _start_bonjour_advertisement",
            "dns-sd",
        ),
    ),
    "rapp_brainstem/start.sh": (
        "01c11f52f1edb7d3e337e4f223aa8d514f622ebb",
        "3fe7ce7bf7198fa4fb155e380fb1525a9eed2a4b",
        ("write_bootstrap()", "requirements.txt", "brainstem.py", "exec "),
    ),
    "rapp_brainstem/start.ps1": (
        "844f84ef54ce2481f670a9ca8830c96a60b70c72",
        "0b779c2dad2ce0d5edf4d8e626e863b1a9d6d159",
        ("python -m pip install", "utils/boot.py", "Get-Command python"),
    ),
    "rapp_brainstem/tls_proxy.py": (
        "55b91b9ecd182a3ce2057787f07c60e9aa3ca128",
        "ee3fc89f515e43042f89fdd9ffe82827022a5503",
        ("def ensure_cert", "class ProxyHandler", "ThreadingHTTPServer", "serve_forever"),
    ),
    "rapp_brainstem/utils/boot.py": (
        "7f9553ed0f079fbce70755ee4cae3e51705dcccf",
        "71d551da85bca64951ac6de1b5ae386b62402154",
        (
            "def _wrap_flask_run",
            "def _install_snapshot_routes",
            "def _install_preferences_routes",
            "runpy.run_path",
        ),
    ),
}

DESCRIPTOR_SOURCES = {
    "azuredeploy.json": (
        "4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6",
        "ccd35c4b93ab787379662bb9e97f3ec8be363758",
    ),
    "installer/azuredeploy.json": (
        "925dee4a211965f2582e71a6d2ad75f60a54ea7d",
        "f39891606d0fe96dba3456128cb7db2a893bc8b4",
    ),
}

SHELL_PLAN = (
    "install.sh",
    "install.command",
    "docs/install.sh",
    "docs/install.command",
    "community_rapp/install.sh",
    "installer/install.sh",
    "installer/install-swarm.sh",
    "installer/start-local.sh",
    "installer/integration_plant.sh",
    "installer/plant.sh",
    "deploy.sh",
)
PYTHON_PLAN = (
    "tools/sign_release.py",
    "tools/lan_advertise.py",
    "installer/hatchling",
    "rapp_brainstem/tls_proxy.py",
)
POWERSHELL_PLAN = (
    "install.ps1",
    "community_rapp/install.ps1",
    "installer/install.ps1",
    "deploy.ps1",
)
CMD_PLAN = ("install.cmd", "docs/install.cmd", "installer/install.cmd")
UNCONDITIONAL = (
    ("rapp_brainstem/start.sh", "shell"),
    ("rapp_brainstem/start.ps1", "powershell"),
    ("rapp_brainstem/utils/boot.py", "python"),
)
IMPORT_SEALED = {
    "tools/sign_release.py": (
        "_ensure_cryptography",
        "_load_pem",
        "cmd_keygen",
        "cmd_sign",
        "cmd_verify",
        "main",
    ),
    "installer/hatchling": (
        "_write_json",
        "_git",
        "_stamp_org_rappid",
        "_tag_generation",
        "_snapshot_state",
        "_restore_state",
        "cmd_stamp",
        "cmd_hatch",
        "cmd_tag_current",
        "cmd_revert",
        "cmd_reset",
        "main",
    ),
    "tools/lan_advertise.py": (
        "_stage_beacon_locally",
        "_start_http_server",
        "_start_bonjour_advertisement",
        "main",
    ),
    "rapp_brainstem/tls_proxy.py": (
        "ensure_cert",
        "ProxyHandler",
        "main",
    ),
}


def _git(*args: str, stdin: bytes | None = None) -> bytes:
    result = subprocess.run(
        ("git", "-C", os.fspath(ROOT), *args),
        input=stdin,
        capture_output=True,
        check=True,
    )
    return result.stdout


def _historical_bytes(relative: str) -> bytes:
    data = (ROOT / relative).read_bytes()
    for marker in (
        b"# RAPP_RESTORED_HISTORICAL_SOURCE_BEGIN\n",
        b"REM RAPP_RESTORED_HISTORICAL_SOURCE_BEGIN\n",
    ):
        if marker in data:
            data = data.split(marker, 1)[1]
            break
    for start_marker, end_marker in (
        (
            b"# RAPP_RESTORED_GATE_BEGIN\n",
            b"# RAPP_RESTORED_GATE_END\n",
        ),
        (
            b"\n# RAPP_RESTORED_IMPORT_OVERRIDE_BEGIN\n",
            b"# RAPP_RESTORED_IMPORT_OVERRIDE_END\n",
        ),
        (
            b"\n# RAPP_RESTORED_IMPORT_SEAL_BEGIN\n",
            b"# RAPP_RESTORED_IMPORT_SEAL_END\n",
        ),
    ):
        if start_marker not in data:
            continue
        start = data.index(start_marker)
        end = data.index(end_marker, start) + len(end_marker)
        data = data[:start] + data[end:]
    return data


@pytest.mark.parametrize("relative", tuple(SOURCES))
def test_recovered_source_matches_recorded_commit_and_blob(relative):
    commit, blob, markers = SOURCES[relative]
    expected = _git("show", f"{commit}:{relative}")
    recovered = _historical_bytes(relative)
    recorded_blob = _git("rev-parse", f"{commit}:{relative}").decode().strip()
    recovered_blob = _git("hash-object", "--stdin", stdin=recovered).decode().strip()

    assert recorded_blob == blob
    assert recovered_blob == blob
    assert recovered == expected

    current = (ROOT / relative).read_text(encoding="utf-8")
    assert commit in current
    assert blob in current
    historical_text = recovered.decode("utf-8")
    for marker in markers:
        assert marker in historical_text, f"{relative} lost substantive marker {marker!r}"


@pytest.mark.parametrize("relative", tuple(DESCRIPTOR_SOURCES))
def test_inert_deployment_descriptor_matches_recorded_history(relative):
    commit, blob = DESCRIPTOR_SOURCES[relative]
    historical = _git("show", f"{commit}:{relative}")
    assert _git("rev-parse", f"{commit}:{relative}").decode().strip() == blob
    assert _git("hash-object", "--stdin", stdin=historical).decode().strip() == blob

    source_descriptor = json.loads(historical)
    descriptor = json.loads((ROOT / relative).read_bytes())
    historical_description = (
        "Rapid Agent "
        "Prototyping"
        " Platform assistant"
    )
    assert source_descriptor["parameters"]["characteristicDescription"][
        "defaultValue"
    ] == historical_description
    source_descriptor["parameters"]["characteristicDescription"][
        "defaultValue"
    ] = "Rapid Agent Prototype Platform assistant"
    assert descriptor == source_descriptor
    assert descriptor["$schema"].endswith("/deploymentTemplate.json#")
    assert descriptor["contentVersion"] == "1.0.0.0"
    assert len(descriptor["parameters"]) == 14
    assert len(descriptor["variables"]) == 14
    assert len(descriptor["resources"]) == 16
    assert len(descriptor["outputs"]) == 15


def test_kernel_pin_and_frozen_grail_bytes_remain_exact():
    pin_path = ROOT / "KERNEL_PIN.json"
    assert hashlib.sha256(pin_path.read_bytes()).hexdigest() == PIN_SHA256
    pin = json.loads(pin_path.read_text(encoding="utf-8"))
    assert pin["kernel"]["grail"] == "kody-w/rapp-installer"
    assert pin["kernel"]["tag"] == "brainstem-v0.6.9"
    assert pin["kernel"]["frozen"] == FROZEN
    for relative, expected in FROZEN.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def _snapshot(path: Path) -> dict[str, tuple[str, int, str]]:
    snapshot = {}
    for item in sorted(path.rglob("*")):
        relative = item.relative_to(path).as_posix()
        if item.is_dir():
            snapshot[relative] = ("dir", stat.S_IMODE(item.stat().st_mode), "")
        elif item.is_file():
            snapshot[relative] = (
                "file",
                stat.S_IMODE(item.stat().st_mode),
                hashlib.sha256(item.read_bytes()).hexdigest(),
            )
    return snapshot


def _sentinel_environment(tmp_path: Path):
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    sentinel = tmp_path / "external-effect-sentinel"
    sentinel_source = (
        "#!/bin/sh\n"
        'printf "%s\\n" "${0##*/}" >> "$RAPP_TEST_SENTINEL"\n'
        "exit 97\n"
    )
    for name in (
        "apt",
        "apt-get",
        "az",
        "brew",
        "chmod",
        "clear",
        "cp",
        "curl",
        "date",
        "dnf",
        "dns-sd",
        "func",
        "gh",
        "git",
        "kill",
        "launchctl",
        "lsof",
        "mkdir",
        "mv",
        "npm",
        "npx",
        "open",
        "openssl",
        "pip",
        "pip3",
        "powershell",
        "pwsh",
        "python",
        "python3",
        "python3.11",
        "python3.12",
        "python3.13",
        "rm",
        "sed",
        "shasum",
        "sha256sum",
        "sleep",
        "systemctl",
        "tar",
        "unzip",
        "winget",
        "xdg-open",
        "yum",
    ):
        tool = fake_bin / name
        tool.write_text(sentinel_source, encoding="utf-8")
        tool.chmod(0o755)

    python_guard = tmp_path / "python-guard"
    python_guard.mkdir()
    (python_guard / "sitecustomize.py").write_text(
        """
import os
import sys

_blocked = {
    "os.chmod",
    "os.chown",
    "os.link",
    "os.mkdir",
    "os.remove",
    "os.rename",
    "os.rmdir",
    "os.symlink",
    "os.system",
    "os.truncate",
    "socket.__new__",
    "socket.connect",
    "subprocess.Popen",
}


def _deny_effect(event, args):
    if event in _blocked or event.startswith("os.posix_spawn"):
        raise RuntimeError("blocked side effect: " + event)
    if event == "open" and len(args) > 1:
        mode = args[1]
        if isinstance(mode, str) and any(flag in mode for flag in "wax+"):
            raise RuntimeError("blocked write open")
        if isinstance(mode, int) and mode & (
            os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
        ):
            raise RuntimeError("blocked write open")


sys.addaudithook(_deny_effect)
""".lstrip(),
        encoding="utf-8",
    )

    effects = tmp_path / "effects"
    home = effects / "home"
    temp = effects / "tmp"
    for directory in (home, temp):
        directory.mkdir(parents=True)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    dependency = evidence / "reviewed-dependency.json"
    approval = evidence / "owner-approval.json"
    section13 = evidence / "section13.json"
    for path in (dependency, approval, section13):
        path.write_text("{}\n", encoding="utf-8")

    environment = {
        "PATH": os.pathsep.join((os.fspath(fake_bin), "/usr/bin", "/bin")),
        "HOME": os.fspath(home),
        "USERPROFILE": os.fspath(home),
        "TMPDIR": os.fspath(temp),
        "TEMP": os.fspath(temp),
        "TMP": os.fspath(temp),
        "PYTHONPATH": os.fspath(python_guard),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "POWERSHELL_TELEMETRY_OPTOUT": "1",
        "POWERSHELL_UPDATECHECK": "Off",
        "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
        "RAPP_TEST_SENTINEL": os.fspath(sentinel),
        "BRAINSTEM_HOME": os.fspath(effects / "brainstem"),
        "SWARM_HOME": os.fspath(effects / "swarm"),
        "PLANT_DRY_RUN_DIR": os.fspath(effects / "plant"),
        "RAPP_INSTALL_MODE": "",
        "RAPP_INSTALL_ASSIST": "",
        "LC_ALL": "C",
        "LANG": "C",
    }
    return environment, effects, sentinel, dependency, approval, section13


def _command(relative: str, kind: str):
    path = os.fspath(ROOT / relative)
    if kind == "shell":
        return ["/bin/bash", path]
    if kind == "python":
        return [sys.executable, path]
    raise AssertionError(kind)


@pytest.mark.parametrize(
    ("relative", "kind"),
    tuple((path, "shell") for path in SHELL_PLAN)
    + tuple((path, "python") for path in PYTHON_PLAN),
)
def test_default_plan_is_effect_free(relative, kind, tmp_path):
    environment, effects, sentinel, *_ = _sentinel_environment(tmp_path)
    before = _snapshot(effects)
    result = subprocess.run(
        _command(relative, kind),
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    plan = json.loads(result.stdout)
    assert plan["target"] == relative
    assert plan["mode"] == "plan"
    assert plan["source_commit"] == SOURCES[relative][0]
    assert plan["source_blob"] == SOURCES[relative][1]
    assert plan["kernel"] == "kody-w/rapp-installer@brainstem-v0.6.9"
    assert plan["kernel_pin_sha256"] == PIN_SHA256
    assert plan["apply_permitted"] is False
    assert not sentinel.exists()
    assert _snapshot(effects) == before


@pytest.mark.parametrize(
    ("relative", "kind"),
    tuple((path, "shell") for path in SHELL_PLAN)
    + tuple((path, "python") for path in PYTHON_PLAN),
)
def test_fully_flagged_apply_still_refuses_without_effects(relative, kind, tmp_path):
    (
        environment,
        effects,
        sentinel,
        dependency,
        approval,
        section13,
    ) = _sentinel_environment(tmp_path)
    before = _snapshot(effects)
    command = _command(relative, kind) + [
        "--apply",
        "--allow-active-effects",
        "--target",
        relative,
        "--kernel-pin",
        os.fspath(ROOT / "KERNEL_PIN.json"),
        "--reviewed-dependency-injection",
        os.fspath(dependency),
        "--owner-approval",
        os.fspath(approval),
        "--section13-evidence",
        os.fspath(section13),
    ]
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )

    assert result.returncode == 78
    assert "410 Gone" in result.stderr
    assert "authenticated fresh section-13 evidence is unavailable" in result.stderr
    assert not sentinel.exists()
    assert _snapshot(effects) == before


@pytest.mark.parametrize(
    ("relative", "kind"),
    tuple((path, "shell") for path in SHELL_PLAN)
    + tuple((path, "python") for path in PYTHON_PLAN),
)
def test_apply_rejects_non_exact_pin_and_directory_evidence(
    relative, kind, tmp_path
):
    (
        environment,
        effects,
        sentinel,
        dependency,
        approval,
        section13,
    ) = _sentinel_environment(tmp_path)
    bad_pin = tmp_path / "KERNEL_PIN.json"
    bad_pin.write_bytes((ROOT / "KERNEL_PIN.json").read_bytes() + b" \n")
    evidence_directory = tmp_path / "not-a-file"
    evidence_directory.mkdir()
    before = _snapshot(effects)
    common = [
        "--apply",
        "--allow-active-effects",
        "--target",
        relative,
        "--reviewed-dependency-injection",
        os.fspath(dependency),
        "--owner-approval",
        os.fspath(approval),
        "--section13-evidence",
        os.fspath(section13),
    ]

    wrong_pin = subprocess.run(
        _command(relative, kind)
        + common[:4]
        + ["--kernel-pin", os.fspath(bad_pin)]
        + common[4:],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert wrong_pin.returncode == 78
    assert "exact KERNEL_PIN.json" in wrong_pin.stderr
    assert "evidence is unavailable" not in wrong_pin.stderr

    directory_evidence = subprocess.run(
        _command(relative, kind)
        + [
            "--apply",
            "--allow-active-effects",
            "--target",
            relative,
            "--kernel-pin",
            os.fspath(ROOT / "KERNEL_PIN.json"),
            "--reviewed-dependency-injection",
            os.fspath(evidence_directory),
            "--owner-approval",
            os.fspath(evidence_directory),
            "--section13-evidence",
            os.fspath(evidence_directory),
        ],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert directory_evidence.returncode == 78
    assert "reviewed dependency injection" in directory_evidence.stderr
    assert "evidence is unavailable" not in directory_evidence.stderr
    assert not sentinel.exists()
    assert _snapshot(effects) == before


@pytest.mark.parametrize(
    ("relative", "kind"),
    (("rapp_brainstem/start.sh", "shell"), ("rapp_brainstem/utils/boot.py", "python")),
)
def test_unconditional_launcher_refusals_retain_history_without_effects(
    relative, kind, tmp_path
):
    environment, effects, sentinel, *_ = _sentinel_environment(tmp_path)
    before = _snapshot(effects)
    for arguments in ((), ("--apply", "--allow-active-effects")):
        result = subprocess.run(
            _command(relative, kind) + list(arguments),
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
        assert result.returncode == 78
        combined = result.stdout + result.stderr
        assert '"mode":"inspect"' in combined
        assert "410 Gone" in combined
    assert not sentinel.exists()
    assert _snapshot(effects) == before


def test_boot_module_is_importable_but_public_main_always_refuses(capsys):
    path = ROOT / "rapp_brainstem/utils/boot.py"
    spec = importlib.util.spec_from_file_location("restored_boot_inspection", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert callable(module._rapp_restored_historical_main)
    with pytest.raises(SystemExit) as refusal:
        module.main()
    assert refusal.value.code == 78
    assert "410 Gone" in capsys.readouterr().err


@pytest.mark.parametrize(("relative", "entrypoints"), tuple(IMPORT_SEALED.items()))
def test_imported_historical_entrypoints_are_sealed_before_effects(
    relative,
    entrypoints,
    tmp_path,
):
    environment, effects, sentinel, *_ = _sentinel_environment(tmp_path)
    before = _snapshot(effects)
    script = """
import importlib.machinery
import importlib.util
import json
import sys

path = sys.argv[1]
entrypoints = json.loads(sys.argv[2])
name = "sealed_" + path.replace("/", "_").replace(".", "_")
loader = importlib.machinery.SourceFileLoader(name, path)
spec = importlib.util.spec_from_loader(name, loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)
for entrypoint in entrypoints:
    target = getattr(module, entrypoint)
    try:
        target()
    except RuntimeError as error:
        if "target-owned CLI plan gate" not in str(error):
            raise
    else:
        raise AssertionError(f"imported entrypoint remained callable: {entrypoint}")
print(json.dumps(entrypoints))
"""
    result = subprocess.run(
        (
            sys.executable,
            "-c",
            script,
            os.fspath(ROOT / relative),
            json.dumps(entrypoints),
        ),
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == list(entrypoints)
    assert not sentinel.exists()
    assert _snapshot(effects) == before


def test_non_native_launchers_gate_before_historical_commands():
    required = (
        "--allow-active-effects",
        "--target",
        "--kernel-pin",
        "--reviewed-dependency-injection",
        "--owner-approval",
        "--section13-evidence",
        "kody-w/rapp-installer@brainstem-v0.6.9",
        "authenticated fresh section-13 evidence is unavailable",
    )
    for relative in POWERSHELL_PLAN:
        source = (ROOT / relative).read_text(encoding="utf-8")
        gate = source.split("# RAPP_RESTORED_GATE_END", 1)[0]
        assert "return 0" in gate
        assert "exit $RappGateCode" in gate
        assert "$global:LASTEXITCODE = $RappGateCode" in gate
        for marker in required:
            assert marker in gate
    deploy_gate = (ROOT / "deploy.ps1").read_text(encoding="utf-8").split(
        "# RAPP_RESTORED_GATE_END", 1
    )[0]
    for bound_parameter in ("$ResourceGroup", "$Location", "$OpenAILocation"):
        assert bound_parameter in deploy_gate
    for relative in CMD_PLAN:
        source = (ROOT / relative).read_text(encoding="utf-8")
        gate = source.split("REM RAPP_RESTORED_HISTORICAL_SOURCE_BEGIN", 1)[0]
        assert "exit /b 0" in gate
        assert "exit /b 78" in gate
        assert "powershell" not in gate.lower()
        assert "http://" not in gate.lower()
        assert "https://" not in gate.lower()
        assert "_rapp_expected_pin" in gate
        assert "\\NUL" in gate
        for marker in required:
            assert marker in gate

    start_ps1 = (ROOT / "rapp_brainstem/start.ps1").read_text(encoding="utf-8")
    gate = start_ps1.split("# RAPP_RESTORED_GATE_END", 1)[0]
    assert '"mode":"inspect"' in gate
    assert "410 Gone" in gate
    assert "exit 78" in gate
    assert "$global:LASTEXITCODE = 78" in gate


def _warm_powershell(executable: str, environment: dict[str, str]) -> None:
    for _ in range(2):
        result = subprocess.run(
            [
                executable,
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "exit 0",
            ],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    ("relative", "tombstone"),
    tuple((path, False) for path in POWERSHELL_PLAN)
    + (("rapp_brainstem/start.ps1", True),),
)
def test_powershell_defaults_and_refusals_are_effect_free_when_available(
    relative, tombstone, tmp_path
):
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if executable is None:
        return
    environment, effects, sentinel, dependency, approval, section13 = (
        _sentinel_environment(tmp_path)
    )
    _warm_powershell(executable, environment)
    before = _snapshot(effects)
    base = [executable, "-NoLogo", "-NoProfile", "-NonInteractive", "-File", os.fspath(ROOT / relative)]
    default = subprocess.run(
        base,
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )
    assert default.returncode == (78 if tombstone else 0)
    if tombstone:
        assert "410 Gone" in default.stdout + default.stderr
    else:
        assert json.loads(default.stdout)["mode"] == "plan"
        rejected = subprocess.run(
            base
            + [
                "--apply",
                "--allow-active-effects",
                "--target",
                relative,
                "--kernel-pin",
                os.fspath(ROOT / "KERNEL_PIN.json"),
                "--reviewed-dependency-injection",
                os.fspath(dependency),
                "--owner-approval",
                os.fspath(approval),
                "--section13-evidence",
                os.fspath(section13),
            ],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
        )
        assert rejected.returncode == 78
        assert "authenticated fresh section-13 evidence is unavailable" in rejected.stderr
    assert not sentinel.exists()
    assert _snapshot(effects) == before


@pytest.mark.parametrize(
    "relative",
    POWERSHELL_PLAN + ("rapp_brainstem/start.ps1",),
)
def test_powershell_iex_returns_without_closing_host_when_available(
    relative, tmp_path
):
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if executable is None:
        return
    environment, effects, sentinel, *_ = _sentinel_environment(tmp_path)
    _warm_powershell(executable, environment)
    before = _snapshot(effects)
    path = os.fspath(ROOT / relative).replace("'", "''")
    command = (
        "& { "
        f"$source = [IO.File]::ReadAllText('{path}'); "
        "Invoke-Expression $source "
        "}; "
        "[Console]::Out.WriteLine('__RAPP_HOST_SURVIVED__')"
    )
    result = subprocess.run(
        [executable, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", command],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0
    assert "__RAPP_HOST_SURVIVED__" in result.stdout
    assert not sentinel.exists()
    assert _snapshot(effects) == before
