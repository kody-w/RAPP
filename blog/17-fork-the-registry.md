# Curate your own agent source: fork the registry

The brainstem reads any GitHub repo that publishes a `registry.json` at its root in the `rapp-registry/1.0` schema. The default is `kody-w/RAR`, but Settings → Agent sources lets users add `owner/repo` entries. Each becomes a tab in the Browse panel.

The 5-minute path to running your own:

**1. Fork `kody-w/RAR`.**

```bash
gh repo fork kody-w/RAR --clone --remote
cd RAR
```

**2. Throw away what you don't want.**

```bash
# Wipe the upstream library, keep the structure.
rm -rf agents/@aibast-agents-library agents/@borg agents/@kody-w
```

The `agents/` directory is organized as `agents/@<publisher>/<stack>/<agent>_agent.py`. Keep the structure even if you only have one publisher namespace — the registry script expects it.

**3. Drop in your own agents.**

```bash
mkdir -p agents/@your-team/general
cp ~/your-cool-agent.py agents/@your-team/general/
```

The agent file just needs to follow the [single-file contract](./01-single-file-agent.md) — `__manifest__`, a class extending `BasicAgent`, a `perform()` method.

**4. Rebuild the registry.**

```bash
python build_registry.py
```

This walks `agents/`, parses each manifest, computes hashes, mints cards (saves them to `docs/api/v1/cards/`), and writes the new `registry.json`. About a second per agent.

**5. Push.**

```bash
git add -A && git commit -m "internal team agents v1"
git push
```

That's it. Your registry is now live at `https://raw.githubusercontent.com/your-team/RAR/main/registry.json`.

**6. Add it as a source in the brainstem.**

Settings → Agent sources → type `your-team/RAR` → Save. Browse now shows your agents alongside (or instead of) the default RAR library.

---

For private libraries, the path is similar but you have to think about access. `raw.githubusercontent.com` doesn't authenticate, so a private repo's `registry.json` won't be reachable directly. Two options:

- **Make it public** with an obscure name. Probably fine for most internal-team libraries — there's no PII in agent code, just descriptions and parameter schemas.
- **Run your own proxy worker** that takes a GitHub PAT, fetches from the private repo, returns to the brainstem. This is a ~30-line Cloudflare Worker. Add it as a source like `your-proxy.workers.dev/your-team/RAR`.

For team-internal stuff specifically, the workflow is: each agent is a `.py` file in a private repo, the team curates which ones make it in, the registry rebuild runs in CI on push, and team members install agents from the brainstem's Browse panel just like they would the public library.

The pattern: distribution is a JSON file. Curation is a git repo. Discovery is a brainstem source entry. None of these involves your team running a server.

A team's "agent shop" is one repo that everyone trusts. Forking that repo is how teams customize. Sourcing different repos is how teams compose. The model scales linearly with the number of repos, which is to say it doesn't bottleneck — every repo is independent.
