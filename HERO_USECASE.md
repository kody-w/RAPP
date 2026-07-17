# Historical Hero Scenarios — Shareable Digital Organisms

> **Current RAPP/1 authority (rev-5).** For canonicalization, identity, frames,
> wire, eggs, registry, trust, and protocol evolution, follow
> [`RAPP1_AUTHORITY.json`](./RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](./RAPP1_STATUS.md). **The scenarios and green checks
> below are a superseded 2026-05 product record, not current product evidence.**

## Current correction

No public planter, browser brainstem, tether, legacy egg transfer, offline
hatcher, cloud tier, or MMR front door is currently shipped. A future scenario
may count only after exact RAPP/1 validation and authenticated acceptance; the
canonical pre-acceptance runner does not convert these historical UX checks
into release claims.

<!-- RAPP1-HISTORICAL-SECTION-START -->

> *"Picture you have two phones and through a QR code where it's on your device because it's all local first... so if you have the Internet, if you have a local model, it will run just the same. It won't be as good. So it's like degrading... It's not like a constant cutoff. It's like, 'Hey, I lost access to the best model, but I'm still here for you where I can.'"*
>
> — the operator, on the canonical scenario this platform must satisfy

This document defines the hero scenarios the RAPP platform must satisfy. Every architectural decision is judged against whether it makes these stories work. They are checked-in here so the bar doesn't drift.

---

## 1. Charizard in the Woods (the offline-share canon)

**The story.** Two friends are in the woods. No internet. Each has a phone. One of them has a useful agent — call it Charizard — and the other one needs it. They open their RAPP front doors on their phones, scan each other's pairing QR codes (Game-Boy-linked-cable style), and the agent transfers device-to-device over WebRTC. The receiver runs the agent locally on their device with whatever local model they have. Both organisms accumulate their own offline experiences. When the network returns, useful mutations rejoin the canonical lineage via PR.

**What must work, end-to-end:**

| Requirement                                      | Implementation                                      | Status |
|---                                               |---                                                  |---     |
| Both phones reach a chat surface offline         | Doorman page (`installer/plant.sh`) + new public `pages/vbrainstem.html` — both fully static + Pyodide + cached | ✅     |
| Pair-by-QR (no copy-paste IDs)                   | `📱 Pair with another device` → autoRenderTetherQR (doorman); **Generate QR** button + 6-digit safety code (vbrainstem.html, ECDSA P-256 keypair fingerprint embedded) | ✅     |
| Cross-device WebRTC channel (DTLS encrypted)     | PeerJS (broker only for handshake) — same in both surfaces | ✅     |
| Agent transfers device-to-device                 | Legacy chunk transport exists, but current receipt must validate the complete RAPP/1 §9 egg and applicable signature—not SHA-256 alone. | ⚠ RAPP/1 migration required |
| Receiver runs agent locally                      | Current target runs only the verified `agent.py` from a valid §9 `rapplication` egg. The contained browser's raw-main loader is legacy behavior. | ⚠ RAPP/1 migration required |
| Live tethered group chat (vs. one-way egg trade) | The contained `pages/vbrainstem.html` demo preserves application transcript state; it is not a third wire or canonical RAPP stream. Current async state uses verified §7 frames. | ⚠ RAPP/1 migration required |
| Graceful degrade when no network                 | `cachedGhJson` returns last-cached state; vbrainstem falls back to in-memory mirror when Edge Tracking Prevention blocks localStorage | ✅     |
| Local model fallback                             | Doorman config supports custom Copilot endpoint; vbrainstem.html `?brainstem=URL` override + localhost-7071 default | ⚠ partial — works for self-hosted endpoint, no offline LLM yet |
| Mutations stay local until bonded back           | Legacy `state_at_seal` and `brainstem-egg/2.3-session` paths demonstrate the UX but require migration to RAPP/1 §§7/9. | ⚠ RAPP/1 migration required |
| One hatcher routes any cartridge kind            | Current acceptance must dispatch registered RAPP/1 §9 variants only after integrity, viability, and signature checks. The legacy hatcher does not yet satisfy that contract. | ⚠ RAPP/1 migration required |

