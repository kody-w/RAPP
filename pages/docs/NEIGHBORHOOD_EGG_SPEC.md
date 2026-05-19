# NEIGHBORHOOD_EGG_SPEC — Wire format and behavior of `rapp-egg/2.0 scale=neighborhood`

> **Schema:** `rapp-egg/2.0` with `scale: neighborhood` · **Status:** Shipping · **Authority:** this file · **First shipped:** 2026-05-18

This is the wire-level spec for **the cartridge that snapshots a *neighborhood* into one file**.  A neighborhood is a group of organisms that recognize each other ([[NEIGHBORHOOD_PROTOCOL]] defines the recognition contract).  The members can live on any [[SUBSTRATE_FEDERATION|substrate]] — LAN, GitHub, Tailscale, HTTPS-with-auth — the egg's format does not care.  Only the *carrier* (the method used to move workspace bytes in and out of each member) varies by substrate; the format and dispatch rules are uniform.

See [[Neighborhood Egg — Snapshot and Hatch]] for the pattern doc (the *why*); this doc is the *what* — exact field shapes, exact directory layout, exact dispatch rules.

If you are writing a snapshot agent, a hatcher, an inspector, a federation backup tool, or any code that reads or writes a `scale: neighborhood` egg — this is the contract.

---

## §1 — Container

The egg is a ZIP file (`ZIP_DEFLATED`) with extension `.egg`.  No other compression methods are used at the container level.  Twin workspaces for **peer** members are stored as gzipped tarballs *inside* the zip (see §5.2); local twin workspaces are stored as individual files.

## §2 — Top-level layout

```
manifest.json                       # required — see §3
members.json                        # required — duplicate of manifest.members (separable load)
brainstem/                          # local member assets
  soul.md                           # required if local has a soul
  agents/<name>_agent.py            # one file per loaded brainstem agent (source)
  core/brainstem.py                 # brainstem core source files (optional)
  core/local_storage.py
  core/port.py
  core/__init__.py
  core/VERSION
  core/requirements-brainstem.txt
  data/<rel>                        # brainstem-level .brainstem_data memory tree
  global_state/<allowlisted>        # ~/.brainstem allowlisted state (§7)
twins/<hash>/<rel>                  # local twin workspaces, file by file
peers/<peer>/peer.json              # per-peer probe + ssh coords
peers/<peer>/twins/<hash>.tar.gz    # peer twin workspaces, tarballed (§5.2)
peers/<peer>/brainstem/agents/<f>   # peer's brainstem agents source
```

`<hash>` is the 32-hex slice from a v2 rappid, or the bare UUID for legacy v1.x — same convention as `~/.rapp/twins/<hash>/`.  `<peer>` is the peer's `name` field from `peers.json`, with path-unsafe characters replaced by `_`.

## §3 — `manifest.json`

Required at the egg root.  Schema:

```jsonc
{
  "schema": "rapp-egg/2.0",
  "scale": "neighborhood",
  "name": "neighborhood-20260518-225153",         // operator-chosen or auto-timestamp
  "snapshotted_at": "2026-05-18T22:51:53-04:00",  // ISO 8601 with offset
  "snapshotted_from": "Kodys-MacBook-Pro.local",  // hostname of the snapshot host
  "created_by": "NeighborhoodSnapshot",
  "members": {
    "local": { ... },                              // see §4
    "peers": [ { ... }, ... ]                      // see §5
  },
  "options": {
    "include_twin_workspaces": true,
    "include_stopped_twins": true,
    "include_brainstem_core": true,
    "include_brainstem_data": true,
    "include_global_state": true,
    "max_twin_bytes": 50000000,
    "global_state_allowlist": [...],               // see §7
    "global_state_denylist":  [...]                // see §7
  }
}
```

The `options` block records the snapshot settings so a hatcher can detect partial snapshots (e.g., "this egg has no brainstem_core because the snapshotter was run with `include_brainstem_core=false`").

## §4 — `members.local`

