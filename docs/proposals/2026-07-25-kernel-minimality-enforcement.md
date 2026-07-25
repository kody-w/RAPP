# Proposal — Enforcement teeth for Article I (2026-07-25)

**Status:** draft, per Article XXVIII.6 (a proposal precedes an amendment PR).
**Amends:** nothing. **Adds:** enforcement machinery for existing law.

## The finding: the law was already there and it was still broken

On 2026-07-25 a three-format skill hot-loader was implemented as **183 lines in
`brainstem.py`**, merged to canary main, and reverted the same day.

It should never have been written. **Article I** already says the brainstem is
"a loader + an LLM loop + a response splitter. That's it." **Article XXVI**
already says any change loading responsibility into `brainstem.py` that could
be served by a `*_agent.py` is **rejected**.

The capability could be served by a `*_agent.py` — it now is. So the change was
unconstitutional at the moment it was typed, and nothing stopped it: not review,
not preflight, not the ring. Preflight went green. The merge was clean.

**A law that only binds people who remember to read it is a convention.** The
gap is not in the rule; it is that nothing forces the question to be asked.

## What is actually missing from the text

Article I lists what the kernel MAY do. Article XXVI states the rejection rule.
Neither says:

1. **Where a capability should go instead.** The extension points exist but are
   nowhere enumerated, so "could be served by a `*_agent.py`" is left to the
   author's imagination — and an author mid-implementation is the worst-placed
   person to judge it.
2. **Who must prove what.** No burden of proof is assigned, so the default is
   silence, and silence favours the change.
3. **That there is one runtime form.** The reverted design would have left
   `.md` files resident in `agents/` as a second runtime shape. Article I
   implies a single form; it does not say so.

## Proposed additions (as a new Article, not an amendment to I or XXVI)

- **Enumerate the existing extension points**: `agents/*_agent.py` (whose
  `__init__` runs on every `/chat` via `load_agents()`, making it already a
  per-turn hook), `BasicAgent.system_context()`, `perform()`, and the `.egg`.
- **Assign the burden of proof**: a `brainstem.py` change must state in writing
  why each extension point is insufficient. "Simpler there" is a cost transfer
  onto every future reader; "belongs conceptually" is taste.
- **Declare one runtime form**: formats are how a capability *arrives*;
  `agent.py` is what it *is*. A fed skill materialises into an `agent.py`
  rather than living in `agents/` in its own shape.
- **Record the precedent**, so the next author meets a worked example rather
  than an abstraction.

## Why a new Article rather than editing I or XXVI

Both are load-bearing and widely cited. Editing them risks invalidating waiver
pins that record the sha256 of the exact passage cited (Article LIII.2). An
additive Article leaves every existing pin valid.

## Open question for ratification

Article XXVI calls a constitutional amendment "a brainstem-level decision". This
proposal is deliberately **not** self-ratifying: it is filed for Kody's
decision, not merged. An agent adding enforcement to a law that constrains
agents should not also be the one to ratify it.
