# Why we don't ship a soul.md editor anymore

For a while the brainstem's Settings panel had a `<textarea>` labeled "soul.md (system prompt)" with a hint underneath: *Loaded as the system prompt every turn. SPEC §7.* Users could edit their AI's persona. It felt like the right thing to expose. After all, the OG local brainstem ships a `soul.md` file that you can rewrite to make your AI yours.

We removed the editor. The textarea is gone. The Settings panel doesn't mention soul. Users can't edit the system prompt. And the system prompt itself is now hardcoded in the brainstem JavaScript, pinned to the verbatim text from the community RAPP's `soul.md`.

This sounds like a regression. It isn't. It's the lesson we learned from shipping the editor.

When we had the editor, here's what happened:

1. Most users never opened it. They didn't even know it was there.
2. A few users opened it once, made small edits ("you are a polite assistant"), saved, never came back.
3. A small number of users tried to write more sophisticated prompts and ended up *worse off* than the default — losing the agent_usage rules, breaking the memory injection, accidentally giving the model permission to lie about tool calls.
4. The soul became un-upgradeable. Once a user customized it, our improvements to the default never reached them. The link-stripping bug from the previous post lived in cached souls for users who'd customized.

The textarea was a vector for users to make their experience worse without realizing it.

Removing it isn't a statement that customization is bad. It's a statement that *system prompts are dangerous things to let regular users edit*. The system prompt is the difference between an AI that fabricates tool calls and one that doesn't. Between an AI that strips your formatted output and one that preserves it. Between an AI that follows the agent honesty rules and one that's free to invent.

We removed the editor and made the soul a constant compiled into the brainstem source. Three benefits:

**The two surfaces stay in lockstep.** The local brainstem and the virtual brainstem now share one canonical soul. When the upstream `soul.md` changes, we update the constant in our brainstem JavaScript and re-deploy. Both surfaces get the change at the same time.

**The agent_usage rules can't be lost.** They're hardcoded. No matter how the user has customized other parts of their setup, the model is told to never fabricate, never pretend, always trust the schema. These aren't optional, and they shouldn't be.

**Upgrades reach everyone.** Soul lives in the deployed code. A push to main means every user gets the new soul on their next page load. No migration needed for the prompt itself.

For users who genuinely want a different persona, the answer is the same as it's always been: fork. The brainstem is one HTML file. Open it, change the SOUL constant, host the file. Your fork has your soul. The trade-off is honest: you lose the upstream's prompt improvements, but you gain real customization.

A textarea is a poor surface for editing things where being subtly wrong has real cost. The system prompt is one of those things. Hardcoding it is restrictive in the same way `const PI = 3.14159` is restrictive — it removes a degree of freedom that wasn't actually serving anyone.
