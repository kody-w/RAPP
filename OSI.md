# Historical RAPP OSI Teaching Model

> **Current RAPP/1 authority (rev-5).** For canonicalization, identity, frames,
> wire, eggs, registry, trust, and protocol evolution, follow
> [`RAPP1_AUTHORITY.json`](./RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](./RAPP1_STATUS.md). RAPP/1's five normative layers
> supersede incompatible schemas in this older seven-layer teaching model.

> **Whole-document disposition:** the implementations, live catalogs,
> browsers, WebRTC carrier, cloud tiers, installers, and test claims below are
> dated architecture history. They do not describe shipped current surfaces.
> Use only the five normative layers and exact contracts in RAPP/1 rev-5.

<!-- RAPP1-HISTORICAL-SECTION-START -->

> A planted RAPP organism is a stack. Each layer abstracts the one below it. The agent at the top doesn't know whether the bytes it reads came from a local file or a peer's GitHub Pages — same way a browser doesn't know if its TCP segments rode Ethernet, Wi-Fi, or LTE. **This document maps the OSI model onto RAPP's primitives so every layer has a defining schema, an implementation, and a test.**
>
> `rapp-osi/1.0` is application documentation metadata, not a protocol
> schema. Read this as a product-layer analogy; RAPP/1 §§4–13 define the
> actual contracts.

## Why this exists

The OSI framing makes one thing precise that the prose specs leave implicit: **what each layer is responsible for, and what it can assume about the layers above and below it.** Without this discipline, code drifts — schemas that should live at L6 leak into L7 application logic; trust scope checks that belong at L5 get skipped at the application level. The OSI map is a lint check on architecture. Every test suite (`tests/osi/L<n>-*.sh`) verifies one layer in isolation.

The model is **fractal** as an application-design aid. Application metadata
such as agent or neighborhood declarations may vary, but protocol frames,
wire, eggs, trust, and registry do not acquire scale-specific alternatives.

---

## L1 — Substrate (the physical layer)

**Purpose.** The bytes have to live somewhere. L1 is the substrate that stores and transports them.

**RAPP analogue.** GitHub (repos + Pages + Issues + PRs API), `raw.githubusercontent.com` (content channel), the public PeerJS broker (signaling for L4a tether), the local filesystem (`~/.brainstem/`, `.brainstem_data/`), and Cloudflare Workers (auth proxy in `worker/`).

**Schemas.** None — this layer is "the medium." Schemas start at L2.

**Implementation.**
- GitHub Pages: every planted seed at `<owner>.github.io/<repo>/`
- raw fetch: `raw.githubusercontent.com/<owner>/<repo>/<sha>/<path>`
- PeerJS: `unpkg.com/peerjs@1.5.4` + the public broker at `peerjs.com`
- Local FS: `~/.brainstem/`, `.brainstem_data/memory.json`, `~/.rapp/twins/`
- Cloudflare auth worker: `worker/worker.js`

**Tests.** `tests/osi/L1-substrate.sh` — verifies (a) local FS is writable; (b) GitHub Pages serves `https://kody-w.github.io/RAPP/` with a 200; (c) `raw.githubusercontent.com` reachable; (d) PeerJS broker reachable. With `--offline`, every L1 check that touches the network must fall back to cached state without erroring.

**What L1 does NOT do.** No identity, no schemas, no trust. Just "can these bytes get from here to there?"

---

## L2 — Identity (the rappid layer)

**Purpose.** Address an organism uniquely while preserving identity across
lawful moves and key succession.

**RAPP analogue.** The exact RAPP/1 §6 form
`rappid:@owner/slug:<64-lowercase-hex>`. Its tail is minted once with
`Hb("rapp/1:rappid", uuid4_octets)` or the keyed SPKI-DER form; it is never
derived from owner/slug.

**Current contract.** A rappid is a grammar, not a `rapp/1` birth-certificate
schema. Bare UUID and versioned rappid records are legacy §12 migration inputs.
Canonicalization preserves the tail; only a verifiable §6.3 re-anchor can mint
a replacement in an enumerated case.

