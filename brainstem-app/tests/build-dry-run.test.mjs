// The build script's dry run against a local stand-in for the fork: it verifies the pin, refuses a
// mismatch, and applies the overlay (product merge, edits, removals, the built-in extension, branding).
// build.sh runs it on macOS and Linux, build.ps1 on Windows.
import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { after, test } from 'node:test';
import { APP_DIR, loadOverlay, readJson, validateProduct } from '../scripts/apply-overlay.mjs';

const TMP = path.resolve(process.env.BRAINSTEM_TEST_TMP || path.join(APP_DIR, '.build', 'test-tmp'));
const ROOT = path.join(TMP, `dry-run-${process.pid}`);
const FORK = path.join(ROOT, 'fork');
const TAG = '1.139.0-fixture';
const GIT_ENV = { ...process.env, GIT_CONFIG_GLOBAL: '/dev/null', GIT_CONFIG_NOSYSTEM: '1', GIT_TERMINAL_PROMPT: '0' };
const overlay = loadOverlay();

function git(cwd, ...args) {
	return execFileSync('git', ['-c', 'user.name=brainstem-fixture', '-c', 'user.email=brainstem-fixture@users.noreply.github.com',
		'-c', 'commit.gpgsign=false', '-c', 'tag.gpgsign=false', ...args], { cwd, env: GIT_ENV, encoding: 'utf8' }).trim();
}

function put(file, text) {
	fs.mkdirSync(path.dirname(file), { recursive: true });
	fs.appendFileSync(file, text);
}

// A tiny repository shaped like the fork where the overlay touches it: each edit's anchor, a product.json
// in upstream's shape, the in-tree AI extension, the Simple Browser the overlay keeps and a .nvmrc.
function makeFork() {
	fs.rmSync(ROOT, { recursive: true, force: true });
	for (const edit of overlay.edits) {
		put(path.join(FORK, edit.file), `// before\n${edit.find}// after\n`);
	}
	fs.copyFileSync(path.join(APP_DIR, 'tests', 'fixtures', 'upstream-product.json'), path.join(FORK, 'product.json'));
	put(path.join(FORK, 'extensions', 'copilot', 'package.json'), '{"name": "copilot-chat"}\n');
	put(path.join(FORK, 'extensions', 'simple-browser', 'package.json'), '{"name": "simple-browser"}\n');
	put(path.join(FORK, '.nvmrc'), `${process.versions.node}\n`);
	git(FORK, 'init', '--quiet', '--initial-branch=main');
	git(FORK, 'add', '-A');
	git(FORK, 'commit', '--quiet', '-m', 'fixture');
	git(FORK, 'tag', TAG);
	return git(FORK, 'rev-parse', 'HEAD');
}

function pinFile(name, commit) {
	const file = path.join(ROOT, name);
	fs.writeFileSync(file, JSON.stringify({ fork: FORK, upstream: 'fixture/vscode', tag: TAG, commit }, null, 2) + '\n');
	return file;
}

// build.sh on macOS and Linux; on Windows its twin, build.ps1, which takes the same switches in its own spelling
// (BRAINSTEM_TEST_BUILD_PS1=1 runs build.ps1 anywhere PowerShell is).
const PS1 = process.platform === 'win32' || process.env.BRAINSTEM_TEST_BUILD_PS1 === '1';
function dryRun(pin, buildDir) {
	return PS1
		? spawnSync('pwsh', ['-NoLogo', '-NoProfile', '-NonInteractive', '-File', path.join(APP_DIR, 'scripts', 'build.ps1'), '-DryRun', '-UpstreamJson', pin, '-BuildDir', buildDir],
			{ env: GIT_ENV, encoding: 'utf8' })
		: spawnSync('bash', [path.join(APP_DIR, 'scripts', 'build.sh'), '--dry-run', '--upstream-json', pin, '--build-dir', buildDir],
			{ env: GIT_ENV, encoding: 'utf8' });
}

const commit = makeFork();

after(() => fs.rmSync(ROOT, { recursive: true, force: true }));

test('verifies the pinned commit and applies the overlay', () => {
	const buildDir = path.join(ROOT, 'build');
	const result = dryRun(pinFile('UPSTREAM.json', commit), buildDir);
	assert.equal(result.status, 0, result.stdout + result.stderr);
	assert.match(result.stdout, new RegExp(`pinned commit verified: ${commit}`));
	assert.match(result.stdout, /Dry run complete/);
	const checkout = path.join(buildDir, 'vscode');
	assert.equal(git(checkout, 'rev-parse', 'HEAD'), commit);

	const product = readJson(path.join(checkout, 'product.json'));
	assert.deepEqual(validateProduct(product, overlay.product), []);
	assert.equal(product.nameLong, 'Brainstem');
	assert.equal(product.applicationName, 'brainstem-app');
	assert.ok(!('extensionsGallery' in product) && !('enableTelemetry' in product));

	for (const edit of overlay.edits) {
		const text = fs.readFileSync(path.join(checkout, edit.file), 'utf8');
		assert.ok(text.includes(edit.replace), `${edit.file}: ${edit.why}`);
	}
	assert.ok(!fs.existsSync(path.join(checkout, 'extensions', 'copilot')));
	assert.ok(fs.existsSync(path.join(checkout, 'extensions', 'simple-browser', 'package.json')));
	assert.ok(fs.existsSync(path.join(checkout, 'extensions', 'rapp', 'package.json')));
	assert.ok(!fs.existsSync(path.join(checkout, 'extensions', 'rapp', 'out')));
	for (const file of Object.keys(overlay.branding.generated)) {
		assert.ok(fs.statSync(path.join(checkout, file)).size > 0, file);
	}
	const report = readJson(path.join(buildDir, 'overlay-report.json'));
	assert.equal(report.commit, commit);
	assert.ok(report.product.removed.includes('extensionsGallery'));
	assert.deepEqual(report.kept_paths, ['extensions/simple-browser']);
});

test('a second dry run on the same checkout gives the same result', () => {
	const buildDir = path.join(ROOT, 'build');
	const result = dryRun(pinFile('UPSTREAM.json', commit), buildDir);
	assert.equal(result.status, 0, result.stdout + result.stderr);
	assert.equal(git(path.join(buildDir, 'vscode'), 'status', '--porcelain', '--', 'product.json').slice(0, 2).trim(), 'M');
});

test('refuses when the tag does not resolve to the pinned commit', () => {
	const result = dryRun(pinFile('WRONG.json', 'a'.repeat(40)), path.join(ROOT, 'build-wrong'));
	assert.notEqual(result.status, 0);
	assert.match(result.stderr, /refusing: .* pins a{40}/);
	assert.ok(!fs.existsSync(path.join(ROOT, 'build-wrong', 'overlay-report.json')));
});

test('refuses a pin that is not a full commit id', () => {
	const result = dryRun(pinFile('SHORT.json', commit.slice(0, 12)), path.join(ROOT, 'build-short'));
	assert.notEqual(result.status, 0);
	assert.match(result.stderr, /full 40-character commit id/);
});

test('refuses a checkout that came from somewhere else', () => {
	const buildDir = path.join(ROOT, 'build-foreign');
	fs.mkdirSync(buildDir, { recursive: true });
	git(ROOT, 'clone', '--quiet', FORK, path.join(buildDir, 'vscode'));
	git(path.join(buildDir, 'vscode'), 'remote', 'set-url', 'origin', path.join(ROOT, 'elsewhere'));
	const result = dryRun(pinFile('UPSTREAM.json', commit), buildDir);
	assert.notEqual(result.status, 0);
	assert.match(result.stderr, /was cloned from .*elsewhere/);
});
