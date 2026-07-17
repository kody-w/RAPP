# Retired simulation harness

The target-owned simulation entrypoints are non-executable historical
fixtures. They return `410 Gone` with exit status 78 and cannot invoke an LLM,
mutate a simulation, create commits, or publish repository state.

Current RAPP/1 status and remaining owner actions are recorded in
[`../../RAPP1_STATUS.md`](../../RAPP1_STATUS.md).
