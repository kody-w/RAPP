# RAPP/1 owner and external action ledger

**Status: `candidate` · `owner-action-required` · not a RAPP/1 §13 registry**

This target-owned ledger makes the remaining decisions executable without
pretending they have been authorized. It is not a trust anchor, registry,
signature, re-anchor, tombstone, genesis entry, or external-repository change.
Nothing here permits authenticated acceptance. Unknown owner values remain
`null` in [`RAPP1_OWNER_ACTIONS.json`](./RAPP1_OWNER_ACTIONS.json).

Authority remains:

- [`RAPP1_AUTHORITY.json`](./RAPP1_AUTHORITY.json), the structural rev-5 pin;
- [`RAPP1_STATUS.md`](./RAPP1_STATUS.md), which remains **NOT YET FULLY
  RAPP/1 CONFORMANT**;
- Constitution Article LV; and
- `kody-w/rapp-1@6723c7add2aed36bb68992fc71a56b0a4bd5ad81`,
  `SPEC.md` SHA-256
  `6d06daba65d7c045716f3d6e95db8401ab58e727820e4114466d847f62cae49b`.

No contributor or automation may generate or sign an owner key, invent an
anchor or SPKI, approve a re-anchor, create registry authority, fabricate a
tombstone/genesis/succession event, or modify an external mirror.

## Candidate namespaces — unregistered

These are owner review inputs, not §13 entries:

- **Protocol pin:** `rapp/1` →
  `kody-w/rapp-1:SPEC.md` at the commit and SHA-256 above.
- **Egg variants (all six):** `organism`, `rapplication`, `session`, `invite`,
  `neighborhood`, `estate`.
- **Facade error codes (exactly six):** `malformed-request`,
  `unknown-session`, `idempotency-in-progress`,
  `session-in-progress`, `inference-refused`, `facade-storage-refused`.
  Zero error codes are currently registered; even `unknown-session` is only a
  specification example until the owner ratifies this actual candidate set.
- **Allowed error steps:** `"1"`, `"1a"`, `"2"`, `"3"`, `"4"`, `"5"`,
  `"6"`, or `null`.
- **Kind families:** `memory`, `body`, `swarm`.
- **Required re-genesis kinds:** `memory.re-genesis` → `memory`,
  `body.re-genesis` → `body`, and `swarm.re-genesis` → `swarm`.
- **Audit-baseline invalid legacy frame kinds requiring
  replacement/retirement if reintroduced:**
  `memory_added` (`installer/plant.sh:6308`), `conversation`
  (`installer/plant.sh:7624`), and `tool_call`
  (`installer/plant.sh:7733`). None satisfies current `label.label` grammar;
  none may be registered as written. Current main retains the legacy planter
  only behind HTTP 410 containment; that implementation state is not registry
  authority.
- **Other kinds:** undecided. Every emitted kind must be separately enumerated
  and assigned exactly one family; prefixes and wildcards grant no authority.

The owner registry also needs explicit SPKI binding, one-current-genesis,
append-only tombstone, time-scoped succession, root-compromise recovery,
no-rollback, and freshness policies. The exact policy requirements are in the
machine ledger.

## Evidence snapshots

### Current post-migration evidence

Recomputed after rebasing onto target `main` at
`4c2b999f8c890b76d057241d29ecda29e0239d79`:

