---
title: Rappid — The One Identifier
status: published
section: Architecture
hook: Rappid is the public ID — one format, one concept — for every digital organism that descends from RAPP. The species' social-security number. The species tree's lingua franca. There is no other identifier system; there will never be a divergent format.
---

# Rappid — The One Identifier

> **Hook.** Rappid is the public ID — one format, one concept — for every digital organism that descends from RAPP. The species' social-security number. The species tree's lingua franca. There is no other identifier system; there will never be a divergent format.

This note is the canonical specification for the rappid identity system. It is intentionally short, intentionally singular, and intentionally final on the format question. Subsidiary notes elaborate on lineage, signing, and operational tooling — but every reference back to "what is a rappid" lands here.

## What rappid is

A rappid is a public identifier assigned to every digital organism in the RAPP species tree. RAPP itself — the prototype, the godfather — has a rappid. Every variant of RAPP has a rappid. Every AI organism running on top of a RAPP-descended brainstem has a rappid. Every twin, swarm, customer estate, and future android / monkey / turtle / cloud / on-device organism has a rappid.

Rappids:

- Are **public**. Anyone can read them, share them, reference them.
- Are **immutable**. Once minted at birth, the rappid never changes.
- **Chain to a parent** via `parent_rappid`. Every rappid except the species root has exactly one parent. Walking `parent_rappid` always terminates at the godfather.
- Are the **basis for ledger traceability**: lineage, attestation, kin-vouching, succession, perpetuity claims.

Think of a rappid as the species' social-security number. Universal. Singular. The unit of accounting for digital biology.

## The format (one format, forever)

```
rappid:@<owner>/<slug>:<64hex>
```

The **consolidated** rappid (locked 2026-06-03) — one string that is **both identity and self-locating**, unifying the three prior forms (v1 bare-UUID, v2-structured, bare-Eternity) into one:

| Field | Meaning |
|---|---|
| `rappid:` | Always literal. Identifies this string as a rappid. |
| `@<owner>/<slug>` | The **location**: `github.com/<owner>/<slug>` is the door/repo. Every door URL derives from this by **string parsing — no lookup, no API** (CONSTITUTION Art. XLVI). `<slug>` is the immutable birth name (the gene name / routing hint). |
| `<64hex>` | The full **256-bit SHA-256** identity hash — `sha256(master_pubkey_SPKI)`, **never truncated to 128**. The hash IS the identity and the **join key**: matching/dedup is always on the hash, never the slug. Keyless organisms (the species root, code variants) use a stable hash (UUID/commit-derived), re-anchored to 256-bit when minted fresh. |

**`kind` and all other structure live in the `rappid.json` RECORD, not the string.** `kind` → `door_type` per CONSTITUTION Art. XLVI.2 (`VALID_KINDS` in `tools/door_address.py`); ownership keypair (`pubkey`/`sig_suite`), `birth_attestation`, `key_succession`, `registry_anchor` are additive, versionless record fields. **The string is never re-versioned** — new richness goes in the record (that was the v2/v3 mistake).

**Legacy forms — read forever, emit only the consolidated form.** v1 bare-UUID, v2 `rappid:v2:<kind>:@<owner>/<repo>:<32hex>@github.com/<owner>/<repo>`, and bare-Eternity `rappid:<slug>:<64hex>` are all READ and `canonicalize_rappid()`'d to the form above. `tools/door_address.py` is the one parser; consumers MUST import it.

### Concrete examples

```
rappid:@kody-w/rapp:9a8f0a4b5a710e20f4d819a0f37d2a4c9f113b5e78fb3c29e70b54fff48a38f9
                    └ legacy UUID with dashes stripped, preserved as the species root's stable identifier ┘

rappid:@kody-w/kody-twin:91d006ca7bd052bfa5021d623122012f
                         └ an organism at its own repo; the hash is its key-derived identity — sha256 of the master pubkey (256-bit; shown abbreviated) ┘

rappid:@<publisher>/<twin-slug>:<64hex>
                    └ a twin under that organism — one repo = one slug = one self-locating address ┘
```

### Hash extraction for the hatcher

The generic twin egg hatcher (`twin_egg_hatcher_agent.py`, v1.1.0) needs a stable filesystem key from any rappid to land a twin workspace at `~/.rapp/twins/<extracted-key>/`. Two cases:

