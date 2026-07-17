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
- **Facade error codes (exactly seven):** `malformed-request`,
  `unknown-session`, `idempotency-conflict`, `idempotency-in-progress`,
  `session-in-progress`, `inference-refused`, `facade-storage-refused`.
- **Kind families:** `memory`, `body`, `swarm`.
- **Required re-genesis kinds:** `memory.re-genesis` → `memory`,
  `body.re-genesis` → `body`, and `swarm.re-genesis` → `swarm`.
- **Other kinds:** undecided. Every emitted kind must be separately enumerated
  and assigned exactly one family; prefixes and wildcards grant no authority.

The owner registry also needs explicit SPKI binding, one-current-genesis,
append-only tombstone, time-scoped succession, root-compromise recovery,
no-rollback, and freshness policies. The exact policy requirements are in the
machine ledger.

## Verified evidence snapshot

| Subject | Verified fact |
|---|---|
| Historical root | `rappid:@kody-w/RAPP:0b635450c04249fbb4b1bdb571044dec` |
| Canonicalized provisional root | `rappid:@kody-w/rapp:0b635450c04249fbb4b1bdb571044dec` |
| Current stored root | `rappid:@kody-w/rapp:9a8f0a4b5a710e20f4d819a0f37d2a4c9f113b5e78fb3c29e70b54fff48a38f9` |
| Root migration | unsigned commit `19ff7d9ff483c0eef258a3b2031da1fd74570854`; `rappid.json` SHA-256 `8710b3c45fd660f96d159be41c861bf9fb9bb45acbc40888815d7942d342792e` |
| Retired invite | `pages/tutorials/commons.egg`; 443 bytes; SHA-256 `2731c02f187701c1d07b3a7f5eed5e2073c203ffb4f6c08d00292894e3319a5d`; egg address `a03fa90289eaefcf1a6521cdc10ee17bc706a0bb353e688ad84135d684380fb7` |
| URL-fixed invite candidate | If the URL is the sole changed unsigned member: `d15305a25cbe6c9aab51a4ed2ab5514345772023a95d658b37fc19303e5778bc`; signing does not change this address |
| Required Commons target | `rappid:@kody-w/rapp-commons:fea3bd6e80bbac79efc22c4c1185c276d1833925a037ce120330be35e2afc3c7`; `https://kody-w.github.io/rapp-commons/` |
| Canonical ecosystem source | `kody-w/RAPP:specs/ecosystem-spec.json`; 60,479 bytes; SHA-256 `0eb8146b62af8e8473d2ca8944ed8aff69e18e41a143eb1ef466f3c3fc153616` |
| Required registry surface, currently not a registry | `kody-w/rapp-map:main/ecosystem-spec.json`; unsigned commit `baded0098d8b97c2876c0b8af4475cf3061b7ad0`; blob `d4021c6f7b916ede041ae9d3c0802977524d5189`; 60,479 bytes; SHA-256 `0eb8146b62af8e8473d2ca8944ed8aff69e18e41a143eb1ef466f3c3fc153616`; schema `rapp-ecosystem-spec/1.0` |
| Divergent mirror | `kody-w/rapp-god:api/v1/ecosystem-spec.json`; audit file commit `c6c0b3e2a68c96f8ed70005101f996ea91e4bd0e`; blob `d5ea75e4dc2be8cfc5f2e694aa5ce8521033609e`; 60,471 bytes; SHA-256 `f1ddcf7e1302a82195fa682ad94140d0d066bbe60647befc5030ec5b50507e9e` |
| Canonical doors | Root returns 200 and exact `rappid.json` bytes; `rapp-cave`, `rapp-installer`, and `sample-session` identity doors return 404 |
| Facade candidate | commit `7f84d84b28bf7b570787af16b0008cec96704f53`; `rapp_brainstem/rapp1_facade.py` SHA-256 `6eca226e5ebc1a41f7eacac9cc98e19d20e5705750b6cd0166d8a0809d19a5da` |