**Acceptance criteria.** Two devices, both in airplane mode, can:
1. Open their front doors and chat with each other through the tether QR (no internet, no broker once the channel is open)
2. Trade an `.egg` over the tether
3. Each receiver validates the complete §9 manifest and reads only verified
   listed contents; no repository fetch is required
4. The receiver runs at least one of the agents in the egg via Pyodide locally
5. A live session can be carried only as the exact RAPP/1 §9 `session`
   variant, with its JSON manifest and signature handled per §9

---

## 2. The Dream Catcher (parallel-dimension reassimilation)

**The story.** Once an organism is hatched on a device, it can live an offline
life and later present verified divergent streams. Current merge ordering is
exactly RAPP/1 §7.4 (fixed `utc`, then `frame_hash`) and each stream must pass
§7.5; the older `(utc, frame_n)` doctrine is migration history.

**The doctrine** (from the transcript, lines 67–78):

> *"Whatever frame hit the UTC one first, that's canon, and then anything that doesn't contradict that. I'm going to layer on that... There are contradictions, so that doesn't get synced. It gets put into a different dimension of that aspect of that life, so you don't lose that data."*

**What must work:**

| Requirement                                       | Implementation                                          | Status |
|---                                                |---                                                      |---     |
| Frames are content-addressed                      | Current target is the exact eleven-key RAPP/1 §7 frame with domain-separated `payload_hash` and `frame_hash`; the legacy `rapp-frame/1.0` chain is migration input only. | ⚠ RAPP/1 migration required |
| Sequence and time are verified                    | RAPP/1 §7.5 verifies `seq`, fixed-form `utc`, `prev`, `prev_wave`, stream binding, and registered genesis. | ⚠ RAPP/1 migration required |
| Eggs carry verified frame data                    | A §9 tree variant may list frame files in `contents`; every included frame is independently verified per §7.5. Legacy `state_at_seal` synthesis is not current. | ⚠ RAPP/1 migration required |
| Diff two parallel dimensions visually             | `🕸️ Dream Catcher` pane — drop both eggs, see diff      | ✅     |
| Current total merge order                         | ascending fixed-form `utc`, ties by `frame_hash`, after full stream verification | ⚠ RAPP/1 migration required |
| Contradictions saved as alternate dimensions      | parallel-only frames with PK collision rendered as ⚡ contradiction (alternate-dimension data); not auto-merged | ✅ ([test](../tests/doorman/dreamcatcher.mjs)) |
| Doorman writes a frame log offline                | Existing `appendFrame()` output is legacy and must migrate to the exact eleven-key §7 envelope. | ⚠ RAPP/1 migration required |
| Reassimilation via PR                             | "Open reassimilation issue on GitHub →" pre-fills issue | ✅     |
| Cross-species check (same rappid required)        | lineage warning fires when rappids differ               | ✅     |

**Acceptance criteria.** Drop two eggs of the same lineage into the Dream Catcher:
1. Frames common to both render greyed-out (shared canon)
2. Frames only in the parallel egg render highlighted (reassimilation candidates)
3. Order accepted cross-stream frames by `utc` then `frame_hash`; refuse
   invalid chains and preserve rejected/fork evidence without repair
4. Operator can open a pre-filled GitHub Issue listing every parallel-only frame as a reassimilation candidate

---

## 3. Mom's Mixtape (the accessibility floor)

**The story.** From the transcript, line 137:

> *"If you can share your mix tape with your mom, and she can use it, that opens up everyone."*

**What must work:** every step of the canonical paths above must be doable without:
- Opening a terminal
- Knowing what a brainstem is
- Understanding GitHub mechanics
- Reading documentation

**The accessibility test:**

| Path                                        | Steps for a non-technical user               |
|---                                          |---                                            |
| Talk to a planted organism                  | Open URL → click "Talk to X" → chat          |
| Show its trade card                         | Click "🃏 Show my card" → tap card to flip   |
| Pair with another device                    | Click "📱 Pair" → other device scans QR      |
| Back up the organism                        | Click "🥚 Export .egg" → file downloads      |
| Verify an egg isn't tampered                | Click "🔬 Verify" → drag egg in              |
| Submit a useful mutation back to lineage    | Click "🌱 Propose an agent" → fill form → submit |
| Reassimilate parallel dimensions            | Click "🕸️ Dream Catcher" → drag both eggs in |

