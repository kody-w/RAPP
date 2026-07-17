# Historical Twin Lifecycle Proposal

> **Current RAPP/1 authority (rev-5).** For canonicalization, identity, frames,
> wire, eggs, registry, trust, and protocol evolution, follow
> [`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../RAPP1_STATUS.md). Filesystem housekeeping is not
> the authenticated §13 registry and cannot authorize identity or re-genesis.

> **Whole-document disposition:** the repository does not currently ship this
> operator lifecycle API, fleet orchestration, egg snapshot flow, or GUI. The
> actions and JSON below are dated design history. Any future synchronous
> façade remains the exact §8 `POST /chat`; presentation derives locally from
> its `response` string and cannot add Twin wire fields.

<!-- RAPP1-HISTORICAL-SECTION-START -->

> **Authority.** This spec defines the operator-facing housekeeping layer on top of Constitution Article XLIX.3 (twin lifecycle: mint → bond → fork → die). XLIX.3 establishes the philosophical states; this spec defines the disk layout, agent verbs, and JSON shapes that let an operator manage many twins cleanly. "Die" in XLIX.3 corresponds to `purge` here. `archive` is a new operator-housekeeping intermediate state — a twin set aside, body preserved, reversible — that XLIX.3 implicitly allows (a stopped on-disk twin) but doesn't formalize.

**Audience.** Authors of `twin_agent.py`, `fleet_agent.py`, `neighborhood_snapshot_agent.py`, `neighborhood_run_agent.py`. Operators building tooling against the brainstem's HTTP surface.

**Status.** v1.0. Locked 2026-05-19.

**Companion docs.**
- Narrative: `pages/vault/Architecture/Twin Lifecycle — Active, Archived, Purged.md`
- Constitutional anchor: Article XLIX.3
- Related specs: `SPEC.md` §18.10 (egg cartridge family), `ESTATE_SPEC.md` (rappid-as-address)

---

## 1. Lifecycle states

A twin on a given brainstem is in exactly one of three states:

| State | Disk location | Visible in default `Twin list` | In default snapshot eggs | Reversible |
|---|---|---|---|---|
| `active` | `~/.rapp/twins/<hash>/` | yes | yes | n/a (default) |
| `archived` | `~/.rapp/twins/.archive/<hash>/` | no — only via `list_archived` | no — only with `include_archived=true` | yes (`unarchive`) |
| `purged` | `~/.rapp/twins/.purged/<hash>.json` (ledger entry only; workspace removed) | no — only via `list_purged` | never | NO |

Application housekeeping state is determined by disk location; there is no
separate local lifecycle index. This does not modify identity, keys, re-genesis,
or the required RAPP/1 §13 registry.

The v1 host actions below retain the legacy field name `rappid_uuid` as a local
workspace selector. It is not a current rappid form and must never be emitted
as protocol identity; new boundaries use the exact §6 rappid.

**Transitions:**

```
active ──archive──► archived ──purge──► purged
   ▲                   │
   └─── unarchive ─────┘
```

There is no direct `active → purged` transition. `purge` only operates on an already-archived twin. This is a safety rail, not a performance constraint.

---

## 2. Scanner rules

`twin_agent._scan_twins()` walks direct children of `~/.rapp/twins/`. It MUST:

1. Skip any entry whose name starts with `.` (dot-prefix convention).
2. Only descend into entries that contain a `rappid.json` at the top of the dir (these are real twin workspaces).

This rule fixes a latent bug where the historical `.trash/` stub showed up as a phantom twin. It also reserves `.cache/`, `.staging/`, `.archive/`, `.purged/` and any future dotdir convention at zero cost.

Archived and purged twins are listed via separate scanner functions (`_scan_archived()`, `_scan_purged()`) that read those dotdirs.

---

## 3. Agent verbs

Five new actions on the `Twin` agent. All operate on the local brainstem unless noted.

### 3.1 `archive`

Move a twin from `active` to `archived`.

**Args:**

```json
{
  "action": "archive",
  "rappid_uuid": "f7a96540-c422-48f2-b250-563798d3f430",
  "reason": "side-loop test iteration — superseded"
}
```

Or bulk:

```json
{
  "action": "archive",
  "filter": {
    "kind": "project",
    "name_prefix": "test-haiku-",
    "name_regex": "^test-",
    "stopped_for_days": 30
  },
  "confirm": false,
  "reason": "weekly tidy"
}
```

**Semantics.**

- Single form (`rappid_uuid` set): executes immediately. If the twin is running, `Twin action=stop` is invoked first; once `pid_alive == false`, the workspace dir is moved to `~/.rapp/twins/.archive/<hash>/` and `archived.json` is written.
- Bulk form (`filter` set): defaults to **dry-run**. Returns the list of matching twins and what would be done. Re-invoke with `confirm: true` to execute.
- Filter clauses are **conjunctive** — all listed clauses must match.
- A running twin matched by filter is stopped and archived. There is no `force` flag; the verb itself is the consent.

**Filter grammar (v1.0):**

| Clause | Type | Meaning |
|---|---|---|
| `kind` | string | Match `rappid.json#kind` exactly (e.g. `project`, `personal`, `memorial`, `place`, `pre-founder`, `operator`). |
| `name_prefix` | string | `rappid.json#name` starts with this. |
| `name_regex` | string | `rappid.json#name` matches this Python `re` pattern. |
| `stopped_for_days` | integer | Mtime of `~/.rapp/twins/<hash>/` newer than (now - N days) and twin not currently running. |
| `exclude_kinds` | string[] | Match anything not in this list. Useful: `["personal", "memorial", "operator"]` keeps canonical personas safe. |

Forward-compatibility: implementations MUST reject unknown clauses with an error rather than ignoring them. (Silent skip would let typos slip past.)

**Return:**

```json
{
  "ok": true,
  "action": "archive",
  "mode": "execute" | "dry-run",
  "archived": [
    {"hash": "...", "name": "...", "kind": "...", "moved_to": "~/.rapp/twins/.archive/<hash>/"}
  ],
  "errors": [
    {"hash": "...", "name": "...", "error": "..."}
  ],
  "would_archive": [...]
}
```

`would_archive` is populated only in dry-run mode; `archived` and `errors` in execute mode.

### 3.2 `unarchive`

Move a twin from `archived` back to `active`.

**Args:**

```json
{
  "action": "unarchive",
  "rappid_uuid": "f7a96540-..."
}
```

**Semantics.**

- Workspace dir moves `.archive/<hash>/` → `<hash>/`.
- `archived.json` is left in place inside the restored workspace (preserves history). It MAY be deleted by the operator manually if desired.
- Does NOT auto-boot. Operator runs `Twin action=boot` explicitly.
- If the port recorded in `archived.json#last_known.port` is now occupied by another running twin, unarchive still succeeds; boot will use the next free port (existing `_allocate_port` discipline).

No bulk form in v1.0. Unarchive is intentionally deliberate — one twin at a time.

### 3.3 `purge`

Permanently remove an archived twin's body. Leave a tombstone ledger entry.

**Args:**

```json
{
  "action": "purge",
  "rappid_uuid": "f7a96540-...",
  "confirm": true
}
```

**Semantics.**

- ONLY operates on a twin already in `archived`. Attempting to purge an active twin returns an error: `archive first`.
- Reads `~/.rapp/twins/.archive/<hash>/archived.json`.
- Writes `~/.rapp/twins/.purged/<hash>.json` (the tombstone — schema below).
- `rm -rf ~/.rapp/twins/.archive/<hash>/` — the body is gone.
- `confirm: true` is REQUIRED. Without it, returns dry-run output describing what would be removed.
- No bulk form in v1.0. Purge is irreversible; one at a time.

### 3.4 `list_archived`

Enumerate `~/.rapp/twins/.archive/`. Returns an array of objects, each containing the full `archived.json` plus a `path` field.

### 3.5 `list_purged`

Enumerate `~/.rapp/twins/.purged/*.json`. Returns the array of tombstone records.

---

## 4. `archived.json` schema

Written into the archived workspace at archive time.

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
    "agents": ["basic_agent.py", "context_memory_agent.py", "manage_memory_agent.py", "test_haiku_frame_agent.py", "twin_agent.py"]
  },
  "retention": {
    "purge_after": null,
    "purge_policy": "operator-explicit"
  }
}
```

**Required fields:** `schema`, `rappid`, `hash`, `name`, `kind`, `archived_at`, `archived_by`, `last_known.alive_at_archive`.

**Optional fields:** `archived_reason`, `last_known.port`, `last_known.workspace_bytes`, `last_known.workspace_files`, `last_known.agents`, `retention.purge_after`, `retention.purge_policy`.

**`retention.purge_policy` values (v1.0):**

| Value | Meaning |
|---|---|
| `operator-explicit` (default) | Never auto-purge. Surfaces in `list_archived` but no timer touches it. |
| `auto:<n>d` (reserved) | Implementations MAY surface this archive as a purge candidate after N days. Actual purge still requires explicit `Twin action=purge`. No timer in v1.0 deletes anything automatically. |

`archived_by` values: `operator` (manual), `cron:<rule_name>` (future SelfHealingCron auto-archive), `fleet:archive_estate` (set via Fleet fanout — see §6).

---

## 5. `.purged/<hash>.json` schema

Written when a twin is purged. The full archived envelope, minus body-size details (no longer meaningful — the body is gone), plus purge metadata.

```json
{
  "schema": "rapp-twin-purged/1.0",
  "rappid": "rappid:@kody-w/test-haiku-composer:f7a96540…",
  "hash": "f7a96540-...",
  "name": "test-haiku-composer",
  "kind": "project",
  "archived_at": "2026-05-19T20:15:00-04:00",
  "archived_by": "operator",
  "archived_reason": "...",
  "purged_at": "2026-08-19T20:30:00-04:00",
  "purged_by": "operator",
  "purged_reason": "retention window elapsed, no recovery needed"
}
```

`purged_reason` is optional but recommended. The tombstone ledger is the only record that this twin ever existed on this brainstem — it is small (<1 KB per twin) and append-only.

**Consistency with Constitution XLIX.3:** XLIX.3 requires that "dead twins leave a tombstone (rappid + final commit) but no further activity." The `.purged/<hash>.json` ledger entry IS that tombstone at the local brainstem layer. Per Article XLVII, the rappid itself remains globally addressable forever — purging from one brainstem does not erase the organism from the substrate.

---

## 6. Snapshot / hatch interactions

`NeighborhoodSnapshot` action=snapshot:

- **Default:** captures only `active` twins. `.archive/` and `.purged/` are skipped.
- **Opt-in `include_archived: true`:** packs `.archive/` into the egg. The egg manifest's `twins[]` array gains a `lifecycle: "active" | "archived"` field on each entry.
- **`include_purged` does NOT exist.** Purge ledgers never travel in snapshots. (If cross-host purge ledgers ever become useful, a separate deliberate export verb will ship; it is not implied by snapshot.)

`NeighborhoodRun` action=hatch:

- **Default:** restores only `active` entries. Archived entries in the egg are ignored.
- **Opt-in `restore_archived: true`:** lays archived entries into `.archive/` on the target host. Does NOT auto-unarchive.

`NeighborhoodSnapshot` and `NeighborhoodRun` flags follow the same per-category opt-in pattern as the existing `overwrite_agents` / `overwrite_core` / etc. — additive, default-safe.

---

## 7. Estate-wide fanout: `Fleet.archive_estate`

A new action on the `Fleet` agent. Composes `Twin action=archive` calls against every peer in `~/.rapp/peers.json` plus the local brainstem.

**Args:**

```json
{
  "action": "archive_estate",
  "filter": { "name_prefix": "test-haiku-" },
  "confirm": false
}
```

**Semantics.**

- Dry-run by default — returns per-peer counts of what WOULD be archived. Operator inspects, then re-runs with `confirm: true`.
- Executes by SSH-invoking each peer's brainstem with the same `Twin action=archive` payload. The SSH carrier is the one already used by `NeighborhoodRun` (`~/.rapp/peers.json` + the same `_SSH_OPTS`).
- **No atomic rollback.** Per-peer results are aggregated; if 3 of 4 succeed and the 4th SSH-times-out, the operator gets a partial result and can retry. Archive is reversible, so partial state is recoverable.
- `archived_by` on each peer's `archived.json` is set to `fleet:archive_estate`.

**Return:**

```json
{
  "ok": true,
  "action": "archive_estate",
  "mode": "execute",
  "per_peer": [
    {"peer": "self",        "ok": true,  "archived_count": 28, "errors": []},
    {"peer": "RappterTwo",  "ok": true,  "archived_count": 0,  "errors": []},
    {"peer": "MacBookPro3", "ok": false, "error": "ssh timeout 8s"}
  ]
}
```

No `Fleet.unarchive_estate` or `Fleet.purge_estate` in v1.0. Unarchive and purge stay deliberate per-host operations.

---

## 8. HTTP surface

All lifecycle verbs flow through the exact RAPP/1 §8 `/chat` request and
response. No new protocol endpoints. Operators address them in natural
language and the LLM composes the agent call.

Examples of operator phrases that map to these verbs (illustrative — the LLM does the routing):

- "Archive everything matching test-haiku-*" → `Twin action=archive filter={name_prefix: "test-haiku-"} confirm=true`
- "Show me what's archived" → `Twin action=list_archived`
- "Bring back grandma-rose" → `Twin action=unarchive rappid_uuid=...`
- "Permanently delete the 6-month-old archived test twins" → operator confirms target list, then `Twin action=purge rappid_uuid=...` per-twin

---

## 9. Compatibility

| Aspect | Compatibility |
|---|---|
| Existing `Twin action=list` | Host-local behavior is preserved; this is not a RAPP protocol compatibility guarantee. |
| Existing eggs | Legacy inputs require one bounded §12 migration into a registered RAPP/1 §9 variant; normal readers then retire the missing-field fallback. |
| Existing `~/.rapp/twins/.trash/` stub (if present) | Deprecated. Implementations SHOULD migrate any extant `.trash/<hash>/` dirs into `.archive/<hash>/` and synthesize an `archived.json` with `archived_by: "migration"` and `archived_reason: "migrated from .trash convention"`. The empty `.trash/` itself can be removed. |
| Constitutional Article XLIX.3 | Aligned. "Die" in XLIX = `purge` here; `archive` is the new operator-housekeeping intermediate state. |

---

## 10. Out of scope for v1.0

Reserved for future revisions:

- Automatic archive policies (`SelfHealingCron` running scheduled `Twin action=archive` calls).
- Automatic purge timers (the `auto:<n>d` retention policy is reserved syntactically but no timer reads it in v1.0).
- Cross-host purge ledger export.
- Per-twin retention policies set at archive time (only the policy *name* is recorded; no enforcement engine).
- A GUI for browsing archives. (Operators use natural language via `/chat`.)
- Purge bulk form. (Single-twin only in v1.0.)

<!-- RAPP1-HISTORICAL-SECTION-END -->
