#!/usr/bin/env python3
"""Check or rewrite the derived fields of RAPP's two tracked-tree receipts.

Two committed receipts restate facts about the tracked tree:

* ``RAPP1_ADAPTATION_INVENTORY.json``: ``snapshot.tracked_path_count`` and
  ``snapshot.tracked_path_set_sha256``, plus ``expected_count`` and
  ``path_set_sha256`` of every ``path_sets`` record (checked by
  ``tests/test_adaptation_inventory.py``).
* ``tests/fixtures/rapp1-doc-scope.json``: ``audit.current_inventory``
  (``tracked_paths`` and ``stable_tracked_bytes``) and
  ``derived_document_scope.expected_tracked_document_count`` (checked by
  ``tools/check_rapp1_docs.py``).

This tool recomputes exactly those fields with the rules of those checks,
from ``git ls-files`` (the index) and the working tree. ``--check`` (the
default) reports stale fields and exits 1; ``--write`` rewrites them in
place. ``snapshot.generated_at`` is set to ``--date`` (default: today, UTC)
only when the snapshot's path count or path-set digest changes.

Nothing else is ever rewritten. Classification rules, surfaces,
dispositions, exclusions, and the dated audit evidence stay hand-authored and
are validated by their own checks. Stage added and removed files first
(``git add``), because the checks read the index.

Exit codes: 0 current (or written), 1 stale, 2 refused (nothing is written:
a write stages both files first and restores the old bytes if a move fails).
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = "RAPP1_ADAPTATION_INVENTORY.json"
DOC_SCOPE = "tests/fixtures/rapp1-doc-scope.json"
RECEIPTS = (INVENTORY, DOC_SCOPE)


class ReceiptError(Exception):
    """A receipt or the tracked tree cannot be refreshed safely."""


@dataclass(frozen=True)
class Refresh:
    """The current and recomputed bytes of both receipts."""

    current: dict[str, bytes]
    expected: dict[str, bytes]
    tracked_paths: int
    documents: int
    stable_bytes: int

    def stale(self) -> list[str]:
        return [name for name in RECEIPTS if self.current[name] != self.expected[name]]


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ReceiptError(f"duplicate JSON key {key!r}")
        value[key] = item
    return value


def load_receipt(data: bytes, name: str) -> dict[str, Any]:
    try:
        value = json.loads(
            data.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except ReceiptError as exc:
        raise ReceiptError(f"{name}: {exc}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReceiptError(f"{name}: not valid UTF-8 JSON ({exc})") from exc
    if not isinstance(value, dict):
        raise ReceiptError(f"{name}: the top level must be an object")
    return value


def render(value: dict[str, Any]) -> bytes:
    """The receipts' committed layout: two-space indent, UTF-8, final LF."""

    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def path_digest(paths: list[str]) -> str:
    """SHA-256 of sorted UTF-8 paths, each terminated by LF."""

    payload = "".join(f"{path}\n" for path in sorted(paths))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def git_tracked_paths(root: Path) -> list[str]:
    """The index's paths, as both checks read them."""

    unmerged = subprocess.check_output(("git", "ls-files", "-u", "-z"), cwd=root)
    if unmerged.strip(b"\0"):
        raise ReceiptError("the index has unmerged paths; resolve them first")
    raw = subprocess.check_output(("git", "ls-files", "-z"), cwd=root)
    try:
        return sorted(item.decode("utf-8") for item in raw.split(b"\0") if item)
    except UnicodeDecodeError as exc:
        raise ReceiptError(f"a tracked path is not UTF-8 ({exc})") from exc


def working_tree_size(root: Path) -> Callable[[str], int]:
    def size_of(relative: str) -> int:
        try:
            return (root / relative).stat().st_size
        except OSError as exc:
            raise ReceiptError(
                f"{relative}: tracked but not readable in the working tree "
                f"({exc.strerror}); restore it or stage its removal"
            ) from exc

    return size_of


