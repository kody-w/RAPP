# Proposal 0010 — The agents workspace is not a RAPP Workspace

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
phase 3, blocks: workspaces). Gap G11 is its twin for the word
"organization"; RAPP Work proposal 0011 handles it, with the same naming
table as this proposal.

## Home specification and section

- **This repository's `CONSTITUTION.md`, Article XVII** ("`agents/` IS the
  User's Workspace"), with Article XVI ("the Brainstem's Workspace Is
  Separate") beside it. Article XVIII needs no change.
- **RAPP Workspace/1** (`kody-w/rapp-workspace`, protocol `rapp-workspace/1`).
  It already uses its name only for its own workspaces, so it needs no
  normative change. A documentation follow-up is listed under Migration.

## Context

Line numbers are for `CONSTITUTION.md` at `8afc973` (the current `main`)
unless another commit is named.

### "Workspace" in this repository

| Where | What it calls a workspace |
|---|---|
| Article XVII, lines 894 and 896 | `agents/`: "`agents/` IS the User's Workspace", "the user's entire operational workspace" |
| Article XVI, lines 645, 651-655, 669, 675, 709, 714 and 724 | What the Brainstem writes while it runs: "the brainstem's workspace" (line 669 says "the brainstem workspace"), for memory, binder state, sessions and swarms |
| Article XVII, line 938 | A folder name: `agents/workspace_agents/`, "the shop". Under proposal 0001 every folder is organization only |
| `pages/vault/Foundations/Glossary.md`, lines 39-41 and 195-197 | "Brainstem workspace" is `.brainstem_data/`; "Workspace" is a user-made folder inside `agents/` |
| `pages/vault/Foundations/Tier 1 — Local Brainstem.md`, line 127 | "`.brainstem_data/` is the workspace" |
| `rapp_brainstem/brainstem.py`, line 1866 (a grail byte, read only) | a comment: "agents/ is the user's workspace" |

So this repository already uses "workspace" for three things: `agents/`, a
folder inside it, and the Brainstem's runtime data. It never uses the
proper noun "RAPP Workspace" on `main` (`git grep "RAPP Workspace"` finds
nothing).

### "RAPP Workspace" in the Brainstem app

On branch `experimental/brainstem-app` at `a81bd9a`, read only here:

- The Explorer "is the RAPP Workspace", with two roots: **Agents**
  (`agents/`) and **Brainstem data** (`.brainstem_data/`, read-only)
  (`brainstem-app/README.md`, lines 18, 51-56 and 99-115).
- It opens as a host workspace file, `RAPP Workspace.code-workspace`, kept in
  the app's own storage, with the window title "RAPP Workspace"
  (`brainstem-app/extensions/rapp/src/startup.ts`, lines 184-192; README
  lines 51-56 and 170).
- The setting `rapp.agentsFolder` is described as "The RAPP Workspace: the
  agents/ folder your Brainstem loads agents from"
  (`brainstem-app/extensions/rapp/package.json`, line 262). The trust dialog
  says "Trust your RAPP Workspace so you can manage them here"
  (`src/launcher.ts`, line 27).
- In all, 81 lines in 13 files of `brainstem-app/` say "RAPP Workspace".

The organism repeats it: the Brainstem app part says "its RAPP Workspace
shows two roots, `agents/` and Brainstem data (read-only)".

### "RAPP Workspace" everywhere else

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
  or mint-once RAPPID and one hard `world_id`." The SDK scaffolds such a
  workspace with identity `kind: "workspace"` and a `SPEC.md` titled
  "RAPP Workspace" (`src/rapp_work/workspace.py`, lines 65-73).
- **The organism and the LTS lock.** The Workspaces part is "Your private,
  local-first workspaces (GODD), changed only by exact SDK plans", and the
  RAPP/1 LTS lock pins "RAPP Workspace/1".
- **RAR.** `kody-w/RAR` `CONSTITUTION.md` Article XVI (lines 632-638 at
  `ecf5f52`) is titled "Local-First Agents Workspace" and says "The `agents/`
  directory IS the workspace".
- **The host editor.** Code - OSS calls the folders one window has open a
  workspace (`.code-workspace` files, Workspace Trust).

### Why it matters

