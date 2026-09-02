# Validate RAPP/1 Containment

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

## Validation

From the repository root, run:

```bash
python3 tools/check_rapp1_docs.py
python3 tests/run_rapp1_conformance.py
```

Diagnose failures against the pinned rev-5 authority and current status, not
against the obsolete repository-local `SPEC.md`, Tier 1/2/3 behavior, RAR
catalog conventions, or legacy egg/runtime tests.

Do not:

- launch `rapp_brainstem`, Cave, browser, installer, or cloud runtimes;
- install missing Python packages or other dependencies automatically;
- change tests or fixtures merely to make a failure pass;
- write into the immutable grail, prepared Cave installer, archives, generated
  mirrors, or owner-authorized identity/trust records; or
- treat structural test success as authenticated RAPP/1 acceptance.

If a failure requires a prohibited central fixture, owner signature, registry,
re-anchor, or invite change, report it as a follow-up instead of fabricating a
local fix.
