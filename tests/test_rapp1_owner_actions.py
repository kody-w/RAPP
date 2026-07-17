import ast
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / "RAPP1_OWNER_ACTIONS.json"
HUMAN_PATH = ROOT / "RAPP1_OWNER_ACTIONS.md"
STATUS_PATH = ROOT / "RAPP1_STATUS.md"
FACADE_PATH = ROOT / "rapp_brainstem/rapp1_facade.py"

EXPECTED_FACADE_CODES = [
    "malformed-request",
    "unknown-session",
    "idempotency-conflict",
    "idempotency-in-progress",
    "session-in-progress",
    "inference-refused",
    "facade-storage-refused",
]
EXPECTED_VARIANTS = [
    "organism",
    "rapplication",
    "session",
    "invite",
    "neighborhood",
    "estate",
]
EXPECTED_RE_GENESIS = [
    {"kind": "memory.re-genesis", "family": "memory"},
    {"kind": "body.re-genesis", "family": "body"},
    {"kind": "swarm.re-genesis", "family": "swarm"},
]
EXPECTED_STATUS_BLOCKERS = [
    "Signed monotonic registry and out-of-band anchor",
    "Lawful root re-anchor",
    "Signed replacement invite",
    "External mirror correction",
]
REQUIRED_ACTION_FIELDS = {
    "id",
    "title",
    "issue_title",
    "status",
    "why",
    "what",
    "where",
    "when",
    "how",
    "prerequisites",
    "owner_inputs",
    "acceptance_tests",
    "rollback_or_retirement",
}


def walk(value):
    yield value
    if isinstance(value, dict):
        for member in value.values():
            yield from walk(member)
    elif isinstance(value, list):
        for member in value:
            yield from walk(member)


def assigned_literal(path, name):
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in module.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if any(isinstance(target, ast.Name) and target.id == name for target in targets):
            return ast.literal_eval(node.value)
    raise AssertionError(f"{name} is not a literal assignment in {path}")


