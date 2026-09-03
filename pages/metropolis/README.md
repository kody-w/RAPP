# Historical RAPP Metropolis snapshot

> **Retired pre-acceptance experiment.** The directory, registration,
> federation, joining, live-presence, and trust behaviors described below are
> disabled. The JSON files preserve legacy identities as invalid migration
> evidence; they are not a RAPP/1 registry, catalog, membership list, or
> acceptance source. Follow
> [`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../RAPP1_STATUS.md).

The substantive directory artifact is restored as a historical explorer while
the behavior boundary above remains in force.

## Restoration provenance and safety boundary

The fullest substantive historical artifacts were located directly in git:

| Artifact | Exact source |
|---|---|
| `index.html` | commit `1d4141f32a0b90c8de24be136478cc583bed6474`, blob `96bb6399db2f43bc70f02af9871b69b81f506db3`, 17,367 bytes |
| `README.md` bounded full record | commit `7422762badde25a34f514a686d8b919a513ab1e5`, blob `33fc70c8d91a78cfc056ac392b0f2535ed1c890c`, 5,736 bytes |
| `scripts/harvest-metropolis-activity.py` | commit `1d4141f32a0b90c8de24be136478cc583bed6474`, blob `1629e896160200a6ce7b08dc1c188908df236060`, 3,158 bytes |
| Last pre-replacement tree carrying the full UI blob | `2526f40730ff0ce40a3385b6daa211aa2f817911` |

The HTML was restored from that exact source before adaptation. Original
sections, copy, filters, table/card presentation, federation logic, and
historical comments remain in place. Current changes are additive or limited
to the exact side-effect boundary:

- `index.json`, `federated-demo.json`, and `activity-snapshot.json` are the only
  runtime data inputs;
- historical tracker URLs are redirected to their checked-in local snapshots;
- the original live `HEAD` probe remains visible in source after an
  unconditional return and cannot execute;
- gate/repository destinations are rendered as recorded text rather than join
  links;
- the original registration instruction remains visible but struck through
  and labeled inactive;
- legacy identities are unchanged and visibly labeled historical/unaccepted;
- the activity view uses the frozen snapshot timestamp and shows retained
  event context; and
- the harvester preserves its original source while its executable entry path
  refuses collection and performs no network or write.

No scheduled activity workflow exists. No token, repository creation,
registration, join, live probe, remote tracker request, or network-derived
trust path is enabled.

## Immutable Grail context

The original directory's brainstem and installer-era language remains part of
the historical record. Its obsolete execution edge is not deleted or replaced
with a blank refusal; it resolves to immutable implementation evidence:

- checked-in pin record: [`KERNEL_PIN.json`](../../KERNEL_PIN.json);
- pinned source: [`kody-w/rapp-installer@brainstem-v0.6.9`](https://github.com/kody-w/rapp-installer/tree/brainstem-v0.6.9);
- frozen files: `rapp_brainstem/brainstem.py`,
  `rapp_brainstem/agents/basic_agent.py`, and `rapp_brainstem/VERSION`.

These are source/evidence links only. This directory adds no executable install
or download command, and it does not alter the pinned Grail bytes.

At restoration base `c83b1feba0155618f0d50b4cf48ba15dd42b0b89`,
`_config.yml` still excludes the local JSON files from the generated Pages
artifact. That central publication setting is intentionally untouched because
it is outside this directory's owned scope. A publication owner must include
the same checked-in snapshots rather than substitute remote URLs.

<!-- RAPP1-HISTORICAL-SECTION-START -->

# RAPP Metropolis — Protocol

> *A Kazaa/torrent-style index of active RAPP neighborhoods. Brainstems are the seeders. Agents are the work. The protocol is the network.*

The metropolis is a **decentralized directory** of planted neighborhoods. It exists in this repo as `pages/metropolis/index.json` + `pages/metropolis/index.html`, but **the protocol matters more than this URL**: anyone can fork the directory and run their own tracker, and trackers can federate by linking to each other.

## What this is

| Thing | Analogue | RAPP |
|---|---|---|
| Tracker | torrent tracker | `index.json` at any URL |
| Seed | torrent metadata | a planted neighborhood seed (gate repo) |
| Seeders | peers hosting the file | brainstems running in that neighborhood |
| Magnet link | peer-to-peer URI | the `gate_repo` URL on GitHub |
| Index page | The Pirate Bay listing | `index.html` rendering the JSON |

The substrate is GitHub (per the master plan). The index itself is a static JSON file. The HTML page renders + filters it client-side. Live-status probes happen in the browser. **No central server. No database. No platform-operated state.**

## Schemas

### `rapp-metropolis-index/1.0`

The top-level tracker document. Fields:

| Field | Purpose |
|---|---|
| `tracker_name`, `tracker_url`, `tracker_operator` | Self-describing identity |
| `purpose` | One-paragraph statement |
| `synced_at` | When this was last updated |
| `federated_trackers` | Other trackers this one knows about — the federation primitive |
| `entries` | Array of `rapp-metropolis-entry/1.0` |
| `protocol` | How registration / federation / live-status work |

### `rapp-metropolis-entry/1.0`

Per-neighborhood entry. Fields:

| Field | Purpose |
|---|---|
| `name`, `display_name`, `kind`, `visibility` | Identity |
| `neighborhood_rappid` | The neighborhood's UUID (per `rapp-neighborhood/1.0`) |
| `gate_repo`, `gate_url`, `private_companion` | Where to find the seed |
| `planted_by`, `planted_at` | Provenance |
| `tags` | Free-form taxonomy for filter / search |
| `join_via` | How an outsider gets in: `request_issue`, `out_of_band_invite`, `public_link`, `file_local` |
| `seeders_min`, `seeders_live` | Minimum-known seeders + live-probed count |
| `live_status` | Filled by the directory page on probe: `reachable`, `unreachable`, `unknown` |

## How to register your neighborhood

1. **Open a PR** adding an entry to `pages/metropolis/index.json` on this repo. Maintainer reviews + merges.
2. **Or run your own tracker.** Fork this directory. Curate as you wish. Federate (or don't).

## How federation works

Each tracker can list other trackers in `federated_trackers`. A directory page (or aggregator agent) can walk those references to compose a multi-tracker view. There is no canonical authority — the metropolis is the union of all trackers, and clients pick which trackers to trust.

## Live status

Each entry's `gate_url` (or `gate_repo`) is HEAD-probed by the directory page on load. Reachable entries get a 🟢; unreachable get ⚫. This is best-effort browser-side; trackers don't store live state.

## How brainstems become seeders

A neighborhood is **seeded by every brainstem that has subscribed to it**. The membership organ (`rapp_brainstem/utils/organs/neighborhood_membership_organ.py`) tracks subscriptions; aggregating across brainstems is a Phase 2 capability (each brainstem can publish its subscription list to its own public estate-view).

For now, `seeders_min` is the manually-known minimum; `seeders_live` is filled in client-side when a tracker can verify reachability.

## What this is NOT

- **Not a marketplace.** No transactions happen here. The commercial layer is governed by `COMMERCIAL.md` separately.
- **Not a vetting authority.** Listing is curation, not endorsement. Trackers can have their own policies.
- **Not the only one.** Anyone running a fork is just as legitimate. Multiple trackers should exist.

## Why this fits the master plan

- **Use everyone else's hardware.** GitHub Pages serves the directory; raw fetches resolve each entry's seed; no platform-operated infrastructure.
- **Local-first.** Browsers cache the index; even if this URL goes away, anyone with a cached copy or a fork keeps the network alive.
- **Adapt to who's home.** Live-status probes degrade gracefully: unreachable doesn't mean gone, just not-home-right-now.
- **Schema-first.** `rapp-metropolis-index/1.0` is the contract. Implementations are interchangeable. Anyone can write their own renderer.

## Related

- [`MASTER_PLAN.md`](../../MASTER_PLAN.md) — first-principles north star
- The seeds the index points at live as their own GitHub repos (e.g. [`kody-w/microsoft-se-team-neighborhood`](https://github.com/kody-w/microsoft-se-team-neighborhood), [`kody-w/braintrust-template`](https://github.com/kody-w/braintrust-template)). Each is a planted organism — same pattern as a planted twin (e.g. [`kody-w/heimdall`](https://github.com/kody-w/heimdall)). The metropolis directory is the **card catalog** that points at all of them.
- [`pages/vault/Field Notes/`](../vault/Field%20Notes/) — engineering essays, including the bibliography-as-protocol field note

<!-- RAPP1-HISTORICAL-SECTION-END -->
