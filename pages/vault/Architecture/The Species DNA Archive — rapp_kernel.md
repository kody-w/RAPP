---
title: The Species DNA Archive — rapp_kernel
status: historical
section: Architecture
hook: Historical rapp_kernel archive design, superseded by the immutable three-file KERNEL_PIN grail record.
---

# The Species DNA Archive — `rapp_kernel/`

> **SUPERSEDED archive design — historical record only.** For
> canonicalization, identity, frames, wire, eggs, registry, trust, and protocol
> evolution, follow RAPP/1 rev-5 through
> [`RAPP1_AUTHORITY.json`](../../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../../RAPP1_STATUS.md). Current frozen kernel evidence
> is exactly the three hashes in [`KERNEL_PIN.json`](../../../KERNEL_PIN.json)
> for `kody-w/rapp-installer@brainstem-v0.6.9`. The local `rapp_kernel/`
> archive and its former moving alias are non-authoritative history.

<!-- RAPP1-HISTORICAL-SECTION-START -->

> **Hook.** `rapp_kernel/` is the public, permanent, versioned source of truth for every kernel that has ever shipped. Four files per version, frozen URLs forever, drift-detected against the running brainstem. The species' fossil record.

## Why this directory exists

The repository at `kody-w/RAPP` is more than a place where the brainstem source lives. By **Constitution Article V** (the install one-liner is sacred) and **Article XXXIV** (rappid + variant lineage), this repo is **publicly load-bearing**: anyone in the world, on any machine, in any variant, must be able to fetch the exact bytes of any kernel version that has ever shipped. Forever.

That promise can't live inside `rapp_brainstem/` alone, because `rapp_brainstem/` is the **current runtime** — it carries one version at a time, plus all the body functions, senses, agents, and state that aren't kernel. To ship the species' history, you need an archive that is:

- **Versioned** — every release preserved at a separate URL.
- **Immutable** — old versions never edited, only added to.
- **Pure** — only the four files Article XXXIII §1 names as kernel DNA.
- **Discoverable** — a manifest you can read programmatically.
- **Verifiable** — checksums you can compare against bytes you fetched.

`rapp_kernel/` is that archive.

## Layout

```
rapp_kernel/
├── README.md
├── manifest.json
└── v/
    └── 0.12.2/
        ├── brainstem.py
        ├── basic_agent.py
        ├── context_memory_agent.py
        ├── manage_memory_agent.py
        ├── VERSION
        └── checksums.txt
```

The diagram originally included a moving alias. That alias is intentionally
omitted here because it is not a current verification source. Versioned
`v/<n>/` directories remain historical snapshots only; they do not supersede
the immutable `KERNEL_PIN.json` grail tag and hashes.

## The four files

Per **Constitution Article XXXIII §1**, the kernel DNA is exactly:

| File | Role |
|---|---|
| `brainstem.py` | The Flask kernel: chat, agents, voice slot, Copilot auth, agent loader, LLM loop. |
| `basic_agent.py` | The base class every agent extends. Defines the `name + metadata + perform()` contract. |
| `context_memory_agent.py` | System-context contributor (every chat turn pulls long-term memory into the prompt). |
| `manage_memory_agent.py` | Tool-call interface for save / recall / list memory. |

These four files are the species. Everything else — body functions, senses, agents beyond the memory pair, the boot wrapper, web assets, state directories — is body, mutation, or musculature. They live in `rapp_brainstem/`, never in `rapp_kernel/`.

## URLs are load-bearing

Per **Constitution Article V**, URLs under this directory are **public infrastructure**. They cannot move, change shape, or be deleted. Examples:

- `https://kody-w.github.io/RAPP/rapp_kernel/manifest.json`
- `https://kody-w.github.io/RAPP/rapp_kernel/v/0.12.2/brainstem.py`
- `https://kody-w.github.io/RAPP/rapp_kernel/v/0.12.2/checksums.txt`

These URLs record the historical design. They are not current installer,
authority, or acceptance URLs. Current frozen-byte verification uses the
immutable grail tag and hashes in `KERNEL_PIN.json`.

## Variant inheritance

When a user creates a variant master per **Article XXXIV.3** (laying an egg that becomes a new species), their variant repo inherits the same `rapp_kernel/` shape. From day one, the variant has its own `rapp_kernel/v/<version>/` paths under its own GitHub Pages. Consumers of the variant get the same pinned-version contract that `kody-w/RAPP` provides — pinning is not a master-only privilege, it's a property of the platform.

## Drift detection

The former fixture suite included
`tests/organism/09-rapp-kernel-archive.sh`; it is retired migration evidence.
Current verification checks the three pinned local bytes. The historical test
was intended to catch:

- Editing a kernel file in `rapp_brainstem/` without updating the archive
- Editing files inside an existing `v/<version>/` directory (which is forbidden)
- A `v/<version>/checksums.txt` whose bytes don't match the files next to it

If any of those conditions hold, the test fails. The archive cannot quietly drift.

## Adding a new version

When the kernel is updated (rare — Article XXXIII §4 keeps the bar high):

1. Bump `rapp_brainstem/VERSION` to the new number.
2. Historical step retired; do not update a moving alias.
3. Create a new directory `rapp_kernel/v/<new>/` with the same four files plus a fresh `checksums.txt` (`shasum -a 256 *.py VERSION > checksums.txt`).
4. Historical step retired; current grail changes require an explicit authority
   event and a new immutable pin.
5. **Never** modify any existing `rapp_kernel/v/<old>/` directory. If 0.12.2 had a bug, the fix is 0.12.3. 0.12.2's bytes stay exactly as they were.

The fixture suite passes only when steps 1–4 are all done in the same change.

## What this directory is not

- **Not a runtime.** Nothing in `rapp_kernel/` is current executable or
  acceptance guidance. It is a historical reference archive.
- **Not exhaustive.** It contains four files. The wider rapp_brainstem ecosystem — body functions, senses, sense viewers, additional agents, the boot wrapper, the install scripts, the web UI — is not here. This directory is pure kernel DNA, not the whole organism.
- **Not authority.** A versioned historical snapshot does not override
  `KERNEL_PIN.json` or RAPP/1.

## See also

- [Constitution Article XXXIII](../../../CONSTITUTION.md) — Digital Organism. Names the four files as DNA.
- [Constitution Article XXXIV §6](../../../CONSTITUTION.md) — The species DNA archive subsection.
- [Constitution Article V](../../../CONSTITUTION.md) — Install one-liner and URL-stability promise.
- [[Boot Sidecar — Integrating Utils Without Modifying the Kernel]] — how everything else gets wired in around this DNA.
- [[Fixture 01 — Canonical Kernel local_storage Drop-In]] — what happens when the archive lacks a sibling the kernel needs.

<!-- RAPP1-HISTORICAL-SECTION-END -->