- **One proper noun, two things.** "RAPP Workspace" is the name of a pinned,
  in-force protocol line, and the Brainstem app uses it for a window onto
  `agents/`. A person or an AI that reads "RAPP Workspace" in the app will
  look up RAPP Workspace/1, and the reverse.
- **They are opposite kinds of folder.** The Brainstem imports and runs the
  top-level `agents/*_agent.py` files on every request. A RAPP Workspace is
  private work (GODD) that the Brainstem never loads and the SDK never runs
  (`rapp-work-sdk/1` §11). Mixing the names invites mixing the folders (see
  Security and privacy).
- **Capitalization is not a qualifier.** The Lexicon's ruling R6
  (`LEXICON.md`, line 260) says a collision is named, not resolved by force,
  and that prose must qualify it, "never rely on capitalization alone, which
  fails in speech and case-folded systems". "RAPP Workspace" against
  "workspace" relies on capitalization.
- **It blocks the lock.** G22 is a phase 3 gap of the RAPP/1 LTS lock-in, and
  it blocks the Workspaces part.

## Options

| Option | Verdict | Why |
|---|---|---|
| A. Rename the RAPP Workspace/1 side | Refused | `rapp-workspace/1` is an in-force, pinned protocol, and the LTS lock pins it. Renaming it moves tokens (RAPP/1 Art. 2) and pins in several repositories, and the frozen `kody-w/rapp-work` root `SPEC.md` §5 would keep saying "RAPP Workspace" forever |
| B. Call the Brainstem side the "Brainstem workspace" | Refused | Article XVI and the vault glossary already use that for Brainstem data only, so the pair would be named after one of its parts |
| C. Call it the "agentspace" or the "workbench" | Refused | Taken: Article LVI (the public commons), Article XLIX (a twin's working area) and the editor's own "workbench" |
| D. Keep both names and only state how they relate | Not enough | The app's proper noun keeps colliding; R6 asks the prose to qualify |
| **E. Qualify the Brainstem side as the agents workspace, keep "RAPP Workspace" for RAPP Workspace/1 only, and state how they relate** | **Recommended** | R6 applied: both meanings of "workspace" stay, and each is qualified. Only prose and app strings change. "Agents workspace" is already RAR's word for the same folder |

## Proposed change

The change is additive only. It follows proposal 0001 and the "Amendment
(2026-07-08)" precedent in Articles XLVI and XLVII: a governing blockquote
note, the old wording kept, and "this note governs".

### 1. `CONSTITUTION.md`, Article XVII: a governing note

Insert this block directly below the Article XVII heading (line 894), and
below proposal 0001's note if that has merged first:

```markdown
> **Amendment (2026-09-25) — the agents workspace is not a RAPP Workspace; additive per Article XXVI.** This article's "User's Workspace" is the **agents workspace**: the Brainstem's `agents/` folder, where a person adds, groups, loads and unloads agents. It is not a **RAPP Workspace**. That name, and the `rapp-workspace/1` token, mean only a RAPP Workspace/1 workspace: a private, local-first folder with its own RAPPID and one `world_id`, which the RAPP Work SDK changes only through exact plans. Article XVI's "brainstem's workspace" is **Brainstem data**: what the running Brainstem writes as it serves the user. Keep the three apart. The agents workspace holds the agent files the Brainstem loads; a RAPP Workspace holds private work, which the Brainstem never loads and the SDK never runs; Brainstem data belongs to the running Brainstem. Keep RAPP Workspaces out of `agents/`, because whatever copies or packs `agents/` would carry them along. A Brainstem reaches a RAPP Workspace only through the RAPP Work SDK's operations, and a change applies only with its plan's exact SHA-256. A window or view that shows `agents/`, even with Brainstem data beside it, shows the agents workspace; it is not a RAPP Workspace. Folder and file names that contain "workspace", such as `workspace_agents/`, are only names. The wording below is preserved (Article XXVI: additive-only, no removals); where it calls `agents/` a workspace, read "agents workspace". See [proposal 0010](./docs/proposals/0010-agents-workspace-is-not-a-rapp-workspace.md).
```

### 2. `CONSTITUTION.md`, Article XVI: a pointer note (recommended)

Insert this block directly below the Article XVI heading (line 645):

```markdown
> **Amendment (2026-09-25) — the brainstem's workspace is Brainstem data; additive per Article XXVI.** In this article "the brainstem's workspace" and "the brainstem workspace" mean **Brainstem data**: what the running Brainstem writes as it serves the user, such as memory and state. `agents/` is the agents workspace (Article XVII). Neither is a **RAPP Workspace**, which means only a RAPP Workspace/1 workspace. The wording below is preserved (Article XXVI: additive-only, no removals); this note governs the names. See the Article XVII amendment of the same date and [proposal 0010](./docs/proposals/0010-agents-workspace-is-not-a-rapp-workspace.md).
```

### 3. Receipts for this new tracked file (this branch)

This branch adds one tracked file, this proposal. As the proposal 0001 and
0002 branches did, it refreshes the two receipts that count tracked files,
recomputed with the digest rules in `tests/test_adaptation_inventory.py`
and `tools/check_rapp1_docs.py`:

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
- No README header, no `experimental/brainstem-app` file, and no other
  repository.
- No token, schema, frame kind, egg variant or wire form.

## Shared naming table

This section is identical in RAPP proposal 0010 (`kody-w/RAPP`, gap G22) and
RAPP Work proposal 0011 (`kody-w/rapp-work`, gap G11). One name means one
thing. Where a word must keep two meanings, the prose qualifies it and never
relies on capitalization alone (RAPP `LEXICON.md`, ruling R6).

| Name | What it is | Who decides | On disk and in records | Change |
|---|---|---|---|---|
| **organization** | The accountable body: one owner, one world, one policy, one release scope and exactly one Hive, with a body stream of signed RAPP/1 frames | Canonical `rapp-work/1` §§1–2 (`kody-w/rapp-1`) | `work.organization`, `rapp-work/1-organization`, `organization_rappid` (also the body stream id) | None |
| **workspace index** | A private, pointer-only list of RAPP Workspaces in one `world_id`. Each entry holds a RAPPID, a lexical path, the world, the mode, a name and an active flag, never content | `rapp-work-sdk/1` §7 (`kody-w/rapp-work`) | Proposed: `WorkspaceIndex`, `kind: "workspace-index"`, `workspace-index.json` (`rapp-work-workspace-index/1`), `workspaces.json` (`rapp-work-workspace-index-pointers/1`), `workspace_index_rappid` | Proposal 0011. The SDK calls this object "Organization" today (`kind: "organization"`, `organization.json` with `rapp-work-organization/1`, `workspaces.json` with `rapp-work-organization-pointers/1`, `organization_rappid`). Those records keep verifying |
| **RAPP Workspace** | A private, local-first workspace under RAPP Workspace/1: one RAPPID and one hard `world_id`. The RAPP Work SDK changes it only through exact plans | RAPP Workspace/1 (`kody-w/rapp-workspace`); its SDK integration is `rapp-work-sdk/1` §7 | `rapp-workspace/1`; the SDK's `Workspace`, `kind: "workspace"` and `.rapp-work/` records | None. The proper noun means this and nothing else |
| **workspace composite** | RAPP Workspace/1's routing-only pointer structure over catalog entries and child composites | RAPP Workspace/1 §12 | `workspace-composite` | None. It is not a workspace index |
| **agents workspace** | The Brainstem's `agents/` folder, where a person adds, groups, loads and unloads agents. Only its top-level `*_agent.py` files are live (the grail's flat loader; RAPP proposal 0001) | RAPP Constitution Article XVII (its "User's Workspace"). RAR's Constitution Article XVI already says "agents workspace" | `agents/` | Proposal 0010. No token |
| **Brainstem data** | What the running Brainstem writes as it serves you: memory, state and sessions | RAPP Constitution Article XVI (its "brainstem's workspace") | `.brainstem_data/` and the Brainstem's own state folder | Proposal 0010. No token |
| **host workspace** | The editor's own word for the folders one window has open | Code - OSS, not RAPP | a `.code-workspace` file | Not a RAPP name. A window that shows `agents/` with Brainstem data beside it shows the agents workspace |

