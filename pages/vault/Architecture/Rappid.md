---
title: Rappid — The One Identifier
status: published
section: Architecture
hook: RAPP/1 §6 defines one current self-locating rappid grammar, mint-once tails, bounded legacy canonicalization, and owner-authorized re-anchor.
---

# Rappid — The One Identifier

> **Mixed current policy and marked history.** Current sections of this note
> are subordinate to RAPP/1 rev-5; explicitly bounded historical sections
> preserve the former identity narrative verbatim. For canonicalization,
> identity, frames, wire, eggs, registry, trust, and protocol evolution, follow
> [`RAPP1_AUTHORITY.json`](../../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../../RAPP1_STATUS.md).

> **Hook.** A rappid is the exact RAPP/1 §6 self-locating identifier. Its tail
> is domain-minted once from permitted entropy, while current authority and
> lawful re-anchor resolve through the authenticated §13 registry.

This is a subordinate architecture guide. The pinned rev-5 specification is
the only protocol authority; this page supplies product context and preserves
the earlier design record where explicitly marked.

## What rappid is

A rappid is a public identifier assigned to every digital organism in the RAPP species tree. RAPP itself — the prototype, the godfather — has a rappid. Every variant of RAPP has a rappid. Every AI organism running on top of a RAPP-descended brainstem has a rappid. Every twin, swarm, customer estate, and future android / monkey / turtle / cloud / on-device organism has a rappid.

Rappids:

- Are **public**. Anyone can read them, share them, reference them.
- Have a tail minted exactly once under §6.2 and then preserved. The only
  re-mint is a verifiably owner-authorized §6.3 re-anchor.
- May carry application lineage such as `parent_rappid`, but that field does
  not itself establish ancestry, authority, or trust.
- Participate in traceability only through verified §§10/13 signatures,
  succession, revocation, and registry records.

Think of a rappid as the species' social-security number. Universal. Singular. The unit of accounting for digital biology.

## The current format

```
rappid:@<owner>/<slug>:<64hex>
```

RAPP/1 §6.1 defines this case-sensitive self-locating grammar:

| Field | Meaning |
|---|---|
| `rappid:` | Always literal. Identifies this string as a rappid. |
| `@<owner>/<slug>` | The initial self-locating anchor. Parsing yields a candidate GitHub door; current authority after succession or re-anchor still resolves through §13. |
| `<64hex>` | The immutable mint-once tail: `Hb("rapp/1:rappid", uuid4_octets)` for keyless identity or `Hb("rapp/1:rappid", SPKI_DER)` for keyed identity. It is never name-, slug-, or commit-derived. |

`kind` is not part of the rappid. The authenticated §13 registry binds each
registered kind to exactly one family; application records may add subordinate
metadata but cannot redefine identity or trust.

**Legacy forms are bounded migration input only.** §6.3 may restructure an old
form while preserving its tail inside a one-time migrator. Provisional tails
must never be emitted or persisted as current, normal readers do not retain
legacy branches indefinitely, and a fresh tail requires a verifiable
owner-signed re-anchor record.

### Concrete examples

```
rappid:@kody-w/rapp:<64-lowercase-hex-tail>
                    └ exact §6.2 domain-separated tail; authority still requires §13 ┘

rappid:@kody-w/kody-twin:<64-lowercase-hex-tail>
                         └ keyed or keyless §6.2 mint, never an abbreviated current identity ┘

rappid:@<publisher>/<twin-slug>:<64hex>
                    └ a twin under that organism — one repo = one slug = one self-locating address ┘
```

### Hash extraction for the hatcher

After strict §6.1 validation, an application may use the complete 64-hex tail
as a local storage key. A legacy identifier may reach that mapping only through
the bounded §6.3 migration path; provisional or abbreviated values must not be
placed in the current namespace. Storage convenience never proves egg
acceptance, identity continuity, or registry authority.

### Why this format

