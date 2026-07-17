# Brainstem Voice — retired design

> **No Shortcut is shipped or installable here.** For canonicalization,
> identity, frames, wire, eggs, registry, trust, and protocol evolution, follow
> RAPP/1 rev-5 through
> [`RAPP1_AUTHORITY.json`](../../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../../RAPP1_STATUS.md).

The former five-action “Brainstem Voice” idea is retained as pre-acceptance
design history. Its promised iCloud link and `.shortcut` download were never
published. Tier 2 and public browser endpoints are retired.

## Correct local design

A future private experiment would:

1. collect text;
2. POST only required string `user_input` plus optional strings `session_id`
   and `idempotency_key` to `http://127.0.0.1:7073/chat`;
3. read an HTTP 200 body containing exactly `response`, `agent_logs` (an
   array), and `session_id`;
4. handle HTTP 422 as exactly
   `{"error":{"code":"<code>","step":null}}`; and
5. derive spoken text locally from `response`.

When `response` contains `|||VOICE|||`, a client may speak the following segment
and stop before `|||TWIN|||`; otherwise it may speak the complete response.
Those markers remain inside the string. There are no voice/twin fields, mode
flags, client history, or other extra wire members.

See [`../protocol.md`](../protocol.md) and the target-owned
[`RAPP1_FACADE.md`](../../../rapp_brainstem/RAPP1_FACADE.md). Publication must
wait for authenticated acceptance and explicit operator action.
