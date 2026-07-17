# Historical RAPP Ecosystem Layout

> **Current RAPP/1 authority (rev-5).** For canonicalization, identity, frames,
> wire, eggs, registry, trust, and protocol evolution, follow
> [`RAPP1_AUTHORITY.json`](./RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](./RAPP1_STATUS.md). This architecture map is subordinate
> to that pin. Retired schema names below are migration inventory, never current
> emission or acceptance instructions.

> **Whole-document disposition:** the layout, lifecycle, surfaces, catalogs,
> tiers, eggs, and shipment ledgers below are dated product history. They are
> not current instructions or capability evidence. Current claims are limited
> to the pinned RAPP/1 authority and the unresolved status record above.

---

<!-- RAPP1-HISTORICAL-SECTION-START -->

## 0. The atom

A RAPP **organism** may inhabit a GitHub repository with this implementation's
file layout. The repository is a substrate, not the identity: RAPP/1 §6
`rappid` survives lawful moves, while §13 binds current anchors and keys.
Voice, memory, and agent source may live as committed application files.
Browser surfaces shown below are retired history.

```
github.com/<user>/<seed>     ← canonical lineage (the trunk)
       │
       └── served at <user>.github.io/<seed>/         ← the front door (public profile)
                                       /doorman/      ← chat surface (Copilot device-code auth)
```

The diagram records the former repository-centered product model. Planting,
hatching, browser chat, and Dream Catcher actions are retired; current RAPP/1
identity and acceptance do not arise from this layout.

---

## 1. Historical product lifecycle (retired)

```
  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
  │  PLANT   │ →  │  HATCH   │ →  │   LIVE   │ →  │  MUTATE  │ →  │ REASSIM. │
  └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
   one-liner       egg → device   accumulates       commits/PRs    Dream Catcher
   plant.sh        local bstem    memories,         add agents,    folds parallel
   on GitHub       or browser     conversations     edit soul,     dimensions back
                                                    save mem        via PR
                                       │
                                       ↓
                                  ┌──────────┐
                                  │  STASIS  │  no commits 3+ years
                                  └──────────┘  MMR floored, organism
                                                preserved as artifact
```

The diagram is preserved design history, not an available lifecycle.

The former re-hatching narrative is not a lawful RAPP/1 re-anchor. Any future
cross-substrate move must satisfy §§6, 9, 10, and 13 without identity
reminting; no such public workflow is currently shipped.

---

## 2. Historical planter output (inert)

The following tree records what retired `installer/plant.sh` attempted to
write. It is not a bootstrap, file checklist, or execution instruction:

```
<seed>/
├── rappid.json                     identity + lineage + kind
├── soul.md                         the AI's voice (spec-compliant Identity block)
├── README.md                       repo landing for GitHub visitors
├── card.json                       optional — operator override of trade-card copy
├── index.html                      the front door (public profile / MySpace)
├── .nojekyll                       so Pages serves dot-prefixed paths
├── .gitignore                      keep secrets out, keep public state in
├── .brainstem_data/
│   └── memory.json                 public memory — facts known to anyone
├── agents/
│   ├── basic_agent.py              base class, never overridden
│   ├── manage_memory_agent.py      doorman tier — save/recall public memories
│   └── context_memory_agent.py     doorman tier — track conversation context
├── doorman/
│   └── index.html                  chat surface (Copilot device-code, Pyodide)
├── installer/
│   └── install.sh                  one-liner kernel installer (visitor flow)
└── rapp_brainstem/
    ├── brainstem.py                frozen at rapp-installer@brainstem-v0.6.9
    ├── VERSION
    └── agents/basic_agent.py       reference copy
```

Files added by visitors over time:
- `agents/<custom>_agent.py` — new agents proposed via PR
- `data/frames.json` — frame log (when the doorman writes one)
- `.brainstem_data/memory.json` accumulates facts as conversations happen

Per-user private memories live in **GitHub Issues** on the seed repo (label `private-memory`). They are not files in the repo; the doorman reads/writes them via the Issues API for authenticated visitors.

---

## 3. Identity stack — everything traces back to the rappid

Current identity is the exact RAPP/1 §6
`rappid:@<lowercase-owner>/<slug>:<64-lowercase-hex>`. The tail is minted once
with the domain-separated §6.2 rule (UUIDv4 octets for keyless identity or
SPKI DER for keyed identity), never from a name. Presentation may be seeded
from the rappid, but presentation, repository location, and application
lineage do not define or authenticate it.

