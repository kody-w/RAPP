#!/usr/bin/env python3
"""Render or verify the restoration provenance ledger."""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "HISTORICAL_SOURCE_LEDGER.json"


def deterministic_gzip(source: bytes) -> bytes:
    payload = bytearray(gzip.compress(source, mtime=0))
    payload[9] = 255
    return bytes(payload)


def line_subsequence() -> dict:
    return {"type": "line-subsequence"}


def marker_set(minimum_line_coverage: float, *markers: str) -> dict:
    return {
        "type": "marker-set",
        "minimum_line_coverage": minimum_line_coverage,
        "markers": list(markers),
    }


def normalized_line_coverage(minimum: float, *markers: str) -> dict:
    return {
        "type": "normalized-line-coverage",
        "minimum": minimum,
        "markers": list(markers),
    }


def python_symbols(minimum_line_coverage: float) -> dict:
    return {
        "type": "python-symbol-superset",
        "minimum_line_coverage": minimum_line_coverage,
    }


SOURCE_RECORDS = (
    {
        "id": "page-installer-plant",
        "category": "browser-page",
        "path": "installer/plant.html",
        "commit": "92221bd9f56d638418472e1b38f1b92aeaefc276",
        "check": normalized_line_coverage(0.955),
        "adaptation": "Keep the complete planter UI; replace repository creation and install execution with local preview and immutable Grail evidence.",
    },
    {
        "id": "page-installer-plant-qr",
        "category": "browser-page",
        "path": "installer/plant_qr.html",
        "commit": "821375ea6afe32c63cb1838cd8e64122cd3628ac",
        "check": normalized_line_coverage(0.985, "QR"),
        "adaptation": "Keep QR and mobile guidance while preventing install, token, redirect, and repository side effects.",
    },
    {
        "id": "page-installer-seed",
        "category": "browser-page",
        "path": "installer/seed.html",
        "commit": "92221bd9f56d638418472e1b38f1b92aeaefc276",
        "check": normalized_line_coverage(0.949, "Seed"),
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
        "check": normalized_line_coverage(0.945, "Shortcut"),
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
        "check": normalized_line_coverage(0.995, "Discord"),
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
            0.335,
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
            0.225,
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
            0.425,
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
            0.210,
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
            0.295,
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
            0.485,
            "rapp-tether/1.0",
            "connect",
            "send",
            "peer",
        ),
        "adaptation": "Retain the complete fixture UI and transport source for explicit local test use.",
    },
    {
        "id": "runtime-vault-viewer",
        "category": "browser-runtime",
        "path": "pages/vault/vault.js",
        "commit": "925dee4a211965f2582e71a6d2ad75f60a54ea7d",
        "check": marker_set(
            0.90,
            "content-bundle.json",
            "sanitizeHtml",
            "buildBacklinks",
        ),
        "adaptation": "Retain the complete searchable vault viewer while replacing moving raw-note fetches with a hash-verified local content bundle and sanitized local renderer.",
    },
    {
        "id": "cave-rar-steward",
        "category": "catalog-code",
        "path": "cave/agents/rar_steward_agent.py",
        "commit": "6bd45f00981959a3fdfcc64fb32608533aae5021",
        "check": marker_set(
            0.245,
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
            0.328,
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
        "check": python_symbols(0.867),
        "adaptation": "Retain the complete private-estate bootstrap behind explicit apply, exact target approval, and unavailable authenticated authority.",
    },
    {
        "id": "estate-rebuild",
        "category": "estate-code",
        "path": "tools/rebuild_estate.py",
        "commit": "591e7aec3b2183e0d48a1d6dfb6ebc59f177daea",
        "check": python_symbols(0.859),
        "adaptation": "Retain complete public-data reconstruction and deterministic candidate output while separating observation from authenticated adoption.",
    },
    {
        "id": "network-sniffer",
        "category": "estate-code",
        "path": "tools/sniff_network.py",
        "commit": "4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6",
        "check": python_symbols(0.667),
        "adaptation": "Retain BFS, topic, beacon, estate, and skipped-record observations with no acceptance and gated output writes.",
    },
    {
        "id": "ecosystem-audit",
        "category": "estate-code",
        "path": "tools/ecosystem_audit.py",
        "commit": "a2c7358a236852586b3c1e430b044703b947aab8",
        "check": python_symbols(0.846),
        "adaptation": "Retain the complete Bond Pulse drift detector with offline fixtures by default and explicit write/online gates.",
    },
    {
        "id": "ecosystem-contract",
        "category": "estate-code",
        "path": "tools/ecosystem_contract.py",
        "commit": "9ad5c6b466ceb511b32630755c3114bad269f518",
        "check": python_symbols(0.976),
        "adaptation": "Retain historical product kind contracts while keeping them separate from RAPP/1 authority.",
    },
    {
        "id": "holo-card-generator",
        "category": "estate-code",
        "path": "tools/holo_card_generator.py",
        "commit": "7b2390499ee9b238902db1470ccdfae89c1f0cbc",
        "check": python_symbols(0.933),
        "adaptation": "Retain deterministic profile, ability, mnemonic, avatar, and summon output while labelling historical and pinned modes unaccepted.",
    },
    {
        "id": "mirror-drift-check",
        "category": "estate-code",
        "path": "tests/mirror-drift.sh",
        "commit": "b4f3e31c1c30cfaf798728cec2de45dbfcfb3e25",
        "check": marker_set(
            0.177,
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
        "check": python_symbols(0.982),
        "adaptation": "Retain the complete collector; default to local snapshot validation, expose a no-write plan, and refuse online writes before mutation.",
    },
)

DISTRIBUTION_SOURCE_RECORDS = (
    ("distribution-root-install-sh", "distribution-code", "install.sh", "25dc094994cf889f0907ea15c255000c07dbfcc9"),
    ("distribution-root-install-ps1", "distribution-code", "install.ps1", "cef3b9160f0ca6773d84ccc605e2d5d81369b2d9"),
    ("distribution-root-install-cmd", "distribution-code", "install.cmd", "4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6"),
    ("distribution-root-install-command", "distribution-code", "install.command", "4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6"),
    ("distribution-docs-install-sh", "distribution-code", "docs/install.sh", "4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6"),
    ("distribution-docs-install-cmd", "distribution-code", "docs/install.cmd", "4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6"),
    ("distribution-docs-install-command", "distribution-code", "docs/install.command", "4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6"),
    ("distribution-community-install-sh", "distribution-code", "community_rapp/install.sh", "4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6"),
    ("distribution-community-install-ps1", "distribution-code", "community_rapp/install.ps1", "4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6"),
    ("distribution-installer-install-sh", "distribution-code", "installer/install.sh", "5f67e1e7a279e45e384a1673d09d1739936f72d9"),
    ("distribution-installer-install-ps1", "distribution-code", "installer/install.ps1", "45d8e9fc6df2989d6c1c591613e30710f768ef1a"),
    ("distribution-installer-install-cmd", "distribution-code", "installer/install.cmd", "b4f3e31c1c30cfaf798728cec2de45dbfcfb3e25"),
    ("distribution-installer-swarm", "distribution-code", "installer/install-swarm.sh", "925dee4a211965f2582e71a6d2ad75f60a54ea7d"),
    ("distribution-installer-start-local", "distribution-code", "installer/start-local.sh", "925dee4a211965f2582e71a6d2ad75f60a54ea7d"),
    ("distribution-installer-integration-plant", "distribution-code", "installer/integration_plant.sh", "0e068b3cd7bb56add2b3a3e2eea6b9142905a574"),
    ("distribution-installer-hatchling", "distribution-code", "installer/hatchling", "9bf771df8b308e11f681fc62a9d04a81450ceb03"),
    ("distribution-installer-plant", "distribution-code", "installer/plant.sh", "f9102acd7c152ab99dce4fe75fcb0968cec3890b"),
    ("distribution-root-deploy-sh", "distribution-code", "deploy.sh", "4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6"),
    ("distribution-root-deploy-ps1", "distribution-code", "deploy.ps1", "4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6"),
    ("distribution-sign-release", "distribution-code", "tools/sign_release.py", "4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6"),
    ("distribution-lan-advertise", "distribution-code", "tools/lan_advertise.py", "da4f78abdff5f2bc9ff9e1266ddbf0723cb20161"),
    ("distribution-brainstem-start-sh", "distribution-code", "rapp_brainstem/start.sh", "01c11f52f1edb7d3e337e4f223aa8d514f622ebb"),
    ("distribution-brainstem-start-ps1", "distribution-code", "rapp_brainstem/start.ps1", "844f84ef54ce2481f670a9ca8830c96a60b70c72"),
    ("distribution-brainstem-tls-proxy", "distribution-code", "rapp_brainstem/tls_proxy.py", "55b91b9ecd182a3ce2057787f07c60e9aa3ca128"),
    ("distribution-brainstem-boot", "distribution-code", "rapp_brainstem/utils/boot.py", "7f9553ed0f079fbce70755ee4cae3e51705dcccf"),
)

SOURCE_RECORDS += tuple(
    {
        "id": record_id,
        "category": category,
        "path": path,
        "commit": commit,
        "check": line_subsequence(),
        "adaptation": (
            "Restore the exact historical implementation after a target-owned "
            "plan/refusal boundary. Default execution emits local provenance; "
            "active effects remain unavailable without exact Grail binding, "
            "reviewed dependency injection, owner approval, and authenticated "
            "fresh section-13 evidence."
        ),
    }
    for record_id, category, path, commit in DISTRIBUTION_SOURCE_RECORDS
)

DEPLOYMENT_TEMPLATE_SOURCE_RECORDS = (
    (
        "deployment-template-root",
        "azuredeploy.json",
        "4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6",
    ),
    (
        "deployment-template-installer",
        "installer/azuredeploy.json",
        "925dee4a211965f2582e71a6d2ad75f60a54ea7d",
    ),
)

SOURCE_RECORDS += tuple(
    {
        "id": record_id,
        "category": "deployment-template",
        "path": path,
        "commit": commit,
        "check": normalized_line_coverage(
            0.997,
            "Rapid Agent Prototype Platform assistant",
        ),
        "adaptation": (
            "Restore the complete inert ARM template byte-for-byte. Deployment "
            "callers retain separate explicit pre-acceptance gates and cannot "
            "reach Azure without unavailable authenticated owner evidence."
        ),
    }
    for record_id, path, commit in DEPLOYMENT_TEMPLATE_SOURCE_RECORDS
)

SWARM_SOURCE_RECORDS = (
    (
        "swarm-index",
        "rapp_swarm/index.html",
        "da6cb94985c9525b681bc20c2926656bdfdad565",
        normalized_line_coverage(
            0.924,
            "Azure Functions · Python 3.11",
            "Application Insights",
            "data-historical-href",
        ),
    ),
    (
        "swarm-build",
        "rapp_swarm/build.sh",
        "7bcc3d24ab3759605630625225fd190612c3d594",
        normalized_line_coverage(1.0, "rsync -a", "services/*_service.py"),
    ),
    (
        "swarm-provision-twin",
        "rapp_swarm/provision-twin.sh",
        "925dee4a211965f2582e71a6d2ad75f60a54ea7d",
        normalized_line_coverage(0.993, "az deployment group create"),
    ),
    (
        "swarm-provision-twin-lite",
        "rapp_swarm/provision-twin-lite.sh",
        "4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6",
        normalized_line_coverage(1.0, "az functionapp create"),
    ),
    (
        "swarm-function-app",
        "rapp_swarm/function_app.py",
        "7246d15d03809dd9df644270d920b1a5743d2515",
        python_symbols(0.995),
    ),
    (
        "swarm-twin-sim",
        "rapp_swarm/twin-sim.sh",
        "da6cb94985c9525b681bc20c2926656bdfdad565",
        normalized_line_coverage(0.994, "cmd_demo_book()", "cmd_demo_hero()"),
    ),
    (
        "swarm-twin-egg",
        "rapp_swarm/twin-egg.sh",
        "da6cb94985c9525b681bc20c2926656bdfdad565",
        normalized_line_coverage(1.0, "cmd_pack()", "cmd_unpack()"),
    ),
    (
        "swarm-test-brainstem-server",
        "tools/test_brainstem_server.py",
        "dd36590c8f5601c3ccf241844cdc9db54f7c420b",
        python_symbols(0.809),
    ),
    (
        "swarm-egg-hatcher",
        "pages/tutorials/egg_hatcher_agent.py",
        "f715eb3e6d4b473bbc34c472d3ad60cf6a2e144f",
        python_symbols(0.933),
    ),
    (
        "swarm-front-door-specs",
        "tools/front_door_specs.py",
        "2efdc1f230ec939f0a1041caeb2813e5c4f59a1f",
        python_symbols(0.998),
    ),
    (
        "swarm-simulation-readme",
        "tools/sim/README.md",
        "05f75bd40dd37f4590da6ebab28110d9a4b4094a",
        normalized_line_coverage(0.988, "Grail-driven autonomy"),
    ),
    (
        "swarm-loop-orchestrator",
        "tools/sim/loop_orchestrator.sh",
        "55b91b9ecd182a3ce2057787f07c60e9aa3ca128",
        normalized_line_coverage(1.0, "historical_orchestrator_cycle"),
    ),
    (
        "swarm-observer",
        "tools/sim/observe.py",
        "55b91b9ecd182a3ce2057787f07c60e9aa3ca128",
        python_symbols(0.989),
    ),
    (
        "swarm-plant-two-brainstems",
        "tools/sim/plant_two_brainstems.py",
        "40f00e1e669d4cd4bb97e2947a0b79739a9ba701",
        python_symbols(0.995),
    ),
    (
        "swarm-push-canvas",
        "tools/sim/push_canvas.sh",
        "8d089dc459f156fb214316db3383e2d95355261d",
        normalized_line_coverage(1.0, "git push"),
    ),
    (
        "swarm-tick-twin",
        "tools/sim/tick_twin.py",
        "05f75bd40dd37f4590da6ebab28110d9a4b4094a",
        python_symbols(0.907),
    ),
    (
        "swarm-cave-agent",
        "cave/agents/cave_agent.py",
        "cdf1aba25ba39c373ba4c738e7c6d421fff0cf86",
        python_symbols(0.733),
    ),
)

SOURCE_RECORDS += tuple(
    {
        "id": record_id,
        "category": "swarm-code",
        "path": path,
        "commit": commit,
        "check": check,
        "adaptation": (
            "Restore the full historical Tier 2 or simulation implementation "
            "behind deterministic local inspect, plan, or sandbox defaults. "
            "Effect paths require exact target receipts, reviewed dependency "
            "injection, and authenticated fresh section-13 owner evidence."
        ),
    }
    for record_id, path, commit, check in SWARM_SOURCE_RECORDS
)

SOURCE_RECORDS += (
    {
        "id": "estate-grail-template",
        "category": "estate-page",
        "path": "tools/templates/rapp_estate_grail.html",
        "commit": "7b2390499ee9b238902db1470ccdfae89c1f0cbc",
        "check": marker_set(
            0.210,
            "rapp-estate/1.1",
            "Doors I own",
            "Membership claims",
            "function parseRappid",
            "function historicalUrls",
        ),
        "adaptation": (
            "Restore the estate dashboard, identity, door, membership, and "
            "runway concepts over strictly local supplied data. Network, "
            "navigation, persistence, and mutation edges stay inert."
        ),
    },
    {
        "id": "swarm-readme",
        "category": "historical-document",
        "path": "rapp_swarm/README.md",
        "commit": "669c3f5518d92c989c5770c08e04b84e4c382294",
        "check": normalized_line_coverage(
            1.0,
            "Twin Stack on Azure Functions",
            "## Wire surface",
            "## Why a separate Tier 2?",
        ),
        "adaptation": (
            "Preserve the complete historical Tier 2 README under a current "
            "safety preface that marks every command and cloud/T2T claim as "
            "dated evidence rather than active instructions."
        ),
    },
    {
        "id": "installer-readme",
        "category": "historical-document",
        "path": "installer/README.md",
        "commit": "bbbc7be70decf233c8dd6996a1eaa2c436618229",
        "check": normalized_line_coverage(
            1.0,
            "Stable filenames",
            "Versioned bundles append, not replace",
            "## Scale rule",
        ),
        "adaptation": (
            "Preserve the complete stable installer URL and versioning "
            "contract under a current Grail-boundary preface. Historical "
            "commands remain evidence, while restored launchers default to "
            "effect-free plans."
        ),
    },
    {
        "id": "worker-readme",
        "category": "historical-document",
        "path": "worker/README.md",
        "commit": "74b526fc6010d4edd790bb0f633fd3e270067300",
        "check": normalized_line_coverage(
            1.0,
            "## Endpoints",
            "## Setup (one time, ~3 minutes)",
            "## Why a dedicated worker?",
        ),
        "adaptation": (
            "Keep the complete historical Worker deployment and endpoint "
            "guide beneath the current default-off capability and exact-host "
            "safety contract."
        ),
    },
    {
        "id": "community-agent-library-interface",
        "category": "historical-document",
        "path": "community_rapp/agent-repo-skill.md",
        "commit": "4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6",
        "check": normalized_line_coverage(
            1.0,
            "## Repo Identity",
            "## Agent Format",
            "last_updated: 2026-03-25",
        ),
        "adaptation": (
            "Preserve the complete historical host-side agent library "
            "interface beneath the current migration note. Its download and "
            "installation claims remain historical rather than executable."
        ),
    },
    {
        "id": "cave-public-beacon",
        "category": "structured-history",
        "path": "cave/.well-known/rapp-cave.json",
        "commit": "19ff7d9ff483c0eef258a3b2031da1fd74570854",
        "check": normalized_line_coverage(
            1.0,
            "public-workspace",
            "Public discovery beacon for the RAPP Cave",
        ),
        "adaptation": (
            "Retain the complete historical public beacon as a nested "
            "observation while top-level discovery, bootstrap, distribution, "
            "and acceptance pointers remain disabled."
        ),
    },
)

ARCHIVED_SOURCE_RECORDS = (
    (
        "archive-t2t",
        "historical/source-archive/rapp_brainstem/t2t.py.txt",
        "rapp_brainstem/t2t.py",
        "743f189e6a9b56359b9d65b185b05b759db51b2e",
    ),
    (
        "archive-workspace",
        "historical/source-archive/rapp_brainstem/workspace.py.txt",
        "rapp_brainstem/workspace.py",
        "743f189e6a9b56359b9d65b185b05b759db51b2e",
    ),
    (
        "archive-swarm-server",
        "historical/source-archive/rapp_brainstem/swarm_server.py.txt",
        "rapp_brainstem/swarm_server.py",
        "28ef6641af7c6036e6ae0dfb7fc481075f683744",
    ),
    (
        "archive-chat",
        "historical/source-archive/rapp_brainstem/chat.py.txt",
        "rapp_brainstem/chat.py",
        "b1db594cf477b10f3297980e65307ed989bf82f9",
    ),
    (
        "archive-lifecycle-organ",
        "historical/source-archive/rapp_brainstem/utils/organs/lifecycle_organ.py.txt",
        "rapp_brainstem/utils/organs/lifecycle_organ.py",
        "2692f73b19dcdc856e184044a3f178f5a50c486d",
    ),
    (
        "archive-neighborhood-membership-organ",
        "historical/source-archive/rapp_brainstem/utils/organs/neighborhood_membership_organ.py.txt",
        "rapp_brainstem/utils/organs/neighborhood_membership_organ.py",
        "ab1946036b2a6d594f6799d86f288175cf5fe551",
    ),
    (
        "archive-reserved-agents-init",
        "historical/source-archive/rapp_brainstem/utils/reserved_agents/__init__.py.txt",
        "rapp_brainstem/utils/reserved_agents/__init__.py",
        "2692f73b19dcdc856e184044a3f178f5a50c486d",
    ),
    (
        "archive-upgrade-agent",
        "historical/source-archive/rapp_brainstem/utils/reserved_agents/upgrade_agent.py.txt",
        "rapp_brainstem/utils/reserved_agents/upgrade_agent.py",
        "2692f73b19dcdc856e184044a3f178f5a50c486d",
    ),
)

SOURCE_RECORDS += tuple(
    {
        "id": record_id,
        "category": "inert-source-archive",
        "path": archive_path,
        "source_path": source_path,
        "commit": commit,
        "check": line_subsequence(),
        "adaptation": (
            "Retain the exact removed target-owned source as a non-executable "
            ".txt archive. The original runtime path stays absent, and the "
            "archive is excluded from GitHub Pages publication."
        ),
    }
    for record_id, archive_path, source_path, commit in ARCHIVED_SOURCE_RECORDS
)

ADDITIONAL_PAGE_SOURCES = (
    (
        "page-root-index",
        "entry-page",
        "index.html",
        "32db6f894e4224e2b0b2944b1d6ac1188ec37b61",
        0.93,
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
        0.786,
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
        0.995,
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
        0.999,
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
            "capsule": {
                "encoding": "gzip+base64",
                "payload": base64.b64encode(
                    deterministic_gzip(source)
                ).decode("ascii"),
            },
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