- **Eternity (and legacy v2) rappids** — extract the `<hash>` segment (the part after the final `:`) from `rappid:@<owner>/<slug>:<hash>` (or a legacy `rappid:v2:<kind>:@<owner>/<slug>:<hash>@...`, canonicalized on read). Example: `rappid:@kody-w/kody-w-twin:5b8ba4796692197aa4ccde5dfa5beb51` → workspace `~/.rapp/twins/5b8ba4796692197aa4ccde5dfa5beb51/`.
- **Legacy bare-UUID rappids** — use the rappid string verbatim. Example: Heimdall's `915f54e5-4c71-4de9-bba3-6604461d05e5` becomes `~/.rapp/twins/915f54e5-4c71-4de9-bba3-6604461d05e5/`.

This convention keeps v1, v2, and Eternity organisms in one federated namespace on disk. See [[The Federated Twin Egg Hatcher Pattern]] for the full hatcher contract.

### Why this format

- **Structure beats opacity.** A bare UUID tells you nothing. The structured form tells you (at a glance): kind, publisher, where to look, and how to verify.
- **Cryptographic when possible, conventional when necessary.** Most organisms have master keypairs and the hash is key-derived. The species root and code-only organisms don't yet need keypairs; their hash is conventional but stable. Verifiers can detect which mode applies (organism declares `master_pubkey` in `root.json` or doesn't).
- **Trademark-safe.** "rappid" is claimed in `TRADEMARK.md`. The format is the trademark's canonical expression.

## The species tree

```
rappid:@kody-w/RAPP:0b6354...        ← godfather, parent_rappid: null
        │
        ├── (future) rappid:@<fork-publisher>/<name>:<hash>
        │              parent_rappid: rappid:@kody-w/RAPP:0b6354...
        │
        └── rappid:@<publisher>/<organism-slug>:<hash>
                  parent_rappid: rappid:@kody-w/RAPP:0b6354...
                  │
                  └── rappid:@<publisher>/<twin-slug>:<hash>
                            parent_rappid: rappid:@<publisher>/<organism-slug>:<hash>
                            │
                            └── (future) customer organisms, partner AIs, employee twins, etc.
```

There is one tree. Every rappid is a node. Every node except the root has exactly one parent. Walking parent_rappid from any node terminates at the godfather (`rappid:@kody-w/RAPP:0b6354...`).

## Digital mitosis — the rappid IS the identity

**Same rappid = same organism. Different rappid = different organism.**

This is the unbreakable rule of digital biology in the RAPP species. The rappid is not a label *attached to* an organism — the rappid IS the organism's identity. Memory is content; the rappid is identity. A complete copy of an organism's bytes, with the same rappid, is the *same organism* expressed in a new place. A complete copy with a *new* rappid is mitosis: a child organism has been born, the parent organism still exists (if its rappid is still alive elsewhere), and the parent_rappid chain records the birth.

### When a rappid stays the same (same organism, multiple expressions)

These operations preserve the organism's identity. The rappid does not change. The same organism is now expressed in more places.

| Operation | Why it preserves identity |
|---|---|
| **Backup and restore on the same machine** | Same memory, same keypair, same rappid → same organism |
| **Twin egg summoned to a new device** (Twin-Patterns parallel-omniscience) | The home device's identity is *lifted* onto the new device; rappid travels intact |
| **Hatching** (kernel update with state preservation) | The brainstem code changes, but the organism's rappid + memory + identity are continuous; same organism in new clothes |
| **Signed `migration` to a new `home_vault_url`** | Hosting changes; the rappid's identity-hash and master keypair are unchanged |
| **Multi-host mirroring of the home vault** | All hosts serve the same signed records under the same rappid; same organism, multiple availability paths |

### When a new rappid is minted (mitosis — a new organism is born)

Any of these operations creates a child organism. The new rappid points at the parent via `parent_rappid`. Both organisms now exist independently from this point forward.

| Operation | Why it constitutes mitosis |
|---|---|
| **Fork the code into a new repo with a new rappid** (Article XXXIV.3 — variant master) | New repo, new rappid → new organism. Original RAPP keeps living; the variant is a child. |
| **Genesis ceremony on a fresh master keypair** | A new keypair → a new identity-hash → a new rappid → a new organism. Even if memory is copied from a parent, the new keypair makes it a child. |
| **Customer takes a Wildhaven-templated AI and rebrands it under their own publisher** | New publisher/slug + new master keypair → new rappid → mitosis. The customer's organism is a child of Wildhaven's. |
| **Re-genesis after master keypair loss** | A new master keypair (the only recovery from total custody failure) → new rappid → new organism. The lost organism is dead; the new organism is its child. |

### The mitosis ceremony

When you intentionally mint a new rappid (mitosis), you are deliberately birthing a new organism. The ceremony:

