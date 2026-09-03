#!/usr/bin/env python3
"""ecosystem_audit — Bond Pulse drift detector.

Walks every offspring listed in `pages/metropolis/index.json`, observes
its published files (via fixture in --offline or via `gh api` →
`raw.githubusercontent.com` in --online), diffs against the per-kind
observations in `tools/ecosystem_contract.py`, and emits both a human report
(`pages/_audit/ecosystem-audit.md`) and a machine envelope
(`pages/_audit/ecosystem-audit.json`, schema `rapp-ecosystem-audit/1.0`).
That envelope and its checked product schemas are local observations, not
RAPP/1 protocol authority.

Default operation is read-only and prints the complete comparison envelope.
Output-file or cache writes require an explicit write request, a matching
owner-approval artifact, and authenticated fresh RAPP/1 section-13 authority.
The last prerequisite is unavailable here, so current write requests refuse.

Stdlib-only — runs from a fresh `git clone` with no pip install. Mirrors
`bond.py`'s discipline: the substrate health check can't depend on its
own installation succeeding.

Modes:
    --offline   (default; CI-safe) Use checked-in tests/fixtures/<name>{-seed,}/
    --online    Attempt fresh network evidence. Cache fallback is labelled stale,
                makes the audit incomplete, and can never be reported as live.
                Set ECOSYSTEM_AUDIT_ONLINE=1 to enable from env.
    --repo NAME Audit one offspring by name; default audits all entries
    --write     Request gated pages/_audit/ output writes
    --no-write  Compatibility flag for the default read-only mode
    --strict    Exit 1 on drift_count > 0 (default: True)

Exit code: 0 for complete/no-drift evidence, 1 for observed drift, and 2 for
unavailable or stale online evidence. ``--lenient`` never masks exit 2.

The Bond Pulse heartbeat (`bond_rhythm_agent`) calls this script as a
subprocess and parses the JSON envelope. Any direct caller can also
`from ecosystem_audit import audit_ecosystem`.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

# Allow running as a script OR being imported
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from ecosystem_contract import (  # noqa: E402
    CONTRACTS, HISTORICAL_KINDS, KERNEL_BASE_FILES, SEED_REQUIRED_AGENTS,
    kind_for_entry, contract_for_kind, all_kinds,
)
from door_address import parse_rappid, InvalidRappidError  # noqa: E402


# ── constants ──────────────────────────────────────────────────────────────

REPO_ROOT = os.path.dirname(_HERE)  # tools/ → repo root
DEFAULT_METROPOLIS = os.path.join(REPO_ROOT, "pages", "metropolis", "index.json")
DEFAULT_AUDIT_OUT_DIR = os.path.join(REPO_ROOT, "pages", "_audit")
DEFAULT_FIXTURES_DIR = os.path.join(REPO_ROOT, "tests", "fixtures")
CACHE_DIR = os.path.expanduser("~/.brainstem/audit_cache")
USER_AGENT = "rapp-ecosystem-audit/1.0"
HTTP_TIMEOUT = 12.0

AUDIT_SCHEMA = "rapp-ecosystem-audit/1.0"
APPROVAL_SCHEMA = "rapp-tool-owner-approval/1.0"
AUTHORITY_REASON = (
    "No authenticated, fresh RAPP/1 section-13 registry rooted in an "
    "out-of-band estate-owner anchor is available to authorize writes."
)

# Identity block sentinel — soul.md must contain this string per ANTIPATTERNS §4
IDENTITY_BLOCK_SENTINEL = "Identity"  # tolerant — matches "## Identity" or "## Identity — read this every turn"


# ── small helpers ──────────────────────────────────────────────────────────

def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _ensure_cache():
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
    except OSError:
        pass


def _cache_key(url: str) -> str:
    return os.path.join(CACHE_DIR, _sha256_str(url)[:16] + ".bin")


def _cache_get(url: str) -> tuple[bytes | None, float | None]:
    p = _cache_key(url)
    if not os.path.exists(p):
        return None, None
    try:
        with open(p, "rb") as f:
            body = f.read()
        age = max(0.0, time.time() - os.path.getmtime(p))
        return body, age
    except OSError:
        return None, None


def _cache_put(url: str, body: bytes) -> None:
    _ensure_cache()
    try:
        with open(_cache_key(url), "wb") as f:
            f.write(body)
    except OSError:
        pass


# ── network fetch (online mode) ────────────────────────────────────────────

def _gh_api(path: str) -> tuple[dict | list | None, str, str]:
    """Try gh CLI and preserve present/missing/unavailable state."""
    try:
        p = subprocess.run(["gh", "api", path], capture_output=True, text=True, timeout=20)
        if p.returncode == 0 and p.stdout.strip():
            try:
                return json.loads(p.stdout), "present", ""
            except (ValueError, json.JSONDecodeError):
                return None, "unavailable", "GitHub API returned invalid JSON"
        detail = (p.stderr or p.stdout or "GitHub API request failed").strip()
        if "HTTP 404" in detail or "not found" in detail.lower():
            return None, "missing", detail[:240]
        return None, "unavailable", detail[:240]
    except FileNotFoundError:
        return None, "unavailable", "gh CLI is not installed"
    except subprocess.TimeoutExpired:
        return None, "unavailable", "GitHub API request timed out"


def _raw_fetch(
    url: str,
    *,
    update_cache: bool = False,
) -> tuple[bytes | None, dict]:
    """Fetch raw bytes while keeping cache fallback visibly stale."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
            body = r.read()
            if update_cache:
                _cache_put(url, body)
            return body, {
                "url": url,
                "source": "raw.githubusercontent.com",
                "status": "present",
                "freshness": "live",
                "observed_at": _now_iso(),
                "cache_updated": bool(update_cache),
            }
    except urllib.error.HTTPError as exc:
        if exc.code in {404, 410}:
            return None, {
                "url": url,
                "source": "raw.githubusercontent.com",
                "status": "missing",
                "freshness": "live",
                "observed_at": _now_iso(),
                "detail": f"HTTP {exc.code}",
            }
        detail = f"HTTP {exc.code}: {exc.reason}"
    except (urllib.error.URLError, OSError) as exc:
        detail = str(exc)

    cached, age = _cache_get(url)
    if cached is not None:
        return cached, {
            "url": url,
            "source": "cache",
            "status": "stale",
            "freshness": "stale",
            "cache_age_seconds": age,
            "observed_at": _now_iso(),
            "detail": f"live fetch unavailable: {detail}",
        }
    return None, {
        "url": url,
        "source": "none",
        "status": "unavailable",
        "freshness": "unavailable",
        "observed_at": _now_iso(),
        "detail": detail,
    }


