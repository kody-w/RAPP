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
