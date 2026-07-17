---
title: Neighborhood Egg — Snapshot and Hatch
status: published
section: Architecture
hook: A single `.egg` file captures the full state of a *neighborhood* — every twin's workspace, every brainstem's agents, allowlisted global state, all of memory — across whatever substrate the members happen to live on. Hatching it restores the federation either in place (push peer assets back to where they came from) or as a single-device replay (extract peer assets into `~/.rapp/simulated/<peer>/twins/<hash>/`). One egg, two targets, multiple carriers (LAN-SSH today; GitHub-raw + Tailscale + HTTPS-with-auth planned). Round-trip verified end-to-end on LAN-SSH.
---

# Neighborhood Egg — Snapshot and Hatch

> **Historical/superseded protocol narrative.** Preserve this dated account as
> history; do not use its schemas as current instructions. Canonicalization,
> identity, frames, wire, eggs, registry, trust, and protocol evolution follow
> RAPP/1 rev-5 through
> [`RAPP1_AUTHORITY.json`](../../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../../RAPP1_STATUS.md).

> **Hook.** A single `.egg` file captures the full state of a *neighborhood*.  Hatching it restores the federation either *in place* (push peer assets back to where they came from) or as a *single-device replay* (extract peer assets into `~/.rapp/simulated/<peer>/twins/<hash>/`).  One egg, two targets, multiple carriers — full round-trip verified on LAN-SSH; the format itself is substrate-agnostic.

[[The Federated Twin Egg Hatcher Pattern]] describes how to package and hatch *one* twin.  This doc describes the sibling pattern that packages and hatches *a whole neighborhood* — every twin on this Mac plus every twin on every reachable peer, wherever those peers happen to live — into one cartridge.  Same `.egg` extension, same `rapp-egg/2.0` family, `scale: neighborhood`.

A **neighborhood** is a group of organisms that recognize each other ([[NEIGHBORHOOD_PROTOCOL]] defines the recognition protocol).  Members can live on a LAN, on GitHub, on Tailscale, behind an HTTPS-with-auth front door — anywhere a [[SUBSTRATE_FEDERATION|RAPP substrate]] can reach them.  This doc is about *capturing the running state of those members into one file*, regardless of where they live.

The canonical wire-level spec is [[NEIGHBORHOOD_EGG_SPEC]]; this doc explains the *why* and the *how to use it*.

## The shape

Five properties make a neighborhood egg different from a twin egg:

1. **Two member kinds.** `members.local` (this Mac, captured from local disk) and `members.peers[]` (every SSH-reachable host in `~/.rapp/peers.json`, captured over SSH).
2. **Whole brainstem, not just twins.** Brainstem agents source, brainstem core files (`brainstem.py`, `local_storage.py`, `port.py`, `__init__.py`, `VERSION`, `requirements-brainstem.txt`), brainstem-level `.brainstem_data` memory, and allowlisted `~/.brainstem/*.json` state all travel.
3. **Tarball-per-peer-twin, raw-per-local-twin.** Local twins land as individual files under `twins/<hash>/...` (so the manifest can preview them); peer twins land as `peers/<peer>/twins/<hash>.tar.gz` (so POSIX bits and timestamps survive the network round-trip).
4. **Allowlist for global state, denylist for secrets.** `rappid.json`, `estate.json`, `self_healing_cron_state.json`, `peers/` directory all travel.  `private-estate-secret`, `keys/`, `venv/`, `logs/`, `brainstem.log`, `lifecycle.log` *never* travel.  Secrets stay home.
5. **Two hatch targets.** `target=in-place` (default) pushes peer assets back to real peer hosts over SSH.  `target=local-simulate` extracts peer assets into `~/.rapp/simulated/<peer>/twins/<hash>/` on this Mac — same egg, no network, full offline replay.

## The matched-pair agents

Two single-file agents.  Both live in any brainstem's `agents/` and follow the standard [[The Agent Contract|agent contract]].

- **`NeighborhoodSnapshot`** — produces the egg.
  - `action="snapshot"` — capture state, write the `.egg`
  - `action="inspect" egg_path="..."` — read manifest of an existing egg
  - `action="list_eggs"` — enumerate the eggs dir
- **`NeighborhoodRun`** — consumes the egg.
  - `action="inspect" egg="..."` — read manifest
  - `action="plan" egg="..."` — dry-run, show what would happen (creates / overwrites / boots)
  - `action="hatch" egg="..." target="in-place"|"local-simulate"` — actually restore
  - `action="list_eggs"` — enumerate

The two agents share no code and don't call each other.  They only share the egg format.  This matches the [[The Distro Hatcher Agent Pattern|hatcher pattern]]: one pack tool, one unpack tool, one stable on-disk format between them.

