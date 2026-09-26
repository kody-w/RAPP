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
governs until the owner merges it, himself or on his authorization (Articles
XXVIII.4 and XXX.2).

The draft lives on the branch `experimental/proposal-0020-distributed-hive`,
and the AI assistant opened pull request #133 from it. The AI merges nothing:
merging that pull request is the owner's acceptance. Besides this file, the pull
request refreshes only the two receipts that count tracked files
(`RAPP1_ADAPTATION_INVENTORY.json` and `tests/fixtures/rapp1-doc-scope.json`).
It does not edit `CONSTITUTION.md`. The amendment text near the end is for a
later pull request, after acceptance (Article XXVIII.6).

**Numbering.** This workstream numbers its drafts from 0020, and the other
drafts use 0001 to 0019: 0001 merged as pull request #119, 0002 is on the
branch `experimental/proposal-0002-tier2-parity`, and 0003 is pull request
#121. Article XXVIII.3 asks for monotonic numbers, so if this merges before the
lower numbers are used, the owner may renumber it first. HIVE-MD's "Remote
member spaces" and `DISTRIBUTED-HIVE.md` already cite it as RAPP proposal 0020.

Line numbers are for `main` at commit `e045fc3`. The files they point into are
the same at `8afc973`, where this draft began, except `CONSTITUTION.md`, whose
placement lines moved down by five with proposal 0001's amendment. This branch
changes none of them.

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
  `acc17dc` of 2026-08-26, still `main` on 2026-09-26),
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
  one file per public RAPP repository, 317 today, in 18 lines, 316 of them
  with a RAPP/1 status earned from rapp-1's own checker and one not yet
  checked;
