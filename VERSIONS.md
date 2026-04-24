# RAPP Brainstem — Versions

Every `rapp_brainstem/VERSION` bump is tagged in this repo as
`brainstem-vX.Y.Z`. A tagged commit is an **immutable reference** — git
will give you the exact tree that was released under that version, and
GitHub's raw file URLs for that tag never change. You can stop worrying
about "will this URL still work in two years?" — yes.

## Install the latest (default)

```bash
curl -fsSL https://kody-w.github.io/RAPP/install.sh | bash
```

## Pin to a specific version (fallback)

If a newer release broke something for you, roll back to a known-good
version:

```bash
BRAINSTEM_VERSION=0.5.1 curl -fsSL https://kody-w.github.io/RAPP/install.sh | bash
```

The installer will check out `tags/brainstem-v0.5.1` instead of `main`.
All older tags stay resolvable forever — the repo's git history and
GitHub's raw CDN both treat tagged commits as load-bearing data.

## Raw-URL access to any tagged version

If you want to fetch a specific file from a specific version without
cloning — e.g., in another script, in a bookmarklet, in a CI job:

```
https://raw.githubusercontent.com/kody-w/RAPP/brainstem-v0.5.1/rapp_brainstem/brainstem.py
https://raw.githubusercontent.com/kody-w/RAPP/brainstem-v0.5.1/rapp_brainstem/web/index.html
```

Substitute any tagged version. The URL is stable as long as the tag
exists.

## Published versions

| Tag | What shipped |
|---|---|
| `brainstem-v0.4.0` | First `VERSION` — Flask brainstem + voice toggle |
| `brainstem-v0.5.0` | VERSION bump to force-pull on existing installs |
| `brainstem-v0.5.1` | Restored Flask brainstem as canonical, added `/twin/toggle` + Twin banner line |
| `brainstem-v0.7.0` | Flask `/` now serves the rich `web/index.html` (Settings aside, binder, twin panel, …) |
| `brainstem-v0.7.1` | Twin can run rapplications via `<action kind="rapp">` + auto-inject binder context |
| `brainstem-v0.7.2` | Fixed `rapp.js` 404 + SOUL_RESPONSE_FORMAT template literal breakage |
| `brainstem-v0.12.2` | Agent-first rapplication platform. Service discovery in kernel (`services/*_service.py` → `/api/<name>`). Factory-clean brainstem (4 core agents, empty `services/`). RAPPstore with 7 rapplications (kanban, webhook, dashboard, vibe_builder, learn_new, swarm_factory + binder/swarms services). VibeBuilder meta-agent generates rapplications from natural language. Twin mode restored with `|||TWIN|||` + action chips. Rapplication SDK (`rapplication-sdk.md`). Constitution Article XX (kernel/extensions/factory-installed rule). vBrainstem: standalone RAPPstore catalog, OS-aware install one-liner, tether default port fix. Login UI polished (green code box, animated dots, model catalog messaging). Windows installer fixes (dep-check SyntaxError, hidden background service, PYTHONIOENCODING, repo-switch detection). `build.sh` vendors services + rsync fallback for Windows. |

## When cutting a new version (maintainer checklist)

1. Bump `rapp_brainstem/VERSION` in the commit that contains the
   changes.
2. After push, create and push the matching tag:
   ```bash
   git tag -a brainstem-vX.Y.Z -m "brainstem vX.Y.Z (one-line summary)"
   git push origin brainstem-vX.Y.Z
   ```
3. Add the new row to the table above.

Never delete a tag. A version that existed continues to exist.
