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


def _validate_derived_document_scope(
    fixture: dict[str, Any],
    tracked_paths: list[str],
    classified_paths: set[str],
) -> list[str]:
    """Require every tracked Markdown/HTML document to have a disposition."""

    errors: list[str] = []
    scope = fixture.get("derived_document_scope")
    if not isinstance(scope, dict):
        return ["fixture: derived_document_scope must be an object"]
    extensions = scope.get("extensions")
    if extensions != [".md", ".html"]:
        errors.append("fixture: derived document extensions must be .md and .html")
        return errors

    candidates = {
        path for path in tracked_paths if Path(path).suffix.lower() in extensions
    }
    if len(candidates) != scope.get("expected_tracked_document_count"):
        errors.append(
            "fixture: derived tracked-document count does not match git ls-files "
            f"({len(candidates)} != {scope.get('expected_tracked_document_count')})"
        )

    prefixes = scope.get("excluded_prefixes", {})
    expected_prefixes = {
        ".github/prompts/",
        "cave/rapplications/rapp-installer/",
        "pages/_site/partials/",
        "pages/vault/Blog Drafts/",
        "pages/vault/Decisions/",
        "pages/vault/Fixtures/",
        "pages/vault/Removals/",
        "responsible-ai/",
        "tests/",
        "tools/",
    }
    if not isinstance(prefixes, dict) or set(prefixes) != expected_prefixes:
        errors.append("fixture: derived document prefix exclusions drifted")
        prefixes = prefixes if isinstance(prefixes, dict) else {}
    for prefix, reason in prefixes.items():
        if not isinstance(reason, str) or not reason.strip():
            errors.append(
                f"fixture: derived prefix exclusion has no justification: {prefix}"
            )

    exact = scope.get("excluded_paths", {})
    if not isinstance(exact, dict):
        errors.append("fixture: derived exact exclusions must be an object")
        exact = {}
    for path, reason in exact.items():
        if path not in candidates:
            errors.append(f"fixture: derived exclusion is not a tracked document: {path}")
        if path in classified_paths:
            errors.append(f"fixture: derived exclusion duplicates a disposition: {path}")
        if not isinstance(reason, str) or not reason.strip():
            errors.append(f"fixture: derived exclusion has no justification: {path}")

    prefix_excluded = {
        path
        for path in candidates
        if any(path.startswith(prefix) for prefix in prefixes)
    }
    unaccounted = candidates - classified_paths - set(exact) - prefix_excluded
    for path in sorted(unaccounted):
        errors.append(f"fixture: tracked document has no disposition: {path}")
    return errors


