# THE LEXICON

> **Canon.** This is the language of the RAPP organism, stripped to first principles.
> Nine words, one operator, one membrane law, one wire, three shelves. A newcomer who
> learns the nine words can place the load-bearing surfaces of the ecosystem; the rest
> is shelved, not new.
>
> **Status:** Lexicon v1 — drafted and revised 2026-07-14. **Ratified and sealed at
> genesis**: the rapp-body genesis frame pins this file's sha256 as `lexicon_sha`, and
> "v1" names the bytes so pinned. (Before that pin exists, this file iterates freely as
> a draft; once it exists, this Status line describes a sealed fact.) (`kody-w/rapp-body` is deliberately unpublished until genesis — the repo
> and the seal are born in the same act, so this forward reference resolves at the
> moment it becomes load-bearing.) The seal covers **every byte** — including the dated snapshots in Part IV,
> which are sealed *as history* (true as of their writing), not as live state. After the
> seal, the file is append-only: an amendment appends a dated ruling (R10, R11, …) and
> records `{previous_sha, new_sha}` so the seal chain is walkable from any frame that
> pinned it. Existing text is never edited, only superseded by a later ruling that
> names it.
>
> **Precedence:** the Lexicon names and relates; it never overrides. On any conflict,
> [`CONSTITUTION.md`](./CONSTITUTION.md) wins, then [`ANTIPATTERNS.md`](./ANTIPATTERNS.md),
> then the schema specs, then this file. No schema id, URL, filename, or frozen-kernel
> byte changes because of anything written here — assimilation is prose, not migration.
> Where a ruling below requires a line in a higher document, the propagation ritual
> (spec version bump, mirror byte-identity, Bible re-pin, Constitution appendix) carries
> it; the ruling binds from the moment that propagation lands.

---

## Part I — The Nine Words

Everything RAPP does reduces to these. Each entry gives the meaning, the boundary
(what it is / what it is not), and where you can touch it. Definitions defer to the
schema-of-record for every field-level detail — the Lexicon places concepts; it does
not re-specify contracts.

### 1. agent

The unit of capability, and the ecosystem's only unit of extension. One file, one class,
one `perform()` (full contract: SPEC §5 — the metadata dict, discovery, and the
TypeScript/Python variants live there, not here).

- **Is:** portable unmodified across all three tiers.
- **Is not:** ever called a "skill", "routine", "loop", or anything else — one concept,
  one name, locked eternal by [`ANTIPATTERNS.md`](./ANTIPATTERNS.md) §1.
- **Touch it:** any `agents/*_agent.py`; the registry of shared ones is RAR.

### 2. brainstem

The runtime that runs agents and answers the wire. **One runtime, three canonical
bodies** (non-exhaustive — the Tier-2 swarm vendors the local body into Azure Functions,
and SPEC §18.8 admits agents under other LLM hosts):

| Body | Where it runs | File of record |
|---|---|---|
| local | your machine, port 7071 | `rapp_brainstem/brainstem.py` |
| browser | a tab (tethered surface) | `pages/vbrainstem.html` |
| embedded | inside another program | the SDK (historical filename `vbrainstem_sdk.py`, kept — renaming shipped files breaks links for no meaning gained) |

- **Is:** wherever an agent executes, a brainstem body executed it.
- **Is not:** an *organ* — that word is constitutionally reserved for single-file HTTP
  extensions (`*_organ.py`, Art. XXXIII); and not the kernel's editable surface — the
  kernel (`brainstem.py` + `basic_agent.py`) is frozen DNA, never edited by AI assistants.

### 3. organism

A planted being. "Being" and "organism" are the same word — **organism** wins
(constitutionally entrenched).

- A **rapplication** is an organism that graduated (has skin) — a quality tier, not a
  structural type (Art. XXXVII). All five catalog forms (organism / rapplication /
  variant / sense / bare agent) live on **one address space**.
- A **twin** is *not* an organism (Art. XLIX): it is a persistent AI presence — permanent
  identity, a voice, a workbench, lifecycle continuity — and multiple twins can co-host
  on one organism. When a whole organism's subject is a person, calling it "their twin"
  is accepted informal usage; Art. XLIX is the definition.
