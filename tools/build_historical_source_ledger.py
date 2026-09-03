#!/usr/bin/env python3
"""Render or verify the restoration provenance ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "HISTORICAL_SOURCE_LEDGER.json"


def line_subsequence() -> dict:
    return {"type": "line-subsequence"}


def marker_set(*markers: str) -> dict:
    return {"type": "marker-set", "markers": list(markers)}


def normalized_line_coverage(minimum: float, *markers: str) -> dict:
    return {
        "type": "normalized-line-coverage",
        "minimum": minimum,
        "markers": list(markers),
    }


def python_symbols() -> dict:
    return {"type": "python-symbol-superset"}


SOURCE_RECORDS = (
    {
        "id": "page-installer-plant",
        "category": "browser-page",
        "path": "installer/plant.html",
        "commit": "92221bd9f56d638418472e1b38f1b92aeaefc276",
        "check": normalized_line_coverage(0.98),
        "adaptation": "Keep the complete planter UI; replace repository creation and install execution with local preview and immutable Grail evidence.",
    },
    {
        "id": "page-installer-plant-qr",
        "category": "browser-page",
        "path": "installer/plant_qr.html",
        "commit": "821375ea6afe32c63cb1838cd8e64122cd3628ac",
        "check": normalized_line_coverage(0.99, "QR"),
        "adaptation": "Keep QR and mobile guidance while preventing install, token, redirect, and repository side effects.",
    },
    {
        "id": "page-installer-seed",
        "category": "browser-page",
        "path": "installer/seed.html",
        "commit": "92221bd9f56d638418472e1b38f1b92aeaefc276",
        "check": normalized_line_coverage(0.99, "Seed"),
        "adaptation": "Keep seed generation and explanatory UI as local preview; no planting, download, or identity acceptance.",
    },
    {
        "id": "page-shortcuts-voice",
        "category": "browser-page",
        "path": "installer/shortcuts/brainstem-voice/index.html",
        "commit": "b4d94199b4d7d6952f513697ed47a3e323e231d6",
        "check": normalized_line_coverage(0.96, "Brainstem", "Voice"),
        "adaptation": "Keep the voice Shortcut walkthrough while deriving presentation locally and removing install or credential effects.",
    },
    {
        "id": "page-shortcuts-index",
        "category": "browser-page",
        "path": "installer/shortcuts/index.html",
        "commit": "b4d94199b4d7d6952f513697ed47a3e323e231d6",
        "check": normalized_line_coverage(0.94, "Shortcut"),
        "adaptation": "Keep the complete Shortcut catalog and copy while making distribution and deep-link actions evidence-only.",
    },
    {
        "id": "page-chat",
        "category": "browser-page",
        "path": "pages/chat.html",
        "commit": "1db25e90f9f22821875e2f01bfb58c7f77243c4d",
        "check": normalized_line_coverage(0.99, "chat"),
        "adaptation": "Keep the historical bridge source and state logic while preventing redirects, token reads, and worker requests.",
    },
    {
        "id": "page-grail-brainstem",
        "category": "browser-page",
        "path": "pages/grail-brainstem/index.html",
        "commit": "871cd3283b7ecc2088f5acba9b79048b79bd30cf",
        "check": line_subsequence(),
        "adaptation": "Keep the full browser runtime snapshot and controls as local replay; Grail execution and external effects remain disabled.",
    },
    {
        "id": "page-lobby",
        "category": "browser-page",
        "path": "pages/lobby.html",
        "commit": "0248ad70a80624032f65dcdee1da98de0dc70ecb",
        "check": normalized_line_coverage(0.99, "lobby"),
        "adaptation": "Keep room and peer UI while replacing sockets and state exchange with deterministic local demonstration data.",
    },
    {
        "id": "page-metropolis",
        "category": "browser-page",
        "path": "pages/metropolis/index.html",
        "commit": "1d4141f32a0b90c8de24be136478cc583bed6474",
        "check": normalized_line_coverage(
            0.93,
            "Metropolis",
            "federated_trackers",
            "activity-snapshot.json",
            "function render",
            "async function fetchTracker",
        ),
        "adaptation": "Restore cards, filters, local federation, and activity over checked-in snapshots; live probes and remote trackers stay disabled.",
    },
    {
        "id": "page-metropolis-discord",
        "category": "browser-page",
        "path": "pages/metropolis/plant-from-discord.html",
        "commit": "1f211283250234b8df406d3f5ba445c2d52c9864",
        "check": normalized_line_coverage(0.99, "Discord"),
        "adaptation": "Keep the complete Discord planting guide and form behavior as local review output; no bot or repository action.",
    },
    {
        "id": "page-payphone",
        "category": "browser-page",
        "path": "pages/payphone.html",
        "commit": "9ad5c6b466ceb511b32630755c3114bad269f518",
        "check": normalized_line_coverage(0.98, "payphone"),
        "adaptation": "Keep the payphone UI and parser context while disabling tokens, API lookup, storage, and remote sessions.",
    },
    {
        "id": "page-sphere",
        "category": "browser-page",
        "path": "pages/sphere.html",
        "commit": "d6e814d9a0ed151cbb3a08b146919491c924d368",
        "check": line_subsequence(),
        "adaptation": "Keep the complete sphere interface and local visual behavior; authentication, providers, microphone, iframe, and inference stay disabled.",
    },
    {
        "id": "page-summon",
        "category": "browser-page",
        "path": "pages/summon.html",
        "commit": "7b2390499ee9b238902db1470ccdfae89c1f0cbc",
        "check": line_subsequence(),
        "adaptation": "Keep the summon experience and historical handoff logic while preventing discovery, storage handoff, and embodiment.",
    },
    {
        "id": "page-tether",
        "category": "browser-page",
        "path": "pages/tether.html",
        "commit": "78fb94dfe765110503cafdbb2d4f82e8922989a9",
        "check": line_subsequence(),
        "adaptation": "Keep the launch sequence, lobby, town square, discovery, and call UI with local shims; plant controls open Grail evidence only.",
    },
    {
        "id": "page-vbrainstem",
        "category": "browser-page",
        "path": "pages/vbrainstem.html",
        "commit": "19ff7d9ff483c0eef258a3b2031da1fd74570854",
        "check": line_subsequence(),
        "adaptation": "Keep the complete browser brainstem UI and source while disabling credential, persistence, network, and artifact-export effects.",
    },
    {
        "id": "page-vbrainstem-index",
        "category": "browser-page",
        "path": "pages/vbrainstem/index.html",
        "commit": "ca9b8b71c98a330ff3413313f717b7b62f3e2402",
        "check": line_subsequence(),
        "adaptation": "Keep the directory alias interface and cards over in-memory fixtures; no auth, storage, federation, or model calls.",
    },
    {
        "id": "page-vneighborhood",
        "category": "browser-page",
        "path": "pages/vneighborhood.html",
        "commit": "1ccd4bdfe513b0fdaa91e9f6bc73e93be59253de",
        "check": normalized_line_coverage(0.99, "vNeighborhood"),
        "adaptation": "Keep the neighborhood UI and state model while disabling peer discovery, room join, worker, and remote state exchange.",
    },
    {
        "id": "runtime-worker",
        "category": "browser-runtime",
        "path": "worker/worker.js",
        "commit": "4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6",
        "check": marker_set(
            "export const HISTORICAL_SOURCE",
            "DEFAULT_CAPABILITIES",
            "RAPP_BROWSER_RUNTIME_ENABLED",
            "explicit-reviewed-runtime-binding-required",
            "/api/copilot/chat",
        ),
        "adaptation": "Retain every route behind explicit runtime, reviewed binding, origin, and per-capability gates with no ambient fetch fallback.",
    },
    {
        "id": "runtime-doorman-chat",
        "category": "browser-runtime",
        "path": "tests/doorman/chat.js",
        "commit": "6bd45f00981959a3fdfcc64fb32608533aae5021",
        "check": marker_set(
            "HISTORICAL_SOURCE",
            "RAPP_DOORMAN_FIXTURE_ORIGINS",
            "requireAllowedFixtureUrl",
            "requireSyntheticToken",
            "playwright",
        ),
        "adaptation": "Retain browser chat automation with synthetic credentials and exact loopback or allowlisted origins.",
    },
    {
        "id": "runtime-doorman-smoke",
        "category": "browser-runtime",
        "path": "tests/doorman/smoke.js",
        "commit": "6bd45f00981959a3fdfcc64fb32608533aae5021",
        "check": marker_set(
            "HISTORICAL_SOURCE",
            "RAPP_DOORMAN_FIXTURE_ORIGINS",
            "requireAllowedFixtureUrl",
            "requireSyntheticToken",
            "fleet",
        ),
        "adaptation": "Retain the full browser smoke fleet behind explicit dependency, credential, and final-origin checks.",
    },
    {
        "id": "runtime-tether-browser-runner",
        "category": "browser-runtime",
        "path": "tests/osi/L4a-tether-browser.sh",
        "commit": "6bd45f00981959a3fdfcc64fb32608533aae5021",
        "check": marker_set(
            "RAPP_OSI_BROWSER_EXTERNAL",
            "RAPP_CHROMIUM_EXECUTABLE",
            "RAPP_PEERJS_BUNDLE",
        ),
        "adaptation": "Retain the browser transport runner while defaulting to an offline-safe skip and requiring supplied dependencies.",
    },
    {
        "id": "runtime-tether-browser-spec",
        "category": "browser-runtime",
        "path": "tests/osi/browser/L4a-tether.spec.mjs",
        "commit": "6bd45f00981959a3fdfcc64fb32608533aae5021",
        "check": marker_set(
            "HISTORICAL_SOURCE",
            "RAPP_OSI_BROWSER_EXTERNAL",
            "rapp-tether/1.0",
            "chromium",
        ),
        "adaptation": "Retain two-browser transport behavior while requiring explicit external execution and supplied broker/browser modules.",
    },
    {
        "id": "runtime-tether-fixture",
        "category": "browser-runtime",
        "path": "tests/osi/browser/fixture.html",
        "commit": "6bd45f00981959a3fdfcc64fb32608533aae5021",
        "check": marker_set(
            "rapp-tether/1.0",
            "connect",
            "send",
            "peer",
        ),
        "adaptation": "Retain the complete fixture UI and transport source for explicit local test use.",
    },
    {
        "id": "cave-rar-steward",
        "category": "catalog-code",
        "path": "cave/agents/rar_steward_agent.py",
        "commit": "6bd45f00981959a3fdfcc64fb32608533aae5021",
        "check": marker_set(
            "class RarStewardAgent",
            "def _clusters",
            "def _junk",
            "def _file_issues",
            "def perform",
        ),
        "adaptation": "Retain health, duplicate, junk, agent, and issue-plan analysis with local catalogs by default and immutable checked network inputs only.",
    },
    {
        "id": "cave-super-rar-builder",
        "category": "catalog-code",
        "path": "cave/tools/build_super_rar.py",
        "commit": "6bd45f00981959a3fdfcc64fb32608533aae5021",
        "check": marker_set(
            "SUPER_RAR_KINDS",
            "RETAINED_RAR_AGENT_EXHAUST",
            "def build_super_rar",
            "def render_rar",
            "--render",
        ),
        "adaptation": "Retain discovery, hashing, rendering, and absent-entry history in read-only check, plan, and render modes.",
    },
    {
        "id": "estate-private-init",
        "category": "estate-code",
        "path": "tools/private_estate_init.py",
        "commit": "591e7aec3b2183e0d48a1d6dfb6ebc59f177daea",
        "check": python_symbols(),
        "adaptation": "Retain the complete private-estate bootstrap behind explicit apply, exact target approval, and unavailable authenticated authority.",
    },
    {
        "id": "estate-rebuild",
        "category": "estate-code",
        "path": "tools/rebuild_estate.py",
        "commit": "591e7aec3b2183e0d48a1d6dfb6ebc59f177daea",
        "check": python_symbols(),
        "adaptation": "Retain complete public-data reconstruction and deterministic candidate output while separating observation from authenticated adoption.",
    },
    {
        "id": "network-sniffer",
        "category": "estate-code",
        "path": "tools/sniff_network.py",
        "commit": "4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6",
        "check": python_symbols(),
        "adaptation": "Retain BFS, topic, beacon, estate, and skipped-record observations with no acceptance and gated output writes.",
    },
    {
        "id": "ecosystem-audit",
        "category": "estate-code",
        "path": "tools/ecosystem_audit.py",
        "commit": "a2c7358a236852586b3c1e430b044703b947aab8",
        "check": python_symbols(),
        "adaptation": "Retain the complete Bond Pulse drift detector with offline fixtures by default and explicit write/online gates.",
    },
    {
        "id": "ecosystem-contract",
        "category": "estate-code",
        "path": "tools/ecosystem_contract.py",
        "commit": "9ad5c6b466ceb511b32630755c3114bad269f518",
        "check": python_symbols(),
        "adaptation": "Retain historical product kind contracts while keeping them separate from RAPP/1 authority.",
    },
    {
        "id": "holo-card-generator",
        "category": "estate-code",
        "path": "tools/holo_card_generator.py",
        "commit": "7b2390499ee9b238902db1470ccdfae89c1f0cbc",
        "check": python_symbols(),
        "adaptation": "Retain deterministic profile, ability, mnemonic, avatar, and summon output while labelling historical and pinned modes unaccepted.",
    },
    {
        "id": "mirror-drift-check",
        "category": "estate-code",
        "path": "tests/mirror-drift.sh",
        "commit": "b4f3e31c1c30cfaf798728cec2de45dbfcfb3e25",
        "check": marker_set(
            "KERNEL_PIN.json",
            "brainstem-v0.6.9",
            "expected_sha",
        ),
        "adaptation": "Retain exact local and immutable-tag hash verification without overwrite or moving-main behavior.",
    },
    {
        "id": "metropolis-collector",
        "category": "metropolis-code",
        "path": "scripts/harvest-metropolis-activity.py",
        "commit": "1d4141f32a0b90c8de24be136478cc583bed6474",
        "check": python_symbols(),
        "adaptation": "Retain the complete collector; default to local snapshot validation, expose a no-write plan, and refuse online writes before mutation.",
    },
)

ADDITIONAL_PAGE_SOURCES = (
    (
        "page-root-index",
        "entry-page",
        "index.html",
        "32db6f894e4224e2b0b2944b1d6ac1188ec37b61",
        0.92,
        ("RAPP Stack",),
    ),
    (
        "page-pages-index",
        "entry-page",
        "pages/index.html",
        "f9a190003429e46ef406efd618120f287e3f3878",
        0.98,
        ("Single-file AI agents",),
    ),
    (
        "page-kernel",
        "entry-page",
        "pages/kernel.html",
        "4352699694151816a8ec69199c34a68d7ae1c051",
        0.96,
        ("RAPP",),
    ),
    (
        "page-installer-index",
        "entry-page",
        "installer/index.html",
        "55b91b9ecd182a3ce2057787f07c60e9aa3ca128",
        0.92,
        ("RAPP Installer",),
    ),
    (
        "page-cave-index",
        "entry-page",
        "cave/index.html",
        "f6bf5ed2c8571fc213c7554a430d3d9c7716a231",
        0.94,
        ("The RAPP Cave",),
    ),
    (
        "page-vault-index",
        "entry-page",
        "pages/vault/index.html",
        "925dee4a211965f2582e71a6d2ad75f60a54ea7d",
        0.78,
        ("vault.js",),
    ),
    (
        "partial-site-header",
        "entry-page",
        "pages/_site/partials/header.html",
        "f9a190003429e46ef406efd618120f287e3f3878",
        0.94,
        ("site-header",),
    ),
    (
        "partial-site-footer",
        "entry-page",
        "pages/_site/partials/footer.html",
        "8383dc24a47bf0e310f20b3ecb7c7675dcaabb81",
        0.96,
        ("site-footer",),
    ),
    (
        "page-pitch-playbook",
        "historical-page",
        "pitch-playbook.html",
        "4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6",
        0.99,
        ("the acceleration layer",),
    ),
    (
        "page-blog",
        "historical-page",
        "blog.html",
        "2526f40730ff0ce40a3385b6daa211aa2f817911",
        0.99,
        ("RAPP",),
    ),
    (
        "page-root-release-notes",
        "historical-page",
        "release-notes.html",
        "2526f40730ff0ce40a3385b6daa211aa2f817911",
        0.99,
        ("Release",),
    ),
    (
        "page-about-ecosystem",
        "historical-page",
        "pages/about/ecosystem.html",
        "2526f40730ff0ce40a3385b6daa211aa2f817911",
        0.99,
        ("ecosystem",),
    ),
    (
        "page-docs-index",
        "historical-page",
        "docs/index.html",
        "8c5555be80357e795090d79c4fb5a33beb0eaab8",
        0.97,
        ("RAPP",),
    ),
    (
        "page-docs-tutorial",
        "historical-page",
        "docs/tutorial.html",
        "8c5555be80357e795090d79c4fb5a33beb0eaab8",
        0.95,
        ("tutorial",),
    ),
    (
        "page-onboarding",
        "historical-page",
        "pages/onboarding.html",
        "8c5555be80357e795090d79c4fb5a33beb0eaab8",
        1.0,
        ("onboarding",),
    ),
    (
        "page-rappid-deck",
        "historical-page",
        "pages/rappid-deck.html",
        "8c5555be80357e795090d79c4fb5a33beb0eaab8",
        0.99,
        ("rappid",),
    ),
    (
        "page-rappid-onepager",
        "historical-page",
        "pages/rappid-onepager.html",
        "8c5555be80357e795090d79c4fb5a33beb0eaab8",
        0.99,
        ("rappid",),
    ),
    (
        "page-invention-backlog",
        "historical-page",
        "pages/share/invention-backlog/index.html",
        "8c5555be80357e795090d79c4fb5a33beb0eaab8",
        0.98,
        ("invention",),
    ),
    (
        "page-about-leadership",
        "historical-page",
        "pages/about/leadership.html",
        "d3d2623646a6111b4a7db9f1b960df233f8964c9",
        0.95,
        ("Leadership",),
    ),
    (
        "page-about-partners",
        "historical-page",
        "pages/about/partners.html",
        "d3d2623646a6111b4a7db9f1b960df233f8964c9",
        0.95,
        ("Partners",),
    ),
    (
        "page-about-process",
        "historical-page",
        "pages/about/process.html",
        "d3d2623646a6111b4a7db9f1b960df233f8964c9",
        0.95,
        ("Process",),
    ),
    (
        "page-about-prompts",
        "historical-page",
        "pages/about/prompts.html",
        "d3d2623646a6111b4a7db9f1b960df233f8964c9",
        0.99,
        ("prompts",),
    ),
    (
        "page-about-security",
        "historical-page",
        "pages/about/security.html",
        "d3d2623646a6111b4a7db9f1b960df233f8964c9",
        0.95,
        ("Security",),
    ),
    (
        "page-product-faq-slide",
        "historical-page",
        "pages/product/faq-slide.html",
        "d3d2623646a6111b4a7db9f1b960df233f8964c9",
        0.94,
        ("Four questions",),
    ),
    (
        "page-product-faq",
        "historical-page",
        "pages/product/faq.html",
        "d3d2623646a6111b4a7db9f1b960df233f8964c9",
        0.97,
        ("FAQ",),
    ),
    (
        "page-product-one-pager",
        "historical-page",
        "pages/product/one-pager.html",
        "d3d2623646a6111b4a7db9f1b960df233f8964c9",
        0.94,
        ("swarm",),
    ),
    (
        "page-product-unsolved",
        "historical-page",
        "pages/product/unsolved.html",
        "d3d2623646a6111b4a7db9f1b960df233f8964c9",
        1.0,
        ("unsolved",),
    ),
    (
        "page-product-use-cases",
        "historical-page",
        "pages/product/use-cases.html",
        "d3d2623646a6111b4a7db9f1b960df233f8964c9",
        0.95,
        ("Lead prioritization",),
    ),
    (
        "page-product-vs",
        "historical-page",
        "pages/product/vs.html",
        "d3d2623646a6111b4a7db9f1b960df233f8964c9",
        1.0,
        ("RAPP",),
    ),
    (
        "page-release-roadmap",
        "historical-page",
        "pages/release/roadmap.html",
        "d3d2623646a6111b4a7db9f1b960df233f8964c9",
        0.99,
        ("Roadmap",),
    ),
    (
        "page-about-anatomy",
        "historical-page",
        "pages/about/anatomy.html",
        "d1c5903c3927478033df1520046ba5297abdbbf8",
        0.99,
        ("anatomy",),
    ),
    (
        "page-release-notes",
        "historical-page",
        "pages/release/release-notes.html",
        "d1c5903c3927478033df1520046ba5297abdbbf8",
        0.99,
        ("Release",),
    ),
    (
        "page-hatch-egg",
        "historical-page",
        "pages/tutorials/hatch-egg.html",
        "d1c5903c3927478033df1520046ba5297abdbbf8",
        0.98,
        ("egg",),
    ),
)

SOURCE_RECORDS += tuple(
    {
        "id": record_id,
        "category": category,
        "path": path,
        "commit": commit,
        "check": normalized_line_coverage(minimum, *markers),
        "adaptation": (
            "Retain the complete historical presentation and local controls; "
            "remove intrusive adaptation banners and redirect only unsafe "
            "execution, installer, download, deployment, or publication edges "
            "to current evidence."
        ),
    }
    for record_id, category, path, commit, minimum, markers in ADDITIONAL_PAGE_SOURCES
)


def run(*args: str, text: bool = False):
    return subprocess.check_output(args, cwd=ROOT, text=text)


def source_record(record: dict) -> dict:
    path = record["path"]
    source_path = record.get("source_path", path)
    commit = record["commit"]
    source = run("git", "show", f"{commit}:{source_path}")
    blob = run(
        "git", "rev-parse", f"{commit}:{source_path}", text=True
    ).strip()
    current = (ROOT / path).read_bytes()
    restored_commit = run(
        "git", "log", "-1", "--format=%H", "--", path, text=True
    ).strip()
    return {
        "id": record["id"],
        "category": record["category"],
        "current_path": path,
        "source": {
            "repository": "kody-w/RAPP",
            "commit": commit,
            "path": source_path,
            "blob": blob,
            "sha256": hashlib.sha256(source).hexdigest(),
            "bytes": len(source),
        },
        "restored": {
            "commit": restored_commit,
            "sha256": hashlib.sha256(current).hexdigest(),
            "bytes": len(current),
        },
        "preservation_check": record["check"],
        "safety_adaptation": record["adaptation"],
        "trust_state": {
            "observed": True,
            "structurally_valid": True,
            "cryptographically_verified": False,
            "fresh": False,
            "accepted": False,
        },
    }


def render() -> str:
    value = {
        "schema": "rapp-historical-source-ledger/1.0",
        "record_kind": "candidate-restoration-provenance",
        "status": "candidate",
        "is_section_13_registry": False,
        "authenticated_acceptance_allowed": False,
        "authority": "RAPP1_AUTHORITY.json",
        "conformance_status": "RAPP1_STATUS.md",
        "policy": {
            "restore_fullest_artifact_first": True,
            "preserve_data_exhaust": True,
            "disable_only_exact_unsafe_edges": True,
            "installer_reference": "KERNEL_PIN.json",
            "grail": "kody-w/rapp-installer@brainstem-v0.6.9",
        },
        "generation_basis": (
            "Each source is pinned by commit/blob/SHA-256/byte count; each "
            "restored path is pinned by its most recent path commit and "
            "current SHA-256/byte count."
        ),
        "artifacts": [source_record(record) for record in SOURCE_RECORDS],
    }
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--render", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    expected = render()

    if args.render:
        print(expected, end="")
        return 0
    if args.write:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=OUTPUT.parent,
            delete=False,
        ) as handle:
            handle.write(expected)
            temporary = Path(handle.name)
        temporary.replace(OUTPUT)
        print(f"wrote {OUTPUT.relative_to(ROOT)}")
        return 0

    if not OUTPUT.is_file():
        print(f"{OUTPUT.relative_to(ROOT)} is missing")
        return 1
    if OUTPUT.read_text(encoding="utf-8") != expected:
        print(f"{OUTPUT.relative_to(ROOT)} is stale")
        return 1
    print(f"{OUTPUT.relative_to(ROOT)} is current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