Words already taken, so not used for these objects: "agentspace" (RAPP
Article LVI, the public commons), "workbench" (RAPP Article XLIX, a twin's
working area, and the editor's name for its whole window), "registry" (the
signed RAPP/1 §13 root of trust), "catalog" (`rapp-work/1-catalog` and
RAPP Workspace/1 catalogs) and "Brainstem workspace" (RAPP's vault glossary
uses it for Brainstem data). Plain-English "organize" and "organization", as
in "every folder is organization" (RAPP proposal 0001) or RAPP Workspace/1's
"organization tree", name an activity, not an object, and stay as they are.

One more record uses "organization" in the pointer-only sense: the discovery
document of the sidecar profile in `kody-w/rapp-workspace`
(`protocols/rapp-work-sdk/1`, field `organization_pointers`, which point at
`workspace-composite` addresses). Both proposals list it as a follow-up for
that repository.

## How they relate, stated precisely

1. **They are different things.** The agents workspace holds agent files;
   the grail's `load_agents()` imports the top-level `*_agent.py` files on
   every request (`rapp_brainstem/brainstem.py`, lines 1202-1205). A RAPP
   Workspace holds private work under its own RAPPID and `world_id`; the
   Brainstem never loads it, and the SDK's discovery never imports or runs
   what it finds (`rapp-work-sdk/1` §11).
