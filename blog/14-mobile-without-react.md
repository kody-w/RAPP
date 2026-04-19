# Mobile responsive without React

The brainstem is one HTML file. About 3500 lines. Vanilla JavaScript, CSS, and a single Pyodide load on demand. No React, no Vue, no Svelte, no build step. The entire UI ships as the file you see when you `view-source`.

Making it usable on mobile took surprisingly little.

**The viewport tag.** First and only meta line that matters:

```html
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
```

`viewport-fit=cover` is the part most non-mobile devs skip. It opts in to drawing under the iPhone's notch and home indicator areas — useful only because we then opt back out per-element with `env(safe-area-inset-*)`.

**One media query.** Everything mobile-specific is inside `@media (max-width: 720px)`. About 40 lines of CSS, no JavaScript changes, no separate render path. Selected highlights:

```css
@media (max-width: 720px) {
  /* Header: drop labels, keep icons. font-size:0 collapses text nodes,
     the .icon span keeps its sized SVG visible. */
  .icon-btn { padding: 6px; font-size: 0; }
  .icon-btn .icon { width: 16px; height: 16px; }
  #btn-signin { font-size: 11px; }   /* exception: keep the label */

  /* iOS home indicator. */
  footer { padding: 10px 12px env(safe-area-inset-bottom, 10px); }

  /* The single most important line for iOS users. */
  #input { font-size: 16px; }   /* prevents Safari's auto-zoom on focus */

  /* Hand: smaller cards, smaller hover lift. */
  .hand-card { transform: translateY(60px) rotate(var(--rot)) scale(.32); }
  .hand-card:hover { transform: translateY(-200px) rotate(0deg) scale(.85); }
}
```

The trick of the day was `font-size: 0` on `.icon-btn`. The HTML for those buttons is `<button><span class="icon"><svg/></span> Browse</button>` — the label is a text node, not wrapped in a span. The text node inherits font-size from its parent. Setting the parent to 0 collapses the text invisibly. The icon SVG inside `<span class="icon">` keeps its width/height because those are pixel-defined. No HTML change, no JS, just a property the text node can't argue with.

The 16px input is non-obvious. iOS Safari zooms the viewport when you focus an input whose computed font-size is less than 16px. Users tap the chat input, the page jumps to 175% zoom, they have to pinch back out to see the rest of the UI. We used to ship 14px inputs. Bumping to 16px on mobile (and only on mobile, so desktop keeps the tighter look) eliminates the zoom entirely. Half a CSS line.

A second media query handles **very small phones** (≤380px, iPhone SE / Mini territory). It hides the wordmark — the logo alone is enough branding at that width.

Total mobile CSS: maybe 60 lines. No abstractions, no breakpoint manager, no responsive grid framework. Just a query, some property overrides, and respect for the safe-area insets.

The pattern: build for the standard width first, write one media query for narrow screens, and trust the browser. It still works.

The brainstem isn't a small app — it has a chat surface, a holo card binder, a model picker, a tether status pill, an agent marketplace, an OAuth flow, in-browser Python execution. The whole thing is responsive enough to use one-handed on a phone. The trick is not adding things until you need them.
