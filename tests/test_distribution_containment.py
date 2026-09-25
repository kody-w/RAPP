from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from html import unescape as html_unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
LIVE_INVENTORY = ROOT / "tests/rapp1-live-surface-inventory.json"

RESTORED_SHELL_ENTRYPOINTS = (
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
RESTORED_POWERSHELL_ENTRYPOINTS = (
    "install.ps1",
    "community_rapp/install.ps1",
    "deploy.ps1",
    "installer/install.ps1",
    "rapp_brainstem/start.ps1",
)
RESTORED_CMD_ENTRYPOINTS = (
    "install.cmd",
    "docs/install.cmd",
    "installer/install.cmd",
)
ADAPTED_BROWSER_ROUTES = (
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


def test_restored_shell_entrypoints_preserve_source_and_default_safe():
    for relative in RESTORED_SHELL_ENTRYPOINTS:
        path = ROOT / relative
        source = path.read_text(encoding="utf-8")
        assert path.stat().st_mode & stat.S_IXUSR
        assert "RAPP_RESTORED_SOURCE_COMMIT=" in source
        assert "RAPP_RESTORED_SOURCE_BLOB=" in source
        assert "RAPP_RESTORED_GATE_BEGIN" in source
        assert "RAPP_RESTORED_GATE_END" in source
        assert "RAPP_RESTORED_HISTORICAL_SOURCE_BEGIN" in source
        assert "kody-w/rapp-installer@brainstem-v0.6.9" in source

        result = subprocess.run(
            ("bash", relative),
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if relative == "rapp_brainstem/start.sh":
            assert result.returncode == 78
            assert '"mode":"inspect"' in result.stderr
            assert "410 Gone" in result.stderr
            continue
        assert result.returncode == 0, (relative, result.stderr)
        plan = json.loads(result.stdout)
        assert plan["target"] == relative
        assert plan["mode"] == "plan"
        assert plan["apply_permitted"] is False
        assert plan["kernel"] == "kody-w/rapp-installer@brainstem-v0.6.9"


def test_installer_apply_refuses_before_external_tools():
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

        sentinel = scratch / "tool-was-invoked"
        evidence = scratch / "evidence"
        evidence.mkdir()
        dependency = evidence / "dependency.json"
        approval = evidence / "approval.json"
        section13 = evidence / "section13.json"
        for path in (dependency, approval, section13):
            path.write_text("{}\n", encoding="utf-8")
        home = scratch / "home"
        home.mkdir()
        before = tuple(home.iterdir())
        environment = os.environ.copy()
        environment.update(
            {
                "BRAINSTEM_HOME": os.fspath(home),
                "HOME": os.fspath(home),
                "PATH": os.pathsep.join(
                    (os.fspath(fake_bin), environment.get("PATH", ""))
                ),
                "RAPP_TEST_SENTINEL": os.fspath(sentinel),
            }
        )
        result = subprocess.run(
            (
                "bash",
                "installer/install.sh",
                "--apply",
                "--allow-active-effects",
                "--target",
                "installer/install.sh",
                "--kernel-pin",
                "KERNEL_PIN.json",
                "--reviewed-dependency-injection",
                os.fspath(dependency),
                "--owner-approval",
                os.fspath(approval),
                "--section13-evidence",
                os.fspath(section13),
            ),
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 78
        assert "authenticated fresh section-13 evidence is unavailable" in result.stderr
        assert not sentinel.exists()
        assert tuple(home.iterdir()) == before
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_windows_installers_preserve_source_behind_static_gates():
    for relative in RESTORED_POWERSHELL_ENTRYPOINTS:
        data = (ROOT / relative).read_bytes()
        source = data.decode("utf-8")
        gate, historical = source.split("# RAPP_RESTORED_GATE_END", 1)
        assert "RAPP_RESTORED_GATE_BEGIN" in gate
        assert "apply_permitted" in gate
        if relative == "rapp_brainstem/start.ps1":
            assert '"mode":"inspect"' in gate
            assert "unconditional public " in gate
            assert '"launcher refusal;' in gate
        else:
            assert "authenticated fresh section-13 evidence is unavailable" in gate
        assert "410 Gone" in source
        assert b"\\n" not in data
        assert b"\r" not in data
        assert len(historical) > 1_000
    for relative in RESTORED_CMD_ENTRYPOINTS:
        source = (ROOT / relative).read_text(encoding="utf-8")
        gate, historical = source.split(
            "REM RAPP_RESTORED_HISTORICAL_SOURCE_BEGIN",
            1,
        )
        assert "exit /b 0" in gate
        assert "exit /b 78" in gate
        assert "powershell" not in gate.lower()
        assert "http" not in gate.lower()
        assert len(historical) > 100


def test_deployment_descriptors_preserve_full_inert_templates():
    for relative in ("azuredeploy.json", "installer/azuredeploy.json"):
        descriptor = json.loads((ROOT / relative).read_text(encoding="utf-8"))
        assert descriptor["$schema"].endswith("/deploymentTemplate.json#")
        assert descriptor["contentVersion"] == "1.0.0.0"
        assert len(descriptor["parameters"]) == 14
        assert len(descriptor["variables"]) == 14
        assert len(descriptor["resources"]) == 16
        assert len(descriptor["outputs"]) == 15
    for relative in ("deploy.sh", "deploy.ps1"):
        source = (ROOT / relative).read_text(encoding="utf-8")
        gate, historical = source.split("RAPP_RESTORED_GATE_END", 1)
        assert "authenticated fresh section-13 evidence is unavailable" in gate
        assert "azuredeploy.json" in historical


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
    assert len(records) == 6
    for record in records:
        path = ROOT / record["path"]
        assert path.stat().st_size == record["bytes"]
        assert _sha256(path) == record["sha256"]


PROPOSAL_0003 = "docs/proposals/0003-reframe-cubby-eggs-and-retire-commons-invite.md"
REFRAMED_CUBBY_EGGS = (
    "cave/rapplications/rapp-installer/cubby-rapp-installer.egg",
    "cave/cubbies/kody-w/eggs/cubby-rapp-installer.egg",
)


def _zip_flag_high_bytes(blob: bytes) -> tuple[int, set[int]]:
    """Return the entry count and each local/central flag high-byte offset."""
    eocd = len(blob) - 22
    assert blob[eocd : eocd + 4] == b"PK\x05\x06"
    entries = int.from_bytes(blob[eocd + 10 : eocd + 12], "little")
    cursor = int.from_bytes(blob[eocd + 16 : eocd + 20], "little")
    offsets: set[int] = set()
    for _ in range(entries):
        assert blob[cursor : cursor + 4] == b"PK\x01\x02"
        local = int.from_bytes(blob[cursor + 42 : cursor + 46], "little")
        assert blob[local : local + 4] == b"PK\x03\x04"
        offsets.update((local + 7, cursor + 9))
        name_length = int.from_bytes(blob[cursor + 28 : cursor + 30], "little")
        extra_length = int.from_bytes(blob[cursor + 30 : cursor + 32], "little")
        comment_length = int.from_bytes(blob[cursor + 32 : cursor + 34], "little")
        cursor += 46 + name_length + extra_length + comment_length
    return entries, offsets


def test_proposal_0003_reframing_exception_is_exact_and_identity_preserving():
    import io
    import zipfile

    from rapp1_core.hashing import EGG_MANIFEST_SPACE, hash_value

    manifest = json.loads(
        (ROOT / "installer/RETIRED_ARTIFACTS.json").read_text(encoding="utf-8")
    )
    assert manifest["repacking_allowed"] is False
    (exception,) = manifest["repacking_exceptions"]
    assert exception["proposal"] == PROPOSAL_0003
    assert (ROOT / PROPOSAL_0003).is_file()
    assert exception["scope"] == "zip-framing-only"
    assert exception["other_artifacts_covered"] is False
    assert exception["packer"] == {
        "repository": "kody-w/rapp-1",
        "commit": "591e014ad39e223b00ab343ae26e5d9a867ebeee",
        "path": "rapp.py",
        "function": "pack_egg",
    }
    assert tuple(exception["paths"]) == REFRAMED_CUBBY_EGGS
    assert exception["id"] == "proposal-0003-part-a"
    snapshot = manifest["prepared_snapshot"]
    assert snapshot["modification_allowed"] is False
    assert snapshot["modification_exceptions"] == [exception["id"]]
    assert REFRAMED_CUBBY_EGGS[0].startswith(snapshot["path"] + "/")
    ledger = (ROOT / "RAPP1_OWNER_ACTIONS.md").read_text(encoding="utf-8")
    residual = ledger.split("\n## Issue-ready immutable Cave residual", 1)[1]
    residual = residual.split("\n## ", 1)[0]
    for marker in (
        "waive",
        PROPOSAL_0003,
        exception["id"],
        exception["before_sha256"],
        exception["after_sha256"],
    ):
        assert marker in residual, marker
    records = {record["path"]: record for record in manifest["immutable_eggs"]}
    for relative in REFRAMED_CUBBY_EGGS:
        assert records[relative]["sha256"] == exception["after_sha256"]
        assert records[relative]["bytes"] == exception["bytes"]
        current = (ROOT / relative).read_bytes()
        before = subprocess.check_output(
            ("git", "show", f"{exception['before_bytes_commit']}:{relative}"),
            cwd=ROOT,
        )
        assert hashlib.sha256(before).hexdigest() == exception["before_sha256"]
        assert hashlib.sha256(current).hexdigest() == exception["after_sha256"]
        assert len(before) == len(current) == exception["bytes"]

        entries, flag_high_bytes = _zip_flag_high_bytes(current)
        assert entries == exception["zip_entries"] == exception["members"] + 1
        assert _zip_flag_high_bytes(before) == (entries, flag_high_bytes)
        changed = {
            offset
            for offset, (old, new) in enumerate(zip(before, current))
            if old != new
        }
        assert changed == flag_high_bytes
        assert len(changed) == exception["changed_bytes_per_copy"] == 2 * entries
        for offset in changed:
            assert (before[offset - 1], before[offset]) == (0x00, 0x00)
            assert (current[offset - 1], current[offset]) == (0x00, 0x08)

        with zipfile.ZipFile(io.BytesIO(before)) as old_zip, zipfile.ZipFile(
            io.BytesIO(current)
        ) as new_zip:
            names = new_zip.namelist()
            assert names == old_zip.namelist()
            assert names[0] == "manifest.json"
            assert len(names) - 1 == exception["members"]
            for name in names:
                assert new_zip.read(name) == old_zip.read(name), name
            egg_manifest = json.loads(new_zip.read("manifest.json"))
        assert egg_manifest["schema"] == "rapp/1-egg"
        assert egg_manifest["sig"] is None
        address_value = {
            key: value for key, value in egg_manifest.items() if key != "sig"
        }
        assert (
            hash_value(EGG_MANIFEST_SPACE, address_value) == exception["egg_address"]
        )


def test_owned_distribution_pages_publish_neither_tier2_nor_power_archive():
    for relative in ("index.html", "installer/index.html"):
        source = (ROOT / relative).read_text(encoding="utf-8")
        lowered = source.lower()
        assert "install-swarm.sh" not in source
        assert "azuredeploy.json" not in source
        assert "install.ps1" not in source
        assert not re.search(
            r"<a\b[^>]*\bhref=[\"'][^\"']*MSFTAIBASMultiAgentCopilot",
            source,
            flags=re.IGNORECASE,
        )
        assert "RAPP/installer/install.sh" not in source
        assert "rapp-current-status" in lowered
        assert "no active installer" in lowered
        assert "kernel_pin.json" in lowered
        assert 'class="current-note"' not in lowered


def test_plant_browser_callers_preserve_source_with_safe_local_controls():
    for relative in ADAPTED_BROWSER_ROUTES:
        source = (ROOT / relative).read_text(encoding="utf-8").lower()
        assert "retired semantic tombstone" not in source
        assert "rapp-history-source" in source
        assert "rapp1_status.md" in source
        assert "kernel_pin.json" in source
        assert "content-security-policy" in source
        assert "connect-src 'none'" in source
        assert "form-action 'none'" in source
    metropolis = (ROOT / "pages/metropolis/index.html").read_text(encoding="utf-8")
    assert "plant-from-discord" in metropolis


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


# Proposal 0003 Part B keeps its own names, apart from Part A's, so that either
# part can be reverted without the other.
COMMONS_RETIREMENT_PROPOSAL = (
    "docs/proposals/0003-reframe-cubby-eggs-and-retire-commons-invite.md"
)
RETIRED_COMMONS_INVITE = "pages/tutorials/commons.egg"
COMMONS_RETIREMENT_RECORDS = frozenset(
    {
        COMMONS_RETIREMENT_PROPOSAL,
        "installer/RETIRED_ARTIFACTS.json",
        "RAPP1_OWNER_ACTIONS.json",
        "RAPP1_OWNER_ACTIONS.md",
    }
)
# These two tests name the retired path on purpose, to prove it is gone.
COMMONS_RETIREMENT_TESTS = frozenset(
    {
        "tests/test_distribution_containment.py",
        "tests/test_rapp1_owner_actions.py",
    }
)
COMMONS_PAGES_GUARD = f"  - {RETIRED_COMMONS_INVITE}"
RETIRED_COMMONS_NAME = re.compile(
    r"(?<![\w.-])commons\.egg(?![\w-])", flags=re.IGNORECASE
)
# Across joined lines only the exact (case-sensitive) Pages path counts, so prose
# such as "the Commons." at a line end before "Eggs are..." is not a reference.
RETIRED_COMMONS_PATH = re.compile(r"(?<![\w.-])commons\.egg(?![\w-])")
HTML_SUFFIXES = frozenset({".htm", ".html", ".xhtml"})
HTML_URL_ATTRIBUTES = frozenset(
    {
        "action",
        "background",
        "cite",
        "data",
        "formaction",
        "href",
        "imagesrcset",
        "longdesc",
        "manifest",
        "ping",
        "poster",
        "src",
        "srcdoc",
        "srcset",
        "style",
        "xlink:href",
    }
)


def _names_retired_commons(text: str, name: re.Pattern = RETIRED_COMMONS_NAME) -> bool:
    """As written, and as a browser or server may resolve it: HTML entities and
    percent-encoding decoded (twice, for double encoding), then tabs and line
    breaks removed, as URL parsing removes them."""
    decoded = text
    for _ in range(2):
        decoded = unquote(html_unescape(decoded))
    return any(
        name.search(candidate)
        for candidate in (text, decoded, re.sub(r"[\t\r\n]", "", decoded))
    )


class _LiveHtmlValues(HTMLParser):
    """What a browser may follow or run: URL attributes (quoted or not),
    srcdoc, <param> values, event handlers, every <meta> content (a refresh
    redirect is one), and inline scripts and styles. Text and data-*
    attributes stay inert."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.values: list[str] = []
        self._raw_text_depth = 0

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if value and (
                name in HTML_URL_ATTRIBUTES
                or name.startswith("on")
                or (tag == "meta" and name == "content")
                or (tag == "param" and name == "value")
            ):
                self.values.append(value)
        if tag in {"script", "style"}:
            self._raw_text_depth += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self._raw_text_depth:
            self._raw_text_depth -= 1

    def handle_data(self, data):
        if self._raw_text_depth:
            self.values.append(data)


def test_proposal_0003_retired_commons_invite_survives_only_in_history():
    from rapp1_core.hashing import EGG_MANIFEST_SPACE, hash_value

    manifest = json.loads(
        (ROOT / "installer/RETIRED_ARTIFACTS.json").read_text(encoding="utf-8")
    )
    assert RETIRED_COMMONS_INVITE not in {
        record["path"] for record in manifest["immutable_eggs"]
    }
    (removed,) = manifest["removed_eggs"]
    assert removed["path"] == RETIRED_COMMONS_INVITE
    assert removed["state"] == "retired-removed-from-tree"
    assert removed["preserved_by"] == ["path", "sha256", "git-history"]
    assert removed["proposal"] == COMMONS_RETIREMENT_PROPOSAL
    assert (ROOT / COMMONS_RETIREMENT_PROPOSAL).is_file()
    assert not (ROOT / RETIRED_COMMONS_INVITE).exists()
    assert (
        subprocess.check_output(
            ("git", "ls-files", "--", RETIRED_COMMONS_INVITE), cwd=ROOT, text=True
        )
        == ""
    )

    retired = subprocess.check_output(
        ("git", "show", f"{removed['bytes_commit']}:{RETIRED_COMMONS_INVITE}"),
        cwd=ROOT,
    )
    assert len(retired) == removed["bytes"]
    assert hashlib.sha256(retired).hexdigest() == removed["sha256"]
    invite = json.loads(retired)
    assert invite["variant"] == "invite"
    assert (
        hash_value(
            EGG_MANIFEST_SPACE,
            {key: value for key, value in invite.items() if key != "sig"},
        )
        == removed["egg_address"]
    )

    ledger = json.loads((ROOT / removed["owner_ledger"]).read_text(encoding="utf-8"))
    evidence = ledger["known_evidence"]["commons_invite"]
    assert evidence["retired_target_path"] == RETIRED_COMMONS_INVITE
    assert evidence["retired_target_sha256"] == removed["sha256"]
    assert evidence["retired_target_size"] == removed["bytes"]
    assert evidence["retired_egg_address"] == removed["egg_address"]
    assert evidence["retired_target_bytes_commit"] == removed["bytes_commit"]
    assert RETIRED_COMMONS_INVITE not in ledger["current_evidence"]["current_path_hashes"]
    (action,) = [
        action
        for action in ledger["actions"]
        if action["id"] == removed["open_owner_action"]
    ]
    assert action["status"] == "owner-action-required"
    assert all(value is None for value in action["owner_inputs"].values())


def _pages_exclude_guard_lines(config: str) -> set[int]:
    section = None
    guards = set()
    for number, line in enumerate(config.splitlines(), 1):
        key = re.match(r"^([A-Za-z_][\w-]*):", line)
        if key:
            section = key.group(1)
        elif section == "exclude" and line == COMMONS_PAGES_GUARD:
            guards.add(number)
    return guards


def test_proposal_0003_retired_commons_invite_has_no_live_reference():
    tracked = [
        relative
        for relative in subprocess.check_output(("git", "ls-files", "-z"), cwd=ROOT)
        .decode("utf-8")
        .split("\0")
        if relative
    ]
    assert COMMONS_RETIREMENT_RECORDS <= set(tracked)
    assert COMMONS_RETIREMENT_TESTS <= set(tracked)
    guards = _pages_exclude_guard_lines(
        (ROOT / "_config.yml").read_text(encoding="utf-8")
    )
    assert len(guards) == 1, "_config.yml must keep excluding the retired path"

    findings = []
    for relative in tracked:
        if relative in COMMONS_RETIREMENT_RECORDS | COMMONS_RETIREMENT_TESTS:
            continue
        data = (ROOT / relative).read_bytes()
        if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
            source = data.decode("utf-16", errors="replace")
        elif b"\0" in data:
            continue  # binary: archives, eggs, images
        else:
            source = data.decode("utf-8", errors="replace")
        if Path(relative).suffix.lower() in HTML_SUFFIXES:
            parser = _LiveHtmlValues()
            parser.feed(source)
            parser.close()
            for value in parser.values:
                if _names_retired_commons(value):
                    findings.append((relative, value.strip()[:160]))
        else:
            allowed = guards if relative == "_config.yml" else set()
            kept = []
            for number, line in enumerate(source.splitlines(), 1):
                if number in allowed:
                    continue
                kept.append(line)
                if _names_retired_commons(line):
                    findings.append((f"{relative}:{number}", line.strip()[:160]))
            # A name split across lines, as in a wrapped Markdown or HTML link.
            if not any(found[0].startswith(f"{relative}:") for found in findings):
                if _names_retired_commons("".join(kept), RETIRED_COMMONS_PATH):
                    findings.append((relative, "names the retired invite across lines"))
    assert findings == []