class Rapp1OwnerActionLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger_text = LEDGER_PATH.read_text(encoding="utf-8")
        cls.ledger = json.loads(cls.ledger_text)
        cls.human = HUMAN_PATH.read_text(encoding="utf-8")

    def test_ledger_cannot_be_mistaken_for_section_13_registry(self):
        self.assertEqual(self.ledger["schema"], "rapp-owner-action-ledger/1.0")
        self.assertEqual(
            self.ledger["record_kind"], "candidate-owner-action-ledger"
        )
        self.assertEqual(self.ledger["status"], "candidate")
        self.assertEqual(
            self.ledger["authority_state"], "owner-action-required"
        )
        self.assertIs(self.ledger["is_section_13_registry"], False)
        self.assertIs(self.ledger["authenticated_acceptance_allowed"], False)
        self.assertNotIn("registry_seq", self.ledger)
        self.assertNotIn("entries", self.ledger)
        self.assertNotIn("sig", self.ledger)

        for value in walk(self.ledger):
            if isinstance(value, dict):
                self.assertNotEqual(value.get("schema"), "rapp/1-registry")

        candidates = self.ledger["candidate_namespaces"]
        self.assertEqual(
            candidates["registration_state"], "candidate-unregistered"
        )
        for candidate in candidates["protocol_pins"]:
            self.assertNotIn("type", candidate)
        self.assertIn("not a RAPP/1 §13 registry", self.human)

    def test_no_signature_or_key_material_is_fabricated(self):
        forbidden_keys = {
            "sig",
            "old_key_sig",
            "private_key",
            "private_key_pem",
            "secret_key",
            "key_seed",
        }
        for value in walk(self.ledger):
            if not isinstance(value, dict):
                continue
            self.assertTrue(forbidden_keys.isdisjoint(value))
            for key, member in value.items():
                if key.endswith("spki_der_b64"):
                    self.assertIsNone(member)

        for action in self.ledger["actions"]:
            self.assertTrue(action["owner_inputs"])
            self.assertTrue(
                all(value is None for value in action["owner_inputs"].values())
            )

        combined = self.ledger_text + self.human
        self.assertNotIn("-----BEGIN PRIVATE KEY-----", combined)
        self.assertNotIn("-----BEGIN EC PRIVATE KEY-----", combined)
        self.assertNotIn("MIGRATED-UNSIGNED", combined)
        self.assertIsNone(
            re.search(
                r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{20,}"
                r"\.\.[A-Za-z0-9_-]{20,}(?![A-Za-z0-9_-])",
                combined,
            )
        )

    def test_every_action_has_execution_and_retirement_details(self):
        actions = self.ledger["actions"]
        self.assertEqual(len(actions), 5)
        self.assertEqual(len({action["id"] for action in actions}), len(actions))
        for action in actions:
            with self.subTest(action=action["id"]):
                self.assertEqual(set(action), REQUIRED_ACTION_FIELDS)
                self.assertEqual(action["status"], "owner-action-required")
                for field in ("why", "what", "when"):
                    self.assertIsInstance(action[field], str)
                    self.assertTrue(action[field].strip())
                self.assertIsInstance(action["where"], dict)
                self.assertTrue(action["where"])
                self.assertGreaterEqual(len(action["how"]), 4)
                self.assertGreaterEqual(len(action["prerequisites"]), 3)
                self.assertGreaterEqual(len(action["acceptance_tests"]), 4)
                for check in action["acceptance_tests"]:
                    self.assertEqual(
                        set(check), {"id", "procedure", "pass_condition"}
                    )
                    self.assertTrue(all(check.values()))
                self.assertEqual(
                    set(action["rollback_or_retirement"]),
                    {"on_failure", "retirement_outcome"},
                )
                self.assertTrue(
                    all(action["rollback_or_retirement"].values())
                )
                self.assertRegex(action["issue_title"], r"^\[[^\]]+ action\] ")

    def test_facade_pending_error_codes_are_covered_exactly(self):
        actual = self.ledger["candidate_namespaces"]["facade_error_codes"]
        self.assertEqual(actual, EXPECTED_FACADE_CODES)
        self.assertEqual(len(actual), len(set(actual)))

        evidence = self.ledger["known_evidence"]["facade_candidate"]
        self.assertEqual(
            evidence["source_commit"],
            "7f84d84b28bf7b570787af16b0008cec96704f53",
        )
        self.assertEqual(evidence["path"], "rapp_brainstem/rapp1_facade.py")
        if FACADE_PATH.exists():
            emitted = list(
                assigned_literal(FACADE_PATH, "PENDING_REGISTRY_ERROR_CODES")
            )
            self.assertEqual(emitted, EXPECTED_FACADE_CODES)

    def test_candidate_protocol_variants_and_kind_families_are_exact(self):
        candidates = self.ledger["candidate_namespaces"]
        self.assertEqual(candidates["egg_variants"], EXPECTED_VARIANTS)
        self.assertEqual(
            candidates["kind_families"], ["memory", "body", "swarm"]
        )
        self.assertEqual(
            candidates["required_re_genesis_kinds"], EXPECTED_RE_GENESIS
        )
        self.assertIsNone(candidates["other_kind_decisions"])
        self.assertEqual(
            candidates["protocol_pins"],
            [
                {
                    "name": "rapp/1",
                    "spec_repo": "kody-w/rapp-1",
                    "spec_path": "SPEC.md",
                    "spec_hash": (
                        "6d06daba65d7c045716f3d6e95db8401"
                        "ab58e727820e4114466d847f62cae49b"
                    ),
                    "deprecated": False,
                }
            ],
        )

    def test_all_status_owner_blockers_are_mapped(self):
        status = STATUS_PATH.read_text(encoding="utf-8")
        owner_section = status.split("## Owner-action blockers", 1)[1]
        owner_section = owner_section.split("\n## ", 1)[0]
        blockers = re.findall(
            r"^\d+\. \*\*(.+?)\*\*", owner_section, flags=re.MULTILINE
        )
        self.assertEqual(blockers, EXPECTED_STATUS_BLOCKERS)

        mapping = self.ledger["status_blocker_map"]
        self.assertEqual(list(mapping), EXPECTED_STATUS_BLOCKERS)
        action_ids = {action["id"] for action in self.ledger["actions"]}
        self.assertTrue(set(mapping.values()).issubset(action_ids))
        self.assertEqual(len(set(mapping.values())), len(mapping))

    def test_verified_ids_hashes_and_paths_are_pinned(self):
        evidence = self.ledger["known_evidence"]
        root = evidence["root_identity"]
        self.assertEqual(
            root["historical_stored_rappid"],
            "rappid:@kody-w/RAPP:0b635450c04249fbb4b1bdb571044dec",
        )
        self.assertEqual(
            root["current_stored_rappid"],
            "rappid:@kody-w/rapp:"
            "9a8f0a4b5a710e20f4d819a0f37d2a4c"
            "9f113b5e78fb3c29e70b54fff48a38f9",
        )
        self.assertEqual(
            root["migration_commit"],
            "19ff7d9ff483c0eef258a3b2031da1fd74570854",
        )
        invite = evidence["commons_invite"]
        self.assertEqual(invite["retired_target_path"], "pages/tutorials/commons.egg")
        self.assertEqual(
            invite["retired_target_sha256"],
            "2731c02f187701c1d07b3a7f5eed5e2073c203ffb4f6c08d00292894e3319a5d",
        )
        mirrors = evidence["ecosystem_mirrors"]
        self.assertEqual(
            mirrors["canonical"]["sha256"],
            "0eb8146b62af8e8473d2ca8944ed8aff69e18e41a143eb1ef466f3c3fc153616",
        )
        self.assertEqual(
            mirrors["divergent_rapp_god"]["sha256"],
            "f1ddcf7e1302a82195fa682ad94140d0d066bbe60647befc5030ec5b50507e9e",
        )

    def test_human_ledger_tracks_machine_actions(self):
        self.assertIn(
            "[`RAPP1_OWNER_ACTIONS.json`](./RAPP1_OWNER_ACTIONS.json)",
            self.human,
        )
        self.assertIn("**Status: `candidate` · `owner-action-required`", self.human)
        for action in self.ledger["actions"]:
            with self.subTest(action=action["id"]):
                self.assertIn(action["issue_title"], self.human)
                self.assertIn(action["id"], self.human)
        for label in ("Why", "What", "Where", "When", "How", "Prerequisites"):
            self.assertEqual(self.human.count(f"- **{label}:"), 5)
        self.assertEqual(self.human.count("- **Exact acceptance:**"), 5)
        self.assertEqual(self.human.count("- **Rollback/retirement:**"), 5)


if __name__ == "__main__":
    unittest.main()
