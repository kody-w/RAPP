"""braintrust_cite_agent.py — verify citations in a synthesized report.

Reads reports/<slug>/manifest.json + bibliography.json and:
  1. Reports who contributed and how many citations each holds
  2. Optionally verifies each source still exists / is reachable (when running
     in the contributor's environment that originally captured it)
  3. Returns a citation-graph view useful for cross-report navigation"""
import json
import os

from agents.basic_agent import BasicAgent


class BraintrustCiteAgent(BasicAgent):
    name = "braintrust_cite"
    metadata = {
        "name": "braintrust_cite",
        "description": "Inspect / verify citations in a synthesized braintrust report. Returns citation distribution, contributor counts, and (optionally) source-reachability checks.",
        "parameters": {
            "type": "object",
            "properties": {
                "report_slug": {"type": "string", "description": "The slug under reports/ (e.g. 'best-practices-x-abc123')."},
                "verify_local_sources": {"type": "boolean", "description": "If true, attempt to verify each `files`/`memory` source still exists on disk (only meaningful in the contributor's own environment)."}
            },
            "required": ["report_slug"]
        }
    }

    def _seed_dir(self):
        return os.environ.get("NEIGHBORHOOD_SEED_DIR", os.getcwd())

    def _load_json(self, path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, ValueError, OSError):
            return None

    def perform(self, report_slug, verify_local_sources=False, **kwargs):
        report_dir = os.path.join(self._seed_dir(), "reports", report_slug)
        manifest = self._load_json(os.path.join(report_dir, "manifest.json"))
        bib = self._load_json(os.path.join(report_dir, "bibliography.json"))
        if not manifest or not bib:
            return json.dumps({
                "schema": "rapp-braintrust-cite-report/1.0",
                "status": "not_found",
                "report_dir": report_dir,
            })

        citations = bib.get("citations") or []
        per_contributor = {}
        per_kind = {}
        for c in citations:
            login = c.get("contributor_login") or "?"
            per_contributor[login] = per_contributor.get(login, 0) + 1
            kind = (c.get("source") or {}).get("kind") or "?"
            per_kind[kind] = per_kind.get(kind, 0) + 1

        verified = None
        if verify_local_sources:
            verified = {"reachable": 0, "missing": 0, "skipped": 0, "details": []}
            for c in citations:
                src = c.get("source") or {}
                kind = src.get("kind")
                ref = src.get("ref") or ""
                if kind in ("memory", "files"):
                    # ref like "/path/to/file.json#0" or "/path/to/notes/foo.md"
                    path = ref.split("#")[0]
                    if os.path.exists(path):
                        verified["reachable"] += 1
                    else:
                        verified["missing"] += 1
                        verified["details"].append({"id": c.get("id"), "ref": ref, "issue": "missing"})
                else:
                    verified["skipped"] += 1

        return json.dumps({
            "schema": "rapp-braintrust-cite-report/1.0",
            "report_slug": report_slug,
            "topic": manifest.get("topic"),
            "citation_count": len(citations),
            "per_contributor": per_contributor,
            "per_kind": per_kind,
            "consensus_state": manifest.get("consensus_state"),
            "contributors_present": manifest.get("contributors_present") or [],
            "verified_local_sources": verified,
        }, indent=2)
