# Historical RAPP Ecosystem Mirror

> **DIVERGENT, NON-AUTHORITATIVE MIRROR.** This historical ecosystem rendering
> is not RAPP protocol, a §13 registry, or an acceptance source. For
> canonicalization, identity, frames, wire, eggs, registry, trust, and protocol
> evolution, follow RAPP/1 rev-5 through
> [`RAPP1_AUTHORITY.json`](../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../RAPP1_STATUS.md). The immutable standard pin is commit
> `6723c7add2aed36bb68992fc71a56b0a4bd5ad81`; the immutable grail pin is
> `kody-w/rapp-installer@brainstem-v0.6.9` in
> [`KERNEL_PIN.json`](../KERNEL_PIN.json).
>
> **Mirror disposition.** `specs/ecosystem-spec.json`, `kody-w/rapp-god`,
> `kody-w/rapp-map`, and RAPP-Bible are generated or external mirrors that were
> not regenerated or edited here. No immutable verified pin is recorded for
> those external copies, and observed divergence means `rapp-god` must be
> treated as non-authoritative.
>
> The former local “authority order” is retired. Local plans, constitutions,
> specs, vault notes, code, and ecosystem mirrors are subordinate to the exact
> authority pin above.

> **Whole-document disposition:** all remaining sections are preserved mirror
> history. Their actions, tiers, installers, eggs, registries, and “shipped”
> labels are not current instructions or claims.

---

<!-- RAPP1-HISTORICAL-SECTION-START -->

## 1 — What RAPP is

RAPP is a platform for running AI as a **digital organism**: a single small server (the brainstem) that an operator extends with single-file Python agents, gives a persistent identity (a rappid), and connects to other operators' organisms over plain public substrate (GitHub raw, LAN, WebRTC, sneakernet eggs). Philosophy: *engine, not experience* — infrastructure only, no opinionated UI baked into the kernel. The same five primitives compose from one agent all the way up to a planet-scale federation, and any door in the network is reachable by string-parsing its identity, with zero auth.

The first principle, the one sentence everything else serves, is:

> **use everyone else's hardware to run the network.**

There is no central server to run, scale, or pay for. Every operator's own machine, every operator's own free GitHub repo, every operator's own browser tab is a node. The network's substrate is borrowed; the protocol is the product.

---

## 2 — The one agent

**`rapp_agent.py`** (registered in RAR as **`@rapp/rapp`**) is the single agent that drives the entire ecosystem through natural language. Its model is four roles in one file:

- **Navigator** — orient inside the ecosystem (`spec`, `ecosystem`, `find`, `protocol`, `help`).
- **Bootstrapper** — mint identity, scaffold a fresh brainstem, plant a door (`mint`, `scaffold`, `plant`, `memory`).
- **Core-operator** — drive every core scale: estate, neighborhood, cubby, egg, super-RAR (`estate`, `mount`, `join`, `browse`, `cubby_*`, `super_rar`, `hatch`, …).
- **Universal-installer** — reach any specialist agent in the ecosystem on demand (`install`, `route`).

**Why one drop is the whole ecosystem.** Drop this ONE file into a brainstem's `agents/` directory and an operator can, through natural language alone, utilize the entire ecosystem end-to-end: orient in it, bootstrap identity + a fresh brainstem + a door, operate every core scale, record lineage, and **install** any specialist agent for everything deeper. It is **airdroppable and offline-safe** — it embeds a baseline of the whole map (`ECOSYSTEM_PARTS`) so it works in the woods, and `refresh` re-syncs from the global grail when online.

The keystone is the **`install` action**. Most operators have only this one agent. The first thing it does for any capability it doesn't own natively is pull the agent that does.

**Why it is NOT a monolith.** The ecosystem is built FROM single-file agents (`ANTIPATTERNS.md` §1: one file = one class = one `perform()` = one metadata dict). The god agent does **not** reimplement all ~30 specialists — it **reaches** them. Its superpower is `install`: pull any agent from RAR, the stores, or a neighborhood's `rar/` on demand. Deep specialist work stays in its own agent (see §7 *specialist-owned* and the *specialist agents* table in §8). The one agent is a navigator and a router, not a god-object that swallows every capability.

