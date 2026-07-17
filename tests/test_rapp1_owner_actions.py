import ast
import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / "RAPP1_OWNER_ACTIONS.json"
HUMAN_PATH = ROOT / "RAPP1_OWNER_ACTIONS.md"
STATUS_PATH = ROOT / "RAPP1_STATUS.md"
FACADE_PATH = ROOT / "rapp_brainstem/rapp1_facade.py"
COMMONS_PATH = ROOT / "pages/tutorials/commons.egg"

EXPECTED_FACADE_CODES = [
    "malformed-request",
    "unknown-session",
    "idempotency-in-progress",
    "session-in-progress",
    "inference-refused",
    "facade-storage-refused",
]
EXPECTED_FACADE_STEPS = ["1", "1a", "2", "3", "4", "5", "6", None]
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
EXPECTED_INVALID_LEGACY_KINDS = [
    ("memory_added", "installer/plant.sh:6308"),
    ("conversation", "installer/plant.sh:7624"),
    ("tool_call", "installer/plant.sh:7733"),
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
        self.assertEqual(
            self.ledger["candidate_namespaces"]["facade_allowed_steps"],
            EXPECTED_FACADE_STEPS,
        )
        self.assertEqual(
            self.ledger["candidate_namespaces"][
                "facade_error_code_registration_state"
            ],
            (
                "zero registered; every listed value is candidate-unregistered, "
                "including unknown-session"
            ),
        )

        evidence = self.ledger["known_evidence"]["facade_current"]
        self.assertEqual(evidence["evidence_state"], "current-post-migration")
        self.assertIsNone(evidence["source_commit"])
        self.assertEqual(evidence["path"], "rapp_brainstem/rapp1_facade.py")
        self.assertEqual(
            evidence["path_sha256"],
            "4bd8e1c51290295c5dfd6dec73a5f12"
            "f3771ec674a5e856ab78edbfc61151a01",
        )
        self.assertEqual(
            evidence["git_blob"], "690226b2492d86cf089ed222cb7cefe38af8c1e5"
        )
        self.assertIn("post-migration pre-acceptance", evidence["path_state"])
        self.assertEqual(evidence["candidate_error_codes"], EXPECTED_FACADE_CODES)
        self.assertEqual(
            evidence["error_code_registration_state"],
            "candidate-unregistered",
        )
        self.assertEqual(evidence["allowed_error_steps"], EXPECTED_FACADE_STEPS)
        self.assertEqual(evidence["migration_state"]["database_schema_version"], 3)
        self.assertEqual(
            evidence["migration_state"]["current_request_fingerprint_version"],
            3,
        )
        self.assertEqual(
            evidence["migration_state"]["inference_boundary_state"],
            (
                "target-owned inference-refused default; adapter only through "
                "explicit dependency injection"
            ),
        )
        self.assertIs(
            evidence["migration_state"]["grail_module_dependency"], False
        )

        baseline = self.ledger["known_evidence"]["facade_audit_baseline"]
        self.assertEqual(baseline["evidence_state"], "audit-baseline")
        self.assertEqual(
            baseline["audit_target_commit"],
            "f71810db3259fea533b4112c1df300d4b0dc781c",
        )
        legacy_wire = baseline["legacy_wire"]
        self.assertEqual(
            legacy_wire["tier_1_handler"],
            "rapp_brainstem/brainstem.py:1441-1559",
        )
        self.assertIs(legacy_wire["tier_1_is_pinned_grail"], True)
        self.assertIs(
            legacy_wire["idempotency_key_in_audited_tier_handlers"], False
        )
        self.assertEqual(legacy_wire["tether_request_shape"], "{messages}")
        if FACADE_PATH.exists():
            facade_bytes = FACADE_PATH.read_bytes()
            self.assertEqual(
                hashlib.sha256(facade_bytes).hexdigest(),
                evidence["path_sha256"],
            )
            git_blob = hashlib.sha1(
                f"blob {len(facade_bytes)}\0".encode("ascii") + facade_bytes
            ).hexdigest()
            self.assertEqual(git_blob, evidence["git_blob"])
            emitted = list(
                assigned_literal(FACADE_PATH, "PENDING_REGISTRY_ERROR_CODES")
            )
            self.assertEqual(emitted, EXPECTED_FACADE_CODES)
            for relative_path, expected_hash in evidence[
                "supporting_paths"
            ].items():
                self.assertEqual(
                    hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest(),
                    expected_hash,
                )

        combined = self.ledger_text + self.human
        self.assertNotIn("7f84d84b28bf7b570787af16b0008cec96704f53", combined)
        self.assertNotIn(
            "6eca226e5ebc1a41f7eacac9cc98e19d20e5705750b6cd0166d8a0809d19a5da",
            combined,
        )

    def test_candidate_protocol_variants_and_kind_families_are_exact(self):
        candidates = self.ledger["candidate_namespaces"]
        self.assertEqual(candidates["egg_variants"], EXPECTED_VARIANTS)
        self.assertEqual(
            candidates["kind_families"], ["memory", "body", "swarm"]
        )
        self.assertEqual(
            candidates["required_re_genesis_kinds"], EXPECTED_RE_GENESIS
        )
        legacy_kinds = candidates[
            "legacy_frame_kinds_requiring_owner_replacement"
        ]
        self.assertEqual(
            [
                (entry["legacy_kind"], entry["audit_source"])
                for entry in legacy_kinds
            ],
            EXPECTED_INVALID_LEGACY_KINDS,
        )
        for entry in legacy_kinds:
            self.assertEqual(entry["evidence_state"], "audit-baseline")
            self.assertIn("HTTP 410-contained", entry["current_migration_state"])
            self.assertIs(entry["valid_current_kind_grammar"], False)
            self.assertIs(entry["registered"], False)
            self.assertIsNone(entry["replacement_kind"])
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
        self.assertEqual(
            root["migration_commit_authentication"], "false/unsigned"
        )
        self.assertIsNone(root["attestation"])
        self.assertEqual(root["candidate_reanchor_case"], "upgrade")
        self.assertIsNone(root["owner_selected_reanchor_case"])
        invite = evidence["commons_invite"]
        self.assertEqual(invite["retired_target_path"], "pages/tutorials/commons.egg")
        self.assertEqual(
            invite["retired_target_sha256"],
            "2731c02f187701c1d07b3a7f5eed5e2073c203ffb4f6c08d00292894e3319a5d",
        )
        self.assertEqual(invite["retired_target_size"], 443)
        self.assertEqual(
            invite["retired_egg_address"],
            "a03fa90289eaefcf1a6521cdc10ee17bc"
            "706a0bb353e688ad84135d684380fb7",
        )
        self.assertEqual(
            invite["url_fixed_unsigned_candidate_address"],
            "d15305a25cbe6c9aab51a4ed2ab55143"
            "45772023a95d658b37fc19303e5778bc",
        )
        self.assertEqual(invite["retired_target_url_status"], 404)
        self.assertEqual(invite["required_target_url_status"], 200)
        continuity = invite["target_identity_continuity"]
        self.assertEqual(
            continuity["historical_provisional_tail"],
            "3929ce90ebe97fe2a95432e9f647f3a3",
        )
        self.assertEqual(
            continuity["tagged_upgrade_result"], continuity["current_tail"]
        )
        self.assertEqual(continuity["candidate_reanchor_case"], "upgrade")
        self.assertIsNone(continuity["owner_selected_reanchor_case"])
        self.assertIs(continuity["authorization_present"], False)
        mirrors = evidence["ecosystem_mirrors"]
        self.assertEqual(
            mirrors["canonical"]["sha256"],
            "0eb8146b62af8e8473d2ca8944ed8aff69e18e41a143eb1ef466f3c3fc153616",
        )
        self.assertEqual(
            mirrors["divergent_rapp_god"]["sha256"],
            "f1ddcf7e1302a82195fa682ad94140d0d066bbe60647befc5030ec5b50507e9e",
        )
        self.assertEqual(
            mirrors["divergent_rapp_god"]["observed_commit"],
            "c6c0b3e2a68c96f8ed70005101f996ea91e4bd0e",
        )
        self.assertEqual(
            mirrors["divergent_rapp_god"]["later_repository_head_observed"],
            "94d0f49800fdd94b627f089c9cf3d07a7774b89b",
        )

    def test_report_hashes_and_required_registry_surface_are_pinned(self):
        self.assertEqual(
            self.ledger["audit_evidence"]["evidence_state"],
            "audit-baseline",
        )
        reports = {
            report["title"]: report
            for report in self.ledger["audit_evidence"]["reports"]
        }
        self.assertEqual(
            {title: report["sha256"] for title, report in reports.items()},
            {
                "RAPP-spec-matrix-report.md": (
                    "e12f3a7a0a2ba15ef23b40421650d855"
                    "1b7d4839781fb07a1b924783fedf6a78"
                ),
                "RAPP-artifact-trust-report.md": (
                    "7cf4506f38f7e23237292772068638387"
                    "fca7832a0cbe240ff2d31db67574c75"
                ),
                "RAPP-canon-mirrors-report.md": (
                    "188eef4a3d2f65b93a4e0832515e8fe"
                    "8b7b8826e1163b683029ab1d14bc51f59"
                ),
            },
        )
        self.assertTrue(
            all(report["repository_path"] is None for report in reports.values())
        )

        surface = self.ledger["known_evidence"]["required_registry_surface"]
        self.assertEqual(surface["repository"], "kody-w/rapp-map")
        self.assertEqual(surface["branch"], "main")
        self.assertEqual(surface["path"], "ecosystem-spec.json")
        self.assertEqual(
            surface["audit_commit"],
            "baded0098d8b97c2876c0b8af4475cf3061b7ad0",
        )
        self.assertEqual(
            surface["git_blob"], "d4021c6f7b916ede041ae9d3c0802977524d5189"
        )
        self.assertEqual(surface["byte_length"], 60479)
        self.assertEqual(
            surface["sha256"],
            "0eb8146b62af8e8473d2ca8944ed8aff69e18e41a143eb1ef466f3c3fc153616",
        )
        self.assertEqual(surface["current_schema"], "rapp-ecosystem-spec/1.0")
        self.assertEqual(surface["commit_authentication"], "false/unsigned")
        self.assertIs(surface["estate_owner_designated"], False)
        self.assertIs(surface["root_rappid_assumed_estate_owner"], False)

        registry_action = next(
            action
            for action in self.ledger["actions"]
            if action["id"] == "owner-publish-authenticated-registry"
        )
        self.assertEqual(
            registry_action["where"]["canonical_registry_repository"],
            "kody-w/rapp-map",
        )
        self.assertEqual(
            registry_action["where"]["canonical_registry_path"],
            "ecosystem-spec.json",
        )
        registry_test_ids = {
            check["id"] for check in registry_action["acceptance_tests"]
        }
        self.assertIn(
            "registry-owner-and-legacy-kind-decisions", registry_test_ids
        )

    def test_current_migration_evidence_is_recomputed(self):
        current = self.ledger["current_evidence"]
        self.assertEqual(current["evidence_state"], "current-post-migration")
        self.assertEqual(current["target_branch"], "main")
        self.assertEqual(
            current["target_commit"],
            "4c2b999f8c890b76d057241d29ecda29e0239d79",
        )
        self.assertEqual(
            current["migration_commits"],
            [
                "2cee074d755fe1ca1e81f5fb0c2331cbc47f1537",
                "803cc76294b8a89273470d3167dde6f01df41e7d",
                "591e7aec3b2183e0d48a1d6dfb6ebc59f177daea",
                "4c2b999f8c890b76d057241d29ecda29e0239d79",
            ],
        )

        status_bytes = STATUS_PATH.read_bytes()
        self.assertEqual(
            hashlib.sha256(status_bytes).hexdigest(),
            current["status_sha256"],
        )
        status = status_bytes.decode("utf-8")
        self.assertIn("## Active-path residual", status)
        self.assertIn(
            "[`RAPP1_OWNER_ACTIONS.md`](./RAPP1_OWNER_ACTIONS.md)", status
        )
        self.assertIn(
            "[`RAPP1_OWNER_ACTIONS.json`](./RAPP1_OWNER_ACTIONS.json)", status
        )

        for relative_path, expected_hash in current["current_path_hashes"].items():
            with self.subTest(path=relative_path):
                self.assertEqual(
                    hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest(),
                    expected_hash,
                )

    def test_human_ledger_records_issue_ready_immutable_cave_residual(self):
        human = HUMAN_PATH.read_text(encoding="utf-8")
        for marker in (
            "## Issue-ready immutable Cave residual (not a target action)",
            "[Containment] Retire Cave hatch.py execution",
            "cave/rapplications/rapp-installer/hatch.py",
            "_extract_egg",
            "os.execve",
            "410/exit-78 tombstone",
            "This target must not patch that prepared clone",
            "immutable archives",
        ):
            self.assertIn(marker, human)

    def test_root_case_remains_an_explicit_owner_decision(self):
        action = next(
            action
            for action in self.ledger["actions"]
            if action["id"] == "owner-authorize-root-upgrade-reanchor"
        )
        self.assertEqual(action["where"]["candidate_case"], "upgrade")
        self.assertIsNone(action["owner_inputs"]["selected_case"])
        self.assertIsNone(
            action["owner_inputs"]["current_root_selected_as_estate_owner"]
        )
        self.assertIsNone(
            action["owner_inputs"][
                "outgoing_owner_authorization_evidence_path"
            ]
        )
        combined = " ".join(
            [action["what"], action["when"], *action["how"]]
        )
        self.assertIn("code and tail length must not select the case", combined)
        self.assertIn(
            "If this root identity is separately selected as estate owner",
            combined,
        )

    def test_kernel_latest_alias_has_safe_disposition_gate(self):
        alias = self.ledger["known_evidence"]["kernel_latest_alias"]
        self.assertEqual(alias["manifest_path"], "rapp_kernel/manifest.json")
        self.assertEqual(
            alias["manifest_sha256"],
            "a2826eb8820f4487948bfdb1bf3f80b4"
            "ca8ccdf902553d5d109cb8de3bb85889",
        )
        self.assertEqual(alias["declared_latest"], "0.6.0")
        self.assertIsNone(alias["signing_method"])
        self.assertIsNone(alias["signing_key_id"])
        self.assertIsNone(alias["signing_verification_uri"])
        self.assertIsNone(alias["version_attestation"])
        self.assertEqual(
            alias["latest_brainstem_sha256"],
            "f7fb359bbe8b6ba3db3665d81cb8e573"
            "a266c716278d8d21d8962ea40821e5aa",
        )
        self.assertEqual(alias["active_pin_tag"], "brainstem-v0.6.9")
        self.assertIs(alias["payload_edit_allowed"], False)
        manifest_path = ROOT / alias["manifest_path"]
        payload_path = ROOT / alias["latest_brainstem_path"]
        self.assertEqual(
            hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            alias["manifest_sha256"],
        )
        self.assertEqual(
            hashlib.sha256(payload_path.read_bytes()).hexdigest(),
            alias["latest_brainstem_sha256"],
        )

        mirror_action = next(
            action
            for action in self.ledger["actions"]
            if action["id"] == "owners-correct-or-retire-external-mirror"
        )
        test_ids = {
            check["id"] for check in mirror_action["acceptance_tests"]
        }
        self.assertIn("kernel-latest-retired-or-provenance-pinned", test_ids)
        self.assertIsNone(
            mirror_action["owner_inputs"]["kernel_latest_disposition"]
        )

    def test_commons_addresses_are_reproducible(self):
        manifest = json.loads(COMMONS_PATH.read_text(encoding="utf-8"))
        manifest.pop("sig")

        def address(value):
            canonical = json.dumps(
                value,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            return hashlib.sha256(b"rapp/1:egg-manifest\n" + canonical).hexdigest()

        self.assertEqual(
            address(manifest),
            self.ledger["known_evidence"]["commons_invite"][
                "retired_egg_address"
            ],
        )
        manifest["payload"][
            "target_url"
        ] = "https://kody-w.github.io/rapp-commons/"
        self.assertEqual(
            address(manifest),
            self.ledger["known_evidence"]["commons_invite"][
                "url_fixed_unsigned_candidate_address"
            ],
        )

    def test_canonical_door_blockers_are_covered_by_facade_gate(self):
        doors = self.ledger["known_evidence"]["canonical_doors"]
        self.assertEqual(doors["root"]["status"], 200)
        self.assertIs(doors["root"]["byte_equal_to_target"], False)
        self.assertEqual(
            doors["root"]["target_sha256"],
            "59dd3b53e2ed0c7594b3754425938b90"
            "7600fdf5787b1cef912276aa9d3711b3",
        )
        self.assertEqual(
            doors["root"]["observed_sha256"],
            "8710b3c45fd660f96d159be41c861bf9"
            "fb9bb45acbc40888815d7942d342792e",
        )
        root_claim = (
            f"Root returns {doors['root']['status']}, but remote bytes differ "
            "from target "
            f"(`byte_equal_to_target: {str(doors['root']['byte_equal_to_target']).lower()}`; "
            f"target SHA-256 `{doors['root']['target_sha256']}`; "
            f"observed SHA-256 `{doors['root']['observed_sha256']}`)"
        )
        self.assertIn(root_claim, self.human)
        self.assertNotIn(
            "Root returns 200 and exact `rappid.json` bytes",
            self.human,
        )
        self.assertEqual(
            [doors[name]["status"] for name in ("cave", "installer", "sample_session")],
            [404, 404, 404],
        )
        self.assertIs(doors["installer"]["immutable_grail_boundary"], True)

        facade_action = next(
            action
            for action in self.ledger["actions"]
            if action["id"] == "owner-enable-public-rapp1-facade"
        )
        test_ids = {
            check["id"] for check in facade_action["acceptance_tests"]
        }
        self.assertIn("facade-canonical-door-claims", test_ids)

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
