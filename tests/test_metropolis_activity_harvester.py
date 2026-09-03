from __future__ import annotations

import json
import importlib.util
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
HARVESTER = ROOT / "scripts" / "harvest-metropolis-activity.py"
SNAPSHOT = ROOT / "pages" / "metropolis" / "activity-snapshot.json"
WORKFLOW = ROOT / ".github" / "workflows" / "harvest-metropolis-activity.yml"


def load_harvester():
    spec = importlib.util.spec_from_file_location("metropolis_harvester", HARVESTER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MetropolisActivityHarvesterAdaptationTests(unittest.TestCase):
    def test_scheduled_writer_is_removed(self) -> None:
        self.assertFalse(WORKFLOW.exists())

    def test_default_and_plan_modes_are_useful_without_network_or_writes(self) -> None:
        before = SNAPSHOT.read_bytes()
        module = load_harvester()
        output = io.StringIO()
        with patch.object(
            module.urllib.request,
            "urlopen",
            side_effect=AssertionError("network must remain unused"),
        ), redirect_stdout(output):
            status = module.main([])
        self.assertEqual(status, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["status"], "frozen-snapshots-valid")
        self.assertFalse(payload["accepted"])
        self.assertFalse(payload["network_used"])
        self.assertFalse(payload["write_performed"])

        output = io.StringIO()
        with redirect_stdout(output):
            status = module.main(["--plan"])
        self.assertEqual(status, 0)
        plan = json.loads(output.getvalue())
        self.assertEqual(plan["status"], "plan-only")
        self.assertFalse(plan["network_default"])
        self.assertFalse(plan["write_default"])
        self.assertTrue(plan["targets"])
        self.assertEqual(SNAPSHOT.read_bytes(), before)

    def test_online_write_request_refuses_before_network_or_mutation(self) -> None:
        before = SNAPSHOT.read_bytes()
        module = load_harvester()
        output = io.StringIO()
        with patch.object(
            module.urllib.request,
            "urlopen",
            side_effect=AssertionError("network must remain unused"),
        ), redirect_stdout(output):
            status = module.main(["--online", "--write"])
        self.assertEqual(status, 78)
        payload = json.loads(output.getvalue())
        self.assertEqual(
            payload["code"],
            "authenticated-collection-binding-required",
        )
        self.assertFalse(payload["network_used"])
        self.assertFalse(payload["write_performed"])
        self.assertEqual(SNAPSHOT.read_bytes(), before)

    def test_full_collector_source_remains_recoverable(self) -> None:
        text = HARVESTER.read_text(encoding="utf-8")
        self.assertIn("urllib.request", text)
        self.assertIn("api.github.com", text)
        self.assertIn("GITHUB_TOKEN", text)
        self.assertIn("historical_source_commit", text)
        self.assertIn("return []", text)


if __name__ == "__main__":
    unittest.main()
