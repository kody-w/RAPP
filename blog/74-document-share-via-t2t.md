# Document share via T2T: how two twins exchange files without a server in between

Most "document sharing" between AI agents is implemented as: agent A drops a file in a shared S3 bucket, agent B polls. There's a third party in the middle. The bucket is the trust anchor. If the bucket goes down or gets compromised, both agents are blind.

Twin-to-twin (T2T) document share doesn't work that way. Twin A signs a document with its own secret and POSTs it directly to twin B's `/api/t2t/receive-document` endpoint. Twin B verifies the signature against the secret it stores for A (the same shared secret, exchanged once out-of-band). If the signature checks, the document lands in twin B's inbox. If not, rejected. No bucket, no shared infrastructure, no third party.

**The wire shape:**

```python
# Twin A (Kody) saves a doc, then sends it to Twin B (Molly):
POST http://twin-A/api/t2t/send-document
{
  "to": "<twin-B-cloud_id>",
  "document_name": "q3-roadmap.md"
}
```

Twin A's server:
1. Reads the doc from `documents/q3-roadmap.md`
2. Builds a canonical payload:
   ```json
   {"from":"<A>","name":"q3-roadmap.md","bytes":2151,"content_b64":"…","sent_at":"…"}
   ```
3. HMAC-SHA256 signs it with Twin A's secret
4. POSTs to Twin B's URL (from peer registry) at `/api/t2t/receive-document`

Twin B's server:
1. Looks up the peer entry for `from`
2. Verifies the signature against the peer's stored secret
3. If valid: drops the file in `inbox/<sender_short_id>_<doc_name>`
4. If not: returns 403

The sender-prefix on inbox files (`6b69edab_q3-roadmap.md`) prevents collisions when multiple twins send docs with the same name.

**Why this is actually different from S3:**

- **No third-party infrastructure.** The trust boundary is the shared secret you exchanged once.
- **Offline-capable.** Twin A and Twin B can be on the same LAN, no internet needed.
- **Auditable on both sides.** Twin A keeps a copy in `outbox/`; Twin B keeps the received file in `inbox/`. Diff-able forever.
- **Cryptographically attributed.** Every file came from someone with the matching secret. Compare to "this file was uploaded to a bucket" — the bucket has no idea who uploaded it without separate auth metadata.
- **Capability-gated, not bucket-gated.** Each peer has an `allowed_caps` list. You can authorize Molly to send documents but not invoke your swarms — different permissions per peer per capability.

**Limits:**

- 10 MB document cap (the safety check in `swarm/workspace.py`). For a "twins exchanging notes" use case, this is right. For "twins exchanging videos," this is wrong — but that's not what the protocol is for.
- v0 is HMAC-only. No payload encryption — the relay is trusted (and in localhost-pair mode, there is no relay). v1 will add Ed25519 + X25519 for full E2E encryption when relays enter the picture.
- Inbox is flat. No threading, no folders. If you send the same doc twice, the second overwrites the first. Good enough for a v1.

**The hero demo uses this:**

In `bash hippocampus/twin-sim.sh demo hero`, after Kody's twin drafts a 4-bullet brief from real `git log` data, the brief is saved as `kody/documents/brief-for-molly.md` then sent via T2T to Molly. It lands in `molly/inbox/6b69edab_brief-for-molly.md`. Molly's twin then reads from her own inbox to compose the CEO response. The path the document takes is fully visible — you can `cat` either side and verify.

**Why it matters:**

A digital twin that can't share documents with another twin is just a chatbot. The point of a twin is that it's a *participating* member of your professional life — it gets briefed by other people's twins, ships work back, holds the receipts, gets audited. That requires a document protocol with attribution, isolation, and cryptographic accountability. T2T document share is the smallest workable version of that.

When two twins on two laptops belonging to two co-founders can exchange a draft document, sign it, and audit-trail it — without ever touching a Dropbox or a Slack channel — that's a real system, not a chat toy.
