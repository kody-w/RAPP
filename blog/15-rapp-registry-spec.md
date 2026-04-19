# `rapp-registry/1.0`: a JSON file is a marketplace

The brainstem's Browse panel lists 138 agents with descriptions, tags, authors, categories, and one-click install. There's no marketplace backend. There's no API. There's a JSON file at the root of a GitHub repo.

```
https://raw.githubusercontent.com/kody-w/RAR/main/registry.json
```

That URL returns a single document containing every agent in `kody-w/RAR`'s library. The brainstem fetches it on boot, parses it, and renders the rows. New agent published? Re-fetch (or wait for the in-page refresh). No deployment, no schema migration, no CDN purge.

The schema is `rapp-registry/1.0`. It looks like:

```json
{
  "schema": "rapp-registry/1.0",
  "version": "1.0.0",
  "generated_at": "2026-04-18T02:35:25Z",
  "stats": {
    "total_agents": 138,
    "publishers": 7,
    "categories": 19
  },
  "agents": [
    {
      "schema": "rapp-agent/1.0",
      "name": "@aibast-agents-library/account_intelligence",
      "version": "1.0.0",
      "display_name": "Account Intelligence",
      "description": "360-degree account briefings with stakeholder mapping...",
      "author": "AIBAST",
      "tags": ["b2b", "sales", "stakeholder-mapping"],
      "category": "b2b_sales",
      "quality_tier": "community",
      "_file": "agents/@aibast-agents-library/b2b_sales_stacks/account_intelligence_stack/account_intelligence_agent.py",
      "_seed": 4997715477691771520,
      "_sha256": "48010aaae45ac5e099bea276e3b90b10ee9e2e6ab03722f59f423c0d0034cc0c",
      "_has_card": true
    },
    ...
  ]
}
```

The fields without underscores are part of the agent's `__manifest__` — what the agent itself declares. The `_`-prefixed fields are derived by the registry build script: file path, content hash, card seed, size. The brainstem only needs `_file` to install: it fetches `https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{_file}`, mints the card, adds it to the binder.

That's the entire installation pipeline. Two HTTP GETs. No package manager.

Browser-side, the brainstem can pull from any number of sources:

```js
state.settings.sources = ['kody-w/RAR'];
```

In Settings, the user types `owner/repo` to add another. The brainstem fetches each source's `registry.json` (trying `main` then `master`), aggregates all the agents into one filterable list, and tags each with its source. Every Browse row carries a "kody-w/RAR" or "your-org/internal-agents" chip so the user knows where it came from.

The registry isn't a database. It's a generated artifact. RAR's CI rebuilds `registry.json` when agents change (`build_registry.py` walks the agents folder, computes hashes, mints cards, writes the JSON). Static GitHub Pages serves it. Edge caches keep it fast.

What this means in practice:

- **Forking is trivial.** Clone RAR, delete agents you don't want, add agents you do, push. Your fork has its own `registry.json`. Anyone can use it.
- **Private libraries are free.** Make a private repo with the same layout. The brainstem won't be able to fetch it (no auth on the unauthenticated `raw.githubusercontent.com` URLs), but a tiny worker can proxy with a token. Or just use a public repo with obscure naming.
- **There's no central authority.** No one approves what goes into "the marketplace" because there is no marketplace. There's a default source (RAR) and however many sources users add.

The whole thing fits in a few hundred lines of build script (server-side) and a few hundred more in the brainstem (client-side). It scales as well as GitHub Pages does, which is to say: well past the size of any single project.

If you're tempted to build a registry server, build a JSON file first.
