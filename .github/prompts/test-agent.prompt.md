# Test a RAPP Agent or Adapter

Read [`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json),
[`RAPP1_STATUS.md`](../../RAPP1_STATUS.md), and
[`KERNEL_PIN.json`](../../KERNEL_PIN.json) first. RAPP is not yet fully RAPP/1
conformant. The immutable grail remains
`kody-w/rapp-installer@brainstem-v0.6.9`; never edit its pinned bytes or the
prepared `cave/rapplications/rapp-installer/**` snapshot.

Treat the code under test as a safe adapter: useful behavior stays intact, but
its default effects remain bounded and independently verifiable.

## Validation sequence

1. Identify the target-owned adapter and its smallest existing focused test.
2. Run that focused test without installing missing dependencies
   automatically.
3. For Cave catalog work, run:

   ```bash
   python3 cave/tools/build_super_rar.py --check
   python3 cave/tests/test_catalog_containment.py
   ```

4. Run the authoritative structural/pre-acceptance gate:

   ```bash
   python3 tests/run_rapp1_conformance.py
   ```

5. Diagnose failures against the pinned RAPP/1 rev-5 authority and current
   status, not the obsolete repository-local `SPEC.md`, moving catalog
   branches, or retired Tier 1/2/3 claims.

## What focused adapter tests should verify

- Agent file parsing, class discovery, metadata, and refusal behavior.
- Machine-readable return values and bounded `data_slush`, when used.
- Source provenance, explicit immutable refs, and SHA-256 validation.
- Moving `main`, `master`, `latest`, and `HEAD` references are never accepted.
- Verification, acceptance, and distribution are represented separately.
- Rejected, missing, and historical records remain available as data exhaust.
- Read-only/analyze/check/plan defaults perform no issue creation, file write,
  installation, streaming, publication, or fetched-code execution.
- Network access occurs only when an explicit pinned source and checksum are
  supplied.
- The exact RAPP/1 §8 request, success, and 422 refusal shapes are preserved
  when the adapter touches the synchronous loopback façade.
- The three hashes in `KERNEL_PIN.json` still match the local immutable grail
  bytes and the pin still names `brainstem-v0.6.9`.

## Failure policy

Fix target-owned code when it violates the contract. Never weaken a test,
rewrite a central fixture/runner, mutate the immutable grail, modify prepared
Cave installer bytes, or fabricate an owner signature, registry, re-anchor,
invite, identity, or trust decision.

If a legacy central assertion encodes the removed tombstone behavior rather
than the current adapt-don't-kill policy, report the exact stale assertion and
its required owner-reviewed follow-up; do not hide the conflict by erasing
restored data.
