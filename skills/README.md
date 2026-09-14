# RAPP skills

These skills operate the [RAPP Work](../docs/rapp-work.md) layer while keeping
RAPP/1 identity, frame, egg, signature, and registry invariants intact.

| Skill | Purpose |
|---|---|
| [`autonomous-rapp-estate-manager`](autonomous-rapp-estate-manager/SKILL.md) | Establish, organize, verify, and maintain a full pointer-only local AI estate from one shareable skill. |
| [`rapp-private-hive`](rapp-private-hive/SKILL.md) | Prepare an existing local RAPP workspace for additive, no-data-loss Private Hive deployment under `rapp-hive/1`. |

Skills are application tooling, not protocol authority. RAPP/1 remains
authoritative for identity, frames, canonicalization, eggs, signatures, and
registry adoption. The normative Private Hive profile lives at
[`protocols/rapp-hive/1`](../protocols/rapp-hive/1/SPEC.md), which is subordinate
to the canonical [`kody-w/rapp-1`](https://github.com/kody-w/rapp-1) protocol.
