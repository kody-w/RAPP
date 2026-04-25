---
title: Documentation Roadmap
status: living
section: Plans & Ledgers
type: roadmap
hook: Three horizons — Now / Next / Later — for documentation across the platform. Append items as they emerge.
---

# Documentation Roadmap

> **Hook.** Three horizons — Now / Next / Later — for documentation across the platform. Append items as they emerge.

This roadmap covers **all platform documentation**, not just the vault. It's the place where "we should write a thing about X" lives until the thing gets written. Each item answers four questions: *what / why / where it'll live / readiness signal*.

This is a living document. Add entries freely; never silently delete (move to the **Shipped** section instead so the history is visible).

## How to add an item

```
### <Title>

- **What.** One sentence.
- **Why.** One sentence — what need it serves.
- **Home.** Where the doc will live (vault note, marketing page, README section, …).
- **Ready when.** The signal that says "this is ready to write" — usually a code change has stabilized, a question has come up enough times, or a stakeholder has asked.
```

## Now — actively scoped

Items currently being written or staged for the next push.

### Pitch playbook → vault link

- **What.** Add a "What's behind this?" link from `pitch-playbook.html` to a curated subset of vault notes that match the playbook's narrative.
- **Why.** The pitch playbook is a high-traffic marketing surface. Linking it to the vault closes the loop from "marketing pitch" to "real reasoning."
- **Home.** `pitch-playbook.html` (one new section in the existing slide structure).
- **Ready when.** Anytime — deferred from Phase 7 of the vault build because it needs a custom slot in the slide narrative rather than a generic nav append.

### `make vault-check` (or shorter invocation)

- **What.** A short alias for `node tests/vault-check.mjs` so contributors can run the guardrail without remembering the path.
- **Why.** Friction-reduction. The current invocation is fine, but a shorter form encourages running it before every PR.
- **Home.** `Makefile` at repo root (would be a new file) or a `tests/check` shell wrapper.
- **Ready when.** Anytime.

### Apple Shortcuts harness (Watch / Siri / iPhone)

- **What.** A `.shortcut` file hosted at `installer/shortcuts/brainstem-voice.shortcut` that lets a user ask their brainstem questions via Siri on iPhone, iPad, Mac, or Apple Watch. The shortcut prompts for input via dictation, POSTs to a configurable brainstem URL, and speaks the `|||VOICE|||` portion of the response aloud.
- **Why.** Apple Watch + Siri become brainstem clients with **zero native code** — no watchOS app, no App Store review, no code signing, no per-OS-version regression testing. Distribution is the same shape as everything else (iCloud share link or hosted file). See [[Surfaces — Mobile, Watch, Voice]].
- **Home.** `installer/shortcuts/` (new subdirectory). The README.md there documents the protocol so other authors can ship their own brainstem-compatible Shortcuts.
- **Ready when.** Now — the brainstem already emits the `|||VOICE|||` slot designed for TTS, so the protocol is in place. The work is creating the Shortcut bundle (requires a Mac with Shortcuts.app), exporting it, and writing the install / configure docs.

### Android automation parallel

- **What.** Equivalent to the Apple Shortcuts entry, but for Android — a Tasker action or a Google Assistant routine that POSTs to the brainstem and speaks the response.
- **Why.** Symmetry. iPhone gets Siri; Android should get an equivalent path before the surfaces story is complete.
- **Home.** `installer/automations/android/` (parallel to `installer/shortcuts/`).
- **Ready when.** After the Apple Shortcut ships and the protocol is proven on the iOS side.

## Next — scoped, not yet started

Items the platform needs but that are blocked on something else (capacity, a code change, a decision).

### Tier 2 deploy walkthrough

- **What.** A step-by-step guide to deploying `rapp_swarm/` to Azure Functions, including the vendoring step, identity setup, and the smoke test.
- **Why.** Tier 2 is the most-skipped tier in evaluations because the deploy story is implicit in the build script.
- **Home.** `rapp_swarm/README.md` (operational) + `pages/vault/Tier 2 — Cloud Swarm.md` (conceptual).
- **Ready when.** `tests/e2e/05-tier2-cloud.sh` is green on the current branch — that's the signal that the deploy path is reproducible.

### Tier 3 publish walkthrough

- **What.** Publishing a Power Platform solution from a Tier-1-developed agent.
- **Why.** Closes the partner-handoff story — the file proceeds from `rapp_brainstem/` to a customer's tenant via the published solution zip.
- **Home.** `worker/README.md` + a new vault note `Tier 3 — Enterprise Power Platform.md`.
- **Ready when.** The current `MSFTAIBASMultiAgentCopilot_*.zip` flow is documented end-to-end and a fresh tenant can install it from the README alone.

### Authoring an agent — the canonical guide

- **What.** A single doc that walks from blank file to a working `*_agent.py` with metadata, `perform()`, optional `data_slush`, and tier-portability checks.
- **Why.** New contributors regularly ask "how do I write an agent?" and there is currently no single answer that's neither too thin (the existing example agents) nor too theoretical (the constitution).
- **Home.** `docs/agent-authoring.md` (the operational guide) + a vault note `[[The Agent IS the Spec]]` (the concept).
- **Ready when.** Phase 2 of the vault build is done — the conceptual posts will give the operational doc somewhere to link.

