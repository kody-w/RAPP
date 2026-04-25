# `pages/` — Audience-facing HTML

Static HTML pages for humans who landed on the project from outside —
prospects, partners, executives, security reviewers, FAQ-skimmers.
Served by GitHub Pages at `https://kody-w.github.io/RAPP/pages/<file>.html`.

## What's here

Audience pages, one per audience or topic:

- `faq.html`, `faq-slide.html`
- `leadership.html`
- `partners.html`
- `one-pager.html`
- `process.html`
- `release-notes.html`
- `roadmap.html`
- `security.html`
- `use-cases.html`

Plus the static viewer for the long-term memory:

- `vault/` — renders `../vault/` (the Obsidian vault) in the browser.
  Wikilinks, backlinks, search, JSZip export/import. See Article
  XXIII for the contract this implements.

## What belongs here

A new HTML file belongs in `pages/` when:

1. **It's audience-facing.** Designed to be read by a human visitor,
   not by code or by an internal contributor. Marketing tone, not
   reference tone.
2. **It has its own URL.** Each page is a destination — linkable,
   shareable, sometimes shared. (See the *one* root exception below.)
3. **It's standalone HTML.** No framework, no build step. Open in a
   browser, render. Same posture as `index.html` at repo root.

## What does NOT belong here

- ❌ **Internal documentation.** Contributor-facing reference is
  `docs/<FILE>.md`. End-user-facing guidance with code blocks is
  also `docs/<FILE>.md`, not an HTML page.
- ❌ **The repo landing page** (`index.html`) — must be at repo
  root because that's where GitHub Pages serves from. Not here.
- ❌ **`pitch-playbook.html`** — must stay at repo root because its
  URL is in active external circulation. New audience pages always
  land in `pages/`; the playbook is the only grandfathered
  exception (Article XVI).
- ❌ **Anything that needs a build step or framework.** This is
  static-by-design. If you reach for React, Next.js, or a bundler,
  you've outgrown the `pages/` pattern; redesign before adding.

## Conventions

- **Filenames are lowercase-hyphen.** `release-notes.html`,
  `use-cases.html`, `faq-slide.html`. Hyphens, not underscores.
  Lowercase, no caps.
- **Every page sets its own meta tags.** When you create or move a
  page, the page must declare:
  - `<meta property="og:url" content="https://kody-w.github.io/RAPP/pages/<file>.html">`
  - `<link rel="canonical" href="https://kody-w.github.io/RAPP/pages/<file>.html">`
  - Title, description, og:title, og:description.
  Honest URLs are an Article XVI rule — moving a page without
  updating these makes the move dishonest.
- **Test fixture stays in sync.** `tests/e2e/08-html-pages.sh`
  enumerates every page; add a new page, add it there.
- **Theme parity with `index.html`.** Pages share the dark/light
  theme toggle from the landing page so visitors who navigate
  between them aren't jolted.

## Scale rule

When you're about to add a page here:

1. *Is the visitor a human, not a contributor or a script?* Yes →
   `pages/`. No → `docs/`.
2. *Would I share this URL with someone who isn't already in the
   project?* Yes → `pages/`. No → reconsider whether it should
   ship.
3. *Can I write it as a single static HTML file?* Yes → `pages/`.
   No → redesign or stop.

If all three are yes, write it. Add the test fixture entry. Set the
canonical URL. Don't forget the og tags.

## Related

- Repo-root rule: [`CONSTITUTION.md`](../CONSTITUTION.md)
  Article XVI.
- Vault viewer contract: Article XXIII.
- HTML-page test enumeration: `../tests/e2e/08-html-pages.sh`.
