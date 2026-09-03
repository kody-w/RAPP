#!/usr/bin/env python3
"""Focused tests for Cave data retention and safe catalog defaults."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
CAVE = ROOT / "cave"
RAR_PATH = CAVE / "rar/index.json"
SUPER_RAR_PATH = CAVE / "super-rar/index.json"
CATALOG_PATHS = (
    RAR_PATH,
    SUPER_RAR_PATH,
    CAVE / "cubbies/index.json",
    CAVE / "facets.json",
)
PINNED_COMMIT = "0123456789abcdef0123456789abcdef01234567"


def _load_module(name: str, path: Path):
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class CaveCatalogRetentionTests(unittest.TestCase):
    def test_historical_entries_and_context_are_retained(self) -> None:
        rar = _read_json(RAR_PATH)
        self.assertEqual(
            {entry["name"] for entry in rar["agents"]},
            {
                "@kody-w/cave",
                "@rapp/rar_steward",
                "@kody-w/rapp_installer",
            },
        )
        missing_agent = next(
            entry
            for entry in rar["agents"]
            if entry["name"] == "@kody-w/rapp_installer"
        )
        self.assertEqual(
            missing_agent["path"],
            "cubbies/kody-w/agents/rapp_installer_agent.py",
        )
        self.assertEqual(
            missing_agent["sha256"],
            "acdccb947f9001bcff4f3e1b8bf84bb6b831522a2c7df0d6cffa3cbdae5bfc80",
        )
        self.assertEqual(missing_agent["version"], "0.6.1-cubby")
        self.assertIn(
            "repo-independent RAPP Installer",
            missing_agent["purpose"],
        )
        self.assertEqual(
            missing_agent["kernel_pin"]["tag"],
            "brainstem-v0.6.9",
        )
        original_agent = missing_agent["historical_metadata"][0]
        self.assertEqual(original_agent["version"], "0.6.1-cubby")
        self.assertEqual(
            original_agent["sha256"],
            "acdccb947f9001bcff4f3e1b8bf84bb6b831522a2c7df0d6cffa3cbdae5bfc80",
        )
        self.assertIn("repo-independent RAPP Installer", original_agent["purpose"])
        self.assertTrue(original_agent["observed_streamable"])
        self.assertFalse(original_agent["accepted"])

        super_rar = _read_json(SUPER_RAR_PATH)
        self.assertEqual(super_rar["count"], 2)
        self.assertEqual(
            {entry["name"] for entry in super_rar["entries"]},
            {"rapp_installer_agent.py", "cubby-rapp-installer.egg"},
        )

        cubbies = _read_json(CAVE / "cubbies/index.json")
        self.assertEqual(len(cubbies["cubbies"]), 1)
        self.assertEqual(cubbies["cubbies"][0]["github_login"], "kody-w")
        self.assertIn(
            "egged & self-bootstrapping",
            cubbies["cubbies"][0]["what_im_cooking"],
        )

        facets = _read_json(CAVE / "facets.json")
        self.assertEqual(
            {facet["name"] for facet in facets["public_facets"]},
            {
                "neighborhood_purpose",
                "join_path",
                "cubby_roster",
                "shared_agents",
                "show_and_tell",
                "cubby_contents",
            },
        )
        shared = next(
            facet
            for facet in facets["public_facets"]
            if facet["name"] == "shared_agents"
        )
        self.assertIn("sha256-pinned", shared["description"])

        seed = _read_json(ROOT / ".well-known/rapp-network-seed.json")
        self.assertEqual(len(seed["operators"]), 1)
        operator = seed["operators"][0]
        self.assertEqual(operator["github"], "kody-w")
        self.assertEqual(operator["role"], "species-root-operator")
        self.assertIn("rapp-estate/main/estate.json", operator["estate_url"])
        self.assertIn("federation_hints[]", seed["how_to_add_yourself"])

    def test_verification_acceptance_and_distribution_are_separate(self) -> None:
        rar = _read_json(RAR_PATH)
        super_rar = _read_json(SUPER_RAR_PATH)
        for document in (rar, super_rar):
            self.assertTrue(document["verified"])
            self.assertIs(document["accepted"], False)
            self.assertIs(document["active_distribution"], False)
            self.assertIs(document["streamable"], False)
            for action in ("fetch", "install", "execute", "stream", "publish"):
                self.assertIs(document["distribution"][action], False)
            self.assertNotIn("/main/", document["raw_url_prefix"])
            self.assertIn("{commit}", document["raw_url_prefix"])
            self.assertIs(
                document["source_policy"]["moving_refs_accepted"],
                False,
            )
            self.assertTrue(
                document["source_policy"]["sha256_required_for_files"]
            )

        entries = [*rar["agents"], *rar["rapps"], *super_rar["entries"]]
        for entry in entries:
            self.assertIn("verified", entry)
            self.assertIs(entry["accepted"], False)
            self.assertEqual(
                entry["acceptance"]["state"],
                "not-accepted",
            )
            for action in ("fetch", "install", "execute", "stream", "publish"):
                self.assertIs(entry["distribution"][action], False)

        present_file = next(
            entry
            for entry in rar["agents"]
            if entry["name"] == "@rapp/rar_steward"
        )
        self.assertTrue(present_file["verified"])
        self.assertTrue(present_file["source"]["present"])
        self.assertEqual(
            present_file["sha256"],
            hashlib.sha256(
                (CAVE / present_file["path"]).read_bytes()
            ).hexdigest(),
        )

        absent_file = next(
            entry
            for entry in rar["agents"]
            if entry["name"] == "@kody-w/rapp_installer"
        )
        self.assertFalse(absent_file["verified"])
        self.assertFalse(absent_file["source"]["present"])
        self.assertEqual(
            absent_file["verification"]["state"],
            "unverified-historical-bytes-absent",
        )
        self.assertEqual(
            absent_file["verification"]["historical_sha256"],
            "acdccb947f9001bcff4f3e1b8bf84bb6b831522a2c7df0d6cffa3cbdae5bfc80",
        )

        installer = rar["rapps"][0]
        self.assertEqual(installer["kernel_pin"]["record"], "KERNEL_PIN.json")
        self.assertEqual(
            installer["kernel_pin"]["grail"],
            "kody-w/rapp-installer",
        )
        self.assertEqual(
            installer["kernel_pin"]["tag"],
            "brainstem-v0.6.9",
        )
        self.assertIs(installer["active_distribution"], False)
        original_rapp = installer["historical_metadata"][0]
        self.assertEqual(original_rapp["version"], "0.6.1")
        self.assertIn("full installer parity", original_rapp["purpose"])
        self.assertFalse(original_rapp["accepted"])

    def test_network_seed_is_observation_not_membership_or_trust(self) -> None:
        seed = _read_json(ROOT / ".well-known/rapp-network-seed.json")
        self.assertEqual(seed["status"], "observation-only")
        self.assertIs(seed["verified"], False)
        self.assertIs(seed["accepted"], False)
        self.assertIs(seed["authoritative"], False)
        self.assertIs(seed["discovery_enabled"], False)
        self.assertIs(seed["joining_enabled"], False)
        self.assertIs(seed["source_policy"]["network_fetch_default"], False)
        self.assertIs(seed["source_policy"]["moving_refs_accepted"], False)
        operator = seed["operators"][0]
        self.assertEqual(operator["membership"], "not-established")
        self.assertEqual(operator["trust"], "not-established")
        self.assertIs(
            operator["reference_state"]["usable_for_acceptance"],
            False,
        )
        self.assertEqual(seed["submission_effect"].split(".")[0], (
            "A PR or federation hint is a reviewable observation draft only"
        ))


class RarStewardSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.path = CAVE / "agents/rar_steward_agent.py"
        cls.module = _load_module("adapted_rar_steward", cls.path)

    def test_substantive_analysis_is_restored(self) -> None:
        source = self.path.read_text(encoding="utf-8")
        for marker in (
            "def _clusters",
            "def _junk",
            "def _file_issues",
            "health_score",
            "recommended_base",
            "existing_fingerprints",
        ):
            self.assertIn(marker, source)
        self.assertNotIn("Fail-closed tombstone for the retired Cave RAR", source)
        self.assertNotIn("import subprocess", source)
        self.assertNotIn('"gh", "issue"', source)

    def test_default_source_is_local_and_network_free(self) -> None:
        agent = self.module.RarStewardAgent()
        with mock.patch.object(
            self.module,
            "_fetch_bytes",
            side_effect=AssertionError("default must not use network"),
        ):
            result = json.loads(agent.perform(action="health"))
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["mode"], "read-only")
        self.assertFalse(result["writes_performed"])
        self.assertFalse(result["accepted"])
        self.assertEqual(result["source"]["kind"], "local")
        self.assertEqual(result["source"]["path"], "cave/rar/index.json")
        self.assertEqual(result["total_agents"], 3)

    def test_legacy_file_issues_action_is_plan_only(self) -> None:
        result = json.loads(
            self.module.RarStewardAgent().perform(
                action="file_issues",
                scope="junk",
                confirm=True,
                tracker="example/repository",
            )
        )
        self.assertEqual(result["status"], "planned")
        self.assertGreater(result["candidates"], 0)
        plan = result["result"]
        self.assertTrue(plan["legacy_confirm_requested"])
        self.assertFalse(plan["write_authorized"])
        self.assertFalse(plan["write_performed"])
        self.assertGreater(len(plan["planned"]), 0)
        self.assertTrue(
            all(item["would_file"] is False for item in plan["planned"])
        )

    def test_network_sources_require_checksum_and_immutable_ref(self) -> None:
        moving = json.loads(
            self.module.RarStewardAgent().perform(
                action="health",
                catalog_url=(
                    "https://raw.githubusercontent.com/kody-w/RAR/"
                    "main/api/v1/index.json"
                ),
                catalog_sha256="0" * 64,
            )
        )
        self.assertEqual(moving["status"], "error")
        self.assertIn("moving refs", moving["error"])

        raw = RAR_PATH.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        pinned_url = (
            "https://raw.githubusercontent.com/kody-w/RAR/"
            f"{PINNED_COMMIT}/api/v1/index.json"
        )
        with mock.patch.object(
            self.module,
            "_fetch_bytes",
            return_value=raw,
        ) as fetch:
            pinned = json.loads(
                self.module.RarStewardAgent().perform(
                    action="health",
                    catalog_url=pinned_url,
                    catalog_ref=PINNED_COMMIT,
                    catalog_sha256=digest,
                )
            )
        fetch.assert_called_once_with(pinned_url)
        self.assertEqual(pinned["status"], "success")
        self.assertEqual(pinned["source"]["kind"], "network")
        self.assertTrue(pinned["source"]["checksum_verified"])
        self.assertFalse(pinned["source"]["accepted"])


class BuilderSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.path = CAVE / "tools/build_super_rar.py"
        cls.module = _load_module("adapted_super_rar_builder", cls.path)

    def test_builder_restores_discovery_and_preserves_missing_entries(self) -> None:
        rar = self.module.render_rar()
        super_rar = self.module.render_super_rar()
        self.assertEqual(
            {entry["name"] for entry in rar["agents"]},
            {
                "@kody-w/cave",
                "@rapp/rar_steward",
                "@kody-w/rapp_installer",
            },
        )
        retained = next(
            entry
            for entry in rar["agents"]
            if entry["name"] == "@kody-w/rapp_installer"
        )
        self.assertFalse(retained["source"]["present"])
        self.assertFalse(retained["verified"])
        self.assertEqual(super_rar["count"], 2)
        self.assertEqual(super_rar["by_kind"], {"agent": 1, "egg": 1})

    def test_default_check_plan_and_render_never_write(self) -> None:
        before = {path: path.read_bytes() for path in CATALOG_PATHS}
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        commands = (
            (sys.executable, "cave/tools/build_super_rar.py"),
            (sys.executable, "cave/tools/build_super_rar.py", "--check"),
            (sys.executable, "cave/tools/build_super_rar.py", "--plan"),
            (
                sys.executable,
                "cave/tools/build_super_rar.py",
                "--render",
                "all",
            ),
        )
        for command in commands:
            result = subprocess.run(
                command,
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(
                result.returncode,
                0,
                result.stdout + result.stderr,
            )
            self.assertEqual(
                before,
                {path: path.read_bytes() for path in CATALOG_PATHS},
            )

        refused = subprocess.run(
            (
                sys.executable,
                "cave/tools/build_super_rar.py",
                "--write",
            ),
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(refused.returncode, 2)
        self.assertIn("unrecognized arguments: --write", refused.stderr)
        self.assertEqual(
            before,
            {path: path.read_bytes() for path in CATALOG_PATHS},
        )

    def test_builder_source_contains_no_catalog_write_path(self) -> None:
        source = self.path.read_text(encoding="utf-8")
        for marker in (
            "write_text(",
            "write_bytes(",
            "json.dump(",
            'open(path, "w")',
            "subprocess",
        ):
            self.assertNotIn(marker, source)
        self.assertIn("build_super_rar", source)
        self.assertIn("render_super_rar", source)
        self.assertIn("render_rar", source)


class IntakePromptAndDiscoveryTests(unittest.TestCase):
    def test_place_form_retains_useful_fields_and_is_draft_only(self) -> None:
        form = (
            ROOT / ".github/ISSUE_TEMPLATE/place-submission.yml"
        ).read_text(encoding="utf-8")
        ids = set(re.findall(r"(?m)^\s+id:\s+([a-z_]+)\s*$", form))
        self.assertEqual(
            ids,
            {
                "place_name",
                "display_name",
                "slug",
                "location",
                "coordinates",
                "description",
                "photo_url",
                "submitter",
                "eligibility",
                "draft_acknowledgement",
            },
        )
        self.assertIn("Review draft only", form)
        self.assertIn("ordinary GitHub issue draft", form)
        self.assertIn("causes no planting", form)
        self.assertNotIn("installer/seed.html", form)

    def test_prompts_retain_guidance_and_route_to_current_pin(self) -> None:
        write_prompt = (
            ROOT / ".github/prompts/write-agent.prompt.md"
        ).read_text(encoding="utf-8")
        test_prompt = (
            ROOT / ".github/prompts/test-agent.prompt.md"
        ).read_text(encoding="utf-8")
        for prompt in (write_prompt, test_prompt):
            self.assertIn("KERNEL_PIN.json", prompt)
            self.assertIn(
                "kody-w/rapp-installer@brainstem-v0.6.9",
                prompt,
            )
            self.assertIn("safe adapter", prompt.lower())
            self.assertIn("tests/run_rapp1_conformance.py", prompt)
        self.assertIn("self.metadata", write_prompt)
        self.assertIn("perform(**kwargs) -> str", write_prompt)
        self.assertIn("data_slush", write_prompt)
        self.assertIn("Do not auto-install", write_prompt)
        self.assertIn("data exhaust", test_prompt)

    def test_machine_discovery_restores_observations_without_acceptance(self) -> None:
        discovery = _read_json(ROOT / "rapp-ai.json")
        self.assertEqual(
            discovery["kernel_pin"]["tag"],
            "brainstem-v0.6.9",
        )
        relations = {entry["rel"] for entry in discovery["entrypoints"]}
        self.assertTrue(
            {
                "cave-rar-observation",
                "cave-super-rar-observation",
                "network-seed-observation",
                "agent-registry",
                "agent-registry-interface",
                "project-continuity",
            }.issubset(relations)
        )
        policy = discovery["catalog_observation_policy"]
        self.assertEqual(
            policy["default_mode"],
            "read-only-analyze-check-plan",
        )
        self.assertIs(policy["moving_refs_accepted"], False)
        self.assertIs(policy["write"], False)
        self.assertIs(policy["install"], False)
        self.assertIs(policy["stream"], False)
        rar_candidate = next(
            candidate
            for candidate in discovery["external_candidates"]
            if candidate["id"] == "rar"
        )
        self.assertTrue(rar_candidate["moving_catalog_entrypoints_exposed"])
        self.assertFalse(rar_candidate["moving_catalog_entrypoints_accepted"])

    def test_workflow_has_read_only_permissions(self) -> None:
        workflow = (
            ROOT / ".github/workflows/cave-super-rar.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertIn(
            "python3 cave/tools/build_super_rar.py --check",
            workflow,
        )
        self.assertIn(
            "python3 cave/tests/test_catalog_containment.py",
            workflow,
        )
        self.assertNotIn("upload-artifact", workflow)
        self.assertNotIn("contents: write", workflow)


if __name__ == "__main__":
    unittest.main()
