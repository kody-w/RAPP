"""Tests for tools/rapp1_receipts.py, the receipts' write mode.

Every test runs in memory against the committed tree: nothing is written.
"""

from __future__ import annotations

import errno
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rapp1_receipts as rr  # noqa: E402

FUTURE = "2099-01-01"
INVENTORY_FIELDS = {
    "$.snapshot.generated_at",
    "$.snapshot.tracked_path_count",
    "$.snapshot.tracked_path_set_sha256",
}
DOC_SCOPE_FIELDS = {
    "$.audit.current_inventory.tracked_paths",
    "$.audit.current_inventory.stable_tracked_bytes",
    "$.derived_document_scope.expected_tracked_document_count",
}


def _tracked() -> list[str]:
    return rr.git_tracked_paths(ROOT)


def _sizes(extra: dict[str, int] | None = None):
    real = rr.working_tree_size(ROOT)
    extra = extra or {}
    return lambda path: extra[path] if path in extra else real(path)


def _path_set_index(record_id: str) -> int:
    inventory = json.loads((ROOT / rr.INVENTORY).read_text(encoding="utf-8"))
    ids = [record["id"] for record in inventory["path_sets"]]
    return ids.index(record_id)


def _changed(before: bytes, after: bytes) -> dict[str, tuple[object, object]]:
    old = rr._leaves(json.loads(before))
    new = rr._leaves(json.loads(after))
    return {
        key: (old.get(key), new.get(key))
        for key in set(old) | set(new)
        if old.get(key) != new.get(key)
    }


def _path_set_fields(record_id: str) -> set[str]:
    index = _path_set_index(record_id)
    return {
        f"$.path_sets[{index}].expected_count",
        f"$.path_sets[{index}].path_set_sha256",
    }


def test_committed_receipts_are_current():
    result = rr.compute(ROOT, FUTURE)
    assert result.stale() == []
    assert result.expected == result.current


def test_values_follow_the_checks_rules():
    tracked = _tracked()
    result = rr.compute(ROOT, FUTURE)
    inventory = json.loads(result.expected[rr.INVENTORY])
    doc_scope = json.loads(result.expected[rr.DOC_SCOPE])
    assert inventory["snapshot"]["tracked_path_count"] == len(tracked)
    assert inventory["snapshot"]["tracked_path_set_sha256"] == rr.path_digest(tracked)
    current = doc_scope["audit"]["current_inventory"]
    assert current["tracked_paths"] == len(tracked)
    assert current["stable_tracked_bytes"] == sum(
        (ROOT / path).stat().st_size for path in tracked
    )
    assert doc_scope["derived_document_scope"]["expected_tracked_document_count"] == sum(
        Path(path).suffix.lower() in {".md", ".html"} for path in tracked
    )


def test_committed_layout_round_trips():
    for name in rr.RECEIPTS:
        data = (ROOT / name).read_bytes()
        assert rr.render(rr.load_receipt(data, name)) == data


def test_a_new_document_moves_only_the_derived_fields():
    new_path = ".synthetic/zz-new-card.md"
    result = rr.compute(
        ROOT, FUTURE, _tracked() + [new_path], _sizes({new_path: 1234})
    )
    assert result.stale() == list(rr.RECEIPTS)

    inventory = _changed(result.current[rr.INVENTORY], result.expected[rr.INVENTORY])
    assert set(inventory) == INVENTORY_FIELDS | _path_set_fields("PS-ALL")
    assert inventory["$.snapshot.generated_at"][1] == FUTURE
    old_count, new_count = inventory["$.snapshot.tracked_path_count"]
    assert new_count == old_count + 1

    doc_scope = _changed(result.current[rr.DOC_SCOPE], result.expected[rr.DOC_SCOPE])
    assert set(doc_scope) == DOC_SCOPE_FIELDS
    old_docs, new_docs = doc_scope[
        "$.derived_document_scope.expected_tracked_document_count"
    ]
    assert new_docs == old_docs + 1
    old_bytes, new_bytes = doc_scope["$.audit.current_inventory.stable_tracked_bytes"]
    growth = sum(
        len(result.expected[name]) - len(result.current[name]) for name in rr.RECEIPTS
    )
    assert new_bytes == old_bytes + 1234 + growth