**Acceptance criteria.** A user with no programming background can complete the full Charizard-in-the-woods loop on a phone in under 5 minutes from first visit.

---

## 4. The Pizza Place / Pokémon-Go Layer (future, defined for parity)

**The story.** From the transcript, lines 38–66:

> *"I like this pizza place. I want you to check going forward where the best times are and then if there are any discounts. So your digital twin is actually planted there or a version of that digital twin in that virtual [location]... You can have intelligence swarms, location-based collaborating in public through the cloud endpoints. And then through the cloud endpoints, you can actually sync back with your digital twin on device when it comes back on device."*

**What's needed** (not yet implemented; flagged so it doesn't get reinvented):

- **Location-tied seeds** — `kind: "place"` already exists on rappid.json; need a `location_geohash` field for proximity-matching
- **Anonymous proximity swarm** — two organisms in the same geohash cell can discover each other and share what their operators have consented to share publicly
- **Public-twin consent layer** — `card.json` already supports `flavor` / `abilities`; needs an explicit `public_facets` field listing what's shareable in proximity
- **Sync-back on reconnect** — the Dream Catcher already handles reassimilation of frames; proximity-acquired frames are just another stream

**Acceptance criteria** (when implemented): a user who plants a `place` seed for the local pizza place sees, when revisiting that pizza place from another organism's front door, the public facets the operator has chosen to expose (e.g. "best times to come", aggregated visitor reactions).

---

## 5. MMR & Lineage (the cohort layer)

**The story.** Every planted organism gets a single global MMR rating (Dota-style, formula identical across the species). Children inherit a fixed snapshot of the parent's MMR-at-our-birth as a lineage gift — true epigenetics: parent regression after the child is planted doesn't reduce the child's inherited cred.

**What must work:**

| Requirement                                       | Implementation                                          | Status |
|---                                                |---                                                      |---     |
| Single global MMR formula                         | `computeMMR()` in front-door — same code on every seed  | ✅     |
| Calibration phase                                 | first 5 mutations OR 7 days → `📐 Calibrating · X%`     | ✅     |
| Activity decay                                     | last-commit recency scales above-baseline (1.0 → 0.45)  | ✅     |
| Plant-time lineage snapshot                       | `lineage_snapshot` block in rappid.json captures parent's MMR-at-our-birth at plant time | ✅ ([test](../tests/doorman/lineage-snapshot.mjs)) |
| Child reads snapshot first, falls back to live    | `_parentLineageGift` prefers `rappid.lineage_snapshot.parent_mmr_at_birth`; live fetch on older seeds | ✅     |
| Offspring boost                                   | `forks_count` adds `sqrt(forks) * 400` to MMR           | ✅     |

**Acceptance criteria.** Plant a child seed with `MIRROR_PARENT=https://github.com/<owner>/<parent-repo>`:
1. The child's `rappid.json` contains a `lineage_snapshot` block with `parent_mmr_at_birth`
2. The child's front-door resume shows the lineage gift derived from the snapshot, not a live fetch
3. Subsequent regression on the parent's MMR doesn't reduce the child's gift

---

## Test Commands

```bash
# Plant tests (syntax + file layout)
bash installer/test_plant.sh

# Frame log + Dream Catcher (Hero §2)
node tests/doorman/dreamcatcher.mjs

# Tether egg send protocol (Hero §1)
node tests/doorman/tether-egg.mjs

# Plant-time lineage snapshot (Hero §5)
node tests/doorman/lineage-snapshot.mjs
```

All four must be green before merging changes that touch the surfaces named in the rows above.

---

## How This Document Is Used

- **Every PR** that touches the front door, doorman, egg export/import, or pairing flow must declare which hero requirement it advances or preserves.
- **Every architecture proposal** that would change one of the ✅ rows must justify why the hero use case is preserved or improved, never degraded.
- **Every release** runs the acceptance criteria as an explicit smoke test (currently manual; CI'd later).

---

## Source

Hero scenarios are extracted from a private design conversation on Agent Shareability (May 2026). The conversation document lives in the operator's records; the canonical scenarios are checked in here so they're part of the repo's permanent specification.

<!-- RAPP1-HISTORICAL-SECTION-END -->
