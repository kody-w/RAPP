#!/usr/bin/env node
// The RAPP extension's unit tests without a full build, as CI runs them on macOS, Linux and Windows. It takes
// from the pinned fork only what the extension compiles against (the vscode API typings and the extensions'
// TypeScript settings), each checked against its digest here, installs the fork's own TypeScript and Node
// typings from a lockfile with their registry integrity hashes, compiles the extension with the compiler the
// fork's build compiles extensions with, and runs its tests.
// Everything goes under .build/extension-tests (or BRAINSTEM_BUILD_DIR). A pin bump changes the digests below:
// the script names each file that no longer matches.
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const APP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const BUILD = path.resolve(process.env.BRAINSTEM_BUILD_DIR || path.join(APP, '.build'));
const WORK = path.join(BUILD, 'extension-tests');
const PIN = JSON.parse(fs.readFileSync(path.join(APP, 'UPSTREAM.json'), 'utf8'));

// What the extension's tsconfig includes from the fork at the pinned commit, and the host's own JSON reader the
// tests hold the app's reading of workspace files to, by SHA-256.
const FORK_FILES = {
	'src/vscode-dts/vscode.d.ts': '4624902099d3eeb466fbb2422c09690143120e94a4cb70047c41f92058eae889',
	'src/vscode-dts/vscode.proposed.workspaceTrust.d.ts': 'fd7ba3f9225f716bb23618bbbdec99185c4002e46116c6c14bc1f2f0d54bd9e3',
	'extensions/tsconfig.base.json': 'f3df7bb184ba02e97c8af11c32038aba10a5481efad2d36d60bb31303059e81a',
	'src/vs/base/common/json.ts': 'd2ecdd688103b1997629bb2a65256186a51cf860f527397a611b9025f32d5954',
};
// The fork's own compiler and Node typings, from its package-lock.json at the pin: its build compiles extensions
// with TypeScript 7.0.2 (build/lib/tsgo.ts, the @typescript/native alias), a launcher plus one native binary
// per platform, and @types/node 24.12.4. Each with the integrity npm checks its tarball against.
const TS = '7.0.2';
const TS_BINARIES = {
	'aix-ppc64': 'sha512-MTKKkWB7p/0E9xi1d1tHtZ5PiLkGEMIq88pK2CubZjOsLtYTLqhgIgi6zepFa+9GHZ6h05NMCkQxGKiPXMxXtQ==',
	'darwin-arm64': 'sha512-gowzar9MwS/aRWp6f3a4KUqzRjAZjOsmGNCM6LcTgXum+dBfgsBVMN+AgvOCCbguXyick6LJhpBszxMebJ8syA==',
	'darwin-x64': 'sha512-SZ9xZInqApNlNGc9s0W1VSsktYSOe9cFqNOIqmN1Gs8SmkjKZYFt017G4VwPxASInODuAdbTW7sXiFUf893RgA==',
	'freebsd-arm64': 'sha512-W5NH4y/J0plIIS5b2xvTEkU7JFxyqdMAOgf+Ilhl0vHQXKO5dZoxd+C/jEtq56c4F3wk71RB4BMRQ2XdI+bwYQ==',
	'freebsd-x64': 'sha512-UMGDx5sTpzNw3WiPebH7l90IWfJggEd+egHt/q6p7/Cm3zqoV7VxkGXt+3DxPIw8CcmvAB0j3sVVfbhX+M4Tpw==',
	'linux-arm': 'sha512-gffT3xPz9sR7j/YJExkyPntrI0P2EP9XbOyWzth2/Gs0RstK+90RBcO0ncXoXy/beYll1SXw846Nf2zdnEz0QQ==',
	'linux-arm64': 'sha512-Qh4eU4/y3yDjnfjjyPYihMj5/ODIlmt+Bzu17OI+fiSRDW57QmU5SiN63exPRNJPKUzcc1INa1NXdrJ+MqHjUQ==',
	'linux-loong64': 'sha512-uEHck9i8hoAzXPiYRib1O7miOnz23SxIeVl6F4LXox+qov1K35jHcEW6VHKvZI+pyvl7fZEP4MCU5LYvIq1GuQ==',
	'linux-mips64el': 'sha512-R4KvAMnE43W5Qeqb0Ly56O3mWMWIAgsMyz36DCaycd5nbg/9kzm0liw3JocfRqyJY0KPmzFjbswozXyW0DnIYA==',
	'linux-ppc64': 'sha512-DORx5b3sd/4S7eayxm4FQv+A7CrkUIGRaHiwI8oiHTAI1fAPWhF4J0vAlkC8biAlHSVVwxMQ3tjZ2/DVbnQiiA==',
	'linux-riscv64': 'sha512-wf0jqEDOjrPRnKwYRyyJDRo11KMbvMFrU+q4zqKyChODBzvlkbhNQfKvLxQCcwTpdDaXSHZTVuh0JoCrKCUMHQ==',
	'linux-s390x': 'sha512-IkwJc3L7yhytWd/ewjyxNDfOmswCm9GWMJT/ue/dU4aZNbwZeYAetq42VyLmsmSjvoX7z74X6ZaYCtzAr0EuGw==',
	'linux-x64': 'sha512-EYdf2cNg7rgCWJnxCdJ+F3V39O8ihb37eHAu1LK8oAFizgTQbPOK7zHHXbPt8rX24COqODXeI3sIf0fCXG7H/A==',
	'netbsd-arm64': 'sha512-+polYF4MF04aPpO5FTkHran9yUQDSXqy5GiSDKpsll5jy3l3+g9QLhpf39T+ePtefhXLOGrLl0QIjkQP6VnelA==',
	'netbsd-x64': 'sha512-8YIT0EHM/3dq10ZOVF/A7pc/YSMtbcecct4rWtexrnSCHOPcpC2KTLXfTCR6vDpnSiY12heNb1GiN/wu+T/FyA==',
	'openbsd-arm64': 'sha512-APT8+ClYnuYm1u9+kgGXoMj2VzWzcymwh2gNSQVySHfkRDGOTVkoWLjCmOQSaO+PoqQ57B0flRp9SA+7GnnkzQ==',
	'openbsd-x64': 'sha512-yX7s+Q0Dln0Dt9tEzZsAjXXR/+ytBM7AlglaqyeMPxQszJ1JhlJdZ6jLA+IzldHtflX81em7lDao1xXu+aRRkg==',
	'sunos-x64': 'sha512-dLJDGaLZ1D4HPQn62u1n8mBDkJREwMsAkCdkwd4Ieqw+x3TUyTsqY0YiBCtE6H6OzzgGk3iuZ3vFWRS+E8/d1g==',
	'win32-arm64': 'sha512-Gyl1Vy6OsWesLzmq+EP0Fb7b4Nid5232AvcA2SFcdYreldpNtYFFofPjnt62y9hQy7VTaZp65ICJjuAQRaVcIQ==',
	'win32-x64': 'sha512-0BQ3HkAHHlKLSp1qRvf3SUhGpGsDuhB/jgFw75guyqbxJqEaS0Cw/VFO8i2nHglJUzQCRtMMR/IBAKE3ETMC4g==',
};
const PACKAGES = {
	typescript: { version: TS, integrity: 'sha512-8FYau96o3NKOhbjKi/qNvG/W5jhzxkbdm5sj9AbZ/5T5sWqn3hJgLfGx27sRKZWTvyzCP8dLRBTf5tBTSRVUNA==', optionalDependencies: Object.fromEntries(Object.keys(TS_BINARIES).map(p => [`@typescript/typescript-${p}`, TS])) },
	'@types/node': { version: '24.12.4', integrity: 'sha512-GUUEShf+PBCGW2KaXwcIt3Yk+e3pkKwWKb9GSyM9WQVE+ep2jzmHdGsHzu4wgcZy5fN9FBdVzjpBQsYlpfpgLA==', dependencies: { 'undici-types': '~7.16.0' } },
	'undici-types': { version: '7.16.0', integrity: 'sha512-Zz+aZWSj8LE6zoxD+xrjh4VfkIG8Ya6LvYkZqtUQGJPZjYl53ypCaUwWqo7eI0x66KBGeRo+mlBEkMSeSZ38Nw==' },
	...Object.fromEntries(Object.entries(TS_BINARIES).map(([platform, integrity]) => {
		const [os, cpu] = platform.split('-');
		return [`@typescript/typescript-${platform}`, { version: TS, integrity, optional: true, os: [os], cpu: [cpu] }];
	})),
};
// The extension as the build copies it into the fork: its sources, Python helper, media and manifest.
const EXTENSION_PARTS = ['package.json', 'tsconfig.json', 'src', 'python', 'media'];

