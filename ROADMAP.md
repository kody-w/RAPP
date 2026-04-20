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

---

## Twin Calibration — fidelity that grows autonomously

**Status:** proposed · **Shape:** prompt change + a small JSONL log · **Depends on:** the twin companion v0

The v0 twin emits hints every turn. Some hints are right, some are noise.
The user votes with their next turn — they act on the hint, push back
against it, or ignore it. That signal is sitting there, free. Calibration
is the move that captures it and uses it to make the twin better over
time, without any explicit teach step from the user.

### The loop

1. **Predict.** Each turn the twin emits its commentary inside `|||TWIN|||`
   AND optionally tags predictions it made, e.g.:
   ```
   |||TWIN|||
   **Hint:** the oldest PR is the release blocker.
   <probe id="t-4711" kind="priority-claim" subject="PR#123" confidence="0.7"/>
   ```
   The probe tag is part of the twin's output, not a separate primitive.
2. **Observe.** On the *next* turn, the twin receives its own prior
   `|||TWIN|||` output as context (appended to the system prompt as a
   tiny `<prior_twin_probes>` block). The twin now knows what it claimed
   a turn ago.
3. **Score.** The twin's prompt instructs: *"For each prior probe,
   judge whether the user's most recent message validates, contradicts,
   or is silent on the claim. Emit a calibration line."* That line
   looks like:
   ```
   <calibration id="t-4711" outcome="validated" note="user merged PR#123 first"/>
   ```
4. **Log.** The brainstem parses any `<calibration …/>` tags out of the
   `|||TWIN|||` block and appends each to `<twin-root>/.twin_calibration.jsonl`
   before rendering. The user never sees the tags; they're stripped
   from what renders in the side panel.
5. **Recalibrate.** The next turn's system prompt injects a rolling
   summary of the twin's hit-rate by `kind`:
   *"Your historical accuracy: priority-claim 62% (21/34), risk-flag
   81% (17/21), api-shape-guess 44%."* The twin uses that to decide
   how confidently to emit new probes of each kind.

### Why this works without a new primitive

- The probes and calibration marks are just **XML-ish tags inside the
  existing `|||TWIN|||` block**. No new delimiter, no new wire field.
  The parser needs one more step — extract-and-strip `<probe/>` and
  `<calibration/>` before rendering — which is a ~20-line addition.
- The log is one JSONL file per twin-root. No DB. Grep-readable.
  Deletable. Exportable.
- No separate LLM call. The twin already runs every turn; it now does
  slightly more work inside the same completion.

### The autonomy claim

The user never has to say *"good hint"* or *"bad hint"*. The twin
watches what the user actually does on the following turn — that's the
ground truth. If the user merges PR#123 after the twin flagged it as
the blocker, the claim is validated. If the user merges a different PR,
the claim is contradicted. If the user changes topic entirely, the
claim is silent — don't count it either way.

This is the *confirm with numbers* move — the twin's confidence for
each probe kind is an actual ratio, stored, auditable, and drifting
toward reality as more turns happen. If the twin starts off overconfident
about priority claims and underconfident about API shapes, the
calibration log will show that, and the next turn's prompt will nudge
the twin to adjust.

### Acceptance

1. `<probe/>` and `<calibration/>` tags are stripped from the rendered
   twin panel and written to `.twin_calibration.jsonl` instead.
2. A rolling accuracy summary is injected into the system prompt — at
   most ~200 tokens, showing last-N windowed hit rates by `kind`.
3. Removing the calibration block from the prompt collapses back to
   v0 twin behavior. Removing the JSONL file resets the twin's
   confidence to neutral. Both are cleanly reversible.
4. The user can read `.twin_calibration.jsonl` with `jq` and see
   what the twin thought and what happened.
