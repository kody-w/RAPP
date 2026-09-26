# Proposal 0030 — Article XVII's starter set names what the grail ships

> **Current RAPP/1 authority (rev-5).** For canonicalization, identity, frames,
> wire, eggs, registry, trust, and protocol evolution, follow
> [`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../RAPP1_STATUS.md). This proposal changes none of
> them. It only corrects which agent files the constitution says the
> Brainstem ships, and it changes no code, no agent file, and no grail byte.

## Status

**Draft until the maintainer merges pull request #135, then accepted**
(Article XXX.2).

Pull request #135 holds only this proposal and its receipts. Article XXVIII.6
has a proposal precede the amendment PR, so the amendment described here is a
separate PR, opened only after #135 is merged; that PR also sets this Status
to `implemented`. Articles XXVIII.4 and XXX.2 reserve both merges for the
maintainer: an AI agent drafted this proposal and does not merge it.

This is the constitutional half of #130. Its README half is in #134, an
ordinary documentation PR (Article XXVIII.2).

**Numbering.** Proposals 0001 and 0003 are on `main`. Drafts on other
branches hold 0002, 0010 and 0020, and the numbers between them are held for
drafts in progress. The follow-ups to proposal 0001 that change the constitution
use 0030 to 0039, so this one is 0030. Article XXVIII.3 asks for monotonic
numbers, so if this merges before the lower numbers are used, the maintainer
may renumber it first.

## Context

Line numbers are for `main` at commit `e045fc3`.

### What Article XVII says (lines 925-936)

> ### What's at the top level of `agents/` by default (the starter set)
>
> - `basic_agent.py` — the base class every agent extends.
> - `hacker_news_agent.py` — HTTP call example.
> - `learn_new_agent.py` — agent that writes agents.
> - `save_memory_agent.py` + `recall_memory_agent.py` — the memory pair.
>
> These five files are the teaching curriculum. A new user opening
> `agents/` sees exactly this and understands what a RAPP agent is.

### What the grail ships

The grail, `kody-w/rapp-installer`, has the same top level of
`rapp_brainstem/agents/` at its long-term-support tag `brainstem-v0.6.9`
(the pin in `KERNEL_PIN.json`), at `brainstem-v0.6.16`, and on `main`:

- `basic_agent.py`, the base class every agent extends;
- `context_memory_agent.py`, `hacker_news_agent.py` and
  `manage_memory_agent.py`;
- one folder, `experimental/`, holding `copilot_research_agent.py`, which
  proposal 0001 parks (only top-level `agents/*_agent.py` files are live).

This repository's `rapp_brainstem/agents/` has the same names.
`basic_agent.py` is one of the three grail bytes that `KERNEL_PIN.json`
pins; the other files are this repository's own versions.

### Where the list came from

The five-file list describes this repository's own layout in April 2026:

- `save_memory_agent.py` and `recall_memory_agent.py` entered this
  repository in `a4402f3` (2026-04-18, "starter agents now mirror the OG
  local brainstem"), sat in `rapp_brainstem/agents/` from `743f189`
  (2026-04-19), and gave way to `manage_memory_agent.py` and
  `context_memory_agent.py`, the names the grail ships, in `cef3b91`
  (2026-04-24, brainstem v0.12.2). The grail has shipped those two memory
  agents since `v0.1.0` and has no history of the save/recall names under
  `rapp_brainstem/agents/`.
- `learn_new_agent.py` was added here in `f94df9d` (2026-04-20), moved out
  in `61193ce` (2026-04-24), shipped again in `04342dc` (2026-04-26) and
  removed in `b4f3e31` (2026-05-16). The grail removed its own copy in
  `ffdbf70` (2026-06-22), "release: v0.6.1 — minimal default agents (remove
  LearnNew)".

Proposal 0001 noted the mismatch (its line 169) and left it for a follow-up.
The 2026-09-24 note at the top of Article XVII already governs *loading*
("Any agent that should be live belongs at the top level, whatever the
curriculum rule below says"), but it does not correct the names in the list.

### The same names elsewhere in the constitution

Article I, line 81, rules out central memory features: "Memory is
`save_memory_agent.py` + `recall_memory_agent.py` + its storage shim. Never
an in-core dict." The rule is unaffected; only the two file names are
stale. Article XVIII, line 1138, uses `save_memory_agent.py` only as an
example of how a file name renders as a human name ("Save Memory"); that
example makes no claim about what ships, so this proposal leaves it.

Both passages sit inside the historical section, which runs from the marker
at line 10 to the marker at line 4016.

## Proposed change

The change is additive only (Article XXVI: no removals), following #124: a
governing blockquote note directly under each passage it corrects, whose old
wording stays and is marked as not governing, and a dated section after
#124's section at the end of the file. That section sits outside the
historical section, so it carries the rule as current guidance, as #124's own
end section does for its notes in Articles XVII, XVIII and XX. `DATE` below
stands for the day the maintainer accepts this proposal by merging it, as
proposal 0001's notes carry the date of the maintainer's ruling. Links in the
quoted text are relative to `CONSTITUTION.md`, where the text goes.

1. **Article XVII, directly under the heading "What's at the top level of
   `agents/` by default (the starter set)"** (line 925). This is the change
   #130 asks for.

   > **Amendment (DATE) — the starter set is what the grail ships; additive per Article XXVI.** At the top level of `rapp_brainstem/agents/`, the grail (`kody-w/rapp-installer`) ships `basic_agent.py` (the base class every agent extends), `context_memory_agent.py`, `hacker_news_agent.py` and `manage_memory_agent.py`, at its long-term-support tag `brainstem-v0.6.9` (the `KERNEL_PIN.json` pin) and at `brainstem-v0.6.16`. Its one folder, `experimental/`, holds `copilot_research_agent.py`, which is parked. It does not ship `learn_new_agent.py`, `save_memory_agent.py` or `recall_memory_agent.py`: the list below describes this repository's own layout in April 2026, when it briefly used the save/recall pair in place of the grail's two memory agents. The list and the "five files" sentence below are preserved (Article XXVI) but do not govern; this note governs, together with the 2026-09-24 note at the top of this article and the amendment of the same date at the end of this file. See [proposal 0030](./docs/proposals/0030-starter-set-names-what-the-grail-ships.md).

2. **Article I, line 81** (optional; the maintainer may take item 1 alone).
   Indented under the bullet, so that it stays part of it:

   > **Amendment (DATE) — the memory agents' names; additive per Article XXVI.** The memory agents the grail ships are `manage_memory_agent.py` and `context_memory_agent.py`; the grail has never shipped the names `save_memory_agent.py` and `recall_memory_agent.py`, which this repository used from 2026-04-18 to 2026-04-24. The rule stands: memory is agents plus the storage shim, never an in-core dict. See [proposal 0030](./docs/proposals/0030-starter-set-names-what-the-grail-ships.md).

3. **A dated section at the end of the file**, after the section
   "Amendment (2026-09-24) — Only top-level agents are live". If the
   maintainer takes item 1 alone, it names Article XVII only.

   > ## Amendment (DATE) — The starter set is what the grail ships
   >
   > > **Additive per Article XXVI; see [proposal 0030](./docs/proposals/0030-starter-set-names-what-the-grail-ships.md).** Articles I and XVII sit inside the historical section above, but which agent files the Brainstem ships at the top of `agents/` is current guidance, so it is stated here as well. At the top level of `rapp_brainstem/agents/`, the grail (`kody-w/rapp-installer`) ships `basic_agent.py`, `context_memory_agent.py`, `hacker_news_agent.py` and `manage_memory_agent.py`, and one folder, `experimental/`, whose `copilot_research_agent.py` is parked. The notes of the same date in Articles I and XVII apply this to their text, and they govern how those passages are read.

Proposal 0010, a draft on the branch `experimental/gap-g22-workspace-names`,
adds a separate note directly under Article XVII's heading (line 894) about
the word "workspace". The two notes don't overlap, and neither depends on
the other.

### Article XXVI check

Nothing is removed or repurposed. The notes and the end section are
additions that say which wording governs, as #124's notes and end section do,
and no rule changes: the starter set still teaches what an agent is, and
memory is still agents.

## Migration

Steps 1 and 2 each land in one PR. Step 3 follows step 2.

1. **Accept the proposal.** Pull request #135: this file and its receipts.
   The maintainer's merge accepts it (Articles XXVIII.4 and XXX.2). Until
   then, nothing here governs.
2. **Apply the amendment.** A separate PR that adds the notes and the end
   section from "Proposed change", cites this proposal (Article XXVIII.6), sets this
   Status to `implemented`, and refreshes the receipts
   (`tests/fixtures/rapp1-doc-scope.json`, checked by
   `tools/check_rapp1_docs.py`). Article XXX.2 requires human review and
   merge for a constitutional amendment.
3. **Sweep.** Article LIII.1: the amendment is not done until the retired
   form, the five-file list presented as the current starter set, has been
   hunted ecosystem-wide and every hit carries a `drift()` issue. At
   `e045fc3` the other mentions in this repository are historical, retired
   or examples, for instance `learn_new_agent.py` in `ECOSYSTEM.md` line
   419, `ECOSYSTEM_MAP.md` lines 105 and 266, `OSI.md` line 143,
   `installer/plant.sh`, `pages/grail-brainstem/index.html`,
   `pages/sphere.html`, `cave/agents/cave_agent.py` and the vendored
   `rapp_swarm/_vendored/agents/learn_new_agent.py`; proposal 0001 lines
   169-170; and the dated vault posts about the memory pair. Inside
   `rapp_brainstem/`, which these changes do not touch,
   `rapp_brainstem/CLAUDE.md` line 105, `rapp_brainstem/CONSTITUTION.md`
   lines 709-711 and 739-740, and `rapp_brainstem/soul.md` line 135 also
   name the old files. The sweep classifies each one when the amendment
   merges.

## Rollback

Revert the amendment PR. The notes are additions, so reverting them restores
the previous reading. This proposal stays as the record (Article XXVIII.3).

## References

- Articles I (line 81), XVII (lines 894-936), XVIII (line 1138), XXVI,
  XXVIII.3, XXVIII.4, XXVIII.6, XXX.2 and LIII.1 of `CONSTITUTION.md`, and
  its section "Amendment (2026-09-24) — Only top-level agents are live"
  (line 4345).
- Proposal 0001, `docs/proposals/0001-only-top-level-agents-are-live.md`
  (#119, squash-merged as `a879530`), and its amendment #124 (`e045fc3`).
- Drift issue #130; its README half, #134.
- The grail's `rapp_brainstem/agents/` at `kody-w/rapp-installer` tags
  `brainstem-v0.6.9` and `brainstem-v0.6.16`, and its commit `ffdbf70`.
- This repository's commits `a4402f3`, `743f189`, `cef3b91`, `f94df9d`,
  `61193ce`, `04342dc` and `b4f3e31`.
