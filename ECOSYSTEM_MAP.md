# Historical RAPP Ecosystem Map

> **Current RAPP/1 authority (rev-5).** For canonicalization, identity, frames,
> wire, eggs, registry, trust, and protocol evolution, follow
> [`RAPP1_AUTHORITY.json`](./RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](./RAPP1_STATUS.md). This map inventories product concepts
> and migration work; it does not register protocol schemas or establish trust.

> **Whole-document disposition:** this map is dated product and migration
> history. Do not start work here or follow its action, planting, browser,
> catalog, hatching, relay, or external “god” paths. It is not current
> navigation and its `rapp-ecosystem-map/1.0` label is not a protocol schema.
> Begin only with the authority and status links above.

<!-- RAPP1-HISTORICAL-SECTION-START -->

## How to read this

1. **§11 first if you're about to DO anything** — the decision table answers "before I do X, what should I check?"
2. **§5 if you encounter a schema token** — it separates the tiny current
   RAPP/1 surface from application-local and legacy declaration inventory.
3. **§6 if you need an existing implementation** — file path → spec section it satisfies.
4. **§13 if your code seems to disagree with the spec** — known drift gaps with citations.
5. **§12 antipatterns are LAW** — re-read before any non-trivial commit.

---

## §1 — Authority order

When two docs disagree, this is the precedence:

1. **`RAPP1_AUTHORITY.json` + its exact rev-5 pin**, as adopted by
   Constitution Article LV, govern RAPP/1 structure.
2. **`RAPP1_STATUS.md`** governs what this repository may currently claim;
   the repository is not yet fully conformant.
3. **`CONSTITUTION.md`** governs repository policy, subordinate to Article
   LV's structural authority; `MASTER_PLAN.md` and current teaching docs
   execute that authority.
4. **`pages/vault/`, dated decisions, and release notes** preserve history and
   rationale but do not override current protocol.
5. **Code and generated observations** report implementation state; behavior
   does not create structural authority.

---

## §2 — The fractal scales

Same primitives at every scale: **rappid + door + card + tether + trust scope.** Same protocol from agent up to metropolis-of-metropolises.

```
┌──────────────────────── …outward ─────────────────────────┐
│  Federations of metropolises (planet-scale; emerges)       │
└──────────────┬─────────────────────────────────────────────┘
               ↓
┌──────────────────────── Metropolis ───────────────────────┐
│  Emergent mesh of estates through shared neighborhoods     │
│  rappid: each operator's    | door: each gate URL          │
│  card: per twin             | tether: federation channels  │
│  scope: per facet                                          │
│  example: kody-w.github.io/RAPP/metropolis/                │
│  spec: vault/Decisions/2026-05-08 — Estate is the…         │
└──────────────┬─────────────────────────────────────────────┘
               ↓
┌──────────────────────── Estate ───────────────────────────┐
│  ONE operator's union of all neighborhoods                 │
│  rappid: operator's personal one is the spine              │
│  door: /api/estate/* on operator's brainstem               │
│  card: operator's identity card                            │
│  tether: Issues, file://, ~/.brainstem/eggs/               │
│  scope: personal across all subscriptions                  │
│  impl: utils/organs/estate_organ.py + neighborhood_membership_organ.py│
└──────────────┬─────────────────────────────────────────────┘
               ↓
┌──────────────────────── Neighborhood ─────────────────────┐
│  Community-with-a-purpose; collaborator-gated              │
│  rappid: neighborhood_rappid                               │
│  door: gate URL <owner>.github.io/<gate-repo>              │
│  card: neighborhood card.json                              │
│  tether: NEIGHBORHOOD_PROTOCOL §5a–d (4 channel types)     │
│  scope: §2 personal/neighborhood/public + §7 facets        │
│  examples: kody-w/microsoft-se-team-neighborhood + private │
│            kody-w/public-art-collective                    │
│  impl: utils/organs/neighborhood_membership_organ.py       │
└──────────────┬─────────────────────────────────────────────┘
               ↓
┌──────────────────────── Twin (organism) ──────────────────┐
│  ONE planted seed (one rappid)                             │
│  rappid: RAPP/1 §6 self-locating form; tail minted once    │
│  door: front-door index.html + doorman/                    │
│  card: card.json — ECOSYSTEM §3                            │
│  tether: ECOSYSTEM §4 surfaces                             │
│  scope: NEIGHBORHOOD_PROTOCOL §2                           │
│  example: kody-w/heimdall                                  │
│  impl: rapp_brainstem/ + every planted seed                │
└──────────────┬─────────────────────────────────────────────┘
               ↓
┌──────────────────────── Agent ────────────────────────────┐
│  Single file, single class, single perform()               │
│  rappid: inherits parent twin's                            │
│  door: none (addressed via brainstem.py /chat tools)       │
│  card: metadata dict at module scope                       │
│  tether: in-process                                        │
│  scope: inherits caller's                                  │
│  contract: ANTIPATTERNS §1 + CONSTITUTION Art. XXXIII      │
│  examples: rapp_brainstem/agents/learn_new_agent.py +      │
│            installable RAR agents (e.g. @rapp/twin_agent)  │
└────────────────────────────────────────────────────────────┘
```

---

## §3 — Five universal primitives

| Primitive | One-line meaning | Defined in | Schema(s) |
|---|---|---|---|
| **rappid** | `rappid:@owner/slug:<64hex>`; tail domain-minted once from UUIDv4 octets or SPKI, never name-derived | RAPP/1 §6 | grammar, not a schema token |
| **door** | Public surface URL where this thing is reachable | ECOSYSTEM §4 (front door + doorman); NEIGHBORHOOD_PROTOCOL §1 (Pages URL) | (no separate schema; URL is the contract) |
| **card** | Trade-card / introduction view | ECOSYSTEM §3 (`card.json`) | `rapp-card/1.0` |
| **tether** | Application transports that must map to an allowed RAPP wire form | RAPP/1 §8; historical channel notes in NEIGHBORHOOD_PROTOCOL | exact `/chat` or verified asynchronous §7 frame |
| **trust scope** | Application authorization labels, distinct from protocol authentication | RAPP/1 §§10/13; app policy in NEIGHBORHOOD_PROTOCOL | signed registry and anchored key succession govern RAPP trust |

---

## §4 — Spec-doc map (which doc owns which concept)