```
                         RAPP/1 §6 rappid
                                    │
       ┌──────────────┬─────────────┼─────────────┐
       ↓              ↓             ↓             ↓
  presentation   §7 stream_id   §10 key use   §13 current anchor
  (application)  (bound form)    (verified)    and succession
```

**Schemas** in this stack:

### Legacy application `rappid.json` record
The example below documents the pre-RAPP/1 product record for bounded
migration only. `rapp/1` is the current **frame** token, not an identity-record
schema. Bare UUID, `rapp-rappid/1.1`, `rappid:v2:…`, and non-64-hex tails are
not current identifiers: §6.3 canonicalization preserves an existing tail,
provisional identities are never emitted, and only an authorized re-anchor
can replace one.
```json
{
  "schema": "rapp/1",
  "rappid": "rappid:@<gh_user>/<repo>:<hash>",
  "kind": "personal" | "place" | "experiment" | "mirror",
  "name": "<repo-slug>",
  "display_name": "<Human Readable>",
  "github": "https://github.com/<user>/<repo>",
  "url":    "https://<user>.github.io/<repo>",
  "parent_rappid": "<uuid of parent organism>",
  "parent_repo":   "https://github.com/kody-w/rapp-installer",
  "planted_by":    "<gh-user>",
  "planted_at":    "<iso8601>",
  "kernel_version": "0.6.0",
  "location":      "<optional human-readable location>",
  "private_companion": {
    "repo":    "<github URL>",
    "purpose": "<why this exists>",
    "auth":    {"scheme": "github_token", "scope_required": "..."}
  }
}
```

### `card.json` (operator override, optional)
Customizes the trade-card copy. All fields optional; missing fields fall through to kind-defaults.
```json
{
  "title": "<one-line subtitle>",
  "type_line": "Front Door — <Whatever>",
  "rarity": "core" | "uncommon" | "rare" | "mythic",
  "abilities": [
    { "kw": "<Keyword>", "text": "<what this does>" }
  ],
  "flavor_text": "<the italicized one-liner>"
}
```

### Current frame (RAPP/1 §7)
Every current frame has exactly the eleven keys below. Producers compute the
domain-separated §7 particle/wave hashes and consumers perform the complete
§7.5 verification order.
```json
{
  "spec": "rapp/1",
  "kind": "<registered-kind>",
  "stream_id": "<RAPP/1 stream_id>",
  "seq": 0,
  "utc": "YYYY-MM-DDTHH:MM:SS.mmmZ",
  "payload": {},
  "payload_hash": "<64hex>",
  "frame_hash": "<64hex>",
  "prev": null,
  "prev_wave": null,
  "sig": null
}
```

### Current egg manifest (RAPP/1 §9)
RAPP/1 has one egg schema and six registered variants: `organism`,
`rapplication`, `session`, `invite`, `neighborhood`, and `estate`.
```json
{
  "schema": "rapp/1-egg",
  "variant": "<registered-variant>",
  "rappid": "<RAPP/1 §6.1 rappid>",
  "created_utc": "YYYY-MM-DDTHH:MM:SS.mmmZ",
  "contents": [],
  "payload": {},
  "sig": "<jws|null>"
}
```
`contents` and deterministic ZIP/JSON serialization follow §9.1; signed eggs
are verified against §13, and invite signatures are mandatory. The formerly
documented `brainstem-egg/2.2-organism` and `rapp-egg-provenance/1.0`
manifests are retired migration inputs.

### User memories (`rapp-user-memories/1.0`, ascended-tier only)
Per-user private memories captured from GitHub Issues.
```json
{
  "schema": "rapp-user-memories/1.0",
  "source_repo": "<owner>/<repo>",
  "exported_at": "<iso8601>",
  "facts": [
    { "login": "<gh-user>", "body": "<fact>",
      "issue_number": <n>, "issue_url": "<url>",
      "created_at": "<iso8601>" }
  ]
}
```

---

## 4. Historical browser surfaces (retired)

Every row in this section records the former browser design. No front door,
doorman, tether, egg, catalog, install, or browser-chat CTA is currently
shipped.

### 4a. Front door — `/index.html`
Former public application profile; retained source is not an authenticated
artifact or active product.

