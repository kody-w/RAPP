# Twin Lifecycle — Active, Archived, Purged

> **HISTORICAL VAULT NOTE — superseded current guidance.** The bounded body is
> dated lifecycle design, not current identity, egg, or protocol instruction.
> For canonicalization, identity, frames, wire, eggs, registry, trust, and
> protocol evolution, follow RAPP/1 rev-5 through
> [`RAPP1_AUTHORITY.json`](../../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../../RAPP1_STATUS.md).

<!-- RAPP1-HISTORICAL-SECTION-START -->

> *Vault note. Twins die. They should die with dignity — reversibly first, then irreversibly only when the operator says so. Three states, two transitions, one ledger.*

The brainstem's `Twin` agent has shipped `summon`, `hatch`, `boot`, `stop`, `lay_egg`, `update_soul`, `list`, and `chat`. What it has not shipped is a retirement path. Twins accumulate. Side-loop experiments, defunct test iterations, generations of haiku-composers — they all sit in `~/.rapp/twins/` indistinguishable from canonical personas. `Twin action=list` returns one undifferentiated wall. `NeighborhoodSnapshot` ingests everything and bloats eggs. There is no spec-grounded way to say "this twin is done."

This note specifies that path.

---

## The three states

| State | Lives at | Boot-able | In `list` | In snapshots |
|---|---|---|---|---|
| **active** | `~/.rapp/twins/<hash>/` | yes | yes | yes |
| **archived** | `~/.rapp/twins/.archive/<hash>/` (workspace intact + `archived.json`) | no — must `unarchive` first | only via `list_archived` | only with `include_archived=true` |
| **purged** | `~/.rapp/twins/.purged/<hash>.json` (tombstone only, body gone) | no — resurrection requires a fresh hatch from an external egg | only via `list_purged` | no |

Two transitions: `archive` (active → archived, reversible) and `purge` (archived → purged, irreversible). No direct active → purged. The intermediate archived state is the safety rail.

---

## Why not just delete

Deletion is one-way and asks the operator to be certain. Most retirements aren't certain — they're "I don't want to look at this right now." Archive is the answer to that mood: it removes the twin from the active list without destroying the workspace. The operator can `unarchive` ten minutes or ten months later. Purge is the answer to "this is genuinely gone forever and I want the disk back."

The Bitcoin-y property: archived twins are *latent organisms* — their soul, agents, and memory are intact on disk. They are recoverable. Purged twins are *deceased* — only their identity remains as a tombstone, by analogy to how the chain remembers spent outputs without storing their bodies.

---

## Why not `.trash/`

Earlier brainstem builds dangled `~/.rapp/twins/.trash/` as a placeholder. The name was wrong: it collides with Finder semantics and implies "auto-emptied eventually." Archives are not trash — they are workspaces the operator chose to set aside, with metadata explaining why and when. The new conventions:

- **`.archive/`** for retired workspaces (the body, intact)
- **`.purged/`** for tombstones (the death certificate)
- **scanner rule:** any direct child of `~/.rapp/twins/` whose name begins with `.` is skipped

The scanner rule also fixes a latent bug: `_scan_twins` currently walks `.trash` as if it were a twin, polluting `Twin action=list` with a ghost entry. Adopting the dotdir-skip convention cleans that up and reserves space for future dotdir conventions (`.cache/`, `.staging/`, etc.) at zero cost.

---

## The agent verbs

Five new actions on the `Twin` agent:

```
action=archive       rappid_uuid=<hash>          → moves to .archive/, writes archived.json
action=archive       filter={...} confirm=true   → batch form, dry-run by default
action=unarchive     rappid_uuid=<hash>          → moves .archive/<hash>/ back to <hash>/
action=purge         rappid_uuid=<hash>          → tombstone .purged/, rm -rf .archive/<hash>/
action=list_archived                             → enumerate .archive/ with tombstones
action=list_purged                               → enumerate .purged/ ledger
```

**Single-target archive** executes immediately. **Filter-form archive** is dry-run unless `confirm=true` is passed — the operator sees the list first. This is the same discipline as `NeighborhoodRun.plan` before `hatch`.

Filter grammar (additive — all clauses must match):

```json
{
  "kind": "project",
  "name_prefix": "test-haiku-",
  "name_regex": "^test-",
  "stopped_for_days": 30,
  "exclude_alive": true
}
```

`exclude_alive: true` is implicit when archiving — a running twin gets stopped first, then archived. This is intentional. There is no `force` flag. If the operator wants to archive a live twin, they confirm by virtue of the verb itself.

---

## The tombstone

When a twin is archived, `archived.json` is written into `~/.rapp/twins/.archive/<hash>/`:

