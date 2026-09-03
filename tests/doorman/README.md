# Doorman browser harness — retained and fixture-gated

This directory retains the substantive Playwright CLI/browser harness as
historical implementation evidence. It is not RAPP/1 conformance evidence and
does not make the former browser product current.

## Provenance

The last full pre-tombstone sources were restored from commit
`6bd45f00981959a3fdfcc64fb32608533aae5021`:

| File | Historical git blob |
|---|---|
| `.gitignore` | `504afef81fbadc8c0a072e1ac93f1376bca7f4a9` |
| `README.md` | `94886650f3515dc94094f9e6eeb2583c5206494b` |
| `chat.js` | `6562be9e8948d11fffbe2937897314f024e63038` |
| `package.json` | `fae48ea89656dec37666ca61ce982e5d8fe4efa8` |
| `smoke.js` | `56e95e0cd380f7fad7f9d53aa59df5909ae621e5` |

The original navigation, welcome/persona checks, chat turn, assistant wait,
system-trace capture, and fleet assertions remain executable.

## Safety adaptation

Browser launch is disabled unless `RAPP_DOORMAN_BROWSER_TESTS=1` is supplied.
The harness:

- never searches files, home directories, environment variables, or CLIs for
  credentials;
- rejects automatic auth and real-looking GitHub token prefixes;
- accepts only an explicit `--test-token=synthetic-...` (or equivalent
  `test-` / `fixture-` prefix);
- allows loopback fixture URLs, plus exact origins explicitly listed in
  `RAPP_DOORMAN_FIXTURE_ORIGINS`;
- navigates first, verifies the final origin, writes the synthetic token only
  in that page's local storage, then reloads; and
- never uses a context-wide initialization script that could place a token in
  an unrelated origin.

Playwright and a browser executable must already be supplied. These scripts do
not install or download dependencies.

## Explicit fixture runs

Anonymous welcome-state inspection:

```bash
RAPP_DOORMAN_BROWSER_TESTS=1 \
  node tests/doorman/chat.js http://127.0.0.1:4173/doorman/
```

Synthetic authenticated fixture turn:

```bash
RAPP_DOORMAN_BROWSER_TESTS=1 \
  node tests/doorman/chat.js http://127.0.0.1:4173/doorman/ \
  --test-token=synthetic-doorman-fixture "fixture message"
```

`smoke.js` retains the historical fleet as data, but those non-loopback
origins are not runnable unless an operator explicitly allowlists them.
Local fixture scenarios can instead be supplied as a JSON array in
`RAPP_DOORMAN_FIXTURES_JSON`; each URL still passes the same origin gate.

The checked-in default performs no browser or network activity. Focused
offline assertions live in `../test-worker-containment.mjs`.
