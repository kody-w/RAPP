---
title: Estate Spec — rappid as the global address
date: 2026-05-09
status: shipped
authority: pages/docs/ESTATE_SPEC.md, CONSTITUTION Article XLVI
tags: [estate, rappid, article-xlvi, address-space, no-fallbacks]
---

# Estate Spec — rappid is the global address

## What we shipped

A constitutional Article (XLVI) that locks in: the rappid IS the address. From any v2 rappid string, by string parsing alone, every canonical URL the door has is computable. Discovery happens through `raw.githubusercontent.com` — no auth, no API, no rate limit, no SDK. The estate is the door catalog. There are no fallbacks; the spec describes what is true.

The full implementation set:

- `pages/docs/ESTATE_SPEC.md` — the canonical spec (the source of truth that consumers conform to).
- `tools/door_address.py` — the SINGLE rappid parser. `door_from_rappid(rappid)` returns the full door object (owner, repo, kind, door_type, all 9 canonical URLs). Pure stdlib. Zero dependencies. Per-consumer reimplementations are constitutionally forbidden.
- `CONSTITUTION.md` Article XLVI — five subsections that pin the spec into governance: rappid determines URL, the canonical Door URL Set, the estate stores only rappid + provenance, discovery is pure raw fetch, no fallbacks.
- `specs/SPEC.md` (the god spec) + `specs/skill.md` (the runbook) — bundle 2.0.0 of `front_door_specs.py`. Replaces the prior 9-file spec bundle. One spec, one runbook, one kind-specific protocol per planting (3 files instead of 14).
- `rapp_brainstem/agents/estate_agent.py` — simplified to use `door_from_rappid()` everywhere. Estate entries are stored as exactly `{rappid, added_at, via}`. Invalid rappids are surfaced as errors, never silently fixed up.
- `rapp_brainstem/agents/plant_seed_agent.py` — emits `facets.json` for both kinds, emits empty `members.json` for twins, passes only rappid+via to estate-append. Every new plant is spec-compliant from birth.
- `tools/backfill_seeds.py` — one-shot operator-tooling that brought all 16 existing kody-w/* seeds into compliance. 75 PUTs, idempotent.
- `tests/features/F13-estate-spec.sh` — 11-step conformance gate. Green.

## Why this became constitutional (the fallback hell)

The estate agent I shipped first had `_enrich_entry()` — a helpful little function that tried to derive `door_type` from `kind`, then `summon_url` from `entry["url"]`, then from rappid, then guarded against the stale `local.github.io` URL it found in `sim-art-collective`. Each fallback was thoughtful. Each was admitting the contract wasn't formal yet.

The compliance audit revealed why: 15 seeds had `rappid.json` files, but **14 of them had bare-UUID rappids** like `41000c66-fa31-4db4-8e0a-d82537f82c4a` from a pre-v2-format planter version. The 15th was `sim-art-collective` with a `@local/local-art-collective` rappid that no longer matched its actual GitHub URL. Files existed; rappids didn't. The estate agent's enrichment was compensating for the planter's drift.

The operator's reaction was load-bearing:

> *"this is the point to write the estate spec... and update the planter for those going forward that are planted and we can retroactively backfill what we created to make them compliant... don't do all of these exception things... let's get it right from the beginning. we have the global door/gate real estate FOR THIS REASON!!!!! make it constitutional ... the rappid is like the unique address for this front gate because this can then be found globally from pure githubrawuserdata IF we set this up correctly."*

The diagnosis was right: every fallback was a missed opportunity to formalize. The cure was the spec — and making it constitutional so the temptation to add another fallback in some future agent is constitutionally rejected before it lands.

## The "rappid is the URL" insight

The v2 rappid format is `rappid:v2:<kind>:@<owner>/<repo>:<32hex>@github.com/<owner>/<repo>`. The `<owner>/<repo>` segment appears **twice by design** — once as the abbreviated identity reference, once as the origin pin. This was always there. We just hadn't formalized that those segments are not just *consistent* with the GitHub repo URL — they ARE the GitHub repo URL.

From a single rappid string, by parsing:
- `https://github.com/<owner>/<repo>` (repo)
- `https://<owner>.github.io/<repo>/` (front door — the sphere)
- `https://raw.githubusercontent.com/<owner>/<repo>/main/rappid.json` (identity)
- ...and 6 more

Nine URLs. All reachable through `raw.githubusercontent.com` without a single API token. The address space was always there; the spec just makes it load-bearing.

## The god-spec consolidation (bonus simplification)

Mid-execution the operator asked a sharper question: *"should we make one god spec that goes with the planter and then also a skill.md that goes with the god spec so when we feed it to any AI they know how to participate in this global network as a 1st class citizen (only requirement is a github account to set up their own estate)."*

Yes. Bundle 1.0.0 shipped 9 separate spec files per planting (HOLOCARD_SPEC, RAPPID_SPEC, ANTIPATTERNS, SOUL_IDENTITY, PARTICIPATION, AGENT_SPEC, RAPPLICATION_SPEC, SENSE_SPEC, README). Bundle 2.0.0 ships ONE god spec (`SPEC.md`) plus ONE runbook (`skill.md`) plus the kind-specific protocol — 3 files. The 9 deep specs collapse into SPEC.md sections §2–§11. The skill.md frames the entire onboarding as: "you can become a 1st-class citizen with one requirement — a GitHub account." Six steps.

This is the moment the platform's "feed me to any AI" proposition became literal. Hand `https://raw.githubusercontent.com/kody-w/RAPP/main/specs/skill.md` to any LLM. After it reads, it knows how to plant a door, emit an estate, summon any other door, and join any gate. No further docs needed.

## What's load-bearing forever

- **`door_from_rappid()` is the single parser.** Every consumer imports it. Per-consumer parsers are constitutionally forbidden (Article XLVI.5).
- **Estate entries are `{rappid, added_at, via}`.** Stored derived fields are stripped on save. Invalid rappids surface as errors.
- **9 canonical URLs per door.** The planter MUST emit them. The backfill enforces them.
- **Pure raw fetch is the discovery substrate.** No agent walks the GitHub API for door lookup; everything goes through `raw.githubusercontent.com`.
- **Reissue, never patch.** Stale rappids get reissued via the backfill script. Consumers never silently fix them up.

## The audit's punchline

After the backfill: **16/16 seeds compliant**. The dry-run reports 0 actions planned. Every door has its 9 canonical URLs. Every URL resolves through pure raw fetch. The estate agent runs zero fallback code paths.

The fallback hell isn't just gone — it's been made constitutionally impossible to come back. That's the difference between a clean refactor and a real lock-in.

---

## Cross-references

- Spec: [`pages/docs/ESTATE_SPEC.md`](../../docs/ESTATE_SPEC.md)
- God spec: [`specs/SPEC.md`](../../../specs/SPEC.md)
- Runbook: [`specs/skill.md`](../../../specs/skill.md)
- Parser: [`tools/door_address.py`](../../../tools/door_address.py)
- Estate agent: [`rapp_brainstem/agents/estate_agent.py`](../../../rapp_brainstem/agents/estate_agent.py)
- Planter: [`rapp_brainstem/agents/plant_seed_agent.py`](../../../rapp_brainstem/agents/plant_seed_agent.py)
- Backfill: [`tools/backfill_seeds.py`](../../../tools/backfill_seeds.py)
- Conformance: [`tests/features/F13-estate-spec.sh`](../../../tests/features/F13-estate-spec.sh)
- Constitution: [`CONSTITUTION.md`](../../../CONSTITUTION.md) Article XLVI
- Companion vault notes:
  - [`2026-05-09 — Bond Pulse — the on-going beat for the full organism`](2026-05-09%20%E2%80%94%20Bond%20Pulse%20%E2%80%94%20the%20on-going%20beat%20for%20the%20full%20organism.md) — the heartbeat that keeps local + global in sync