```jsonc
{
  "host": "Kodys-MacBook-Pro.local",
  "brainstem_url": "http://localhost:7071",
  "brainstem_dir": "/Users/.../python/openrapp",
  "brainstem_version": "0.1.0-dev",
  "loaded_agents":  ["ContextMemory", "Twin", "Fleet", ...],
  "model": "gpt-4o",
  "agent_files_captured":  ["fleet_agent.py", ...],   // file basenames under brainstem/agents/
  "core_files_captured":   ["brainstem.py", ...],     // file basenames under brainstem/core/
  "brainstem_data_files":  ["shared_memories/...", ...],  // relpath under brainstem/data/
  "global_state_files":    ["rappid.json", ...],      // relpath under brainstem/global_state/
  "twins": [ {twin_meta}, ... ]                       // §4.1
}
```

### §4.1 — local twin entry

```jsonc
{
  "hash":  "0d51f2b3-7c2c-4f9a-8e5b-7f0c92ab4d7e",
  "rappid": "0d51f2b3-7c2c-4f9a-8e5b-7f0c92ab4d7e",   // or v2 rappid string
  "name":  "grandma-rose",
  "kind":  "memorial",                                  // or operator/personal/project/place/...
  "port":  7082,                                        // last-known port from ~/.rapp/ports/<hash>.port
  "pid":   92230,                                       // last-known pid; null if no pid file
  "alive_at_snapshot": false,                           // pid is alive at snapshot time
  "workspace_bytes": 3370,
  "workspace_files": 8,
  "agents": ["agent_a.py", "agent_b.py"],               // twin's agents/ contents
  "agent_count": 2,
  "has_memory": true,                                   // .brainstem_data dir exists
  "memory_files": ["memory.json"],                      // relpath under twin's .brainstem_data
  "memory_file_count": 1,
  "has_soul": true,                                     // soul.md exists
  "has_rappid_json": true,
  "has_own_brainstem": true                             // twin ships its own brainstem.py
}
```

Every file under `~/.rapp/twins/<hash>/` lands in the egg at `twins/<hash>/<rel>`, individual files (not a tarball).  Skips: `__pycache__/`, `*.pyc`, `*.pyo`, `.DS_Store`, `.git/`, `node_modules/`, `.venv/`.

## §5 — `members.peers`

A peer entry has both probe info and (if SSH-reachable) a captured twin roster:

```jsonc
{
  "name": "MacBookPro3",                                // matches peer name in peers.json
  "url":  "http://Kodys-MacBook-Pro-3.local:7071",
  "ssh_user": "kodyw",
  "ssh_host": "Kodys-MacBook-Pro-3.local",
  "reachable_http": true,
  "health": { /* /health response */ },
  "probed_at": "2026-05-18T22:51:55-04:00",
  "ssh_ok": true,
  "twins": [ {peer_twin_meta}, ... ],                   // §5.1
  "agent_files": ["basic_agent.py", "..._agent.py"]     // peer brainstem's agents
}
```

### §5.1 — peer twin entry

```jsonc
{
  "hash":  "0d51f2b3-...",
  "rappid": "...",
  "name":  "grandma-rose",
  "kind":  "memorial",
  "workspace_bytes": 0,                                 // not enumerated remotely; tarball size
                                                        // is authoritative
  "workspace_files": 8,
  "has_soul": true,
  "agents":  [],
  "captured": true,
  "captured_path_in_egg": "peers/MacBookPro3/twins/0d51f2b3-....tar.gz",
  "captured_bytes": 10240
}
```

If `captured` is `false`, the entry will carry a `reason` field (`"oversize"`, `"tar_failed"`, etc.).

### §5.2 — peer twin tarball

A peer twin's workspace travels as `peers/<peer>/twins/<hash>.tar.gz` — a gzipped tar archive of the workspace.  The format is uniform regardless of carrier (LAN-SSH, GitHub raw, HTTPS-with-auth, etc.) so the unpacker doesn't need to know how the bytes were captured.

For the **LAN-SSH carrier** (v1 shipping), the tarball is produced on the peer with:

```
COPYFILE_DISABLE=1 tar --exclude '._*' --exclude '.DS_Store' \
  -czf - -C $HOME/.rapp/twins <hash>
```

The flags suppress macOS AppleDouble (`._*`) resource-fork files and `.DS_Store` noise.  Other carriers SHOULD produce equivalent tarballs (no `._*`, no `.DS_Store`).  Extractors MUST defensively skip any leftover `._*` or `.DS_Store` members in case the egg was produced by an older or non-conforming snapshotter.

