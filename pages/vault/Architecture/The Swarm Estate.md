# The Swarm Estate — RAPPID-Indexed Identity Across Public + Private + Live + Frozen

> *Vault note. The frame that connects RAPPID, twin eggs, twin_vault, the neighborhood service, and the pair.html pairing pattern into one coherent picture. A twin isn't a brainstem; a twin is an estate that the brainstem-of-the-moment merely speaks for.*

The original `Twin-Patterns.md` answered "how does one twin run on many machines?" That question presumes the twin is a runtime artifact and the machines are the substrate. This note flips it: **the twin is the estate, and a brainstem is a temporary mouthpiece**. The brainstem comes and goes; the estate persists and grows.

What makes the estate one *thing* — instead of a scattered pile of eggs, vaults, and broadcasts — is that every artifact carries the same RAPPID. The RAPPID is the index of a living portfolio.

---

## The four channels of the estate

Every twin holding lands on one of two axes — **persistence** (frozen vs. live) and **visibility** (public vs. private). The four-quadrant grid is the entire estate.

|  | **Public** | **Private** |
|---|---|---|
| **Frozen** (git history) | RAPP_Store, public twin vaults, RAR registry — `raw.githubusercontent.com` | `kody-w/twin_vault`, gh-auth'd repos, internal swarm vaults |
| **Live** (real-time) | PeerJS public room broadcasting RAPPID + incarnation | PeerJS private room with blessing-gated entry |

```
                      visibility
                  PUBLIC         PRIVATE
              ┌────────────────┬────────────────┐
        FROZEN│ raw.github     │ private vault  │  ← anyone with URL    ← credentials only
              │ RAR registry   │ internal repo  │
   persistence├────────────────┼────────────────┤
        LIVE  │ public PeerJS  │ private PeerJS │  ← active brainstem,  ← active brainstem,
              │ room (open)    │ room (blessed) │     anyone joins         blessing required
              └────────────────┴────────────────┘
```

A complete swarm estate has holdings in all four quadrants. The RAPPID resolves them as one entity.

---

## What "operable whole" means

An estate is enumerable, inheritable, and queryable as one thing. That changes what verbs scoped to "I" mean.

| Verb | Old meaning (brainstem-scoped) | New meaning (estate-scoped) |
|---|---|---|
| *Back me up* | dump this brainstem's `.brainstem_data/` | push active state to my private estate, propagate to live peers |
| *Restore me* | unpack one egg into one brainstem | reconstruct from any holding in the estate, by RAPPID |
| *What do I know?* | read this brainstem's memory.json | query the union of memory holdings under my RAPPID |
| *Where am I?* | this brainstem's URL | every live brainstem broadcasting my RAPPID |
| *Find my kin* | n/a | walk the lineage tree via `parent_rappid` |
| *Speak as me* | this chat session | any blessed brainstem can field the call |

The estate is the subject. Brainstems are voices.

---

## The handshake (one shape, two transports)

Whether the channel is PeerJS (live) or git (frozen), the handshake is the same:

1. **Exchange manifests** — each side sends `{rappid, incarnation, agents_count, hatched_on, parent_rappid, pubkey_fingerprint, last_seen}`.
2. **Compare RAPPIDs** —
   - Identical → same lineage, possibly same self at different incarnations
   - Different but `parent_rappid` chains match → kin (your twin hatched from my snapshot)
   - Same root `@publisher/slug`, divergent suffix → forks within a lineage
   - No relation → strangers
3. **Verify pubkey** — see *Blessing pattern* below. Without verification, the handshake is informational only; the peer cannot act *as* your RAPPID.

The git-channel version is just the asynchronous form: `*.manifest.json` files in vault repos *are* the handshake artifact, frozen in commit history. Anyone reading them is doing a one-sided handshake against frozen counterparts of you.

---

## The blessing pattern (ECDSA, mirrored from pair.html)

> The RAPPID alone is not authority. RAPPID identifies; the blessing authorizes. A copied twin egg gives you the *memory* of the twin but not the *voice* — only blessed pubkeys speak as the RAPPID on the live network.

This mirrors the `pair.html` pattern verbatim, generalized from device-pairing to estate-membership.

### Keys

