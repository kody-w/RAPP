# The single-file agent contract

Every agent framework I've used wants you to commit to its world. Decorators, base classes, lifecycle hooks, dependency injection. You learn the framework, you write to its grammar, and the moment you want to share an agent with someone outside that ecosystem you have to extract it from the framework's gravity.

RAPP agents are one Python file. That's the contract.

```python
from agents.basic_agent import BasicAgent

__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "@rapp/hacker_news",
    "display_name": "Hacker News",
    "description": "Fetches the top N stories from Hacker News.",
    "example_call": "What are the top 5 stories on Hacker News right now?",
}

class HackerNewsAgent(BasicAgent):
    def __init__(self):
        self.name = "HackerNews"
        self.metadata = { "name": self.name, "description": "...",
                          "parameters": { ... } }
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        ...
        return json.dumps({ "status": "success", "summary": "..." })
```

Three pieces:
- `__manifest__` — what other RAPP surfaces (registries, browsers, cards) read about this agent without instantiating it.
- A class extending `BasicAgent` with a `name` and a `metadata` (OpenAI function-calling schema).
- A `perform(**kwargs)` method that does the work and returns a string (or JSON-serialized envelope).

That's it. No registration. No build step. Drop the file into `agents/`, and the brainstem hot-loads it on next request.

The contract works in three different runtimes without changes:
- The local Python brainstem (Flask, port 7071) imports it directly.
- The virtual brainstem in the browser parses it with a JS parser, mints a card, and runs `perform()` in Pyodide.
- The tether server (`tether/server.py`, stdlib-only) loads it the same way the local brainstem does.

The same file is portable across all three because the contract doesn't depend on any of them. The `BasicAgent` base class is six lines. The `__manifest__` is ordinary Python with no decorators. `perform()` is a method that returns a string.

Why does this matter? Because the *unit of distribution* is the file, not the framework. You can paste an agent into a Slack DM. You can email it. You can git-clone it. You can drag-drop it onto a webpage. There's no `npm install`, no `pip install <our-thing>`, no virtualenv to set up before someone can read your code and decide whether to run it.

The smallest unit of agent-shaped intent that can plausibly be moved between humans is one Python file. Anything bigger is a framework asking you to adopt it; anything smaller can't carry its own metadata. We picked the smallest workable thing and stopped there.
