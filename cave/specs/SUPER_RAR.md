# The Cave super-RAR — retained observation, safe adapters

For canonicalization, identity, frames, wire, eggs, registry, trust, and
protocol evolution, follow RAPP/1 rev-5 through
[`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json) and
[`RAPP1_STATUS.md`](../../RAPP1_STATUS.md). The Cave RAR files are not an
authenticated §13 registry or an artifact-acceptance source.

The catalog design and its substantive tools are preserved instead of replaced
with tombstones. Their current contract is **observe, analyze, check, render,
and plan**. They do not write catalogs, create issues, install code, stream
artifacts, publish releases, or accept trust.

## Two retained indexes

- **RAR** (`rar/index.json`) records the Cave participation agents,
  cubby-agent observations, and rapplication observations with their original
  names, versions, paths, purposes, schemas, and hashes.
- **super-RAR** (`super-rar/index.json`) inventories every supported kind across
  every cubby: agents, organs, senses, rapplications, neighborhoods, and eggs.

Removed source bytes do not cause a record to disappear. The builder retains
known historical entries, their substantive original metadata, and later
observed state/hash transitions, marks the source absent, and leaves current
verification false. This is data exhaust, not a distribution promise.

## State is separate from metadata

Every entry carries independent state:

- `verified` and `verification` describe only the evidence actually checked.
  A local file may be SHA-256 verified while an absent historical file or
  directory remains unverified.
- `accepted` and `acceptance` remain false without an authenticated current
  registry and applicable owner policy.
- `distribution` separately disables fetch, install, execute, stream, and
  publish.

A matching SHA-256 proves byte equality only. It does not prove publisher
identity, authorization, freshness, safety, compatibility, or RAPP/1
acceptance.

## Source policy

Catalog URL fields use this template:

```text
https://raw.githubusercontent.com/kody-w/RAPP/{commit}/cave
```

The caller must substitute a full 40-character commit and verify the entry's
SHA-256. Moving `main`, `master`, `latest`, or `HEAD` references are
observations only and are never accepted. Network fetching is off by default.

The prepared Cave installer snapshot remains untouched and non-installing. Its
catalog record points to [`KERNEL_PIN.json`](../../KERNEL_PIN.json), whose
read-only grail is `kody-w/rapp-installer@brainstem-v0.6.9`. The Cave path is
not an alternate installer.

## Read-only builder

`tools/build_super_rar.py` restores the original discovery and rendering work:

- scans all cubbies and all six supported kinds;
- extracts agent manifest names and docstring purposes;
- computes local SHA-256 values;
- preserves known records whose historical bytes are now absent;
- renders both catalogs in memory;
- validates paths, hashes, retained entries, headers, source policy, state, and
  installer pin facts; and
- compares rendered observations with committed JSON.

Commands:

```bash
# Default: read-only check
python3 cave/tools/build_super_rar.py

# Explicit check
python3 cave/tools/build_super_rar.py --check

# Report drift without writing
python3 cave/tools/build_super_rar.py --plan

# Emit reviewed candidate JSON to stdout
python3 cave/tools/build_super_rar.py --render rar
python3 cave/tools/build_super_rar.py --render super-rar
python3 cave/tools/build_super_rar.py --render all
```

There is intentionally no write mode. Updating committed observations remains
a normal reviewed source change.

## Read-only steward

`agents/rar_steward_agent.py` restores the original quality analysis:

| Action | Result |
|---|---|
| `health` | card coverage, placeholder pressure, duplicate pressure, score, and grade |
| `duplicates` | same-but-different clusters with a suggested reviewed base |
| `junk` | weak or duplicate records to annotate or improve |
| `agent` | deeper assessment from catalog or explicitly supplied card data |
| `issue_plan` | deterministic issue titles, bodies, and fingerprints |
| `file_issues` | retained compatibility alias for the same plan-only result |

The default source is the repository-local `cave/rar/index.json`. A network
source must be explicitly supplied with an immutable GitHub commit and exact
SHA-256. The steward never invokes `gh`, never creates or updates an issue, and
never mutates a catalog. Even `confirm=true` is retained only as historical
input and cannot authorize a write.

## CI

`.github/workflows/cave-super-rar.yml` has read-only repository permission. It
runs the builder check and focused retention/safety tests. It performs no
write-back or artifact publication.

## Historical design context

The super-RAR originated as the public counterpart of the batcave super-store:
one cross-cubby inventory above the narrower participation-agent RAR. The Cave
flipped the visibility axis while retaining the cubby primitive, multi-kind
anatomy, and catalog hygiene work. That design context remains useful for
migration and analysis; public reachability still grants no trust or execution
authority.