**Implementation.**
- `rapp_brainstem/utils/bond.py` — mints + serializes
- `rapp_brainstem/utils/rappid.py` — schema R/W
- `rappid.json` at the root of every planted seed
- `~/.brainstem/rappid.json` for the operator's own brainstem
- `~/.brainstem/bonds.json` — append-only lineage log

**Existing implementation tests.** `tests/osi/L2-identity.sh` exercises the
legacy runtime. Passing it does not establish RAPP/1 §6/§13 conformance; see
`RAPP1_STATUS.md` for the remaining owner-authorized identity work.

**What L2 does NOT do.** No discovery (that's L3). No trust decisions (that's L5). The identity is just the address — what you do with it is upper-layer business.

---

## L3 — Discovery (the lineage + catalog layer)

**Purpose.** Given a rappid, find the organism. Given an organism, walk the family tree. Discovery is the routing layer — it answers "who exists, and how do I reach them?"

**Legacy application analogue.** Four discovery channels from
NEIGHBORHOOD_PROTOCOL §4:
- 4a — Product-lineage walk (`parent_rappid` backward, GitHub forks API forward)
- 4b — Public catalog (`kody-w/rapp-egg-hub/index.json`)
- 4c — Direct invitation (URL or QR shared out-of-band)
- 4d — Canonical test neighbor (`kody-w/rapp-test-neighbor`)

These are application discovery adapters. Current authoritative resolution of
anchors, keys, kinds, errors, and re-genesis comes from the signed, monotonic
RAPP/1 §13 registry rooted in an out-of-band estate-owner rappid.

**Schemas.**
- legacy/application `parent_rappid` lineage metadata (not a RAPP/1 frame field)
- `rapp-metropolis-index/1.0` (federated tracker)
- `rapp-metropolis-entry/1.0` (one neighborhood entry)
- `rapp-egg-hub-entry/1.0` (egg catalog)
- `rapp-rappid-estate-view/1.0` (estate-by-identity lookup, the global passport)

**Implementation.**
- `pages/metropolis/index.json` + `index.html` — the live tracker
- `pages/metropolis/README.md` — protocol + federation rules
- `rapp_brainstem/utils/organs/neighborhood_membership_organ.py::_estate_view` + `by-rappid` route
- `rapp_brainstem/utils/peer_registry.py` — local peer cache
- GitHub forks API + Contents API (cached via `cachedGhJson`)

**Existing tests.** `tests/osi/L3-discovery.sh` validates legacy application
discovery. It does not prove §13 resolution, freshness, key succession, or
authenticated acceptance.

**What L3 does NOT do.** No content delivery (that's L4). No trust enforcement on what the discovered organism exposes (that's L5).

---

## L4 — Channels (the transport layer)

**Purpose.** Move bytes between two organisms. Different channels have different latency, durability, and consent properties — pick the right one for the message.

**Application adapters.** Four historical channel types from
NEIGHBORHOOD_PROTOCOL §5:

| Channel | Latency | Durability | Transport property (not RAPP trust) |
|---|---|---|---|
| **4a — WebRTC tether** | live | ephemeral | DTLS encrypted, broker drops out after handshake |
| **4b — GitHub Issues** | minutes-hours | durable | label-routed (`private-memory`, `egg-submission`, `dream-catcher`, `agent-proposal`, `neighborhood-message`) |
| **4c — Pull Requests** | minutes-hours | durable + canonical | asymmetric — only operator can merge into trunk |
| **4d — raw fetch** | network-dependent | cached for offline | content-addressed via `raw.githubusercontent.com/<owner>/<repo>/<sha>/<path>` |

At the protocol boundary every adapter must carry one of exactly two RAPP/1 §8
forms: the exact synchronous `/chat` exchange or an asynchronous verified §7
frame. `rapp-tether/1.0` is application-local history, not a third wire.

