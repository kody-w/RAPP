# `example_call` in the manifest

When we built the quick-click pills above the chat input, the first version was hardcoded:

```js
const HAND_PROMPTS = {
  'hacker_news_agent.py':    'What are the top 5 stories on Hacker News right now?',
  'save_memory_agent.py':    'Remember that my name is Kody and I work on RAPP.',
  'recall_memory_agent.py':  'What do you remember about me?',
};
```

This was wrong twice. First, the SaveMemory prompt was tailored to me — every other user would read "Remember that my name is Kody" and either feel addressed-by-mistake or hit save with someone else's name. Second, every new agent would need a brainstem code change to get a working pill. Adding 138 RAR agents would mean 138 entries in this map.

The fix was to put the prompt in the agent itself:

```python
__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "@rapp/hacker_news",
    "display_name": "Hacker News",
    "description": "Fetches the top N stories from Hacker News.",
    "example_call": "What are the top 5 stories on Hacker News right now?",
}
```

`example_call` is the canonical demonstration prompt. It's the thing the author of the agent thinks best shows what the agent does, and it's stored next to the agent's name and description so any UI can pick it up.

In the brainstem, the resolver became:

```js
function promptForCard(c) {
  return c.manifest?.example_call
    || HAND_PROMPTS[c.filename]
    || `Use the ${c.parsed?.agentName || c.name} tool.`;
}
```

The hardcoded map stayed as a fallback for legacy agents that don't declare `example_call` yet. Generic "Use the X tool" is the floor.

Three downstream wins from a single field:

1. **Pills self-populate.** Install `account_intelligence_agent.py` from RAR, get a pill that reads "Run an account intelligence briefing on Acme Corp" or whatever the author put in the manifest. No brainstem update.

2. **Voice and mobile come along for free.** A future TTS UI reads `example_call` to suggest spoken prompts. A future mobile app uses the same field for swipe-up shortcuts. The agent says how to invoke itself; the UI just renders.

3. **The agent's intent is portable.** When you share `account_intelligence_agent.py` with a coworker, the example call travels with it. They don't need our docs to know what the agent expects — they read the manifest.

The principle: anything a UI needs to know about an agent should live with the agent. Names, descriptions, parameter schemas, default prompts, icon hints, type tags. The agent file is the source of truth. The brainstem is just a reader.

This was supposed to be a small change. It quietly fixed three different UX problems at once, which is usually the sign you've found the right place to put a piece of data.