def _fetch_offspring_file(
    owner_repo: str,
    path: str,
    *,
    update_cache: bool = False,
) -> tuple[bytes | None, dict]:
    """Fetch one file and return bytes plus source/freshness evidence."""
    # Prefer gh api (auth + rate limit)
    api_path = f"repos/{owner_repo}/contents/{path}"
    blob, api_status, api_detail = _gh_api(api_path)
    if isinstance(blob, dict) and blob.get("content"):
        try:
            return base64.b64decode(blob["content"]), {
                "url": f"https://api.github.com/{api_path}",
                "source": "gh-api",
                "status": "present",
                "freshness": "live",
                "observed_at": _now_iso(),
            }
        except (ValueError, TypeError):
            pass
    if api_status == "missing":
        return None, {
            "url": f"https://api.github.com/{api_path}",
            "source": "gh-api",
            "status": "missing",
            "freshness": "live",
            "observed_at": _now_iso(),
            "detail": api_detail,
        }

    # Fallback to raw.githubusercontent.com
    raw_url = f"https://raw.githubusercontent.com/{owner_repo}/main/{path}"
    body, evidence = _raw_fetch(raw_url, update_cache=update_cache)
    if evidence["status"] == "unavailable" and api_detail:
        evidence["detail"] = (
            f"GitHub API unavailable: {api_detail}; "
            f"raw fetch unavailable: {evidence.get('detail', '')}"
        )
    return body, evidence


# ── offline fixture discovery ─────────────────────────────────────────────

def _find_fixture_dir(name: str, fixtures_dir: str) -> str | None:
    """Pick the fixture dir for an offspring name. Tries <name>-seed/ then <name>/."""
    for candidate in (f"{name}-seed", name):
        p = os.path.join(fixtures_dir, candidate)
        if os.path.isdir(p):
            return p
    return None


def _read_fixture_file(fixture_dir: str, path: str) -> bytes | None:
    full = os.path.join(fixture_dir, path)
    if not os.path.isfile(full):
        return None
    try:
        with open(full, "rb") as f:
            return f.read()
    except OSError:
        return None


# ── owner_repo extraction from gate_repo URL ──────────────────────────────

def _owner_repo_from_entry(entry: dict) -> str | None:
    gr = entry.get("gate_repo") or ""
    if not gr:
        return None
    if gr.startswith("https://github.com/"):
        tail = gr[len("https://github.com/"):].rstrip("/").split("/")
        if len(tail) >= 2:
            return f"{tail[0]}/{tail[1]}"
    if "/" in gr and not gr.startswith("http"):
        return gr  # already in owner/repo form
    return None


def _metropolis_rappid_drift(value) -> list[dict]:
    invalid_detail = None
    if not isinstance(value, str):
        invalid_detail = "neighborhood_rappid is not a string"
    else:
        try:
            parse_rappid(value)
        except (InvalidRappidError, TypeError) as exc:
            invalid_detail = str(exc)
    if invalid_detail is None:
        return []
    return [{
        "category": "rappid_drift",
        "path": "pages/metropolis/index.json#neighborhood_rappid",
        "detail": (
            "metropolis neighborhood_rappid must be an exact RAPP/1 "
            f"section 6.1 rappid; got {value!r}: {invalid_detail}"
        ),
    }]


# ── per-offspring product observation checks ──────────────────────────────

