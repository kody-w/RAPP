# `specs/` — Network protocol specs

This directory holds **network-level protocol specs** — the canonical contracts for how RAPP organisms discover each other, address each other, and federate over the public web.

It is **not** a duplicate of `pages/docs/`. The two directories cover different layers of the platform:

| Layer | Spec home | Question it answers |
|---|---|---|
| Agent contract | [`pages/docs/SPEC.md`](../pages/docs/SPEC.md) | How does a single-file agent work? What's the v1 contract? |
| Network protocol | [`specs/SPEC.md`](./SPEC.md) | How do organisms find and talk to each other across the web? |
| Agent skill (canonical manifest) | [`pages/docs/skill.md`](../pages/docs/skill.md) | The official rendered skill for running RAPP brainstem |
| Network-participation runbook | [`specs/skill.md`](./skill.md) | How does an AI become a 1st-class citizen of the network? |
| Installer skill | [`skill.md`](../skill.md) (root) | How does an LLM install the brainstem on a user's behalf? |

## What's here

- **[`SPEC.md`](./SPEC.md)** — the network protocol spec. Federation, doors, gates, rappid addressing, the canonical raw.githubusercontent.com URL shapes. Schema: `rapp-protocol/1.0`.
- **[`skill.md`](./skill.md)** — the action-oriented companion to `SPEC.md`. Six steps from zero to network citizen.

## Why two directories

Historically, network-protocol specs and agent-contract specs were both called "SPEC" with different scopes. The directories disambiguate them. `pages/docs/` is published through the site (rendered alongside ROADMAP, ESTATE_SPEC, PUBLIC_PRIVATE_BOUNDARY, etc.). `specs/` is the network-layer contract referenced from `examples/`-style implementations and from the Constitution.

When a doc references "the SPEC," the convention is:
- "[v1] SPEC" or "agent SPEC" → `pages/docs/SPEC.md`
- "Network SPEC" or "Protocol SPEC" → `specs/SPEC.md`