| Subject | Current verified fact |
|---|---|
| Migration commits | `2cee074d755fe1ca1e81f5fb0c2331cbc47f1537`, `803cc76294b8a89273470d3167dde6f01df41e7d`, `591e7aec3b2183e0d48a1d6dfb6ebc59f177daea`, `4c2b999f8c890b76d057241d29ecda29e0239d79` |
| Status | `RAPP1_STATUS.md` SHA-256 `294d5f854c46e2c43ec039894a2b3779ec0060ebb69cf580c71e6114079187e4`; both owner-ledger links, dated audit counts, `Target-owned launch containment`, and `Active-path residual` are present |
| Current facade | `rapp_brainstem/rapp1_facade.py`; source commit intentionally null because these bytes and the ledger share a commit; blob `690226b2492d86cf089ed222cb7cefe38af8c1e5`; SHA-256 `4bd8e1c51290295c5dfd6dec73a5f12f3771ec674a5e856ab78edbfc61151a01`; tracked target-owned loopback-only post-migration pre-acceptance candidate |
| Facade support | launcher SHA-256 `4737fae8574e58177010653f8f83cf376b011add0c855e1c81a686ae4a74a9f9`; contract SHA-256 `0f970f3e43edc2f4c4c8803b5800115f7714bb3683bc5185569e122e77a98f77`; tests SHA-256 `92c46db51854fd988aea4dafacae184218a30f43a3dd77688b67c028901a8f54` |
| Current facade migration state | SQLite schema version 3; canonical semantic request-fingerprint version 3; bound legacy version 2 and unbound legacy version 1 remain migration inputs; production inference defaults to target-owned refusal and has no grail module dependency |
| Current pending errors | Exactly `malformed-request`, `unknown-session`, `idempotency-in-progress`, `session-in-progress`, `inference-refused`, `facade-storage-refused`; still candidate-unregistered |
| Recomputed unchanged evidence | `rappid.json`, Commons invite, local ecosystem JSON, kernel archive/manifest, `KERNEL_PIN.json`, cave identity, and installer packaging identity retain the hashes in the machine ledger |

### Audit baseline and unchanged trust evidence

The reports below describe target commit
`f71810db3259fea533b4112c1df300d4b0dc781c`. They remain baseline evidence,
not claims about post-migration active-path state. Local hash-bearing paths
listed as unchanged above were recomputed on the rebased tree.

| Subject | Verified fact |
|---|---|
| Historical root | `rappid:@kody-w/RAPP:0b635450c04249fbb4b1bdb571044dec` |
| Canonicalized provisional root | `rappid:@kody-w/rapp:0b635450c04249fbb4b1bdb571044dec` |
| Current stored root | `rappid:@kody-w/rapp:9a8f0a4b5a710e20f4d819a0f37d2a4c9f113b5e78fb3c29e70b54fff48a38f9` |
| Root migration | unsigned commit `19ff7d9ff483c0eef258a3b2031da1fd74570854`; current `rappid.json` SHA-256 `59dd3b53e2ed0c7594b3754425938b907600fdf5787b1cef912276aa9d3711b3` after correcting its migration note to tagged-hash truth; `attestation:null`; `upgrade` is a candidate case, not an inferred decision |
| Retired invite | `pages/tutorials/commons.egg`; 443 bytes; SHA-256 `2731c02f187701c1d07b3a7f5eed5e2073c203ffb4f6c08d00292894e3319a5d`; egg address `a03fa90289eaefcf1a6521cdc10ee17bc706a0bb353e688ad84135d684380fb7` |
| URL-fixed invite candidate | If the URL is the sole changed unsigned member: `d15305a25cbe6c9aab51a4ed2ab5514345772023a95d658b37fc19303e5778bc`; signing does not change this address |
| Required Commons target | `rappid:@kody-w/rapp-commons:fea3bd6e80bbac79efc22c4c1185c276d1833925a037ce120330be35e2afc3c7`; `https://kody-w.github.io/rapp-commons/` |
| Canonical ecosystem source | `kody-w/RAPP:specs/ecosystem-spec.json`; 60,479 bytes; SHA-256 `0eb8146b62af8e8473d2ca8944ed8aff69e18e41a143eb1ef466f3c3fc153616` |
| Required registry surface, currently not a registry | `kody-w/rapp-map:main/ecosystem-spec.json`; unsigned commit `baded0098d8b97c2876c0b8af4475cf3061b7ad0`; blob `d4021c6f7b916ede041ae9d3c0802977524d5189`; 60,479 bytes; SHA-256 `0eb8146b62af8e8473d2ca8944ed8aff69e18e41a143eb1ef466f3c3fc153616`; schema `rapp-ecosystem-spec/1.0`; no estate owner designated |
| Divergent mirror | `kody-w/rapp-god:api/v1/ecosystem-spec.json`; audit file commit `c6c0b3e2a68c96f8ed70005101f996ea91e4bd0e`; blob `d5ea75e4dc2be8cfc5f2e694aa5ce8521033609e`; 60,471 bytes; SHA-256 `f1ddcf7e1302a82195fa682ad94140d0d066bbe60647befc5030ec5b50507e9e` |
| Kernel `latest` alias | `rapp_kernel/manifest.json` declares unauthenticated `0.6.0`; `rapp_kernel/latest/brainstem.py` SHA-256 `f7fb359bbe8b6ba3db3665d81cb8e573a266c716278d8d21d8962ea40821e5aa`; active pin is distinct `brainstem-v0.6.9` |
| Canonical doors | Root returns 200, but remote bytes differ from target (`byte_equal_to_target: false`; target SHA-256 `59dd3b53e2ed0c7594b3754425938b907600fdf5787b1cef912276aa9d3711b3`; observed SHA-256 `8710b3c45fd660f96d159be41c861bf9fb9bb45acbc40888815d7942d342792e`); `rapp-cave`, `rapp-installer`, and `sample-session` identity doors return 404 |
| Facade legacy-wire baseline | At `f71810…`, audited Tier 1/Tier 2 lacked `idempotency_key`, and Tether posted incompatible `{messages}`; current main now contains the separate migrated facade described above |