def _diff_offspring(name: str, kind: str, contract: dict,
                    file_getter, owner_repo: str | None) -> dict:
    """Run product-observation checks against an offspring. file_getter is a
    callable(path) -> (bytes | None, source_label).

    Returns a dict {ok: bool, drift: list, fingerprint_sha256: str | None,
                    rappid: str | None, fetched_from: str}.
    """
    drift = []
    sources_seen = set()
    fingerprint_sha256 = None
    rappid = None
    rappid_record_seen = False
    record_kind = None  # the `kind` FIELD from the rappid.json record (consolidated form)

    # 1. required_files presence
    for path in contract.get("required_files", []):
        body, source = file_getter(path)
        if source not in {"missing", "unavailable"}:
            sources_seen.add(source)
        if body is None and source == "missing":
            drift.append({"category": "missing_files", "path": path,
                          "detail": f"required file '{path}' not found"})

    # 2. Product-local schemas do not establish RAPP/1 conformance.
    for path, expected_schema in (
        contract.get("expected_product_schemas") or {}
    ).items():
        body, source = file_getter(path)
        if source not in {"missing", "unavailable"}:
            sources_seen.add(source)
        if body is None:
            # Already covered by missing_files above (if required); skip silent for optional
            continue
        try:
            d = json.loads(body)
        except (ValueError, json.JSONDecodeError):
            drift.append({"category": "product_schema_drift", "path": path,
                          "detail": "file is not valid JSON"})
            continue
        actual_schema = d.get("schema") if isinstance(d, dict) else None
        if actual_schema != expected_schema:
            drift.append({"category": "product_schema_drift", "path": path,
                          "detail": f"expected schema={expected_schema!r}, got {actual_schema!r}"})
        if path == "rappid.json" and isinstance(d, dict):
            rappid_record_seen = True
            rappid = d.get("rappid")
            record_kind = d.get("kind")  # kind lives in the RECORD, not the string
            try:
                fingerprint_sha256 = _sha256_bytes(body)
            except Exception:
                pass

    # 3. Every encountered rappid is exact, regardless of whether kind is enforced.
    if not rappid_record_seen:
        body, source = file_getter("rappid.json")
        if source not in {"missing", "unavailable"}:
            sources_seen.add(source)
        if body is not None:
            try:
                identity = json.loads(body)
            except (ValueError, json.JSONDecodeError):
                identity = None
            if isinstance(identity, dict):
                rappid_record_seen = True
                rappid = identity.get("rappid")
                record_kind = identity.get("kind")
                fingerprint_sha256 = _sha256_bytes(body)
            else:
                drift.append({
                    "category": "rappid_drift",
                    "path": "rappid.json",
                    "detail": "rappid.json is not a JSON identity object",
                })

    if rappid_record_seen:
        invalid_detail = None
        if not isinstance(rappid, str):
            invalid_detail = "rappid member is not a string"
        else:
            try:
                parse_rappid(rappid)
            except (InvalidRappidError, TypeError) as exc:
                invalid_detail = str(exc)
        if invalid_detail is not None:
            drift.append({
                "category": "rappid_drift",
                "path": "rappid.json",
                "detail": (
                    "expected exact RAPP/1 section 6.1 rappid; "
                    f"got {rappid!r}: {invalid_detail}"
                ),
            })

    expected_kind = contract.get("rappid_kind")
    if expected_kind is not None and rappid_record_seen:
        actual_kind = record_kind
        if actual_kind != expected_kind:
            drift.append({"category": "rappid_drift",
                          "path": "rappid.json",
                          "detail": f"expected kind={expected_kind!r} (from rappid.json record), "
                                    f"got {actual_kind!r}"})

    # 4. identity_block_required (soul.md must mention "Identity")
    if contract.get("identity_block_required"):
        body, source = file_getter("soul.md")
        if source not in {"missing", "unavailable"}:
            sources_seen.add(source)
        if body is None:
            # Already in missing_files if required; otherwise flag explicitly
            pass
        else:
            try:
                txt = body.decode("utf-8", errors="replace")
            except Exception:
                txt = ""
            if IDENTITY_BLOCK_SENTINEL not in txt:
                drift.append({"category": "identity_block_missing",
                              "path": "soul.md",
                              "detail": "soul.md must contain the Identity block sentinel (per ANTIPATTERNS §4)"})

    # 5. rar_required + sha256-validate against agents/
    if contract.get("rar_required"):
        body, source = file_getter("rar/index.json")
        if source not in {"missing", "unavailable"}:
            sources_seen.add(source)
        if body is None:
            # already reported as missing_file if required
            pass
        else:
            try:
                rar_index = json.loads(body)
            except (ValueError, json.JSONDecodeError):
                rar_index = None
            if not isinstance(rar_index, dict) or rar_index.get("schema") != "rapp-rar-index/1.0":
                drift.append({"category": "product_schema_drift", "path": "rar/index.json",
                              "detail": "rar/index.json schema invalid or missing"})
            else:
                # Recompute sha256 of every required_for_participation + kernel_base_included entry
                items = (rar_index.get("required_for_participation") or []) + \
                        (rar_index.get("kernel_base_included") or [])
                for item in items:
                    rel = item.get("file")
                    expected_sha = (item.get("sha256") or "").lower()
                    if not rel or not expected_sha:
                        continue
                    file_body, file_source = file_getter(rel)
                    if file_body is None and file_source == "missing":
                        drift.append({"category": "missing_files", "path": rel,
                                      "detail": f"rar/index.json declares {rel} but file is absent"})
                        continue
                    if file_body is None:
                        continue
                    actual_sha = _sha256_bytes(file_body)
                    if actual_sha != expected_sha:
                        drift.append({"category": "kernel_drift" if rel.endswith("basic_agent.py")
                                      else "product_schema_drift",
                                      "path": rel,
                                      "detail": f"sha256 mismatch — manifest={expected_sha[:12]}…, actual={actual_sha[:12]}…"})

    # 6. kernel_base_check: agents/{SEED_REQUIRED_AGENTS} must be present.
    #    This is the seed-portable minimum — basic_agent.py only. The other
    #    kernel-tier agents (manage_memory, context_memory per Art. XXXIII)
    #    are brainstem-internal and loaded by the joining brainstem.
    if contract.get("kernel_base_check"):
        for fname in SEED_REQUIRED_AGENTS:
            rel = f"agents/{fname}"
            body, source = file_getter(rel)
            if source not in {"missing", "unavailable"}:
                sources_seen.add(source)
            if body is None and source == "missing":
                drift.append({"category": "missing_files", "path": rel,
                              "detail": f"seed-portable kernel base {rel} required by kind"})

    file_evidence = dict(getattr(file_getter, "evidence", {}))
    evidence_issues = [
        {
            "path": path,
            "source": evidence.get("source"),
            "freshness": evidence.get("freshness"),
            "status": evidence.get("status"),
            "detail": evidence.get("detail", ""),
        }
        for path, evidence in sorted(file_evidence.items())
        if evidence.get("status") in {"stale", "unavailable"}
        or evidence.get("freshness") in {"stale", "unavailable"}
    ]
    evidence_complete = not evidence_issues
    observed_sources = {
        str(evidence.get("source"))
        for evidence in file_evidence.values()
        if evidence.get("source")
    }
    fetched_from = ",".join(sorted(observed_sources or sources_seen)) or "none"
    return {
        "ok": not drift and evidence_complete,
        "drift": drift,
        "fingerprint_sha256": fingerprint_sha256,
        "rappid": rappid,
        "fetched_from": fetched_from,
        "evidence_complete": evidence_complete,
        "evidence_issues": evidence_issues,
        "file_evidence": file_evidence,
        "kind_lifecycle": contract.get("lifecycle", "product-observation"),
        "historical_observation": (
            contract.get("historical_shape")
            if contract.get("lifecycle") == "historical-observation"
            else None
        ),
    }


