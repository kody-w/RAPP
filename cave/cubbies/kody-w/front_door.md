# Kody — front door

Founder cubby, public edition. This is the front door of **The RAPP Cave** — the
public mirror of the operator's estate. Where the private batcave keeps the
operator set OUT of the open grail repo behind a collaborator gate, the cave does
the opposite: it ships only the public-safe rapplication anyone can pull. No gh
auth, no collaborator invite, no 404 for outsiders — the front door is open.
Browse it at https://kody-w.github.io/RAPP/cave/ or pull the raw files straight
from https://raw.githubusercontent.com/kody-w/RAPP/main/cave .

## What I'm cooking

- the **rapp-installer** rapplication — the grail brainstem itself, egged &
  self-bootstrapping, so a single public pull stands up a working local brainstem
- the cave itself — this public neighborhood

## How this cubby is organized

- `agents/` - standalone single-file agents, drop one into your brainstem's
  agents dir and go. (Single-file rapplication agents live here too for
  quick grabs.) Public-safe only — no operator/twin internals.
- `rapplications/` - whole rapplications, ONE FOLDER each: the agent, its
  CLI/tools, tests, README and specs together. Start here to understand or
  extend one.
- `eggs/` - hatchable units (`cubby-<name>.egg`, brainstem-egg/2.3-cubby):
  the portable one-file form of a whole cubby or rapplication. Hatch with
  RappAgent — pull, hatch, run, no auth required.
- `show-and-tell/` - dated posts and demos only; durable docs live with
  their rapplication.

## How to join

This cave is PUBLIC, so joining is the inverse of a collaborator invite: fork the
repo and open a PR adding your own cubby under `cubbies/<your-handle>/` (copy
`cubbies/_template/`), or just pull what's here and run it locally. Anyone can
walk in.
