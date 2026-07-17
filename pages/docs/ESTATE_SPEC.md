# Historical Estate Address Proposal

> **Current RAPP/1 authority (rev-5).** For canonicalization, identity, frames,
> wire, eggs, registry, trust, and protocol evolution, follow
> [`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../RAPP1_STATUS.md). This file remains product-level
> estate context; its incompatible address and cartridge rules are legacy
> migration material, not protocol authority.
>
> **Schema:** `rapp-estate/1.1` · **Status:** product architecture, subordinate
> to RAPP/1 · **First shipped:** 2026-05-09

This is an application architecture for estate views and conventional GitHub
door URLs. It is **not** the load-bearing RAPP identity or discovery spec.
Parsing a self-locating rappid can produce a candidate URL, but authenticated
current anchors, lawful moves, keys, and re-genesis resolve through RAPP/1
§13.

Use these URL conventions for product views only after validating the §6
rappid and resolving current registry state. On conflict, the pinned RAPP/1
authority wins.

> **Historical proposal (2026-05-10), superseded.** The planned
> `brainstem-egg/2.3-estate` cartridge and schema/type hatcher are retired
> migration material. A current estate cartridge is the RAPP/1 §9 `estate`
> variant; identity continuity additionally requires verified §§6, 10, and 13
> state and never follows from transport alone.

> **Whole-document disposition:** the repository does not currently provision
> estate repositories, doors, catalogs, or plant/hatch flows. The remaining
> product rules and “shipped” labels are dated history, not operator actions.

<!-- RAPP1-HISTORICAL-SECTION-START -->

---

## 1. The rappid is identity; location is registry-resolved

The **consolidated** rappid format (locked 2026-06-03):

```
rappid:@<owner>/<slug>:<64hex>
```

The `@<owner>/<slug>` portion supplies the initial self-locating anchor. String
parsing derives the application URL candidates in §2, but does not establish
current authority after a lawful move, re-anchor, key rotation, or re-genesis.
Resolve those through RAPP/1 §13.

| Field | How |
|---|---|
| `owner` | Everything after `@` and before `/` |
| `repo` (`slug`) | Everything after `/` and before the final `:` |
| `hash` | The 64-hex after the final `:` — the 256-bit identity / join key |

`kind` is not part of the §6 rappid. Protocol kind/family bindings come from
§13; application `door_type` may come from product metadata.
`door_from_rappid()` returns candidate URLs only. Legacy v2 strings and bare
UUIDs may be recognized inside bounded §12 migration, but provisional or
legacy identifiers are never emitted or accepted as current.

The dated application `door_type` list in `tools/door_address.py` remains a
UI convention. It neither registers RAPP frame kinds nor replaces the signed
§13 registry and constitutional registration process.

---

## 2. Application door URL convention

GitHub-hosted product doors conventionally publish these URLs. They are not
RAPP protocol requirements or trust anchors:

| # | Name | URL pattern | Required for |
|---|---|---|---|
| 1 | `repo` | `https://github.com/<owner>/<repo>` | all (the canonical browsing URL) |
| 2 | `front` | `https://<owner>.github.io/<repo>/` | all (the heimdall snapshot — the operator-facing chat surface) |
| 3 | `identity` | `https://raw.githubusercontent.com/<owner>/<repo>/main/rappid.json` | application record carrying a RAPP/1 §6 rappid; `rapp/1` is the frame token, not an identity schema |
| 4 | `holocard` | `https://raw.githubusercontent.com/<owner>/<repo>/main/card.json` | all (`rappcards/1.1.2`) |
| 5 | `holo_md` | `https://raw.githubusercontent.com/<owner>/<repo>/main/holo.md` | all (the friendly entry doc) |
| 6 | `avatar` | `https://raw.githubusercontent.com/<owner>/<repo>/main/holo.svg` | all (procedural sprite) |
| 7 | `summon_qr` | `https://raw.githubusercontent.com/<owner>/<repo>/main/holo-qr.svg` | all (QR encoding the front-door URL) |
| 8 | `members` | `https://raw.githubusercontent.com/<owner>/<repo>/main/members.json` | gates only (`rapp-neighborhood-members/1.0`) |
| 9 | `facets` | `https://raw.githubusercontent.com/<owner>/<repo>/main/facets.json` | all (`rapp-facets/1.0` — the door's published-capability declaration) |

**The .nojekyll + index.html invariant.** A planted door's index.html serves the heimdall front-door grail; for that to work over GitHub Pages, the repo MUST contain a `.nojekyll` file at root. The planter emits it. The backfill enforces it.

**Current documentation invariant.** A planted repo may carry onboarding
material, but any current teaching copy must link
`RAPP1_AUTHORITY.json` and `RAPP1_STATUS.md`. Legacy `specs/` bundles are not
structural authority.

---

## 3. The Estate Stores Only Rappid + Provenance

The user's **estate** is the door catalog — every door they own (`created`) plus every door they're a contributor in (`member`). It lives in two places:

- **Local application catalog:** `~/.brainstem/estate.json`
- **Public mirror (optional):** `https://raw.githubusercontent.com/<github-handle>/rapp-estate/main/estate.json`

Per Article XLVI.3, each entry stores **only**:

```json
{
  "rappid": "rappid:@owner/repo:hex",
  "added_at": "2026-05-09T00:00:00Z",
  "via": "created" | "scan" | "manual" | "import" | "published-by-other"
}
```

Application views may derive initial GitHub URL candidates via
`door_from_rappid(rappid)`. Before use, resolve the rappid and current anchor
through §13. Never silently patch, re-mint, or trust a location merely because
it was string-derived.

This is the constitutional answer to *"don't do all of these exception things."*

### 3.1 The full estate.json schema

```json
{
  "schema": "rapp-estate/1.1",
  "owner": {
    "rappid": "rappid:@<github>/<their-twin-or-brainstem>:hex",
    "github": "<github-handle>"
  },
  "created": [{ "rappid": "...", "added_at": "...", "via": "created" }],
  "member":  [{ "rappid": "...", "added_at": "...", "via": "scan" }],
  "updated_at": "2026-05-09T00:00:00Z"
}
```

The `owner.rappid` is intended to be the operator's personal §6 rappid. The
local file is an application cache; the out-of-band estate-owner rappid and
signed §13 registry form the trust root.
The two relationships below are product-lineage/membership metadata only:

- **As ancestor** of `created[]`: every door the operator planted has `parent_rappid = owner.rappid` in its own `rappid.json`.
- **As member-proof** for `member[]`: every gate the operator joined lists `owner.rappid` in its own `members.json`.

The same identity, two roles. No additional ID system needed.

---

## 4. Raw fetch is transport, not authoritative discovery

A public GitHub application view can fetch candidate door content with
`curl`. That provides availability only. A conformant consumer validates the
§6 identifier, resolves §13 state, and verifies any required §10 signature
before accepting protocol data.

### 4.1 Discover one door from its rappid

```bash
# From the rappid, parse <owner>/<repo>:
RAPPID='rappid:@kody-w/echo-brainstem:abc...'
OWNER_REPO=$(echo "$RAPPID" | sed 's|.*:@\([^:]*\):.*|\1|')

# Fetch identity, holocard, holo.md, etc.:
curl -fsSL "https://raw.githubusercontent.com/${OWNER_REPO}/main/rappid.json"
curl -fsSL "https://raw.githubusercontent.com/${OWNER_REPO}/main/card.json"
curl -fsSL "https://raw.githubusercontent.com/${OWNER_REPO}/main/holo.md"
```

### 4.2 Discover a user's full estate from their GitHub handle

```bash
# A single unauthenticated transport fetch (not trusted acceptance):
curl -fsSL "https://raw.githubusercontent.com/<github-handle>/rapp-estate/main/estate.json"
```

This returns an unverified application catalog. Validate identifiers and
registry state before following it.

### 4.3 The chain rule

An application may graph-walk these raw resources for discovery candidates.
Each candidate remains untrusted until the relevant RAPP/1 checks pass.

---

## Historical pre-RAPP/1 implementation appendix (superseded)

Everything below this marker preserves the former derivation, recovery,
cartridge, and adoption contract for migration and audit context. Its
present-tense `MUST` statements, legacy schema examples, hatcher instructions,
and trust claims are **not current instructions**. Current implementations use
RAPP/1 §§6–13 and total migration under §12.

## 5. The `door_from_rappid` Derivation Contract

Every consumer that maps rappid → door URLs MUST use a function with this contract:

```python
def door_from_rappid(rappid: str) -> dict:
    """Return the canonical door object for a rappid. Pure function.

    Returns:
      {
        "rappid": str,
        "owner": str,
        "repo": str,
        "kind": str,
        "door_type": "front_door" | "gate",
        "urls": {
          "repo": "https://github.com/<owner>/<repo>",
          "front": "https://<owner>.github.io/<repo>/",
          "identity": "https://raw.githubusercontent.com/<owner>/<repo>/main/rappid.json",
          "holocard": "https://raw.githubusercontent.com/<owner>/<repo>/main/card.json",
          "holo_md": "https://raw.githubusercontent.com/<owner>/<repo>/main/holo.md",
          "avatar": "https://raw.githubusercontent.com/<owner>/<repo>/main/holo.svg",
          "summon_qr": "https://raw.githubusercontent.com/<owner>/<repo>/main/holo-qr.svg",
          "members": "https://raw.githubusercontent.com/<owner>/<repo>/main/members.json",  # gates only
          "facets": "https://raw.githubusercontent.com/<owner>/<repo>/main/facets.json"
        }
      }

    Raises:
      InvalidRappidError only if the string is genuinely malformed (no parseable
      @<owner>/<slug>:<hash> and no canonicalizable legacy form). It MUST ACCEPT
      the consolidated Eternity form `rappid:@<owner>/<slug>:<64hex>` (one
      location segment) and MUST canonicalize every legacy form on read (v2
      `rappid:v2:<kind>:@<owner>/<repo>:<32hex>@github.com/...`, bare UUID, bare
      `rappid:<slug>:<64hex>`) via `canonicalize_rappid()` before deriving — it
      MUST NOT reject a rappid merely for "not being v2".
    """
```

> **Amendment (2026-07-08, per CONSTITUTION Art. XXXIV.1 lock 2026-06-03).** An
> earlier draft of this Raises clause read "*if the string is not a valid v2
> rappid OR if the `<owner>/<repo>` appears differently in the two segments*."
> That is superseded: the canonical consolidated Eternity form has ONE
> `@<owner>/<slug>` segment (not two) and is not a "v2 rappid", so the old clause
> would reject every currently-mintable rappid. The contract now validates the
> Eternity form and read-forever-canonicalizes legacy v2 (never emitting it),
> matching the reference `tools/door_address.py` (`parse_rappid` /
> `canonicalize_rappid`). Identity is `rapp-eternity/1.0` — the sole identity
> standard, which `rapp/1` subsumes.

Implementation lives at `tools/door_address.py`. Imported by `plant_seed_agent.py`, `estate_agent.py`, and any future federation/discovery consumer. One implementation, one contract — no per-consumer reinventions.

---

## 6. Disaster Recovery — The Estate Is Recomputable

The estate file is a **cache** of relationships the network already publishes. Both copies (`~/.brainstem/estate.json` locally and `<handle>/rapp-estate/main/estate.json` publicly) can be reconstructed from scratch given just the operator's GitHub handle. **This is the load-bearing property the spec exists to guarantee.** If both caches are gone, the rebuild walks public data and produces an identical estate.

### 6.1 The two relationships, both publicly visible

- **Created** — every door the operator planted has its `rappid.json` carry `parent_rappid = <operator-rappid>`. Discovery: walk `<handle>/*` repos, fetch each `rappid.json`, filter on `parent_rappid` matching the operator.
- **Member** — every gate the operator joined lists their rappid in `members.json`. Discovery: search public GitHub for any `members.json` containing the operator's rappid string.

### 6.2 The rebuild procedure

```bash
python3 tools/rebuild_estate.py --handle <gh>            # dry-run, prints
python3 tools/rebuild_estate.py --handle <gh> --apply    # writes ~/.brainstem/estate.json
```

Pseudo-code:

```python
def rebuild(handle):
    operator_rappid = discover_operator(handle)            # § 6.3
    created = []
    for repo in gh_repo_list(handle):
        rappid_meta = raw_fetch(handle, repo, "rappid.json")
        if rappid_meta and rappid_meta["parent_rappid"] == operator_rappid:
            created.append({"rappid": rappid_meta["rappid"], "added_at": now(), "via": "rebuild"})
    member = []
    for hit in gh_search_code(operator_rappid, filename="members.json"):
        gate = raw_fetch_rappid_json(hit.repo)
        member.append({"rappid": gate["rappid"], "added_at": now(), "via": "rebuild"})
    return {"schema": "rapp-estate/1.1", "owner": {...}, "created": created, "member": member}
```

### 6.3 Operator-rappid discovery

The rebuild needs to know the operator's personal rappid before it can filter `parent_rappid` matches. Discovery order:

1. **Local** — `~/.brainstem/rappid.json` (fast path when the operator runs the rebuild on their own machine).
2. **Conventional repos** — `<handle>/<handle>-twin`, `<handle>/<handle>-brainstem`, `<handle>/.brainstem`, plus operator-specific anchors. If any has a valid rappid, derive the operator rappid by ensuring `kind` is `operator` (swap from `twin` if necessary; same owner/repo/hex).
3. **Repo scan** — walk `<handle>/*` for any `rappid.json` with `kind=operator` or `kind=twin` matching the conventional pattern.
4. **Operator hint** — if all automatic discovery fails, the operator passes `--operator-rappid <rappid>` explicitly.

### 6.4 The constitutional invariant

Per Article XLVI.6:
- Every planted door's `rappid.json` MUST set `parent_rappid` to the planter's personal rappid (NOT to None, NOT to the species root). Historical `tools/backfill_seeds.py --patch-parents <op-rappid>` now emits only an owner-action plan; it cannot write this edge without authenticated §13.3 authorization.
- The rebuild tool is operator-tooling, but the **property** it proves is load-bearing: relationships are knowable from public data. Losing local state is recoverable.

### 6.5 What this enables

- **Disaster recovery**: laptop dies, no backup → the estate rebuilds from any other device with `gh` auth.
- **Drop-in rappid lookup**: pass any rappid to `estate fetch rappid=<rappid>` → the agent parses, traces `parent_rappid` if needed, and fetches whoever owns that door's published estate. No local state required.
- **Federation auditing**: anyone can verify a published estate's claims by running the rebuild for the same handle and comparing results.

---

## 7. Adoption + Compliance

- **All NEW plantings** (after this spec ships) emit the full Door URL Set. No exceptions.
- **Existing plantings** may be inspected by `tools/backfill_seeds.py`. The tool is read-only and reports missing files or identity drift; it performs no PUT, remint, or re-anchor. Closing its `OWNER_ACTION_REQUIRED` findings requires authenticated owner action.
- **Stale rappids** (where the `<owner>/<repo>` doesn't match the actual hosting URL) are rejected by `door_from_rappid()` and reissued by the backfill script (the historical `sim-art-collective` case is the canonical example).

---

## 7.5 Neighborhood-scale estate (federation as a first-class scale)

> **Schema anchor:** `rapp-egg/2.0` declares `scale` ∈ {`agent`, `twin`, `brainstem`, `neighborhood`, `swarm`, `factory`, `industry`, `estate`}. Sections 7.5–7.7 cover the two scales above the single-twin door — **neighborhood** and **estate** — and the cartridge form each takes.

The estate model up through §7 assumes a single operator anchoring a catalog of single-twin doors. That stays true for the common case. But the rappid-as-URL property scales: any door that has its own rappid can itself be a *gate* whose `members.json` enumerates rappids of constituent doors. When a gate's members are themselves twins (rather than humans), the gate IS a federation, and the federation IS a door.

### 7.5.1 The neighborhood as an estate

A **neighborhood-scale estate** is an estate whose `created[]` and `member[]` are populated with rappids of *twin federations* rather than (or in addition to) single twins. The four-twin AIBAST deployment (Heimdall + @kody-w + Bots in Blazers + AIBAST, see [[The Federated Twin Egg Hatcher Pattern]]) is the canonical example: four twins, one neighborhood-rappid, one operator estate that references the neighborhood-rappid as a single entry whose URLs resolve to a `members.json` enumerating the four.

The door-type derivation in §1 still holds: a rappid with `kind = "neighborhood"` resolves to `door_type = "gate"` (XLVI.2), and the canonical Door URL Set in §2 already requires gates to publish `members.json`. The neighborhood-scale extension is operational, not schema-breaking:

- **`members.json` carries twin rappids.** Each entry is `{rappid, port_hint, joined_at, via}`. The `port_hint` is the integer port the member should boot on (7081–7084 for the AIBAST four-twin), used by the hatcher to assign listening sockets on the destination host. `via` records how the member joined: `seed` (hatched from the same cartridge), `invite` (cross-signed in), or `import` (imported from another federation).
- **`facets.json` advertises federation capabilities.** A neighborhood gate's facets MUST include `federation` (with members count) and SHOULD include `mesh_chat` (cross-twin fan-out) and `boot_all` (idempotent boot of every member's child brainstem). Consumers reading facets can tell at a glance "this is a four-twin federation that supports mesh chat" without unpacking any cartridge.
- **The 9 canonical URLs are unchanged.** A neighborhood gate publishes the same Door URL Set as any other gate. `members.json` is the only field whose semantics extend (from "humans who joined" to "twin rappids that compose the federation"); the file path, schema name (`rapp-neighborhood-members/1.0`), and discovery protocol are identical.

### 7.5.2 The federation cartridge — `rapp-egg/2.0` with `scale: neighborhood`

When a neighborhood is exported as a portable cartridge, it ships as the `rapp-egg/2.0` shape described in [[NEIGHBORHOOD_PROTOCOL]] §5e. The manifest declares `scale: neighborhood`; the zip carries each member's workspace under `twins/<hash>/` plus a top-level `members.json` mirroring `manifest.json::members[]`. Hatching unpacks each `twins/<hash>/` into `~/.rapp/twins/<hash>/` on the destination host and writes the neighborhood roster + the cartridge's own rappid to `~/.rapp/neighborhoods/<neighborhood_hash>/` for future `Neighborhood.boot_all` and `Twin.list` consumers.

The canonical hatcher is `@kody/twin_egg_hatcher` v1.1.0 (distributed via RAR PR #98). It dispatches per `scale`: `twin` lands at `~/.rapp/twins/<hash>/`, `neighborhood` lands BOTH `~/.rapp/twins/<hash>/` per member AND `~/.rapp/neighborhoods/<hash>/` for the roster, and container scales (`swarm` / `factory` / `industry` / `estate`) currently land at `~/.rapp/<scale>s/<hash>/` as best-effort scaffolding pending scale-specific handlers. The hatcher's introspection rule is: read `manifest.scale`, dispatch; if `scale` is unknown, refuse (no silent fallback).

### 7.5.3 The four-twin worked example

The first neighborhood-scale federation that shipped is the AIBAST deployment:

| Port | Twin              | Member rappid kind | Source     |
|------|-------------------|--------------------|------------|
| 7081 | Heimdall          | `personal`         | public repo |
| 7082 | @kody-w           | `operator`         | public repo |
| 7083 | Bots in Blazers   | `project`          | private repo |
| 7084 | AIBAST            | `project`          | `.egg` file |

All four were hatched from a single cartridge — `aibast-federation.egg`, 19,903 bytes — that bundled each twin's `rappid.json` + `soul.md` + `agents/` + `.brainstem_data/`. The cartridge's manifest declared `scale: neighborhood` at the `rapp-egg/2.0` level, with `members[]` enumerating four entries. The cartridge is the federation in suspended animation: hatching it on a fresh laptop produces byte-for-byte the same four-twin conversation surface that ran on the source. Memories travel with the cartridge by design (`.brainstem_data/` is included).

---

## 7.6 Estate cartridges — substrate-portable identity (`brainstem-egg/2.3-estate`)

The neighborhood cartridge above moves *one federation*. The **estate cartridge** moves the *whole operator identity* — every door the operator created, every gate they're a member of, every cross-signed device, every memory layer — across substrates in one motion.

### 7.6.1 Schema and family

The estate cartridge is the `brainstem-egg/2.3-estate` member of the egg family table in [SPEC.md §18.10](./SPEC.md). At the `rapp-egg/2.0` level it declares `scale: estate`. The two schema names coexist: `rapp-egg/2.0` is the universal cartridge envelope (any scale); `brainstem-egg/2.3-estate` is the family-table name for the estate-scale instance of that envelope. Producers MUST emit both fields in `manifest.json`:

```json
{
  "schema": "brainstem-egg/2.3-estate",
  "scale":  "estate",
  "rapp_egg_version": "2.0",
  "owner_rappid": "rappid:@<gh>/<their-brainstem>:hex",
  "estate_snapshot_at": "<iso8601>",
  "members": [ /* see 7.6.2 */ ]
}
```

### 7.6.2 Layout — nested cartridges

The estate cartridge's `members[]` are not flat twins — they are *themselves cartridges*, one per door in the operator's catalog. A typical estate cartridge layout:

```
manifest.json                                  # scale: estate, members: [...]
estate.json                                    # the full rapp-estate/1.1 catalog
owner_rappid.json                              # operator's personal rappid
members/
    <neighborhood-hash>/                       # nested neighborhood cartridge
        manifest.json                          # scale: neighborhood
        members.json
        twins/<hash>/...
    <twin-hash>/                               # nested single-twin cartridge
        manifest.json                          # scale: twin
        rappid.json
        soul.md
        agents/*.py
        .brainstem_data/
    ...
README.md                                      # human-readable cartridge inventory
```

Each `members/<hash>/manifest.json` is a complete, independently-hatchable cartridge. An operator can extract one nested cartridge and hatch it standalone; the estate hatcher just iterates `members[]` and recursively dispatches the existing per-scale hatchers (`scale: twin` → twin handler, `scale: neighborhood` → neighborhood handler).

### 7.6.3 Substrate migration

The estate cartridge is the **substrate-portable identity primitive**. Workflow:

1. **Export.** On the source brainstem, `EstateExport(action="cartridge")` walks `~/.brainstem/estate.json`, collects each referenced door's local workspace (or fetches it from the canonical URL set if absent locally), and zips the lot with the estate-scale manifest at root.
2. **Migrate.** AirDrop / sneakernet / file-fetch the `.egg` to the destination. The cartridge is opaque on the wire — no DNS, no GitHub Pages, no PeerJS broker required.
3. **Re-anchor.** On the destination, `egg_hatcher_agent.py` reads `manifest.scale = estate`, recursively hatches each `members/<hash>/` per its own scale, restores `~/.brainstem/estate.json` from the bundled copy, and verifies that every member's `parent_rappid` still resolves through `owner_rappid`. **No re-cross-signing required** — rappids stay intact across the move; the cross-signing chain in each member's `.brainstem_data/` is part of the payload.

The substrate dimension is orthogonal to the addressing dimension. §6.5 already declares that the rappid-as-URL property works across GitHub Raw, LAN HTTP, AirDrop'd eggs, and `file://` sneakernet. The estate cartridge generalizes that: not just a single door's URLs, but the *whole catalog* and *every member's body* is substrate-agnostic.

### 7.6.4 Properties this guarantees

- **Identity portability.** An operator's whole digital identity (every twin, every federation, every memory) is one `.egg`. Lose the laptop, hatch the egg on a new one, federation resumes.
- **Cross-substrate disaster recovery.** If GitHub is unreachable, the estate cartridge is the source of truth. Combined with §6 (the estate is recomputable from public data), the operator has two independent recovery paths.
- **Offline-first federation handoff.** Two operators meeting in person can AirDrop estate cartridges with no network round-trip. The receiving brainstem becomes a temporary mirror of the sender's whole identity, gated by which subset the recipient chooses to actually hatch.

### 7.6.5 Cartridge integrity and provenance

Estate cartridges carry the same `provenance.file_hashes` + `manifest_hash` envelope as the organism eggs described in [`ECOSYSTEM.md`](../../ECOSYSTEM.md) §9. The verifier recomputes per-file SHA-256s, the manifest hash, and the recursive integrity of each nested member cartridge. A tampered estate is detectable client-side without any network call. The owner's M-key signature (per [[The Swarm Estate]] §"Cross-signing hierarchy") MAY be appended to the manifest as `owner_signature`; verifiers SHOULD check it when present but MUST NOT require it (the cartridge's own cross-signing chains inside each member are the authoritative key material).

---

## 6.5 Substrate-Agnostic Federation (Article XLVII.5)

This spec defines the rappid as the global address. **What URL substrate that address is fetched over** is a separate concern, covered in [`SUBSTRATE_FEDERATION.md`](./SUBSTRATE_FEDERATION.md). The four substrates — GitHub raw, LAN HTTP + Bonjour, AirDrop'd egg cartridges, sneakernet `file://` — all serve the same rappid-keyed JSON. The estate spec applies uniformly across all of them.

The TL;DR: an operator's estate.json + beacon are reachable via:

- `https://raw.githubusercontent.com/<handle>/rapp-estate/main/...` (default)
- `http://<lan-ip>:8080/...` (LAN, via `tools/lan_advertise.py`)
- AirDrop'd `.egg` extracted to a peer's machine (the egg bundles the federation tools)
- `file://...` URLs from sneakernet-imported eggs (`tools/import_peer_egg.py`)

The sniffer (`tools/sniff_network.py`) walks all four substrates uniformly. Authority for the substrate model: SUBSTRATE_FEDERATION.md + CONSTITUTION Article XLVII.

---

## 7. Public/Private Boundary (Article XLVIII)

**The two-tier estate is mandatory from first install.** Discovery is public (this spec); substance is private. Every operator gets BOTH `<handle>/rapp-estate` (public) AND `<handle>/rapp-estate-private` (private GitHub repo). The public beacon's `private_estate_pointer` + `private_estate_commitment` + `private_door_count` (REQUIRED in `rapp-network-beacon/1.1`) advertise the existence and integrity of private state without leaking what it contains. URLs inside the private repo are opaque (Article XLVIII.6) so even a 404 reveals nothing.

Authority: [`pages/docs/PUBLIC_PRIVATE_BOUNDARY.md`](./PUBLIC_PRIVATE_BOUNDARY.md). Constitutional anchor: CONSTITUTION Article XLVIII (6 subsections). Conformance: `tests/features/F15-private-estate.sh` (10 steps).

---

## 8. Cross-references

- **CONSTITUTION Article XLVI** — the principles in load-bearing form.
- **CONSTITUTION Article XXXIV** — Rappid: Lineage Tracking and Variant Species (where the format originated).
- **CONSTITUTION Article XXIII** — the vault as long-term memory; specs travel with plantings.
- **CONSTITUTION Article XLII** — the global substrate is GitHub Raw + Issues (this spec is the formal version of that article's promise).
- **`specs/RAPPID_SPEC.md`** (bundled in every planting) — the format definition itself.
- **`specs/HOLOCARD_SPEC.md`** — the rappcards/1.1.2 schema for `card.json`.
- **`tools/door_address.py`** — the pure derivation implementation.
- **`rapp_brainstem/agents/estate_agent.py`** — the local-first agent that reads/writes the estate.
- **`rapp_brainstem/agents/plant_seed_agent.py`** — the planter that emits the Door URL Set on every new plant.
- **`rapp_brainstem/agents/twin_egg_hatcher_agent.py`** — the universal hatcher dispatched per `rapp-egg/2.0` scale (twin / brainstem / neighborhood / swarm / factory / industry / estate).

> **Serving-surface note (2026-07-08).** The estate / plant / hatch capabilities are canonically driven as **actions on the one agent** (`@rapp/rapp` — e.g. `estate`, `door`, `whoami`, `hatch`) plus RAR-distributed specialists, not as standalone kernel files at fixed paths. Two hatcher layers coexist (per `pages/docs/SPEC.md` §18.10 / `ECOSYSTEM.md` §15.5): the kernel `.egg` **kind**-router `egg_hatcher_agent.py` and the `rapp-egg/2.0` **scale**-dispatcher `@kody/twin_egg_hatcher` (`twin_egg_hatcher_agent.py`, RAR PR #98, the canonical hatcher per §7.5.2) — an additive superset, not a competitor. Treat the `*_agent.py` filenames above as role labels; resolve the live serving agent through RAR / the one-agent action surface.
- **[[The Federated Twin Egg Hatcher Pattern]]** — the kernel-side pattern that makes neighborhood-scale federations operable; canonical home of the four-twin AIBAST worked example.
- **[[NEIGHBORHOOD_PROTOCOL]] §5e** — the on-the-wire format for neighborhood-scale cartridges; §7.5.2 of this spec is the addressing-layer view of the same artifact.
- **[[The Swarm Estate]]** — the cryptographic backing (M/S/U/D cross-signing) that travels inside each member's `.brainstem_data/` when an estate cartridge migrates substrates.
- **`tests/features/F13-estate-spec.sh`** — conformance gate.

---

*The rappid encodes the address. The address encodes the door. The door encodes the contract. There is no other map.*

<!-- RAPP1-HISTORICAL-SECTION-END -->