The audit reports are retained with maintainer session
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
- **What:** The estate owner approves the candidate namespaces, supplies a
  keyed estate-owner rappid and matching public SPKI, authenticates an
  append-only `rapp/1-registry`, distributes the anchor independently, and
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
  2. Enumerate every additional emitted kind by exact name and family.
  3. Prepare canonical strict I-JSON in RAPP with an owner-selected monotonic
     uint53 sequence and append-only §13.3 entries; label it unsigned and
     non-authoritative and do not overwrite either current ecosystem document.
  4. Include keyed-rappid/SPKI bindings, exactly one current genesis per
     stream, all deprecations, tombstones, re-anchors, current estate owner,
     and master-plan pointer.
  5. Have the owner authenticate the registry outside automation; publish only
     the public SPKI and self-certifying anchor.
  6. Through a separately authorized external publisher, advance
     `kody-w/rapp-map:main/ecosystem-spec.json` and record the immutable
     publication commit. Target automation must not write that repository.
  7. Distribute the anchor out of band, persist the highest accepted sequence,
     and apply the owner freshness window.
- **Prerequisites:** Owner-controlled Ed25519 or P-256 key outside this
  repository; reviewed root re-anchor evidence; complete stream/genesis
  inventory; reviewed facade namespace; separately authorized `rapp-map`
  publisher.
- **Exact acceptance:**
  1. Fetch the required `rapp-map` surface through the recorded immutable
     publication commit; `rapp1_core.strict_loads` accepts it and its bytes
     equal `rapp1_core.canonical_bytes`.
  2. Registry schema and sequence are exact; detached unencoded JWS
     verification passes against an SPKI whose tagged hash equals the
     out-of-band anchor tail.
  3. Authenticated entries exact-match the protocol pin, six variants, seven
     error codes, three families, and three re-genesis kinds.
  4. Every keyed identity resolves and every stream has one live genesis.
  5. A lower sequence is refused; over-age evidence reports `STALE`, never
     `VERIFIED` or clean.
- **Rollback/retirement:** On any failure, do not authorize external
  publication; keep the unsigned target export non-authoritative and every
  candidate unregistered. Published appends are immutable; correct through a
  later authenticated append/deprecation/tombstone. Root compromise requires
  a newly distributed out-of-band anchor.

Owner-supplied anchor, SPKI, sequence, candidate export path, external
publication commit, channel, freshness window, publication time, and stream
inventory are deliberately `null`.

## 2. Authorize the historical root provisional-upgrade re-anchor

**Issue title:** `[Owner action] Authorize the historical root provisional-upgrade re-anchor`

- **Why:** Unsigned commit
  `19ff7d9ff483c0eef258a3b2031da1fd74570854` changed the stored root, but
  `_migrated_from` and commit authorship do not authorize §6.3 re-anchor.
- **What:** Authorize exactly the historical/provisional/current mapping in the
  evidence table with `case:"upgrade"` and prove that the provisional identity
  resolved to `kody-w` at read time.
- **Where:** `rappid.json`, the migration commit and parent tree, plus the
  owner-selected immutable re-anchor record location in the registry.
- **When:** During the trust-genesis ceremony and before the current root
  authorizes any accepted public artifact.
- **How:**
  1. Verify the pre-migration stored ID, historical v2 provenance, UUID
     `0b635450-c042-49fb-b4b1-bdb571044dec`, repository owner, unsigned commit
     state, and git lineage.
  2. Canonicalize on read to the lowercase 32-hex provisional ID without
     emitting it.
  3. Recompute `Hb("rapp/1:rappid", UUID_octets)` and require the existing tail
     `9a8f0a4b5a710e20f4d819a0f37d2a4c9f113b5e78fb3c29e70b54fff48a38f9`.
     Do not mint another identity.
  4. Bind owner-reviewed upgrade evidence to those exact IDs.
  5. Have the outgoing estate owner authenticate the record outside automation
     and append it in the signed registry.
  6. Preserve both `_migrated_from` strings, UUID, migration commit, and
     historical tree.
- **Prerequisites:** Prepared anchor/SPKI ceremony; independently reviewable
  before/after git trees; owner confirmation that the case is `upgrade`, not
  rotation, compromise, or tag migration; no delegated automation approval.
- **Exact acceptance:**
  1. Old/new IDs, case, UUID, and tagged tail match byte-for-byte.
  2. Owner authentication verifies under the tenure in effect at the chosen
     authorization time.
  3. Evidence proves owner resolution at read time; metadata alone is refused.
  4. All migration provenance and the `false/unsigned` commit state remain
     recoverable and are not presented as protocol authentication.
  5. No code path can infer authorization from this ledger, `rappid.json`, a
     commit author, or an automation identity.