# ── owner-reviewed plan classification ────────────────────────────────────

def _classify_drift(offspring_result: dict, kind: str) -> str:
    """Classify observations without authorizing execution."""
    if not offspring_result.get("evidence_complete", True):
        return "EVIDENCE_INCOMPLETE"
    if kind in HISTORICAL_KINDS:
        return "HISTORICAL"
    drift = offspring_result.get("drift") or []
    if not drift:
        return "ALIGNED"
    has_missing = any(d.get("category") == "missing_files" for d in drift)
    has_schema = any(
        d.get("category") in ("product_schema_drift", "rappid_drift")
        for d in drift
    )
    has_kernel = any(d.get("category") == "kernel_drift" for d in drift)
    if has_kernel:
        return "GLOBAL_TO_LOCAL"
    if has_missing or has_schema:
        return "LOCAL_TO_GLOBAL"
    return "INFORMATIONAL"


def _owner_review_guidance(
    offspring_name: str,
    owner_repo: str | None,
    direction: str,
    kind: str,
) -> dict | None:
    if direction == "ALIGNED":
        return None
    source = owner_repo or f"<owner>/{offspring_name}"
    strategy = None
    if direction == "LOCAL_TO_GLOBAL":
        mechanism = (
            "Graft"
            if kind in ("neighborhood", "ant-farm", "braintrust", "workspace")
            else "Launch"
        )
        strategy = {
            "historical_mechanism": mechanism,
            "target_repository": source,
            "parameter_plan": (
                {"upstream_repo": source, "dry_run": True}
                if mechanism == "Graft"
                else {
                    "target_repo": source,
                    "instructions": "<owner-reviewed-diff>",
                    "dry_run": True,
                }
            ),
            "intent": (
                "prepare a publication proposal for missing or divergent "
                "offspring files"
            ),
        }
    elif direction == "GLOBAL_TO_LOCAL":
        strategy = {
            "historical_mechanism": "RarLoader",
            "source_repository": source,
            "parameter_plan": {
                "gate_repo": source,
                "dry_run": True,
            },
            "intent": (
                "prepare a separately verified local refresh proposal from "
                "offspring bytes"
            ),
        }
    elif direction == "HISTORICAL":
        strategy = {
            "historical_mechanism": "compare-only",
            "source_repository": source,
            "intent": (
                "retain the former required and optional file shape as drift "
                "evidence without reactivating the retired surface"
            ),
        }

    guidance = {
        "LOCAL_TO_GLOBAL": (
            "Review the exact source-labelled differences and the historical "
            "publication strategy; prepare a separate owner-authorized change "
            "proposal if still desired."
        ),
        "GLOBAL_TO_LOCAL": (
            "Review the exact source-labelled differences and the historical "
            "loader strategy; verify every candidate byte before a separate "
            "local update proposal."
        ),
        "EVIDENCE_INCOMPLETE": (
            "Restore fresh online evidence and rerun before planning a change."
        ),
        "HISTORICAL": (
            "Preserve and compare the retired shape as historical evidence; "
            "do not repair or reactivate it from this report."
        ),
        "INFORMATIONAL": (
            "Review the observation; no executable change is proposed."
        ),
    }.get(
        direction,
        "Review the observation; no executable change is proposed.",
    )
    return {
        "schema": "rapp-ecosystem-repair-plan/1.0",
        "status": "owner-review-required",
        "owner_review_required": True,
        "executable": False,
        "auto_execute": False,
        "apply_permitted": False,
        "direction": direction,
        "offspring": offspring_name,
        "kind": kind,
        "source_repository": source,
        "guidance": guidance,
        "historical_strategy": strategy,
        "required_gates": [
            "fresh source evidence",
            "exact diff review",
            "explicit owner approval",
            "authenticated RAPP/1 authority where acceptance is claimed",
            "separate non-automatic execution",
        ],
    }


