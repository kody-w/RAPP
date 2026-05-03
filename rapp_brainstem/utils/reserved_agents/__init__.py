"""utils/reserved_agents — first-party lifecycle agents shipped with the kernel.

These agents follow the standard BasicAgent contract (one file, one class,
one metadata dict, one perform()), but they live OUTSIDE the agents/*_agent.py
glob the kernel auto-discovers at boot. The kernel does not load them as
ordinary tools every chat turn — that would advertise dangerous operations
(kernel upgrade, system service install, peer registration) to the LLM as
default capabilities, and pay their token cost on every request.

Instead, reserved agents are invoked on demand by the lifecycle organ
(utils/organs/lifecycle_organ.py), which is the LLM's ONLY surface for
triggering kernel-level operations. The organ enforces a confirmation
handshake (see soul.md "Lifecycle handshake protocol") so destructive
operations always pass through an explicit user "yes" before they run.

Why this directory exists rather than putting them in agents/:
  - Token economy: ~150 tokens of metadata × every chat turn × N agents.
  - Safety isolation: dangerous tools shouldn't be in the default palette.
  - Code organization: lifecycle code is kernel-adjacent infrastructure,
    not user-domain agent work.

Why these agents still follow the BasicAgent contract:
  - Tier portability — if Tier 2 (rapp_swarm) ever wants to invoke
    upgrade/backup/etc. directly, the agent file drops in unmodified.
  - Constitutional consistency — one file = one class = one perform()
    is the platform's only plugin shape. Reserved agents don't break it,
    they just don't auto-load.

Constitutional note: this is a kernel-shipped staging area for
first-party lifecycle code. It is NOT a permission boundary on user
agents. User agents always live in agents/ and always load. RAR
(memory: project_rar_no_discrimination.md) is metadata, never authority;
reserved_agents/ is also not a gate — it's where the platform's own
lifecycle tools wait to be called.
"""