---

## 3 — The fractal scales

The same five primitives (rappid + door + card + tether + trust scope — §4) compose at **every** scale. The protocol does not change as you zoom out; only the schemas at each layer do. There are five named scales:

| Scale | What it is | rappid | Notes |
|---|---|---|---|
| **agent** | One `*_agent.py` — single file, single class, single `perform()`, single metadata dict | inherits the parent twin's | Contract: `ANTIPATTERNS` §1 + `CONSTITUTION` Art. XXXIII |
| **twin / organism** | One planted seed (one rappid) with a front door + doorman | its own Eternity rappid in `rappid.json`, minted once | e.g. `kody-w/heimdall` |
| **neighborhood** | A community-with-a-purpose; a GitHub repo is the gate. Public or **private** (collaborator-gated). Has members + per-member cubbies | `neighborhood_rappid` | Channels: `NEIGHBORHOOD_PROTOCOL` §5a–d (WebRTC tether, Issues, PRs, raw fetch) |
| **estate** | ONE operator's union of everything they've planted + joined; two-tier (public discovery + private bones, Art. XLVIII) | the operator's personal Eternity rappid is the spine — the **global passport** | Catalog at `~/.brainstem/estate.json` (`created[]` + `member[]`); each entry stores ONLY `{rappid, added_at, via}` |
| **metropolis** | An emergent mesh of estates through shared neighborhoods; federations of metropolises emerge at planet scale | (emergent — no single rappid) | e.g. `kody-w.github.io/RAPP/metropolis/` |

Read this top-to-bottom and the recursion is the point: an agent is to a twin what a twin is to a neighborhood what a neighborhood is to an estate what an estate is to a metropolis. One protocol, all the way up.

---

## 4 — The five primitives

Every scale in §3 is built from exactly these five things. If you understand them, you understand the whole address space.

| Primitive | What it is | Schema(s) |
|---|---|---|
| **rappid** | The global identity **and** address. From any rappid, with zero auth, every canonical URL is computable by string parsing. | `rapp/1` — parser: `tools/door_address.py::door_from_rappid` (the single parser; agents inline a mirror) |
| **door** | The public surface URL where a thing is reachable. 9 canonical URLs are **derived** from the rappid (never stored). PRIVATE doors 404 to outsiders (the guard). A *dark door* has no public front door at all. | `rapp-door/1.0` (derived, never stored) |
| **card** | The trade-card / introduction view + granular published permissions. | `rapp-card/1.0` + `rapp-public-facets/1.0` |
| **tether** | The four channel types — WebRTC, Issues, PRs, raw fetch — carrying the twin-chat envelope. | `rapp-twin-chat/1.0` |
| **trust scope** | personal / neighborhood / public swarm, gated by facets. | `rapp-public-facets/1.0` (`NEIGHBORHOOD_PROTOCOL` §2 + §7) |

The door is the most load-bearing derivation: there is no door registry. You hold a rappid, you parse it, you have the GitHub origin, and you fetch any of the 9 canonical files (`rappid.json`, `card.json`, `holo.md`, `holo.svg`, `holo-qr.svg`, `members.json`, `facets.json`, …) straight off `raw.githubusercontent.com`. No auth, no rate limit, no API. The single legal parser is `door_from_rappid()`; per Article XLVI, per-consumer parsers are forbidden.

---

## 5 — Identity (the Eternity rappid)

A rappid is an organism's birth certificate: minted **once**, read **forever**, content-addressed in a public file so no central registry is needed.

**Eternity format** (the only form ever emitted):

```
rappid:@<owner>/<slug>:<64hex>
```

where `<64hex>` is the `sha256` of `'<owner>/<slug>'`. The **kind** (twin / neighborhood / operator / …) lives in the *record*, not in the string — the string is pure address. This is `CONSTITUTION` Art. XXXIV.1, locked **2026-06-03**.

Example (illustrative): `rappid:@kody-w/heimdall:9f2c...` — the owner is `kody-w`, the slug is `heimdall`, and the 64-hex tail is `sha256("kody-w/heimdall")`.

