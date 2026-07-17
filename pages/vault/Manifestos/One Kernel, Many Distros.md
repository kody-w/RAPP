---
title: One Kernel, Many Distros
status: historical
section: Manifestos
hook: The federation principle made explicit. One kernel — universal, immutable, frozen at grail. Many distros — opt-in personalities, each layering different organisms on the same substrate. Everything composes; nothing forks.
---

# One Kernel, Many Distros

> **HISTORICAL MANIFESTO — superseded current guidance.** The bounded body is
> dated kernel/distro doctrine, not authority or distribution instruction. For
> canonicalization, identity, frames, wire, eggs, registry, trust, and protocol
> evolution, follow RAPP/1 rev-5 through
> [`RAPP1_AUTHORITY.json`](../../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../../RAPP1_STATUS.md).

<!-- RAPP1-HISTORICAL-SECTION-START -->

> **Hook.** The federation principle made explicit. **One kernel** — universal, immutable, frozen at grail. **Many distros** — opt-in personalities, each layering different organisms on the same substrate. Everything composes; nothing forks.

## The vision

A future contributor with a curiosity about AI agents discovers RAPP. They install the bare kernel — it's tiny, runs locally, asks for one credential. They write an agent, hand the file to a friend, the friend runs the same agent. They figure out the platform in an afternoon.

Then they look around. They see distros:

- **Rappter** — the full organism distro. Twins, neighborhoods, bonds, eggs, the Pokédex. *"What it would look like if a single creator filled the platform with their vision."*
- **Minimal** — bare kernel plus a tiny set of utility agents. *"What it looks like for a researcher who only wants the LLM-routing pipe."*
- **Enterprise** — kernel plus audit logging, RBAC, SSO. *"What it looks like for a team buying into the platform as infrastructure."*
- **Research** — kernel plus experimental sense models, novel organ types, observability. *"What it looks like for a lab studying emergent behavior."*
- **Embedded** — kernel plus a stripped-down runtime, no Pages site, mobile-first UI. *"What it looks like in a sensor or a wearable."*

They pick the distro that fits their use case. They install it. They never had to fork the kernel; they never had to choose between platforms.

Their organism, planted under Rappter, can still talk to an organism running on Minimal — because the network protocol is kernel-level. Their agent file works on Enterprise — because the agent contract is kernel-level. Their `.egg` cartridge hatches on Research — because the cartridge format is kernel-level.

**One kernel. Many distros. One ecosystem.**

## Why this is the right shape

A monolithic platform inevitably accumulates one opinion's worth of features. Eventually those features outgrow the kernel's scope, but they can't be removed without breaking users who depend on them. The platform calcifies.

A platform with no kernel — just "frameworks" or "patterns" — can't federate. Two implementations diverge in incompatible ways. Cross-implementation interop becomes impossible. The ecosystem fragments.

The Linux model — small frozen kernel, multiple distros — is the resolution. It's not novel; it's borrowed wholesale because it works. Linux has been the foundation of the open-source ecosystem for 30+ years partly because the kernel-distro split lets innovation happen *around* the kernel without destabilizing it.

RAPP makes the same bet: the kernel stays small and frozen; distros are where the ecosystem evolves.

## What this is not

- **Not a marketing tagline.** "One kernel, many distros" is operationalized in `tests/mirror-drift.sh`, the `boot.py` Flask-wrap pattern, the `sys.modules` shim, and the Constitution's amendment process. If those mechanisms break, this vision breaks with them.
- **Not "pick your favorite framework."** The kernel SPEC is non-negotiable. Distros that violate it (modify sacred files, fork the agent contract, ship an incompatible egg format) are not RAPP distros; they're forks. Forks are allowed but they lose interop.
- **Not centrally planned.** Today only one distro exists. The second, third, fourth distros aren't going to be designed by Kody — they'll be built by whoever needs them. The kernel just has to be small enough and stable enough that building a distro is worth the effort.

## What this asks of the kernel

The kernel can only support many distros if it stays *small enough and stable enough* that multiple distros can productively layer on top.

That means:

- **Three sacred files.** The fewer the immutable surface, the easier distros are to build. Today: `brainstem.py`, `VERSION`, `basic_agent.py`. Adding a fourth sacred file should be a deliberate constitutional act, not casual.
- **Extension points, not extension *frameworks*.** The kernel offers `sys.modules` shims and `Flask.run` monkey-patches, not a plugin system. Plugin systems calcify; bare extension points don't.
- **Documentation as the contract.** Distros depend on the SPEC docs being authoritative. If the SPEC says "the universal control plane MUST follow the canonical shape," distros can build to that interface. If the SPEC says "rapp-zoo is the universal control plane," distros are stuck implementing rapp-zoo.

## What this asks of distros

A distro that wants to be part of the ecosystem (not a fork) must:

- Never modify the sacred kernel files
- Compose via the kernel's existing extension points
- Be hatchable + unhatchable without re-installing the kernel
- Document what it adds + what it leaves to the kernel
- Backlink to the kernel hub for SPEC documentation

In exchange, the distro gets:
- Cross-distro interop (organisms on different distros can talk via the kernel-level network protocol)
- Cross-distro agent portability (an agent file written for one distro runs on any other)
- A stable substrate that doesn't change under it

## What this enables

- **Probe-class deployment.** A device shipped today with the bare kernel can hatch an organism years later from any distro that exists then.
- **Innovation without forking.** A research distro can experiment with new organ types without breaking compatibility with the rest of the ecosystem.
- **Audience-specific personalities.** Embedded, enterprise, research, hobbyist — all running the same kernel, none forced to accept the others' opinions about UI or workflow.
- **Federation as the network model.** Organisms find each other across distros via kernel-level addressing (the rappid). The federation is the platform; the platform is federated by construction.

## See also

- [[Distros as a Pattern]] — the engineering shape this manifesto formalizes
- [[The Kernel-as-God-SPEC]] — what the kernel does for distros
- [[Mirror Spec]] — the byte-identical-to-grail discipline that anchors the kernel
- [[2026-05-16 — Kernel-Distro Split]] — the decision that adopted this model
- [[Engine, Not Experience]] — the founding stance compatible with this manifesto

<!-- RAPP1-HISTORICAL-SECTION-END -->
