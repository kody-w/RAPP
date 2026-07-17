# End-to-end scenarios

Only `08-html-pages.sh` is part of the canonical offline RAPP/1
structural/pre-acceptance runner. It parses and inspects target-owned static
HTML without credentials or deployment.

`07-ui-smoke.sh`, `11-binder-bootstrap.sh`, and `enable-mi-on-twin.sh` are
application/deployment scenarios and are not RAPP/1 conformance evidence.
They require their own documented environment and are intentionally excluded
from the offline gate.

Former Tier 1/Tier 2, install, cross-version, and legacy wire scenarios were
positive tests for retired contracts. Their exact bytes are quarantined under
`../fixtures/legacy-conformance/e2e/` and inventoried in
`../fixtures/rapp1-retired-test-inventory.json`.
