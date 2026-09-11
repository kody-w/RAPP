# RAPP estate protocols

These application profiles extend RAPP/1 by registration rather than changing
the frozen RAPP/1 frame envelope.

| Protocol | Purpose | Conformance |
|---|---|---|
| [`rapp-hive/1`](rapp-hive/1/SPEC.md) | Private Hive workspaces, generic RAPP objects, sealed GODD rooms, PII-free DOGG, Dream Catcher convergence, and multi-channel projection | `python3 rapp-hive/1/reference/hive_conformance.py` |

An estate activates a profile through an owner-signed RAPP/1 `protocol`
registry entry pinning this repository, the normative path, and exact SHA-256.

