# ESTATE_SPEC — The Rappid Is The Global Address

> **Schema:** `rapp-estate/1.1` · **Status:** Constitutional (Article XLVI) · **Authority:** this file · **First shipped:** 2026-05-09

This is the load-bearing spec for **how any door (twin or neighborhood) is discovered and addressed across the network**. It locks in a property the rappid format has always implied but the codebase had not enforced: from a single rappid string, with zero auth and zero API calls, you can compute every canonical URL the door has and fetch its full identity from `raw.githubusercontent.com`.

If you are writing a planter, an estate agent, a federation walker, a holocard renderer, a discovery UI, or any code that maps from "I have a rappid" → "I want to read the door" — this spec is the contract. There are no fallbacks; the spec describes what is true.

> **2026-05-10 — estate is portable:** the entire estate (every door, every rappid, the door catalog, the public/private/on-device tiers per [`PUBLIC_PRIVATE_BOUNDARY.md`](./PUBLIC_PRIVATE_BOUNDARY.md)) is a planned `brainstem-egg/2.3-estate` cartridge. Substrate-migrate the whole identity by exporting → AirDropping/sneakernetting → re-anchoring on the new substrate via [`egg_hatcher_agent.py`](../../rapp_brainstem/agents/egg_hatcher_agent.py). The estate cartridge is the missing identity-portability primitive — paired with the rappid-as-global-address property below, the operator's whole digital identity becomes substrate-agnostic. See [SPEC.md §18.10](./SPEC.md) family table.

---

## 1. The rappid IS the URL

The canonical v2 rappid format:

```
rappid:v2:<kind>:@<owner>/<repo>:<32-hex-no-dashes>@github.com/<owner>/<repo>
```

The `<owner>/<repo>` segment appears **twice** by design — first as the abbreviated identity reference, then as the full origin pin. Both MUST be the same string. A rappid where they disagree is invalid and MUST be rejected (Article XLVI.5).

From this string alone, by **string parsing** (not lookup, not config, not env), you derive:

| Field | How |
|---|---|
| `kind` | The token between `rappid:v2:` and `:@` |
| `owner` | Everything after `@` and before `/` in the first segment |
| `repo` | Everything after `/` and before `:` in the first segment |
| `door_type` | `"front_door"` if `kind == "twin"`, else `"gate"` (XLVI.2) |

**Valid kinds** (frozen as of 2026-05-09): `twin`, `neighborhood`, `ant-farm`, `braintrust`, `workspace`, `hatched`, `rapplication`, `prototype`, `operator`. Adding a new kind requires a CONSTITUTION amendment because every consumer derives behavior from this token.

---

## 2. The Canonical Door URL Set

Every planted door MUST be reachable at these URLs. The planter MUST emit each one as appropriate to the door's type. A consumer holding a rappid MUST be able to fetch any of these URLs without an API call:

