# Proposal 0031 — The historical app constitution says only top-level agents are live

> **Current RAPP/1 authority (rev-5).** For canonicalization, identity, frames,
> wire, eggs, registry, trust, and protocol evolution, follow
> [`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../RAPP1_STATUS.md). This proposal changes none of
> them. It only adds dated notes to the historical application constitution,
> `rapp_brainstem/CONSTITUTION.md`, so that it no longer reads as if files in
> folders under `agents/` load. It changes no code, no agent file, and no
> grail byte.

## Status

**Draft until the maintainer merges pull request #136, then accepted**
(Article XXX.2).

Pull request #136 holds only this proposal and its receipts. Article XXVIII.6
has a proposal precede the amendment PR, so the amendment described here is a
separate PR, opened only after #136 is merged; that PR also sets this Status
to `implemented`. Articles XXVIII.4 and XXX.2 reserve both merges for the
maintainer: an AI agent drafted this proposal and does not merge it. The
amendment changes `rapp_brainstem/CONSTITUTION.md`, and proposal 0001
(Migration step 3) merges a change to that file only on the maintainer's
authorization.

This proposal answers drift issue #126. Per Article LIII.1, #126 stays open
until a re-sweep after the amendment confirms it.

**Numbering.** Proposals 0001 and 0003 are on `main`. Drafts on other
branches hold 0002, 0010, 0020 and 0030 (#135). The follow-ups to proposal
0001 that change a constitution use 0030 to 0039, and this is the second, so
it is 0031. Article XXVIII.3 asks for monotonic numbers, so the maintainer
may renumber it before merging.

## Context

Line numbers are for `main` at commit `3314302`.
`rapp_brainstem/CONSTITUTION.md` has not changed since `e045fc3`, where #126
was filed, so #126's line numbers still hold.

### The rule

Proposal 0001 (`docs/proposals/0001-only-top-level-agents-are-live.md`,
accepted in #119 as `a879530` and applied by #124 as `e045fc3`): in the local
Brainstem (Tier 1), live agents come only from the top-level
`agents/*_agent.py` files, hot-loaded on every `/chat` request. Every folder
under `agents/` is organization only and never loads, whatever its name, and
loading or unloading an agent is a plain file move. The grail's
`load_agents()` (`rapp_brainstem/brainstem.py` at
`kody-w/rapp-installer@brainstem-v0.6.9`, lines 1202-1205) globs
`os.path.join(AGENTS_PATH, "*_agent.py")`, which is one level. #124 added
dated notes to the root `CONSTITUTION.md`, in Articles XVII, XVIII and XX,
and a dated section at its end.

### The file

`rapp_brainstem/CONSTITUTION.md` (1,104 lines) is the historical application
constitution. Its header (lines 3-8) marks it "superseded current guidance",
and the markers at lines 10 and 1104 put its whole body in a historical
section. It is this repository's own file: the grail's
`rapp_brainstem/CONSTITUTION.md` at `brainstem-v0.6.9` has 182 lines, no
Article XII, and no mention of `workspace_agents/` or `rglob`. No kernel pin,
source-ledger record or inventory path set covers its bytes.
`tests/fixtures/rapp1-doc-scope.json` lists it by path three times
(`classifications.historical`, `audit.categories.POST-STALE-LIVE-DOC` and
`audit.provenance.existing_report.R1-DOC-01.current_live_paths`), and its
bytes count toward `audit.current_inventory.stable_tracked_bytes`.

### Why it says what it says

The text was an accurate record of this repository's own copy of the
Brainstem at the time. Commit `c1f356e` (2026-04-21, "Make agents/ a
user-organized recursive tree") made that copy's `load_agents()` walk
`agents/` with `rglob("*_agent.py")` and wrote the recursive tree into this
file; `d7f067e` (v0.11.0, the same day) put the tree under
`workspace_agents/`. Commit `06d16f1` (2026-05-01, "brainstem: revert kernel
to canonical shape") put the one-level glob back, and this file was not
updated. So this repository's tags `brainstem-v0.10.0` through
`brainstem-v0.12.1` recursed and `brainstem-v0.12.3` does not. Every grail
release since `v0.1.0` (`kody-w/rapp-installer` `8220932`, 2026-03-05) has
globbed one level.

### What it still says

These are #126's hits:

- **Article I-A, lines 70-71.** Agent discovery follows "Recursion rules per
  Article XII".
- **Article IX, lines 497-499, 506-507 and 544.** A workshop is a folder
  under `agents/workspace_agents/<my_swarm>/` that iterates "against the
  hotload loop", with the "Same hotload loop on both ends", and a folder
  under `workspace_agents/` is the place to develop.
- **Article XII.** The showroom and `workspace_agents/` layers with
  reserved subfolders (lines 692-719); "A recursive tree inside
  `workspace_agents/`", where "`*_agent.py` files inside it load" (lines
  723-770); organizational folders only under `workspace_agents/` and a
  curriculum-only top level (lines 779-785); no depth limit (line 791);
  `swarm_factory_agent` at the top of `workspace_agents/` (lines 792-795);
  and "Discovery": "`load_agents()` walks `agents/` recursively via
  `rglob("*_agent.py")`", with Tier 2 mirroring that shape (lines 797-805).
- **Article XIII, lines 823, 828-834 and 851-852.** "New agent" writes
  `*_agent.py` "at chosen location"; "Disable", "Enable" and "Mark
  experimental" are moves into and out of reserved folders, shown "with
  their semantics explained"; hiding those folders is a don't.
- **Article XIV, lines 877-878, 885 and 894.** Reserved folders are hidden
  in the beginner view and labelled in the advanced one.

The starter-set file names in Article XII (lines 709-711 and 739-740) are
a different question, which proposal 0030's sweep covers.

## Proposed change

The change is additive only (Article XXVI: no removals), following #124: a
governing blockquote note at each place below, with the old wording kept and
marked as not governing. The anchors match the ones #124 used in the root
`CONSTITUTION.md`: the article heading (Article XVII there, XII here), the UI
mapping (XVIII there, XIII here) and the beginner view's reserved-folders
bullet (XX there, XIV here). The texts are not copies of each other, so the
notes are adapted rather than copied. `DATE` below stands for the day the
maintainer accepts this proposal by merging it, as proposal 0001's notes
carry the date of the maintainer's ruling. Links in the quoted text are
relative to `rapp_brainstem/CONSTITUTION.md`, where the text goes.

All five notes fall inside the file's historical section, and no dated
section is added at its end. The whole file is historical, its header
already sends readers to current guidance, and the rule is stated as current
guidance at the end of the root `CONSTITUTION.md`, in #124's section
"Amendment (2026-09-24) — Only top-level agents are live", which the notes
cite. The header, the file's only text outside the historical section, does
not change.

1. **Article I-A, lines 70-71.** Indented under the "Agent discovery" bullet,
   so that it stays part of it:

   > **Amendment (DATE) — discovery is the top level only; additive per Article XXVI.** Agent discovery means the top-level `agents/*_agent.py` files only, reloaded from disk on every request. It does not recurse, so no file in a folder under `agents/` loads. "Recursion rules per Article XII" is preserved but does not govern; the note of the same date in Article XII governs. See [proposal 0031](../docs/proposals/0031-app-constitution-only-top-level-agents-are-live.md).

2. **Article IX, directly under its heading** (line 493):

   > **Amendment (DATE) — a workshop folder is organization, not live; additive per Article XXVI.** Only top-level `agents/*_agent.py` files are live (the note of the same date in Article XII), so the files of a workshop under `agents/workspace_agents/<my_swarm>/`, or in any other folder, do not hot-load. To run them, move them to the top level of `agents/`; to unload them, move them back into a folder. A singleton is live once it sits at the top level of `agents/`. Where the text below says a workshop in a folder iterates against the hotload loop, or that both shapes share the same hotload loop, this note governs. See [proposal 0031](../docs/proposals/0031-app-constitution-only-top-level-agents-are-live.md).

3. **Article XII, directly under its heading** (line 679). This is the main
   note, and it follows #124's note in root Article XVII:

   > **Amendment (DATE) — only top-level agents are live; additive per Article XXVI.** In the local Brainstem (Tier 1), live agents come only from the top-level `*_agent.py` files in `agents/` (the `AGENTS_PATH` folder), hot-loaded on every `/chat` request. The grail's `load_agents()` (`rapp_brainstem/brainstem.py` at `kody-w/rapp-installer@brainstem-v0.6.9`, lines 1202-1205) does `pattern = os.path.join(AGENTS_PATH, "*_agent.py")` and then `glob.glob(pattern)`: one level, no recursion, no `rglob`. Every folder under `agents/` is organization only and never loads, whatever its name: `workspace_agents/`, `experimental_agents/`, `disabled_agents/` and `local_agents/` are conventions with no engine meaning, and an agent kept in any folder, such as `workspace_agents/swarm_factory_agent.py`, is parked, not live. Loading or unloading an agent is a plain file move: move it to the top of `agents/` to load it, or into any folder to unload it. Any agent that should be live belongs at the top level, whatever the showroom rules below say. The recursive-tree, auto-loading-folder, reserved-name, `rglob` and Tier 2 mirroring wording below is preserved (Article XXVI: additive-only, no removals) but does not govern; this note governs, together with the amendment "Only top-level agents are live" (2026-09-24) at the end of the root [`CONSTITUTION.md`](../CONSTITUTION.md). Tier 2 (`rapp_swarm/`) loads differently; [proposal 0001](../docs/proposals/0001-only-top-level-agents-are-live.md) records how, as of 2026-09-25. See [proposal 0031](../docs/proposals/0031-app-constitution-only-top-level-agents-are-live.md).

4. **Article XIII, directly under the heading "Mapping"** (line 819). It
   follows #124's note in root Article XVIII:

   > **Amendment (DATE) — load and unload are file moves; additive per Article XXVI.** Only top-level `agents/*_agent.py` files are live (the note of the same date in Article XII), and the engine discovers nothing below the top level. **Load** = move the file to the top level of `agents/`. **Unload** = move it into any folder, or delete it. A plain file move, such as drag and drop in a file manager, is all it takes, and "New agent" writes a live agent only at the top level. The "Disable", "Enable" and "Mark experimental" rows below are such moves and remain UI conventions, but `experimental_agents/` and `disabled_agents/` have no engine meaning: any folder unloads, and only a move to the top level loads. Where the text below calls those folders reserved or gives them semantics to explain, this note governs. See [proposal 0031](../docs/proposals/0031-app-constitution-only-top-level-agents-are-live.md).

5. **Article XIV, lines 877-878.** Indented under the beginner view's bullet
   "Reserved folders (`experimental_agents/`, `disabled_agents/`) hidden.",
   so that it stays part of it. It follows #124's note in root Article XX:

   > **Amendment (DATE) — no engine-reserved folders; additive per Article XXVI.** The engine reserves no folder names: every folder under `agents/` is organization only, and nothing in a folder is live (the note of the same date in Article XII). Whether a view shows or hides a folder is a display choice and changes nothing about what loads. Where this article calls those folders reserved, in either view, this note governs. See [proposal 0031](../docs/proposals/0031-app-constitution-only-top-level-agents-are-live.md).

### Article XXVI check

Nothing is removed or repurposed. The notes are additions that say which
wording governs, as #124's notes do, and they add no new rule: each one
applies proposal 0001's rule, which is already accepted, to this file's
text.

### Receipts

The amendment adds bytes to one tracked file and adds no path. The path sets
in `RAPP1_ADAPTATION_INVENTORY.json` and `tests/fixtures/rapp1-doc-scope.json`
therefore stay as they are, and only
`audit.current_inventory.stable_tracked_bytes` moves;
`tools/rapp1_receipts.py --write` refreshes it.

## Migration

Steps 1 and 2 each land in one PR. Step 3 follows step 2.

1. **Accept the proposal.** Pull request #136: this file and its receipts.
   The maintainer's merge accepts it (Articles XXVIII.4 and XXX.2). Until
   then, nothing here governs.
2. **Apply the amendment.** A separate PR, opened by the maintainer or on
   the maintainer's authorization, adds the five notes from "Proposed
   change" with `DATE` filled in, cites this proposal (Article XXVIII.6),
   sets this Status to `implemented`, and refreshes the receipts
   (`tools/rapp1_receipts.py --write`, checked by
   `tools/check_rapp1_docs.py`). Article XXX.2 requires human review and
   merge for a constitutional amendment.
3. **Sweep.** Article LIII.1: the amendment is not done until the retired
   form has been hunted ecosystem-wide and every hit carries a `drift()`
   issue. #126's sweep notes classify the other mentions in this
   repository, and after the amendment merges, a re-sweep of this file
   decides whether #126 is fixed. `rapp_brainstem/.gitignore` (#127) needs
   only a comment fix, which is not a constitution change and is not part
   of this proposal.

## Rollback

Revert the amendment PR. The notes are additions, so reverting them restores
the previous reading. This proposal stays as the record (Article XXVIII.3).

## Alternatives considered

- **Rewrite or delete the retired passages.** Article XXVI allows no
  removals, and the passages are an accurate record of what this
  repository's copy did from `c1f356e` to `06d16f1`.
- **Leave the file alone because it is marked historical.** The header says
  "superseded", but Articles XII to XIV still state the retired form as
  rules, with no pointer to what replaced them. A reader who follows them
  puts agents in folders and expects them to load (#126, "Severity").
- **Add a dated section at the end, as #124 did in the root
  `CONSTITUTION.md`.** The root file is current guidance with a historical
  section inside it, while this file is historical as a whole. The rule
  stays stated as current guidance in one place, the root file's 2026-09-24
  section, and the notes point to it.

## References

- Articles XXVI, XXVIII.3, XXVIII.4, XXVIII.6, XXX.2 and LIII.1 of
  `CONSTITUTION.md`, its notes of 2026-09-24 in Articles XVII (line 896),
  XVIII (line 1019) and XX (line 1149), and its section "Amendment
  (2026-09-24) — Only top-level agents are live" (line 4345).
- Proposal 0001, `docs/proposals/0001-only-top-level-agents-are-live.md`
  (#119, squash-merged as `a879530`), and its amendment #124 (`e045fc3`);
  proposal 0030 (#135).
- Drift issues #126 (this file) and #127 (`rapp_brainstem/.gitignore`).
- The grail's `rapp_brainstem/brainstem.py` and
  `rapp_brainstem/CONSTITUTION.md` at `kody-w/rapp-installer` tag
  `brainstem-v0.6.9`, and its commit `8220932` (`v0.1.0`).
- This repository's commits `c1f356e`, `d7f067e` and `06d16f1`, and its
  tags `brainstem-v0.10.0` to `brainstem-v0.12.3`.
