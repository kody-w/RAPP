---
title: 2026-05-16 — Marie Kondo Audit
status: published
section: Decisions
hook: The policy adopted to drive the kernel-distro split — "if it's not strictly justified for the kernel, it goes in the distro." How that played out in practice + the exceptions.
---

# 2026-05-16 — Marie Kondo Audit

> **Hook.** The policy adopted to drive the kernel-distro split — *"if it's not strictly justified for the kernel, it goes in the distro."* How that played out in practice + the exceptions.

## The policy

Said out loud:

> *"Kernel should be kernel and not just have random stuff. If it's not justified for the kernel and is just a nice-to-have, then put it in the distro. Think Marie Kondo."*

The test for each item:

1. **Does it exist in grail?** (`kody-w/rapp-installer`) — if yes, it stays in the mirror.
2. **Does a SPEC doc reference it as load-bearing?** (e.g., Constitution Article XXXIV.7 references `tools/sign_release.py`) — if yes, it stays.
3. **Would another distro need its own version?** — if yes, the current one is the Rappter distro's, not the kernel's; it goes.
4. **Does it bring the kernel joy?** (Marie Kondo proper.) Pitches that drive adoption, narrative docs that explain the kernel, the audience-facing site — yes. A Pokédex UI for managing organism collections — no.

If a file fails all four tests, it's accretion and goes to the distro.

## What the audit moved

Total: ~15,000 lines deleted from the kernel mirror in commit `32b2497`, picked up by the distro:

| Path | Reason |
|---|---|
| `rapp-zoo/` (~1700 lines) | Pokédex UI for organism collections backed by `.egg` cartridges. Eggs / lineage / bonding all live in distro's `lib/`, so the UI consuming them belongs there too. Constitutionally amended (Article XXXVIII.4). |
| `examples/rapp-commons/` (~376K) | Reference neighborhood implementation. Organism-layer feature; kernel SPEC defines what a neighborhood is, distros provide reference implementations. |
| `rapp_kernel/` (~184K) | Alternate versioned-archive scheme. Grail itself doesn't ship a `rapp_kernel/` directory. Distro-flavored accretion. |
| `tools/{holo_card_generator, rebuild_estate, private_estate_init, import_peer_egg, door_address, backfill_seeds, lan_advertise, front_door_specs, embed_prompts, path_opacity, sim/}` | Organism-layer tools: cards, estates, eggs, doors, seeds, networks, simulations. All distro-flavored. |

## What the audit did NOT move

The pruning intentionally stopped at several lines that *looked* like they should go to the distro but failed the test:

- **`pitch-playbook.html`** — Marie Kondo "no" until you remember it's the kernel's adoption engine. *Without the pitch playbook the kernel never gets adopted.* Stays. See [[2026-05-16 — Why pitch-playbook stays in the kernel]].
- **`tools/sign_release.py`, `ecosystem_audit.py`, `ecosystem_contract.py`, `ecosystem_graph.py`, `sniff_network.py`, `test_brainstem_server.py`** — kernel-relevant tools that the SPEC docs reference. Stay.
- **`tools/templates/`** — templates for the kernel's own emitters. Stay.
- **All the narrative root docs** (MASTER_PLAN, ECOSYSTEM, HERO_USECASE, ANTIPATTERNS, etc.) — explain the kernel; ARE the kernel's god-SPEC content. Stay. See [[2026-05-16 — Restoring narrative docs to the kernel]].
- **T2 (rapp_swarm/) and T3 (worker/, MSFT zip)** — the three-tier Stack is the kernel's identity. Already in grail at root. See [[2026-05-16 — T2 and T3 belong in the kernel]].
- **community_rapp/** — grail-canonical surface, NOT the same thing as the reference neighborhood. See [[2026-05-16 — community_rapp is grail]].

## Mistakes along the way

The first pass over-pruned. T2/T3, community_rapp, the narrative docs, and the pitch-playbook all got migrated to the distro in commit `b4f3e31` before being restored in commit `4f6c14b` once each one's justification became clear. The cost was a noisy git history; the win was that the boundary is now explicit.

Two general lessons:

1. **Marie Kondo bias toward keeping.** If you can't articulate why a file is in the distro in one sentence, keep it in the kernel. The cost of redundant kernel content is much lower than the cost of breaking the SPEC's references.
2. **The SPEC docs are the test fixture.** If the Constitution / ECOSYSTEM / HERO_USECASE references the file as load-bearing, that's the answer. Don't unilaterally amend the SPEC to justify a move; that's the wrong direction.

## See also

- [[2026-05-16 — Kernel-Distro Split]] — the split this policy drove
- [[Adding to the Kernel vs the Distro]] — the decision framework for future contributions
- [[The Kernel-as-God-SPEC]] — the architectural frame the audit honors
- [[2026-05-16 — Why pitch-playbook stays in the kernel]] — the canonical exception
