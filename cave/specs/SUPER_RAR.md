# The Cave super-RAR — the public super-store

> **Retired catalog/download guidance.** For canonicalization, identity, frames,
> wire, eggs, registry, trust, and protocol evolution, follow RAPP/1 rev-5
> through [`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../RAPP1_STATUS.md). The indexes are untrusted
> historical/application observations, not an authenticated §13 registry.

The cave preserves a historical super-RAR design. It is not a current
capability, registry, or public loading service.

<!-- RAPP1-HISTORICAL-SECTION-START -->

- **RAR** (`rar/index.json`) — generated historical observation, not a §13
  registry or load source.
- **super-RAR** (`super-rar/index.json`) — generated historical aggregate, not
  a store or streamable catalog.

## Historical implementation record (inert)

| Part | File | What it does |
|---|---|---|
| **Builder** | `tools/build_super_rar.py` | Historical generator; output remains untrusted. |
| **Agent** | `agents/cave_agent.py` (`@kody-w/cave`) | Retired loader; do not install or invoke it. |
| **Steward** | `agents/rar_steward_agent.py` (`@rapp/rar_steward`) | Historical index-hygiene experiment. |

## Retired direct download

The former no-auth `curl` commands are removed. A hash in `rar/index.json` or
`super-rar/index.json` does not supply an owner signature, trust anchor,
revocation state, or registry freshness. Do not load these candidates into a
brainstem without a future conformant acceptance path.

## Freshness

The checked-in indexes are generated observations and must not be hand-edited
or treated as fresh. This document provides no rebuild or execution CTA.

## Difference from the batcave

The former design compared private and public streaming. Both descriptions are
history, not a current trust or access mechanism.

<!-- RAPP1-HISTORICAL-SECTION-END -->