## §6 — `peers.json` (on disk, not in egg)

The snapshot host reads `~/.rapp/peers.json` to know which peers to probe AND which carrier to use for each (see §6.1).  Schema:

```jsonc
{
  "peers": [
    {
      // common fields (every entry)
      "name": "RappterTwo",
      "url":  "http://RappterTwos-Mac-mini.local:7071",   // /health probe URL

      // carrier-specific coords (presence selects the carrier — see §6.1)
      "ssh_user": "rapptertwo",                            // LAN-SSH carrier
      "ssh_host": "RappterTwos-Mac-mini.local"
    },
    "http://192.168.86.116:7071"                          // string form: HTTP probe only, no carrier
  ]
}
```

Env override: `BRAINSTEM_PEERS=url1,url2,...` (comma-sep, HTTP-probe only — no carrier).

Loopback URLs (`localhost`, `127.0.0.1`) are filtered out — those are "local," not peers.

### §6.1 — Carriers

The egg format is substrate-agnostic.  Each peer entry's carrier is selected by which coordinate fields are present:

| Carrier | Selected by | Read | Write | Status |
|---|---|---|---|---|
| **LAN-SSH** | `ssh_user` + `ssh_host` | `ssh peer 'COPYFILE_DISABLE=1 tar --exclude="._*" -czf - -C $HOME/.rapp/twins <hash>'` | `ssh peer 'cd $HOME/.rapp/twins && tar -xzf -'` (stdin = tarball) | ✅ shipping (v1) |
| **GitHub raw** | `github_repo: "<owner>/<repo>"` (planned) | `gh api repos/<o>/<r>/contents/...` and raw URL fetch (no auth for public) | PR to the repo (operator-merge gated) | planned |
| **HTTPS w/ auth** | `auth_url` + `auth_token_env` (planned) | `GET <auth_url>/twin/<hash>/workspace.tar.gz` | `PUT <auth_url>/twin/<hash>/workspace.tar.gz` | planned |
| **Tailscale** | `tailscale_name` (planned) | LAN-SSH over the Tailscale interface | Same | planned (no carrier code change needed if `ssh_host` resolves over Tailscale) |
| **file:// import** | `egg_path: "..."` (planned — a peer cartridge sub-bundle) | Read entries from an attached `.egg` | Hand the operator a `.egg` to deliver | planned (covered by [[SUBSTRATE_FEDERATION]] §4–§5) |

A peer entry MAY declare multiple carriers; the snapshot agent picks the first one that works.  A peer entry with only `url` falls back to HTTP-probe-only — the manifest records the probe result but captures no workspace bytes (the peer appears in the egg but with `twins: []`).

Carriers are pluggable.  Adding a new carrier means: (a) defining its coordinate fields in `peers.json`, (b) implementing the (read, write) pair in the snapshot/run agents, (c) listing it here.  The egg format itself does not change.

## §7 — Global state allowlist / denylist

`~/.brainstem/` contains both useful state (small JSON state files, peer config) and noise (logs) plus secrets (signing keys, estate secrets).  The snapshot uses a strict allowlist:

**Allowlist — files (exact match):**
- `rappid.json`
- `estate.json`
- `self_healing_cron_state.json`

**Allowlist — directories (walked recursively):**
- `peers/`

**Denylist — never travels, regardless:**
- `private-estate-secret`
- `private-estate-map.json`
- `keys/`            *(SSH keys, signing keys)*
- `venv/`            *(reproducible)*
- `src/`             *(reproducible)*
- `logs/`
- `brainstem.log`
- `lifecycle.log`

The lists are exposed in `manifest.options.global_state_allowlist` and `global_state_denylist` so a hatcher can audit what should have been included.

## §8 — Hatch targets

A hatcher MUST support two `target` values:

### §8.1 — `target=in-place` (default)

