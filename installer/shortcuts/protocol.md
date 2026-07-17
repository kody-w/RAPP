# Apple Shortcut adapter — pre-acceptance

> **No Shortcut is shipped.** For canonicalization, identity, frames, wire,
> eggs, registry, trust, and protocol evolution, follow RAPP/1 rev-5 through
> [`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../RAPP1_STATUS.md). The former Tier 2, browser, and
> live-install claims are retired. This is a local authoring reference only.

## Exact HTTP contract

A future Shortcut may call the separate target-owned façade at
`http://127.0.0.1:7073/chat`. It must send a JSON object containing required
string `user_input` and, only when needed, optional string `session_id` and
optional string `idempotency_key`:

```json
{"user_input":"What is next?","session_id":"optional","idempotency_key":"optional"}
```

Omit unused optional members. Do not send history, identity, mode, voice, twin,
or other application fields. The server owns transcript history.

HTTP 200 has exactly:

```json
{"response":"...","agent_logs":[],"session_id":"..."}
```

`agent_logs` is an array. A contract refusal is HTTP 422 with exactly:

```json
{"error":{"code":"<code>","step":null}}
```

The codes remain pending owner registration, so this façade is not publicly
conformant or authenticated.

## Five local actions

1. **Ask for Input** — collect text.
2. **Get Contents of URL** — POST JSON to
   `http://127.0.0.1:7073/chat` with `Content-Type: application/json`.
3. **Get Dictionary Value** — read `response`.
4. **Derive speech locally** — when `response` contains `|||VOICE|||`, take the
   text after it and stop before `|||TWIN|||` if present; otherwise use the
   complete `response`.
5. **Speak Text** — speak the locally derived string.

`|||VOICE|||` and `|||TWIN|||` are optional application rendering markers
inside `response`. They never authorize `voice_response`, `twin_response`, mode
flags, or any other top-level wire member.

For a follow-up, save the successful `session_id` and send it on the next
request. For a deliberate retry, reuse the same `idempotency_key`; do not invent
additional retry fields.

## Distribution status

There is no checked-in `.shortcut`, iCloud share link, direct download, public
facade deployment, Azure endpoint, or Copilot Studio endpoint. The historical
signing helper does not make this an install surface. An operator may author a
private local experiment, but publication must wait for the acceptance blockers
in `RAPP1_STATUS.md`.

## Related

- [`README.md`](README.md) — directory status.
- [`brainstem-voice/README.md`](brainstem-voice/README.md) — retired design.
- [`rapp_brainstem/RAPP1_FACADE.md`](../../rapp_brainstem/RAPP1_FACADE.md) —
  façade behavior and pending error codes.
