# RAPP browser worker — retained source, disabled runtime

This directory preserves the substantive historical Cloudflare Worker instead
of replacing it with an HTTP 410 stub. It remains a pre-acceptance browser
adapter, not the RAPP/1 wire and not a shipped service.

## Provenance

The implementation was restored from commit
`4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6`:

| File | Historical git blob |
|---|---|
| `worker.js` | `030437b4fd79cb4bf833a4c14a204f4c05ec2bd5` |
| `README.md` | `0290d508aec45b4c963ae590d1716bc7ababafc7` |
| `wrangler.toml` | `b354cbb6759952105263b862d7ba18c185daa591` |

The restored routes still contain the original OAuth exchange, device flow,
Copilot session/model/chat proxy, public model catalog, user lookup, cache, and
CORS logic. The unsafe edge is adapted at the runtime boundary rather than
deleted.

## Fail-closed contract

`GET /healthz` and CORS preflight are read-only. Every route that could touch
an upstream returns a local refusal unless all of these are explicit:

1. `RAPP_BROWSER_RUNTIME_ENABLED` is exactly `true`;
2. `RAPP_REVIEWED_BROWSER_RUNTIME` is a reviewed fetch binding with a
   `fetch(input, init)` method; and
3. `RAPP_BROWSER_RUNTIME_CAPABILITIES` enables the exact route capability.

Capabilities are false by default:

`oauthExchange`, `deviceFlow`, `copilotToken`, `copilotModels`,
`copilotChat`, `catalog`, and `user`.

The capabilities binding may be a comma-separated list, a JSON object, or an
object supplied by a test host. The optional `RAPP_BROWSER_RUNTIME_CACHE`
binding must expose `match` and `put`; there is no fallback to a global cache.
`RAPP_BROWSER_ALLOWED_ORIGINS` adds exact origins to the localhost-only
default. The worker never falls back to global `fetch`.

The repository intentionally supplies neither the reviewed fetch binding nor
enabled capabilities. Therefore the checked-in default cannot exchange a
token, invoke a model, read the catalog or user API, or perform any network
request.

## Authority boundary

The immutable grail remains the bytes recorded in
[`../KERNEL_PIN.json`](../KERNEL_PIN.json) from
`kody-w/rapp-installer@brainstem-v0.6.9`. This worker does not modify or
replace those bytes. Current status and owner-action blockers remain in
[`../RAPP1_STATUS.md`](../RAPP1_STATUS.md).

Focused offline coverage:

```bash
node tests/test-worker-containment.mjs
```