- Local member assets restored to their canonical paths (`agents/` → brainstem's agents dir, `core/` → brainstem dir, `data/` → brainstem's `.brainstem_data/`, `global_state/` → `~/.brainstem/`, `twins/<hash>/` → `~/.rapp/twins/<hash>/`).
- For each peer in `members.peers`: invoke the **carrier** matched by the peer's coordinate fields (§6.1).  The carrier's write half checks whether each twin already exists on the peer and either skips (default safety, unless `overwrite_peer_twins=true`) or pushes the tarball.  For the LAN-SSH carrier (v1 shipping), this is `cat tarball | ssh peer 'cd $HOME/.rapp/twins && tar -xzf -'`.  Future carriers (HTTPS-with-auth, GitHub PR, Tailscale) follow the same pattern with their own write primitives.
- After restore, twins in `members.local.twins` with `alive_at_snapshot=true` are booted via this brainstem's Twin agent (`action="boot", rappid_uuid="<hash>"`).

### §8.2 — `target=local-simulate`

- Local member assets restored as in §8.1.
- For each peer in `members.peers`: SSH is **NEVER** invoked.  Instead, each peer twin tarball is extracted into `~/.rapp/simulated/<peer>/twins/<hash>/` on the host running the hatch.
- Simulated peer twin boot is OUT of MVP scope — files are restored but not registered with the Twin agent in v1.  Future versions MAY add port-rebasing + Twin agent registration for the simulated namespace.

The simulated namespace is hash-collision-safe: the same `<hash>` may appear under multiple `<peer>` directories without conflict.  `rm -rf ~/.rapp/simulated/` wipes simulation state without affecting real twins.

## §9 — Safety model

Hatch MUST default to non-destructive (gap-filling) behavior.  Per-category opt-in flags:

| Flag | Affects |
|---|---|
| `overwrite_agents` | brainstem `agents/*_agent.py` |
| `overwrite_core` | brainstem core source files |
| `overwrite_data` | brainstem `.brainstem_data` memory |
| `overwrite_global_state` | `~/.brainstem/` allowlisted state |
| `overwrite_twins` | local `~/.rapp/twins/<hash>/` |
| `overwrite_peer_twins` | real peer `$HOME/.rapp/twins/<hash>/` (in-place) OR `~/.rapp/simulated/<peer>/twins/<hash>/` (local-simulate) |

Hatchers MUST report per-category created / overwritten / skipped counts and per-peer breakdowns.  Hatchers MUST provide a `plan` action that performs the same path mapping but writes nothing.

## §10 — Authority & related specs

This spec is shipping.  The implementation is in [`kody-w/rappLocalFirstFleet`](https://github.com/kody-w/rappLocalFirstFleet) in:
- `agents/neighborhood_snapshot_agent.py`
- `agents/neighborhood_run_agent.py`

Related specs:

- [[SPEC#1810-the-egg-cartridge-family|SPEC §18.10]] — the `.egg` cartridge family table (this scale is the `rapp-egg/2.0 scale=neighborhood` row, equivalent to the planned `brainstem-egg/2.3-neighborhood`)
- [[ESTATE_SPEC]] — estate-scale eggs (super-set; one estate may contain many neighborhood snapshots over time)
- [[SUBSTRATE_FEDERATION]] — the substrates the egg can travel across (LAN-SSH per §5.2, plus AirDrop / sneakernet / file:// per the existing carriers)
- [[NEIGHBORHOOD_PROTOCOL]] — the *other* sense of "neighborhood" — trust scope between organisms, distinct from this cartridge format

## §11 — Authoring guidance

- Eggs are typically 5–10 MB compressed for a single-Mac federation; up to 50 MB+ for a LAN with multiple richly-populated peers.  No hard cap.
- Eggs are not signed (yet).  Treat them as you would any `.tar.gz` — trust the source.  Future schemas may add signing via [[ESTATE_SPEC]] cross-signing.
- Eggs are NOT for sharing publicly.  Per §7's denylist they exclude secrets, but they DO contain twin memory contents and brainstem-loaded agent source — that's your operator-private state.  Treat eggs like a `~/Library` backup.
- For pushing a federation to a fresh machine, AirDrop the `.egg` over to that machine (substrate 3 per [[SUBSTRATE_FEDERATION]]), drop the two `neighborhood_*_agent.py` files into its brainstem's `agents/`, then talk to the brainstem: "Hatch this egg."
