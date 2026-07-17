#!/usr/bin/env python3
"""Fail-closed documentation gate for the dated RAPP/1 post-audit ledger."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "rapp1-doc-scope.json"


def _load_fixture() -> dict[str, Any]:
    try:
        return json.loads(FIXTURE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load {FIXTURE.relative_to(ROOT)}: {exc}") from exc


def _read(relative_path: str) -> str:
    path = ROOT / relative_path
    if not path.is_file():
        raise ValueError(f"{relative_path}: required file is missing")
    return path.read_text(encoding="utf-8")


def _path_set_digest(paths: list[str]) -> str:
    payload = "".join(f"{path}\n" for path in sorted(paths))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _strip_historical_sections(
    text: str, start_marker: str, end_marker: str
) -> tuple[str, list[str]]:
    """Return active text and marker-structure errors."""

    active: list[str] = []
    errors: list[str] = []
    in_history = False
    for line_number, line in enumerate(text.splitlines(), start=1):
        has_start = start_marker in line
        has_end = end_marker in line
        if has_start:
            if in_history:
                errors.append(f"nested historical start marker at line {line_number}")
            in_history = True
        if not in_history and not has_start and not has_end:
            active.append(line)
        if has_end:
            if not in_history:
                errors.append(f"historical end marker without start at line {line_number}")
            in_history = False
    if in_history:
        errors.append("unclosed historical section")
    return "\n".join(active), errors


def _has_authority_link(text: str) -> bool:
    return "RAPP1_AUTHORITY.json" in text or "/rapp-1/" in text


def _has_status_link(text: str) -> bool:
    return "RAPP1_STATUS.md" in text


def _has_authority_topics(text: str, topics: list[str]) -> bool:
    lowered = text.lower()
    variants = {
        "canonicalization": ("canonicalization", "canonical"),
        "identity": ("identity", "rappid"),
        "frames": ("frames", "frame"),
        "wire": ("wire", "chat"),
        "eggs": ("eggs", "egg"),
        "registry": ("registry",),
        "trust": ("trust",),
        "protocol evolution": ("protocol evolution", "evolution"),
    }
    return all(
        any(token in lowered for token in variants.get(topic, (topic,)))
        for topic in topics
    )


def _is_negated_context(text: str, start: int, end: int) -> bool:
    context = text[max(0, start - 100) : min(len(text), end + 100)]
    return bool(
        re.search(
            r"\b(?:no|not|never|without|retired|historical|inert|do not|"
            r"must not|isn't|aren't|wasn't|weren't)\b",
            context,
            flags=re.IGNORECASE,
        )
    )


def _validate_fixture(fixture: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if fixture.get("schema_version") != "rapp1-documentation-scope/2.0":
        errors.append("fixture: unsupported schema_version")

    audit = fixture.get("audit")
    if not isinstance(audit, dict):
        return errors + ["fixture: audit must be an object"]
    if audit.get("source") != "post-docs-target-ledger":
        errors.append("fixture: audit source must be post-docs-target-ledger")
    if audit.get("baseline_tracked_paths") != 640:
        errors.append("fixture: dated baseline must remain 640 paths")
    if audit.get("post_audit_tracked_paths") != 691:
        errors.append("fixture: post-audit inventory must be 691 paths")
    tracked_paths = [
        path
        for path in subprocess.check_output(
            ("git", "ls-files", "-z"), cwd=ROOT
        ).decode("utf-8").split("\0")
        if path
    ]
    if len(tracked_paths) != audit.get("post_audit_tracked_paths"):
        errors.append(
            "fixture: post-audit tracked-path count does not match git ls-files "
            f"({len(tracked_paths)} != {audit.get('post_audit_tracked_paths')})"
        )

    provenance = audit.get("provenance", {})
    existing_report = provenance.get("existing_report", {})
    if existing_report.get("source") != "verify-rapp-files":
        errors.append("fixture: existing report source must be verify-rapp-files")
    expected_report_fields = {
        "report_sha256": (
            "9ac01e164dc0eb820d5f53afed82f53c501059c18a8bf66b8b23c533af728ce7"
        ),
        "scope_commit": "f71810db3259fea533b4112c1df300d4b0dc781c",
        "tracked_path_count": 640,
    }
    for field, expected in expected_report_fields.items():
        if existing_report.get(field) != expected:
            errors.append(f"fixture: existing report {field} does not match evidence")
    definitions = existing_report.get("definitions", {})
    expected_definitions = {
        "current-live": (
            "an active implementation/declaration/document that readers, tooling, "
            "or runtime may treat as current authority"
        ),
        "R1-DOC-01": (
            "current documentation re-specifies or advertises a retired "
            "identity/frame/wire/egg/protocol contract instead of subordinating "
            "itself to root SPEC.md"
        ),
        "excluded_from_stale_live": (
            "Genuine dated history, fixtures, generated observations, immutable "
            "snapshots, and unrelated material were not treated as stale-live "
            "merely for containing retired vocabulary."
        ),
    }
    if definitions != expected_definitions:
        errors.append("fixture: original stale-live definitions do not match evidence")

    original_r1_doc = existing_report.get("R1-DOC-01", {})
    original_current = original_r1_doc.get("current_live_paths", [])
    original_mirrors = original_r1_doc.get("mirror_paths", [])
    original_all = original_current + original_mirrors
    original_counts = (
        original_r1_doc.get("expected_count"),
        original_r1_doc.get("current_live_count"),
        original_r1_doc.get("mirror_count"),
    )
    if original_counts != (56, 53, 3):
        errors.append("fixture: original R1-DOC-01 counts must remain 56/53/3")
    if len(set(original_all)) != 56:
        errors.append("fixture: original R1-DOC-01 paths must be 56 unique paths")
    for field, paths in (
        ("path_set_sha256", original_all),
        ("current_live_path_set_sha256", original_current),
        ("mirror_path_set_sha256", original_mirrors),
    ):
        if original_r1_doc.get(field) != _path_set_digest(paths):
            errors.append(f"fixture: original R1-DOC-01 {field} mismatch")

    boundaries = existing_report.get("superseding_boundaries", {})
    expected_generated = {
        "pages/_site/index.json",
        "specs/ecosystem-spec.json",
    }
    expected_immutable = {
        "cave/rapplications/rapp-installer/HATCH.md",
        "cave/rapplications/rapp-installer/README.md",
        "cave/rapplications/rapp-installer/installer/community_rapp/skill.md",
        "cave/rapplications/rapp-installer/manifest.json",
    }
    if set(boundaries.get("generated", [])) != expected_generated:
        errors.append("fixture: superseding generated boundary drifted")
    if set(boundaries.get("immutable_prepared_clone", [])) != expected_immutable:
        errors.append("fixture: immutable prepared-clone boundary drifted")

    categories = audit.get("categories")
    required_categories = {
        "POST-STALE-LIVE-DOC": 60,
        "POST-MARKETING-LEGACY": 19,
        "POST-SHORTCUT-LEGACY": 5,
        "POST-CONTAIN-PLANT": 14,
        "POST-CONTAIN-CAVE": 10,
        "POST-CANON": 11,
        "POST-CANON-05": 3,
        "VOICE-TWIN-WIRE": 9,
    }
    if not isinstance(categories, dict):
        return errors + ["fixture: audit.categories must be an object"]
    for category_name, exact_count in required_categories.items():
        category = categories.get(category_name)
        if not isinstance(category, dict):
            errors.append(f"fixture: missing {category_name}")
            continue
        paths = category.get("paths")
        if not isinstance(paths, list) or not all(
            isinstance(path, str) and path for path in paths
        ):
            errors.append(f"fixture: {category_name}.paths must be non-empty strings")
            continue
        if len(paths) != len(set(paths)):
            errors.append(f"fixture: {category_name} contains duplicate paths")
        if len(paths) != exact_count or category.get("expected_count") != exact_count:
            errors.append(
                f"fixture: {category_name} must contain exactly {exact_count} paths"
            )
        actual_digest = _path_set_digest(paths)
        if category.get("path_set_sha256") != actual_digest:
            errors.append(
                f"fixture: {category_name} path digest mismatch "
                f"(expected {category.get('path_set_sha256')}, got {actual_digest})"
            )

    classifications = fixture.get("classifications")
    if not isinstance(classifications, dict):
        return errors + ["fixture: classifications must be an object"]
    expected_classes = {"current", "historical", "superseded", "excluded"}
    if set(classifications) != expected_classes:
        errors.append(
            "fixture: classifications must be exactly current, historical, "
            "superseded, and excluded"
        )
        return errors

    seen: dict[str, str] = {}
    for classification, paths in classifications.items():
        if not isinstance(paths, list):
            errors.append(f"fixture: classifications.{classification} must be a list")
            continue
        for path in paths:
            if path in seen:
                errors.append(
                    f"fixture: {path} appears in both {seen[path]} and {classification}"
                )
            seen[path] = classification
            if not (ROOT / path).is_file():
                errors.append(f"fixture: classified path is missing: {path}")

    reasons = fixture.get("exclusion_reasons", {})
    if set(reasons) != set(classifications.get("excluded", [])):
        errors.append("fixture: every excluded path must have exactly one reason")

    for category_name, category in categories.items():
        for path in category.get("paths", []):
            if path not in seen:
                errors.append(
                    f"fixture: {category_name} path has no disposition: {path}"
                )
    for path in original_all:
        if path not in seen:
            errors.append(f"fixture: original R1-DOC-01 path has no disposition: {path}")
    for path in expected_generated | expected_immutable:
        if seen.get(path) != "excluded":
            errors.append(f"fixture: superseding boundary must be excluded: {path}")

    for path in fixture.get("required_files", []):
        if not (ROOT / path).is_file():
            errors.append(f"fixture: required file is missing: {path}")
    return errors


def _validate_document(
    relative_path: str,
    classification: str,
    fixture: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    text = _read(relative_path)
    markers = fixture["required_markers"]
    active_text, marker_errors = _strip_historical_sections(
        text, markers["historical_start"], markers["historical_end"]
    )
    errors.extend(f"{relative_path}: {error}" for error in marker_errors)

    authority = fixture["canon_authority"]
    authority_text = active_text if classification == "current" else text
    if not _has_authority_link(authority_text):
        errors.append(f"{relative_path}: missing RAPP/1 authority link")
    if not _has_status_link(authority_text):
        errors.append(f"{relative_path}: missing RAPP1_STATUS.md link")
    if authority["required_revision"].lower() not in authority_text.lower():
        errors.append(f"{relative_path}: missing rev-5 authority statement")

    if classification == "current":
        if not _has_authority_topics(authority_text, authority["authority_topics"]):
            errors.append(
                f"{relative_path}: current guidance does not defer all authority topics"
            )
        for pattern in fixture["retired_active_patterns"]:
            match = re.search(pattern, authority_text, flags=re.IGNORECASE)
            if match and not _is_negated_context(
                authority_text, match.start(), match.end()
            ):
                errors.append(
                    f"{relative_path}: active text matches retired pattern {pattern!r}"
                )
    elif classification == "historical":
        if (
            markers["historical_start"] not in text
            or markers["historical_end"] not in text
        ):
            errors.append(
                f"{relative_path}: historical document must use bounded markers"
            )
    elif classification == "superseded":
        if not re.search(
            r"\b(?:superseded|historical|retired|not current|no longer current)\b",
            text,
            flags=re.IGNORECASE,
        ):
            errors.append(f"{relative_path}: missing supersession disposition")

    return errors


def _active_text(relative_path: str, fixture: dict[str, Any]) -> tuple[str, list[str]]:
    text = _read(relative_path)
    markers = fixture["required_markers"]
    active, marker_errors = _strip_historical_sections(
        text, markers["historical_start"], markers["historical_end"]
    )
    return active, [f"{relative_path}: {error}" for error in marker_errors]


def _validate_post_categories(fixture: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    categories = fixture["audit"]["categories"]
    rules = fixture["category_rules"]
    classifications = fixture["classifications"]
    disposition = {
        path: classification
        for classification, paths in classifications.items()
        for path in paths
    }

    for path in categories["POST-STALE-LIVE-DOC"]["paths"]:
        classification = disposition[path]
        if classification == "historical":
            text = _read(path)
            markers = fixture["required_markers"]
            if (
                markers["historical_start"] not in text
                or markers["historical_end"] not in text
            ):
                errors.append(f"{path}: stale-live history is not bounded")
        elif classification == "superseded":
            text = _read(path)
            if not re.search(
                r"\b(?:superseded|historical|retired|pre-acceptance)\b",
                text,
                flags=re.IGNORECASE,
            ):
                errors.append(f"{path}: stale-live path lacks a disposition")
        elif classification == "excluded" and path != "pages/_site/index.json":
            errors.append(f"{path}: stale-live path cannot escape via exclusion")

    marketing_rule = rules["POST-MARKETING-LEGACY"]
    disposition_terms = marketing_rule["required_disposition_terms"]
    for path in categories["POST-MARKETING-LEGACY"]["paths"]:
        text = _read(path)
        lowered = text.lower()
        if not any(term in lowered for term in disposition_terms):
            errors.append(f"{path}: legacy marketing claim has no current disposition")
        active, marker_errors = _active_text(path, fixture)
        errors.extend(marker_errors)
        for pattern in fixture["retired_active_patterns"]:
            if re.search(pattern, active, flags=re.IGNORECASE):
                errors.append(
                    f"{path}: active marketing matches retired pattern {pattern!r}"
                )

    shortcut_rule = rules["POST-SHORTCUT-LEGACY"]
    for path in categories["POST-SHORTCUT-LEGACY"]["paths"]:
        text = _read(path)
        lowered = text.lower()
        for token in shortcut_rule["required_wire_tokens"]:
            if token.lower() not in lowered:
                errors.append(f"{path}: missing exact façade token {token!r}")
        if not re.search(r"\b(?:exactly|exact)\b", text, flags=re.IGNORECASE):
            errors.append(f"{path}: façade shapes are not declared exact")
        if not re.search(
            r"\b(?:derived?|derive|speak|speech)\b[^.\n]*\b(?:locally|response)\b"
            r"|\b(?:locally|response)\b[^.\n]*\b(?:derived?|derive|speak|speech)\b",
            text,
            flags=re.IGNORECASE,
        ):
            errors.append(f"{path}: voice is not derived locally from response")
        lines = text.splitlines()
        for token in shortcut_rule["forbidden_extra_members"]:
            for line_number, line in enumerate(lines):
                if token not in line:
                    continue
                context = " ".join(
                    lines[max(0, line_number - 1) : min(len(lines), line_number + 2)]
                )
                if not re.search(
                    r"\b(?:no|not|never|without|forbid|do not)\b",
                    context,
                    flags=re.IGNORECASE,
                ):
                    errors.append(
                        f"{path}: {token!r} is not explicitly rejected as an extra member"
                    )

    plant_rule = rules["POST-CONTAIN-PLANT"]
    for path in categories["POST-CONTAIN-PLANT"]["paths"]:
        active, marker_errors = _active_text(path, fixture)
        errors.extend(marker_errors)
        for pattern in plant_rule["forbidden_live_patterns"]:
            match = re.search(pattern, active, flags=re.IGNORECASE)
            if match:
                errors.append(f"{path}: live plant.sh CTA matches {pattern!r}")

    cave_rule = rules["POST-CONTAIN-CAVE"]
    for path in categories["POST-CONTAIN-CAVE"]["paths"]:
        text = _read(path)
        if not any(
            term in text.lower() for term in cave_rule["required_disposition_terms"]
        ):
            errors.append(f"{path}: cave installer/catalog history is not tombstoned")
        active, marker_errors = _active_text(path, fixture)
        errors.extend(marker_errors)
        for pattern in cave_rule["forbidden_live_patterns"]:
            match = re.search(pattern, active, flags=re.IGNORECASE)
            if match and not re.search(
                r"\b(?:no|not|never|do not|retired|historical|inert)\b",
                active[max(0, match.start() - 80) : match.end() + 80],
                flags=re.IGNORECASE,
            ):
                errors.append(f"{path}: live cave CTA matches {pattern!r}")
        for script_tag in re.findall(r"<script\b[^>]*>", active, flags=re.IGNORECASE):
            if 'type="application/rapp-history"' not in script_tag.lower():
                errors.append(f"{path}: cave script is executable rather than inert")

    canon_rule = rules["POST-CANON"]
    for path in categories["POST-CANON"]["paths"]:
        text = _read(path)
        if (
            canon_rule["required_authority_commit"] not in text
            and "RAPP1_AUTHORITY.json" not in text
        ):
            errors.append(f"{path}: missing immutable RAPP/1 authority pin")
        if (
            canon_rule["required_pin"] not in text
            and "KERNEL_PIN.json" not in text
        ):
            errors.append(f"{path}: missing immutable grail pin")
        active, marker_errors = _active_text(path, fixture)
        errors.extend(marker_errors)
        for pattern in canon_rule["forbidden_live_patterns"]:
            if re.search(pattern, active, flags=re.IGNORECASE):
                errors.append(f"{path}: active canon text matches {pattern!r}")
    ecosystem_spec = _read("specs/ECOSYSTEM_SPEC.md").lower()
    if "rapp-god" not in ecosystem_spec or not re.search(
        r"\b(?:non-authoritative|divergent)\b", ecosystem_spec
    ):
        errors.append(
            "specs/ECOSYSTEM_SPEC.md: rapp-god must be explicitly divergent "
            "or non-authoritative"
        )

    tutorial_rule = rules["POST-CANON-05"]
    navigation_text = _read(tutorial_rule["navigation_path"])
    try:
        json.loads(navigation_text)
    except json.JSONDecodeError as exc:
        errors.append(f"{tutorial_rule['navigation_path']}: invalid JSON: {exc}")
    for retired_token in ("hatch-egg", "brainstem-egg", "sample-agent.egg"):
        if retired_token in navigation_text.lower():
            errors.append(
                f"{tutorial_rule['navigation_path']}: advertises retired {retired_token}"
            )
    tutorial_text = _read(tutorial_rule["retired_tutorial_path"])
    if not re.search(r"\bnoindex\b", tutorial_text, flags=re.IGNORECASE):
        errors.append(
            f"{tutorial_rule['retired_tutorial_path']}: missing noindex retirement"
        )
    markers = fixture["required_markers"]
    if (
        markers["historical_start"] not in tutorial_text
        or markers["historical_end"] not in tutorial_text
    ):
        errors.append(
            f"{tutorial_rule['retired_tutorial_path']}: history is not bounded"
        )

    voice_rule = rules["VOICE-TWIN-WIRE"]
    for path in categories["VOICE-TWIN-WIRE"]["paths"]:
        text = _read(path)
        for token in voice_rule["required_tokens"]:
            if token.lower() not in text.lower():
                errors.append(f"{path}: missing Voice/Twin token {token!r}")
        active, marker_errors = _active_text(path, fixture)
        errors.extend(marker_errors)
        for pattern in voice_rule["forbidden_positive_patterns"]:
            if re.search(pattern, active, flags=re.IGNORECASE):
                errors.append(f"{path}: advertises an extra Voice/Twin wire field")

    status = _read("RAPP1_STATUS.md")
    if "2026-07-16 baseline: 640/640 tracked paths" not in status:
        errors.append("RAPP1_STATUS.md: missing dated 640-path baseline")
    if not re.search(
        r"2026-07-17[\s\S]{0,100}691/691 tracked\s+paths",
        status,
        flags=re.IGNORECASE,
    ):
        errors.append("RAPP1_STATUS.md: missing dated 691-path post-audit inventory")
    for category in (
        "Authenticated owner action",
        "Generated target artifacts",
        "Immutable history",
        "External mirrors",
    ):
        if category not in status:
            errors.append(f"RAPP1_STATUS.md: missing unresolved category {category!r}")
    return errors


def main() -> int:
    try:
        fixture = _load_fixture()
        errors = _validate_fixture(fixture)
        if not errors:
            for classification in ("current", "historical", "superseded"):
                for path in fixture["classifications"][classification]:
                    errors.extend(_validate_document(path, classification, fixture))
            errors.extend(_validate_post_categories(fixture))
    except (KeyError, TypeError, ValueError) as exc:
        errors = [str(exc)]

    if errors:
        print("RAPP/1 documentation gate failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    managed_count = sum(
        len(fixture["classifications"][classification])
        for classification in ("current", "historical", "superseded")
    )
    category_count = sum(
        category["expected_count"]
        for category in fixture["audit"]["categories"].values()
    )
    print(
        "RAPP/1 documentation gate passed "
        f"({managed_count} managed documents; {category_count} ledger entries)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