The audit-baseline reports are retained with maintainer session
`9ac7ec28-fb92-4452-a8c9-477a2363685d`. Their SHA-256 values are:

- `RAPP-spec-matrix-report.md`:
  `e12f3a7a0a2ba15ef23b40421650d8551b7d4839781fb07a1b924783fedf6a78`;
- `RAPP-artifact-trust-report.md`:
  `7cf4506f38f7e23237292772068638387fca7832a0cbe240ff2d31db67574c75`;
- `RAPP-canon-mirrors-report.md`:
  `188eef4a3d2f65b93a4e0832515e8fe8b7b8826e1163b683029ab1d14bc51f59`.

They are evidence, not authority.

## 1. Publish the authenticated registry and out-of-band anchor

**Issue title:** `[Owner action] Publish the authenticated RAPP/1 registry and out-of-band anchor`

- **Why:** The structural authority pin cannot authenticate the owner, keys,
  namespaces, registry sequence, revocation state, genesis state, or freshness.
  No estate owner is designated, and the root rappid must not be assumed to be
  that owner.
- **What:** The owner independently selects the estate-owner rappid, approves
  the candidate namespaces and valid legacy-kind replacements, supplies the
  matching public SPKI, authenticates an append-only `rapp/1-registry` at
  sequence zero or greater, distributes the anchor independently, and
  separately authorizes publication at the required canonical surface.
- **Where:** RAPP may prepare a labeled, unsigned, non-authoritative candidate.
  The required publication surface is
  `kody-w/rapp-map:main/ecosystem-spec.json`. Its current bytes are the
  unsigned `rapp-ecosystem-spec/1.0` document, not a registry. Do not relabel
  `specs/ecosystem-spec.json` or `RAPP1_AUTHORITY.json`.
- **When:** One coordinated owner ceremony after stream inventory, namespace
  review, and root-upgrade evidence; before any authenticated public use.
- **How:**
  1. Review the protocol, variants, error codes, families, and kinds above.
  2. Select the keyed estate owner independently; never infer it from the
     repository root identity or a structural pin.
  3. Select valid `label.label` replacements or retirement outcomes for
     `memory_added`, `conversation`, and `tool_call`; never register those
     spellings as current kinds or edit `installer/plant.sh`. Implement only in
     target-owned adapters/retirement records.
  4. Enumerate every additional emitted kind by exact name and family.
  5. Prepare canonical strict I-JSON in RAPP with an owner-selected monotonic
     uint53 sequence and append-only §13.3 entries; label it unsigned and
     non-authoritative and do not overwrite either current ecosystem document.
  6. Include keyed-rappid/SPKI bindings, exactly one current genesis per
     stream, all deprecations, tombstones, re-anchors, current estate owner,
     and master-plan pointer.
  7. Have the owner authenticate the registry outside automation; publish only
     the public SPKI and self-certifying anchor.
  8. Through a separately authorized external publisher, advance
     `kody-w/rapp-map:main/ecosystem-spec.json` and record the immutable
     publication commit. Target automation must not write that repository.
  9. Distribute the anchor out of band, persist the highest accepted sequence,
     and apply the owner freshness window.
