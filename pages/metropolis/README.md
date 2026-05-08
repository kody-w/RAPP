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