def _suggest_action(
    offspring_name: str,
    owner_repo: str | None,
    direction: str,
    kind: str,
) -> dict | None:
    """Compatibility name for the retained, non-executable repair planner."""
    return _owner_review_guidance(
        offspring_name,
        owner_repo,
        direction,
        kind,
    )


# ── main audit ─────────────────────────────────────────────────────────────

def _build_file_getter_offline(fixture_dir: str | None):
    cached: dict[str, tuple[bytes | None, dict]] = {}

    def get(path: str):
        if path not in cached:
            body = (
                _read_fixture_file(fixture_dir, path)
                if fixture_dir is not None
                else None
            )
            cached[path] = (
                body,
                {
                    "path": path,
                    "source": "fixture" if fixture_dir else "none",
                    "status": "present" if body is not None else "missing",
                    "freshness": "offline-fixture",
                    "fixture_dir": fixture_dir,
                },
            )
        body, evidence = cached[path]
        get.evidence[path] = evidence
        return body, "fixture" if body is not None else "missing"

    get.evidence = {}
    return get


def _build_file_getter_online(owner_repo: str | None):
    cached: dict[str, tuple[bytes | None, dict]] = {}

    def get(path: str):
        if not owner_repo:
            evidence = {
                "path": path,
                "source": "none",
                "status": "unavailable",
                "freshness": "unavailable",
                "detail": "entry has no resolvable owner/repository source",
            }
            get.evidence[path] = evidence
            return None, "unavailable"
        if path not in cached:
            body, evidence = _fetch_offspring_file(owner_repo, path)
            evidence = {"path": path, **evidence}
            cached[path] = (body, evidence)
        body, evidence = cached[path]
        get.evidence[path] = evidence
        status = evidence.get("status")
        if status == "missing":
            source_label = "missing"
        elif status == "unavailable":
            source_label = "unavailable"
        else:
            source_label = str(evidence.get("source") or "unknown")
        return body, source_label

    get.evidence = {}
    return get


def _inspect_owner_approval(
    approval_path: str,
    *,
    operation: str,
    target: dict,
) -> dict:
    if not approval_path:
        return {
            "supplied": False,
            "structurally_matching": False,
            "authenticated": False,
            "fresh": False,
            "status": "MISSING",
            "detail": "an explicit owner-approval artifact is required",
        }
    path = os.path.expanduser(approval_path)
    try:
        with open(path, "rb") as handle:
            raw = handle.read()
        value = json.loads(raw)
    except (OSError, TypeError, ValueError) as exc:
        return {
            "supplied": True,
            "path": path,
            "structurally_matching": False,
            "authenticated": False,
            "fresh": False,
            "status": "INVALID",
            "detail": f"owner-approval artifact could not be inspected: {exc}",
        }
    structurally_matching = (
        type(value) is dict
        and value.get("schema") == APPROVAL_SCHEMA
        and value.get("operation") == operation
        and value.get("target") == target
    )
    return {
        "supplied": True,
        "path": path,
        "sha256": _sha256_bytes(raw),
        "byte_length": len(raw),
        "schema": value.get("schema") if type(value) is dict else None,
        "operation": value.get("operation") if type(value) is dict else None,
        "target": value.get("target") if type(value) is dict else None,
        "structurally_matching": structurally_matching,
        "authenticated": False,
        "fresh": False,
        "status": "STRUCTURAL_ONLY" if structurally_matching else "MISMATCH",
        "detail": (
            AUTHORITY_REASON
            if structurally_matching
            else "artifact schema, operation, or target does not exactly match"
        ),
    }


def _output_write_gate(out_dir: str, approval_path: str) -> dict:
    target = {
        "out_dir": os.path.abspath(os.path.expanduser(out_dir)),
        "artifacts": [
            "ecosystem-audit.json",
            "ecosystem-audit.md",
        ],
    }
    approval = _inspect_owner_approval(
        approval_path,
        operation="ecosystem-audit-write",
        target=target,
    )
    if not approval["supplied"]:
        code = "owner-approval-artifact-required"
    elif not approval["structurally_matching"]:
        code = "owner-approval-artifact-invalid"
    else:
        code = "authenticated-registry-unavailable"
    return {
        "permitted": False,
        "code": code,
        "detail": approval["detail"],
        "target": target,
        "approval": approval,
        "prerequisites": {
            "explicit_write_flag": True,
            "owner_approval_artifact_supplied": approval["supplied"],
            "owner_approval_artifact_matches": approval[
                "structurally_matching"
            ],
            "section_13_registry_authenticated": False,
            "registry_freshness_verified": False,
            "out_of_band_estate_owner_anchor_verified": False,
        },
    }