- **Prerequisites:** Owner-controlled Ed25519 or P-256 key outside this
  repository; reviewed root re-anchor evidence; complete stream/genesis
  inventory; reviewed facade namespace; owner-approved dispositions for the
  three invalid legacy kinds; separately authorized `rapp-map` publisher.
- **Exact acceptance:**
  1. Fetch the required `rapp-map` surface through the recorded immutable
     publication commit; `rapp1_core.strict_loads` accepts it and its bytes
     equal `rapp1_core.canonical_bytes`.
  2. Registry schema and sequence are exact; detached unencoded JWS
     verification passes against an SPKI whose tagged hash equals the
     out-of-band anchor tail.
  3. Authenticated entries exact-match the protocol pin, six variants, six
     error codes, three families, and three re-genesis kinds.
  4. The estate owner matches the independently distributed anchor, not an
     inferred root identity; the three invalid legacy kinds remain
     unregistered and each has an approved replacement/retirement.
  5. Every keyed identity resolves and every stream has one live genesis.
  6. A lower sequence is refused; over-age evidence reports `STALE`, never
     `VERIFIED` or clean.
- **Rollback/retirement:** On any failure, do not authorize external
  publication; keep the unsigned target export non-authoritative and every
  candidate unregistered. Published appends are immutable; correct through a
  later authenticated append/deprecation/tombstone. Root compromise requires
  a newly distributed out-of-band anchor.

Owner-supplied anchor, SPKI, sequence, candidate export path, external
publication commit, channel, freshness window, publication time, stream
inventory, and legacy-kind replacement map are deliberately `null`.

## 2. Authorize the historical root provisional-upgrade re-anchor

**Issue title:** `[Owner action] Authorize the historical root provisional-upgrade re-anchor`

- **Why:** Unsigned commit
  `19ff7d9ff483c0eef258a3b2031da1fd74570854` changed the stored root, but
  `_migrated_from` and commit authorship do not authorize §6.3 re-anchor.
- **What:** The owner explicitly selects the lawful §6.3 case. The 32→64
  evidence makes `upgrade` a candidate, not an inferred decision. To close
  this action, the owner selects `upgrade`, authorizes exactly the
  historical/provisional/current mapping, and proves that the provisional
  identity resolved to `kody-w` at read time. Any other owner-selected case
  retires this candidate action and requires separate case-specific review.
- **Where:** `rappid.json`, the migration commit and parent tree, plus the
  owner-selected immutable re-anchor record location in the registry.
- **When:** Select the case during the trust-genesis ceremony and, if
  `upgrade` is selected, authorize before the current root is accepted or used
  for public artifacts. Do not assume the root is the estate owner.
- **How:**
  1. Verify the pre-migration stored ID, historical v2 provenance, UUID
     `0b635450-c042-49fb-b4b1-bdb571044dec`, repository owner, unsigned commit
     state, and git lineage.
  2. Canonicalize on read to the lowercase 32-hex provisional ID without
     emitting it.
  3. Recompute `Hb("rapp/1:rappid", UUID_octets)` and require the existing tail
     `9a8f0a4b5a710e20f4d819a0f37d2a4c9f113b5e78fb3c29e70b54fff48a38f9`.
     Do not mint another identity.
  4. Require the owner to select the case explicitly. If `upgrade` is selected,
     bind its resolution evidence to those exact IDs; code and tail length may
     not choose the case.
  5. Have the applicable owner authenticate outside automation. If this root
     is separately selected as estate owner, also require the additional
     outgoing-owner authorization.
  6. Append only the verified record in the signed registry.
  7. Preserve both `_migrated_from` strings, UUID, migration commit, and
     historical tree.
- **Prerequisites:** Prepared anchor/SPKI ceremony; independently reviewable
  before/after git trees; explicit owner case selection after reviewing every
  §6.3 case; independent estate-owner selection; no delegated automation
  approval.
