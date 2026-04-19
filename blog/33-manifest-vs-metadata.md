# `__manifest__` vs `self.metadata`: two metadata blocks per agent and why

Every RAPP agent declares two metadata structures:

```python
__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "@rapp/hacker_news",
    "version": "1.0.0",
    "display_name": "Hacker News",
    "description": "Fetches the top N stories from Hacker News.",
    "author": "RAPP",
    "tags": ["starter", "news", "http"],
    "category": "integrations",
    "quality_tier": "official",
    "example_call": "What are the top 5 stories on Hacker News right now?",
}

class HackerNewsAgent(BasicAgent):
    def __init__(self):
        self.name = "HackerNews"
        self.metadata = {
            "name": self.name,
            "description": "Fetches the current top stories ...",
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {"type": "integer", "minimum": 1, "maximum": 30},
                },
                "required": [],
            },
        }
        super().__init__(name=self.name, metadata=self.metadata)
```

Two blocks. Two consumers. Two reasons to be there.

**`__manifest__` is module-level.** It can be read without instantiating the class. That matters for surfaces that *list* agents but don't *run* them: the registry build script that walks `agents/` and emits `registry.json`; the brainstem's binder rendering, which mints a card from the source without importing it; the marketplace UI that shows what's available.

The fields are all "what is this agent, who made it, what does it do, what's it for" — registry-level metadata.

**`self.metadata` is instance-level.** It's the OpenAI function-calling tool schema — the structure the LLM consumes to decide whether and how to call the agent. The fields are `name`, `description`, and `parameters` (a JSON schema). Different audience: the model, not the human-facing UI.

Same data exists in both? Yes — `name` and `description` overlap. The duplication is intentional. The manifest's description is for users (in the binder, in the registry browser); the metadata's description is for the LLM (it's the prompt the model reads to decide whether to invoke). They can — and sometimes should — be different. The manifest can say *"Saves a fact, preference, insight, or task to persistent memory."* The metadata might say *"Saves information to persistent memory for future conversations. You MUST call this tool whenever the user asks you to remember something..."* The latter has prompt-engineering instructions the user shouldn't see; the former has marketing copy the LLM doesn't need.

**The `name` field is also slightly different.**

- `__manifest__["name"]` is the *publisher-namespaced* name: `"@rapp/hacker_news"`. Globally unique. Used by registries.
- `self.name` (which `self.metadata["name"]` mirrors) is the *short* name: `"HackerNews"`. The model uses this for tool calls. It's local to the agent's runtime.

Two names, two scopes. The publisher-namespaced one prevents collisions when two libraries both publish a "calendar" agent. The short one keeps the model's tool-calling surface readable.

**What this buys:**

- **The build script doesn't have to import every file.** It can grep out `__manifest__` and skip instantiation. (Important when 138 agents have 138 different dependency trees and you don't want to install them all just to build a registry.)

- **The brainstem can render cards without Pyodide.** Cards come from `__manifest__`. Pyodide is only needed when you actually want to run an agent's `perform()`.

- **The two audiences are addressable separately.** Polish the manifest description for browse-panel readability; tune the metadata description for LLM tool-selection. They evolve independently.

**The cost:**

You have to keep them in sync where they overlap. Most agents do this by writing the manifest first and then either copying the description into `self.metadata` or pointing both at a shared variable. We don't lint for divergence yet; we should.

**The principle:**

When you have one piece of code that two different consumers want to read, give each consumer a separate slot — even if they look 80% the same. The 20% divergence is exactly where you wanted to differentiate; the 80% overlap is fine to maintain. The alternative (one slot, one consumer compromises) usually means both consumers are poorly served.

Two metadata blocks. One file. Two audiences. Both happy.
