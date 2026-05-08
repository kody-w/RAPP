# Project Braintrust (template)

A federated-research RAPP neighborhood. Drop a request in; every online contributor's brainstem queries THEIR own library; findings synthesize into a bibliography-annotated report with full consensus before merge.

This is the **fifth canonical seed** in `installer/neighborhood-seeds/`, demonstrating the **Project Braintrust pattern** — the pattern where a distributed neighborhood of librarians collaborates asynchronously without anyone having to be in the loop synchronously.

## The flow

```
                                    ┌─────────────────────────┐
   ┌──────────┐    1. drop request   │  Operator A             │
   │ Operator ├──────────────────────►  drops a request via    │
   │   A      │                       │  braintrust_request     │
   └──────────┘                       └────────────┬────────────┘
                                                   │
                              ┌────────────────────┴──────────────────────┐
                              │ 2. each online contributor's brainstem    │
                              │    sees the request via braintrust_listen │
                              ▼                    ▼                      ▼
                       ┌───────────┐        ┌───────────┐          ┌───────────┐
                       │ Contrib B │        │ Contrib C │          │ Contrib D │
                       │ runs      │        │ runs      │          │ runs      │
                       │ library_  │        │ library_  │          │ library_  │
                       │ query on  │        │ query on  │          │ query on  │
                       │ THEIR     │        │ THEIR     │          │ THEIR     │
                       │ library   │        │ library   │          │ library   │
                       └─────┬─────┘        └─────┬─────┘          └─────┬─────┘
                             │                    │                      │
                             │ 3. each posts findings as Issue comment   │
                             │    via braintrust_contribute              │
                             │                                           │
                             └─────────────────────┬─────────────────────┘
                                                   │
                                                   ▼
                                       ┌──────────────────────┐
                                       │ 4. coordinator runs  │
                                       │    braintrust_       │
                                       │    synthesize        │
                                       │                      │
                                       │ → bibliography-      │
                                       │   annotated report   │
                                       │   PR'd to main       │
                                       └──────────┬───────────┘
                                                  │
                                                  │ 5. consensus
                                                  │    via PR review
                                                  ▼
                                       ┌──────────────────────┐
                                       │ 6. merged report     │
                                       │    lands in reports/ │
                                       │    requester's       │
                                       │    inbox surfaces it │
                                       └──────────────────────┘
```

## The five agents (auto-mounted on every contributor's brainstem)

| Agent | Purpose |
|---|---|
| `braintrust_request_agent` | Open a research request — Issue with `braintrust-request` label + structured body |
| `library_query_agent` | Query the operator's local library (memory + files by default; operators override locally for vault / Notion / etc.) |
| `braintrust_contribute_agent` | Run the library query against an active request and post findings as a contribution comment |
| `braintrust_synthesize_agent` | Aggregate contributions into a bibliography-annotated report and open a PR |
| `braintrust_cite_agent` | Verify citations in a synthesized report against the source contributions |

## Schemas

- `rapp-neighborhood/1.0` (visibility: `private-workspace`, kind: `braintrust`)
- `rapp-braintrust-request/1.0` — the request artifact
- `rapp-braintrust-contribution/1.0` — a contributor's findings + provenance
- `rapp-braintrust-citation/1.0` — a single bibliography entry
- `rapp-braintrust-report/1.0` — the synthesized output

## How a request looks (`rapp-braintrust-request/1.0`)

```json
{
  "schema": "rapp-braintrust-request/1.0",
  "request_id": "<short-id>",
  "topic": "What are the best practices for X?",
  "scope": "Optional — narrow the search",
  "requester": {
    "github_login": "kody-w",
    "rappid": "<uuid>",
    "seed_url": null
  },
  "deadline": "2026-05-09T00:00:00Z",
  "min_quorum": 2,
  "library_kinds_requested": ["memory", "files", "vault"]
}
```

## How a contribution looks (`rapp-braintrust-contribution/1.0`)

```json
{
  "schema": "rapp-braintrust-contribution/1.0",
  "request_id": "<short-id>",
  "contributor": {
    "github_login": "rappter1",
    "rappid": "<uuid>",
    "seed_url": "<optional>"
  },
  "captured_at": "2026-05-08T01:00:00Z",
  "findings": [
    {
      "snippet": "...",
      "source": {
        "kind": "memory",
        "ref": ".brainstem_data/memory.json:fact-key",
        "captured_via": "library_query_agent"
      },
      "confidence": 0.85
    }
  ],
  "library_kinds_searched": ["memory", "files"]
}
```

## How a synthesized report looks (`rapp-braintrust-report/1.0`)

```json
{
  "schema": "rapp-braintrust-report/1.0",
  "request_id": "<short-id>",
  "synthesized_at": "<iso8601>",
  "synthesized_by": {"github_login": "kody-w", "rappid": "..."},
  "contributors": ["kody-w", "rappter1", "alex"],
  "report_path": "reports/<slug>/report.md",
  "bibliography_path": "reports/<slug>/bibliography.json",
  "citation_count": 12,
  "consensus_state": "pending_review" | "approved" | "merged"
}
```

The actual `report.md` has inline citations like `[1]` and `[2,3]` mapping to bibliography entries. The `bibliography.json` is parallel machine-readable, where each entry is a `rapp-braintrust-citation/1.0`.

## Why "library" matters here

The default `library_query_agent.py` is intentionally minimal — it queries `.brainstem_data/memory.json` + a configurable list of file paths. **Each operator is expected to drop a more sophisticated `library_query_agent.py` into their personal `agents/` directory** that knows about *their* knowledge stores: their Obsidian vault, their Notion workspace, their private GitHub repos, their RAG index, etc.

When a personal agent has the same name as a neighborhood-shared one, the personal one wins. This is how each librarian curates their own shelf without the neighborhood needing to know the implementation details — only the contract (`library_query_agent.perform(topic) → findings[]`).

## Privacy

Each contributor's library_index is `scope: personal` — never auto-shared. The contributor's agent decides what slips out per request based on the topic. The neighborhood only sees the `braintrust-contribution` artifacts, which are explicit contributions, not the full library.

## Self-healing

| Situation | Behavior |
|---|---|
| 0 contributors online | Request sits open until at least one comes back |
| 1 contributor online | They contribute alone; quorum check enforces minimum |
| Some contributors slow | Synthesis waits for deadline OR until quorum + opt-in additions |
| Synthesizer offline | Any other contributor with synthesize role can run it |
| Contributor disagrees with synthesis | PR review request changes — consensus through GitHub's existing review primitives |

## Use this template

1. Clone this directory, rename, plant as a private GitHub repo
2. Add your contributors as collaborators
3. Each contributor's brainstem subscribes via `brainstem join <repo-url>`; agents auto-mount
4. Drop a request via `braintrust_request_agent` — wait
5. Run `braintrust_synthesize_agent` after deadline / quorum reached
6. Review the PR; merge when consensus reached
7. Final report lives at `reports/<slug>/report.md`
