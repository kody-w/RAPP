# The RAPPstore — a JSON file is a marketplace, again

We did this trick once already. Back in [blog/15](./15-rapp-registry-spec.md), the brainstem's Browse panel listed 138 agents — descriptions, tags, authors, one-click install — and the entire backend was a JSON file at the root of a GitHub repo. No marketplace API. No service. `registry.json`. Done.

We're doing it again, one tier up. The RAPPstore catalogs **rapplications** — converged single-file `agent.py` workflows produced by the [double-jump loop](./89-double-jump-loop.md) — and the entire backend is, once more, a JSON file at the root of a GitHub repo.

```
https://raw.githubusercontent.com/kody-w/RAPP/main/store/index.json
```

That URL returns `store/index.json`, schema `rapp-store/1.0`. The browser UI at `store/index.html` fetches it on boot, parses it, renders cards. New rapplication shipped? Re-fetch. No deploy, no migration, no cache purge.

**Same shape, different tier.**

The cloud registry from blog/15 indexed `rapp-agent/1.0` files inside `kody-w/RAR`. The RAPPstore indexes `rapp-application/1.0` files inside `kody-w/RAPP`. RAR catalogs the bricks. RAPPstore catalogs the buildings. Same fork-the-marketplace pattern from [blog/17](./17-fork-the-registry.md): clone the JSON, edit it, host it, point your users at your URL. The pattern doesn't care what tier you're at — RAPP-agents, RAR-agents, swarms, rapplications. The format works for all of them because [a JSON file is everything](./59-json-as-everything.md).

**The schema, verbatim.**

Here's the actual top of `store/index.json` (one entry shown, abbreviated):

```json
{
  "schema": "rapp-store/1.0",
  "name": "RAPPstore — official",
  "maintainer": "@kody.cloud",
  "version": "1.0.0",
  "homepage": "https://kody-w.github.io/RAPP/store/",
  "install_protocol": "drop the singleton .py file into your local brainstem's `agents/` dir.",
  "rapplications": [
    {
      "id": "bookfactoryagent",
      "name": "BookFactory",
      "version": "0.3.0",
      "summary": "Five-persona content pipeline (Writer → Editor → CEO → Publisher → Reviewer)...",
      "tagline": "Source material in, publishable chapter out — 8 LLM calls under one POST.",
      "category": "creative-pipeline",
      "tags": ["composite", "creative-pipeline", "twin-stack", "singleton"],
      "manifest_name": "@rapp/book-factory-singleton",
      "singleton_filename": "bookfactory_agent.py",
      "singleton_url": "https://raw.githubusercontent.com/kody-w/RAPP/main/agents/bookfactory_agent.py",
      "singleton_sha256": "e4cc1cd9212d6f845219966ac7df06ab4a3e0c1346a98b0ed2c147032afdf0a4",
      "singleton_lines": 543,
      "singleton_bytes": 24779,
      "egg_url": null,
      "metrics": { "llm_calls_per_invocation": 8, "wall_time_sec_per_call_p50": 75 },
      "example_call": {
        "endpoint": "POST /api/swarm/{guid}/agent",
        "body": { "name": "BookFactory", "args": { "source": "...", "chapter_title": "..." } }
      }
    }
  ]
}
```

Required fields per entry: `id`, `name`, `version`, `summary`, `manifest_name`, `singleton_filename`, `singleton_url`. Optional: `singleton_sha256` (audit), `egg_url` (a pre-populated state pack), `metrics` (the receipts), `example_call` (so the user knows what to POST). Same field-discipline as the `rapp-swarm/1.0` bundle from blog/59 — required fields are the union of all consumers' minimums; optional fields are the union of every consumer's nice-to-haves.

**The install protocol is one line.**

```bash
curl -fsSL <singleton_url> -o agents/<name>.py
```

That's it. The singleton is everything. No `pip install`. No native deps. No install script. The Python file imports `BasicAgent` and reads an LLM key out of the environment, and your local brainstem hot-loads it from `agents/`. The HTML store has a "Copy install command" button that drops exactly this `curl` line on your clipboard, pre-filled with the URL and filename from the catalog entry.

The deploy path is the same line, wrapped: POST a `rapp-swarm/1.0` bundle that contains the singleton's source. We test exactly this in `tests/test-rapplication-store.sh` — the install path drops `bookfactory_agent.py` into a swarm bundle, hits `/api/swarm/deploy`, and asserts `BookFactory` shows up in `healthz` as one agent. End-to-end, the file is the install.

**Why JSON-as-marketplace works (again).**

We made this argument in blog/59 about swarm bundles. It rhymes here:

- **Marketplace.** Browse what's available. The HTML page renders cards from the same `index.json` — name, tagline, pills, stats (lines, bytes, LLM calls, p50 wall), download button.
- **Deploy unit.** The URL IS the install. Catalog row → `singleton_url` → `curl` → working agent. No transformation. No "submit job, get artifact back."
- **Portable archive.** Clone `RAPP/`, you have the catalog. The catalog is in your repo. You can build offline against it. You can serve it from your laptop. You can email it.
- **Auditable.** Each entry pins `singleton_sha256`. Section 2 of the test suite recomputes the hash on disk and fails if it drifts. No opaque blobs. The thing you `curl` is the thing the catalog said it would be.

**Fork your own RAPPstore.**

Same five-minute path as blog/17, one tier up:

```bash
gh repo fork kody-w/RAPP --clone --remote
cd RAPP
# trim the official catalog
$EDITOR store/index.json
# add your own singleton
cp ~/your_rapplication.py agents/
# pin its hash
shasum -a 256 agents/your_rapplication.py
# edit store/index.json to add the entry
git add -A && git commit -m "internal team rapplications v1"
git push
```

Your store is now live at `https://raw.githubusercontent.com/your-team/RAPP/main/store/index.json`. Point users at it. Done. You don't run a server. You don't run a build worker. GitHub Pages serves the HTML viewer. `raw.githubusercontent.com` serves the JSON. Edge caches keep it fast.

**This isn't another agent marketplace.**

It looks like one — there's a catalog, there are listings, there's a download button — but the contract is different in every direction that matters:

- **No upload service.** You don't `rapp publish`. You add a row to a JSON file and push to git.
- **No auth to browse.** `raw.githubusercontent.com` doesn't gate. The catalog is a public artifact.
- **No "submit your rapplication for review."** There's no review queue because there's no central authority. The official RAPPstore lists what `kody-w/RAPP` ships. Your fork lists what your fork ships. Both are equally legitimate.
- **No proprietary protocol.** The "API" is `GET /index.json` and `GET /<singleton>.py`. Two HTTP calls. Anyone can write a client in twenty lines.

The URL is the only contract. Distribution is a JSON file you control.

If you're tempted to build a rapplication marketplace, build a JSON file first. We did. Then we built the HTML viewer on top of it as a hundred lines of vanilla JS. The marketplace is `store/index.json` plus `store/index.html` plus a `curl` command. Everything else is a consequence.
