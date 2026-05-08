# Decision 0001 — Public gate / private workflow split

**Date:** 2026-05-08
**Status:** Adopted
**Decided by:** kody-w (founder)

## Decision

The neighborhood is split across two GitHub repos:

- `kody-w/microsoft-se-team-neighborhood` — public gate (identity, card, join path)
- `kody-w/microsoft-se-team-neighborhood-private` — private workflow (this repo)

Both share the same `neighborhood_rappid`. They are two faces of one neighborhood.

## Why

Bill (the prospective member who motivated this design) does not want the SE Team's workflow exposed publicly. We need a public surface so people know the neighborhood exists and can request access — but the actual roster, agents, twin chat, and decisions need to be visible only to authenticated members.

The `private_companion` block in `rappid.json` (existing schema) already anticipated this pattern. We're upgrading it from a single-organism convention to a neighborhood-scope primitive.

## How to apply

- Public-safe content goes in the gate repo: identity, purpose, lineage, public-facing agents.
- Member-only content goes in this repo: members.json, federation agents, decisions, runbooks.
- Trust anchor is GitHub collaborator status on this repo. No separate auth.

## Alternatives rejected

- **Branch split (main private + gh-pages public):** doesn't actually gate — anyone who can read main can read gh-pages history, and collaborator scope is repo-level not branch-level.
- **Mono-repo with /public/ and /private/ folders:** GitHub doesn't gate folders.
- **GitHub Org with Teams:** correct at scale, overkill for the founder + first-member test rig. Both repos transfer cleanly into an org later when the member count justifies the overhead.

## Consequences

- Two repos to maintain in sync (the `neighborhood_rappid` and the lineage label must match).
- The gate has to advertise the private companion URL so brainstems can find it. (It does — see `private_companion` block in the gate's `neighborhood.json`.)
- When transferring to an org later, both repos go together; the `gate_repo` and `private_companion` cross-references need updating.