def test_a_new_tool_moves_its_prefix_path_set_but_not_documents():
    new_path = "tools/zz_synthetic_tool.py"
    tracked = _tracked() + [new_path]
    result = rr.compute(ROOT, FUTURE, tracked, _sizes({new_path: 10}))

    inventory = _changed(result.current[rr.INVENTORY], result.expected[rr.INVENTORY])
    assert set(inventory) == (
        INVENTORY_FIELDS | _path_set_fields("PS-ALL") | _path_set_fields("PS-TOOLS")
    )
    record = json.loads(result.expected[rr.INVENTORY])["path_sets"][
        _path_set_index("PS-TOOLS")
    ]
    tools = [path for path in tracked if path.startswith("tools/")]
    assert record["expected_count"] == len(tools)
    assert record["path_set_sha256"] == rr.path_digest(tools)

    doc_scope = _changed(result.current[rr.DOC_SCOPE], result.expected[rr.DOC_SCOPE])
    assert set(doc_scope) == DOC_SCOPE_FIELDS - {
        "$.derived_document_scope.expected_tracked_document_count"
    }


def test_a_removed_path_shrinks_the_counts():
    tracked = _tracked()
    removed = next(
        path for path in tracked if path.startswith("pages/") and path.endswith(".html")
    )
    remaining = [path for path in tracked if path != removed]
    result = rr.compute(ROOT, FUTURE, remaining, _sizes())
    doc_scope = json.loads(result.expected[rr.DOC_SCOPE])
    assert doc_scope["audit"]["current_inventory"]["tracked_paths"] == len(tracked) - 1
    old = json.loads(result.current[rr.DOC_SCOPE])
    assert (
        doc_scope["derived_document_scope"]["expected_tracked_document_count"]
        == old["derived_document_scope"]["expected_tracked_document_count"] - 1
    )


def test_stable_bytes_counts_both_receipts_as_written():
    new_path = "zz-synthetic.txt"
    tracked = _tracked() + [new_path]
    result = rr.compute(ROOT, FUTURE, tracked, _sizes({new_path: 7}))
    written = result.expected
    recorded = json.loads(written[rr.DOC_SCOPE])["audit"]["current_inventory"][
        "stable_tracked_bytes"
    ]
    others = sum(
        (ROOT / path).stat().st_size
        for path in tracked
        if path not in rr.RECEIPTS and path != new_path
    )
    assert recorded == others + 7 + len(written[rr.INVENTORY]) + len(written[rr.DOC_SCOPE])


def test_generated_at_moves_only_with_the_snapshot():
    unchanged = rr.compute(ROOT, FUTURE)
    assert unchanged.expected[rr.INVENTORY] == unchanged.current[rr.INVENTORY]
    new_path = "zz-synthetic.txt"
    moved = rr.compute(ROOT, FUTURE, _tracked() + [new_path], _sizes({new_path: 1}))
    snapshot = json.loads(moved.expected[rr.INVENTORY])["snapshot"]
    assert snapshot["generated_at"] == FUTURE