| Element | Purpose | Driven by |
|---|---|---|
| Hero (sigil + name + handle + place + blurb + CTA) | Identity moment | rappid (sigil) + display_name + kind (blurb defaults) |
| Hero stats chips | Signs of life | memory.json + age + frozen-kernel marker |
| **Track Record / What I bring to the table** | The resume | All sources below |
| ⌬ **MMR + tier** | Single global rating | Live formula — see §6 |
| **Agents** | What capabilities exist | `agents/` listing via Contents API (cached) |
| **Achievements** | Milestones earned | Derived from mem count + age + mut count |
| **Mutation log** | Live evolution feed | Last 5 commits via Commits API (cached) |
| **Lineage** | Application provenance (not RAPP identity/trust) | legacy parent metadata; verify current anchor via §13 |
| 🃏 Show my card | Trade card overlay | Auto-derived; tap to flip → QR back |
| 📱 Pair with another device | WebRTC tether | PeerJS broker → DTLS, QR auto-renders |
| 🌱 Propose an agent | The lineage-evolution path | Pre-fills GitHub create-file URL |
| 🥚 Export .egg | Legacy exporter under migration | Current target is the RAPP/1 §9 `organism` variant |
| 🔬 Verify an .egg | RAPP acceptance | complete §9.3 checks, then applicable §§10/13 signature verification |
| 🕸️ Dream Catcher | Parallel-dimension reassimilation | Diff two eggs, surface candidate frames |
| 🌐 Back up to Egg Hub | Retired catalog CTA | No submission path |
| 💻 Install kernel locally | Retired installer CTA | No command offered |
| Front-door details (collapsed) | Engineering trivia | Slug, rappid, kernel, lineage HTML |

### 4b. Doorman — `/doorman/index.html`
Former chat experiment. No browser authentication, inference, or agent loading
service is currently offered.

| Element | Purpose |
|---|---|
| Persona header (name + location + AT THE FRONT DOOR badge) | Identity context for the visitor |
| Chat log (markdown rendered) | Two-way conversation; assistant messages render with marked.js |
| Typing-dots loading bubble | Visible state while LLM thinks; labels itself "calling X…" during tool calls |
| Auth pane → Copilot device-code modal | First-visit sign-in; matches canonical brainstem modal exactly |
| Memory pane (Save a memory) | Manual override; visitor can write public OR per-user-private memory |
| Model selector | Pulls live Copilot catalog via `/api/copilot/models`, persists choice in localStorage |
| Chat actions row | Save memory · Clear chat · Export ascended .egg (operator only) · Sign out |
| 🥚 Export ascended .egg | Legacy tiered export; not a current §9 variant or trust claim |
| Private indicator badge | ✓ ascended — full twin voice loaded · or · public · or · device-only |
| Pyodide agent loader | Loads doorman + ascended agents from `kody-w/RAPP/main/rapp_brainstem/agents/` |

The doorman pages and the front-door pages are the **only** two surfaces an organism exposes by default. Both are static HTML rendered in the browser; there's no server-side code on the seed.

---

## 5. Memory — three concentric tiers

```
                ┌───────────────────────────────────────┐
                │      DEVICE LOCAL (localStorage)       │   This visitor on this device.
                │      Anonymous-friendly. No auth.       │   Survives reload, never leaves.
                └───────────────────────────────────────┘
                ┌───────────────────────────────────────┐
                │      PUBLIC (.brainstem_data/         │   Anyone who visits sees these.
                │           memory.json — git tracked)   │   Operator commits to grow.
                └───────────────────────────────────────┘
                ┌───────────────────────────────────────┐
                │      PER-USER PRIVATE (GitHub Issues)  │   Per-@login. Authed visitors only.
                │           label: private-memory        │   Surfaces as `[@login] <fact>`
                └───────────────────────────────────────┘
```

The doorman's system prompt assembles all three at chat time:
- Device-local memory: free-floating facts, no prefix
- Public memory: free-floating facts, no prefix
- Per-user private (visible only to that user): `[@<login>] <fact>` so the LLM understands the access boundary

---

## 6. MMR — single global rating, computed client-side from public signals

```
  base_mmr = 1000
           + memCount × 30          (each conversation deepens us)
           + sqrt(mutCount) × 250   (each operator commit shapes us)
           + customAgents × 350     (each new agent earned beyond defaults)
           + sqrt(ageDays) × 80     (lived time matters)
           + sqrt(forkCount) × 400  (offspring planted from this lineage)

  above_baseline = max(0, base_mmr - 1000)
  decayed         = above_baseline × activityFactor

  final_mmr      = 1000 + decayed + lineage_gift
```

