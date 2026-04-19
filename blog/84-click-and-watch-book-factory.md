# Click-and-watch: the book factory as a single web page

A dark page opens with a promise in the title bar: “Book Factory — agent.py all the way down.” At the top, a small status light sits inside a `.status-bar`. Red means nothing is ready. Yellow pulses while the page is checking. Green means the system is live. Below it, the interface stacks a form, a row of buttons, and then the real attraction: a vertical timeline of steps. Each step can turn amber while running, green when done, red on error. Click a step and its body opens, showing monospaced logs and delegated work as it happens. At the end, the page renders a final chapter in serif, as if all that machinery existed only to hand over something readable.

That scene is the product spec.

This “book factory” is framed not as a component stack or a backend-heavy wizard, but as a single page: `brainstem/onboard/book-factory.html`. The file presents the workflow directly in the interface: status at the top, controls beneath it, a pipeline timeline through the middle, and a readable final output at the end.

The page’s own heading says as much:

```html
<title>Book Factory — agent.py all the way down</title>
```

The CSS tells you what kind of experience the author wanted. Not polished illusion; operational visibility. There is a “Pipeline timeline,” with `.step.running`, `.step.done`, and `.step.error`. There is a `.step-body` in monospace with `white-space: pre-wrap`, meant for raw output, not prettified summaries. There is even a `.delegate` style inside the step body:

```css
.step-body .delegate {
  color: #f0b66f; font-style: italic; padding: 2px 0;
}
```

That rule suggests the interface was designed to distinguish delegated work from other output inside a step.

The implementation details available in the provided material point in a similar direction. The page is described as fetching agent source files, sending them to a deploy endpoint, and running personas in sequence so the user can watch the pipeline unfold. Even without the full script body quoted here, the visible structure emphasizes observability over abstraction: the user sees stages, state changes, logs, and a final rendered artifact rather than a single opaque progress indicator.

Here is the visual grammar that supports that behavior:

```css
.step.running { border-color: #d29922; background: rgba(210,153,34,.05); }
.step.done    { border-color: #2ea043; }
.step.error   { border-color: #f85149; }
```

Amber for work in progress. Green for completion. Red for trouble. Nothing fancy, just enough to let the eye scan the pipeline.

There are limits to what the provided source shows. We have the top of the file and part of the style section, plus a summary of the JavaScript behavior. We do not have the full script body here, so some implementation specifics require the repository itself, a fuller code excerpt, or technical documentation to verify directly. What is clear from the material in hand is the shape of the experience: one page that makes the workflow legible, step by step, and ends by turning process into prose.

That is what makes the page notable. It does not merely decorate the system; it expresses the system. The workflow, the state transitions, the error surfaces, and the handoff from machine process to readable chapter are all visible in the interface itself. If you wanted to understand how the product presents its own operation, `brainstem/onboard/book-factory.html` is the place to begin.