- **Exact acceptance:**
  1. The owner explicitly selected `upgrade`; old/new IDs, case, UUID, and
     tagged tail match byte-for-byte, with no code inference.
  2. Owner authentication verifies under the tenure in effect at the chosen
     authorization time; if the root is separately selected as estate owner,
     the additional outgoing-owner authorization also verifies.
  3. Evidence proves owner resolution at read time; metadata alone is refused.
  4. All migration provenance and the `false/unsigned` commit state remain
     recoverable and are not presented as protocol authentication.
  5. No code path can infer authorization from this ledger, `rappid.json`, a
     commit author, or an automation identity.
- **Rollback/retirement:** Failure leaves the current ID structurally visible
  but unauthenticated. Keep old IDs as provenance; neither mint nor silently
  restore another ID. If the owner selects another case, retire this candidate
  and prepare a distinct owner-reviewed case action without automated
  authorization. A valid append is later superseded only by another
  owner-authorized re-anchor or tombstone.

Owner authorization time, key identifier, selected case, estate-owner
selection, outgoing-owner evidence path, record path, and case evidence bundle
are deliberately `null`. **No automation can self-authorize.**

## 3. Reissue and retire the Commons invite

**Issue title:** `[Owner action] Reissue the signed RAPP/1 Commons invite and retire the placeholder`

- **Why:** The 443-byte `pages/tutorials/commons.egg` at address
  `a03fa90289eaefcf1a6521cdc10ee17bc706a0bb353e688ad84135d684380fb7`
  has a placeholder-shaped, non-verifying signature member and points at the
  404 URL `https://kody-w.github.io/commons/`. The external well-known object
  is still `brainstem-egg/2.3-neighborhood` with the superseded 32-hex
  identity.
- **What:** Authorize Commons identity continuity, issue a new canonical signed
  `rapp/1-egg` `invite` for the current Commons target, record its new path and
  address, publish it at the well-known external path and one approved
  target-owned path, then remove the old tutorial artifact from live use.
- **Where:**
  - replace `kody-w/rapp-commons:.well-known/neighborhood.egg`;
  - public URL
    `https://kody-w.github.io/rapp-commons/.well-known/neighborhood.egg`;
  - candidate target path `pages/tutorials/artifacts/commons-invite.egg`;
  - URL-only fixed candidate address
    `d15305a25cbe6c9aab51a4ed2ab5514345772023a95d658b37fc19303e5778bc`;
  - retire `pages/tutorials/commons.egg`.
- **When:** After the Commons upgrade re-anchor and owner succession are
  authenticated. Switch links and retire the placeholder atomically only after
  both replacement locations verify.
- **How:**
  1. Create the exact seven-member §9.1 manifest with
     `schema:"rapp/1-egg"`, `variant:"invite"`, `contents:[]`, and no extras.
  2. Use the current Commons rappid, `target_kind:"neighborhood"`, and
     `target_url:"https://kody-w.github.io/rapp-commons/"`.
  3. Require the owner to select the lawful Commons re-anchor case explicitly.
     `upgrade` is only a candidate from the 32→64 evidence. If selected,
     authenticate the mapping from provisional tail
     `3929ce90ebe97fe2a95432e9f647f3a3` to the exact current identity. A remote
     `_migrated_from` assertion is only provenance.
  4. Have the estate owner in effect at `created_utc` authenticate the
     canonical manifest-without-signature outside automation.
  5. Verify through fresh registry succession; a merely registered non-owner
     key is insufficient.
  6. Record `H("rapp/1:egg-manifest", manifest without signature)`. If the URL
     is the sole changed unsigned member, it must equal `d15305…e5778bc`;
     signing alone cannot alter the address.
  7. Publish byte-identical canonical JSON at both approved locations, update
     tutorial links, and remove the old path from live distribution.
- **Prerequisites:** Explicitly owner-selected and authenticated lawful Commons
  re-anchor plus owner succession; owner-confirmed current Commons identity and
  Pages URL; external repository publisher; approved target path and commits.
