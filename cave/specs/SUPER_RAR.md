# Cave RAR ledgers — retired

Read [`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json) and
[`RAPP1_STATUS.md`](../../RAPP1_STATUS.md) first. The Cave RAR and super-RAR are
not RAPP/1 registries, catalogs, stores, download indexes, or acceptance
sources.

## Current disposition

- `rar/index.json`, `super-rar/index.json`, `cubbies/index.json`, and
  `facets.json` are sealed historical ledgers.
- Every retained entry is explicitly `retired`, `streamable: false`, and
  `active_distribution: false`.
- Repository-relative paths and SHA-256 values preserve historical integrity
  evidence only. They authorize no fetch, installation, import, execution, or
  trust decision.
- `agents/cave_agent.py` and `agents/rar_steward_agent.py` are fail-closed
  tombstones. The steward performs no network access, catalog curation, GitHub
  issue creation, repository write, or installation.
- `tools/build_super_rar.py --check` is a read-only containment validator. It
  cannot rebuild, discover, refresh, or write an index.
- `.github/workflows/cave-super-rar.yml` runs only that inert-ledger check. It
  packages and publishes nothing.

The prepared `cave/rapplications/rapp-installer/` subtree and retained egg bytes
remain immutable historical evidence. No Cave process may turn them into an
executable distribution.
