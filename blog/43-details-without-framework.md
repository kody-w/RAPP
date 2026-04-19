# `<details>` for collapsible UI without a framework

Every collapsible widget in the brainstem is a native HTML `<details>` element. The agent-call log chips. The accordion-style sections inside the binder modal. The expandable settings rows. None of them use a framework's "Disclosure" or "Accordion" component. They all use `<details>` plus some CSS.

```html
<details>
  <summary>› ✦ <span class="al-name">Save Memory</span> agent called</summary>
  <pre class="al-pre">{...args...}</pre>
  <pre class="al-pre">{...result...}</pre>
</details>
```

The browser handles open/close natively. Click the summary, the contents reveal. Click again, they hide. Keyboard accessible (Enter / Space toggle, Tab focuses, screen readers announce as "expandable"). All for free.

The only CSS we add:

```css
/* Hide the default ▶ disclosure triangle. */
.agent-log details summary::-webkit-details-marker { display: none; }

/* Substitute our own arrow that rotates 90° when open. */
.agent-log details summary::before {
  content: '›';
  color: #58a6ff;
  display: inline-block;
  transition: transform .15s;
}
.agent-log details[open] summary::before { transform: rotate(90deg); }
```

`details[open]` is the magic selector. The browser sets the `open` attribute on the element when it's expanded. CSS reads it. Animation comes from a CSS transition on the `transform`. No JavaScript involved in the open/close itself.

**The one piece of JS we add: the `toggle` event.**

```js
div.querySelectorAll('.agent-log details').forEach(d => {
  d.addEventListener('toggle', () => { if (d.open) scrollChat(); });
});
```

When a chip opens, we want the chat to scroll so the new content stays in view. The `toggle` event fires on every open/close. We check `d.open` and scroll if it's the open transition. Three lines.

**Why this beats a framework component:**

A framework "Disclosure" component would give you:
- A controlled `open` state.
- An `onChange` callback.
- Optional animation primitives.
- Probably a custom indicator slot.

You'd write maybe ~50 lines of component code. You'd have to import it, configure it, handle re-renders when the open state changes. The browser already does ALL of this — natively, fast, accessible, with no library code shipped to the user.

`<details>` is in every browser back to IE11 (well, IE11 doesn't render the indicator, but the open/close works). Mobile browsers handle it correctly. Screen readers announce it correctly. Keyboard shortcuts work. The CSS to skin it is portable.

**Why this isn't more popular:**

Two reasons.

**One: it's perceived as "old."** `<details>` shipped in HTML5 over a decade ago. Many devs learned framework patterns first, never circled back to native equivalents. They reach for the framework primitive because that's what they know.

**Two: it doesn't compose with framework state.** If your app holds open/close state in Redux/Zustand/whatever, you'd want a controlled component so the framework can render the right state. `<details>` is uncontrolled — the browser owns the state. You CAN sync via the `open` attribute and the `toggle` event, but it requires a tiny bit of glue.

For a vanilla app like the brainstem, neither of those matters. The browser is the framework. `<details>` is exactly the right primitive.

**The pattern generalizes:**

Every UI primitive a framework gives you, the browser probably has a native version of:

- Modal? `<dialog>` (with `.showModal()`).
- Tooltip? `title` attribute (basic), or CSS `::before` overlay (styled).
- Date picker? `<input type="date">`.
- Color picker? `<input type="color">`.
- Range slider? `<input type="range">`.
- Search box with autocomplete? `<input list="...">` + `<datalist>`.
- Progress bar? `<progress>`.
- Meter? `<meter>`.
- Disclosure? `<details>`.

Each of these is browser-native, accessible by default, faster than a JS component, and *zero* bytes of JS shipped to the user. The styling defaults are usually ugly; that's CSS work, not framework work.

For a vanilla project: reach for the native element first. Add framework component only when the native one can't do what you need (often: never).

The brainstem ships about 20 `<details>` elements across its UI. None of them required any JavaScript beyond optional auto-scroll on open. They all work. They all look correct. They cost almost nothing.

The browser already built the components. Use them.
