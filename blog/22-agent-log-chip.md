# The agent-log chip

Tool-using LLMs are nondeterministic. The same question can fire one tool, three tools, or none. The user who asked "what's on Hacker News right now?" doesn't necessarily know that an agent ran, what arguments it received, or what raw JSON came back. Most of the time they shouldn't have to. Sometimes they want to.

The brainstem solves this with a small chip beneath each assistant message:

> › ✦ **Save Memory** agent called

Click it open and you get two sections:

```
ARGS
  {
    "memory_type": "fact",
    "content": "Always include clickable links when sharing HN stories"
  }

RESULT
  {"status": "success", "id": "...", "summary": "Saved fact: ..."}
```

Three rules govern this chip:

**Rule 1: Default closed.** Most users will never click. The summary line says enough — they know an agent ran, they know which one, that's plenty. The chip is collapsed unless the user opts in.

**Rule 2: No clutter in the summary.** The earliest version showed args inline: "Save Memory called with `{}`". The empty curlies were technical-debt clutter — meaningful only when there were args, ugly when there weren't. We pulled the args into the body so the summary is always one clean phrase: `<Name> agent called`.

**Rule 3: Auto-scroll on toggle.** Expanding the chip grows the bubble downward. Users used to lose the new content below the fold. A `<details>` toggle listener auto-scrolls the chat to bottom when any chip opens.

The implementation is twenty lines of CSS and ten lines of JS. The chip is a native `<details>` element with a custom `summary`. No framework component, no state management. CSS hides the default `▶` triangle and substitutes a styled `›` that rotates 90° when open. The render walks the assistant's `agent_logs` array and emits one `<details>` per call:

```js
agent_logs.map(l => {
  const pretty = l.name.replace(/([a-z])([A-Z])/g, '$1 $2');
  const hasArgs = l.args && Object.keys(l.args).length > 0;
  const argsBlock = hasArgs
    ? `<div class="al-section">args</div><pre class="al-pre args">${escapeHtml(JSON.stringify(l.args, null, 2))}</pre>`
    : '';
  return `
    <details>
      <summary>${icon('spark')} <span class="al-name">${escapeHtml(pretty)}</span> agent called</summary>
      ${argsBlock}
      <div class="al-section">result</div>
      <pre class="al-pre">${escapeHtml(outStr)}</pre>
    </details>`;
}).join('')
```

`SaveMemory` becomes `Save Memory` for the human-facing summary. The CamelCase split is a one-line regex.

The chip occupies maybe 30px of vertical space when closed. It looks like a chat artifact, not a debugger. When you need to see what really happened, it's there. When you don't, it stays out of your way.

This is the right shape for any "AI did something opaque" affordance: tiny when collapsed, structured when expanded, never hides the data, never demands attention. The data is yours to inspect; the UI just presents it well.
