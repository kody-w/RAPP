#!/usr/bin/env python3
"""Check the explicit current-document set for retired RAPP teachings."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
SCOPE_PATH = ROOT / "tests/fixtures/rapp1-doc-scope.json"
AUTHORITY_TOPICS = (
    "canonicalization",
    "identity",
    "frame",
    "wire",
    "egg",
    "registry",
    "trust",
    "evolution",
)
RETIRED_PATTERNS = (
    re.compile(r"\brapp-frame/\d", re.IGNORECASE),
    re.compile(r"\bbrainstem-egg/\d", re.IGNORECASE),
    re.compile(r"\brapp-egg/\d", re.IGNORECASE),
    re.compile(r"\brapp-rappid/\d", re.IGNORECASE),
    re.compile(r"\brapp-eternity/1\.0\b", re.IGNORECASE),
    re.compile(r"\brapp-protocol/1\.0\b", re.IGNORECASE),
    re.compile(r"\brapp-chat-response/1\.0\b", re.IGNORECASE),
    re.compile(r"\brappid:v2\b", re.IGNORECASE),
    re.compile(r"\bread(?:\s+|-)?forever\b", re.IGNORECASE),
    re.compile(r"\bread.compat(?:ibility|ible)\b", re.IGNORECASE),
    re.compile(r"\bbackwards?-compat(?:ibility|ible)?\b", re.IGNORECASE),
    re.compile(r"\bconversation_history\b", re.IGNORECASE),
    re.compile(r"\buuidv?5\b", re.IGNORECASE),
    re.compile(r"sha256\s*\(\s*[\"']?(?:owner|slug)", re.IGNORECASE),
    re.compile(r"hashlib\.sha256\s*\(\s*owner_repo", re.IGNORECASE),
)
CONTEXT_MARKERS = (
    "historical",
    "legacy",
    "migration",
    "migrate",
    "retired",
    "superseded",
    "non-rapp/1",
    "not current",
    "do not emit",
    "must not emit",
    "rapp1_authority.json",
    "rapp/1 §",
)
HISTORICAL_SECTION_START = "<!-- RAPP1-HISTORICAL-SECTION-START -->"
HISTORICAL_SECTION_END = "<!-- RAPP1-HISTORICAL-SECTION-END -->"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def load_scope() -> dict:
    with SCOPE_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def safe_path(relative: str) -> Path:
    posix_path = PurePosixPath(relative)
    if posix_path.is_absolute() or ".." in posix_path.parts:
        raise ValueError(f"unsafe documentation path: {relative}")
    return ROOT.joinpath(*posix_path.parts)


def authority_failures(relative: str, text: str) -> list[str]:
    lowered = text.lower()
    failures = []
    for required in ("RAPP1_AUTHORITY.json", "RAPP1_STATUS.md", "rev-5"):
        if required.lower() not in lowered:
            failures.append(f"{relative}: missing {required} authority declaration")
    missing_topics = [topic for topic in AUTHORITY_TOPICS if topic not in lowered]
    if missing_topics:
        failures.append(
            f"{relative}: authority declaration omits {', '.join(missing_topics)}"
        )
    return failures


def authority_link_failures(relative: str, path: Path, text: str) -> list[str]:
    failures = []
    for name in ("RAPP1_AUTHORITY.json", "RAPP1_STATUS.md"):
        candidates = re.findall(
            rf"(?<![A-Za-z0-9_.-])((?:\.\.?/)*{re.escape(name)})", text
        )
        target = (ROOT / name).resolve()
        if not any(
            (path.parent / candidate).resolve() == target
            and (path.parent / candidate).is_file()
            for candidate in candidates
        ):
            failures.append(f"{relative}: no resolving local link to {name}")
    return failures


def historical_marker_failures(relative: str, text: str) -> list[str]:
    failures = []
    in_historical_section = False
    for line_number, line in enumerate(text.splitlines(), start=1):
        if HISTORICAL_SECTION_START in line:
            if in_historical_section:
                failures.append(
                    f"{relative}:{line_number}: nested historical-section start"
                )
            in_historical_section = True
        if HISTORICAL_SECTION_END in line:
            if not in_historical_section:
                failures.append(
                    f"{relative}:{line_number}: historical-section end without start"
                )
            in_historical_section = False
    if in_historical_section:
        failures.append(f"{relative}: historical section has no end marker")
    return failures


def retired_token_failures(relative: str, text: str) -> list[str]:
    lines = text.splitlines()
    failures = []
    in_historical_section = False
    for line_number, line in enumerate(lines, start=1):
        if HISTORICAL_SECTION_START in line:
            in_historical_section = True
            continue
        if HISTORICAL_SECTION_END in line:
            in_historical_section = False
            continue
        for pattern in RETIRED_PATTERNS:
            if not pattern.search(line):
                continue
            if in_historical_section:
                continue
            lowered_line = line.lower()
            if "resolved" in lowered_line and "~~" in line:
                continue
            start = max(0, line_number - 7)
            end = min(len(lines), line_number + 6)
            context = "\n".join(lines[start:end]).lower()
            if not any(marker in context for marker in CONTEXT_MARKERS):
                failures.append(
                    f"{relative}:{line_number}: retired teaching lacks a nearby "
                    "history/migration marker or RAPP/1 authority reference"
                )
    return failures


def audit_scope_failures(
    scope: dict, managed: set[str], excluded: set[str]
) -> list[str]:
    failures = []
    audit_scope = scope.get("audit_scope")
    if not isinstance(audit_scope, dict):
        return ["scope: audit_scope must record audit provenance"]

    ledger = audit_scope.get("r1_doc_01")
    if not isinstance(ledger, dict):
        failures.append("scope: audit_scope.r1_doc_01 must be an object")
    else:
        paths = ledger.get("paths")
        expected_count = ledger.get("path_count")
        if not isinstance(paths, list) or not paths:
            failures.append("scope: R1-DOC-01 paths must be a non-empty list")
        else:
            unique_paths = set(paths)
            if len(unique_paths) != len(paths):
                failures.append("scope: R1-DOC-01 paths contain duplicates")
            if expected_count != len(paths):
                failures.append(
                    "scope: R1-DOC-01 path_count does not match its path list"
                )
            for relative in sorted(unique_paths - managed - excluded):
                failures.append(
                    f"scope: R1-DOC-01 path {relative} is not checked or excluded"
                )
        if not SHA256_PATTERN.fullmatch(str(ledger.get("sha256", ""))):
            failures.append("scope: R1-DOC-01 source has no valid SHA-256")

    canon = audit_scope.get("canon_mirrors")
    if not isinstance(canon, dict):
        failures.append("scope: audit_scope.canon_mirrors must be an object")
    else:
        if not SHA256_PATTERN.fullmatch(str(canon.get("sha256", ""))):
            failures.append("scope: canon-mirrors source has no valid SHA-256")
        for name in (
            "live_declarations_section",
            "historical_section",
            "generated_section",
        ):
            if not str(canon.get(name, "")).strip():
                failures.append(f"scope: canon-mirrors {name} is missing")
        live_paths = canon.get("live_paths")
        if not isinstance(live_paths, list) or not live_paths:
            failures.append(
                "scope: canon-mirrors live_paths must be a non-empty list"
            )
        else:
            unique_live_paths = set(live_paths)
            if len(unique_live_paths) != len(live_paths):
                failures.append("scope: canon-mirrors live_paths contain duplicates")
            if canon.get("live_path_count") != len(live_paths):
                failures.append(
                    "scope: canon-mirrors live_path_count does not match its path list"
                )
            for relative in sorted(unique_live_paths - managed - excluded):
                failures.append(
                    f"scope: canon §7.1 path {relative} is not checked or excluded"
                )
    return failures


def check_docs(scope: dict | None = None) -> list[str]:
    scope = scope or load_scope()
    failures = []
    groups = (
        "current_documents",
        "superseded_documents",
        "historical_documents",
    )
    seen: set[str] = set()
    for group in groups:
        entries = scope.get(group)
        if not isinstance(entries, list) or not entries:
            failures.append(f"scope: {group} must be a non-empty list")
            continue
        for relative in entries:
            if relative in seen:
                failures.append(f"scope: duplicate path {relative}")
                continue
            seen.add(relative)
            try:
                path = safe_path(relative)
            except ValueError as error:
                failures.append(str(error))
                continue
            if not path.is_file():
                failures.append(f"{relative}: allowlisted document is missing")
                continue
            text = path.read_text(encoding="utf-8")
            failures.extend(authority_failures(relative, text))
            failures.extend(authority_link_failures(relative, path, text))
            failures.extend(historical_marker_failures(relative, text))
            lowered = text.lower()
            if group == "current_documents":
                failures.extend(retired_token_failures(relative, text))
            elif group == "superseded_documents" and "superseded" not in lowered:
                failures.append(f"{relative}: missing superseded-document marker")
            elif group == "historical_documents" and not (
                "historical" in lowered or "superseded" in lowered
            ):
                failures.append(f"{relative}: missing historical-document marker")

    excluded = scope.get("excluded_documents")
    if not isinstance(excluded, dict) or not excluded:
        failures.append("scope: excluded_documents must record explicit exclusions")
        excluded_paths: set[str] = set()
    else:
        excluded_paths = set(excluded)
        overlap = seen.intersection(excluded)
        for relative in sorted(overlap):
            failures.append(f"scope: {relative} is both checked and excluded")
        for relative, reason in excluded.items():
            if not isinstance(reason, str) or not reason.strip():
                failures.append(f"scope: excluded path {relative} has no reason")
            try:
                path = safe_path(relative)
            except ValueError as error:
                failures.append(str(error))
                continue
            if not path.is_file():
                failures.append(f"{relative}: excluded document is missing")

    failures.extend(audit_scope_failures(scope, seen, excluded_paths))
    return failures


def main() -> int:
    failures = check_docs()
    if failures:
        print("RAPP/1 documentation gate failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    scope = load_scope()
    count = sum(
        len(scope[group])
        for group in (
            "current_documents",
            "superseded_documents",
            "historical_documents",
        )
    )
    ledger_paths = set(scope["audit_scope"]["r1_doc_01"]["paths"])
    managed = set().union(
        *(
            set(scope[group])
            for group in (
                "current_documents",
                "superseded_documents",
                "historical_documents",
            )
        )
    )
    managed_ledger = len(ledger_paths & managed)
    excluded_ledger = len(ledger_paths - managed)
    canon_paths = set(scope["audit_scope"]["canon_mirrors"]["live_paths"])
    managed_canon = len(canon_paths & managed)
    excluded_canon = len(canon_paths - managed)
    print(
        "RAPP/1 documentation gate passed "
        f"({count} managed documents; R1-DOC-01 ledger: "
        f"{managed_ledger} managed, {excluded_ledger} explicitly excluded; "
        f"canon §7.1: {managed_canon} managed, "
        f"{excluded_canon} explicitly excluded)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
