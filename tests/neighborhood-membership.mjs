#!/usr/bin/env node
/* tests/neighborhood-membership.mjs — Public-gate / private-companion seed pair validator.
 *
 * Verifies the structural contract of a planted RAPP neighborhood split across
 * two repos:
 *
 *   - shared neighborhood_rappid across both seeds
 *   - bidirectional cross-references (gate.private_companion.repo ↔ private.gate_repo.repo)
 *   - schema versions current and consistent
 *   - required files present
 *   - members.json roster includes the founder + at least one test seat
 *   - no member-only data leaked into the public gate
 *
 * Run:   node tests/neighborhood-membership.mjs
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname  = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '..');

const SEED_DIR = path.join(ROOT, 'installer', 'neighborhood-seeds');
const PUBLIC_SEED  = path.join(SEED_DIR, 'microsoft-se-team-neighborhood');
const PRIVATE_SEED = path.join(SEED_DIR, 'microsoft-se-team-neighborhood-private');

let pass = 0, fail = 0;
const failures = [];
function test(name, fn) {
  return Promise.resolve().then(fn).then(() => {
    pass++; process.stdout.write(`  \x1b[32m✓\x1b[0m ${name}\n`);
  }).catch(err => {
    fail++; failures.push({ name, err });
    process.stdout.write(`  \x1b[31m✗\x1b[0m ${name}\n    ${err.message}\n`);
  });
}
function assert(cond, msg) { if (!cond) throw new Error(msg || 'assertion failed'); }
function readJSON(p) { return JSON.parse(fs.readFileSync(p, 'utf8')); }
function exists(p) { return fs.existsSync(p); }

const PUB = readJSON(path.join(PUBLIC_SEED, 'neighborhood.json'));
const PRV = readJSON(path.join(PRIVATE_SEED, 'neighborhood.json'));

console.log('\nneighborhood-membership.mjs — seed-pair coherence\n');

await test('both seeds carry the same neighborhood_rappid', () => {
  assert(PUB.neighborhood_rappid, 'public missing neighborhood_rappid');
  assert(PRV.neighborhood_rappid, 'private missing neighborhood_rappid');
  assert(
    PUB.neighborhood_rappid === PRV.neighborhood_rappid,
    `mismatch: public=${PUB.neighborhood_rappid} private=${PRV.neighborhood_rappid}`
  );
});

await test('schema is rapp-neighborhood/1.0 on both', () => {
  assert(PUB.schema === 'rapp-neighborhood/1.0', `public schema: ${PUB.schema}`);
  assert(PRV.schema === 'rapp-neighborhood/1.0', `private schema: ${PRV.schema}`);
});

await test('public visibility is gate, private visibility is private', () => {
  assert(PUB.visibility === 'public-gate', `public visibility: ${PUB.visibility}`);
  assert(PRV.visibility === 'private', `private visibility: ${PRV.visibility}`);
});

await test('cross-references are bidirectional', () => {
  const pcRepo = (PUB.private_companion || {}).repo;
  const grRepo = (PRV.gate_repo || {}).repo;
  assert(pcRepo, 'public.private_companion.repo missing');
  assert(grRepo, 'private.gate_repo.repo missing');
  assert(pcRepo === PRV.github, `public.private_companion.repo (${pcRepo}) does not match private.github (${PRV.github})`);
  assert(grRepo === PUB.github, `private.gate_repo.repo (${grRepo}) does not match public.github (${PUB.github})`);
});

await test('public auth scheme requires github_token + repo scope', () => {
  const auth = (PUB.private_companion || {}).auth || {};
  assert(auth.scheme === 'github_token', `auth scheme: ${auth.scheme}`);
  assert(auth.scope_required === 'repo', `auth scope: ${auth.scope_required}`);
});

// basic_agent.py is the base class — it matches the glob but isn't a registered
// agent (no metadata to expose). Exclude it from agent inventory checks.
const agentFiles = (dir) =>
  fs.readdirSync(dir).filter(f => f.endsWith('_agent.py') && f !== 'basic_agent.py').sort();

await test('public seed has the public-safe agent and ONLY that one', () => {
  const files = agentFiles(path.join(PUBLIC_SEED, 'agents'));
  assert(files.length === 1, `expected exactly 1 registered agent in public seed, got ${files.length}: ${files.join(', ')}`);
  assert(files[0] === 'neighborhood_introduce_agent.py', `unexpected agent in public seed: ${files[0]}`);
});

await test('private seed has the four neighborhood agents', () => {
  const files = agentFiles(path.join(PRIVATE_SEED, 'agents'));
  const expected = [
    'neighborhood_ask_agent.py',
    'neighborhood_federate_agent.py',
    'neighborhood_introduce_agent.py',
    'neighborhood_subscribe_agent.py',
  ];
  assert(
    JSON.stringify(files) === JSON.stringify(expected),
    `expected ${JSON.stringify(expected)}, got ${JSON.stringify(files)}`
  );
});

await test('both seeds ship basic_agent.py (the base class)', () => {
  assert(exists(path.join(PUBLIC_SEED, 'agents', 'basic_agent.py')), 'public missing basic_agent.py');
  assert(exists(path.join(PRIVATE_SEED, 'agents', 'basic_agent.py')), 'private missing basic_agent.py');
});

await test('private seed has members.json with founder + rappter1 seats', () => {
  const m = readJSON(path.join(PRIVATE_SEED, 'members.json'));
  assert(m.schema === 'rapp-neighborhood-members/1.0', `members schema: ${m.schema}`);
  assert(m.neighborhood_rappid === PUB.neighborhood_rappid, 'members.neighborhood_rappid mismatch');
  const logins = (m.members || []).map(x => x.github_login);
  assert(logins.includes('kody-w'), 'kody-w not in members.json');
  assert(logins.includes('rappter1'), 'rappter1 not in members.json');
  const founder = m.members.find(x => x.role === 'founder');
  assert(founder && founder.github_login === 'kody-w', 'kody-w should be the founder');
});

await test('public seed has NO members.json (no leak of roster)', () => {
  assert(!exists(path.join(PUBLIC_SEED, 'members.json')),
    'members.json should not be in public seed');
});

await test('public seed has .nojekyll for GitHub Pages dot-paths', () => {
  assert(exists(path.join(PUBLIC_SEED, '.nojekyll')), '.nojekyll missing');
});

await test('public gate index.html references the private companion via neighborhood.json fetch', () => {
  const html = fs.readFileSync(path.join(PUBLIC_SEED, 'index.html'), 'utf8');
  assert(html.includes('./neighborhood.json'), 'index.html should fetch neighborhood.json client-side');
  assert(html.includes('private_companion'), 'index.html should reference private_companion');
  assert(html.includes('Microsoft SE Team'), 'index.html should display the neighborhood name');
});

await test('public facets explicitly scope member_roster as neighborhood-only', () => {
  const f = readJSON(path.join(PUBLIC_SEED, 'facets.json'));
  const roster = (f.public_facets || []).find(x => x.name === 'member_roster');
  assert(roster, 'member_roster facet missing');
  assert(roster.scope === 'neighborhood', `roster scope leaked to ${roster.scope} (must be 'neighborhood')`);
});

await test('private decisions log carries the v1 split rationale', () => {
  const decisionFile = path.join(PRIVATE_SEED, 'state', 'decisions', '0001-public-gate-private-workflow.md');
  assert(exists(decisionFile), 'decision 0001 missing');
  const md = fs.readFileSync(decisionFile, 'utf8');
  assert(md.includes('Public gate / private workflow split'), 'decision 0001 title drifted');
});

await test('membership organ exists and exports name="neighborhoods"', () => {
  const organ = path.join(ROOT, 'rapp_brainstem', 'utils', 'organs', 'neighborhood_membership_organ.py');
  assert(exists(organ), 'organ file missing');
  const src = fs.readFileSync(organ, 'utf8');
  assert(src.includes('name = "neighborhoods"'), 'organ name must be "neighborhoods" (plural)');
  assert(src.includes('def handle('), 'organ must export handle()');
});

await test('membership organ supports file:// local mode', () => {
  const organ = path.join(ROOT, 'rapp_brainstem', 'utils', 'organs', 'neighborhood_membership_organ.py');
  const src = fs.readFileSync(organ, 'utf8');
  assert(src.includes('_local_path_from_url'), 'organ must parse file:// URLs');
  assert(src.includes('_join_local'), 'organ must have local-mode join handler');
  assert(src.includes('"mode": "local"'), 'local-mode response must include mode=local');
});

// --- New seeds (local-only-test, public-art-collective, private-workspace-template) ---

const LOCAL_TEST_SEED   = path.join(ROOT, 'installer', 'neighborhood-seeds', 'local-only-test');
const PUBLIC_ART_SEED   = path.join(ROOT, 'installer', 'neighborhood-seeds', 'public-art-collective');
const PRIVATE_WS_SEED   = path.join(ROOT, 'installer', 'neighborhood-seeds', 'private-workspace-template');

await test('local-only-test seed has visibility=public + null github', () => {
  const n = readJSON(path.join(LOCAL_TEST_SEED, 'neighborhood.json'));
  assert(n.schema === 'rapp-neighborhood/1.0', `schema: ${n.schema}`);
  assert(n.visibility === 'public', `visibility: ${n.visibility}`);
  assert(n.github === null, 'local-only seed must not declare a github repo');
  assert(n.private_companion === null, 'local-only seed must not declare a private companion');
});

await test('local-only-test seed ships a diagnostic ping agent', () => {
  const ping = path.join(LOCAL_TEST_SEED, 'agents', 'local_test_ping_agent.py');
  assert(exists(ping), 'local_test_ping_agent.py must exist');
});

await test('public-art-collective seed has visibility=public + null companion', () => {
  const n = readJSON(path.join(PUBLIC_ART_SEED, 'neighborhood.json'));
  assert(n.schema === 'rapp-neighborhood/1.0', `schema: ${n.schema}`);
  assert(n.visibility === 'public', `visibility: ${n.visibility}`);
  assert(n.private_companion === null, 'public neighborhood must have null private_companion');
  assert(n.contribution_policy && n.contribution_policy.submit_via === 'pull_request',
    'public-art must declare PR-based submission policy');
  assert(n.contribution_policy.license.startsWith('CC0'), 'public-art must declare CC0 license');
});

await test('public-art-collective ships the four collective agents', () => {
  const dir = path.join(PUBLIC_ART_SEED, 'agents');
  const files = fs.readdirSync(dir).filter(f => f.endsWith('_agent.py') && f !== 'basic_agent.py').sort();
  const expected = ['art_curate_agent.py', 'art_remix_agent.py', 'art_submit_agent.py', 'art_vote_agent.py'];
  assert(JSON.stringify(files) === JSON.stringify(expected),
    `expected ${JSON.stringify(expected)}, got ${JSON.stringify(files)}`);
});

await test('public-art-collective has submissions/index.json bootstrap', () => {
  const idx = readJSON(path.join(PUBLIC_ART_SEED, 'submissions', 'index.json'));
  assert(idx.schema === 'rapp-art-submissions-index/1.0', `submissions schema: ${idx.schema}`);
  assert(Array.isArray(idx.submissions), 'submissions must be array');
});

await test('private-workspace-template has visibility=private-workspace + null gate', () => {
  const n = readJSON(path.join(PRIVATE_WS_SEED, 'neighborhood.json'));
  assert(n.visibility === 'private-workspace', `visibility: ${n.visibility}`);
  assert(n.gate_repo === null, 'private-workspace must have null gate_repo');
  assert(n.kind === 'workspace', `kind: ${n.kind}`);
  assert(n.membership_policy && n.membership_policy.join_path === 'out_of_band',
    'private-workspace join_path must be out_of_band (no public Issue path)');
});

await test('private-workspace-template ships the four workspace agents', () => {
  const dir = path.join(PRIVATE_WS_SEED, 'agents');
  const files = fs.readdirSync(dir).filter(f => f.endsWith('_agent.py') && f !== 'basic_agent.py').sort();
  const expected = ['workspace_decision_agent.py', 'workspace_inbox_agent.py', 'workspace_init_agent.py', 'workspace_invite_agent.py'];
  assert(JSON.stringify(files) === JSON.stringify(expected),
    `expected ${JSON.stringify(expected)}, got ${JSON.stringify(files)}`);
});

await test('private-workspace-template has state subdirs (decisions, runbooks, inbox)', () => {
  for (const d of ['decisions', 'runbooks', 'inbox']) {
    assert(exists(path.join(PRIVATE_WS_SEED, 'state', d, '.gitkeep')),
      `state/${d}/.gitkeep missing`);
  }
});

await test('all three new seeds carry distinct neighborhood_rappids', () => {
  const a = readJSON(path.join(LOCAL_TEST_SEED, 'neighborhood.json')).neighborhood_rappid;
  const b = readJSON(path.join(PUBLIC_ART_SEED, 'neighborhood.json')).neighborhood_rappid;
  const c = readJSON(path.join(PRIVATE_WS_SEED, 'neighborhood.json')).neighborhood_rappid;
  assert(a && b && c, 'all rappids must be present');
  assert(a !== b && b !== c && a !== c, `rappids must be distinct (got ${a}, ${b}, ${c})`);
});

await test('master plan exists at repo root and references the one-liner', () => {
  const mp = path.join(ROOT, 'MASTER_PLAN.md');
  assert(exists(mp), 'MASTER_PLAN.md must exist at repo root');
  const src = fs.readFileSync(mp, 'utf8');
  assert(src.includes("Use everyone else's hardware to run the network"),
    'master plan must carry the one-liner');
  assert(src.includes('Master Plan, Part 1'), 'must have Part 1');
  assert(src.includes('Master Plan, Part Deux'), 'must have Part Deux');
});

await test('all four scenario shell scripts exist + are executable', () => {
  for (const name of ['01-local-on-device.sh', '02-cross-device.sh', '03-public-art.sh', '04-private-workspace.sh', '_lib.sh']) {
    const p = path.join(ROOT, 'tests', 'scenarios', name);
    assert(exists(p), `tests/scenarios/${name} missing`);
    const stat = fs.statSync(p);
    if (name !== '_lib.sh') {
      assert((stat.mode & 0o111) !== 0, `tests/scenarios/${name} must be executable`);
    }
  }
});

console.log(`\n  ${pass} passing, ${fail} failing\n`);
if (fail) {
  for (const f of failures) {
    console.error(`  - ${f.name}: ${f.err.message}`);
  }
  process.exit(1);
}