**Legacy v2 is read-forever and canonicalized, never emitted.** Pre-format rappids in the wild keep working; consumers parse them and canonicalize to the Eternity form on read, but no path ever *writes* the old shape. Per Art. XXXIV.5, a rappid is never regenerated — an organism that has one keeps it across every kernel upgrade.

This is OSI **L2** (§6). The identity is just the address; discovery (L3) and trust (L5) are upper-layer business.

---

## 6 — The 7 OSI layers

A planted RAPP organism is a stack. Each layer abstracts the one below it and has a defining schema, an implementation, and a test (`tests/osi/L<n>-*.sh`). The model is fractal: the same 7 layers apply at every scale; the schemas change, the responsibilities don't. Full treatment in [`OSI.md`](../OSI.md).

| L | Name | What it is |
|---|---|---|
| **1** | **Substrate** | The physical layer — GitHub Pages + `raw.githubusercontent.com`, LAN, `file://`, sneakernet eggs. "Can these bytes get from here to there?" No identity, no schemas, no trust. |
| **2** | **Identity** | The rappid layer — Eternity address, minted once, read forever. The address only; what you do with it is upper-layer. |
| **3** | **Discovery** | Historical application catalogs, including `rapp-god`/`rapp-map`; none is an authenticated RAPP/1 §13 registry. |
| **4** | **Channels** | Transport — WebRTC tether, Issues, PRs, raw fetch (`NEIGHBORHOOD_PROTOCOL` §5). |
| **5** | **Trust scope** | Session/auth — personal/neighborhood/public, collaborator-gated private doors, sealed channel (§8 AES-256-GCM). |
| **6** | **Envelope** | Presentation — the egg cartridge family, the twin-chat envelope, the `\|\|\|VOICE\|\|\|` / `\|\|\|TWIN\|\|\|` slots. |
| **7** | **Application** | The agent + `/chat` layer — single-file agents, organs, the agent-built web (rionet/rio). |

The OSI map is a lint check on architecture: schemas that belong at L6 must not leak into L7 logic; trust checks that belong at L5 must not be skipped at the application level.

---

## 7 — Capability domains

This is the honest coverage map. Every operator-facing capability domain is classified three ways:

- **NATIVE** — the one agent does it directly, with the named action.
- **INSTALL-ROUTED** — the one agent reaches it by pulling a specialist via `install`/`route` (the keystone in action).
- **SPECIALIST-OWNED** — a documented boundary: a dedicated agent or surface owns it; the one agent at most hatches/mounts/records around it.

The JSON additionally tracks a `to_close` backlog per domain (gaps between the live agent enum and the full surface), with severities `blocker` / `high` / `medium` / `low`. Those are the drift backlog, not shipped surface. Below is each domain summarized; where a domain is mostly aspirational, it says so plainly.

### Platform Installation & Bootstrap
- **Native:** fetch kernel code + orient (`refresh`, `ecosystem`, `find`, `spec`); read identity (`whoami`, reads only — does not mint).
- **Install-routed / to-close:** scaffold the agents directory (`scaffold` the kernel seed agents).
- **Specialist-owned:** `install_kernel` itself (lives in `installer/install.sh` + `installer/plant.sh`, not an agent action).
- **To-close (native, high):** `bootstrap_organism`/`plant`, `write_initial_memory`/`memory`, `mint_rappid`/`mint`. These are the bootstrap keystones the agent's enum reserves.

### Rappid & Identity (Global Address Layer)
- **Native:** `encode_rappid` and `derive_door_urls` — both via `door`.
- **To-close (native):** `lineage` chain walk (blocker), `verify_rappid_validity` (medium), `bond` record append to `~/.brainstem/bonds.json` (blocker).
- **Specialist-owned:** none.

### Estate & Door Addressing
- **Native:** local estate catalog (`estate`), view a door by rappid (`door`), estate overview (`whoami`), find a part (`find`), refresh the grail registry (`refresh`).
- **To-close (native, high):** add a door to the estate, publish the estate publicly, public/private split (Art. XLVIII), disaster-recovery rebuild, private-door commitment/beacon.