- the **subway map** drawn from those files
  (<https://kody-w.github.io/rapp-hive-public/portfolio/subway.html>);
- one RAPP/1 §7 `body.pulse` frame per crawl, on the body stream
  `rappid:@kody-w/rapp1-network:71216534…`, a keyless rappid minted on
  2026-09-25
  ([`portfolio/rappid.json`](https://kody-w.github.io/rapp-hive-public/portfolio/rappid.json)).
  The first frame,
  [`portfolio/versions/2026-09-25-0/pulse.json`](https://kody-w.github.io/rapp-hive-public/portfolio/versions/2026-09-25-0/pulse.json),
  has `seq` 0 and `sig: null`.

The public copy has moved on since `a8f4cd8`. From `b684d17` (2026-09-26, 1,098
files) its `PUBLISHED.md` also lists 317 station pointers in the contract's
version 2: 4 pinned at an LTS commit (`rapp-1`, `rapp-installer`, `rapp-map`
and `rapp-work`) and 313 on the newest channel. They were published before this
proposal's acceptance, as Hive files under the Hive's own rules. No
`estate.json` on `main` pins that copy, so no walk from the live seed reaches
them; a walk started at the root does, and the network tooling's resolver reads
all 317 and checks the 4 LTS stations' files against their pointers' hashes. At
`HEAD` it also reads the 11 station cards merged on 2026-09-26 (Migration
step 4).

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

The convention and the Hive agent side are already drafted, on
`kody-w/rapp-model-hive`, branch `experimental/hive-md-distributed`, commit
`e322226`:
[`DISTRIBUTED-HIVE.md`](https://github.com/kody-w/rapp-model-hive/blob/e3222268bf751dadc61bbf25c698bc592af346cc/DISTRIBUTED-HIVE.md),
the single source of truth for everything below, and
[HIVE-MD, "Remote member spaces"](https://github.com/kody-w/rapp-model-hive/blob/e3222268bf751dadc61bbf25c698bc592af346cc/HIVE-MD.md#remote-member-spaces),
what the Hive agent does with it.

### RAPP/1 is drafting the same idea from the other side

The rev-17 draft of RAPP/1 (experimental, not in force: `kody-w/rapp-1`,
branch `experimental/rapp1-core-rev17`, commit `65a35c1`) adds three
owner-signed registry entries. A `release-pin` names a release manifest that
pins every component file of one release by SHA-256 and length at an immutable
commit, and binds each organism's door of record (§13.5); a component may have
no rappid. A `lifecycle` entry says a subject is `active`, `deprecated`,
`superseded` or `archived`, where the subject is an organism's rappid or, for a
repository with no rappid of its own, its HTTPS URI (§13.6). A `stream-signer`
entry grants a keyed signer the right to sign given kinds on one stream
(§13.7). It also says that seeds, beacons, estate catalogs,
Hive indexes and member pointers are locators: content is verified only when a
manifest pins it, and a locator that disagrees with it is drift. This proposal
is that locator layer. It uses the same lifecycle words, hashes station files
the way a release manifest does, and never presents its own results as
verified by a registry.

## Proposed change

### 1. One chain, from the seed to every station

A **station** is a public repository on the network. A **Hive root** is a
Hive's public copy. Everything below is read with plain static fetches of raw
URLs: no server, no API, no search.

1. **Seed** (exists). Migration step 3 points its operator entry's
   `beacon_url` at a full commit and records the beacon's SHA-256. (The entry's
   `reference_state` already has `commit_pin` and `sha256` fields, both `null`
   today.) Readers read only its `operators[]`, as `sniff_network.py` does.
2. **Beacon**, `rapp-network-beacon/1.1`, exactly as Articles XLVII and XLVIII
   define it, with its `estate_url` at a full commit.
3. **`estate.json`** gains one optional array, `hives[]`. Each entry pins a
   Hive root the operator keeps: the public copy's commit and the hash of its
   `PUBLISHED.md` (section 6).
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

- **LTS**, the channel `rapp1-lts` and the default, reads each station at the
  full commit its pointer pins (`lts:`), copied from the estate's LTS pins. It
  fetches exactly the files the pointer lists and checks each hash. A pointer
  without `lts` is reported as not pinned and is not fetched.
- **Newest** reads the Hive root and every station at `HEAD` (or at a
  pointer's `newest:` branch) and follows links into uncurated stations.
  Nothing is pinned: hashes are recorded, and the root's files are checked
  only against the `PUBLISHED.md` read with them.

The Brainstem's Hive agent reads only pinned commits. The network tooling's
resolver reads both channels.

### 3. Integrity now, authenticity later

In a fully pinned chain, the seed pins the beacon by commit and SHA-256, the
beacon names `estate.json` at a full commit, `hives[]` pins `PUBLISHED.md` by
commit and hash, `PUBLISHED.md` pins each pointer, and each pointer pins each
station file at its LTS commit. Readers check hashes from `hives[]` down. Above
it they record each URL, whether it is pinned (it has a 40-hex commit part) and
the SHA-256 of the bytes they read, and check nothing. `sniff_network.py` also
checks nothing there today, but it records the SHA-256 of the parsed JSON
(`parsed_payload_sha256`), not of the bytes, and no pin state. A station file must
be normalized text (UTF-8, LF line ends, NFC), and its hash is the SHA-256 of
its bytes: the value HIVE-MD's rule gives, `sha256sum` prints, and a RAPP/1
release manifest pins. These are file listings, not RAPP/1 §5 content
addresses. So moving the Hive root's LTS takes one new pin at each level above
it: `estate.json`, the beacon, and the seed (a RAPP pull request). Newest needs
none of them.

Hashes prove integrity only. Authenticity needs one signature at the top: the
estate owner's signed RAPP/1 §13 registry, rooted in a keyed `estate_owner`
rappid shared out of band (§13.1). The kody-w estate's registry exists and is
signed (`kody-w/rapp-map` `ecosystem-spec.json`, `registry_seq` 2), but no entry
in it covers this chain. RAPP's `RAPP1_STATUS.md` and `specs/ecosystem-spec.json`
predate it and still describe that path as quarantined; this proposal closes
neither. How a signed entry covers the `hives[]` pin is
RAPP/1's to define (§10, §13; the rev-17 draft's release pins are one way).
This proposal defines no signature and no trust rule. Until a verified entry
covers the chain, every result says `authenticity: unverified` and nothing is
accepted (Article LV.3), just as `sniff_network.py` does today.

### 4. The pointer and the card

The normative text is `DISTRIBUTED-HIVE.md` (sections 6 to 9). In short, both
files start with a frontmatter of `key: value` and `  - item` lines only, each
key once. Readers refuse any other line, an unknown key or a missing required
key. Each
file is at most 64 KB of UTF-8 text under the Hive's text rules.

| Pointer key | Value |
|---|---|
| `station` | its name, the file name without `.md`: the repository name for the Hive operator's own repositories, else `<owner>.<repo>` |
| `repo`, `raw` | `owner/repo`, and the raw base it is read from, ending in `/` with the repo's owner and name |
| `lts` | present exactly when `channel` is `rapp1-lts`: the 40-hex commit it is read at |
| `newest` | `HEAD`, or a branch name without `/` |
| `line`, `also_on` | its subway line id; an optional sorted list of other lines |
| `channel` | `rapp1-lts` or `newest` |
| `lifecycle`, `superseded_by` | `active`, `deprecated`, `superseded` or `archived`; the successor's `owner/repo`, required with `superseded` |
| (body) | with `lts` only: one `sha256  path` line per file read at that commit, sorted, at most 200 |

| Card key | Value |
|---|---|
| `member`, `repo` | the repository's own name, and the `owner/repo` it is read from |
| `hive`, `hive_root` | the id of its Hive, and the raw base of that Hive's public copy |
| `what`, `line` | what it is, in one line of at most 200 characters; its subway line id |
| `also_on`, `version`, `channel`, `lifecycle`, `superseded_by`, `indexable` | optional; `channel`, `lifecycle` and `superseded_by` as in the pointer (`superseded_by` only with a `lifecycle` that allows it); the generator writes a `lifecycle` only when it is not `active`, and never a `channel` or `version`; `indexable: false` keeps it out of network indexes |
| `links`, `shares` | optional sorted lists: its neighbors; its paths under `.rapp/shared/` |
| `rappid` | only once it exists: the `rappid` of its own `rappid.json` |

The network reads only the **readable set**: `README.md`, `rappid.json`,
`.rapp/member.md`, and `.rapp/shared/<path>` (one to four portable names, no
instruction-file name, at most 120 characters, ending in `.md`, `.json` or
`.txt`). It never reads the RAPP Workspace's private folders or bootstrap
files. A repository named like an instruction file (`agents`, `claude`,
`claude.local`, `gemini`, `skill`, `copilot-instructions`) cannot be a station,
because a Hive refuses those file names.

A card with `indexable: false` is honored like a beacon's flag (XLVII.3): the
station is kept only as `{repo, indexable: false}`, and its links are not
followed. A card whose `hive` names another Hive is recorded but not counted.
No network tool (the resolver, the card generator, the Hive agent) writes
`rappid.json` or mints a rappid; a card's `rappid` only mirrors
one that already exists.

The lifecycle words are the rev-17 draft's (§13.6) and the portfolio's. A
pointer's or a card's lifecycle is a copy, reported as unverified: the
authority would be a signed `lifecycle` entry whose subject is the station's
rappid or, without one, its repository URI, and none is signed yet. A
`superseded_by` is an edge of the graph, so a walk finds the successor.

### 5. RAPP/1 release pins (the rev-17 draft)

If the rev-17 draft is accepted, the estate's LTS release manifest pins every
component of RAPP/1 LTS, and the stations and the Hive root among them. Then
the manifest is the authority and the Hive's files are locators: a reader that
is given the manifest checks every pinned file by length and SHA-256, and
reports a pointer or a Hive root that disagrees with it as drift
(`DISTRIBUTED-HIVE.md` section 11.4). The network tooling's resolver already
does this as a rehearsal of §13.5 steps 2 and 3. Step 1, verifying the signed
registry, stays with RAPP/1's reference implementation, so such a result is
still unverified. On 2026-09-26 it checked the estate kit's prepared and
unsigned LTS candidates this way, each named by its `manifest_hash`: every file
each one pins matched, and it reported as drift each Hive pointer that did not
yet carry the candidate's pin, most of the 317, which are still on the newest
channel. Nothing in this proposal depends on rev-17: without it, the pointers
carry the LTS commits.

### 6. One optional array

`estate.json` may carry `hives[]`. Each entry has exactly five members:

```json
"hives": [
  {
    "hive": "af02504304365b6d8b068553156b5e6d",
    "name": "rapp-hive",
    "root": "https://raw.githubusercontent.com/kody-w/rapp-hive-public/",
    "commit": "<40-hex commit of the public copy>",
    "published_sha256": "<HIVE-MD hash of PUBLISHED.md at that commit>"
  }
]
```

An entry with another member, or one of the wrong shape, is skipped with a
finding. The array is optional, so today's readers are unaffected:
`sniff_network.py` only counts `estate.json`'s `created` and `member`
entries.

### 7. Pulses

A walk can be announced as a RAPP/1 §7 frame of kind `body.pulse` on an
existing body stream (a body stream is a rappid, §6.1.1). A stream has one
writer, or it forks (§7.6). So the resolver prints the walk's fragment (its
graph hash, mode, Hive ids and refs, and totals) for the stream's owner to put
in the owner's own pulse, and builds a frame only for a stream its caller owns.
The portfolio already publishes its crawls this way, on `rapp1-network`, with
`sig: null`. An unsigned pulse is a valid frame whose chain proves integrity
only; it does not speak for the estate. The estate's published registry
(`kody-w/rapp-map` `ecosystem-spec.json`, `registry_seq` 2) registers the
`body.pulse` kind but no genesis for `rapp1-network`, so until that genesis is
registered such a frame is structurally checkable only (RAPP/1 §7.5, §7.6,
§13.3). Under the rev-17 draft (§13.7), a frame on a keyless stream such as
`rapp1-network` speaks for the estate when the estate owner signs it, or when a
`stream-signer` entry grants its keyed signer that stream and kind. Station
repositories carry no frames.

### 8. Who writes what

- **Each station** writes its card and its shares, by ordinary commits.
- **The Hive root's curator** (the network lead) writes pointers by signed
  commits and publishes the public copy through an approved manifest.
- **The estate kit** writes `estate.json`, the beacon and the seed's pins.
- **Tools** read. The card generator writes only into local checkouts; it
  never commits, pushes or mints.

### 9. What this does not change

- No beacon field is added or becomes required, and the beacon stays
  `rapp-network-beacon/1.1`. The chain needs no new seed field either: a
  reader reads only an operator entry's handle, `beacon_url` and `estate_url`,
  and ignores its other members, such as a record of the moving URL a pin
  replaced.
- Article XLVIII is untouched. Nothing in the chain points into a private
  repository, the Hive root's public copy is public, and cards and pointers
  carry no private content.
- The door entries of `estate.json` keep XLVI.3's shape. `hives[]` is a
  separate top-level array.
- `sniff_network.py` is unchanged until acceptance. After it, it gains at most
  an optional stage (Migration step 6).
- RAPP/1 is unchanged: no new identity form, frame kind or trust rule. The
  lifecycle words and the release-manifest check follow the rev-17 draft
  without depending on it.
- This branch changes no code. After acceptance only Migration step 3 (a
  containment test that holds the seed's pin), step 6 (`tools/sniff_network.py`
  and its tests) and D2's own acceptance pull request
  (`cave/tests/test_catalog_containment.py`, on purpose) may change code here,
  and no step changes a grail byte.

### Checked against the articles it touches

- **Article XXVI.** Article I (the brainstem stays light) and Article XXV
  (chat is the only wire) are untouched. Nothing is added to the kernel, and no
  request or response changes.
- **XLVI.3, XLVI.5 and XLVI.6.** Door entries keep `{rappid, added_at, via}`,
  and XLVI.5's ban on stored derived fields applies to them. A `hives[]` entry
  derives from nothing: a Hive root has no rappid. It records the owner's
  choice of Hive root and commit, which, unlike a door entry, cannot be
  recomputed from the network (XLVI.6): an estate rebuilt from the network has
  no `hives[]`, and once it is published and the beacon and seed are re-pinned
  to it, a walk from the seed stops at the estate in both channels, as today
  (Rollback, step 3). A walk started at the Hive root (XLVII.4) still works.
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

**Recommendation: mint no station rappid in wave 2, and decide once the owner
has decided the rev-17 draft. If rev-17 is accepted, mint keyless rappids for
the stations that need a RAPP/1 identity, and a keyed one only for a station
that must sign as itself.**

- The distributed Hive needs no station rappid. Integrity comes from the
  pinned hashes, and authenticity from one signature at the top (section 3).
- Under the rev-17 draft a station needs no rappid to be released or given a
  lifecycle: a release component may have `rappid: null`, and a lifecycle
  entry may name a repository by its URI (§13.5, §13.6). It needs one only for
  a door of record, or for streams of its own. A keyless rappid serves both:
  the estate owner signs the release pin, and a `stream-signer` entry lets a
  keyed signer speak on its streams without re-minting it (§13.7).
- Keyless is still a one-way door (Context, item 7): a keyless station never
  signs as itself. If one later must, the path is a new keyed rappid and a
  `superseded` lifecycle entry that names it (rev-17 §13.6), not a re-anchor.
- Keyed is recoverable. A routine key change is a `rotation` record signed by
  the old key; a lost or leaked key is a `compromise` record with a §10
  tombstone (§6.3). But each keyed station costs one Ed25519 key, kept by the
  owner and never in a repository, and one §13 `spki` entry: about 300 keys for
  the whole portfolio.
- Already minted, and mint-once: 30 stations carry a `rappid.json` whose
  rappid is a door of the estate kit's draft `estate.json` (`bb2b9ce`), among
  them RAPP (keyless: its tail is the tagged upgrade of its legacy UUID, still
  waiting for the owner-signed §13.3 record), `rapp-work` (keyed,
  `owner-anchor.json`) and `rapp-map`; and so does the portfolio's body stream
  `rapp1-network` (keyless, 2026-09-25). That stream never signs as
  itself, but its frames can still carry a registered key's signature (§10),
  and the rev-17 draft adds the entry that says which key speaks for it. Cards
  mirror existing rappids; no tool re-mints them.

**Alternatives:** keyed for every station now, so each can sign as itself, at
the cost of about 300 keys in the owner's custody, where a station already
minted keyless takes a new keyed rappid and a `superseded` entry; or keyless for
every station now, which is cheap and permanent, and before rev-17 names only a
location.

### D2. Accepting the operator in the seed

**Recommendation: accept `kody-w` only after the beacon is real and pinned and
a verified entry of the estate's signed registry covers it. Keep
`verified: false` and `accepted: false` until then, as today.**

- Today the seed points at a status document, not a beacon, with
  `indexable: false`, and `estate.json` is a status document too. Accepting
  now would accept nothing that can be checked.
- Conditions: a `rapp-network-beacon/1.1` beacon whose `operator_rappid` is
  keyed (the §13.1 `estate_owner` anchor); the seed entry pinning that beacon
  by commit and SHA-256, which the seed's own `source_policy` already
  requires; and a verified registry entry that covers that beacon or its pins.
  The estate's signed registry exists, at `registry_seq` 2, but covers neither;
  RAPP/1 defines how, and the rev-17 draft's release pins are one way.
- Acceptance changes fields that `cave/tests/test_catalog_containment.py`
  (lines 206–225) holds at their observation-only values, so it is its own
  RAPP pull request that changes that test on purpose. The estate kit drafts
  it, owner-gated, on RAPP's `experimental/rapp1-network-seed-acceptance`
  (`ec59b24`).

**Alternative:** accept once the beacon is real and pinned, before the estate's
signed registry covers it. That is sooner, but acceptance would rest on a GitHub account
and a hash rather than a key, against the seed's own
`accepted_registry_required_for_trust: true` and Article LV.3.

### D3. Beacon 1.1 and `estate.json` fields

**Recommendation: beacon 1.1 exactly as Articles XLVII and XLVIII define it,
with no new field. `estate.json` gains one optional array, `hives[]`, of
five-member entries.**

- Beacon: `schema: rapp-network-beacon/1.1`, a keyed `operator_rappid`, a
  commit-pinned `estate_url`, `protocol.implements`, `discovery.indexable:
  true` (the operator wants to be found), `discovery.federation_hints`, and
  XLVIII's `private_estate_pointer`, `private_estate_commitment` and
  `private_door_count`: the fields the historical beacon list in
  `pages/docs/PUBLIC_PRIVATE_BOUNDARY.md` §4.5 already names.
- `hives[]`: exactly `{hive, name, root, commit, published_sha256}`. The Hive
  root pin has one home, the estate inventory, so the beacon stays a small
  consent-and-pointer document and XLVIII.2's rules are untouched (the public
  copy is public).
- No hash is added above the root. The seed entry already has
  `reference_state.commit_pin` and `sha256` for the beacon, and pinning the
  upper chain is the estate kit's. Readers check hashes from `hives[]` down.
- The estate kit drafts the beacon, `estate.json` and the seed's pins; the
  network tooling's resolver already reads them and reports today's
  placeholders honestly.

**Alternatives:** carry the Hive root pin in the beacon, which saves one fetch
and one level of pins but turns the beacon into an inventory; or add an
`estate_sha256` next to the beacon's `estate_url`, which pins one more level by
hash but adds a beacon field that the §4.5 list does not name and that the
signed registry will make unneeded.

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

Each step is one pull request, as Article XXVIII.3 asks, except where it says
otherwise: a step that spans repositories takes one per repository, and the
Hive's own changes are signed commits under its rules. Each names the
workstream that owns it. Steps 1 to 3 are drafted on experimental
branches and change nothing live (step 3 by the estate kit, on `kody-w/rapp-estate`
`experimental/rapp1-distributed-hive` and RAPP
`experimental/rapp1-network-seed-acceptance`). Steps 4 and 5 have begun
(Context).

0. **Accept** (the owner). Merge this file with its receipts, refreshed on the
   `main` of that day, because other open pull requests change the same counts.
   Record D1 to D4. The Status becomes `accepted`, and `implemented` once
   steps 1 to 5 are live and the step-7 amendment has merged (step 6 is
   optional).
1. **Convention and agent** (rapp-model-hive). Merge `DISTRIBUTED-HIVE.md`,
   HIVE-MD's "Remote member spaces" and the Hive agent's remote references
   (`url=` pinned to a commit, with an optional `sha256=` anchor) and
   `resolve`, from `experimental/hive-md-distributed`, with their tests on
   macOS, Ubuntu and Windows.
2. **Resolver and card generator** (network tooling, kept in a private
   repository until it graduates). The resolver walks the chain in both
   channels, checks a release manifest when one is given, and writes a
   deterministic graph and snapshot. The generator writes cards and pointers
   from the portfolio and plans which repositories are `auto` or held. Both are
   tested on a synthetic Contoso network.
3. **Estate, beacon and seed** (estate kit, after D2 and D3). In
   `kody-w/rapp-estate`: a real `rapp-network-beacon/1.1` beacon and an
   `estate.json` whose `hives[]` pins the current public copy. Its keyed
   `operator_rappid` is the estate owner's existing `estate_owner` rappid
   (`rappid:@kody-w/estate-owner:b5814e45…`, in the published registry); no tool
   mints one. In RAPP:
   pin the seed's `beacon_url` to that commit and record its hash. Keep the
   seed's `estate_url` at `main`: `cave/tests/test_catalog_containment.py`
   (line 126) expects it, and the beacon's `estate_url` wins anyway. That pull
   request also adds a containment test that holds the pin, refreshes
   `tests/fixtures/rapp1-doc-scope.json` and runs the `cave-super-rar`
   workflow, which watches the seed's path. On 2026-09-26 the drafts read end
   to end: a walk from RAPP's draft seed (`ceb7115`, which pins the beacon, or
   `ec59b24` after it, which adds D2's owner-gated acceptance record) reads the
   draft beacon
   (`6747768`), the `estate.json` it pins (`bb2b9ce`) and the Hive root that
   `estate.json` pins (`eafa6de`), anchored by its `published_sha256`, with
   all 317 pointers.
4. **Cards** (network lead; wave 2 after D1 and D4). The wave-1
   `rapp1/network-header` pull requests merged on 2026-09-26 (RAPP's own, #120,
   as `1feed67`); only `kody-w/rapp-installer` #48 is still open. Cards for
   11 of the 15 wave-1 stations followed the same day, each its own pull
   request under the card schema (`DISTRIBUTED-HIVE.md` section 8): 8 made
   with the card generator's `card` command (section 18), for `RAR`,
   `rapp-1`, `rapp-model-hive`, `hive-hub-mcp`, `hive-hub-join`,
   `rapp-hive-hub-join`, `rapp-drift-lint` and `lisppy`, and 3 made by hand
   because those repositories pin their tracked path sets, for `rapp-work`,
   `hive-hub` and `rapp-hive-hub`. RAPP's own card is pull request #132,
   stacked on #131, a writer for its two receipts; `rapp-installer`'s waits
   with #48, and `rapp-workspace` (whose header is
   held) and `rapp-hive-public` have none yet. Then wave 2, one pull request
   per repository. Held repositories get hand-made pull requests. RAPP is one of
   them: its card changes RAPP's path set and adds a tracked document, so its
   pull request also refreshes both receipts and gives `.rapp/member.md` a
   disposition in the documentation scope.
5. **Pointers and publish** (network lead). The 317 pointers in the
   contract's version 2 are published (from `b684d17`, 4 with `lts`). With the
   estate kit's LTS pins,
   move each pinned station to `rapp1-lts` in the portfolio and add its `lts`
   by signed commits (the generator refuses a pin whose portfolio channel says
   `newest`), approve the manifest, and publish the public copy. Then the
   estate kit pins `hives[]`, and the beacon and seed pins above it, to that
   copy.
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

- **Before acceptance:** close the pull request and delete this branch. The
  cards and pointers already published stay until they are undone as in
  steps 4 and 5.
- **After acceptance, before the amendment:** a later proposal can supersede
  this one (Article XXVIII.3), and the amendment text is then never proposed.
- **Step 1:** revert the merge in `kody-w/rapp-model-hive`. Remote references
  are device-local pins (`.git/rapp-hive/references.json`, never committed)
  with a device cache (`.git/rapp-hive/remote/`): unpin them and delete the
  cache. `resolve` commits nothing.
- **Step 2:** stop running the tools. They write only to local folders.
- **Step 3:** publish an `estate.json` without `hives[]` and a beacon whose
  `estate_url` names it, then move the seed's pin to that beacon, or back to
  the moving URL, observation-only as today (a RAPP pull request). Only then
  are readers back to today: they stop at the estate. Until the seed's pin
  moves, a walk from the seed still reads the pinned beacon, the pinned
  `estate.json` and its `hives[]`.
- **Step 4:** a card is inert markdown. Nothing runs it, and `rapp_check.py`
  does not read it. Close the pull request, or delete `.rapp/member.md` with an
  ordinary commit.
- **Step 5:** move a pointer to `former/<station>.md` by a signed commit and
  publish again, or choose an earlier public-copy commit, which still exists.
  Newest readers see the change at once; LTS readers only once `hives[]`, and
  the beacon and seed pins above it, are re-pinned to that commit (section 3).
  A publication cannot be recalled from anyone who already copied it, so only
  public data is ever published.
- **Step 6:** revert the pull request and regenerate the ledger and receipts in
  the same revert.
- **Step 7:** do not delete the text. A later amendment, proposed like this
  one, marks the new rule superseded, and its wording stays, as Article XXVI's
  additive-only practice requires (see the 2026-07-08 note in Article XLVI).

## Proposed amendment text

For the pull request of Migration step 7, and only after acceptance. Nothing on
this branch edits `CONSTITUTION.md`.

**Where.** As a new section at the end of `CONSTITUTION.md`, after Article LVII
and proposal 0001's amendment (pull request #124, merged as `e045fc3`), with a
one-line pointer after XLVII.5.3 (between lines 3677 and 3679). Article XLVII
lies inside the RAPP1 historical section (the markers at lines 10 and 4016),
which the banner and `tools/check_rapp1_docs.py` treat as history, and proposal
0001's amendment states its current rule at the end for the same reason. If the
owner prefers it inside Article XLVII, its heading is
`### XLVII.6 — The Network Is One Distributed Hive`, and the text stays the
same.

> ## Amendment (date of merge) — The network is one distributed Hive (XLVII.6)
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
> and the files the network may read are defined by `DISTRIBUTED-HIVE.md` in
> `kody-w/rapp-model-hive`, at the commit the amendment pull request names.
>
> The chain extends XLVII.1 and XLVII.2: seed → beacon → `estate.json`
> `hives[]` → the Hive root's `PUBLISHED.md` → pointers → cards → their
> `links`.
>
> - `estate.json` MAY carry `hives[]`. Each entry is
>   exactly `{hive, name, root, commit, published_sha256}`: `root` is the raw
>   base of the public copy, `commit` its full 40-hex commit, and
>   `published_sha256` the hash of its `PUBLISHED.md` at that commit. Door
>   entries keep XLVI.3's shape. The chain needs no new seed or beacon field,
>   and readers ignore an operator entry's other members. `hives[]` is
>   the one part of `estate.json` that XLVI.6's rebuild does not recompute.
> - **LTS** (`rapp1-lts`) reads each curated station at the full commit its
>   pointer pins and checks every file against the pointer's hash; a station
>   file is normalized text, hashed by its bytes. **Newest** reads `HEAD` and
>   marks every file unpinned.
> - A pointer's or a card's lifecycle (`active`, `deprecated`, `superseded`,
>   `archived`) is a copy, never evidence of a state.
> - A station joins by publishing its card (XLVII.1). A pointer pins a station;
>   it does not admit it. Any operator may keep Hive roots. Walks cross Hives
>   through links and federation hints and may start at any node (XLVII.4).
> - A card's `indexable: false` is honored like the beacon's (XLVII.3).
> - Hashes give integrity. Authenticity comes only from the estate owner's
>   signed RAPP/1 §13 registry, and only for what a verified entry in it
>   covers. Until such an entry covers this chain (RAPP/1 defines how) and a
>   reader verifies it against the out-of-band anchor, every result is
>   unverified and nothing is accepted (Article LV.3).
> - Identity, frames and signatures are RAPP/1's. The network's tools (the
>   resolver, the card generator and the Hive agent) never mint a rappid or
>   write `rappid.json`; a station's rappid, if its owner mints one (RAPP/1
>   §6.2), is minted once, and a card only mirrors it. A walk's pulse is a
>   RAPP/1 §7 `body.pulse` frame on an existing body stream.
>
> **This amendment requires:**
> - Readers take every set of files from an index (`PUBLISHED.md`, a pointer,
>   a card) and otherwise read only the chain's documents and a station's
>   readable set; they never list a folder, never follow a redirect, and fetch
>   only from origins their transport policy allows.
> - Readers never fetch `.rapp/cache/`, `.rapp/workspace/`, `.rapp/reports/` or
>   the RAPP Workspace bootstrap files.
> - LTS readers report every hash mismatch, missing file and refused file.
>
> **This amendment forbids:**
> - Station pointers in a Hive's own `members/`, which holds people.
> - Treating a pointer, a card or a matching hash as authenticated acceptance.
> - Private-estate content in any card, pointer or public copy (XLVIII.5).
>
> **Why this is constitutional and not a feature:** without it, the map of the
> network lives in one place and the discovery chain stops at the estate. With
> it, each repository publishes its own place on the network, the curator pins
> what it has checked, and anyone can read the whole network from the seed
> with plain raw fetches and check every byte from `hives[]` down: no registry,
> and, until the chain is signed, trust in the raw server only for the seed,
> the beacon and `estate.json`, whose bytes are recorded but not checked.

## References

- [`CONSTITUTION.md`](../../CONSTITUTION.md): Article I, Article XXV,
  Article XXVI, Article XXVIII (.3, .4, .6), Article XXX.2, Article XLVI (.3,
  .5, .6), Article XLVII (.1 to .5, and .5.3 for placement), Article XLVIII
  (.1, .2, .5, .6), Article LV (.2, .3) and Article LVII.
- RAPP/1 rev-5, pinned by [`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json):
  [`kody-w/rapp-1` `SPEC.md` at `d2cd5ab`](https://github.com/kody-w/rapp-1/blob/d2cd5abed48d3f52b86bbb975ac3558286d1db41/SPEC.md),
  §5, §6.1.1, §6.2, §6.3, §7 (§7.5 and §7.6), §10, §13.1 and §13.3.
  Status: [`RAPP1_STATUS.md`](../../RAPP1_STATUS.md).
- This repository: `.well-known/rapp-network-seed.json` lines 2–43;
  `tools/sniff_network.py` lines 71, 815, 921, 992, 1015, 1036, 1106–1111 and
  1131–1135; `HISTORICAL_SOURCE_LEDGER.json` (`network-sniffer`);
  `cave/tests/test_catalog_containment.py` lines 126 and 206–225;
  `.github/workflows/cave-super-rar.yml`; `RAPP1_ADAPTATION_INVENTORY.json`;
  `tests/fixtures/rapp1-doc-scope.json`;
  `pages/docs/PUBLIC_PRIVATE_BOUNDARY.md` §4.5.
- The convention, on `kody-w/rapp-model-hive`, branch
  `experimental/hive-md-distributed`, at `e322226`:
  [`DISTRIBUTED-HIVE.md`](https://github.com/kody-w/rapp-model-hive/blob/e3222268bf751dadc61bbf25c698bc592af346cc/DISTRIBUTED-HIVE.md)
  and [HIVE-MD, "Remote member spaces"](https://github.com/kody-w/rapp-model-hive/blob/e3222268bf751dadc61bbf25c698bc592af346cc/HIVE-MD.md#remote-member-spaces).
- The rev-17 draft of RAPP/1 (experimental, not in force):
  [`kody-w/rapp-1` `SPEC.md` at `65a35c1`](https://github.com/kody-w/rapp-1/blob/65a35c145a9a74c047f32661cde307158a913f77/SPEC.md),
  §13.5, §13.6 and §13.7, and its design record
  [`REV-17-DESIGN.md`](https://github.com/kody-w/rapp-1/blob/65a35c145a9a74c047f32661cde307158a913f77/REV-17-DESIGN.md),
  on the branch `experimental/rapp1-core-rev17`.
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
- Related pull requests: #119 (proposal 0001), #124 (proposal 0001's
  amendment, merged as `e045fc3`), #120 (RAPP's network header) and #121
  (proposal 0003).