- **Rollback/retirement:** Failure leaves the current ID structurally visible
  but unauthenticated. Keep old IDs as provenance; neither mint nor silently
  restore another ID. A valid append is later superseded only by another
  owner-authorized re-anchor or tombstone.

Owner authorization time, owner key identifier, record path, and evidence
bundle path are deliberately `null`. **No automation can self-authorize.**

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
  3. Require an owner-authenticated `case:"upgrade"` mapping from provisional
     tail `3929ce90ebe97fe2a95432e9f647f3a3` to the exact current Commons
     identity. A remote `_migrated_from` assertion is only provenance.
  4. Have the estate owner in effect at `created_utc` authenticate the
     canonical manifest-without-signature outside automation.
  5. Verify through fresh registry succession; a merely registered non-owner
     key is insufficient.
  6. Record `H("rapp/1:egg-manifest", manifest without signature)`. If the URL
     is the sole changed unsigned member, it must equal `d15305…e5778bc`;
     signing alone cannot alter the address.
  7. Publish byte-identical canonical JSON at both approved locations, update
     tutorial links, and remove the old path from live distribution.
- **Prerequisites:** Authenticated Commons re-anchor and owner succession;
  owner-confirmed current Commons identity and Pages URL; external repository
  publisher; approved target path and commits.
- **Exact acceptance:**
  1. Manifest and payload member sets and values are exact; no legacy schema,
     old identity, or wrong `/commons/` URL remains.
  2. The exact Commons provisional-upgrade re-anchor authenticates; remote
     `_migrated_from` and repository commits are not authorization.
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

Owner creation time, owner key identifier, approved target path, final egg
address, and publication commits are deliberately `null`.

## 4. Correct or retire the divergent `rapp-god` mirror

**Issue title:** `[External owner action] Correct or remove the divergent rapp-god ecosystem mirror`

- **Why:** The target and `rapp-map` match at 60,479 bytes and SHA-256
  `0eb814…3616`; `rapp-god` is 60,471 bytes and SHA-256 `f1ddcf…e9e`.
  It still names `rapp-rappid/2.0` where canonical names `rapp/1`. Moving
  `main` URLs are not immutable provenance.
- **What:** External and canonical owners choose correction or removal. Then
  the target records immutable commit/hash provenance for each retained mirror.
- **Where:** Canonical `kody-w/RAPP:specs/ecosystem-spec.json`; matching
  `kody-w/rapp-map:ecosystem-spec.json`; divergent
  `kody-w/rapp-god:api/v1/ecosystem-spec.json`; target claims in
  `specs/ecosystem-spec.json` and `specs/ECOSYSTEM_SPEC.md`.
- **When:** Before any mirror supplies authority, provenance, or clean status;
  repeat whenever an intentionally pinned mirror advances.
- **How:**
  1. File an external-owner issue containing audit file commit
     `c6c0b3e2a68c96f8ed70005101f996ea91e4bd0e`, later observed repository head
     `94d0f49800fdd94b627f089c9cf3d07a7774b89b`, blob IDs, lengths, hashes, and
     two JSON differences from the machine ledger.
  2. On correction, republish exact bytes from an approved immutable canonical
     commit and record the new immutable external commit.
  3. Otherwise remove `rapp-god` from active target mirror/authority claims and
     retain it only as divergent evidence.
  4. Regenerate target machine/human declarations with repository, path,
     commit, length, SHA-256, observation time, and status.
  5. State that no ecosystem mirror is the §13 registry or anchor.
- **Prerequisites:** Explicit owner decision; approved immutable canonical
  commit; identified target generator; mirror quarantined while pending.
- **Exact acceptance:**
  1. Every retained immutable URL matches canonical length, SHA-256, and bytes,
     or `rapp-god` is absent from active claims.
  2. `$.primitives[0].schema` and `$.schemas_ref` match canonical exactly.
  3. Target machine and human provenance agree and contain no moving-main-only
     proof.
  4. No updated claim calls a mirror the authenticated registry or anchor.
- **Rollback/retirement:** On drift, quarantine and remove the mirror claim;
  never import divergent bytes into canonical. Retain observed commit/hashes as
  history. Reinstatement requires a new exact-byte proof and target pin update.