function fail(message) {
	console.error(`test-extension: ${message}`);
	process.exit(1);
}

function run(file, args, options = {}) {
	const result = spawnSync(file, args, { stdio: 'inherit', shell: false, ...options });
	if (result.error) {
		fail(`${file} did not start: ${result.error.message}`);
	}
	return result.status ?? 1;
}

const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');

// A local checkout of the fork at the pin (a full build's) when there is one, else the fork on GitHub at the pin.
async function forkFile(name) {
	const local = path.join(BUILD, 'vscode', name);
	if (fs.existsSync(local)) {
		const bytes = fs.readFileSync(local);
		if (sha256(bytes) === FORK_FILES[name]) {
			return bytes;
		}
	}
	const match = /^https:\/\/github\.com\/([\w.-]+)\/([\w.-]+?)(?:\.git)?\/?$/.exec(PIN.fork);
	if (!match || !/^[0-9a-f]{40}$/.test(PIN.commit)) {
		fail('UPSTREAM.json names no GitHub fork and full commit');
	}
	const url = `https://raw.githubusercontent.com/${match[1]}/${match[2]}/${PIN.commit}/${name}`;
	for (let attempt = 1; ; attempt++) {
		try {
			const reply = await fetch(url);
			if (!reply.ok) {
				throw new Error(`HTTP ${reply.status}`);
			}
			return Buffer.from(await reply.arrayBuffer());
		} catch (error) {
			if (attempt === 3) {
				fail(`could not fetch ${url}: ${error.message}`);
			}
			await new Promise(resolve => setTimeout(resolve, 2000 * attempt));
		}
	}
}

