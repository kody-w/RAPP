# `installer/shortcuts/`

> **Pre-acceptance documentation; no Shortcut is shipped.** For
> canonicalization, identity, frames, wire, eggs, registry, trust, and protocol
> evolution, follow RAPP/1 rev-5 through
> [`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../RAPP1_STATUS.md).

This directory preserves an Apple Shortcut design and signing helper. It no
longer advertises a live install, Tier 2 endpoint, or browser product.

| Path | Current disposition |
|---|---|
| [`protocol.md`](protocol.md) | Exact local façade request, success, nested error, and client-side speech derivation. |
| [`index.html`](index.html) | Pre-acceptance design page; no download or install. |
| `sign.sh` | Historical local authoring helper, not a shipped Shortcut. |
| [`brainstem-voice/`](brainstem-voice/) | Retired, unshipped design notes. |

## Wire rule

A client sends required string `user_input` and optional strings `session_id` /
`idempotency_key`. Success contains exactly `response`, `agent_logs` (an array),
and `session_id`; HTTP 422 contains exactly nested
`{"error":{"code":"...","step":null}}`.

Voice is derived locally from the `response` string. There is no
`voice_response`, `twin_response`, `voice_mode`, or `twin_mode` response member.
The server owns history, so clients do not send `conversation_history`.

## Publication status

No `.shortcut` artifact or iCloud link is present. Do not present this directory
as installable. The target-owned façade binds to `127.0.0.1:7073` and remains
pre-acceptance until the owner actions in `RAPP1_STATUS.md` are complete.

The dated form-factor rationale remains in the
[superseded vault note](../../pages/vault/Architecture/Surfaces%20%E2%80%94%20Mobile,%20Watch,%20Voice.md).
