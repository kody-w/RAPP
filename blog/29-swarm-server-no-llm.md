# Why the swarm server doesn't make LLM calls

The swarm server in this repo (`swarm/server.py`, ~300 lines stdlib) hosts deployed swarms behind one endpoint. It loads agents, routes per-tenant memory, executes `perform()` calls, returns JSON. What it doesn't do: any LLM work. No model selection. No system prompt assembly. No chat loop. No OpenAI client, no Copilot bearer, no Anthropic call.

This was a deliberate choice. The brainstem (browser or local) does the LLM. The swarm server is a dumb agent executor.

**The deployment matrix:**

| Layer            | Holds…                                             |
|------------------|----------------------------------------------------|
| Brainstem        | Conversation, system prompt, model creds, chat loop|
| Swarm server     | Agent code, per-tenant memory                      |

The brainstem decides "model needs to call `SaveMemory(content='foo')`." It POSTs `{name: "SaveMemory", args: {content: "foo"}, user_guid: "..."}` to the swarm endpoint. The swarm runs it and returns the output. The brainstem feeds the output back to the model. Loop continues. Same shape as the tether.

**Three reasons it's structured this way:**

**1. Credentials live where the user is.** The user is in their browser when they're chatting; their Copilot bearer was minted by the brainstem during the device-code flow. The bearer is a short-lived token in the browser's localStorage. Putting it on the swarm server would mean copying credentials around — every swarm endpoint would need OAuth setup, secret management, refresh logic. The browser already has all that. Keep it there.

**2. Model selection is a user choice, not a server choice.** A given user might want Claude Sonnet for some chats and GPT-4o for others. The model picker is in the brainstem's header; switching models is a one-click change to a state value. If the swarm server held the LLM, every swarm would be locked to whatever model that swarm was deployed with — or you'd need a "set model" endpoint that's just re-implementing what the brainstem already does.

**3. Swarm endpoints become trivially deployable.** No OAuth, no secret management, no LLM dependency. The local stdlib server is 300 lines. The Azure Functions version of the same wire contract is similarly small. A future Cloudflare Worker version is small. Each implementation is a thin agent executor; none of them needs to know what an LLM is.

**The trade-off:**

You can't curl the swarm endpoint and have a chat with it. You can curl it and execute one agent at a time, but the loop — "model decides which tool to call, calls it, model wraps the result, returns to user" — has to live somewhere. Today that somewhere is exclusively the brainstem.

For a future where you want a swarm to be chat-callable directly (e.g., from Copilot Studio, from Slack, from a phone shortcut), one of two things has to happen:

- **The brainstem becomes a library, not just a UI.** A `rapp-brainstem` Python package that anyone can `pip install` and feed a model + a swarm endpoint, getting a chat loop back. The library does the LLM call, the swarm does agent execution.

- **The swarm server gains a `/chat` endpoint** that takes credentials per-request. `Authorization: Bearer ghu_...` from the caller. The swarm uses that bearer to call Copilot, runs the loop server-side, returns the assistant message. Credentials never persist on the server.

We haven't built either yet. The first is more work but cleaner; the second is faster to ship but expands the swarm server's responsibility surface.

**The principle:**

When you're splitting one thing into two (one LLM, one execution), the natural seam is "where the credentials are." Credentials want to live with the human. Execution wants to live with the data. Following those two pulls gives you most of the architecture for free.

The swarm server doesn't make LLM calls because the LLM credentials don't naturally live there. Everything else falls out of that.
