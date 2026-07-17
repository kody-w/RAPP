---
title: Verifying Mirror Compliance
status: historical
section: Process
hook: The one-liner that confirms this kernel mirror is byte-identical to grail. Run it after any kernel-touching PR. "DRIFT" means restore from grail, not edit in place.
---

# Verifying Mirror Compliance

> **SUPERSEDED runbook — historical record only.** For canonicalization,
> identity, frames, wire, eggs, registry, trust, and protocol evolution, follow
> RAPP/1 rev-5 through
> [`RAPP1_AUTHORITY.json`](../../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../../RAPP1_STATUS.md). Current mirror verification is
> against [`KERNEL_PIN.json`](../../../KERNEL_PIN.json) and immutable
> `kody-w/rapp-installer@brainstem-v0.6.9`, never moving `main` or `latest`.

<!-- RAPP1-HISTORICAL-SECTION-START -->

> **Hook.** The one-liner that confirms this kernel mirror is byte-identical to grail. Run it after any kernel-touching PR. "DRIFT" means restore from grail, not edit in place.

## The check

`tests/mirror-drift.sh`:

```bash
#!/usr/bin/env bash
set -e
GRAIL_RAW="https://raw.githubusercontent.com/kody-w/rapp-installer/brainstem-v0.6.9"

for f in rapp_brainstem/brainstem.py \
         rapp_brainstem/VERSION \
         rapp_brainstem/agents/basic_agent.py; do
  diff <(curl -fsSL "$GRAIL_RAW/$f") "$f" >/dev/null 2>&1 \
    && echo "OK    $f" \
    || echo "DRIFT $f"
done
```

Three `OK` lines = compliant mirror. Any `DRIFT` line = the mirror has diverged from grail and is no longer a valid mirror.

## When to run it

- **After any PR that touches `rapp_brainstem/`** — even adjacent edits (`soul.md`, `requirements.txt`) are worth a drift-check, because file shuffling sometimes inadvertently touches the sacred three.
- **After hatching a distro** — to confirm the distro didn't modify the kernel.
- **Before tagging a release** — release tags should always land on a compliant mirror.
- **Periodically, as a heartbeat** — even if nothing seems to have changed locally, run it weekly. Sometimes drift comes from somewhere unexpected (an editor auto-format on save, a script that re-wrote line endings).

## What "DRIFT" means

A `DRIFT` line means *the mirror's file is no longer byte-identical to grail's file at this path*. Three possible causes:

1. **The mirror's file was edited.** Restore from grail: `curl -fsSL "$GRAIL_RAW/$f" -o "$f"` and commit.
2. **The immutable pin and a claimed upstream branch disagree.** The pin wins.
   Do not follow the branch or mutate the three local frozen bytes.
3. **A new grail version is proposed.** That requires an explicit authority
   event and a new immutable pin; ordinary drift remediation cannot advance it.

The restore command is `cp` (or `curl`), never `git revert`. Drift is a structural fact about file contents, not a git history fact.

## What "DRIFT" does NOT mean

- **It does not mean the mirror is broken in any other sense.** Mirror compliance is narrow: it covers exactly three files. Anything else can be the mirror's prerogative.
- **It does not mean grail is right and the mirror is wrong morally.** It means they disagree, and the mirror's job is to match grail. If you think grail should change, that's a separate conversation with Kody — never with the mirror.
- **It does not mean the file was edited by AI.** Sometimes it's an editor save, a line-ending conversion, a copy-paste from a stale clone (see [[The 426-line False Drift]]).

## CI integration (not done, would be nice)

Today the check is manual. Easy CI addition:

```yaml
# .github/workflows/mirror-drift.yml
name: Mirror Drift Check
on: [push, pull_request]
jobs:
  drift:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: bash tests/mirror-drift.sh
```

This would catch drift on every PR before merge. Not added yet because the kernel files change rarely; the cost of running it manually is low. If drift becomes a frequent issue, automate it.

## The three sacred files (the only three this check covers)

Per the [[Mirror Spec]]:

- `rapp_brainstem/brainstem.py` — the kernel
- `rapp_brainstem/VERSION` — the kernel's version string
- `rapp_brainstem/agents/basic_agent.py` — the agent ABI

Everything else is the mirror's prerogative (per Mirror Spec). The kernel mirror can carry whatever else it wants (the audience site, the vault, the narrative docs, the deploy artifacts), and that's not "drift."

## See also

- [[Mirror Spec]] — the contract this verifies
- [[The 426-line False Drift]] — what happens when you don't run this
- [[The Stale Local Clone Trap]] — why the script reads from GitHub, not a local clone
- [[Grail is GitHub, not local]] — the same lesson, stated as the rule
- [`tests/mirror-drift.sh`](../../../tests/mirror-drift.sh) — the script

<!-- RAPP1-HISTORICAL-SECTION-END -->
