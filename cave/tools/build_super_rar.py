#!/usr/bin/env python3
"""Build and validate read-only Cave RAR catalog observations.

This restores the substantive pre-tombstone builder: it discovers every
supported kind across every cubby, extracts agent names and purposes, computes
SHA-256 values, renders the neighborhood RAR, and checks committed indexes for
drift. It also preserves known historical entries whose bytes are no longer in
the working tree so catalog regeneration cannot erase data exhaust.

The safety adaptation has no write mode. With no arguments the tool performs
``--check``. ``--plan`` reports drift and ``--render`` emits candidate JSON to
stdout for review. No mode installs, streams, executes, publishes, or accepts
an entry. Network transport requires a caller-supplied full commit in the
catalog URL template and a matching per-file SHA-256.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


SUPER_RAR_KINDS = {
    "agent": ("agents", "*_agent.py"),
    "organ": ("organs", "*_organ.py"),
    "sense": ("senses", "*.py"),
    "rapplication": ("rapplications", "*"),
    "neighborhood": ("neighborhoods", "*"),
    "egg": ("eggs", "*.egg"),
}
CAVE = Path(__file__).resolve().parents[1]
CUBBIES = CAVE / "cubbies"
RAW_URL_TEMPLATE = (
    "https://raw.githubusercontent.com/kody-w/RAPP/{commit}/cave"
)
NEIGHBORHOOD_RAPPID = (
    "rappid:@kody-w/rapp-cave:"
    "ca72ca0a3cb90c357fb09e38b02f85f09935cacbf61e94740c57f1eb30a73e0a"
)
KERNEL_REFERENCE = {
    "record": "KERNEL_PIN.json",
    "grail": "kody-w/rapp-installer",
    "tag": "brainstem-v0.6.9",
    "policy": "read-only",
}
SOURCE_POLICY = {
    "repository": "kody-w/RAPP",
    "url_template": RAW_URL_TEMPLATE,
    "required_ref": "full 40-character commit SHA",
    "moving_refs_accepted": False,
    "sha256_required_for_files": True,
    "network_fetch_default": False,
}
PROVENANCE = {
    "builder_restored_from": "6bd45f00981959a3fdfcc64fb32608533aae5021",
    "catalog_exhaust_restored_from": (
        "d3d2623646a6111b4a7db9f1b960df233f8964c9"
    ),
    "initial_super_rar_design": (
        "cdf1aba25ba39c373ba4c738e7c6d421fff0cf86"
    ),
}
RAR_NOTE = (
    "Read-only historical catalog observation. Full entry metadata is retained "
    "separately from verification, acceptance, and distribution state. A path "
    "or SHA-256 does not authorize fetch, installation, execution, streaming, "
    "identity, trust, or RAPP/1 acceptance."
)
SUPER_RAR_NOTE = (
    "Read-only Cave inventory observation across every cubby kind. Missing "
    "historical entries remain recorded as data exhaust. No entry is accepted "
    "or distributable from this catalog."
)

RETAINED_RAR_AGENT_EXHAUST = (
    {
        "name": "@kody-w/rapp_installer",
        "version": "0.6.1-cubby",
        "path": "cubbies/kody-w/agents/rapp_installer_agent.py",
        "sha256": (
            "acdccb947f9001bcff4f3e1b8bf84bb6"
            "b831522a2c7df0d6cffa3cbdae5bfc80"
        ),
        "purpose": (
            "Drive the self-contained, repo-independent RAPP Installer "
            "rapplication (status / bootstrap one-liner / health) from any "
            "brainstem — the grail ported out of its repo. Stream via `cave "
            "load cubby=kody-w` or plain public curl."
        ),
        "required_by_tether": False,
        "schema": "rapp-agent/1.0",
        "status": "historical-observation",
        "historical_observation_at": "2026-07-17T12:14:46Z",
        "kernel_pin": KERNEL_REFERENCE,
        "historical_metadata": [
            {
                "commit": "f6bf5ed2c8571fc213c7554a430d3d9c7716a231",
                "version": "0.6.1-cubby",
                "sha256": (
                    "acdccb947f9001bcff4f3e1b8bf84bb6"
                    "b831522a2c7df0d6cffa3cbdae5bfc80"
                ),
                "purpose": (
                    "Drive the self-contained, repo-independent RAPP "
                    "Installer rapplication (status / bootstrap one-liner / "
                    "health) from any brainstem — the grail ported out of its "
                    "repo. Stream via `cave load cubby=kody-w` or plain public "
                    "curl."
                ),
                "observed_streamable": True,
                "accepted": False,
            },
            {
                "commit": "d3d2623646a6111b4a7db9f1b960df233f8964c9",
                "version": "0.0.0-cubby",
                "sha256": (
                    "cabfb8b9067dc1a5bff1f05a22f46e95"
                    "b159913df5cd330fac5b6576f7d8f055"
                ),
                "purpose": (
                    "Fail-closed tombstone for the retired Cave RAPP "
                    "Installer agent."
                ),
                "observed_streamable": False,
                "accepted": False,
            },
        ],
    },
)
RETAINED_SUPER_RAR_EXHAUST = (
    {
        "kind": "agent",
        "name": "rapp_installer_agent.py",
        "cubby": "kody-w",
        "path": "cubbies/kody-w/agents/rapp_installer_agent.py",
        "sha256": (
            "acdccb947f9001bcff4f3e1b8bf84bb6"
            "b831522a2c7df0d6cffa3cbdae5bfc80"
        ),
        "purpose": (
            "Drive the self-contained, repo-independent RAPP Installer "
            "rapplication from any brainstem; original bootstrap and stream "
            "details are retained only as historical metadata."
        ),
        "status": "historical-observation",
        "historical_observation_at": "2026-07-17T12:14:46Z",
        "kernel_pin": KERNEL_REFERENCE,
        "historical_metadata": [
            {
                "commit": "f6bf5ed2c8571fc213c7554a430d3d9c7716a231",
                "sha256": (
                    "acdccb947f9001bcff4f3e1b8bf84bb6"
                    "b831522a2c7df0d6cffa3cbdae5bfc80"
                ),
                "observed_streamable": True,
                "accepted": False,
            },
            {
                "commit": "d3d2623646a6111b4a7db9f1b960df233f8964c9",
                "sha256": (
                    "cabfb8b9067dc1a5bff1f05a22f46e95"
                    "b159913df5cd330fac5b6576f7d8f055"
                ),
                "observed_streamable": False,
                "accepted": False,
            },
        ],
    },
)
HISTORICAL_FILE_OBSERVATIONS = {
    "cubbies/kody-w/eggs/cubby-rapp-installer.egg": [
        {
            "commit": "f6bf5ed2c8571fc213c7554a430d3d9c7716a231",
            "sha256": (
                "eae07bfd67b5e5f1b21fc62c7d3d33e1"
                "c2bd414ff74be04746f21c700ff789a9"
            ),
            "accepted": False,
        },
        {
            "commit": "b67627d450e309ae8d0d78b9289d01f6acec8022",
            "sha256": (
                "38ce5e8f1236b584eb3c6d4a6663ce46"
                "a0ff73c06599628d87fe610e035fb18b"
            ),
            "accepted": False,
        },
    ]
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _purpose(path: Path) -> str:
    """Return the first docstring line of a Python artifact."""
    try:
        head = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )[:1200]
    except OSError:
        return ""
    match = re.search(r'"""(.+?)(?:\n|""")', head)
    return match.group(1).strip()[:200] if match else ""


def _manifest_name(path: Path, default: str) -> tuple[str, bool]:
    """Read the manifest name and required_by_tether flag without importing."""
    try:
        head = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )[:4000]
    except OSError:
        return default, False
    match = re.search(r'"name"\s*:\s*"(@[^"]+)"', head)
    name = match.group(1) if match else default
    required = bool(
        re.search(r'"required_by_tether"\s*:\s*[Tt]rue', head)
    )
    return name, required


def _distribution_state() -> dict:
    return {
        "state": "disabled",
        "fetch": False,
        "install": False,
        "execute": False,
        "stream": False,
        "publish": False,
    }


def _with_file_state(entry: dict, path: Path) -> dict:
    result = dict(entry)
    present = path.is_file()
    if present:
        digest = _sha256_file(path)
        result["sha256"] = digest
        result["verified"] = True
        result["verification"] = {
            "state": "verified-local-sha256",
            "method": "sha256",
            "sha256": digest,
            "scope": "local-bytes-only",
        }
    else:
        result["verified"] = False
        result["verification"] = {
            "state": "unverified-historical-bytes-absent",
            "method": "sha256",
            "historical_sha256": result.get("sha256"),
            "scope": "historical-observation-only",
        }
    result["accepted"] = False
    result["acceptance"] = {
        "state": "not-accepted",
        "authenticated_registry": False,
    }
    result["active_distribution"] = False
    result["streamable"] = False
    result["distribution"] = _distribution_state()
    result["source"] = {
        "path": result.get("path"),
        "present": present,
        "kind": "file",
    }
    return result


def _with_directory_state(entry: dict, path: Path) -> dict:
    result = dict(entry)
    present = path.is_dir()
    result["verified"] = False
    result["verification"] = {
        "state": (
            "unverified-directory-observation"
            if present
            else "unverified-historical-directory-absent"
        ),
        "method": None,
        "scope": "metadata-only",
    }
    result["accepted"] = False
    result["acceptance"] = {
        "state": "not-accepted",
        "authenticated_registry": False,
    }
    result["active_distribution"] = False
    result["streamable"] = False
    result["distribution"] = _distribution_state()
    result["source"] = {
        "path": result.get("path"),
        "present": present,
        "kind": "directory",
    }
    return result


def _safe_relative(relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or "://" in relative:
        raise ValueError(f"unsafe catalog path: {relative}")
    candidate = CAVE / path
    try:
        candidate.resolve(strict=False).relative_to(CAVE.resolve())
    except ValueError as exc:
        raise ValueError(f"catalog path escapes the Cave: {relative}") from exc
    return candidate


def build_super_rar() -> list[dict]:
    """Discover every supported kind across every current cubby."""
    entries = []
    seen = set()
    if CUBBIES.is_dir():
        for handle in sorted(os.listdir(CUBBIES)):
            if handle.startswith((".", "_")):
                continue
            for kind, (subdirectory, pattern) in SUPER_RAR_KINDS.items():
                glob_pattern = os.fspath(
                    CUBBIES / handle / subdirectory / pattern
                )
                for raw_path in sorted(glob.glob(glob_pattern)):
                    path = Path(raw_path)
                    name = path.name
                    if (
                        name.startswith(".")
                        or name == "__pycache__"
                        or path.is_symlink()
                    ):
                        continue
                    relative = path.relative_to(CAVE).as_posix()
                    entry = {
                        "kind": kind,
                        "name": name,
                        "cubby": handle,
                        "path": relative,
                    }
                    if relative in HISTORICAL_FILE_OBSERVATIONS:
                        entry["historical_metadata"] = (
                            HISTORICAL_FILE_OBSERVATIONS[relative]
                        )
                    if path.is_file():
                        purpose = _purpose(path) if path.suffix == ".py" else ""
                        if purpose:
                            entry["purpose"] = purpose
                        entry = _with_file_state(entry, path)
                    else:
                        entry = _with_directory_state(entry, path)
                    entries.append(entry)
                    seen.add(relative)

    for retained in RETAINED_SUPER_RAR_EXHAUST:
        if retained["path"] not in seen:
            entries.append(
                _with_file_state(
                    retained,
                    _safe_relative(retained["path"]),
                )
            )
    entries.sort(
        key=lambda entry: (
            entry.get("cubby", ""),
            entry.get("kind", ""),
            entry.get("path", ""),
        )
    )
    return entries


def render_super_rar() -> dict:
    entries = build_super_rar()
    by_kind: dict[str, int] = {}
    for entry in entries:
        kind = entry["kind"]
        by_kind[kind] = by_kind.get(kind, 0) + 1
    return {
        "schema": "rapp-super-rar/1.0",
        "status": "historical-observation",
        "verified": True,
        "accepted": False,
        "active_distribution": False,
        "streamable": False,
        "distribution": _distribution_state(),
        "neighborhood_rappid": NEIGHBORHOOD_RAPPID,
        "note": SUPER_RAR_NOTE,
        "raw_url_prefix": RAW_URL_TEMPLATE,
        "source_policy": SOURCE_POLICY,
        "provenance": PROVENANCE,
        "built_at": _now(),
        "count": len(entries),
        "by_kind": by_kind,
        "entries": entries,
    }


def render_rar() -> dict:
    """Render participation-agent and rapplication observations."""
    agents = []
    seen_agents = set()
    for path in sorted((CAVE / "agents").glob("*_agent.py")):
        if path.is_symlink():
            continue
        base = path.name[: -len("_agent.py")]
        name, required = _manifest_name(path, f"@kody-w/{base}")
        entry = {
            "name": name,
            "version": "1.0.0",
            "path": f"agents/{path.name}",
            "purpose": _purpose(path)
            or f"Cave participation agent: {base}.",
            "required_by_tether": required,
            "schema": "rapp-agent/1.0",
        }
        agents.append(_with_file_state(entry, path))
        seen_agents.add(entry["path"])

    if CUBBIES.is_dir():
        for handle in sorted(os.listdir(CUBBIES)):
            if handle.startswith((".", "_")):
                continue
            agent_pattern = CUBBIES / handle / "agents" / "*_agent.py"
            for raw_path in sorted(glob.glob(os.fspath(agent_pattern))):
                path = Path(raw_path)
                if path.is_symlink():
                    continue
                relative = path.relative_to(CAVE).as_posix()
                entry = {
                    "name": f"@{handle}/{path.name[:-len('_agent.py')]}",
                    "version": "0.0.0-cubby",
                    "path": relative,
                    "purpose": _purpose(path)
                    or f"Historical cubby agent observation from @{handle}.",
                    "required_by_tether": False,
                    "schema": "rapp-agent/1.0",
                }
                agents.append(_with_file_state(entry, path))
                seen_agents.add(relative)

    for retained in RETAINED_RAR_AGENT_EXHAUST:
        if retained["path"] not in seen_agents:
            agents.append(
                _with_file_state(
                    retained,
                    _safe_relative(retained["path"]),
                )
            )
    agents.sort(key=lambda entry: entry["path"])

    rapps = []
    if CUBBIES.is_dir():
        for handle in sorted(os.listdir(CUBBIES)):
            if handle.startswith((".", "_")):
                continue
            rapp_pattern = CUBBIES / handle / "rapplications" / "*"
            for raw_path in sorted(glob.glob(os.fspath(rapp_pattern))):
                path = Path(raw_path)
                if path.is_symlink() or not path.is_dir():
                    continue
                entry = {
                    "name": f"@{handle}/{path.name}",
                    "version": "0.0.0-cubby",
                    "path": path.relative_to(CAVE).as_posix() + "/",
                    "purpose": (
                        f"Historical rapplication bundle observation from "
                        f"@{handle}."
                    ),
                    "schema": "rapp-rapplication/1.0",
                }
                rapps.append(_with_directory_state(entry, path))

    for path in sorted((CAVE / "rapplications").glob("*")):
        if path.is_symlink() or not path.is_dir():
            continue
        entry = {
            "name": f"@kody-w/{path.name}",
            "version": "0.0.0",
            "schema": "rapp-rapplication/1.0",
            "path": path.relative_to(CAVE).as_posix() + "/",
        }
        if path.name == "rapp-installer":
            entry.update(
                {
                    "status": "retired",
                    "immutable_prepared_snapshot": True,
                    "purpose": (
                        "Retained prepared snapshot: rapp-installer. The "
                        "current immutable grail reference is KERNEL_PIN.json "
                        "and kody-w/rapp-installer@brainstem-v0.6.9; this Cave "
                        "path authorizes no bootstrap or installation."
                    ),
                    "kernel_pin": KERNEL_REFERENCE,
                    "historical_metadata": [
                        {
                            "commit": (
                                "f6bf5ed2c8571fc213c7554a430d3d9c7716a231"
                            ),
                            "version": "0.6.1",
                            "agent_sha256": (
                                "eae07bfd67b5e5f1b21fc62c7d3d33e1"
                                "c2bd414ff74be04746f21c700ff789a9"
                            ),
                            "purpose": (
                                "The rapp-installer grail brainstem, carved "
                                "out of its git repo into a self-contained, "
                                "egged rapplication — full installer parity "
                                "(T1/T2/T3), self-bootstrapping "
                                "(hatch.py/bootstrap.sh), zero grail-commit "
                                "risk. PUBLIC pull (no auth): curl -fsSL "
                                "https://raw.githubusercontent.com/kody-w/"
                                "RAPP/main/cave/rapplications/rapp-installer/"
                                "bootstrap.sh | bash"
                            ),
                            "accepted": False,
                            "distribution": "historical-only",
                        },
                        {
                            "commit": (
                                "b67627d450e309ae8d0d78b9289d01f6acec8022"
                            ),
                            "version": "0.0.0",
                            "purpose": (
                                "Retired prepared snapshot: rapp-installer. "
                                "No bootstrap, installation, or publication "
                                "is authorized."
                            ),
                            "accepted": False,
                            "distribution": "disabled",
                        },
                    ],
                }
            )
        else:
            entry["purpose"] = (
                f"Historical Cave flagship rapplication observation: "
                f"{path.name}."
            )
        rapps.append(_with_directory_state(entry, path))
    rapps.sort(key=lambda entry: entry["path"])

    return {
        "schema": "rapp-rar-index/1.1",
        "status": "historical-observation",
        "verified": True,
        "accepted": False,
        "active_distribution": False,
        "streamable": False,
        "distribution": _distribution_state(),
        "neighborhood_rappid": NEIGHBORHOOD_RAPPID,
        "rar_for": "kody-w/RAPP",
        "kind": "workspace",
        "raw_url_prefix": RAW_URL_TEMPLATE,
        "source_policy": SOURCE_POLICY,
        "note": RAR_NOTE,
        "provenance": PROVENANCE,
        "updated_at": _now(),
        "agents": agents,
        "rapps": rapps,
        "verification": {
            "schema": "rapp-rar-manifest/1.0",
            "scheme": "sha256",
            "mode": "read-only-local-check",
            "scope": "integrity-only-not-trust",
            "catalog_verified": True,
            "accepted": False,
            "moving_refs_accepted": False,
            "required_ref": "full 40-character commit SHA",
            "authorizes_fetch": False,
            "authorizes_installation": False,
            "authorizes_execution": False,
            "authorizes_streaming": False,
        },
    }


def _stable(document: dict) -> str:
    filtered = {
        key: value
        for key, value in document.items()
        if key not in {"built_at", "updated_at"}
    }
    return json.dumps(filtered, indent=2, sort_keys=True)


def _load(path: Path) -> tuple[dict | None, list[str]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"cannot read valid JSON: {exc}"]
    if not isinstance(value, dict):
        return None, ["top-level JSON value must be an object"]
    return value, []


def _validate_entry(entry: object, prefix: str) -> list[str]:
    if not isinstance(entry, dict):
        return [f"{prefix} must be an object"]
    errors = []
    for key, expected in (
        ("accepted", False),
        ("active_distribution", False),
        ("streamable", False),
    ):
        if entry.get(key) is not expected:
            errors.append(f"{prefix}.{key} must be {expected!r}")
    distribution = entry.get("distribution")
    if not isinstance(distribution, dict):
        errors.append(f"{prefix}.distribution must be an object")
    else:
        for action in ("fetch", "install", "execute", "stream", "publish"):
            if distribution.get(action) is not False:
                errors.append(
                    f"{prefix}.distribution.{action} must be false"
                )

    relative = entry.get("path")
    if not isinstance(relative, str) or not relative:
        errors.append(f"{prefix}.path must be a non-empty string")
        return errors
    try:
        path = _safe_relative(relative)
    except ValueError as exc:
        errors.append(f"{prefix}.{exc}")
        return errors

    source = entry.get("source")
    if not isinstance(source, dict):
        errors.append(f"{prefix}.source must be an object")
        return errors
    present = path.is_file() or path.is_dir()
    if source.get("present") is not present:
        errors.append(f"{prefix}.source.present does not match the working tree")

    if path.is_file():
        digest = entry.get("sha256")
        if digest != _sha256_file(path):
            errors.append(f"{prefix}.sha256 does not match local bytes")
        if entry.get("verified") is not True:
            errors.append(f"{prefix}.verified must be true for local file bytes")
    elif not present:
        if entry.get("verified") is not False:
            errors.append(
                f"{prefix}.verified must be false for absent historical bytes"
            )
        verification = entry.get("verification")
        if not isinstance(verification, dict) or not verification.get(
            "historical_sha256"
        ):
            errors.append(
                f"{prefix} must retain a historical SHA-256 when bytes are absent"
            )
    return errors


def _validate_catalog(relative: str, expected: dict) -> list[str]:
    path = CAVE / relative
    document, errors = _load(path)
    if document is None:
        return errors

    fixed = {
        "schema": expected["schema"],
        "status": "historical-observation",
        "accepted": False,
        "active_distribution": False,
        "streamable": False,
        "raw_url_prefix": RAW_URL_TEMPLATE,
    }
    for key, value in fixed.items():
        if document.get(key) != value:
            errors.append(f"{key} must be {value!r}")
    if "/main/" in str(document.get("raw_url_prefix", "")).lower():
        errors.append("raw_url_prefix must not accept a moving main branch")

    source_policy = document.get("source_policy")
    if source_policy != SOURCE_POLICY:
        errors.append("source_policy must require a commit pin and SHA-256")

    groups = ("agents", "rapps") if relative == "rar/index.json" else ("entries",)
    for group in groups:
        entries = document.get(group)
        if not isinstance(entries, list):
            errors.append(f"{group} must be an array")
            continue
        for index, entry in enumerate(entries):
            errors.extend(_validate_entry(entry, f"{group}[{index}]"))

    if relative == "rar/index.json":
        names = {
            entry.get("name")
            for entry in document.get("agents", [])
            if isinstance(entry, dict)
        }
        required = {
            "@kody-w/cave",
            "@rapp/rar_steward",
            "@kody-w/rapp_installer",
        }
        if not required.issubset(names):
            errors.append("agents must retain every known historical entry")
        installer = next(
            (
                entry
                for entry in document.get("rapps", [])
                if isinstance(entry, dict)
                and entry.get("name") == "@kody-w/rapp-installer"
            ),
            None,
        )
        if not installer:
            errors.append("rapps must retain @kody-w/rapp-installer")
        elif installer.get("kernel_pin") != KERNEL_REFERENCE:
            errors.append(
                "rapp-installer must point to KERNEL_PIN.json and "
                "brainstem-v0.6.9"
            )
    else:
        entries = document.get("entries", [])
        if isinstance(entries, list):
            if document.get("count") != len(entries):
                errors.append("count must match entries")
            by_kind = {}
            for entry in entries:
                if isinstance(entry, dict):
                    kind = entry.get("kind")
                    if isinstance(kind, str):
                        by_kind[kind] = by_kind.get(kind, 0) + 1
            if document.get("by_kind") != by_kind:
                errors.append("by_kind must match entries")
            names = {
                entry.get("name")
                for entry in entries
                if isinstance(entry, dict)
            }
            if "rapp_installer_agent.py" not in names:
                errors.append(
                    "entries must retain the removed installer-agent observation"
                )

    if _stable(document) != _stable(expected):
        errors.append("committed catalog differs from the rendered observation")
    return errors


def _targets() -> dict[str, dict]:
    return {
        "super-rar/index.json": render_super_rar(),
        "rar/index.json": render_rar(),
    }


def _check(targets: dict[str, dict]) -> dict[str, list[str]]:
    return {
        relative: errors
        for relative, expected in targets.items()
        if (errors := _validate_catalog(relative, expected))
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Render or check read-only Cave catalog observations. "
            "There is intentionally no write mode."
        )
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--check",
        action="store_true",
        help="validate committed catalogs (default)",
    )
    group.add_argument(
        "--plan",
        action="store_true",
        help="report what would differ without writing",
    )
    group.add_argument(
        "--render",
        choices=("rar", "super-rar", "all"),
        help="emit candidate JSON to stdout without writing",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    targets = _targets()

    if args.render:
        if args.render == "rar":
            value = targets["rar/index.json"]
        elif args.render == "super-rar":
            value = targets["super-rar/index.json"]
        else:
            value = targets
        print(json.dumps(value, indent=2, ensure_ascii=False))
        return 0

    failures = _check(targets)
    if args.plan:
        if not failures:
            print("PLAN: committed Cave catalog observations are current.")
        else:
            for relative, errors in failures.items():
                print(f"PLAN: {relative} would change")
                for error in errors:
                    print(f"  - {error}")
        print("PLAN ONLY: no files were written.")
        return 0

    if failures:
        for relative, errors in failures.items():
            print(f"DRIFT: {relative}")
            for error in errors:
                print(f"  - {error}")
        print(
            "Review `--render all` and update catalogs through a reviewed "
            "commit; this tool never writes."
        )
        return 1

    summary = targets["super-rar/index.json"]
    print(
        "Cave catalog observations are current: "
        f"{summary['count']} super-RAR entries {summary['by_kind']}. "
        "No files were written and no entries were accepted or distributed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
