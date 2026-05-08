"""library_query_agent.py — default implementation. Operators override locally.

This is the contract every contributor's brainstem implements:

    library_query.perform(topic, scope=None) → {
        "library_kinds_searched": [...],
        "findings": [{"snippet", "source": {kind, ref}, "confidence", ...}, ...]
    }

The default implementation queries:
  1. The brainstem's public memory (.brainstem_data/memory.json)
  2. Any markdown files under known paths declared via LIBRARY_PATHS env var

OPERATORS SHOULD OVERRIDE THIS LOCALLY. Drop a smarter library_query_agent.py
into your personal agents/ directory that knows about your Obsidian vault, your
Notion workspace, your private GitHub repo, your RAG index, etc. The personal
agent shadows the neighborhood-shared one (auto-discovery picks the local copy).

Privacy: this agent decides what slips out per request. The full library is
NEVER auto-shared — only the matching findings are surfaced as contributions.
"""
import json
import os
import re

from agents.basic_agent import BasicAgent


class LibraryQueryAgent(BasicAgent):
    name = "library_query"
    metadata = {
        "name": "library_query",
        "description": "Query the operator's local library for content matching a topic. Returns findings tagged with provenance (source kind + ref). Operator-extensible — drop a custom version locally to query Obsidian / Notion / private repos / RAG / etc.",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Topic / question to search the library for."},
                "scope": {"type": "string", "description": "Optional narrowing scope."},
                "max_findings": {"type": "integer", "description": "Maximum findings to return (default 20)."}
            },
            "required": ["topic"]
        }
    }

    def _candidate_paths(self):
        # LIBRARY_PATHS is a colon-separated list the operator can set.
        env = os.environ.get("LIBRARY_PATHS", "")
        paths = [p for p in env.split(":") if p]
        # Always include the brainstem memory and any state/decisions in the seed.
        seed = os.environ.get("NEIGHBORHOOD_SEED_DIR", os.getcwd())
        candidates = paths[:]
        for p in (
            ".brainstem_data/memory.json",
            os.path.join(seed, ".brainstem_data", "memory.json"),
            os.path.join(seed, "state", "decisions"),
            os.path.join(seed, "state", "runbooks"),
        ):
            if p not in candidates:
                candidates.append(p)
        return candidates

    def _terms(self, topic):
        return [t for t in re.findall(r"[a-zA-Z0-9_]{3,}", (topic or "").lower())]

    def _scan_memory_json(self, path, terms):
        try:
            with open(path, "r") as f:
                doc = json.load(f)
        except (FileNotFoundError, ValueError, OSError):
            return []
        out = []
        # Memory format varies — be defensive.
        if isinstance(doc, dict):
            facts = doc.get("facts") or doc.get("memories") or []
        elif isinstance(doc, list):
            facts = doc
        else:
            facts = []
        for i, item in enumerate(facts):
            text = item.get("body") or item.get("text") or item.get("fact") or json.dumps(item)
            low = text.lower()
            score = sum(1 for t in terms if t in low)
            if score == 0:
                continue
            out.append({
                "snippet": text[:300],
                "source": {
                    "kind": "memory",
                    "ref": f"{path}#{i}",
                    "captured_via": "library_query_agent",
                },
                "confidence": min(1.0, 0.4 + 0.15 * score),
            })
        return out

    def _scan_markdown_dir(self, path, terms):
        if not os.path.isdir(path):
            return []
        out = []
        for entry in os.listdir(path):
            if not entry.endswith(".md"):
                continue
            full = os.path.join(path, entry)
            try:
                with open(full, "r") as f:
                    text = f.read()
            except OSError:
                continue
            low = text.lower()
            score = sum(low.count(t) for t in terms)
            if score == 0:
                continue
            # Pull the first paragraph that contains any term as a snippet.
            snippet = ""
            for para in text.split("\n\n"):
                if any(t in para.lower() for t in terms):
                    snippet = para[:400].strip()
                    break
            out.append({
                "snippet": snippet or text[:200].strip(),
                "source": {
                    "kind": "files",
                    "ref": full,
                    "captured_via": "library_query_agent",
                },
                "confidence": min(1.0, 0.5 + 0.05 * score),
            })
        return out

    def perform(self, topic, scope=None, max_findings=20, **kwargs):
        terms = self._terms(topic)
        if scope:
            terms.extend(self._terms(scope))
        findings = []
        kinds_searched = set()
        for cand in self._candidate_paths():
            if not os.path.exists(cand):
                continue
            if cand.endswith(".json"):
                hits = self._scan_memory_json(cand, terms)
                if hits:
                    findings.extend(hits)
                    kinds_searched.add("memory")
            elif os.path.isdir(cand):
                hits = self._scan_markdown_dir(cand, terms)
                if hits:
                    findings.extend(hits)
                    kinds_searched.add("files")

        findings.sort(key=lambda f: f.get("confidence") or 0, reverse=True)
        findings = findings[: int(max_findings or 20)]

        return json.dumps({
            "schema": "rapp-library-query-result/1.0",
            "topic": topic,
            "scope": scope,
            "library_kinds_searched": sorted(list(kinds_searched)),
            "findings_count": len(findings),
            "findings": findings,
            "note": (
                "Default library_query_agent. For a richer search, drop a custom "
                "library_query_agent.py into your personal agents/ directory."
            ),
        }, indent=2)
