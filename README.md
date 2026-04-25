# RAPP

A local-first AI agent server. Single-file Python agents, no API keys — uses your existing GitHub Copilot OAuth as the LLM backend. Drops in your home directory or any project repo via one curl pipe.

```bash
curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash
```

Brainstem comes up at `http://localhost:7071`. One GitHub account with Copilot access is the only dependency. No OpenAI/Anthropic key. No cloud account. No enterprise gate.

## What an "agent" is here

```python
from agents.basic_agent import BasicAgent

class WeatherAgent(BasicAgent):
    def __init__(self):
        self.name = 'Weather'
        self.metadata = {
            "name": self.name,
            "description": "Get the weather for a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name."}
                },
                "required": ["city"]
            }
        }
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        return f"It's sunny in {kwargs['city']}."
```

Drop that file in `agents/`, it auto-discovers on the next request. The `metadata` is OpenAI function-calling schema; the LLM decides when to invoke `perform()`. No registration step. No build step. No SDK to import.

## Why it might be interesting

- **Single-file plugin contract.** One file = one class = one `metadata` = one `perform()`. Reload-on-disk every request, so you edit and test without restarting the server.
- **GitHub Copilot as the LLM backend.** Exchanges your `gh auth` token for short-lived Copilot API tokens cached in `~/.brainstem/`. No new credentials to manage. (Yes, this is a load-bearing OAuth flow — see the auth chain in `brainstem.py`.)
- **Same file runs on three tiers.** Local Flask server (this repo), Azure Functions deployment in `rapp_swarm/`, and a Cloudflare worker that proxies into Microsoft Copilot Studio in `worker/`. The `*_agent.py` file is the contract; the engine ports.
- **Project-local install mode.** `curl ... | bash -s -- --here` drops the brainstem into `./.brainstem/` in the current directory, picks a free port (7072+), writes a self-contained `start.sh`, and adds itself to the project's `.gitignore`. Runs alongside your global install.
- **Agent-aware install handshake.** Setting `RAPP_INSTALL_ASSIST=1` on the bash side of the pipe makes the installer print a structured prompt (delimited by `<<<RAPP_INSTALLER_HANDSHAKE v=1>>>`) instead of installing — so an LLM running the one-liner on a user's behalf can ask global vs. local before committing. See `skill.md` for the agent protocol.
- **About 1,100 lines of Flask** (`rapp_brainstem/brainstem.py`). The whole engine is one file you can read in an afternoon.

## What it is *not*

- Not a hosted service. There is no SaaS layer; the brainstem runs on your machine.
- Not a framework. Single Python files; no DSL, no decorators, no class hierarchy beyond `BasicAgent`.
- Not a benchmark or eval harness. It's an agent runtime, not a research tool.

## Install modes

```bash
# Global (default — installs at ~/.brainstem, port 7071, with a `brainstem` CLI):
curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash

# Project-local (installs at ./.brainstem/, free port 7072+, gitignored):
curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash -s -- --here

# Pin to a tagged version (immutable per the rollback contract):
curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | BRAINSTEM_VERSION=0.11.6 bash
```

Windows:

```powershell
irm https://raw.githubusercontent.com/kody-w/RAPP/main/installer/install.ps1 | iex
```

## For LLMs running the installer on someone's behalf

