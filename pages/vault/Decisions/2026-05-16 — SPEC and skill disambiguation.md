---
title: 2026-05-16 — SPEC and skill disambiguation (3 layers, 2 filenames)
status: published
section: Decisions
hook: Five files share two filenames (SPEC.md ×2, skill.md ×3) but cover three different layers of the platform. Resolved via scope markers + a specs/README.md directory map rather than renames — preserves git history and existing links.
---

# 2026-05-16 — SPEC and skill disambiguation (3 layers, 2 filenames)

> **Historical/superseded documentation decision.** Preserve the naming
> decision below, but its former authority order is no longer current.
> Canonicalization, identity, frames, wire, eggs, registry, trust, and protocol
> evolution follow RAPP/1 rev-5 through
> [`RAPP1_AUTHORITY.json`](../../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../../RAPP1_STATUS.md).

> **Hook.** Five files share two filenames (SPEC.md ×2, skill.md ×3) but cover three different layers of the platform. Resolved via scope markers + a `specs/README.md` directory map rather than renames — preserves git history and existing links.

## The collision

Surfaced during the post-Marie-Kondo audit:

| File | Lines | What it actually is |
|---|---:|---|
| `pages/docs/SPEC.md` | 1106 | **v1 agent contract** — single-file agent format, sacred tenets, frozen v1 |
| `specs/SPEC.md` | 420 | **Network protocol spec** — federation, doors, gates, rappid addressing |
| `pages/docs/skill.md` | 195 | **Canonical agent skill manifest** (rendered docs) |
| `specs/skill.md` | 323 | **Network-participation runbook** — 6 steps to become a 1st-class network citizen |
| `skill.md` (root) | 469 | **Installer skill manifest** — for Claude / Copilot CLI to install brainstem |

Three layers of the platform — installer, agent, network — and two filenames historically reused at each layer with different scope. Looked like duplicates from the outside, were actually distinct docs.

## Why not rename or consolidate

Three options were on the table:

1. **Rename** — `specs/SPEC.md` → `specs/NETWORK_PROTOCOL.md`, etc. Breaks every existing link, requires updating inbound references in CLAUDE.md, ECOSYSTEM_MAP.md, two pages/docs/* files, examples/, etc.
2. **Consolidate** — merge into one canonical `pages/docs/SPEC.md`. Loses scope-specific content; one document trying to cover installer + agent + network would be incoherent.
3. **Add scope markers** — leave the filenames alone, add a clarifying header to each file declaring its scope.

Option 3 won. Three reasons:

- **Preserves git history** — no `git mv`, no rename-detection ambiguity.
- **Preserves external links** — anyone bookmarking `pages/docs/SPEC.md` keeps working.
- **The fix is *informational*, not *structural*.** The files weren't broken; only their relationship was unclear. Headers fix the relationship.

## What was added

Each of the 5 files now starts with a scope blockquote (or HTML comment for the YAML-frontmatter ones) declaring:

- What layer it covers
- What it is *not* — with a link to the file that covers the other layer
- A link to `specs/README.md` for the spec-directory map

Plus a new `specs/README.md` with the directory map (the table above, plus rationale for why two directories).

Plus two new cards on `pages/kernel.html` so visitors discover the Network Protocol Spec and the network-citizen skill alongside the agent SPEC.

## The naming convention going forward

When a doc references "the SPEC," use the qualifier:

- *"v1 SPEC"* or *"agent SPEC"* → `pages/docs/SPEC.md`
- *"Network SPEC"* or *"Protocol SPEC"* → `specs/SPEC.md`

When a doc references "the skill," use the scope:

- *"installer skill"* → `skill.md` at root
- *"canonical agent skill"* → `pages/docs/skill.md`
- *"network runbook"* → `specs/skill.md`

## See also

- [[The skill.md Pattern]] — the founding decision behind why skill.md exists at all
- [[2026-05-16 — Kernel-Distro Split]] — the larger context for the audit
- [[2026-05-16 — Marie Kondo Audit]] — the policy that surfaced the duplication question
- [`specs/README.md`](../../../specs/README.md) — the directory map
