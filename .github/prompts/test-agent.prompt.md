# Test Agent Contract

Run the RAPP v1 contract test suite and diagnose any failures.

## Steps

1. Run the Node test suite:
   ```bash
   node tests/run-tests.mjs
   ```

2. Run the Python agent tests:
   ```bash
   cd rapp_brainstem && python3 -m pytest test_local_agents.py -v
   ```

3. If any tests fail, read the failing test source to understand what v1 contract property is being verified, then fix the agent or code that violates it.

## What the tests verify

- Agent file parsing and class discovery
- `__manifest__` extraction and schema validation
- Seed/mnemonic round-trips
- Card ↔ `*_agent.py` byte equality (SHA-256)
- Tamper detection
- Binder JSON round-trip
- Multi-agent chain via `data_slush`
- Digital twin file presence

## Key constraint

Never modify test expectations to make tests pass. The tests encode the frozen v1 contract from [SPEC.md](../../SPEC.md). If a test fails, the code under test is wrong, not the test.