```json
{
  "schema": "rapp-twin-tombstone/1.0",
  "rappid": "rappid:@kody-w/test-haiku-composer:f7a96540…",
  "hash": "f7a96540-c422-48f2-b250-563798d3f430",
  "name": "test-haiku-composer",
  "kind": "project",
  "archived_at": "2026-05-19T20:15:00-04:00",
  "archived_by": "operator",
  "archived_reason": "side-loop test iteration — superseded",
  "last_known": {
    "port": 7090,
    "alive_at_archive": false,
    "workspace_bytes": 90562,
    "workspace_files": 7,
    "agents": ["basic_agent.py", "context_memory_agent.py", "..."]
  },
  "retention": {
    "purge_after": null,
    "purge_policy": "operator-explicit"
  }
}
```

When the twin is purged, the workspace is `rm -rf`'d but a smaller record lands at `~/.rapp/twins/.purged/<hash>.json`: the same envelope minus `last_known.workspace_bytes/files/agents`, plus `purged_at` and `purged_by`. The dead are remembered by their names.

**Retention defaults to `operator-explicit`** — twins never auto-purge. Reserved future policies: `auto:<n>d` would mark candidates after N days, but actual deletion always requires the explicit `purge` verb. The constitution does not let timers euthanize organisms.

---

## Snapshots interact carefully

`NeighborhoodSnapshot` defaults: capture **active only**. Eggs stay lean. Opt-in `include_archived=true` packs `.archive/` into the egg with a `lifecycle: archived` field on each entry of the manifest's `twins[]` array. `.purged/` ledgers **never travel** in snapshots — identity-of-the-dead is per-host. (A separate, deliberate export verb may ship later if cross-host purge ledgers become useful, but it is not implied by snapshot.)

`NeighborhoodRun.hatch` symmetric: by default it restores active. Opt-in `restore_archived=true` lays archived twins down in `.archive/` on the target host. No automatic unarchive — the operator on the target host decides whether to revive.

This means an operator who wants to fully duplicate their estate (active + retired) sets both `include_archived` and `restore_archived`. An operator who wants a fresh-feeling estate restored elsewhere uses defaults and the archives stay home.

---

## Estate-wide retirement

Local archive is the common case. Sometimes the operator wants a class of twins gone from every brainstem — "the test-haiku-* swarm everywhere." `Fleet` gains:

```
action=archive_estate   filter={...}   confirm=true
```

This fans out via the same SSH carrier `NeighborhoodRun` already uses. Each peer's brainstem runs `Twin action=archive filter=…` locally and returns a per-peer result. **There is no atomic rollback.** If three peers archive cleanly and the fourth's SSH times out, the operator gets a partial result and can retry the fourth. Distributed atomicity is a worse property to chase than recoverability — archive is reversible, so partial state is recoverable.

`Fleet.archive_estate` is opt-in. The default scope of every lifecycle verb is the local brainstem.

---

## What this is not

- **Not an egg.** Eggs are for transport; archives are for retirement. The two are orthogonal: an operator may `lay_egg` on a twin and then `archive` it (capture before retirement), or `archive` then `lay_egg` from the archive (back up a retired body before purge).
- **Not a delete shortcut.** A new operator should not learn `purge` first. Documentation surfaces `archive` and `unarchive` prominently; `purge` lives under a separate heading with the word "irreversible."
- **Not auto-tidy.** No timer in the MVP. Auto-archive policies via `SelfHealingCron` are reserved future work.
- **Not a constitutional matter.** The constitution governs what an organism IS and how identity transfers. Lifecycle is operator-level housekeeping. A purged twin is not "killed" — it is removed from one operator's estate. If a snapshot exists elsewhere, the organism continues to exist.

---

## Worked example — 2026-05-19

Operator's local estate had 37 twins. 28 were `test-haiku-*` iterations from side-loop testing. Single bulk call:

```
Twin action=archive filter={"name_prefix": "test-haiku-"} confirm=false
→ dry-run: 28 candidates, 0 alive, total 50 MB workspace bytes, would write 28 archived.json tombstones

Twin action=archive filter={"name_prefix": "test-haiku-"} confirm=true
→ archived: 28, errors: 0, time: 3s
```

After: `Twin action=list` returns 9 twins (the named personas + the one alive). `Twin action=list_archived` returns the 28 with their tombstones. Disk usage in `~/.rapp/twins/` unchanged (the bytes moved sideways into `.archive/`). Snapshot eggs shrink to active-only by default.

---

## Cross-references

- See `pages/docs/TWIN_LIFECYCLE_SPEC.md` for the JSON schemas and action arg shapes.
- See `pages/vault/Architecture/The Federated Twin Egg Hatcher Pattern.md` for how eggs interact with lifecycle.
- See `pages/vault/Architecture/Neighborhood Egg — Snapshot and Hatch.md` for snapshot include/restore flags.
- See `LEXICON.md` for the canonical terms (archive, purge, tombstone).

<!-- RAPP1-HISTORICAL-SECTION-END -->
