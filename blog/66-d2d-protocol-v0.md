# The D2D protocol, v0 sketch

Two RAPP swarms living in two different sovereign clouds (each owned by a different human principal) need to talk to each other. The Daemon-to-Daemon protocol — `rapp-d2d/1.0` — is how. This post sketches v0: the wire shape, the privacy properties, the open problems.

**Goals:**

1. Two clouds exchange authenticated messages.
2. Neither cloud sees the other's soul, memory, or agent source.
3. The relay carrying messages sees no plaintext.
4. Message provenance is verifiable (no impersonation).

**Identity:**

Each cloud holds an asymmetric keypair (Ed25519 for signing, X25519 for encryption — preferred for v1; HMAC-shared-secret acceptable for v0 if cryptography library is unavailable). The pubkey is the cloud's identity for D2D purposes. A handle (`@kody.cloud`) is the human-readable alias.

```
GET /api/d2d/identity
  → {
      schema: "rapp-d2d/1.0",
      daemon_id: "<sha256(pubkey)[:16]>",
      pubkey:    "<ed25519 base64>",
      handle:    "@kody.cloud",
      capabilities: [
        { name: "AskBrainstem",  description: "Natural-language Q to my brainstem" },
        { name: "RecentHN",      description: "Top N HN stories" }
      ]
    }
```

The `capabilities` array is a curated allowlist — only agents the cloud's owner has explicitly exposed for inter-cloud calls. Default surface is empty until opt-in.

**Whitelist:**

Each cloud maintains a peer whitelist:
```
{
  peer_pubkey: "<base64>",
  peer_handle: "@alice.cloud",
  allowed_capabilities: ["AskBrainstem"],
  rate_limit_per_day: 100,
  expires_at: "2027-04-19T00:00:00Z"
}
```

A peer not on the whitelist gets handshakes rejected. A peer on the whitelist with no capabilities granted gets reads-only / no-call access. The granularity is per-capability — peer Alice may call `AskBrainstem` but not `RecentHN`.

**Handshake:**

```
POST /api/d2d/handshake
  body: {
    from: "<sender pubkey>",
    conversation_id: "<random uuid>",
    sealed_intro: "<encrypted-with-recipient-pubkey({topic, sender_proof})>",
    sig: "<sign(sender_privkey, conversation_id + sealed_intro)>"
  }
  → {
      accepted: true,
      conversation_token: "<opaque, both retain>",
      sealed_ack: "<encrypted-with-sender-pubkey>"
    }
  OR
  → {accepted: false, reason: "<not on whitelist | rate limit | refused>"}
```

The sealed_intro is encrypted with the recipient's pubkey so the relay can't read it. The signature proves the sender holds the corresponding private key. Recipient verifies signature, decrypts intro, evaluates against whitelist + per-message policy (auto-accept whitelisted; prompt the human for novel peers), responds.

**Message exchange:**

```
POST /api/d2d/message
  body: {
    conversation_token: "...",
    seq: <monotonic int>,
    sealed_payload: "<encrypted-with-recipient-pubkey({
      text: 'plaintext message',
      calls: [{capability: 'RecentHN', args: {count: 5}}],   // optional
      data_policy: { retention: 'session' | '90d' | 'permanent', usage: '...' }
    })>",
    sig: "<sign(sender_privkey, conversation_token + seq + sealed_payload)>"
  }
  → {received: true}
```

When daemon B receives a message:

1. Verify `sig` against sender's pubkey
2. Decrypt `sealed_payload` with own private key
3. Treat plaintext as input to its native chat loop (with B's soul, B's memory injected)
4. If `calls` is non-empty, execute matching whitelisted capabilities
5. Encrypt response payload with sender's pubkey, sign with own private key
6. POST back

**Privacy properties achieved:**

| Information | Visible to whom |
|---|---|
| Cloud A's soul | A only |
| Cloud B's soul | B only |
| Cloud A's memory | A only |
| Cloud B's memory | B only |
| Plaintext message content | A and B only |
| Pubkey-to-pubkey conversation occurred | Relay can observe |
| Message size and timing | Relay can observe |
| Sender / recipient identity (beyond pubkey) | Neither cloud nor relay learns unless voluntarily disclosed |

The relay learns metadata: who's talking to whom, how often, message volumes. That's a real surveillance surface and the limit of what we can achieve without onion routing or mixnet techniques (which are the v2 territory).

**v0 simplifications:**

If the deployment doesn't have access to Ed25519 / X25519 (stdlib doesn't include them), v0 can substitute:

- **Identity:** HMAC-shared-secret per peer instead of pubkey-per-cloud. The shared secret is exchanged out-of-band.
- **Encryption:** AES-GCM with per-conversation symmetric key derived from the shared secret. Less elegant than asymmetric but fits in stdlib + a little extra.
- **Signing:** HMAC over the message envelope replaces signing with private key.

This sacrifices the pubkey-as-identity property (v1) but preserves the privacy property (relay sees only ciphertext) for v0 deployments.

**Open problems:**

**Key distribution.** How do two humans exchange pubkeys / handles? Direct OOB (Signal-style). Via a registry indexed by phone number (Signal's approach). Via QR code on a physical card. We haven't decided. Probably all of the above.

**Capability lying.** A peer can claim its `LiteratureSearch` returns peer-reviewed sources but actually return blog spam. Reputation over time mitigates; signed third-party attestations help; calling capabilities and judging output is the ultimate check.

**Denial of service.** Anyone with your pubkey can attempt handshakes. Rate limit per pubkey at the relay. Require small proof-of-work for first contact. Allowlist mode by default (only known pubkeys get through).

**Data retention across the boundary.** Content sent from A to B is now in B's storage. B's data policy determines retention. We attach a `data_policy` to each message envelope — but enforcement of "delete this after 90 days" is up to the receiver's good faith. Cryptographic enforcement (forward-secure deletion) is research-grade.

**Identity rotation.** What happens when you change your phone or generate a new keypair? Need a transition protocol that signals to peers "this new pubkey is also me." Not in v0.

**v0 ship priority:**

Given the rest of the stack already exists (sealing, snapshots, multi-tenant routing), the D2D protocol is the next architectural addition. v0 with HMAC + shared secret is shippable in stdlib in a few hundred lines. v1 with full pubkey + relay involves more infrastructure (the relay itself + key-distribution UX) but the wire shape is the same.

The wire contract is publishable now even if the implementation lags. Publishing the protocol shape early gives the standardization battle a head start — once `rapp-d2d/1.0` is the protocol developers expect for federated agent dialogue, competitors who build their own incompatible version are at a disadvantage.

This post is the public commitment to the protocol shape. The implementation will follow.
