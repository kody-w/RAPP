# Contributing to The Batcave

Membership = GitHub collaborator status on this private repo
(`kody-w/rapp-batcave`). The operator adds you:

```bash
gh api -X PUT repos/kody-w/rapp-batcave/collaborators/<your-login> --field permission=push
```

## The three rules

1. **Write only in your own cubby** (`cubbies/<your-handle>/`) plus the
   append-only zones (`events/`, your own entries in `members.json` and
   `cubbies/index.json`). Anything touching someone else's cubby goes
   through a PR they merge. CODEOWNERS + the cubby-guard workflow enforce
   the line.
2. **Bones, not substance.** No PII, no secrets, no customer material —
   `.gitignore` covers the defaults and `batcave stash` refuses
   secret-shaped files (PUBLIC_PRIVATE_BOUNDARY §1.8). Audit your diff
   before pushing.
3. **Personal branches are `cubby/<your-handle>/<topic>`.** They never need
   to merge to `main`; keep WIP there as long as you like. `main` is the
   shared truth everyone's `batcave sync` pulls.

## Day one

```bash
gh repo clone kody-w/rapp-batcave
# from your brainstem chat: "batcave join", then "batcave show_and_tell title=hello"
# or by hand: cp -r cubbies/_template cubbies/<your-handle> && edit cubby.json
```

To run a brainstem against your cubby directly:

```bash
AGENTS_PATH=cubbies/<you>/agents SOUL_PATH=cubbies/<you>/soul.md PORT=7073 \
  python3 brainstem.py   # from your local brainstem checkout
```

Or stream cubby agents into your existing brainstem without commit risk:
`batcave load` (registers them in `.git/info/exclude` — git never sees them).
