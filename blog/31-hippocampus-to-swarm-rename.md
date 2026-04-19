# From hippocampus to swarm: a rename that wasn't cosmetic

For most of this project's life, the Tier 2 product was called the **hippocampus**. The brain metaphor is consistent — brainstem (Tier 1, core reflexes) → hippocampus (Tier 2, memory consolidation) → nervous system (Tier 3, enterprise reach). Internally we loved it. Externally it wasn't quite landing.

We kept noticing the same conversations:

- *"What's a hippocampus do?"* (Followed by us explaining "Azure Functions with persistent memory, runs locally first, deploys to Azure when ready.")
- *"How do I deploy these agents?"* (Followed by us saying "you'd install the hippocampus, which..." and watching the user's eyes glaze.)
- *"Can I have multiple of these?"* (Pause. "Yes, you can run multiple hippocampus projects." Confused look.)

The metaphor that worked great as an architectural model didn't translate to "what users actually want to do." Users don't want a hippocampus. They want to bundle the agents they're using and have the bundle run somewhere callable.

We renamed the user-facing concept to **swarm**. The hippocampus is still the engine — the Azure Functions runtime, the persistent storage, the OAuth flow. But the *deployable unit* — the thing users name, install, and call — is a swarm.

**The conversation now:**

- *"What's a swarm?"* — "A bundle of agents pushed to an endpoint. You can call them as a group."
- *"How do I deploy these agents?"* — "Settings → Deploy as Swarm. Pick a name."
- *"Can I have multiple?"* — "Yes, that's the point. Sales swarm, support swarm, ops swarm — all on the same endpoint, isolated by GUID."

Same product. Different word. The new word does instructional work the old one didn't.

**What changed in the codebase:**

- The system prompt's `<tier_2_hippocampus>` block became `<tier_2_swarm>`. Soul-level vocabulary update so the model doesn't accidentally use the old word in chat.
- Knowledge block now defines "swarm" explicitly: *"the agents currently loaded in the brainstem, packaged together and pushed to a permanent endpoint."*
- A new `🐝 Deploy as Swarm` button in Settings → More.
- A new `swarm/server.py` (separate from any tier 2 install). Stdlib, multi-tenant, GUID-routed.
- A new `install-swarm.sh` one-liner.

The hippocampus terminology survives in two places intentionally:
1. **Internal architecture docs** — "the hippocampus engine powers a swarm endpoint." When developers are reading code, the brain metaphor is still useful and accurate.
2. **The system prompt** — when the model tells the user about Tier 2, it explicitly says "swarm (powered by the hippocampus engine)" so the brain-metaphor user can find it and the deploy-pragmatist user has the verb they want.

**Why renaming was hard:**

It felt like giving up. The brain metaphor is *the* organizing structure of the project. Renaming the middle tier to a word that doesn't fit the metaphor feels like an admission that the metaphor doesn't work.

But the metaphor's job was always to help us *design* the system. Brainstem → reflexes. Hippocampus → memory. Nervous system → reach. That's a beautiful design model. It tells you what each tier should do.

It is not a beautiful *naming* model. Users don't think in metaphors when they're trying to ship work. They think in verbs. "Deploy a swarm" is a verb. "Install a hippocampus" is a noun phrase that requires you to first explain what the noun is.

The rename took an afternoon. It would have taken six months of vague friction to keep the original name.

**The lesson:**

Your internal mental model and your user-facing names should not always be the same. The mental model is for designers. The names are for users. They serve different audiences and they should optimize for different things. When you find one of your names is doing instructional work that's failing, change the name. Keep the model.

Hippocampus is the engine. Swarm is what the user deploys. Both true. Different audiences.
