# Patent-pending in build-in-public: how we say what we have without giving it away

Build-in-public and patent strategy are usually in tension. Build-in-public says "share everything" — architecture, decisions, postmortems, code. Patent strategy says "disclose nothing publicly until the priority date is locked, otherwise prior art exists and you lose."

Reconciling them requires being precise about what's *patentable* and what's *publishable*. Most build-in-public content isn't patentable anyway. Most patentable inventions don't need to be the public-facing content. The question is the boundary between them.

**What's typically NOT patentable (so safe to publish):**

- **Architectural patterns** that have prior art (multi-tenant routing, env-var configuration, OAuth flows). The general patterns aren't novel; specific applications might be.
- **Postmortems and bug stories.** A bug fix isn't a patent.
- **CSS specificity adventures.** Very much not.
- **Build-tool decisions.** "We chose stdlib over Flask because…" — process, not invention.
- **Wire-protocol specs you intentionally want to standardize.** Protocols you publish AS standards aren't claimable as your private IP afterward — but you may not WANT to claim them as private IP if your goal is interop.
- **Engineering philosophy posts.** "Single-file agents are the contract because…" — opinion, not invention.

These constitute about 90% of the content we've published in this blog series (52 posts at the time of this writing, plus the new batch). All publicly available; none undermines a patent strategy because none of it is patentable as standalone subject matter.

**What IS patentable (and shouldn't be publicly disclosed pre-filing):**

- **Novel integrated systems** that combine multiple known components in non-obvious ways to solve a specific problem. The integrated combination is the invention.
- **Specific algorithms** with non-obvious technical merit (rare in product engineering; common in research).
- **Specific data structures** that are novel and useful (also rare).
- **Specific user-experience workflows** that combine UI patterns in novel ways for a specific outcome (occasionally patentable; depends on jurisdiction).

For us, the patentable invention is the **integrated combination of phone-verified sovereign agent cloud + GUID-routed multi-tenancy + immutable sealing + endowment-funded perpetual operation + cryptographic inter-cloud privacy + multi-generational inheritance governance for perpetual digital preservation of a human principal**. The combination is the invention. Each individual element is prior art.

**The discipline pre-filing:**

Until the provisional is filed, the integrated combination shouldn't be described publicly as one assembly. You can publish posts about *individual elements* that are prior art anyway. You can publish posts about *adjacent ideas* (relay design, capability invocation) that don't reveal the combination's novelty. You can NOT publish a post that says "here's our complete integrated system that combines phone verification, GUID routing, sealing, endowment funding, federated privacy, and multi-generational governance to perpetually preserve humans" — that's the patent, disclosing it pre-filing creates prior art against your own application.

We were careful about this. Posts pre-patent-filing covered:

- Sealing (a primitive, not the integrated system) — post #53
- Snapshot semantics (a primitive) — post #54
- Wire-contract methodology — post #70
- HTTP 423 status code — post #56

None of those discloses the integrated combination. Posts that DO discuss the integrated combination — this one, the relay-design post, swarms-calling-swarms — were drafted but only published after the patent was filed (or are publishing now, with patent-pending status established).

**Post-filing: "Patent Pending" as positioning:**

Once the provisional is filed, "Patent Pending" is a defensible label you can use everywhere. It signals:

- **Priority date is locked.** Anyone copying you has a defensible claim against them.
- **You're committed enough to pay for protection.** Signals the team takes the IP seriously.
- **You have IP to license.** Future strategic partners know there's a thing to license, not just code to fork.

"Patent Pending" doesn't entitle you to sue (you can't enforce a provisional). But it deters casual copying because the threat of an issued patent in 2-3 years is real, and most copycats won't take the risk.

**The build-in-public posts after filing:**

After the provisional, the discipline relaxes. You can publish:

- Architecture posts about the system. The patent's prior-art protection is established.
- Detailed implementation posts. The implementation can be public; the patent claims the system, not necessarily the specific implementation.
- Comparison posts. "Here's how we do X vs. how others might do X." Useful marketing.

You still don't publish:

- The full provisional disclosure verbatim (still in a private repo).
- Specific business strategy (pricing, sales playbooks, conversion rates).
- Customer-identifying information without explicit consent.
- Internal financial models.

The boundary moves; build-in-public expands. But the strategic moat (brand, customer relationships, operational excellence, business model) stays private.

**What "Patent Pending" lets you say differently:**

Before filing:
> *"We've built a system that combines several capabilities in a novel way."*

After filing:
> *"Patent pending on our integrated digital twin preservation system, which combines phone-verified sovereign agent clouds with sealing, endowment funding, cross-cloud privacy, and multi-generational governance to provide perpetual digital preservation of a human principal."*

You can describe the invention. You can teach how it works. You can explain why the combination is novel. Because the priority date is locked, you can talk about the integrated system without creating prior art against yourself.

This is when build-in-public becomes maximally useful: substantive content about the actual invention, branded with patent-pending status, building authority and category-defining position.

**The lesson:**

Build-in-public and patent strategy aren't fundamentally in conflict. They're sequenced. Pre-filing, publish the parts that aren't patentable (most of your content) and reserve the integrated-system descriptions for post-filing. After filing, expand the public content to include the system itself, branded with patent-pending status that legitimizes both the IP claim and the build-in-public posture.

The mistake to avoid: publishing the integrated system pre-filing. The cost is the loss of the priority date and potentially the patent itself. The cost of a few weeks' delay between writing a post and publishing it is negligible by comparison.

For us: provisional filed, integrated-system posts now publishing, build-in-public continues at full speed. The architecture is documented openly; the invention is patent-pending; the moat (brand, customer relationships, operational layer) stays private.

Both bets pay off. They're complementary, not opposed.