- **Exact acceptance:**
  1. Manifest and payload member sets and values are exact; no legacy schema,
     old identity, or wrong `/commons/` URL remains.
  2. The explicitly owner-selected Commons re-anchor case and its evidence
     authenticate without code inference; for `upgrade`, the provisional and
     current tails match exactly. Remote `_migrated_from` and repository
     commits are not authorization.
  3. Detached JWS and owner tenure at `created_utc` both verify.
  4. Computed egg address matches owner evidence and equals
     `d15305…e5778bc` when only the URL changed among unsigned members.
  5. Immutable external and target URLs serve byte-identical canonical bytes.
  6. No live reference to `pages/tutorials/commons.egg` remains; the old path
     is absent or explicitly retired and cannot be accepted.
- **Rollback/retirement:** Joining remains disabled on failure—never fall back
  to either invalid predecessor. Preserve the retired target artifact only by
  path, SHA-256, and git history. Future invites are new addressed artifacts,
  not edits to a content-addressed invite.

Owner creation time, owner key identifier, Commons re-anchor case, approved
target path, final egg address, and publication commits are deliberately
`null`.

## 4. Correct or retire the divergent `rapp-god` mirror

**Issue title:** `[External owner action] Correct or remove the divergent rapp-god ecosystem mirror`

- **Why:** The target and `rapp-map` match at 60,479 bytes and SHA-256
  `0eb814…3616`; `rapp-god` is 60,471 bytes and SHA-256 `f1ddcf…e9e`.
  It still names `rapp-rappid/2.0` where canonical names `rapp/1`. Moving
  `main` URLs are not immutable provenance. Separately, `rapp_kernel/latest`
  is an unauthenticated v0.6.0 archive alias while the active pin is
  `brainstem-v0.6.9`.
- **What:** The target immediately marks/removes `rapp-god` as
  non-authoritative while the external owner chooses correction or continued
  removal. The target records immutable provenance for every retained mirror
  and either retires the kernel `latest` claim or adds a target-owned sidecar
  pinning its unchanged bytes as historical v0.6.0, never current 0.6.9.
- **Where:** Canonical `kody-w/RAPP:specs/ecosystem-spec.json`; matching
  `kody-w/rapp-map:ecosystem-spec.json`; divergent
  `kody-w/rapp-god:api/v1/ecosystem-spec.json`; target claims in
  `specs/ecosystem-spec.json` and `specs/ECOSYSTEM_SPEC.md`; kernel alias
  `rapp_kernel/manifest.json` and `rapp_kernel/latest/brainstem.py`.
- **When:** Before any mirror supplies authority, provenance, or clean status;
  repeat whenever an intentionally pinned mirror advances.
- **How:**
  1. Immediately remove or mark `rapp-god` non-authoritative in target-owned
     claims; do not wait for external correction to fail closed.
  2. File an external-owner issue containing audit file commit
     `c6c0b3e2a68c96f8ed70005101f996ea91e4bd0e`, later observed repository head
     `94d0f49800fdd94b627f089c9cf3d07a7774b89b`, blob IDs, lengths, hashes, and
     two JSON differences from the machine ledger.
  3. On correction, republish exact bytes from an approved immutable canonical
     commit and record the new immutable external commit.
  4. Otherwise remove `rapp-god` from active target mirror/authority claims and
     retain it only as divergent evidence.
  5. Regenerate target machine/human declarations with repository, path,
     commit, length, SHA-256, observation time, and status.
  6. Preserve `rapp_kernel/latest/brainstem.py` byte-for-byte. Either retire
     its mutable/current claim or add a target-owned sidecar pinning SHA-256
     `f7fb359bbe8b6ba3db3665d81cb8e573a266c716278d8d21d8962ea40821e5aa`
     as historical v0.6.0, distinct from the 0.6.9 active pin.
  7. State that no ecosystem mirror or kernel alias is the §13 registry or
     anchor.
- **Prerequisites:** Target authority to remove its own claim; external-owner
  approval only for correction/reinstatement; approved immutable canonical
  commit; identified target generator; mirror quarantined while pending.
- **Exact acceptance:**
  1. Every retained immutable URL matches canonical length, SHA-256, and bytes,
     or `rapp-god` is absent from active claims.
  2. `$.primitives[0].schema` and `$.schemas_ref` match canonical exactly.
  3. Target machine and human provenance agree and contain no moving-main-only
     proof.
  4. The kernel alias payload retains its exact hash and is retired as
     latest/current or explicitly provenance-pinned as unauthenticated
     historical v0.6.0; the active 0.6.9 pin remains distinct.
  5. No updated claim calls a mirror or alias the authenticated registry or
     anchor.
