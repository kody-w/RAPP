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

## Audit coverage and checker limitation

The convergence work used repeated literal file-by-file reviews. The counts
are dated evidence, not interchangeable snapshots:

- **Baseline (2026-07-16, `f71810d`): 640/640 tracked paths**, 5
  ZIP-compatible archives, 450 recursively counted archive members, and 2 JSON
  eggs.
- **Post-implementation review (`e1c2fbb`): 691/691 tracked paths**, the same
  5 archives, 450 recursive members, and 2 JSON eggs.
- **Integrated closure tree: 693/693 tracked paths** after removing the last
  live Cave installer agent. The canonical gate derives current inventory from
  `git ls-files`; it does not treat an older count as current.

Every tracked file in each snapshot was individually reviewed and classified,
with a contextual disposition per path in the corresponding audit ledger.

Semantic, runtime, and cryptographic depth was applied where relevant to each
artifact's role. This full audit is separate from the named checker:
`rapp_check.py` is a shallow checker and is insufficient by itself. Its output
must not be substituted for the full file/archive review and contextual ledger.

Complete review coverage and classification do not establish full RAPP/1
conformance or authenticated acceptance. The migration and owner-action
blockers below remain open.

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

Execution-ready candidate instructions for these owner decisions, plus the
dependent public-facade release gate, are in
[`RAPP1_OWNER_ACTIONS.md`](./RAPP1_OWNER_ACTIONS.md); the machine-readable
counterpart is [`RAPP1_OWNER_ACTIONS.json`](./RAPP1_OWNER_ACTIONS.json). Both
remain `candidate` / `owner-action-required` and are not a §13 registry.

## Target-owned launch containment

`rapp_brainstem/start.sh`, `start.ps1`, and `utils/boot.py` are explicit
HTTP-410 tombstones. They perform no dependency setup, imports, subprocess
launch, or network bind. The immutable `brainstem.py` bytes are invoked
directly only by credential-scrubbed, process-owned, OS-assigned-port test
fixtures as historical evidence; this is not a public launcher or product
surface.

The target-owned façade launcher binds only `127.0.0.1`. It imports no grail
module and defaults to the candidate `inference-refused` response until a
reviewed side-effect-free inference adapter is supplied through explicit
dependency injection.

## Active-path residual

Approved-place planting is fail-closed before repository creation. The retained
legacy planter is contained with HTTP 410 semantics, and no authenticated
RAPP/1 replacement currently emits a strict machine-readable plant result.
`.github/workflows/plant-approved-place.yml` may be re-enabled only after such a
producer returns an exact §6.1 rappid and URL as structured data rather than a
human log.

Historical seed backfill is also plan-only. Strict identity failures,
owner/slug source mismatches, and parent-pointer changes remain explicit owner
actions; the retired tool cannot mint or PUT a replacement identity.

## Immutable grail boundary

The files pinned by [`KERNEL_PIN.json`](./KERNEL_PIN.json) remain read-only and
byte-identical to `kody-w/rapp-installer@brainstem-v0.6.9`. RAPP/1 convergence
must happen in target-owned adapters, validators, migration tooling, and
retirement policy. Historical `rapp-frame/*` and `brainstem-egg/*` paths may
remain as dated evidence or implementation inputs, but they are not the current
RAPP/1 frame or egg authority.

Until all owner-action blockers and implementation migrations are complete,
this repository must continue to lead with **NOT YET FULLY RAPP/1 CONFORMANT**.
