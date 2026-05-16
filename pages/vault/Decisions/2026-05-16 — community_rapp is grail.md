---
title: 2026-05-16 — community_rapp is grail
status: published
section: Decisions
hook: community_rapp/ is grail-canonical — a community-side install surface that lives in the kernel mirror. Distinct from examples/rapp-commons/ (which is a reference neighborhood and went to the distro).
---

# 2026-05-16 — community_rapp is grail

> **Hook.** `community_rapp/` is grail-canonical — a community-side install surface that lives in the kernel mirror. Distinct from `examples/rapp-commons/` (which is a reference neighborhood and went to the distro).

## The clarification

During the Marie Kondo audit, both `community_rapp/` and `examples/rapp-commons/` looked plausibly like "the community / commons / hangout surface." Two directories, similar-sounding purposes, easy to conflate.

Grail's main branch on GitHub clarified the question:

```
gh api /repos/kody-w/rapp-installer/contents
# ...
# d  community_rapp
# ...
```

`community_rapp/` is grail-canonical. It ships in the actual frozen-kernel repo. Specifically, it contains:

- `community_rapp/agent-repo-skill.md` — skill spec for agent-repo authors
- `community_rapp/install.ps1`, `install.sh` — community-side install entry points
- `community_rapp/skill.md` — agent contract for participating in the community surface

This is *kernel-side* community infrastructure — the surface a new community member uses to install the brainstem and start contributing agents. It's part of the install one-liner's downstream surface.

`examples/rapp-commons/` is something completely different — a *reference implementation of a neighborhood*, with `rappid.json`, `neighborhood.json`, `card.json`, `holo.md`, `members.json`, `events/SCHEMA.md`, etc. It's an organism-layer feature (the Commons neighborhood pattern). It moved to the Rappter distro.

## The two-word disambiguation

| Term | Grail-canonical? | What it is | Where it lives |
|---|---|---|---|
| `community_rapp/` | yes | Kernel-side install surface for community contributors | `kody-w/RAPP/community_rapp/` |
| `examples/rapp-commons/` | no | Reference implementation of a neighborhood | `kody-w/rappter-distro/examples/rapp-commons/` |
| `kody-w/rapp-commons` (separate repo) | no | The planted Commons neighborhood itself | own GitHub repo |

The names are confusingly similar; the roles are distinct. When in doubt: *is it about the kernel's install surface for community members?* That's `community_rapp/`. *Is it about a neighborhood implementation?* That's `examples/rapp-commons/` (in the distro) or `kody-w/rapp-commons` (planted).

## How this changes future audits

When auditing a "community"-flavored directory, the test is:

1. **Does grail ship a directory by this exact name?** Check `gh api /repos/kody-w/rapp-installer/contents`. If yes → grail-canonical → kernel.
2. **Does the directory contain agent-contract or install-flow content?** → likely kernel-side community infrastructure.
3. **Does the directory contain neighborhood implementation files** (rappid.json, neighborhood.json, members.json, card.json, holo.md)? → reference neighborhood → distro.

The Marie Kondo audit could have stripped `community_rapp/` if I had skipped step 1. Always check grail first.

## See also

- [[Grail is GitHub, not local]] — the meta-lesson about authoritative reads
- [[2026-05-16 — Marie Kondo Audit]] — the policy
- [[2026-05-16 — Kernel-Distro Split]] — the larger split
- [[2026-05-11 — The Commons]] — the planted Commons neighborhood (which uses the reference implementation)
