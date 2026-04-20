# RAPP Roadmap

Post-v1 directions. The v1 contract ([SPEC.md](./SPEC.md)) is frozen. Every
item here must honor it: **one file per agent**, data sloshing is the wire,
no frameworks.

---

## Digital Twin Buddy — an agent.py that fires every turn

**Status:** proposed · **Shape:** single-file agent · **Surface:** brainstem side panel

A persistent companion rendered next to the main chat, reacting in real time
to the last call + response. Think Claude Code's side-panel buddy — but
instead of a generic helper, it's *your digital twin* watching the
conversation with you, offering hints, highlighting risks, and surfacing what
you'd say next if you were watching someone else have the conversation.

### The shape

One file: `rapp_brainstem/agents/digital_twin_agent.py` — a regular RAPP
single-file agent honoring the v1 contract. The only non-ordinary thing
about it is **when** it runs, not **what** it is.

### Trigger (the only new primitive)

Today: agents fire inside the tool-calling loop, invoked by the LLM.

Added: a **turn-post hook** — after the brainstem returns a response to the
user, it invokes the twin agent **in parallel**, outside the chat thread,
passing the turn's state via data_slush. The user doesn't wait for the
twin; the twin's output streams into the side panel asynchronously.

```
user → brainstem → response (renders in main chat)
                ↘
                 twin agent (parallel, data_slush-fed) → side panel
```

One hook. One agent. Zero new concepts besides the hook itself.

### Input — data_slush is the wire

The twin **only** sees what the hook passes it. No hidden access, no
separate context store:

```python
{
  "user_input":     "<last user turn>",
  "assistant_text": "<last assistant text>",
  "tool_calls":     [{...}],       # what agents the main loop fired
  "agent_logs":     [{...}],       # and what they returned
  "soul":           "<current soul.md>",
  "binder":         [{...}],       # installed rapplications
  "prev_twin":      "<last twin output>",  # for continuity
}
```

The twin's `perform(**data_slush)` returns markdown. That markdown is the
side-panel content for this turn. Next turn, the prior output becomes
`prev_twin` — the twin is a stream of reactions, not a fresh take each time.

### Output — freeform markdown, not structured

No schema beyond "markdown string." The panel renders it as-is. The twin
can produce:

- A one-liner: "That function signature looks off — the third arg is unused."
- A structured block: tagged sections (**risk**, **suggestion**, **question**).
- Silence: returning `""` is valid — some turns don't need commentary.

Brevity is a feature. The twin is *ambient*, not a second chat.

### The "it's your twin, not a buddy" part

The twin's soul is **you** — authored by the user, stored at
`<twin-root>/twin_soul.md`. It's allowed to be first-person:
*"I would have pushed back on that last claim."* The twin is a mirror
tuned to the user's own heuristics, not a neutral assistant.

Onboarding writes the first `twin_soul.md` from answers to ~5 seed
questions. It grows over time via a separate `teach_twin` agent the user
can invoke explicitly ("twin: remember I always check for this").

### What this is NOT

- **Not a copilot replacement.** The main chat still drives. The twin is
  a second pair of eyes, not a second hand.
- **Not cross-turn state beyond data_slush.** If the twin wants memory
  across turns, it reads/writes it via the existing
  `AzureFileStorageManager` shim, same as any other agent. No hidden bus.
- **Not a new tier.** Lives in the brainstem. Tier 2 (swarm) and Tier 3
  (Copilot Studio) run the same agent file unmodified — they just don't
  render a side panel.

### Open questions

- **Rate limiting.** Does the twin fire on *every* turn, or only when
  signal is high (tool calls ran / response was long / user asked a
  question)? Probably every turn with the twin itself deciding when to
  return `""`.
- **Interruption.** If the user starts typing while the twin is still
  generating, does the twin abort? Probably yes — the side panel should
  always reflect the *previous* turn, never a half-formed reaction to
  the in-flight one.
- **Model choice.** Same provider as main chat, or a cheaper/faster
  model by default? Leaning toward same — twin quality matters and the
  user already paid the provider setup cost.

### Acceptance

The feature ships when all of the following are true:

1. `digital_twin_agent.py` is a single file under 500 lines.
2. The brainstem's turn-post hook is a ≤30-line addition to
   `rapp_brainstem/brainstem.py`.
3. Removing the agent file turns the feature off — no dangling UI, no
   dead routes.
4. The twin can be installed into any RAPP brainstem as a rapplication
   (catalog entry in `rapp_store/index.json`).
5. The side panel renders markdown with zero JS beyond what
   `rapp_brainstem/web/index.html` already ships.