- **Self-location without inferred trust.** Owner and slug identify the initial
  candidate door; §13 establishes which registry state is authoritative.
- **Exact mint domains.** Keyless and keyed identities use the two §6.2
  formulas. Neither an unsigned file nor a matching URL is a trust anchor.
- **Trademark-safe.** "rappid" is claimed in `TRADEMARK.md`. The format is the trademark's canonical expression.

## The species tree

The tree below is an application-lineage illustration, not a trust graph.
Every current identifier must satisfy §6, and every accepted lineage,
succession, or revocation claim must be authenticated through §§10/13.

```
rappid:@<owner>/<root>:<64hex>        ← application root
        │
        ├── (future) rappid:@<fork-publisher>/<name>:<hash>
        │              parent_rappid: <application lineage claim>
        │
        └── rappid:@<publisher>/<organism-slug>:<hash>
                  parent_rappid: <application lineage claim>
                  │
                  └── rappid:@<publisher>/<twin-slug>:<hash>
                            parent_rappid: rappid:@<publisher>/<organism-slug>:<hash>
                            │
                            └── (future) customer organisms, partner AIs, employee twins, etc.
```

RAPP/1 does not infer this tree from unsigned `parent_rappid` fields. Product
lineage may impose one-parent/acyclic rules, but a verifier accepts those
claims only when the applicable signed registry records establish them.

## Digital mitosis — the rappid IS the identity

**Same rappid = same organism. Different rappid = different organism.**

The rappid names identity; copied bytes, a matching URL, or an egg do not by
themselves prove continuity. A verifier also requires applicable integrity,
signature, tombstone, succession, and registry checks. A different valid
mint-once tail is a different identity; any claimed parent/child relationship
requires authenticated registry evidence rather than an unsigned field.

### When a rappid stays the same (same organism, multiple expressions)

These operations preserve the organism's identity. The rappid does not change. The same organism is now expressed in more places.

| Operation | Why it preserves identity |
|---|---|
| **Verified backup and restore** | Reuses the stored tail and keys after integrity and applicable registry checks |
| **Verified egg restored on another device** | The stored tail is reused only after complete §9 verification and applicable §§10/13 checks |
| **Hatching with state preservation** | Target-owned adapters preserve the stored tail; hatching never silently re-mints |
| **Move without identity change** | Reuses the exact stored rappid; current location/authority still resolves through §13 |
| **Provenance-stamped mirroring** | Mirrors serve verified bytes; mirror location alone does not confer authority |

### When a different rappid is minted

A different valid tail is a different identifier. It represents either a new
identity or an authorized continuity transition; an unsigned `parent_rappid`
or `_migrated_from` field cannot decide which.

| Operation | Identity result |
|---|---|
| **Fork plus a fresh §6.2 mint** | A distinct identity; the repository name does not create it |
| **Genesis with a fresh master keypair** | A distinct keyed identity using domain-separated SPKI minting |
| **Rebranding with a fresh permitted mint** | A distinct identity unless signed registry evidence establishes an allowed transition |
| **Authorized §6.3 re-anchor** | A new rappid linked to the old only by the required owner-signed §13 record; compromise also requires a tombstone |

### The identity-minting ceremony

When a product creates a distinct identity, the protocol steps are:

1. Select exactly one permitted §6.2 source: UUIDv4 octets or master-key
   `SPKI_DER`.
2. Compute the full tail with `Hb("rapp/1:rappid", source_bytes)`.
3. Validate the exact lowercase §6.1 owner, slug, and 64-hex grammar.
4. Persist and reuse that tail; never derive it from names or silently re-mint.
5. Publish any genesis, lineage, key, or continuity claims through the
   applicable signed §§10/13 records.
6. For re-anchor, follow only the enumerated §6.3 cases and refuse until the
   required authorization verifies.

The identifier is usable only after required registry and signature checks
verify. No parent, continuity, or authority claim follows from minting alone.

### Why this rule matters

