# PUBLIC_PRIVATE_BOUNDARY — The Two-Tier Estate (Mandatory)

> **Schema:** `rapp-private-estate/1.0` · **Status:** Constitutional (Article XLVIII) · **Authority:** this file · **First shipped:** 2026-05-09 · **Bumps:** `rapp-network-beacon/1.0` → `1.1`

This is the spec for the platform's two-tier estate model. **Every Article-XLVIII-compliant operator has BOTH a public estate AND a private estate from first install.** The public estate is the discovery surface (rappid, door catalog, beacon, federation feed). The private estate is the substance surface (PII, contacts, mailbox content, conversation history, private trust signals). Both are first-class infrastructure; neither is opt-in.

This spec also introduces **URL opacity** as a load-bearing privacy property: the URLs themselves inside the private repo cannot be allowed to leak semantic information, because URLs surface in beacons, error pages, agent logs, browser history, and 404 responses to unauthorized viewers. A URL is metadata even when its content is access-gated.

If you are writing a planter, an estate agent, a sniffer, a mailbox client, a witness cache, or any code that touches an operator's content — this is the contract.

---

## §1 — Why two tiers (and why mandatory)

A public-only estate is a toy. The federation primitives that make the platform useful for real work — Inbox, Bilateral Channel, Web of Trust private signals, Presence opt-in, secret ballots — cannot exist on a public-only substrate. Real work involves PII (real names, contacts, dated correspondence, decisions you don't want indexed by search engines).

If private is opt-in, the dominant outcome is operators stay public-only because it's "easier" — and then they leak PII to public when real work happens, OR they leave the platform when real work needs to happen. Both outcomes destroy the platform's value.

**Article XLVIII makes the two-tier estate mandatory from first install.** Every operator gets both `<handle>/rapp-estate` (public) and `<handle>/rapp-estate-private` (private GitHub repo) atomically. The private estate may be empty at install (no PII yet to land); the substrate is what matters. Adding PII later doesn't require an architectural upgrade.

**Cost:** one additional free private repo per operator. GitHub's free tier supports unlimited private repos for individuals.

**Benefit:** the platform is structurally usable for sensitive work, not just public showcase.

---

## §2 — The boundary (what goes where)

| Lives in PUBLIC estate | Lives in PRIVATE estate |
|---|---|
| Operator's personal rappid | Real names of contacts |
| Door catalog (rappids only) | Email addresses, phone numbers |
| Beacon (`.well-known/rapp-network.json`) | Mailbox content (received + sent) |
| Federation feed (`feed.jsonl`) | Bilateral channel transcripts |
| Witness cache of OTHERS' public estates | Private trust signatures |
| Activity timeline (own actions, public-shaped) | Personal memory / journal entries |
| `private_estate_pointer` + commitment hash | Conversation history with patients/clients/partners |
| `private_door_count` (transparency, no leak) | Private door rappids (doors not advertised publicly) |
| ZERO PII | All PII |

**The bridge:** the public beacon's `private_estate_pointer` field tells anyone who lands on the public estate: "this operator has private content; if you're authorized, fetch from `<that URL>` via `gh api` with your auth." Sniffers SURFACE the existence (count + commitment), NEVER attempt to fetch.

**What the public never sees:** the contents of the private estate, its internal paths, the names of recipients, topic strings, dates of correspondence, or any other metadata that would allow an unauthorized viewer to characterize the private content.

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
    "rappid": "rappid:v2:operator:@<handle>/<repo>:<hex>@github.com/<handle>/<repo>",
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

## §7 — The publish flow (atomic two-tier)

The estate agent's `publish` action (Article XLVIII.1 enforces atomicity):

1. **Verify private estate exists.** If `<handle>/rapp-estate-private` doesn't exist, INVOKE `init_private` first. No public publish can occur without a private estate present.
2. **Compute commitment hash.** sha256 of the private estate's normalized JSON tree (sorted by path, content concatenated). Deterministic; verifiable by anyone with read access.
3. **Audit URL opacity.** Run `tools/path_opacity.py::audit_paths()`. Any non-opaque path → REFUSE publish with clear error.
4. **Write public estate** (estate.json + beacon with `private_estate_pointer` + `private_estate_commitment` + `private_door_count`).
5. **Set `rapp-estate` topic on public repo** (Article XLVII discovery surface).

If any step fails, the publish is REVERTED (best-effort; the public repo's prior state remains the canonical view until publish completes successfully).

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
