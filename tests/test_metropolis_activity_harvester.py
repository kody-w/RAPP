from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HARVESTER = ROOT / "scripts" / "harvest-metropolis-activity.py"
SNAPSHOT = ROOT / "pages" / "metropolis" / "activity-snapshot.json"
WORKFLOW = ROOT / ".github" / "workflows" / "harvest-metropolis-activity.yml"


class MetropolisActivityHarvesterRetirementTests(unittest.TestCase):
    def test_scheduled_writer_is_removed(self) -> None:
        self.assertFalse(WORKFLOW.exists())

    def test_tombstone_refuses_without_network_or_writes(self) -> None:
        before = SNAPSHOT.read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            result = subprocess.run(
                [sys.executable, str(HARVESTER)],
                cwd=temporary,
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 78, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "gone")
        self.assertEqual(
            payload["code"],
            "metropolis-activity-harvester-retired",
        )
        self.assertFalse(payload["accepted"])
        self.assertEqual(SNAPSHOT.read_bytes(), before)

    def test_tombstone_has_no_network_client(self) -> None:
        text = HARVESTER.read_text(encoding="utf-8")
        self.assertNotIn("urllib", text)
        self.assertNotIn("requests", text)
        self.assertNotIn("api.github.com", text)
        self.assertNotIn("GITHUB_TOKEN", text)


if __name__ == "__main__":
    unittest.main()