Canonical home of the source is [`kody-w/rappLocalFirstFleet`](https://github.com/kody-w/rappLocalFirstFleet) in `agents/`.  Drop both files into any brainstem's `agents/` directory and the next `/chat` hot-loads them — that's the *only* installation step.

## The safety model

Hatch *never* overwrites by default.  Each category of destination has its own opt-in flag:

| Flag | Affects | Default |
|---|---|---|
| `overwrite_agents` | This brainstem's `agents/*_agent.py` | `false` |
| `overwrite_core` | This brainstem's core source (`brainstem.py` etc.) | `false` |
| `overwrite_data` | This brainstem's `.brainstem_data/` memory | `false` |
| `overwrite_global_state` | `~/.brainstem/*.json` allowlisted state | `false` |
| `overwrite_twins` | Local `~/.rapp/twins/<hash>/` workspaces | `false` |
| `overwrite_peer_twins` | Real peer twin workspaces (in-place target) OR simulated peer workspaces (local-simulate target) | `false` |

Defaults fill gaps only.  Files that already exist on disk are skipped.

Before any destructive hatch, run `action="plan"` — it prints exactly how many files would be created vs. overwritten vs. skipped per category, plus which twins would get booted afterward.  Plan is read-only.

## Carriers

The egg's *format* is substrate-agnostic.  The snapshot and hatch agents need to read and write peer-side state somehow — and "somehow" is pluggable.  Each carrier is a (read, write) pair that knows how to enumerate twins on a peer and move workspace bytes in and out.

The peer roster lives in `~/.rapp/peers.json` (or `BRAINSTEM_PEERS` env).  Each entry declares the carrier-specific coordinates:

```json
{
  "peers": [
    {"name": "RappterTwo",  "url": "http://RappterTwos-Mac-mini.local:7071",
     "ssh_user": "rapptertwo", "ssh_host": "RappterTwos-Mac-mini.local"},
    {"name": "MacBookPro3", "url": "http://Kodys-MacBook-Pro-3.local:7071",
     "ssh_user": "kodyw",    "ssh_host": "Kodys-MacBook-Pro-3.local"}
  ]
}
```

### Carriers, today and planned

| Carrier | Status | When members live on… | Read | Write |
|---|---|---|---|---|
| **LAN-SSH** | ✅ shipping | A LAN with SSH access | `ssh peer 'tar -czf - -C ~/.rapp/twins <hash>'` | `cat tarball \| ssh peer 'tar -xzf - -C ~/.rapp/twins'` |
| **GitHub-neighborhood** | ✅ shipping (read + opt-in PR write) | Public neighborhood repos like [`kody-w/rapp-commons`](https://github.com/kody-w/rapp-commons) — peer entry declares `github_neighborhood: "<owner>/<repo>"`; snapshot walks `members.json`, parses each member's v2 rappid (per [[ESTATE_SPEC]] §1), fetches the member's own repo, packs as a tarball | `gh api repos/<m-o>/<m-r>/git/trees/main?recursive=1` → fetch each blob via contents API + base64-decode → tarball | **Opt-in PR mode** (`github_write_enabled=true` on hatch): clone the captured twin's source repo shallow → apply the snapshot's tarball → if anything changed, branch + commit + push + `gh pr create`.  Never writes to `main` directly.  Supports `github_write_dry_run=true` to preview the diff without pushing |
| **Tailscale** | ✅ shipping (implicit) | A Tailnet (peer's `ssh_host` resolves over the Tailscale interface) | Same as LAN-SSH | Same as LAN-SSH |
| **HTTPS w/ auth** | planned | Brainstems behind a front-gate ([[The Auth Cascade]]) | `GET /api/twin/<hash>/workspace` | `PUT /api/twin/<hash>/workspace` |
| **file:// + sneakernet** | (already covered by §4 of [[SUBSTRATE_FEDERATION]]) | A USB stick / SD card | Read peer's exported egg sub-cartridge | Hand the operator a `.egg` to drop in |

### Verifying the Tailscale path

Tailscale doesn't need its own carrier — it works through the LAN-SSH carrier transparently when the peer's `ssh_host` resolves over the Tailnet.  To verify on a new Tailnet:

1. Confirm `ssh tailnet-hostname.tail-net.ts.net` succeeds with key-only auth (`-o BatchMode=yes`).
2. In `~/.rapp/peers.json`, set `ssh_host` to the Tailnet hostname (e.g., `mac-mini-2.tail-net.ts.net`) and `ssh_user` to the peer's username.
3. Run a snapshot.  The peer entry's `ssh_ok` should be `true` and twins should be captured under `peers/<name>/twins/<hash>.tar.gz` — same as a plain LAN run.

No code change needed.  The `subprocess.run(["ssh", ...])` call resolves through whichever interface `ssh_host` points at.

### Opt-in github-write (PR mode)

When the egg has captured a github-neighborhood peer and the operator wants to push *back* to GitHub, set `github_write_enabled=true` on the hatch.  Behavior:

```
target=in-place + github_write_enabled=true:
  for each captured twin in the github peer:
    1. gh repo clone <member-source-repo> /tmp/<work> --depth 1
    2. untar peers/<peer>/twins/<hash>.tar.gz into /tmp/<work>, stripping
       the leading <hash>/ so files land at repo root
    3. git status — if nothing changed: report no_changes, skip
    4. else: checkout -b rapp-neighborhood-restore/<timestamp>
            git add -A && git commit -m "rapp neighborhood-egg restore @ <ts>"
            git push -u origin <branch>
            gh pr create --base main --head <branch> ...
    5. record PR URL in the hatch report
```

Always opens a PR — **never writes to `main` directly**.  Operator reviews + merges.  Pass `github_write_dry_run=true` to clone+diff+report without pushing or PR-ing, useful for previewing what would change.

The currently-shipped LAN-SSH carrier uses BatchMode key-only SSH auth (no password prompts).  No agent or daemon needs to be installed on the peer — just sshd, tar, gzip.  This is what lets a fresh peer join the neighborhood just by authorizing one SSH key.

Each carrier is small enough to be its own helper module; the snapshot/run agents dispatch on which carrier coords the peer entry provides (`ssh_user` → LAN-SSH; future: `github_repo` → GitHub raw; `auth_url` → HTTPS; etc.).  See [[SUBSTRATE_FEDERATION]] for how these line up with the broader substrate ladder.

## The local-simulate target

`target=local-simulate` is the offline-replay mode.  Instead of pushing peer assets back to real peer hosts, the runner extracts each peer's twin tarballs into a dedicated namespace on the Mac doing the hatch:

```
~/.rapp/simulated/
  RappterTwo/
    twins/
      <hash>/
        rappid.json
        soul.md
        brainstem.py
        agents/
        utils/
        installer/
        .brainstem_data/
        ...
  MacBookPro3/
    twins/
      <hash>/
        ...
```

SSH is never invoked.  The real peers are never touched.  The simulated namespace is hash-collision-safe — the same twin can exist on multiple real peers (e.g., a memorial twin replicated across the LAN), and each instance keeps its identity in its own peer-named subdirectory.

Use cases:
- **Disconnected dev loop** — author and test against a federation without the LAN attached
- **CI fixtures** — pack a known federation snapshot, replay deterministically in CI
- **Demos without the network** — give a talk in a Faraday cage, hatch into simulate mode, demo the swarm
- **Catastrophe replay** — "what would the federation have done at 23:00 last night?" — hatch that night's egg and ask
- **Pre-deploy validation** — try a hatch in simulate mode first to verify everything extracts cleanly before doing the real in-place restore

The MVP doesn't auto-boot simulated peer twins.  Booting them requires port-rebasing (so they don't collide with whatever's listening on the snapshot-time port) plus registration with this brainstem's Twin agent under the simulated path — both out of scope for v1.  In the MVP, simulated twins are file-level replays; you can read their soul, inspect their agents, diff against the real peer, and serve them manually if needed.

## Boot after restore

For `target=in-place`, the runner additionally consults each local-member twin's `alive_at_snapshot` flag in the manifest.  Twins that were alive when the snapshot was taken get re-booted via this brainstem's Twin agent (`action="boot", rappid_uuid="<hash>"`).  Twins that were stopped at snapshot time are restored on disk but not booted.

This means: snapshot the live federation → ship the egg → hatch on a fresh machine → the same twins come back up on the same ports.

## What was verified end-to-end (2026-05-18)

- Snapshotted the live federation from this Mac.  Pulled 5 twins from MacBookPro3 + 1 twin from RappterTwo over SSH.  Egg size: 5.97 MB compressed, 1147 files.
- `rm -rf ~/.rapp/twins/0d51f2b3-...` of the Grandma Rose memorial twin on MacBookPro3 over SSH.  Confirmed gone.
- Hatched the egg with `target=in-place`.  Per-peer report: MacBookPro3 → 1 twin created, 4 skipped.  SSH-verified: Grandma Rose's full workspace back with original timestamps, all subdirs intact (`agents/`, `installer/`, `utils/`, `.brainstem_data/`), soul preserved.
- Repeated on RappterTwo (seeded a twin, destroyed it, hatched).  Same clean result.
- Hatched the same egg with `target=local-simulate`.  Six peer twins extracted to `~/.rapp/simulated/<peer>/twins/<hash>/` on this Mac.  SSH-verified: real peers untouched.

## See also

- [[The Federated Twin Egg Hatcher Pattern]] — the single-twin sibling pattern
- [[The Distro Hatcher Agent Pattern]] — the kernel-extension hatcher (different target)
- [[NEIGHBORHOOD_EGG_SPEC]] — wire-level reference spec
- [[The Swarm Estate]] — the larger frame (estate-scale eggs, identity portability)
- [[SUBSTRATE_FEDERATION]] — the substrate carriers (egg cartridges are substrate-agnostic)
- [[NEIGHBORHOOD_PROTOCOL]] — the *other* sense of "neighborhood" (trust scope between organisms), distinct from the egg cartridge described here
