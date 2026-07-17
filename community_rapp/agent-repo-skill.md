# Retired host-onboarding record

> **Retired — not a RAPP agent or current installation path.**

This file formerly described a non-RAPP host “skill” that downloaded agents
from another repository. It is retained only as migration context for systems
that consumed the old host convention.

RAPP runtime capabilities are single-file `*_agent.py` agents. This record does
not register, install, download, or authorize an agent, and it does not make
`kody-w/rapp-installer` a public gateway. Current protocol authority and claim
limits are:

- [`RAPP1_AUTHORITY.json`](../RAPP1_AUTHORITY.json)
- [`RAPP1_STATUS.md`](../RAPP1_STATUS.md)

Portable non-RAPP Agent Skills belong in `kody-w/rapp-skills`; conversion into
RAPP requires a separately reviewed single-file agent whose actual source and
manifest remain inspectable.
