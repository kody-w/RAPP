# RAPP/1 `/chat` façade — pre-acceptance

This target-owned façade is the repository's only candidate RAPP/1 synchronous
wire endpoint. It is **not publicly conformant or authenticated**. Acceptance
remains blocked until the estate owner publishes the authenticated RAPP/1 §13
registry and registers the error codes below. The structural authority pin in
`RAPP1_AUTHORITY.json` is not that registry.

The façade is separate from the immutable grail application. It does not mount
or serve any route from `brainstem.py`; the private production boundary calls
only the pinned `call_copilot(messages, tools=None)` function. Agents and tools
are never loaded or run. A tool-bearing, ambiguous, empty, or failed assistant
inference is refused.

## Launch

```bash
python3.11 -m pip install -r requirements-rapp1-core.txt -r rapp_brainstem/requirements.txt
python3.11 rapp_brainstem/run_rapp1_facade.py
```

Defaults:

- bind: `127.0.0.1:7073` (separate from grail port `7071`);
- SQLite: `~/.brainstem/rapp1-facade.sqlite3`.

Configuration is limited to `RAPP1_FACADE_HOST`, `RAPP1_FACADE_PORT`, and
`RAPP1_FACADE_DB`. The launcher serves `POST /chat`, its loopback-only browser
preflight, and control-plane `GET /health`. Health explicitly reports
`authenticated:false` and `fully_conformant:false`. The checked-in browser UI
posts chat requests directly to `http://127.0.0.1:7073/chat`; CORS is granted
only to loopback browser origins.

## Wire and durability

`POST /chat` accepts a JSON object with required string `user_input`, optional
string `session_id`, and optional string `idempotency_key`. Every other member,
including client-supplied history, is ignored after the entire request passes
the strict RAPP I-JSON profile. `user_input` may be any string, including the
empty string or whitespace, and is never trimmed or normalized. Duplicate
members, invalid UTF-8, a BOM, lone surrogates, invalid binary64 numbers,
excessive depth, or a canonical form over 1 MiB are malformed even when they
occur only in ignored members. A separate 2 MiB raw transport cap bounds the
request read before parsing, so an oversized raw body is refused with the exact
malformed-request envelope. Newly generated assistant text is normalized to
NFC before persistence and emission; stored replay bytes are never rewritten.
Success has exactly:

```json
{"response":"...","agent_logs":[],"session_id":"..."}
```

This ordinary §8 response object is JSON, not a JCS ordering requirement.

The server persists and supplies the transcript. SQLite `BEGIN IMMEDIATE`
transactions validate an existing session, reserve its active turn, and reserve
idempotency before inference. Creation keys are global; existing-session keys
are scoped by `(session_id, key)`. Completion stores the turn and exact response
bytes atomically. Every repeated same-scope key replays the original terminal
status and body byte-for-byte, even when recognized or ignored request content
differs. Historical request fingerprints remain storage metadata only; they do
not gate or rewrite terminal replay.

Only one inference may be pending for a session. A concurrent duplicate with
the same scope and key waits on a process condition and polls the durable row
for cross-worker completion, then replays the terminal bytes without another
inference. Active work refreshes a durable heartbeat. Only a pending
reservation whose heartbeat is absent or older than the bounded 30-second
orphan policy fails closed as `idempotency-in-progress`; it is never retried
automatically. A concurrent different key remains `session-in-progress`.

## Pending error-code registry

All `/chat` contract errors are HTTP 422 with exactly
`{"error":{"code":string,"step":null}}`. These names are **pending owner
registration and are not registered codes**:

- `malformed-request`
- `unknown-session`
- `idempotency-in-progress`
- `session-in-progress`
- `inference-refused`
- `facade-storage-refused`

Until §13 owner registration and the remaining owner actions in
`RAPP1_STATUS.md` are complete, callers must treat this endpoint as a local
pre-acceptance implementation only.