function lockfile() {
	const devDependencies = { typescript: PACKAGES.typescript.version, '@types/node': PACKAGES['@types/node'].version };
	const packages = { '': { name: 'brainstem-app-extension-tests', devDependencies } };
	for (const [name, { version, integrity, ...rest }] of Object.entries(PACKAGES)) {
		packages[`node_modules/${name}`] = {
			version,
			resolved: `https://registry.npmjs.org/${name}/-/${name.split('/').pop()}-${version}.tgz`,
			integrity,
			dev: true,
			...rest,
		};
	}
	return {
		manifest: { name: 'brainstem-app-extension-tests', private: true, devDependencies },
		lock: { name: 'brainstem-app-extension-tests', lockfileVersion: 3, requires: true, packages },
	};
}

const major = Number(process.versions.node.split('.')[0]);
if (major < 20) {
	fail(`Node ${process.versions.node} is too old; the tests need Node 20 or newer`);
}
console.log(`node ${process.versions.node} on ${process.platform}-${process.arch}; fork ${PIN.fork} at ${PIN.commit}`);

// The tree the extension's tsconfig expects: the fork's typings two folders up, its base settings one up.
fs.rmSync(path.join(WORK, 'extensions'), { recursive: true, force: true });
fs.rmSync(path.join(WORK, 'src'), { recursive: true, force: true });
for (const name of Object.keys(FORK_FILES)) {
	const bytes = await forkFile(name);
	if (sha256(bytes) !== FORK_FILES[name]) {
		fail(`${name} at ${PIN.commit} is not the file this script pins (sha256 ${sha256(bytes)}); update FORK_FILES for a new pin`);
	}
	fs.mkdirSync(path.dirname(path.join(WORK, name)), { recursive: true });
	fs.writeFileSync(path.join(WORK, name), bytes);
}
const extension = path.join(WORK, 'extensions', 'rapp');
for (const part of EXTENSION_PARTS) {
	fs.cpSync(path.join(APP, 'extensions', 'rapp', part), path.join(extension, part), { recursive: true });
}

