# `tests/` — RAPP/1 pre-acceptance gates

The authoritative target-owned offline command is:

```bash
python3.11 -m pip install \
  -r requirements-rapp1-core.txt \
  -r rapp_brainstem/requirements.txt \
  pytest
python3.11 tests/run_rapp1_conformance.py
```

Use `python3.11 tests/run_rapp1_conformance.py --list` to see every gate and
the separately reported owner-action blockers. A green run proves local
structural/pre-acceptance behavior only; it does not establish authenticated
RAPP/1 acceptance.

## Canonical coverage

| Path | Coverage |
|---|---|
| `run_rapp1_conformance.py` | Runs every canonical offline gate and propagates any failure. |
| `rapp1_core/` | Strict JSON/JCS, identity, frames, eggs, JWS/trust, and CLI behavior. |
| `../rapp_brainstem/test_rapp1_facade.py` | Exact pre-acceptance `/chat`, sessions, idempotency, durability, and refusals. |
| `test_rapp1_authority.py` | Structural authority pin, provenance fixture, status, and immutable boundary. |
| `test_rapp1_containment.py` | Retired active surfaces and target-owned 410 containment. |
| `test_rapp1_docs.py` + `../tools/check_rapp1_docs.py` | Current, historical, generated, and excluded documentation scope. |
| `test_active_path_migrations.py` and other top-level Python tests | Owner-independent migration and planning behavior. |
| `run-tests.mjs` | Dependency-free current JS/static contract checks. |
| `vault-check.mjs` | Vault links/aliases, metadata, and PII posture. |
| `check_rapp1_static.py` | Strict JSON, HTML parse, shell/JS syntax, and retired-test inventory. |
| `e2e/08-html-pages.sh` | Target-owned HTML smoke checks. |
| `../installer/test_plant.sh` | Side-effect-free target-owned planter retirement. |

The one ambient-network pytest,
`TestMemoryAgentIntegration.test_manage_then_recall_memory`, is deliberately
deselected because it downloads moving agent sources. Cloud/provider,
credentialed deployment, destructive planting, and Playwright suites are not
part of the authoritative offline gate.

## Retired tests

Exact bytes of tests that positively asserted pre-rev-5 identity, frame, egg,
browser, Tier 2, or wire behavior live under
`fixtures/legacy-conformance/` with a final `.txt` suffix. They are migration
evidence, never executable conformance tests. Their authoritative disposition
is `fixtures/rapp1-retired-test-inventory.json`.

Legacy request or artifact strings remain in executable tests only as explicit
negative, migration, documentation, or retirement detectors recorded in that
inventory.