- **Identity is not portable as content alone.** Copying bytes or changing an
  identifier proves neither sameness nor transfer; validators require the
  applicable §6, §10, and §13 evidence.
- **Lineage is verifiable only when signed.** Public timestamps or fields alone
  do not prevent forged ancestry; §§10/13 authorization does.
- **Inheritance does not imply trust.** A child may copy application content,
  but kind and trust bindings come from authenticated registry state.
- **Names do not mint or authorize identity.** Rebranding cannot derive a tail
  or create a trusted parent relationship.

Application lineage can support evolutionary accounting after every identity
and relationship in the walk has been validated. Walking unsigned
`parent_rappid` values is discovery evidence, not verification.

## `parent_rappid` rules

These are product lineage rules, not additions to the §6 grammar:

1. A product may require one parent for every non-root record.
2. It must reject cycles in any lineage it presents.
3. It must not infer continuity, kind, or trust from the parent field.
4. It validates every rappid independently and verifies relationship authority
   through §§10/13.
5. Multiple children may reference one parent only when each claim verifies.

## How a rappid is declared

> **Historical declaration and cryptographic model (superseded).** The
> following examples preserve the pre-rev-5 account. They are not current
> identity records, signature policy, or trust instructions.

<!-- RAPP1-HISTORICAL-SECTION-START -->

### For organisms with a code repo (kernel variants, code-only organisms)

Declare in `rappid.json` at the repo root. Schema: `rapp/1` (ratified canon; formerly `rapp-rappid/2.0`). The `rappid` field carries the consolidated **Eternity** string `rappid:@<owner>/<slug>:<hash>`; `kind` lives in the record.

```json
{
  "schema": "rapp/1",
  "rappid": "rappid:@kody-w/rapp:9a8f0a4b5a710e20f4d819a0f37d2a4c9f113b5e78fb3c29e70b54fff48a38f9",
  "kind": "prototype",
  "parent_rappid": null,
  "parent_repo": null,
  "parent_commit": null,
  "born_at": "2026-05-01T00:00:00Z",
  "name": "rapp",
  "role": "prototype",
  "attestation": null
}
```

### For organisms with cryptographic identity (AI organisms, twins, etc.)

Declare in a signed `root.json` under `blessings/<hash>/` in the home vault:

```json
{
  "alg": "ecdsa-p256",
  "schema": "swarm-estate-record/1.0",
  "kind": "root",
  "rappid": "rappid:@<publisher>/<organism-slug>:144d67...",
  "issued_by": "fp:M:...",
  "issued_by_role": "M",
  "payload": {
    "master_pubkey": "<base64 SPKI>",
    "parent_rappid": "rappid:@kody-w/RAPP:0b6354...",
    "self_signing_pubkey": "...",
    "user_signing_pubkey": "...",
    ...
  },
  "signature": "<ECDSA signature over canonical JSON>"
}
```

Both declarations are valid rappid identity records. The first carries no cryptographic backing; the second does. Verifiers handle both: presence of a `master_pubkey` triggers signature verification; absence means the rappid is treated as conventional / unsigned.

## Cryptographic backing — when and how

Per Constitution Articles XXXIV.7 and XXXVI:

