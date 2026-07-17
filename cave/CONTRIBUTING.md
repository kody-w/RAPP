# Contributing to The RAPP Cave

> **RETIRED CONTRIBUTION GUIDE — do not follow the bounded commands.** Cave
> membership, cubby streaming, catalog, and installer workflows are historical
> application design, not current acceptance paths. For canonicalization,
> identity, frames, wire, eggs, registry, trust, and protocol evolution, follow
> RAPP/1 rev-5 through
> [`RAPP1_AUTHORITY.json`](../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../RAPP1_STATUS.md).

<!-- RAPP1-HISTORICAL-SECTION-START -->

Membership is **open**. There's no collaborator grant and no operator approval —
the cave lives in the public repo [`kody-w/RAPP`](https://github.com/kody-w/RAPP)
under `cave/`. You join the same way you'd contribute to any open-source project:
fork, branch, add your cubby, open a PR.

```bash
gh repo fork kody-w/RAPP --clone     # or clone your fork by hand — no gh required
cp -r cave/cubbies/_template cave/cubbies/<your-login>
$EDITOR cave/cubbies/<your-login>/cubby.json cave/cubbies/<your-login>/front_door.md
# commit on a personal branch, push to your fork, open a PR
```

On merge, the cubby is yours — and the world can already pull it.

## The three rules

1. **Write only in your own cubby** (`cave/cubbies/<your-login>/`) plus the
   append-only zones (your own `show-and-tell/`, your one row in
   `cubbies/index.json`). Anything touching someone else's cubby goes through a
   PR they review. CODEOWNERS + the cubby-guard workflow enforce the line.
2. **Bones, not substance — and this cave is PUBLIC.** No PII, no secrets, no
   customer material, ever. `.gitignore` covers the defaults and `cave stash`
   refuses secret-shaped files (PUBLIC_PRIVATE_BOUNDARY §1.8). Everything you put
   here is world-readable the instant it merges — post slugs and status, never
   substance you wouldn't publish in the open. Audit your diff before you push.
3. **Personal branches are `cubby/<your-login>/<topic>`** (on your fork). They
   never need to merge to `main`; keep WIP there as long as you like. The cave's
   `main` (in `kody-w/RAPP`) is the shared truth everyone's `cave sync` / plain
   `curl` pulls.

## Day one

```bash
gh repo fork kody-w/RAPP --clone
# from your brainstem chat: "cave join", then "cave show_and_tell title=hello"
# or by hand: cp -r cave/cubbies/_template cave/cubbies/<your-login> && edit cubby.json
# push to your fork and open a PR
```

To run a brainstem against your cubby directly:

```bash
AGENTS_PATH=cave/cubbies/<you>/agents SOUL_PATH=cave/cubbies/<you>/soul.md PORT=7073 \
  python3 brainstem.py   # from your local brainstem checkout
```

Or stream any cubby's agents into your existing brainstem without commit risk:
`cave load` (registers them in `.git/info/exclude` — git never sees them).

<!-- RAPP1-HISTORICAL-SECTION-END -->
