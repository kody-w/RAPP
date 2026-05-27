# Lexicon

Two vocabularies live in this project: a **human vocabulary** for customers, partners, and people encountering AI organisms for the first time, and a **developer vocabulary** for the protocol spec, the source code, and the legal documents. They map 1:1; the choice of which to use depends on who's reading.

This document is the authoritative mapping. Writers should pick one vocabulary per document and stay consistent. Mixing them in the same paragraph is the antipattern.

## When to use which

| Audience | Vocabulary |
|---|---|
| Customers, end-users, normal humans | **Human** |
| Marketing copy, product pages, blog posts | **Human** |
| Investor-facing decks, pitch materials | **Human** |
| Engineers integrating with the protocol | **Developer** |
| Constitution, RFC-style specs, technical vault notes | **Developer** |
| Source code, schema definitions, signed records | **Developer** |
| Legal documents (patents, contracts) | **Developer** (precision required) |

## The mapping

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

## Naming principles

Steve Jobs's pattern, applied:

1. **Prefer one word over compound.** "Estate" beats "swarm estate." "Soul" beats "swarm-estate-rappid." "Voice" beats "device-signing-key."
2. **Prefer biological metaphors.** We're already calling brainstems brainstems and the species a species. Lean in: organs, voices, blessing, mitosis. The metaphor coheres if we don't fight it.
3. **Reserve compound technical terms for developers.** `swarm-estate-record/1.0` is a JSON schema; developers parse it. Don't write that string at humans.
4. **Don't mix in one paragraph.** A blog post says "soul-key" throughout; a vault note says "master keypair" throughout. Mixing implies they're two different things, which is the antipattern this whole document exists to prevent.

## Examples

### Customer-facing (Human vocabulary)

> *Wildhaven AI Homes is an Estate. Its soul-key is held by five stewards — operator, CEO, outside counsel, family member, geographic redundancy. Three together can summon the soul. The AI speaks through voices on each device. Wildhaven's herald blesses customer AIs as kin. Walk lineage to the origin: always RAPP.*

### Developer-facing (Developer vocabulary)

> *Wildhaven AI Homes' rappid is `rappid:v2:organism:@wildhaven/ai-homes:144d67...@github.com/kody-w/wildhaven-ceo`. The master keypair is split via Shamir 3-of-5 SLIP-39. Device keys are signed by S into the cross-signing chain; kin-vouches are signed by U. parent_rappid chains to the species root.*

Both paragraphs describe the same system. Different vocabularies for different audiences.

## What not to rename (load-bearing technical terms)

- **rappid** stays in the protocol spec, code, JSON schemas. It's the developer term.
- **mitosis**, **dreamcatcher**, **species tree**, **brainstem**, **kernel**, **organs** are already perfect; no rename.
- **rapplication** has accumulated brand equity in commits and documentation. Don't relitigate.
- The string format `rappid:v2:<kind>:@<pub>/<slug>:<hash>@<host>` stays. Verifiers and parsers depend on it.

## Trademark interaction

`TRADEMARK.md` claims **rappid** as a trademark. The developer term and the customer term are both legitimate uses of the mark — "rappid" used in technical documentation referring to the protocol, "soul" used metaphorically in marketing copy. Both protect the mark's distinctiveness.

## Adoption sequence

1. **All new customer-facing documents** (blog posts, marketing pages, pitch decks) use the Human vocabulary.
2. **All new developer-facing documents** (vault notes, constitution articles, code comments) use the Developer vocabulary.
3. **Existing documents stay as they are** until natural revisit. Don't sweep retroactively unless the document is being substantially edited anyway.
4. **The lexicon is the source of truth** when there's any doubt. Reference it; don't invent new mappings.

## Provenance

Drafted 2026-05-02 after a "what would Steve Jobs think" review. The Human vocabulary emerged from asking what a normal customer can say aloud without sounding like an engineer. The Developer vocabulary stayed because the protocol spec needs precision the marketing copy doesn't.

The principle: **same system, two vocabularies, no confusion if writers stay disciplined.**
