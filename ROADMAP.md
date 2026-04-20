# RAPP Roadmap

Post-v1 directions. The v1 contract ([SPEC.md](./SPEC.md)) is frozen. Every
item here must honor it: **one file per agent**, data sloshing is the wire,
no frameworks, no new primitives where an existing pattern will do.

---

## Digital Twin Companion — a third split, like `|||VOICE|||`

**Status:** shipped (v0) · **Shape:** prompt change + parser change · **Surface:** brainstem side panel

A persistent mirror rendered next to the main chat, reacting to the turn the
user just had. Think Claude Code's side-panel buddy — but instead of a
generic helper, it's *your digital twin* watching the conversation with
you: hints, risks, what you'd say next if you were watching someone else
have this conversation.

### The whole trick is one more delimiter

The brainstem already splits LLM output on `|||VOICE|||` — a sacred OG
pattern where the model produces two parts in one response:

```
<full formatted reply>
|||VOICE|||
<concise TTS line>
```

The parser is ~15 lines (`_parse_voice_split` in `rapp_swarm/function_app.py`).
It takes the raw completion and returns `(formatted, voice)`.

The twin is **exactly the same move, one more delimiter**:

```
<full formatted reply>
|||VOICE|||
<concise TTS line>
|||TWIN|||
<twin's first-person reaction to the turn>
```

The parser returns `(formatted, voice, twin)`. The UI renders `formatted`
in the main chat, pipes `voice` to TTS (unchanged), and drops `twin` into
a side panel. Empty twin section = no side-panel update that turn.

**No new agent. No new hook. No parallel call. No new cost.** Same LLM
completion, same turn, same latency. Adding the twin panel is one prompt
change and one parser change.

### What drives the twin

The system prompt. That's it.

Today's prompt says *"structure your response in TWO parts separated by
`|||VOICE|||`"*. The updated prompt says *"...THREE parts. Third part
after `|||TWIN|||` is your first-person reaction to what just happened:
observations, hints, concerns, the thing you'd whisper to yourself if you
were watching this conversation from the outside. Keep it short. Empty is
fine."*

The twin's personality — its voice, its priorities, what it notices — is
authored by the user as a section of `soul.md` (or a standalone
`twin_soul.md` loaded into the same system message). The soul is already
sacred (§7). The twin's voice is just another paragraph in it.

### Why this is the right shape

- **Honors §5 / §8.** The agent contract doesn't change. `/chat` request
  and response shapes don't change — the twin content lives *inside* the
  existing `response` string. A v1 client that doesn't know about the
  delimiter gets the main reply and the voice line; everything still
  works. (Graceful degradation by construction.)
- **Honors `data_slush`.** The twin sees the whole turn because it *is*
  the turn. No separate context bus, no parallel agent reading the same
  state from a second place.
- **Honors the Sacred Tenet.** The agent file is untouched. No new
  `digital_twin_agent.py`. No new primitive. The twin is a prompt
  pattern, not a new thing to maintain.
- **Reversibility.** Remove the delimiter from the prompt and the twin
  disappears. The parser's `twin` return just stays empty. Zero cleanup.

### Parser rules

```python
def _parse_twin_split(content):
    """Split on |||VOICE||| then |||TWIN|||. Returns (formatted, voice, twin).
    All delimiters optional — missing ones yield empty strings downstream."""
    if not content:
        return "", "", ""
    main, _, rest = content.partition("|||VOICE|||")
    voice, _, twin = rest.partition("|||TWIN|||")
    return main.strip(), voice.strip(), twin.strip()
```

**Order matters.** `|||VOICE|||` comes before `|||TWIN|||`. If the model
emits `|||TWIN|||` without `|||VOICE|||`, the twin text leaks into
`voice` — treat that as a prompt-authoring bug, not a parser bug.

### What the twin SHOULD produce

- Short. A sentence, maybe a short list. The panel is ambient.
- First-person: *"I'd push back on the third claim. We've seen that
  pattern before and it cost us a week."* Not *"The user should..."*.
- Silent when there's nothing to add. Empty is valid.
- Structured when useful: bold one-word tags (`**Risk:**`, `**Hint:**`,
  `**Question:**`) — but only if the prompt asks for it.

### What the twin MUST NOT do

- Call tools. The twin is a reaction, not an actor. If the twin wants
  tool calls, authoring is wrong — add the agent to the binder and let
  the main loop call it.
- Contain a second response to the user. That's what the main reply is
  for. The twin comments *on* the turn; it doesn't *replace* part of it.
- Exceed a ~500-token soft cap. Prompt should enforce. Long twin output =
  the twin is trying to be the assistant; re-author.

### UI (thin)

- A right-side panel in `rapp_brainstem/web/index.html`. Fixed width on
  desktop, collapsible. Hidden on narrow viewports.
- Markdown render (we already have a renderer for the main chat — reuse).
- One panel per turn. No scrollback — the twin is about *this* turn.
  Prior turns roll off. (If the user wants history, ship it later.)
- Visual treatment: muted, slightly offset typography, so it's legible
  without competing with the main chat.

### Acceptance

1. `_parse_twin_split` (or equivalent) lands as a ~20-line addition to the
   chat response path.
2. The default soul prompt is updated to emit three parts. A user running
   without the updated soul still works — the twin is just empty.
3. Side panel renders markdown, empty panel collapses, zero new JS
   dependencies.
4. The existing `/chat` response shape is unchanged. Clients that don't
   know about the twin see the main reply in the existing field.
5. Tier 2 (`rapp_swarm/`) and Tier 3 (Copilot Studio) ship the same
   delimiter convention — the main reply surface ignores the twin block
   if the surface has nowhere to render it. (Twin text is not lost —
   it's just not rendered; a future tier 2 UI can read it.)

### Open questions

- **Third delimiter conflict.** If the model happens to emit
  `|||TWIN|||` inside a code block, it'd be misparsed. In practice
  `|||VOICE|||` hasn't hit this in production. Keep the delimiter as-is
  and revisit only if a real collision shows up.
- **Turn-scoping the twin.** Does the twin ever see *its own prior
  output*? Right now — no, the conversation history passed to the LLM
  is just user/assistant text. The main reply is the anchor; the twin
  is a fresh reaction each turn. If continuity becomes important later,
  add the prior twin as a system-note on the next turn.
- **A per-agent twin voice.** Different binders might want different
  twin personas (the book-factory twin vs. the sales twin). Scope for
  later — for v1 of this feature, one twin per tenant, authored in the
  soul.
