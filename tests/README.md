# `tests/` — RAPP/1 pre-acceptance gates

The authoritative target-owned offline command is:

```bash
python3 -m pip install \
  -r requirements-rapp1-core.txt \
  -r rapp_brainstem/requirements.txt \
  pytest
python3 tests/run_rapp1_conformance.py
```

Use `python3 tests/run_rapp1_conformance.py --list` to see every gate and
the separately reported owner-action blockers. A green run proves local
structural/pre-acceptance behavior only; it does not establish authenticated
RAPP/1 acceptance.

## Canonical coverage

| Path | Coverage |
|---|---|
| `run_rapp1_conformance.py` | Runs every canonical offline gate and propagates any failure. |
| `check_offline_boundary.py` + `offline_guard/` | Builds a minimal allowlisted environment, isolates user/config state, permits loopback, and denies external Python/Node/HTTP egress. |
| `rapp1_core/` | Strict JSON/JCS, identity, frames, eggs, JWS/trust, and CLI behavior. |
| `../rapp_brainstem/test_rapp1_facade.py` | Exact pre-acceptance `/chat`, sessions, idempotency, durability, and refusals. |
| `test_rapp1_authority.py` | Structural authority pin, provenance fixture, status, and immutable boundary. |
| `test_rapp1_containment.py` | Retired active surfaces and target-owned 410 containment. |
| `test_rapp1_docs.py` + `../tools/check_rapp1_docs.py` | Current, historical, generated, and excluded documentation scope. |
| `test_active_path_migrations.py` and other top-level Python tests | Owner-independent migration and planning behavior. |
| `run-tests.mjs` | Dependency-free current JS/static contract checks. |
| `vault-check.mjs` | Vault links/aliases, metadata, and PII posture. |
| `check_rapp1_static.py` | Strict syntax, immutable workflow refs, ECOSYSTEM_MAP implementation paths, retired fixtures, and exhaustive active-suite inventory. |
| `e2e/07-ui-smoke.sh` + `e2e/08-html-pages.sh` | Local served-UI and target-owned HTML smoke checks. |
| `features/F10-ecosystem-audit.sh` | Offline ecosystem contract and drift fixtures. |
| `organism/run-all.sh` | Retained local kernel, encoding, storage, and concurrency fixtures. |
| `scenarios/16-metropolis-tracker.sh` + `scenarios/20-cross-tracker-federation.sh` | Offline tracker and federation fixtures. |
| `../installer/test_plant.sh` | Side-effect-free target-owned planter retirement. |

Every tracked test candidate is classified in
`rapp1-test-suite-inventory.json`. Ambient-network, authenticated `gh`,
cloud/provider, credentialed deployment, destructive install/removal,
Dreamcatcher, doorman, mirror, and Playwright/PeerJS suites are not part of the
authoritative offline gate; canonical static inspection still checks their
applicable syntax.

Brainstem boot checks run from a tracked-files-only copy under the runner work
directory, so checkout-local `.env`, Copilot sessions, and token files cannot
be discovered. The former executable browser parity suite is quarantined
because its `rapp.js` dependency no longer exists; `run-tests.mjs` is the
current core/static replacement.

Canonical subprocesses inherit only `PATH` plus necessary locale/platform
variables; credential, agent-socket, and config-file handles are not copied.
Python sockets and Node net/tls/dgram/DNS/fetch APIs reject non-loopback
destinations, while proxy settings cover external HTTP clients such as curl.

The supplemental `rapp-drift-lint` workflow is pinned to immutable commit
`de1c664154d3456224bdf95e830736ffb5270c2b`; it is hygiene only, not RAPP/1
authority or authenticated acceptance evidence.

## Retired tests

Exact bytes of tests that positively asserted pre-rev-5 identity, frame, egg,
browser, Tier 2, or wire behavior live under
`fixtures/legacy-conformance/` with a final `.txt` suffix. They are migration
evidence, never executable conformance tests. Their authoritative disposition
is `fixtures/rapp1-retired-test-inventory.json`.

Legacy request or artifact strings remain in executable tests only as explicit
negative, migration, documentation, or retirement detectors recorded in that
inventory.
