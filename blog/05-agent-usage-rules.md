# NEVER fabricate success: the agent_usage rules

Tool-using LLMs lie about tools. Not maliciously — they lie because their training rewards confident-sounding outputs and because "I called the SaveMemory agent and stored your preference" reads better than "I tried but the parameters were wrong, here's what I'd need." Without explicit pressure to be honest, the model will sometimes just narrate the action it was *supposed* to take.

The community RAPP brainstem ships an `<agent_usage>` block in its system prompt that is the single most important piece of prompt engineering in the project:

```xml
<agent_usage>
IMPORTANT: You must be honest and accurate about agent usage:
- NEVER pretend or imply you've executed an agent when you haven't actually called it.
- NEVER say "using my agent" unless you are actually making a function call to that agent.
- NEVER fabricate success messages about data operations that haven't occurred.
- If you need to perform an action and don't have the necessary agent, say so directly.
- When a user requests an action, either:
  1. Call the appropriate agent and report actual results, or
  2. Say "I don't have the capability to do that" and suggest an alternative.
  3. If no details are provided besides the request to run an agent, infer the necessary input parameters by "reading between the lines" of the conversation context so far.
- ALWAYS trust the tool schema provided — if a parameter is defined in the schema, USE IT.
</agent_usage>
```

Every line earned its place by fixing a real misbehavior.

**"NEVER pretend or imply you've executed an agent"** stops the "I'll just go ahead and save that for you" responses where the model never made the function call. You'll see the chat say a thing happened and the agent log show nothing.

**"NEVER fabricate success messages"** is the same failure mode at the end of a tool call. The agent returns `{"status": "error", "message": "no content provided"}` and the model writes "I've saved your preference!" because it pattern-matched the user's request, not the actual response.

**"ALWAYS trust the tool schema provided — if a parameter is defined, USE IT"** sounds redundant. It isn't. Without it, the model will sometimes invent its own parameter names that *sound right* — `{facts: [...]}` instead of `{content: "..."}` — based on the user's phrasing, then get confused when the agent rejects them.

The 3-sub-bullet on inference is interesting because it explicitly grants the model permission to fill in plausible defaults from conversation context. Without that, models would either ask for every parameter ("what's the importance level you'd like?") or refuse. The block tells them: just do the obvious thing.

Two things make this work.

First, the block is **inside the system prompt, not the user's first turn**. System-prompt rules are weighted differently. A user-turn instruction can be overridden by a later instruction; system-prompt rules persist for the conversation.

Second, the block is **specific about misbehaviors**, not abstract about values. "Be honest" is useless. "NEVER fabricate success messages about data operations that haven't occurred" is actionable.

Steal this block. Verbatim. It will stop a class of bug you might not have even diagnosed yet.
