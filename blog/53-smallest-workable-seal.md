# The smallest workable seal

Sealing a swarm — making it immutable, preserved, queryable, but never writable again — sounds like it should require something heavy. A blockchain. A WORM filesystem. A multi-step ceremony with cryptographic attestation. We considered all of those.

What we shipped is two things:

1. A field in the swarm's `manifest.json`: `"sealing": {"status": "sealed", "sealed_at": "...", "sealed_by": "...", "trigger": "..."}`.
2. `chmod 0444` on every memory file in the swarm.

That's it. That's the whole sealing engine.

When an agent tries to write a memory in a sealed swarm, the standard memory shim does its `open(path, 'w')` and the OS raises `PermissionError`. The swarm server catches that and returns a clean error envelope tagged `{sealed: true}`. Reads work because `chmod 0444` still allows reading. The swarm is preserved at the OS layer; the application doesn't have to enforce anything.

When the deploy endpoint receives a bundle targeting a sealed swarm_guid, it checks `manifest.sealing.status` and returns `423 Locked` before doing anything destructive. When DELETE receives a sealed swarm_guid, same thing. Application-layer enforcement at the only two endpoints that would mutate the sealed state.

That's the entire sealing contract. About 80 lines of code in the swarm server.

**What we considered and rejected:**

- **Filesystem snapshots (ZFS / Btrfs).** Real filesystem-level immutability. Required us to ship with one specific filesystem; ruled out for portability.
- **WORM cloud storage.** Object stores with retention locks. Real, durable, but requires a specific cloud provider and ties pricing to their lock-policy SLAs. Overkill for the on-laptop use case.
- **Hash chains.** Each write produces a hash; sealed-state captures the chain root. Resists tampering by an attacker who has filesystem access. Genuine improvement, but the threat model doesn't justify it for v0.
- **Cryptographic attestation.** Sign the seal event with a hardware key. Strongest. Also the most ceremony for the user. Reserved for the high-tier product (rapptwin's premium sealing service may add this).

The principle: **the smallest workable enforcement that delivers the user-visible promise.** The user-visible promise is "after sealing, your twin is preserved and writes are rejected." `chmod 0444` plus a manifest flag delivers that promise. Anything more is defense against threats we don't yet have, paid for in complexity we don't yet need.

If a hostile actor has filesystem access to your sealed swarm directory, they can `chmod +w` the file and edit it. Yes. We're not defending against that — the threat model is "the principal wanted preservation and the system honors it." We're not defending against operators of the storage layer mucking with state at rest; that's a deployment-environment problem, addressed by trust in your storage provider.

**The lesson:** when you build immutability into a system, ask which threats the immutability is for. Honest preservation against accidental rewrites is one threat. Cryptographic non-repudiation is another. Tamper-evident audit logs against a hostile sysadmin is a third. They take dramatically different amounts of code. Pick the threat your product actually has, build for that, and stop.

We have 80 lines of sealing code that handle the threats our users actually face. The fancier versions exist; we'll ship them when someone needs them.
