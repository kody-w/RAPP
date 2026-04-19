# Phone-anchored sovereign clouds: the federation pattern

Federated systems have an identity problem. To talk to your peers, you need to know which peers you trust. Public-key cryptography solves the *trust* part — verify a signature, you know who sent it. But pubkeys are unmemorable. You can't tell your mother her cloud's pubkey at brunch. The federation pattern needs a usable identity layer on top of the cryptographic one.

Mastodon used `@user@instance` handles. Bluesky uses domain-as-handle. Signal, WhatsApp, Telegram all converged on phone numbers. The phone number works because it's something humans already exchange and verify, with infrastructure (SMS) reaching every adult on Earth.

The **phone-anchored sovereign cloud** pattern combines:

- **Phone number** as the human identity primitive (verified via SMS at registration).
- **Sovereign cloud** as the per-human compute substrate (their multi-tenant agent host).
- **Handle** as the public-facing identifier (independent of the phone number, not exposed to peers).
- **Pubkey** as the cryptographic identity for inter-cloud authentication (derived or registered at install).

A human registers their phone, gets a cloud. The cloud has a handle (`@kody.cloud`) and a pubkey (`ed25519:abc123...`). To peer with another human's cloud, you exchange handles via any human channel (text, in person, email). The cloud-to-cloud crypto handles the trust verification under the hood.

**Why phone-anchored:**

1. **Universal.** Every adult has a phone number. Onboarding is "what's your number?" — the lowest-friction identity question that exists.
2. **Already-trusted infrastructure.** SMS verification has been the standard for high-trust account onboarding for over a decade. Familiar. Tested.
3. **One-to-one with humans.** Phone numbers are personal in a way email addresses aren't (which can be shared accounts, role accounts, work-vs-personal). Phone-as-identity gets you closer to "this is a unique human."
4. **Existing key-distribution problem solved.** "Add @alice.cloud as a peer" → behind the scenes, cloud queries "who controls handle @alice.cloud?" → returns Alice's pubkey from a registry indexed by hashed phone number. Bound to Alice's actual control of her phone.

**Why sovereign cloud:**

1. **Single ownership boundary.** "My cloud" is unambiguous. Inside it, my rules; outside, I negotiate. Federation works human-to-human, not user-to-user-of-shared-platform.
2. **Heterogeneous internal organization.** Inside one cloud you might have many swarms — sales swarm, support swarm, family swarm. The sovereign boundary is the cloud; granular structure is the owner's prerogative.
3. **Migration unit.** When you change phones / providers / hosting, you migrate one cloud (with N swarms inside). Atomic.
4. **Inheritance unit.** Your cloud is what your descendants inherit. Multi-generational governance attaches to the cloud.

**Why handle (separate from phone):**

The phone number is *for authentication*, not for *identification*. You don't want to publish your phone number to peer with someone — privacy, spam, surveillance. The handle is the public-facing identifier.

```
@kody.cloud           — what others see and reference
phone hash            — what the registry indexes by (private)
ed25519:abc...       — what the cryptography uses (technical)
```

Three identifiers, three roles. The handle is human-friendly and shareable. The phone hash is the registry key (allowing the registry to verify ownership without exposing the phone). The pubkey is the cryptographic substrate.

**Why pubkey (separate from phone):**

Phone numbers can be SIM-swapped. An attacker convinces the carrier to port the number to their device. Suddenly they can pass SMS verification as you. If the phone IS the only authentication primitive, the SIM-swap attacker takes everything.

Layering a device-resident pubkey on top defends:
- Phone proves "you're the human."
- Pubkey proves "you're the human from the original device."
- High-trust operations (whitelist amendments, sealing, endowment changes) require BOTH.
- Low-trust operations (continue an existing chat) require only phone.

Same pattern Signal uses. Works.

**The federation graph:**

```
   @kody.cloud                  @alice.cloud
       |                            |
       +---------- D2D --------------+
       |                            |
   @molly.cloud                @bob.cloud
       |                            |
       +---------- D2D --------------+
```

Each `@x.cloud` is a sovereign cloud bound to a phone-verified human. Edges are mutual whitelists (D2D protocol, see post #66). The graph is a friend-of-friend network — your cloud talks to clouds you've authorized; transitivity isn't automatic.

**Comparison to existing federation patterns:**

| | Mastodon | Bluesky | Signal | RAPP |
|---|---|---|---|---|
| Identity primitive | `@user@instance` | Domain | Phone | Phone |
| Sovereignty unit | User account on a server | DID | Account | Cloud |
| Cryptographic identity | Server-managed | DID-managed | Per-device key | Per-cloud key |
| Multi-asset per identity | One account = one stream | One identity = one feed | One account = messages | One cloud = many swarms |
| Inheritance | Account dies with user | Same | Same | Cloud persists past user |

RAPP is unusual in two dimensions:
- Multi-asset per identity (many swarms inside one cloud)
- Inheritance (cloud outlives the human via sealing + endowment)

The phone-anchored federation pattern adapts to support these — phone authenticates, cloud holds the multi-asset state, sealing transitions the cloud to immutable state, inheritance protocols govern post-mortem.

**The lesson:**

When you're building a federated system that needs human-grade identity, look at what messaging apps converged on. The convergence is not coincidence — phone-as-identity is the lowest-friction usable identity primitive available today. Layer cryptographic identity (pubkeys) on top for technical reasons; layer human-readable handles on top for product reasons. Three identifiers, distinct roles, all complementary.

The phone-anchored sovereign cloud pattern is what we're building toward for RAPP. Not done yet — the relay (post #49) and the D2D protocol (post #66) are the next implementation steps. But the architecture is settled, and publishing it here commits us to it.

If you're building anything federated, copy this. The work has been done; the pattern is reusable.
