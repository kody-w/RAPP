---
title: The Stale Local Clone Trap
status: published
section: Removals
hook: General anti-pattern — treating a local git clone as a source of truth for canonical content. Always pull from the canonical URL (raw.githubusercontent.com/.../main/...) instead. Memory-noted for future AI sessions.
---

# The Stale Local Clone Trap

> **Hook.** General anti-pattern — treating a local git clone as a source of truth for canonical content. Always pull from the canonical URL (`raw.githubusercontent.com/.../main/...`) instead. Memory-noted for future AI sessions.

## The pattern

You need to read a file from a "canonical" repo (grail, an upstream, a sister project). You see the repo cloned locally on your machine. You `cat` it or `cp` from it, treating the local version as authoritative.

But the local clone might be:

- On a feature branch that hasn't been merged
- Behind origin/main by hours, days, or weeks
- Ahead of origin/main with uncommitted local work
- Cloned from a fork, not the canonical repo
- Stale leftover from a different project entirely
- Modified in place during debugging and never reverted
- A worktree with checkout of an old tag

In every one of these cases, the local file IS NOT what `kody-w/<repo>/main` actually contains right now.

## When this hurts

The damage scales with how much you trust the local content:

- **Read-only inspection** — minor; you formed an opinion based on stale data, but you can re-verify before acting
- **Citation in docs** — moderate; you wrote "grail does X" when grail actually does Y; needs correction
- **`cp` into a kernel mirror** — severe; you've now propagated stale content as if it were canonical. See [[The 426-line False Drift]]
- **Automated drift detection that uses the local clone as the baseline** — catastrophic; the system thinks everything's fine while drift accumulates

## The fix

Two rules:

### Rule 1 — Always read from the canonical URL

For anything labeled "canonical" (grail, the SPEC, an upstream), read from `raw.githubusercontent.com/<owner>/<repo>/main/<path>` (or the equivalent for non-GitHub hosts). Use `curl -fsSL`. Don't `cat` a local clone.

```bash
# WRONG
cat ~/Documents/GitHub/Rappter/rapp-installer/rapp_brainstem/brainstem.py

# RIGHT
curl -fsSL https://raw.githubusercontent.com/kody-w/rapp-installer/main/rapp_brainstem/brainstem.py
```

### Rule 2 — If you must use a local clone, verify it first

If offline work requires using a local clone, verify before reading:

```bash
cd /path/to/clone
git fetch origin
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] || { echo "clone not at origin/main"; exit 1; }
[ -z "$(git status -uno --porcelain)" ] || { echo "clone has uncommitted changes"; exit 1; }
```

Or more pragmatically: if the clone isn't on `main` with clean `status -uno`, refuse to use it as a source of truth. Pull fresh content from the canonical URL.

## Why local clones go stale

It's not laziness — there are legitimate reasons a local clone diverges:

- You were investigating a bug on a feature branch
- You forgot to switch back after a PR review
- You pulled, made local changes, never committed
- You cloned 6 months ago and never updated
- Multiple worktrees share the same clone

The clone is YOUR working copy. It's optimized for whatever you're working on, not for being authoritative.

## The lesson, internalized

When you find yourself thinking *"grail says X"* or *"the upstream has Y"*, the next thought should be *"how do I know — did I just check the canonical URL, or am I trusting my memory + a local clone?"*

For AI assistants reading this in a future session: **never trust a local clone for canonical reads. Always curl.** The memory entry at `project_grail_is_github_not_local.md` is there to bake this in.

## See also

- [[The 426-line False Drift]] — the concrete incident that surfaced this
- [[Mirror Spec]] — the contract that depends on canonical reads
- [[Verifying Mirror Compliance]] — the right way to check kernel files
- [[git-add-A is a footgun]] — sister anti-pattern in the same domain (trusting local state too much)
