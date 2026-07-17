# RAPP/1 `/chat` façade — pre-acceptance

This target-owned façade is the repository's only candidate RAPP/1 synchronous
wire endpoint. It is **not publicly conformant or authenticated**. Acceptance
remains blocked until the estate owner publishes the authenticated RAPP/1 §13
registry and registers the error codes below. The structural authority pin in
`RAPP1_AUTHORITY.json` is not that registry.

The façade is separate from the immutable grail application. It does not mount
or serve any route from `brainstem.py`; the private production boundary calls
only the pinned `call_copilot(messages, tools=None)` function. Agents and tools
are never loaded or run. A tool-bearing, ambiguous, empty, or failed inference
is refused rather than normalized.

## Launch

```bash
python3.11 rapp_brainstem/run_rapp1_facade.py
```

Defaults:

- bind: `127.0.0.1:7073` (separate from grail port `7071`);
- SQLite: `~/.brainstem/rapp1-facade.sqlite3`.

Configuration is limited to `RAPP1_FACADE_HOST`, `RAPP1_FACADE_PORT`, and
`RAPP1_FACADE_DB`. The launcher serves only `POST /chat` and control-plane
`GET /health`. Health explicitly reports `authenticated:false` and
`fully_conformant:false`.

## Wire and durability

`POST /chat` accepts a JSON object with required string `user_input`, optional
string `session_id`, and optional string `idempotency_key`. Every other member,
including client-supplied history, is ignored. Success has exactly:

```json
{"response":"...","agent_logs":[],"session_id":"..."}
```

The server persists and supplies the transcript. SQLite `BEGIN IMMEDIATE`
transactions validate an existing session, reserve its active turn, and reserve
idempotency before inference. Creation keys are global; existing-session keys
are scoped by `(session_id, key)`. Completion stores the turn and exact response
bytes atomically. A completed duplicate of the same canonical request replays
those bytes. Reusing a key for different recognized request content fails
closed as an idempotency conflict; ignored members do not affect comparison.

Only one inference may be pending for a session. A concurrent duplicate is
refused without inference. A process crash leaves the durable reservation
pending, deliberately failing closed; recovery is an operator decision, never
an automatic retry of possibly completed work.

## Pending error-code registry

All `/chat` contract errors are HTTP 422 with exactly
`{"error":{"code":string,"step":null}}`. These names are **pending owner
registration and are not registered codes**:

- `malformed-request`
- `unknown-session`
- `idempotency-conflict`
- `idempotency-in-progress`
- `session-in-progress`
- `inference-refused`
- `facade-storage-refused`

Until §13 owner registration and the remaining owner actions in
`RAPP1_STATUS.md` are complete, callers must treat this endpoint as a local
pre-acceptance implementation only.
