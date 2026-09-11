# Reference acceptance API

Requires Python 3.10+ and the versions in [`../requirements.txt`](../requirements.txt).
The implementation imports only this directory, Python's standard library,
`cryptography`, and `jsonschema`. It makes no network calls and starts no server.
[`../SPEC.md`](../SPEC.md) is normative; this page describes the local API.
The implemented class is **`interval-local-receiver`**, a normative candidate,
not estate activation or complete galactic DTN transport. Every federation
kind is registered in the **memory** family, with the exact
`<issuer-rappid>:<instance>` stream owner. Epochs, resumable chunks, delegation,
multi-room/batch work and legal/settlement negotiation are not implemented.

## Run the release gate

From `protocols/rapp-federation/1`:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 reference/schema_source.py --check
PYTHONDONTWRITEBYTECODE=1 python3 reference/conformance.py --report conformance-results.json
```

`conformance.py` accepts unittest selectors and `--verbose`. The report records
actual test counts, scanned signed fixture frames, refusal codes, environment
versions, and source SHA-256 commitments. Tests create uniquely named SQLite
files **inside this profile directory**, close them, and remove their own
files. They do not use operating-system temporary directories.

`vectors.py --write` intentionally regenerates the public fixture after an
approved SPEC change. It has no `--check` option: the conformance reproducibility
test is the fixture check. Finish all SPEC/source edits before regeneration;
do not edit or run a generator during verification. The full suite reports
whether its inputs stayed unchanged, and identical report bytes are not
rewritten. A second identical full run must leave persistent files unchanged.

Every key seed, AES key, identity, and datum in that
module is synthetic and publicly reproducible. **Never use those keys in an
estate, service, or production demo.**

## Application boundary

Import `rapp_federation` with this `reference` directory on the application's
module path. Supply a receiver-local database path, the local Hive RAPPID,
independently provisioned `CellAnchor` objects, and a trusted `Clock` interval
to `Federation`. Never derive these trust inputs from an arriving bundle.
Validity is half open: the clock's upper bound must be strictly before
expiry. Offline durations are configured by policy/agreement, not a global
one-year/network timeout. Authorizing receipts name their actual clock basis
and distinguish offline authorization from online-confirmed assurance.

| API | Meaning |
|---|---|
| `install_registry(hive, raw_bytes)` | Verify the actual owner signature, SPKIs, kind/profile bindings, and durable registry frontier. This alone is not proof of instantaneous global freshness. |
| `accept(canonical_frame_bytes)` | Strict, serialized frame/causality/authority acceptance. Most successful records are only evidence, not business execution. Raises `Refusal` with stable `code` on rejection. |
| `stage(canonical_frame_bytes)` | Retain signed but unaccepted candidates durably. It does not advance a head, policy, request, budget, or receipt. |
| `drain()` | Retry dependency-ready candidates; retain missing context and quarantine invalid independent candidates. Returns separate accepted, pending, and quarantined results. |
| `history()` | Fresh copies of accepted frames in unchanged RAPP/1 `(utc, frame_hash)` order. |
| `observe_clock(Clock(lower, upper))` | Update the host's trusted time interval and durable observed floor. `Clock(None, None)` declares unknown time. |
| `issue_challenge(terms)` | Issue a local, short-lived, single-request challenge bound to parties and exact terms for online owner confirmation. |
| `approve_dogg(content_hash, evidence_hash)` | Record an independent local publishing review. **Never call this automatically because the wire says `pii_status:"none"`.** |
| `verify_bundle_contents(bundle_hash, artifacts)` | Check the exact typed-address-to-bytes inventory. The result explicitly says execution is not authorized. |
| `status(original_request_hash)` | Inspect durable business phase, original wave, receipt frontier, quota reservation, and local key-release status. |
| `open_request(original_request_hash, sealed_egg_bytes, key_service)` | Require signed individual destination acceptance, an executing receipt, live authorization, and a file-backed ledger; reserve before scoped key release; verify/decrypt once; return bytes without executing or assimilating them. |
| `close()` | Close this connection; accepted state remains in the protected receiver-local database. |

The local `key_service` adapter receives a `ReleasePermit` binding the original
request, grant, parties/world, artifact, key service/key id, action, units, mode,
validity, both checkpoints, and both registry commitments. It must authenticate
the actual recipient and independently enforce current authority or the
explicit bounded-offline lease. The Python dataclass is **not a transferable
credential** and must never be accepted as authorization over the network.

The callback supplies **already authorized local artifact material**. This
Ed25519-only reference does not implement native ECDH-ES+A256KW key acquisition
or an Ed25519-to-distinct-encryption-key binding. Ed25519 SPKI bytes, raw public
keys, native release JSON, and service URL responses are not DEKs. A recipient
without compatible authenticated key-agreement material must defer native
remote key acquisition; see [SPEC §9.1](../SPEC.md#91-native-key-acquisition-is-not-redefined).
The online-confirmed tests confirm authority while using explicitly scoped,
locally provisioned fixture material, not an invented native ECDH exchange.

An exception after the release reservation leaves the request `in-doubt`;
there is no automatic retry or budget refund. External execution needs its own
durable idempotency integration. This reference deliberately does not invoke
tools, send money, publish data, or write to a local Hive's GODD.
An atomic execution-attempt marker and retained signed request/receipt history
are checked against the ledger and consumption totals on reopen. Partial
loss or contradictory state raises `recovery-quarantine`; the implementation
never recreates fresh allocations from a missing ledger.

Protect the SQLite file and its surrounding directory as private GODD
metadata. This reference detects rollback relative to its persisted frontier,
not a malicious restoration of the entire file. Deployments need
rollback-resistant storage and one receiving serialization domain per
recipient. An owner-equivocation latch survives ordinary restart and registry
refresh; clearing it is not exposed as a convenient API.

Cross-cell private control/registry/receipt metadata also requires a signed
parent sealed egg, not merely a private URL or encrypted business payload.
These local APIs consume already authorized decoded bytes; transport
disclosure/key custody belongs to an independently validated carrier adapter.
