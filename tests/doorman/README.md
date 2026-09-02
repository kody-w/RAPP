# Retired Doorman browser harness

This directory preserves the location and explanation of the former external
Doorman browser harness. It previously drove planted browser pages, discovered
operator authentication material, and placed a token into page storage before
contacting historical deployments.

That behavior is retired and is not RAPP/1 conformance evidence:

- `chat.js` and `smoke.js` are fail-closed tombstones that immediately report
  **410 Gone** and exit with code **78**;
- they do not inspect arguments, environment credentials, the operator's home
  directory, CLI authentication, browser storage, or network destinations;
- `package.json` exposes no scripts and has no browser dependency; and
- no setup, fleet target, or authenticated execution instructions remain.

The preserved executable files exist only so stale direct invocations fail
closed. Their containment is verified offline by
`node tests/test-worker-containment.mjs`.
