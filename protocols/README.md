# RAPP estate protocols

These application profiles extend RAPP/1 by registration rather than changing
the frozen RAPP/1 frame envelope.

They are the protocol layer of [RAPP Work](../docs/rapp-work.md): business
collaboration and compliance while retaining byte-level RAPP/1 conformance.

| Protocol | Purpose | Conformance |
|---|---|---|
| [`rapp-hive/1`](rapp-hive/1/SPEC.md) | Private Hive workspaces, generic RAPP objects, sealed GODD rooms, PII-free DOGG, Dream Catcher convergence, and multi-channel projection | `python3 rapp-hive/1/reference/hive_conformance.py` |
| [`rapp-federation/1`](rapp-federation/1/SPEC.md) | The universal logical Hive Mind: consent-bound business collaboration among sovereign Private Hives, including delay-tolerant exchange and durable receipts | `python3 rapp-federation/1/reference/conformance.py --report rapp-federation/1/conformance-results.json` |

An estate activates a profile through an owner-signed RAPP/1 `protocol`
registry entry pinning this repository, the normative path, and exact SHA-256.
The checked-in federation implementation is a bounded candidate receiver, not
evidence that any estate has activated the profile or deployed a galactic
transport network.
