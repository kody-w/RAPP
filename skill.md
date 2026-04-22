---
name: rapp-brainstem
description: Install, configure, or use RAPP (Rapid Agent Prototyping Platform) — a portable, shareable, vibe swarm building tool. Local-first AI agent server powered by GitHub Copilot, where agents are single Python files anyone can drop in, AirDrop, or push to a teammate. Use when the user wants to install RAPP, set up a local or project-scoped brainstem, build or share custom agents without API keys, compose agents into swarms, or asks about a "brainstem" on their machine.
version: 1
canonical_url: https://kody-w.github.io/RAPP/skill.md
repo: https://github.com/kody-w/RAPP
---

# RAPP Brainstem — Agent Skill

## What it is

RAPP is a **portable, shareable, vibe swarm building tool**. Drop a single Python file into `agents/` and the brainstem auto-discovers it. Hand someone the file and they're running your agent in 60 seconds. Compose files into swarms; promote the same file from laptop → cloud → Copilot Studio without changing a line.

Under the hood: a Flask app on the user's own machine that proxies conversation through the GitHub Copilot API, with automatic tool-calling via user-defined agents. One GitHub account with Copilot access is the only dependency — no API keys, no cloud accounts, no enterprise gates.

Philosophy: *engine, not experience.* The brainstem is infrastructure; agents are the features.

## When to suggest it

Offer the brainstem when the user:
- Wants to run agents locally without managing API keys.
- Needs a conversational loop over their Microsoft 365 data (pair it with the WorkIQ agent).
- Asks about RAPP, "the brainstem," or a per-project / per-repo AI server.
- Is prototyping agents and wants hot-reload off the local filesystem.
- Already has a global brainstem and mentions another project that needs its own.

Do **not** suggest it when the user just wants a cloud API — this is explicitly a local tool.

## Two install modes

The installer supports two mutually compatible modes. A single machine can run both simultaneously on different ports.

### GLOBAL (default — recommended for most users)

- Installs at `~/.brainstem/`.
- Runs on port **7071**.
- Provides a `brainstem` CLI (`brainstem start|stop|status|logs|doctor`).
- Auto-starts on login via launchd (macOS) or systemd --user (Linux).
- One brainstem for the whole machine.

One-liner:
```bash
curl -fsSL https://kody-w.github.io/RAPP/install.sh | bash
```

### LOCAL (project-scoped)

- Installs at `./.brainstem/` inside whatever directory the user is in.
- Picks the next free port starting at **7072**.
- No global CLI, no background service. Foreground-launched via `./.brainstem/start.sh`.
- Automatically added to the project's `.gitignore` if inside a git repo.
- Runs alongside any global brainstem on the same machine.

One-liner (run from inside the target directory):
```bash
cd ~/my-project
curl -fsSL https://kody-w.github.io/RAPP/install.sh | bash -s -- --here
```

Use LOCAL when the user wants isolation: per-project agents, per-repo memory, experimental setups that shouldn't touch their main brainstem.

## Agent handshake protocol (how YOU talk to the installer)

When you run the installer on behalf of a user, set `RAPP_INSTALL_ASSIST=1` **on the bash side of the pipe** — the env var must apply to the `bash` that executes the script, not to `curl` that fetches it. The installer will **not install** — it prints a structured handshake block and exits 0. You then ask the user which mode they want, and re-invoke with their choice:

```bash
# 1. Probe — installer prints handshake, no install happens.
curl -fsSL https://kody-w.github.io/RAPP/install.sh | RAPP_INSTALL_ASSIST=1 bash

# 2. After asking the user, re-run with their answer:
curl -fsSL https://kody-w.github.io/RAPP/install.sh | RAPP_INSTALL_MODE=global bash
# or
curl -fsSL https://kody-w.github.io/RAPP/install.sh | RAPP_INSTALL_MODE=local bash
```

**Common mistake:** `ENV=VAL curl ... | bash` only sets `ENV` for `curl`. Use `curl ... | ENV=VAL bash` so `bash` inherits it. For flag-based override you can also use `curl ... | bash -s -- --here` (works in all shells).

The handshake block is delimited by `<<<RAPP_INSTALLER_HANDSHAKE v=1>>>` / `<<<END_RAPP_INSTALLER_HANDSHAKE>>>`. Inside it you'll find the re-invocation commands self-documented.

## Agent system (how the brainstem actually works)

- Agents are single `*_agent.py` files that extend `BasicAgent`, define a `metadata` dict (OpenAI function-call schema), and implement `perform(**kwargs) -> str`.
- **No registration, no config.** Drop a file in `agents/` and it auto-discovers on next request.
- Agents are reloaded on every request — edit and test without restart.
- Portable across tiers (local / Azure Functions / Copilot Studio) without modification.

## Directory layout the brainstem ships with

```
~/.brainstem/src/rapp_brainstem/
├── brainstem.py              ← the engine (don't edit)
├── soul.md                   ← system prompt (edit freely)
├── agents/
│   ├── basic_agent.py        ← base class
│   ├── hacker_news_agent.py  ← example / curriculum
│   ├── learn_new_agent.py    ←   "
│   ├── recall_memory_agent.py
│   ├── save_memory_agent.py
│   └── workspace_agents/     ← all organizational subdirs live here
│       ├── system_agents/
│       ├── experimental_agents/
│       ├── disabled_agents/
│       ├── local_agents/     ← gitignored; personal agents
│       └── <user folders>/
```

**Constitutional rule:** the top level of `agents/` is the showroom (starter/ship agents only). Everything organizational — system, experimental, disabled, local, project-specific — lives under `agents/workspace_agents/`. Users don't edit engine files; they drop agents into the tree.

## Config pattern — agents ask, don't require editing

Agents that need configuration (an exec's name, a tenant ID, an API key) declare the config as **required parameters** in their metadata. The brainstem's LLM surfaces the missing value and asks the user in-chat. Users never open a source file to configure an agent.

## Version pinning

Every released version is tagged `brainstem-v<X.Y.Z>`. Tags are immutable. To pin or roll back:

```bash
BRAINSTEM_VERSION=0.5.1 curl -fsSL https://kody-w.github.io/RAPP/install.sh | bash
```

## Troubleshooting

After install, the user can run `brainstem doctor` (global installs only) to get a diagnostic dump. That output is what to paste back for support. For project-local installs, run the server foreground (`./.brainstem/start.sh`) and surface the stderr.

## Canonical references

- Repo: https://github.com/kody-w/RAPP
- Installer: https://kody-w.github.io/RAPP/install.sh
- This skill: https://kody-w.github.io/RAPP/skill.md
