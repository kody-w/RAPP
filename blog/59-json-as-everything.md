# Why a JSON file is a marketplace AND a deployment unit AND a portable archive

The `rapp-swarm/1.0` bundle format does three jobs at once:

1. **Marketplace listing.** Each registry's `registry.json` enumerates available swarms and agents.
2. **Deployment unit.** A `<swarm-name>.swarm.json` file is the input to `POST /api/swarm/deploy`, which installs the swarm on any compatible runtime.
3. **Portable archive.** The same JSON file, unchanged, can be checked into Git, emailed, dropped on a thumb drive, or stored in any object store as a long-term archive of the swarm's complete state.

One file format. Three product roles. Every other system in this space tries to use three different formats — a registry catalog (one schema), a deploy bundle (different schema), an archive format (yet another). We collapsed them.

**Why one file works for all three:**

A JSON document with a schema version, a name, and a body of self-contained data IS a marketplace listing if you list it; IS a deploy artifact if you POST it to a deploy endpoint; IS an archive if you persist it anywhere durable. The format doesn't care about its audience. Different consumers read what they need.

```
{
  "schema": "rapp-swarm/1.0",
  "name": "sales-swarm-9",
  "purpose": "B2B sales acceleration agents",
  "created_at": "2026-04-19T...",
  "created_by": "wildfeuer05",
  "soul": "<soul>...</soul>",
  "agent_count": 9,
  "agents": [
    {
      "filename": "...",
      "name": "AccountIntelligence",
      "description": "...",
      "source": "import json\nfrom agents.basic_agent import BasicAgent\n...",
      "sha256": "..."
    },
    ...
  ]
}
```

The marketplace consumer reads `name`, `purpose`, `agent_count`, `created_by`. Skips `agents[].source` (too heavy). Renders a card. Done.

The deploy consumer reads everything. Writes each agent's `source` to disk. Writes the manifest. Done.

The archive consumer treats the whole document as opaque. Stores it. Possibly verifies `sha256` integrity later. Done.

Three different jobs, one format, no transformation step between them.

**The benefits:**

**No conversion errors.** When the registry catalog and the deploy bundle are different formats, you have a transformation step (catalog → deploy). Transformations have bugs. They lose information. They drift between versions. With one format, no transformation — the document you fetched from the registry is the same document the deploy endpoint accepts.

**Round-trip semantics are obvious.** Export a swarm → bundle. Install bundle → swarm. Re-export → bundle. The bundles before and after are byte-identical (modulo timestamps). You can verify reversibility by diffing.

**Version migration is one schema, not three.** When we ship `rapp-swarm/1.1`, every consumer (marketplace, deploy, archive) handles it the same way. We don't have to coordinate "the registry now serves 1.1, but the deploy endpoint still expects 1.0, and archives written in 1.0 should still install on 1.1 endpoints."

**The discipline this requires:**

You have to design the schema for all three roles up front. Adding a field that a marketplace would need but a deploy endpoint would ignore? Fine — extra fields are harmless. Adding a field that's required for marketplace display but missing from older archives? Now you have a versioning problem.

The trick is to make REQUIRED fields the union of all consumers' minimums, and OPTIONAL fields the union of every consumer's nice-to-have. Required is small (schema, name, agents); optional is large (purpose, soul, created_by, _file paths, ratings, tags). Marketplace consumers ignore optional fields they don't render. Deploy consumers ignore optional fields they don't need. Archive consumers store everything.

**The pattern generalizes:**

Whenever you find yourself designing two formats for "the same conceptual thing in different contexts," ask whether you actually need two formats. Often you don't. The audiences are different but the data is the same; the audiences just consume different subsets.

Some examples beyond ours:

- **Containerfile / image / pulled-archive.** Docker built three formats; OCI eventually unified into one image spec that's all of "buildable definition," "runnable image," and "exportable tarball." Same data, different consumers.
- **OpenAPI spec / generated client / interactive playground.** All three from one document.
- **Markdown files / static site / RSS feed.** Hugo / Jekyll / 11ty render the same Markdown into all three outputs. The Markdown doesn't change.

**The anti-pattern:**

Designing the marketplace schema first, then the deploy schema as a "richer" superset, then the archive as some compressed projection of either. Three formats that look similar but aren't. Conversions everywhere. Drift over time. Eventually a fourth format because none of the existing three quite fit a new consumer.

**The lesson:**

When you have one logical thing serving multiple roles, give it ONE serialized form. Let consumers read what they need. The cost of having extra fields some consumers ignore is much lower than the cost of multiple schemas with subtle drift.

`rapp-swarm/1.0` is one JSON shape that registries enumerate, deploy endpoints accept, and humans archive. Three jobs, one file. We never have to write a converter.