def _validate_fixture(fixture: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if fixture.get("schema_version") != "rapp1-documentation-scope/2.0":
        errors.append("fixture: unsupported schema_version")

    audit = fixture.get("audit")
    if not isinstance(audit, dict):
        return errors + ["fixture: audit must be an object"]
    if audit.get("source") != "verify-rapp-files-final-post-ledger":
        errors.append(
            "fixture: audit source must be verify-rapp-files-final-post-ledger"
        )
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
        "canon_report_sha256": (
            "188eef4a3d2f65b93a4e0832515e8fe8b7b8826e1163b683029ab1d14bc51f59"
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

    final_report = provenance.get("final_report", {})
    expected_final_fields = {
        "source": "verify-rapp-files",
        "report_sha256": (
            "f5ba5abbf21067dd644d70f9076201b7ca3bf8afd934edbb9f2b4614060ad50b"
        ),
        "tracked_path_count": 691,
        "data_rows": 691,
        "report_bytes": 117017,
        "tracked_bytes": 8298082,
        "recursive_archive_members": 450,
    }
    for field, expected in expected_final_fields.items():
        if final_report.get(field) != expected:
            errors.append(f"fixture: final report {field} does not match evidence")
    expected_status_counts = {
        "compliant": 224,
        "context-allowed": 269,
        "noncompliant": 165,
        "N/A": 18,
        "owner-blocked": 15,
    }
    if final_report.get("status_counts") != expected_status_counts:
        errors.append("fixture: final report status counts do not match evidence")
    expected_disposition_counts = {
        "current-live": 390,
        "fixture": 122,
        "generated": 5,
        "history": 79,
        "immutable": 24,
        "legacy-reader": 5,
        "mirror": 27,
        "retired": 21,
        "unrelated": 18,
    }
    if final_report.get("disposition_counts") != expected_disposition_counts:
        errors.append("fixture: final report disposition counts do not match evidence")
    expected_final_definitions = {
        "POST-STALE-LIVE-DOC": (
            "current/published/living target-owned guidance teaches superseded "
            "topology, installer, identity, egg, wire, or protocol behavior as "
            "actionable. Fix by rev-5 rewrite, explicit whole-section historical "
            "bounding, or retirement/removal from live navigation. A top banner "
            "does not cure later contradictory instructions. Dated decisions, "
            "release snapshots, fixtures, and explicitly bounded migration prose "
            "are excluded."
        ),
        "POST-MARKETING-LEGACY": (
            "public sales/product copy represents unverified legacy behavior as "
            "shipped/current. Remove/qualify until verified; historical comparisons "
            "are excluded."
        ),
        "POST-SHORTCUT-LEGACY": (
            "active Shortcut instructions depend on direct legacy /chat, Tier 2, "
            "conversation_history, voice_response, agent_logs extras. Route through "
            "façade, use exact success/error object, derive TTS locally; unknown "
            "request fields alone are allowed, relying on them is drift."
        ),
        "POST-CONTAIN-PLANT": (
            "plant.sh is a correct 410 tombstone, but callers/CTAs/tests still "
            "promise planting. Preserve plant.sh; retire callers."
        ),
        "POST-CONTAIN-CAVE": (
            "prepared Cave artifacts remain advertised/downloadable/hatchable/"
            "side-effecting. Retire links/catalog/agent/hatcher from outside the "
            "immutable payload; do not edit embedded/pinned archive bytes."
        ),
    }
    if final_report.get("definitions") != expected_final_definitions:
        errors.append("fixture: final report definitions do not match evidence")
    if final_report.get("absent_ids") != ["POST-CANON", "POST-CANON-05"]:
        errors.append("fixture: final report absent-ID evidence drifted")

    categories = audit.get("categories")
    required_categories = {
        "POST-STALE-LIVE-DOC": 60,
        "POST-MARKETING-LEGACY": 19,
        "POST-SHORTCUT-LEGACY": 5,
        "POST-CONTAIN-PLANT": 7,
        "POST-CONTAIN-CAVE": 20,
        "POST-MIRROR": 23,
        "POST-OWNER-MIRROR": 4,
        "POST-IMMUTABLE-PIN": 17,
        "POST-IMMUTABLE-ARTIFACT": 6,
        "POST-STATUS-01": 2,
        "POST-QA-DOC": 3,
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
        for path in paths:
            if not (ROOT / path).is_file():
                errors.append(f"fixture: {category_name} path is missing: {path}")
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

    target_checks = fixture.get("target_checks", {})
    expected_target_checks = {
        "canon_closure": (
            11,
            "d04fdf1f095f44a1fca7c30c989b890c3bced11d97fd024d830e0cd321244589",
        ),
        "retired_tutorial": (
            3,
            "9308d946bd01549a8b02626e7dd2729cd0ebe46adc94fbf86718a9419fb30039",
        ),
        "voice_twin_wire": (
            9,
            "dda129ecee5bbfbc28ae24b82448168f07907b4818a58f4c676d8c46ac46beb7",
        ),
    }
    if not isinstance(target_checks, dict) or set(target_checks) != set(
        expected_target_checks
    ):
        errors.append("fixture: target checks drifted or use fabricated report IDs")
    else:
        for name, (count, digest) in expected_target_checks.items():
            check = target_checks[name]
            paths = check.get("paths", [])
            if check.get("expected_count") != count or len(paths) != count:
                errors.append(f"fixture: {name} target check must contain {count} paths")
            if check.get("path_set_sha256") != digest or _path_set_digest(paths) != digest:
                errors.append(f"fixture: {name} target-check path digest mismatch")
            if "not a final-ledger ID" not in check.get("provenance", ""):
                errors.append(f"fixture: {name} target-check provenance is missing")
            for path in paths:
                if not (ROOT / path).is_file():
                    errors.append(f"fixture: {name} target-check path is missing: {path}")

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
    errors.extend(_validate_derived_document_scope(fixture, tracked_paths, set(seen)))

    ownership_exclusions = fixture.get("ownership_exclusions", {})
    actionable_categories = {
        "POST-STALE-LIVE-DOC",
        "POST-MARKETING-LEGACY",
        "POST-SHORTCUT-LEGACY",
        "POST-CONTAIN-PLANT",
        "POST-CONTAIN-CAVE",
    }
    for category_name in actionable_categories:
        for path in categories[category_name].get("paths", []):
            if path not in seen and path not in ownership_exclusions:
                errors.append(
                    f"fixture: {category_name} path has no disposition: {path}"
                )
    actionable_paths = {
        path
        for category_name in actionable_categories
        for path in categories[category_name]["paths"]
    }
    for path, reason in ownership_exclusions.items():
        if path not in actionable_paths:
            errors.append(f"fixture: ownership exclusion is outside action scope: {path}")
        if not isinstance(reason, str) or not reason:
            errors.append(f"fixture: ownership exclusion has no reason: {path}")
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
    ownership_exclusions = fixture["ownership_exclusions"]
    changed_paths = set(
        subprocess.check_output(
            ("git", "diff", "--name-only", "HEAD", "--"), cwd=ROOT, text=True
        ).splitlines()
    )
    protected_categories = (
        "POST-MIRROR",
        "POST-IMMUTABLE-PIN",
        "POST-IMMUTABLE-ARTIFACT",
    )
    protected_paths = {
        path
        for category_name in protected_categories
        for path in categories[category_name]["paths"]
    } | set(ownership_exclusions)
    for path in sorted(changed_paths & protected_paths):
        errors.append(f"{path}: protected mirror/immutable/owned path was modified")
    allowed_owner_mirror_edit = {"specs/ECOSYSTEM_SPEC.md"}
    for path in sorted(
        changed_paths
        & (set(categories["POST-OWNER-MIRROR"]["paths"]) - allowed_owner_mirror_edit)
    ):
        errors.append(f"{path}: generated/external owner mirror was modified")

    for path in categories["POST-STALE-LIVE-DOC"]["paths"]:
        if path in ownership_exclusions:
            continue
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
        if path in ownership_exclusions:
            continue
        text = _read(path)
        lowered = text.lower()
        if not any(term in lowered for term in disposition_terms):
            errors.append(f"{path}: legacy marketing claim has no current disposition")
        if disposition.get(path) == "excluded":
            continue
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
        if path in ownership_exclusions:
            continue
        raw = _read(path)
        active, marker_errors = _active_text(path, fixture)
        errors.extend(marker_errors)
        for pattern in plant_rule["forbidden_live_patterns"]:
            match = re.search(pattern, active, flags=re.IGNORECASE)
            if match:
                errors.append(f"{path}: live plant.sh CTA matches {pattern!r}")
        for script_tag in re.findall(r"<script\b[^>]*>", raw, flags=re.IGNORECASE):
            if 'type="application/rapp-history"' not in script_tag.lower():
                errors.append(f"{path}: retired planting script remains executable")

    cave_rule = rules["POST-CONTAIN-CAVE"]
    for path in categories["POST-CONTAIN-CAVE"]["paths"]:
        if path in ownership_exclusions:
            continue
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
        for script_tag in re.findall(r"<script\b[^>]*>", text, flags=re.IGNORECASE):
            if 'type="application/rapp-history"' not in script_tag.lower():
                errors.append(f"{path}: cave script is executable rather than inert")
    structured_cave = {
        "cave/.well-known/rapp-cave.json": {
            "status": "retired",
            "public": False,
            "raw_base": None,
            "cubbies_index": None,
            "rapplications": None,
            "bootstrap": None,
            "join_via": None,
        },
        "cave/cubbies/_template/cubby.json": {
            "status": "retired-template",
        },
        "cave/cubbies/index.json": {
            "status": "retired",
            "cubbies": [],
        },
        "cave/cubbies/kody-w/cubby.json": {
            "status": "retired",
        },
    }
    for path, expected_values in structured_cave.items():
        try:
            value = json.loads(_read(path))
        except json.JSONDecodeError as exc:
            errors.append(f"{path}: invalid cave tombstone JSON: {exc}")
            continue
        for key, expected in expected_values.items():
            if value.get(key) != expected:
                errors.append(f"{path}: cave tombstone field {key!r} drifted")
        streamable = value.get("streamable")
        if isinstance(streamable, dict) and streamable.get("agents") is not False:
            errors.append(f"{path}: cave agent streaming must remain false")

    target_checks = fixture["target_checks"]
    canon_rule = rules["canon_closure"]
    for path in target_checks["canon_closure"]["paths"]:
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

    tutorial_rule = rules["retired_tutorial"]
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
    for path in target_checks["retired_tutorial"]["paths"]:
        if path == tutorial_rule["retired_tutorial_path"]:
            continue
        active, marker_errors = _active_text(path, fixture)
        errors.extend(marker_errors)
        for retired_token in ("hatch-egg", "brainstem-egg", "sample-agent.egg"):
            if retired_token in active.lower():
                errors.append(f"{path}: advertises retired {retired_token}")
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

    voice_rule = rules["voice_twin_wire"]
    for path in target_checks["voice_twin_wire"]["paths"]:
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
    for evidence in (
        "8,298,082 tracked bytes",
        "450 recursively counted archive",
        "f5ba5abbf21067dd644d70f9076201b7ca3bf8afd934edbb9f2b4614060ad50b",
        "does not define categories named `POST-CANON` or `POST-CANON-05`",
    ):
        if evidence not in status:
            errors.append(f"RAPP1_STATUS.md: missing post-ledger evidence {evidence!r}")
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
        f"({managed_count} managed documents; {category_count} ledger entries; "
        f"{fixture['derived_document_scope']['expected_tracked_document_count']} "
        "tracked Markdown/HTML files accounted)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
