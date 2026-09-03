# Retired RAPP browser worker

This directory is retained as historical evidence of the former Cloudflare
OAuth and API proxy. That service once exchanged GitHub OAuth and device-flow
credentials, exposed Copilot control-plane helpers, and proxied model catalog
and user requests for browser clients.

The runtime is now an unconditional tombstone:

- every method and path, including preflight and the former health route,
  returns **HTTP 410 Gone**;
- no OAuth exchange, token handling, inference, catalog, user, cache, or
  upstream request remains;
- `worker.js` has no environment-secret dependency; and
- the Wrangler metadata is retained only to identify the historical artifact.

**Do not deploy or configure this worker as a current RAPP surface.** Current
authority and remaining migration blockers are documented in
[`../RAPP1_STATUS.md`](../RAPP1_STATUS.md).

Containment is verified offline by `node tests/test-worker-containment.mjs`.