2. **Brainstem data is neither.** The running Brainstem writes it. A view may
   show it beside `agents/`, read-only, as the Brainstem app does; that does
   not make it part of the agents workspace or a RAPP Workspace.
3. **Neither holds the other.** A RAPP Workspace is kept out of `agents/`.
   Whatever copies or packs `agents/` would carry it along: an `organism` egg
   may include `agents/*` (RAPP/1 `SPEC.md` §9.2), and the preserved Tier 2
   build copies the `agents/` tree recursively (Article XVII, lines 996-998;
   its apply mode is refused today). The Brainstem's agents folder is never
   pointed at a RAPP Workspace.
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

## Token and naming analysis

- **No token moves.** `rapp-workspace/1` and every other versioned token are
  untouched. No schema, frame kind, egg variant, registry entry or wire form
  changes. "Agents workspace" and "Brainstem data" are names in prose and in
  an app's interface; neither is a token.
- **RAPP/1 Article 2 (one label, one shape).** The prose name now follows the
  token: "RAPP Workspace" means what `rapp-workspace/1` denotes, and nothing
  else.
- **Article XXV (chat is the only wire).** No request, response, slot or
  schema changes, and nothing is removed or renamed in the constitution; the
  notes are additions.
- **Article XXVI (amendments).** Additive only. Article I is preserved:
  nothing is added to `brainstem.py` or `function_app.py`. Article XXV is
  preserved.
- **Lexicon ruling R6.** Both meanings of "workspace" stay, and each is
  qualified in prose. This proposal does not add a Lexicon ruling: the
  Lexicon's whole-document disposition keeps it as dated product history, so
  the constitution note governs. A dated ruling (Article LII.2) is the
  owner's call.
- **Identity (RAPP/1 Article 7).** Nothing is renamed that carries a RAPPID.
  The agents workspace has no RAPPID of its own; a RAPP Workspace keeps its
  minted RAPPID.
- **The app's workspace file name** (`RAPP Workspace.code-workspace`) is a
  private path in the app's own storage, not a token. Migration step 3 moves
  it additively.
- **Names checked for collisions** across `kody-w/RAPP`, `kody-w/rapp-1`,
  `kody-w/rapp-work`, `kody-w/RAR`, `kody-w/rapp-workspace` and the Brainstem
  kernel's newest tag: "agents workspace" appears only in RAR's Article XVI,
  with the same meaning, and "workspace index" appears nowhere.

## Security and privacy analysis

- **Execution boundary.** Top-level files in the agents workspace run with
  the Brainstem's full rights on every request. A RAPP Workspace is GODD that
  the Brainstem never runs. Calling both "RAPP Workspace" invites the wrong
  expectation in both directions: that `agents/` enjoys the SDK's inert,
  exact-plan handling (it does not), or that a RAPP Workspace is a place for
  agents.
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
- **No new data flow.** This proposal adds no network access, credentials,
  paths, personal data or identities. Its examples are public.

## Migration

