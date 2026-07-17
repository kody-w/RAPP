import copy
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = ROOT / "tools/check_rapp1_docs.py"
SPEC = importlib.util.spec_from_file_location("check_rapp1_docs", GATE_PATH)
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


class Rapp1DocumentationTests(unittest.TestCase):
    def test_explicit_documentation_scope_passes(self):
        self.assertEqual(GATE.check_docs(), [])

    def test_scope_uses_target_owned_authority(self):
        scope = GATE.load_scope()
        self.assertEqual(scope["schema"], "rapp1-documentation-scope/1.0")
        self.assertEqual(scope["authority"], "RAPP1_AUTHORITY.json")
        self.assertEqual(scope["status"], "RAPP1_STATUS.md")
        self.assertIn("pages/vbrainstem.html", scope["excluded_documents"])
        self.assertIn("specs/ecosystem-spec.json", scope["excluded_documents"])
        ledger = scope["audit_scope"]["r1_doc_01"]
        self.assertEqual(ledger["path_count"], 56)
        self.assertEqual(len(ledger["paths"]), 56)
        self.assertEqual(
            ledger["sha256"],
            "9ac01e164dc0eb820d5f53afed82f53c501059c18a8bf66b8b23c533af728ce7",
        )
        self.assertEqual(
            scope["audit_scope"]["canon_mirrors"]["sha256"],
            "188eef4a3d2f65b93a4e0832515e8fe8b7b8826e1163b683029ab1d14bc51f59",
        )
        self.assertEqual(
            scope["audit_scope"]["canon_mirrors"]["live_path_count"], 45
        )

    def test_every_audit_ledger_path_is_classified(self):
        scope = GATE.load_scope()
        ledger_paths = set(scope["audit_scope"]["r1_doc_01"]["paths"])
        checked_paths = set().union(
            *(
                set(scope[group])
                for group in (
                    "current_documents",
                    "superseded_documents",
                    "historical_documents",
                )
            )
        )
        excluded_paths = set(scope["excluded_documents"])
        self.assertEqual(ledger_paths - checked_paths - excluded_paths, set())
        self.assertEqual(len(ledger_paths & checked_paths), 44)
        self.assertEqual(len(ledger_paths & excluded_paths), 12)
        canon_paths = set(scope["audit_scope"]["canon_mirrors"]["live_paths"])
        self.assertEqual(canon_paths - checked_paths - excluded_paths, set())
        self.assertEqual(len(canon_paths & checked_paths), 33)
        self.assertEqual(len(canon_paths & excluded_paths), 12)

    def test_unclassified_audit_path_is_rejected(self):
        scope = copy.deepcopy(GATE.load_scope())
        scope["excluded_documents"].pop("cave/rappid.json")
        failures = GATE.check_docs(scope)
        self.assertIn(
            "scope: R1-DOC-01 path cave/rappid.json is not checked or excluded",
            failures,
        )

    def test_explicit_historical_section_is_bounded(self):
        text = "\n".join(
            (
                GATE.HISTORICAL_SECTION_START,
                "legacy example: rapp-frame/1.0",
                GATE.HISTORICAL_SECTION_END,
                "current section",
                "one",
                "two",
                "three",
                "four",
                "five",
                "six",
                "current claim: rapp-frame/1.0",
            )
        )
        failures = GATE.retired_token_failures("example.md", text)
        self.assertEqual(len(failures), 1)
        self.assertIn("example.md:11", failures[0])

    def test_unclosed_historical_section_is_rejected(self):
        failures = GATE.historical_marker_failures(
            "example.md", GATE.HISTORICAL_SECTION_START
        )
        self.assertEqual(
            failures, ["example.md: historical section has no end marker"]
        )


if __name__ == "__main__":
    unittest.main()
