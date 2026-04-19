# The hand was a UX restriction we didn't realize we'd built

The brainstem has a "hand" of agents above the chat input. Three pills (or holographic cards in card mode), each representing a loaded agent. The metaphor is from card games — you have a *binder* of all your agents, you *play* a few to your *hand* for the current session.

For most of the project's life, the hand was the gating mechanism for what the LLM could call. The chat-loop function `handTools()` returned tools for *only* hand-loaded agents:

```js
function handTools() {
  const out = [];
  for (const f of state.hand) {
    const c = state.binder.cards.find(x => x.filename === f);
    if (!c) continue;
    out.push({
      type: 'function',
      function: {
        name: ...,
        description: ...,
        parameters: ...,
      },
    });
  }
  return out;
}
```

If you had `HackerNews` in your binder but hadn't played it to your hand, the LLM didn't see it. It couldn't call HackerNews. The model would respond "I don't have a tool for that" or worse, fabricate a tool call against an agent it didn't actually have.

This was a bug we didn't realize was a bug because we'd designed it that way.

The community RAPP brainstem doesn't work this way. Its `get_agent_metadata()` returns one tool entry per `*_agent.py` loaded from the agents folder — *every* installed agent is callable. There's no curation step. The model has full access to whatever the user has installed.

We replicated the curation step in the brainstem because it felt right architecturally — "the user picks what's in their hand, then the model can call those." It read like good UX.

In practice it caused this conversation:

- User: *"What's on Hacker News right now?"*
- Brainstem: *"I don't have a HackerNews agent loaded. Want me to do something else?"*
- User: *"What do you mean? It's right there in my binder."*

The user's mental model was "if I installed it, the AI can use it." Our mental model was "if you played it to your hand, the AI can use it." The user's was correct; ours was an extra step that did no work.

**The fix was a one-line change:**

```js
function binderTools() {
  const out = [];
  const seen = new Set();
  for (const c of state.binder.cards) {   // ← state.hand → state.binder.cards
    const p = parseAgentSource(c.source);
    const name = p.name || c.name;
    if (seen.has(name)) continue;
    seen.add(name);
    out.push({type: 'function', function: {name, description: p.description, parameters: p.parameters}});
  }
  return out;
}
```

(Plus a rename — `handTools` → `binderTools` to reflect the new semantic.)

The hand stays. It's still in the UI. It still functions as the quick-click row of starter prompts above the chat input. But it no longer restricts what the LLM can do. The hand is for *human* curation (which prompts are easy to launch); the binder is the LLM's tool surface.

**Two roles, one model wasn't enough:**

The hand had been doing two jobs at once:
1. "These are the agents I want quick-click access to." (Human-facing UX.)
2. "These are the agents the model is allowed to use." (LLM-facing tool list.)

Conflating them seemed natural. They're not the same thing. A user who wants to ask the model about HackerNews shouldn't have to first add HackerNews to their hand — the model has the agent right there in the binder, why is it pretending it doesn't? Conversely, a user might have 50 agents installed; they don't want all 50 as quick-click pills cluttering the chat. The hand is a sane UX constraint; it's a wrong tooling constraint.

Splitting the roles: hand = quick-click prompts (5-10 max, user-curated). Binder = LLM tool surface (everything installed). The model can call anything; the user can shortcut the common ones.

**The principle:**

When you find yourself thinking "this UI affordance also restricts what the system does," ask whether the restriction is intentional or accidental. UI affordances are about helping humans. System restrictions are about correctness, security, or capability. They're different concerns and deserve different mechanisms.

If you're using one mechanism for both, you're probably restricting things the user wishes weren't restricted, or exposing things you wish weren't exposed. Split the concerns. The UI affordance gets a smaller scope; the system surface gets the right scope. Both serve their actual users better.

The fix shipped in commit `293080a`. The model can now call any installed agent. The hand is still there above the chat — but it's UX, not gatekeeping.
