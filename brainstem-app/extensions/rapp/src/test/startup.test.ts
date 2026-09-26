// Unit tests for where the global Brainstem folder is found, how it is started and what a window does when it
// starts, against synthetic folders built under the test temp folder (BRAINSTEM_TEST_TMP, or .test-tmp here).
import * as assert from 'assert';
import { spawnSync } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import * as url from 'url';
import { after, describe, test } from 'node:test';
import { createWhole, dataLocalPath, dataUri, defaultBrainstemFolder, folderGlobs, isOwnWorkspaceFile, isRappWorkspaceWindow, isRunning, ownershipRefusal, readShownNote, readTolerant, resolveAgentsFolder, resolveBrainstemFolder, resolveDataFolder, rootsOf, SHOWN_GRACE_MS, shownElsewhere, START_STATUS_ENV, startCommand, startFailure, startupAction, StartupInputs, WORKSPACE_FILE, workspaceFileText, workspaceFileUpdate, workspaceKey, WORKSPACES_FOLDER, writeShownNote, writeWhole } from '../startup';

const TMP = path.resolve(process.env.BRAINSTEM_TEST_TMP || path.join(__dirname, '..', '..', '.test-tmp'));
const ROOT = path.join(TMP, `startup-fixture-${process.pid}`);
const HOME = path.join(ROOT, 'home');
const DEFAULT = defaultBrainstemFolder(HOME);
const SET = path.join(ROOT, 'chosen', 'rapp_brainstem');
const RUNNING = path.join(ROOT, 'running', 'rapp_brainstem');
const NO_PY = path.join(ROOT, 'no-py', 'rapp_brainstem');
const HIVES = path.join(HOME, 'Hives');
const IN_HIVE = path.join(HIVES, 'team-notes', 'shared', 'rapp_brainstem');
const REFERENCE = path.join(ROOT, 'notes', 'old-vault');
const OTHER = path.join(ROOT, 'some-project');
const FORBIDDEN = [HIVES, REFERENCE];
// Real folders are judged by this system's own rules; made-up paths name the platform they are for.
const PLATFORM = process.platform;
const real = (folder: string) => fs.realpathSync.native(folder);

function write(file: string, text = ''): void {
	fs.mkdirSync(path.dirname(file), { recursive: true });
	fs.writeFileSync(file, text);
}

function brainstemAt(folder: string, scripts = true): void {
	write(path.join(folder, 'brainstem.py'), 'raise SystemExit("never run by the tests")\n');
	if (scripts) {
		write(path.join(folder, 'start.sh'), '#!/bin/bash\nexit 1\n');
		write(path.join(folder, 'start.ps1'), 'exit 1\n');
	}
}

fs.rmSync(ROOT, { recursive: true, force: true });
[DEFAULT, SET, RUNNING, IN_HIVE].forEach(folder => brainstemAt(folder));
brainstemAt(path.join(REFERENCE, 'rapp_brainstem'));
write(path.join(NO_PY, 'start.sh'));
write(path.join(ROOT, 'a-file'));
fs.mkdirSync(OTHER, { recursive: true });
try {
	fs.symlinkSync(DEFAULT, path.join(ROOT, 'linked-brainstem'));
} catch {
	// Symlinks need privileges on some systems; the link case then just resolves the path itself.
}

after(() => fs.rmSync(ROOT, { recursive: true, force: true }));

const resolve = (setting: string, healthDir?: string, home = HOME) => resolveBrainstemFolder({ setting, healthDir, home, forbidden: FORBIDDEN, platform: PLATFORM });

