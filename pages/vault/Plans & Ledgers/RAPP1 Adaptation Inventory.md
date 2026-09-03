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
| GRAIL-001 | Installer/Grail | Immutable pin plus full historical source and plan adapters | Keep apply paths bound to the exact pin, reviewed injection, owner approval, and fresh section-13 evidence | None for read-only |
| WORKER-001 | Worker, Doorman, browser tether | Full source, capabilities default-off, exact host allowlist | Add versioned binding receipts and fully local positive browser fixtures | Registry for trust |
| BROWSER-001 | Restored browser pages | Full historical UI with unsafe edges disabled | Add reviewed adapters only after exact validators exist | Registry, root, invite |
| PAGES-001 | GitHub Pages | Curated public history and status | Keep publication inventory, links, snapshots, and source records exact | None |
| METRO-001 | Metropolis | Full local explorer and collector source | Optional reviewed online observation binding with freshness labels | Registry for acceptance |
| CAVE-001 | Cave catalog and steward | Full read-only catalog algorithms | Inject identity/frame/egg/registry validators without erasing rejected records | Registry, root, invite |
| ESTATE-001 | Estate recovery/bootstrap | Full write algorithms behind refusal gates | Verify owner tenure, target approval, and adoption receipts before mutation | Registry, root |
| NETWORK-001 | Network/audit tools | Offline/read-only by default | Add optional authenticated acceptance pass while retaining raw observations | Registry, root |
| SWARM-001 | Tier 2, simulations, host tools | Full source with inspect/plan/sandbox defaults | Keep source receipts, local replay, exact loopback chat, and effect gates synchronized | Registry for release |
| GENERATED-001 | Generated manifests and snapshots | Mixed generator contracts | Standardize pinned inputs, check mode, output hash, and provenance | None |
| HISTORY-001 | Source/archive/test corpus | Preserved evidence plus exact inert copies of removed runtimes | Keep every source receipt and port useful behavior into safe replay tests | None |
| TEST-001 | Canonical gate | Structural, preservation, mutation, and safety coverage | Maintain source-retention and pre-effect authorization tests as adapters evolve | Owner fixtures remain external |
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
That ledger currently verifies 125 restoration records: 50 page or partial
artifacts, 59 executable/code artifacts, 8 structured documents or templates,
and 8 exact non-executable copies of removed runtime sources.

## Executable adaptation examples

### Worker and browser harness

The Worker keeps the historical route implementation while every capability is
false by default. Activation requires both an explicit runtime flag and a
reviewed binding. Copilot forwarding is limited to four exact historical hosts;
suffix confusion, userinfo, alternate schemes, ports, IPs, Unicode, punycode,
encoded hosts, and unapproved redirects fail before credentials or transport.
Doorman and tether tests use synthetic credentials, allowlisted origins, and
dependency-supplied browsers; they do not auto-install or discover tokens.

### Distribution and Grail adapters

Root, docs, community, installer, deployment, signing, LAN, and Brainstem
launcher sources are restored at their stable paths. Default invocations emit
local provenance plans with no effects. The two complete ARM templates are
retained byte-for-byte as inert data. Apply paths require the exact immutable
Grail pin, reviewed dependency injection, target-specific owner approval, and
authenticated fresh section-13 evidence; unavailable evidence refuses before
transport or mutation.

### Cave

The RAR steward again performs health, duplicate, junk, agent, and issue-plan
analysis. The Super RAR builder again discovers and renders catalog entries.
Both default to local read-only modes. Moving refs, missing hashes,
installation, streaming, execution, publication, and acceptance are refused.
The full Cave agent and public beacon observation are retained while active
clone, copy, bootstrap, streaming, and acceptance edges remain disabled.

### Estate and network tools

Private-estate bootstrap, estate reconstruction, network discovery, ecosystem
audit, product contracts, and holocard generation retain their full
algorithms. Their default modes inspect, compare, or plan. Mutation requires an
exact target-specific approval and authenticated fresh registry evidence,
which this repository cannot currently supply.

### Swarm and simulations

Tier 2 provisioning, Azure function, Twin egg, local simulation, front-door,
test-server, Cave-host, and tutorial hatcher implementations are restored with
exact source provenance. Defaults inspect, plan, or replay only in memory or
bounded local fixtures. RAPP chat routes solely through
`http://127.0.0.1:7073/chat`; deployment, packaging, extraction, process,
filesystem, model, credential, and repository effects stop before their
executors unless every receipt and owner-evidence gate passes.

Eight source files removed from active T2T, workspace, Swarm-server, chat,
lifecycle, neighborhood-membership, and reserved-upgrade paths are retained
byte-for-byte under `historical/source-archive/`. Their original runtime paths
remain absent; the archive uses non-executable `.txt` files, is excluded from
GitHub Pages, and is cross-linked from the source ledger.

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
