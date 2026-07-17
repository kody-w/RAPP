# `specs/` — Network protocol specs

> **Current RAPP/1 authority (rev-5).** For canonicalization, identity, frames,
> wire, eggs, registry, trust, and protocol evolution, follow
> [`RAPP1_AUTHORITY.json`](../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../RAPP1_STATUS.md). Files in this directory are either
> product runbooks, generated mirrors, or superseded protocol history.

This directory preserves network-level product documentation. It is not a
second protocol authority.

It is **not** a duplicate of `pages/docs/`. The two directories cover different layers of the platform:

| Layer | Spec home | Question it answers |
|---|---|---|
| Historical agent contract | [`pages/docs/SPEC.md`](../pages/docs/SPEC.md) | What did the pre-RAPP/1 single-file-agent platform contract say? |
| Historical network protocol | [`specs/SPEC.md`](./SPEC.md) | What did the retired network contract teach? |
| Historical host onboarding | [`pages/docs/skill.md`](../pages/docs/skill.md) | What retired installer and host guidance was previously advertised? |
| Historical network runbook | [`specs/skill.md`](./skill.md) | What pre-RAPP/1 participation flow was retired? |
| Historical installer runbook | [`skill.md`](../skill.md) (root) | What Tier 1/2/3 onboarding commands must no longer be executed? |

## What's here

- **[`SPEC.md`](./SPEC.md)** — superseded `rapp-protocol/1.0` history for
  migration analysis; it is not current protocol.
- **[`skill.md`](./skill.md)** — archived action-oriented companion. Its six
  steps are not current instructions.

## Why two directories

Historically, network-protocol specs and agent-contract specs were both called "SPEC" with different scopes. The directories disambiguate them. `pages/docs/` is published through the site (rendered alongside ROADMAP, ESTATE_SPEC, PUBLIC_PRIVATE_BOUNDARY, etc.). `specs/` is the network-layer contract referenced from `examples/`-style implementations and from the Constitution.

When a doc references "the SPEC," the convention is:
- "[v1] SPEC" or "agent SPEC" → `pages/docs/SPEC.md`
- "Network SPEC" or "Protocol SPEC" → `specs/SPEC.md`