One pull request per step, each through its own repository's front door
(Articles XXVIII and XXIX). This workstream opens none of them; the ready
text for each is below, for the owner.

1. **This proposal (RAPP, docs only).** The maintainer accepts the proposal
   by merging it (Article XXX.2), then merges the amendment by hand in its
   own pull request, which cites the proposal (Articles XXVIII.4 and
   XXVIII.6).
   - *Ready text, amendment PR.* Title: "Constitution: the agents workspace
     is not a RAPP Workspace (proposal 0010)". Body: "Adds the two governing
     notes from proposal 0010 to Articles XVII and XVI, word for word, and
     recomputes `stable_tracked_bytes` in
     `tests/fixtures/rapp1-doc-scope.json`, which counts every tracked
     byte. Additive per Article XXVI; changes no code, grail byte or token."
2. **The Brainstem app's words (RAPP, branch `experimental/brainstem-app`,
   by that branch's owner).** Replace "RAPP Workspace" with "agents
   workspace" where it means `agents/`, and title the window "Agents
   Workspace": the window title in `src/startup.ts` (`TITLE`), the trust
   message in `src/launcher.ts` (`TRUST_MESSAGE`), the setting and welcome
   texts in `extensions/rapp/package.json`, `README.md`, code comments, and
   the tests that pin these strings. The roots keep their names, **Agents**
   and **Brainstem data**.
   - *Ready text.* Title: "Brainstem app: call agents/ the agents
     workspace, not the RAPP Workspace (proposal 0010)". Body: "RAPP
     Workspace is RAPP Workspace/1's name. The window shows the agents
     workspace, with Brainstem data beside it, read-only. Strings, docs and
     tests only; no behavior change."
3. **The app's workspace file (same branch, a separate change).** Additive
   first: recognize both `RAPP Workspace.code-workspace` and
   `Agents Workspace.code-workspace` as the app's own file for one release,
   write only the new name, and leave the old file where it is. Then stop
   recognizing the old name. Internal names such as `RappWorkspace` and
   `isRappWorkspaceWindow` may follow (`AgentsWorkspace`,
   `isAgentsWorkspaceWindow`); nobody sees them.
4. **RAPP Workspace/1 (`kody-w/rapp-workspace`, a pull request to `main`).**
   Add the shared naming table to `docs/rapp-work.md`, with one sentence:
   "A Brainstem's agents workspace and its Brainstem data are not RAPP
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
   later pull request).** Name them after what they point at (for example
   `workspace_composite_pointers`) under a new discovery schema token, never
   by widening the current one. This waits for the owner to decide which
   document owns the `rapp-work-sdk/1` label: that repository's sidecar
   profile and `kody-w/rapp-work`'s SDK profile are two different documents
   under the same label (RAPP Work proposal 0011, Context).
7. **The organism (`kody-w/rapp-work`, branch
   `experimental/rapp-work-constitution`, by its maintainer).** Say "agents
   workspace" in the Brainstem app part and mark G22 as proposed. This
   workstream reports it and does not edit it.