def test_dated_evidence_is_never_rewritten():
    new_path = "docs/zz-synthetic.md"
    result = rr.compute(ROOT, FUTURE, _tracked() + [new_path], _sizes({new_path: 5}))
    old = json.loads(result.current[rr.DOC_SCOPE])
    new = json.loads(result.expected[rr.DOC_SCOPE])
    for key in set(old) - {"audit", "derived_document_scope"}:
        assert new[key] == old[key], key
    for key in set(old["audit"]) - {"current_inventory"}:
        assert new["audit"][key] == old["audit"][key], key
    scope = set(old["derived_document_scope"]) - {"expected_tracked_document_count"}
    for key in scope:
        assert new["derived_document_scope"][key] == old["derived_document_scope"][key]
    old_inventory = json.loads(result.current[rr.INVENTORY])
    new_inventory = json.loads(result.expected[rr.INVENTORY])
    for key in set(old_inventory) - {"snapshot", "path_sets"}:
        assert new_inventory[key] == old_inventory[key], key
    derived = {"expected_count", "path_set_sha256"}
    for before, after in zip(old_inventory["path_sets"], new_inventory["path_sets"]):
        assert {k: v for k, v in before.items() if k not in derived} == {
            k: v for k, v in after.items() if k not in derived
        }


def test_refuses_an_explicit_path_set_that_names_an_untracked_path():
    inventory = json.loads((ROOT / rr.INVENTORY).read_text(encoding="utf-8"))
    record = inventory["path_sets"][_path_set_index("PS-IMMUTABLE-GRAIL")]
    grail = record["selector"]["paths"][0]
    remaining = [path for path in _tracked() if path != grail]
    with pytest.raises(rr.ReceiptError, match="untracked paths"):
        rr.compute(ROOT, FUTURE, remaining, _sizes())


def test_refuses_a_tracked_path_missing_from_the_working_tree():
    missing = "zz-synthetic-missing.txt"
    with pytest.raises(rr.ReceiptError, match="not readable in the working tree"):
        rr.compute(ROOT, FUTURE, _tracked() + [missing])


def test_refuses_duplicate_keys_and_non_objects():
    with pytest.raises(rr.ReceiptError, match="duplicate JSON key"):
        rr.load_receipt(b'{"a": 1, "a": 2}', "x.json")
    with pytest.raises(rr.ReceiptError, match="must be an object"):
        rr.load_receipt(b"[]", "x.json")


def test_refuses_mutable_generated_paths_and_unknown_selectors():
    doc_scope = json.loads((ROOT / rr.DOC_SCOPE).read_text(encoding="utf-8"))
    doc_scope["audit"]["mutable_generated_paths"] = ["README.md"]
    with pytest.raises(rr.ReceiptError, match="mutable_generated_paths must be empty"):
        rr.refresh_doc_scope(doc_scope, _tracked(), _sizes(), b"")

    inventory = json.loads((ROOT / rr.INVENTORY).read_text(encoding="utf-8"))
    inventory["path_sets"][0]["selector"] = {"type": "glob", "pattern": "*"}
    with pytest.raises(rr.ReceiptError, match="unsupported selector type"):
        rr.refresh_inventory(inventory, _tracked(), FUTURE)


def test_changed_fields_names_each_stale_field():
    result = rr.compute(ROOT, FUTURE, _tracked() + ["zz.md"], _sizes({"zz.md": 3}))
    lines = rr.changed_fields(
        result.current[rr.DOC_SCOPE], result.expected[rr.DOC_SCOPE], rr.DOC_SCOPE
    )
    assert any(line.startswith("$.audit.current_inventory.tracked_paths: ") for line in lines)


