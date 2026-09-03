---
title: "Adapt, Don't Kill — preserve data exhaust"
status: living
date: 2026-09-03
---

# Adapt, Don't Kill — preserve data exhaust

Historical output is not clutter. It is the repository's memory: examples,
failed assumptions, working interfaces, product language, implementation
patterns, and evidence future agents can use to understand why the system
evolved.

## Decision

RAPP migrations adapt existing artifacts in place. They do not replace real
pages, code, catalogs, tools, or workflows with tombstones or clean-slate
summaries.

The order of operations is:

1. **Recover the fullest artifact first.** Identify the last substantive
   source commit and checksum before changing behavior.
2. **Preserve the data exhaust.** Keep original sections, examples, schemas,
   algorithms, UI, and provenance available at the known path.
3. **Change only the unsafe edge.** Replace automatic network, credential,
   mutation, deployment, or write behavior with explicit safe defaults,
   reviewed bindings, local previews, or read-only plans.
4. **Update instead of erase.** Correct stale claims inline and carry the old
   framing as dated context where it remains useful.
5. **Point installer context to the Grail.** When an artifact needs installer
   provenance, reference `KERNEL_PIN.json` and
   `kody-w/rapp-installer@brainstem-v0.6.9`; do not remove the installer
   story or substitute a moving source.
6. **Inventory the remaining RAPP/1 gap.** Every adapted artifact records what
   remains to migrate across identity, wire, frames, eggs, registry/trust,
   installer pinning, and owner-authorized acceptance.

## What containment means now

Containment is additive. A default-off capability flag, explicit owner-approved
apply mode, synthetic fixture credential, local snapshot, or reviewed runtime
binding may prevent unsafe execution. The surrounding implementation remains
real and inspectable.

A blank refusal page or a source file reduced to `410 Gone` fails this rule
because it destroys the learning corpus even if it appears operationally safe.

## Acceptance test

An adapted artifact passes only when:

- its substantive historical content or implementation is present;
- its source commit and checksum are recorded;
- safe local behavior remains usable where possible;
- obsolete side effects are disabled by default and cannot silently run;
- Grail references are pinned rather than deleted;
- current RAPP/1 gaps and owner blockers are explicit; and
- the original known URL or source path still teaches a future reader what was
  built.

## Related

- [[Historical URLs remain visible and inert]]
- [[Roots Are Public Surfaces]]
- [[The Species DNA Archive — rapp_kernel]]
- [`RAPP1_STATUS.md`](../../../RAPP1_STATUS.md)
- [`KERNEL_PIN.json`](../../../KERNEL_PIN.json)