def _object(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReceiptError(f"{where} must be an object")
    return value


def _strings(value: Any, where: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ReceiptError(f"{where} must be a list of strings")
    return value


def refresh_inventory(
    inventory: dict[str, Any], tracked: list[str], today: str
) -> dict[str, Any]:
    """Recompute the inventory's snapshot and path-set counts and digests."""

    refreshed = copy.deepcopy(inventory)
    snapshot = _object(refreshed.get("snapshot"), f"{INVENTORY}: snapshot")
    count, digest = len(tracked), path_digest(tracked)
    if (
        snapshot.get("tracked_path_count") != count
        or snapshot.get("tracked_path_set_sha256") != digest
    ):
        snapshot["generated_at"] = today
        snapshot["tracked_path_count"] = count
        snapshot["tracked_path_set_sha256"] = digest

    path_sets = refreshed.get("path_sets")
    if not isinstance(path_sets, list):
        raise ReceiptError(f"{INVENTORY}: path_sets must be a list")
    known = set(tracked)
    for index, record in enumerate(path_sets):
        record = _object(record, f"{INVENTORY}: path_sets[{index}]")
        label = f"{INVENTORY}: path set {record.get('id', index)!r}"
        selector = _object(record.get("selector"), f"{label} selector")
        kind = selector.get("type")
        if kind == "git-prefix":
            prefix = selector.get("prefix")
            if not isinstance(prefix, str):
                raise ReceiptError(f"{label}: prefix must be a string")
            paths = [path for path in tracked if path.startswith(prefix)]
        elif kind == "explicit":
            paths = sorted(_strings(selector.get("paths"), f"{label} paths"))
            untracked = [path for path in paths if path not in known]
            if untracked:
                raise ReceiptError(
                    f"{label} lists untracked paths {untracked}; "
                    "fix the declaration by hand"
                )
        else:
            raise ReceiptError(f"{label}: unsupported selector type {kind!r}")
        record["expected_count"] = len(paths)
        record["path_set_sha256"] = path_digest(paths)
    return refreshed


def refresh_doc_scope(
    doc_scope: dict[str, Any],
    tracked: list[str],
    size_of: Callable[[str], int],
    inventory_bytes: bytes,
) -> tuple[dict[str, Any], bytes]:
    """Recompute the fixture's current counts; return it and its bytes.

    ``stable_tracked_bytes`` includes both receipts' own sizes, so it is
    solved as a fixed point over the bytes that will be written.
    """

    refreshed = copy.deepcopy(doc_scope)
    audit = _object(refreshed.get("audit"), f"{DOC_SCOPE}: audit")
    current = _object(
        audit.get("current_inventory"), f"{DOC_SCOPE}: audit.current_inventory"
    )
    if audit.get("mutable_generated_paths") != []:
        raise ReceiptError(
            f"{DOC_SCOPE}: audit.mutable_generated_paths must be empty "
            "(tools/check_rapp1_docs.py requires it)"
        )
    scope = _object(
        refreshed.get("derived_document_scope"),
        f"{DOC_SCOPE}: derived_document_scope",
    )
    extensions = _strings(
        scope.get("extensions"), f"{DOC_SCOPE}: derived_document_scope.extensions"
    )

    current["tracked_paths"] = len(tracked)
    scope["expected_tracked_document_count"] = sum(
        PurePosixPath(path).suffix.lower() in extensions for path in tracked
    )
    others = sum(size_of(path) for path in tracked if path not in RECEIPTS)
    inventory_size = len(inventory_bytes) if INVENTORY in tracked else 0

    value = current.get("stable_tracked_bytes")
    if not isinstance(value, int) or isinstance(value, bool):
        value = 0
    for _ in range(16):
        current["stable_tracked_bytes"] = value
        data = render(refreshed)
        total = others + inventory_size + (len(data) if DOC_SCOPE in tracked else 0)
        if total == value:
            return refreshed, data
        value = total
    raise ReceiptError(f"{DOC_SCOPE}: stable_tracked_bytes did not converge")


def compute(
    root: Path,
    today: str,
    tracked: list[str] | None = None,
    size_of: Callable[[str], int] | None = None,
) -> Refresh:
    """Recompute both receipts for ``root`` without writing anything."""

    tracked = git_tracked_paths(root) if tracked is None else sorted(tracked)
    size_of = working_tree_size(root) if size_of is None else size_of
    current: dict[str, bytes] = {}
    for name in RECEIPTS:
        try:
            current[name] = (root / name).read_bytes()
        except OSError as exc:
            raise ReceiptError(f"{name}: cannot read ({exc.strerror})") from exc
    inventory = refresh_inventory(
        load_receipt(current[INVENTORY], INVENTORY), tracked, today
    )
    inventory_bytes = render(inventory)
    doc_scope, doc_scope_bytes = refresh_doc_scope(
        load_receipt(current[DOC_SCOPE], DOC_SCOPE), tracked, size_of, inventory_bytes
    )
    return Refresh(
        current=current,
        expected={INVENTORY: inventory_bytes, DOC_SCOPE: doc_scope_bytes},
        tracked_paths=len(tracked),
        documents=doc_scope["derived_document_scope"]["expected_tracked_document_count"],
        stable_bytes=doc_scope["audit"]["current_inventory"]["stable_tracked_bytes"],
    )


def _leaves(value: Any, where: str = "$") -> dict[str, Any]:
    if isinstance(value, dict):
        items: dict[str, Any] = {}
        for key, child in value.items():
            items.update(_leaves(child, f"{where}.{key}"))
        return items or {where: {}}
    if isinstance(value, list):
        items = {}
        for index, child in enumerate(value):
            items.update(_leaves(child, f"{where}[{index}]"))
        return items or {where: []}
    return {where: value}


def changed_fields(before: bytes, after: bytes, name: str) -> list[str]:
    """Readable ``path: old -> new`` lines for one receipt."""

    old = _leaves(load_receipt(before, name))
    new = _leaves(load_receipt(after, name))
    lines = [
        f"{key}: {json.dumps(old.get(key))} -> {json.dumps(new.get(key))}"
        for key in sorted(set(old) | set(new))
        if old.get(key) != new.get(key)
    ]
    return lines or ["layout differs from the committed two-space rendering"]


def _stage(path: Path, data: bytes) -> str:
    """Write `data` to a new file beside `path`, with `path`'s mode; return its name."""
    mode = path.stat().st_mode & 0o7777
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
        os.chmod(temporary, mode)
    except BaseException:
        os.unlink(temporary)
        raise
    return temporary


def write_receipts(root: Path, result: Refresh) -> list[str]:
    """Write every stale receipt, all or nothing.

    Each new file is staged beside its receipt first, then moved into place;
    when a move fails, the receipts already moved get their old bytes back.
    """
    stale = result.stale()
    staged: list[tuple[str, str]] = []
    try:
        for name in stale:
            staged.append((name, _stage(root / name, result.expected[name])))
        moved: list[str] = []
        try:
            for name, temporary in staged:
                os.replace(temporary, root / name)
                moved.append(name)
        except OSError:
            for name in moved:
                os.replace(_stage(root / name, result.current[name]), root / name)
            raise
    finally:
        for _, temporary in staged:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return stale


def _date(text: str) -> str:
    try:
        return dt.date.fromisoformat(text).isoformat()
    except ValueError as exc:
        raise argparse.ArgumentTypeError("use YYYY-MM-DD") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Check or rewrite the tracked-tree fields of "
            f"{INVENTORY} and {DOC_SCOPE}."
        )
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check", action="store_true", help="report stale fields (the default)"
    )
    mode.add_argument(
        "--write", action="store_true", help="rewrite stale fields in place"
    )
    parser.add_argument(
        "--date",
        type=_date,
        default=dt.datetime.now(dt.timezone.utc).date().isoformat(),
        help="snapshot.generated_at when the snapshot changes (default: today, UTC)",
    )
    args = parser.parse_args(argv)

    try:
        result = compute(ROOT, args.date)
    except (ReceiptError, subprocess.CalledProcessError, OSError) as exc:
        print(f"rapp1_receipts: refused: {exc}", file=sys.stderr)
        return 2

    summary = (
        f"{result.tracked_paths} tracked paths, {result.documents} documents, "
        f"{result.stable_bytes} stable bytes"
    )
    stale = result.stale()
    if not stale:
        print(f"RAPP/1 receipts are current: {summary}")
        return 0
    if not args.write:
        for name in stale:
            for line in changed_fields(result.current[name], result.expected[name], name):
                print(f"stale: {name} {line}")
        sys.stdout.flush()
        print("run: python3 tools/rapp1_receipts.py --write", file=sys.stderr)
        return 1
    try:
        written = write_receipts(ROOT, result)
    except OSError as exc:
        print(f"rapp1_receipts: refused: nothing written ({exc})", file=sys.stderr)
        return 2
    for name in written:
        print(f"wrote {name}")
    print(f"RAPP/1 receipts are current: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