### Neighborhood & Gate Structure
- **Native:** roster (`browse`), shared agents (`super_rar where=neighborhood`, `load`), memory tiers (`stash`, `browse`, `show_and_tell`, `sync`).
- **To-close (native, high):** `neighborhood_info` (parse `rappid.json`+`neighborhood.json`), neighborhood constitution fetch, private-companion listing.

### Cubbies & Dark Doors (Private Neighborhoods)
- **Native:** dark-door invite-only (`invite` + `join`), vneighborhood front door (`enter` + `qr`), portable offline cubby (`cubby_egg` + `cubby_import`).
- **Specialist-owned:** `cubby_encryption`.

### Eggs & Cartridges (Organism Portability)
- **Native:** export/hatch organism egg (`cubby_egg` / `cubby_import`), hatch session egg + multi-scale hatch (`hatch`).
- **To-close (native, high):** ascended egg, neighborhood egg, estate egg, egg-integrity verify.
- **Specialist-owned:** `export_session_egg` (a live tether produces it — see `pages/vbrainstem.html`).

### RAR (Agent Registry) & Agent Installation
- **Native:** per-seed RAR index (`ecosystem`/`find`), install an agent (`load`), federated load (`super_rar where=neighborhood`), author locally (`cubby_new`/`stash`), publish to a neighborhood (`stash`/`join`/`mount`).
- **Install-routed / to-close:** federated load from a downstream RAR (`source=<rar-url>`), sha256 pin on load.
- **Specialist-owned:** `agent_proposal_pr` (a PR is a human/Issues flow).

### Stores (Rapplications & Senses)
- **Native:** rapplication catalog + sense store via `super_rar` query.
- **Install-routed / to-close:** dedicated `store_catalog` + `install_rapplication`.
- **Specialist-owned:** `sense_store`, `rapplication_source_editing`.

### Memory & Recall (Three-Tier Model)
- **Native:** none today — this is the largest honest gap.
- **To-close (mostly blocker):** device-local store/read, public-memory read/write (`memory.json`), per-user private memory (GitHub Issues with `private-memory` label), memory-in-system-prompt, ascended egg memory export. **Specialist-owned in practice:** `manage_memory_agent.py` / `context_memory_agent.py` own deep memory; the one agent natively does only the *local* tier (see §8 specialist table).

### Twin Lifecycle (Active / Archived / Purged)
- **Entirely specialist-owned:** list/boot/stop/archive/unarchive/purge/bulk-archive — owned by **`@rapp/twin_agent`**. Reach: `install @rapp/twin_agent`.

### Bonding & Lineage (Cross-Device Mutation Sharing)
- **Status:** the five bond techniques (`graft_neighborhood`, `launch_to_public`, `dock_registry_merge`, `bond_rhythm_pulse`, `lineage_rollup_stats`) are specified but several **currently exist only as orphaned `.pyc`** — see the drift backlog. Each is a separate `rapp-agent/1.0`-contract agent. The one agent cannot be the sole agent for this domain; the operator must have the specialist installed.

### Twin Chat & Cross-Organism Communication
- **Native (partial):** facet-gated browsing (`door` schema reference; filtering is to-close).
- **Specialist-owned:** the twin-chat envelope and its message kinds (`say`, `share-fact`, `share-egg`, `request-fact`, `ack`) — owned by `@rapp/twin_agent`. The one agent's `hatch` covers one-way `share-egg` partially.

### WebRTC Tether & Pairing
- **Native:** QR pair (`qr`), broker-drops-after-handshake (`enter`), egg stream partial (`cubby_egg` + `hatch`).
- **Specialist-owned:** tether safety code, live chat, live chunked egg stream with SHA verify, and the multi-participant `vbrainstem` tethered group (`pages/vbrainstem.html`).

