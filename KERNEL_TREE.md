# RAPP kernel tree

This repo (`kody-w/RAPP`) is a **mirror** of the RAPP grail kernel at [`kody-w/rapp-installer`](https://github.com/kody-w/rapp-installer). Its purpose is to show the **full kernel tree end-to-end in one repo** — every file the kernel ships, plus the mirror's own optional surfaces (Pages site, audience docs, drift-check tests).

Per the [Mirror Spec](./pages/vault/Architecture/Mirror%20Spec.md), only **three** files must be byte-identical to grail. Everything else is the mirror's prerogative — RAPP carries the full grail tree at its grail paths plus a few mirror-only additions (`pages/`, `tests/mirror-drift.sh`, `rappid.json`).

The full-bodied **Rappter distro** (organs, senses, lineage/bonding lib, rich UI, narrative essays) lives in a sibling repo: [`kody-w/rappter-distro`](https://github.com/kody-w/rappter-distro). The distro layers on top of this kernel without modifying it.

## The complete grail tree

### 🔒 Sacred files (Mirror Spec — byte-identical to grail forever)

| Path | Purpose |
|---|---|
| `rapp_brainstem/brainstem.py` | The kernel itself. Flask server. `/chat`, `/agents`, `/health`, `/login`, `/voice`, `/models`, `/version`, `/diagnostics`. Sacred (Constitution Article XXXIII — never edited by AI assistants). |
| `rapp_brainstem/VERSION` | Kernel semver. |
| `rapp_brainstem/agents/basic_agent.py` | Agent ABI. Base class every single-file agent extends. |

Drift check: `bash tests/mirror-drift.sh`

### 🧠 Tier 1 — Brainstem (local Python server)

| Path | Purpose |
|---|---|
| `rapp_brainstem/local_storage.py` | Local JSON storage shim — drop-in for `utils.azure_file_storage`, lets agents written for Azure run unchanged on disk. |
| `rapp_brainstem/soul.md` | Default system prompt. |
| `rapp_brainstem/requirements.txt` | Python deps: flask, flask-cors, requests, python-dotenv, pyzipper. |
| `rapp_brainstem/start.sh`, `start.ps1` | Venv bootstrap + run. |
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
| `rapp_brainstem/agents/experimental/copilot_research_agent.py` | Experimental Copilot-research agent. |

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
| `skill.md` | Top-level agent skill spec (LLM-consumable). |
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
| `rappid.json` | **Mirror-only.** Species root identity — every RAPP descendant's `parent_rappid` chain ends here. |
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

Three `OK` lines = the kernel mirror is byte-identical to grail main. Anything else = drift, restore from grail.