**Implementation.**
- 4a tether: `installer/plant.sh` and the contained legacy
  `pages/vbrainstem.html` surface implement historical transport behavior; they
  do not establish the current wire or trust contract.
- 4b Issues: `cachedGhJson('/repos/.../issues?labels=...')`
- 4c PRs: `gh pr create` from `learn_new_agent.py` and the front door's "Propose an agent" pane
- 4d raw fetch: `cachedGhJson` / `cachedGhText` wrappers — REQUIRED per ANTIPATTERNS §5

**Tests.** `tests/osi/L4-channels.sh` — verifies (a) PeerJS broker reachable for 4a handshake (browser test stubbed; can't open data channel from shell); (b) GitHub Issues API returns labeled issues correctly; (c) raw fetch through `cachedGhJson` returns cache on network failure (offline mode); (d) `rapp-tether/1.0` envelope shape from doorman frame log.

**What L4 does NOT do.** No content interpretation (that's L6 envelope + L7 application). No facet enforcement (that's L5).

---

## L5 — Authorization and protocol trust

**Purpose.** Separate application authorization ("who may see this view") from
protocol authentication ("who signed this artifact under current keys").

**RAPP analogue.** Trust scopes from NEIGHBORHOOD_PROTOCOL §2:

| Scope | Boundary | Persistence |
|---|---|---|
| **Personal** | one device, one visitor | localStorage |
| **Neighborhood** | repo collaborators (push access) | GitHub Issues + private repo files |
| **Public swarm** | anyone | committed to the seed repo |

These scopes and `public_facets` are application policy. They do not
authenticate a RAPP frame, egg, invite, or registry record.

**Current RAPP trust.** Apply §10 JWS verification and resolve `kid`, key
succession, revocation, registered kinds/errors, and re-genesis through the
signed monotonic §13 registry. GitHub collaborator status, repository push
permission, transport encryption, and an unsigned local roster are not
protocol trust anchors.

**Schemas.**
- `rapp-public-facets/1.0` — granular facet declaration (NEIGHBORHOOD_PROTOCOL §7)
- `rapp-neighborhood-members/1.0` — roster (collaborator-status check)
- `rapp-twin-spec/1.0` — soul Identity block (per-organism identity assertion)

**Implementation.**
- `rapp_brainstem/utils/organs/neighborhood_membership_organ.py::_verify_membership` — role check via Contents API (`members.json`) + GitHub collaborators API
- `card.json` (operator-set) — `public_facets` array
- Doorman system prompt assembly — three memory tiers (device-local, public, per-user) merged with `[@<login>] <fact>` prefix to telegraph access boundary
- ANTIPATTERNS §4 — soul.md MUST include the Identity block

**Tests.** `tests/osi/L5-trust-scope.sh` — verifies (a) `rapp-public-facets/1.0` schema validates; (b) facet declared with `scope: neighborhood` blocks public-only callers; (c) collaborator check correctly classifies operator vs visitor; (d) per-user issue memories are filtered by `@<login>`.

**What L5 does NOT do.** It does not let an application ACL bypass §7, §9,
§10, or §13 verification.

---

## L6 — Envelope (the presentation layer)

**Purpose.** Wrap payload in a structured envelope with provenance, integrity, and routing. Envelopes are content-addressed (SHA-256) where applicable.

**RAPP analogue.** The one RAPP/1 frame and one RAPP/1 egg manifest.

**Current contracts.**
- Frame: exactly the eleven RAPP/1 §7 keys, `spec:"rapp/1"`, registered kind
  and stream binding, particle/wave hashes, complete ordered verification.
- Egg: exactly the seven-member RAPP/1 §9 manifest,
  `schema:"rapp/1-egg"`, a ratified variant, deterministic storage, integrity
  then viability checks, and applicable signature verification.
- Historical `rapp-twin-chat/1.0`, `brainstem-egg/*`, `rapp-frame/*`, and local
  provenance/state/card envelopes are legacy or application metadata, not
  alternate current protocol envelopes.

**Implementation.**
- `rapp_brainstem/agents/twin_agent.py::_chat` — legacy adapter under migration
- `rapp_brainstem/utils/bond.py` — legacy egg implementation under migration
- `rapp_brainstem/utils/egg.py` — legacy egg utilities
- `pages/vbrainstem.html::exportCart` — contained legacy session export
- `rapp_brainstem/agents/egg_hatcher_agent.py` — legacy schema/type router, not
  current §9 variant dispatch
- `tests/doorman/dreamcatcher.mjs` — legacy frame-chain validation

**Existing tests.** The L6 and browser suites validate legacy implementation
behavior only. They must not be cited as RAPP/1 conformance; the complete
current checks are those in §§7.5 and 9.3.

**What L6 does NOT do.** No agent invocation (that's L7). No transport selection (that's L4).

---

## L7 — Application (the agent + /chat layer)

**Purpose.** Do the work. `agent` remains the repository term for capability.
At the protocol boundary, synchronous invocation uses the exact RAPP/1 §8
`/chat` contract.

**Host/application analogue.** Agents (single-file `*_agent.py`), the exact
RAPP `/chat` boundary, and application-only HTTP views under `/api/*`.

**Application metadata and exact wire.**
- `rapp-agent/1.0` — application-local host metadata, not a RAPP protocol schema
- Request: required `user_input`; optional `session_id` and
  `idempotency_key`; ignore unrecognized members
- HTTP 200: exactly `{response:string, agent_logs:[string], session_id:string}`
- HTTP 422 refusal: exactly `{error:{code:string, step:string|null}}`
- The historical `rapp-chat-response/1.0` wrapper and
  `conversation_history` request member are not current RAPP/1 wire forms
- `rapp-twin-spec/1.0` — soul Identity block
- `rapp-rar-index/1.0` — application discovery manifest. Its SHA-256 values
  provide integrity only; hot-loaders must also apply applicable §§10/13 trust
  before installation.
- `rapp-rar-loadout/1.0` — RarLoader install-result envelope

**Implementation.**
- `rapp_brainstem/brainstem.py` — Flask + `/chat` + provider dispatch (KERNEL — Art. XXXIII)
- `rapp_brainstem/agents/basic_agent.py` — `BasicAgent` base class (KERNEL)
- `rapp_brainstem/agents/*_agent.py` — every agent (auto-discovered, reloaded per request)
- `rapp_brainstem/utils/organs/*_organ.py` — HTTP extensions
- `rapp_brainstem/soul.md` — voice/twin protocol (sacred per CLAUDE.md §5)
- `rapp_swarm/function_app.py` — Tier 2 (Azure Functions) — same agent contract, prefixed routes

**Existing tests.** `tests/osi/L7-application.sh` verifies the legacy host and
application slots. It does not establish exact §8 conformance.

**What L7 does NOT do.** It does not add sibling capability routes or bypass
frame, signature, and registry checks through a historical twin-chat adapter.

---

## Cross-cutting concerns

These run *orthogonal* to the layer model — every layer must satisfy them.

### CC1 — Tier portability (CONSTITUTION Art. XV)

The same agent file runs unmodified on Tier 1 (Flask), Tier 2 (Azure Functions), and Tier 3 (Copilot Studio). Storage backends differ; the contract surface doesn't.

**Test.** `tests/osi/X1-tier-portability.sh` checks host portability. A path
prefix or different envelope may be an adapter behavior, but a conformant RAPP
boundary still exposes the exact §8 contract.

### CC2 — Survival (SURVIVAL.md)

Every layer must degrade gracefully. L1 down → L4d falls back to cached. L5 down → L7 surfaces "no permission" without crashing. Ten failure-mode rows enumerated in `SURVIVAL.md`.

**Test.** `tests/osi/X2-survival.sh` — simulate L1 outage (block network); confirm cached state still serves; confirm error messages are honest, not silently degraded.

### CC3 — RAPP/1 egg lifecycle

Current eggs roundtrip per RAPP/1 §9: exact manifest, registered variant,
domain-separated file and manifest addresses, deterministic container,
integrity then viability, and applicable §10/§13 signature verification. A
deep fetch from an origin repository is not authentication.

**Test.** `tests/osi/X3-egg-lifecycle.sh` — pack egg from a fresh seed, verify SHA, hatch into a new directory, confirm rappid + agents + soul preserved bit-for-bit.

### CC4 — Federation adapters

Two organisms may use the historical twin-chat adapters over several
transports, but each current protocol interaction must map to one exact §8
form.

**Existing test.** `tests/osi/X4-federation.sh` verifies legacy adapter
roundtrips and the host's application envelope; it is not proof of exact
RAPP/1 §8 conformance.

---

## The matrix view

|             | Agent | Twin | Neighborhood | Metropolis |
|---          |---    |---   |---           |---         |
| **L1 substrate**  | local FS | local FS + GitHub | + collaborator gate | + federated trackers |
| **L2 identity**   | inherited | own rappid | neighborhood_rappid | (per twin) |
| **L3 discovery**  | in metadata | lineage walk | gate URL + members.json | tracker index |
| **L4 channels**   | in-process | tether + Issues + PRs + raw | + collaborator-gated | + cross-tracker fetch |
| **L5 trust scope**| application ACL | + §10/§13 verification | + signed registry | + signed registry |
| **L6 envelope**   | host metadata | exact RAPP/1 §7 frame / §9 egg | same contracts | same contracts |
| **L7 application**| `perform()` | exact §8 `/chat` | agent behind §8 | agent behind §8 |

**Reading the matrix:** every cell has a defining schema and a test. If a cell is empty, that's a gap — track it in `ECOSYSTEM_MAP.md` §13 drift.

---

## How to use this document

- **Designing a new feature?** Identify which layer it belongs to. If you find yourself writing trust-scope logic at L7, that's a smell — push it down.
- **Debugging?** Walk the layers from L7 down. The error usually surfaces several layers below where it manifests.
- **Adding protocol structure?** Follow Constitution Articles II–IV and the
  signed §13 registry process; do not mint a schema token in this document.
- **Writing a test?** Match it to a layer file in `tests/osi/`. If the test doesn't fit one layer, it's probably a CC test (X1–X4) or it's actually two tests.

## How to run the tests

```bash
# All layers + cross-cutting concerns
bash tests/osi/run.sh

# A single layer
bash tests/osi/L1-substrate.sh
bash tests/osi/L6-envelope.sh

# Offline mode (skip network-dependent checks)
bash tests/osi/run.sh --offline
```

The runner prints a green/red matrix: rows are layers, columns are scales (agent / twin / neighborhood). Anything red is a regression against this contract.

## Cross-references

- [`ECOSYSTEM_MAP.md`](./ECOSYSTEM_MAP.md) — the product synthesis index. OSI
  layers are §2.5; neither document overrides RAPP/1.
- [`NEIGHBORHOOD_PROTOCOL.md`](./NEIGHBORHOOD_PROTOCOL.md) — historical and
  application adapter guidance; RAPP/1 §8 is the current wire
- [`ECOSYSTEM.md`](./ECOSYSTEM.md) — anatomy of one organism (L2 + L7)
- [`SURVIVAL.md`](./SURVIVAL.md) — degradation contract (CC2)
- [`HERO_USECASE.md`](./HERO_USECASE.md) — the four scenarios this stack exists to satisfy
- [`ANTIPATTERNS.md`](./ANTIPATTERNS.md) — locked rules per layer (notably: §1 ONE term for L7 unit; §2 frozen kernel = L7 base; §5 local-first L4d fallback)

---

*Application document metadata: `rapp-osi/1.0`. This label may track revisions
to the teaching model; it does not version or register RAPP protocol.*

<!-- RAPP1-HISTORICAL-SECTION-END -->