- **Rollback/retirement:** On drift, quarantine and remove the mirror claim;
  never import divergent bytes into canonical. Retire the kernel latest/current
  claim unless historical provenance verifies, while keeping its versioned
  payload byte-identical. Retain observed commit/hashes as history.
  Reinstatement requires a new exact-byte proof and immutable provenance.

The decision, all publication commits/times, kernel alias disposition, and
sidecar path are deliberately `null`. This ledger implementation performs
**no external write or payload edit**.

## 5. Approve the public RAPP/1 facade switch

**Issue title:** `[Owner action] Approve the public RAPP/1 facade switch after registry closure`

- **Why:** Current main contains the migrated stateful target-owned facade, but
  it remains pre-acceptance and its six candidate errors are
  unregistered. At the `f71810…` audit baseline, Tier 1/Tier 2 lacked
  `idempotency_key`, Tether sent incompatible `{messages}`, alternate routes
  could bypass the wire or touch the immutable grail, and the `rapp-cave`,
  `rapp-installer`, and `sample-session` identity doors returned 404.
- **What:** Publish one stateful `POST /chat` gateway only after registration
  and closure; constrain error steps to the exact allowed domain; route
  target-owned clients through it; close or retire missing canonical-door
  claims; retain `GET /health` as control plane; make all alternate capability
  routes unreachable; inject a separately reviewed inference adapter; prove
  there is no grail import, token/cache access, telemetry write, agent/tool
  execution, or other grail side effect.
- **Where:** Current candidate `rapp_brainstem/rapp1_facade.py` with source
  commit intentionally null because the bytes and ledger share a commit,
  SHA-256
  `4bd8e1c51290295c5dfd6dec73a5f12f3771ec674a5e856ab78edbfc61151a01`,
  plus `run_rapp1_facade.py`; owner-selected public origin; frozen paths in
  `KERNEL_PIN.json`; exact door evidence in the machine ledger.
- **When:** Only after all four status blockers, the post-migration
  `Active-path residual`, canonical-door dispositions, current facade tests,
  pin gate, and owner deployment review pass at one commit.
- **How:**
  1. Use the recomputed current facade bytes above as the review baseline.
     Keep the production launcher at its target-owned `inference-refused`
     default until a separately reviewed, side-effect-free inference adapter
     is supplied through explicit dependency injection. Never import or call
     the pinned brainstem module.
  2. Exact-match the six emitted errors to fresh authenticated registry
     entries.
  3. Permit error `step` only as `"1"`, `"1a"`, `"2"`, `"3"`, `"4"`, `"5"`,
     `"6"`, or `null`.
  4. Remove or isolate all direct-agent, alternate-chat, business-function,
     browser-worker, and grail `/chat` routes.
  5. Route target-owned Tier 2 and Tether through the gateway and retire their
     direct incompatible wire use; do not edit pinned Tier 1.
  6. Verify the root identity door serves the exact target bytes. Separately
     authorize publication or retire each 404 door claim. Never modify or
     deploy `kody-w/rapp-installer`, its clone, or pinned files.
  7. Use durable target-owned storage outside grail paths. Review and record
     the exact injected adapter bytes and prove it cannot access grail token
     caches, telemetry, agents, tools, or persistence.
  8. Exercise exact wire, refusal, idempotency, concurrency, and route tests at
     the public origin.
  9. Hash all three frozen files before/after and run
     `python3 check_kernel_pin.py`.
- **Prerequisites:** The four actions above accepted; target-main migrations
  through `4c2b999…` present; every remaining `Active-path residual` closed or
  explicitly fail-closed; approved publish-or-retire disposition for the three
  404 identity doors; approved Tier 2/Tether/worker gateway or retirement
  dispositions; an owner-reviewed inference adapter supplied only through
  explicit dependency injection; all non-owner gates green.