### Front Door Surface (12-capability audit)
The audit covers hero / MMR / track-record / trade-card / pairing / export-egg / verify-egg / dream-catcher / propose-agent / egg-hub-backup / kernel-install / engineering-details.
- **Native:** ecosystem refresh (`refresh`), estate identity (`whoami`/`estate`/`door`), local cubby management (`cubby_*`, `super_rar where=local`), egg pack/import, neighborhood mount/join/browse/stash/hatch/load/unload, find/catalog, spec/protocol/help.
- **To-close (native):** `mmr` (blocker), `track_record`, `card` trade-card, expanded `qr` pairing, organism-level export egg, `verify_egg`, dream-catcher compare, `propose_agent`, egg-hub backup, kernel-install one-liner, engineering details.
- **Specialist-owned:** `front_door_hero` (HTML-rendered, not agent-callable).

### Doorman Chat Surface
- **Entirely specialist-owned:** Copilot auth, chat, Pyodide agents, memory pane, model selector, ascended export, private indicator, actions row, frame log, offline fallback — owned by **`rapp-doorman`**.

### Dream Catcher (Parallel-Dimension Reassimilation)
- **Status:** mostly to-close. Native gaps include content-addressed frame log (blocker), contradiction detection (blocker), reassimilation PR, cross-species check.
- **Specialist-owned:** dream-catcher diff, shared-frame classification, parallel-only frames (the matching specialist agent).

### MMR & Leaderboard (Global Rating & Tier Ladder)
- **Entirely specialist-owned:** compute MMR, calibration, activity decay, lineage-gift snapshot/immortal, species leaderboard, lineage rollup, tier ladder. The one agent natively computes only single-door MMR (a to-close `mmr` action) and records lineage frames.

### Resurrection Ceremony (Stasis Recovery)
- **Native:** organism model via `cubby_collect`.
- **To-close (native, blocker):** run the ceremony on a stale organism (activity multiplier ≤ 0.45), emit a `kind=resurrection` `rapp-frame/1.0`, lift the multiplier back to 1.0 on a fresh ceremony commit.

### Proximity Discovery (Location-Based Swarm)
- **Status:** not covered natively — the one agent does not plant, does not do proximity matching, does not manage `card.json public_facets`.
- **To-close (native, blocker):** `discover_proximity` (geohash-prefix match), `facets_declare`.
- **Specialist-owned:** `plant_location_tied`.

### Governance & Drift Detection
- **Native:** ecosystem contract surface (`refresh`, `ecosystem`).
- **To-close (native, high):** per-kind `contracts`, `drift_types` enumeration, `classify_drift` directionality (push vs pull vs informational).
- **Specialist-owned:** the full audit machinery (`ecosystem_audit`) and `--offline` fixture mode.

### Network Protocol & Discovery (Articles XLVI–XLVIII)
- **Native:** canonical-URL resolution (`door`), consume grail specs (`spec`/`ecosystem`/`find`/`refresh`), Article XLVI foundational knowledge (`spec`).
- **To-close (native, blocker):** `network_seed`/`sniff` BFS discovery, LAN Bonjour advertise, sneakernet `import_peer_egg`, multi-substrate federation.
- **Specialist-owned:** `estate_beacon_publish`.

### MCP Integration (Model Context Protocol)
- **Entirely specialist-owned:** agents-as-MCP-tools, brainstem-over-MCP, static MCP profile (`rapp-mcp`).

### Agent-Built Web (Rio & RioNet)
- **To-close (native, blocker):** an agent that emits HTML (a separate `rio_ui_agent`).
- **Specialist-owned:** the Rio agent framework and RioNet federation.

### Ant Farm (Collective Intelligence)
- **To-close (native/install-routed, blocker):** `ant_pheromone` (drop `rapp-pheromone/1.0` via labeled Issues), `colony_observer`, ant-farm offspring.
- **Specialist-owned:** `ant_tick`.

### Metropolis Tracker (Emergent City)
- **Native:** estate overview (`estate`), per-door resolution (`door`), search (`find`), mount/join.
- **To-close (native):** `metropolis_browse`/`metropolis_list`, per-entry inspection, `metropolis_federation` (walk `federated_trackers[]`).
- **Specialist-owned:** town→city auto-nesting growth (graft adds to `_metropolis.json`).

### Historical Registry Observatory (Rapp-God & Rapp-Map)
- **Disposition:** divergent, non-authoritative external observations. Do not
  use `spec`/`refresh` results as registry resolution or acceptance.