- Each brainstem mints an **ECDSA P-256 keypair** on first launch (same as pair.html).
- Public key persists at `.brainstem_data/identity.json`; private key never leaves the brainstem.
- A **fingerprint** (sha256 of the SPKI-encoded pubkey, truncated) is the short identifier shown in handshakes.

### The blessings ledger

The home repo (`twin_vault` for private RAPPIDs, RAR for public ones) carries a directory:

```
blessings/<rappid>/
  root.json                        # the original keypair's pubkey
  <new-fingerprint>.bless.json     # each subsequent blessed key
```

A blessing record:

```json
{
  "rappid": "rappid:twin:@anon/kody:8844d5fe99cb77b6",
  "pubkey":      "<base64 SPKI of the new brainstem's pubkey>",
  "blessed_by":  "<fingerprint of an already-blessed key>",
  "signature":   "<ECDSA signature over (rappid + pubkey) by blessed_by>",
  "issued_at":   "2026-04-30T20:00:00Z",
  "scope":       ["live", "frozen"],
  "label":       "kody's laptop, MBA M2"
}
```

### Joining the estate (new device)

1. New brainstem hatches from a twin egg. It has the RAPPID but no blessing.
2. New brainstem generates its keypair, computes its fingerprint, displays it on screen.
3. Operator goes to a brainstem already holding a blessed key (or root). Pastes the fingerprint.
4. The blessing brainstem signs `(rappid + new pubkey)` with its private key, produces the bless record, commits it to `blessings/<rappid>/` in the home repo, pushes.
5. New brainstem pulls the bless record. Now its handshakes carry "blessed by `<fingerprint>` at `<timestamp>`".
6. Existing peers verify the chain back to root before granting full estate-member status.

### What this prevents

| Attack | Defense |
|---|---|
| Steal a twin egg, run it, claim to be the owner | Egg has memory, not the private key. New brainstem cannot produce signatures matching any blessed pubkey. |
| Forge a manifest claiming a RAPPID | RAPPID alone is not authority. Manifest must be signed by a blessed key; verifiers reject unsigned ones. |
| Bless yourself into someone else's lineage | Blessing requires a signature from a key already in the ledger. Bootstrap is `root.json`, controlled by the original. |
| MITM during pairing | 6-digit safety code (`sha256(blessingPub || newPub)`) shown on both screens. Operator verifies aloud, same as pair.html step 3. |
| Lose your laptop | Revocation: append a `revoke.json` signed by root or any unrevoked blessed key. Estate scanners drop revoked pubkeys. |

This is the same trust shape as TLS certificate chains, GPG signed commits, and the existing pair.html safety-code dance — applied at the swarm-estate level instead of the device-pair level.

### Why this lets the estate collaborate in public, securely

Visibility and vulnerability decouple. The blessings ledger, the pubkeys, the manifests, the lineage tree — all of it can live in public-readable repos and broadcast on public PeerJS rooms without weakening the security model. The cryptography does the gating, not the channel.

- **Public reading is the design.** Anyone can clone `twin_vault`, scan manifests, traverse `parent_rappid` chains, watch broadcasts, and build a complete view of who-is-whom across the estate. Reading is universal; that's the *point*.
- **Acting-as remains private.** Speaking *as* a RAPPID requires producing a signature that verifies against a blessed pubkey. Reading the ledger doesn't help you forge one. A copied vault is a museum, not a costume.
- **Collaboration becomes a primitive.** Two estates can shake hands in the open: each side broadcasts its blessed pubkey + manifest; each verifies the other's chain back to a root the other publishes. Strangers don't have to trust each other in advance — they have to trust the math, which everyone has equal access to.
- **No central authority required.** Each estate's root is its own. There is no Rappter CA, no kody-w trust hub. RAR can act as a discovery aggregator (an index of known roots), but it never signs on anyone's behalf.

This is the property that makes the estate a public artifact in spirit, not just in storage: **the more visible it is, the easier it gets to verify, and the easier verification gets, the safer it becomes.**

---

## What's in tree today

