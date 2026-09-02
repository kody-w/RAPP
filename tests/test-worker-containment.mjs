#!/usr/bin/env node

import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');

function read(relativePath) {
  return fs.readFileSync(path.join(root, relativePath), 'utf8');
}

function readJson(relativePath) {
  return JSON.parse(read(relativePath));
}

function assertNoMatches(source, patterns, label) {
  for (const pattern of patterns) {
    assert.doesNotMatch(source, pattern, `${label} must not match ${pattern}`);
  }
}

function assertInertPackage(relativePath) {
  const manifest = readJson(relativePath);
  assert.equal(manifest.private, true, `${relativePath} must remain private`);
  for (const field of [
    'scripts',
    'dependencies',
    'devDependencies',
    'optionalDependencies',
    'peerDependencies',
  ]) {
    assert.deepEqual(
      manifest[field] ?? {},
      {},
      `${relativePath} must not expose ${field}`,
    );
  }
}

function assertExit78(label, command, args) {
  const syntheticToken = 'synthetic-containment-token-not-a-credential';
  const result = spawnSync(command, args, {
    cwd: root,
    encoding: 'utf8',
    timeout: 5000,
    env: {
      PATH: process.env.PATH || '/usr/bin:/bin',
      HOME: path.join(root, '.containment-no-home'),
      GH_TOKEN: syntheticToken,
      GITHUB_TOKEN: syntheticToken,
      COPILOT_TOKEN: syntheticToken,
    },
  });

  assert.equal(result.error, undefined, `${label} must terminate without spawn error`);
  assert.equal(result.signal, null, `${label} must not be killed`);
  assert.equal(result.status, 78, `${label} must fail closed with exit 78`);
  const output = `${result.stdout || ''}${result.stderr || ''}`;
  assert.match(output, /410 Gone/, `${label} must explain retirement`);
  assert.doesNotMatch(output, new RegExp(syntheticToken), `${label} must not echo credentials`);
}