| Activity | Multiplier | Trigger |
|---|---|---|
| ✓ Active | 1.00 | last commit ≤ 30 days |
| 〰 Slowing | 0.85 | 30–180 days |
| 💤 Dormant | 0.65 | 180 days–3 years |
| ❄ Stasis | 0.45 | 3+ years (floors at 1000 baseline) |

**Calibration**: the first 5 mutations OR 7 days, the organism is in placement and shows `📐 Calibrating · X% complete` instead of a tier — same idea as Dota 2's first 10 placement matches.

**Lineage gift**: `(parent_mmr - 1000) × 0.30` — the child inherits 30% of the parent's above-baseline as a head start. Sits OUTSIDE the activity multiplier so inherited cred doesn't wither under inactivity (your genes are your genes).

**Tier ladder** (Dota 2 medals — recognizable):
```
<1500   Herald
 1500   Guardian
 2000   Crusader
 2500   Archon
 3000   Legend
 3500   Ancient
 4500   Divine
 6000+  Immortal (animated rainbow text)
```

The formula is identical across all planted seeds, so its application-level
MMR needs no separate leaderboard registry. This does not replace the required
RAPP/1 §13 protocol registry.

---

## 7. Evolution — PR-driven, frozen kernel never moves

The immutable grail is
[`kody-w/rapp-installer@brainstem-v0.6.9`](https://github.com/kody-w/rapp-installer/tree/brainstem-v0.6.9).
Pinned `brainstem.py`, `agents/basic_agent.py`, and `VERSION` bytes are mirrored
without local edits. The pin does **not** track a moving latest release; a
change requires an explicit authority event. Capabilities grow through
drop-in RAPP agents outside those pinned bytes.

```
visitor finds useful pattern        →  packages as <name>_agent.py
                                                  │
                                                  ↓
                                       opens PR on the seed repo
                                                  │
                                       ┌──────────┴──────────┐
                                       ↓                     ↓
                              operator merges          visitor leaves PR
                              into main                 sitting on fork
                                       │                     │
                                       ↓                     ↓
                              global lineage           personal branch
                              moves forward            of this organism
                              (everyone sees           (only that visitor
                              new agent on next        sees the mutation)
                              page render)
```

The 🌱 Propose-an-agent pane drafts a `BasicAgent` skeleton, accepts the visitor's name + description + agent code, and opens GitHub's `/new/<branch>?filename=...&value=...` URL. GitHub auto-handles fork + branch + PR for non-collaborators. Operator reviews and decides.

---

## 8. Egg cartridges — portable organisms (and other portable units)

Current eggs follow the single RAPP/1 §9 manifest
(`schema:"rapp/1-egg"`) and its ratified variants. ZIP variants use the exact
deterministic container rules; JSON variants serialize the manifest
canonically. Consumers verify integrity, viability, and any signature before
hatching.

> **Historical migration inventory (2026-05-10).** The table records the
> retired pre-RAPP/1 family and the implementation state it had at the time.
> It is not an emission, acceptance, or canonical-hatcher table.
>
> | Schema | Kind | Container | Hatch destination | Status |
> |---|---|---|---|---|
> | legacy `brainstem-egg/2.2-organism` | `organism` | ZIP | `~/.rapp/twins/<rappid>/` | retired; migrate via §12 |
> | legacy `brainstem-egg/2.2-rapplication` | `rapplication` | ZIP | planted rapp under host | retired; migrate via §12 |
> | legacy `brainstem-egg/2.3-session` | `session` | JSON | contained browser surfaces | retired; migrate via §12 |
> | legacy `brainstem-egg/2.3-neighborhood` | `neighborhood` | ZIP | repo / local mirror | retired proposal |
> | legacy `brainstem-egg/2.3-estate` | `estate` | ZIP | substrate move | retired proposal |

### Historical doorman-tier layout
This legacy layout is retained to explain existing archives; current packers
must instead satisfy RAPP/1 §9's registered variant and exact manifest.
Layout:
```
<egg>.zip
├── manifest.json     (with provenance.state_at_seal block)
├── rappid.json
├── soul.md
├── card.json         (if present)
├── agents/
│   ├── __init__.py
│   ├── manage_memory_agent.py
│   └── context_memory_agent.py
└── data/
    └── memory.json
```

### Historical ascended-tier layout
Adds:
```
├── agents/
│   ├── learn_new_agent.py        ascended-tier
│   └── swarm_factory_agent.py    ascended-tier
├── private/
│   ├── soul.md                   from private companion
│   ├── README.md                 from private companion
│   └── .brainstem_data/memory.json
└── data/
    └── user_memories.json        all per-user issue memories
```

Legacy kernels used `brainstem-egg/2.2-organism` and a `tier` field. A current
consumer does not infer either: it dispatches the RAPP/1 §9 `variant` and
refuses malformed or unregistered inputs after any bounded §12 migration.

---

## 9. Integrity stack — non-GMO chain

The following four checks describe the **legacy envelope** retained for
migration diagnostics:

1. **Per-file SHA-256** in `provenance.file_hashes` — catches edits to any file
2. **Manifest hash** — `sha256(canonical-sorted file_hashes)` catches edits to the table itself
3. **Origin commit SHA** — pins the egg to a real commit on the public seed repo
4. **State-at-seal snapshot** — captures all state-derived signals (MMR, mutation count, fork count, recent commits) for offline rendering

The 🔬 Verify pane on the front door recomputes everything client-side. Three verdicts:
- ✓ **envelope intact** — internal hashes match
- ⚠ **partial** — missing or unexpected files
- ✗ **tampered** — at least one file edited offline

Plus 🌐 **legacy deep-verify against a live repo** re-fetches files and checks
the historical hashes. That proves content equality, not RAPP authentication.
Current trust comes from RAPP/1 §§10 and 13: verify JWS signatures against the
signed, monotonic registry and anchored key succession. A repository's push
permissions are not the protocol trust anchor.

---

## 10. Dream Catcher — parallel-dimension reassimilation

Pattern from `kody-w/rappterbook` (`engine/merge/merge_frame.py`). Each hatched
egg can be a parallel offline dimension. Current reassimilation must first
verify RAPP/1 §7 frames and use the §7.4 total order; the older implementation
is migration evidence only.

The 🕸️ pane on the front door:
1. Drop the **canonical** egg (left) and a **parallel-dimension** egg (right)
2. Frame-set diff by verified `frame_hash`:
   - **Shared frames** (in both): grey, already in canon
   - **Parallel-only frames**: highlighted green with 🌱
3. Lineage check: rappids must match (cross-species reassimilation isn't supported)
4. **Reassimilation action**: opens a pre-filled GitHub Issue listing every parallel-only frame as a candidate. Operator reviews on GitHub and cherry-picks what's worth bonding back.

**Current merge order (RAPP/1 §7.4):**
- ascending fixed-form `utc`, with ties broken by ascending `frame_hash`
- verify each stream's contiguous `seq`, `prev`, and applicable `prev_wave`
- preserve rejected or fork evidence diagnostically; never silently repair,
  reparent, or treat a legacy `(utc, frame_n)` pair as a current primary key

---

## 11. The network — three modes

```
              ┌────────────────────────────────┐
              │     MODE A: ONLINE              │
              │   GitHub APIs flowing           │   Live MMR, live agents,
              │   raw.githubusercontent.com     │   live mutation log,
              │   reachable                     │   deep-verify works
              └────────────────────────────────┘
                            ↓ network drops
              ┌────────────────────────────────┐
              │     MODE B: AIRPLANE            │
              │   GitHub unreachable            │   localStorage cache
              │   localStorage cache wins       │   (24h TTL) renders
              │                                 │   stale data with 📡 pill
              └────────────────────────────────┘
                            ↓ never had network
              ┌────────────────────────────────┐
              │     MODE C: HATCHED OFFLINE     │
              │   Legacy state_at_seal block is │   application snapshot
              │   available for migration       │   from the seal moment
              └────────────────────────────────┘
```

Every fetch the resume makes goes through `cachedGhJson` / `cachedGhText` wrappers:
- On success: cache to localStorage with timestamp
- On failure or no-network: return last-cached value with a `stale: true` flag, render with a 📡 pill

The legacy `state_at_seal` block is an application rendering fallback, not
RAPP identity, trust, or current egg structure. Current offline acceptance
still performs the complete §9 checks with locally available trusted §13
state.

**Application availability matrix (not a RAPP trust-anchor matrix):**

| Mode | Data source | Limitation |
|---|---|---|
| Online | `raw.githubusercontent.com/<owner>/<repo>/main/...` | Transport location alone does not authenticate RAPP data |
| Airplane | localStorage cache stamped with last-sync date | Availability cache only; verify current forms normally |
| Hatched offline | legacy `state_at_seal` + `provenance.file_hashes` | Migration evidence only, not RAPP/1 §9 |
| Offline-only | historical publisher signatures | Retired trust model; RAPP/1 §§10/13 govern |

---

## 12. Historical external integrations (inactive)

### GitHub Pages
Historically served application files. A Pages URL or moving branch is not an
authenticated source, installer, front door, or RAPP/1 acceptance path.

### raw.githubusercontent.com
An application content channel. Seed files are anonymously fetchable at
`raw.githubusercontent.com/<user>/<repo>/<branch>/<path>` for UI and migration
work, but location and availability do not authenticate them; RAPP acceptance
uses the pinned verification and registry rules.

### GitHub Copilot (via the auth worker)
The retired doorman experiment used these support endpoints. They are not a
shipped browser service or additional RAPP/1 wire capabilities:
- `POST <auth-worker>/api/auth/device` — start device flow
- `POST <auth-worker>/api/auth/device/poll` — poll for token
- `POST <auth-worker>/api/copilot/token` — exchange ghu_* for copilot session
- `POST <auth-worker>/api/copilot/chat` — chat completions
- `GET  <auth-worker>/api/copilot/models?endpoint=...` — model catalog

The auth worker (Cloudflare Worker, `worker/`) is a thin proxy — it doesn't store visitor tokens; it forwards the device-code dance and chat traffic.

### GitHub Contents/Commits/Issues APIs
The retired front door used these APIs:
- `/repos/<owner>/<repo>/contents/agents` — list agents
- `/repos/<owner>/<repo>/commits?per_page=N` — mutation log
- `/repos/<owner>/<repo>` — fork count, repo metadata
- `/repos/<owner>/<repo>/issues?labels=private-memory&creator=<login>` — per-user memory

All wrapped through `cachedGhJson` for local-first rendering.

### kody-w/rapp-egg-hub
Historical external catalog reference. No Egg Hub CTA, backup, submission, or
download is current, and external catalog data is non-authoritative here.

### MCP (Model Context Protocol) — kody-w/rapp-mcp
[`kody-w/rapp-mcp`](https://github.com/kody-w/rapp-mcp) is an application
adapter, not a new RAPP wire form. At the RAPP boundary it must map to the exact
§8 `POST /chat` request (`user_input`, optional `session_id` and
`idempotency_key`) and exact success/error responses. MCP tools, status calls,
bootstrap operations, catalogs, and historical `rapp-mcp-spec/1.0` /
`rapp-static-mcp/1.0` profiles remain adapter concerns and may not expand that
wire contract.

### PeerJS public broker
Historical WebRTC dependency for a retired browser tether; no pairing service
is currently offered.

### Historical CDN dependencies
- `cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js` — Pyodide for in-browser agent execution
- `cdn.jsdelivr.net/npm/marked/marked.min.js` — markdown rendering in chat
- `cdn.jsdelivr.net/npm/jszip@3.10.1` — egg pack/unpack
- `unpkg.com/peerjs@1.5.4` — WebRTC tether
- `api.qrserver.com/v1/create-qr-code` — QR rendering for pair + card-back

---

## 13. Historical component inventory from retired `installer/plant.sh`

| Path | Role | Generated by |
|---|---|---|
| `rappid.json` | identity + lineage | `write_rappid_json` |
| `soul.md` | the AI's voice (kind-aware default + Identity block) | `write_soul_md` |
| `README.md` | repo landing | `write_readme` |
| `index.html` | front door | template inline in `plant.sh`, populated by Python placeholder substitution |
| `doorman/index.html` | chat surface | `write_doorman_html` |
| `installer/install.sh` | one-liner kernel installer | `write_install_sh` |
| `.gitignore` / `.nojekyll` | Pages + git config | `write_gitignore`, `write_nojekyll` |
| `.brainstem_data/memory.json` | initial public memory file | `write_memory_json` |
| `agents/manage_memory_agent.py` | application agent — public memory R/W | fetched by `fetch_seed_agents`; not a pinned grail byte |
| `agents/context_memory_agent.py` | application agent — conversation context | fetched by `fetch_seed_agents`; not a pinned grail byte |
| `rapp_brainstem/brainstem.py` | immutable kernel | exact `rapp-installer@brainstem-v0.6.9` byte |
| `rapp_brainstem/VERSION` | immutable version pin | exact `rapp-installer@brainstem-v0.6.9` byte |
| `rapp_brainstem/agents/basic_agent.py` | immutable base class | exact `rapp-installer@brainstem-v0.6.9` byte |

Files added on demand:
- `card.json` — operator commits to override card copy
- `agents/<custom>_agent.py` — visitors propose via PR
- `data/frames.json` — when the doorman writes a frame log (deferred)

---

## 14. Historical surface inventory (all affordances retired)

### Front door (`/`)
- Hero: tap `💬 Talk to <Name>` → `/doorman/`
- 🃏 Show my card → overlay → tap card to flip → QR back → tap to flip back
- 📱 Pair with another device → broker handshake → QR auto-renders → other device scans → DTLS channel
- 🌱 Propose an agent → fill form → submits to GitHub create-file URL → PR auto-forks for non-collaborators
- 🥚 Export .egg → JSZip pack → download
- 🔬 Verify an .egg → perform all RAPP/1 §9.3 checks and required §§10/13
  signature resolution; repository deep-fetch is optional transport evidence,
  not trust
- 🕸️ Dream Catcher → drop two eggs → frame diff → reassimilation issue
- 🌐 Back up to Egg Hub → pre-filled GitHub Issue at `kody-w/rapp-egg-hub`
- 💻 Install kernel locally → copy curl command
- Front-door details (collapsed) → slug + rappid + kernel + lineage

### Doorman (`/doorman/`)
- Sign in with GitHub (device-code modal — not auto-popping the GitHub tab; visitor copies code, then opens GitHub)
- Chat (markdown rendered, typing dots, model selector)
- + Save a memory (public or private)
- 🥚 Export ascended .egg (operator-only)
- Clear chat
- Sign out

### What the visitor never has to do
- Open a terminal
- Read documentation
- Know what a brainstem is
- Know what a rappid is
- Understand the egg format

(See HERO_USECASE.md §3 — "Mom's Mixtape" — for the accessibility floor.)

---

## 15. Superseded 2026-05 shipment ledger

✅ **Application behavior observed today (not RAPP/1 conformance):**
- Plant flow (one-liner)
- Front door + Track Record + MMR
- Trade card (4D — rappid-locked + state-aware)
- Doorman with Copilot device-code auth
- Operator-fallback ascension
- Legacy tiered egg export with historical SHA/state metadata; §9 migration pending
- Legacy deep-verify UI; complete §9/§10/§13 acceptance pending
- Legacy Dream Catcher diff; migrate ordering and verification to §7.4/§7.5
- Local-first rendering (cachedGhJson)
- Propose-an-agent PR flow
- Egg Hub backup (issue-based)
- **Legacy doorman `appendFrame()` writing retired `rapp-frame/1.0` to
  localStorage.** This test evidence describes the contained browser surface;
  it is not RAPP/1 §7 conformance.

⚠ **Partial — works, can be tightened:**
- Egg send over the tether channel (today: manual paste via tether chat; should be one-tap stream)
- Local-LLM fallback in doorman (today: custom Copilot endpoints work; no offline-LLM path)
- Plant-time MMR snapshot for lineage gift (today: live-fetched at view time)

✅ **Recently shipped (2026-05-08):**
- **Lineage roll-up stats** (avg/median/min/max MMR across the lineage tree). Agent: `rapp_brainstem/agents/lineage_rollup_agent.py` (`LineageRollup` tool); test: `tests/features/F1-lineage-rollup.sh`.
- **Global leaderboard** (aggregate the species via fork-tree walking, Herald → Immortal tier ladder, 10-min cache). Agent: `rapp_brainstem/agents/species_leaderboard_agent.py` (`SpeciesLeaderboard` tool); test: `tests/features/F2-leaderboard.sh`.
- **Location-aware proximity swarm** (Pizza Place / Pokémon-Go layer). Pure-stdlib geohash + match-by-prefix; `kind: "place"` seeds get `location_geohash` written by plant.sh when `MIRROR_LOCATION_LAT` + `MIRROR_LOCATION_LNG` set. Agent: `rapp_brainstem/agents/proximity_discovery_agent.py` (`Proximity` tool); test: `tests/features/F3-proximity.sh`.
- **ed25519 publisher signatures** (offline-only verification chains per CONSTITUTION Art. XXXIV.7). Tool: `tools/sign_release.py` (keygen / sign / verify); manifest at `rapp_kernel/manifest.json` declares `signing.preferred_method = "ed25519"`. Test: `tests/features/F4-ed25519-sign.sh`.
- **Historical stasis recovery / resurrection ceremony.** Its retired
  `rapp-frame/1.0` output is migration input; a current implementation must
  emit a registered kind in the exact RAPP/1 §7 envelope.

❌ **Not yet built (defined for parity):**
- (none currently — the §15 backlog is empty as of 2026-05-08)

---

## 15.5 Historical multi-scale eggs and federation lifecycle

This section preserves the **historical pre-RAPP/1 implementation narrative**.
Its `brainstem-egg/2.2-organism` and `rapp-egg/2.0` scale dispatch are retired
migration inputs, not current schemas or hatch instructions. Current portable
scales are represented by the registered variants of RAPP/1 §9; consumers
dispatch `manifest.variant` only after the complete §9.3 checks.

| Scale | What it carries | Where it hatches | Status |
|---|---|---|---|
| `twin` | One twin's identity + soul + agents + memories | `~/.rapp/twins/<hash>/` | historical claim; retired |
| `brainstem` | A whole brainstem distro (kernel + agents + organs) | target brainstem folder | historical claim; retired |
| `neighborhood` | N federated twins + roster + member memories | `~/.rapp/twins/<hash>/` per member + `~/.rapp/neighborhoods/<hash>/` for the roster | historical legacy implementation; retired `brainstem-egg/2.3-neighborhood` proposal |
| `swarm` / `factory` / `industry` | Container scales above neighborhood | `~/.rapp/<scale>s/<hash>/` as best-effort scaffolding | partial — scale-specific handlers TBD |
| `estate` | Whole operator identity: catalog + every nested twin / neighborhood cartridge + memories | recursive dispatch, restores `~/.brainstem/estate.json` | planned ([[ESTATE_SPEC]] §7.6) |

### The four-twin AIBAST federation, in one file

The historical design described `aibast-federation.egg` as a 19,903-byte
cartridge. It is not a current shipment or accepted RAPP/1 egg. Its former
contents were:

- 🌈 **Heimdall** on port 7081 (`personal` rappid)
- 🧬 **@kody-w** on port 7082 (`operator` rappid)
- 🏭 **Bots in Blazers** on port 7083 (`project` rappid)
- ⚡ **AIBAST** on port 7084 (`project` rappid)

The claimed hatch, memory transfer, AirDrop, and four-twin reproduction are
retired narrative, not current behavior.

### Why the scale matters for the lifecycle

The retired PLANT → HATCH → LIVE → MUTATE → REASSIM. model was framed for a
single organism. The following bullets preserve that historical extension:

- **Twin scale** — the lifecycle as written.
- **Neighborhood scale** — the federation lifecycle. PLANT is collective (one cartridge plants N members); HATCH is one motion; LIVE is the four-channel grid in [[The Swarm Estate]]; MUTATE happens per-member but cross-twin handoff is a first-class chat verb (Fleet's `mesh_chat` action fans a single prompt across every twin on every peer); REASSIM. uses the same Dream Catcher pattern per member.
- **Estate scale** — the substrate lifecycle. Re-anchoring is the move; no re-cross-signing is required because rappids stay intact across substrates.

Cross-references: [[The Federated Twin Egg Hatcher Pattern]] for the kernel-side hatcher and the four-twin worked example; [[ESTATE_SPEC]] §7.5–§7.6 for the formal neighborhood-scale and estate-scale schemas; [[NEIGHBORHOOD_PROTOCOL]] §5e for the on-the-wire neighborhood cartridge layout.

---

## 16. Reading order for new contributors

1. [`RAPP1_AUTHORITY.json`](./RAPP1_AUTHORITY.json) — exact structural pin
2. [`RAPP1_STATUS.md`](./RAPP1_STATUS.md) — current limits and owner blockers
3. [`CLAUDE.md`](./CLAUDE.md) — current target instructions
4. This mixed-current map — RAPP/1 crosswalk plus historical product inventory
5. [`HERO_USECASE.md`](./HERO_USECASE.md) and [`pages/vault/`](./pages/vault/) — preserved history

Only the authority/status pair governs current RAPP/1 claims.

<!-- RAPP1-HISTORICAL-SECTION-END -->
