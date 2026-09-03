"""RarStewardAgent — read-only steward of an explicitly sourced RAR catalog.

A registry rots when it fills with undocumented stubs, placeholders, and
same-but-different agents. This restored steward keeps the original substantive
analysis:

* ``health`` scores card coverage, placeholder pressure, and duplication.
* ``duplicates`` clusters agents that may belong in one reviewed base.
* ``junk`` identifies low-quality records without deleting them.
* ``agent`` performs a deeper assessment using catalog or explicitly supplied
  card data.
* ``issue_plan`` / legacy ``file_issues`` produces deterministic issue drafts.

The safety adapter is intentionally read-only. The default source is the local
committed Cave catalog. Network reads require an explicit immutable reference
and SHA-256. Moving GitHub refs are rejected. Issue actions only return plans;
they never invoke GitHub, write files, install code, stream artifacts, or accept
catalog entries.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

try:
    from agents.basic_agent import BasicAgent  # type: ignore
except ImportError:
    try:
        from basic_agent import BasicAgent  # type: ignore
    except ImportError:
        class BasicAgent:
            def __init__(self, name="Agent", metadata=None):
                self.name = name
                self.metadata = metadata or {}


__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "@rapp/rar_steward",
    "version": "1.0.0",
    "display_name": "RarStewardAgent",
    "description": (
        "Read-only RAR steward: surveys catalog health, clusters "
        "same-but-different agents, flags low-quality records, and produces "
        "operator review plans without filing issues or changing a catalog."
    ),
    "author": "Kody Wildfeuer",
    "tags": [
        "rar",
        "steward",
        "registry",
        "quality",
        "dedup",
        "merge",
        "curation",
    ],
    "category": "core",
    "quality_tier": "official",
    "requires_env": [],
    "dependencies": ["@rapp/basic_agent"],
    "safety": {
        "default_mode": "read-only",
        "network_default": False,
        "writes": False,
        "issue_creation": False,
        "installation": False,
        "streaming": False,
        "acceptance": False,
    },
}

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG_PATH = "cave/rar/index.json"
STEWARD_TRACKER = "kody-w/RAR"
STEWARD_LABEL = "rar-steward"

_STOP = {
    "agent",
    "the",
    "a",
    "an",
    "of",
    "for",
    "to",
    "and",
    "or",
    "rapp",
    "generator",
    "helper",
    "tool",
    "assistant",
    "v1",
    "v2",
    "py",
}
_PLACEHOLDER = re.compile(
    r"\b(test|tmp|temp|demo|foo|bar|baz|example|placeholder|untitled|"
    r"copy|wip|draft|sample|hello[_-]?world)\b",
    re.IGNORECASE,
)
_DUP_THRESHOLD = 0.6
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_MOVING_REFS = {"main", "master", "head", "latest", "trunk"}


class SourceError(ValueError):
    """Raised when a catalog or card source is unsafe or invalid."""


def _scrub(text):
    """Redact token-shaped strings before they enter a return envelope."""
    if not text:
        return text
    text = re.sub(r"gh[pousr]_[A-Za-z0-9]{20,}", "[redacted-token]", text)
    text = re.sub(r"github_pat_[A-Za-z0-9_]{20,}", "[redacted-token]", text)
    return re.sub(
        r"(?i)(authorization|token|bearer|secret|password)\s*[:=]\s*\S+",
        r"\1=[redacted]",
        text,
    )


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _tokens(text):
    return {
        token
        for token in re.split(r"[^a-z0-9]+", (text or "").lower())
        if token and token not in _STOP and len(token) > 1
    }


def _jaccard(left, right):
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def _safe_local_path(value):
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = REPO_ROOT / candidate
    candidate = candidate.resolve()
    try:
        candidate.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise SourceError("local sources must remain inside the repository") from exc
    if not candidate.is_file():
        raise SourceError(f"local source is not a file: {candidate}")
    return candidate


def _validate_network_source(url, source_ref, expected_sha256):
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise SourceError("network sources must use an explicit https URL")
    if not _SHA256.fullmatch((expected_sha256 or "").lower()):
        raise SourceError("network sources require an explicit SHA-256 checksum")

    path_parts = {part.lower() for part in parsed.path.split("/") if part}
    if path_parts & _MOVING_REFS:
        raise SourceError("moving refs such as main/master/latest are observations only")

    host = parsed.netloc.lower()
    if host in {"github.com", "raw.githubusercontent.com", "api.github.com"}:
        candidates = [
            part.lower()
            for part in parsed.path.split("/")
            if _COMMIT.fullmatch(part.lower())
        ]
        if source_ref and _COMMIT.fullmatch(str(source_ref).lower()):
            candidates.append(str(source_ref).lower())
        if not candidates:
            raise SourceError(
                "GitHub network sources require a full 40-character commit pin"
            )


def _fetch_bytes(url, timeout=15):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "rapp-rar-steward-read-only/1.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _load_json_source(
    *,
    label,
    local_path=None,
    url=None,
    source_ref=None,
    expected_sha256=None,
):
    if local_path and url:
        raise SourceError(f"{label}: choose a local path or URL, not both")

    if url:
        _validate_network_source(url, source_ref, expected_sha256)
        try:
            raw = _fetch_bytes(url)
        except Exception as exc:
            raise SourceError(f"{label}: network read failed: {_scrub(str(exc))}") from exc
        digest = _sha256_bytes(raw)
        if digest != str(expected_sha256).lower():
            raise SourceError(f"{label}: SHA-256 mismatch")
        source = {
            "kind": "network",
            "url": url,
            "ref": source_ref,
            "sha256": digest,
            "checksum_verified": True,
            "accepted": False,
        }
    else:
        path = _safe_local_path(local_path or DEFAULT_CATALOG_PATH)
        raw = path.read_bytes()
        digest = _sha256_bytes(raw)
        checksum_verified = False
        if expected_sha256:
            if not _SHA256.fullmatch(str(expected_sha256).lower()):
                raise SourceError(f"{label}: invalid SHA-256 checksum")
            if digest != str(expected_sha256).lower():
                raise SourceError(f"{label}: SHA-256 mismatch")
            checksum_verified = True
        source = {
            "kind": "local",
            "path": path.relative_to(REPO_ROOT).as_posix(),
            "sha256": digest,
            "checksum_verified": checksum_verified,
            "accepted": False,
        }

    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceError(f"{label}: source is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise SourceError(f"{label}: top-level JSON value must be an object")
    return value, source


class _UF:
    def __init__(self, size):
        self.parents = list(range(size))

    def find(self, value):
        while self.parents[value] != value:
            self.parents[value] = self.parents[self.parents[value]]
            value = self.parents[value]
        return value

    def union(self, left, right):
        self.parents[self.find(left)] = self.find(right)


class RarStewardAgent(BasicAgent):
    def __init__(self):
        self.name = "RarStewardAgent"
        self.metadata = {
            "name": self.name,
            "description": (
                "Read-only RAR analysis: catalog health, merge-candidate "
                "clusters, low-quality records, deep assessment, and issue "
                "drafts. No issue creation, catalog writes, installation, "
                "streaming, or acceptance."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "health",
                            "duplicates",
                            "junk",
                            "agent",
                            "issue_plan",
                            "file_issues",
                            "help",
                        ],
                    },
                    "name": {
                        "type": "string",
                        "description": "agent: rar_name or id to assess",
                    },
                    "publisher": {
                        "type": "string",
                        "description": "optional publisher filter, such as @kody-w",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "maximum clusters/items to return (default 25)",
                    },
                    "scope": {
                        "type": "string",
                        "enum": ["merge", "junk", "all"],
                        "description": "issue plan scope (default all)",
                    },
                    "catalog_path": {
                        "type": "string",
                        "description": (
                            "repository-local JSON source; defaults to "
                            "cave/rar/index.json"
                        ),
                    },
                    "catalog_url": {
                        "type": "string",
                        "description": (
                            "explicit immutable HTTPS catalog URL; requires "
                            "catalog_sha256 and a full GitHub commit pin"
                        ),
                    },
                    "catalog_ref": {
                        "type": "string",
                        "description": "explicit immutable source reference",
                    },
                    "catalog_sha256": {
                        "type": "string",
                        "description": "expected SHA-256 for an explicit source",
                    },
                    "card_path": {
                        "type": "string",
                        "description": "optional repository-local card JSON",
                    },
                    "card_url": {
                        "type": "string",
                        "description": "optional pinned HTTPS card URL",
                    },
                    "card_ref": {
                        "type": "string",
                        "description": "explicit immutable card source reference",
                    },
                    "card_sha256": {
                        "type": "string",
                        "description": "required SHA-256 for card_url",
                    },
                    "tracker": {
                        "type": "string",
                        "description": "owner/repo recorded in issue drafts",
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": (
                            "legacy field retained for compatibility; ignored "
                            "because this adapter never files issues"
                        ),
                    },
                    "existing_issues_path": {
                        "type": "string",
                        "description": (
                            "optional repository-local JSON issue export used "
                            "for read-only fingerprint deduplication"
                        ),
                    },
                },
            },
        }
        super().__init__(self.name, self.metadata)

    def system_context(self):
        return (
            "RarStewardAgent analyzes explicitly sourced catalog observations. "
            "It defaults to the local Cave catalog and never writes, installs, "
            "streams, files issues, or accepts artifacts. Remote data requires "
            "a checksum and immutable pin."
        )

    def _env(self, action, status, **fields):
        return json.dumps(
            {
                "schema": "rapp-rar-steward/1.0",
                "action": action,
                "status": status,
                "mode": "read-only",
                "writes_performed": False,
                "accepted": False,
                **fields,
            },
            indent=2,
            ensure_ascii=False,
        )

    def _catalog(self, kwargs):
        catalog_url = (kwargs.get("catalog_url") or "").strip() or None
        catalog_path = None
        if not catalog_url:
            catalog_path = (
                (kwargs.get("catalog_path") or DEFAULT_CATALOG_PATH).strip()
            )
        document, source = _load_json_source(
            label="catalog",
            local_path=catalog_path,
            url=catalog_url,
            source_ref=kwargs.get("catalog_ref"),
            expected_sha256=kwargs.get("catalog_sha256"),
        )
        agents = document.get("agents", [])
        if not isinstance(agents, list):
            raise SourceError("catalog: agents must be an array")
        agents = [agent for agent in agents if isinstance(agent, dict)]
        publisher = kwargs.get("publisher")
        if publisher:
            expected = "@" + str(publisher).lstrip("@")
            agents = [
                agent
                for agent in agents
                if agent.get("publisher") in {publisher, expected}
                or str(agent.get("name", "")).startswith(expected + "/")
            ]
        source["catalog_schema"] = document.get("schema")
        source["catalog_accepted"] = bool(document.get("accepted", False))
        return agents, source

    def _card(self, hit, kwargs):
        card_url = (kwargs.get("card_url") or "").strip() or None
        card_path = (kwargs.get("card_path") or "").strip() or None
        if card_url or card_path:
            return _load_json_source(
                label="card",
                local_path=card_path,
                url=card_url,
                source_ref=kwargs.get("card_ref"),
                expected_sha256=kwargs.get("card_sha256"),
            )
        for key in ("card", "manifest"):
            value = hit.get(key)
            if isinstance(value, dict):
                return value, {
                    "kind": "inline",
                    "field": key,
                    "checksum_verified": False,
                    "accepted": False,
                }
        return {}, {
            "kind": "catalog-entry",
            "checksum_verified": False,
            "accepted": False,
        }

    def _clusters(self, agents):
        tokens = [
            _tokens(
                agent.get("name", "")
                + " "
                + agent.get("id", "").split("__")[-1]
            )
            for agent in agents
        ]
        union = _UF(len(agents))
        for left in range(len(agents)):
            for right in range(left + 1, len(agents)):
                if not tokens[left] or not tokens[right]:
                    continue
                similarity = _jaccard(tokens[left], tokens[right])
                same_category = (
                    agents[left].get("category")
                    and agents[left].get("category")
                    == agents[right].get("category")
                )
                threshold = _DUP_THRESHOLD - (0.1 if same_category else 0)
                if similarity >= threshold:
                    union.union(left, right)

        groups = {}
        for index in range(len(agents)):
            groups.setdefault(union.find(index), []).append(index)

        clusters = []
        for members in groups.values():
            if len(members) < 2:
                continue
            records = [agents[index] for index in members]
            common = (
                set.intersection(*[tokens[index] for index in members])
                if all(tokens[index] for index in members)
                else set()
            )
            base = (
                "_".join(sorted(common))
                or "_".join(sorted(_tokens(records[0].get("name", "")))[:2])
                or "unified"
            )
            clusters.append(
                {
                    "recommended_base": f"{base}_agent.py",
                    "size": len(records),
                    "publishers": sorted(
                        {
                            record.get("publisher")
                            for record in records
                            if record.get("publisher")
                        }
                    ),
                    "category": records[0].get("category"),
                    "members": [
                        {
                            "rar_name": record.get("rar_name")
                            or record.get("name"),
                            "name": record.get("name"),
                            "publisher": record.get("publisher"),
                        }
                        for record in records
                    ],
                    "why": (
                        "these share the core name tokens "
                        + (
                            ", ".join(sorted(common))
                            if common
                            else "(near-overlap)"
                        )
                        + " — review whether one quality base can cover the "
                        "union of their inputs and outputs."
                    ),
                }
            )
        clusters.sort(key=lambda cluster: -cluster["size"])
        return clusters

    def _junk(self, agents):
        findings = []
        seen = {}
        for agent in agents:
            reasons = []
            name = agent.get("name", "")
            identifier = agent.get("id", "")
            if not agent.get("has_card") and not agent.get("manifest"):
                reasons.append("no card (undocumented — no summary/tags)")
            version = str(agent.get("version", ""))
            if (
                version in ("", "0.0.0")
                or version.endswith("-stub")
                or version.startswith("0.0")
            ):
                reasons.append(f"pre-release/stub version ({version or 'none'})")
            if _PLACEHOLDER.search(name) or _PLACEHOLDER.search(identifier):
                reasons.append("placeholder/test name")
            key = (agent.get("rar_name") or identifier or name).lower()
            if key in seen:
                reasons.append(f"exact duplicate rar_name of {seen[key]}")
            else:
                seen[key] = agent.get("rar_name") or identifier or name
            if reasons:
                findings.append(
                    {
                        "rar_name": agent.get("rar_name") or name,
                        "name": name,
                        "publisher": agent.get("publisher"),
                        "reasons": reasons,
                    }
                )
        return findings

    def _fp(self, *parts):
        key = "|".join(str(part) for part in parts)
        return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]

    def _existing_fingerprints(self, path_value):
        if not path_value:
            return {}
        path = _safe_local_path(path_value)
        try:
            records = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SourceError("existing issue export is not valid JSON") from exc
        if not isinstance(records, list):
            raise SourceError("existing issue export must be an array")
        existing = {}
        for record in records:
            if not isinstance(record, dict):
                continue
            blob = (
                str(record.get("title", ""))
                + "\n"
                + str(record.get("body", ""))
            )
            for fingerprint in re.findall(
                r'(?:fp:|"fingerprint"\s*:\s*")([0-9a-f]{12})',
                blob,
            ):
                existing.setdefault(fingerprint, record.get("number"))
        return existing

    def _file_issues(
        self,
        items,
        tracker,
        label,
        prefix,
        confirm,
        existing_issues_path=None,
    ):
        """Return idempotent issue drafts; never list or create remote issues."""
        existing = self._existing_fingerprints(existing_issues_path)
        skipped_existing = []
        planned = []
        for item in items:
            fingerprint = item["fingerprint"]
            title = f"[{prefix}] {item['title']} (fp:{fingerprint})"
            machine = {
                "schema": "rapp-drift-issue/1.0",
                "fingerprint": fingerprint,
                "prefix": prefix,
                **(item.get("machine") or {}),
            }
            body = (
                item["body_md"]
                + "\n\n```json\n"
                + json.dumps(machine, ensure_ascii=False)
                + "\n```\n"
            )
            if fingerprint in existing:
                skipped_existing.append(
                    {
                        "fingerprint": fingerprint,
                        "title": title,
                        "number": existing[fingerprint],
                    }
                )
                continue
            planned.append(
                {
                    "title": title,
                    "fingerprint": fingerprint,
                    "body": body,
                    "would_file": False,
                }
            )
        return {
            "tracker": tracker,
            "label": label,
            "legacy_confirm_requested": bool(confirm),
            "write_authorized": False,
            "write_performed": False,
            "reason": (
                "This adapter produces review drafts only. File or modify an "
                "issue through a separately authorized human workflow."
            ),
            "skipped_existing": skipped_existing,
            "planned": planned,
        }

    def perform(self, **kwargs):
        action = (kwargs.get("action") or "health").lower()
        valid_actions = {
            "health",
            "duplicates",
            "junk",
            "agent",
            "issue_plan",
            "file_issues",
        }
        if action == "help" or action not in valid_actions:
            return (
                "RarStewardAgent — read-only catalog quality analysis.\n"
                "  action=health           catalog health + quality score\n"
                "  action=duplicates       same-but-different review clusters\n"
                "  action=junk             low-quality records to review\n"
                "  action=agent name=…     deep assessment of one record\n"
                "  action=issue_plan       deterministic issue drafts\n"
                "  action=file_issues      legacy alias; still plan-only\n"
                "  catalog_path=…          local source (default cave/rar/index.json)\n"
                "  catalog_url=… catalog_sha256=… catalog_ref=<40-hex commit>\n"
                "Network sources must be immutable and checksummed. No action "
                "writes, installs, streams, files issues, or accepts entries."
            )

        try:
            limit = max(1, min(int(kwargs.get("limit") or 25), 200))
        except (TypeError, ValueError):
            limit = 25

        try:
            agents, source = self._catalog(kwargs)
        except SourceError as exc:
            return self._env(action, "error", error=_scrub(str(exc)))

        if action == "agent":
            name = (kwargs.get("name") or "").strip()
            if not name:
                return self._env(
                    action,
                    "error",
                    error="pass name=<rar_name or id>",
                    source=source,
                )
            hit = next(
                (
                    agent
                    for agent in agents
                    if name
                    in " ".join(
                        str(agent.get(key, ""))
                        for key in ("rar_name", "id", "name")
                    )
                ),
                None,
            )
            if not hit:
                return self._env(
                    action,
                    "not_found",
                    name=name,
                    source=source,
                )
            try:
                card, card_source = self._card(hit, kwargs)
            except SourceError as exc:
                return self._env(
                    action,
                    "error",
                    error=_scrub(str(exc)),
                    source=source,
                )
            score = 100
            notes = []
            if not hit.get("has_card") and not hit.get("manifest"):
                score -= 40
                notes.append("no card")
            summary = (
                card.get("summary")
                or card.get("description")
                or hit.get("purpose")
                or ""
            )
            if len(summary) < 40:
                score -= 20
                notes.append("thin/absent summary")
            if not (card.get("tags") or hit.get("tags")):
                score -= 15
                notes.append("no tags")
            if _PLACEHOLDER.search(hit.get("name", "")):
                score -= 25
                notes.append("placeholder name")
            return self._env(
                action,
                "success",
                source=source,
                card_source=card_source,
                rar_name=hit.get("rar_name") or hit.get("name"),
                quality_score=max(0, score),
                notes=notes or ["looks healthy as an unaccepted observation"],
                summary=summary[:200],
                category=hit.get("category"),
            )

        if not agents:
            return self._env(
                action,
                "empty",
                source=source,
                note="no agents matched the explicit source.",
            )

        if action in {"issue_plan", "file_issues"}:
            scope = (kwargs.get("scope") or "all").lower()
            if scope not in {"merge", "junk", "all"}:
                scope = "all"
            items = []
            if scope in {"merge", "all"}:
                for cluster in self._clusters(agents):
                    members = [
                        member["rar_name"] for member in cluster["members"]
                    ]
                    fingerprint = self._fp("merge", *sorted(members))
                    body = (
                        f"**Merge candidate** — {cluster['size']} "
                        "same-but-different agents.\n\n"
                        f"Recommended unified base: "
                        f"`{cluster['recommended_base']}`\n\n"
                        "Members:\n"
                        + "".join(
                            f"- `{member}`\n" for member in sorted(members)
                        )
                        + f"\nWhy: {cluster['why']}\n\n"
                        "Review the union of behavior and preserve lineage. "
                        "This plan does not merge or retire anything."
                    )
                    items.append(
                        {
                            "title": (
                                f"review {cluster['size']} related agents → "
                                f"{cluster['recommended_base']}"
                            ),
                            "fingerprint": fingerprint,
                            "body_md": body,
                            "machine": {
                                "kind": "merge",
                                "recommended_base": cluster[
                                    "recommended_base"
                                ],
                                "members": members,
                            },
                        }
                    )
            if scope in {"junk", "all"}:
                confirmable = ("no card", "placeholder", "duplicate")
                for finding in self._junk(agents):
                    reasons = finding["reasons"]
                    if not any(
                        marker in " ".join(reasons).lower()
                        for marker in confirmable
                    ):
                        continue
                    fingerprint = self._fp(
                        "junk",
                        finding["rar_name"],
                        *reasons,
                    )
                    body = (
                        f"**Review candidate** — "
                        f"`{finding['rar_name']}`\n\n"
                        "Reasons flagged:\n"
                        + "".join(f"- {reason}\n" for reason in reasons)
                        + "\nReview and improve, annotate, or retain the "
                        "record. The steward never deletes it."
                    )
                    items.append(
                        {
                            "title": (
                                f"review: {finding['rar_name']} "
                                f"({', '.join(reasons)})"
                            ),
                            "fingerprint": fingerprint,
                            "body_md": body,
                            "machine": {
                                "kind": "junk",
                                "rar_name": finding["rar_name"],
                                "reasons": reasons,
                            },
                        }
                    )
            try:
                result = self._file_issues(
                    items,
                    (kwargs.get("tracker") or STEWARD_TRACKER).strip(),
                    STEWARD_LABEL,
                    "rar-steward",
                    kwargs.get("confirm", False),
                    kwargs.get("existing_issues_path"),
                )
            except SourceError as exc:
                return self._env(
                    action,
                    "error",
                    source=source,
                    error=_scrub(str(exc)),
                )
            return self._env(
                action,
                "planned",
                source=source,
                scope=scope,
                scanned=len(agents),
                candidates=len(items),
                result=result,
            )

        if action == "duplicates":
            clusters = self._clusters(agents)
            return self._env(
                action,
                "success",
                source=source,
                scanned=len(agents),
                clusters=len(clusters),
                agents_in_clusters=sum(
                    cluster["size"] for cluster in clusters
                ),
                merge_candidates=clusters[:limit],
                ruling=(
                    "Review only: preserve every record and lineage until a "
                    "human-approved consolidation is accepted."
                ),
            )

        if action == "junk":
            findings = self._junk(agents)
            by_reason = {}
            for finding in findings:
                for reason in finding["reasons"]:
                    key = reason.split(" (")[0]
                    by_reason[key] = by_reason.get(key, 0) + 1
            return self._env(
                action,
                "success",
                source=source,
                scanned=len(agents),
                flagged=len(findings),
                by_reason=by_reason,
                candidates=findings[:limit],
                ruling=(
                    "Review only: annotate or improve weak records; never "
                    "erase data exhaust automatically."
                ),
            )

        clusters = self._clusters(agents)
        findings = self._junk(agents)
        total = len(agents)
        carded = sum(
            1
            for agent in agents
            if agent.get("has_card") or agent.get("manifest")
        )
        placeholders = sum(
            1
            for agent in agents
            if _PLACEHOLDER.search(agent.get("name", ""))
        )
        in_clusters = sum(cluster["size"] for cluster in clusters)
        publishers = {}
        for agent in agents:
            publisher = agent.get("publisher", "?")
            publishers[publisher] = publishers.get(publisher, 0) + 1
        card_coverage = carded / total
        duplicate_pressure = in_clusters / total
        placeholder_rate = placeholders / total
        score = round(
            100
            * (
                0.45 * card_coverage
                + 0.35 * (1 - duplicate_pressure)
                + 0.20 * (1 - placeholder_rate)
            )
        )
        grade = (
            "A"
            if score >= 85
            else "B"
            if score >= 70
            else "C"
            if score >= 55
            else "D"
        )
        return self._env(
            action,
            "success",
            source=source,
            surveyed_at=_now(),
            total_agents=total,
            by_publisher=dict(
                sorted(publishers.items(), key=lambda item: -item[1])
            ),
            card_coverage=f"{round(card_coverage * 100)}%",
            merge_clusters=len(clusters),
            agents_in_merge_clusters=in_clusters,
            junk_candidates=len(findings),
            placeholder_agents=placeholders,
            health_score=score,
            grade=grade,
            top_merge_clusters=[
                {
                    "base": cluster["recommended_base"],
                    "size": cluster["size"],
                    "members": [
                        member["rar_name"]
                        for member in cluster["members"]
                    ],
                }
                for cluster in clusters[:8]
            ],
            guidance=(
                "Improve cards and metadata, then review consolidation "
                "suggestions. The steward retains records and emits plans only."
            ),
        )


if __name__ == "__main__":
    print(RarStewardAgent().perform(action="help"))
