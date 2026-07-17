import hashlib
import json
import re
import subprocess
import unittest
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_PATH = ROOT / "RAPP1_AUTHORITY.json"
FIXTURE_PATH = ROOT / "tests/fixtures/rapp1-spec-rev5.json"

EXPECTED_STANDARD = {
    "repository": "kody-w/rapp-1",
    "commit": "6723c7add2aed36bb68992fc71a56b0a4bd5ad81",
    "path": "SPEC.md",
    "sha256": "6d06daba65d7c045716f3d6e95db8401ab58e727820e4114466d847f62cae49b",
    "byte_length": 41880,
    "wire_tag": "rapp/1",
    "revision": "rev-5",
    "canonical_url": (
        "https://github.com/kody-w/rapp-1/blob/"
        "6723c7add2aed36bb68992fc71a56b0a4bd5ad81/SPEC.md"
    ),
    "retrieval_url": (
        "https://raw.githubusercontent.com/kody-w/rapp-1/"
        "6723c7add2aed36bb68992fc71a56b0a4bd5ad81/SPEC.md"
    ),
}

EXPECTED_GRAIL = {
    "rapp_brainstem/brainstem.py": (
        "a293dd9f11eef915bf15776f08c736faa60cb749820871b6753ea98233142a71"
    ),
    "rapp_brainstem/agents/basic_agent.py": (
        "701488bc00d536a7b23295e7da99c62f24e9b00f233daa325886430c736b78eb"
    ),
    "rapp_brainstem/VERSION": (
        "13eb74b44be6e3a85a0efa0dedf56aec05e9e50140e1c8bbc0d0fbd8097b0717"
    ),
}


def load_json(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Rapp1AuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.authority = load_json(AUTHORITY_PATH)
        cls.fixture = load_json(FIXTURE_PATH)

    def test_authority_shape_and_exact_source_pin(self):
        self.assertEqual(
            set(self.authority),
            {
                "schema",
                "record_kind",
                "target",
                "standard",
                "offline_verification",
                "authenticated_registry",
                "immutable_grail_boundary",
            },
        )
        self.assertEqual(self.authority["schema"], "rapp-authority-pin/1.0")
        self.assertEqual(
            self.authority["record_kind"], "structural-authority-pin"
        )
        self.assertEqual(self.authority["standard"], EXPECTED_STANDARD)
        self.assertRegex(
            self.authority["standard"]["commit"], r"^[0-9a-f]{40}$"
        )
        self.assertRegex(
            self.authority["standard"]["sha256"], r"^[0-9a-f]{64}$"
        )

    def test_staged_fixture_matches_without_vendoring_spec_bytes(self):
        fixture_source = dict(self.fixture["source"])
        self.assertEqual(fixture_source.pop("line_count"), 528)
        self.assertEqual(fixture_source, EXPECTED_STANDARD)
        self.assertEqual(
            self.fixture["schema"], "rapp-authority-source-fixture/1.0"
        )
        self.assertFalse(self.fixture["contains_spec_bytes"])
        self.assertIsNone(self.fixture["source_license_path"])

        offline = self.authority["offline_verification"]
        fixture = PurePosixPath(offline["fixture"])
        self.assertFalse(fixture.is_absolute())
        self.assertNotIn("..", fixture.parts)
        self.assertEqual(ROOT / fixture, FIXTURE_PATH)
        self.assertEqual(offline["strategy"], "metadata-fixture")
        self.assertFalse(offline["vendored_spec_bytes"])

    def test_pin_is_explicitly_not_an_authenticated_registry(self):
        registry = self.authority["authenticated_registry"]
        self.assertFalse(registry["is_section_13_registry"])
        self.assertIn("not an authenticated", registry["statement"].lower())
        serialized = json.dumps(self.authority, sort_keys=True)
        self.assertNotIn('"registry_seq"', serialized)
        self.assertIsNone(re.search(r'"sig"\s*:', serialized))

    def test_immutable_grail_pin_and_local_bytes_are_unchanged(self):
        kernel_pin = load_json(ROOT / "KERNEL_PIN.json")
        self.assertEqual(kernel_pin["spec"], "rapp-distro/1.0")
        self.assertEqual(
            kernel_pin["kernel"]["grail"], "kody-w/rapp-installer"
        )
        self.assertEqual(kernel_pin["kernel"]["tag"], "brainstem-v0.6.9")
        self.assertEqual(kernel_pin["kernel"]["frozen"], EXPECTED_GRAIL)

        boundary = self.authority["immutable_grail_boundary"]
        self.assertEqual(boundary["repository"], "kody-w/rapp-installer")
        self.assertEqual(boundary["tag"], "brainstem-v0.6.9")
        self.assertEqual(boundary["policy"], "read-only")
        self.assertEqual(boundary["frozen"], EXPECTED_GRAIL)

        for relative_path, expected_hash in EXPECTED_GRAIL.items():
            with self.subTest(path=relative_path):
                self.assertEqual(sha256(ROOT / relative_path), expected_hash)

    def test_status_and_entrypoints_expose_claim_limits(self):
        status = (ROOT / "RAPP1_STATUS.md").read_text(encoding="utf-8")
        tracked_count = len(
            subprocess.check_output(
                ("git", "ls-files", "-z"), cwd=ROOT
            ).split(b"\0")
        ) - 1
        self.assertTrue(
            status.startswith("# NOT YET FULLY RAPP/1 CONFORMANT\n")
        )
        for phrase in (
            "Baseline (2026-07-16, `f71810d`): 640/640 tracked paths",
            "Post-implementation review (`e1c2fbb`): 691/691 tracked paths",
            f"Integrated closure tree: {tracked_count}/{tracked_count} tracked paths",
            "Every tracked file in each snapshot was individually reviewed and classified",
            "ZIP-compatible archives",
            "450 recursively counted archive members",
            "2 JSON eggs",
            "contextual disposition per path",
            "Semantic, runtime, and cryptographic depth was applied where relevant",
            "`rapp_check.py` is a shallow checker and is insufficient by itself",
            "This full audit is separate from the named checker",
            "do not establish full RAPP/1\nconformance or authenticated acceptance",
            "Structural validation is not authenticated acceptance",
            "Signed monotonic registry and out-of-band anchor",
            "Lawful root re-anchor",
            "Signed replacement invite",
            "External mirror correction",
        ):
            self.assertIn(phrase, status)
        self.assertNotIn(
            "not every file received exhaustive semantic", status
        )

        for relative_path in ("README.md", "pages/kernel.html"):
            text = (ROOT / relative_path).read_text(encoding="utf-8")
            with self.subTest(path=relative_path):
                self.assertIn("NOT YET FULLY RAPP/1 CONFORMANT", text)
                self.assertIn("RAPP1_AUTHORITY.json", text)
                self.assertIn("RAPP1_STATUS.md", text)

        constitution = (ROOT / "CONSTITUTION.md").read_text(encoding="utf-8")
        self.assertGreater(
            constitution.find("## Article LV — RAPP/1 Rev-5"),
            constitution.find("## Article LIV — One Schema Name"),
        )


if __name__ == "__main__":
    unittest.main()
