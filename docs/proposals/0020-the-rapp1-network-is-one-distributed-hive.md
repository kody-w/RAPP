# Proposal 0020 — The RAPP/1 network is one distributed Hive

> **Current RAPP/1 authority (rev-5).** For canonicalization, identity, frames,
> wire, eggs, registry, trust, and protocol evolution, follow
> [`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../RAPP1_STATUS.md). This proposal changes none of
> them. It says how the network's public repositories are found and read, and
> this draft changes no code.

## Status

**Draft.** The owner's merge would accept it (Article XXX.2).

An AI assistant drafted this proposal for the distributed-Hive workstream.
**The owner has not chosen.** He can accept it with the recommended owner
decisions (D1 to D4 below), change any of them, or refuse it. Nothing here
governs until he merges it by hand (Article XXVIII.4, Article XXX.2).

The draft lives on the branch `experimental/proposal-0020-distributed-hive`.
No pull request is open for it; the AI opens none and merges nothing. Besides
this file, the branch refreshes only the two receipts that count tracked files
(`RAPP1_ADAPTATION_INVENTORY.json` and `tests/fixtures/rapp1-doc-scope.json`).
It does not edit `CONSTITUTION.md`. The amendment text near the end is for a
later pull request, after acceptance (Article XXVIII.6).

**Numbering.** Numbers 0020 to 0029 are set aside for this workstream, and
0001 to 0019 for other drafts: 0001 is pull request #119, 0002 is on the
branch `experimental/proposal-0002-tier2-parity`, and 0003 is pull request
#121. Article XXVIII.3 asks for monotonic numbers, so if this merges before the
lower numbers are used, the owner may renumber it first. HIVE-MD's "Remote
member spaces" already cites it as proposal 0020.

Line numbers are for `main` at commit `8afc973`. This branch changes none of
the files they point into.

## Context

### What the constitution describes

Article XLVII says the network needs no registry. An operator publishes a
beacon, and sniffers start at a seed and walk beacons over raw URLs (XLVII.1,
XLVII.2). The beacon's `discovery.indexable` is consent (XLVII.3). The network
is a graph, and a walk may start anywhere (XLVII.4). Any substrate that serves
the same JSON works, including a LAN and `file://` (XLVII.5). Article XLVIII
adds the private-extension fields (`rapp-network-beacon/1.1`) and keeps private
content out of every public file. Article XLVI makes `estate.json` the
operator's catalog of doors.

### What is live today

- **The seed** ([`.well-known/rapp-network-seed.json`](../../.well-known/rapp-network-seed.json),
  lines 2–43) is `rapp-network-seed/1.0`, `observation-only`, with
  `discovery_enabled: false`. It lists one operator, `kody-w`, with
  `verified: false` and `accepted: false`. Its `beacon_url` and `estate_url`
  are moving `main` URLs in `kody-w/rapp-estate`, recorded as
  `moving-branch-observation` with `commit_pin: null` and `sha256: null`. Its
  own `source_policy` requires a full commit pin and a SHA-256 and accepts no
  moving ref (lines 14–20). `federation_hints` is empty.
- **The beacon is a placeholder.** In `kody-w/rapp-estate` at `main` (commit
  `acc17dc`, 2026-09-25),
  [`.well-known/rapp-network.json`](https://github.com/kody-w/rapp-estate/blob/acc17dca283619f288274f237c8c61f437d014f3/.well-known/rapp-network.json)
  is a status document: `document_type: rapp-network-publication-status`,
  `accepted_as_network_beacon: false`, a top-level `indexable: false`, and no
  `schema`.
- **So is [`estate.json`](https://github.com/kody-w/rapp-estate/blob/acc17dca283619f288274f237c8c61f437d014f3/estate.json):**
  `document_type: rapp-estate-publication-status`,
  `accepted_as_estate_manifest: false`, and no `created` or `member` entries.
- **The sniffer stops at the estate.**
  [`tools/sniff_network.py`](../../tools/sniff_network.py) makes no network
  call by default, and `--online` also needs a reviewed source binding. Online,
  it reads the seed's `operators` (line 921), keeps a beacon only if its
  `schema` is 1.0 or 1.1 (line 815), honors `discovery.indexable` (line 992),
  requires a valid `operator_rappid` (line 1015), and lets the beacon's
  `estate_url` win (line 1036). From `estate.json` it only counts the
  `created` and `member` entries (lines 1106–1111). The only things it queues
  are the beacon's federation hints (lines 1131–1135). Every record says
  `accepted: false`. Today it would skip `kody-w`, because the status document
  has no beacon schema.

A walk from the seed today reaches one placeholder and stops. That is honest:
nothing has been published as a beacon yet.

### The RAPP Hive already maps the network

The RAPP project is also run as a Hive: a folder of markdown files in git,
changed by signed commits, under the HIVE-MD convention of
`kody-w/rapp-model-hive`. Its public copy is `kody-w/rapp-hive-public`. At
commit `a8f4cd8`, its
[`PUBLISHED.md`](https://github.com/kody-w/rapp-hive-public/blob/a8f4cd86f6248d07f98ce2c38d1a3c0f97307a31/PUBLISHED.md)
names the Hive (`hive: af02504304365b6d8b068553156b5e6d`) and the approved
manifest, and lists all 743 published files with their SHA-256. It holds:

- the **portfolio**
  ([`portfolio/PORTFOLIO.md`](https://github.com/kody-w/rapp-hive-public/blob/a8f4cd86f6248d07f98ce2c38d1a3c0f97307a31/portfolio/PORTFOLIO.md)):
  one file per public RAPP repository, 317 today, in 18 lines, each with a
  RAPP/1 status earned from rapp-1's own checker;
- the **subway map** drawn from those files
  (<https://kody-w.github.io/rapp-hive-public/portfolio/subway.html>);
- one RAPP/1 §7 `body.pulse` frame per crawl, on the body stream
  `rappid:@kody-w/rapp1-network:71216534…`, a keyless rappid minted on
  2026-09-25
  ([`portfolio/rappid.json`](https://kody-w.github.io/rapp-hive-public/portfolio/rappid.json)).
  The first frame,
  [`portfolio/versions/2026-09-25-0/pulse.json`](https://kody-w.github.io/rapp-hive-public/portfolio/versions/2026-09-25-0/pulse.json),
  has `seq` 0 and `sig: null`.

### What falls short

- The richest map of the network is not on the discovery chain. Nothing in
  the seed, the beacon or `estate.json` points to it, and a sniffer that
  follows Article XLVII never reaches it.
- The facts about each repository (what it is, its line, its neighbors) are
  written in the Hive, not in the repository. A repository cannot publish its
  own place on the network, although publishing is the signal (XLVII.1).
- Nobody can read "the whole network at its long-term-support commits" with
  plain raw fetches and check every byte.

### Why the Hive convention needs a new part

1. **Pointers cannot live in a Hive's own `members/`.** There,
   `members/<name>/` is a person's space: their device keys and one vote.
   Names are lowercase letters, digits and dashes, at most 32 characters, so
   `RAPP`, `RAR` or `RAPP_Store` could not be names. Only that member's own
   signed commits may change the space, so a curator could not write it. The
   checker also refuses a pointer file there.
2. **A public copy holds one room and has no `HIVE.md`.** Publishing copies
   the approved files of one room into a separate repository with
   `PUBLISHED.md`. A clean public copy has `PUBLISHED.md` and no `HIVE.md`, and
   a reader refuses a listing that names `HIVE.md`. So a reader starts at
   `PUBLISHED.md`, and whatever the network adds to the root (pointers, former
   pointers, pulses) sits in sub-folders of that one room.
3. **A raw URL cannot list a folder.** `raw.githubusercontent.com` serves
   files, not folders: a folder URL answers 404. Every set of files must come
   from an index: `PUBLISHED.md` for the root, a pointer's list of hashes for a
   station at its pinned commit, and a card's `shares` for the newest files.
4. **`.rapp/` is already in use.** RAR has
   [`.rapp/bootstrap.json`, `.rapp/bootstrap.py` and `.rapp/bootstrap-managed.json`](https://github.com/kody-w/RAR/tree/ecf5f52312cf083eaedf5e0aa8782debc7f0af4b/.rapp),
   the RAPP Workspace bootstrap files. `kody-w/rapp-tools` at `b0e37eb` treats
   `.rapp/cache`, `.rapp/workspace` and `.rapp/reports` as private control
   folders
   ([`rapp_workspace.py` line 88](https://github.com/kody-w/rapp-tools/blob/b0e37eb3c67e309f342629e0ec96dea2688a5951/rapp_workspace.py#L88)).
   The network may use only `.rapp/member.md` and `.rapp/shared/`.
5. **Markdown causes no drift.** rapp-1's `rapp_check.py` reads only `.json`
   and `.egg` files
   ([line 73 at `591e014`](https://github.com/kody-w/rapp-1/blob/591e014ad39e223b00ab343ae26e5d9a867ebeee/rapp_check.py#L73)),
   so a markdown card cannot change a repository's checker status. A frame
   file would be checked: any error in it, or a signature that cannot be
   checked without a trusted anchor, shows as drift (lines 169–178 and
   575–576). So station repositories carry no frames.
6. **Some repositories pin their own file list.** RAPP pins its tracked path
   count and digest in `RAPP1_ADAPTATION_INVENTORY.json`, and its document and
   byte counts in `tests/fixtures/rapp1-doc-scope.json`. A new file there needs
   a hand-made change that refreshes both receipts, as this branch does.
7. **A keyless rappid stays keyless.** RAPP/1 §6.2 allows a re-anchor in
   exactly three cases: a 128→256-bit provisional upgrade, §10 key rotation or
   compromise, and a pre-rev-3 keyed tail. None makes a keyless identity keyed,
   and §10 says keyless rappids "assert location, not authorship".

The Hive agent side is already drafted:
[HIVE-MD, "Remote member spaces"](https://github.com/kody-w/rapp-model-hive/blob/16bdd71882564ecdecff374ae148042e816f8507/HIVE-MD.md#remote-member-spaces),
on `kody-w/rapp-model-hive`, branch `experimental/hive-md-distributed`, commit
`16bdd71`.

## Proposed change

### 1. One chain, from the seed to every station

A **station** is a public repository on the network. A **Hive root** is a
Hive's public copy. Everything below is read with plain static fetches of raw
URLs: no server, no API, no search.

1. **Seed** (exists). Its operator entry points `beacon_url` at a full commit
   and records the beacon's SHA-256. (The entry's `reference_state` already has
   `commit_pin` and `sha256` fields, both `null` today.)
2. **Beacon**, `rapp-network-beacon/1.1`, exactly as Articles XLVII and XLVIII
   define it. When its `estate_url` points at a full commit, an optional
   `estate_sha256` pins `estate.json`.
3. **`estate.json`** gains one optional array, `hives[]`. Each entry pins a
   Hive root the operator keeps: the public copy's commit and the hash of its
   `PUBLISHED.md` (section 5).
4. **Hive root, `PUBLISHED.md`.** Its frontmatter names the Hive (`hive:`),
   which must equal the `hives[]` entry. Its body lists `sha256  path` for
   every file, including the pointers.
5. **Pointers, `members/<station>.md`**: one per station the Hive curates, in
   the Hive's one published room (`shared/<room>/members/<station>.md` inside
   the Hive). A station that leaves is moved to `former/<station>.md`.
6. **Cards, `.rapp/member.md`**, in each station's own repository, changed by
   its own commits, with optional files under `.rapp/shared/`.
7. **Links.** A card's `links` name its neighbors and make the network a graph
   (XLVII.4). A linked repository with no pointer is an uncurated station:
   found, but not pinned.

A station joins by publishing its card with `hive:` and `hive_root:`
(Publishing IS The Signal, XLVII.1). The curator pins it by adding its pointer.
A pointer is curation, not admission, and there is no request file. Any
operator may keep a Hive root and list it in their own `estate.json`. A walk
crosses Hives through links and federation hints. It may also start at a
beacon, an estate or a Hive root (XLVII.4), and it says where it started.

### 2. Two channels: LTS and newest

- **LTS** (the default) reads each station at the full commit its pointer
  pins (`lts:`), copied from the estate kit's LTS pins. It fetches exactly the
  files the pointer lists and checks each hash. A pointer without `lts` is
  reported as not pinned and is not fetched.
- **Newest** reads the Hive root and every station at `HEAD` (or at a
  pointer's `newest:` branch) and follows links into uncurated stations.
  Nothing is pinned: hashes are recorded, and the root's files are checked
  only against the `PUBLISHED.md` read with them.

The Brainstem's Hive agent reads only pinned commits. The network tooling's
resolver reads both channels.

### 3. Integrity now, authenticity later

In a fully pinned chain, each level pins the next by hash. The seed pins the
beacon, the beacon pins `estate.json`, `hives[]` pins `PUBLISHED.md`,
`PUBLISHED.md` pins each pointer, and each pointer pins each station file at
its LTS commit. File hashes follow HIVE-MD's rule: SHA-256 of the UTF-8 text
with LF line ends, in NFC. They are file listings, not RAPP/1 §5 content
addresses. So moving the Hive root's LTS takes one new pin at each level above
it: `estate.json`, the beacon, and the seed (a RAPP pull request). Newest needs
none of them.

Hashes prove integrity only. Authenticity needs one signature at the top: the
estate owner's signed RAPP/1 §13 registry, rooted in a keyed `estate_owner`
rappid shared out of band (§13.1). How that signature covers the `hives[]` pin
is RAPP/1's to define (§10, §13). This proposal defines no signature and no
trust rule. Until then every result says `authenticity: unverified` and
nothing is accepted (Article LV.3), just as `sniff_network.py` does today.

### 4. The pointer and the card

The normative text is HIVE-MD's "Remote member spaces". In short, both files
start with a frontmatter of `key: value` and `  - item` lines only, each key
once. Readers refuse any other line, an unknown key or a missing key. Each file
is at most 64 KB of UTF-8 text under the Hive's text rules.

| Pointer key | Value |
|---|---|
| `station` | its name, the file name without `.md`: the repository name for the Hive operator's own repositories, else `<owner>.<repo>` |
| `repo`, `raw` | `owner/repo`, and the raw base it is read from, ending in `/` |
| `lts` | present exactly when `channel` is `lts`: the 40-hex commit it is read at |
| `newest` | `HEAD`, or a branch name without `/` |
| `line`, `also_on` | its subway line id; an optional sorted list of other lines |
| `channel`, `lifecycle` | `lts` or `newest`; `active`, `frozen` or `retired` |
| (body) | with `lts` only: one `sha256  path` line per file read at that commit, sorted, at most 200 |

| Card key | Value |
|---|---|
| `member`, `repo` | the repository's own name, and the `owner/repo` it is read from |
| `hive`, `hive_root` | the id of its Hive, and the raw base of that Hive's public copy |
| `what`, `line`, `channel`, `lifecycle` | what it is, in one line of at most 200 characters; the rest as in the pointer |
| `also_on`, `version`, `indexable` | optional; `indexable: false` keeps it out of network indexes |
| `links`, `shares` | optional sorted lists: its neighbors; its paths under `.rapp/shared/` |
| `rappid` | only once it exists: the `rappid` of its own `rappid.json` |

The network reads only the **readable set**: `README.md`, `rappid.json`,
`.rapp/member.md`, and `.rapp/shared/<path>` (one to four portable names, no
instruction-file name, at most 120 characters, ending in `.md`, `.json` or
`.txt`). It never reads the RAPP Workspace's private folders or bootstrap
files. A repository named like an instruction file (`agents`, `claude`,
`gemini`, `skill`, `copilot-instructions`) cannot be a station, because a Hive
refuses those file names.

A card with `indexable: false` is honored like a beacon's flag (XLVII.3): the
station is kept only as `{repo, indexable: false}`, and its links are not
followed. A card whose `hive` names another Hive is recorded but not counted.
No tool writes `rappid.json` or mints a rappid; a card's `rappid` only mirrors
one that already exists.

### 5. Two optional fields

`estate.json` may carry:

```json
"hives": [
  {
    "hive": "af02504304365b6d8b068553156b5e6d",
    "name": "rapp-hive",
    "root": "https://raw.githubusercontent.com/kody-w/rapp-hive-public/",
    "commit": "<40-hex commit of the public copy>",
    "published_sha256": "<hash of PUBLISHED.md at that commit>",
    "lts_pins": {"url": "<raw URL at a commit>", "sha256": "<64-hex>"}
  }
]
```

`lts_pins` is optional. When it is present, a reader compares each pointer's
`lts` with it and reports any difference; the pointer stays authoritative.

A beacon may carry `estate_sha256` next to a commit-pinned `estate_url`.

Both fields are optional, so today's readers are unaffected:
`sniff_network.py` ignores both.

### 6. Pulses

A walk can be announced as a RAPP/1 §7 frame of kind `body.pulse` on an
existing body stream (a body stream is a rappid, §6.1.1). Its payload carries
the walk's graph hash, its mode, the Hive id, the ref the Hive root was read
at, and the totals. `prev_wave` is `null`, and `sig` stays `null` until the
stream is keyed. The portfolio already publishes its crawls this way, on
`rapp1-network`. Which stream carries walk pulses, and whether it is keyed, is
part of D1. Until a §13 registry lists the stream's genesis and the
`body.pulse` kind, such a frame is structurally checkable only (RAPP/1 §7.5,
§13.3). Station repositories carry no frames.

### 7. Who writes what

- **Each station** writes its card and its shares, by ordinary commits.
- **The Hive root's curator** (the network lead) writes pointers by signed
  commits and publishes the public copy through an approved manifest.
- **The estate kit** writes `estate.json`, the beacon and the seed's pins.
- **Tools** read. The card generator writes only into local checkouts; it
  never commits, pushes or mints.

### 8. What this does not change

- No beacon field becomes required, and the beacon stays
  `rapp-network-beacon/1.1`.
- Article XLVIII is untouched. Nothing in the chain points into a private
  repository, the Hive root's public copy is public, and cards and pointers
  carry no private content. `estate_sha256` hashes a public file and says
  nothing about the private estate.
- The door entries of `estate.json` keep XLVI.3's shape. `hives[]` is a
  separate top-level array.
- `sniff_network.py` is unchanged until acceptance. After it, it gains at most
  an optional stage (Migration step 6).
- RAPP/1 is unchanged: no new identity form, frame kind or trust rule.
- No code in this repository, and no grail byte, changes.

### Checked against the articles it touches

- **Article XXVI.** Article I (the brainstem stays light) and Article XXV
  (chat is the only wire) are untouched. Nothing is added to the kernel, and no
  request or response changes.
- **XLVI.3, XLVI.5 and XLVI.6.** Door entries keep `{rappid, added_at, via}`,
  and XLVI.5's ban on stored derived fields applies to them. A `hives[]` entry
  derives from nothing: a Hive root has no rappid. It records the owner's
  choice of commit, and that choice, unlike a door entry, cannot be recomputed
  from the network (XLVI.6). Losing it loses only that choice; newest still
  works.
- **XLVII.1 to XLVII.5.** Publishing is still the signal. The walk is pure
  raw. Both consent flags are honored. A walk can start anywhere. Other
  substrates work through the reader's transport policy (allowed origins and
  `file://` roots, as in `sniff_network.py`).
- **LV and LVII.** Identity, frames and trust stay RAPP/1's, and protocol
  matters stay in `kody-w/rapp-1`. Cards and pointers are Hive files, not
  protocol forms.

## Owner decisions

These are this workstream's recommendations. The estate kit prepares the same
decisions for its own files. Nothing here is decided.

### D1. Station rappids: keyless or keyed (permanent)

**Recommendation: do not mint station rappids now. When a station needs its
own identity, mint it keyed.**

- The distributed Hive needs no station rappid. Integrity comes from the
  pinned hashes, and authenticity from one signature at the top (section 3).
- Keyless is a one-way door (Context, item 7): a keyless station can never
  sign its own frames, pulses or eggs.
- Keyed is recoverable. A routine key change is a `rotation` record signed by
  the old key; a lost or leaked key is a `compromise` record with a §10
  tombstone. Both are owner-signed §13.3 records, and the identity continues
  (§6.3).
- Cost: one Ed25519 key per minted station, kept by the owner and never in a
  repository, and one §13 `spki` entry each.
- Already minted, and mint-once: RAPP (keyless: its tail is the tagged upgrade
  of its legacy UUID, still waiting for the owner-signed §13.3 record),
  `rapp-work` (keyed, `owner-anchor.json`), `rapp-map`, and the portfolio's
  body stream `rapp1-network` (keyless, 2026-09-25), which can therefore never
  sign its pulses. Cards mirror existing rappids; no tool re-mints them.

**Alternative:** keyless for every station now. It is cheap and needs no key
custody, but it is permanent: those stations can never sign.

### D2. Accepting the operator in the seed

**Recommendation: accept `kody-w` only after the beacon is real and pinned.
Keep `verified: false` and `accepted: false` until then, as today.**

- Today the seed points at a status document, not a beacon, with
  `indexable: false`, and `estate.json` is a status document too. Accepting
  now would accept nothing that can be checked.
- Conditions: a `rapp-network-beacon/1.1` beacon whose `operator_rappid` is
  keyed (the §13.1 `estate_owner` anchor); the seed entry pinning that beacon
  by commit and SHA-256, which the seed's own `source_policy` already
  requires; and the signed registry that makes acceptance mean something.
- Acceptance changes fields that `cave/tests/test_catalog_containment.py`
  (lines 206–225) holds at their observation-only values, so it is its own
  RAPP pull request that changes that test on purpose.

**Alternative:** accept once the beacon is real and pinned, before the signed
registry exists. That is sooner, but acceptance would rest on a GitHub account
and a hash rather than a key, against the seed's own
`accepted_registry_required_for_trust: true` and Article LV.3.

### D3. Beacon 1.1 and `estate.json` fields

**Recommendation: beacon 1.1 exactly as Articles XLVII and XLVIII define it
(no new required field), plus an optional `estate_sha256`. `estate.json` gains
one optional array, `hives[]`.**

- Beacon: `schema: rapp-network-beacon/1.1`, a keyed `operator_rappid`, a
  commit-pinned `estate_url` (with the optional `estate_sha256`),
  `protocol.implements`, `discovery.indexable: true` (the operator wants to be
  found), `discovery.federation_hints`, and XLVIII's `private_estate_pointer`,
  `private_estate_commitment` and `private_door_count`.
- `hives[]`: `{hive, name, root, commit, published_sha256, lts_pins?}`. The
  Hive root pin has one home, the estate inventory, so the beacon stays a
  small consent-and-pointer document and XLVIII.2's rules are untouched (the
  public copy is public).
- Both additions keep today's labels, because `sniff_network.py` accepts only
  the beacon labels 1.0 and 1.1 (line 71). If the owner wants a new label for
  a new field, the beacon label and `sniff_network.py` change together.
- RAPP's historical list of beacon fields
  (`pages/docs/PUBLIC_PRIVATE_BOUNDARY.md` §4.5) does not name
  `estate_sha256`; the amendment below names both fields instead.
- The network tooling's resolver is built to read these fields and to report
  placeholders honestly until they exist.

**Alternative:** carry the Hive root pin in the beacon. That saves one fetch
and one level of pins, but the beacon turns into an inventory instead of a
small consent-and-pointer document.

### D4. Approving wave 2

**Recommendation: approve wave 2 for the repositories marked `auto`, one pull
request per repository carrying both the header and the card, paced. Keep the
held repositories for hand-made pull requests.**

- The network lead's wave-2 plan of 2026-09-25 sorts the portfolio's 302
  wave-2 repositories into 223 `auto`, 63 held for a hand-made change, and 16
  skipped. The card generator's own plan also holds a repository that pins its
  tracked path set, has anything in `.rapp/` besides the RAPP Workspace
  bootstrap files, already has a different card, is empty, or is named like an
  instruction file. So the pull requests go to the repositories that both plans
  mark `auto`: at most 223.
- The card is markdown, so `rapp_check.py` cannot turn a repository's status
  to drift because of it (Context, item 5).
- No `rappid.json` in wave 2 (D1).
- Pace: about one pull request per 5 seconds, with backoff on GitHub's
  secondary rate limits.

**Alternative:** send wave 2 with the header only and add cards in a later
wave. The pull requests are smaller now, but every repository gets a second one
later, and until then the Hive reads those stations without their cards.

## Migration

Each step is its own pull request, or one per repository where it says so, and
names the workstream that owns it. Steps 1 and 2 are drafted on experimental
branches and change nothing live.

0. **Accept** (the owner). Merge this file with its receipts, refreshed on the
   `main` of that day, because other open pull requests change the same counts.
   Record D1 to D4. The Status becomes `accepted`, and `implemented` once
   steps 1 to 5 are live.
1. **Convention and agent** (rapp-model-hive). Merge HIVE-MD's "Remote member
   spaces" and the Hive agent's remote references (`url=`, pinned to a commit)
   and `resolve`, from `experimental/hive-md-distributed`, with their tests on
   macOS, Ubuntu and Windows.
2. **Resolver and card generator** (network tooling). The resolver walks the
   chain in both channels and writes a deterministic graph. The generator
   writes cards and pointers from the portfolio and plans which repositories
   are `auto` or held. Both are tested on a synthetic Contoso network.
3. **Estate, beacon and seed** (estate kit, after D2 and D3). In
   `kody-w/rapp-estate`: a real `rapp-network-beacon/1.1` beacon and an
   `estate.json` whose `hives[]` pins the current public copy. A keyed
   `operator_rappid` needs the owner's key (D1, D2); no tool mints it. In RAPP:
   pin the seed's `beacon_url` to that commit and record its hash. Keep the
   seed's `estate_url` at `main`: `cave/tests/test_catalog_containment.py`
   (line 126) expects it, and the beacon's `estate_url` wins anyway. That pull
   request also refreshes `tests/fixtures/rapp1-doc-scope.json` and runs the
   `cave-super-rar` workflow, which watches the seed's path.
4. **Cards** (network lead, after D1 and D4). Add `.rapp/member.md` through
   the existing `rapp1/network-header` pull request branches (RAPP's own is
   pull request #120), then wave 2, one pull request per repository. Held
   repositories get hand-made pull requests. RAPP is one of them: its card
   changes RAPP's path set and adds a tracked document, so its pull request also
   refreshes both receipts and gives `.rapp/member.md` a disposition in the
   documentation scope.
5. **Pointers and publish** (network lead). With the estate kit's LTS pins,
   write `members/<station>.md` into the Hive's published room by signed
   commits, approve the manifest, and publish the public copy. Then the estate
   kit re-pins `hives[]`, and the beacon and seed pins above it, to the new
   public copy.
6. **Optional `sniff_network.py` stage** (network tooling, a RAPP pull request,
   after acceptance). When an estate has `hives[]`, record each entry, and
   optionally fetch its `PUBLISHED.md` and check the hash. Keep everything else:
   offline by default, `--online` only with a reviewed binding, the transport
   policy, no redirects, and `accepted: false`. Add tests. The file is the
   `network-sniffer` record of `HISTORICAL_SOURCE_LEDGER.json`, which pins its
   latest commit and bytes, so the pull request also regenerates the ledger
   (`tools/build_historical_source_ledger.py --write`) after its last commit,
   keeps every historical symbol, and refreshes the byte receipt.
7. **Constitution amendment** (this workstream drafts; the owner merges by
   hand, XXX.2). Add XLVII.6 below, citing this proposal (XXVIII.6).

## Rollback

- **Before acceptance:** delete this branch. Nothing else changes.
- **Step 1:** revert the merge in `kody-w/rapp-model-hive`. Remote references
  are device-local pins (`.git/rapp-hive/references.json`, never committed)
  with a device cache (`.git/rapp-hive/remote/`): unpin them and delete the
  cache. `resolve` commits nothing.
- **Step 2:** stop running the tools. They write only to local folders.
- **Step 3:** remove `hives[]` from `estate.json`, and readers are back to
  today: they stop at the estate. `estate_sha256` is optional, so a beacon
  without it stays valid. The seed pin can go back to the moving URL,
  observation-only as today.
- **Step 4:** a card is inert markdown. Nothing runs it, and `rapp_check.py`
  does not read it. Close the pull request, or delete `.rapp/member.md` with an
  ordinary commit.
- **Step 5:** move a pointer to `former/<station>.md` by a signed commit and
  publish again, or re-pin `hives[]` to an earlier public-copy commit, which
  still exists. A publication cannot be recalled from anyone who already copied
  it, so only public data is ever published.
- **Step 6:** revert the pull request and regenerate the ledger and receipts in
  the same revert.
- **Step 7:** revert the amendment pull request. Its text is additive.

## Proposed amendment text

For the pull request of Migration step 7, and only after acceptance. Nothing on
this branch edits `CONSTITUTION.md`.

**Where.** After XLVII.5.3 and before Article XLVII's closing "What this
article requires" list (lines 3672 and 3674). Article XLVII lies inside the
RAPP1 historical section (the markers at lines 10 and 4011), while Articles LVI
and LVII sit after Article LV. The owner may prefer a new article after LVII,
with a one-line pointer in XLVII; the text stays the same apart from its
heading.

> #### XLVII.6 — The Network Is One Distributed Hive
>
> **Amendment (date of merge) — additive per Article XXVI; proposal 0020.**
>
> **Every station keeps its own member space in its own repository; a Hive
> root pins the stations; plain raw fetches read the whole network.** A
> *station* is a public repository on the network. Its member space is its
> card, `.rapp/member.md`, and the files its card lists under `.rapp/shared/`,
> changed only by its own commits. A *Hive root* is a Hive's public copy. Its
> `PUBLISHED.md` lists every file with its SHA-256, including one pointer,
> `members/<station>.md`, per station the Hive curates. The card, the pointer
> and the files the network may read are defined by the "Remote member spaces"
> section of HIVE-MD in `kody-w/rapp-model-hive`, at the commit the amendment
> pull request names.
>
> The chain extends XLVII.1 and XLVII.2: seed → beacon → `estate.json`
> `hives[]` → the Hive root's `PUBLISHED.md` → pointers → cards → their
> `links`.
>
> - `estate.json` MAY carry `hives[]`. Each entry is
>   `{hive, name, root, commit, published_sha256}`, optionally with
>   `lts_pins: {url, sha256}`: `root` is the raw base of the public copy,
>   `commit` its full 40-hex commit, and `published_sha256` the hash of its
>   `PUBLISHED.md` at that commit. Door entries keep XLVI.3's shape.
> - A `rapp-network-beacon/1.1` beacon MAY carry `estate_sha256` next to an
>   `estate_url` pinned to a full commit. No beacon field becomes required.
> - **LTS** reads each curated station at the full commit its pointer pins and
>   checks every file against the pointer's hash. **Newest** reads `HEAD` and
>   marks every file unpinned.
> - A station joins by publishing its card (XLVII.1). A pointer pins a station;
>   it does not admit it. Any operator may keep Hive roots. Walks cross Hives
>   through links and federation hints and may start at any node (XLVII.4).
> - A card's `indexable: false` is honored like the beacon's (XLVII.3).
> - Hashes give integrity. Authenticity comes only from the estate owner's
>   signed RAPP/1 §13 registry. Until it exists, every result is unverified and
>   nothing is accepted (Article LV.3).
> - Identity, frames and signatures are RAPP/1's. No tool mints a rappid for a
>   station. A walk's pulse is a RAPP/1 §7 `body.pulse` frame on an existing
>   body stream.
>
> **This subsection requires:**
> - Readers fetch only through an index (`PUBLISHED.md`, a pointer, a card),
>   never by listing a folder, never following a redirect, and only from
>   origins their transport policy allows.
> - Readers never fetch `.rapp/cache/`, `.rapp/workspace/`, `.rapp/reports/` or
>   the RAPP Workspace bootstrap files.
> - LTS readers report every hash mismatch, missing file and refused file.
>
> **This subsection forbids:**
> - Station pointers in a Hive's own `members/`, which holds people.
> - Treating a pointer, a card or a matching hash as authenticated acceptance.
> - Private-estate content in any card, pointer or public copy (XLVIII.5).
>
> **Why this is constitutional and not a feature:** without it, the map of the
> network lives in one place and the discovery chain stops at the estate. With
> it, each repository publishes its own place on the network, the curator pins
> what it has checked, and anyone can read and check the whole network from the
> seed with plain raw fetches: no registry, and no trust in the raw server
> beyond the hashes.

## References

- [`CONSTITUTION.md`](../../CONSTITUTION.md): Article I, Article XXV,
  Article XXVI, Article XXVIII (.3, .4, .6), Article XXX.2, Article XLVI (.3,
  .5, .6), Article XLVII (.1 to .5, and .5.3 for placement), Article XLVIII
  (.1, .2, .5, .6), Article LV (.2, .3) and Article LVII.
- RAPP/1 rev-5, pinned by [`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json):
  [`kody-w/rapp-1` `SPEC.md` at `d2cd5ab`](https://github.com/kody-w/rapp-1/blob/d2cd5abed48d3f52b86bbb975ac3558286d1db41/SPEC.md),
  §5, §6.1.1, §6.2, §6.3, §7.1, §7.2, §7.4, §7.5, §10, §13.1 and §13.3.
  Status: [`RAPP1_STATUS.md`](../../RAPP1_STATUS.md).
- This repository: `.well-known/rapp-network-seed.json` lines 2–43;
  `tools/sniff_network.py` lines 71, 815, 921, 992, 1015, 1036, 1106–1111 and
  1131–1135; `HISTORICAL_SOURCE_LEDGER.json` (`network-sniffer`);
  `cave/tests/test_catalog_containment.py` lines 126 and 206–225;
  `.github/workflows/cave-super-rar.yml`; `RAPP1_ADAPTATION_INVENTORY.json`;
  `tests/fixtures/rapp1-doc-scope.json`;
  `pages/docs/PUBLIC_PRIVATE_BOUNDARY.md` §4.5.
- The Hive convention:
  [HIVE-MD at `16bdd71`, "Remote member spaces"](https://github.com/kody-w/rapp-model-hive/blob/16bdd71882564ecdecff374ae148042e816f8507/HIVE-MD.md#remote-member-spaces)
  (`kody-w/rapp-model-hive`, branch `experimental/hive-md-distributed`).
- The RAPP Hive's public copy at `a8f4cd8`:
  [`PUBLISHED.md`](https://github.com/kody-w/rapp-hive-public/blob/a8f4cd86f6248d07f98ce2c38d1a3c0f97307a31/PUBLISHED.md),
  [`portfolio/PORTFOLIO.md`](https://github.com/kody-w/rapp-hive-public/blob/a8f4cd86f6248d07f98ce2c38d1a3c0f97307a31/portfolio/PORTFOLIO.md),
  [the subway map](https://kody-w.github.io/rapp-hive-public/portfolio/subway.html),
  [`portfolio/rappid.json`](https://kody-w.github.io/rapp-hive-public/portfolio/rappid.json).
- The placeholders in `kody-w/rapp-estate` at `acc17dc`:
  [`.well-known/rapp-network.json`](https://github.com/kody-w/rapp-estate/blob/acc17dca283619f288274f237c8c61f437d014f3/.well-known/rapp-network.json)
  and
  [`estate.json`](https://github.com/kody-w/rapp-estate/blob/acc17dca283619f288274f237c8c61f437d014f3/estate.json).
- rapp-1's checker:
  [`rapp_check.py` at `591e014`](https://github.com/kody-w/rapp-1/blob/591e014ad39e223b00ab343ae26e5d9a867ebeee/rapp_check.py),
  lines 73, 169–178 and 575–576.
- `.rapp/` today: [RAR's `.rapp/`](https://github.com/kody-w/RAR/tree/ecf5f52312cf083eaedf5e0aa8782debc7f0af4b/.rapp)
  and
  [`kody-w/rapp-tools` `rapp_workspace.py` line 88 at `b0e37eb`](https://github.com/kody-w/rapp-tools/blob/b0e37eb3c67e309f342629e0ec96dea2688a5951/rapp_workspace.py#L88).
- Related pull requests: #119 (proposal 0001), #120 (RAPP's network header)
  and #121 (proposal 0003).