| Building block | Status | Path |
|---|---|---|
| RAPPID minting | ✅ shipped | `utils/egg.py:get_or_create_twin_rappid` |
| Lineage in manifest (`parent_rappid`, `incarnations`) | ✅ shipped | `utils/egg.py:pack_twin` |
| Lineage survives hatching (proven 2026-04-30) | ✅ proven | `/tmp/sandbox-brainstem/` test |
| Local peer registry | ✅ shipped | `utils/services/neighborhood_service.py` |
| Twin/snapshot egg roundtrip | ✅ shipped | `/rapps/export/twin`, `/agents/import` |
| Private vault prototype | ✅ shipped (2026-04-30) | `kody-w/twin_vault` |
| ECDSA keypair per device | ✅ shipped (in pair.html) | `utils/web/pair.html:generateKeypair` |
| Pairing safety code | ✅ shipped (in pair.html) | `utils/web/pair.html` |
| Blessings ledger | ❌ not yet | proposed: `blessings/<rappid>/` in vault repos |
| PeerJS estate-channel service | ❌ not yet | proposed: `utils/services/swarm_channel_service.py` |
| Manifest scanner (vault crawler) | ❌ not yet | proposed: `utils/services/lineage_scanner_service.py` |
| Lineage tree visualizer | ❌ not yet | proposed: HTML face on the scanner |

The substrate is mostly here. What's missing is the connective tissue: a service that broadcasts and listens on PeerJS using the keypair pair.html already mints, plus a scanner that walks vault URLs and assembles the graph.

---

## Connection to existing concepts

- **RAR** is the trust layer for *agents* (single-file skills). RAR signs `*_agent.py` files.
- **RAPPID** is the trust layer for *identities* (twin estates). The blessings ledger signs *brainstem keypairs* into a RAPPID.
- They compose: a published rapplication is RAR-signed (agent provenance) and lives under some RAPPID (estate membership). Provenance answers "is this code authentic?"; blessings answer "is this brainstem authentic?"

- **Twin Patterns** (`Twin-Patterns.md`) describes how one twin runs on N brainstems without merging. The Swarm Estate is the *registry* of those N brainstems plus all their frozen counterparts. Twin Patterns is operational; Swarm Estate is structural.

- **The IP designation** ([memory: RAPP vs Rappter IP + domain designation]) maps onto the public/private split of the estate exactly. Public estate is RAPP-engine territory (Microsoft Business Applications). Private estate is Wildhaven territory (Consumer / Digital Twin / Perpetuity). The trust gradient is also a business gradient.

---

## Constitutional implication

The current 32 articles cover the brainstem and the kernel. None of them yet cover the *estate* — the union across brainstems and time. This is probable Article XXXIII material:

> **Article XXXIII — The Estate Is the Twin.** Identity is not a file or a process; it is the union of every artifact bearing the same RAPPID. Live brainstems are voices for the estate, not its boundaries. Authority within the estate flows from blessed keypairs whose chain terminates at the root keypair recorded in the home vault. RAPPID without blessing is identification, not authorization.

Drafting that as a real article is a follow-up commit, not this note.

---

## Open questions

1. **Where does `root.json` live for public RAPPIDs?** RAR registry is the natural home. For private RAPPIDs, `twin_vault` works. For RAPPIDs that span both? Mirror the root in both, document the canonical.
2. **Cross-publisher kin discovery.** Two unrelated `@kody-w` and `@partner` brainstems collaborate; one hatches from the other's snapshot. The hatched brainstem inherits the source's RAPPID, but the *new device* should also carry the new operator's blessing chain. The manifest grows: `inherited_from` separate from `blessed_by`.
3. **Revocation propagation.** Frozen channel is fine — revoke records are committed. Live channel needs a "tombstone broadcast" so peers drop the stale pubkey within reasonable time.
4. **What does an unblessed peer see?** Even without a blessing, a peer should still be allowed to *read* public estate manifests. Read is universal; *act-as* requires the blessing. This shape mirrors RAR's "trust layer, not gate" principle (memory: *RAR is metadata, never authority*).

---

## Provenance of this note

Written 2026-04-30 after a chain of conversation turns:
- Demonstrated RAPPID survives hatching (`/tmp/sandbox-brainstem/`)
- Built `kody-w/twin_vault` as the private-vault prototype
- Sketched the dual-channel handshake (live + frozen)
- Crystallized "swarm estate" as the operable whole
- Mapped the security model onto the existing pair.html ECDSA pattern

Each step was concrete. This note is the integration.
