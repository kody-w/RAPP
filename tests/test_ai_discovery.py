"""Offline contract tests for RAPP's machine-facing discovery surface."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AiDiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.discovery = json.loads(
            (ROOT / "rapp-ai.json").read_text(encoding="utf-8")
        )
        self.authority = json.loads(
            (ROOT / "RAPP1_AUTHORITY.json").read_text(encoding="utf-8")
        )

    def test_discovery_matches_authority_and_status(self) -> None:
        self.assertEqual(
            self.discovery["schema"],
            "rapp-ai-discovery/1.0",
        )
        self.assertIn("ai-runtime", self.discovery["audience"]["primary"])
        self.assertEqual(
            self.discovery["audience"]["sovereign_authority"],
            "human-owner",
        )
        self.assertEqual(
            self.discovery["status"]["rapp_1_conformance"],
            "not-yet-fully-conformant",
        )
        self.assertFalse(
            self.discovery["status"]["authenticated_section_13_registry"]
        )
        self.assertFalse(self.discovery["status"]["public_installer"])
        self.assertEqual(
            self.discovery["authority"]["commit"],
            self.authority["standard"]["commit"],
        )
        self.assertEqual(
            self.discovery["authority"]["sha256"],
            self.authority["standard"]["sha256"],
        )

    def test_local_entrypoints_exist(self) -> None:
        for entrypoint in self.discovery["entrypoints"]:
            href = entrypoint["href"]
            if "://" not in href:
                self.assertTrue((ROOT / href).is_file(), href)

    def test_growth_is_permissioned_not_self_replicating(self) -> None:
        growth = self.discovery["growth_loop"]
        self.assertEqual(growth["mode"], "permissioned-ai-to-ai")
        self.assertIn("emit-adoption-receipt", growth["steps"])
        self.assertIn("silent-installation", growth["forbidden"])
        self.assertIn("self-replication", growth["forbidden"])
        self.assertIn("human-authority-bypass", growth["forbidden"])

    def test_capacity_market_is_truthfully_non_shipped(self) -> None:
        market = self.discovery["ai_capacity_market"]
        self.assertEqual(market["status"], "proposal-not-shipped")
        self.assertEqual(market["market_unit"], "bounded-rapp-cell-work-cycle")
        self.assertEqual(market["pricing"], "flat-fee")
        self.assertEqual(
            market["buyer"],
            "ai-runtime-acting-under-human-budget-permit",
        )
        self.assertEqual(
            market["seller"],
            "ai-runtime-offering-owner-approved-capability",
        )
        self.assertEqual(
            set(market["required_limits"]),
            {
                "maximum-price",
                "maximum-cycle-count",
                "maximum-elapsed-seconds",
                "maximum-delegation-depth",
                "allowed-capabilities",
                "allowed-sellers",
                "expiry",
            },
        )
        self.assertEqual(
            set(market["refuse"]),
            {
                "missing-owner-permit",
                "over-budget",
                "expired-offer",
                "policy-forbidden-action",
                "unbounded-recursive-delegation",
                "receipt-verification-failure",
                "acceptance-rule-failure",
            },
        )
        self.assertEqual(
            market["reservation"],
            "funds-held-before-execution",
        )
        self.assertEqual(
            market["settlement"],
            "capture-after-acceptance",
        )

    def test_human_and_machine_entrypoints_agree(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        llms = (ROOT / "llms.txt").read_text(encoding="utf-8")
        claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        copilot = (
            ROOT / ".github" / "copilot-instructions.md"
        ).read_text(encoding="utf-8")

        for text in (readme, llms, claude, copilot):
            self.assertIn("AI runtime", text)
            self.assertIn("human", text.lower())
        self.assertIn("proposal, not a live payment service", llms)
        self.assertIn("human-issued budget permit", llms)
        self.assertIn(
            "The human approves the economic envelope.",
            llms,
        )
        self.assertIn("proposal, not a shipped payment service", readme)
        self.assertIn("human-approved budget envelope", claude)
        self.assertIn("human-approved budget envelope", copilot)
        self.assertIn(
            "AIs hire AIs. Humans set the law. RAPP proves the work.",
            llms,
        )


if __name__ == "__main__":
    unittest.main()
