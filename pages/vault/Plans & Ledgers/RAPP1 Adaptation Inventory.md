---
title: "RAPP1 Adaptation Inventory"
status: living
date: 2026-09-03
---

# RAPP/1 Adaptation Inventory

This report is the human reading companion to
[`RAPP1_ADAPTATION_INVENTORY.json`](../../../RAPP1_ADAPTATION_INVENTORY.json).
The machine record is a candidate migration inventory, not a RAPP/1 section 13
registry, trust anchor, signature, owner authorization, or full-conformance
claim.

The repository remains **not yet fully RAPP/1 conformant**. The structural
authority is [`RAPP1_AUTHORITY.json`](../../../RAPP1_AUTHORITY.json), current
limitations are in [`RAPP1_STATUS.md`](../../../RAPP1_STATUS.md), and owner-only
work is in [`RAPP1_OWNER_ACTIONS.json`](../../../RAPP1_OWNER_ACTIONS.json).
Canonicalization, identity, frames, wire, eggs, registry, trust, and protocol
evolution all remain subordinate to that rev-5 authority.

## Governing rule: adapt, do not kill

Historical source is data exhaust: it records ideas, interfaces, algorithms,
schemas, examples, observations, mistakes, and working product behavior. The
migration order is therefore:

1. Recover the fullest real artifact.
2. Record its commit, blob, SHA-256, and byte count.
3. Preserve its substantive body and useful local interactions.
4. Disable only the exact unsafe edge.
5. Prefer local fixtures, explicit capabilities, reviewed bindings, and
   owner-approved apply modes.
6. Point installer context to [`KERNEL_PIN.json`](../../../KERNEL_PIN.json) and
   `kody-w/rapp-installer@brainstem-v0.6.9`.
7. Record the remaining RAPP/1 gap and its acceptance test.

A blank refusal, hidden body, summary replacement, deleted algorithm, or
semantic tombstone is not a successful migration target.

## State is multidimensional

No catalog, page, hash, publication, GitHub account, token, or local check may
collapse these independent states:

| Dimension | Meaning |
|---|---|
| observed | The bytes or claim were encountered. |
| structurally valid | The local shape and deterministic checks pass. |
| cryptographically verified | The applicable signature and key binding pass. |
| fresh | Sequence, tenure, revocation, and freshness requirements pass. |
| accepted | Every required RAPP/1 and owner-policy gate passes. |

Most restored artifacts are useful **observations** or safe local replays. They
are not accepted protocol objects.

## Surface map

| ID | Surface | Current state | Next local adaptation | Owner dependency |
|---|---|---|---|---|
| GOV-001 | Authority, status, owner actions | Structurally pinned, owner-blocked | Keep status, source ledgers, and negative claims synchronized | Registry, root, invite |
| CORE-001 | Strict structural core | Active structural validation | Inject signature, tenure, registry, revocation, and freshness readers | Registry |
| IDENT-001 | RAPPIDs and doors | Historical mapping preserved | Resolve continuity only through authenticated evidence; never remint on read | Registry, root |
| FRAME-001 | Frames and streams | Structural/pre-acceptance | Verify JWS, tenure, monotonic sequence, forks, replay, and re-genesis | Registry |
| EGG-001 | Eggs and archives | Structural/pre-acceptance | Verify signers and variants, emit acceptance receipts, stage without execution | Registry, invite |
| TRUST-001 | Registry and key trust | Owner-blocked | Implement public-key verification and durable monotonic registry state | Registry |
| WIRE-001 | Exact `POST /chat` facade | Loopback candidate | Complete public-origin, adapter-receipt, replay, and concurrency gates | Registry |
| GRAIL-001 | Installer/Grail | Immutable pin plus historical UI | Resolve only through the pin; keep apply paths explicit and approved | None for read-only |
| WORKER-001 | Worker, Doorman, browser tether | Full source, capabilities default-off | Add binding receipts and fully local positive browser fixtures | Registry for trust |
| BROWSER-001 | Restored browser pages | Full historical UI with unsafe edges disabled | Add reviewed adapters only after exact validators exist | Registry, root, invite |
| PAGES-001 | GitHub Pages | Curated public history and status | Keep publication inventory, links, snapshots, and source records exact | None |
| METRO-001 | Metropolis | Full local explorer and collector source | Optional reviewed online observation binding with freshness labels | Registry for acceptance |
| CAVE-001 | Cave catalog and steward | Full read-only catalog algorithms | Inject identity/frame/egg/registry validators without erasing rejected records | Registry, root, invite |
| ESTATE-001 | Estate recovery/bootstrap | Full write algorithms behind refusal gates | Verify owner tenure, target approval, and adoption receipts before mutation | Registry, root |
| NETWORK-001 | Network/audit tools | Offline/read-only by default | Add optional authenticated acceptance pass while retaining raw observations | Registry, root |
| SWARM-001 | Tier 2, simulations, host tools | Several refusal shells remain | Restore algorithms into bounded loopback sandboxes and explicit deploy receipts | Registry for release |
| GENERATED-001 | Generated manifests and snapshots | Mixed generator contracts | Standardize pinned inputs, check mode, output hash, and provenance | None |
| HISTORY-001 | Source/archive/test corpus | Preserved evidence | Index every source and port useful behavior into safe replay tests | None |
| TEST-001 | Canonical gate | Structural and safety coverage | Replace tombstone assertions with preservation and unsafe-edge tests | Owner fixtures remain external |
| MIRROR-001 | External mirrors | Historical observations | Require immutable provenance and byte identity for any republication | Optional owner publication |

