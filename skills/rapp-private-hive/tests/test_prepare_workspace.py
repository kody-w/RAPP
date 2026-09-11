from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import types
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "prepare_workspace.py"
SPEC = importlib.util.spec_from_file_location("prepare_workspace", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class WorkspacePreparationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = Path(tempfile.mkdtemp(prefix="rapp-private-hive-test-"))
        self.addCleanup(shutil.rmtree, self.temporary)
        self.workspace = self.temporary / "workspace"
        self.workspace.mkdir()
        self.member = "rappid:@alice/member:" + "1" * 64
        self.workspace_rappid = "rappid:@alice/workspace:" + "2" * 64
        (self.workspace / "rappid.json").write_text(
            json.dumps({"schema": "rapp/1", "rappid": self.workspace_rappid, "mode": "solo"}),
            encoding="utf-8",
        )
        (self.workspace / "notes").mkdir()
        (self.workspace / "notes" / "private.md").write_text("private GODD", encoding="utf-8")
        (self.workspace / "dogg").mkdir()
        (self.workspace / "dogg" / "template.json").write_text('{"safe":true}', encoding="utf-8")
        self.before = {
            path.relative_to(self.workspace).as_posix(): path.read_bytes()
            for path in self.workspace.rglob("*")
            if path.is_file()
        }

    def args(self, **values):
        return types.SimpleNamespace(**values)

    def prepare(self):
        return MODULE.command_prepare(
            self.args(
                workspace=str(self.workspace),
                member_rappid=self.member,
                hive_name="alice-private-hive",
                world_id="alice-world",
            )
        )

    def assert_original_bytes_unchanged(self):
        for relative, expected in self.before.items():
            self.assertEqual((self.workspace / relative).read_bytes(), expected)

    def test_prepare_is_additive_and_idempotent(self):
        first = self.prepare()
        second = self.prepare()
        self.assertEqual(first["status"], "prepared")
        self.assertEqual(second["status"], "already-prepared")
        self.assert_original_bytes_unchanged()
        selection = MODULE.read_json(self.workspace / ".rapp-hive" / "selection.json")
        self.assertEqual(selection["default"], "local-only")
        self.assertEqual(selection["entries"], [])

    def test_dogg_requires_pii_evidence_and_stages_by_copy(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, "pii"):
            MODULE.command_select(
                self.args(
                    workspace=str(self.workspace),
                    path="dogg/template.json",
                    data_class="dogg",
                    room="general",
                    protection=None,
                    pii_evidence_hash=None,
                )
            )
        evidence = hashlib.sha256(b"fictional PII scan").hexdigest()
        selected = MODULE.command_select(
            self.args(
                workspace=str(self.workspace),
                path="dogg/template.json",
                data_class="dogg",
                room="general",
                protection=None,
                pii_evidence_hash=evidence,
            )
        )
        outbox = self.temporary / "outbox"
        staged = MODULE.command_stage(
            self.args(workspace=str(self.workspace), outbox=str(outbox))
        )
        self.assertEqual(selected["entry"]["pii_status"], "none")
        self.assertEqual(staged["staged"], 1)
        self.assertTrue((Path(staged["outbox"]) / "objects" / "dogg" / "template.json").is_file())
        self.assert_original_bytes_unchanged()

    def test_plaintext_godd_never_enters_outbox(self):
        self.prepare()
        selected = MODULE.command_select(
            self.args(
                workspace=str(self.workspace),
                path="notes/private.md",
                data_class="godd",
                room="private",
                protection="sealed-room",
                pii_evidence_hash=None,
            )
        )
        outbox = self.temporary / "outbox"
        staged = MODULE.command_stage(
            self.args(workspace=str(self.workspace), outbox=str(outbox))
        )
        self.assertEqual(selected["entry"]["status"], "pending-seal")
        self.assertEqual(staged["staged"], 0)
        self.assertEqual(staged["pending_godd"], ["notes/private.md"])
        self.assertFalse(any(path.name == "private.md" for path in outbox.rglob("*")))
        self.assert_original_bytes_unchanged()

    def test_changed_selection_refuses_staging_without_deleting_source(self):
        self.prepare()
        evidence = hashlib.sha256(b"fictional PII scan").hexdigest()
        MODULE.command_select(
            self.args(
                workspace=str(self.workspace),
                path="dogg/template.json",
                data_class="dogg",
                room="general",
                protection=None,
                pii_evidence_hash=evidence,
            )
        )
        source = self.workspace / "dogg" / "template.json"
        source.write_text('{"safe":true,"evolved":true}', encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "reselect"):
            MODULE.command_stage(
                self.args(workspace=str(self.workspace), outbox=str(self.temporary / "outbox"))
            )
        self.assertTrue(source.is_file())

    def test_skill_lock_matches_every_managed_file(self):
        skill_root = Path(__file__).resolve().parents[1]
        lock = json.loads((skill_root / "rapp" / "agent.lock.json").read_text(encoding="utf-8"))
        self.assertEqual(lock["schema"], "rapp-skill-lock/1")
        self.assertEqual(lock["name"], "rapp-private-hive")
        for entry in lock["files"]:
            path = skill_root / entry["path"]
            self.assertTrue(path.is_file(), entry["path"])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), entry["sha256"])


if __name__ == "__main__":
    unittest.main()