- **Exact acceptance:**
  1. Deployment source, authenticated registry, and this ledger contain exactly
     the same six error codes.
  2. `python3 -m pytest rapp_brainstem/test_rapp1_facade.py -q` passes and the
     same cases pass against the public origin.
  3. Every emitted step exact-matches `"1"`, `"1a"`, `"2"`, `"3"`, `"4"`,
     `"5"`, `"6"`, or `null`; current null values remain valid.
  4. Only `POST /chat` is a public RAPP capability; `GET /health` is control
     plane. `/agents`, `/agents/invoke`, `/api/agent`, `/api/copilot/chat`,
     `/api/businessinsightbot_function`, `/api/trigger/copilot-studio`, and the
     worker/grail routes are unreachable or return 404/410 without execution;
     target-owned clients do not bypass the facade.
  5. The root door serves exact target bytes with SHA-256
     `59dd3b53e2ed0c7594b3754425938b907600fdf5787b1cef912276aa9d3711b3`;
     every 404 claim is served from an authorized pinned publication or
     retired, with no installer deployment or byte change.
  6. Frozen hashes remain
     `a293dd9f11eef915bf15776f08c736faa60cb749820871b6753ea98233142a71`,
     `701488bc00d536a7b23295e7da99c62f24e9b00f233daa325886430c736b78eb`,
     and
     `13eb74b44be6e3a85a0efa0dedf56aec05e9e50140e1c8bbc0d0fbd8097b0717`;
     the launcher imports no grail module, accesses no grail token/cache or
     telemetry state, tools and agents never run, and the pin gate passes.
  7. Routing and claim/status changes switch atomically. Otherwise public
     health/docs remain pre-acceptance and not fully conformant.
- **Rollback/retirement:** Withdraw to unavailable/maintenance-only, preserve
  durable idempotency evidence, restore explicit pre-acceptance claims, and
  never fall back to the grail or legacy route. Registered code history is not
  reused or silently removed.

Public origin, deployment commit, switch time, registry evidence location,
canonical-door disposition record, reviewed inference-adapter evidence, and
rollback owner are deliberately `null`.

## Issue-ready immutable Cave residual (not a target action)

**Issue title:** `[Containment] Retire Cave hatch.py execution of extracted installer runtimes`

- **Affected immutable path:**
  `cave/rapplications/rapp-installer/hatch.py`, mirrored from the separately
  owned installer payload. This target must not patch that prepared clone or
  any egg/archive containing it.
- **Observed behavior:** `_read_egg_bytes` accepts any local archive or HTTPS
  response. `_extract_egg` checks the schema string and path containment, but
  does not authenticate a signer, pin the archive, validate the manifest
  `slug`, or verify member digests. `main` then advertises the extracted
  `serve.py` and, with `--run`, executes it via `os.execve`. Thus an extracted
  payload remains an equivalent public launcher and can execute attacker- or
  stale-archive-controlled server code at user privilege. The checked-in
  target tombstone at `serve.py` does not constrain a newly extracted
  replacement.
- **Required external-owner fix:** In the authoritative installer repository,
  retire `hatch.py`, its `--run` option, and launch guidance with an explicit
  410/exit-78 tombstone that performs no download, extraction, venv/pip work,
  subprocess, import, execution, or network bind. Publish any replacement
  payload only through the owner's authenticated artifact process; do not
  patch this target's prepared clone or immutable archives.
- **Acceptance:** Invoking the authoritative hatcher with no arguments, a
  local egg, an HTTPS egg, `--run`, or `--no-venv --run` always returns the
  documented 410/78 refusal and creates no files, child processes, or sockets.
  The target's immutable copies remain byte-identical until an independently
  authorized replacement artifact is adopted.

## Status-blocker closure map

| `RAPP1_STATUS.md` owner blocker | Action |
|---|---|
| Signed monotonic registry and out-of-band anchor | `owner-publish-authenticated-registry` |
| Lawful root re-anchor | `owner-authorize-root-upgrade-reanchor` |
| Signed replacement invite | `owner-reissue-commons-invite` |
| External mirror correction | `owners-correct-or-retire-external-mirror` |

The fifth action, `owner-enable-public-rapp1-facade`, is a dependent release
gate and closes no blocker by itself.