def audit_ecosystem(*, mode: str = "offline",
                    repo_filter: str | None = None,
                    metropolis_index_path: str | None = None,
                    fixtures_dir: str | None = None,
                    out_dir: str | None = None,
                    write_outputs: bool = False,
                    owner_approval_path: str = "") -> dict:
    """Run the audit. Returns the rapp-ecosystem-audit/1.0 envelope."""
    metropolis_path = metropolis_index_path or DEFAULT_METROPOLIS
    fixtures = fixtures_dir or DEFAULT_FIXTURES_DIR
    out = out_dir or DEFAULT_AUDIT_OUT_DIR

    if not os.path.exists(metropolis_path):
        return {
            "schema": AUDIT_SCHEMA,
            "audited_at": _now_iso(),
            "ok": False,
            "status": "EVIDENCE_INCOMPLETE",
            "evidence_complete": False,
            "incomplete_count": 1,
            "error": f"metropolis index not found at {metropolis_path}",
        }

    with open(metropolis_path) as f:
        metropolis = json.load(f)
    entries = metropolis.get("entries") or []
    metropolis_url = metropolis.get("tracker_url") or "(no tracker_url)"

    if repo_filter:
        # match by name OR by owner/repo gate_repo
        filtered = []
        for e in entries:
            if e.get("name") == repo_filter:
                filtered.append(e); continue
            owner_repo = _owner_repo_from_entry(e)
            if owner_repo == repo_filter:
                filtered.append(e); continue
        entries = filtered

    by_kind = {}
    offspring_results = []
    next_actions = []

    for entry in entries:
        name = entry.get("name") or "(unnamed)"
        kind = kind_for_entry(entry)
        contract = contract_for_kind(kind)
        owner_repo = _owner_repo_from_entry(entry)
        entry_rappid = entry.get("neighborhood_rappid")
        entry_identity_drift = _metropolis_rappid_drift(entry_rappid)

        if mode == "online":
            getter = _build_file_getter_online(owner_repo)
        else:
            fixture_dir = _find_fixture_dir(name, fixtures)
            getter = _build_file_getter_offline(fixture_dir)
            if fixture_dir is None:
                result = {
                    "name": name,
                    "kind": kind,
                    "rappid": entry_rappid,
                    "ok": not entry_identity_drift,
                    "skipped": not entry_identity_drift,
                    "drift": entry_identity_drift,
                    "fetched_from": "none",
                    "fingerprint_sha256": None,
                    "evidence_complete": True,
                    "file_evidence": {},
                    "kind_lifecycle": contract.get(
                        "lifecycle", "product-observation"
                    ),
                    "_note": (
                        "--offline mode; no "
                        f"tests/fixtures/{name}/ or {name}-seed/ found."
                    ),
                }
                if result["skipped"]:
                    result["skip_reason"] = "no_fixture"
                offspring_results.append(result)
                bucket = by_kind.setdefault(
                    kind,
                    {"ok": 0, "drift": 0, "incomplete": 0, "skipped": 0},
                )
                if result["skipped"]:
                    bucket["skipped"] += 1
                else:
                    bucket["drift"] += 1
                    direction = _classify_drift(result, kind)
                    action = _suggest_action(
                        name, owner_repo, direction, kind
                    )
                    if action:
                        next_actions.append(action)
                continue

        result = _diff_offspring(name, kind, contract, getter, owner_repo)
        result["drift"] = entry_identity_drift + result["drift"]
        source_rappid = result.get("rappid")
        if (
            isinstance(source_rappid, str)
            and isinstance(entry_rappid, str)
            and source_rappid != entry_rappid
        ):
            result["drift"].append({
                "category": "rappid_drift",
                "path": "rappid.json",
                "detail": (
                    "fixture/source rappid does not exactly match metropolis "
                    f"neighborhood_rappid: source={source_rappid!r}, "
                    f"metropolis={entry_rappid!r}"
                ),
            })
        result["ok"] = (
            not result["drift"]
            and result.get("evidence_complete", True)
        )
        result["name"] = name
        result["kind"] = kind
        result["kind_contract_version"] = "1.0"
        result["kind_observation_version"] = "1.0"
        result["entry_metropolis_rappid"] = entry_rappid
        offspring_results.append(result)

        bucket = by_kind.setdefault(
            kind,
            {"ok": 0, "drift": 0, "incomplete": 0, "skipped": 0},
        )
        if result["ok"]:
            bucket["ok"] += 1
        else:
            if not result.get("evidence_complete", True):
                bucket["incomplete"] += 1
            if result["drift"]:
                bucket["drift"] += 1
            direction = _classify_drift(result, kind)
            action = _suggest_action(
                name, owner_repo, direction, kind
            )
            if action:
                next_actions.append(action)

    drift_count = sum(
        1
        for result in offspring_results
        if result.get("drift") and not result.get("skipped")
    )
    incomplete_count = sum(
        1
        for result in offspring_results
        if not result.get("evidence_complete", True)
        and not result.get("skipped")
    )
    evidence_complete = incomplete_count == 0

    summary = {
        "_purpose": (
            "Source-labelled observations for owner review; this report "
            "authorizes no execution."
        ),
        "local_to_global_candidates": [
            item["offspring"]
            for item in next_actions
            if item["direction"] == "LOCAL_TO_GLOBAL"
        ],
        "global_to_local_candidates": [
            item["offspring"]
            for item in next_actions
            if item["direction"] == "GLOBAL_TO_LOCAL"
        ],
        "evidence_incomplete": [
            item["offspring"]
            for item in next_actions
            if item["direction"] == "EVIDENCE_INCOMPLETE"
        ],
        "historical_only": [
            item["offspring"]
            for item in next_actions
            if item["direction"] == "HISTORICAL"
        ],
        "informational_only": [
            item["offspring"]
            for item in next_actions
            if item["direction"] == "INFORMATIONAL"
        ],
    }

    audit = {
        "schema": AUDIT_SCHEMA,
        "authority_state": "product-local-observation",
        "rapp_protocol_authority": False,
        "accepted": False,
        "auto_execute": False,
        "audited_at": _now_iso(),
        "mode": mode,
        "metropolis_url": metropolis_url,
        "metropolis_path": metropolis_path,
        "offspring_count": len(offspring_results),
        "drift_count": drift_count,
        "incomplete_count": incomplete_count,
        "evidence_complete": evidence_complete,
        "status": (
            "EVIDENCE_INCOMPLETE"
            if not evidence_complete
            else "DRIFT_OBSERVED"
            if drift_count
            else "COMPLETE"
        ),
        "by_kind": by_kind,
        "offspring": offspring_results,
        "summary": summary,
        "next_actions": next_actions,
        "repair_plans": next_actions,
        "owner_review_required": bool(next_actions),
        "write_outputs_requested": bool(write_outputs),
        "ok": drift_count == 0 and evidence_complete,
    }

    if write_outputs:
        write_gate = _output_write_gate(out, owner_approval_path)
        audit["output_write"] = write_gate
        if write_gate["permitted"]:
            _write_outputs(audit, out)
            audit["output_write"]["written"] = True
        else:
            audit["output_write"]["written"] = False

    return audit


