#!/usr/bin/env node
// Self-contained JavaScript/static checks for the current RAPP/1 rev-5
// pre-acceptance surface. Behavioral Python conformance runs through
// tests/run_rapp1_conformance.py; this runner needs only Node.js.

import {
  existsSync,
  readFileSync,
  readdirSync,
  statSync,
} from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, '..');
const EXPECTED_AUTHORITY_COMMIT =
  '6723c7add2aed36bb68992fc71a56b0a4bd5ad81';
const EXPECTED_SPEC_SHA =
  '6d06daba65d7c045716f3d6e95db8401ab58e727820e4114466d847f62cae49b';
const OWNER_BLOCKERS = [
  'Signed monotonic registry and out-of-band anchor',
  'Lawful root re-anchor',
  'Signed replacement invite',
  'External mirror correction',
];

let passed = 0;
const failures = [];

function read(relative) {
  return readFileSync(join(ROOT, relative), 'utf8');
}

function json(relative) {
  return JSON.parse(read(relative));
}

function sha256(relative) {
  return createHash('sha256')
    .update(readFileSync(join(ROOT, relative)))
    .digest('hex');
}

function equal(actual, expected, message = 'values differ') {
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    throw new Error(
      `${message}\nexpected ${JSON.stringify(expected)}\nactual   ${JSON.stringify(actual)}`,
    );
  }
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function test(name, check) {
  try {
    check();
    passed += 1;
    console.log(`  \x1b[32m✓\x1b[0m ${name}`);
  } catch (error) {
    failures.push({ name, error });
    console.log(`  \x1b[31m✗\x1b[0m ${name}`);
    console.log(`    ${error.message}`);
  }
}

console.log('\n\x1b[1mRAPP/1 rev-5 core/static contract checks\x1b[0m\n');

const authority = json('RAPP1_AUTHORITY.json');
const fixture = json('tests/fixtures/rapp1-spec-rev5.json');
const status = read('RAPP1_STATUS.md');

test('authority is the rev-5 structural pin', () => {
  equal(authority.schema, 'rapp-authority-pin/1.0');
  equal(authority.record_kind, 'structural-authority-pin');
  equal(authority.standard.commit, EXPECTED_AUTHORITY_COMMIT);
  equal(authority.standard.sha256, EXPECTED_SPEC_SHA);
  equal(authority.standard.wire_tag, 'rapp/1');
  equal(authority.standard.revision, 'rev-5');
  equal(authority.target.status, 'not-yet-fully-rapp-1-conformant');
});

test('offline provenance fixture agrees with every authority field', () => {
  for (const [key, value] of Object.entries(authority.standard)) {
    equal(fixture.source[key], value, `provenance field differs: ${key}`);
  }
  assert(
    Number.isInteger(fixture.source.line_count) && fixture.source.line_count > 0,
    'offline fixture line count must be a positive integer',
  );
  equal(fixture.contains_spec_bytes, false);
  equal(authority.offline_verification.vendored_spec_bytes, false);
});

test('structural pin does not claim authenticated registry authority', () => {
  equal(authority.authenticated_registry.is_section_13_registry, false);
  assert(
    /not an authenticated RAPP\/1 section 13 registry/i.test(
      authority.authenticated_registry.statement,
    ),
    'missing non-authority statement',
  );
});

test('status leads with the non-conformance declaration', () => {
  assert(
    status.startsWith('# NOT YET FULLY RAPP/1 CONFORMANT'),
    'status must lead with the non-conformance declaration',
  );
  assert(
    status.includes('Structural validation is not authenticated acceptance'),
    'status must distinguish structural validation from acceptance',
  );
});

test('all owner-action blockers remain explicit', () => {
  assert(status.includes('## Owner-action blockers'), 'blocker heading missing');
  for (const blocker of OWNER_BLOCKERS) {
    assert(status.includes(`**${blocker}**`), `missing blocker: ${blocker}`);
  }
});

test('immutable grail hashes agree and bytes remain pinned', () => {
  const pin = json('KERNEL_PIN.json');
  const frozen = authority.immutable_grail_boundary.frozen;
  equal(pin.kernel.frozen, frozen);
  for (const [relative, expected] of Object.entries(frozen)) {
    equal(sha256(relative), expected, `grail byte drift: ${relative}`);
  }
});

test('strict core module set is present', () => {
  const expected = [
    '__init__.py',
    '__main__.py',
    'canonical.py',
    'cli.py',
    'egg.py',
    'errors.py',
    'frame.py',
    'hashing.py',
    'identity.py',
    'jws.py',
    'trust.py',
  ];
  const actual = readdirSync(join(ROOT, 'rapp1_core'))
    .filter((name) => name.endsWith('.py'))
    .sort();
  equal(actual, expected.sort());
  for (const name of actual) {
    assert(
      statSync(join(ROOT, 'rapp1_core', name)).size > 0,
      `empty core module: ${name}`,
    );
  }
});