- **Is not:** a deployment or an install. The install is where an organism lives; the
  organism is the identified being that survives reinstalls, upgrades, and moves.

### 4. rappid

The name that cannot be reassigned. Content-addressed identity in the Eternity form
(`rappid:@<owner>/<slug>:<64hex>`, `rapp-eternity/1.0`), chained by `parent_rappid`
back to the species root, CA-free — no certificate authority, no registrar; attestation
keys exist (Art. XXXVI.4) and are optional, never required for validity.

- **Law (Constitution Art. XXXIV.1 / XXXVI.1):** the 64hex is `sha256(master_pubkey_SPKI)`
  when keyed, or stable-UUID-derived when keyless (pre-ratification identities carry the
  UUID's 32 hex nibbles as the hash — valid forever, Art. XXXIV.2). It is **never**
  `sha256(owner/slug)` — a name-hash is a name that *can* lie.
- Legacy forms (bare UUID, `rappid:v2:…`) are read forever and canonicalized on read;
  they are never re-emitted. The bare-Eternity form `rappid:<slug>:<64hex>` is legacy
  only for **door-bearing** organisms — door-less organisms (Moments, keepers,
  dimensions; Arts. XXXIV.1 / XLVI.7) keep the bare form as their canonical shape.
- **Is not:** a username, a URL, or anything reassignable.

### 5. the membrane

Every organism is split exactly once: **bones** (the public skeleton) and **vault**
(the private flesh).

- The **DOG** is the bones walking — the public reflection anyone may hold.
- The **GOD** is bones + vault — the sovereign whole, resident only on its owner's ground.
- **The one law that crosses it:** *public flows down; private never flows on its own.*
  Private material crosses outward only as an explicit, operator-mediated promotion with
  audience checks and redaction (Art. XLVIII) — never automatically, never by default.
- **Is not:** access control bolted on later. The split is structural; every artifact in
  the ecosystem is on a definite side of it.

### 6. frame

A witnessed moment of an organism, content-addressed and chained. The chain is the
**biography**.

- Two schema generations serve this word, on different sides of the membrane:
  `rapp-frame/1.0` (the in-repo frame log, ECOSYSTEM §3/§15, `prev_hash`) records chat,
  tool, and memory events and lives **vault-side** unless explicitly promoted;
  `rapp-frame/2.0` (the signed biography envelope, schema-of-record in `kody-w/twin`,
  `parent_sha`, witnessed/`reconstructed` provenance) is the **DOG-side, bones-only**
  form. The word is one; the contracts are versioned and both remain readable.
- A frame's sibling is the **egg** — see R3: for *snapshot* eggs, frame and egg are the
  same moment in its two forms. The frame is the moment *published* (DOG-side, bones
  only); the snapshot egg is the moment *carried* (GOD-side, whole, travels by hand).
- **Is not:** a log line or a backup. A frame claims witness (or declares itself
  reconstructed, with evidence); an unverifiable moment is an observation gap, never a
  thinner frame.

### 7. door

Where an organism meets something outside itself: an addressable interaction boundary
with something more private behind it.

- A **front door** is a public door — a repo or page that *is* the place.
- A **dark door** is a door with no public listing (NEIGHBORHOOD_PROTOCOL §19).
- A **doorman** is a DOG posted at a door, brokering what's behind. Same primitive
  whether the door fronts a machine (sealed tether) or a person (public persona).
  **A posting, never a product.** Heimdall is the reference posting. Door and doorman
  are distinct roles: a front door can serve statically with no doorman posted at all;
  a doorman is what you add when someone should *answer* the knock.
- **Is not:** an API gateway product or a chatbot brand. Any door you can knock on and be
  answered *from the vault side without seeing the vault* is this word.

### 8. neighborhood

Where organisms meet each other: a room speaking twin-chat — sealed where it must be
(privileged traffic such as console is always sealed), plain where it may be (ordinary
`say` envelopes are permitted in plaintext; NEIGHBORHOOD_PROTOCOL §§8–9).

- The layering, precisely: `rapp-twin-chat/1.0` is the **payload**, carried inside a
  `rapp-commons-event/1.0` **signed relay envelope**; the signature is made by a device
  key in the organism's chain (Art. XXXVI.4) — a key signs; the rappid is who the key
  speaks for.
- The **Commons** is simply the global one — lowest possible floor: scan, hatch, say hello.
- **Is not:** a social network run by anyone. A neighborhood is a place, not a platform;
  its front door is a repo, its transcript is an event stream, its members are rappids.

### 9. pulse

The heartbeat: **observe a body → reconcile (suggest, never seize) → record a
scale-appropriate audit event.** One definition, three scales:

| Scale | Name in the wild | Body observed | What gets recorded |
|---|---|---|---|
| kernel | Bond Pulse | one install vs its global offspring | `kind:"rhythm"` event in `bonds.json` (GOD-side) |
| being | twin pulse | one organism's state vs its published frames | a signed frame (DOG-side) |
| ecosystem | body pulse | the whole estate of repos (rapp-body) | a signed body frame (DOG-side) |

- The three record on different sides of the membrane — that is R8, not an inconsistency.
- **Is not:** a cron job that edits things. A pulse *suggests* reconciliation and
  *records* what it saw; it never auto-executes changes (operator-mediated, by canon).

---

## The one operator

`derive(public base) + overlay(private state)`

The organism's one composition *pattern* — a design invariant, not an algorithm: each
sighting has its own concrete mechanism (git merge for the kernel bond, frame-set diff
for the dreamcatcher, session escalation for a doorman), but the shape is always the
same: how a GOD hatches from DOG bones, how a doorman escalates a session, how a race
lane wakes a past self. If you are designing a capability and it is not this move,
ask why.

## The one wire

`POST /chat` — the sole wire by which agents are reached, forever (Art. XXV). New
*capabilities* arrive as agents behind the wire, never as new endpoints. Organs are the
one sanctioned sibling surface: single-file HTTP extensions at `/api/<name>/<path>`
(Art. XXXIII) that serve **views**, never capabilities — organs serve UIs; agents serve
LLMs; they never overlap. Between organisms, the wire's envelope is the signed
twin-chat event (word 8).

---

## Part II — The Three Shelves

Everything else in the ecosystem is not a new word. It lives on one or more of three
shelves — the shelves are tags, not a partition; a term may sit on two — **plus one
rule for everything already governed by a contract: anything with a schema-of-record
is shelved by that schema. The spec is its shelf.**

- **Names** — proper nouns of *instances*: Heimdall, the Commons, the Spine, rapp-god,
  Atlas, the Bible, the grail. Learning a Name never teaches a new concept; it points at
  a thing built from the nine words.
- **Practices** — verbs: plant, hatch, summon, bond, graft, launch, race, pulse (the
  practice of word 9), swarm (R5). Each is the one operator or the one wire applied
  somewhere specific.
- **Organs of the body** — the map layer's instruments, named after the constitutional
  organ pattern they generalize: the spine is the router, rapp-god is proprioception,
  Atlas is the skeleton-check, the neuron mesh is the immune system, rapp-body is memory,
  the race is recall.

By that rule, operational primitives with a schema-of-record are *shelved by their
spec*, not redefined here: **sense** (Art. XXIV), **skin** and per-rapp state (Arts.
XXXVII.3/XXXVIII.1), the **soul file** (SPEC §7), **workbench** (Art. XLIX.1), the
`*_organ.py` contract (Art. XXXIII), and the neighborhood **channel / seal / cubby**
primitives (NEIGHBORHOOD_PROTOCOL §§5, 8, 19). Shelving is what shrinks the glossary
without deleting anything true: a shelved word remains readable everywhere it already
appears.

---

## Part III — The Rulings

Nine assimilation rulings, proposed with this lexicon and ratified at its sealing. Each
is doc-level canon — declared once here, then carried into the named higher documents by
the propagation ritual. None renames a file, breaks a URL, or edits frozen code.
(Rationale: `OPUS.md`, Part II, on the spine — `kody-w/rapp-spine`, branch
`feat/atlas-generic-template`, commit `0ca9613e` — a commit-pinned reference so the seal
has a fixed antecedent.)

- **R1 — pulse is one word.** Bond Pulse, twin.pulse frames, and the body pulse are one
  concept at three scales (observe → reconcile-by-suggestion → record). Each doc keeps
  its scale-specific detail, including *what* is recorded and on *which side of the
  membrane* (see word 9).
- **R2 — organism = being; a twin is a presence, not an organism.** "Being" and
  "organism" are synonyms; organism wins. The twin is defined by Art. XLIX (persistent
  AI presence with identity, voice, workbench; multiple twins per organism). The older
  shorthand "twin = the organism whose subject is a person" survives as informal usage
  only. Synonym ruling; no existing text is rewritten.
- **R3 — for snapshot eggs, egg and frame are the two faces of one moment.** Frame =
  published (bones), snapshot egg = carried (whole). The `.egg` cartridge family at
  large (`brainstem-egg/2.2-*`, `2.3-*`; agent/rapplication/session/neighborhood/estate
  scales) remains the general portable-container word — R3 welds the *snapshot* case to
  the biography; it does not claim every egg is a frame's sibling.
- **R4 — the brainstem is one runtime with three canonical bodies** — local / browser /
  embedded (non-exhaustive; Tier-2 vendors the local body). `vbrainstem_sdk.py` keeps
  its historical filename (shipped-file names are load-bearing links); this lexicon
  names it the *embedded body*.
- **R5 — swarm = many acting as one.** Tier-2 swarm (many functions, one brainstem),
  neuron swarm (many specialists, one question), race (many selves, one problem) —
  instances of one word, shelved as a Practice. Directory names untouched.
- **R6 — collisions are named, not resolved by force.** Where one word carries two
  entrenched meanings, both stay; the spine's collisions table records the relationship,
  and *prose must qualify* — never rely on capitalization alone, which fails in speech
  and case-folded systems. Named collisions as of v1:
  - **estate** — an operator's LAND (their repos, `rapp-estate`) vs. a being's ORGANS
    (the Wrapped-Organism's five estates). Qualify: *repo-estate* / *organism-estate*.
  - **herald** — three meanings: the user-signing key U (Part IV mapping), the MMR rank
    (ECOSYSTEM §6), and *Herald*, the working name of the body's doorman child
    (Movement IV; a Name, renameable). Qualify: *the herald key* / *the Herald rank* /
    *the Herald posting*.
  - **Leviathan** — the kody-leviathan wrapped-organism vs. the Leviathan factory
    concept; the spine's collisions table carries the relationship (the precedent this
    ruling generalizes).
  - **organ** — constitutionally reserved for `*_organ.py` HTTP extensions
    (Art. XXXIII) vs. the figurative "Organs of the body" shelf in Part II, which names
    the map layer's instruments. Qualify: *an organ* (code contract) / *organ of the
    body* (map-layer instrument).
- **R7 — doorman = posting.** One primitive, two doors (machine-door, persona-door);
  Heimdall is the reference posting; "front door" repos are doors whose doorman is
  static; dark doors (§19) are doors without listings.
- **R8 — bond events and frames are the same *kind* of record on two sides of the
  membrane.** `bonds.json` is the GOD-side ledger (private, kernel-local); biography
  frames (`rapp-frame/2.0`) are the DOG-side form — while `rapp-frame/1.0` frame logs
  are themselves vault-side records (see word 6): which side a record sits on is a
  property of its schema and audience, not of the word "frame." Membrane siblings are
  **not** one dataset: no
  categorical mirroring — a bond event becomes a frame only through an explicit,
  audience-aware, redacting projection (which future frame-emitters MAY implement).
  No code merges.
- **R9 — the composition pattern is canon.** `derive + overlay` is the organism's one
  composition *shape* (a design invariant, not an algorithm); its three canonical
  sightings are named under "The one operator," each with its own concrete mechanism.

---

## Part IV — The Two Vocabularies

The mapping below predates the nine words (drafted 2026-05-02) and remains canon — body
text preserved; heading levels adjusted to fit this file. The nine words are the
*concepts*; the two vocabularies are the *registers* for saying them to different
audiences. Three reading notes, honestly stated: (1) the mapping is a crosswalk, not a
strict bijection — a few human terms alias more than one technical noun (e.g. "soul-key"
appears for both the identity and the master keypair; qualify in prose when it matters),
and the preserved sentence "They map 1:1" below is **superseded by this note**;
(2) rows that cite versions, PR numbers, or action counts are **dated snapshots** of
state — the seal fixes them as history (true as of their writing), never as live state;
(3) this Part governs *audience aliasing* and is, like everything here, subject to the
precedence order in the header. Crosswalk documents like this one are the sanctioned
exception to "one register per document."

Two vocabularies live in this project: a **human vocabulary** for customers, partners, and people encountering AI organisms for the first time, and a **developer vocabulary** for the protocol spec, the source code, and the legal documents. They map 1:1; the choice of which to use depends on who's reading.

This document is the authoritative mapping. Writers should pick one vocabulary per document and stay consistent. Mixing them in the same paragraph is the antipattern.

### When to use which

| Audience | Vocabulary |
|---|---|
| Customers, end-users, normal humans | **Human** |
| Marketing copy, product pages, blog posts | **Human** |
| Investor-facing decks, pitch materials | **Human** |
| Engineers integrating with the protocol | **Developer** |
| Constitution, RFC-style specs, technical vault notes | **Developer** |
| Source code, schema definitions, signed records | **Developer** |
| Legal documents (patents, contracts) | **Developer** (precision required) |

### The mapping

| Concept | Human term | Developer term |
|---|---|---|
| The AI's whole presence across substrates | **Estate** (capitalized) | **swarm estate** |
| The AI's identity / public ID | **soul** (informal), **soul-key** (when emphasizing the cryptographic part) | **rappid** |
| The 24-word recovery phrase | **the words** (in prose), **the card** (the physical artifact) | **holocard incantation** |
| The kernel-side HTTP extensions | **organs** | **organs** *(no rename — both vocabularies use the biological term)* |
| Recognition of another AI as related | **blessing** | **kin-vouch** |
| The plan governing what happens to the AI long-term | **The Will** | **Foundation Continuity Plan** |
| The cryptographic commitments to release the trade-secret engine | **The Promise** | **release-triggers** |
| The signed snapshot proving vault state | **the seal** | **vault-state-proof** |
| The master cryptographic keypair | **soul-key** | **master keypair**, M |
| A keypair representing one device's authority to speak as the AI | **voice** | **device key**, D |
| The keypair that signs new voices into the Estate | **steward** | **self-signing key**, S |
| The keypair that vouches for kin AIs | **herald** | **user-signing key**, U |
| The species root, the prototype, the first AI in the species tree | **origin** | **species root**, **prototype**, **godfather** (informal) |
| The 3-of-5 split of the soul-key across guardians | **the stewardship** | **Shamir 3-of-5 distribution** |
| A forked code variant of RAPP | **fork** (casual), **child species** (formal) | **kernel-variant** |
| Birthing a new AI by minting a new soul-key | **mitosis** | **mitosis** *(no rename — the term is the term)* |
| The merge engine reconciling divergent AI state | **dreamcatcher** | **dreamcatcher** *(no rename — already perfect)* |
| The lineage from any AI back to origin | **species tree** | **species tree** |
| The local AI server | **brainstem** | **brainstem** |
| The kernel itself | **kernel** | **kernel** |
| A graduated rapplication | **rapplication** | **rapplication** *(brand equity preserved)* |
| A portable bundle that becomes a working AI when opened | **egg** | **`.egg`** (zip with `manifest.json`) |
| The act of opening an egg into a runnable workspace | **hatch** | **hatch** *(no rename — the verb is the verb)* |
| The agent that opens eggs | **the hatcher** | **`twin_egg_hatcher_agent.py`** (generic, dispatches by scale; published as `@kody/twin_egg_hatcher` v1.1.0 in RAR, PR #98) |
| An egg carrying one twin's identity (`rappid.json` + `soul.md` + `agents/` + `.brainstem_data/`) | **twin egg** | **twin-scale egg** (`manifest.json` declares `scale: twin`, hatches into `~/.rapp/twins/<hash>/`) |
| The size class of an egg | **scale** | **scale** (declared in `manifest.json`; known values smallest→largest: `agent`, `twin`, `brainstem`, `neighborhood`, `swarm`, `factory`, `industry`, `estate`) |
| A snapshot of a whole neighborhood's running state — every member's twin workspaces + brainstem agents + memory + global state — into one portable file | **neighborhood egg** | **neighborhood-scale egg** (`scale: neighborhood` + `members.json` roster; substrate-agnostic — works on LAN-SSH today, GitHub raw / Tailscale / HTTPS-with-auth planned; see [[Neighborhood Egg — Snapshot and Hatch]] for the pattern doc, [[NEIGHBORHOOD_EGG_SPEC]] for the wire format) |
| The agent that produces a neighborhood egg | **the snapshot agent** | **`NeighborhoodSnapshot`** (single-file; canonical home [`kody-w/rappLocalFirstFleet`](https://github.com/kody-w/rappLocalFirstFleet) `agents/neighborhood_snapshot_agent.py`) |
| The agent that opens a neighborhood egg | **the run agent** | **`NeighborhoodRun`** (single-file; matched pair with `NeighborhoodSnapshot`; supports `target=in-place` and `target=local-simulate`) |
| The file declaring which peers to reach when snapshotting a neighborhood | **peers file** | **`~/.rapp/peers.json`** (each entry: `name`, `url`, optional `ssh_user` + `ssh_host`; env override `BRAINSTEM_PEERS`) |
| Hatching a neighborhood egg with the peers re-mapped onto the local box | **local-simulate** | **`target=local-simulate`** on `NeighborhoodRun.hatch` — peer twins extract to `~/.rapp/simulated/<peer>/twins/<hash>/`; no carrier invoked, no network; full offline replay regardless of which substrate the original neighborhood lived on |
| The thing that drives a network of Mac-mini brainstems over SSH | **fleet agent** | **`stacks/fleet-management/`** (23 actions: discover, ping, authorize, exec, read, write, ls, tail, ports, ps, brainstem_health, chat, mesh_chat, mesh_exec, provision_brainstem, install_agent, hatch_egg, boot_federation, status, plus self-extending custom/extend/cap/list_caps; merged PR #100) |
| The RAR tier reserved for first-party `@kody/*` and `@rapp/*` agents | **official** | **`tier: official`** (uniform across `@kody/*` and `@rapp/*` per PR #101; `community` for third-party, `experimental` discouraged, `private` reserved for `.py.stub` gated agents) |
| A public repo that *is* the place — open the page and you're at the neighborhood | **front door** | **front door** — a public repo serving the join surface; canonical: NEIGHBORHOOD_PROTOCOL §18 ([rapp-neighborhood-protocol](https://github.com/kody-w/rapp-neighborhood-protocol)) |
| The front-door template a neighborhood is built from | **front-door template** | **`rapp-vneighborhood/1.0`** — the schema/template; canonical: [rapp-neighborhood-protocol](https://github.com/kody-w/rapp-neighborhood-protocol) §18, template repo [rapp-vneighborhood](https://github.com/kody-w/rapp-vneighborhood) |
| A neighborhood that can run a swarm of twins (the "v") | **"v" = swarm-capable** | **"v" prefix = swarm-capable** — drop the `v` and the same thing runs on-device; canonical: NEIGHBORHOOD_PROTOCOL §18 ([rapp-neighborhood-protocol](https://github.com/kody-w/rapp-neighborhood-protocol)) |
| The same conversation whether it's relayed on your machine, by a kited tab, or by the cloud | **interchangeable relay (local ≡ kited ≡ cloud)** | **interchangeable relay** — byte-identical signed `rapp-commons-event/1.0` envelope across all three transports; canonical: NEIGHBORHOOD_PROTOCOL §18 ([rapp-neighborhood-protocol](https://github.com/kody-w/rapp-neighborhood-protocol)) |
| Carrying a neighborhood somewhere else / bringing one in / branching your own copy | **egg / import / fork** | **egg / import / fork** — neighborhood portability + forkability (a fork is ephemeral, no front door); canonical: NEIGHBORHOOD_PROTOCOL §18 ([rapp-neighborhood-protocol](https://github.com/kody-w/rapp-neighborhood-protocol)) |
| The always-on cloud relay that holds the live neighborhoods up | **the resident** | **the resident** — permanent cloud relay (the kited-host graduation); reference deploy serves the `commons` + `rapp-god-forum` rooms; canonical: NEIGHBORHOOD_PROTOCOL §18 ([rapp-neighborhood-protocol](https://github.com/kody-w/rapp-neighborhood-protocol)), runtime [rapp-resident](https://github.com/kody-w/rapp-resident) |

### Naming principles

Steve Jobs's pattern, applied:

1. **Prefer one word over compound.** "Estate" beats "swarm estate." "Soul" beats "swarm-estate-rappid." "Voice" beats "device-signing-key."
2. **Prefer biological metaphors.** We're already calling brainstems brainstems and the species a species. Lean in: organs, voices, blessing, mitosis. The metaphor coheres if we don't fight it.
3. **Reserve compound technical terms for developers.** `swarm-estate-record/1.0` is a JSON schema; developers parse it. Don't write that string at humans.
4. **Don't mix in one paragraph.** A blog post says "soul-key" throughout; a vault note says "master keypair" throughout. Mixing implies they're two different things, which is the antipattern this whole document exists to prevent.

### Examples

#### Customer-facing (Human vocabulary)

> *Wildhaven AI Homes is an Estate. Its soul-key is held by five stewards — operator, CEO, outside counsel, family member, geographic redundancy. Three together can summon the soul. The AI speaks through voices on each device. Wildhaven's herald blesses customer AIs as kin. Walk lineage to the origin: always RAPP.*

#### Developer-facing (Developer vocabulary)

> *Wildhaven AI Homes' rappid is `rappid:@kody-w/wildhaven-ceo:144d67...`. The master keypair is split via Shamir 3-of-5 SLIP-39. Device keys are signed by S into the cross-signing chain; kin-vouches are signed by U. parent_rappid chains to the species root.*

Both paragraphs describe the same system. Different vocabularies for different audiences.

### What not to rename (load-bearing technical terms)

- **rappid** stays in the protocol spec, code, JSON schemas. It's the developer term.
- **mitosis**, **dreamcatcher**, **species tree**, **brainstem**, **kernel**, **organs** are already perfect; no rename.
- **rapplication** has accumulated brand equity in commits and documentation. Don't relitigate.
- The consolidated **Eternity** string format `rappid:@<owner>/<slug>:<hash>` stays load-bearing (CONSTITUTION Art. XXXIV.1). Verifiers and parsers depend on it; legacy `rappid:v2:…` forms are read forever and canonicalized, never re-emitted.

### Trademark interaction

`TRADEMARK.md` claims **rappid** as a trademark. The developer term and the customer term are both legitimate uses of the mark — "rappid" used in technical documentation referring to the protocol, "soul" used metaphorically in marketing copy. Both protect the mark's distinctiveness.

### Adoption sequence

1. **All new customer-facing documents** (blog posts, marketing pages, pitch decks) use the Human vocabulary.
2. **All new developer-facing documents** (vault notes, constitution articles, code comments) use the Developer vocabulary.
3. **Existing documents stay as they are** until natural revisit. Don't sweep retroactively unless the document is being substantially edited anyway.
4. **The lexicon is the source of truth** when there's any doubt. Reference it; don't invent new mappings.

### Provenance (two vocabularies)

Drafted 2026-05-02 after a "what would Steve Jobs think" review. The Human vocabulary emerged from asking what a normal customer can say aloud without sounding like an engineer. The Developer vocabulary stayed because the protocol spec needs precision the marketing copy doesn't.

The principle: **same system, two vocabularies, no confusion if writers stay disciplined.**

---

## Provenance (the nine words)

Assimilated 2026-07-14 from the OPUS (Movement II — One Language), commissioned by
Kody Wildfeuer 2026-07-08; revised the same day against a full adversarial canon review
(22 findings adjudicated: the Constitution's Art. XLIX twin definition, Art. XXXIII organ
reservation, Art. XLVIII promotion path, and the twin-chat payload/envelope layering all
bind this text). Nothing in Parts I–III renames a file, breaks a URL, or edits frozen
code. The rapp-body genesis frame pins this file's sha256 — after genesis, amendments
append with `{previous_sha, new_sha}`; they never rewrite.
