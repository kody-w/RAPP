# CLAUDE.md

This file guides Claude Code when working in this repository.

## What this repo is

**`kody-w/RAPP` is a mirror** of the RAPP grail kernel at [`kody-w/rapp-installer`](https://github.com/kody-w/rapp-installer). Per the [Mirror Spec](./pages/vault/Architecture/Mirror%20Spec.md), a valid mirror keeps three files byte-identical to grail and ships a thin re-fetcher installer.

This repo **is not** the place to add features. New agents, organs, senses, UI, deployment infra, narrative docs → go to the [`kody-w/rappter-distro`](https://github.com/kody-w/rappter-distro) repo (the full-bodied Rappter distro that layers on top of the kernel).

## What you must never touch

- `kody-w/rapp-installer` (grail). **Read-only forever.** Never push, never modify. The local clone at `~/Documents/GitHub/Rappter/rapp-installer/` is also read-only.
- `rapp_brainstem/brainstem.py` — kernel file. Byte-identical to grail. The only acceptable "edit" is `cp` from grail.
- `rapp_brainstem/VERSION` — kernel version. Byte-identical to grail.
- `rapp_brainstem/agents/basic_agent.py` — agent ABI. Byte-identical to grail.

Per Constitution Article XXXIII, these are the digital organism's DNA — universal, drop-in replaceable, never edited by AI assistants.

## What lives here (the mirror)

| Path | Purpose |
|---|---|
| `rapp_brainstem/` | Grail kernel + grail-bundled agents (context_memory, manage_memory, hacker_news, onboarding, experimental/) |
| `rapp_brainstem/local_storage.py` | Sibling storage shim (mirrors grail layout) |
| `installer/install.{sh,ps1,cmd}` | Thin re-fetchers of grail's installer. Pass `--rappter` to also hatch rappter-distro. |
| `pages/` | Audience-facing site, docs, vault prose (mirror prerogative per Mirror Spec) |
| `CONSTITUTION.md` | Protocol governance (peer to README at root) |
| `rappid.json` | Species root identity — every RAPP descendant's `parent_rappid` chain ends here |
| `LICENSE`, `LICENSE-DOCS`, `index.html`, `404.html` | Repo + Pages root |

## What lives in the distro (not here)

If a user asks you to add any of these, redirect to `kody-w/rappter-distro`:

- Single-file `*_agent.py` files beyond grail's bundle (swarm_factory, learn_new, upgrade)
- Organs (`*_organ.py`) — HTTP route extensions under `/api/<name>/*`
- Senses (`*_sense.py`) — chat response channels (voice, twin)
- Lineage/bonding/egg cartridge lib (`bond.py`, `egg.py`, `lineage.py`, `rappid.py`, `frames.py`, etc.)
- Rich UI (`index.html` larger than grail's, web assets, tls_proxy)
- Tier 2 (Azure Functions swarm), Tier 3 (Cloudflare Worker, Copilot Studio bundle)
- Ops tooling (ecosystem audit, graph, rebuild_estate, sign_release)
- Rappter narrative docs (ECOSYSTEM, HERO_USECASE, ANTIPATTERNS, NEIGHBORHOOD_PROTOCOL, OSI, MASTER_PLAN, etc.)
- Obsidian vault prose for distro decisions (the kernel-protocol vault notes stay in `pages/vault/`)

## Commands

```bash
# Run the bare kernel locally
cd rapp_brainstem
./start.sh                              # creates venv, runs brainstem on :7071
python brainstem.py                     # direct run (deps already installed)

# Run grail's kernel tests
python3 -m pytest rapp_brainstem/test_local_agents.py -v
python3 -m pytest rapp_brainstem/test_hatch_rapp_agent.py -v

# Mirror Spec drift check (should be silent)
for f in rapp_brainstem/brainstem.py rapp_brainstem/VERSION rapp_brainstem/agents/basic_agent.py; do
  diff <(curl -fsSL "https://raw.githubusercontent.com/kody-w/rapp-installer/main/$f") "$f" \
    || echo "DRIFT: $f"
done
```

## Install URLs are sacred (Constitution Article V)

```
curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash
```

Never relocate `installer/install.sh`. The URL shape is sacred. Internally it's a thin re-fetcher of grail's installer; that's where install logic lives.

## Related repos in the ecosystem

- [`kody-w/rapp-installer`](https://github.com/kody-w/rapp-installer) — **grail**. The frozen kernel. Read-only.
- [`kody-w/rappter-distro`](https://github.com/kody-w/rappter-distro) — the full-bodied Rappter distro.
- [`kody-w/RAR`](https://github.com/kody-w/RAR) — bare-agent registry / trust layer.
- [`kody-w/rapp_store`](https://github.com/kody-w/rapp_store) — rapplication catalog.
- [`kody-w/RAPP_Sense_Store`](https://github.com/kody-w/RAPP_Sense_Store) — sense catalog.

## When in doubt

- Reading the kernel? Read `rapp_brainstem/brainstem.py`.
- Want to add a feature? Don't add it here. Add it to `rappter-distro`.
- Want to ship a different distro? Create a new sibling repo. The contract: never touch the three sacred files.
- Need to update the kernel? You can't. Only `kody-w/rapp-installer` (grail) gets new kernel versions, and that's a manual op by Kody — never an AI action.