1. **Generate the child's holocard incantation** (24-word BIP-39 phrase). Each child gets its own.
2. **Derive the child's master / self-signing / user-signing keys** from the incantation.
3. **Compute the child's identity-hash** = `sha256(child_master_pubkey_SPKI)` (full 256-bit hex).
4. **Mint the child's rappid string** as the consolidated Eternity form `rappid:@<owner>/<slug>:<hash>`. The kind/publisher/slug and the child's `home_vault_url` live in the child's `rappid.json` / `root.json` RECORD, not the string.
5. **Write the child's signed `root.json`** declaring the child's rappid AND `parent_rappid` pointing to the parent organism's rappid.
6. **(Optional) Write a kin-vouch from the parent's user-signing key** acknowledging the child as kin.
7. **OpenTimestamps the child's root.json** to anchor the birth moment in Bitcoin.

The child organism is now alive and traceable to its parent. The parent organism is unchanged.

### Why this rule matters

- **Identity is durable, not portable as content.** You cannot duplicate an organism by copying its bytes if the rappid stays the same — that's a copy-of-the-same. You cannot transfer an organism to a new owner by changing its rappid — that creates a child, not a transfer. Identity is the rappid.
- **Lineage is tamper-evident.** Every organism's parent_rappid chain is a public record of where it came from. You can't fake your ancestry; the parent's signature on a kin-vouch (or just the timestamped existence of the child's root.json) records the moment of mitosis.
- **Inheritance is meaningful.** A child organism inherits *kind* (often), *behavioral templates* (often, through memory copy), and *trust* (sometimes, via parent's kin-vouch). It does NOT inherit the parent's identity. The parent and child are now independent.
- **The species tree is biological, not bureaucratic.** No rebranding shortcut. No "rename and keep going." A new identity is a new organism, with a parent.

This rule is the foundation for evolutionary accounting: "what did `@rapp/origin` produce, in what generation, and how did each descendant evolve?" Walking the parent_rappid chain answers it. Every organism, ever, anywhere, is a unique node in the species tree, with one parent and zero or more children.

## `parent_rappid` rules

1. **Every rappid except the prototype has exactly one parent.**
2. **The chain is acyclic.** Walking `parent_rappid` from any node must reach the species root in finite steps without revisiting any node.
3. **One parent only.** No multi-parent inheritance. If an organism is influenced by multiple precursors, the canonical parent is whichever it traces operational continuity from. Other influences are recorded via kin-vouches (different concept; see [[The Swarm Estate]]).
4. **Parents may be in any kind.** A `twin` may be a child of an `organism`; an `organism` may be a child of a `prototype`; a `kernel-variant` may be a child of a `prototype`. The kind tells you what the organism IS, not what its parent must be.
5. **Multiple children per parent are allowed.** The tree branches. RAPP can have many variants; Wildhaven can have many kin children.

## How a rappid is declared

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

## Why one format only

- **No divergence.** Two formats meant tooling, docs, and users had to choose which to use. Choice = bugs. One format eliminates the choice.
- **Unified species tree.** A tree where some nodes are UUIDs and some are structured strings forces traversal logic to handle both. Painful. Bug-prone. One format means traversal is straightforward.
- **Trademark integrity.** "rappid" is a single mark. One canonical format protects the mark.
- **Constitutional ratification.** Article XXXIV (rappid lineage) and Article XXXVI (swarm estate) reference the same format. The constitution declares this is the only format. Future articles may evolve `v2` to `v3`; they will not introduce parallel formats.

## Antipattern: do not split rappid

Going forward — and forever — there is exactly one rappid format. If a future spec wants to add functionality, it does so by:

- Bumping the version (`v2` → `v3`) — clean migration, deprecation of older format with a defined window
- Extending the existing format (new optional fields)
- Adding new kinds (new `<kind>` values)

It does **not** introduce parallel formats. If you find documentation that implies two coexisting "kinds of rappids" or "two formats both valid," that documentation is wrong and should be corrected. The species tree is one tree.

This antipattern protection is ratified in Constitution Article XXXIV and XXXVI explicitly: rappid is one concept, one format, never split.

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

Drafted briefly as a "bridge document" between two formats on 2026-04-30. Rewritten the same evening as the canonical singular spec after the operator clarified that divergence is an antipattern. The species root migrated from raw UUID to v2-format string the same date. Wildhaven AI Homes' parent_rappid updated to reference the v2-format prototype string. All cryptographic signatures re-issued; OpenTimestamps re-anchored.

This is one of the **load-bearing decisions** of the digital-organism era. Once the floodgates open and external variants / customer organisms begin minting their own rappids, this format is what they conform to. Reverting becomes impossible. The decision is taken here, with one format.