# ── output writers ────────────────────────────────────────────────────────

def render_human_report(audit: dict) -> str:
    """Markdown rendering of the audit dict."""
    lines = []
    lines.append("# Bond Pulse — Ecosystem Observation Audit\n")
    lines.append(f"> Schema: `{audit.get('schema')}`. Generated by `tools/ecosystem_audit.py`.\n")
    lines.append(
        "> This report is source-labelled owner-review guidance only. "
        "It authorizes no execution.\n"
    )
    lines.append(f"- **Audited at:** {audit.get('audited_at')}")
    lines.append(f"- **Mode:** `{audit.get('mode')}`")
    lines.append(f"- **Status:** `{audit.get('status')}`")
    lines.append(f"- **Evidence complete:** `{audit.get('evidence_complete')}`")
    lines.append(f"- **Metropolis:** {audit.get('metropolis_url')}")
    lines.append(f"- **Offspring audited:** {audit.get('offspring_count')}")
    lines.append(f"- **Drift count:** {audit.get('drift_count')}")
    lines.append(f"- **Incomplete evidence count:** {audit.get('incomplete_count')}")
    lines.append("")

    by_kind = audit.get("by_kind") or {}
    if by_kind:
        lines.append("## By kind\n")
        lines.append("| Kind | Aligned | Drifted | Incomplete | Skipped |")
        lines.append("|---|---|---|---|---|")
        for kind in sorted(by_kind.keys()):
            b = by_kind[kind]
            lines.append(
                f"| `{kind}` | {b.get('ok', 0)} | {b.get('drift', 0)} | "
                f"{b.get('incomplete', 0)} | {b.get('skipped', 0)} |"
            )
        lines.append("")

    summary = audit.get("summary") or {}
    push = summary.get("local_to_global_candidates") or []
    pull = summary.get("global_to_local_candidates") or []
    incomplete = summary.get("evidence_incomplete") or []
    historical = summary.get("historical_only") or []
    info = summary.get("informational_only") or []
    if push or pull or incomplete or historical or info:
        lines.append("## Observation classifications\n")
        if push:
            lines.append(
                f"**LOCAL → GLOBAL candidates** ({len(push)}): "
                f"{', '.join(push)}"
            )
        if pull:
            lines.append(
                f"**GLOBAL → LOCAL candidates** ({len(pull)}): "
                f"{', '.join(pull)}"
            )
        if incomplete:
            lines.append(
                f"**Evidence incomplete** ({len(incomplete)}): "
                f"{', '.join(incomplete)}"
            )
        if historical:
            lines.append(
                f"**Historical only** ({len(historical)}): "
                f"{', '.join(historical)}"
            )
        if info:
            lines.append(f"**Informational only** ({len(info)}): {', '.join(info)}")
        lines.append("")

    actions = audit.get("next_actions") or []
    if actions:
        lines.append("## Owner-reviewed plan guidance\n")
        for a in actions:
            lines.append(
                f"- **{a['offspring']}** ({a['direction']}) — "
                f"{a.get('guidance', '')}"
            )
            lines.append("  - Executable: `false`; owner review required.")
            strategy = a.get("historical_strategy") or {}
            if strategy:
                lines.append(
                    "  - Retained strategy: "
                    f"`{strategy.get('historical_mechanism')}`"
                )
                if strategy.get("parameter_plan"):
                    lines.append(
                        "  - Read-only parameter plan: `"
                        + json.dumps(
                            strategy["parameter_plan"],
                            sort_keys=True,
                        )
                        + "`"
                    )
        lines.append("")

    lines.append("## Per-offspring detail\n")
    for o in (audit.get("offspring") or []):
        if o.get("skipped"):
            status = "🟡 skipped"
        elif not o.get("evidence_complete", True):
            status = "⛔ evidence incomplete"
        elif o.get("kind_lifecycle") == "historical-observation":
            status = "📜 historical observation"
        else:
            status = "✅ aligned" if o.get("ok") else "⚠️ drifted"
        lines.append(f"### {o.get('name')} — {status}\n")
        lines.append(f"- kind: `{o.get('kind')}`")
        lines.append(f"- lifecycle: `{o.get('kind_lifecycle')}`")
        lines.append(f"- rappid: `{(o.get('rappid') or o.get('entry_metropolis_rappid') or '(none)')[:96]}`")
        lines.append(f"- fetched_from: `{o.get('fetched_from')}`")
        if o.get("skipped"):
            lines.append(f"- skip_reason: `{o.get('skip_reason')}`")
        for d in (o.get("drift") or []):
            lines.append(f"- ⚠️ **{d.get('category')}** at `{d.get('path')}` — {d.get('detail')}")
        for issue in (o.get("evidence_issues") or []):
            lines.append(
                f"- ⛔ **evidence** at `{issue.get('path')}` — "
                f"source={issue.get('source')}, "
                f"freshness={issue.get('freshness')}: "
                f"{issue.get('detail')}"
            )
        lines.append("")

    return "\n".join(lines) + "\n"


