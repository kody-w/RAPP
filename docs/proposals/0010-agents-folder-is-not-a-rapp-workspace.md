# Proposal 0010 — The Brainstem's agents folder is not a RAPP Workspace

> **Current RAPP/1 authority (rev-5).** For canonicalization, identity, frames,
> wire, eggs, registry, trust, and protocol evolution, follow
> [`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../RAPP1_STATUS.md). This proposal changes none of
> them. It only says which "workspace" this repository's constitution means.
> It changes no code, no agent file, no grail byte and no token.

## Status

**Draft, not accepted.**

An AI agent drafted this proposal for gap G22 of the RAPP/1 LTS lock-in and
pushed it to the experimental branch `experimental/gap-g22-workspace-names`
only. It opens no pull request and merges nothing. It does not edit
`CONSTITUTION.md`: the exact amendment text is below, and a constitutional
amendment needs the maintainer's deliberate human merge (Articles XXVIII.4
and XXX.2).

**Revision 2.** An independent review of the first draft (round 1: one high,
one medium and five low findings) found that the draft's name for `agents/`,
"agents workspace", is already RAR's name for something else. This revision
names `agents/` the **Brainstem's agents folder**, the words the ecosystem
already uses for it, adds the record-level `workspace` door kind, and
answers every other finding; see "Review round 1 disposition". The file moved
from `0010-agents-workspace-is-not-a-rapp-workspace.md` to this path, so that
its permanent name does not carry the refused term.

**Numbering.** `docs/proposals/` does not exist on `main`. Proposals 0001
(`experimental/constitution-live-agents`) and 0002
(`experimental/proposal-0002-tier2-parity`) are drafts on their own branches.
This workstream drafts RAPP proposals in the range 0010 to 0019, so parallel
drafts cannot take the same number. This one is 0010.

## Gap

**G22 — "Workspace" names two things.** The Brainstem app calls `agents/`
plus Brainstem data the "RAPP Workspace", as Article XVII calls `agents/` the
"User's Workspace", while RAPP Workspace/1 uses the same name for private,
local-first SDK workspaces. The organism records it as an idea
([`organism/gaps/G22.md`](https://github.com/kody-w/rapp-work/blob/experimental/rapp-work-constitution/organism/gaps/G22.md),
phase 3, blocks: workspaces), with the fix "Name one of them differently, or
state how they relate". Gap G11 is its twin for the word "organization";
RAPP Work proposal 0011 handles it, with the same naming table as this
proposal.

## Home specification and section

- **This repository's `CONSTITUTION.md`, Article XVII** ("`agents/` IS the
  User's Workspace"), with Article XVI ("the Brainstem's Workspace Is
  Separate") beside it. Both sit inside the constitution's historical section
  (`RAPP1-HISTORICAL-SECTION-START` at line 10 to `-END` at line 4011), so,
  as proposal 0001 does, a short section after the last article states the
  rule as current guidance. Article XVIII needs no change.
- **RAPP Workspace/1** (`kody-w/rapp-workspace`, protocol `rapp-workspace/1`).
  It already uses its name only for its own workspaces, so it needs no
  normative change. A documentation follow-up is listed under Migration.

## Context

Line numbers are for `CONSTITUTION.md` at `8afc973` (the current `main`)
unless another commit is named.

### "Workspace" in this repository

This repository uses "workspace" for many things. These are the uses this
proposal names or must keep apart, found with a case-insensitive
`git grep -n -i workspace` over the tracked tree:

| Where | What it calls a workspace |
|---|---|
| Article XVII, lines 894 and 896 | `agents/`: "`agents/` IS the User's Workspace", "the user's entire operational workspace" |
| Article III.7, line 306 | Where a person keeps their own agents: "User-authored agents live in the user's own workspace, not this repo" |
| Article XVI, lines 645, 654, 669, 675, 709, 713-716 and 724-726; Article XXXII's cross-reference, lines 2234-2235 | What the Brainstem writes while it runs: "the brainstem's workspace" (line 669 says "the brainstem workspace"), for memory, state, sessions and swarms |
| Article XVII, line 938 | A folder name: `agents/workspace_agents/`, "the shop". Under proposal 0001 every subfolder of `agents/` is organization only |
| Article XLVI.2, line 3405 | A door-bearing record kind: `workspace` is one of the kinds whose door type is `gate` |
| `tools/door_address.py` line 63; `tools/ecosystem_contract.py` lines 137-150; `tools/front_door_specs.py` lines 98-99 | The same kind in code: `_GATE_KINDS` holds `"workspace"`; the contract for "workspace: private-pattern (gate + private companion)" expects `rappid.json` (`rapp/1`, kind `workspace`), `neighborhood.json` and `members.json`; a door of this kind is planted with `specs/WORKSPACE_PROTOCOL.md`, whose work items are labeled Issues |
| `cave/rappid.json` line 4; `pages/metropolis/index.json` lines 120-125 | The same kind in records: the RAPP Cave (`"schema": "rapp/1"`, `"kind": "workspace"`, "public-workspace pattern") and the `private-workspace-template` entry (`"kind": "workspace"`) |
| `protocols/rapp-hive/1/SPEC.md` §2, line 72; `skills/rapp-private-hive/SKILL.md` lines 8 and 16; `skills/README.md` line 9; `skills/autonomous-rapp-estate-manager/SKILL.md` lines 3, 70 and 124 | Lowercase "RAPP workspace" in RAPP Workspace/1's sense, such as the "Local RAPP workspace" boundary of `rapp-hive/1` |
| `pages/about/ecosystem.json` line 527; `pages/about/ecosystem.html` line 2069 | Lowercase "private RAPP workspace" for a workspace gate: the template repository's description, which `tools/ecosystem_graph.py` copies from that repository's metadata |
| `pages/vault/Foundations/Glossary.md`, lines 39-41 and 195-197 | "Brainstem workspace" is `.brainstem_data/`; "Workspace" is a user-made folder inside `agents/` |
| `pages/vault/Foundations/Tier 1 — Local Brainstem.md`, line 127 | "`.brainstem_data/` is the workspace" |
| `rapp_brainstem/brainstem.py`, line 1866 (a grail byte, read only) | a comment: "agents/ is the user's workspace" |

The capitalized "RAPP Workspace" appears nowhere on `main`
(`git grep "RAPP Workspace"` finds nothing). The lowercase "RAPP workspace"
does, in two senses: RAPP Workspace/1's and the workspace gate's. Ruling R6
(below) says that letter case distinguishes nothing, so this repository
already uses the name both ways.

### "RAPP Workspace" in the Brainstem app

On branch `experimental/brainstem-app` at `d601936`, read only here:

- The Explorer "shows your **RAPP Workspace**: your Brainstem's agents and,
  read-only, its data" (`brainstem-app/README.md`, line 21), with two roots:
  **Agents** (`agents/`) and **Brainstem data** (`.brainstem_data/`,
  read-only) (README lines 116-131).
- It opens as a host workspace file, `RAPP Workspace.code-workspace`, kept in
  the app's own storage, with the window title "RAPP Workspace" (README lines
  59-64 and 191; `brainstem-app/extensions/rapp/src/startup.ts`, lines 228
  and 237).
- The setting `rapp.agentsFolder` is described as "The RAPP Workspace's
  Agents root: the agents/ folder your Brainstem loads agents from"
  (`brainstem-app/extensions/rapp/package.json`, line 263). The trust dialog
  says "Trust your RAPP Workspace so you can manage them here"
  (`src/launcher.ts`, line 26).
- In all, 80 lines in 13 files of `brainstem-app/` say "RAPP Workspace",
  while the setting's own key already says "agents folder".

The organism repeats it: the Brainstem app part says "its RAPP Workspace
shows two roots, `agents/` and Brainstem data (read-only)".

### The same words everywhere else

- **RAPP Workspace/1.** `kody-w/rapp-workspace` at `52d4f19`: "**Protocol
  ID:** `rapp-workspace/1`", "**Name:** RAPP Workspace/1" (root `SPEC.md`,
  lines 3-5). The normative `protocols/rapp-workspace/1/SPEC.md` §2 (line 42)
  says "`rapp-workspace/1` is the sole current RAPP Workspace core protocol",
  and §12 defines the routing-only `workspace-composite` (line 420).
- **The historical RAPP Work text.** `kody-w/rapp-work` root `SPEC.md` §5
  (lines 52-60 at `29ead23`): "RAPP Workspace is the local-first product
  layer. It carries project skills in `.github/skills`, preserves one
  workspace identity and world, and can migrate older workspaces additively".
  That file is frozen: the signed registry of `kody-w/rapp-work` pins it by
  SHA-256, so its words never change. It is historical evidence, not the
  canonical `rapp-work/1` in `kody-w/rapp-1`, whose §5 is about rollback
  targets.
- **The RAPP Work SDK.** `rapp-work-sdk/1` §7: "A Workspace has one existing
  or mint-once RAPPID and one hard `world_id`." The SDK sets the identity
  `kind: "workspace"` in `_identity()` (`src/rapp_work/workspace.py`, lines
  169-199) and writes it to `rappid.json` with `"schema": "rapp/1"` and
  `"workspace_spec": "rapp-work-sdk/1"` (line 130); the scaffolded `SPEC.md`
  is titled "RAPP Workspace" (lines 65-73).
- **The organism and the LTS lock.** The Workspaces part is "Your private,
  local-first workspaces (GODD), changed only by exact SDK plans", and the
  RAPP/1 LTS lock pins "RAPP Workspace/1".
- **RAR.** `kody-w/RAR` `CONSTITUTION.md` at `ecf5f52`, Article XVI
  ("Local-First Agents Workspace", line 632), uses "agents workspace" for
  something else: a person's "local copy of RAPP as a personal **agents
  workspace** — a self-contained store" (line 634), "a local RAPP instance
  that serves as your personal card collection and agent workbench" (line
  638). Its setup clones `kody-w/RAR`, builds the registry and opens the
  store page (lines 640-662), and its agents live under `agents/@yourname/`
  (lines 692-699). There, "The `agents/` directory IS the workspace" (line
  634) means that store's own `agents/` tree. RAR describes a Brainstem's
  `agents/` folder separately: "In a RAPP Brainstem runtime, the `agents/`
  folder stays pristine" (line 112). Its ratification note repeats
  "local-first agents workspaces" (line 1105).
- **"Agents folder".** RAPP (6 lines at `8afc973`), RAR (41 lines), the
  newest installer tag `brainstem-v0.6.16` (5 lines) and the Brainstem app
  (2 lines) say "agents folder", and every use means a Brainstem's `agents/`
  folder, as in "Drop `*_agent.py` files into the agents folder"
  (`docs/index.html`, line 294) and "drop it into your agents folder" (RAR
  `index.html`, line 1195). "Drop this file into any RAPP brainstem's
  `agents/` directory" says the same in RAPP, RAR and `kody-w/rapp-1`.
- **The host editor.** Code - OSS calls the folders one window has open a
  workspace (`.code-workspace` files, Workspace Trust).

### How RAPP's door tooling reads an SDK Workspace

A scratch probe, outside both repositories, scaffolded a synthetic SDK
Workspace with `kody-w/rapp-work` at `29ead23` (Python 3.13) and passed its
`rappid.json` (`"kind": "workspace"`, `"schema": "rapp/1"`,
`"workspace_spec": "rapp-work-sdk/1"`) to this repository's
`tools/door_address.py` `door_from_rappid` (Python 3.11). The result was
`kind: "workspace"`, `door_type: "gate"` and nine public URLs, among them
`https://github.com/example/finance` and `https://example.github.io/finance/`.
The door tooling cannot tell a private SDK Workspace from a workspace gate by
its record, because both carry the same `schema` and `kind` values; only the
SDK's record adds `workspace_spec`. An SDK Organization's `kind:
"organization"`, and the proposed `workspace-index`, are refused as
unsupported door kinds.

### Why it matters

- **One proper noun, two things.** "RAPP Workspace" is the name of a pinned,
  in-force protocol line, and the Brainstem app uses it for a window onto
  `agents/`. A person or an AI that reads "RAPP Workspace" in the app will
  look up RAPP Workspace/1, and the reverse.
- **They are opposite kinds of folder.** The Brainstem imports and runs the
  top-level `agents/*_agent.py` files on every request. A RAPP Workspace
  holds private work that the Brainstem never loads and the SDK never runs
  (`rapp-work-sdk/1` §11). What it holds is classified by content, not by
  place: "DOGG and GODD classify data, not storage locations"
  (`kody-w/rapp-work` root `SPEC.md` §4, line 39). Mixing the names invites
  mixing the folders (see Security and privacy).
- **Capitalization is not a qualifier.** The Lexicon's ruling R6
  (`LEXICON.md`, line 260) says a collision is named, not resolved by force,
  and that prose must qualify it, "never rely on capitalization alone, which
  fails in speech and case-folded systems". "RAPP Workspace" against
  "workspace" relies on capitalization.
- **The word is also a record value.** `kind: "workspace"` in a `rapp/1`
  `rappid.json` means a workspace gate to RAPP's door tooling and a private
  workspace to the RAPP Work SDK: one value with two meanings, the split that
  RAPP/1 Article 2 forbids for versioned tokens.
- **It blocks the lock.** G22 is a phase 3 gap of the RAPP/1 LTS lock-in, and
  it blocks the Workspaces part.

## Options

| Option | Verdict | Why |
|---|---|---|
| A. Rename the RAPP Workspace/1 side | Refused | `rapp-workspace/1` is an in-force, pinned protocol, and the LTS lock pins it. Renaming it moves tokens (RAPP/1 Art. 2) and pins in several repositories, and the frozen `kody-w/rapp-work` root `SPEC.md` §5 would keep saying "RAPP Workspace" forever |
| B. Call the Brainstem side the "Brainstem workspace" | Refused | Article XVI and the vault glossary already use that for Brainstem data only, so the pair would be named after one of its parts |
| C. Call it the "agentspace" or the "workbench" | Refused | Taken: Article LVI (the public commons), Article XLIX (a twin's working area), the editor's own "workbench", and RAR's "agent workbench" |
| D. Call it the "agents workspace" | Refused | RAR's Article XVI already uses it for a local copy of RAR, a card collection and agent workbench (lines 632-638 and 1105). Adopting it would give "agents workspace" two meanings across RAPP and RAR, the very defect this proposal fixes. The first draft recommended it; the review found the collision |
| E. Call it the "agent workspace" | Refused | Unused as a phrase (RAPP's only matches are inside "multi-agent workspace"), but one letter from RAR's term, which fails in speech as capitalization does |
| F. Keep "agents workspace", record the RAR collision under R6 and qualify both uses | Not recommended | Workable ("the Brainstem's agents workspace" against RAR's "local agents workspace"), but it keeps one more meaning of "workspace" and asks RAR to qualify its own words (ready text under open question 1) |
| G. Keep both names and only state how they relate | Not enough | The app's proper noun keeps colliding; R6 asks the prose to qualify |
| **H. Call the Brainstem side the Brainstem's agents folder, keep "RAPP Workspace" for RAPP Workspace/1 only, and state how they relate** | **Recommended** | The ecosystem's existing words: RAPP, RAR, the newest installer tag and the Brainstem app say "agents folder", every use means a Brainstem's `agents/`, and the app's own setting is `rapp.agentsFolder`. It takes a meaning away from "workspace" instead of adding a qualified one. Only prose and app strings change |

## Proposed change

The change is additive only. It follows proposal 0001 and the "Amendment
(2026-07-08)" precedent in Articles XLVI and XLVII: a governing blockquote
note, the old wording kept, and "this note governs".

### 1. `CONSTITUTION.md`, Article XVII: a governing note

Insert this block directly below the Article XVII heading (line 894), and
below proposal 0001's note if that has merged first:

```markdown
> **Amendment (2026-09-25) — the Brainstem's agents folder is not a RAPP Workspace; additive per Article XXVI.** This article's "User's Workspace" is the **Brainstem's agents folder**: the Brainstem's `agents/` folder (its `AGENTS_PATH`), where a person adds, groups, loads and unloads agents. Article III.7's "the user's own workspace", where user-authored agents live, is the same folder of the user's own Brainstem. It is not a **RAPP Workspace**. That name, in any letter case, and the `rapp-workspace/1` token mean only a RAPP Workspace/1 workspace: a private, local-first folder with its own RAPPID and one `world_id`, which the RAPP Work SDK changes only through exact plans. Article XVI's "brainstem's workspace" is **Brainstem data**: what the running Brainstem writes as it serves the user. Keep the three apart. The agents folder holds the agent files the Brainstem loads; a RAPP Workspace holds private work, which the Brainstem never loads and the SDK never runs; Brainstem data belongs to the running Brainstem. Keep RAPP Workspaces out of the agents folder, because whatever copies or packs `agents/` would carry them along. A Brainstem reaches a RAPP Workspace only through the RAPP Work SDK's operations, and a change applies only with its plan's exact SHA-256. A window or view that shows `agents/`, even with Brainstem data beside it, shows the Brainstem's agents folder; it is not a RAPP Workspace. Folder and file names that contain "workspace", such as `workspace_agents/`, are only names. The wording below is preserved (Article XXVI: additive-only, no removals); where it calls `agents/` a workspace, read "the Brainstem's agents folder". This note governs the names. See [proposal 0010](./docs/proposals/0010-agents-folder-is-not-a-rapp-workspace.md).
```

### 2. `CONSTITUTION.md`, Article XVI: a pointer note (recommended)

Insert this block directly below the Article XVI heading (line 645):

```markdown
> **Amendment (2026-09-25) — the brainstem's workspace is Brainstem data; additive per Article XXVI.** In this article "the brainstem's workspace" and "the brainstem workspace" mean **Brainstem data**: what the running Brainstem writes as it serves the user, such as memory and state. `agents/` is the Brainstem's agents folder (Article XVII). Neither is a **RAPP Workspace**, which means only a RAPP Workspace/1 workspace. The wording below is preserved (Article XXVI: additive-only, no removals); this note governs the names. See the Article XVII amendment of the same date and [proposal 0010](./docs/proposals/0010-agents-folder-is-not-a-rapp-workspace.md).
```

### 3. `CONSTITUTION.md`, after the last article: current guidance (recommended)

Articles XVI and XVII sit inside the historical section, as proposal 0001
found for Articles XVII, XVIII and XX, while which "workspace" they mean is
current guidance. As proposal 0001's amendment does, append this at the end
of `CONSTITUTION.md`, after proposal 0001's section if that has merged
first:

```markdown
---

## Amendment (2026-09-25) — The Brainstem's agents folder is not a RAPP Workspace

> **Additive per Article XXVI; see [proposal 0010](./docs/proposals/0010-agents-folder-is-not-a-rapp-workspace.md).**
> Articles XVI and XVII sit inside the historical section above, but which
> "workspace" they mean is current guidance, so it is stated here as well. A
> **RAPP Workspace**, in any letter case, is only a RAPP Workspace/1
> workspace. Article XVII's "User's Workspace" is the **Brainstem's agents
> folder**, the Brainstem's `agents/`, and Article XVI's "brainstem's
> workspace" is **Brainstem data**; neither is a RAPP Workspace. The notes of
> the same date in Articles XVI and XVII apply this to their text, and they
> govern how those articles are read.
```

### 4. Receipts for this tracked file (this branch)

This branch adds one tracked file, this proposal. As the proposal 0001 and
0002 branches did, it refreshes the two receipts that count tracked files and
bytes, computed with the repository's own rules: `_tracked_paths()` and
`_path_digest()` in `tests/test_adaptation_inventory.py`, and the tracked-byte
sum of `tools/check_rapp1_docs.py`. Revision 2 recomputed them for the new
file name and size.

- `RAPP1_ADAPTATION_INVENTORY.json`: `snapshot.generated_at`
  `2026-09-25`; `snapshot.tracked_path_count` and path set `PS-ALL`
  `expected_count` from 793 to 794; both path-set digests recomputed.
- `tests/fixtures/rapp1-doc-scope.json`: `current_inventory.tracked_paths`
  from 793 to 794 and `stable_tracked_bytes` recomputed;
  `expected_tracked_document_count` from 299 to 300; this proposal listed
  under the `current` disposition.

### What does not change

- No code, no agent file, and nothing under `rapp_brainstem/`. The three
  grail files pinned by `KERNEL_PIN.json` are untouched.
- `CONSTITUTION.md` itself is not edited on this branch, and no stale
  sentence is deleted or rewritten anywhere (Article XXVI).
- No README header, no `experimental/brainstem-app` file, no RAR file, and
  no other repository. RAR's Article XVI keeps its "agents workspace", and
  this proposal asks RAR for no change.
- No token, schema, frame kind, egg variant or wire form.

## Shared naming table

This section is identical in RAPP proposal 0010 (`kody-w/RAPP`, gap G22) and
RAPP Work proposal 0011 (`kody-w/rapp-work`, gap G11). One name means one
thing. Where a word must keep two meanings, the prose qualifies it and never
relies on capitalization alone (RAPP `LEXICON.md`, ruling R6).

| Name | What it is | Who decides | On disk and in records | Change |
|---|---|---|---|---|
| **organization** | The accountable body: one owner, one world, one policy, one release scope and exactly one Hive, with a body stream of signed RAPP/1 frames | Canonical `rapp-work/1` §§1–2 (`kody-w/rapp-1`) | `work.organization`, `rapp-work/1-organization`, `organization_rappid` (also the body stream id) | None |
| **workspace index** | A private, pointer-only list of RAPP Workspaces in one `world_id`. Each entry holds a RAPPID, a lexical path, the world, the mode, a name and an active flag, never content. It lists workspaces; it is not an index of any workspace's files | `rapp-work-sdk/1` §7 (`kody-w/rapp-work`) | Proposed: `WorkspaceIndex`, `kind: "workspace-index"`, `workspace-index.json` (`rapp-work-workspace-index/1`), `workspaces.json` (`rapp-work-workspace-index-pointers/1`), `workspace_index_rappid` | Proposal 0011. The SDK calls this object "Organization" today (`kind: "organization"`, `organization.json` with `rapp-work-organization/1`, `workspaces.json` with `rapp-work-organization-pointers/1`, `organization_rappid`). Those records keep verifying through a migration window whose end the owner sets (proposal 0011, decision D1) |
| **organization tree** | RAPP Workspace/1's candidate grouping of one catalog's entries: a lens output of 1 to 32 content-addressed tiles, assessed against bounds and never authority. A verified one may be wrapped into a workspace composite | RAPP Workspace/1 §12 (`kody-w/rapp-workspace`) | its tiles; `rapp-workspace/1/organization-assessment` records | None. It is neither the accountable organization nor a workspace index |
| **RAPP Workspace** | A private, local-first workspace under RAPP Workspace/1: one RAPPID and one hard `world_id`. The RAPP Work SDK changes it only through exact plans | RAPP Workspace/1 (`kody-w/rapp-workspace`); its SDK integration is `rapp-work-sdk/1` §7 (`kody-w/rapp-work`) | `rapp-workspace/1`; the SDK's `Workspace`: `rappid.json` with `"kind": "workspace"` and `"workspace_spec": "rapp-work-sdk/1"`, and `.rapp-work/` records | None. The proper noun means this and nothing else, in any letter case |
| **workspace composite** | RAPP Workspace/1's routing-only pointer structure over catalog entries and child composites | RAPP Workspace/1 §12 | `workspace-composite` | None. It is not a workspace index |
| **workspace gate** | A planted RAPP door of the door-bearing kind `workspace`, door type `gate`: members pick up work items through labeled Issues, in the private-workspace or public-workspace pattern | RAPP Constitution Article XLVI.2 (`kody-w/RAPP`) and its `tools/door_address.py` | `rappid.json` with `"schema": "rapp/1"` and `"kind": "workspace"`, beside `neighborhood.json` and `members.json` | Proposal 0010 names it in prose. No token. Its `kind` value is the same string as the SDK's; see the named collisions below |
| **Brainstem agents folder** | A Brainstem's `agents/` folder (its `AGENTS_PATH`), where a person adds, groups, loads and unloads agents. Only its top-level `*_agent.py` files are live (the grail's flat loader; RAPP proposal 0001) | RAPP Constitution Article XVII (its "User's Workspace") | `agents/` | Proposal 0010. No token. RAPP, RAR, the installer and the Brainstem app already call it the agents folder |
| **Brainstem data** | What the running Brainstem writes as it serves you: memory, state and sessions | RAPP Constitution Article XVI (its "brainstem's workspace") | `.brainstem_data/` and the Brainstem's own state folder | Proposal 0010. No token |
| **host workspace** | The editor's own word for the folders one window has open | Code - OSS, not RAPP | a `.code-workspace` file | Not a RAPP name. A window that shows `agents/` with Brainstem data beside it shows the Brainstem agents folder |

Named collisions (R6: both meanings stay, and prose qualifies them):

- **`kind: "workspace"` in a `rapp/1` `rappid.json`.** RAPP's door tooling
  reads the value as a workspace gate and resolves the record's RAPPID to door
  type `gate` and nine public URLs. The RAPP Work SDK writes the same value,
  with the same `"schema": "rapp/1"`, for a private RAPP Workspace, and adds
  `workspace_spec`. No document says which vocabulary owns a `rappid.json`
  `kind` value. Both proposals leave this to the owner and move no token.
- **"agents workspace".** RAR's Constitution Article XVI uses it for a
  person's local copy of RAR, their card collection and agent workbench. These
  proposals do not use it.
- **"private workspace".** RAPP's door patterns (`private-workspace`,
  `public-workspace`) name workspace gates, while RAPP Workspace/1 calls its
  own workspaces private. Qualify: *private workspace gate*, *RAPP Workspace*.

Words already taken, so not used for these objects: "agentspace" (RAPP
Article LVI, the public commons), "workbench" (RAPP Article XLIX, a twin's
working area; the editor's name for its whole window; RAR's agent
workbench), "registry" (the signed RAPP/1 §13 root of trust), "catalog"
(`rapp-work/1-catalog` and RAPP Workspace/1 catalogs), "Brainstem workspace"
(RAPP's vault glossary uses it for Brainstem data) and "external index"
(RAPP Workspace/1 §12: bounded indexes of file and path metadata inside a
scan boundary; a workspace index holds none). "Agent workspace" differs from
RAR's term by one letter, which fails in speech as capitalization does.

Plain-English "organize" and "organization" name an activity and stay as they
are: the organism's invariant "Every folder is organization" and RAPP proposal
0001's "Every subfolder of `agents/` is organization only" mean that a folder
only groups files. RAPP Workspace/1's organization tree is an object, with its
own row above.

The sidecar profile in `kody-w/rapp-workspace` (`protocols/rapp-work-sdk/1`)
names a discovery field `organization_pointers`: routing-only pointers to
`workspace-composite` addresses, which may wrap a verified organization tree.
Both proposals list it as an optional follow-up for that repository.

## How they relate, stated precisely

1. **They are different things.** The Brainstem's agents folder holds agent
   files; the grail's `load_agents()` imports the top-level `*_agent.py`
   files on every request (`rapp_brainstem/brainstem.py`, lines 1202-1205). A
   RAPP Workspace holds private work under its own RAPPID and `world_id`; the
   Brainstem never loads it, and the SDK's discovery never imports or runs
   what it finds (`rapp-work-sdk/1` §11).
2. **Brainstem data is neither.** The running Brainstem writes it. A view may
   show it beside `agents/`, read-only, as the Brainstem app does; that does
   not make it part of the agents folder or a RAPP Workspace.
3. **A RAPP Workspace stays out of the agents folder.** Whatever copies or
   packs `agents/` would carry it along: an `organism` egg may include
   `agents/*` (RAPP/1 `SPEC.md` §9.2), and the preserved Tier 2 build copies
   the `agents/` tree recursively (Article XVII, lines 997-999; its apply mode
   is refused today). The Brainstem's agents folder is never pointed at a
   RAPP Workspace either. The reverse, a Brainstem's agents folder kept inside
   a RAPP Workspace, is not ruled here: the SDK would treat its files as inert
   data, while a Brainstem pointed at that folder would run its top-level
   agents from inside private work. Whether to rule it is open question 6.
4. **One door between them.** A Brainstem reaches a RAPP Workspace only
   through the RAPP Work SDK's operations (`status`, `verify`, `discover`,
   `scaffold`, `update`, `migrate`), and a change applies only with its
   plan's exact SHA-256 (`rapp-work-sdk/1` §2). That door is not built yet:
   the Brainstem has no SDK agent (the organism's gap G17). When it comes, it
   is one agent file at the top of `agents/`, and the RAPP Workspaces it works
   on stay where they are.
5. **Names are only names.** `agents/workspace_agents/` and the editor's
   `.code-workspace` files contain the word, and they are not RAPP
   Workspaces.
6. **A workspace gate is a door, not a folder on a Brainstem's machine.** It
   is a planted repository that RAPP's door tooling resolves to public URLs
   (Article XLVI.2). Its `rappid.json` and an SDK Workspace's carry the same
   `schema` and `kind` values, so the door tooling reads a private SDK
   Workspace's record as a gate (Context). This proposal recommends that door
   tooling treat a `rappid.json` that carries `workspace_spec` as an SDK
   identity, never as a door; the choice is open question 7.

## Token and naming analysis

- **No token moves.** `rapp-workspace/1` and every other versioned token are
  untouched. No schema, frame kind, egg variant, registry entry or wire form
  changes. "Brainstem's agents folder" and "Brainstem data" are names in
  prose and in an app's interface; neither is a token.
- **RAPP/1 Article 2 (one label, one shape).** The prose name now follows the
  token: "RAPP Workspace" means what `rapp-workspace/1` denotes, and nothing
  else. One value keeps two meanings at record level: `kind: "workspace"` in
  a `rapp/1` `rappid.json`, for the workspace gate and for the SDK's
  Workspace. This proposal records it and moves nothing, because each way to
  separate them changes or reinterprets a value that tools compare byte for
  byte; the choice is the owner's (open question 7).
- **Article XXV (chat is the only wire).** No request, response, slot or
  schema changes, and nothing is removed or renamed in the constitution; the
  notes and the closing section are additions.
- **Article XXVI (amendments).** Additive only. Article I is preserved:
  nothing is added to `brainstem.py` or `function_app.py`. Article XXV is
  preserved.
- **Lexicon ruling R6.** The historical uses of "workspace" in Articles XVI
  and XVII get names of their own, the Brainstem's agents folder and
  Brainstem data, and so leave the word; the uses that stay (RAPP Workspace,
  the workspace gate and the host workspace) are qualified in prose. The
  named collisions are listed with the table. This proposal does not add a
  Lexicon ruling: the Lexicon's whole-document disposition keeps it as dated
  product history, so the constitution notes govern. A dated ruling (Article
  LII.2) is the owner's call.
- **Identity (RAPP/1 Article 7).** Nothing is renamed that carries a RAPPID.
  The Brainstem's agents folder has no RAPPID of its own; a RAPP Workspace
  keeps its minted RAPPID.
- **The app's workspace file name** (`RAPP Workspace.code-workspace`) is a
  private path in the app's own storage, not a token. Migration step 3 moves
  it additively.
- **Names checked for collisions**, case-insensitively, across `kody-w/RAPP`
  (`8afc973`), `kody-w/rapp-1` (`591e014`), `kody-w/rapp-work` (`29ead23`),
  `kody-w/RAR` (`ecf5f52`), `kody-w/rapp-workspace` (`52d4f19`), the
  Brainstem kernel's newest tag (`brainstem-v0.6.16`) and the Brainstem app
  branch (`d601936`): "Brainstem agents folder" appears nowhere as a phrase,
  and "agents folder" always means a Brainstem's `agents/` (Context);
  "agents workspace" appears only in RAR, for a local RAR instance; "agent
  workspace" appears only inside "multi-agent workspace"; "workspace gate"
  and "workspace index" appear nowhere. The first draft's check missed RAR's
  meaning.

## Security and privacy analysis

- **Execution boundary.** Top-level files in the Brainstem's agents folder
  run with the Brainstem's full rights on every request. A RAPP Workspace
  holds private work that the Brainstem never runs. Calling both "RAPP
  Workspace" invites the wrong expectation in both directions: that `agents/`
  enjoys the SDK's inert, exact-plan handling (it does not), or that a RAPP
  Workspace is a place for agents.
- **Leaks by copying.** A RAPP Workspace placed inside `agents/` would ride
  along with anything that copies or packs the agents tree (Relation 3), and
  `agents/` is also the curriculum Article XVI wants people to read and copy.
  The note's placement rule closes that path.
- **Trust prompts.** The host's Workspace Trust decides whether a window may
  run tasks and full extensions. A prompt that says "Trust your RAPP
  Workspace" could lead a person to grant trust to the wrong folder. The app
  follow-up names the folder precisely.
- **Brainstem data stays read-only in views.** The note calls it the running
  Brainstem's own data, which keeps a view from treating it as an editable
  workspace.
- **A private workspace read as a door.** Given an SDK Workspace's record,
  RAPP's door tooling derives public URLs for it (Context). A consumer that
  followed them would look for a public repository named after a private
  workspace, and one that published a door for it would expose that name. No
  SDK operation publishes anything, so nothing leaks today; open question 7
  keeps it that way.
- **No new data flow.** This proposal adds no network access, credentials,
  paths, personal data or identities. Its examples are public or synthetic.

## Migration

One pull request per step, each through its own repository's front door
(Articles XXVIII and XXIX). This workstream opens none of them; the ready
text for each is below, for the owner.

1. **This proposal (RAPP, docs only).** The maintainer accepts the proposal
   by merging it (Article XXX.2), then merges the amendment by hand in its
   own pull request, which cites the proposal (Articles XXVIII.4 and
   XXVIII.6).
   - *Ready text, amendment PR.* Title: "Constitution: the Brainstem's agents
     folder is not a RAPP Workspace (proposal 0010)". Body: "Adds the two
     governing notes and the closing section from proposal 0010 to Articles
     XVII and XVI and to the end of the constitution, word for word, and
     recomputes `stable_tracked_bytes` in `tests/fixtures/rapp1-doc-scope.json`,
     which counts every tracked byte. Additive per Article XXVI; changes no
     code, grail byte or token."
2. **The Brainstem app's words (RAPP, branch `experimental/brainstem-app`,
   by that branch's owner).** Replace "RAPP Workspace" with "agents folder",
   or "your Brainstem's agents folder", where it means `agents/`, and title
   the window with the owner's own name for its first root, "Agents", so that
   the title reads "… — Agents — Brainstem": `TITLE` in `src/startup.ts`
   (line 237), `TRUST_MESSAGE` in `src/launcher.ts` (line 26, for example
   "Trust your Brainstem's agents folder so you can manage them here."), the
   setting and welcome texts in `extensions/rapp/package.json` (lines 78,
   263, 269 and 275), `README.md`, code comments, and the tests that pin these
   strings. The roots keep their names, **Agents** and **Brainstem data**.
   - *Ready text.* Title: "Brainstem app: call agents/ the Brainstem's agents
     folder, not the RAPP Workspace (proposal 0010)". Body: "RAPP Workspace
     is RAPP Workspace/1's name. The window shows the Brainstem's agents
     folder, with Brainstem data beside it, read-only. Strings, docs and tests
     only; no behavior change."
3. **The app's workspace file (same branch, a separate change).** Additive
   first: recognize both `RAPP Workspace.code-workspace` and
   `Brainstem agents.code-workspace` as the app's own file for one release,
   write only the new name, and leave the old file where it is. Then stop
   recognizing the old name. The Explorer header then reads "Brainstem agents
   (Workspace)", where "(Workspace)" is the host's own word. Internal names
   such as `RappWorkspace` and `isRappWorkspaceWindow` may follow
   (`AgentsFolder`, `isAgentsFolderWindow`); nobody sees them.
4. **RAPP Workspace/1 (`kody-w/rapp-workspace`, a pull request to `main`).**
   Add the shared naming table to `docs/rapp-work.md`, with one sentence: "A
   Brainstem's agents folder and its Brainstem data are not RAPP
   Workspaces." That file is not in the exact-byte manifest, so no pin moves.
   - *Ready text.* Title: "docs: name what a RAPP Workspace is and is not
     (RAPP proposal 0010, RAPP Work proposal 0011)". Body: "Docs only. Adds
     the shared naming table. No normative byte, pin or manifest entry
     changes."
5. **RAPP Workspace/1, pinned wording (optional, the owner's call).** Should
   the owner want the terminology in its root `README.md` or `SPEC.md`, or in
   `protocols/rapp-workspace/1/SPEC.md` §2, do it in a release that re-pins
   anyway: those files are exact-byte entries in
   `protocols/rapp-workspace/1/manifest.json`, whose hash
   `protocols/index.json` pins.
6. **The sidecar's `organization_pointers` (`kody-w/rapp-workspace`, a
   later pull request, optional).** They point at `workspace-composite`
   addresses, which may wrap a verified organization tree, so the name
   follows RAPP Workspace/1's meaning, yet a reader can take it for the
   accountable organization. If the owner wants it renamed, name the field
   after what it points at (for example `workspace_composite_pointers`) under
   a new discovery schema token, never by widening the current one, and keep
   the byte-pinned prior-release fixture verifying. This waits for the owner
   to decide which document owns the `rapp-work-sdk/1` label: that
   repository's sidecar profile and `kody-w/rapp-work`'s SDK profile are two
   different documents under the same label (RAPP Work proposal 0011,
   Context).
7. **The organism (`kody-w/rapp-work`, branch
   `experimental/rapp-work-constitution`, by its maintainer).** Say "agents
   folder" in the Brainstem app part ("its RAPP Workspace shows two roots"),
   and record G22 as proposed with this proposal's names: `agents/` is the
   Brainstem's agents folder, not an "agents workspace". This workstream
   reports it and does not edit it.
8. **Optional docs in this repository (each its own pull request, the
   owner's call).** Qualify "workspace" in the vault glossary entries
   "Brainstem workspace" and "Workspace", in `pages/vault/Foundations/Tier 1
   — Local Brainstem.md` line 127, and in `rapp_brainstem/CONSTITUTION.md`,
   the historical application constitution. The description "private RAPP
   workspace" in `pages/about/ecosystem.json` and `.html` comes from the
   `kody-w/private-workspace-template` repository's metadata; the owner may
   change it there, for example to "private workspace gate", and regenerate.
   The grail comment in `rapp_brainstem/brainstem.py` line 1866 is never
   edited; the Article XVII note covers it.
9. **The record-level kind (the owner's decision, open question 7).** Under
   its recommended answer, a separate RAPP proposal changes the door tooling
   (`tools/door_address.py` and the consumers that import it) to refuse a
   `rappid.json` that carries `workspace_spec`, with its own vectors. No
   record changes.

## Rollback

- **Before any merge:** delete the branch.
- **After the amendment merges:** revert the amendment commit, then
  recompute the receipts and rerun `python3 tests/run_restoration_acceptance.py`.
  `stable_tracked_bytes` in `tests/fixtures/rapp1-doc-scope.json` counts every
  tracked byte, and merges in between (proposals 0001 and 0002 edit the same
  receipt lines) can make a plain revert conflict or leave stale counts. No
  runtime behavior changes, so nothing outside the repository needs rolling
  back.
- **The app (steps 2 and 3):** revert its commits. Step 3 leaves the old
  workspace file in place, so an older build still finds its own file, and
  nobody is stranded.
- **RAPP Workspace/1 (step 4):** revert the documentation commit; no pin
  moved.

## Conformance and test vectors

This branch is documentation only, so it adds no test. Its checks, run
locally with Python 3.11 before the push, and again for revision 2 after the
file was renamed:

- `python3 tests/run_restoration_acceptance.py` passes. It covers
  `tools/check_rapp1_docs.py`, which requires this file to have a
  disposition and, as a `current` document, to link `RAPP1_AUTHORITY.json`
  and `RAPP1_STATUS.md`, state rev-5, name every authority topic and avoid
  the retired patterns; and `tests/test_adaptation_inventory.py`, which
  recomputes both path-set digests.
- **The receipts are live checks (mutations run locally, then restored):**
  - Dropping this file from the `current` list in
    `tests/fixtures/rapp1-doc-scope.json` makes `tools/check_rapp1_docs.py`
    fail with "tracked document has no disposition" for this path.
  - Setting `expected_tracked_document_count` back to 299 makes it fail with
    "derived tracked-document count does not match git ls-files
    (300 != 299)".
  - Setting `snapshot.tracked_path_count` in
    `RAPP1_ADAPTATION_INVENTORY.json` back to 793, or changing one hex digit
    of its `tracked_path_set_sha256`, makes
    `tests/test_adaptation_inventory.py::test_inventory_path_sets_match_the_tracked_tree`
    fail.
  - Each file was then restored, and the full acceptance run passed again.

Vectors for the follow-ups:

- **V1 (step 1).** Under the Article XVII heading, `CONSTITUTION.md` carries
  the note, and the note contains "Brainstem's agents folder" and "RAPP
  Workspace/1"; the closing section follows the last article.
- **V2 (step 2).** `git grep -n "RAPP Workspace" -- brainstem-app` finds no
  line that means `agents/`. The app's tests pin the window title's "Agents"
  and the trust message.
- **V3 (step 3).** A test opens a window whose workspace file has the old
  name and gets the app's own behavior, and a new write uses only the new
  name.
- **V4 (optional, the owner's call).** The app refuses an agents folder that
  is a RAPP Workspace (one that holds `rappid.json` with `workspace_spec` and
  `.rapp-work/sdk.json`) and says why. This is new behavior, so it needs its
  own review.
- **V5 (step 9, if the owner so decides).** `door_from_rappid` refuses a
  record that carries `workspace_spec`, and every existing door vector, the
  RAPP Cave's among them, still resolves.

## Reference implementation

None. This is a naming proposal. Nothing here governs until the maintainer
merges the amendment.

## Open questions for the owner (decisions)

1. **The name.** "The Brainstem's agents folder" (recommended: RAPP, RAR,
   the installer and the Brainstem app already say "agents folder"), or keep
   "agents workspace" with the RAR collision recorded and both uses qualified
   (Option F)? Under Option F this ready text would go to RAR through its
   feature request form, for its maintainer. *Title:* "Constitution Article
   XVI: qualify 'agents workspace' as a local RAR instance". *Body:* "RAPP's
   constitution may call a Brainstem's `agents/` folder the Brainstem's
   agents workspace (RAPP proposal 0010, Option F). RAR's Article XVI uses
   'agents workspace' for a person's local copy of RAR. Suggest 'local RAR
   agents workspace' in Article XVI and its ratification note, with one
   sentence saying that it is not a Brainstem's `agents/` folder. Docs only."
   Nothing is filed.
2. **How much the note says.** Keep the placement rule ("Keep RAPP
   Workspaces out of the agents folder") and the one-door rule (SDK
   operations and an exact plan hash) in the Article XVII note, or keep the
   note to names only?
3. **Article XVI.** Add its pointer note too (recommended), or only the
   Article XVII note?
4. **The closing section.** Add it after the last article (recommended, as
   proposal 0001 does), or rely on the two notes alone?
5. **The app's window.** The title segment "Agents" and the workspace file
   `Brainstem agents.code-workspace` (recommended), or other qualified names
   from the table?
6. **The reverse placement.** Should the Article XVII note also say that a
   Brainstem's agents folder is not kept inside a RAPP Workspace, so that a
   Brainstem never runs files from inside private work?
7. **`kind: "workspace"` in `rappid.json`.** Which vocabulary owns a
   `rapp/1` `rappid.json` `kind` value? (a) Recommended: RAPP's door-bearing
   kinds (Article XLVI.2) apply only to door records, and door tooling treats
   a record that carries `workspace_spec` as an SDK identity and refuses to
   resolve it (Migration step 9, a RAPP tools change under its own proposal).
   (b) The SDK writes a new kind value for its Workspaces, which changes
   every SDK Workspace identity record and is RAPP Work's to propose (RAPP
   Work proposal 0011, open question 12). (c) RAPP renames its door kind,
   which amends the frozen set in Article XLVI.2; refused here.
8. **RAPP Workspace/1.** A docs-only note now (step 4), with pinned wording
   only at its next re-pin (step 5)?

## Owner actions needed

- Accept or refuse this proposal, and answer the questions above.
- If accepted: merge this proposal (Article XXX.2), then merge the amendment
  pull request by hand (Articles XXVIII.4 and XXX.2).
- Ask the Brainstem app's branch owner for steps 2 and 3.
- Accept or refuse the `kody-w/rapp-workspace` documentation pull request
  (step 4), and decide steps 5 and 6.
- Decide the record-level kind (open question 7, with RAPP Work proposal
  0011).
- Have the organism's maintainer record G22 as proposed with this proposal's
  names (step 7).

## Review round 1 disposition

The round 1 review of `30a38e8` found one high, one medium and five low
issues. Each is answered here.

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | high | "Agents workspace" is RAR's term for something else, not the same folder | Fixed: `agents/` is now the Brainstem's agents folder, the words every repository checked already uses for it. Context quotes RAR's Article XVI; Options D, E and F record the refused and the not-recommended names; the collision check is corrected; open question 1 keeps the alternative, with ready RAR text; the shared naming table changed in both proposals |
| 2 | medium | Context and the table missed existing uses of "workspace", one at record level | Fixed: Context lists Article III.7, the Article XLVI.2 door kind with its tools and records, and both lowercase senses of "RAPP workspace"; the "three things" and "never uses" claims are gone; both tables gain a "workspace gate" row and the named collision of `kind: "workspace"`, which a probe confirmed; open question 7 asks the owner |
| 3 | low | A plain revert does not restore the receipts | Fixed: revert, then recompute the receipts and rerun the acceptance run |
| 4 | low | The table's §7 reference named no repository | Fixed in both proposals: `rapp-work-sdk/1` §7 (`kody-w/rapp-work`) |
| 5 | low | The table called RAPP Workspace/1's organization an activity | Fixed in both proposals: the organization tree has its own row, as an object |
| 6 | low | Relation 3 claimed more than the note says | Fixed: retitled "A RAPP Workspace stays out of the agents folder"; the reverse case is stated and left to open question 6 |
| 7 | low | Four precision slips | Fixed: the Tier 2 bullet is at lines 997-999; the SDK's kind is set in `_identity()` (lines 169-199) and written at line 130; the Article XVII note now says "This note governs the names"; "A RAPP Workspace is GODD" is gone, because DOGG and GODD classify data, not places |

Also changed in revision 2, beyond the findings: the closing current-guidance
section (Proposed change 3), for the same reason proposal 0001 has one; the
Brainstem app citations now name its current head, `d601936`; and the file
name.

## References

- [`CONSTITUTION.md`](../../CONSTITUTION.md): Articles I, III.7, XVI, XVII,
  XVIII, XXV, XXVI, XXVIII (.3, .4, .6), XXIX, XXX.2, XXXII, XLVI.2, XLIX,
  LII, LV, LVI and LVII; precedent: the "Amendment (2026-07-08)" notes in
  Articles XLVI and XLVII.
- [`LEXICON.md`](../../LEXICON.md): Part III, ruling R6.
- `tools/door_address.py`, `tools/ecosystem_contract.py`,
  `tools/front_door_specs.py`, `tools/ecosystem_graph.py`,
  `cave/rappid.json`, `pages/metropolis/index.json`.
- RAPP proposal 0001, "Only top-level agents are live", on branch
  `experimental/constitution-live-agents`, with its amendment on
  `experimental/amendment-0001-live-agents` (not edited here); RAPP proposal
  0002 on `experimental/proposal-0002-tier2-parity` (receipt precedent).
- Grail loader: `rapp_brainstem/brainstem.py` lines 1202-1205, pinned by
  `KERNEL_PIN.json`.
- The Brainstem app: branch `experimental/brainstem-app` at `d601936`,
  `brainstem-app/README.md`, `extensions/rapp/package.json`,
  `extensions/rapp/src/startup.ts`, `extensions/rapp/src/launcher.ts`.
- RAPP Workspace/1: [`kody-w/rapp-workspace`](https://github.com/kody-w/rapp-workspace)
  root `SPEC.md`, `protocols/rapp-workspace/1/SPEC.md` §§2 and 12,
  `protocols/rapp-workspace/1/manifest.json`, `protocols/index.json`,
  `docs/rapp-work.md`, and the sidecar profile `protocols/rapp-work-sdk/1`.
- RAPP Work: [`kody-w/rapp-work`](https://github.com/kody-w/rapp-work) root
  `SPEC.md` §§4 and 5 (historical), `protocols/rapp-work-sdk/1/SPEC.md` §§2,
  7 and 11, `src/rapp_work/workspace.py`, and proposal 0011 on branch
  `experimental/gap-g11-workspace-index`.
- Canonical `rapp-work/1`: [`kody-w/rapp-1`](https://github.com/kody-w/rapp-1)
  `protocols/rapp-work/1/SPEC.md` §§1–2; RAPP/1 `SPEC.md` §9.2 and
  `CONSTITUTION.md` Articles 2 and 7.
- RAR: [`kody-w/RAR`](https://github.com/kody-w/RAR) `CONSTITUTION.md`
  Article XVI and its ratification note, and `CONTRIBUTING.md`.
- The organism: [`organism/`](https://github.com/kody-w/rapp-work/tree/experimental/rapp-work-constitution/organism)
  on `kody-w/rapp-work` branch `experimental/rapp-work-constitution`: gaps
  G11, G17 and G22, and the Workspaces and Brainstem app parts.
