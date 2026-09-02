#!/usr/bin/env python3
"""Regression tests for the retired Cave catalog and steward."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CAVE = ROOT / "cave"
CATALOGS = (
    CAVE / "facets.json",
    CAVE / "cubbies/index.json",
    CAVE / "rar/index.json",
    CAVE / "super-rar/index.json",
)


class CaveCatalogContainmentTests(unittest.TestCase):
    def test_every_catalog_entry_is_retired_and_non_streamable(self) -> None:
        for path in CATALOGS:
            document = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(document["status"], "retired", path)
            self.assertIs(document["active_distribution"], False, path)
            self.assertIs(document["streamable"], False, path)
            for group in ("agents", "rapps", "entries"):
                for entry in document.get(group, []):
                    self.assertEqual(entry["status"], "retired", (path, entry))
                    self.assertIs(
                        entry["active_distribution"], False, (path, entry)
                    )
                    self.assertIs(entry["streamable"], False, (path, entry))

    def test_steward_is_a_side_effect_free_refusal(self) -> None:
        path = CAVE / "agents/rar_steward_agent.py"
        source = path.read_text(encoding="utf-8")
        for marker in (
            "import subprocess",
            "import urllib",
            "urlopen(",
            "file_issues",
            "STEWARD_TRACKER",
            "INDEX_URL",
        ):
            self.assertNotIn(marker, source)

        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location("retired_rar_steward", path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        with self.assertRaisesRegex(RuntimeError, "^410 Gone:"):
            module.RarStewardAgent().perform(
                action="file_issues",
                confirm=True,
                tracker="example/repository",
            )

    def test_validator_has_no_write_or_rebuild_mode(self) -> None:
        before = {path: path.read_bytes() for path in CATALOGS}
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")

        check = subprocess.run(
            (sys.executable, "cave/tools/build_super_rar.py", "--check"),
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        self.assertIn("non-distributable", check.stdout)

        retired = subprocess.run(
            (sys.executable, "cave/tools/build_super_rar.py"),
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(retired.returncode, 2, retired.stdout + retired.stderr)
        self.assertIn("no rebuild or write mode exists", retired.stdout)
        self.assertEqual(before, {path: path.read_bytes() for path in CATALOGS})


if __name__ == "__main__":
    unittest.main()
