---
title: 2026-05-16 — Kernel-Distro Split
status: published
section: Decisions
hook: RAPP becomes the god SPEC repo for the kernel; rappter-distro is extracted as a sibling carrying the organism layer. The Linux-kernel-and-distros model, applied to the platform.
---

# 2026-05-16 — Kernel-Distro Split

> **Hook.** RAPP becomes the god SPEC repo for the kernel; rappter-distro is extracted as a sibling carrying the organism layer. The Linux-kernel-and-distros model, applied to the platform.

## What changed

The platform had been accumulating organism-layer features inside the kernel mirror (`kody-w/RAPP`) for months — organs, senses, lineage / bonding / egg-cartridge lib, rich UI, additional agents beyond grail's bundle, Rappter-specific narrative documents, ops tooling. The mirror was no longer a kernel mirror in any meaningful sense; it was a Rappter-distro-flavored superset that happened to contain the kernel files.

On 2026-05-16 the split was made explicit:

- **`kody-w/RAPP`** is the **kernel mirror** + the **god SPEC repo**. It carries the full grail kernel tree end-to-end (three sacred files byte-identical to grail, plus the full Tier 1 / Tier 2 / Tier 3 deploy surface, plus all the SPEC documentation, plus the audience-facing Pages site, plus the vault).
- **`kody-w/rappter-distro`** is a **distro** layered on top — organs, senses, lib (bond / egg / lineage / rappid / frames / peer_registry / twin), rich UI (`index.html` 223 KB), post-kernel agents (`swarm_factory`, `learn_new`, `upgrade`), the Pokédex (`rapp-zoo`), organism-layer tools, the reference neighborhood example.

The kernel doesn't care which distro is on top. The distro composes onto the kernel via `sys.modules` shims and the `boot.py` Flask-wrap pattern — without ever editing `brainstem.py`.

## Why now

Two forcing functions arrived in the same week:

1. **Drift from grail.** A drift-check script (`tests/mirror-drift.sh`) made the mirror's mis-alignment with `kody-w/rapp-installer` visible and embarrassing. The mirror was carrying ~1000 lines of post-grail accretion inside `brainstem.py`-adjacent files, plus a tree's worth of extras that grail doesn't ship.
2. **Linux-kernel mental model.** The conceptual frame — *"the brainstem.py is the kernel; everything else is userspace"* — finally clicked. Once you say it out loud, the Rappter Stack's "Brainstem → Swarm → Copilot Studio" looks exactly like *"kernel + distro"* in the Linux world. The distro is the desktop environment; the kernel is the kernel.

## What stayed in the kernel mirror

- Three sacred files (Mirror Spec: byte-identical to grail forever)
- Tier 1 brainstem + Tier 2 Azure Functions (`rapp_swarm/`, `azuredeploy.json`, `deploy.sh`) + Tier 3 (`worker/` Cloudflare + `MSFTAIBASMultiAgentCopilot_*.zip`)
- All grail-canonical files (`community_rapp/`, `docs/`, `blog.html`, `release-notes.html`, `skill.md`, `install.command`)
- All canon SPEC docs (CONSTITUTION, MASTER_PLAN, ECOSYSTEM, HERO_USECASE, ECOSYSTEM_MAP, ANTIPATTERNS, NEIGHBORHOOD_PROTOCOL, OSI, LEXICON, SURVIVAL, DEFINITION_OF_DONE, TRADEMARK, COMMERCIAL, KERNEL_TREE)
- The `pages/` audience site + `pages/kernel.html` hub
- The vault (this folder)
- `pitch-playbook.html` (the adoption engine — see [[2026-05-16 — Why pitch-playbook stays in the kernel]])
- Kernel-relevant tools (`sign_release`, `ecosystem_audit`, `ecosystem_contract`, `ecosystem_graph`, `sniff_network`, `test_brainstem_server`)

## What moved to the distro

- `agents/@rappter/{swarm_factory, learn_new, upgrade}`
- `lib/{bond, egg, lineage, rappid, frames, peer_registry, twin, llm, workspace, index_card, boot}`
- `organs/{estate, lifecycle, neighborhood, neighborhood_membership, swarm_estate}`
- `senses/{voice, twin}`
- `ui/{index.html, web/, tls_proxy.py}`
- `rapp-zoo/` (the Pokédex)
- `examples/rapp-commons/` (reference neighborhood)
- `rapp_kernel/` (alternate versioned-archive scheme)
- Organism-layer tools (holo_card_generator, rebuild_estate, private_estate_init, import_peer_egg, door_address, backfill_seeds, lan_advertise, front_door_specs, embed_prompts, path_opacity, sim/)

## How install changes

The sacred one-liner URL (Constitution Article V) is unchanged:

```bash
curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash
```

You get the bare kernel. To hatch the Rappter distro on top:

```bash
curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash -s -- --rappter
```

Or independently:

```bash
curl -fsSL https://raw.githubusercontent.com/kody-w/rappter-distro/main/install.sh | bash
```

## See also

- [[Mirror Spec]] — the frozen-kernel contract that this split honors
- [[Boot Sidecar — Integrating Utils Without Modifying the Kernel]] — the load-bearing trick that makes the distro work without editing `brainstem.py`
- [[2026-05-16 — Marie Kondo Audit]] — the policy that drove the split
- [[2026-05-16 — Why pitch-playbook stays in the kernel]] — the adoption-engine exception
- [[2026-05-16 — rapp-zoo moves to distro + Article XXXVIII.4 amendment]] — the constitutional impact
- [[The Kernel-as-God-SPEC]] — the architectural frame
- [[Distros as a Pattern]] — the Linux-distros analogy made explicit
