#!/usr/bin/env node

import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const source = fs.readFileSync(path.join(here, '..', 'worker', 'worker.js'), 'utf8');
const encoded = Buffer.from(source).toString('base64');
const worker = (await import(`data:text/javascript;base64,${encoded}`)).default;

let upstreamCalls = [];
globalThis.fetch = async (...args) => {
  upstreamCalls.push(args);
  throw new Error('retired capability route attempted an upstream fetch');
};

for (const [route, method] of [
  ['/api/copilot/chat', 'POST'],
  ['/api/copilot/chat/', 'GET'],
  ['/api/copilot/chat/completions', 'POST'],
  ['/api/copilot/chat', 'OPTIONS'],
]) {
  const response = await worker.fetch(new Request(`https://worker.example${route}`, {
    method,
    headers: { Authorization: 'Bearer test', 'Content-Type': 'application/json' },
    body: method === 'GET' ? undefined : '{}',
  }), {}, {});
  assert.equal(response.status, 410, `${method} ${route} must return 410`);
  assert.equal(response.headers.get('Cache-Control'), 'no-store');
  const body = await response.json();
  assert.equal(body.error, 'gone');
  assert.equal(body.code, 'capability-route-retired');
  assert.equal(body.guidance, 'RAPP1_STATUS.md');
}

assert.equal(upstreamCalls.length, 0, 'retired routes must never proxy inference');

const health = await worker.fetch(new Request('https://worker.example/healthz'), {}, {});
assert.equal(health.status, 200);
assert.equal(await health.text(), 'ok');

globalThis.fetch = async (...args) => {
  upstreamCalls.push(args);
  return new Response('{"data":[]}', {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
};
const models = await worker.fetch(new Request(
  'https://worker.example/api/copilot/models',
  { headers: { Authorization: 'Bearer test' } },
), {}, {});
assert.equal(models.status, 200, 'model control-plane route must remain available');
assert.equal(upstreamCalls.length, 1);
assert.match(String(upstreamCalls[0][0]), /githubcopilot\.com\/models$/);

console.log('worker containment: 4 retired requests refused; control plane preserved');
