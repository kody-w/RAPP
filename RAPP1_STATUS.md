# NOT YET FULLY RAPP/1 CONFORMANT

This repository has adopted a target-owned **structural authority pin** for
RAPP/1 rev-5. It has not completed the authenticated trust and migration work
required for a full conformance claim.

## Current authority

[`RAPP1_AUTHORITY.json`](./RAPP1_AUTHORITY.json) pins the exact `SPEC.md` bytes
from `kody-w/rapp-1` at commit
`6723c7add2aed36bb68992fc71a56b0a4bd5ad81`, SHA-256
`6d06daba65d7c045716f3d6e95db8401ab58e727820e4114466d847f62cae49b`,
wire tag `rapp/1`, revision `rev-5`.

The pin is deliberately **not** an authenticated registry under RAPP/1 §13.
It carries no owner signature, trust anchor, registry sequence, key succession,
or freshness proof.

## Audit coverage and limitation

The 2026-07-16 audit covered **640/640 inventory entries**. That number is
coverage, not a conformance pass count. The audit's named limitation is its
**shallow check**: every entry received an inventory/structural check, but not
every file received exhaustive semantic, cryptographic, runtime, or
cross-repository verification.

Maintainer evidence is retained in Copilot session
`9ac7ec28-fb92-4452-a8c9-477a2363685d`; no machine-local audit path is part of
this repository.

## Structural validation is not authenticated acceptance

The offline gate can verify:

- authority-record shape and exact pinned metadata;
- agreement with the staged provenance fixture;
- local hashes of the immutable grail files.

It cannot authenticate the estate owner or establish registry freshness.
Frames, eggs, signatures, re-anchors, and invites may pass structural checks
without being acceptable under RAPP/1 §§6–13. Authenticated acceptance requires
a verified §13 registry rooted in an out-of-band estate-owner anchor and
monotonic `registry_seq`.

## Owner-action blockers

Only the estate owner can close these dependencies:

1. **Signed monotonic registry and out-of-band anchor** — publish and sign the
   §13 registry, distribute the estate-owner rappid anchor independently, and
   establish sequence/freshness handling.
2. **Lawful root re-anchor** — issue the applicable owner-authorized §6.3/§13.3
   record with the required continuity, tombstone, or out-of-band recovery
   proof. A contributor must not invent the key or authorization.
3. **Signed replacement invite** — replace the legacy/invalid invite with a
   `rapp/1-egg` `invite` whose signature verifies under the estate-owner
   succession.
4. **External mirror correction** — update affected mirrors outside this target
   from their owners' sources of record, preserving exact bytes, hashes, and
   provenance.

No contributor or automation may fabricate signatures, keys, registry
authority, or a re-anchor to make these blockers appear closed.

## Immutable grail boundary

The files pinned by [`KERNEL_PIN.json`](./KERNEL_PIN.json) remain read-only and
byte-identical to `kody-w/rapp-installer@brainstem-v0.6.9`. RAPP/1 convergence
must happen in target-owned adapters, validators, migration tooling, and
retirement policy. Historical `rapp-frame/*` and `brainstem-egg/*` paths may
remain as dated evidence or implementation inputs, but they are not the current
RAPP/1 frame or egg authority.

Until all owner-action blockers and implementation migrations are complete,
this repository must continue to lead with **NOT YET FULLY RAPP/1 CONFORMANT**.