def test_command_line_check_passes_on_the_committed_tree():
    completed = subprocess.run(
        (sys.executable, "-B", "tools/rapp1_receipts.py", "--check"),
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert completed.stdout.startswith("RAPP/1 receipts are current: ")


def test_command_line_rejects_a_bad_date():
    completed = subprocess.run(
        (sys.executable, "-B", "tools/rapp1_receipts.py", "--date", "26-09-2026"),
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 2
    assert "YYYY-MM-DD" in completed.stderr


def _recorded(result) -> int:
    return json.loads(result.expected[rr.DOC_SCOPE])["audit"]["current_inventory"][
        "stable_tracked_bytes"
    ]


def test_stable_bytes_is_a_fixed_point_across_a_digit_boundary():
    new_path = "zz-synthetic-large.bin"
    tracked = _tracked() + [new_path]
    empty = rr.compute(ROOT, FUTURE, tracked, _sizes({new_path: 0}))
    size = 10**8 - _recorded(empty)  # a one-pass sum would record exactly 10**8
    result = rr.compute(ROOT, FUTURE, tracked, _sizes({new_path: size}))
    written = result.expected
    others = sum(
        (ROOT / path).stat().st_size
        for path in tracked
        if path not in rr.RECEIPTS and path != new_path
    )
    total = others + size + len(written[rr.INVENTORY]) + len(written[rr.DOC_SCOPE])
    assert _recorded(result) == total == 10**8 + 1


def test_stable_bytes_counts_the_receipts_at_their_new_sizes():
    count = len(_tracked())
    extra = 10 ** len(str(count)) - count  # enough paths for the counts to gain a digit
    new_paths = [f"zz-synthetic/{index:06d}.txt" for index in range(extra)]
    tracked = _tracked() + new_paths
    result = rr.compute(ROOT, FUTURE, tracked, _sizes(dict.fromkeys(new_paths, 1)))
    written = result.expected
    for name in rr.RECEIPTS:  # the path counts gain a digit, so both receipts grow
        assert len(written[name]) > len(result.current[name]), name
    added = set(new_paths)
    others = sum(
        (ROOT / path).stat().st_size
        for path in tracked
        if path not in rr.RECEIPTS and path not in added
    )
    total = others + extra + len(written[rr.INVENTORY]) + len(written[rr.DOC_SCOPE])
    assert _recorded(result) == total


def test_a_rename_moves_the_snapshot_digest_with_the_same_count():
    tracked = _tracked()
    renamed = next(path for path in tracked if path.startswith("pages/"))
    moved = [path for path in tracked if path != renamed] + ["zz-synthetic/renamed.html"]
    result = rr.compute(ROOT, FUTURE, moved, _sizes({"zz-synthetic/renamed.html": 1}))
    snapshot = json.loads(result.expected[rr.INVENTORY])["snapshot"]
    assert snapshot["tracked_path_count"] == len(tracked)
    assert snapshot["tracked_path_set_sha256"] == rr.path_digest(moved)
    assert snapshot["generated_at"] == FUTURE


def test_explicit_path_sets_are_recomputed_duplicates_included():
    tracked = _tracked()
    inventory = json.loads((ROOT / rr.INVENTORY).read_text(encoding="utf-8"))
    index = _path_set_index("PS-IMMUTABLE-GRAIL")
    paths = inventory["path_sets"][index]["selector"]["paths"]
    paths.extend([paths[0], "README.md"])
    refreshed = rr.refresh_inventory(inventory, tracked, FUTURE)["path_sets"][index]
    assert refreshed["expected_count"] == len(paths)
    assert refreshed["path_set_sha256"] == rr.path_digest(sorted(paths))


def test_document_suffixes_match_in_any_case():
    new_paths = ["zz-synthetic/UPPER.MD", "zz-synthetic/Page.HTML", "zz-synthetic/notes.txt"]
    result = rr.compute(
        ROOT, FUTURE, _tracked() + new_paths, _sizes(dict.fromkeys(new_paths, 1))
    )
    before = json.loads(result.current[rr.DOC_SCOPE])["derived_document_scope"]
    after = json.loads(result.expected[rr.DOC_SCOPE])["derived_document_scope"]
    assert (
        after["expected_tracked_document_count"]
        == before["expected_tracked_document_count"] + 2
    )


def test_refuses_an_index_with_unmerged_paths(monkeypatch):
    def fake_git(command, cwd):
        return b"100644 " + b"0" * 40 + b" 1\tREADME.md\0" if "-u" in command else b""

    monkeypatch.setattr(rr.subprocess, "check_output", fake_git)
    with pytest.raises(rr.ReceiptError, match="unmerged paths"):
        rr.git_tracked_paths(ROOT)


def _stale_result():
    new_path = "zz-synthetic.txt"
    return rr.compute(ROOT, FUTURE, _tracked() + [new_path], _sizes({new_path: 1}))


def test_exit_codes_and_what_gets_written(monkeypatch, capsys):
    stale, current, writes = _stale_result(), rr.compute(ROOT, FUTURE), []
    assert current.stale() == []
    monkeypatch.setattr(rr, "compute", lambda root, today: stale)
    def record(root, result):
        writes.append(result)
        return result.stale()

    monkeypatch.setattr(rr, "write_receipts", record)
    assert rr.main(["--check"]) == 1 and rr.main([]) == 1 and writes == []
    out = capsys.readouterr().out
    assert "stale: RAPP1_ADAPTATION_INVENTORY.json $.snapshot.tracked_path_count" in out
    assert rr.main(["--write"]) == 0 and writes == [stale]

    monkeypatch.setattr(rr, "compute", lambda root, today: current)
    assert rr.main(["--write"]) == 0 and writes == [stale]  # a current tree writes nothing

    failures = (
        rr.ReceiptError("bad receipt"),
        FileNotFoundError("git"),
        subprocess.CalledProcessError(128, ("git", "ls-files")),
    )
    for failure in failures:
        def refuse(root, today, failure=failure):
            raise failure

        monkeypatch.setattr(rr, "compute", refuse)
        assert rr.main(["--write"]) == 2
    monkeypatch.setattr(rr, "compute", lambda root, today: stale)

    def unwritable(root, result):
        raise PermissionError("read-only")

    monkeypatch.setattr(rr, "write_receipts", unwritable)
    assert rr.main(["--write"]) == 2


def test_a_write_is_all_or_nothing(monkeypatch):
    stale, calls, live = _stale_result(), [], set()
    staged = iter(f"staged-{index}" for index in range(10))

    def stage(path, data):
        name = next(staged)
        calls.append(("stage", path.name, data))
        live.add(name)
        return name

    def replace(source, target):
        calls.append(("replace", source, Path(target).name))
        if source == "staged-1":
            raise OSError(errno.EIO, "input/output error")
        live.discard(source)

    monkeypatch.setattr(rr, "_stage", stage)
    monkeypatch.setattr(rr.os, "replace", replace)
    monkeypatch.setattr(rr.os.path, "exists", lambda path: path in live)
    monkeypatch.setattr(rr.os, "unlink", lambda path: calls.append(("unlink", path)))
    with pytest.raises(OSError):
        rr.write_receipts(ROOT, stale)
    inventory, doc_scope = Path(rr.INVENTORY).name, Path(rr.DOC_SCOPE).name
    assert calls == [
        ("stage", inventory, stale.expected[rr.INVENTORY]),
        ("stage", doc_scope, stale.expected[rr.DOC_SCOPE]),
        ("replace", "staged-0", inventory),
        ("replace", "staged-1", doc_scope),
        # the first receipt gets its old bytes back
        ("stage", inventory, stale.current[rr.INVENTORY]),
        ("replace", "staged-2", inventory),
        # the file that never moved is removed
        ("unlink", "staged-1"),
    ]


def test_a_staged_file_sits_beside_its_receipt_with_its_mode(monkeypatch):
    target = ROOT / rr.DOC_SCOPE
    made, modes = [], []

    def mkstemp(dir, prefix):
        made.append((Path(dir), prefix))
        return os.open(os.devnull, os.O_WRONLY), "staged-name"

    monkeypatch.setattr(rr.tempfile, "mkstemp", mkstemp)
    monkeypatch.setattr(rr.os, "chmod", lambda path, mode: modes.append((path, mode)))
    assert rr._stage(target, b"data") == "staged-name"
    assert made == [(target.parent, f".{target.name}.")]
    assert modes == [("staged-name", target.stat().st_mode & 0o7777)]
