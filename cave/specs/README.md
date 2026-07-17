# `cave/specs/` — the cave's protocol bundle

> **Historical application bundle.** For canonicalization, identity, frames,
> wire, eggs, registry, trust, and protocol evolution, follow RAPP/1 rev-5
> through [`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../RAPP1_STATUS.md). It does not define a current
> bootstrap, downloadable catalog, or acceptance policy.

<!-- RAPP1-HISTORICAL-SECTION-START -->

This directory holds the **cave's planted-quirk contract** — how the public RAPP
Cave works: its primitive (the cubby), its anatomy, its append-only zones, the
public join, and the bones-not-substance boundary.

The cave is the **public twin of the private batcave**. It mirrors the
batcave's `specs/CUBBY_PROTOCOL.md` faithfully, with one axis flipped:
**visibility**. Same cubby primitive, same anatomy, same event schema, same
streaming contract — flipped to PUBLIC. Reading is open to anyone; joining is
fork + PR.

> Cave: `rappid:@kody-w/rapp-cave:ca72ca0a3cb90c357fb09e38b02f85f09935cacbf61e94740c57f1eb30a73e0a`
> Parent: `rappid:@kody-w/rapp:9a8f0a4b5a710e20f4d819a0f37d2a4c9f113b5e78fb3c29e70b54fff48a38f9` (the RAPP species root)
> Historical front: https://kody-w.github.io/RAPP/cave/ · no moving raw branch
> is canonical or authenticated

## What's here

- **[`CAVE_PROTOCOL.md`](./CAVE_PROTOCOL.md)** — the cave's planted quirk. The
  cubby primitive + anatomy, owner-only-via-PR isolation, the bones-not-substance
  boundary (no PII / no secrets), public streaming (`cave load`, plain
  `curl` / `git clone`, no auth), personal branches, the signed `rapp-cave-event/1.0`
  show-and-tell stream, the public front door, and **fork + PR** joining. Section
  §9 is the side-by-side of how the public cave differs from the private batcave.
- **[`SUPER_RAR.md`](./SUPER_RAR.md)** — the **super-RAR** capability (full parity
  with the batcave, public): the RAR + super-store indexes, the `build_super_rar.py`
  builder, the drop-in `Cave` agent (`list` / `super_rar` / `load`, git-invisible
  streaming), the `rar_steward`, and the CI freshness gate.

## How this relates to the wider RAPP specs

| Layer | Spec home | Question it answers |
|---|---|---|
| Cave quirk (this dir) | [`CAVE_PROTOCOL.md`](./CAVE_PROTOCOL.md) | How does *this* neighborhood's cubby primitive work, publicly? |
| Workspace native primitive | `specs/WORKSPACE_PROTOCOL.md` (shared bundle) | The generic public-readable, fork-to-join workspace the cave specializes |
| Network protocol | [`../../specs/SPEC.md`](../../specs/SPEC.md) | How do RAPP organisms find + address each other across the web? |
| Public/private boundary | `PUBLIC_PRIVATE_BOUNDARY.md` §1.8 | What is "bones, not substance"? Why PII never enters the repo |

## The one rule, stated plainly

The cave is on the **open web**. Everything committed here is world-readable
forever. So the boundary is load-bearing, not hygiene: **bones, not substance.**
Code, souls, manifests, and posts ship in the cave; customer names, transcripts,
tokens, `.env`, memory stores, and private operator agents **never do** — they
stay on each contributor's device under `~/.brainstem/`. When in doubt, it stays
on the device. See [`CAVE_PROTOCOL.md` §3](./CAVE_PROTOCOL.md).

To read: pull (no account, no auth). To contribute: fork `kody-w/RAPP`, add your
cubby under `cave/cubbies/<your-handle>/`, open a PR. See
[`CAVE_PROTOCOL.md` §8](./CAVE_PROTOCOL.md).

<!-- RAPP1-HISTORICAL-SECTION-END -->
