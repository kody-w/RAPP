# RAPP Brainstem — Versions

> **Current RAPP/1 authority (rev-5).** For canonicalization, identity, frames,
> wire, eggs, registry, trust, and protocol evolution, follow
> [`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../RAPP1_STATUS.md). Release tags remain immutable
> history; resolvability does not make a retired schema current or acceptable.

## Current immutable grail policy

The runtime grail is
[`kody-w/rapp-installer@brainstem-v0.6.9`](https://github.com/kody-w/rapp-installer/tree/brainstem-v0.6.9).
Its pinned `brainstem.py`, `agents/basic_agent.py`, and `VERSION` bytes are
never edited locally and do not follow this repository's moving latest tag.
The local tags below are release history, not structural authority.

## Historical moving-release workflow (superseded)

<!-- RAPP1-HISTORICAL-SECTION-START -->

The remainder preserves the former local tagging, install, rollback, schema,
and release procedures. Do not use them to replace the three immutable grail
bytes or to claim current protocol conformance.

Every `rapp_brainstem/VERSION` bump is tagged in this repo as
`brainstem-vX.Y.Z`. A tagged commit is an **immutable reference** — git
will give you the exact tree that was released under that version, and
GitHub's raw file URLs for that tag never change. You can stop worrying
about "will this URL still work in two years?" — yes.

## Install the latest (default)

```bash
curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash
```

## Pin to a specific version (fallback)

If a newer release broke something for you, roll back to a known-good
version:

```bash
BRAINSTEM_VERSION=0.5.1 curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash
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
| `brainstem-v0.15.x` | **Egg-cartridge unification + tethered vBrainstem (2026-05-10).** Five-variant `.egg` family: `brainstem-egg/2.3-session` (shipping), `brainstem-egg/2.3-neighborhood` + `brainstem-egg/2.3-estate` (planned), joining the existing `2.2-organism` and `2.2-rapplication`. New kernel agent `egg_hatcher_agent.py` introspects any egg's manifest schema/type and routes by kind (refuses on unknown). New public surface `pages/vbrainstem.html` — multi-participant browser-tab tether with QR-pair WebRTC handshake (PeerJS + ECDSA P-256 + 6-digit safety code), three exchangeable LLM backends (localhost default / `?brainstem=URL` / `?copilot=1` via Doorman + Pyodide), Coordinator-driven debate-demo workflow. Spec additions: SPEC.md §18.10–§18.12. |

## Historical schema declaration ledger

This table preserves schema names reported by past releases. It is not the
RAPP/1 §13 registry and its `shipping` labels are historical. Retired forms
may remain retrievable for audit, but RAPP/1 §12 migrates and retires their
normal readers; retrievability never means current acceptance.

| Schema | Status | Owner | Reference |
|---|---|---|---|
| `brainstem-egg/2.0` | legacy | `utils/egg.py` | (legacy twin egg) |
| `brainstem-egg/2.1` | legacy | `utils/bond.py`, `twin_agent.py` | variant repo cartridge |
| `brainstem-egg/2.2-organism` | shipping | `utils/bond.py` | full instance cartridge |
| `brainstem-egg/2.2-rapplication` | shipping | `utils/bond.py` | single rapp cartridge |
| `brainstem-egg/2.3-session` | shipping (2026-05-10) | `pages/vbrainstem.html` (export); `egg_hatcher_agent.py` (route) | session cartridge — JSON; rappid + sha256-pinned runtime + transcript + participants. Spec: [`kody-w/rappterbox/carts/SCHEMA.md`](https://github.com/kody-w/rappterbox/blob/main/carts/SCHEMA.md) |
| `brainstem-egg/2.3-neighborhood` | planned | `egg_hatcher_agent.py` (manual instructions for now) | neighborhood gate cartridge |
| `brainstem-egg/2.3-estate` | planned | `egg_hatcher_agent.py` (manual instructions for now) | operator-identity cartridge — whole multi-tier identity portable across substrates |
| `rappterbox-cart/0.1` | deprecated | `kody-w/rappterbox/console.html` (loader) | superseded by `brainstem-egg/2.3-session` 2026-05-10; loader accepts both for one release |

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

<!-- RAPP1-HISTORICAL-SECTION-END -->
