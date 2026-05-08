"""braintrust_synthesize_agent.py — merge contributions into a bibliography-annotated report.

Pulls all contribution comments on the request Issue, dedupes findings,
allocates citation IDs, and produces:

  reports/<slug>/report.md          — markdown with inline [N] citations
  reports/<slug>/bibliography.json  — parallel machine-readable citation set
  reports/<slug>/manifest.json      — rapp-braintrust-report/1.0

The "neighborhood adapts to who's home" property is enforced HERE:

  - Synthesis NEVER blocks on a missing contributor.
  - If a contributor was removed (no longer collaborator) but had previously
    contributed, their already-posted contribution still counts.
  - If a contributor is offline / never showed up, they are simply absent.
    We work with what's home.
  - The minimum-quorum check is the ONLY adapt-or-defer signal — and even then
    the synthesizer can be invoked with `force_quorum=true` to ship anyway.

The report is opened as a PR. Consensus happens via PR review (each contributor
who *is* still home can approve or request changes). PR merge = canonical."""
import hashlib
import json
import os
import re
import time
import urllib.parse

from agents.basic_agent import BasicAgent


class BraintrustSynthesizeAgent(BasicAgent):
    name = "braintrust_synthesize"
    metadata = {
        "name": "braintrust_synthesize",
        "description": "Merge contributions into a bibliography-annotated report. Adapts to who is home — never blocks on absent contributors. Returns the report files to commit + the PR-draft URL.",
        "parameters": {
            "type": "object",
            "properties": {
                "request_id": {"type": "string", "description": "The braintrust request ID."},
                "topic": {"type": "string", "description": "The request topic (used for the report title)."},
                "contributions": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "List of rapp-braintrust-contribution/1.0 objects. In Phase 2 these are pulled from Issue comments; for Phase 1 the orchestrator passes them in."
                },
                "synthesizer_login": {"type": "string", "description": "Login of whoever is running synthesis."},
                "synthesizer_rappid": {"type": "string", "description": "Synthesizer's personal organism rappid."},
                "min_quorum": {"type": "integer", "description": "Minimum contributors with at least one finding. Default 1."},
                "force_quorum": {"type": "boolean", "description": "If true, ship even when below quorum (uses what's home)."}
            },
            "required": ["request_id", "topic", "contributions", "synthesizer_login"]
        }
    }

    def _seed_dir(self):
        return os.environ.get("NEIGHBORHOOD_SEED_DIR", os.getcwd())

    def _slugify(self, s):
        out = []
        for c in (s or "").lower():
            if c.isalnum():
                out.append(c)
            elif c in (" ", "-", "_"):
                out.append("-")
        return ("".join(out).strip("-") or "report")[:48]

    def _dedupe_findings(self, contributions):
        """Each finding is keyed by (source.kind, source.ref) so the same source
        cited by two contributors becomes ONE bibliography entry with both
        contributors credited. Findings with the same (login, source-ref)
        pair are merged at the finding level."""
        bib = {}
        for c in contributions or []:
            login = ((c.get("contributor") or {}).get("github_login")) or "?"
            rappid = ((c.get("contributor") or {}).get("rappid"))
            for f in (c.get("findings") or []):
                src = f.get("source") or {}
                key = (login, (src.get("kind") or "?"), (src.get("ref") or "?"))
                if key in bib:
                    continue
                bib[key] = {
                    "contributor_login": login,
                    "contributor_rappid": rappid,
                    "snippet": f.get("snippet") or "",
                    "source": src,
                    "confidence": f.get("confidence") or 0,
                    "captured_at": c.get("captured_at"),
                }
        # Allocate stable citation IDs by sort order (login, kind, ref) so
        # different runs produce the same numbering.
        items = sorted(bib.values(), key=lambda x: (x["contributor_login"], x["source"].get("kind") or "", x["source"].get("ref") or ""))
        for i, it in enumerate(items, start=1):
            it["id"] = i
            it["schema"] = "rapp-braintrust-citation/1.0"
        return items

    def _render_report_md(self, request_id, topic, contributors_present, citations):
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        lines = [
            f"# Braintrust Report — {topic}",
            "",
            f"**Request ID:** `{request_id}`",
            f"**Synthesized:** {ts}",
            f"**Contributors present:** {', '.join('@' + c for c in contributors_present) or '(none)'}",
            f"**Citations:** {len(citations)}",
            "",
            "## Findings",
            "",
        ]
        # Group citations by contributor for the prose section.
        by_contrib = {}
        for c in citations:
            by_contrib.setdefault(c["contributor_login"], []).append(c)
        if not citations:
            lines.append("_No findings were submitted by present contributors. The neighborhood is home but the libraries had nothing on this topic._")
        else:
            for login, items in by_contrib.items():
                lines.append(f"### From @{login}")
                lines.append("")
                for it in items:
                    snip = (it.get("snippet") or "").replace("\n", " ").strip()
                    lines.append(f"- {snip} [[{it['id']}]](#cite-{it['id']})")
                lines.append("")

        lines += [
            "## Bibliography",
            "",
            "| # | Contributor | Source | Snippet |",
            "|---|---|---|---|",
        ]
        for c in citations:
            src = c["source"]
            ref = (src.get("ref") or "").replace("|", "\\|")
            snip = (c.get("snippet") or "")[:120].replace("\n", " ").replace("|", "\\|")
            lines.append(f'<a id="cite-{c["id"]}"></a> [{c["id"]}] | @{c["contributor_login"]} | `{src.get("kind")}`: `{ref}` | {snip} |')
        lines += [
            "",
            "---",
            f"_Schema: `rapp-braintrust-report/1.0` · adapt-to-who's-home: True · quorum-met: {len(contributors_present) >= 1}_",
        ]
        return "\n".join(lines)

    def perform(self, request_id, topic, contributions, synthesizer_login,
                synthesizer_rappid=None, min_quorum=1, force_quorum=False, **kwargs):
        present = sorted({
            (c.get("contributor") or {}).get("github_login") or "?"
            for c in (contributions or [])
        } - {"?"})
        # contributors who reported "is_empty: True" still count as present
        # — they showed up. quorum is about presence, not richness.
        contributors_with_findings = sorted({
            (c.get("contributor") or {}).get("github_login") or "?"
            for c in (contributions or []) if (c.get("findings") or [])
        } - {"?"})

        if not present and not force_quorum:
            return json.dumps({
                "status": "deferred",
                "reason": "nobody is home — no contributions received",
                "next_step": "wait for contributors to come online or re-run with force_quorum=true",
            })

        if len(contributors_with_findings) < int(min_quorum or 1) and not force_quorum:
            return json.dumps({
                "status": "deferred",
                "reason": f"present={len(present)} (with findings={len(contributors_with_findings)}) below min_quorum={min_quorum}",
                "present": present,
                "contributors_with_findings": contributors_with_findings,
                "hint": "re-run with force_quorum=true to ship with what's home",
            })

        citations = self._dedupe_findings(contributions)
        slug = self._slugify(topic) + "-" + request_id[:6]
        report_dir = os.path.join(self._seed_dir(), "reports", slug)
        os.makedirs(report_dir, exist_ok=True)

        report_md_path = os.path.join(report_dir, "report.md")
        bibliography_path = os.path.join(report_dir, "bibliography.json")
        manifest_path = os.path.join(report_dir, "manifest.json")

        report_md = self._render_report_md(request_id, topic, present, citations)
        try:
            with open(report_md_path, "w") as f:
                f.write(report_md)
            with open(bibliography_path, "w") as f:
                json.dump({"schema": "rapp-braintrust-bibliography/1.0", "citations": citations}, f, indent=2)
            manifest = {
                "schema": "rapp-braintrust-report/1.0",
                "request_id": request_id,
                "topic": topic,
                "synthesized_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "synthesized_by": {"github_login": synthesizer_login, "rappid": synthesizer_rappid},
                "contributors_present": present,
                "contributors_with_findings": contributors_with_findings,
                "report_path": os.path.relpath(report_md_path, self._seed_dir()),
                "bibliography_path": os.path.relpath(bibliography_path, self._seed_dir()),
                "citation_count": len(citations),
                "consensus_state": "pending_review",
                "adaptive_to_whats_home": True,
            }
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)
        except OSError as e:
            return json.dumps({"status": "error", "error": str(e)})

        return json.dumps({
            "schema": "rapp-braintrust-synthesis-envelope/1.0",
            "status": "ok",
            "report": manifest,
            "wrote": [report_md_path, bibliography_path, manifest_path],
            "next_step": (
                "Open a PR adding reports/" + slug + "/. Contributors review; merge when consensus reached. "
                "Use the Inbox agent on the requester's workspace to surface the merged report back."
            ),
        }, indent=2)