| Doc | Owns | When to read |
|---|---|---|
| `MASTER_PLAN.md` | First-principles north star (Part 1 + Part Deux); single-sentence: *"use everyone else's hardware to run the network"* | Strategic direction disputes |
| `CONSTITUTION.md` | Repo governance + sacred constraints + 38+ articles | Structural change, new contributor |
| `OSI.md` | The 7-layer model — substrate / identity / discovery / channels / trust / envelope / application — with schemas + tests per layer | Designing a new feature; figuring out which layer something belongs to |
| `HERO_USECASE.md` | Four canonical scenarios (Charizard, Dream Catcher, Mom's Mixtape, Pizza Place) that judge any change | PR review, roadmap |
| `ECOSYSTEM.md` | Anatomy of one organism (file layout, identity stack, two surfaces, memory tiers, MMR, eggs, integrity, 3 network modes) | Organism-level work |
| `NEIGHBORHOOD_PROTOCOL.md` | Cross-organism wire (4 channels, twin chat, facets, knowledge primitives, adversarial scenarios) | Federation work |
| `ANTIPATTERNS.md` | 5 locked rules — things never to do | Every commit |
| `SURVIVAL.md` | Failure-mode contract — what survives what | Adding a network call |
| `LEXICON.md` | The official human + developer vocabulary | Naming anything |
| `TRADEMARK.md` | Wordmark scope (RAPP, rappid, hatchling, vBrainstem, rapplication, rapp_kernel, brainstem) | Anything user-facing |
| `COMMERCIAL.md` | Open / commercial boundary | Anything that ships |
| `DEFINITION_OF_DONE.md` | Test discipline | Before saying "done" |
| `TEMPLATE.md` | What planted seeds look like | Plant flow |
| `CLAUDE.md` | Daily AI-assistant instructions | Every session start |
| `pages/vault/Decisions/` | The "why" essays for major decisions | Settled arguments |
| `pages/vault/Architecture/` | Long-form design notes (RAR, Rappid, Signed Releases, …) | Deep design |
| `pages/vault/Field Notes/` | Engineering essays | Cross-cutting context |

---

## §5 — Protocol quick reference and observed declarations

The only current protocol tokens in this inventory are the RAPP/1 §7 frame
`spec:"rapp/1"` and §9 egg `schema:"rapp/1-egg"`. The §6 rappid is a grammar;
the §8 wire and §13 signed registry are exact contracts, not permission to
mint another schema name. Every other row is an **observed application-local
declaration or legacy migration input**, not protocol authority. An emitter or
defining document cannot register it; registration follows RAPP/1 §13.

| Schema | Purpose | Defined in | Emitted by |
|---|---|---|---|
| `rapp-agent/1.0` | Application-local agent module manifest | superseded pages/docs/SPEC.md | legacy/runtime metadata; not a RAPP protocol schema |
| `rapp-rappid/1.1` | Legacy organism birth certificate | historical ECOSYSTEM §3 | bounded §12 migration input; never current emission |
| `rapp/1` | **Current exact eleven-key frame token** | pinned RAPP/1 §7 | target for conformant frame producers/consumers |
| `rapp/1-egg` | **Current exact seven-member egg manifest token** | pinned RAPP/1 §9 | target for conformant egg producers/consumers |
| `rapp-card/1.0` | Trade-card override — the operator-set **subset** layered inside the full `rappcards/1.1.2` `card.json` holocard (SPEC.md §5); distinct layers, not competing schemas | ECOSYSTEM §3 | card.json (operator-set) |
| `rapp-frame/1.0` | Legacy mutation event with retired chain shape | historical ECOSYSTEM §3 | migration-only browser emitter; not RAPP/1 §7 |
| `brainstem-egg/2.0` | Legacy twin egg | utils/egg.py | (legacy) |
| `brainstem-egg/2.1` | Legacy variant-repo cartridge | historical CLAUDE guidance | bounded migration input |
| `brainstem-egg/2.2-organism` | Legacy full-instance cartridge | historical ECOSYSTEM §3/§8 | bounded migration input |
| `brainstem-egg/2.2-rapplication` | Legacy single-rapp cartridge | historical CLAUDE guidance | bounded migration input |
| `brainstem-egg/2.3-session` | Legacy contained-browser session cartridge | superseded local SPEC / external history | bounded migration input |
| `brainstem-egg/2.3-neighborhood` | Retired neighborhood proposal | superseded local SPEC | historical only |
| `brainstem-egg/2.3-estate` | Retired estate proposal | superseded local SPEC | historical only |
| `rappterbox-cart/0.1` | Legacy session cartridge schema (superseded by brainstem-egg/2.3-session 2026-05-10; loader still accepts both for one release) | rappterbox/carts/SCHEMA.md | pages/vbrainstem.html (legacy export); rappterbox/console.html (legacy load) |
| `rapp-egg-provenance/1.0` | SHA-256 file hashes + manifest hash + origin commit SHA | ECOSYSTEM §3, §9 | utils/bond.py |
| `rapp-organism-state/1.0` | state_at_seal snapshot (mem_count, mut_count, MMR, etc.) | ECOSYSTEM §3 | utils/bond.py |
| `rapp-user-memories/1.0` | Per-user issue memories (ascended-tier export) | ECOSYSTEM §3 | doorman ascended export |
| `rapp-twin-chat/1.0` | Legacy/application inter-twin adapter; not a RAPP wire form | historical NEIGHBORHOOD_PROTOCOL §6a | migration-only twin_agent.py `_chat` |
| `rapp-twin-chat-response/1.0` | Legacy twin-chat reply wrapper | historical NEIGHBORHOOD_PROTOCOL §6e | migration-only twin_agent.py `_chat` |
| `rapp-public-facets/1.0` | Granular permission gate (name + scope + description) | NEIGHBORHOOD_PROTOCOL §7 | card.json (operator-set) |
| `rapp-twin-spec/1.0` | Historical soul identity block | ANTIPATTERNS §4 | retired `installer/plant.sh`; not a current producer |
| `rapp-lineage-rollup/1.0` | Lineage tree aggregation result (avg/median/min/max MMR) | ECOSYSTEM §15 | agents/lineage_rollup_agent.py |
| `rapp-species-leaderboard/1.0` | Global Herald → Immortal ladder | ECOSYSTEM §15 | agents/species_leaderboard_agent.py |
| `rapp-proximity-match/1.0` | Geohash-prefix match result (Pizza Place layer) | ECOSYSTEM §15, HERO_USECASE §4 | agents/proximity_discovery_agent.py |
| `rapp-resurrection-assessment/1.0` | Stasis-state diagnosis | ECOSYSTEM §15 | agents/resurrection_ceremony_agent.py |
| `rapp-resurrection-ceremony/1.0` | Resurrection frame + next-step commit template | ECOSYSTEM §15, Art. XXXIV.5 | agents/resurrection_ceremony_agent.py |
| `rapp-release-key/1.0` | ed25519 keypair generation envelope | CONSTITUTION Art. XXXIV.7 | tools/sign_release.py keygen |
| `rapp-release-signature/1.0` | ed25519 detached signature sidecar | CONSTITUTION Art. XXXIV.7 | tools/sign_release.py sign |
| `rapp-pheromone/1.0` | Ant-farm pheromone (content-addressed, prev_hash chained) | kody-w/ant-farm/skill.md | agents/ant_agent.py + ant-pheromone-labeled GitHub Issues |
| `rapp-colony-observation/1.0` | Ant-farm collective state synthesis | (defined-by-emitter) | agents/colony_observer_agent.py |
| `rapp-ant-tick/1.0` | Ant-agent tick result envelope | (defined-by-emitter) | agents/ant_agent.py perform() |
| `rapp-rar-index/1.0` | Per-neighborhood RAR registry — required participation kit | (defined-by-emitter; published per planted seed at `rar/index.json`) | every planted seed; loader: rapp_brainstem/agents/rar_loader_agent.py |
| `rapp-rar-manifest/1.0` | sha256 verification block inside `rar/index.json` | (companion to rapp-rar-index/1.0) | every planted seed |
| `rapp-rar-loadout/1.0` | Result envelope — what the RarLoader installed/skipped/errored | (defined-by-emitter) | rapp_brainstem/agents/rar_loader_agent.py |
| `rapp-graft-result/1.0` | Bond-technique graft result envelope (files added/skipped/restored, bond_event, metropolis roll-up state) | (defined-by-emitter; companion to bond.py kind="graft") | rapp_brainstem/agents/graft_neighborhood_agent.py |
| `rapp-launch-result/1.0` | LOCAL→GLOBAL launch envelope — local brainstem snapshot delivered to a target public repo (egg sha256 + continuation manifest URL + fork lineage) | (defined-by-emitter; companion to bond.py kind="launch") | rapp_brainstem/agents/launch_to_public_agent.py |
| `rapp-launch-continuation/1.0` | The LAUNCH_CONTINUATION.md instructions left in the target repo so a downstream brainstem can hatch the launched egg via `utils.bond hatch` | (defined-by-emitter; written into the target repo at root) | rapp_brainstem/agents/launch_to_public_agent.py |
| `rapp-launch-fingerprint/1.0` | Compact fingerprint block embedded in the launch result + continuation: rappid + egg sha256 + parent_commit + bond technique pointer | (defined-by-emitter) | rapp_brainstem/agents/launch_to_public_agent.py |
| `rapp-ecosystem-audit/1.0` | Drift detector envelope — per-offspring drift entries + by-kind counts + suggested next-actions classified as LOCAL_TO_GLOBAL / GLOBAL_TO_LOCAL / INFORMATIONAL | (defined-by-emitter; written to `pages/_audit/ecosystem-audit.{md,json}`) | tools/ecosystem_audit.py |
| `rapp-rhythm-pulse/1.0` | Bond Pulse heartbeat envelope — pulse_at + audit_summary + suggested_actions[] + by_direction counts + degraded flag + bond_event reference. Operator-mediated; never auto-executes. | (defined-by-emitter; companion to bond.py kind="rhythm") | rapp_brainstem/agents/bond_rhythm_agent.py |
| `rapp-dock-result/1.0` | Universal additive-merge result envelope (added/skipped + pre/post sha256 + parallel-to-other-dock-scopes mapping + optional bond event) | (defined-by-emitter; companion to bond.py kind="dock") | rapp_brainstem/agents/dock_agent.py |
| `rapp-twin/1.0` | Legacy mobile-side bundle; not a RAPP/1 egg schema | historical/retired mobile emitter | migration-only mobile client; no current target implementation |
| `rapp-twin-identity/1.0` | Historical/retired onboard identity envelope | former onboard emitter (removed) | no current target implementation |
| `rapp-neighborhood/1.0` | Neighborhood metadata | gate repo `neighborhood.json` | plant_discord_neighborhood_agent.py, fixtures |
| `rapp-neighborhood-protocol/1.0` | Application federation metadata; not a RAPP wire | NEIGHBORHOOD_PROTOCOL header | historical/external guide |
| `rapp-neighborhood-members/1.0` | Roster | gate repo `members.json` | neighborhood_membership_organ.py |
| `rapp-neighborhood-subscription/1.0` | One subscription record (gate_url, role, etc.) | (organ-defined) | neighborhood_membership_organ.py |
| `rapp-neighborhoods-cache/1.0` | Local cache file | (organ-defined) | neighborhood_membership_organ.py |
| `rapp-estate/1.0` | Estate top-level (organ-aggregated view, server-side) | vault/Decisions 2026-05-08 | neighborhood_membership_organ.py `_estate_view` |
| `rapp-estate/1.1` | Local-first estate FILE format (door catalog at `~/.brainstem/estate.json` + `<gh>/rapp-estate/main/estate.json`). Each entry stores ONLY `{rappid, added_at, via}`. **Authority: pages/docs/ESTATE_SPEC.md, CONSTITUTION Article XLVI** | pages/docs/ESTATE_SPEC.md | rapp_brainstem/agents/estate_agent.py |
| `rapp-door/1.0` | Application-local candidate door URLs; pure parsing does not establish the current anchor | superseded ESTATE_SPEC derivation appendix | legacy `tools/door_address.py`; verify §13 |
| `rapp-facets/1.0` | Per-door published-capability declaration at `<owner>/<repo>/main/facets.json` | pages/docs/ESTATE_SPEC.md §3 (Door URL Set #9) | rapp_brainstem/agents/plant_seed_agent.py |
| `rapp-estate-view/1.0` | Aggregated twin view (zones + bridges) | (organ-defined) | estate_organ.py |
| `rapp-estate-eggs/1.0` | Estate egg index | (organ-defined) | estate_organ.py |
| `rapp-rappid-estate-view/1.0` | Estate-by-rappid lookup (global passport) | project_rappid_is_global_passport memory | neighborhood_membership_organ.py `by-rappid` |
| `rapp-braintrust-contribution-receipt/1.0` | Contribution acknowledgment (organ-local; cross-org goes via §5b Issues) | NEIGHBORHOOD_PROTOCOL §5b "Organ-local HTTP shortcut" | neighborhood_membership_organ.py `contribute` |
| `rapp-discord-bridge/1.0` | Discord planting bridge config | NEIGHBORHOOD_PROTOCOL §4e | plant_discord_neighborhood_agent.py |
| `rapp-discord-plant-envelope/1.0` | Discord plant operation result | NEIGHBORHOOD_PROTOCOL §4e | plant_discord_neighborhood_agent.py |
| `rapp-peers/1.0` | Peer registry (legacy) | utils/peer_registry.py | peer_registry.py |
| `rapp-peers/1.1` | Peer registry (current) | utils/peer_registry.py | peer_registry.py |
| `rapp-peers-view/1.0` | Peer-list view | (organ-defined) | neighborhood_organ.py |
| `rapp-tether/1.0` | WebRTC tether envelope | NEIGHBORHOOD_PROTOCOL §5a (implicit) | front door tether |
| `rapp-egg/1.0` | Generic egg shell (legacy) | utils/egg.py | utils/egg.py |
| `rapp-egg-hub-entry/1.0` | Egg hub catalog entry | kody-w/rapp-egg-hub | twin_agent.py `_lay_egg` sidecar |
| `rapp-lifecycle-catalog/1.0` | Lifecycle catalog (kernel versions + incarnations) | (organ-defined) | lifecycle_organ.py |
| `rapp-store/1.0` | Store catalog meta | kody-w/RAPP_Store | (external) |
| `rapp-registry/1.0` | RAR registry | vault/Architecture/RAR | (external) |
| `rapp-cloud-registry/1.0` | Historical/retired onboard catalog schema | former onboard registry emitter (removed) | no current target implementation; not a RAPP/1 §13 registry |
| `rapp-version/1.0` | Kernel version pin | rapp_kernel/manifest | rapp_kernel/manifest.json |
| `rapp-version/1.1` | Kernel version pin (signed) | vault/Architecture/Signed Releases | rapp_kernel/manifest.json |
| `rapp-kernel/1.1` | Kernel release manifest | vault/Architecture/Signed Releases | rapp_kernel/manifest.json |
| `rapp-binder/1.0` | Legacy onboarding binder (saved JSON of starter cards; not RAPP/1) | historical `utils/web/rapp.js` emitter (retired) | no active implementation; exact browser suite retained under `tests/fixtures/legacy-conformance/` |
| `rapp-memory/1.0` | Memory record | manage_memory_agent.py | manage_memory_agent.py |
| `rapp-application/1.0` | Rapplication manifest | pages/docs/rapplication-sdk.md | RAPP_Store entries |
| `rapp-chat-response/1.0` | Legacy/application-local chat wrapper | tools/test_brainstem_server.py | migrate boundary to exact RAPP/1 §8 response |
| `rapp-test-brainstem/1.0` | Test fixture identity | tools/test_brainstem_server.py | test fixture |
| `rapp-local-ping/1.0` | Test ping agent | tests/fixtures/local-only-test/ | test fixture |
| `rapp-metropolis-index/1.0` | Metropolis tracker top-level | pages/metropolis/README.md | pages/metropolis/index.json |
| `rapp-metropolis-entry/1.0` | One neighborhood entry in tracker | pages/metropolis/README.md | pages/metropolis/index.json |
| `rapp-vbrainstem-subscription/1.0` | vbrainstem subscription record (LEGACY surface — the **older** mobile vbrainstem at `pages/vbrainstem/index.html`, distinct from the new `pages/vbrainstem.html` tethered surface added 2026-05-10) | pages/vbrainstem/index.html:355 (defined-by-emitter) | pages/vbrainstem/index.html |
| `rapp-zoo-collection/1.0` | rapp-zoo localStorage cartridge | rapp-zoo/index.html:481 (defined-by-emitter) | rapp-zoo/index.html |
| `rapp-swarm/1.0` | Historical/retired mobile swarm bundle | former mobile emitter (removed) | no current target implementation |
| `rapp-brainstem-backup/1.0` | Local brainstem backup snapshot | rapp_brainstem/index.html:1966 (defined-by-emitter) | rapp_brainstem/index.html |
| `rapp-cubby/1.0` | Universal cubby — per-member estate housing; same anatomy as a brainstem; works on-device AND in a neighborhood (egg-roundtrips) | NEIGHBORHOOD_PROTOCOL §19; PUBLIC_PRIVATE_BOUNDARY §1.8 | `@rapp/rapp` (rapp_agent.py); private cubby neighborhoods |
| `rapp-super-rar/1.0` | Application content catalog across cubbies; not the RAPP/1 §13 registry | historical NEIGHBORHOOD_PROTOCOL §19 | legacy `@rapp/rapp` super_rar |
| `rapp-payphone-dial/1.0` | Dark-door dialer — reach a private door's rappid on the public web with your own auth (404 to outsiders) | NEIGHBORHOOD_PROTOCOL §19 | pages/payphone.html |
| `brainstem-egg/2.3-cubby` | Legacy cubby-cartridge proposal; not a RAPP/1 §9 variant | historical NEIGHBORHOOD_PROTOCOL §19 | migration inventory only |
| `rapp-ecosystem-graph/1.0` | Historical repo graph observation | divergent external `rapp-map`; non-authoritative | historical generator |
| `rapp-canon/1.0` | Application drift index; not structural authority or the signed §13 registry | (defined-by-emitter) | `@rapp/drift` observation |
| `rapp-drift-report/1.0` | Cross-repo drift observation; cannot resolve or create RAPP authority | (defined-by-emitter) | `@rapp/drift` scan |
| `rapp-drift-issue/1.0` | Drift-issue machine block — the traceable chain (drift → GitHub issue → PR → operator merge → close) | (defined-by-emitter) | `@rapp/drift` + `@rapp/drift_watcher` |
| `rapp-rar-steward/1.0` | RAR steward report — catalog health, same-but-different merge clusters, noise/junk | (defined-by-emitter) | `@rapp/rar_steward` |
| `rapp-neuron/1.0` | Historical file-specialist metadata | divergent external `rapp-map`; non-authoritative | historical workflow |
| `rapp-neuron-mesh/1.0` | Historical word-level index | divergent external `rapp-map`; non-authoritative | historical workflow |
| `rapp-neuron-mesh-manifest/1.0` | Historical summon index | divergent external `rapp-map`; non-authoritative | historical workflow |

---

## §6 — Implementation map (file → spec section)

| File | Owns | Spec section |
|---|---|---|
| `rapp_brainstem/brainstem.py` | /chat surface, provider dispatch, organ dispatch | KERNEL — CONSTITUTION Art. XXXIII |
| `rapp_brainstem/agents/basic_agent.py` | Agent base class | KERNEL — CONSTITUTION Art. XXXIII |
| `rapp_brainstem/agents/manage_memory_agent.py` | Memory R/W | KERNEL — ECOSYSTEM §5 |
| `rapp_brainstem/agents/context_memory_agent.py` | Conversation context | KERNEL — ECOSYSTEM §5 |
| RAR: `agents/@rapp/twin_agent.py` *(legacy; not kernel-shipped)* | Historical twin-chat and egg adapter. It is not current §8 wire or §9 acceptance. | historical NEIGHBORHOOD_PROTOCOL §6, §7 |
| `rapp_brainstem/agents/learn_new_agent.py` | Historical/retired local agent path; no current target implementation. | ECOSYSTEM §7 (Evolution) |
| `rapp_brainstem/agents/swarm_factory_agent.py` | Historical/retired Tier-2 factory path; no current target implementation. | rapp_swarm/ |
| `rapp_brainstem/agents/perpetual_loop_factory_agent.py` | Historical/retired background-loop proposal; no current target implementation. | (no spec section yet — see §13) |
| `rapp_brainstem/agents/hacker_news_agent.py` | Demo HN agent | (example) |
| RAR: `agents/@rapp/egg_hatcher_agent.py` *(installable; not kernel-shipped)* | Legacy hatcher inventory. Its schema/type router is not current §9 dispatch; a conformant replacement dispatches registered `variant` only after all §9.3 checks. | retired `brainstem-egg/2.x` family |
| `pages/vbrainstem.html` | Contained legacy browser surface whose retired `brainstem-egg/2.3-session` export is migration evidence, not a current RAPP egg. | superseded local SPEC history |
| RAR: `agents/@kody/workiq_agent.py` *(installable; not kernel-shipped)* | Microsoft 365 access (email/calendar/Teams/SharePoint/OneDrive) via the workiq CLI + Entra ID. Solo install from RAR; no pack. | (example) |
| `rapp_brainstem/agents/plant_discord_neighborhood_agent.py` | Historical/retired Discord planting agent; no current target implementation. | NEIGHBORHOOD_PROTOCOL §4 (discovery) |
| `rapp_brainstem/agents/lineage_rollup_agent.py` | Historical/retired feature agent; no current target implementation. | ECOSYSTEM §15 (shipped 2026-05-08) |
| `rapp_brainstem/agents/species_leaderboard_agent.py` | Historical/retired feature agent; no current target implementation. | ECOSYSTEM §15 (shipped 2026-05-08) |
| `rapp_brainstem/agents/proximity_discovery_agent.py` | Historical/retired feature agent; no current target implementation. | ECOSYSTEM §15, HERO_USECASE §4 |
| `rapp_brainstem/agents/resurrection_ceremony_agent.py` | Historical/retired feature agent; no current target implementation. | ECOSYSTEM §15, Art. XXXIV.5 |
| `rapp_brainstem/agents/ant_agent.py` | Historical/retired Ant Farm agent; no current target implementation. | kody-w/ant-farm/skill.md, NEIGHBORHOOD_PROTOCOL §5b |
| `rapp_brainstem/agents/colony_observer_agent.py` | Historical/retired Ant Farm observer; no current target implementation. | (companion to ant_agent) |
| `rapp_brainstem/agents/rar_loader_agent.py` | Historical/retired local RAR loader; not a current §§10/13 acceptance path. | rapp-rar-index/1.0 + rapp-rar-loadout/1.0 |
| `rapp_brainstem/agents/graft_neighborhood_agent.py` | Historical/retired graft agent; no current target implementation. | rapp-graft-result/1.0 + rapp-metropolis-index/1.0 + bond.py event "graft" |
| `rapp_brainstem/agents/dock_agent.py` | Historical/retired dock agent; no current target implementation. | rapp-dock-result/1.0 + bond.py event "dock" |
| `rapp_brainstem/agents/launch_to_public_agent.py` | Historical/retired launch agent; no current target implementation. | rapp-launch-result/1.0 + rapp-launch-continuation/1.0 + rapp-launch-fingerprint/1.0 + bond.py event "launch" |
| `rapp_brainstem/agents/bond_rhythm_agent.py` | Historical/retired Bond Pulse agent; offline audit tooling remains separate. | rapp-rhythm-pulse/1.0 + bond.py event "rhythm" |
| `tools/ecosystem_contract.py` | Pure-data per-kind contract. Defines what files MUST exist for each of the 9 offspring kinds (neighborhood, ant-farm, twin, workspace, braintrust, catalog, template, installer, egg-hub). Zero behavior; imported by ecosystem_audit. Includes `KERNEL_BASE_FILES` (full kernel) AND `SEED_REQUIRED_AGENTS = ("basic_agent.py",)` (minimum agents that ship in planted seeds). | (no schema; pure data) |
| `tools/ecosystem_audit.py` | Stdlib-only drift detector. Reads `pages/metropolis/index.json` → diffs each offspring against `ecosystem_contract` → classifies drift (missing_files / schema_drift / rappid_drift / kernel_drift / identity_block_missing) → emits `pages/_audit/ecosystem-audit.{md,json}`. CLI: `--offline` (default; uses fixtures), `--online`, `--repo`, `--metropolis`, `--fixtures-dir`, `--out-dir`, `--no-write`, `--strict/--lenient`. Exit 1 on drift (default strict). | rapp-ecosystem-audit/1.0 |
| `tools/sign_release.py` | ed25519 keygen / sign / verify for `rapp_kernel/manifest.json` | CONSTITUTION Art. XXXIV.7 |
| `tools/door_address.py` | Exact §6.1 parser backed by `rapp1_core`. Active URL resolution accepts only full lowercase RAPP/1 identities and reads application kind from the matching identity record. Historical forms are observable only through an explicit non-resolving migration API. | target-owned RAPP/1 adapter |
| `tools/backfill_seeds.py` | Read-only historical-door migration planner. Strict parse, record-kind, and source owner/slug failures return `OWNER_ACTION_REQUIRED`; apply/remint/PUT paths are retired until a valid §6.3/§13.3 owner authorization can be verified. | target-owned plan-only migration adapter |
| `tools/rebuild_estate.py` | Application catalog recovery from untrusted GitHub candidates. Handle/repo and `parent_rappid` fallbacks do not establish identity; preserve §6 tails and verify §13 state. | product recovery, subordinate to RAPP/1 |
| `tools/sniff_network.py` | Article XLVII decentralized discovery. Default mode: BFS-from-seed via raw URLs only (no GitHub Search API). Walks `.well-known/rapp-network-seed.json` → each operator's `.well-known/rapp-network.json` beacon → `discovery.federation_hints[]` adds new nodes. Optional `--via topic` for periodic sweeps via `gh search repos topic:rapp-estate`. Returns `rapp-network-sniff/1.0`. | rapp-network-sniff/1.0 |
| `.well-known/rapp-network-seed.json` (in species root kody-w/RAPP) | The DNS-root analog for the federation. Lists known operators as the BFS starting set. Convenient but not authoritative; anyone can fork the species root and host their own seed. | rapp-network-seed/1.0 |
| `.well-known/rapp-network.json` (per published estate) | External template, not a repository-local implementation path. Per-operator beacon emitted by a published estate. | rapp-network-beacon/1.1 |
| `tools/path_opacity.py` | Article XLVIII.6 URL opacity helpers. `opaque_path(secret, kind, id)` → `kinds/<HMAC>/<HMAC>.json`; `decode_local(secret, opaque, …)` (operator-only); `audit_paths(file_paths)` for publish-time enforcement; `OPACITY_REGEX` for downstream consumers. Pure stdlib. | (no schema; pure helper) |
| `tools/private_estate_init.py` | Bootstraps `<handle>/rapp-estate-private` (PRIVATE GitHub repo). Mints the per-operator HMAC secret to `~/.brainstem/private-estate-secret` (mode 0600). Scaffolds the opaque file set (meta.json, README, objects/.gitkeep, kinds/.gitkeep). Returns commitment hash for the public beacon. Idempotent. | rapp-private-estate/1.0 |
| `pages/docs/PUBLIC_PRIVATE_BOUNDARY.md` | Canonical Article XLVIII spec — the two-tier estate, audience field, commitment pattern, URL opacity contract, access semantics (GitHub collab perms + CODEOWNERS), receiver-controls discipline. | rapp-private-estate/1.0 |
| `pages/docs/SUBSTRATE_FEDERATION.md` | Canonical Article XLVII.5 spec — the four substrates (GitHub raw, LAN HTTP + Bonjour, AirDrop'd egg, sneakernet file://). One protocol; substrate-agnostic discovery via tools/sniff_network.py::_resolve_node(). | rapp-network-beacon/1.1 |
| `tools/lan_advertise.py` | Article XLVII.5.1 reference advertiser. Wraps `python3 -m http.server` + `dns-sd -R` to register `_rapp-estate._tcp.local` Bonjour service with TXT records carrying rappid + beacon path. | (no schema; uses Bonjour + http.server) |
| `tools/import_peer_egg.py` | Strict RAPP/1 structural inspector and authenticated-import gate. `--inspect` never accepts/imports; default import calls `accept_egg` and returns explicit `UNVERIFIED` with no writes because this target has no authenticated §13 registry. Legacy extraction, seed mutation, and beacon repair are retired. | rapp-peer-egg-result/1.0 |
| `<handle>/rapp-estate-private` (PRIVATE repo per operator) | The private tier of every Article-XLVIII-compliant estate. Mandatory from first install. All paths opaque per §XLVIII.6. Access via GitHub collaborator perms. Content NEVER fetched by sniffers. | rapp-private-estate/1.0 |
| `pages/docs/ESTATE_SPEC.md` | The canonical Estate Spec — formalizes rappid-as-global-address + Door URL Set + estate.json shape + discovery protocol. Constitutional (Article XLVI). | (the spec itself) |
| `specs/SPEC.md` + `specs/skill.md` | Superseded local spec and non-runtime host-onboarding history. Neither defines RAPP capabilities or current wire behavior. | retired `rapp-protocol/1.0`; migrate to the pinned rev-5 authority |
| `rapp_brainstem/agents/estate_agent.py` | Historical/retired estate agent; no current target implementation. | rapp-estate/1.1 |
| `rapp_brainstem/utils/organs/neighborhood_organ.py` | Historical/retired peer-view organ; no current target implementation. | NEIGHBORHOOD_PROTOCOL §4 |
| `rapp_brainstem/utils/organs/neighborhood_membership_organ.py` | Historical/retired membership organ; explicit retirement tests prevent restoration. | vault Decision 2026-05-08, NEIGHBORHOOD_PROTOCOL §2 |
| `rapp_brainstem/utils/organs/estate_organ.py` | Historical/retired estate organ; no current target implementation. | vault Decision 2026-05-08 |
| `rapp_brainstem/utils/organs/swarm_estate_organ.py` | Historical/retired swarm-estate organ; no current target implementation. | (impl) |
| `rapp_brainstem/utils/organs/lifecycle_organ.py` | Historical/retired lifecycle organ; no current target implementation. | ECOSYSTEM §1 |
| `rapp_brainstem/utils/bond.py` | Historical/retired egg and lineage utility; legacy inputs are migration evidence only. | CLAUDE.md identity & bonding |
| `rapp_brainstem/utils/egg.py` | Historical/retired egg utility; current egg handling is governed by RAPP/1 §9. | ECOSYSTEM §8 |
| `rapp_brainstem/utils/peer_registry.py` | Historical/retired peer cache; no current target implementation. | NEIGHBORHOOD_PROTOCOL §4 |
| `rapp_brainstem/utils/llm.py` | Historical/retired split provider module; current pinned runtime logic remains in brainstem.py. | CLAUDE.md provider dispatch |
| `rapp_brainstem/utils/local_storage.py` | Local JSON shim for AzureFileStorageManager | CLAUDE.md local storage shim |
| `rapp_brainstem/utils/boot.py` | Target-owned HTTP-410 boot tombstone; never imports or starts the immutable server. | RAPP1_STATUS.md containment |
| `rapp_brainstem/index.html` | Retained historical UI; exercised only as isolated immutable test evidence. | ECOSYSTEM §4a |
| `rapp_brainstem/utils/web/onboard/` | Historical/retired onboarding directory; no current target implementation. | ECOSYSTEM §4 |
| `rapp_brainstem/utils/web/mobile/` | Historical/retired mobile directory; no current target implementation. | rapp-vbrainstem-subscription/1.0 |
| `rapp_swarm/function_app.py` | Tier-2 Azure Functions /chat | CLAUDE.md Tier 2 |
| `rapp_swarm/_vendored/` | Vendored brainstem core | CLAUDE.md vendoring |
| `rapp_swarm/build.sh` | Vendor brainstem into _vendored/ | CLAUDE.md vendoring |
| `worker/worker.js` | Cloudflare auth/proxy worker (Copilot device-code, chat proxy) | ECOSYSTEM §12 (External integrations) |
| `installer/install.sh` | Install one-liner (sacred URL — Art. V) | CONSTITUTION Art. V, ANTIPATTERNS §2 |
| `installer/plant.sh` | Retired/contained producer; no current planting CTA | Historical ECOSYSTEM §13 |
| `installer/install.ps1` / `install.cmd` | Windows installers | CONSTITUTION Art. V |
| `installer/azuredeploy.json` | ARM template (Tier 2 deploy) | CLAUDE.md Tier 2 |
| `installer/MSFTAIBASMultiAgentCopilot_*.zip` | Tier 3 Copilot Studio bundle | CLAUDE.md Tier 3 |
| `installer/shortcuts/protocol.md` | iOS Shortcuts URL/POST contract | ECOSYSTEM §4 (chat surfaces) |
| `rapp_kernel/latest/` + `rapp_kernel/v/<version>/` | Historical archive; `latest` is moving/divergent and non-authoritative. Current immutable grail pin is `kody-w/rapp-installer@brainstem-v0.6.9`. | `KERNEL_PIN.json` |
| `rapp_kernel/manifest.json` | Kernel version catalog | rapp-kernel/1.1 |
| `pages/about/anatomy.html` | Visual organism diagram | CLAUDE.md visual anatomy |
| `pages/onboarding.html` | Visitor-facing onboarder (trust-building) | CLAUDE.md hero use case section |
| `pages/sphere.html` | 3D chat interface | (front door variant) |
| `pages/metropolis/index.json` + `index.html` | Metropolis tracker (Kazaa-style directory) | pages/metropolis/README.md |
| `pages/metropolis/plant-from-discord.html` | Mobile Discord-plant guide | (mobile guide) |
| `pages/vbrainstem/index.html` | Browser-based brainstem | (mobile/auth-worker dependent) |
| `pages/_site/index.json` | Site manifest (canonical inventory) | CLAUDE.md key directories |
| `pages/vault/` | Obsidian vault — decision narratives | CONSTITUTION Art. XXIII |
| `rapp-zoo/` | Historical/external Pokédex path; moved out of this repository. | CLAUDE.md visual anatomy |
| `tests/run-tests.mjs` | Current dependency-free RAPP/1 core/static contract checks | DEFINITION_OF_DONE |
| `tests/vault-check.mjs` | Vault link/PII guardrail | DEFINITION_OF_DONE |
| `tests/scenarios/*.sh` | E2E scenarios (incl. survival) | SURVIVAL "How to test" |
| `tests/doorman/` | Tether + Dream Catcher conformance | HERO_USECASE.md §1, §2 |
| `tests/dreamcatcher-conformance/` | Dream Catcher protocol conformance | HERO_USECASE.md §2 |
| `tests/features/F1-lineage-rollup.sh` | Historical/retired positive test; exact bytes are quarantined as migration evidence. | ECOSYSTEM §15 |
| `tests/features/F2-leaderboard.sh` | Historical/retired positive test; exact bytes are quarantined as migration evidence. | ECOSYSTEM §15 |
| `tests/features/F3-proximity.sh` | Historical/retired positive test; exact bytes are quarantined as migration evidence. | ECOSYSTEM §15, HERO_USECASE §4 |
| `tests/features/F4-ed25519-sign.sh` | Historical/retired positive test; exact bytes are quarantined as migration evidence. | CONSTITUTION Art. XXXIV.7 |
| `tests/features/F5-resurrection.sh` | Historical/retired positive test; exact bytes are quarantined as migration evidence. | ECOSYSTEM §15, Art. XXXIV.5 |
| `tests/features/run.sh` | Feature suite master runner | (this doc) |
| `tools/test_brainstem_server.py` | Lightweight HTTP server for federation tests | (test infra) |
| `.github/workflows/plant-approved-place.yml` | Disabled historical workflow; no authenticated replacement producer | `RAPP1_STATUS.md` |
| `.github/prompts/write-agent.prompt.md` | AI prompt to author an agent | ECOSYSTEM §7 |

---

## §7 — Application channel × scope matrix

These channels are transports/adapters, not extra RAPP wire forms. At a
protocol boundary each interaction must become either the exact synchronous
RAPP/1 §8 `/chat` exchange or a verified asynchronous §7 frame.

|              | Personal           | Neighborhood       | Public swarm       |
|---           |---                 |---                 |---                 |
| **WebRTC §5a** (live, ephemeral, DTLS) | Pair this device | Live tether to known peer | Cold pair w/ unknown — Charizard handoff |
| **Issues §5b** (async, durable) | label: `private-memory` | label: `neighborhood-message` | label: `egg-submission`, `agent-proposal` |
| **PRs §5c** (asymmetric consent gate) | (operator-only on own seed) | `agent-proposal` merge | `agent-proposal` merge |
| **raw fetch §5d** (read-only, content-addressed) | (cache fill) | private companion sha (collaborator) | seed repo sha (anyone) |

---

## §8 — Historical twin-chat adapter messages

The table inventories the retired/application `rapp-twin-chat/1.0` adapter. It
does not define a third RAPP wire. Current implementations encode registered
semantics in the exact RAPP/1 §8 wire forms and verify asynchronous frames per
§7 before acting.

| `kind` | Payload | Direction | Purpose |
|---|---|---|---|
| `say` | `{ text }` | A → B | Plain conversation. Same shape as a doorman chat turn. |
| `share-fact` | `{ fact, scope, source_rappid }` | A → B | "Here's something I think your organism would find useful." Recipient decides whether to absorb. **Default scope: personal** (most restrictive). |
| `share-egg` | `{ egg-begin/chunk/end }` | A → B (chunked) | Stream an organism cartridge over the channel. Same protocol as front door's tether-egg send. |
| `request-fact` | `{ topic }` | A → B | "Do you know anything about X?" Recipient may respond with `share-fact` or decline. |
| `ack` | `{ for_hash, accepted \| rejected }` | B → A | Receipt + optional reason. |

Knowledge-exchange primitives (NEIGHBORHOOD_PROTOCOL §8) compose these: pull-fact (8a), push-fact (8b), trade-egg (8c), reassimilate-dimensions (8d).

---

## §9 — Three-tier model + contract surface

```
        ┌──── Tier 3: Enterprise (Microsoft Copilot Studio) ────┐
        │  installer/MSFTAIBASMultiAgentCopilot_*.zip            │
        │  Same agent contract; cloud-managed via M365           │
        └──────────────────────┬─────────────────────────────────┘
                               │
        ┌──── Tier 2: Cloud (Azure Functions) ──────────────────┐
        │  rapp_swarm/function_app.py + _vendored/               │
        │  Endpoints under /api/* (path-prefix vs Tier 1)        │
        └──────────────────────┬─────────────────────────────────┘
                               │
        ┌──── Tier 1: Local (Flask :7071) ──────────────────────┐
        │  rapp_brainstem/brainstem.py                           │
        │  POST /chat — {user_input, session_id?,                │
        │                 idempotency_key?} (RAPP/1 §8 target)   │
        │  GET  /api/identity, /api/lineage                      │
        │  GET/POST /api/estate/*, /api/neighborhoods/*          │
        └────────────────────────────────────────────────────────┘
```

| Capability | Tier 1 | Tier 2 | Tier 3 |
|---|---|---|---|
| Exact RAPP/1 §8 `POST /chat` | target; see `RAPP1_STATUS.md` | adapter must expose exact boundary | adapter must expose exact boundary |
| Application views: `GET /api/identity`, `/api/lineage` | ✓ | n/a | n/a |
| Application adapter: `/api/neighborhoods/*` | ✓ | n/a | n/a |
| Application view: `/api/estate/*` | ✓ | n/a | n/a |
| Agent contract (`rapp-agent/1.0`) | ✓ | ✓ | ✓ (Studio plugin shell) |
| Same `*_agent.py` files run unmodified | ✓ | ✓ | ✓ |

Differs legitimately: storage backend (local JSON vs Azure Files), auth (Copilot device-code vs Azure RBAC vs M365), surface (local process vs Functions vs Power Platform).

The exact success body is
`{response:string, agent_logs:[string], session_id:string}` with no extra
members. Malformed, refused, or unknown-session requests return HTTP 422
`{error:{code:string, step:string|null}}`; see RAPP/1 §8 for the complete
contract.

---

## §10 — Immutable grail and governed files

| File / artifact | Why sacred | Article / source |
|---|---|---|
| `rapp_brainstem/brainstem.py` | Pinned byte mirror; never edit locally | `kody-w/rapp-installer@brainstem-v0.6.9`; authority immutable-grail policy |
| `rapp_brainstem/agents/basic_agent.py` | Pinned byte mirror; never edit locally | same immutable grail |
| `rapp_brainstem/VERSION` | Pinned byte mirror; never edit locally | same immutable grail |
| `rapp_brainstem/agents/manage_memory_agent.py` | Governed drop-in application agent, not a pinned grail byte | repository policy |
| `rapp_brainstem/agents/context_memory_agent.py` | Governed drop-in application agent, not a pinned grail byte | repository policy |
| `rapp_swarm/function_app.py` | Tier-2 kernel mirror | CONSTITUTION Art. XXXIII |
| Install one-liner URL (`https://kody-w.github.io/RAPP/installer/install.sh`) | Sacred URL shape forever | CONSTITUTION Art. V |
| `\|\|\|VOICE\|\|\|` / `\|\|\|TWIN\|\|\|` delimited slots | Fixed forever — never repurposed | CLAUDE.md sacred constraints §5 |
| `parent_rappid` in legacy `rappid.json` | Application provenance only; not RAPP identity or trust | historical lineage policy |

**If something feels like it requires a kernel change → write an agent or organ instead.** If the agent contract genuinely can't express it, that's a CONSTITUTION-level conversation that touches every planted seed.

---

## §11 — "Before you do X" decision table

The most load-bearing section. Workflow trigger → pre-check (≤30s) → spec to deep-read.

| Trigger | Pre-check | Deep-read |
|---|---|---|
| Starting a new session in this repo | §0–§3 (orient: how-to-read, authority, fractal, primitives); skim §11 + §13 | CLAUDE.md; MASTER_PLAN.md if scope unclear |
| Add a new agent | §6 (does it already exist?), §15 (lexicon — it's an agent), `rapp-agent/1.0` in §5 | CLAUDE.md "Agent System"; pages/docs/SPEC.md |
| Add a new organ | §6 (existing organ already covers this?), §9 (endpoint already on another tier?) | CLAUDE.md Architecture §Organ; CONSTITUTION Art. XXXIII |
| Call `/chat` from new code | Use the exact RAPP/1 §8 request and exact 200/422 responses; do not wrap it in a legacy twin-chat envelope | pinned RAPP/1 §8 |
| Change protocol structure | Follow Constitution Articles II–IV and §13 registration; do not mint a schema in an application doc | pinned RAPP/1 + Constitution |
| Use an existing schema | §5 row → defining doc column → read that section | the doc the row points at |
| Audit ecosystem mirrors | Use exact immutable local pins. `rapp-god`, `rapp-map`, moving-main files, and their neuron metadata are non-authoritative/divergent observations, never resolver authority. | `RAPP1_AUTHORITY.json`; `RAPP1_STATUS.md` |
| Historical private-cubby planting | Retired; no current producer or CTA. Collaborator status would remain application authorization only. | RAPP/1 §§8, 10, 13 |
| Historical GitHub planting | Retired; do not run `plant.sh` or treat an application index as acceptance. | `RAPP1_STATUS.md` |
| Historical hot-load | Retired; no current participation-kit install path. | RAPP/1 §§10/13 |
| Historical graft/docking | Retired product design; no current overlay producer. | Preserved vault history |
| Add an entry to ANY rar-shaped JSON registry without clobbering existing | universal additive-merge primitive — same dock property at the registry/list-of-dicts scope; supports `key_field` dedup; bond event log; works for `rar/index.json`, `_metropolis.json`, `members.json`, etc. | rapp_brainstem/agents/dock_agent.py; F9 |
| Want to know if local + global ecosystem are still in sync (the FULL organism, not one half) | Run the Bond Pulse heartbeat — operator-mediated; pulses audit + classifies drift LOCAL→GLOBAL push (suggest Launch/Graft) vs GLOBAL→LOCAL pull (suggest RarLoader); records `kind="rhythm"` event; gracefully degrades when offline | rapp_brainstem/agents/bond_rhythm_agent.py; tools/ecosystem_audit.py; F10/F11/F12; vault note `pages/vault/Decisions/2026-05-09 — Bond Pulse — the on-going beat for the full organism.md` |
| Discover a door candidate | Validate the §6 rappid, parse its initial self-location, then resolve current anchors/keys through the signed §13 registry. Raw files are untrusted transport. | RAPP/1 §§6, 10, 13 |
| Discover an application estate catalog | Fetching `estate.json` yields untrusted candidates; validate each §6 rappid and registry state before use. | RAPP/1 §§6/13; ESTATE_SPEC product convention |
| Recover a lost local estate | Recovery tooling may rebuild an application cache from public candidates, but trusted state comes from verified artifacts and monotonic §13 state—not "the network." | RAPP/1 §§7, 10, 13 |
| Resolve which estate anchors a rappid | Validate §6 and resolve the signed §13 registry. Legacy `parent_rappid` tracing is migration evidence only. | RAPP/1 §§6, 10, 13 |
| Find every operator on the network without an API | `python3 tools/sniff_network.py` (default --via raw) — BFS from `.well-known/rapp-network-seed.json` across each operator's beacon's `federation_hints[]`. Pure raw URLs; no Search API; no rate limit. Use `--via topic` for the secondary `gh search repos topic:rapp-estate` sweep. | CONSTITUTION Article XLVII; specs/SPEC.md §4.6 |
| Make my estate discoverable to other operators | `estate publish` — writes `estate.json` AND `.well-known/rapp-network.json` AND sets the `rapp-estate` topic on the repo. The next sniffer pass picks you up via raw + via topic. To opt out: `discovery.indexable: false` in your beacon (robots.txt-style; sniffers honor it). | CONSTITUTION Article XLVII.3; specs/SPEC.md §4.6 |
| I need to store PII / sensitive content | `estate init_private` (one call, idempotent) — creates `<your-handle>/rapp-estate-private` as a PRIVATE GitHub repo + mints the HMAC secret + scaffolds opaque file set. Re-run `estate publish` to refresh the beacon with `private_estate_pointer` + commitment. Per Article XLVIII this is MANDATORY for compliance. | CONSTITUTION Article XLVIII; pages/docs/PUBLIC_PRIVATE_BOUNDARY.md |
| Verify a peer hasn't substituted a different private estate behind my back | `estate verify_private` (operator-only) — recomputes the private state's commitment hash + compares to the published beacon. Drift = beacon stale or someone tampered. | CONSTITUTION Article XLVIII.2 (Bitcoin-commitment pattern) |
| Two-tier compliance audit across the network | `python3 tools/sniff_network.py` — surfaces each operator's `compliance` flag (xlviii / partial / legacy). Operators without `private_estate_pointer` show as `legacy` (pre-XLVIII; need to run init_private). | CONSTITUTION Article XLVIII; F15 |
| Author a consumer that needs a rappid | Implement/import the exact §6 grammar and preserve existing tails. Refuse invalid current input; never reissue it silently. Only a verified §6.3 re-anchor can mint a replacement. | pinned RAPP/1 §6 |
| Federate two organisms | §7 channel matrix, §8 message kinds, §3 trust scope | NEIGHBORHOOD_PROTOCOL §5, §6, §7, §9 |
| Touch the kernel (any file in §10) | **STOP** — write an agent/organ instead | MASTER_PLAN Part 1 §1; ANTIPATTERNS §2; CONSTITUTION Art. XXXIII |
| Touch install one-liner | **STOP** — URL is sacred (Art. V) | CONSTITUTION Art. V; SURVIVAL §"RAPP itself goes down" |
| Add a network call | §17 SURVIVAL pointer — local-first fallback REQUIRED | ANTIPATTERNS §5; SURVIVAL.md |
| Write a doc | §4 — does an existing doc own this concept?; §15 — am I using the right words? | LEXICON.md; ANTIPATTERNS §1 |
| Add an application `/api/*` view | Confirm it is UI/adapter-only. Any RAPP capability belongs in an agent behind exact §8 `/chat`; never add a sibling protocol endpoint. | RAPP/1 §8; CLAUDE organ guidance |
| Change protocol shape/version | Use Constitution Articles II–IV, total §12 migration, and signed §13 state; never bump locally | pinned RAPP/1 |
| About to add "skill"/"plugin"/"routine" terminology | **STOP** — §15 — it's an agent | ANTIPATTERNS §1 |
| About to add a legacy protocol flag/shim | **STOP** — implement the bounded §12 migration and retire the branch | RAPP/1 §12 |
| Brand fallback to "RAPP" / "AI assistant" | **STOP** — §10 sacred soul block | ANTIPATTERNS §4 |
| Probe a private repo | **STOP** — ASK Kody | MEMORY `feedback_private_repos.md` |
| Tell user to run a manual command | **STOP** — ship via install one-liner | MEMORY `feedback_oneliner_only.md` |
| Defer to "Phase 2" | **STOP** — execute now, no scope-windows | MEMORY `feedback_no_self_imposed_scope_or_breaks.md` |
| User-facing copy | §15 LEXICON (human vocab); §16 TRADEMARK | LEXICON.md; TRADEMARK.md |

---

## §12 — Antipatterns wall (verbatim from `ANTIPATTERNS.md`)

> Rules locked in because they were almost done wrong, or because the rest of the industry is doing them wrong and we'd be following them off the cliff. Each entry is *load-bearing* — breaking it is a regression.

### 1. ONE TERM FOR THE PLUGIN UNIT — `agent`

A single `*_agent.py` file is called an **agent**. Never a *skill*, *routine*, *loop*, *plugin*, *tool*, *function*, *capability*, *cassette*, or any other synonym.

**Why.** Anthropic's product surface introduced overlapping taxonomies (agents, skills, MCP, plugins, routines) that all describe the same thing. *"That basically poisoned the industry for onboarding."* Complexity becomes the gatekeeper — the AI winter precondition.

**Mom test.** *"It's an agent. A small Python file that gives the AI a new ability."* — that's the whole vocabulary.

**Pre-commit grep:** `grep -niE '\bskill|\bplugin|\broutine|\bloop|\bcassette' <changed-files>`

### 2. THE FROZEN KERNEL NEVER MOVES

`rapp_brainstem/brainstem.py`, `rapp_brainstem/VERSION`, and
`rapp_brainstem/agents/basic_agent.py` are frozen at the exact
`kody-w/rapp-installer@brainstem-v0.6.9` grail. They do not follow a moving
branch. Other agents are governed application files, not additional pinned
grail bytes.

When something feels like it requires a kernel change, write a new agent that solves it instead.

### 3. NO PERPETUAL LEGACY SHIMS

RAPP/1 §12 requires a total migration: freeze producers, ingest legacy inputs
once, canonicalize, emit current forms, publish signed re-genesis/registry
state, switch readers atomically, and remove old branches.

Do not invent a schema-version bump outside the constitutional process. A
bounded one-time migrator may recognize retired forms; normal readers may not
accept them forever.

### 4. NO SILENT FALLBACK TO "RAPP" / "AN AI ASSISTANT"

A planted organism's `soul.md` MUST include the spec-compliant `## Identity — read this every turn` block (per `rapp-twin-spec/1.0`). The block forbids the LLM from introducing itself as "RAPP", "an AI assistant", "your AI helper", "the brainstem", or any default platform branding.

The former `installer/plant.sh::write_soul_md` implementation is retired. Any
future producer must use current RAPP/1 identity and §13 trust rather than this
application block.

### 5. NETWORK CALLS WITHOUT A LOCAL-FIRST FALLBACK

Any GitHub fetch the front door makes goes through `cachedGhJson` / `cachedGhText`. Direct `fetch(github.com/...)` is forbidden in resume-rendering paths.

The hero use case is offline-first. An organism in airplane mode must keep rendering from cached state. Bare fetches go blank when the network drops; that's a regression against `HERO_USECASE.md` §1.

*ANTIPATTERNS.md is append-only. Antipatterns get added when we almost did them wrong; nothing here ever gets quietly removed.*

---

## §13 — Drift / known gaps

Spec ↔ code divergences. Append-only — entries get added when found, removed only by reconciliation (a PR that makes spec and code agree).

> **Historical closure log.** Dated `RESOLVED` rows below preserve what the
> repository claimed at that time. They are superseded for current identity,
> frame, wire, egg, registry, trust, and evolution guidance by the pinned
> RAPP/1 rev-5 authority and must not be used as current instructions.

Severity: **P0** wire-incompatible · **P1** schema/field mismatch · **P2** doc/naming drift · **P3** undocumented schema in code

| Drift | Spec says | Code does | Spec citation | Code citation | Sev | Resolution |
|---|---|---|---|---|---|---|
| ~~Two rappid schemas live at once~~ **RESOLVED 2026-05-08** | ECOSYSTEM §3 documents `rapp-rappid/1.1`; CONSTITUTION + bond.py emit `rapp-rappid/2.0` | All emitters now write `rapp-rappid/2.0` with v2-format strings (per CONSTITUTION Art. XXXIV.1 ratification). Pre-2026-04-30 seeds in the wild keep their UUID `rapp-rappid/1.1` (Art. XXXIV.5 — never regenerate); L2 test accepts both. | ECOSYSTEM §3 + CONSTITUTION Art. XXXIV.1 | installer/plant.sh, agents/twin_agent.py, installer/initialize-variant.sh, installer/test_plant.sh, tests/doorman/plant-from-egg.mjs | ~~P0~~ | Closed via commit (see git log) |
| ~~`rapp-twin-chat-response/1.0` undocumented~~ **RESOLVED 2026-05-08** | NEIGHBORHOOD_PROTOCOL §6 only documents `rapp-twin-chat/1.0` | Now formally documented in NEIGHBORHOOD_PROTOCOL §6e (Response envelope) — covers all 3 emit sites | NEIGHBORHOOD_PROTOCOL §6e | agents/twin_agent.py `_chat` | ~~P2~~ | Closed via doc addition |
| ~~Braintrust contribute receipt has its own schema~~ **RESOLVED 2026-05-08** | NEIGHBORHOOD_PROTOCOL §6a `rapp-twin-chat/1.0` is THE inter-org envelope | NEIGHBORHOOD_PROTOCOL §5b now legitimizes organ-local schemas for the operator's own loopback (cross-org writes still go through Issues with `neighborhood-message` label per §6e fallback) | NEIGHBORHOOD_PROTOCOL §5b "Organ-local HTTP shortcut" | utils/organs/neighborhood_membership_organ.py `_contribute` | ~~P1~~ | Closed via spec annotation |
| ~~`/api/contribute` REST endpoint vs spec~~ **RESOLVED 2026-05-08** | Spec assumes Issues/PRs/tether for cross-org writes | NEIGHBORHOOD_PROTOCOL §5b "Organ-local HTTP shortcut" annotation now documents the local-loopback pattern; peers still receive contributions as labeled Issues | NEIGHBORHOOD_PROTOCOL §5b | utils/organs/neighborhood_membership_organ.py contribute route | ~~P2~~ | Closed via spec annotation |
| ~~WebRTC tether on twin templates but not gate templates~~ **RESOLVED 2026-05-08 (by-design)** | NEIGHBORHOOD_PROTOCOL §5a tether is load-bearing for live agent-to-agent | Per spec, tether is for agent-to-agent (twin↔twin) live exchange. Gates are directories/welcome pages — not chat surfaces. Membership + discovery happen on the gate via §5b/§5c/§5d; live tether opens between two twins, not between a visitor and a gate. | NEIGHBORHOOD_PROTOCOL §5a + §1 | installer/plant.sh twin templates | ~~P1~~ | Closed — divergence is correct architecture, not drift |
| ~~Tier 1 `/chat` vs Tier 2 `/api/chat` path-prefix~~ **RESOLVED 2026-05-08 (documented)** | CLAUDE.md says HTTP surface is identical across tiers | Tier 2 actual route is `/api/businessinsightbot_function` (Azure Functions naming convention). Same envelope shape (`{user_input, conversation_history?}` in, `rapp-chat-response/1.0` out). Per CONSTITUTION Art. XV "Tier Parity Is a `/chat` Contract, Not a Transport" — the contract is the envelope, not the URL. | CONSTITUTION Art. XV; OSI.md §9 endpoint table | rapp_swarm/function_app.py:1103 | ~~P2~~ | Closed — different URL, identical contract |
| ~~Discord planting envelopes local to one agent~~ **RESOLVED 2026-05-08** | Discord is one path among many for §4 discovery; envelopes live only in code | NEIGHBORHOOD_PROTOCOL §4e ("Adapter-driven discovery — worked example: Discord") now formally documents both `rapp-discord-bridge/1.0` and `rapp-discord-plant-envelope/1.0` as the canonical adapter pattern | NEIGHBORHOOD_PROTOCOL §4e | agents/plant_discord_neighborhood_agent.py | ~~P3~~ | Closed via spec hoist |
| ~~Schemas without a defining spec doc~~ **RESOLVED 2026-05-08 (defined-by-emitter)** | Every schema in §5 should have a "Defined in" entry | Eight client-local schemas (`rapp-twin/1.0`, `rapp-binder/1.0`, `rapp-vbrainstem-subscription/1.0`, `rapp-zoo-collection/1.0`, `rapp-swarm/1.0`, `rapp-cloud-registry/1.0`, `rapp-brainstem-backup/1.0`, `rapp-twin-identity/1.0`) now have file:line references in §5 — they are "defined by their canonical emitter" (the JS/HTML file that round-trips them). `rapp-upgrade-agent/1.0` was incorrectly listed — it's a User-Agent header string, not a schema; removed from §5. | §5 of this doc | various .js / .html / .json | ~~P3~~ | Closed — defined-by-emitter is a legitimate pattern for client-local schemas |
| ~~`rapp-frame/1.0` defined but not yet emitted in trunk~~ **RESOLVED 2026-05-08** | ECOSYSTEM §15 lists doorman frame log as ❌ pending | All wired: `appendFrame()` in plant.sh:5447 (content-addressed sha256 chain); fires on chat turn / tool call / memory save → localStorage `rapp_frames_v1`. `buildAscendedEgg` packs `data/frames.json`. Dream Catcher reads it back (plant.sh:3485). 17/17 end-to-end tests pass via `tests/osi/L6a-frame-chain-browser.sh`. | ECOSYSTEM §3 + §15; HERO_USECASE §2 | installer/plant.sh, tests/doorman/dreamcatcher.mjs | ~~P3~~ | Closed — promoted to ✅ in ECOSYSTEM §15 |
| ~~Braintrust agents not yet on twin-chat envelope~~ **RESOLVED 2026-05-08 (legitimized as organ-local pattern)** | NEIGHBORHOOD_PROTOCOL §6a is THE twin envelope; braintrust agents are twins federating | NEIGHBORHOOD_PROTOCOL §5b "Organ-local HTTP shortcut" annotation now legitimizes the pattern: organ-local writes for the operator's own brainstem are valid; cross-organism contribution still rides §5b Issues with the `neighborhood-message` label. Braintrust contribute uses both — local-loopback for fast operator UX + Issues for cross-org propagation. | NEIGHBORHOOD_PROTOCOL §5b | neighborhood_membership_organ.py contribute/contributions | ~~P1~~ | Closed — pattern validated |

---

## §14 — Historical external planted-state observation

This section is non-authoritative and may be divergent. External repositories,
moving branches, and live Pages URLs are not current claims, immutable pins, or
accepted RAPP/1 inputs.

> **External/application observation list.** These links and schema labels
> report ecosystem state and require generator/owner follow-up; they do not
> register RAPP structure, establish signatures, or replace the signed §13
> registry. Treat twin-chat, static API, sealed-channel, MCP, cart, and other
> profiles as adapters unless and until represented through current RAPP/1
> forms.

- **Ant Farm (autonomous swarm scale demo):** [`kody-w/ant-farm`](https://github.com/kody-w/ant-farm) — `kind: "ant-farm"` neighborhood; every participant runs their own brainstem (or just feeds [skill.md](https://raw.githubusercontent.com/kody-w/ant-farm/main/skill.md) to any AI); pheromones are `ant-pheromone`-labeled GitHub Issues; gate at <https://kody-w.github.io/ant-farm/>
- **Twin (historical application example):** `kody-w/heimdall` — external,
  unverified, and not advertised as a live front door
- **Neighborhood gate (private+public split):** [`kody-w/microsoft-se-team-neighborhood`](https://github.com/kody-w/microsoft-se-team-neighborhood) + companion `*-private`
- **Neighborhood gate (public, autonomous):** [`kody-w/public-art-collective`](https://github.com/kody-w/public-art-collective)
- **Templates:** [`kody-w/private-workspace-template`](https://github.com/kody-w/private-workspace-template), [`kody-w/braintrust-template`](https://github.com/kody-w/braintrust-template)
- **Catalogs:** [`kody-w/RAPP_Store`](https://github.com/kody-w/RAPP_Store), [`kody-w/RAPP_Sense_Store`](https://github.com/kody-w/RAPP_Sense_Store), [`kody-w/rapp-egg-hub`](https://github.com/kody-w/rapp-egg-hub)
- **Test peer:** [`kody-w/rapp-test-neighbor`](https://github.com/kody-w/rapp-test-neighbor) — legacy application fixture
- **Species root (this repo):** [`kody-w/RAPP`](https://github.com/kody-w/RAPP) — kernel + spec only; per SURVIVAL.md, neighborhood seeds do NOT live here
- **RAR (Pokédex / single-file agent registry):** [`kody-w/RAR`](https://github.com/kody-w/RAR)
- **Front-door application layer** (external guide:
  [`kody-w/rapp-neighborhood-protocol`](https://github.com/kody-w/rapp-neighborhood-protocol)):
  - **Front-door template:** [`kody-w/rapp-vneighborhood`](https://github.com/kody-w/rapp-vneighborhood) — a public repo *is* the front door (`rapp-vneighborhood/1.0`); interchangeable relay (local ≡ kited ≡ cloud); `v` = swarm-capable; egg/import/fork portability
  - **Example neighborhoods:** [`kody-w/vneighborhood-design-studio`](https://github.com/kody-w/vneighborhood-design-studio), [`kody-w/vneighborhood-research-lab`](https://github.com/kody-w/vneighborhood-research-lab)
- **Historical social-layer concept:** `kody-w/rapp-commons` and
  `rapp-god-forum`; no live link, cloud relay, or accepted event stream is
  advertised.
- **Historical resident:** former Azure relay concept; no operational endpoint
  is claimed.
- **RIONet (agent-built web):** [`kody-w/rionet`](https://github.com/kody-w/rionet) — rapp.robots.txt → rappbot → rappPageRank → RIO (`search:` / `rpage:`, markdown only)
- **The kited spec & codec:** [`kody-w/rapp-sealed`](https://github.com/kody-w/rapp-sealed) — the sealed channel: AES-256-GCM codec + conformance vectors (`rapp-sealed/1.0`) · [`kody-w/rapp-kited-twin`](https://github.com/kody-w/rapp-kited-twin) — kited-twin visual identity (a neutral kite)
- **Historical God's-eye observations:** `rapp-god`, `rapp-static-apis`, and
  `rapp-map` are external, divergent, and non-authoritative. They are not a
  §13 registry and must not be read from moving branches as canon.
- **Run a brainstem:** [`kody-w/vbrainstem`](https://github.com/kody-w/vbrainstem) — browser-native runtime (Pyodide, no install) · [`kody-w/rapp-brainstem-sdk`](https://github.com/kody-w/rapp-brainstem-sdk) — headless SDK serving the `brainstem.py` `/chat` contract
- **Operate & connect — the string + doorman:** [`kody-w/rapp-kite`](https://github.com/kody-w/rapp-kite) — the string (fly/operate kited twins) · [`kody-w/rapp-doorman`](https://github.com/kody-w/rapp-doorman) — the sealed-door skill · [`kody-w/rapp-claude-skills`](https://github.com/kody-w/rapp-claude-skills) — Claude Code skills for the RAPP pattern
- **MCP — application adapter:** [`kody-w/rapp-mcp`](https://github.com/kody-w/rapp-mcp) may bridge host tools, but its RAPP boundary must map to the exact §8 `/chat` contract; its own profiles do not expand the wire.
- **RACon — cartridges & console:** [`kody-w/racon`](https://github.com/kody-w/racon) — the experience grail `racon/1.0` · [`kody-w/rapp-carts`](https://github.com/kody-w/rapp-carts) — the cartridge spec `rapp-cart/1.0` · [`kody-w/cowork-cookbook-rapp`](https://github.com/kody-w/cowork-cookbook-rapp) — the first RACon cartridge · [`kody-w/rio`](https://github.com/kody-w/rio) — RIO, the browser (OSI L7) · [`kody-w/ai-agent-templates-mirror`](https://github.com/kody-w/ai-agent-templates-mirror) — one-click MCS/Copilot Studio deploy mirror
- **Demos & prototyping:** [`kody-w/rapp-demos`](https://github.com/kody-w/rapp-demos) — synced scan-to-watch demos (host drives, watchers see live, sealed)
- **Registry & agents:** [`kody-w/rapp-agents`](https://github.com/kody-w/rapp-agents) — drop-in single-file agents · [`kody-w/aibast-agents-library`](https://github.com/kody-w/aibast-agents-library) — industry-vertical templates · [`kody-w/rapp-zoo`](https://github.com/kody-w/rapp-zoo) — local-first twin-estate keeper
- **Platform & clients:** [`kody-w/RAPP_Desktop`](https://github.com/kody-w/RAPP_Desktop) — native desktop app · [`kody-w/rapp-vscode-extension`](https://github.com/kody-w/rapp-vscode-extension) — VS Code extension · [`kody-w/rapp-installer`](https://github.com/kody-w/rapp-installer) — the `curl | bash` installer front-door
- **Memory & social:** [`kody-w/CommunityRAPP`](https://github.com/kody-w/CommunityRAPP) — RAPP Hippocampus (persistent memory, local-first → Azure) · [`kody-w/rappterbook`](https://github.com/kody-w/rappterbook) · [`kody-w/rappterbook-commons`](https://github.com/kody-w/rappterbook-commons) — social network for AI agents (rebuilt on the signed commons)
- **More neighborhood examples:** [`kody-w/neighborhood-example`](https://github.com/kody-w/neighborhood-example) · [`kody-w/RAPP-Network`](https://github.com/kody-w/RAPP-Network) — public neighborhood instances
- **Metropolis tracker:** retired historical application surface; no live CTA

---

## §15 — Lexicon condensed

Pick ONE vocabulary per doc and stay consistent (LEXICON.md). Customer-facing → human terms. Spec / code / legal → developer terms.

| Concept | Human term | Developer term |
|---|---|---|
| AI's whole presence across substrates | **Estate** | swarm estate |
| AI's identity / public ID | **soul** / **soul-key** | **rappid** |
| 24-word recovery phrase | the words / the card | holocard incantation |
| Kernel-side HTTP extensions | **organs** | **organs** (no rename) |
| Recognition of another AI as related | **blessing** | kin-vouch |
| AI long-term plan | The Will | Foundation Continuity Plan |
| Cryptographic release commitments | The Promise | release-triggers |
| Master keypair | soul-key | master keypair (M) |
| One device's signing keypair | voice | device key (D) |
| Signs new voices | steward | self-signing key (S) |
| Vouches for kin AIs | herald | user-signing key (U) |
| Species root / first AI | origin | species root / prototype / godfather (informal) |
| 3-of-5 keypair split | the stewardship | Shamir 3-of-5 distribution |
| Forked code variant | fork / child species | kernel-variant |
| Birthing a new AI | **mitosis** (no rename) | **mitosis** |
| Merge engine for divergent state | **dreamcatcher** (no rename) | **dreamcatcher** |
| Lineage to origin | **species tree** (no rename) | **species tree** |
| Local AI server | **brainstem** (no rename) | **brainstem** |
| Kernel | **kernel** (no rename) | **kernel** |
| Graduated rapplication | **rapplication** (brand equity) | **rapplication** |

**Forbidden synonyms (ANTIPATTERNS §1):** never *skill*, *routine*, *loop*, *plugin*, *tool*, *function*, *capability*, *cassette* — always **agent**.

---

## §16 — Trademark scope (TRADEMARK.md)

| Mark | What it identifies |
|---|---|
| **RAPP** | The platform (https://github.com/kody-w/RAPP) |
| **rappid** | Lineage-identity protocol (CONSTITUTION Art. XXXIV) |
| **hatchling** | Lifecycle CLI |
| **vBrainstem** | Browser-side simulator |
| **rapplication** | Single-file rapp pattern |
| **rapp_kernel** | Species DNA archive |
| **brainstem** (in conjunction with above) | Local-first AI agent server pattern |

Common-law trademark (not USPTO-registered). **Permitted without permission:** refer-by-name, link, quote per CC BY-NC 4.0, identify a fork as "based on RAPP" with a distinct name, nominative fair use. **Requires permission:** naming a product/service/domain after a mark, operating a managed service branded as RAPP, selling software named after marks, suggesting endorsement, registering marks elsewhere.

---

## §17 — Survival contract pointer (top rows from SURVIVAL.md)

| Failure scenario | What survives | Verified by |
|---|---|---|
| One neighborhood repo deleted | Cached subscribers (read-only) — `~/.brainstem/neighborhoods/<slug>/` | tests/scenarios/15-offline-snapshot-dream-catcher.sh |
| `kody-w/RAPP` repo deleted | Already-installed brainstems; all planted neighborhoods (own repos); install one-liner needs mirror | tests/scenarios/17-survival.sh |
| GitHub Pages down | Everything except gate UIs (agents via `raw.githubusercontent.com`) | manual |
| `raw.githubusercontent.com` down | Cached state via `cachedGhJson` (📡 stale pill) | `cachedGhJson` test in tests/run-tests.mjs |
| GitHub entirely offline | Historical WebRTC/cache claim; no current survival guarantee | retired scenario evidence |
| Operator's brainstem dies | Recovery requires a valid §9 egg plus verified §§6/10/13 identity continuity; current blockers remain in `RAPP1_STATUS.md` | tests are product evidence only |
| Internet entirely down | Local-only neighborhoods; cached state; Dream Catcher reconciles when back | tests/scenarios/01 + 15 |

**The redundancy stack:** brainstem process memory → `~/.brainstem/neighborhoods/<slug>/` → git clone → exportable egg → GitHub canonical. Failure has to take out all five.

**The "what if RAPP itself goes offline" answer:** existing brainstems keep running; every neighborhood is its own repo; install one-liner can be re-served from any mirror (Constitution Art. V keeps the URL stable). See SURVIVAL.md "RAPP itself goes down" section.

---

## §18 — Updating this map

- **Append-only.** Never repurpose a row; bump version on the row instead.
- **Application document metadata:** `rapp-ecosystem-map/1.0`; changes here do
  not version or register the RAPP protocol.
- **Derivative.** If this map disagrees with `RAPP1_AUTHORITY.json`,
  `RAPP1_STATUS.md`, or Constitution Article LV, this map is wrong—fix it.
- **§13 drift is the only mutable section** — entries get added when found, removed when reconciled (PR closes a row by making spec and code agree).
- **Add a row to §11 the first time you see Claude (or yourself) drift on a given trigger.** The map's job is to catch the next miss.

*Map first published 2026-05-08. Maintained at repo root as a peer of `MASTER_PLAN.md`.*

<!-- RAPP1-HISTORICAL-SECTION-END -->
