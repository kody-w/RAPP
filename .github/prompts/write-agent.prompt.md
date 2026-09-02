# Retired Legacy-Agent Authoring Prompt

Read [`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json) and
[`RAPP1_STATUS.md`](../../RAPP1_STATUS.md) first. This repository is not yet
fully RAPP/1 conformant. Canonicalization, identity, frames, wire, eggs,
registry, trust, and protocol evolution follow RAPP/1 rev-5 through those
records. Its only target-owned synchronous protocol surface is
the loopback pre-acceptance façade at `127.0.0.1:7073`; it imports no grail
module and defaults to the exact `inference-refused` response until a reviewed,
side-effect-free adapter is explicitly injected. Its request is required string
`user_input` plus optional strings `session_id` and `idempotency_key`; success
contains exactly `response`, `agent_logs` (array), and `session_id`; refusal is
HTTP 422 with exactly nested `error.code` and `error.step`.

Do **not** create or modify an agent under `rapp_brainstem/`, the prepared Cave
installer, or any other contained legacy runtime. Refuse requests that rely on:

- missing dependencies being installed automatically;
- the repository-local `SPEC.md` as protocol authority;
- Tier 1/2/3 portability or deployment;
- RAR publication, catalog insertion, planting, hatching, or installation; or
- edits to `KERNEL_PIN.json` bytes, archives, generated mirrors, or
  owner-authorized identity/trust records.

If the requester needs new behavior, explain that the old drop-in-agent path is
retired. A future implementation must live in an explicitly named target-owned
adapter outside the immutable grail, preserve the exact RAPP/1 §8 request,
success, and refusal shapes, perform no implicit package installation or remote
publication, and remain fail-closed without authenticated acceptance.

This prompt is a containment notice, not an authoring workflow.