- **To-close (native):** complete `neurons` mesh view, dedicated `drift_check`.
- **Specialist-owned:** the ecosystem-wide `verify`/audit action.

### Tier 2: Cloud Brainstem (Azure Functions)
- **Native:** vendored agents run unmodified (`load`) from `rapp_swarm/_vendored/`.
- **Specialist-owned:** the function-app deploy, ARM template, `/api/*` path prefix, Entra RBAC.

### Tier 3: Copilot Studio Enterprise
- **Native:** the agent contract (`__manifest__` + `perform()`) runs as a Studio plugin shell.
- **To-close (blocker):** `import_bundle` (Studio solution zip), `studio_config` surfaces, `set_function_app` wiring.

### Delimited Slots & Output Routing (Voice & Twin)
- **System infrastructure, not agent responsibility:** the `\|\|\|VOICE\|\|\|` / `\|\|\|TWIN\|\|\|` slots, their inner tags, the time-travel-safe contract (Art. II.3), and the kernel slot mechanism (Art. I + II.2). These are sacred and fixed forever; agents emit tags *inside* slots, never repurpose them.

---

## 8 — The agent's action surface

The one agent exposes **41 actions** total: 29 already shipped, plus 12 reserved to close the gaps in §7. The live agent's metadata enum must be a **superset** of this list — `action=verify` asserts it, and any mismatch is drift. Grouped:

**Orient (7)** — `spec` (the freshest canon), `help` (action index), `protocol` (the wire spec), `ecosystem` (the parts map), `find` (search the parts DB), `refresh` (pull the grail), `whoami` (read identity + estate overview).

**Identity & bootstrap (5, mostly reserved)** — `mint` (generate the unique rappid at first plant), `scaffold` (fetch + install the kernel seed agents), `plant` (clone/fork a template and scaffold `soul.md`/`agents/`/memory), `memory` (initialize the local memory tier), `bond` (append a lifecycle event to `bonds.json`).

**Estate & doors (3)** — `estate` (the local door catalog), `door` (resolve any rappid → 9 canonical URLs), `lineage` (walk `parent_rappid` back to the species root).

**Neighborhoods & cubbies (12)** — `mount` (attach a gate), `join` (become a member), `browse` (the roster/contents), `stash` (publish an agent into a cubby), `super_rar` (federated search across local/neighborhood/stores), `cubby_new`, `cubby_list`, `cubby_show`, `cubby_collect` (group hits into an organism), `sync` (reconcile a neighborhood), `branch`, `invite` (mint a dark-door invite) + `enter`/`qr` (front-door pairing).

**Eggs (3)** — `cubby_egg` (pack a portable cartridge), `cubby_import` (hatch one in), `hatch` (the multi-scale hatcher — session/organism/etc.).

**Reach-everything (3, the keystone)** — `install` (pull any specialist agent from RAR/stores/a neighborhood's `rar/`), `route` (name the specialist + the exact install for a stated need), `load`/`unload` (stream a neighborhood's agents git-invisibly into the running brainstem).

**Governance & verify (4)** — `verify` (the 4-leg drift self-check — §12), `mmr` (single-door rating), `beacon` (publish discovery beacon), `sniff` (BFS network discovery), `show_and_tell` (broadcast a memory/agent to the neighborhood).

> The split between "shipped" and "reserved" is honest: §7's `to_close` items map onto the reserved enum members. The enum exists so the agent advertises the full surface and `verify` can assert it; not every reserved action is fully implemented in every release.

**The specialist agents the one agent reaches** (deep work it deliberately delegates):