describe('Global Brainstem folder', () => {
	test('a folder only /health reports is the setting\'s or the default when it is that folder, and is then named as that one', () => {
		const uid = process.getuid?.();
		const reported = (healthDir: string, setting = '') => resolveBrainstemFolder({ setting, healthDir, home: HOME, forbidden: FORBIDDEN, platform: PLATFORM, uid });
		fs.chmodSync(DEFAULT, 0o777);
		try {
			assert.deepStrictEqual([reported(DEFAULT).folder, reported(DEFAULT).source], [DEFAULT, 'default'], 'the default itself is known, writable or not');
			assert.deepStrictEqual([reported(DEFAULT, SET).folder, reported(DEFAULT, SET).source], [SET, 'setting'], 'the setting comes first');
		} finally {
			fs.chmodSync(DEFAULT, 0o755);
		}
		const link = path.join(ROOT, 'linked-brainstem');
		if (fs.existsSync(link)) {
			assert.deepStrictEqual([reported(link).folder, reported(link).source], [DEFAULT, 'default'], 'a link to the default is the default, by its own path');
		}
	});

	test('any other folder /health reports is taken as its real path, when it is yours and neither it nor what holds it can be changed by others', () => {
		const uid = process.getuid?.();
		const reported = (healthDir: string) => resolveBrainstemFolder({ setting: '', healthDir, home: HOME, forbidden: FORBIDDEN, platform: PLATFORM, uid });
		if (uid === undefined) {
			assert.deepStrictEqual(reported(RUNNING).refused, [{ source: 'health', reason: 'not the setting\'s or the default folder' }], 'Windows has no such mode bits');
			return;
		}
		assert.deepStrictEqual([reported(RUNNING).folder, reported(RUNNING).source], [real(RUNNING), 'health']);
		const open = path.join(ROOT, 'shared-place');
		const shared = path.join(open, 'rapp_brainstem');
		brainstemAt(shared);
		const link = path.join(ROOT, 'shared-link');
		try {
			fs.chmodSync(shared, 0o777);
			assert.deepStrictEqual([reported(shared).folder, reported(shared).refused], [DEFAULT, [{ source: 'health', reason: 'writable by others' }]]);
			fs.chmodSync(shared, 0o755);
			fs.chmodSync(open, 0o777);
			assert.deepStrictEqual(reported(shared).refused, [{ source: 'health', reason: 'inside a folder others can change' }], 'anyone could swap it for another');
			fs.chmodSync(open, 0o1777);
			assert.deepStrictEqual([reported(shared).folder, reported(shared).source], [real(shared), 'health'], 'a sticky folder, as /tmp is, keeps what is yours yours');
			fs.chmodSync(open, 0o755);
			fs.symlinkSync(shared, link);
			assert.deepStrictEqual([reported(link).folder, reported(link).source], [real(shared), 'health'], 'a link is followed once, and only its real path is kept');
		} finally {
			fs.chmodSync(open, 0o755);
			fs.chmodSync(shared, 0o755);
			// A link to a folder is unlinked: Node 25's rmSync refuses one without `recursive`.
			if (fs.lstatSync(link, { throwIfNoEntry: false })) {
				fs.unlinkSync(link);
			}
		}
	});

	test('the ownership check reads the folder, then every folder above it', () => {
		const stats = (table: Record<string, [number, number]>) => (folder: string) => {
			const [uid, mode] = table[folder] ?? [0, 0o40755];
			return { uid, mode };
		};
		const own = { '/srv/me/b': [501, 0o40755] as [number, number], '/srv/me': [501, 0o40755] as [number, number] };
		assert.deepStrictEqual([
			ownershipRefusal('/srv/me/b', 501, 'darwin', stats(own)),
			ownershipRefusal('/srv/me/b', 501, 'linux', stats({ ...own, '/srv/me/b': [501, 0o40775] })),
			ownershipRefusal('/srv/me/b', 501, 'darwin', stats({ ...own, '/srv/me/b': [501, 0o40757] })),
			ownershipRefusal('/srv/me/b', 501, 'darwin', stats({ ...own, '/srv/me/b': [0, 0o40755] })),
			ownershipRefusal('/srv/me/b', 501, 'darwin', stats({ ...own, '/srv/me': [502, 0o40755] })),
			ownershipRefusal('/srv/me/b', 501, 'darwin', stats({ ...own, '/srv': [0, 0o40777] })),
			ownershipRefusal('/srv/me/b', 501, 'darwin', stats({ ...own, '/srv': [0, 0o41777] })),
			ownershipRefusal('/srv/me/b', 501, 'win32', stats(own)),
			ownershipRefusal('/srv/me/b', undefined, 'darwin', stats(own)),
			ownershipRefusal('/srv/me/b', 501, 'darwin', () => { throw new Error('gone'); }),
		], [
			undefined, 'writable by others', 'writable by others', 'not owned by you', 'inside a folder someone else owns',
			'inside a folder others can change', undefined, 'not the setting\'s or the default folder', 'not the setting\'s or the default folder', 'no such folder',
		]);
	});

	test('is the setting first, then the running Brainstem\'s folder, then the installer\'s default', () => {
		const running = process.getuid ? { folder: real(RUNNING), source: 'health', refused: [] } : { folder: DEFAULT, source: 'default', refused: [{ source: 'health', reason: 'not the setting\'s or the default folder' }] };
		assert.deepStrictEqual([
			resolve(SET, RUNNING),
			resolve('', RUNNING),
			resolve('  ', undefined),
			resolve(`~/${path.relative(HOME, DEFAULT)}`, RUNNING),
		], [
			{ folder: SET, source: 'setting', refused: [] },
			running,
			{ folder: DEFAULT, source: 'default', refused: [] },
			{ folder: DEFAULT, source: 'setting', refused: [] },
		]);
	});

	test('refuses a relative path, a missing folder, a folder without brainstem.py, a non-local path, a file and a Hive', { skip: PLATFORM === 'win32' && 'these made-up paths are POSIX ones' }, () => {
		assert.deepStrictEqual([
			resolve('rapp_brainstem', 'relative/rapp_brainstem'),
			resolve(path.join(ROOT, 'gone'), NO_PY),
			resolve('\\\\server\\share\\rapp_brainstem', 'file:///rapp_brainstem'),
			resolve('//server/share/rapp_brainstem', 'http://127.0.0.1:7071'),
			resolve(path.join(ROOT, 'a-file'), IN_HIVE),
			resolve(path.join(REFERENCE, 'rapp_brainstem'), undefined, path.join(ROOT, 'nobody')),
		].map(found => [found.folder, found.source, found.refused.map(r => `${r.source}: ${r.reason}`)]), [
			[DEFAULT, 'default', ['setting: not an absolute path', 'health: not an absolute path']],
			[DEFAULT, 'default', ['setting: no such folder', 'health: has no brainstem.py']],
			[DEFAULT, 'default', ['setting: not a local path', 'health: not a local path']],
			[DEFAULT, 'default', ['setting: not a local path', 'health: not a local path']],
			[DEFAULT, 'default', ['setting: not a folder', 'health: inside a Hive or a reference']],
			[undefined, undefined, ['setting: inside a Hive or a reference', 'default: no such folder']],
		]);
	});

	test('its start script runs as a child of the terminal\'s own process, so the host asks before quitting stops it', { skip: PLATFORM === 'win32' && 'PowerShell never runs a script in its own place' }, () => {
		const folder = path.join(ROOT, 'child-start', 'rapp_brainstem');
		brainstemAt(folder, false);
		// Like the grail's start.sh, it ends by exec'ing its server, here one that says whose child it is.
		write(path.join(folder, 'start.sh'), '#!/bin/bash\nexec bash -c \'echo $PPID > parent.txt\'\n');
		const start = startCommand(folder, FORBIDDEN, PLATFORM);
		assert.ok(start);
		const run = spawnSync(start.shellPath, [...start.shellArgs], { cwd: start.cwd });
		assert.strictEqual(run.status, 0);
		const terminal = Number(fs.readFileSync(path.join(folder, 'parent.txt'), 'utf8').trim());
		assert.notStrictEqual(terminal, process.pid, 'the script took the terminal process\'s place');
		assert.ok(terminal > 0);
	});

	test('a start script that stops with an error keeps its terminal on what it printed and leaves its exit code for the app', { skip: PLATFORM === 'win32' && 'on Windows start.ps1 is the terminal\'s own script' }, () => {
		const folder = path.join(ROOT, 'failing-start', 'rapp_brainstem');
		brainstemAt(folder, false);
		const status = path.join(ROOT, 'failing-start', 'start status');
		const run = (code: number) => {
			fs.rmSync(status, { force: true });
			write(path.join(folder, 'start.sh'), `#!/bin/bash\necho the reason it stopped\nexit ${code}\n`);
			const start = startCommand(folder, FORBIDDEN, PLATFORM);
			assert.ok(start);
			// Return is pressed at once: stdin ends.
			const result = spawnSync(start.shellPath, [...start.shellArgs], { cwd: start.cwd, input: '', env: { ...process.env, [START_STATUS_ENV]: status }, encoding: 'utf8' });
			return { exit: result.status, printed: result.stdout, failure: startFailure(status) };
		};
		const failed = run(3);
		assert.deepStrictEqual([failed.exit, failed.failure], [0, 3], 'it ends only after Return, with its exit code in the file (a path with a space)');
		assert.match(failed.printed, /the reason it stopped\n\nYour Brainstem stopped with exit code 3\. What it printed is above\. Press Return to close this terminal\.\n$/);
		for (const code of [0, 130, 143]) {
			const ended = run(code);
			assert.deepStrictEqual([ended.exit, ended.failure, /Press Return/.test(ended.printed)], [0, undefined, false], `exit ${code} is a normal stop: the terminal ends quietly`);
		}
		const killed = run(137);
		assert.deepStrictEqual([killed.exit, killed.failure], [0, 137], 'a signal other than a plain stop counts as an error');
		assert.deepStrictEqual(['7\n', 'nope', '', '1234'].map(text => (fs.writeFileSync(status, text), startFailure(status))), [7, undefined, undefined, undefined]);
		assert.strictEqual(startFailure(path.join(ROOT, 'failing-start', 'missing')), undefined);
	});

	test('on Windows a full path starts with a drive', () => {
		const windows = (folder: string) => resolveBrainstemFolder({ setting: folder, home: path.join(ROOT, 'nobody'), forbidden: [], platform: 'win32' }).refused[0];
		assert.deepStrictEqual([windows('\\rapp_brainstem'), windows('C:rapp_brainstem'), windows('\\\\server\\share')], [
			{ source: 'setting', reason: 'not an absolute path' },
			{ source: 'setting', reason: 'not an absolute path' },
			{ source: 'setting', reason: 'not a local path' },
		]);
	});

	test('is started with its own start script, in its folder, only when it has one', () => {
		assert.deepStrictEqual([
			startCommand(DEFAULT, FORBIDDEN, 'darwin'),
			startCommand(DEFAULT, FORBIDDEN, 'win32'),
			startCommand(NO_PY, FORBIDDEN, 'win32'),
			startCommand(OTHER, FORBIDDEN, 'linux'),
			startCommand(IN_HIVE, FORBIDDEN, 'darwin'),
		].map(start => start && { ...start, shellArgs: start.shellArgs.map(arg => (arg.startsWith('bash ./start.sh;') ? 'bash ./start.sh; …' : arg)) }), [
			{ cwd: DEFAULT, shellPath: 'bash', shellArgs: ['-c', 'bash ./start.sh; …'] },
			{ cwd: DEFAULT, shellPath: 'powershell.exe', shellArgs: ['-ExecutionPolicy', 'Bypass', '-File', '.\\start.ps1'] },
			undefined,
			undefined,
			undefined,
		]);
	});
});

