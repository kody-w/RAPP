---
title: "RAPP Restoration and Adaptation Ledger"
status: living
date: 2026-09-03
---

# RAPP Restoration and Adaptation Ledger

This ledger turns the flagship restoration into an additive RAPP/1 migration.
The goal is not to return blindly to old behavior. It is to recover the full
learning corpus, preserve useful interfaces and algorithms, then adapt each
unsafe edge toward the current protocol and Grail.

Canonicalization, identity, frames, wire, eggs, registry, trust, and protocol
evolution follow RAPP/1 rev-5 through
[`RAPP1_AUTHORITY.json`](../../../RAPP1_AUTHORITY.json) and
[`RAPP1_STATUS.md`](../../../RAPP1_STATUS.md).

## Track A — Restore the actual artifacts

- [ ] Recover every HTML page replaced by a tombstone from its last substantive
      commit.
- [ ] Record source commit, blob, SHA-256, and byte count for every restored
      page.
- [ ] Remove intrusive status banners without removing original content
      callouts.
- [ ] Restore safe local interactions: navigation, tabs, search, rendering,
      previews, diagrams, themes, and deterministic demo state.
- [ ] Recover runtime, catalog, test, and tool source that was reduced to
      refusal shells.
- [ ] Keep known URLs and source paths stable.
- [ ] Add a machine-readable historical-content source ledger.

## Track B — Adapt instead of kill

- [ ] Replace automatic network calls with explicit reviewed bindings or local
      checked-in snapshots.
- [ ] Replace credential discovery with caller-supplied synthetic/test
      credentials and origin allowlists.
- [ ] Make mutation, repository creation, deployment, and publication
      explicit owner-approved modes; default to inspect, preview, or plan.
- [ ] Preserve full schemas and algorithms even when acceptance is disabled.
- [ ] Point installer context to `KERNEL_PIN.json` and
      `kody-w/rapp-installer@brainstem-v0.6.9`.
- [ ] Keep historical identifiers unchanged as evidence; never silently
      remint or rewrite them into apparent compliance.
- [ ] Separate `observed`, `verified`, and `accepted` states in every catalog,
      network, and audit result.

## Track C — Inventory the RAPP/1 migration

- [ ] Create `RAPP1_ADAPTATION_INVENTORY.json`.
- [ ] Cover every active, adapted, historical, immutable, generated, and
      owner-blocked surface.
- [ ] Record gaps by layer:
  - canonicalization and addressing;
  - rappid identity and succession;
  - frame envelope and verification;
  - synchronous `/chat` wire;
  - `rapp/1-egg` containers;
  - registry, signatures, trust, and freshness;
  - Grail installer pinning;
  - product-local side effects and safety.
- [ ] Name the exact local adaptation, owner action, and acceptance test for
      every gap.
- [ ] Link the inventory to `RAPP1_STATUS.md` without rewriting authenticated
      owner evidence.

## Track D — Add to RAPP while restoring

### 1. Historical Source Ledger

A machine-readable index from current path to recovered commit, blob,
SHA-256, byte count, restoration commit, and preserved interaction set.

**Acceptance:** every restored artifact is reproducible from Git history and
has no unproven provenance field.

### 2. Adaptation Contract

A small shared schema for default-off capabilities:

- `historical_source`;
- `default_mode`;
- `capabilities`;
- `reviewed_binding_required`;
- `side_effects`;
- `grail`;
- `rapp1_gaps`;
- `acceptance_tests`.

**Acceptance:** worker, tools, catalogs, and browser demos describe safety in
the same machine-verifiable shape instead of inventing one-off flags.

### 3. Grail Resolver

A read-only helper that resolves installer provenance from `KERNEL_PIN.json`
and emits the exact repository, tag, paths, and hashes for UI/docs/tooling.

**Acceptance:** no restored artifact points at a moving installer branch or
duplicates Grail constants manually.

### 4. Data Exhaust Explorer

Index historical pages, source versions, decision notes, removed tests, and
adapted code so humans and AI runtimes can search the full evolution corpus.

**Acceptance:** search results distinguish current authority, adapted
capability, historical evidence, and owner-blocked state without hiding any
artifact.

### 5. RAPP/1 Migration Receipts

Append-only records linking:

`historical source -> restored artifact -> adapted edge -> test -> remaining gap`

**Acceptance:** every migration can be audited without claiming authenticated
RAPP/1 acceptance.

### 6. Safe Historical Replay

Allow browser experiences to replay their real UI against deterministic local
fixtures, with network/mutation disabled unless a reviewed binding is supplied.

**Acceptance:** pages remain useful and interactive without tokens, external
services, repository writes, or fake success.

## Track E — Validation and release

- [ ] Add regression tests that fail if a substantive artifact becomes a
      tombstone, blank page, summary shell, or hidden body.
- [ ] Verify restored page anchors and interactions in a real browser.
- [ ] Verify no default path performs network, credential, mutation, install,
      or deployment side effects.
- [ ] Run the full RAPP/1 structural/pre-acceptance gate.
- [ ] Build GitHub Pages and verify known URLs publicly.
- [ ] Confirm the three authenticated owner blockers remain explicit.
- [ ] Append completion receipts to this ledger and the machine inventory.

## Owner-blocked, not deletion candidates

These remain open dependencies, not reasons to remove content:

1. Signed monotonic registry and out-of-band anchor.
2. Lawful root re-anchor.
3. Signed replacement invite.

Until those close, local adaptations may become safer and more exact, but they
must not claim authenticated RAPP/1 acceptance.

## Related

- [[Adapt, Don't Kill — preserve data exhaust]]
- [[Historical URLs remain visible and inert]]
- [[Documentation Roadmap]]
- [[Platform Backlog]]
- [`RAPP1_STATUS.md`](../../../RAPP1_STATUS.md)
- [`RAPP1_OWNER_ACTIONS.md`](../../../RAPP1_OWNER_ACTIONS.md)