The exact paths, gap matrix, and acceptance tests are machine-readable in the
inventory.

## Restored browser contract

The seventeen restored specialty pages retain their original interfaces,
visuals, copy, examples, and local interactions. Their shared safety target is:

- no automatic external network request;
- no ambient credential discovery or persistence;
- no repository creation, mutation, planting, install, or deployment;
- no media, peer, worker, or redirect activation without a reviewed binding;
- no identity, membership, frame, egg, registry, or trust acceptance claim;
- installer controls resolve to immutable Grail evidence;
- exact source provenance remains machine-verifiable.

The source records are in
[`HISTORICAL_SOURCE_LEDGER.json`](../../../HISTORICAL_SOURCE_LEDGER.json).
That ledger currently verifies 66 restoration records: 50 page or partial
artifacts and 16 executable/code artifacts.

## Executable adaptation examples

### Worker and browser harness

The Worker keeps the historical route implementation while every capability is
false by default. Activation requires both an explicit runtime flag and a
reviewed binding. Doorman and tether tests use synthetic credentials,
allowlisted origins, and dependency-supplied browsers; they do not auto-install
or discover tokens.

### Cave

The RAR steward again performs health, duplicate, junk, agent, and issue-plan
analysis. The Super RAR builder again discovers and renders catalog entries.
Both default to local read-only modes. Moving refs, missing hashes,
installation, streaming, execution, publication, and acceptance are refused.
Historical installer observations remain present even when their executable
source is absent.

### Estate and network tools

Private-estate bootstrap, estate reconstruction, network discovery, ecosystem
audit, product contracts, and holocard generation retain their full
algorithms. Their default modes inspect, compare, or plan. Mutation requires an
exact target-specific approval and authenticated fresh registry evidence,
which this repository cannot currently supply.

### Metropolis

The directory again renders cards, filters, local federation, activity, and
the complete historical roster. It reads only checked-in snapshots. The
collector defaults to local snapshot validation, provides a non-mutating plan,
and refuses online/write requests before any side effect.

## Exact owner-only blockers

Only the estate owner can close these three dependencies:

1. **Signed monotonic registry and out-of-band anchor** - select the estate
   owner, key/SPKI, namespaces, sequence, legacy dispositions, and publish the
   authenticated section 13 registry with independently distributed anchor.
2. **Lawful root re-anchor** - select and authenticate the applicable
   continuity, tombstone, or recovery case under valid owner tenure.
3. **Signed replacement invite** - publish the conformant `rapp/1-egg` Commons
   invite with valid detached JWS and byte-identical approved copies.

No contributor, automation, test fixture, GitHub login, local hash, or status
file may manufacture these facts.

## Acceptance bar

The restoration is locally complete only when:

- all source commits, blobs, SHA-256 values, byte counts, and preservation
  checks pass;
- all seventeen specialty pages are substantive adapted artifacts, not
  tombstones;
- GitHub Pages publishes every required local asset and excludes runtime/test
  internals;
- browser replay makes no default external request and useful local controls
  work on desktop and mobile;
- the immutable Grail hashes remain exact;
- the full structural gate passes while still reporting the three owner
  blockers;
- live GitHub Pages URLs show the restored bodies without intrusive warning
  banners.

Passing these checks establishes a verified adaptation state. It does not by
itself establish authenticated RAPP/1 acceptance.
