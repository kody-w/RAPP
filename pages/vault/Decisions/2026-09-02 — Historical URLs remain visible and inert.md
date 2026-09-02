---
title: "Historical URLs remain visible and inert"
status: living
date: 2026-09-02
---

# Historical URLs remain visible and inert

Externally shared URLs are compatibility contracts even after the behavior
behind them retires. Replacing a page with a blank warning preserves the path
but destroys the artifact people were sent there to understand.

## Decision

Retained public history follows four rules:

1. **Keep the known URL working.** Restore the last useful page or deck rather
   than serving an unexplained blank surface or moving it without an alias.
2. **Make status unmistakable.** Historical pages use `noindex`, a visible
   retirement banner, and links to `RAPP1_AUTHORITY.json` and
   `RAPP1_STATUS.md`.
3. **Preserve content, not side effects.** Old prose and visuals remain
   readable. Network probes, token handling, redirects, installers, joins,
   deployment actions, and other retired behavior become inert.
4. **Describe static hosting honestly.** GitHub Pages returns HTTP 200 for a
   retained HTML tombstone. These are *semantic tombstones*, not claimed HTTP
   410 responses.

The bounded `RAPP1-HISTORICAL-SECTION-START/END` markers continue to separate
dated material from current guidance. Visibility does not make that material
authority; hiding it does not make the repository safer when scripts can still
execute or shared links become useless.

## Publication boundary

The Pages build publishes the intentional documentation surface and excludes
runtime source UIs, test fixtures, prepared immutable installer payloads, and
other executable evidence. Repository history remains available through Git,
while the public site exposes only current authority, inert historical
artifacts, and explicit retired aliases.

## Why this matters

RAPP's pitch playbook was explicitly grandfathered because its root URL was
already circulating. The same compatibility principle applies across the
flagship: preserve provenance and human context without reviving superseded
capabilities.

## Related

- [[Roots Are Public Surfaces]]
- [[2026-05-16 — Why pitch-playbook stays in the kernel]]
- [[Adding to the Kernel vs the Distro]]
- [`RAPP1_STATUS.md`](../../../RAPP1_STATUS.md)
