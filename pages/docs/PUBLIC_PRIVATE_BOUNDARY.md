# Historical Public/Private Estate Boundary

> **Current RAPP/1 authority (rev-5).** For canonicalization, identity, frames,
> wire, eggs, registry, trust, and protocol evolution, follow
> [`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../RAPP1_STATUS.md). This privacy architecture cannot
> replace RAPP/1 §9 eggs or §§10/13 authenticated trust.

> **Disposition:** retired product architecture dated 2026-05-09. No current
> installer creates public/private estate repositories or a mandatory
> three-tier operator estate. Do not follow the planter, bootstrap, publishing,
> or discovery actions below. Current implementations still must minimize
> disclosure and apply RAPP/1 §§9, 10, and 13 at every acceptance boundary.

<!-- RAPP1-HISTORICAL-SECTION-START -->

This is the spec for the platform's estate model. **Every Article-XLVIII-compliant operator has THREE tiers from first install:** the public estate (discovery), the private estate (the *bones* — workflow + sanitized structure), and the local-only on-device tier (the *substance* — PII, customer data, real content). All three are first-class infrastructure; none are opt-in.

The 2026-05-10 tightening (§1.5 below) corrects an earlier ambiguity: the private estate was previously described as "where PII lives," which encouraged operators to push real customer data into a GitHub-private repo. That trades one threat model (the public web seeing PII) for another (GitHub-the-vendor seeing PII). The third tier — the operator's local device — is the default home for PII. The private repo holds the *bones* of the digital organism so collaborators can run the workflow; the substance the workflow operates on stays on the operator's machine unless they explicitly override.

This spec also introduces **URL opacity** as a load-bearing privacy property: the URLs themselves inside the private repo cannot be allowed to leak semantic information, because URLs surface in beacons, error pages, agent logs, browser history, and 404 responses to unauthorized viewers. A URL is metadata even when its content is access-gated.

If you are writing a planter, an estate agent, a sniffer, a mailbox client, a witness cache, or any code that touches an operator's content — this is the contract.

---

## §1 — Why three tiers (and why mandatory)

A public-only estate is a toy. The federation primitives that make the platform useful for real work — Inbox, Bilateral Channel, Web of Trust private signals, Presence opt-in, secret ballots — cannot exist on a public-only substrate.

But a **two-tier-with-PII-in-private** estate is also broken — see §1.5. The version that actually works has three tiers. Each addresses a distinct threat model.

**Article XLVIII makes all three tiers mandatory from first install.** Every operator atomically gets:

1. `<handle>/rapp-estate` — public discovery surface (zero PII)
2. `<handle>/rapp-estate-private` — private GitHub repo for the *bones* (workflow agents, sanitized member metadata, structural artifacts; collaborator-gated; **no PII by default**)
3. `~/.brainstem/neighborhoods/<slug>/<handle>/customers/` (or equivalent per-neighborhood path) — **local on-device** for the *substance* (PII, customer specifics, real content)

**Cost:** one additional free private repo per operator + the operator's existing disk space. GitHub's free tier supports unlimited private repos for individuals.

**Benefit:** the platform is structurally usable for sensitive work AND structurally invisible to the GitHub-as-vendor threat model AND survives airgapped customer sites without configuration.

---

> **Historical 2026-05-10 cartridge proposal, superseded.** The retired
> `brainstem-egg/2.3-estate` and schema/type hatcher are migration evidence.
> Current portability uses the RAPP/1 §9 `estate` variant and requires
> identity, signature, and registry verification under §§6, 10, and 13.

## §1.5 — Why the private repo doesn't hold PII by default (the 2026-05-10 tightening)

The original spec described the private estate as "where PII lives." That description traded one threat model for another:

- **Threat A — the public web sees PII.** Mitigated by putting PII in a GitHub-private repo (collaborator-gated). ✓
- **Threat B — GitHub-the-vendor sees PII.** **NOT mitigated** by putting PII in a private repo. GitHub admins can read your private repos. A breach of GitHub exposes private repo contents. A subpoena to GitHub extracts your private repo without your knowledge. Future TOS changes around content scanning of private repos land first on the contents you most want unscanned.
- **Threat C — collaborators-of-collaborators see PII.** A collaborator on your private repo who is also a collaborator on someone else's private repo can correlate contents. Not mitigated by repo-level access controls.

For most consumer use (personal notes, casual correspondence) Threat A is the only one that matters. For the use cases that monetize the platform — regulated industries, cross-org legal/financial/healthcare correspondence, M&A diligence, anything subpoenable — **Threats B and C are the ones that close deals**. A platform that ships PII straight to GitHub-private fails the second threat model and loses those buyers.

**The fix:** make the local device the canonical home for PII; make the private repo the canonical home for the *bones* (workflow + sanitized structure that collaborators need to run the workflow). The two-tier-with-PII-in-private layout from `1.0` was a stepping-stone; the three-tier-with-PII-on-device layout from `1.1` is the ratified spec.

This is a tightening, not a breaking change. Operators who already pushed PII into their private estate may keep doing so by exercising the explicit override (§1.6). New operators get the on-device default automatically. Existing data is not migrated by the platform — operators choose if and when to extract PII from their private repo onto the device.

---

## §1.6 — The override (operator-mediated, never automatic)

The local-on-device default is just that — a default. Operators MAY put PII in the private repo when their use case calls for it. Examples:

- **Compliance archival** — a regulated industry that requires off-device retention with audit trails the auditor can pull from a single repo.
- **Public-by-construction engagements** — work where the customer name and outcome are PR material, the customer has explicitly consented to the engagement being public, and the operator wants the record co-located with the workflow.
- **Sole-operator backup** — a single-operator neighborhood where the private repo IS the operator's backup of their own work.
- **Cross-org diligence rooms** — a 72-hour ephemeral gate where both parties have agreed to ratify the contents into both their private estates.

The override is **never automatic**. It is exercised by one of these explicit actions, in order of increasing intentionality:

1. **Per-file:** the operator places a file directly inside `ses/<handle>/projects/<slug>/` (in the workspace, outside the gitignored local data directory). They consciously chose to put it there. The .gitignore does not exclude it. `git add` works. They commit it.

2. **Per-engagement:** the operator marks a specific customer slug for repo-archival via `~/.brainstem/neighborhoods/<slug>/<handle>/customers/<slug>/.publish-to-repo` (a flag file). The factory + pinger respect this flag and copy the customer's sanitized-or-full content (operator's choice, named per-file in the flag's body) into the workspace at commit time.

3. **Repo-wide:** the operator edits the workspace's `.gitignore` to remove the `.brainstem/` exclusion. This is highly unusual; it disables the on-device-canonical guarantee for the whole neighborhood. The brainstem warns when it detects this on next chat, but does not refuse — the operator is sovereign.

4. **Encrypted-at-rest** (deferred — see `pages/vault/Decisions/2026-05-10 — Feature freeze (LFPE deferred).md`): a future Article XLVIII.7 may add client-side envelope encryption for the private estate, which would let operators push PII in encrypted form so even GitHub-the-vendor sees only ciphertext. This is not yet ratified.

The override exists precisely so the spec doesn't dictate the operator's compliance posture. Defaults are local-canonical; intentional acts move data into the repo. Article VIII (operator-mediated) governs throughout.

---

## §1.7 — Workbench is the canonical local-tier primitive (per-twin, sibling-peekable)

The local on-device tier is structured as **workbenches**. A workbench is one twin's working area for one ongoing thing — a customer engagement, a research thread, a personal project, a code experiment, a pattern they're debugging, anything. The customer-data dir from BWAT (`~/.brainstem/neighborhoods/<slug>/<handle>/customers/`) is one specialization; the generic primitive is broader.

### §1.7.1 — Path convention

```
~/.brainstem/workbenches/
├── <workbench-slug>/
│   ├── meta.json                ← {owner_rappid, twin_rappids[], type, created, neighborhood?, peers_visible}
│   ├── status.json              ← schema-versioned status enum + last-touched
│   ├── notes.md                 ← working notes
│   ├── (any files the twin needs — outcomes, intakes, attachments, scratch)
│   └── attachments/
└── <another-workbench-slug>/
```

Workbench slugs are operator-chosen (e.g. `acme-corp-q3`, `mars-physics-paper`, `house-renovation-2026`). The slug is the only identifier that ever leaves the device by default — the contents are local-only per §1.5.

The pre-existing path `~/.brainstem/neighborhoods/<slug>/<handle>/customers/<project>/` from BWAT and similar neighborhoods continues to work as a specialized form (`type: "customer-engagement"` in meta.json, neighborhood field set). Operators MAY use either path layout; the canonical local-tier primitive is the workbench.

### §1.7.2 — Per-twin association

A workbench's `meta.json` includes `twin_rappids[]` — the list of twins that consider this workbench part of their working set. A twin's own workbench is one where its rappid appears in that list.

The operator's primary twin (rappid in `~/.brainstem/rappid.json`) implicitly owns every workbench unless the workbench explicitly opts out. Planted twins (BillTwin, AliceTwin, neighborhood twins) become workbench-associated when the operator runs them on a workbench.

### §1.7.3 — Sibling peek (cross-twin local collaboration)

**Default:** any twin running on the operator's device can read any other twin's workbench by walking `~/.brainstem/workbenches/`. The default is permissive because all twins on the device share the same operator + the same trust boundary (the operator's user account on their machine).

**Why this matters:** cross-twin collaboration becomes a local file read. BillTwin working on a customer engagement can ask AliceTwin's workbench "what did you learn last quarter on a similar engagement?" without any network call, any vendor, any RPC, any auth. The two twins are both local; the workbench is the substrate they share.

**Opt-out:** a workbench's `meta.json` MAY set `peers_visible: false` to restrict reads to the workbench's listed `twin_rappids[]` only. Sibling twins receive a "permission denied by workbench owner" instead of contents. This is the workbench owner's choice, not a kernel-imposed restriction.

**Opt-in cross-device:** sibling-peek is local-only by default. Cross-device workbench sharing requires either (a) explicit sneakernet of the workbench (zip + AirDrop, like an egg), or (b) the override paths in §1.6 to push specific workbench contents into the repo. There is no automatic cross-device peek.

### §1.7.4 — Implication for agents

Agents that need to read a workbench MUST go through `~/.brainstem/workbenches/` as the canonical entry point. Agents that need to write to a workbench MUST honor its `peers_visible` setting. Agents that create workbenches MUST set `meta.json` with at minimum `owner_rappid`, `created`, and `twin_rappids[]` (which can be `[<the-creating-twin's-rappid>]`).

Workbench discovery is filesystem-native: `ls ~/.brainstem/workbenches/`
returns the slugs and each `meta.json` supplies application metadata. This
needs no separate **application catalog**; it does not replace or bypass the
RAPP/1 §13 protocol registry.

---

## §1.8 — The private repo IS the full digital organism (bones, organs, senses, agents, rar, rapplications, holocards) — MINUS PII

Read together: §1.5 (PII not in private repo by default), §1.7 (PII lives in workbenches on-device). The corollary is the load-bearing claim of the new model:

**Cloning the private repo gives you a fully runnable digital organism. It has every anatomical layer the organism needs to function — just no operator-specific PII.**

### §1.8.1 — What "the bones of the digital organism" means concretely

The private repo carries the COMPLETE shape of the organism, minus substance. Per the visual anatomy at `pages/about/anatomy.html` and the implementations in `rapp_brainstem/`, that means every contributor's pull-down of the repo includes:

- **Identity** — `rappid.json`, `neighborhood.json`, `members.json`
- **Soul** — `soul.md` (the voice anchor)
- **Agents** — `agents/*_agent.py`; `rar/index.json` SHA-256 values are
  application integrity metadata, not RAPP trust
- **Organs** — `utils/organs/*_organ.py` (HTTP extension surfaces — Article XXXIII)
- **Senses** — modular per-channel output overlays (eli5, headlines, etc., from `kody-w/RAPP_Sense_Store`)
- **Rapplications** — `rapplications/<name>/` (graduated workflows — Article XXXVII)
- **Holocards** — `card.json`, `holo.svg`, `holo.md`, `holo-qr.svg`, `facets.json` (identity proof + summon QR — Article XLVI.2 door URL set)
- **Specs bundle** — `specs/AGENT_CONTRACT.md`, `specs/NEIGHBORHOOD_PROTOCOL.md`, `specs/RAR_INDEX.md` (so the repo is self-documenting)
- **RAR / participation kit** — application discovery metadata whose hash is
  an integrity hint only; RAPP trust still requires §§10/13
- **Constitution + governance** — `CONSTITUTION.md`, `SKILL.md`, `SETUP.md`, `QUICK_START.md`, `onboarding.html`, `README.md`
- **Per-contributor front doors** — `ses/<handle>/front_door.md`, `ses/<handle>/projects.json` (sanitized, slugs + status only)
- **`.gitignore`** that excludes the local on-device PII path (`.brainstem/`)

### §1.8.2 — What does NOT enter the repo (per-contributor PII)

The PII for each contributor's specific use of this organism stays on THEIR device only:

- Real names of customers / clients / patients / counterparties
- Email addresses, phone numbers, addresses, contracts
- Customer-specific outcomes, KPI values, financial details, technical specifics
- Mailbox content, conversation transcripts, working notes, drafts
- Personal memory / journal entries
- Voice recordings, screenshots, attachments

All of the above lives at `~/.brainstem/workbenches/<slug>/` per §1.7. Each contributor has their own workbenches; their PII belongs to them. The repo holds the substrate they all share; the device holds the substance they each own.

### §1.8.3 — Why this is the right architecture for active multi-contributor neighborhoods

When a new contributor joins the neighborhood (gets added as a collaborator on the private repo + clones it):

1. **They get a fully runnable organism on day one.** Every agent, every organ, every rapplication, every holocard. They can run the workflow against their own customers immediately, without needing anyone else's data.
2. **They never see anyone else's PII.** Other contributors' real customer names + outcomes + notes never lived in the repo, so cloning doesn't expose them.
3. **They never accidentally leak their own PII.** The `.gitignore` excludes `.brainstem/`. PII reaching the repo would require an explicit operator override per §1.6.
4. **The neighborhood scales without compounding privacy risk.** Adding the 50th contributor to a regulated-industry neighborhood doesn't expand the attack surface for the first 49. Each contributor's substance is on their own device; the substrate they share is bones-only.
5. **The neighborhood survives any contributor leaving.** A departing contributor takes their PII with them (it was always on their device); the substrate they contributed to (the bones — agents they wrote, rapplications they shipped) stays in the repo for the rest of the neighborhood.

### §1.8.4 — Conformance for active contributors

**Every active contributor of a neighborhood MUST follow this pattern.** Specifically:

- They MUST keep customer / project PII in `~/.brainstem/workbenches/<slug>/` (or the per-neighborhood specialization at `~/.brainstem/neighborhoods/<slug>/<handle>/customers/<slug>/`).
- They MUST NOT `git add` files containing customer-specific PII into the repo unless they exercise an explicit override per §1.6 with a documented reason in the commit message.
- They MUST honor the workspace's `.gitignore` exclusion of `.brainstem/` and `.bwat-data/` and similar per-neighborhood data paths.
- They SHOULD periodically audit `git diff` against `main` before pushing to confirm no customer-specific content slipped in (the local-data dirs are gitignored, but a copy/paste into `ses/<handle>/projects.json` could leak — visual review catches this).

**Enforcement is per-contributor honor + structural defaults**, not platform policing. The platform CAN'T inspect the contents of a contributor's commits without violating their privacy; the discipline is operator-mediated per Article VIII. The structural defaults (gitignore, workbench convention, sanitized projects.json, override paths) make the right thing the easy thing.

### §1.8.5 — Cross-reference: this is exactly Article XXXVII (rapplications-as-organisms) at neighborhood scale

Article XXXVII (Rapplications ARE Organisms, shipped 2026-05-02) established that the egg → overlay → hatch lifecycle applies at the rapplication scope, not just the kernel scope. Section §1.8 here applies the same insight at the neighborhood scope: **the private repo IS the neighborhood-organism's distributable shape**. Cloning it = hatching the neighborhood-organism into your brainstem. Adding your PII = giving the hatched organism a body to operate against.

The kernel constitution Article XLIX (twin primitive) closes the loop: each contributor's local instance of the neighborhood-organism IS a twin (or hosts twins). The twin's workbench is where their PII-bearing work lives. Sibling twins on the same device peek as permitted by §1.7.3.

The result is structural: **the repo is the substrate, the device is the substance, the twin is the unit of work, the workbench is the unit of state.** Every layer has a home. Every contributor knows where their data lives. Every neighborhood knows what it ships.

---

---

## §2 — The boundary (what goes where, by default)

| Lives in PUBLIC estate | Lives in PRIVATE estate (the *bones*) | Lives LOCAL ON-DEVICE only (the *substance*) |
|---|---|---|
| Operator's personal rappid | Workflow agents (`agents/*_agent.py`) | Real names of customers / clients / patients |
| Door catalog (rappids only) | Rapplications (`rapplications/<name>/`) | Email addresses, phone numbers, contracts |
| Beacon (`.well-known/rapp-network.json`) | Sanitized member metadata (handle + role only) | Customer-specific outcomes, KPIs, contract values |
| Federation feed (`feed.jsonl`) | Per-operator front doors (`ses/<handle>/`) — sanitized | Mailbox content (received + sent) |
| Witness cache of OTHERS' public estates | `projects.json` per operator — slugs + status enums + dates ONLY | Bilateral channel transcripts |
| Activity timeline (own actions, public-shaped) | `members.json` — handles + roles | Personal memory / journal entries |
| `private_estate_pointer` + commitment hash | `neighborhood.json` + `rappid.json` + `soul.md` | Working notes, attachments, drafts |
| `private_door_count` (transparency, no leak) | Manifest (`rar/index.json`) + sha256s | Voice recordings, screenshots, photos |
| ZERO PII | ZERO PII by default — see §1.6 for explicit override | Per-twin workbenches at `~/.brainstem/workbenches/<slug>/` (canonical, per §1.7) — siblings on the same device can peek by default |

**The new bridge:** the private estate's `projects.json` per operator carries only an opaque slug, a status enum (`active` / `blocked` / `awaiting` / `shipped`), and a last-touched timestamp. The slug correlates to a customer-data directory ONLY on the operator's own device; teammates with collaborator access to the private repo see the slug + status, never the customer name behind it.

**The .gitignore enforcement:** every planted neighborhood ships with a `.gitignore` excluding the local-on-device path (`.brainstem/`, `.bwat-data/`, etc). `git add` of any path under that exclusion fails by construction. PII reaching the private repo by accident is structurally impossible without the operator explicitly editing `.gitignore` (an action they will notice).

**What the public never sees:** the contents of the private estate, its internal paths, recipient handles beyond what they consented to publish, topic strings, dates of correspondence, or any metadata that would allow an unauthorized viewer to characterize the private content.

**What collaborators on the private estate see:** the workflow + sanitized member metadata + each operator's project slugs + status. They do NOT see PII, customer names, contract values, or any substance — that's on each operator's own device.

**What GitHub-the-vendor sees:** the same as a collaborator on the private repo. Workflow code (which is identical across all operators of this neighborhood, so leaks no operator-specific intelligence) + sanitized metadata. A subpoena served to GitHub for an operator's private repo extracts the bones, not the substance.

---

## §3 — The architecture (file layout)

```
PUBLIC: <handle>/rapp-estate (public repo)
├── estate.json                    ← public door catalog (rappids only)
├── .well-known/
│   └── rapp-network.json          ← beacon (rapp-network-beacon/1.1)
│       ↳ private_estate_pointer: <https URL of private repo>
│       ↳ private_estate_commitment: sha256 of normalized private state
│       ↳ private_door_count: N
│       ↳ NEVER: internal paths, topic names, recipient handles
├── feed.jsonl                     ← public activity ring buffer
├── witness/                       ← snapshots of OTHER operators' public estates
└── (rest of Article XLVII surface)


PRIVATE: <handle>/rapp-estate-private (PRIVATE repo)
├── meta.json                      ← schema + index pointer
│                                    (one well-known file at one well-known
│                                    path; content-free; safe to expose)
├── README.md                      ← "see operator's local brainstem map"
├── objects/
│   └── <sha256>.json              ← every artifact stored under content-hash
│                                    the hash reveals nothing about content
└── kinds/
    └── <HMAC(secret, kind)>/
        └── <HMAC(secret, id)>.json
                                   ← where 'mailbox-inbox', 'channel-with-bill',
                                     'contact-jane' become opaque HMACs
                                     the operator's local map can decode


LOCAL (NEVER published, ever):
~/.brainstem/
├── private-estate-secret          ← per-operator HMAC secret (32 bytes)
└── private-estate-map.json        ← human-readable ↔ opaque token table
                                     (encrypted at rest with the secret)
```

**Cross-operator access** (when bill needs to read kody-w's mailbox channel with him):

1. kody-w invites bill as a GitHub collaborator on `kody-w/rapp-estate-private` (or, finer-grain, on a sub-folder via CODEOWNERS — Round 1 uses repo-level for simplicity).
2. kody-w exports a SCOPED HMAC secret (or the full secret if full access) and shares it with bill out-of-band (1-time link, QR code, in-person).
3. bill's brainstem stores it at `~/.brainstem/peer-secrets/kody-w.hmac` and uses it to decode opaque paths in kody-w's private repo.

---

## §4 — URL opacity (Article XLVIII.6)

**The threat:** static URLs leak metadata even when their content is access-gated. A URL like `<handle>/rapp-estate-private/main/mailbox/inbox/dr-jones-oncology/2026-05-09-test-results.json` reveals — *just by existing in any system that touches it* — that kody-w receives correspondence from dr-jones-oncology dated 2026-05-09 about test results.

URLs surface in:
- The public beacon (if not carefully scrubbed)
- Commit history of the private repo (visible to repo collaborators)
- Browser URL bars + history (if the operator ever clicks)
- Agent logs + brainstem console output
- Error pages (404s often echo the requested path)
- Any third-party tool that touches them
- Search engine caches (if a private repo briefly went public)

### §4.1 The opacity contract

Every path inside the private repo carries **zero semantic information**. Specifically:

- **Two well-known paths are exempt:** `meta.json` (schema + index pointer) and `README.md` (instructions). These are content-free; their existence is already advertised by the public beacon.
- **All other content lives at opaque paths**, in one of two patterns:
  - `objects/<sha256-of-content>.json` — content-addressed; hash is deterministic but reveals nothing about what the content represents.
  - `kinds/<HMAC(secret,kind)>/<HMAC(secret,id)>.json` — for queryable content (e.g., "find all mailbox-inbox entries"); the kind+id are HMAC'd with the operator's per-install secret so only authorized parties can navigate.
- **The local map** at `~/.brainstem/private-estate-map.json` records the human-readable ↔ opaque mapping. It is encrypted at rest with the operator's secret, never published, never logged.

### §4.2 Validation regex

A spec-compliant private repo's tree has files matching ONLY:

```
^(meta\.json|README\.md|objects/(\.gitkeep|[a-f0-9]+\.json)|kinds/(\.gitkeep|[a-f0-9]+(/[a-f0-9]+\.json)?))$
```

Any path outside this regex is a violation (caught by `tests/features/F15-private-estate.sh` step 8).

### §4.3 The HMAC secret

- Generated at install time by `tools/private_estate_init.py` (32 random bytes from `os.urandom`).
- Stored at `~/.brainstem/private-estate-secret` (file mode 0600).
- NEVER appears in any committed file, any beacon field, any agent log, any error message, any process argument list. Constitutionally enforced.
- **Lost secret recovery:** if the operator loses the secret, the URLs in their private repo still exist, but they (and everyone else) can no longer decode which opaque token corresponds to which kind/id. They fall back to walking `meta.json`'s index, which lists every committed entry by its opaque path + kind hint (the kind hint is the HMAC key tag — short and re-derivable if the operator has any of their old kinds in cleartext to seed re-discovery). Better than nothing; worse than not losing the secret.

### §4.4 The publish-time invariant

The estate agent's `publish` action invokes `tools/path_opacity.py::audit_paths()` against the private repo before computing the commitment hash. If any path violates the opacity regex, the publish is REFUSED with a clear error pointing at the offending path. Catches operator drift (someone editing private repo files manually with semantic names).

### §4.5 What the beacon CAN'T contain

The public beacon's allowed fields (rapp-network-beacon/1.1):

- `schema`, `operator_rappid`, `github`, `estate_url`, `grail_url`
- `protocol.spec_version`, `protocol.estate_schema`, `protocol.implements`, `protocol.spec_url`
- `discovery.indexable`, `discovery.consent`, `discovery.federation_hints`
- `private_estate_pointer` (URL of private repo, no path beyond it)
- `private_estate_commitment` (sha256, opaque)
- `private_door_count` (integer)
- `minted_at`

The beacon CANNOT contain (constitutionally — Article XLVIII.5 + XLVIII.6):

- Any internal private-repo path beyond the well-known `meta.json`
- Any recipient handle, contact name, topic string, or other semantic identifier
- Any field that surfaces operator's private collaborators (their identities are visible only to them and the collaborators themselves via GitHub's UI)
- Any field that would let a sniffer characterize what's inside

---

## §5 — Schema: `rapp-private-estate/1.0` (the meta.json shape)

```json
{
  "schema": "rapp-private-estate/1.0",
  "owner": {
    "rappid": "rappid:@<handle>/<repo>:<hex>",
    "github": "<handle>"
  },
  "private_door_count": 0,
  "kinds": {
    "<HMAC(secret, 'mailbox-inbox')>": "kinds/<HMAC>/...",
    "<HMAC(secret, 'channel')>":       "kinds/<HMAC>/...",
    "<HMAC(secret, 'contact')>":       "kinds/<HMAC>/...",
    "<HMAC(secret, 'memory')>":        "kinds/<HMAC>/...",
    "<HMAC(secret, 'trust-signal')>":  "kinds/<HMAC>/..."
  },
  "objects_count": 0,
  "kinds_count": 0,
  "updated_at": "2026-05-09T00:00:00Z",
  "_note": "Semantic names live in the operator's local map at ~/.brainstem/private-estate-map.json (encrypted). This file's only public-readable purpose is operator-side index navigation."
}
```

The `kinds` object provides a stable index of well-known kind tokens (HMACs of common primitives). It's not enumeration of CONTENT — only of WHAT KINDS this operator's private estate uses. Even this can be omitted by paranoid operators (the brainstem walks `kinds/` directory directly).

---

## §6 — The receiver-controls discipline (XLVIII.4)

Senders/peers cannot force content into the operator's public estate. The flow:

1. **Sender** publishes their proposal to THEIR public mailbox-public surface (e.g. `<sender>/rapp-mailbox-public/inbox/<recipient-handle>/<id>.json`).
2. **Recipient's brainstem** polls the senders it knows about (or trusts).
3. **Recipient** reviews the proposal. If accepted, the brainstem MOVES the content to the recipient's private mailbox (opaque path) AND can either delete the public copy or move it to a `processed/` folder (still public, for sender's confirmation).
4. **NO automatic flow** moves content from anyone's private estate to anyone else's public estate. Constitutionally enforced.

This is the Webmention pattern + IndieWeb's POSSE: the receiver decides what to render. The platform is a substrate; the operator is the policy.

---

## §7 — The publish flow (atomic two-tier; Article XLVIII.1 enforced)

The estate agent's `publish` action is constitutionally atomic. Whatever path the operator takes (install.sh → chat, programmatic, AI walking through skill.md), they all converge on `publish`. Hooking the auto-create here means EVERY operator on EVERY path ends up XLVIII-compliant.

**Step 0 — Auto-create private estate (NEW; the constitutional enforcement):**
If `<handle>/rapp-estate-private` does NOT exist, the publish action invokes `tools/private_estate_init.py::init_private_estate()` automatically. This:
- Creates the private repo (`gh repo create --private`).
- Mints the operator's HMAC secret to `~/.brainstem/private-estate-secret` (mode 0600).
- Scaffolds the opaque file set (`meta.json`, `README.md`, `objects/.gitkeep`, `kinds/.gitkeep`).
- Returns the URL + commitment hash for the public beacon.

The publish action surfaces `auto_created_private: true` in its response so the operator sees what happened. Idempotent: re-publishing when the private estate already exists is a no-op.

**Operator opt-out (rare; produces non-compliance):**
Pass `skip_private_create=true` to the publish action. The auto-create is skipped; the beacon's `private_estate_pointer` + `private_estate_commitment` are empty; sniffers flag the operator as `compliance: legacy`. This exists for operators who insist on public-only mode on principle, but it's against Article XLVIII.

**Continuing steps:**

1. **Verify private estate exists** (always true after step 0 unless skip_private_create).
2. **Compute commitment hash.** sha256 of the private estate's normalized JSON tree (sorted by path, content concatenated). Deterministic; verifiable by anyone with read access.
3. **Audit URL opacity.** Run `tools/path_opacity.py::audit_paths()`. Any non-opaque path → REFUSE publish with clear error.
4. **Write public estate** (estate.json + beacon with `private_estate_pointer` + `private_estate_commitment` + `private_door_count`).
5. **Set `rapp-estate` topic on public repo** (Article XLVII discovery surface).

If any step fails, the publish is REVERTED (best-effort; the public repo's prior state remains the canonical view until publish completes successfully).

---

## §7.5 — This boundary applies on every substrate

The two-tier model defined here is **substrate-independent**. Whether your estate is served via GitHub raw, LAN HTTP + Bonjour, an AirDrop'd egg, or a sneakernet `file://` URL — the public/private boundary holds, the URL opacity contract holds, the receiver-controls discipline holds. See [`SUBSTRATE_FEDERATION.md`](./SUBSTRATE_FEDERATION.md) for the full substrate ladder (Articles XLVII.5 / .5.1 / .5.2 / .5.3).

A peer who receives your egg over AirDrop or sneakernet ALSO sees only your public estate from the egg by default — the private estate is referenced via `private_estate_pointer` in the bundled beacon, but the actual private content is in a separate (PRIVATE) repo or an encrypted file you exchange separately. The boundary doesn't dissolve when the substrate changes.

---

## §8 — Cross-references

- **CONSTITUTION Article XLVIII** — the boundary, in load-bearing form (6 subsections).
- **CONSTITUTION Article XLVI** — Estate Spec (rappid is the URL); applies to BOTH tiers.
- **CONSTITUTION Article XLVII** — Discoverability without a central registry; the public beacon is the discovery surface.
- **CONSTITUTION Article XXIII** — Specs travel with the planted repo; this spec ships in `specs/SPEC.md` §4.7 inside every planting.
- **`tools/path_opacity.py`** — the canonical opacity helper (`opaque_path`, `decode_local`, `audit_paths`).
- **`tools/private_estate_init.py`** — bootstraps a private estate; called by install + by `estate_agent.init_private`.
- **`rapp_brainstem/agents/estate_agent.py`** — `init_private`, `publish_private`, `fetch_private` actions; bumps beacon schema to 1.1.
- **`tools/sniff_network.py`** — surfaces `private_estate_pointer` existence; never fetches.
- **`tests/features/F15-private-estate.sh`** — 9-step conformance gate.

---

*The boundary is not optional. The URLs are not metadata. The private repo is not for advanced users. The operator's secret is not for the network. From day one — every operator, every estate, every URL — the substrate for real work is in place.*

<!-- RAPP1-HISTORICAL-SECTION-END -->
