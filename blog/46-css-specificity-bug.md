# Specificity is a real bug class: `.bubble pre` vs `.al-pre`

The agent-call log chip in the brainstem has a body section showing the agent's args and result. When closed, just a one-line summary. When you click open, two `<pre>` blocks appear, scoped tight to their `<details>` container — rounded corners, dark green for results, dark cyan for args.

For one frustrating week, expanding the chip looked broken. The pre blocks burst out of the rounded `<details>` corners. The bubble looked split — the assistant's text had nice rounded edges, then the pre block had a different background and busted shape jutting below it.

Screenshot: ugly. Cause: CSS specificity.

The relevant rules:

```css
/* Defined for markdown-rendered pre blocks inside assistant bubbles. */
.msg.assistant .bubble pre {
  background: #0d1117;
  padding: 10px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 8px 0;             /* ← the problem */
}

/* Defined for the agent-log chip's pre blocks specifically. */
.agent-log .al-pre {
  padding: 4px 10px 8px;     /* tight, no margin */
  background: #0d1117;
  font-size: 10px;
  white-space: pre-wrap;
  max-height: 200px;
  overflow-y: auto;
  margin: 0;                  /* ← what we wanted */
}
```

The agent-log pre has `<pre class="al-pre">`. It also lives inside an assistant bubble (it's appended to the message). So both selectors match. CSS uses the more-specific one to resolve the conflict.

**Specificity counts:**

- `.msg.assistant .bubble pre` = 0,3,1 (two classes + one element)
- `.agent-log .al-pre` = 0,2,0 (two classes)

`0,3,1` beats `0,2,0`. The bubble's pre rule wins. The agent-log pre got `padding: 10px`, `border-radius: 6px`, `margin: 8px 0` — exactly the markdown pre styling, which is wrong inside the chip.

**Why it looked broken:**

`margin: 8px 0` adds 8px of space above and below the pre block, *inside* the rounded `<details>` container. The container had `overflow: hidden`, but the margin lives within the box model — it pushed the pre away from the container's edges, leaving white space that broke the visual continuity. The pre's own dark background then started below where the rounded container expected it to start.

The visible effect: the bubble has rounded corners on top, then a flat-bottomed dark section, then the pre block, then more flat-bottom. Looks like the bubble fell apart.

**The fix:**

Two characters. Add `:not(.al-pre)` to the bubble's pre rule:

```css
.msg.assistant .bubble pre:not(.al-pre) {
  background: #0d1117;
  padding: 10px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 8px 0;
}
```

Now the bubble's rule matches markdown pre blocks but skips agent-log pre blocks. The `.agent-log .al-pre` rule wins by default for `.al-pre` elements (its only competition for that selector is the now-excluded one).

**Three lessons:**

**One: scope your "everything inside this container" rules carefully.** `.msg.assistant .bubble pre` is a *very* broad target — it matches every `<pre>` ever rendered in any assistant bubble, including ones from nested components like the agent-log chip. The components that get nested didn't exist when this rule was written, but the rule had no way to know.

**Two: specificity is a numbers game.** When you write a rule for a specific component, count the selectors. If something else in your stylesheet has higher specificity for the same elements, your rule loses. The browser doesn't care which rule was written later or which one is "more correct" — it cares about the specificity score.

**Three: `:not()` is the fastest fix.** When you find an over-broad rule that's hitting things it shouldn't, the cleanest solution is usually to scope the *broad* rule narrower (with `:not()`) rather than to make the *narrow* rule more specific (with `!important` or selector chains). The result reads as "this rule applies to X except Y," which is honest about the intent.

The bug existed in the codebase for over a week before someone (a user, in a screenshot) pointed it out. Once identified, the fix took two minutes. The diagnosis took longer than the fix because we kept assuming the issue was in the agent-log code — wrong padding, wrong margin, wrong overflow — when it was actually in the bubble's code overriding the agent-log's intent.

CSS specificity is real engineering. Treat it that way.