describe('RAPP Workspace folder', () => {
	const AGENTS = path.join(DEFAULT, 'agents');
	const CHOSEN = path.join(ROOT, 'chosen', 'rapp_brainstem', 'agents');
	fs.mkdirSync(AGENTS, { recursive: true });
	fs.mkdirSync(CHOSEN, { recursive: true });
	const agentsOf = (setting: string, root?: string) => resolveAgentsFolder({ setting, root, home: HOME, forbidden: FORBIDDEN, platform: PLATFORM });

	test('is the setting rapp.agentsFolder when it names a usable folder, else the Brainstem\'s own agents/, which must exist', () => {
		assert.deepStrictEqual([
			agentsOf(CHOSEN, DEFAULT),
			agentsOf('', DEFAULT),
			agentsOf(`~/${path.relative(HOME, AGENTS).split(path.sep).join('/')}`, RUNNING),
			agentsOf('relative/agents', DEFAULT),
			agentsOf(path.join(HIVES, 'team-notes'), DEFAULT),
			agentsOf('', RUNNING),
			agentsOf('', undefined),
		].map(found => [found.folder, found.source, found.refused.map(r => `${r.source}: ${r.reason}`)]), [
			[CHOSEN, 'setting', []],
			[AGENTS, 'brainstem', []],
			[AGENTS, 'setting', []],
			[AGENTS, 'brainstem', ['setting: not an absolute path']],
			[AGENTS, 'brainstem', ['setting: inside a Hive or a reference']],
			[undefined, undefined, ['default: its agents/ is missing']],
			[undefined, undefined, []],
		]);
	});

	const DATA = path.join(DEFAULT, '.brainstem_data');
	const SECRET = path.join(DEFAULT, '.brainstem_secret');
	fs.mkdirSync(path.join(DATA, 'shared_memories'), { recursive: true });
	fs.writeFileSync(SECRET, 'never read by the tests');
	const TITLE = '${dirty}${activeEditorShort}${separator}RAPP Workspace${separator}${appName}';
	const EXCLUDES = { '**/*.sqlite3*': true, '**/*cache*.json': true, '**/.brainstem_secret': true };
	const dataRoot = (data: string) => ({ name: 'Brainstem data', uri: dataUri(data) });
	// What an earlier build wrote for the data root: its plain path, kept read-only by two absolute globs.
	const legacyGlobs = (data: string) => Object.fromEntries(folderGlobs(data).map(glob => [glob, true]));
	const rootPath = (entry: { path?: string; uri?: string }) => entry.path ?? dataLocalPath(decodeURIComponent((entry.uri ?? '').replace(/^brainstem-data:\/\//, '')));

	test('opens as a workspace whose window says RAPP Workspace, with Agents and the read-only Brainstem data as its roots', () => {
		assert.deepStrictEqual(JSON.parse(workspaceFileText(AGENTS, DATA)), {
			folders: [{ name: 'Agents', path: AGENTS }, dataRoot(DATA)],
			settings: { 'window.title': TITLE, 'files.exclude': EXCLUDES },
		});
		assert.deepStrictEqual(JSON.parse(workspaceFileText(AGENTS)), { folders: [{ name: 'Agents', path: AGENTS }], settings: { 'window.title': TITLE } }, 'no data folder yet: one root');
	});

	test('the data root is a brainstem-data: URI of the folder\'s own path, which maps back to it on every system', () => {
		assert.deepStrictEqual([
			dataUri('/Volumes/Data/brainstem/src/rapp_brainstem/.brainstem_data', 'darwin'),
			dataUri('/srv/some one/#odd%/.brainstem_data', 'linux'),
			dataUri('D:\\Brainstem\\src\\rapp_brainstem\\.brainstem_data', 'win32'),
		], [
			'brainstem-data:///Volumes/Data/brainstem/src/rapp_brainstem/.brainstem_data',
			'brainstem-data:///srv/some%20one/%23odd%25/.brainstem_data',
			'brainstem-data:///D%3A/Brainstem/src/rapp_brainstem/.brainstem_data',
		]);
		assert.deepStrictEqual([
			dataLocalPath('/srv/some one/#odd%/.brainstem_data', 'linux'),
			dataLocalPath('/D:/Brainstem/.brainstem_data/shared_memories/memory.json', 'win32'),
			dataLocalPath('/D:', 'win32'),
			dataLocalPath('/share/.brainstem_data', 'win32'),
			dataLocalPath('relative/.brainstem_data', 'darwin'),
		], ['/srv/some one/#odd%/.brainstem_data', 'D:\\Brainstem\\.brainstem_data\\shared_memories\\memory.json', 'D:\\', undefined, undefined]);
	});

	test('nothing else of the Brainstem\'s folder is in it: not the folder itself, not .env, not .venv, not the secret', () => {
		const workspace = JSON.parse(workspaceFileText(AGENTS, DATA)) as { folders: { path?: string; uri?: string }[] };
		for (const entry of workspace.folders) {
			const folder = rootPath(entry) ?? '';
			assert.ok(path.relative(folder, DEFAULT).startsWith('..'), `the root ${folder} holds the Brainstem's folder`);
			for (const kept of [SECRET, path.join(DEFAULT, '.env'), path.join(DEFAULT, '.venv'), path.join(DEFAULT, 'brainstem.py')]) {
				assert.ok(path.relative(folder, kept).startsWith('..'), `${kept} is inside the root ${folder}`);
			}
		}
		assert.deepStrictEqual(workspace.folders.map(rootPath), [AGENTS, DATA]);
	});

	test('the data folder is the Brainstem\'s own .brainstem_data: a real folder, not a link, outside Hives', () => {
		const brace = path.join(ROOT, 'odd{name}', 'rapp_brainstem');
		fs.mkdirSync(path.join(brace, '.brainstem_data'), { recursive: true });
		const linkedData = path.join(ROOT, 'linked-data', 'rapp_brainstem');
		fs.mkdirSync(linkedData, { recursive: true });
		let linked = false;
		try {
			fs.symlinkSync(DATA, path.join(linkedData, '.brainstem_data'));
			linked = true;
		} catch {
			// Symlinks need privileges on some systems.
		}
		const fileInstead = path.join(ROOT, 'file-data', 'rapp_brainstem');
		write(path.join(fileInstead, '.brainstem_data'), 'not a folder');
		fs.mkdirSync(path.join(IN_HIVE, '.brainstem_data'), { recursive: true });
		assert.deepStrictEqual([
			resolveDataFolder(DEFAULT, FORBIDDEN, PLATFORM),
			resolveDataFolder(RUNNING, FORBIDDEN, PLATFORM),
			resolveDataFolder(brace, FORBIDDEN, PLATFORM),
			resolveDataFolder(fileInstead, FORBIDDEN, PLATFORM),
			resolveDataFolder(IN_HIVE, FORBIDDEN, PLATFORM),
			resolveDataFolder(undefined, FORBIDDEN, PLATFORM),
		], [DATA, undefined, path.join(brace, '.brainstem_data'), undefined, undefined, undefined]);
		if (linked) {
			assert.strictEqual(resolveDataFolder(linkedData, FORBIDDEN, PLATFORM), undefined, 'a link could lead anywhere');
		}
	});

	test('its workspace file keeps a person\'s own settings, names and folders, and is written only when a root or a rule changes', () => {
		const storage = path.join(ROOT, 'storage');
		const old = JSON.stringify({ folders: [{ name: 'agents', path: AGENTS }], settings: { 'window.title': TITLE } }, null, '\t');
		const mine = JSON.stringify({ folders: [{ name: 'My agents', path: AGENTS }], settings: { 'window.title': 'Mine', 'editor.fontSize': 15 } }, null, '\t');
		const withComments = `{\n\t// mine\n\t"folders": [{ "path": ${JSON.stringify(AGENTS)}, },],\n\t/* block */ "settings": { "note": "a, } b", },\n}\n`;
		const relative = JSON.stringify({ folders: [{ path: path.relative(storage, AGENTS) }] });
		const moved = workspaceFileUpdate(JSON.stringify({
			folders: [{ name: 'agents', path: path.join(ROOT, 'old', 'agents') }, { path: OTHER }],
			settings: { 'window.title': 'Mine' },
			extensions: { recommendations: [] },
		}), AGENTS, storage);
		assert.deepStrictEqual([
			workspaceFileUpdate(undefined, AGENTS, storage) === workspaceFileText(AGENTS),
			workspaceFileUpdate(mine, AGENTS, storage),
			workspaceFileUpdate(withComments, AGENTS, storage),
			workspaceFileUpdate(relative, AGENTS, storage),
			workspaceFileUpdate('{ not a workspace', AGENTS, storage),
			workspaceFileUpdate(old, AGENTS, storage),
			moved,
		], [true, undefined, undefined, undefined, undefined, undefined, undefined], 'Agents and every other root stay exactly as written; a file that does not list this Agents folder is not the app\'s to change');
		const mineFirst = JSON.stringify({ folders: [{ name: 'Mine', path: OTHER }, { name: 'Agents', path: AGENTS }] });
		const draggedLower = JSON.stringify({ folders: [{ name: 'Brainstem data', uri: dataUri(path.join(DEFAULT, '.brainstem_data')) }, { name: 'Agents', path: AGENTS }] });
		assert.deepStrictEqual([
			workspaceFileUpdate(mineFirst, AGENTS, storage),
			JSON.parse(workspaceFileUpdate(draggedLower, AGENTS, storage, path.join(DEFAULT, '.brainstem_data')) ?? 'null').folders,
		], [
			undefined,
			[{ name: 'Brainstem data', uri: dataUri(path.join(DEFAULT, '.brainstem_data')) }, { name: 'Agents', path: AGENTS }],
		], 'the roots stay in a person\'s order: Agents found wherever it is, never twice, and first only when missing');
	});

	test('each Agents folder has its own workspace file in the app\'s storage; the one earlier builds kept is the app\'s own too', () => {
		const storage = path.join(ROOT, 'storage');
		const own = path.join(storage, WORKSPACES_FOLDER, workspaceKey(AGENTS), WORKSPACE_FILE);
		assert.match(workspaceKey(AGENTS), /^[0-9a-f]{16}$/);
		assert.notStrictEqual(workspaceKey(AGENTS), workspaceKey(path.join(ROOT, 'another', 'agents')));
		assert.deepStrictEqual([
			isOwnWorkspaceFile(own, storage),
			isOwnWorkspaceFile(path.join(storage, WORKSPACE_FILE), storage),
			isOwnWorkspaceFile(path.join(ROOT, 'Downloads', WORKSPACE_FILE), storage),
			isOwnWorkspaceFile(path.join(storage, WORKSPACES_FOLDER, 'not-a-key', WORKSPACE_FILE), storage),
			isOwnWorkspaceFile(path.join(storage, WORKSPACES_FOLDER, workspaceKey(AGENTS), 'Other.code-workspace'), storage),
			isOwnWorkspaceFile(path.join(storage, WORKSPACES_FOLDER, `${workspaceKey(AGENTS)}-2`, WORKSPACE_FILE), storage),
			isOwnWorkspaceFile(path.join(storage, WORKSPACES_FOLDER, `${workspaceKey(AGENTS)}-1000`, WORKSPACE_FILE), storage),
		], [true, true, false, false, false, true, false]);
		const cased = path.join(storage, WORKSPACES_FOLDER, workspaceKey(AGENTS).toUpperCase(), WORKSPACE_FILE.toLowerCase());
		assert.deepStrictEqual([isOwnWorkspaceFile(cased, storage, 'darwin'), isOwnWorkspaceFile(cased, storage, 'win32'), isOwnWorkspaceFile(cased, storage, 'linux')], [true, true, false],
			'its name and key folder in other letter case are its own where the file system ignores case, as samePath judges it');
		fs.mkdirSync(path.dirname(own), { recursive: true });
		fs.writeFileSync(own, workspaceFileText(AGENTS));
		assert.deepStrictEqual(rootsOf(own), [AGENTS]);
		assert.deepStrictEqual(rootsOf(path.join(storage, 'missing.code-workspace')), []);
		assert.strictEqual(workspaceKey(`${AGENTS}${path.sep}`), workspaceKey(AGENTS), 'one folder, one file');
		if (process.platform !== 'linux') {
			assert.strictEqual(workspaceKey(AGENTS.toUpperCase()), workspaceKey(AGENTS), 'letter case does not make another file where the file system ignores it');
		}
	});

	test('files are written whole: a rename retried on Windows while another program holds the file, and a new file never made over one someone else just made', () => {
		const file = path.join(ROOT, 'whole', 'note.json');
		// The module itself (the compiled import reads through to it), so the app's own calls see the stand-in.
		const nodeFs = require('fs') as { renameSync: typeof fs.renameSync };
		const rename = nodeFs.renameSync;
		let failures = 2;
		nodeFs.renameSync = (from, to) => {
			if (failures-- > 0) {
				throw Object.assign(new Error('busy'), { code: 'EPERM' });
			}
			rename(from, to);
		};
		try {
			writeWhole(file, 'one', 'win32');
			assert.strictEqual(fs.readFileSync(file, 'utf8'), 'one', 'tried again until the rename went through');
			failures = 1;
			assert.throws(() => writeWhole(file, 'two', 'linux'), /busy/, 'elsewhere, never tried again');
			assert.deepStrictEqual([fs.readFileSync(file, 'utf8'), fs.readdirSync(path.dirname(file))], ['one', ['note.json']], 'and no partial file is left');
		} finally {
			nodeFs.renameSync = rename;
		}
		const made = path.join(ROOT, 'whole', 'made.json');
		assert.deepStrictEqual([createWhole(made, 'first'), createWhole(made, 'second'), fs.readFileSync(made, 'utf8')], [true, false, 'first']);
		assert.deepStrictEqual(fs.readdirSync(path.dirname(made)).sort(), ['made.json', 'note.json']);
		// A volume without links (FAT, exFAT, some network drives): made by an exclusive write instead.
		const linker = require('fs') as { linkSync: typeof fs.linkSync };
		const link = linker.linkSync;
		linker.linkSync = () => {
			throw Object.assign(new Error('no links here'), { code: 'ENOTSUP' });
		};
		try {
			const unlinked = path.join(ROOT, 'whole', 'unlinked.json');
			assert.deepStrictEqual([createWhole(unlinked, 'first'), createWhole(unlinked, 'second'), fs.readFileSync(unlinked, 'utf8')], [true, false, 'first']);
		} finally {
			linker.linkSync = link;
		}
		assert.deepStrictEqual(fs.readdirSync(path.dirname(made)).sort(), ['made.json', 'note.json', 'unlinked.json'], 'no partial file left');
	});

	test('a workspace file reads as the host reads it: a byte order mark, comments, and a trailing comma before a comment', () => {
		const file = path.join(ROOT, 'lenient', 'RAPP Workspace.code-workspace');
		fs.mkdirSync(path.dirname(file), { recursive: true });
		fs.writeFileSync(file, `\uFEFF{\n\t"folders": [\n\t\t{ "path": ${JSON.stringify(AGENTS)} }, // mine\n\t\t/* more later */\n\t],\n}\n`);
		assert.deepStrictEqual(rootsOf(file), [AGENTS]);
		assert.notStrictEqual(workspaceFileUpdate(fs.readFileSync(file, 'utf8'), AGENTS, path.dirname(file), path.join(DEFAULT, '.brainstem_data')), undefined, 'so its data root can join');
	});

	test('a workspace file is read as the host reads it: past a slip it reads past, and one it would refuse names no roots', () => {
		const dir = path.join(ROOT, 'as-the-host');
		fs.mkdirSync(dir, { recursive: true });
		const rootsFrom = (name: string, text: string) => {
			const file = path.join(dir, `${name}.code-workspace`);
			fs.writeFileSync(file, text);
			return rootsOf(file);
		};
		const agents = JSON.stringify(AGENTS);
		assert.deepStrictEqual([
			rootsFrom('missing-comma', `{\n\t"folders": [{ "path": ${agents} }]\n\t"settings": {}\n}\n`),
			rootsFrom('cut-inside-folders', `{ "folders": [{ "path": ${agents} }, { "pa`),
			rootsFrom('stray', `{ "folders": [{ "path": ${agents} }] x }`),
			rootsFrom('by-uri', `{ "folders": [{ "uri": ${JSON.stringify(url.pathToFileURL(AGENTS).href)} }] }`),
		], [[AGENTS], [AGENTS], [AGENTS], [AGENTS]]);
		assert.deepStrictEqual([
			rootsFrom('empty', ''),
			rootsFrom('blank', ' \n\t\n'),
			rootsFrom('cut-before-folders', '{ "settings": { "editor.fontSize": 15 }, "fold'),
			rootsFrom('renamed', `{ "folderz": [{ "path": ${agents} }] }`),
			rootsFrom('not-a-list', `{ "folders": { "path": ${agents} } }`),
			rootsFrom('bad-name', `{ "folders": [{ "path": ${agents}, "name": 7 }] }`),
		], [[], [], [], [], [], []], 'the host refuses these, or leaves out that entry');
		assert.strictEqual(workspaceFileUpdate(fs.readFileSync(path.join(dir, 'missing-comma.code-workspace'), 'utf8'), AGENTS, dir, path.join(DEFAULT, '.brainstem_data')), undefined,
			'a file read past a slip is never rewritten: only one that reads as JSON is');
	});

	test('the tolerant reader reads every damaged file exactly as the host\'s own reader does', () => {
		// The host's reader at the pinned commit, compiled: by scripts/test-extension.mjs from the fork's source it
		// fetched by digest, or the fork's own build for build.sh --test.
		const hostFile = process.env.BRAINSTEM_TEST_HOST_JSON;
		assert.ok(hostFile && fs.existsSync(hostFile), `no host JSON reader at BRAINSTEM_TEST_HOST_JSON (${hostFile}): run the tests with scripts/test-extension.mjs or build.sh --test`);
		const parse = (require(hostFile) as { parse?: (text: string) => unknown }).parse;
		assert.ok(typeof parse === 'function', 'the host\'s reader has a parse()');
		const sample = `\uFEFF// mine\n{\n\t"folders": [\n\t\t{ "name": "Agents", "path": "/x/rapp_brainstem/agents" },\n\t\t{ "name": "Brainstem data", "uri": "brainstem-data:///x/rapp_brainstem/.brainstem_data" }, /* more */\n\t],\n\t"settings": { "window.title": "\\u0052APP \\"W\\"\\\\s", "n": -1.5e3, "on": true, "off": false, "none": null, "list": [1, 0.5, "a\\tb"] },\n}\n`;
		const cases = new Set<string>([sample, '', ' ', '{', '}', '[', ']', ',', ':', '"', '/', '-', '/*', '//', '1.', '1e', '-x', '01', '"\\u12', '"\\q"', '"a\nb"', '"a\u2028b"', 'tru', 'true1', '{"a" 1}', '{"a":}', '{,"a":1}', '[1 2]', '[,1]', '[1,,2]', '{"a":1 "b":2}', '{"a":1}{"b":2}']);
		// Every kind of white space and line break the host knows, and some it does not, beside a value and in one.
		for (const c of ['\u0020', '\u0009', '\u000b', '\u000c', '\u00a0', '\u1680', '\u2000', '\u200a', '\u200b', '\u202f', '\u205f', '\u3000', '\ufeff',
			'\n', '\r', '\u2028', '\u2029', '\u0085', '\u180e', '\u200c', '\u00ad', '\u0000', '\u001f']) {
			for (const text of [`${c}true`, `[${c}null${c}]`, `{"a":${c}1${c}}`, `"x${c}y"`, `{${c}"folders"${c}:${c}[]${c}}`]) {
				cases.add(text);
			}
		}
		for (const text of ['[01]', '[-01]', '[1.e5]', '[1e+]', '[.5]', '[-]', '[--1]', '[1e999]', '[0x1]', '["\\u00e9\\u12"]', '{"a":1,,"b":2}', '{"a" "b":1}', '{"a"::1}', '[1:2]', '{]', '[}']) {
			cases.add(text);
		}
		for (let i = 0; i <= sample.length; i++) {
			cases.add(sample.slice(0, i));
			cases.add(sample.slice(0, i) + sample.slice(i + 1));
			for (const extra of [',', '}', ']', '{', '[', '"', ':', 'x', '/', '*', '-', '\n']) {
				cases.add(sample.slice(0, i) + extra + sample.slice(i));
			}
		}
		let compared = 0;
		for (const text of cases) {
			assert.deepStrictEqual(readTolerant(text), parse(text), `differs from the host on ${JSON.stringify(text)}`);
			compared++;
		}
		assert.ok(compared > 3000, `compared ${compared} files`);
	});

	test('a person\'s own order of rules is never a reason to rewrite the file', () => {
		const storage = path.join(ROOT, 'storage');
		const DATA = path.join(DEFAULT, '.brainstem_data');
		const theirs = JSON.parse(workspaceFileText(AGENTS, DATA));
		const reordered = { ...theirs, settings: { ...theirs.settings, 'files.exclude': Object.fromEntries(Object.entries(theirs.settings['files.exclude']).reverse()) } };
		assert.strictEqual(workspaceFileUpdate(JSON.stringify(reordered), AGENTS, storage, DATA), undefined);
	});

	test('an Agents root named through a link stays as written (the host trusts a folder by its path as written); the data root follows the folder', () => {
		const storage = path.join(ROOT, 'storage');
		const realHome = path.join(ROOT, 'real-home', 'rapp_brainstem');
		fs.mkdirSync(path.join(realHome, 'agents'), { recursive: true });
		fs.mkdirSync(path.join(realHome, '.brainstem_data'), { recursive: true });
		const link = path.join(ROOT, 'link-home');
		try {
			fs.symlinkSync(path.join(ROOT, 'real-home'), link);
		} catch {
			return; // Symlinks need privileges on some systems.
		}
		const viaLink = path.join(link, 'rapp_brainstem');
		const first = workspaceFileText(path.join(viaLink, 'agents'), path.join(viaLink, '.brainstem_data'));
		const healed = JSON.parse(workspaceFileUpdate(first, path.join(realHome, 'agents'), storage, path.join(realHome, '.brainstem_data')) ?? 'null');
		assert.deepStrictEqual(healed.folders, [{ name: 'Agents', path: path.join(viaLink, 'agents') }, dataRoot(path.join(realHome, '.brainstem_data'))]);
	});

	test('an earlier build\'s data root, a plain path with two read-only globs, becomes the read-only brainstem-data: root, and only those globs go', () => {
		const storage = path.join(ROOT, 'storage');
		const theirs = { '**/.brainstem_data/**': true, '/Volumes/Backup/rapp_brainstem/.brainstem_data/**': true, '**/notes/**': true };
		const earlier = JSON.stringify({
			folders: [{ name: 'Agents', path: AGENTS }, { name: 'Brainstem data', path: DATA }],
			settings: { 'window.title': TITLE, 'files.readonlyInclude': { ...legacyGlobs(DATA), ...theirs }, 'files.exclude': EXCLUDES },
		});
		const migrated = JSON.parse(workspaceFileUpdate(earlier, AGENTS, storage, DATA) ?? 'null');
		assert.deepStrictEqual(migrated, {
			folders: [{ name: 'Agents', path: AGENTS }, dataRoot(DATA)],
			settings: { 'window.title': TITLE, 'files.readonlyInclude': theirs, 'files.exclude': EXCLUDES },
		});
		assert.strictEqual(workspaceFileUpdate(JSON.stringify(migrated), AGENTS, storage, DATA), undefined, 'up to date: left as it is');
		const only = JSON.stringify({ folders: [{ name: 'Agents', path: AGENTS }, { name: 'Brainstem data', path: DATA }], settings: { 'window.title': TITLE, 'files.readonlyInclude': legacyGlobs(DATA), 'files.exclude': EXCLUDES } });
		assert.strictEqual(JSON.parse(workspaceFileUpdate(only, AGENTS, storage, DATA) ?? 'null').settings['files.readonlyInclude'], undefined, 'no rules of its own left: the key goes');
	});

	test('the data root joins when its folder is there, keeps a person\'s own name and rules, follows a move, and leaves when it is gone', () => {
		const storage = path.join(ROOT, 'storage');
		const old = JSON.stringify({ folders: [{ name: 'agents', path: AGENTS }, { path: OTHER }], settings: { 'window.title': TITLE, 'files.exclude': { '**/*.log': true } } });
		const joined = JSON.parse(workspaceFileUpdate(old, AGENTS, storage, DATA) ?? 'null');
		assert.deepStrictEqual(joined, {
			folders: [{ name: 'agents', path: AGENTS }, dataRoot(DATA), { path: OTHER }],
			settings: { 'window.title': TITLE, 'files.exclude': { ...EXCLUDES, '**/*.log': true } },
		}, 'the data root joins right after Agents; Agents and the rest stay exactly as written');
		const current = JSON.stringify(joined);
		assert.strictEqual(workspaceFileUpdate(current, AGENTS, storage, DATA), undefined, 'up to date: left as it is');
		const renamed = JSON.stringify({ ...joined, folders: [joined.folders[0], { ...joined.folders[1], name: 'Memory' }, joined.folders[2]] });
		assert.strictEqual(workspaceFileUpdate(renamed, AGENTS, storage, DATA), undefined, 'a person\'s own name for it stays');
		const shown = JSON.stringify({ ...joined, settings: { ...joined.settings, 'files.exclude': { '**/*cache*.json': false } } });
		assert.deepStrictEqual(JSON.parse(workspaceFileUpdate(shown, AGENTS, storage, DATA) ?? 'null').settings['files.exclude'], { ...EXCLUDES, '**/*cache*.json': false }, 'a person\'s own value wins; only what is missing is added');
		const elsewhere = path.join(ROOT, 'elsewhere', '.brainstem_data');
		const followed = JSON.parse(workspaceFileUpdate(current, AGENTS, storage, elsewhere) ?? 'null');
		assert.deepStrictEqual(followed.folders, [{ name: 'agents', path: AGENTS }, dataRoot(elsewhere), { path: OTHER }]);
		const gone = JSON.parse(workspaceFileUpdate(current, AGENTS, storage) ?? 'null');
		assert.deepStrictEqual(gone.folders, [{ name: 'agents', path: AGENTS }, { path: OTHER }]);
	});
});

describe('Startup', () => {
	const AGENTS = path.join(DEFAULT, 'agents');
	const base: StartupInputs = {
		openFolders: [], workspaceFile: false, openDocuments: 0, remote: false,
		root: DEFAULT, agents: AGENTS, openOnStartup: true, showUI: true, workspaceShown: false,
	};
	const linked = path.join(ROOT, 'linked-brainstem');

	test('an empty window opens the RAPP Workspace while no other window shows it, and never over an open document', () => {
		assert.deepStrictEqual([
			startupAction(base),
			startupAction({ ...base, workspaceShown: true }),
			startupAction({ ...base, openOnStartup: false }),
			startupAction({ ...base, openDocuments: 1 }),
			startupAction({ ...base, agents: undefined }),
			startupAction({ ...base, remote: true }),
			startupAction({ ...base, workspaceFile: true }),
		], ['open-workspace', 'nothing', 'nothing', 'nothing', 'nothing', 'nothing', 'nothing']);
	});

	test('the Brainstem\'s own folder opens the RAPP Workspace instead, every time it is opened', () => {
		assert.deepStrictEqual([
			startupAction({ ...base, openFolders: [DEFAULT] }),
			startupAction({ ...base, openFolders: [`${DEFAULT}${path.sep}`], workspaceShown: true }),
			startupAction({ ...base, openFolders: [fs.existsSync(linked) ? linked : DEFAULT] }),
			startupAction({ ...base, openFolders: [DEFAULT], openOnStartup: false }),
		], ['open-workspace', 'open-workspace', 'open-workspace', 'nothing']);
	});

	test('the note of which windows show the RAPP Workspace: live windows of this launch, or one that left it a moment ago', () => {
		const note = { launch: 'L', hosts: [11, 22], leftAt: 1000 };
		const alive = (pid: number) => pid === 22;
		assert.deepStrictEqual([
			shownElsewhere(note, 'L', 99, 1000 + SHOWN_GRACE_MS + 1, alive),
			shownElsewhere(note, 'L', 22, 1000 + SHOWN_GRACE_MS + 1, alive),
			shownElsewhere({ ...note, hosts: [] }, 'L', 99, 1000 + SHOWN_GRACE_MS - 1, alive),
			shownElsewhere({ ...note, hosts: [] }, 'L', 99, 1000 + SHOWN_GRACE_MS, alive),
			shownElsewhere(note, 'another launch', 99, 1000, alive),
			shownElsewhere(undefined, 'L', 99, 1000, alive),
		], [true, false, true, false, false, false], 'a live other window; never this one; a window that just left; not after the grace; not another launch; no note');
		const file = path.join(ROOT, 'shown', 'workspace-shown.json');
		assert.strictEqual(readShownNote(file), undefined);
		writeShownNote(file, note);
		assert.deepStrictEqual(readShownNote(file), note);
		assert.deepStrictEqual(fs.readdirSync(path.dirname(file)), ['workspace-shown.json'], 'written whole, with nothing left beside it');
		fs.writeFileSync(file, '{"launch": 1}');
		assert.strictEqual(readShownNote(file), undefined, 'a note it cannot read counts as none');
		const blocked = path.join(ROOT, 'shown-blocked', 'workspace-shown.json');
		fs.mkdirSync(path.join(blocked, 'in-the-way'), { recursive: true });
		assert.throws(() => writeShownNote(blocked, note));
		assert.deepStrictEqual(fs.readdirSync(path.dirname(blocked)), ['workspace-shown.json'], 'a write that fails leaves no partial file behind');
		assert.deepStrictEqual([isRunning(process.pid), isRunning(2 ** 31 - 2)], [true, false]);
	});

	test('the RAPP Workspace, as a folder or in its workspace file, shows the Brainstem\'s web UI', () => {
		assert.deepStrictEqual([
			startupAction({ ...base, openFolders: [AGENTS] }),
			startupAction({ ...base, openFolders: [AGENTS], workspaceFile: true }),
			startupAction({ ...base, openFolders: [`${AGENTS}${path.sep}`], workspaceShown: true }),
			startupAction({ ...base, openFolders: [AGENTS], showUI: false }),
		], ['show-ui', 'show-ui', 'show-ui', 'nothing']);
	});

	test('the RAPP Workspace with its Brainstem data root, or in the app\'s own workspace file, is still the RAPP Workspace', () => {
		const DATA = path.join(DEFAULT, '.brainstem_data');
		assert.deepStrictEqual([
			startupAction({ ...base, data: DATA, openFolders: [AGENTS, DATA], workspaceFile: true }),
			startupAction({ ...base, data: DATA, openFolders: [AGENTS, OTHER], workspaceFile: true }),
			startupAction({ ...base, data: DATA, openFolders: [AGENTS, OTHER], workspaceFile: true, ownFile: true }),
			startupAction({ ...base, data: DATA, openFolders: [DATA, AGENTS], workspaceFile: true }),
			startupAction({ ...base, data: DATA, openFolders: [DATA] }),
			startupAction({ ...base, data: DATA, openFolders: [DATA, AGENTS], workspaceFile: true, ownFile: true }),
			startupAction({ ...base, data: DATA, openFolders: [OTHER, DATA], workspaceFile: true, ownFile: true }),
		], ['show-ui', 'nothing', 'show-ui', 'nothing', 'nothing', 'show-ui', 'nothing'], 'in the app\'s own file, agents/ anywhere among the roots');
		assert.strictEqual(isRappWorkspaceWindow({ openFolders: [AGENTS, DATA], agents: AGENTS }), false, 'a second root is the RAPP Workspace\'s only when it is the data folder');
	});

	test('any other folder or workspace does nothing', () => {
		assert.deepStrictEqual([
			startupAction({ ...base, openFolders: [OTHER] }),
			startupAction({ ...base, openFolders: [path.dirname(DEFAULT)] }),
			startupAction({ ...base, openFolders: [path.join(AGENTS, 'disabled_agents')] }),
			startupAction({ ...base, openFolders: [DEFAULT, OTHER] }),
			startupAction({ ...base, openFolders: [AGENTS, OTHER] }),
			startupAction({ ...base, openFolders: [DEFAULT], workspaceFile: true }),
			startupAction({ ...base, openFolders: [undefined] }),
		], ['nothing', 'nothing', 'nothing', 'nothing', 'nothing', 'nothing', 'nothing']);
	});
});
