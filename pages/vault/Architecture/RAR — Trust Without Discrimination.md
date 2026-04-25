---
title: RAR — Trust Without Discrimination
status: published
section: Architecture
hook: The RAR registry adds supply-chain protection at the install gate without ever refusing an agent the user wants to load. Trust is metadata; the user is authority. Provenance information without permission gates.
---

# RAR — Trust Without Discrimination

> **Hook.** The RAR registry adds supply-chain protection at the install gate without ever refusing an agent the user wants to load. Trust is metadata; the user is authority. Provenance information without permission gates.

This is the design captured at the end of the Article XXV session, before context loss. Future contributors picking up the RAR build should read this first.

## What RAR is

A separate registry — its own GitHub repo, its own governance, its own attack surface — that holds publisher identities and the cryptographic signatures by which agents are bound to those identities. Because it lives in a different repo than `rapp_store`, a compromise of one doesn't compromise both.

Convention: `https://raw.githubusercontent.com/kody-w/RAR/main/publishers/<publisher>/keys.json`. Overridable via `RAR_REGISTRY_URL` env var so distros can run their own RAR (same pattern as `RAPPSTORE_URL`).

## Where signatures live

Inside the per-version manifest, additive to the existing `rapp-version/1.0` schema (bumping to `1.1` for sig support):

```json
// rapp_store/binder/versions/1.0.0/manifest.json
{
  "schema": "rapp-version/1.1",
  "id": "binder",
  "version": "1.0.0",
  "agent":   { "filename": "binder_agent.py",   "sha256": "...", "rar_sig": "<base64>" },
  "service": { "filename": "binder_service.py", "sha256": "...", "rar_sig": "<base64>" },
  "rar_publisher": "rar:@rapp",
  "rar_manifest_sig": "<base64>"
}
```

Per-file `rar_sig` covers tampering of an individual file. The manifest-level `rar_manifest_sig` is defense in depth — if an attacker replaces both the file AND the per-file sig, the manifest signature still won't match unless they have the publisher's offline key.

## Where verification happens

**In binder, on install.** Not in the brainstem kernel. The brainstem trusts what's already in `agents/` and `services/` — that's the existing trust boundary (Article XVII says `agents/` is the user's workspace, and the user's workspace doesn't ask permission). Binder is the gate because it's the one place code crosses from "remote" to "local."

```
binder install <id>:
  1. Fetch catalog → get entry
  2. Download files → verify SHAs against per-version manifest (existing)
  3. Fetch publisher pubkey from RAR registry        [NEW]
  4. Verify each file's rar_sig against pubkey      [NEW]
  5. Verify rar_manifest_sig against pubkey         [NEW]
  6. Record provenance in binder.json               [NEW]
  7. Install
```

Note step 7: install **always happens**. Verification populates a `verified: true | false | unsigned` field in `binder.json` for record-keeping and optional UI badging — it never refuses the install.

## The non-negotiable: no discrimination

This is the part most likely to get "fixed" by a well-meaning contributor in the future. Don't.

**An agent.py that meets the v0 contract loads. Forever. No exceptions.** That contract is small:

- Filename matches `*_agent.py`
- Contains a class extending `BasicAgent`
- Defines a `metadata` dict
- Defines a `perform(**kwargs) -> str` method

If those four conditions are met, the agent loads. RAR is *additional information about provenance*, not a precondition for execution.

Specifically:

- **No prompts. None.** Not "Install anyway?", not "This package is unverified, continue?", not anything. The user clicked install — that IS the consent. Asking again is friction theater. Signed and unsigned packages install identically and silently.
- **No "official"/"unofficial" badges that imply hierarchy.** A "verified" checkmark next to signed packages is fine; the absence of one is just absence, not a status flag.
- **No "hard mode" toggle that refuses unsigned agents.** There is no hard mode. There is no soft mode. There is just loading.
- **The brainstem's agent loader never gates on signature.** It only checks the v0 contract. RAR is binder's concern; the kernel doesn't know RAR exists.
- **Dev agents, WIP agents, hand-rolled agents, agents from a backup tape, agents written in a workshop ten years from now** — all welcome, all equal, all just code that meets the contract.

## Why no discrimination

Same doctrine as Article XXV ("chat is the only wire") applied to agents instead of the wire. The principle:

> **The user is the final authority on what runs on their machine. RAR provides verification metadata; it never blocks.**

A v0 brainstem from years ago still chats with current → a v0 agent from years ago still loads on current. The wire is forever; the agent contract is forever. RAR is information that helps consumers reason about provenance — it is not a permission gate.

If a contributor proposes adding load-time signature enforcement "for security," the answer is no. Real security at the install gate (binder verifying signatures and recording provenance) is good and worth building. Refusing the user's own files is security theater that breaks the time-travel guarantee for agents and breaks Article XVII.

## Threat coverage

| Threat | Without RAR | With RAR |
|--------|-------------|----------|
| Single file tampered, catalog SHA still good | Catalog SHA catches | Catalog SHA + RAR sig both catch |
| Catalog AND file both tampered by repo writer | **Not caught** — repo writer sets new SHA | RAR sig from publisher's offline key required; repo writer can't forge |
| Malicious package published as new publisher | User installs blindly | Provenance is recorded — auditable, traceable |
| Locally-dropped agent in `agents/` | Loads | Loads (Article XVII — user's workspace) |
| Edge brainstem from before RAR existed | Loads agents fine | Loads agents fine (additive schema) |

## Time-travel safety

RAR is purely additive (Article XXV — additive-only schema evolution, no removals or renames). Old brainstems without RAR support ignore the new manifest fields and install as before. New brainstems verify when present and record provenance. Signed and unsigned packages coexist in the same catalog. Same wire, same contract, same loading discipline — RAR adds metadata to the install audit trail without changing anything that already works.

## What to build first (when the next session picks this up)

The minimum order, each step incremental and reversible:

1. **Spec the manifest fields and `RAR_REGISTRY_URL`** — Constitution amendment + SPEC update. The schema bump from `rapp-version/1.0` to `rapp-version/1.1` is additive.
2. **Stand up the RAR registry repo** — start with one publisher (`@rapp`) and one keypair; sign existing rapp_store manifests offline; commit signatures into the per-version manifests.
3. **Teach binder to fetch keys + verify** — populate `verified` field in `binder.json`. Install always happens; verification result is metadata.
4. **One acid test** (`tests/e2e/13-rar-supply-chain.sh`) — install a tampered file, confirm binder still installs but flags `verified: false`. Install an unsigned package, confirm binder installs and flags `verified: unsigned`.
5. **(Optional, much later)** UI surface — verified checkmark badge, never a gate.

## What this is NOT

- **Not a license check.** RAR doesn't validate that you're allowed to use a package; it validates who shipped it.
- **Not DRM.** It doesn't prevent copying, modifying, or redistributing.
- **Not a permission system.** The user's workspace is sovereign.
- **Not a rating or review system.** Signatures are about provenance, not quality.

## Status

Design captured. Implementation deferred. The principles in this note are inviolable; the implementation order is recommended but flexible. When in doubt: **we don't discriminate.**
