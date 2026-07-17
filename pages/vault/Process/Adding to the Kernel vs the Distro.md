---
title: Adding to the Kernel vs the Distro
status: historical
section: Process
hook: Decision framework for new contributions. Three tests — does grail ship it, does the SPEC reference it as load-bearing, would another distro need its own version? If any answer is yes, it belongs in the kernel. Otherwise it's distro.
---

# Adding to the Kernel vs the Distro

> **HISTORICAL CONTRIBUTION RUNBOOK — superseded current guidance.** The
> bounded body preserves dated kernel/distro process and must not direct edits
> to pinned bytes. For canonicalization, identity, frames, wire, eggs,
> registry, trust, and protocol evolution, follow RAPP/1 rev-5 through
> [`RAPP1_AUTHORITY.json`](../../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../../RAPP1_STATUS.md).

<!-- RAPP1-HISTORICAL-SECTION-START -->

> **Hook.** Decision framework for new contributions. Three tests — does grail ship it, does the SPEC reference it as load-bearing, would another distro need its own version? If any answer is yes, it belongs in the kernel. Otherwise it's distro.

## The decision

When you're about to add a file to the platform, ask:

### Test 1 — Does grail ship it?

```bash
gh api /repos/kody-w/rapp-installer/contents/<path> 2>&1 | head -5
```

If grail has a file at this path (or a directory by this name), it's kernel. Period. Even if it doesn't *feel* like SPEC material to you (an HTML page, a deploy artifact, a community-side install script), grail's authorial judgment is final on what's kernel.

### Test 2 — Does the SPEC reference it as load-bearing?

Grep CONSTITUTION + the canonical docs:

```bash
grep -rlE "$(basename <new-file>)" CONSTITUTION.md MASTER_PLAN.md ECOSYSTEM.md HERO_USECASE.md pages/docs/*.md
```

If CONSTITUTION cites the file (e.g., Article XXXIV.7 references `tools/sign_release.py`), it's kernel-load-bearing. The SPEC's references must work; broken references mean broken SPEC.

### Test 3 — Would another distro need its own version?

Think hypothetically: if a `minimal-distro` or `enterprise-distro` were built, would it ship its OWN version of this file? If yes, the current file is *this distro's* implementation, not the kernel's interface — it belongs in the distro.

Examples:
- `bond.py` (egg cartridge packer) — a minimal distro probably uses a different egg format or no eggs at all. **Distro.**
- `brainstem.py` — every distro must use the same kernel. **Kernel (grail-canonical, sacred).**
- `azuredeploy.json` — every distro that wants Tier 2 deploys the same ARM template. **Kernel (grail-canonical).**
- `holo_card_generator.py` — only distros that ship a Pokédex need it. **Distro.**

## The hierarchy of answers

If any of the three tests is "yes," the file is kernel:

| Test | If yes → |
|---|---|
| Grail ships it | Kernel (no further argument; grail is final) |
| SPEC references it as load-bearing | Kernel (the SPEC owns it) |
| Another distro would NOT ship its own version | Kernel (it's a universal interface, not a distro implementation) |

If all three are "no," the file is distro.

## The adoption-engine exception

One narrow override: even if the three tests say "distro," the file stays in the kernel if it's **load-bearing for kernel adoption**. The canonical example is `pitch-playbook.html` — grail doesn't ship it, SPEC doesn't reference it, no other distro needs a copy. But removing it weakens kernel adoption, so it stays. See [[2026-05-16 — Why pitch-playbook stays in the kernel]].

This exception is narrow. It does not justify:
- Sales material for specific distros (lives in that distro)
- Pitch material for downstream services (consulting, support)
- Anything that contradicts the kernel SPEC

## Borderline cases (and how to resolve)

When the three tests give ambiguous answers:

- **The file is in grail's tree but only as a stub or example** — counts as grail-canonical. Kernel.
- **The SPEC references the file but only in a "see also" footer** — still load-bearing. Kernel.
- **A second distro could plausibly fork this file and ship its own version, but for now there's only one distro** — distro. Future-proof for the multi-distro world.
- **The file is documentation that explains the kernel but isn't itself in grail** — kernel. The kernel's own narrative belongs with the kernel. See [[2026-05-16 — Restoring narrative docs to the kernel]].

If still ambiguous after the three tests + the exception: **prefer kernel.** The cost of redundant kernel content is much lower than the cost of breaking SPEC references when a file moves.

## What this implies for distros

Distros should pre-declare which files they own. Today only `kody-w/rappter-distro` exists; future distros should ship a similar `MIGRATION_NOTES.md` or `distro.json` enumerating what they add on top of the kernel. That makes the kernel/distro boundary auditable, not implicit.

## See also

- [[The Kernel-as-God-SPEC]] — the architectural frame
- [[2026-05-16 — Marie Kondo Audit]] — the policy this codifies
- [[Distros as a Pattern]] — what a valid distro looks like
- [[2026-05-16 — Why pitch-playbook stays in the kernel]] — the canonical exception
- [[Grail is GitHub, not local]] — how to do Test 1 correctly

<!-- RAPP1-HISTORICAL-SECTION-END -->