| # | Name | URL pattern | Required for |
|---|---|---|---|
| 1 | `repo` | `https://github.com/<owner>/<repo>` | all (the canonical browsing URL) |
| 2 | `front` | `https://<owner>.github.io/<repo>/` | all (the heimdall snapshot — the operator-facing chat surface) |
| 3 | `identity` | `https://raw.githubusercontent.com/<owner>/<repo>/main/rappid.json` | all (`rapp-rappid/2.0`) |
| 4 | `holocard` | `https://raw.githubusercontent.com/<owner>/<repo>/main/card.json` | all (`rappcards/1.1.2`) |
| 5 | `holo_md` | `https://raw.githubusercontent.com/<owner>/<repo>/main/holo.md` | all (the friendly entry doc) |
| 6 | `avatar` | `https://raw.githubusercontent.com/<owner>/<repo>/main/holo.svg` | all (procedural sprite) |
| 7 | `summon_qr` | `https://raw.githubusercontent.com/<owner>/<repo>/main/holo-qr.svg` | all (QR encoding the front-door URL) |
| 8 | `members` | `https://raw.githubusercontent.com/<owner>/<repo>/main/members.json` | gates only (`rapp-neighborhood-members/1.0`) |
| 9 | `facets` | `https://raw.githubusercontent.com/<owner>/<repo>/main/facets.json` | all (`rapp-facets/1.0` — the door's published-capability declaration) |

**The .nojekyll + index.html invariant.** A planted door's index.html serves the heimdall front-door grail; for that to work over GitHub Pages, the repo MUST contain a `.nojekyll` file at root. The planter emits it. The backfill enforces it.

**The specs/ invariant.** Per "specs travel with the planted repo" (CONSTITUTION Article XXIII; memory: `feedback_specs_travel_with_planting.md`), every planted door MUST also carry the `specs/` bundle (RAPPID_SPEC, HOLOCARD_SPEC, ANTIPATTERNS, SOUL_IDENTITY, PARTICIPATION, AGENT_SPEC, RAPPLICATION_SPEC, SENSE_SPEC, the kind-specific protocol, and **ESTATE_SPEC** as of bundle v1.1.0).

---

## 3. The Estate Stores Only Rappid + Provenance

The user's **estate** is the door catalog — every door they own (`created`) plus every door they're a contributor in (`member`). It lives in two places:

- **Local source of truth:** `~/.brainstem/estate.json`
- **Public mirror (optional):** `https://raw.githubusercontent.com/<github-handle>/rapp-estate/main/estate.json`

Per Article XLVI.3, each entry stores **only**:

```json
{
  "rappid": "rappid:v2:twin:@owner/repo:hex@github.com/owner/repo",
  "added_at": "2026-05-09T00:00:00Z",
  "via": "created" | "scan" | "manual" | "import" | "published-by-other"
}
```

Everything else (owner, repo, kind, door_type, name, summon_url, holocard URL, all 9 canonical URLs) is **DERIVED** at read time via `door_from_rappid(rappid)`. There are no stored fallback fields. There are no patched URLs. If the rappid changes, every derived field updates. If the rappid is invalid, the entry surfaces as an error — never silently fixed up.

This is the constitutional answer to *"don't do all of these exception things."*

### 3.1 The full estate.json schema

```json
{
  "schema": "rapp-estate/1.1",
  "owner": {
    "rappid": "rappid:v2:operator:@<github>/<their-twin-or-brainstem>:hex@github.com/<github>/...",
    "github": "<github-handle>"
  },
  "created": [{ "rappid": "...", "added_at": "...", "via": "created" }],
  "member":  [{ "rappid": "...", "added_at": "...", "via": "scan" }],
  "updated_at": "2026-05-09T00:00:00Z"
}
```

The `owner.rappid` is the operator's **personal** rappid — minted once at first install, lives at `~/.brainstem/rappid.json`. It is the universal anchor for both sides of the estate:

- **As ancestor** of `created[]`: every door the operator planted has `parent_rappid = owner.rappid` in its own `rappid.json`.
- **As member-proof** for `member[]`: every gate the operator joined lists `owner.rappid` in its own `members.json`.

The same identity, two roles. No additional ID system needed.

---

## 4. Discovery Is Pure Raw Fetch

A consumer MUST be able to discover any door, and any user's full estate, with `curl` alone. No `gh` CLI, no API token, no rate limit (for public repos), no auth.

### 4.1 Discover one door from its rappid

```bash
# From the rappid, parse <owner>/<repo>:
RAPPID='rappid:v2:twin:@kody-w/echo-brainstem:abc...@github.com/kody-w/echo-brainstem'
OWNER_REPO=$(echo "$RAPPID" | sed 's|.*:@\([^:]*\):.*|\1|')

# Fetch identity, holocard, holo.md, etc.:
curl -fsSL "https://raw.githubusercontent.com/${OWNER_REPO}/main/rappid.json"
curl -fsSL "https://raw.githubusercontent.com/${OWNER_REPO}/main/card.json"
curl -fsSL "https://raw.githubusercontent.com/${OWNER_REPO}/main/holo.md"
```

### 4.2 Discover a user's full estate from their GitHub handle

```bash
# A single roundtrip, no auth, no API:
curl -fsSL "https://raw.githubusercontent.com/<github-handle>/rapp-estate/main/estate.json"
```

This returns the full door catalog. From there, every entry's rappid expands to the door's own URL set via `door_from_rappid()`.

### 4.3 The chain rule

To enumerate every door in a user's reach: fetch their estate → for each entry's rappid, fetch the door's `rappid.json` → if you want to walk into a gate's membership, fetch its `members.json` → each member's rappid expands to their estate URL. Federation is a graph walk over pure raw fetches.

---

## 5. The `door_from_rappid` Derivation Contract

Every consumer that maps rappid → door URLs MUST use a function with this contract:

```python
def door_from_rappid(rappid: str) -> dict:
    """Return the canonical door object for a rappid. Pure function.

    Returns:
      {
        "rappid": str,
        "owner": str,
        "repo": str,
        "kind": str,
        "door_type": "front_door" | "gate",
        "urls": {
          "repo": "https://github.com/<owner>/<repo>",
          "front": "https://<owner>.github.io/<repo>/",
          "identity": "https://raw.githubusercontent.com/<owner>/<repo>/main/rappid.json",
          "holocard": "https://raw.githubusercontent.com/<owner>/<repo>/main/card.json",
          "holo_md": "https://raw.githubusercontent.com/<owner>/<repo>/main/holo.md",
          "avatar": "https://raw.githubusercontent.com/<owner>/<repo>/main/holo.svg",
          "summon_qr": "https://raw.githubusercontent.com/<owner>/<repo>/main/holo-qr.svg",
          "members": "https://raw.githubusercontent.com/<owner>/<repo>/main/members.json",  # gates only
          "facets": "https://raw.githubusercontent.com/<owner>/<repo>/main/facets.json"
        }
      }

    Raises:
      InvalidRappidError if the string is not a valid v2 rappid OR if the
      <owner>/<repo> appears differently in the two segments.
    """
```

Implementation lives at `tools/door_address.py`. Imported by `plant_seed_agent.py`, `estate_agent.py`, and any future federation/discovery consumer. One implementation, one contract — no per-consumer reinventions.

---

## 6. Disaster Recovery — The Estate Is Recomputable

The estate file is a **cache** of relationships the network already publishes. Both copies (`~/.brainstem/estate.json` locally and `<handle>/rapp-estate/main/estate.json` publicly) can be reconstructed from scratch given just the operator's GitHub handle. **This is the load-bearing property the spec exists to guarantee.** If both caches are gone, the rebuild walks public data and produces an identical estate.

### 6.1 The two relationships, both publicly visible

- **Created** — every door the operator planted has its `rappid.json` carry `parent_rappid = <operator-rappid>`. Discovery: walk `<handle>/*` repos, fetch each `rappid.json`, filter on `parent_rappid` matching the operator.
- **Member** — every gate the operator joined lists their rappid in `members.json`. Discovery: search public GitHub for any `members.json` containing the operator's rappid string.

### 6.2 The rebuild procedure

```bash
python3 tools/rebuild_estate.py --handle <gh>            # dry-run, prints
python3 tools/rebuild_estate.py --handle <gh> --apply    # writes ~/.brainstem/estate.json
```

Pseudo-code:

```python
def rebuild(handle):
    operator_rappid = discover_operator(handle)            # § 6.3
    created = []
    for repo in gh_repo_list(handle):
        rappid_meta = raw_fetch(handle, repo, "rappid.json")
        if rappid_meta and rappid_meta["parent_rappid"] == operator_rappid:
            created.append({"rappid": rappid_meta["rappid"], "added_at": now(), "via": "rebuild"})
    member = []
    for hit in gh_search_code(operator_rappid, filename="members.json"):
        gate = raw_fetch_rappid_json(hit.repo)
        member.append({"rappid": gate["rappid"], "added_at": now(), "via": "rebuild"})
    return {"schema": "rapp-estate/1.1", "owner": {...}, "created": created, "member": member}
```

### 6.3 Operator-rappid discovery

The rebuild needs to know the operator's personal rappid before it can filter `parent_rappid` matches. Discovery order:

1. **Local** — `~/.brainstem/rappid.json` (fast path when the operator runs the rebuild on their own machine).
2. **Conventional repos** — `<handle>/<handle>-twin`, `<handle>/<handle>-brainstem`, `<handle>/.brainstem`, plus operator-specific anchors. If any has a valid rappid, derive the operator rappid by ensuring `kind` is `operator` (swap from `twin` if necessary; same owner/repo/hex).
3. **Repo scan** — walk `<handle>/*` for any `rappid.json` with `kind=operator` or `kind=twin` matching the conventional pattern.
4. **Operator hint** — if all automatic discovery fails, the operator passes `--operator-rappid <rappid>` explicitly.

### 6.4 The constitutional invariant

Per Article XLVI.6:
- Every planted door's `rappid.json` MUST set `parent_rappid` to the planter's personal rappid (NOT to None, NOT to the species root). The planter (`plant_seed_agent.py`) enforces this on every new plant; `tools/backfill_seeds.py --patch-parents <op-rappid>` brings older plantings into compliance.
- The rebuild tool is operator-tooling, but the **property** it proves is load-bearing: relationships are knowable from public data. Losing local state is recoverable.

### 6.5 What this enables

- **Disaster recovery**: laptop dies, no backup → the estate rebuilds from any other device with `gh` auth.
- **Drop-in rappid lookup**: pass any rappid to `estate fetch rappid=<rappid>` → the agent parses, traces `parent_rappid` if needed, and fetches whoever owns that door's published estate. No local state required.
- **Federation auditing**: anyone can verify a published estate's claims by running the rebuild for the same handle and comparing results.

---

## 7. Adoption + Compliance

- **All NEW plantings** (after this spec ships) emit the full Door URL Set. No exceptions.
- **All EXISTING plantings** are backfilled by `tools/backfill_seeds.py` — runnable any time, idempotent. The script downloads each known seed's `rappid.json`, validates it against the spec, and PUTs the missing canonical files. It is the operator's responsibility to run it for plantings created before 2026-05-09.
- **Stale rappids** (where the `<owner>/<repo>` doesn't match the actual hosting URL) are rejected by `door_from_rappid()` and reissued by the backfill script (the historical `sim-art-collective` case is the canonical example).

---

## 6.5 Substrate-Agnostic Federation (Article XLVII.5)

This spec defines the rappid as the global address. **What URL substrate that address is fetched over** is a separate concern, covered in [`SUBSTRATE_FEDERATION.md`](./SUBSTRATE_FEDERATION.md). The four substrates — GitHub raw, LAN HTTP + Bonjour, AirDrop'd egg cartridges, sneakernet `file://` — all serve the same rappid-keyed JSON. The estate spec applies uniformly across all of them.

The TL;DR: an operator's estate.json + beacon are reachable via:

- `https://raw.githubusercontent.com/<handle>/rapp-estate/main/...` (default)
- `http://<lan-ip>:8080/...` (LAN, via `tools/lan_advertise.py`)
- AirDrop'd `.egg` extracted to a peer's machine (the egg bundles the federation tools)
- `file://...` URLs from sneakernet-imported eggs (`tools/import_peer_egg.py`)

The sniffer (`tools/sniff_network.py`) walks all four substrates uniformly. Authority for the substrate model: SUBSTRATE_FEDERATION.md + CONSTITUTION Article XLVII.

---

## 7. Public/Private Boundary (Article XLVIII)

**The two-tier estate is mandatory from first install.** Discovery is public (this spec); substance is private. Every operator gets BOTH `<handle>/rapp-estate` (public) AND `<handle>/rapp-estate-private` (private GitHub repo). The public beacon's `private_estate_pointer` + `private_estate_commitment` + `private_door_count` (REQUIRED in `rapp-network-beacon/1.1`) advertise the existence and integrity of private state without leaking what it contains. URLs inside the private repo are opaque (Article XLVIII.6) so even a 404 reveals nothing.

Authority: [`pages/docs/PUBLIC_PRIVATE_BOUNDARY.md`](./PUBLIC_PRIVATE_BOUNDARY.md). Constitutional anchor: CONSTITUTION Article XLVIII (6 subsections). Conformance: `tests/features/F15-private-estate.sh` (10 steps).

---

## 8. Cross-references

- **CONSTITUTION Article XLVI** — the principles in load-bearing form.
- **CONSTITUTION Article XXXIV** — Rappid: Lineage Tracking and Variant Species (where the format originated).
- **CONSTITUTION Article XXIII** — the vault as long-term memory; specs travel with plantings.
- **CONSTITUTION Article XLII** — the global substrate is GitHub Raw + Issues (this spec is the formal version of that article's promise).
- **`specs/RAPPID_SPEC.md`** (bundled in every planting) — the format definition itself.
- **`specs/HOLOCARD_SPEC.md`** — the rappcards/1.1.2 schema for `card.json`.
- **`tools/door_address.py`** — the pure derivation implementation.
- **`rapp_brainstem/agents/estate_agent.py`** — the local-first agent that reads/writes the estate.
- **`rapp_brainstem/agents/plant_seed_agent.py`** — the planter that emits the Door URL Set on every new plant.
- **`tests/features/F13-estate-spec.sh`** — conformance gate.

---

*The rappid encodes the address. The address encodes the door. The door encodes the contract. There is no other map.*