### Service authoring — the canonical guide

- **What.** Companion to the agent-authoring guide, for the single-file HTTP services declared in CONSTITUTION Article III (Sacred Constraint #2).
- **Why.** Services are newer and have less precedent in the repo; the convention is at risk of drifting.
- **Home.** `docs/service-authoring.md` + a vault note (TBD title).
- **Ready when.** At least three published services exist in `rapp_store/`. (Currently: `dashboard`, `kanban`, `webhook`. ✅ ready, just not started.)

## Later — known gaps not yet scoped

Items the platform should eventually have docs for, but where the underlying thing is still moving fast.

- **The vibe builder.** What it does, the loop it runs, the calibration signals it consumes. Wait until the agent settles into its current shape.
- **The swarm factory pattern.** A vault note explaining how `swarm_factory_agent` produces composed pipelines without becoming a router. Wait for the next workshop run that uses it heavily.
- **The rapp store contract.** What makes a directory in `rapp_store/` a valid rapplication, the manifest schema, the publish workflow. Wait for v1 of the manifest schema to stabilize.
- **The skill.md / rapplication-sdk.md story.** A vault note covering the *AI-readable skill* pattern — what `pages/docs/skill.md` is for, why it's distinct from `SPEC.md`, who consumes it.
- **The card pattern (live index card).** Recently shipped (commit `dd1434b`). Worth a vault note once a second card-shaped artifact has been built, so the post can compare two real instances rather than describing one in the abstract.
- **Provider dispatch beyond GitHub Copilot.** Once Anthropic and Azure OpenAI paths have parity test coverage, document the swap.

## Shipped

Items that started in *Now* or *Next* and have been published. **Append-only — never delete from this list.** Each entry has a date and a pointer to the artifact.

- **2026-04-24** · CONSTITUTION Article XVI extended with repo-root discipline rules. → `CONSTITUTION.md` lines 639–696.
- **2026-04-24** · CONSTITUTION Article XXIII added — *The Vault Is the Long-Term Memory*. → `CONSTITUTION.md` lines 1131–1241 (approx).
- **2026-04-24** · Vault scaffold — 28 markdown notes (26 stubs + welcome + index) under `vault/`. → `vault/`.
- **2026-04-24** · Static vault viewer — fetch-from-GitHub renderer with wikilinks, backlinks, search, JSZip export, drop-zip import, localStorage cache. → `pages/vault/`.
- **2026-04-24** · `CLAUDE.md` Key Directories table updated with `vault/`, `pages/`, `pages/docs/` entries and the *write the why here* instruction.
- **2026-04-24** · Repo-root cleanup — 10 marketing HTMLs moved to `pages/`, 2 docs moved to `pages/docs/`, all canonical / og:url URLs and tests updated. → `pages/`, `pages/docs/`, `tests/e2e/08-html-pages.sh`.
- **2026-04-24** · Vault build-out (Phases 1–8) — 26 stubs converted to published essays, 9 foundational notes, 5 reading paths, viewer polish (keyboard nav, anchor links, Open-in-Obsidian, mobile breadcrumb, reading mode, SVG graph view), `tests/vault-check.mjs` link/PII guardrail, README + SPEC + 10 marketing pages tied back to the vault. → `vault/` (46 notes), `pages/vault/`, `tests/vault-check.mjs`. See [[Vault Build-Out Plan]] and [[Release Ledger]].
- **2026-04-24** · Repo restructure — install scripts → `installer/`, platform docs → `pages/docs/`, Tier 3 zip → `installer/` (briefly tried `rapp_studio/`, folded back same session — see [[Repo Root Reorganization 2026-04-24]]). Each kept subdir gained a `README.md` with scale rules. CLAUDE.md updated; sacred constraints expanded from 4 to 6. Install one-liner URL changed from `RAPP/install.sh` to `RAPP/installer/install.sh`.
- **2026-04-24** · Root cleanup pass 2 — `vault/` and `docs/` moved under `pages/`. Root down to 12 entries; `installer/` and `tests/` kept at root (install URL is sacred per Article V; tests aren't pages). All references updated; `vault-check.mjs` now scans `pages/vault/`; 598 wikilinks still resolve.
- **2026-04-24** · PWA shipped on both web surfaces — `pages/vault/` and `rapp_brainstem/web/` are now installable on every desktop + mobile browser, offline-resilient. Vault uses stale-while-revalidate for markdown so notes are instant offline; brainstem caches its UI shell but passes `/chat` and API calls through to the network. iOS meta tags + manifest + SW + SVG icons. See [[Surfaces — Mobile, Watch, Voice]].
- **2026-04-24** · "RAPP monorepo" → "RAPP platform" across CLAUDE.md, CONSTITUTION.md, README.md, vault notes, and the viewer chrome. The platform reaches further than one repo; the term should reflect that.

## Related

- [[Vault Build-Out Plan]]
- [[Release Ledger]]
- [CONSTITUTION](https://github.com/kody-w/RAPP/blob/main/CONSTITUTION.md) Article XXIII
