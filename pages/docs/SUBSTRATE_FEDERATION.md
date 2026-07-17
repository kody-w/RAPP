# SUBSTRATE_FEDERATION — The Four Substrates of the RAPP Network

> **Current RAPP/1 authority (rev-5).** For canonicalization, identity, frames,
> wire, eggs, registry, trust, and protocol evolution, follow
> [`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../RAPP1_STATUS.md). Carrier choice never changes the
> RAPP/1 §7/§8 envelope, §9 egg, or §13 trust requirements.

> **Application metadata:** `rapp-network-beacon/1.1` · **Status:** carrier
> architecture, subordinate to RAPP/1 · **First shipped:** 2026-05-09

This document describes application discovery across several media. It does
not define RAPP protocol structure: every medium carries the same exact §7/§8
forms and §9 eggs, and authenticated acceptance always uses §§10/13.

If you're writing a sniffer, an advertiser, an egg importer, or any code that maps from "I want to find peers" → "they showed up in my catalog" — this is the contract.

---

## §1 — One protocol, four substrates

The federation walks across **whatever URLs serve the canonical JSON**. GitHub raw is the default substrate, but never the only one. Removing any substrate (or any individual operator on any substrate) does not partition the federation. **No centralized substrate is load-bearing.**

The four substrates form a ladder of decreasing connectivity requirements:

| # | Substrate | Connectivity | Article | Tools |
|---|---|---|---|---|
| 1 | GitHub raw URLs | Internet + (optional) `gh` auth | XLVII (default) | `tools/sniff_network.py` (default `--via raw`) |
| 2 | LAN HTTP + Bonjour mDNS | Shared LAN | XLVII.5.1 | `tools/lan_advertise.py` + `tools/sniff_network.py --via bonjour` |
| 3 | Egg cartridge over AirDrop | Wi-Fi Direct (no shared net) | XLVII.5.2 | The `.egg` itself + bundled `lan-quickstart.sh` |
| 4 | Sneakernet via `file://` | **Zero — just byte exchange** | XLVII.5.3 | `tools/import_peer_egg.py` (extract + add to local seed) |
| 5 | WebRTC tether (operator-pair, ephemeral) | Internet (broker for handshake only); P2P after | XLIX (Twin) + SPEC §18.11 | `pages/vbrainstem.html` (QR-pair → ECDSA P-256 + 6-digit safety code → DTLS-SRTP data channel) |

> **Historical note (2026-05-10), superseded structurally.** The contained
> WebRTC surface emitted a retired `brainstem-egg/2.3-session` cartridge.
> Current portability uses the registered RAPP/1 §9 variants; changing carrier
> never changes the manifest or verification rules.

**Same application discovery metadata on all four:**
- Same `rapp-network-beacon/1.1` JSON shape for beacons
- Same `rapp-estate/1.1` JSON shape for estates
- Same `door_from_rappid()` parser (per Article XLVI.5)
- Same `discovery.indexable` consent flag (honored uniformly; robots.txt-style)
- Same federation properties (decentralized, multi-root, censorship-resilient)

**Same sniffer for all four.** `tools/sniff_network.py::_resolve_node()` normalizes seed/hint entries into `(handle, beacon_url, estate_url)` tuples. Bare handle strings template to github raw URLs; dicts with explicit `beacon_url` use them as-is. The BFS walks all substrates uniformly. The `substrate` label (`github-raw`, `lan-http`, `file`, `http`, `https`) surfaces in each sniff record so consumers can distinguish snapshot vs. live data when it matters.

---

## §2 — Substrate 1: GitHub raw (Article XLVII)

**Use when:** You have internet + a public GitHub account.

**Beacon URL pattern:**
```
https://raw.githubusercontent.com/<handle>/rapp-estate/main/.well-known/rapp-network.json
```

**Discover via:**
```bash
python3 tools/sniff_network.py
# Default: BFS from kody-w/RAPP/.well-known/rapp-network-seed.json
```

**Or via topic search (eventually-consistent, slower; secondary):**
```bash
python3 tools/sniff_network.py --via topic
# Uses gh search repos topic:rapp-estate
```

**Setup:** `estate publish` (handles the github side end-to-end — creates `<handle>/rapp-estate`, writes beacon, sets the `rapp-estate` topic, optionally creates `<handle>/rapp-estate-private` per Article XLVIII).

---

## §3 — Substrate 2: LAN HTTP + Bonjour (Article XLVII.5.1)

**Use when:** You're on a shared LAN (office, home, coffee shop WiFi).

The LAN equivalent of GitHub's `topic:rapp-estate` is the Bonjour service type **`_rapp-estate._tcp.local`**. Same UX as `gh search repos topic:rapp-estate`, scoped to the LAN, zero-config.

**Mapping:**

| GitHub | LAN |
|---|---|
| `topic:rapp-estate` on a repo | `_rapp-estate._tcp` service type |
| `gh search repos topic:rapp-estate` | `dns-sd -B _rapp-estate._tcp local.` |
| Beacon at raw URL | Beacon at LAN HTTP URL announced via TXT record |
| `estate publish` (sets topic) | `tools/lan_advertise.py` (registers Bonjour) |
| `sniff --via topic` | `sniff --via bonjour` |

**Advertise yourself on the LAN:**
```bash
python3 tools/lan_advertise.py --port 8080
# ▸ HTTP server on port 8080 (serving ~/.brainstem)
# ▸ Bonjour: <handle>-brainstem._rapp-estate._tcp.local. (port 8080)
# beacon URL: http://<your-lan-ip>:8080/.well-known/rapp-network.json
# estate URL: http://<your-lan-ip>:8080/estate.json
```

**Discover LAN peers:**
```bash
python3 tools/sniff_network.py --via bonjour
# · browsing _rapp-estate._tcp.local for 3s…
# · found 2 Bonjour service(s): kody-w-brainstem, rappter1-brainstem
# ★ kody-w     doors: 16 created  (substrate: lan-http)  [🔒 xlviii]
# ★ rappter1   doors:  5 created  (substrate: lan-http)  [🔒 xlviii]
```

**Application TXT-record convention** (advertisers may publish this discovery
metadata; consumers still validate §6 and resolve §13 before use):

```
rappid       = the operator's exact RAPP/1 §6 rappid
github       = the operator's github handle (informational; LAN doesn't require it)
beacon_path  = "/.well-known/rapp-network.json"
estate_path  = "/estate.json"
schema       = "rapp-network-beacon/1.1"
indexable    = "true" | "false"
```

## Historical pre-RAPP/1 carrier appendix (superseded)

<!-- RAPP1-HISTORICAL-SECTION-START -->

The remaining carrier procedures record the shipped legacy implementation.
Their old egg layouts, schema strings, synthesized beacons, and acceptance
steps are migration evidence only. A current carrier transports a valid
RAPP/1 §9 egg unchanged and never bypasses §§6, 10, or 13 verification.

### §3.1 — LAN-SSH as a neighborhood-egg carrier (historical v1)

Substrate 2 also covers **direct SSH-tar transport** for full-state cartridges, used by the neighborhood-egg snapshot/hatch pattern ([[Neighborhood Egg — Snapshot and Hatch]], [`NEIGHBORHOOD_EGG_SPEC.md`](./NEIGHBORHOOD_EGG_SPEC.md)).  Bonjour + LAN HTTP advertises and discovers; LAN-SSH moves the bytes.  Same substrate, different carrier.

The cartridge format itself is **substrate-agnostic** — see [`NEIGHBORHOOD_EGG_SPEC.md`](./NEIGHBORHOOD_EGG_SPEC.md) §6.1 for the full carrier matrix (LAN-SSH today; GitHub raw, HTTPS-with-auth, Tailscale planned).  This subsection documents the LAN-SSH carrier specifically because it's the v1 shipping path.

**Carrier (capture side):**

```bash
# capturing peer twin workspaces into a snapshot:
ssh peer 'COPYFILE_DISABLE=1 tar --exclude="._*" --exclude=".DS_Store" \
  -czf - -C $HOME/.rapp/twins <hash>'
# stdout = .tar.gz stream → snapshot agent embeds at peers/<peer>/twins/<hash>.tar.gz
```

**Carrier (restore side):**

```bash
# restoring a peer twin workspace from a snapshot:
cat peers/<peer>/twins/<hash>.tar.gz \
  | ssh peer 'mkdir -p $HOME/.rapp/twins && cd $HOME/.rapp/twins && tar -xzf -'
```

**Auth:** SSH with `BatchMode=yes`, `StrictHostKeyChecking=accept-new`, key-only.  No password prompts.  Peer hosts are listed in `~/.rapp/peers.json` (see [`NEIGHBORHOOD_EGG_SPEC.md`](./NEIGHBORHOOD_EGG_SPEC.md) §6).

**No agent on the peer required.**  The peer just needs sshd, tar, gzip — all macOS/Linux default.  This is what lets a fresh peer be "joined" to the neighborhood just by authorizing one SSH key.

**The same neighborhood format on other substrates.**  When members live on GitHub (per [[ESTATE_SPEC]] §1 — rappid-as-URL), the carrier is `gh api` + raw URL fetch + PR-on-write.  When members live behind an auth gate ([[The Auth Cascade]]), the carrier is HTTPS-with-token.  When members live on a Tailnet, the LAN-SSH carrier still works — `ssh_host` just resolves through the Tailscale interface.  The egg contents are the same regardless.

---

## §4 — Substrate 3: AirDrop'd egg cartridge (Article XLVII.5.2)

**Use when:** Two devices that aren't on the same network — but can AirDrop / Wi-Fi-Direct between each other (e.g. two Macs at a conference, on a plane, in a SCIF).

**The egg is a fully portable federation node.** Every `brainstem-egg/2.2-organism` cartridge bundles the LAN federation toolchain at `tools/<name>` inside the egg + a `lan-quickstart.sh` launcher at the egg root. After extracting (just `unzip`), the recipient runs the quickstart and they're advertising on the LAN — **no kody-w/RAPP install required**.

**Pack an egg:**
```bash
brainstem egg ~/Desktop/rappter1.egg
# Or programmatically: bond.pack_organism(home, src, kernel_version)
```

**Egg layout:**
```
egg root/
├── manifest.json          ← lan_federation_ready: true
├── rappid.json            ← operator identity
├── soul.md, .env          ← personality + config
├── agents/, organs/, senses/, services/, data/
├── tools/                 ← LAN federation toolchain (bundled per XLVII.5.2)
│   ├── lan_advertise.py
│   ├── sniff_network.py
│   ├── door_address.py
│   ├── path_opacity.py
│   ├── private_estate_init.py
│   ├── rebuild_estate.py
│   └── import_peer_egg.py
└── lan-quickstart.sh      ← bash launcher
```

**Recipient's flow** (after AirDrop):
```bash
unzip rappter1.egg -d ~/Desktop/rappter1-brainstem/
cd ~/Desktop/rappter1-brainstem/

bash lan-quickstart.sh advertise        # broadcast on Bonjour
bash lan-quickstart.sh sniff             # discover other peers
bash lan-quickstart.sh both              # advertise + sniff in one shot
```

The quickstart copies the egg's `rappid.json` + `.well-known/` into `$RAPP_BRAINSTEM_HOME` (default `~/.brainstem`) so the bundled tools see the operator's state via standard paths — same conventions as a normal install, just sourced from the egg.

---

## §5 — Substrate 4: Sneakernet via `file://` (Article XLVII.5.3)

**Use when:** Two devices with NO shared network at all. Just file exchange — USB stick, link cable, SD card, Bluetooth, paper printout someone OCRs. The Charizard floor.

**The egg IS a federation packet.** When operator A hands B an egg via any non-network medium, B's brainstem registers A as a federation peer by extracting the egg + adding a `file://` URL to B's local seed. B's sniffer walks A as a `substrate: file` node identical to live LAN/github operators.

**Import a received egg:**
```bash
python3 tools/import_peer_egg.py /path/to/received.egg
# Or via the bundled launcher:
bash lan-quickstart.sh import-peer /path/to/received.egg
```

What `import_peer_egg.py` does:
1. Validates the egg's `manifest.json` + `rappid.json`
2. Derives the peer's handle from their rappid (`@<handle>/<repo>`)
3. Extracts to `~/.brainstem/peers/<handle>/`
4. Synthesizes a beacon at `<peers>/<handle>/.well-known/rapp-network.json` if the egg didn't carry one (works for older egg formats)
5. Adds a `{github, beacon_url: file://..., estate_url: file://...}` entry to `~/.brainstem/network-seed.json`

**Sniff via the local seed:**
```bash
python3 tools/sniff_network.py --via raw --seed-url file://~/.brainstem/network-seed.json
# Or via the launcher:
bash lan-quickstart.sh sniff-via-seed
# → walks all peers in your local seed (sneakernet-imported AND any github-substrate seeds)
```

**Symmetric flow:**
- A packs egg-A → sneakernet → B → B imports egg-A → B's seed includes A
- B packs egg-B → sneakernet → A → A imports egg-B → A's seed includes B
- No third device required to mediate. Each egg-exchange is a "tick" of the federation. Async, persistent.

---

## §6 — The unified sniffer

`tools/sniff_network.py` walks all four substrates via the same BFS, gated by `--via`:

```bash
python3 tools/sniff_network.py                        # --via raw (default; github seed)
python3 tools/sniff_network.py --via raw --seed-url <any-url>
python3 tools/sniff_network.py --via topic            # gh search topic:rapp-estate
python3 tools/sniff_network.py --via bonjour          # LAN _rapp-estate._tcp browse
```

Each operator's record carries a `substrate` field so consumers know how the data got there:

```json
{
  "github":          "rappter1",
  "operator_rappid": "rappid:@rappter1/rappter1-twin:...",
  "beacon_url":      "file:///Users/kodywildfeuer/.brainstem/peers/rappter1/.well-known/rapp-network.json",
  "substrate":       "file",
  "estate_url":      "file:///Users/kodywildfeuer/.brainstem/peers/rappter1/estate.json",
  "compliance":      "xlviii",
  "discovered_via":  "seed",
  "hop":             0
}
```

`substrate` values: `github-raw`, `lan-http`, `file`, `http`, `https`, `other`.

`compliance` values: `xlviii` (full Article XLVIII compliance), `partial` (has private pointer but doesn't declare XLVIII), `legacy` (public-only, pre-XLVIII).

---

## §7 — Honored consent across substrates

The `discovery.indexable` flag in every beacon is the operator's robots.txt-style consent statement. `true` (default) means "indexable by sniffers; appears in federation walks." `false` means "do not include me in federation indexes; do not surface me to other operators automatically." **Sniffers MUST honor this flag on every substrate equally** — github raw, LAN, AirDrop'd egg, sneakernet — no exceptions.

The `--include-private` flag in `sniff_network.py` exists for operator-side audit tooling (the operator running diagnostics on their own beacon) and is constitutionally reserved for self-audit, not for crawling others.

Operators who want to be reachable by their direct contacts but not surface in public sniffs set `indexable: false`. Their estate is still publicly fetchable (it's a public file at a known URL), but the network's automatic discovery surface respects their opt-out.

---

## §8 — Constitutional summary

The constitutional ladder for substrate-agnostic federation:

- **Article XLVII** — Discoverability without a central registry; publishing IS the signal
  - **XLVII.1** — Publishing IS the signal
  - **XLVII.2** — Pure-raw discovery is the default
  - **XLVII.3** — Consent is in the beacon (robots.txt analog)
  - **XLVII.4** — The network is a graph, not a tree
  - **XLVII.5** — Substrate-agnostic federation (the general principle; this doc)
    - **XLVII.5.1** — LAN auto-discovery via Bonjour
    - **XLVII.5.2** — The egg carries the federation tools (AirDrop-portable)
    - **XLVII.5.3** — Sneakernet federation (the egg IS a federation packet)

The platform's local-first promise survives every centralized-substrate failure mode. GitHub flagged your account? LAN. No shared LAN? AirDrop the egg. No shared network at all? USB stick. **The federation walks whatever lights up.**

---

## §9 — Cross-references

- **CONSTITUTION Article XLVII.5 (and subsections .5.1–.5.3)** — the load-bearing principles
- **`specs/SPEC.md` §4.5.5** — bundled into every planted seed (anonymous AI contributors can read it offline)
- **`tools/sniff_network.py`** — reference unified sniffer (`_resolve_node()` is the single normalizer)
- **`tools/lan_advertise.py`** — reference Bonjour advertiser (XLVII.5.1)
- **`tools/import_peer_egg.py`** — reference sneakernet importer (XLVII.5.3)
- **`rapp_brainstem/utils/bond.py::ORGANISM_LAN_FEDERATION_TOOLS`** — list of tools bundled in every egg (XLVII.5.2)
- **Vault note `2026-05-10 — rappter1 first contact + Article XLVII.5 substrate-agnostic federation.md`** — the motivating story
- **Companion specs:**
  - `pages/docs/ESTATE_SPEC.md` — Article XLVI (rappid is the address)
  - `pages/docs/PUBLIC_PRIVATE_BOUNDARY.md` — Article XLVIII (two-tier estate + URL opacity)

---

*One protocol. Four substrates. Federation walks whatever lights up.*

<!-- RAPP1-HISTORICAL-SECTION-END -->