The decision and all publication commits/times are deliberately `null`. This
ledger implementation performs **no external write**.

## 5. Approve the public RAPP/1 facade switch

**Issue title:** `[Owner action] Approve the public RAPP/1 facade switch after registry closure`

- **Why:** The local facade is a pre-acceptance candidate. Its seven errors are
  not registered, historical alternate routes could bypass the only wire or
  touch the immutable grail, and the `rapp-cave`, `rapp-installer`, and
  `sample-session` canonical identity doors return 404.
- **What:** Publish one `POST /chat` capability only after registration and
  closure; close or retire missing canonical-door claims; retain `GET /health`
  as control plane; make all alternate capability routes unreachable; prove no
  grail side effects.
- **Where:** Candidate `rapp_brainstem/rapp1_facade.py` and
  `run_rapp1_facade.py`; owner-selected public origin; frozen paths in
  `KERNEL_PIN.json`; exact door evidence in the machine ledger.
- **When:** Only after all four status blockers, implementation migrations,
  canonical-door dispositions, facade tests, pin gate, and owner deployment
  review pass at one commit.
- **How:**
  1. Integrate the reviewed facade without mounting the pinned brainstem app;
     keep tools disabled at the private inference boundary.
  2. Exact-match the seven emitted errors to fresh authenticated registry
     entries.
  3. Remove or isolate all direct-agent, alternate-chat, business-function,
     browser-worker, and grail `/chat` routes.
  4. Verify the root identity door serves the exact target bytes. Separately
     authorize publication or retire each 404 door claim. Never modify or
     deploy `kody-w/rapp-installer`, its clone, or pinned files.
  5. Use durable target-owned storage outside grail paths.
  6. Exercise exact wire, refusal, idempotency, concurrency, and route tests at
     the public origin.
  7. Hash all three frozen files before/after and run
     `python3 check_kernel_pin.py`.
- **Prerequisites:** The four actions above accepted; migrations and facade
  merged into one reviewed deployment; approved publish-or-retire disposition
  for the three 404 identity doors; all non-owner gates green.
- **Exact acceptance:**
  1. Deployment source, authenticated registry, and this ledger contain exactly
     the same seven error codes.
  2. `python3 -m pytest rapp_brainstem/test_rapp1_facade.py -q` passes and the
     same cases pass against the public origin.
  3. Only `POST /chat` is a public RAPP capability; `GET /health` is control
     plane. `/agents`, `/agents/invoke`, `/api/agent`, `/api/copilot/chat`,
     `/api/businessinsightbot_function`, `/api/trigger/copilot-studio`, and the
     grail port are unreachable or return 404/410 without execution.
  4. The root door serves exact target bytes with SHA-256
     `8710b3c45fd660f96d159be41c861bf9fb9bb45acbc40888815d7942d342792e`;
     every 404 claim is served from an authorized pinned publication or
     retired, with no installer deployment or byte change.
  5. Frozen hashes remain
     `a293dd9f11eef915bf15776f08c736faa60cb749820871b6753ea98233142a71`,
     `701488bc00d536a7b23295e7da99c62f24e9b00f233daa325886430c736b78eb`,
     and
     `13eb74b44be6e3a85a0efa0dedf56aec05e9e50140e1c8bbc0d0fbd8097b0717`;
     tools never run; pin gate passes.
  6. Routing and claim/status changes switch atomically. Otherwise public
     health/docs remain pre-acceptance and not fully conformant.
- **Rollback/retirement:** Withdraw to unavailable/maintenance-only, preserve
  durable idempotency evidence, restore explicit pre-acceptance claims, and
  never fall back to the grail or legacy route. Registered code history is not
  reused or silently removed.

Public origin, deployment commit, switch time, registry evidence location,
canonical-door disposition record, and rollback owner are deliberately
`null`.

## Status-blocker closure map

| `RAPP1_STATUS.md` owner blocker | Action |
|---|---|
| Signed monotonic registry and out-of-band anchor | `owner-publish-authenticated-registry` |
| Lawful root re-anchor | `owner-authorize-root-upgrade-reanchor` |
| Signed replacement invite | `owner-reissue-commons-invite` |
| External mirror correction | `owners-correct-or-retire-external-mirror` |

The fifth action, `owner-enable-public-rapp1-facade`, is a dependent release
gate and closes no blocker by itself.
