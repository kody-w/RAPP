# Swarms calling swarms: composition with consent

[Post #52](./52-swarms-calling-swarms.md) introduced the idea of swarms invoking other swarms' agents. This post extends that into a concrete protocol: how cross-swarm capability invocation works on the wire, with consent enforced and identity preserved at every hop.

**The shape:**

A swarm in cloud A wants to invoke a capability exposed by a swarm in cloud B. The invocation rides over the D2D protocol (post #66) as a special message type:

```json
{
  "conversation_token": "...",
  "seq": 17,
  "sealed_payload": "<encrypted-with-B-pubkey({
    type: 'capability_invocation',
    target_swarm: '<swarm_guid_in_B>',
    capability: 'AskBrainstem',
    args: { question: '...' },
    invocation_id: '<uuid for tracking>',
    consent_token: '<see below>'
  })>",
  "sig": "<sign(A-privkey, ...)>"
}
```

When B receives this:

1. Verify signature against A's pubkey
2. Decrypt payload
3. Check that A is whitelisted for `target_swarm` and `capability` (post #66 whitelist)
4. Check `consent_token` validity (see below)
5. Execute capability against B's swarm
6. Return result over the same D2D protocol channel

**The consent_token mechanism:**

Cross-swarm calls happen on behalf of someone. When A invokes "B.AskBrainstem('what's your weather forecast?')" — who's that "asking" question for?

Three cases:
- **Cloud A's owner directly** — they typed something into their brainstem that triggered a tool call to A's CalendarAgent, which triggered a sub-call to B's AskBrainstem. Owner of A is the principal; owner of A consented to A's calls.
- **A peer of cloud A** — peer C's cloud is talking to A. A's response involves a sub-call to B. Now we have two principals: peer C (the asker) and owner A (the relayer). B needs to know.
- **Automated workflow** — a scheduled or webhook-triggered swarm in A makes the call. No human in the loop right now; A's owner pre-authorized this kind of invocation.

The `consent_token` encodes which case applies. It's a structured object signed by A's private key:

```json
{
  "consent_type": "owner_direct" | "peer_relayed" | "preauthorized",
  "principal_pubkey": "<who's responsible for this call>",
  "issued_at": "<iso timestamp>",
  "expires_at": "<iso timestamp>",
  "scope": ["capability_name"],
  "signature": "<sign(A-privkey, ...)>"
}
```

B's policy can require certain consent types. Maybe B's owner says "only accept calls from peers I've directly whitelisted, never relayed calls from peers-of-peers." That's enforceable: B checks `consent_type === 'owner_direct'` or `principal_pubkey ∈ B's whitelist`.

**Why this matters:**

Without consent_token, you have a transitive-trust problem. Alice trusts Bob; Bob trusts Carol; Alice's data could leak to Carol via Bob's relayed calls without Alice ever consenting. The token makes the chain explicit. Each cloud sees who *originally* requested the call, not just who passed it along, and can refuse based on that.

This is the same problem OAuth scopes solve for traditional API access — explicit authorization for each capability. We're applying it to AI capability invocation across federated agent clouds.

**Composition orchestrator pattern:**

The most powerful use case is an *orchestrator swarm* — a swarm whose entire job is to compose other swarms' capabilities into one coherent answer.

```
User → Orchestrator swarm in cloud A
        |
        +----> A's local swarms (sales, research, ...)
        |
        +----> B's swarm (specialized analysis)  via D2D
        |
        +----> C's swarm (data lookup)            via D2D
        |
        ↓
        Synthesized response
```

The orchestrator coordinates. The user sees one answer. Underneath, three clouds contributed. Each contribution is auditable via consent_tokens — the user can ask "show me what was queried where on my behalf."

**Per-call data policy:**

Each cross-swarm message carries a `data_policy` field (post #66):

```json
"data_policy": {
  "retention": "session" | "90d" | "permanent",
  "usage": "this_call_only" | "memory_eligible",
  "revocable": true
}
```

A's call to B with `retention: session` tells B: "use the contents of this call for this response, don't store it." B's adherence is good faith but the signal is explicit. Compliant peers honor it; hostile peers can't be forced, but at least the convention is published.

**Why publish the protocol now:**

Post #58 ("open the bones, close the body") covers the why. Capability invocation across federated AI systems is a category that doesn't have a standard yet. By publishing `rapp-d2d/1.0` with capability invocation in the spec, we set the shape. Other implementations adopt it (interop wins) or build their own (lose the standardization battle).

Worth noting: the spec is published; the implementation is partial. We have the wire shape designed but only the basic message-passing is implemented in code. Full capability invocation with consent tokens is in the v0.2 backlog. Publishing the spec early is intentional — commits us, signals intent, invites scrutiny while there's still time to refine.

**Open problems (carry over from post #66):**

- **Capability lying.** B claims `LiteratureSearch` returns peer-reviewed; actually returns blog spam. Reputation, signed third-party attestations, calling-and-judging are the mitigations.
- **Pricing for cross-swarm calls.** Should B charge A for invoking B's capabilities? Almost certainly yes for institutional / professional cases. Stripe-style metered billing on top of the protocol; outside the protocol's scope.
- **Async / streaming responses.** Some capability calls take seconds (LLM responses). The protocol needs to support asynchronous completion — initial ack, eventual response. Not in v0.

**The lesson:**

Federated AI systems are coming. The first protocol that combines (a) cryptographic identity, (b) granular capability whitelisting, (c) explicit per-call consent, (d) data-policy envelopes, (e) cross-cloud composition with audit trails — wins the standardization race. We're trying to be that protocol.

The shape is publishable now. Implementation follows the spec, not the other way around.
