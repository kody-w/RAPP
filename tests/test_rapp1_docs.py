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

    def test_fresh_post_ledger_is_exact_and_distinct_from_baseline(self) -> None:
        audit = self.fixture["audit"]
        self.assertEqual(audit["source"], "verify-rapp-files-final-post-ledger")
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
            "POST-CONTAIN-PLANT": 7,
            "POST-CONTAIN-CAVE": 20,
            "POST-MIRROR": 23,
            "POST-OWNER-MIRROR": 4,
            "POST-IMMUTABLE-PIN": 17,
            "POST-IMMUTABLE-ARTIFACT": 6,
            "POST-STATUS-01": 2,
            "POST-QA-DOC": 3,
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
        self.assertNotIn("POST-CANON", audit["categories"])
        self.assertNotIn("POST-CANON-05", audit["categories"])

    def test_final_verify_report_provenance_is_exact(self) -> None:
        report = self.fixture["audit"]["provenance"]["final_report"]
        self.assertEqual(report["source"], "verify-rapp-files")
        self.assertEqual(
            report["report_sha256"],
            "f5ba5abbf21067dd644d70f9076201b7ca3bf8afd934edbb9f2b4614060ad50b",
        )
        self.assertEqual(report["tracked_path_count"], 691)
        self.assertEqual(report["data_rows"], 691)
        self.assertEqual(report["report_bytes"], 117017)
        self.assertEqual(report["tracked_bytes"], 8298082)
        self.assertEqual(report["recursive_archive_members"], 450)
        self.assertEqual(report["absent_ids"], ["POST-CANON", "POST-CANON-05"])

    def test_existing_verify_report_provenance_is_exact(self) -> None:
        report = self.fixture["audit"]["provenance"]["existing_report"]
        self.assertEqual(report["source"], "verify-rapp-files")
        self.assertEqual(
            report["report_sha256"],
            "9ac01e164dc0eb820d5f53afed82f53c501059c18a8bf66b8b23c533af728ce7",
        )
        self.assertEqual(
            report["canon_report_sha256"],
            "188eef4a3d2f65b93a4e0832515e8fe8b7b8826e1163b683029ab1d14bc51f59",
        )
        self.assertEqual(
            report["scope_commit"], "f71810db3259fea533b4112c1df300d4b0dc781c"
        )
        self.assertEqual(report["tracked_path_count"], 640)
        self.assertIn("not rerun", report["scope_note"])
        self.assertNotIn("report_path", report)

        r1_doc = report["R1-DOC-01"]
        current = r1_doc["current_live_paths"]
        mirrors = r1_doc["mirror_paths"]
        self.assertEqual((len(current), len(mirrors)), (53, 3))
        self.assertEqual(len(set(current + mirrors)), 56)
        for field, paths in (
            ("current_live_path_set_sha256", current),
            ("mirror_path_set_sha256", mirrors),
            ("path_set_sha256", current + mirrors),
        ):
            payload = "".join(f"{path}\n" for path in sorted(paths))
            self.assertEqual(
                r1_doc[field], hashlib.sha256(payload.encode()).hexdigest()
            )

    def test_every_actionable_post_path_has_one_disposition_or_owner(self) -> None:
        disposition = {}
        for classification, paths in self.fixture["classifications"].items():
            for path in paths:
                self.assertNotIn(path, disposition, path)
                disposition[path] = classification

        actionable = (
            "POST-STALE-LIVE-DOC",
            "POST-MARKETING-LEGACY",
            "POST-SHORTCUT-LEGACY",
            "POST-CONTAIN-PLANT",
            "POST-CONTAIN-CAVE",
        )
        ownership = self.fixture["ownership_exclusions"]
        for name, category in self.fixture["audit"]["categories"].items():
            for path in category["paths"]:
                self.assertTrue((ROOT / path).is_file(), path)
                if name in actionable:
                    self.assertTrue(
                        path in disposition or path in ownership,
                        f"{name}: {path}",
                    )

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

    def test_new_tracked_document_cannot_escape_derived_scope(self) -> None:
        tracked = subprocess.check_output(
            ("git", "ls-files"), cwd=ROOT, text=True
        ).splitlines()
        tracked.append("pages/docs/new-current-guide.md")
        classified = {
            path
            for paths in self.fixture["classifications"].values()
            for path in paths
        }
        errors = self.checker._validate_derived_document_scope(
            self.fixture, tracked, classified
        )
        self.assertTrue(
            any(
                "pages/docs/new-current-guide.md" in error
                and "no disposition" in error
                for error in errors
            ),
            errors,
        )

    def test_blanket_vault_exclusion_is_rejected(self) -> None:
        fixture = copy.deepcopy(self.fixture)
        fixture["derived_document_scope"]["excluded_prefixes"][
            "pages/vault/"
        ] = "blanket history"
        errors = self.checker._validate_fixture(fixture)
        self.assertTrue(
            any("prefix exclusions drifted" in error for error in errors), errors
        )

    def test_derived_exclusion_requires_justification(self) -> None:
        fixture = copy.deepcopy(self.fixture)
        fixture["derived_document_scope"]["excluded_paths"]["404.html"] = ""
        errors = self.checker._validate_fixture(fixture)
        self.assertTrue(
            any("404.html" in error and "no justification" in error for error in errors),
            errors,
        )

    def test_original_r1_doc_path_cannot_escape_fixture(self) -> None:
        fixture = copy.deepcopy(self.fixture)
        original = fixture["audit"]["provenance"]["existing_report"]["R1-DOC-01"]
        escaped = "CONSTITUTION.md"
        self.assertIn(escaped, original["current_live_paths"])
        for paths in fixture["classifications"].values():
            if escaped in paths:
                paths.remove(escaped)
        errors = self.checker._validate_fixture(fixture)
        self.assertTrue(
            any(
                escaped in error and "original R1-DOC-01" in error
                for error in errors
            ),
            errors,
        )

    def test_superseding_boundaries_remain_excluded(self) -> None:
        report = self.fixture["audit"]["provenance"]["existing_report"]
        excluded = set(self.fixture["classifications"]["excluded"])
        boundaries = report["superseding_boundaries"]
        self.assertLessEqual(set(boundaries["generated"]), excluded)
        self.assertLessEqual(set(boundaries["immutable_prepared_clone"]), excluded)

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
        path = "installer/plant.html"
        text = (ROOT / path).read_text(encoding="utf-8")
        mutated = (
            "[Install now](https://raw.githubusercontent.com/example/RAPP/plant.sh)\n"
            + text
        )
        errors = self._category_mutation_errors(path, mutated)
        self.assertTrue(any(path in error and "plant.sh CTA" in error for error in errors))

    def test_executable_planting_script_mutation_is_rejected(self) -> None:
        path = "installer/plant.html"
        text = (ROOT / path).read_text(encoding="utf-8")
        mutated = text.replace(
            '<script type="application/rapp-history">', "<script>", 1
        )
        errors = self._category_mutation_errors(path, mutated)
        self.assertTrue(
            any(path in error and "script remains executable" in error for error in errors),
            errors,
        )

    def test_live_cave_bootstrap_mutation_is_rejected(self) -> None:
        path = "cave/.well-known/rapp-cave.json"
        value = json.loads((ROOT / path).read_text(encoding="utf-8"))
        value["bootstrap"] = "curl https://example.invalid/bootstrap.sh | bash"
        errors = self._category_mutation_errors(path, json.dumps(value))
        self.assertTrue(
            any(path in error and "'bootstrap' drifted" in error for error in errors),
            errors,
        )

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

    def test_immutable_generated_and_owned_boundaries_are_unmodified(self) -> None:
        categories = self.fixture["audit"]["categories"]
        protected = set(self.fixture["ownership_exclusions"])
        for name in (
            "POST-MIRROR",
            "POST-IMMUTABLE-PIN",
            "POST-IMMUTABLE-ARTIFACT",
        ):
            protected.update(categories[name]["paths"])
        changed = set(
            subprocess.check_output(
                ("git", "diff", "--name-only", "HEAD", "--"), cwd=ROOT, text=True
            ).splitlines()
        )
        self.assertFalse(changed & protected, sorted(changed & protected))
        self.assertEqual(
            set(categories["POST-OWNER-MIRROR"]["paths"]),
            {
                "pages/about/ecosystem.html",
                "pages/about/ecosystem.json",
                "specs/ECOSYSTEM_SPEC.md",
                "specs/ecosystem-spec.json",
            },
        )

    def test_status_retains_both_dated_inventories(self) -> None:
        status = (ROOT / "RAPP1_STATUS.md").read_text(encoding="utf-8")
        self.assertIn("2026-07-16 baseline: 640/640 tracked paths", status)
        self.assertRegex(status, r"(?s)2026-07-17.{0,100}691/691 tracked\s+paths")
        self.assertIn("8,298,082 tracked bytes", status)
        self.assertIn("450 recursively counted archive", status)
        self.assertIn(
            "f5ba5abbf21067dd644d70f9076201b7ca3bf8afd934edbb9f2b4614060ad50b",
            status,
        )
        for category in (
            "Authenticated owner action",
            "Generated target artifacts",
            "Immutable history",
            "External mirrors",
        ):
            self.assertIn(category, status)


if __name__ == "__main__":
    unittest.main()