test('pre-acceptance facade uses strict parsing and exact refusal status', () => {
  const source = read('rapp_brainstem/rapp1_facade.py');
  for (const marker of [
    'strict_loads',
    'idempotency_key',
    '"agent_logs": []',
    '"session_id": reserved.session_id',
    '_http_response(_error_body(code), 422)',
  ]) {
    assert(source.includes(marker), `facade marker missing: ${marker}`);
  }
  assert(!source.includes('"assistant_response"'), 'retired response alias returned');
  assert(!source.includes('"voice_response"'), 'application field leaked into wire');
});

test('contained Tier 2 deployment cannot advertise RAPP/1', () => {
  const guard = json('rapp_swarm/RAPP1_DEPLOYMENT_GUARD.json');
  equal(guard.status, 'retired');
  equal(guard.rapp1_packaging_allowed, false);
  equal(guard.rapp1_advertising_allowed, false);
});

test('legacy browser execution surfaces are static 410 tombstones', () => {
  for (const relative of [
    'pages/vbrainstem.html',
    'pages/tether.html',
    'pages/sphere.html',
    'rapp_swarm/index.html',
  ]) {
    const source = read(relative).toLowerCase();
    assert(source.includes('http 410'), `${relative} lacks HTTP 410`);
    assert(!source.includes('<script'), `${relative} still executes scripts`);
    assert(!source.includes('fetch('), `${relative} still performs fetch`);
  }
});

test('legacy plant producer is an explicit refusal only', () => {
  const source = read('installer/plant.sh');
  assert(source.includes('410 Gone'), 'plant retirement is missing');
  assert(source.includes('exit 78'), 'plant retirement exit is missing');
  for (const marker of ['gh repo create', 'git push', 'rapp-frame/', 'brainstem-egg/']) {
    assert(!source.includes(marker), `retired plant marker remains: ${marker}`);
  }
});

test('target-owned legacy launchers are explicit refusal only', () => {
  const launchers = [
    ['rapp_brainstem/start.sh', ['brainstem.py', 'boot.py', 'python', 'pip', 'exec ']],
    ['rapp_brainstem/start.ps1', ['brainstem.py', 'boot.py', 'python', 'pip', 'Start-Process']],
    ['rapp_brainstem/utils/boot.py', ['brainstem.py', 'lineage_check', 'import ', 'subprocess', 'exec']],
  ];
  for (const [relative, forbidden] of launchers) {
    const source = read(relative);
    assert(source.includes('410 Gone'), `${relative} retirement is missing`);
    for (const marker of forbidden) {
      assert(!source.includes(marker), `${relative} retains launch marker: ${marker}`);
    }
  }
  assert(read('rapp_brainstem/start.sh').includes('exit 78'));
  assert(read('rapp_brainstem/start.ps1').includes('exit 78'));
  assert(read('rapp_brainstem/utils/boot.py').includes('SystemExit(78)'));
});

test('live distribution inventory uses dynamic category coverage', () => {
  const inventory = json('tests/rapp1-live-surface-inventory.json');
  equal(inventory.schema, 'rapp1-live-surface-inventory/1.0');
  equal(Object.keys(inventory.categories).sort(), [
    'browser',
    'containment',
    'installer',
    'marketing',
    'wire',
  ]);
  assert(inventory.count_policy.includes('git ls-files'), 'count policy is not dynamic');
  for (const [category, paths] of Object.entries(inventory.categories)) {
    assert(paths.length > 0, `empty live category: ${category}`);
    for (const relative of paths) {
      assert(existsSync(join(ROOT, relative)), `stale ${category} path: ${relative}`);
    }
  }
});

test('retired archives remain exact bytes without publication', () => {
  const manifest = json('installer/RETIRED_ARTIFACTS.json');
  equal(manifest.publication_allowed, false);
  equal(manifest.repacking_allowed, false);
  equal(manifest.power_archive.signature_status, 'unsigned');
  equal(manifest.power_archive.active_download_allowed, false);
  const records = [
    ...manifest.power_archive.copies,
    ...manifest.immutable_eggs,
  ];
  equal(records.length, 7);
  for (const record of records) {
    equal(sha256(record.path), record.sha256, `archive drift: ${record.path}`);
    equal(statSync(join(ROOT, record.path)).size, record.bytes, `size drift: ${record.path}`);
  }
});