def _write_outputs(audit: dict, out_dir: str) -> None:
    try:
        os.makedirs(out_dir, exist_ok=True)
    except OSError:
        return
    json_path = os.path.join(out_dir, "ecosystem-audit.json")
    md_path = os.path.join(out_dir, "ecosystem-audit.md")
    try:
        with open(json_path, "w") as f:
            json.dump(audit, f, indent=2)
            f.write("\n")
        with open(md_path, "w") as f:
            f.write(render_human_report(audit))
    except OSError:
        pass


# ── CLI ────────────────────────────────────────────────────────────────────

def _resolve_mode(args) -> str:
    if args.online:
        return "online"
    if args.offline:
        return "offline"
    if os.environ.get("ECOSYSTEM_AUDIT_ONLINE") == "1":
        return "online"
    return "offline"


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="ecosystem_audit",
        description=(
            "Source-labelled ecosystem observations with owner-reviewed, "
            "non-executable plan guidance."
        ),
    )
    p.add_argument("--offline", action="store_true",
                   help="Use checked-in fixtures only (default; CI-safe).")
    p.add_argument("--online", action="store_true",
                   help="Attempt fresh evidence via gh api + raw.githubusercontent.com.")
    p.add_argument("--repo", default=None,
                   help="Audit one offspring by name or owner/repo.")
    p.add_argument("--metropolis", default=None,
                   help="Override path to pages/metropolis/index.json.")
    p.add_argument("--fixtures-dir", default=None,
                   help="Override tests/fixtures/ directory (used by --offline).")
    p.add_argument("--out-dir", default=None,
                   help="Target directory used only with --write.")
    p.add_argument(
        "--write",
        action="store_true",
        help="request gated JSON and Markdown output writes",
    )
    p.add_argument("--no-write", action="store_true",
                   help="compatibility flag for default read-only behavior")
    p.add_argument(
        "--owner-approval",
        default="",
        help="target-owned approval artifact required with --write",
    )
    p.add_argument("--strict", action="store_true", default=True,
                   help="Exit 1 if drift_count > 0 (default).")
    p.add_argument("--lenient", dest="strict", action="store_false",
                   help="Exit 0 even if drift detected (just report).")
    args = p.parse_args(argv)

    mode = _resolve_mode(args)
    write_requested = bool(args.write and not args.no_write)
    audit = audit_ecosystem(
        mode=mode,
        repo_filter=args.repo,
        metropolis_index_path=args.metropolis,
        fixtures_dir=args.fixtures_dir,
        out_dir=args.out_dir,
        write_outputs=write_requested,
        owner_approval_path=args.owner_approval,
    )

    write_result = audit.get("output_write") or {}
    if not write_result.get("written"):
        print(json.dumps(audit, indent=2))
    else:
        print(json.dumps({
            "schema": AUDIT_SCHEMA,
            "audited_at": audit.get("audited_at"),
            "mode": audit.get("mode"),
            "status": audit.get("status"),
            "evidence_complete": audit.get("evidence_complete"),
            "offspring_count": audit.get("offspring_count"),
            "drift_count": audit.get("drift_count"),
            "incomplete_count": audit.get("incomplete_count"),
            "by_kind": audit.get("by_kind"),
            "outputs": {
                "markdown": os.path.join(args.out_dir or DEFAULT_AUDIT_OUT_DIR, "ecosystem-audit.md"),
                "json":     os.path.join(args.out_dir or DEFAULT_AUDIT_OUT_DIR, "ecosystem-audit.json"),
            },
        }, indent=2))

    if write_requested and not write_result.get("written"):
        return 2
    if not audit.get("evidence_complete", False):
        return 2
    if args.strict and audit.get("drift_count", 0) > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
