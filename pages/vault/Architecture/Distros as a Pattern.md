---
title: Distros as a Pattern
status: published
section: Architecture
hook: The Linux-distros analogy made explicit. Rappter is one distro; other distros (minimal, research, enterprise, embedded) can exist. The contract: never modify the three sacred kernel files; everything else is the distro's prerogative.
---

# Distros as a Pattern

> **Hook.** The Linux-distros analogy made explicit. Rappter is one distro; other distros (minimal, research, enterprise, embedded) can exist. The contract: never modify the three sacred kernel files; everything else is the distro's prerogative.

## The analogy

```
Linux kernel    →  RAPP kernel (brainstem.py + basic_agent.py + VERSION, in kody-w/rapp-installer)
Linux distro    →  RAPP distro (a sibling repo that composes onto the kernel)
Ubuntu          →  kody-w/rappter-distro (today's reference distro)
Alpine / NixOS  →  future minimal / research distros (not yet built)
RHEL            →  future enterprise distro (not yet built)
```

The kernel doesn't care which distro is on top. Distros don't fork the kernel — they layer onto it via the kernel's own extension points (`sys.modules` shims for `utils.*`, agent discovery from `agents/*_agent.py`, and the `boot.py` `Flask.run` monkey-patch). The kernel files stay byte-identical to grail; the distro composes around them.

## What a valid distro is

A distro is a sibling repo to `kody-w/RAPP` that:

1. **Never modifies the three sacred kernel files.** `brainstem.py`, `VERSION`, `agents/basic_agent.py` are immutable. Distros may add agents, organs, senses, and library modules — but they may not edit the kernel.
2. **Composes onto the kernel via the kernel's existing extension points.** Three primary mechanisms:
   - `agents/*_agent.py` files auto-discovered by the kernel's agent loader
   - `sys.modules` shim for the `utils` namespace (anything dropped into `~/.brainstem/utils/` imports transparently)
   - `boot.py`-style wrapper that monkey-patches `Flask.run` to add organs / senses / static mounts before the kernel starts serving
3. **Has its own `install.sh`** that hatches the distro onto an existing brainstem install (assumes the user has already run grail's install one-liner).
4. **Has its own README** explaining what it adds, what it does NOT add (kernel-canonical things stay with the kernel), and a backlink to the kernel hub for the SPEC.
5. **Can be hatched and unhatched.** A user should be able to install the kernel alone, then hatch a distro, then optionally hatch a different distro without re-installing the kernel.

## What a distro is not

- **Not a fork.** Forks edit the kernel. Distros never do.
- **Not a SPEC source.** The kernel repo is the god SPEC. Distros may have their own implementation docs but they don't compete with the kernel SPEC.
- **Not mandatory.** The kernel works on its own. If a user just wants T1 / T2 / T3 with the grail-bundled agents and no organism layer, they don't need any distro.

## How extension actually works (boot.py pattern)

The mechanism that makes distros possible without kernel modification:

```python
# distro's boot.py
def main():
    _wrap_flask_run()   # patch Flask before kernel starts
    runpy.run_path("brainstem.py", run_name="__main__")  # run grail's kernel verbatim

def _wrap_flask_run():
    _real_run = flask.Flask.run
    def _wrapped_run(self, *args, **kwargs):
        install_organs(self)
        install_senses(self)
        _mount_web_static(self)
        return _real_run(self, *args, **kwargs)
    flask.Flask.run = _wrapped_run
```

The kernel never knows boot.py exists. start.sh invokes `python utils/boot.py` instead of `python brainstem.py`; that's the one line a distro changes in the user's install dir. Run `python brainstem.py` directly and you get the bare kernel.

## Why this matters for the ecosystem

Multiple distros mean:

- **Innovation without forking.** A research distro can experiment with new organ types, new sense models, novel UIs — without touching the kernel and breaking compatibility with the broader ecosystem.
- **Audience-specific distributions.** A minimal embedded distro for IoT devices; an enterprise distro with audit logging; a research distro with experimental telemetry. All compose on the same kernel.
- **Federation across distros.** Two organisms on different distros can still talk to each other because the network protocol (specs/SPEC.md) and the agent contract (pages/docs/SPEC.md) are kernel-level, not distro-level.

## Open questions (still being figured out)

- **Distro discovery.** Today the only distro is `kody-w/rappter-distro`. When a second distro appears, how do users discover it? Probably a catalog file at a well-known URL, but unspecified.
- **Distro signing.** Eventually distros should be cryptographically attested so a user installing a third-party distro can verify provenance. Sketch lives in `pages/vault/Architecture/Signed Releases and Variant Attestation.md`.
- **Multi-distro composition.** Today you hatch one distro. Eventually you might hatch two (e.g., enterprise audit + research telemetry). Whether their organs/senses compose cleanly is an open spec question.

## See also

- [[The Kernel-as-God-SPEC]] — the framing that makes distros possible
- [[Boot Sidecar — Integrating Utils Without Modifying the Kernel]] — the load-bearing mechanism
- [[Mirror Spec]] — the byte-identical-to-grail discipline distros must respect
- [[2026-05-16 — Kernel-Distro Split]] — the decision that made the distro pattern explicit
- [[One Kernel, Many Distros]] — manifesto version of this idea
- [[Signed Releases and Variant Attestation]] — open question about distro signing
