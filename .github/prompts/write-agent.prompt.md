# Write a Safe RAPP Agent Adapter

Read [`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json),
[`RAPP1_STATUS.md`](../../RAPP1_STATUS.md), and
[`KERNEL_PIN.json`](../../KERNEL_PIN.json) first. The immutable grail is
`kody-w/rapp-installer@brainstem-v0.6.9`; its pinned bytes and the prepared
`cave/rapplications/rapp-installer/**` snapshot are read-only.
Canonicalization, identity, frames, wire, eggs, registry, trust, and protocol
evolution all follow RAPP/1 rev-5 through those authority and status records.

Ask what the agent should do and where the caller-owned adapter belongs. If no
safe target-owned path is identified, return an implementation plan instead of
writing into `rapp_brainstem/`, the prepared Cave installer, an archive, a
generated mirror, or an owner identity/trust record.

This safe adapter contract preserves useful authoring guidance without
granting implicit execution or distribution authority.

## Agent contract

For a reviewed single-file adapter:

1. Filename: `<thing>_agent.py` in the explicitly approved target-owned agents
   directory, never in the immutable grail.
2. Import `BasicAgent` through the host's documented compatibility boundary.
   Do not modify the pinned `agents/basic_agent.py`.
3. Define one class extending `BasicAgent`.
4. Set `self.name` to the PascalCase tool name the LLM sees.
5. Define `self.metadata` as an OpenAI function-calling schema with `name`,
   `description`, and `parameters`.
6. Implement `perform(**kwargs) -> str` with a machine-readable success or
   refusal result.
7. Optionally emit `data_slush` for bounded host-local chaining.
8. Optionally implement `system_context() -> str`.
9. Optionally include a module-level `__manifest__` for catalog observation.

## Safe-adapter requirements

- Default to read-only analysis, checking, or planning.
- Treat local or network inputs as untrusted observations until verification
  and explicit acceptance are complete.
- Require explicit URLs, immutable commit/release pins, and SHA-256 values for
  network-fetched code or catalog data. Never accept a moving `main`, `master`,
  `latest`, or `HEAD` reference.
- Do not auto-install missing packages. Declare dependencies and fail closed.
- Do not create issues, write files, publish, install, stream, execute fetched
  code, spend money, or make irreversible remote changes without a separate
  human-approved adapter and explicit authorization.
- Preserve source metadata and rejected records as data exhaust; attach
  verification, acceptance, and distribution state separately.
- Never infer identity, trust, registry membership, or conformance from a URL,
  catalog listing, hash, or public repository.
- If the adapter participates in the synchronous RAPP boundary, preserve the
  exact RAPP/1 §8 request, success, and 422 refusal shapes through the
  target-owned loopback façade. Do not add wire fields.
- Accept dependencies through explicit injection. Fail closed when the
  reviewed adapter is absent.

## After authoring

Run the smallest existing targeted test for the adapter, then:

```bash
python3 tests/run_rapp1_conformance.py
```

For Cave catalog adapters also run:

```bash
python3 cave/tools/build_super_rar.py --check
python3 cave/tests/test_catalog_containment.py
```

Do not change central fixtures or runners merely to make a failure pass. If a
failure requires an owner signature, authenticated registry, re-anchor, invite,
immutable-grail edit, or generated-mirror edit, report it as a follow-up.