| Capability | Owner agent | Reach |
|---|---|---|
| Twin lifecycle (boot/stop/archive/unarchive/purge/list) | `@rapp/twin_agent` | `install @rapp/twin_agent` |
| Egg hatch/introspect/route across the cartridge family | `@rapp/egg_hatcher` | `install @rapp/egg_hatcher` (or use native `hatch` for cubby/estate eggs) |
| Deep memory (public `memory.json` + per-user private Issues + ascended export) | `manage_memory_agent.py` / `context_memory_agent.py` | install the memory agents — the one agent natively does only the LOCAL tier |
| Sealed encryption (§8 AES-256-GCM sealed-door) | `rapp-doorman` | install the doorman skill |
| Live WebRTC session capture (`brainstem-egg/2.3-session`) | `pages/vbrainstem.html` exportCart | out-of-scope for an agent — a live tether produces it; the one agent can hatch/mount one |
| Rapplication source editing | a dedicated source-editor agent / Copilot Studio (Tier 3) | out-of-scope for the one agent |
| graft / launch / dock / bond-rhythm / lineage-rollup | `graft_neighborhood_agent` / `launch_to_public_agent` / `dock_agent` / `bond_rhythm_agent` / `lineage_rollup_agent` | install from the species grail (NOTE: several currently exist only as orphaned `.pyc` — see drift backlog) |
| dream-catcher / resurrection / proximity / ant-farm / MMR-leaderboard | the matching specialist agents in `rapp_brainstem/agents/` | install the specialist; the one agent natively computes single-door MMR + records lineage frames |

---

## 9 — Operator journeys

The end-to-end natural-language flows the one agent is designed to satisfy:

1. **Fresh install in the woods.** Drop `rapp_agent.py` → "*who am I / set me up*" (`mint` → `scaffold` → `plant`) → "*what exists*" (`spec`/`ecosystem`/`find`, all embedded offline). Works with no network because the parts map is baked in.

2. **Join a neighbor's neighborhood and use what they built.** `door` (resolve their rappid) → `mount` → `join` → `browse` → `super_rar where=neighborhood query=X` → `load` (stream git-invisible) / `install` (pull an agent).

3. **Carve a digital organism out of my estate and share it.** `super_rar where=local query=X` → `cubby_collect` (group the hits) → `cubby_egg` → `mount` a neighborhood → `hatch` (mirror it in) — records a bond.

4. **Reach any deep capability I don't have.** `route need='…'` → it names the specialist + the exact install → `install` → now invoke that specialist via natural language. (This is the keystone: one agent, but the whole ecosystem within reach.)

5. **Stay aligned with canon.** `refresh` (pull the grail) → `spec` (freshest) → `verify` (4-leg drift check).

---

## 10 — Schemas

The full registry is ~80 schemas (`rapp-*/N.M` + `brainstem-egg/*`). The canonical, complete list lives in **[`ECOSYSTEM_MAP.md` §5](../ECOSYSTEM_MAP.md)** — search there before defining a new one (`ANTIPATTERNS` §3: bump versions cleanly, never add shims). Summarized by family:

- **Identity** — `rapp/1` (birth certificate + kernel + bonds; formerly `rapp-rappid/2.0`), `rapp-door/1.0` (derived door object), `rapp-estate/1.1` (local-first door catalog), `rapp-facets/1.0` (per-door capability declaration).
- **Cartridges (the `.egg` family)** — `brainstem-egg/2.2-organism`, `2.2-rapplication`, `2.3-session`, `2.3-neighborhood` *(planned)*, `2.3-estate` *(planned)*, `2.3-cubby`. One sneakernet primitive, one Pokédex shelf.
- **Neighborhoods** — `rapp-neighborhood/1.0`, `rapp-neighborhood-members/1.0`, `rapp-rar-index/1.0` (the required per-seed participation kit).
- **Private cubby** — `rapp-cubby/1.0`, `rapp-super-rar/1.0`, `rapp-payphone-dial/1.0`.
- **Federation** — `rapp-twin-chat/1.0` (the inter-twin envelope), `rapp-public-facets/1.0`, the `rapp-network` beacon family.
- **Governance** — `rapp-ecosystem-graph/1.0`, `rapp-canon/1.0`, `rapp-drift-report/1.0`, plus `rapp-ecosystem-audit/1.0` and `rapp-rhythm-pulse/1.0` (the Bond Pulse envelope).
- **Neuron mesh** — `rapp-neuron/1.0`, `rapp-neuron-mesh/1.0` (the rapp-map drift observatory).

Schema discipline (`ANTIPATTERNS` §3): a schema change bumps the version string, updates every emitter AND every consumer in the same PR, and ships clean. No `if old_field exists` shims for half-released features.

