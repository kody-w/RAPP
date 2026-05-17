---
title: The 426-line False Drift
status: published
section: Removals
hook: Cautionary tale — I almost downgraded brainstem.py from 1544 to 1118 LOC because I trusted a stale local clone of grail instead of GitHub main. The drift-check script caught it before push. Lesson: source of truth is the canonical URL, not the local file system.
---

# The 426-line False Drift

> **Hook.** Cautionary tale — I almost downgraded `brainstem.py` from 1544 to 1118 LOC because I trusted a stale local clone of grail instead of GitHub main. The drift-check script caught it before push. Lesson: source of truth is the canonical URL, not the local file system.

## What happened

During the [[2026-05-16 — Kernel-Distro Split]], I diff-checked the kernel mirror's `brainstem.py` against what I thought was grail's `brainstem.py`. The "grail" I checked was the local clone at `~/Documents/GitHub/Rappter/rapp-installer/` — which I assumed was current.

That clone was on a feature branch (`feature/hatch-rapp-agent`) at commit `b4b63f2`, with `VERSION=0.4.0` and `brainstem.py` at 1,118 lines. It also had uncommitted working-tree modifications.

The real grail main on GitHub was at `VERSION=0.6.0` with `brainstem.py` at 1,544 lines — exactly what the kernel mirror was already carrying.

I diagnosed the mirror as having "+426 LOC of post-grail accretion" and started planning extractions (which features to refactor as organs, which `_tlog()` calls to drop, etc.). I then `cp`'d the local-clone brainstem.py over the mirror's. **One push away from shipping the regression.**

## What caught it

`tests/mirror-drift.sh` — the script I'd written explicitly for the Mirror Spec contract — does its diff against the *canonical URL*, not the local clone:

```bash
diff <(curl -fsSL "https://raw.githubusercontent.com/kody-w/rapp-installer/main/$f") "$f"
```

After the `cp`, I ran the drift-check. It immediately flagged:

```
DRIFT rapp_brainstem/brainstem.py (1118 vs 1544 lines)
DRIFT rapp_brainstem/VERSION (0.4.0 vs 0.6.0)
```

That told me the mirror NOW disagreed with grail main — which meant the mirror had been right before my `cp`. Reverted via `git checkout HEAD -- ...` before the commit.

## The general lesson

**The local file system is never authoritative. Any operation that treats a local clone as a source of truth is wrong.**

Specifically:

- Local clones can be on feature branches
- Local clones can have stale `main`
- Local clones can have uncommitted modifications
- Local clones can be cloned from a fork
- Local clones can be the user's WIP that has nothing to do with upstream

The only authoritative reads are from canonical URLs. For grail, that's:

```
https://raw.githubusercontent.com/kody-w/rapp-installer/main/rapp_brainstem/brainstem.py
```

For any other repo, substitute the path. Never `cp` from a local clone to a kernel mirror without first verifying `git rev-parse HEAD` matches `git rev-parse origin/main` AND `git status -uno` is clean.

## The save mechanism worked

This is the rare case where defensive tooling actually saved the system. I'd written `tests/mirror-drift.sh` for a different reason — to catch silent drift accumulating over time. The fact that it ran against the GitHub URL (not the local clone) was almost incidental. But it caught the mistake before push.

The lesson for tooling: **defensive scripts should compare against canonical sources, not against whatever's most convenient.** A drift-check that compared against a local clone would have *confirmed* the bad `cp` instead of catching it.

## What's permanent in the repo from this

- `tests/mirror-drift.sh` exists and is correct (always checks against GitHub raw)
- A memory entry at `~/.claude/projects/.../memory/project_grail_is_github_not_local.md` so future AI sessions don't repeat the mistake
- This vault note

## See also

- [[Mirror Spec]] — the contract this would have violated
- [[The Stale Local Clone Trap]] — the more general anti-pattern
- [[2026-05-16 — Kernel-Distro Split]] — the larger work this was part of
- [`tests/mirror-drift.sh`](../../../tests/mirror-drift.sh) — the script that caught it