const { manifest, lock } = lockfile();
const stamp = path.join(WORK, 'node_modules', '.brainstem-tests');
const want = sha256(JSON.stringify(lock));
if (!fs.existsSync(stamp) || fs.readFileSync(stamp, 'utf8') !== want) {
	fs.writeFileSync(path.join(WORK, 'package.json'), JSON.stringify(manifest, null, '\t') + '\n');
	fs.writeFileSync(path.join(WORK, 'package-lock.json'), JSON.stringify(lock, null, '\t') + '\n');
	const npmArgs = ['ci', '--ignore-scripts', '--no-audit', '--no-fund', '--cache', path.join(BUILD, 'npm-cache')];
	// npm.cmd is a batch file, which Node runs only through a shell: one command line, every part of it the script's own.
	const npmCi = () => process.platform === 'win32'
		? run(['npm.cmd', ...npmArgs.map(arg => `"${arg}"`)].join(' '), [], { cwd: WORK, shell: true })
		: run('npm', npmArgs, { cwd: WORK });
	// Once more after a pause: a registry download can drop on a busy runner.
	if (npmCi() !== 0 && (await new Promise(resolve => setTimeout(resolve, 5000)), npmCi()) !== 0) {
		fail('npm ci failed');
	}
	fs.writeFileSync(stamp, want);
}

console.log(`compile the RAPP extension (TypeScript ${TS})`);
if (run(process.execPath, [path.join(WORK, 'node_modules', 'typescript', 'bin', 'tsc'), '--project', path.join(extension, 'tsconfig.json'), '--pretty', 'false']) !== 0) {
	fail('the extension did not compile');
}
// The host's JSON reader, compiled on its own, for the test that holds the app's reading of workspace files to it.
const hostJson = path.join(WORK, 'host-json');
fs.rmSync(hostJson, { recursive: true, force: true });
if (run(process.execPath, [path.join(WORK, 'node_modules', 'typescript', 'bin', 'tsc'), path.join(WORK, 'src', 'vs', 'base', 'common', 'json.ts'), '--outDir', hostJson, '--module', 'commonjs', '--target', 'es2022', '--preserveConstEnums', '--skipLibCheck', '--pretty', 'false']) !== 0) {
	fail('the host\'s JSON reader did not compile');
}

const tests = fs.readdirSync(path.join(extension, 'out', 'test')).filter(name => name.endsWith('.test.js')).sort().map(name => path.join(extension, 'out', 'test', name));
const tmp = path.join(WORK, 'test-tmp');
fs.rmSync(tmp, { recursive: true, force: true });
fs.mkdirSync(tmp, { recursive: true });
const python = process.env.BRAINSTEM_TEST_PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
console.log(`run ${tests.length} test files with ${python}`);
process.exit(run(process.execPath, ['--test', ...tests], { env: { ...process.env, BRAINSTEM_TEST_TMP: tmp, BRAINSTEM_TEST_PYTHON: python, BRAINSTEM_TEST_HOST_JSON: path.join(hostJson, 'json.js') } }));
