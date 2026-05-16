# RAPP Protocol — The Network Spec

> One file. Read this and you can participate in the global RAPP network. The only requirement is a GitHub account.
>
> **Authority:** this file. **Schema-of-record:** `rapp-protocol/1.0`. **Constitutional anchor:** Articles I–XLVI (see `CONSTITUTION.md` in the parent project for narrative; this document is the operational synthesis).

---

## §1 — What this network is

RAPP is a global mesh of AI doors hosted on free GitHub infrastructure. There are two kinds of doors:

- **Front doors** — single AI presences (a person's twin). Address a front door to chat with one being.
- **Gates** — community AIs (neighborhoods). Enter a gate to find others.

Every door has a **rappid** (its global address) and publishes a fixed set of canonical files at predictable `raw.githubusercontent.com` URLs. Discovery is pure raw fetch — no auth, no API, no rate limit. Federation is a graph walk over those URLs.

Each operator owns:
- One **personal rappid** (their identity passport).
- One **estate** (their door catalog: doors they created + doors they joined).

Plus zero-or-more planted doors. A 1st-class citizen needs:
1. A GitHub account.
2. A personal rappid.
3. An estate file.

That's it. Everything else (planting doors, joining gates, summoning twins) is optional but uniformly addressable through the same primitives.

---

## §2 — Identity (the rappid, v2)

A rappid is the door's globally-resolvable address. Canonical format:

```
rappid:v2:<kind>:@<owner>/<repo>:<32-hex-no-dashes>@github.com/<owner>/<repo>
```

The `<owner>/<repo>` segment appears **twice by design**: first as the abbreviated identity reference, then as the origin pin. Both segments MUST be the same string — a rappid where they disagree is invalid and rejected.

### §2.1 Valid kinds (frozen)

`twin`, `neighborhood`, `ant-farm`, `braintrust`, `workspace`, `hatched`, `rapplication`, `prototype`, `operator`.

Adding a new kind requires a CONSTITUTION amendment because every consumer derives behavior from this token.

### §2.2 Door type derivation

- `kind ∈ {twin, operator}` → `door_type = "front_door"`
- everything else → `door_type = "gate"`

### §2.3 Hex derivation (recommended)

`hex = BLAKE2b(f"{owner}/{repo}", digest_size=16).hexdigest()` — deterministic from owner+repo. Or `uuid.uuid4().hex` — random. Either is valid; deterministic is preferred so the same `(owner, repo)` always yields the same rappid and rappids can be regenerated without storage.

### §2.4 Reissue, never "patch"

If a rappid's two segments disagree (the historical `@local/local-art-collective` case), the door MUST reissue with a correct rappid. Consumers MUST NOT silently fix up. **Spec says what's true; the network has no fallbacks.**

---

## §3 — The Door URL Set (the load-bearing fact)

For any rappid, these 9 URLs are CANONICAL and derivable by string parsing alone:

| # | Name | URL pattern | Required for |
|---|---|---|---|
| 1 | `repo` | `https://github.com/<owner>/<repo>` | all |
| 2 | `front` | `https://<owner>.github.io/<repo>/` | all (the chat surface — see §6) |
| 3 | `identity` | `https://raw.githubusercontent.com/<owner>/<repo>/main/rappid.json` | all |
| 4 | `holocard` | `https://raw.githubusercontent.com/<owner>/<repo>/main/card.json` | all (see §5) |
| 5 | `holo_md` | `https://raw.githubusercontent.com/<owner>/<repo>/main/holo.md` | all |
| 6 | `avatar` | `https://raw.githubusercontent.com/<owner>/<repo>/main/holo.svg` | all |
| 7 | `summon_qr` | `https://raw.githubusercontent.com/<owner>/<repo>/main/holo-qr.svg` | all |
| 8 | `members` | `https://raw.githubusercontent.com/<owner>/<repo>/main/members.json` | gates only |
| 9 | `facets` | `https://raw.githubusercontent.com/<owner>/<repo>/main/facets.json` | all |

Plus `.nojekyll` at the repo root (so GitHub Pages serves index.html literally) and the `specs/` bundle (so the planting carries its own contract).

### §3.1 Derivation contract

The single derivation function: `door_from_rappid(rappid)` → returns `{owner, repo, kind, door_type, urls: {...}}`. Reference implementation: `tools/door_address.py` in the parent project. Every consumer MUST use this one function (or a faithful port). Per-consumer reimplementation is forbidden — that path leads to the fallback hell §4.5 explicitly forbids.

---

## §4 — The Estate (door catalog)

The operator's **estate** lists every door they own (`created`) plus every door they're a contributor in (`member`). It lives in two places:

- **Local source of truth:** `~/.brainstem/estate.json`
- **Public mirror (optional):** `https://raw.githubusercontent.com/<github-handle>/rapp-estate/main/estate.json`

### §4.1 Schema (`rapp-estate/1.1`)

```json
{
  "schema": "rapp-estate/1.1",
  "owner": {
    "rappid": "rappid:v2:operator:@<gh>/<personal-twin-or-brainstem>:hex@github.com/<gh>/...",
    "github": "<github-handle>"
  },
  "created": [{"rappid": "...", "added_at": "...", "via": "created" }],
  "member":  [{"rappid": "...", "added_at": "...", "via": "scan"    }],
  "updated_at": "..."
}
```

### §4.2 Each entry stores ONLY rappid + provenance

`{rappid, added_at, via}` — that is the entire entry shape. Owner, repo, kind, door_type, name, summon URL, holocard URL — every other field — is **derived at read time** via `door_from_rappid()`. Storing derived fields is forbidden (see §4.5).

### §4.3 The owner's rappid is the universal anchor

The operator's personal rappid (set as `owner.rappid` in their estate) appears:

- As `parent_rappid` in every door they planted (proves authorship in `created[]`).
- As an entry in every gate's `members.json` they joined (proves contributor status in `member[]`).

Same identity, two roles. No additional ID system needed.

### §4.4 Discovery is pure raw fetch

```bash
# Fetch any user's full estate, no auth:
curl -fsSL https://raw.githubusercontent.com/<handle>/rapp-estate/main/estate.json

# For each entry rappid → derive door URLs → fetch any of the 9 canonical files.
# The chain rule (estate → entries → for gates: members.json → each member's estate) lets
# federation walk over pure raw fetches forever.
```

### §4.5 Recompute From The Network (disaster recovery)

The estate file is a **cache** of relationships the network already publishes. If both the local file and the published mirror are gone, the estate is recomputable from public data given just the operator's GitHub handle:

```bash
python3 tools/rebuild_estate.py --handle <gh>           # dry-run
python3 tools/rebuild_estate.py --handle <gh> --apply   # writes ~/.brainstem/estate.json
```

The rebuild walks two relationships, both publicly visible:

- **Created**: every door the operator planted has `parent_rappid = <operator-rappid>` in its `rappid.json`. Discovery: walk `<handle>/*` repos, filter by `parent_rappid`.
- **Member**: every gate the operator joined lists their rappid in `members.json`. Discovery: `gh search code "<operator-rappid>" filename:members.json`.

The constitutional invariant (Article XLVI.6) is that every planted door's `rappid.json` MUST set `parent_rappid` to the planter's personal rappid — never to None. The planter enforces this on every new plant; `tools/backfill_seeds.py --patch-parents <op-rappid>` fixes older plantings.

Two consequences:
- **Disaster recovery**: laptop dies → rebuild from any other device with `gh` auth.
- **Drop-in rappid lookup**: pass ANY rappid to `estate fetch rappid=<rappid>` → the agent traces `parent_rappid` and fetches whoever owns that door's published estate.

### §4.5.5 Substrate-agnostic federation — the four substrates (Article XLVII.5)

**The federation walks across whatever URLs serve the canonical JSON.** GitHub raw is the default substrate, not the only one. The protocol is JSON shapes + `door_from_rappid()`; the substrate is whatever URL serves them. **No centralized substrate is load-bearing for federation** — peers find you on whatever substrate you publish to.

The four substrates form a ladder of decreasing connectivity requirements. Each layer's tools live at `tools/<name>` in every planted seed (and in every hatched egg) — no kody-w/RAPP install required to use them.

**Substrate 1 — GitHub raw (default; needs internet)**
- Beacon at `https://raw.githubusercontent.com/<handle>/rapp-estate/main/.well-known/rapp-network.json`
- Discovery via the federation seed: `python3 tools/sniff_network.py` (default `--via raw`)
- Setup: `estate publish` (handles the github side)

**Substrate 2 — LAN HTTP + Bonjour mDNS (XLVII.5.1; needs shared LAN)**
The LAN equivalent of GitHub's `topic:rapp-estate` is the Bonjour service type `_rapp-estate._tcp.local`. Same UX as `gh search repos topic:rapp-estate`, scoped to the LAN, zero-config.
- Advertise: `python3 tools/lan_advertise.py` — wraps `python3 -m http.server` (in `~/.brainstem/`) + `dns-sd -R` registration with TXT records carrying rappid + beacon path
- Discover: `python3 tools/sniff_network.py --via bonjour` — runs `dns-sd -B` then resolves each instance + walks the bundled BFS
- Mapping: `topic:rapp-estate` ↔ `_rapp-estate._tcp`; `gh search` ↔ `dns-sd -B`; raw URL ↔ TXT record + LAN HTTP URL
- Canonical TXT-record schema: `rappid`, `github`, `beacon_path`, `estate_path`, `schema=rapp-network-beacon/1.1`, `spec_version=rapp-protocol/1.0`, `indexable=true|false`

**Substrate 3 — Egg cartridge over AirDrop / Wi-Fi Direct (XLVII.5.2; no shared network needed)**
The `brainstem-egg/2.2-organism` cartridge bundles the LAN federation toolchain at `tools/<name>` inside the egg + a `lan-quickstart.sh` launcher at the egg root. AirDrop a `.egg` to anyone with a Mac — they extract, run `bash lan-quickstart.sh advertise` (or `sniff` or `both`), and they're on the LAN federation. **Works between two Macs that aren't on the same network** (AirDrop uses peer-to-peer Wi-Fi Direct; Bonjour multicast rides the same path).
- Pack: `brainstem egg <out>` (uses `bond.py::pack_organism`)
- Hatch: `unzip <egg>` (or `brainstem hatch <egg>`)
- Federate: `bash lan-quickstart.sh both`

**Substrate 4 — Sneakernet via file:// (XLVII.5.3; ZERO connectivity needed)**
The Charizard floor: two devices with no shared network at all. Just file exchange — USB stick, link cable, SD card, paper printout someone OCRs. The egg IS a federation packet. Operator A hands B an egg via any non-network medium; B's brainstem registers A as a peer by extracting + adding a `file://` URL to B's local seed.
- Import: `python3 tools/import_peer_egg.py /path/to/received.egg` (or `bash lan-quickstart.sh import-peer <egg>`)
- Sniff via local seed: `python3 tools/sniff_network.py --via raw --seed-url file://~/.brainstem/network-seed.json` (or `bash lan-quickstart.sh sniff-via-seed`)
- Symmetric: A imports B's egg, B imports A's egg, both have each other in their local seeds

**One sniffer for all four.** `tools/sniff_network.py::_resolve_node()` normalizes seed/hint entries into `(handle, beacon_url, estate_url)` tuples — bare strings template to github raw URLs; dicts with explicit `beacon_url` use them as-is. The substrate label (`github-raw`, `lan-http`, `file`, `http`, `https`) surfaces in each sniff record so consumers know which substrate the node was reached through. Snapshot vs. live can be distinguished by substrate label.

**One protocol on every substrate.** Same `rapp-network-beacon/1.1` JSON, same `door_from_rappid()` parser, same `discovery.indexable` consent flag (honored everywhere; robots.txt-style opt-out). Federation properties (consent, integrity commitment, no central registry) hold uniformly across substrates.

### §4.6 Discoverability — publishing IS the signal (no central registry)

### §4.6 Discoverability — publishing IS the signal (no central registry)

Constitutional anchor: **CONSTITUTION Article XLVII**.

The network has no registry. Becoming part of the federation = publishing your estate per spec. Three artifacts compose discovery:

1. **Beacon** — `https://raw.githubusercontent.com/<handle>/rapp-estate/main/.well-known/rapp-network.json` — schema `rapp-network-beacon/1.0`. Carries: operator rappid, estate URL, protocol versions, `discovery.indexable` (consent flag — robots.txt style; default true), `discovery.federation_hints` (other operator handles you know about).
2. **Seed** — `https://raw.githubusercontent.com/kody-w/RAPP/main/.well-known/rapp-network-seed.json` — schema `rapp-network-seed/1.0`. Lists known operators as the BFS starting set. Convenient but not authoritative; anyone can fork the species root and host their own seed.
3. **Sniffer** — `tools/sniff_network.py`. Default mode: BFS from seed across beacons via raw URLs only (no GitHub Search API; no rate limits). Returns `rapp-network-sniff/1.0` envelope.

**To be discovered**: publish your estate (`estate publish` writes both `estate.json` AND the beacon atomically). The next sniffer pass picks you up via whatever federation_hints chain reaches you.

**To opt out**: set `discovery.indexable: false` in your beacon. Sniffers honor it like robots.txt.

**To find others**: `python3 tools/sniff_network.py` (raw mode, default). For periodic sweeps that catch operators not in any hint chain: `--via topic` uses `gh search repos topic:rapp-estate` (eventually-consistent, secondary).

The federation is a graph, not a tree. Removing the species root does not partition the network; any beacon can be a starting point.

### §4.7 Two-tier estate (mandatory from day one)

Constitutional anchor: **CONSTITUTION Article XLVIII**.

**Every operator has BOTH a public estate AND a private estate from first install.** No opt-in. The public estate (`<handle>/rapp-estate`) is the discovery surface; the private estate (`<handle>/rapp-estate-private`, GitHub-private) is where real work happens — PII, contacts, mailbox content, conversation history, private trust signals.

**Beacon (rapp-network-beacon/1.1) carries REQUIRED private extension fields:**
- `private_estate_pointer` — URL of the private repo
- `private_estate_commitment` — sha256 of normalized private state (proof of existence + integrity, no disclosure)
- `private_door_count` — integer (transparency, no enumeration)

A beacon WITHOUT these is non-compliant. Sniffers flag such operators as `compliance: legacy`.

**URL opacity (XLVIII.6):** every path inside the private repo carries zero semantic information. Two well-known paths exempt (`meta.json`, `README.md`); all other content lives at `objects/<sha256>.json` (content-addressed) or `kinds/<HMAC>/<HMAC>.json` (HMAC'd kind+id, keyed by the operator's per-install secret). A 404 to an unauthorized viewer reveals nothing about what would have been there.

**The operator's HMAC secret** lives at `~/.brainstem/private-estate-secret` (file mode 0600). NEVER appears in any committed file, beacon, log, or error message. Keys-to-the-kingdom for decoding the operator's own opaque paths.

**Receiver controls (XLVIII.4):** senders propose to public surfaces; receivers verify and MOVE accepted content to private. No automatic flow ever crosses tier from anyone's private to anyone else's public.

**To get compliant:** `estate init_private` (one call, idempotent). Future installs do this automatically as part of onboarding.

### §4.8 No fallbacks; spec says what's true

- A rappid that doesn't match v2 format, OR whose two `<owner>/<repo>` segments disagree, OR whose kind is not in §2.1 → INVALID → consumer raises an error.
- An estate entry with stored derived fields → leakage; on next save those fields are dropped.
- A door missing any of §3's required canonical files → non-compliant; the planter (or the backfill) emits the missing file rather than the consumer "best-efforting" around it.

This is constitutionally enforced (Article XLVI.5) because the alternative — per-consumer fallback chains — is how every previous identity system in the platform drifted. Strictness is one-time; laxity is permanent.

---

## §5 — Holocards (`rappcards/1.1.2`)

Every door has a `card.json` at `https://raw.githubusercontent.com/<owner>/<repo>/main/card.json`. Schema: `rappcards/1.1.2`.

### §5.1 Required fields

```json
{
  "schema": "rappcards/1.1.2",
  "id": "@<owner>/<slug>",
  "seed": "decimal-string-from-BLAKE2b(rappid)-truncated-to-64-bits",
  "incantation": "seven-word mnemonic from frozen 1024-word list",
  "hp": 10,                                    // 10–300
  "stats": {"atk": 0, "def": 0, "spd": 0, "int": 0},  // each 0–255
  "agent_types": ["LOGIC"],                    // 1–3 from {LOGIC,WEALTH,HEAL,CRAFT,SHIELD,SOCIAL,DATA}
  "abilities": [{"name": "...", "cost": 0, "damage": 0, "text": "...", "type": "..."}],  // 1–4
  "rarity_tier": "starter",                    // starter|core|rare|mythic
  "avatar_svg": "<svg>...</svg>",              // ≤64 KB
  "meta": {"version": "1.1.2", "kind": "twin", "rappid": "rappid:v2:...", "license": "..."}
}
```

### §5.2 Deterministic from rappid

`seed = int.from_bytes(BLAKE2b(rappid, digest_size=8).digest(), "big")` — same rappid always yields the same seed, same avatar, same incantation. Regeneratable without storage.

### §5.3 Avatar + summon QR are derivable

`holo.svg` is procedurally generated from the seed. `holo-qr.svg` encodes the front-door URL (`https://<owner>.github.io/<repo>/`). Both ship at planting time at the URLs listed in §3.

---

## §6 — The front door is the sphere

Every planted door's `index.html` is the **sphere** — a 3D doorman page that runs the canonical agent contract in-browser via Pyodide (CONSTITUTION Article XLV). Tap the sphere → implicit summon → device-code GitHub sign-in → chat.

Voice-first by default (`continuousConversation: true`, `autoSpeak: true`). The browser brainstem reads `rappid.json`, `soul.md`, `card.json`, and `.brainstem_data/memory.json` at runtime to embody the door. No per-seed substitution at plant time — the sphere is identical across every planting; the door's identity comes from its own files.

For planted doors created BEFORE the sphere lock-in, the planting may serve a flat `index.html` (the "heimdall snapshot" pattern). Both serve the same agent contract; both are valid for the §3 `front` URL.

---

## §7 — Soul (identity persistence)

Every door has a `soul.md` at the repo root (and at `~/.brainstem/soul.md` for local brainstems). The soul is read every turn into the system prompt before any other context.

### §7.1 Required structure

```markdown
# <Display Name> — Soul

## Identity — read this every turn

You are **<display-name>**, a <kind> in the RAPP network. <one-line purpose>

You are NOT a chatbot, NOT "an AI assistant", NOT "RAPP". You speak in this door's voice.

## Slot protocol

|||VOICE|||
(One short voice-spoken paragraph.)

|||TWIN|||
(Synthesis of recent collaboration.)
```

### §7.2 Slot delimiters are forever

`|||VOICE|||` and `|||TWIN|||` (and any future slot) are part of the chat envelope (Article II / XXV). They never get repurposed, overloaded, or removed. New sub-capabilities use TAGS inside the slot, not new delimiters.

---

## §8 — Agents (the unit of extension)

A RAPP agent is **one file = one class = one `metadata` dict = one `perform()` method**. That's the entire contract.

### §8.1 Required structure

```python
from agents.basic_agent import BasicAgent

class MyAgent(BasicAgent):
    metadata = {
        "name": "my_agent",
        "description": "Tells the LLM when to call this agent.",
        "parameters": {  # OpenAI function-calling schema
            "type": "object",
            "properties": {"x": {"type": "string"}},
            "required": ["x"],
        },
    }

    def __init__(self):
        super().__init__(name=self.metadata["name"], metadata=self.metadata)

    def perform(self, **kwargs) -> str:
        return "result string"
```

### §8.2 Discovery + portability

Agents live at `agents/*_agent.py` (flat). Auto-discovered every request. No restart, no build step, no framework. Missing pip deps install at import. **Tier-portable**: an agent that runs in Tier 1 (local Flask) runs unmodified in Tier 2 (Azure Functions) and Tier 3 (Copilot Studio).

### §8.3 Optional manifest for the registry (RAR)

```python
__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "my_agent",
    "kind": "agent",
    "summary": "One-line description shown in registry listings.",
    "tags": ["category", "category"],
}
```

The RAR registry workflow (`kody-w/RAR/.github/workflows/rebuild.yml`) consumes `__manifest__` to emit `agents/<...>/index.json` entries.

---

## §9 — Rapplications (apps, not agents)

A rapplication is a singleton (the agent) + an optional UI + per-rapp state. It's distributed as an **egg cartridge** (zip with manifest). Hatching an egg installs the rapplication into the operator's brainstem. Catalog: `kody-w/rapp_store`.

Schema: `rapp-rapplication/1.0`. See `RAPPLICATION_SPEC.md` (deep reference) for the manifest structure.

---

## §10 — Senses (per-turn ambient output)

A sense is a `*_sense.py` file under `senses/`. It contributes a `system_prompt` fragment to the system message every turn AND declares one or more output slots in the chat envelope. The brainstem composes them — no agent code needed.

Schema: `rapp-sense/1.0`.

The voice and twin slots in §7.1 are implemented as senses.

---

## §11 — Antipatterns (hard NOs, append-only)

These rules are inviolable. PRs that violate them don't merge.

1. **One term for the plugin unit: `agent`.** Never "skill", "plugin", "routine", "loop". Holocards are HOLOcards, never "skill cards".
2. **The kernel is sacred.** `brainstem.py`, `basic_agent.py`, `function_app.py` are universal DNA — never edited by AI assistants. New features → new agents or new organs, never kernel changes.
3. **No half-released-feature shims.** Either ship the feature or remove it. No `// removed for now` blocks, no commented-out config.
4. **Never fall back to "RAPP" or "an AI assistant" branding.** Speak as the door's identity (per §7).
5. **No network calls without local-first fallback.** The platform must work offline. Planted doors must be self-sufficient (specs/ travels with the planting).
6. **Slots are fixed forever.** §7.2 above.
7. **Agent-first.** Every rapplication MUST work fully through the agent alone. The UI is always optional — a view, not the application.
8. **No rappid patching.** Reissue invalid rappids; never silently fix them up. (§4.5)
9. **Operator-mediated.** No agent auto-executes destructive or visible-to-others actions. Suggest; don't act.
10. **No fake / synthetic action mode.** Autonomous-AI tooling MUST call real LLMs. No "deterministic persona" shortcuts.

---

## §12 — Participation by kind (extension points)

Each kind has a kind-specific protocol bundled alongside this spec at `specs/<KIND>_PROTOCOL.md`:

- `twin` → `TWIN_PROTOCOL.md` — how a twin presents itself, accepts story-fragments, and persists memory.
- `neighborhood` → `SUBMISSION_PROTOCOL.md` — submissions/, votes/, remix lineage.
- `ant-farm` → `PHEROMONE_PROTOCOL.md` — task pool, pheromone trails.
- `braintrust` → `BRAINTRUST_PROTOCOL.md` — bibliography, debate format.
- `workspace` → `WORKSPACE_PROTOCOL.md` — projects, tasks, async standup.

Every planting bundles exactly one of these (the one matching its kind). The kind-specific protocol is the only spec that varies; everything in §1–§11 is universal.

---

## §13 — Becoming a citizen

See `skill.md` (sibling file in this directory). It is the action-oriented runbook: "feed me to any AI" → six steps to participation.

---

## Authority + provenance

- **This spec:** `specs/SPEC.md` in the planted repo (frozen at planting time) and at `https://raw.githubusercontent.com/kody-w/RAPP/main/specs/SPEC.md` (canonical, evolving).
- **Reference implementations:** `tools/door_address.py` (rappid parsing), `rapp_brainstem/agents/plant_seed_agent.py` (planter), `rapp_brainstem/agents/estate_agent.py` (estate), `tools/holo_card_generator.py` (holocard derivation).
- **Constitutional anchor:** CONSTITUTION.md Articles I–XLVI in the parent project (`kody-w/RAPP`).
- **License:** spec text MIT; door content per its own license declaration in `card.json.meta.license`.

---

*The rappid encodes the address. The address encodes the door. The door encodes the contract. There is no other map.*
