#!/usr/bin/env python3
"""Regression tests for the dated RAPP/1 documentation closure ledger."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "rapp1-doc-scope.json"
CHECKER_PATH = ROOT / "tools" / "check_rapp1_docs.py"


def load_checker():
    spec = importlib.util.spec_from_file_location("check_rapp1_docs", CHECKER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Rapp1DocumentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        cls.checker = load_checker()

    def test_documentation_gate_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, str(CHECKER_PATH)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("documentation gate passed", result.stdout)

    def test_fresh_verify_rapp_files_ledger_is_exact(self) -> None:
        audit = self.fixture["audit"]
        self.assertEqual(audit["source"], "verify-rapp-files")
        self.assertEqual(audit["report_date"], "2026-07-17")
        self.assertEqual(audit["baseline_tracked_paths"], 640)
        self.assertEqual(audit["post_audit_tracked_paths"], 691)
        tracked = subprocess.check_output(
            ("git", "ls-files"), cwd=ROOT, text=True
        ).splitlines()
        self.assertEqual(len(tracked), audit["post_audit_tracked_paths"])

        exact_counts = {
            "POST-STALE-LIVE-DOC": 60,
            "POST-MARKETING-LEGACY": 19,
            "POST-SHORTCUT-LEGACY": 5,
            "POST-CONTAIN-PLANT": 14,
            "POST-CONTAIN-CAVE": 10,
            "POST-CANON": 11,
            "POST-CANON-05": 3,
            "VOICE-TWIN-WIRE": 9,
        }
        self.assertEqual(set(audit["categories"]), set(exact_counts))
        for name, count in exact_counts.items():
            category = audit["categories"][name]
            paths = category["paths"]
            self.assertEqual(category["expected_count"], count, name)
            self.assertEqual(len(paths), count, name)
            self.assertEqual(len(set(paths)), count, name)
            payload = "".join(f"{path}\n" for path in sorted(paths))
            self.assertEqual(
                hashlib.sha256(payload.encode()).hexdigest(),
                category["path_set_sha256"],
                name,
            )

    def test_every_post_path_has_one_disposition(self) -> None:
        disposition = {}
        for classification, paths in self.fixture["classifications"].items():
            for path in paths:
                self.assertNotIn(path, disposition, path)
                disposition[path] = classification

        for category in self.fixture["audit"]["categories"].values():
            for path in category["paths"]:
                self.assertIn(path, disposition)
                self.assertTrue((ROOT / path).is_file(), path)

    def test_stale_live_path_cannot_escape_fixture(self) -> None:
        fixture = copy.deepcopy(self.fixture)
        escaped = fixture["audit"]["categories"]["POST-STALE-LIVE-DOC"]["paths"][0]
        for paths in fixture["classifications"].values():
            if escaped in paths:
                paths.remove(escaped)
        errors = self.checker._validate_fixture(fixture)
        self.assertTrue(
            any(escaped in error and "no disposition" in error for error in errors),
            errors,
        )

    def test_category_count_and_digest_are_fail_closed(self) -> None:
        fixture = copy.deepcopy(self.fixture)
        category = fixture["audit"]["categories"]["POST-MARKETING-LEGACY"]
        category["paths"] = category["paths"][:-1]
        errors = self.checker._validate_fixture(fixture)
        self.assertTrue(any("exactly 19" in error for error in errors), errors)
        self.assertTrue(any("path digest mismatch" in error for error in errors), errors)

    def test_historical_body_cannot_lose_bounded_marker(self) -> None:
        path = "BRAINSTEM_MANDATE.md"
        text = (ROOT / path).read_text(encoding="utf-8")
        start = self.fixture["required_markers"]["historical_start"]
        mutated = text.replace(start, "", 1)
        with mock.patch.object(self.checker, "_read", return_value=mutated):
            errors = self.checker._validate_document(
                path, "historical", self.fixture
            )
        self.assertTrue(any("bounded markers" in error for error in errors), errors)

    def test_legacy_frame_marker_is_not_current_guidance(self) -> None:
        legacy_form = "rapp-frame/1.0"
        for path in self.fixture["classifications"]["current"]:
            active, marker_errors = self.checker._active_text(path, self.fixture)
            self.assertFalse(marker_errors, path)
            self.assertNotIn(legacy_form, active, path)

    def _category_mutation_errors(self, path: str, mutated: str) -> list[str]:
        real_read = self.checker._read

        def read_with_mutation(relative_path: str) -> str:
            if relative_path == path:
                return mutated
            return real_read(relative_path)

        with mock.patch.object(
            self.checker, "_read", side_effect=read_with_mutation
        ):
            return self.checker._validate_post_categories(self.fixture)

    def test_live_plant_cta_mutation_is_rejected(self) -> None:
        path = "README.md"
        text = (ROOT / path).read_text(encoding="utf-8")
        mutated = (
            "[Install now](https://raw.githubusercontent.com/example/RAPP/plant.sh)\n"
            + text
        )
        errors = self._category_mutation_errors(path, mutated)
        self.assertTrue(any(path in error and "plant.sh CTA" in error for error in errors))

    def test_shortcut_extra_member_mutation_is_rejected(self) -> None:
        path = "installer/shortcuts/README.md"
        text = (ROOT / path).read_text(encoding="utf-8")
        mutated = text + "\nThe server returns `voice_response` as an extra payload.\n"
        errors = self._category_mutation_errors(path, mutated)
        self.assertTrue(
            any(path in error and "voice_response" in error for error in errors),
            errors,
        )

    def test_active_moving_main_authority_mutation_is_rejected(self) -> None:
        path = "README.md"
        text = (ROOT / path).read_text(encoding="utf-8")
        mutated = "Track main as the canonical authority.\n" + text
        errors = self._category_mutation_errors(path, mutated)
        self.assertTrue(
            any(path in error and "active canon text" in error for error in errors),
            errors,
        )

    def test_tutorial_navigation_mutation_is_rejected(self) -> None:
        path = "pages/_site/index.json"
        text = (ROOT / path).read_text(encoding="utf-8")
        mutated = text + '\n"pages/tutorials/hatch-egg.html"\n'
        errors = self._category_mutation_errors(path, mutated)
        self.assertTrue(
            any(path in error and "advertises retired hatch-egg" in error for error in errors),
            errors,
        )

    def test_voice_twin_extra_field_mutation_is_rejected(self) -> None:
        path = "pages/docs/ROADMAP.md"
        text = (ROOT / path).read_text(encoding="utf-8")
        mutated = "The façade returns `voice_response` for speech.\n" + text
        errors = self._category_mutation_errors(path, mutated)
        self.assertTrue(
            any(path in error and "extra Voice/Twin wire field" in error for error in errors),
            errors,
        )

    def test_immutable_and_generated_boundaries_are_not_owned(self) -> None:
        all_paths = {
            path
            for category in self.fixture["audit"]["categories"].values()
            for path in category["paths"]
        }
        immutable_prefix = "cave/rapplications/rapp-installer/"
        self.assertFalse(any(path.startswith(immutable_prefix) for path in all_paths))
        self.assertNotIn("ecosystem.json", all_paths)
        self.assertNotIn("pages/about/ecosystem.html", all_paths)
        self.assertNotIn("index.html", all_paths)
        self.assertNotIn("pages/index.html", all_paths)

    def test_status_retains_both_dated_inventories(self) -> None:
        status = (ROOT / "RAPP1_STATUS.md").read_text(encoding="utf-8")
        self.assertIn("2026-07-16 baseline: 640/640 tracked paths", status)
        self.assertRegex(status, r"(?s)2026-07-17.{0,100}691/691 tracked\s+paths")
        for category in (
            "Authenticated owner action",
            "Generated target artifacts",
            "Immutable history",
            "External mirrors",
        ):
            self.assertIn(category, status)


if __name__ == "__main__":
    unittest.main()