- **The species root** (`rappid:@kody-w/RAPP:0b6354...`) currently has no master keypair. Its rappid is anchored by convention (the existing UUID, dashes-stripped, preserved in the hash field). A future ceremony may mint a master keypair for RAPP itself; until then, the hash field's stability is sufficient.
- **Code variants** (kernel forks) declare their rappid in `rappid.json`. Cryptographic backing is opt-in via the Article XXXIV.7 attestation envelope (signed by parent's release key).
- **AI organisms, twins, customer estates** mint a master keypair via the holocard incantation ceremony. They declare their rappid in a `root.json` signed by the master key. The hash field is `sha256(master_pubkey_SPKI)` (full 256-bit hex).

The same rappid format describes all three cases. The verifier inspects which fields are present and applies the appropriate verification.

## What this replaces / supersedes

Before 2026-04-30, two parallel systems briefly coexisted:

1. **`rapp-rappid/1.1`** (Article XXXIV draft) — rappids in `rappid.json` files at repo roots
2. **`rappid:v2:` cryptographic format** (Swarm Estate Protocol draft) — structured rappids for AI organisms with master keypairs <!-- legacy v2 form: read-forever, never written -->

These were merged on 2026-04-30 into a unified structured format, then **consolidated again on 2026-06-03 into the single Eternity form** `rappid:@<owner>/<slug>:<hash>` (CONSTITUTION Art. XXXIV.1) — `kind` and host moved into the `rappid.json` record, the string stripped to identity + self-locating address. Existing UUIDs (e.g., the species root's `0b635450-...`) are preserved in the hash field (dashes stripped). The schema migrated from `1.1` to `2.0`; legacy `rappid:v2:…` strings are read forever and canonicalized, never re-emitted. **No rappid was lost; every existing rappid has a unique Eternity string.**

<!-- RAPP1-HISTORICAL-SECTION-END -->

## Why one format only

- **No divergence.** Two formats meant tooling, docs, and users had to choose which to use. Choice = bugs. One format eliminates the choice.
- **Unified species tree.** A tree where some nodes are UUIDs and some are structured strings forces traversal logic to handle both. Painful. Bug-prone. One format means traversal is straightforward.
- **Trademark integrity.** "rappid" is a single mark. One canonical format protects the mark.
- **Constitutional ratification.** Article XXXIV (rappid lineage) and Article XXXVI (swarm estate) reference the same format. The constitution declares this is the only format. Future articles may evolve `v2` to `v3`; they will not introduce parallel formats.

## Antipattern: do not split rappid

There is exactly one current rappid grammar. Future protocol evolution follows
RAPP/1 §12 total migration and retirement rather than parallel normal readers.
It may:

- Publish a replacement through the constitutional/spec process.
- Migrate all accepted state and emit only the replacement.
- Register new kinds through the authenticated §13 registry.

It does **not** retain parallel current formats indefinitely. If documentation
teaches two simultaneously current grammars, correct it or label the older one
as bounded migration/history.

RAPP/1 §§6 and 12 govern this invariant.

## Related

- [[The Swarm Estate]] — the cryptographic protocol used by AI organisms with master keypairs (kind: `organism`, `twin`, etc.)
- [[Local-First-by-Design]] — survival model for any rappid (signed records are local-first; hosts are transports)
- [[Decentralized-by-Design]] — full four-layer architecture
- [[Twin-Patterns]] — how one organism runs on N brainstems
- [[The Federated Twin Egg Hatcher Pattern]] — how rappid hash extraction maps to on-disk twin workspaces
- [[The Species DNA Archive — rapp_kernel]] — the kernel's versioned source code archive
- [[Signed Releases and Variant Attestation]] — Article XXXIV.7 cryptographic backing for code variants
- `CONSTITUTION.md` Articles XXXIII (organism), XXXIV (rappid + lineage), XXXV (license stability), XXXVI (swarm estate)
- `TRADEMARK.md` — trademark policy claiming "rappid"

## Provenance

<!-- RAPP1-HISTORICAL-SECTION-START -->

Drafted briefly as a "bridge document" between two formats on 2026-04-30. Rewritten the same evening as the canonical singular spec after the operator clarified that divergence is an antipattern. The species root migrated from raw UUID to v2-format string the same date. Wildhaven AI Homes' parent_rappid updated to reference the v2-format prototype string. All cryptographic signatures re-issued; OpenTimestamps re-anchored.

This is one of the **load-bearing decisions** of the digital-organism era. Once the floodgates open and external variants / customer organisms begin minting their own rappids, this format is what they conform to. Reverting becomes impossible. The decision is taken here, with one format.

<!-- RAPP1-HISTORICAL-SECTION-END -->