test('owned pages do not publish retired distribution or plant callers', () => {
  for (const relative of ['index.html', 'installer/index.html']) {
    const source = read(relative);
    for (const marker of ['install-swarm.sh', 'azuredeploy.json', 'install.ps1']) {
      assert(!source.includes(marker), `${relative} advertises ${marker}`);
    }
    assert(
      !source.includes('RAPP/installer/install.sh'),
      `${relative} advertises the retired installer`,
    );
    assert(
      !/<a\b[^>]*href=["'][^"']*MSFTAIBASMultiAgentCopilot/i.test(source),
      `${relative} publishes the unsigned Power archive`,
    );
  }
  for (const relative of [
    'installer/plant.html',
    'installer/plant_qr.html',
    'installer/seed.html',
    'pages/metropolis/plant-from-discord.html',
  ]) {
    const source = read(relative).toLowerCase();
    assert(source.includes('http 410'), `${relative} lacks HTTP 410`);
    assert(!source.includes('<script'), `${relative} still executes scripts`);
    assert(!source.includes('plant.sh'), `${relative} still calls the planter`);
  }
  assert(
    !read('pages/metropolis/index.html').includes('plant-from-discord'),
    'metropolis still links the retired planter',
  );
});

const agentsDir = join(ROOT, 'rapp_brainstem', 'agents');
const agentFiles = readdirSync(agentsDir)
  .filter((name) => name.endsWith('_agent.py') && name !== 'basic_agent.py')
  .sort();

test('current starter agent set exists', () => {
  equal(agentFiles, [
    'context_memory_agent.py',
    'hacker_news_agent.py',
    'manage_memory_agent.py',
  ]);
});

for (const filename of agentFiles) {
  test(`${filename} keeps the current single-file agent contract`, () => {
    const source = read(`rapp_brainstem/agents/${filename}`);
    const subclasses = [
      ...source.matchAll(/^class\s+([A-Za-z_]\w*Agent)\(BasicAgent\):/gm),
    ];
    equal(subclasses.length, 1, 'expected exactly one BasicAgent subclass');
    assert(
      source.includes('from agents.basic_agent import BasicAgent'),
      'BasicAgent import missing',
    );
    assert(source.includes('self.metadata = {'), 'metadata assignment missing');
    assert(/def perform\(self,\s*\*\*kwargs\):/.test(source), 'perform(**kwargs) missing');
    assert(source.includes('"schema": "rapp-agent/1.0"'), 'agent manifest missing');
  });
}

test('removed reserved and neighborhood capability trees stay absent', () => {
  for (const relative of [
    'rapp_brainstem/utils/reserved_agents',
    'rapp_brainstem/utils/organs/lifecycle_organ.py',
    'rapp_brainstem/utils/organs/neighborhood_membership_organ.py',
  ]) {
    assert(!existsSync(join(ROOT, relative)), `retired capability returned: ${relative}`);
  }
});

test('legacy-positive tests are data fixtures, not executable tests', () => {
  const inventory = json('tests/fixtures/rapp1-retired-test-inventory.json');
  equal(inventory.schema, 'rapp1-retired-test-inventory/1.0');
  equal(inventory.quarantine.path_count, inventory.quarantine.files.length);
  assert(
    inventory.quarantine.files.every(
      (entry) => entry.rationale && /^[0-9a-f]{64}$/.test(entry.sha256),
    ),
    'every quarantined test needs a rationale and byte hash',
  );
  assert(
    existsSync(join(ROOT, inventory.quarantine.root)),
    'legacy quarantine root missing',
  );
});

test('retired browser parity suite is quarantined, not executable', () => {
  assert(!existsSync(join(ROOT, 'tests', 'index.html')));
  assert(
    existsSync(join(ROOT, 'tests', 'fixtures', 'legacy-conformance', 'index.html.txt')),
    'retired browser suite fixture missing',
  );
});

test('canonical runner and pinned workflow are present', () => {
  for (const relative of [
    'tests/check_offline_boundary.py',
    'tests/offline_guard/sitecustomize.py',
    'tests/offline_guard/node-network-guard.cjs',
    'tests/run_rapp1_conformance.py',
    'tests/test_rapp1_runner.py',
    '.github/workflows/rapp1-conformance.yml',
  ]) {
    assert(existsSync(join(ROOT, relative)), `missing: ${relative}`);
  }
});

const total = passed + failures.length;
console.log(`\n${passed}/${total} passed.`);
if (failures.length) {
  console.log('\nFailures:');
  for (const { name, error } of failures) {
    console.log(` • ${name}: ${error.message}`);
  }
  process.exit(1);
}
