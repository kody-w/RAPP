---
title: git-add-A is a footgun
status: published
section: Field Notes
hook: Twice during the kernel-distro restructure, `git add -A` swept in files that had reappeared in the working tree (rapp-zoo, specs/, rapp_kernel/). Discipline: stage explicitly. Sanity-check with `git diff --cached --stat` before commit.
---

# git-add-A is a footgun

> **Hook.** Twice during the kernel-distro restructure, `git add -A` swept in files that had reappeared in the working tree (rapp-zoo, specs/, rapp_kernel/). Discipline: stage explicitly. Sanity-check with `git diff --cached --stat` before commit.

## The pattern

You're doing a lot of file moves. You run `git add -A` to stage everything in one go. The commit lands. Looking at the diff stat later, you realize the commit included files you hadn't intended:

- A directory you'd just `rm -rf`'d that reappeared somehow (maybe from a `cp -R` operation, maybe from an editor reload, maybe from a worktree)
- Test fixtures the editor wrote
- A `.copilot_token` that wasn't in `.gitignore`
- An entire venv directory that should have been ignored

`git add -A` doesn't know any of these are unintended. It stages whatever's in the working tree that isn't already in `.gitignore`. The mistake was trusting the working tree to reflect your intent.

## Concrete incidents

During the 2026-05-16 kernel-distro split, this happened twice:

1. **Commit `1f21128`** ("docs: wire pages/kernel.html into every navigation surface") accidentally included `rapp-zoo/` and `specs/` — both directories I'd deleted in the diet commit two days earlier. They had reappeared in the working tree (likely from `cp -R` operations during the restoration pass that didn't strip them from the source) and got swept in. Took a follow-up audit + a Marie Kondo move to clean up.

2. **Commit `55b91b9`** ("vault: 9 new Decisions notes") included another batch of resurrected files (installer extras, tls_proxy.py, organism-layer tools/) that had similarly reappeared. Committed because the user explicitly asked to sync local to remote, but the duplication-with-the-distro is real.

In both cases, the actual changes I cared about were the vault notes and the kernel hub work. The reappeared files came along for the ride.

## The discipline

Three rules that prevent this:

### Rule 1 — Stage explicitly when you know what you're committing

```bash
git add CLAUDE.md README.md pages/kernel.html installer/install.sh
```

Better than `git add -A` because it forces you to enumerate. If you can't list the files, you don't know what you're committing.

### Rule 2 — When you must use `git add -A`, sanity-check with `git diff --cached --stat`

```bash
git add -A
git diff --cached --stat
# Read it. Anything unexpected?
git commit -m "..."
```

The diff stat surfaces unintended additions before the commit lands. Files you didn't mean to touch jump out — especially binary files, large additions, and deletions of things you thought were already deleted.

### Rule 3 — Scan for sensitive files before every commit

```bash
git diff --cached --name-only | xargs grep -lE \
    "AZURE_OPENAI_API_KEY|sk-[A-Za-z0-9]{30,}|AKIA[A-Z0-9]{16}|ghp_[A-Za-z0-9]{30,}"
```

Cheap, fast, catches the highest-cost mistakes (secret leakage). Already caught one live `AZURE_OPENAI_API_KEY` in `tier2/local.settings.json` during this restructure — would have been pushed to a public repo if not for the scan.

## Why files reappear

If you're not sure why a file you `rm`'d shows up again, common causes:

- `cp -R src dst/` where `src` doesn't get cleaned up afterward — the file lives in both places
- Editor "restore previous session" features that re-write recent files on open
- A worktree mounted into the same path
- An auto-save script (linter, formatter, type-checker)
- The user manually restored it between your shell sessions
- A test fixture generator that wrote files as a side effect

The cause matters less than the discipline. If `git status` shows untracked files you don't recognize, *don't* `git add -A` until you've understood where they came from.

## When `git add -A` is actually fine

There are cases where `-A` is the right tool:

- Initial commit of a fresh repo (everything in the working tree IS the intended commit)
- After a `git rm` + `git mv` series where you genuinely want every change reflected
- Automation in CI where the build is deterministic and the tree is sandboxed

Outside those cases, prefer explicit staging.

## See also

- [[The Stale Local Clone Trap]] — sister anti-pattern (trusting local state too much)
- [[The 426-line False Drift]] — another instance of the same family
- [[Verifying Mirror Compliance]] — defensive scripting that catches mistakes