Fetch [`skill.md`](https://kody-w.github.io/RAPP/pages/docs/skill.md) and cache it. It documents what RAPP is, when to suggest it, both install modes, and the handshake protocol. The TL;DR: set `RAPP_INSTALL_ASSIST=1` (on the bash side of the pipe — env vars don't propagate across the curl side) and the installer prints a delimited prompt instead of installing.

## Repo layout

| Path | What |
|---|---|
| `rapp_brainstem/` | The engine — Flask server, agent loader, auth chain |
| `rapp_brainstem/agents/` | Showroom (top-level starter agents) + `workspace_agents/` (everything organizational: system, experimental, disabled, local-only, project folders) |
| `rapp_swarm/` | Tier 2 — Azure Functions target |
| `worker/` | Cloudflare auth/proxy worker |
| `rapp_store/` | Catalog of distributable agents |
| `installer/` | Public install surface — one-liner installers (`install.sh` / `install.ps1` / `install.cmd`), `start-local.sh`, `install-swarm.sh`, ARM template, install widget, and the Tier 3 Copilot Studio bundle (`MSFTAIBASMultiAgentCopilot_*.zip`) |
| `CONSTITUTION.md` | Articles governing the repo. Peer of `README.md` at root |
| `pages/docs/` | Reference (`SPEC.md`, `ROADMAP.md`, `AGENTS.md`, `VERSIONS.md`, `skill.md`, `rapplication-sdk.md`) |
| `pages/vault/` | Long-term memory — Obsidian vault of decision narratives (Article XXIII) |
| `pages/` | Audience-facing HTML (faq, leadership, partners, security, …) |
| `index.html` | Landing page at kody-w.github.io/RAPP/ |
| `pitch-playbook.html` | 6-slide narrative for non-technical audiences (see below) |
| `tests/` | Browser + Node test runner |

## Tests

```bash
python3 -m pytest rapp_brainstem/test_local_agents.py -v
node tests/run-tests.mjs   # JS contract tests, no deps
```

Coverage: agent parsing, manifest extraction, byte-equal card↔agent.py round-trip, SHA-256 tamper detection, multi-agent `data_slush` propagation, binder JSON round-trip.

## Browser-only brainstem

`rapp_brainstem/web/index.html` is a client-side brainstem at UI + functional parity with the Flask one — bring your own OpenAI-compatible key, runs entirely in the browser. Multi-agent hot-loading is organized as a card game: deck (everything you've loaded) → hand (currently active) → tap-to-play. A card is a JSON projection of a `*_agent.py` with the source embedded and SHA-256-hashed; cards round-trip to/from `.py` byte-for-byte through the same code path as raw imports.

## The pitch (non-technical companion)

If you're not the audience for the rest of this README, [**pitch-playbook.html**](https://kody-w.github.io/RAPP/pitch-playbook.html) is a 6-slide deck that frames RAPP as an *adoption layer* on top of whatever AI tools your team already pays for — built for execs and team leads. Same product, different conversation. The marketing tagline that lives there and on the landing page is *"portable, shareable, vibe swarm building tool"* — accurate, but optimized for prospects who care about team adoption, not for engineers reading code.

## Constitution & spec

- [`CONSTITUTION.md`](./CONSTITUTION.md) — articles governing what belongs, what's sacred, what's ruled out. Worth a skim if you want to contribute.
- [`pages/docs/SPEC.md`](./pages/docs/SPEC.md) — the v1 contract for the single-file agent format. Frozen on purpose; the agent contract is the API.

## The vault

[`pages/vault/`](./pages/vault/) is the platform's second-brain wiki — the *why* behind every decision, captured as long-form notes. It's a real Obsidian vault (open with *File → Open folder as vault*) and it's also rendered as a static site at [`pages/vault/`](https://kody-w.github.io/RAPP/pages/vault/) with wikilinks, backlinks, full-text search, a graph view, and JSZip export to a portable Obsidian-compatible bundle.

Start with [`pages/vault/Foundations/The Platform in 90 Seconds.md`](./pages/vault/Foundations/The%20Platform%20in%2090%20Seconds.md) or pick a [reading path](./pages/vault/Reading%20Paths/) by audience (engineer, architect, partner, exec, contributor). The vault is mandated by Constitution Article XXIII — when you make a decision worth remembering, write it as a vault note rather than burying it in a commit message.

## Versioning & rollback

Every release is tagged `brainstem-v<X.Y.Z>` and tags are immutable. To pin (or roll back if something wobbles):

```bash
curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | BRAINSTEM_VERSION=0.11.6 bash
```

The installer honors `BRAINSTEM_VERSION` by checking out the matching tag and resetting to it. See Constitution Article VIII for the full release discipline.

## History

The previous engine code that lived in this repo (the Rapp intelligence engine for Rappterbook) is preserved on the `archive/engine` branch — the "genetic twin" referenced in SPEC §16.
