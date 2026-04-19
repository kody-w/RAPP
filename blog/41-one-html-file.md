# One HTML file, no build step, 4500 lines

The brainstem at `kody-w.github.io/RAPP/brainstem/` is a single HTML file. About 4500 lines. Inline CSS at the top, inline JavaScript at the bottom, HTML markup in the middle. There's a separate `rapp.js` that holds the card-minting library, but the chat surface itself — UI, state, routing, OAuth, model picker, Pyodide loader, swarm deploy modal — is all in one file.

No bundler. No transpiler. No npm install. The "build" is `git push`.

This is, in 2026, an unusual choice. The default for a project of this complexity is React + TypeScript + Vite + a state library + a router + a UI kit. The mainstream tooling assumes you want all of that. We don't have any of it.

**What we lose by going vanilla:**

- **Component reuse.** Same UI patterns repeat in two places? You copy them. There's no `<HoloCard>` component you can drop in three different views.
- **Type safety.** No TypeScript means runtime bugs that a compiler would catch at compile time. We've shipped a few. Mostly fine.
- **Hot reload during dev.** Editing a file means refreshing the browser. The app boots in <100ms so this is mostly fine; if it weren't, we'd reach for browser-sync or a similar minimal tool.
- **Tree-shaking.** Every byte of code we write ships to the browser. No dead-code elimination. Forces discipline about what we add.

**What we gain:**

- **Inspectability.** A user who wants to know how the brainstem works can View Source. The whole thing is right there. They don't need to track down which webpack chunk implements which feature.
- **Forkability.** Want your own brainstem? Save the HTML file. Edit it. Host it anywhere that serves static files. The fork is one file, not a Git submodule pulling in a dependency tree.
- **No build chain rot.** The webpack/Vite/Rollup/Parcel cycle is real. Build tools deprecate every 18 months. A vanilla HTML file works in the browser today and will work in the browser in a decade. We don't have to upgrade anything to keep shipping.
- **Cold-start time approaches zero.** The browser parses HTML, applies CSS, executes JS. Done. No framework hydration, no JS chunk waterfall, no waiting for the bundler's runtime to initialize.

**The rules that make it work:**

**Keep state in one object.** `state` is a global object with `settings`, `binder`, `hand`, `tether`, etc. Updates are direct mutations: `state.settings.model = 'gpt-4o'; LS.set('settings', state.settings);`. No reducers, no actions, no stores. This works because the app's state graph is small and writes happen in obvious places.

**Render functions are just DOM manipulation.** Need to update the agent list? `renderAgents()` clears the container and rebuilds it from `state.binder.cards`. Coarse-grained, fast enough at our scale, no diff algorithm needed. (At higher cardinality you'd want incremental updates, which is what frameworks give you. We're not at higher cardinality.)

**CSS classes do the styling work, not inline styles.** Component-level styles are scoped via class names. We never use a class twice for unrelated things. Naming is the discipline that replaces components.

**One file, but split mentally.** The CSS section is grouped by surface (header, chat, hand-cards, modals). The JS section is grouped by concern (state, providers, bootBinder, renderHand, chatLoop, OAuth, install modal, swarm modal). When you need to change one thing, you scroll to its section and work there.

**Where this stops working:**

- **Multi-developer churn.** Vanilla works great for one or two developers who own the file. Five developers all editing one HTML file produces merge hell. We're at one developer.
- **Component sprawl.** If we had 50 visually-distinct UI primitives we'd need to organize them as components. We have ~10. CSS classes handle the variation.
- **Test surface.** No framework means no framework's test helpers. Our tests are JS-side parsing/cards via Node + a few smoke tests. No browser DOM tests. If we needed browser tests we'd reach for Playwright separately.

**The pattern generalizes:**

For projects under ~5000 lines of UI code, with one or two contributors, where shipping speed matters more than long-term scaling — vanilla is faster, simpler, more inspectable, and longer-lived than the framework default. The constraints of "no components, no types" are real but they're also a budget on complexity. The brainstem is what it is partly *because* the constraint forced us to keep it focused.

When you're picking a stack, ask: do I expect this project to outgrow vanilla? If the answer is "no, probably not, this is going to be small forever," vanilla is the right answer. If yes, pay the framework cost up front.

Most projects answer "no" and pick a framework anyway. That's where the complexity comes from.
