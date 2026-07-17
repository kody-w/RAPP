# End-to-end scenarios

`07-ui-smoke.sh` and `08-html-pages.sh` are part of the canonical offline
RAPP/1 structural/pre-acceptance runner. They boot only the local target and
inspect target-owned HTML without credentials or deployment.

`11-binder-bootstrap.sh` is quarantined as legacy-positive migration evidence.
`enable-mi-on-twin.sh` changes Azure managed identity and remains an explicitly
credentialed/destructive exclusion.

Former Tier 1/Tier 2, install, cross-version, and legacy wire scenarios were
positive tests for retired contracts. Their exact bytes are quarantined under
`../fixtures/legacy-conformance/e2e/` and inventoried in
`../fixtures/rapp1-retired-test-inventory.json`.
