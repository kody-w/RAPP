# Historical RAPP Repository Inventory

> **Current RAPP/1 authority (rev-5).** For canonicalization, identity, frames,
> wire, eggs, registry, trust, and protocol evolution, follow
> [`RAPP1_AUTHORITY.json`](./RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](./RAPP1_STATUS.md). This inventory may describe legacy
> files, but only the pinned standard defines current protocol artifacts.

> **Whole-document disposition:** names in the tree below prove only that
> source or an archive exists. They do not establish a live installer, Pages
> product, browser UI, Tier 2/3 deployment, catalog, hatcher, or portable egg.
> The only immutable runtime claim is the three-byte-set grail pin
> `kody-w/rapp-installer@brainstem-v0.6.9`; all acceptance claims remain
> limited by `RAPP1_STATUS.md`.

<!-- RAPP1-HISTORICAL-SECTION-START -->

> **Looking for the human-facing entry point?** The [**Kernel hub**](https://kody-w.github.io/RAPP/pages/kernel.html) is the unified reading order for the whole canon — trilogy, law, reference, specs, vault Reading Paths. This page (KERNEL_TREE.md) is the file-by-file *inventory* of what's in this repo; the hub is the *narrative* that explains how it all fits.

This repo (`kody-w/RAPP`) mirrors the immutable RAPP grail at
[`kody-w/rapp-installer@brainstem-v0.6.9`](https://github.com/kody-w/rapp-installer/tree/brainstem-v0.6.9).
The exact pin—not a moving branch—governs the three pinned bytes.

Per the [Mirror Spec](./pages/vault/Architecture/Mirror%20Spec.md), only **three** files must be byte-identical to grail. Everything else is the mirror's prerogative — RAPP carries the full grail tree at its grail paths plus a few mirror-only additions (`pages/`, `tests/mirror-drift.sh`, `rappid.json`).

The full-bodied **Rappter distro** (organs, senses, lineage/bonding lib, rich UI, narrative essays) lives in a sibling repo: [`kody-w/rappter-distro`](https://github.com/kody-w/rappter-distro). The distro layers on top of this kernel without modifying it.

## The complete grail tree

### 🔒 Sacred files (byte-identical to the exact grail pin)

| Path | Purpose |
|---|---|
| `rapp_brainstem/brainstem.py` | The kernel itself. Flask server. `/chat`, `/agents`, `/health`, `/login`, `/voice`, `/models`, `/version`, `/diagnostics`. Sacred (Constitution Article XXXIII — never edited by AI assistants). |
| `rapp_brainstem/VERSION` | Kernel semver. |
| `rapp_brainstem/agents/basic_agent.py` | Agent ABI. Base class every single-file agent extends. |

`tests/mirror-drift.sh` is a legacy moving-main diagnostic and is not
authoritative for the immutable pin. Validate against the authority/KERNEL_PIN
recorded tag and digests.

### 🧠 Tier 1 — Brainstem (local Python server)

| Path | Purpose |
|---|---|
| `rapp_brainstem/local_storage.py` | Local JSON storage shim — drop-in for `utils.azure_file_storage`, lets agents written for Azure run unchanged on disk. |
| `rapp_brainstem/soul.md` | Default system prompt. |
| `rapp_brainstem/requirements.txt` | Python deps: flask, flask-cors, requests, python-dotenv, pyzipper. |
| `rapp_brainstem/start.sh`, `start.ps1`, `utils/boot.py` | Target-owned HTTP-410 launcher tombstones; no import, process, dependency, or network activity. |
| `rapp_brainstem/index.html` | Browser-side chat UI bundled with the kernel. |
| `rapp_brainstem/test_local_agents.py` | Kernel agent-contract test. |
| `rapp_brainstem/.env.example`, `.gitignore` | Config template + git hygiene. |
| `rapp_brainstem/README.md`, `CLAUDE.md`, `CONSTITUTION.md` | Per-kernel docs (alongside the repo-level ones at root). |

### 🤖 Grail-bundled agents (auto-discovered from `agents/*_agent.py`)

| Path | Purpose |
|---|---|
| `rapp_brainstem/agents/context_memory_agent.py` | Reads persistent memory storage; injects per-turn context. |
| `rapp_brainstem/agents/manage_memory_agent.py` | Writes persistent memory. |
| `rapp_brainstem/agents/hacker_news_agent.py` | Fetches + summarizes HN front page. |
| `rapp_brainstem/agents/egg_hatcher_agent.py` | Legacy cartridge router under migration. Its retired `rapp-egg/2.0` dispatch is not current RAPP/1 §9 acceptance and must not be presented as such. |
| `rapp_brainstem/agents/twin_agent.py` | Twin federation primitive. Actions: `summon`, `hatch`, `boot`, `stop`, `list`, `chat`, `inspect`, `lay_egg`, `history`, `lineage`. Federates every workspace under `~/.rapp/twins/<hash>/` through one tool. See [[The Federated Twin Egg Hatcher Pattern]]. |
| `rapp_brainstem/agents/experimental/copilot_research_agent.py` | Experimental Copilot-research agent. |

### 🥚 Hatched workspaces (runtime, not in this repo)

Twin and neighborhood eggs hatch into well-known runtime directories under the operator's home — mirror locations to the kernel's own `~/.brainstem/` install, but for *organisms the kernel federates* rather than the kernel itself:

| Path | Purpose |
|---|---|
| `~/.rapp/twins/<hash>/` | Canonical per-twin workspace. Holds the hatched `rappid.json` + `soul.md` + `agents/` for each twin. The kernel's built-in `twin_agent.py` (see above) lists, boots, stops, and chats with every workspace under this folder. `<hash>` is the 32-hex portion of a v2 rappid or a bare UUID for legacy v1.x twins. |
| `~/.rapp/neighborhoods/<hash>/` | Application-local roster path used by the legacy runtime. Retired `rapp-egg/2.0` cartridges are migration inputs; a current neighborhood egg is the verified RAPP/1 §9 `neighborhood` variant. |

These directories are *not* committed to this repo — they are produced at runtime by the generic `twin_egg_hatcher_agent.py` (or the in-kernel `egg_hatcher_agent.py`) when an egg is hatched. See [[The Federated Twin Egg Hatcher Pattern]] for the end-to-end flow.

### ☁️ Tier 2 — Swarm (Azure Functions deployment)

| Path | Purpose |
|---|---|
| `azuredeploy.json` | ARM template — one-click Deploy-to-Azure for the Swarm Function App. |
| `deploy.sh`, `deploy.ps1` | Manual Azure deploy scripts. |
| `rapp_swarm/function_app.py` | Azure Functions HTTP entry. Same `/chat` surface as Tier 1. |
| `rapp_swarm/_vendored/` | Vendored brainstem core for self-sufficient cloud deploys. |
| `rapp_swarm/host.json`, `requirements.txt`, `local.settings.json.example` | Functions runtime config. |
| `rapp_swarm/build.sh` | Re-vendors brainstem into `_vendored/` after kernel changes. |
| `rapp_swarm/provision-twin.sh`, `provision-twin-lite.sh`, `twin-egg.sh`, `twin-sim.sh` | Twin provisioning + simulation. |
| `installer/install-swarm.sh` | Convenience installer for Tier 2. |

### 🏢 Tier 3 — Copilot Studio (Power Platform solution)

| Path | Purpose |
|---|---|
| `MSFTAIBASMultiAgentCopilot_1_0_0_5.zip` | Unmanaged Power Platform solution. Import into Copilot Studio, wire the Tier 2 Function App URL, publish to Teams. |
| `worker/worker.js`, `wrangler.toml`, `README.md` | Cloudflare Worker — OAuth bridge for browser-side Copilot access without exposing credentials. |

### 🚀 Installer family

| Path | Purpose |
|---|---|
| `install.sh`, `install.cmd`, `install.ps1`, `install.command` | Root installers (grail layout). `install.command` is the macOS double-click variant. |
| `installer/install.sh`, `install.cmd`, `install.ps1` | RAPP's mirror-prerogative installer family at the sacred URL `https://kody-w.github.io/RAPP/installer/install.sh` (Constitution Article V). |
| `docs/install.sh`, `install.cmd`, `install.command` | Docs-page installers (also referenced from grail's tutorial). |
| `installer/azuredeploy.json` | Mirror copy of the Tier 2 ARM template at the installer URL. |
| `installer/MSFTAIBASMultiAgentCopilot_1_0_0_5.zip` | Mirror copy of the Tier 3 bundle at the installer URL. |

### 🌐 Pages site (Pages content shipped by grail)

| Path | Purpose |
|---|---|
| `index.html` | Repo-root landing page (kody-w.github.io/RAPP/). Three-tier pitch + install widget. |
| `blog.html` | Blog feed. |
| `release-notes.html` | Release history. |
| `docs/index.html`, `tutorial.html` | Documentation landing + step-by-step tutorial. |
| `404.html` | GitHub Pages 404. |

### 🏘️ Community surface

| Path | Purpose |
|---|---|
| `community_rapp/skill.md` | Agent contract — the LLM-readable spec for participating in the community. |
| `community_rapp/agent-repo-skill.md` | Skill spec for agent-repo authors. |
| `community_rapp/install.sh`, `install.ps1` | Community-side install entry points. |

### 📜 Specs + tests

| Path | Purpose |
|---|---|
| `skill.md` | Historically named, non-runtime host-onboarding runbook; not a RAPP agent or capability. |
| `tests/test_installer.sh` | Grail's installer test. |
| `tests/mirror-drift.sh` | **Mirror-only.** Verifies the three sacred files match grail main on GitHub. |

### 🔧 Repo plumbing

| Path | Purpose |
|---|---|
| `.github/copilot-instructions.md` | Copilot-coding guidance for this repo. |
| `.gitignore` | Git hygiene. |
| `CLAUDE.md` | Claude Code guidance for this repo. |
| `README.md` | Repo README. |
| `CONSTITUTION.md` | Protocol governance (peer of README, at root). |
| `LICENSE`, `LICENSE-DOCS` | Licenses. |
| `rappid.json` | **Mirror-only legacy application record.** Current identity and anchor resolution follow RAPP/1 §§6/13; `parent_rappid` is not a trust chain. |
| `pages/` | **Mirror-only.** Rappter audience-facing site (Mirror Spec explicitly lists `pages/` as free-to-change). |

## The distro layer (not in this repo)

The full-bodied Rappter organism lives in [`kody-w/rappter-distro`](https://github.com/kody-w/rappter-distro):

- `agents/@rappter/` — swarm_factory, learn_new, upgrade (beyond grail's bundle)
- `lib/` — bond, egg, lineage, rappid, frames, peer_registry, twin (organism layer)
- `organs/` — `/api/<name>/*` route extensions (estate, lifecycle, neighborhood)
- `senses/` — response channels (`|||VOICE|||`, `|||TWIN|||`)
- `ui/` — rich 223 KB index.html, web assets, `tls_proxy.py`
- `tools/`, `examples/`, `docs/` (ECOSYSTEM, HERO_USECASE, ANTIPATTERNS, NEIGHBORHOOD_PROTOCOL, OSI, MASTER_PLAN, vault)

Install with `--rappter`:

```bash
curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash -s -- --rappter
```

The distro never modifies the three sacred kernel files; it composes onto the kernel via `sys.modules` shims + agent discovery + the `boot.py` Flask-run wrapper.

## Mirror compliance

```bash
bash tests/mirror-drift.sh
```

The legacy script's three `OK` lines compare its configured source only.
Authoritative equality means the three files match the exact
`kody-w/rapp-installer@brainstem-v0.6.9` pin; never restore from moving main.

<!-- RAPP1-HISTORICAL-SECTION-END -->
