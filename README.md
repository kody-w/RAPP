# RAPP

A **mirror** of the RAPP grail kernel at [`kody-w/rapp-installer`](https://github.com/kody-w/rapp-installer).

Per the [Mirror Spec](./pages/vault/Architecture/Mirror%20Spec.md), this repo carries:

1. The three sacred kernel files (`rapp_brainstem/brainstem.py`, `rapp_brainstem/VERSION`, `rapp_brainstem/agents/basic_agent.py`) **byte-identical to grail**.
2. A thin re-fetcher installer (`installer/install.sh`) that pipes grail's installer to bash at install time so the mirror cannot drift.
3. Rappter-owned mirror prerogatives — Pages site (`pages/`), root constitution (`CONSTITUTION.md`), and species-root identity (`rappid.json`).

Everything else — agents beyond grail's bundled set, organs, senses, lineage/bonding lib, rich UI, Tier 2 (Azure Functions) + Tier 3 (Cloudflare Worker) deployments, Rappter narrative docs, vault prose — lives in the sibling **rappter-distro** repo and layers onto the kernel on demand.

## Install

```bash
# Bare kernel (Linux-tarball-equivalent: just brainstem.py + agents/basic_agent.py)
curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash

# Bare kernel + the Rappter distro (full-bodied organism)
curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash -s -- --rappter
```

Any other flag (e.g. `--here`, `--local`) passes straight through to grail's installer.

## Verify the mirror

```bash
for f in rapp_brainstem/brainstem.py rapp_brainstem/VERSION rapp_brainstem/agents/basic_agent.py; do
  diff <(curl -fsSL "https://raw.githubusercontent.com/kody-w/rapp-installer/main/$f") "$f" \
    || echo "DRIFT: $f"
done
```

Three silent diffs = compliant mirror.

## Repo layout

```
rapp_brainstem/        # grail kernel (byte-identical, plus mirror's own soul/index/agents)
installer/             # thin re-fetcher of grail's installer (with --rappter flag)
pages/                 # Pages site, docs, vault, onboarding (mirror prerogative)
CONSTITUTION.md        # protocol governance (peer to README)
rappid.json            # species root identity — every RAPP descendant traces parent back here
```

## Related repos

- [`kody-w/rapp-installer`](https://github.com/kody-w/rapp-installer) — **grail**. The frozen kernel. Never touched.
- [`kody-w/rappter-distro`](https://github.com/kody-w/rappter-distro) — the full-bodied Rappter distro that layers on top.
- [`kody-w/RAR`](https://github.com/kody-w/RAR) — bare-agent registry.
- [`kody-w/rapp_store`](https://github.com/kody-w/rapp_store) — rapplication catalog.
- [`kody-w/RAPP_Sense_Store`](https://github.com/kody-w/RAPP_Sense_Store) — sense catalog.

## Other distros

The kernel doesn't care which distro layers on top. New distros can target different use cases (minimal/research/enterprise/embedded) without forking the kernel. The contract for a valid distro: never modify the three sacred kernel files.
