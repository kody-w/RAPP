# `docs/` — Governance and reference

Long-form, stable documents that aren't the catalog card (`README.md`)
or running code. The kind of file you read once to understand a
contract, not the kind you grep daily.

## What's here

| File | What |
|---|---|
| [`SPEC.md`](./SPEC.md) | The frozen v1 wire contract for the single-file agent format. The API |
| [`ROADMAP.md`](./ROADMAP.md) | Post-v1 directions that must honor the v1 contract |
| [`AGENTS.md`](./AGENTS.md) | Guidance to AI assistants editing this repo (Cursor, Codex, etc.) |
| [`VERSIONS.md`](./VERSIONS.md) | Brainstem release tag history and rollback discipline |
| [`skill.md`](./skill.md) | The canonical AI-readable skill manifest for RAPP |
| [`rapplication-sdk.md`](./rapplication-sdk.md) | SDK-shaped reference for building rapplications |

> Note: [`CONSTITUTION.md`](../../CONSTITUTION.md) is at repo root, not here — it's a peer of `README.md` because governance is part of the catalog card. See Article XVI.

## What belongs here

A file earns a place in `docs/` when **all** of these are true:

1. **It's reference, not narrative.** Stable contracts, frozen specs,
   versioned conventions. The kind of thing a contributor reads to
   *check* something, not to *understand why*.
2. **It outlives the current task.** If it's the why behind a
   decision, it belongs in `vault/` (see Article XXIII). If it's
   notes for the current PR, it doesn't belong in the repo at all.
3. **It's load-bearing.** A test or another doc references it. A
   user, contributor, or AI assistant looks for it by name.

## What does NOT belong here

- ❌ **Decision narratives** ("why we picked X over Y"). Those are
  vault notes — `pages/vault/Founding Decisions/`,
  `pages/vault/Architecture/`, etc. Capture the *why* there, where
  Obsidian wikilinks make the graph queryable.
- ❌ **Status updates, in-flight notes, work logs.** Those have no
  future reader. PR descriptions or vault `Plans & Ledgers/` if
  ongoing.
- ❌ **Per-tier deep dives.** `rapp_brainstem/CONSTITUTION.md` and
  `rapp_brainstem/README.md` exist because they document *that
  tier's* internals. New tier-specific docs go inside the tier
  directory, not here.
- ❌ **Tutorial-shaped or audience-shaped content.** Marketing or
  audience pages are `pages/<file>.html`. Tutorials are stubbed in
  the vault and grow into a published note when they earn it.

## Conventions

- **Filenames.** Top-level governance is `UPPERCASE.md`
  (`SPEC.md`, `ROADMAP.md`, `AGENTS.md`,
  `VERSIONS.md`). Reference / SDK material is `lowercase.md`
  (`skill.md`, `rapplication-sdk.md`). Two visual buckets at a
  glance.
- **Cross-links use relative paths.** From within `docs/`, link
  siblings as `[FOO](./FOO.md)`. From `README.md` at repo root, link
  in as `[FOO](./docs/FOO.md)`.
- **No subdirectories without justification.** A flat `docs/` keeps
  the index scannable. If `docs/` ever grows past ~15 files, the
  fix is probably to move some content to `vault/` (the why) or to a
  tier directory (the how) — not to add `docs/governance/` and
  `docs/reference/`.

## Scale rule

When you're about to add a doc here, ask:

1. *Is this a contract someone will check, or a story someone will
   read?* Contract → `docs/`. Story → `vault/`.
2. *Will this file be referenced by name by code, tests, or other
   docs?* Yes → `docs/` (load-bearing). No → reconsider whether it
   needs to ship.
3. *Is the audience a human contributor, or end-user prospects?*
   Contributor / AI assistant → `docs/`. Prospect → `pages/<file>.html`.

If all three answers point here, write it. Otherwise, route it to the
right surface.

## Related

- Repo-root residency rule: [`CONSTITUTION.md`](../../CONSTITUTION.md)
  Article XVI.
- Vault-versus-docs rule: [`CONSTITUTION.md`](../../CONSTITUTION.md)
  Article XXIII.