8. **Optional docs in this repository (each its own pull request, the
   owner's call).** Qualify "workspace" in the vault glossary entries
   "Brainstem workspace" and "Workspace", in `pages/vault/Foundations/Tier 1
   — Local Brainstem.md` line 127, and in `rapp_brainstem/CONSTITUTION.md`,
   the historical application constitution. The grail comment in
   `rapp_brainstem/brainstem.py` line 1866 is never edited; the Article XVII
   note covers it.

## Rollback

- **Before any merge:** delete the branch.
- **After the amendment merges:** revert the amendment commit. The notes are
  additions and the receipts travel with them, so a revert restores the
  earlier bytes exactly. No runtime behavior changes, so nothing outside the
  repository needs rolling back.
- **The app (steps 2 and 3):** revert its commits. Step 3 leaves the old
  workspace file in place, so an older build still finds its own file, and
  nobody is stranded.
- **RAPP Workspace/1 (step 4):** revert the documentation commit; no pin
  moved.

## Conformance and test vectors

This branch is documentation only, so it adds no test. Its checks, run
locally with Python 3.11 before the push:

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
  the note, and the note contains "agents workspace" and "RAPP Workspace/1".
- **V2 (step 2).** `git grep -n "RAPP Workspace" -- brainstem-app` finds no
  line that means `agents/`. The app's tests pin the window title
  "Agents Workspace" and the trust message.
- **V3 (step 3).** A test opens a window whose workspace file has the old
  name and gets the app's own behavior, and a new write uses only the new
  name.
- **V4 (optional, the owner's call).** The app refuses an agents folder that
  is a RAPP Workspace (one that holds `rappid.json` and `.rapp-work/sdk.json`)
  and says why. This is new behavior, so it needs its own review.

## Reference implementation

None. This is a naming proposal. Nothing here governs until the maintainer
merges the amendment.

## Open questions for the owner (decisions)

1. **The name.** "Agents workspace" (RAR's existing word, recommended) or
   "agent workspace"?
2. **How much the note says.** Keep the placement rule ("Keep RAPP
   Workspaces out of `agents/`") and the one-door rule (SDK operations and an
   exact plan hash) in the Article XVII note, or keep the note to names only?
3. **Article XVI.** Add its pointer note too (recommended), or only the
   Article XVII note?
4. **The app's window.** "Agents Workspace", or another qualified name from
   the table?
5. **RAPP Workspace/1.** A docs-only note now (step 4), with pinned wording
   only at its next re-pin (step 5)?

## Owner actions needed

- Accept or refuse this proposal, and answer the questions above.
- If accepted: merge this proposal (Article XXX.2), then merge the amendment
  pull request by hand (Articles XXVIII.4 and XXX.2).
- Ask the Brainstem app's branch owner for steps 2 and 3.
- Accept or refuse the `kody-w/rapp-workspace` documentation pull request
  (step 4), and decide steps 5 and 6.
- Have the organism's maintainer record G22 as proposed (step 7).

## References

- [`CONSTITUTION.md`](../../CONSTITUTION.md): Articles I, XVI, XVII, XVIII,
  XXV, XXVI, XXVIII (.3, .4, .6), XXIX, XXX.2, XLIX, LII, LV and LVI;
  precedent: the "Amendment (2026-07-08)" notes in Articles XLVI and XLVII.
- [`LEXICON.md`](../../LEXICON.md): Part III, ruling R6.
- RAPP proposal 0001, "Only top-level agents are live", on branch
  `experimental/constitution-live-agents` (not edited here); RAPP proposal
  0002 on `experimental/proposal-0002-tier2-parity` (receipt precedent).
- Grail loader: `rapp_brainstem/brainstem.py` lines 1202-1205, pinned by
  `KERNEL_PIN.json`.
- The Brainstem app: branch `experimental/brainstem-app` at `a81bd9a`,
  `brainstem-app/README.md`, `extensions/rapp/package.json`,
  `extensions/rapp/src/startup.ts`, `extensions/rapp/src/launcher.ts`.
- RAPP Workspace/1: [`kody-w/rapp-workspace`](https://github.com/kody-w/rapp-workspace)
  root `SPEC.md`, `protocols/rapp-workspace/1/SPEC.md` §§2 and 12,
  `protocols/rapp-workspace/1/manifest.json`, `protocols/index.json`,
  `docs/rapp-work.md`, and the sidecar profile `protocols/rapp-work-sdk/1`.
- RAPP Work: [`kody-w/rapp-work`](https://github.com/kody-w/rapp-work) root
  `SPEC.md` §5 (historical), `protocols/rapp-work-sdk/1/SPEC.md` §§2, 7 and
  11, and proposal 0011 on branch `experimental/gap-g11-workspace-index`.
- Canonical `rapp-work/1`: [`kody-w/rapp-1`](https://github.com/kody-w/rapp-1)
  `protocols/rapp-work/1/SPEC.md` §§1–2; RAPP/1 `SPEC.md` §9.2 and
  `CONSTITUTION.md` Articles 2 and 7.
- RAR: [`kody-w/RAR`](https://github.com/kody-w/RAR) `CONSTITUTION.md`
  Article XVI.
- The organism: [`organism/`](https://github.com/kody-w/rapp-work/tree/experimental/rapp-work-constitution/organism)
  on `kody-w/rapp-work` branch `experimental/rapp-work-constitution`: gaps
  G11, G17 and G22, and the Workspaces and Brainstem app parts.