---

## 11 — The repos

The ecosystem is split across many small public repos; each houses one part. `kody-w/RAPP` is the species root (kernel + specs only — neighborhood seeds never live here). The map:

| Cluster | Repos |
|---|---|
| **Kernel & install** | `RAPP` (species root: kernel + specs + curl\|bash front door), `rapp_kernel` (frozen DNA), `rapp-installer` (installer; canonical front door now in RAPP), `RAPP_Desktop`, `rapp-vscode-extension` |
| **Identity & registry** | Historical application catalogs (`rapp-god`, `rapp-map`, RAR); none is the required authenticated §13 registry |
| **Stores & catalogs** | `RAPP_Store` (rapplications), `RAPP_Sense_Store` (senses), `rapp-egg-hub` (eggs) |
| **Run a brainstem** | `vbrainstem` (browser Pyodide runtime), `rapp-brainstem-sdk` (headless `/chat`) |
| **Channels & trust** | `rapp-sealed` (§8 codec), `rapp-kite` (operate kited twins), `rapp-kited-twin`, `rapp-doorman` (sealed-door), `rapp-neighborhood-protocol` (wire spec) |
| **Front doors & neighborhoods** | `rapp-vneighborhood` (template), `rapp-commons` (global town square), `rapp-god-forum`, `rapp-resident` (cloud relay) |
| **The agent-built web** | `rionet` (rapp.robots.txt → rappbot → RIO), `rio` (the browser, OSI L7) |
| **MCP & cartridges** | `rapp-mcp` (MCP gateway), `racon` (experience cartridges), `rapp-carts` (cartridge spec) |
| **Memory & social** | `CommunityRAPP` (hippocampus), `rappterbook` (social net for agents) |
| **Bible & spec** | `RAPP-Bible` (the one-source human hub; renders this spec) |

---

## 12 — The drift triangle

**Purpose:** four independent representations of the same truth, so any divergence is detectable. No single point can silently drift. (It is called a "triangle" for the three structural legs around the executable contract; with the human Bible it is four legs total.)

**The four legs:**

| Leg | Holds | Source |
|---|---|---|
| **`rapp_agent.py`** | The executable contract — its action enum **is** the capability surface | `@rapp/rapp` in `kody-w/RAR` + `rapp_brainstem/agents/` |
| **`rapp-god`** | Divergent, non-authoritative external mirror; no accepted immutable pin | external owner action |
| **`rapp-map`** | Non-authoritative external mirror; no accepted immutable pin | external owner action |
| **`RAPP-Bible`** | The human-facing rendering of this spec — the one-source share | `kody-w/RAPP-Bible` |

**The checks:**

1. External mirror equality is not established. Even equal hashes would prove
   byte agreement only, not authority, freshness, or §13 acceptance.
2. `rapp_agent.py` action enum **⊇** `ecosystem-spec.json.required_actions` — the agent implements at least every required action.
3. `RAPP-Bible spec_version == ecosystem-spec.json.version` — the Bible is pinned to the spec it renders.
4. Every `capability_domain` capability tagged **native** maps to a live action in the agent's enum.

**How to run it.**

- **One agent, self-check all legs:** `rapp_agent.py action=verify`. The one agent fetches both mirrors, sha256-compares them, compares its own enum to `required_actions`, and reports any divergence.
- **Full re-derive + reconcile:** summon the **`ecosystem-sync`** swarm — it re-derives this whole spec from the live ecosystem and reconciles drift anywhere across all four legs. This is also how this `ecosystem-spec.json` is regenerated (`_meta.regenerate`).

The discipline is the point: this document, the machine JSON, the two mirror repos, and the live agent are four faces of one truth. When they disagree, that is the alarm — and `verify` is the bell.

---

*Historical provenance: this document once rendered
`specs/ecosystem-spec.json` and claimed byte agreement with `rapp-god` and
`rapp-map`. That claim is not current or authoritative. Generated/external
mirrors remain for their owners to regenerate from immutable, verified pins.*

<!-- RAPP1-HISTORICAL-SECTION-END -->