const workerSource = read('worker/worker.js');
assert.equal(
  (workerSource.match(/\bfetch\s*\(/g) || []).length,
  1,
  'the Worker handler must be the only fetch-shaped call in worker.js',
);
assert.match(workerSource, /\bfetch\(\)\s*\{/);
assertNoMatches(workerSource, [
  /\basync\b/,
  /\bawait\b/,
  /\bcaches\b/,
  /\bWebSocket\b/,
  /\bXMLHttpRequest\b/,
  /\bGH_(?:CLIENT|DEVICE|TOKEN|SECRET)\b/,
  /https?:\/\//i,
  /github(?:copilot)?\.com/i,
  /models\.github/i,
  /\/api\//,
], 'worker.js');

const workerReadme = read('worker/README.md');
assert.match(workerReadme, /retired/i);
assert.match(workerReadme, /do not deploy/i);
assert.doesNotMatch(
  workerReadme,
  /\bwrangler\s+(?:deploy|dev|login|secret|tail)\b/i,
  'worker README must not contain deployment instructions',
);
const wranglerConfig = read('worker/wrangler.toml');
assert.match(wranglerConfig, /Do not deploy/);
assert.doesNotMatch(wranglerConfig, /\bwrangler\s+(?:deploy|dev|login|secret|tail)\b/i);

const encodedWorker = Buffer.from(workerSource).toString('base64');
const worker = (await import(`data:text/javascript;base64,${encodedWorker}`)).default;
const originalFetch = globalThis.fetch;
let upstreamCalls = 0;
globalThis.fetch = async () => {
  upstreamCalls += 1;
  throw new Error('retired worker attempted an upstream request');
};

const workerRequests = [
  ['GET', '/'],
  ['HEAD', '/healthz'],
  ['POST', '/api/auth/token'],
  ['POST', '/api/auth/device'],
  ['POST', '/api/auth/device/poll'],
  ['GET', '/api/copilot/token'],
  ['GET', '/api/copilot/models'],
  ['POST', '/api/copilot/chat'],
  ['PUT', '/api/copilot/chat/completions'],
  ['GET', '/api/models'],
  ['DELETE', '/api/user'],
  ['OPTIONS', '/anything/preflight'],
  ['PATCH', '/unknown?query=ignored'],
];

try {
  for (const [method, route] of workerRequests) {
    const init = {
      method,
      headers: {
        Authorization: 'Bearer synthetic',
        'Content-Type': 'application/json',
        Origin: 'https://arbitrary.example',
      },
    };
    if (method !== 'GET' && method !== 'HEAD') init.body = '{"ignored":true}';

    const response = await worker.fetch(
      new Request(`https://worker.example${route}`, init),
      { GH_CLIENT_SECRET: 'must-not-be-read' },
      { waitUntil() { throw new Error('retired worker attempted background work'); } },
    );

    assert.equal(response.status, 410, `${method} ${route} must return 410`);
    assert.equal(response.headers.get('Cache-Control'), 'no-store');
    assert.equal(response.headers.get('Access-Control-Allow-Origin'), '*');
    assert.deepEqual(await response.json(), {
      error: 'gone',
      code: 'runtime-retired',
      status: 410,
      message: 'The retired RAPP browser worker is unavailable.',
      guidance: 'RAPP1_STATUS.md',
    });
  }
} finally {
  globalThis.fetch = originalFetch;
}
assert.equal(upstreamCalls, 0, 'retired worker must never perform upstream requests');

assertInertPackage('tests/doorman/package.json');
const doormanSources = [
  ['tests/doorman/chat.js', 'Doorman chat tombstone'],
  ['tests/doorman/smoke.js', 'Doorman fleet tombstone'],
];
for (const [relativePath, label] of doormanSources) {
  const source = read(relativePath);
  assert.match(source, /process\.exit\(78\)/);
  assertNoMatches(source, [
    /node:(?:child_process|fs|os)/,
    /\.copilot_token/,
    /\bgh\s+auth\s+token\b/i,
    /\blocalStorage\b/,
    /\bplaywright\b/i,
    /\bchromium\b/i,
    /https?:\/\//i,
    /\bfetch\s*\(/,
  ], label);
}
const doormanReadme = read('tests/doorman/README.md');
assert.match(doormanReadme, /retired/i);
assert.match(doormanReadme, /exit with code \*\*78\*\*/);
assertNoMatches(doormanReadme, [
  /\bnpm\s+install\b/i,
  /\bnode\s+(?:chat|smoke)\.js\b/i,
], 'Doorman README');
assertExit78(
  'Doorman chat tombstone',
  process.execPath,
  [
    path.join(root, 'tests/doorman/chat.js'),
    'https://arbitrary.example/',
    '--token=synthetic-containment-token-not-a-credential',
    'ignored message',
  ],
);
assertExit78(
  'Doorman fleet tombstone',
  process.execPath,
  [path.join(root, 'tests/doorman/smoke.js')],
);

assertInertPackage('tests/osi/browser/package.json');
assert.match(
  readJson('tests/osi/browser/package.json').description,
  /Retired historical OSI tether browser suite/,
);
const tetherShell = read('tests/osi/L4a-tether-browser.sh');
const tetherSpec = read('tests/osi/browser/L4a-tether.spec.mjs');
for (const [source, label] of [
  [tetherShell, 'OSI tether shell tombstone'],
  [tetherSpec, 'OSI tether JavaScript tombstone'],
]) {
  assertNoMatches(source, [
    /\bnpm\b/i,
    /\bnpx\b/i,
    /\bplaywright\b/i,
    /\bchromium\b/i,
    /\bpeerjs\b/i,
    /\bcurl\b/i,
    /\bwget\b/i,
    /https?:\/\//i,
    /rapp-tether\/1\.0/i,
  ], label);
}
assert.match(tetherShell, /\bexit 78\b/);
assert.match(tetherSpec, /process\.exit\(78\)/);

const tetherFixture = read('tests/osi/browser/fixture.html');
assertNoMatches(tetherFixture, [
  /<script\b/i,
  /<iframe\b/i,
  /\bsrc\s*=/i,
  /\bhref\s*=/i,
  /https?:\/\//i,
  /\bpeerjs\b/i,
  /rapp-tether\/1\.0/i,
], 'OSI tether fixture');
assert.match(tetherFixture, /default-src 'none'/);

assertExit78(
  'OSI tether shell tombstone',
  '/bin/bash',
  [path.join(root, 'tests/osi/L4a-tether-browser.sh')],
);
assertExit78(
  'OSI tether JavaScript tombstone',
  process.execPath,
  [path.join(root, 'tests/osi/browser/L4a-tether.spec.mjs')],
);

console.log(
  `browser/runtime containment: ${workerRequests.length} worker requests refused; `
  + 'Doorman and OSI browser tombstones verified',
);
