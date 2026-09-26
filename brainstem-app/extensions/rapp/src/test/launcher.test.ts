// Unit tests for the launcher against a stand-in vscode API and a synthetic Brainstem folder under the test
// temp folder: an empty window or the Brainstem's own folder opens the RAPP Workspace (its agents/), which is
// managed and shows the web UI; a window's startup never runs the Brainstem's start script; a click runs it
// once, however often it is clicked; and a Brainstem that already answers is shown, not started again.
import * as assert from 'assert';
import * as fs from 'fs';
import * as path from 'path';
import type * as vscode from 'vscode';
import { after, beforeEach, describe, test } from 'node:test';

const loader = require('module') as { _resolveFilename: (request: string, ...rest: unknown[]) => string };
const resolveFilename = loader._resolveFilename;
loader._resolveFilename = function (this: unknown, request: string, ...rest: unknown[]): string {
	return request === 'vscode' ? path.join(__dirname, 'vscodeStub.js') : resolveFilename.call(this, request, ...rest);
};

const stub = require('./vscodeStub') as typeof import('./vscodeStub');
const { BrainstemLauncher } = require('../launcher') as typeof import('../launcher');
const { browserReuseFilter, dataUri, START_STATUS_ENV, startCommand, workspaceKey } = require('../startup') as typeof import('../startup');
type Status = import('../chatView').Status;

const TMP = path.resolve(process.env.BRAINSTEM_TEST_TMP || path.join(__dirname, '..', '..', '.test-tmp'));
const ROOT = path.join(TMP, `launcher-fixture-${process.pid}`);
const FOLDER = path.join(ROOT, 'rapp_brainstem');
const AGENTS = path.join(FOLDER, 'agents');
const STORAGE = path.join(ROOT, 'global-storage');
// The file earlier builds kept (a window may still have it open).
const WORKSPACE_FILE = path.join(STORAGE, 'RAPP Workspace.code-workspace');
const ADDRESS = 'http://127.0.0.1:7071';
const UP: Status = { state: 'connected', version: '0.6.9' };
const DOWN: Status = { state: 'not-running', reason: 'connect ECONNREFUSED' };
const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));
const TRUST = 'Your Brainstem already runs these agents. Trust your RAPP Workspace so you can manage them here.';
const trustAsked = (...folders: string[]) => ({ message: `${TRUST}\n\n${folders.length === 1 ? 'Folder' : 'Folders'}: ${folders.map(f => `\` ${f} \``).join(', ')}` });
const START_TRUST = 'Starting your Brainstem runs its own start script in a terminal, which Restricted Mode does not allow. Trust your RAPP Workspace to start it here.';
const statusFileOf = (terminal: { options: unknown }) => (terminal.options as { env: Record<string, string> }).env[START_STATUS_ENV];
const LAUNCH = process.env.VSCODE_PID || String(process.ppid);
const SHOWN_FILE = path.join(STORAGE, 'workspace-shown.json');
const shownNote = () => JSON.parse(fs.readFileSync(SHOWN_FILE, 'utf8')) as { launch: string; hosts: number[]; leftAt: number };
const writeShown = (note: { launch: string; hosts: number[]; leftAt: number }) => (fs.mkdirSync(STORAGE, { recursive: true }), fs.writeFileSync(SHOWN_FILE, JSON.stringify(note)));
// A process id no process can have, and one that certainly runs (this test's parent).
const ENDED = 2 ** 31 - 2;
const RUNNING = process.ppid;

fs.rmSync(ROOT, { recursive: true, force: true });
fs.mkdirSync(FOLDER, { recursive: true });
fs.writeFileSync(path.join(FOLDER, 'brainstem.py'), 'raise SystemExit("never run by the tests")\n');
fs.writeFileSync(path.join(FOLDER, 'start.sh'), '#!/bin/bash\nexit 1\n');
fs.writeFileSync(path.join(FOLDER, 'start.ps1'), 'exit 1\n');
fs.mkdirSync(AGENTS);
fs.writeFileSync(path.join(AGENTS, 'basic_agent.py'), 'class BasicAgent:\n    pass\n');
after(() => fs.rmSync(ROOT, { recursive: true, force: true }));
// This Agents folder's own workspace file (keyed by its real path, so only once the folder exists), and the next.
const OWN_FILE = path.join(STORAGE, 'workspaces', workspaceKey(AGENTS), 'RAPP Workspace.code-workspace');
const NEXT_FILE = path.join(STORAGE, 'workspaces', `${workspaceKey(AGENTS)}-2`, 'RAPP Workspace.code-workspace');

function launcher(statuses: Status[], pollMs = 0, url = ADDRESS, store = new Map<string, unknown>(), set: { brainstemFolder?: string; agentsFolder?: string } = {}) {
	const context = {
		globalState: { get: (key: string, fallback?: unknown) => store.get(key) ?? fallback, update: async (key: string, value: unknown) => void store.set(key, value) },
		globalStorageUri: stub.Uri.file(STORAGE),
	};
	const managed: (string | undefined)[] = [];
	const starting: boolean[] = [];
	let polls = 0;
	const view = {
		poll: async () => {
			await sleep(pollMs);
			return statuses[Math.min(polls++, statuses.length - 1)];
		},
		setStarting: (on: boolean) => void starting.push(on),
	};
	const settings = () => ({ url, brainstemFolder: FOLDER, agentsFolder: '', openOnStartup: true, showUI: true, ...set });
	const it = new BrainstemLauncher(context as unknown as vscode.ExtensionContext, view as never, settings, () => [], root => void managed.push(root));
	return { it, store, starting, managed };
}

// A home folder of the test's own while `run` runs, so the default Brainstem folder is never this device's own.
async function withHome(home: string, run: () => Promise<void>): Promise<void> {
	const saved = { HOME: process.env.HOME, USERPROFILE: process.env.USERPROFILE };
	fs.mkdirSync(home, { recursive: true });
	process.env.HOME = home;
	process.env.USERPROFILE = home;
	try {
		await run();
	} finally {
		for (const [key, value] of Object.entries(saved)) {
			if (value === undefined) {
				delete process.env[key];
			} else {
				process.env[key] = value;
			}
		}
	}
}

const commandIds = () => stub.recorded.commands.map(([id]) => id);
// The window has this workspace file open, with these roots on disk (as the host opened it).
function openWorkspaceFile(file: string, roots: string[]): void {
	fs.mkdirSync(path.dirname(file), { recursive: true });
	fs.writeFileSync(file, JSON.stringify({ folders: roots.map((root, i) => (i === 0 ? { name: 'Agents', path: root } : { path: root })) }));
	stub.workspace.workspaceFile = stub.Uri.file(file);
	stub.workspace.workspaceFolders = roots.map(root => ({ uri: stub.Uri.file(root) }));
}
const browserOpen = { url: `${ADDRESS}/`, reuseUrlFilter: `${ADDRESS}/**` };

beforeEach(() => {
	stub.recorded.commands.length = 0;
	stub.recorded.terminals.length = 0;
	stub.recorded.messages.length = 0;
	stub.workspace.workspaceFolders = undefined;
	stub.workspace.workspaceFile = undefined;
	stub.workspace.isTrusted = true;
	stub.workspace.folderListeners.length = 0;
	stub.recorded.trustRequests.length = 0;
	stub.recorded.watchers.length = 0;
	stub.window.terminals = [];
	stub.window.showInformationMessage = async (message: string) => void stub.recorded.messages.push(message);
	fs.rmSync(SHOWN_FILE, { force: true });
	fs.rmSync(WORKSPACE_FILE, { force: true });
	fs.rmSync(path.join(STORAGE, 'workspaces'), { recursive: true, force: true });
	stub.registeredCommands.splice(0, Infinity, 'workbench.action.browser.open', 'workbench.action.browser.reload', 'simpleBrowser.api.open');
});

describe('Launcher', () => {
	test('an empty window opens the RAPP Workspace, from a workspace file outside agents/, and runs nothing; one beside it stays empty', async () => {
		const { it, store } = launcher([DOWN]);
		await it.onStartup();
		await it.onStartup();
		assert.deepStrictEqual(stub.recorded.commands.map(([id, uri, options]) => [id, (uri as { fsPath?: string })?.fsPath, options]), [
			['vscode.openFolder', OWN_FILE, { forceReuseWindow: true }],
		]);
		assert.deepStrictEqual(JSON.parse(fs.readFileSync(OWN_FILE, 'utf8')).folders, [{ name: 'Agents', path: AGENTS }]);
		const note = shownNote();
		assert.deepStrictEqual([[...store.keys()], note.launch, note.hosts, Math.abs(Date.now() - note.leftAt) < 5000], [[], LAUNCH, [], true], 'noted as it switches, in a file in the app\'s storage');
		assert.deepStrictEqual(fs.readdirSync(AGENTS), ['basic_agent.py']);
		assert.strictEqual(stub.recorded.terminals.length, 0);
	});

	test('an empty window opens it again once no window shows it, as when the app is reopened after its windows closed', async () => {
		const opened = () => stub.recorded.commands.filter(([id]) => id === 'vscode.openFolder').length;
		const cases: [{ launch: string; hosts: number[]; leftAt: number }, number, string][] = [
			[{ launch: LAUNCH, hosts: [], leftAt: Date.now() - 2000 }, 0, 'a window left it a moment ago (its folder was just closed there): this one stays empty'],
			[{ launch: LAUNCH, hosts: [RUNNING], leftAt: 0 }, 0, 'another window shows it: this new one stays empty'],
			[{ launch: LAUNCH, hosts: [ENDED], leftAt: Date.now() - 60000 }, 1, 'no window shows it any more: the reopened app shows it again'],
			[{ launch: 'an earlier launch', hosts: [RUNNING], leftAt: Date.now() }, 2, 'a note from an earlier launch never keeps a new launch empty'],
		];
		for (const [note, expected, why] of cases) {
			writeShown(note);
			await launcher([DOWN]).it.onStartup();
			assert.strictEqual(opened(), expected, why);
		}
	});

	test('a window showing the RAPP Workspace is in the note while it does, and leaves it with the time as it goes', async () => {
		stub.workspace.workspaceFolders = [{ uri: stub.Uri.file(AGENTS) }];
		stub.workspace.workspaceFile = stub.Uri.file(WORKSPACE_FILE);
		writeShown({ launch: LAUNCH, hosts: [RUNNING, ENDED], leftAt: 5 });
		const { it } = launcher([UP]);
		await it.onStartup();
		assert.deepStrictEqual(shownNote(), { launch: LAUNCH, hosts: [RUNNING, process.pid], leftAt: 5 }, 'a host that no longer runs goes');
		it.dispose();
		const gone = shownNote();
		assert.deepStrictEqual([gone.hosts, Math.abs(Date.now() - gone.leftAt) < 5000], [[RUNNING], true], 'written at once, as a plain file, as the window goes');
	});

	test('a window on the Brainstem\'s own folder opens the RAPP Workspace instead', async () => {
		stub.workspace.workspaceFolders = [{ uri: stub.Uri.file(FOLDER) }];
		await launcher([UP]).it.onStartup();
		assert.deepStrictEqual(stub.recorded.commands.map(([id, uri]) => [id, (uri as { fsPath?: string })?.fsPath]), [['vscode.openFolder', OWN_FILE]]);
	});

	test('the file earlier builds kept goes on being used while it names this Agents folder', async () => {
		fs.mkdirSync(STORAGE, { recursive: true });
		fs.writeFileSync(WORKSPACE_FILE, JSON.stringify({ folders: [{ name: 'Agents', path: AGENTS }], settings: { 'window.title': 'RAPP Workspace' } }));
		await launcher([DOWN]).it.onStartup();
		assert.deepStrictEqual(stub.recorded.commands.map(([id, uri]) => [id, (uri as { fsPath?: string })?.fsPath]), [['vscode.openFolder', WORKSPACE_FILE]], 'so a window keeps its tabs and layout');
	});

	test('the RAPP Workspace is watched, asks once for trust, and shows the web UI when it answers, else the offline card', async () => {
		stub.workspace.workspaceFolders = [{ uri: stub.Uri.file(AGENTS) }];
		stub.workspace.workspaceFile = stub.Uri.file(WORKSPACE_FILE);
		stub.workspace.isTrusted = false;
		const up = launcher([UP]);
		await up.it.onStartup();
		await up.it.onStartup();
		const down = launcher([DOWN]);
		await down.it.onStartup();
		assert.deepStrictEqual(stub.recorded.commands, [
			['workbench.action.browser.open', browserOpen], ['workbench.action.browser.open', browserOpen], ['rapp.brainstem.focus'],
		]);
		assert.deepStrictEqual([up.managed, down.managed], [[AGENTS, AGENTS], [AGENTS]]);
		assert.deepStrictEqual(stub.recorded.trustRequests, [trustAsked(AGENTS), trustAsked(AGENTS)], 'it says which folder it asks about');
		assert.strictEqual(stub.recorded.terminals.length, 0);
	});

	test('the trust question counts once it is answered: a window closed while it shows asks again next time', async () => {
		stub.workspace.workspaceFolders = [{ uri: stub.Uri.file(AGENTS) }];
		stub.workspace.workspaceFile = stub.Uri.file(WORKSPACE_FILE);
		stub.workspace.isTrusted = false;
		const answer = stub.workspace.requestWorkspaceTrust;
		const profile = new Map<string, unknown>();
		try {
			stub.workspace.requestWorkspaceTrust = async (options?: unknown) => (stub.recorded.trustRequests.push(options), new Promise<boolean>(() => undefined));
			void launcher([DOWN], 0, ADDRESS, profile).it.onStartup();
			await sleep(30);
			assert.strictEqual(stub.recorded.trustRequests.length, 1);
			assert.ok(!profile.has('rapp.trustAskedFor'), 'a question nobody answered was remembered as asked');
			stub.workspace.requestWorkspaceTrust = answer;
			await launcher([DOWN], 0, ADDRESS, profile).it.onStartup();
			await launcher([DOWN], 0, ADDRESS, profile).it.onStartup();
			assert.strictEqual(stub.recorded.trustRequests.length, 2, 'once answered, it is not asked again');
			assert.deepStrictEqual(profile.get('rapp.trustAskedFor'), [`${WORKSPACE_FILE}\n${AGENTS}`], 'by the paths the host trusts (the workspace file, and the folder as written, not where a link leads)');
		} finally {
			stub.workspace.requestWorkspaceTrust = answer;
		}
	});

	test('the Brainstem data folder joins the RAPP Workspace as its read-only brainstem-data: root, which asks for no trust of its own', async () => {
		const DATA = path.join(FOLDER, '.brainstem_data');
		fs.mkdirSync(path.join(DATA, 'shared_memories'), { recursive: true });
		try {
			const profile = new Map<string, unknown>();
			stub.workspace.isTrusted = false;
			openWorkspaceFile(WORKSPACE_FILE, [AGENTS]);
			await launcher([DOWN], 0, ADDRESS, profile).it.onStartup();
			const written = JSON.parse(fs.readFileSync(WORKSPACE_FILE, 'utf8'));
			assert.deepStrictEqual(written.folders, [{ name: 'Agents', path: AGENTS }, { name: 'Brainstem data', uri: dataUri(DATA) }], 'the open workspace file gains the data root');
			assert.strictEqual(written.settings['files.readonlyInclude'], undefined, 'its provider keeps it read-only; no glob is needed');
			stub.workspace.workspaceFolders = [{ uri: stub.Uri.file(AGENTS) }, { uri: stub.Uri.parse(dataUri(DATA)) }];
			stub.recorded.commands.length = 0;
			const it = launcher([UP], 0, ADDRESS, profile).it;
			await it.onStartup();
			await it.openFolder();
			assert.deepStrictEqual(stub.recorded.commands.map(([id]) => id), ['workbench.action.browser.open', 'workbench.action.browser.open'], 'still the RAPP Workspace: its page is shown, not the workspace opened again');
			assert.deepStrictEqual(stub.recorded.trustRequests, [trustAsked(AGENTS)], 'asked once, about the folder on disk');
		} finally {
			fs.rmSync(DATA, { recursive: true, force: true });
		}
	});

	test('a data folder that appears while the RAPP Workspace is open joins it then', async () => {
		const DATA = path.join(FOLDER, '.brainstem_data');
		openWorkspaceFile(WORKSPACE_FILE, [AGENTS]);
		const { it } = launcher([DOWN]);
		await it.onStartup();
		assert.deepStrictEqual(JSON.parse(fs.readFileSync(WORKSPACE_FILE, 'utf8')).folders, [{ name: 'Agents', path: AGENTS }]);
		const watcher = stub.recorded.watchers.find(w => w.pattern.pattern === '.brainstem_data');
		assert.ok(watcher, 'the Brainstem\'s folder is watched for its data folder');
		assert.strictEqual(watcher.pattern.baseUri.fsPath, FOLDER);
		fs.mkdirSync(DATA);
		try {
			watcher.fireCreate(stub.Uri.file(DATA));
			assert.deepStrictEqual(JSON.parse(fs.readFileSync(WORKSPACE_FILE, 'utf8')).folders, [{ name: 'Agents', path: AGENTS }, { name: 'Brainstem data', uri: dataUri(DATA) }]);
			assert.ok(watcher.disposed, 'and then no longer watched');
			it.dispose();
		} finally {
			fs.rmSync(DATA, { recursive: true, force: true });
		}
	});

	test('a click runs the folder\'s own start script once, however often it is clicked, then shows the web UI', async () => {
		const { it, starting } = launcher([DOWN, UP], 50);
		const first = it.start();
		await sleep(10);
		await it.start();
		await first;
		const own = startCommand(FOLDER, []);
		assert.ok(own);
		assert.deepStrictEqual(stub.recorded.terminals.map(t => ({ options: t.options, sent: t.sent })), [
			{ options: { name: 'Brainstem', cwd: FOLDER, shellPath: own.shellPath, shellArgs: own.shellArgs, env: { [START_STATUS_ENV]: statusFileOf(stub.recorded.terminals[0]) }, isTransient: true }, sent: [] },
		], 'the script is the terminal\'s own process, and the terminal is not revived after a restart');
		assert.match(path.relative(STORAGE, statusFileOf(stub.recorded.terminals[0])), new RegExp(`^start-status-${process.pid}-\\d+-\\d+$`), 'its own status file, in the app\'s storage, named for this window and this start');
		assert.deepStrictEqual(starting, [true, false]);
		// Opened once, never reloaded: a tab that could only show that nothing answered loads again in the host.
		assert.deepStrictEqual(stub.recorded.commands, [['workbench.action.browser.open', browserOpen]]);
	});

	test('a start script still running is shown, not run again; once it has ended, its terminal gives way to a new one', async () => {
		const { it } = launcher([DOWN]);
		const first = it.start();
		await sleep(20);
		await it.start();
		assert.strictEqual(stub.recorded.terminals.length, 1, 'a second click while it starts runs nothing');
		it.dispose();
		await first;
		const [running] = stub.recorded.terminals;
		await it.start();
		assert.deepStrictEqual([stub.recorded.terminals.length, running.shown, running.disposed], [1, 3, false], 'the script still runs: its terminal is shown again');
		assert.match(stub.recorded.messages.join('\n'), /start script is still running in its terminal/);
		running.exitStatus = { code: 1 };
		await it.start();
		assert.deepStrictEqual([stub.recorded.terminals.length, running.disposed], [2, true], 'the ended one is closed, and a new one runs the script');
	});

	test('a Brainstem that already answers is shown, not started again', async () => {
		await launcher([UP]).it.start();
		assert.deepStrictEqual([stub.recorded.terminals.length, commandIds()], [0, ['workbench.action.browser.open']]);
	});

	test('in Restricted Mode, Start in the RAPP Workspace asks for trust in the Brainstem\'s words, naming the folder, and starts nothing without it', async () => {
		stub.workspace.workspaceFolders = [{ uri: stub.Uri.file(AGENTS) }];
		stub.workspace.workspaceFile = stub.Uri.file(WORKSPACE_FILE);
		stub.workspace.isTrusted = false;
		const answer = stub.workspace.requestWorkspaceTrust;
		try {
			stub.workspace.requestWorkspaceTrust = async (options?: unknown) => (stub.recorded.trustRequests.push(options), undefined as unknown as boolean);
			await launcher([DOWN]).it.start();
			assert.deepStrictEqual([stub.recorded.trustRequests, stub.recorded.terminals.length], [[{ message: `${START_TRUST}\n\nFolder: \` ${AGENTS} \`` }], 0]);
			assert.match(stub.recorded.messages.join('\n'), /was not started: this window is in Restricted Mode/);
			stub.workspace.requestWorkspaceTrust = answer;
			const { it } = launcher([DOWN]);
			const run = it.start();
			await sleep(20);
			assert.strictEqual(stub.recorded.terminals.length, 1, 'trusted, it starts');
			it.dispose();
			await run;
		} finally {
			stub.workspace.requestWorkspaceTrust = answer;
		}
	});

	test('any other window in Restricted Mode starts nothing and asks no trust in the Brainstem\'s name: it offers the RAPP Workspace in a new window', async () => {
		const other = path.join(ROOT, 'some-project');
		fs.mkdirSync(other, { recursive: true });
		stub.workspace.workspaceFolders = [{ uri: stub.Uri.file(other) }];
		stub.workspace.isTrusted = false;
		let answer: (pick: string | undefined) => void = () => undefined;
		stub.window.showInformationMessage = (message: string) => (stub.recorded.messages.push(message), new Promise(resolve => (answer = resolve)));
		const { it } = launcher([DOWN]);
		await it.start();
		assert.deepStrictEqual([stub.recorded.trustRequests.length, stub.recorded.terminals.length], [0, 0], 'returned without waiting for the notice');
		assert.match(stub.recorded.messages.join('\n'), /this window is in Restricted Mode\. Open your Brainstem to start it from its RAPP Workspace, in a window of its own\./);
		stub.workspace.isTrusted = true;
		const run = it.start();
		await sleep(20);
		assert.strictEqual(stub.recorded.terminals.length, 1, 'a notice nobody answered does not hold Start');
		it.dispose();
		await run;
		stub.workspace.isTrusted = false;
		answer('Open your Brainstem');
		await sleep(20);
		assert.deepStrictEqual(stub.recorded.commands.filter(([id]) => id === 'vscode.openFolder').map(([, uri, options]) => [(uri as { fsPath: string }).fsPath, options]), [[OWN_FILE, { forceNewWindow: true }]], 'the window keeps its folder');
	});

	test('from a window the app treats as the RAPP Workspace though its file is from elsewhere, Open your Brainstem opens a window of its own', async () => {
		const saved = path.join(ROOT, 'Documents', 'Saved.code-workspace');
		stub.workspace.workspaceFolders = [{ uri: stub.Uri.file(AGENTS) }];
		stub.workspace.workspaceFile = stub.Uri.file(saved);
		const { it, managed } = launcher([UP]);
		await it.onStartup();
		stub.recorded.commands.length = 0;
		await it.openFolder();
		assert.deepStrictEqual([managed, stub.recorded.commands.map(([id, uri, options]) => [id, (uri as { fsPath?: string })?.fsPath, options])],
			[[AGENTS], [['vscode.openFolder', OWN_FILE, { forceNewWindow: true }]]], 'so this window keeps its conversation');
		it.dispose();
	});

	test('a workspace file from elsewhere is never trusted in the Brainstem\'s words, even with only agents/ in it', async () => {
		const foreign = path.join(ROOT, 'Downloads', 'RAPP Workspace.code-workspace');
		stub.workspace.workspaceFolders = [{ uri: stub.Uri.file(AGENTS) }];
		stub.workspace.workspaceFile = stub.Uri.file(foreign);
		stub.workspace.isTrusted = false;
		const { it } = launcher([DOWN]);
		await it.onStartup();
		await it.start();
		assert.deepStrictEqual([stub.recorded.trustRequests.length, stub.recorded.terminals.length], [0, 0]);
		assert.match(stub.recorded.messages.join('\n'), /Open your Brainstem to start it from its RAPP Workspace/);
		stub.recorded.commands.length = 0;
		await it.openFolder(true);
		assert.deepStrictEqual(stub.recorded.commands.map(([id, uri, options]) => [id, (uri as { fsPath?: string })?.fsPath, options]), [['vscode.openFolder', OWN_FILE, { forceNewWindow: true }]], 'Open your Brainstem opens the app\'s own RAPP Workspace');
	});

	test('a window on an older Agents folder opens this Agents folder\'s own workspace, a new one, and never changes its own in place', async () => {
		const older = path.join(ROOT, 'old-agents');
		const olderFile = JSON.stringify({ folders: [{ name: 'Agents', path: older }], settings: { 'window.title': 'RAPP Workspace' } });
		fs.mkdirSync(STORAGE, { recursive: true });
		fs.writeFileSync(WORKSPACE_FILE, olderFile);
		stub.workspace.workspaceFolders = [{ uri: stub.Uri.file(older) }];
		stub.workspace.workspaceFile = stub.Uri.file(WORKSPACE_FILE);
		stub.workspace.isTrusted = false;
		writeShown({ launch: LAUNCH, hosts: [process.pid], leftAt: 0 });
		await launcher([DOWN]).it.openFolder();
		assert.deepStrictEqual([stub.recorded.commands.map(([id, uri, options]) => [id, (uri as { fsPath?: string })?.fsPath, options]), stub.recorded.trustRequests.length],
			[[['vscode.openFolder', OWN_FILE, { forceNewWindow: true }]], 0], 'a new workspace in a window of its own, which the host judges afresh and the Brainstem asks about by name when it opens');
		assert.strictEqual(fs.readFileSync(WORKSPACE_FILE, 'utf8'), olderFile, 'the open one is left as it is, and so is its conversation');
		assert.deepStrictEqual(shownNote().hosts, [process.pid], 'this window did not leave anything');
	});

	test('in the app\'s own file, agents/ anywhere among the roots is the RAPP Workspace: shown, watched, and never reordered', async () => {
		const data = path.join(FOLDER, '.brainstem_data');
		fs.mkdirSync(data, { recursive: true });
		after(() => fs.rmSync(data, { recursive: true, force: true }));
		const arranged = JSON.stringify({ folders: [{ name: 'Brainstem data', uri: dataUri(data) }, { name: 'Agents', path: AGENTS }], settings: { 'window.title': 'RAPP Workspace' } });
		fs.mkdirSync(STORAGE, { recursive: true });
		fs.writeFileSync(WORKSPACE_FILE, arranged);
		stub.workspace.workspaceFolders = [{ uri: stub.Uri.parse(dataUri(data)) }, { uri: stub.Uri.file(AGENTS) }];
		stub.workspace.workspaceFile = stub.Uri.file(WORKSPACE_FILE);
		const { it, managed } = launcher([UP]);
		await it.onStartup();
		await it.openFolder();
		assert.deepStrictEqual([commandIds(), managed], [['workbench.action.browser.open', 'workbench.action.browser.open'], [AGENTS]]);
		assert.deepStrictEqual(JSON.parse(fs.readFileSync(WORKSPACE_FILE, 'utf8')).folders.map((f: { name: string }) => f.name), ['Brainstem data', 'Agents'], 'in the order the person gave them');
		assert.ok(!fs.existsSync(path.join(STORAGE, 'workspaces')), 'only the file this window has open is written');
		it.dispose();
		fs.rmSync(data, { recursive: true, force: true });
	});

	test('the app\'s own file with agents/ taken out of it is never rewritten: the RAPP Workspace opens from the next free file, in a window of its own', async () => {
		const mine = JSON.stringify({ folders: [{ name: 'Mine', path: path.join(ROOT, 'some-project') }] });
		fs.mkdirSync(path.dirname(OWN_FILE), { recursive: true });
		fs.writeFileSync(OWN_FILE, mine);
		stub.workspace.workspaceFolders = [{ uri: stub.Uri.file(path.join(ROOT, 'some-project')) }];
		stub.workspace.workspaceFile = stub.Uri.file(OWN_FILE);
		await launcher([DOWN]).it.openFolder();
		assert.deepStrictEqual([stub.recorded.commands.map(([id, uri, options]) => [id, (uri as { fsPath?: string })?.fsPath, options]), fs.readFileSync(OWN_FILE, 'utf8')],
			[[['vscode.openFolder', NEXT_FILE, { forceNewWindow: true }]], mine]);
		assert.deepStrictEqual(JSON.parse(fs.readFileSync(NEXT_FILE, 'utf8')).folders, [{ name: 'Agents', path: AGENTS }]);
	});

	test('another window\'s file is never rewritten either: an empty window starting up leaves it and opens the next free one', async () => {
		const mine = JSON.stringify({ folders: [{ name: 'Mine', path: path.join(ROOT, 'some-project') }] });
		fs.mkdirSync(path.dirname(OWN_FILE), { recursive: true });
		fs.writeFileSync(OWN_FILE, mine);
		await launcher([DOWN]).it.onStartup();
		assert.deepStrictEqual([stub.recorded.commands.map(([id, uri]) => [id, (uri as { fsPath?: string })?.fsPath]), fs.readFileSync(OWN_FILE, 'utf8')], [[['vscode.openFolder', NEXT_FILE]], mine]);
	});

	test('a root added or taken out without a reload: the window enters or leaves the RAPP Workspace as it happens', async () => {
		const mine = path.join(ROOT, 'some-project');
		stub.workspace.workspaceFolders = [{ uri: stub.Uri.file(AGENTS) }];
		stub.workspace.workspaceFile = stub.Uri.file(WORKSPACE_FILE);
		const { it, managed } = launcher([UP]);
		await it.onStartup();
		assert.deepStrictEqual([managed, shownNote().hosts.includes(process.pid)], [[AGENTS], true]);
		stub.workspace.workspaceFolders = [{ uri: stub.Uri.file(mine) }];
		stub.workspace.fireWorkspaceFolders();
		await sleep(20);
		assert.deepStrictEqual([managed, shownNote().hosts.includes(process.pid)], [[AGENTS, undefined], false], 'agents/ taken out: no longer watched or counted');
		stub.workspace.workspaceFolders = [{ uri: stub.Uri.file(mine) }, { uri: stub.Uri.file(AGENTS) }];
		stub.workspace.fireWorkspaceFolders();
		await sleep(20);
		assert.deepStrictEqual([managed, shownNote().hosts.includes(process.pid)], [[AGENTS, undefined, AGENTS], true], 'added back (Add Folder to Workspace puts it last): the RAPP Workspace again');
		stub.workspace.fireWorkspaceFolders();
		await sleep(20);
		assert.deepStrictEqual(managed, [AGENTS, undefined, AGENTS], 'a change that leaves it the RAPP Workspace enters nothing again');
		it.dispose();
	});

	test('a RAPP Workspace file that cannot be read now is left exactly as it is', { skip: (process.platform === 'win32' || process.getuid?.() === 0) && 'needs a file its owner cannot read' }, async () => {
		const text = JSON.stringify({ folders: [{ name: 'Agents', path: AGENTS }, { name: 'Mine', path: path.join(ROOT, 'some-project') }], settings: { 'editor.fontSize': 15 } });
		fs.mkdirSync(path.dirname(OWN_FILE), { recursive: true });
		fs.writeFileSync(OWN_FILE, text);
		fs.chmodSync(OWN_FILE, 0o000);
		try {
			stub.workspace.workspaceFolders = [{ uri: stub.Uri.file(AGENTS) }, { uri: stub.Uri.file(path.join(ROOT, 'some-project')) }];
			stub.workspace.workspaceFile = stub.Uri.file(OWN_FILE);
			const { it, managed } = launcher([UP]);
			await it.onStartup();
			assert.deepStrictEqual(managed, [AGENTS]);
			it.dispose();
		} finally {
			fs.chmodSync(OWN_FILE, 0o644);
		}
		assert.strictEqual(fs.readFileSync(OWN_FILE, 'utf8'), text);
	});

	test('a RAPP Workspace file that cannot be read now is passed over this time and left exactly as it is: the next free one opens', { skip: (process.platform === 'win32' || process.getuid?.() === 0) && 'needs a file its owner cannot read' }, async () => {
		const text = JSON.stringify({ folders: [{ name: 'Agents', path: AGENTS }], settings: { 'editor.fontSize': 15 } });
		fs.mkdirSync(path.dirname(OWN_FILE), { recursive: true });
		fs.writeFileSync(OWN_FILE, text);
		fs.chmodSync(OWN_FILE, 0o000);
		try {
			await launcher([DOWN]).it.onStartup();
			assert.deepStrictEqual(stub.recorded.commands.map(([id, uri]) => [id, (uri as { fsPath?: string })?.fsPath]), [['vscode.openFolder', NEXT_FILE]], 'the host could not open it either');
		} finally {
			fs.chmodSync(OWN_FILE, 0o644);
		}
		assert.strictEqual(fs.readFileSync(OWN_FILE, 'utf8'), text);
		stub.recorded.commands.length = 0;
		// A later launch (the note of a window that just switched keeps an empty window empty for a moment).
		fs.rmSync(SHOWN_FILE, { force: true });
		await launcher([DOWN]).it.onStartup();
		assert.deepStrictEqual(stub.recorded.commands.map(([id, uri]) => [id, (uri as { fsPath?: string })?.fsPath]), [['vscode.openFolder', OWN_FILE]], 'once it can be read again, it is this folder\'s file again');
	});

	test('a file the host itself would refuse (empty, or cut short before its folders) is passed over and left as it is: the next free one opens', async () => {
		for (const broken of ['', '{ "settings": { "editor.fontSize": 15 }, "fold']) {
			fs.mkdirSync(path.dirname(OWN_FILE), { recursive: true });
			fs.writeFileSync(OWN_FILE, broken);
			stub.recorded.commands.length = 0;
			fs.rmSync(SHOWN_FILE, { force: true });
			await launcher([DOWN]).it.onStartup();
			assert.deepStrictEqual([stub.recorded.commands.map(([id, uri]) => [id, (uri as { fsPath?: string })?.fsPath]), fs.readFileSync(OWN_FILE, 'utf8')], [[['vscode.openFolder', NEXT_FILE]], broken], JSON.stringify(broken));
			assert.deepStrictEqual(JSON.parse(fs.readFileSync(NEXT_FILE, 'utf8')).folders, [{ name: 'Agents', path: AGENTS }]);
			fs.rmSync(path.join(STORAGE, 'workspaces'), { recursive: true, force: true });
		}
	});

	test('the file earlier builds kept, with a slip the host reads past, stays in use while it lists this Agents folder', async () => {
		const slipped = `{ "folders": [{ "name": "Mine", "path": ${JSON.stringify(path.join(ROOT, 'some-project'))} } { "name": "Agents", "path": ${JSON.stringify(AGENTS)} }] }\n`;
		fs.mkdirSync(STORAGE, { recursive: true });
		fs.writeFileSync(WORKSPACE_FILE, slipped);
		await launcher([DOWN]).it.onStartup();
		assert.deepStrictEqual([stub.recorded.commands.map(([id, uri]) => [id, (uri as { fsPath?: string })?.fsPath]), fs.readFileSync(WORKSPACE_FILE, 'utf8'), fs.existsSync(OWN_FILE)],
			[[['vscode.openFolder', WORKSPACE_FILE]], slipped, false]);
	});

	test('a slip in its file that the host reads past keeps it this folder\'s: opened as it is, never rewritten, and no second file', async () => {
		const data = path.join(FOLDER, '.brainstem_data');
		fs.mkdirSync(data, { recursive: true });
		// A missing comma after the folders: the host's reader keeps going past it, the app's stops.
		const slipped = `{\n\t"folders": [{ "name": "Agents", "path": ${JSON.stringify(AGENTS)} }]\n\t"settings": { "editor.fontSize": 15 }\n}\n`;
		fs.mkdirSync(path.dirname(OWN_FILE), { recursive: true });
		fs.writeFileSync(OWN_FILE, slipped);
		try {
			await launcher([DOWN]).it.onStartup();
			assert.deepStrictEqual(stub.recorded.commands.map(([id, uri]) => [id, (uri as { fsPath?: string })?.fsPath]), [['vscode.openFolder', OWN_FILE]], 'an empty window opens it');
			stub.recorded.commands.length = 0;
			// The window it opened in, whose roots the host read past the slip.
			stub.workspace.workspaceFile = stub.Uri.file(OWN_FILE);
			stub.workspace.workspaceFolders = [{ uri: stub.Uri.file(AGENTS) }];
			const { it, managed } = launcher([UP]);
			await it.onStartup();
			await it.openFolder();
			assert.deepStrictEqual([managed, commandIds()], [[AGENTS], ['workbench.action.browser.open', 'workbench.action.browser.open']], 'it is the RAPP Workspace, and Open your Brainstem shows its page');
			it.dispose();
		} finally {
			fs.rmSync(data, { recursive: true, force: true });
		}
		assert.deepStrictEqual([fs.readFileSync(OWN_FILE, 'utf8'), fs.existsSync(path.dirname(NEXT_FILE))], [slipped, false], 'its data root waits until it reads as JSON again');
	});

	test('agents/ taken out of a file with a slip in it: Open your Brainstem opens the next free file, and leaves that one as it is', async () => {
		const mine = path.join(ROOT, 'some-project');
		const slipped = `{ "folders": [{ "name": "Mine", "path": ${JSON.stringify(mine)} }] "settings": {} }\n`;
		fs.mkdirSync(path.dirname(OWN_FILE), { recursive: true });
		fs.writeFileSync(OWN_FILE, slipped);
		stub.workspace.workspaceFile = stub.Uri.file(OWN_FILE);
		stub.workspace.workspaceFolders = [{ uri: stub.Uri.file(mine) }];
		await launcher([DOWN]).it.openFolder();
		assert.deepStrictEqual([stub.recorded.commands.map(([id, uri, options]) => [id, (uri as { fsPath?: string })?.fsPath, options]), fs.readFileSync(OWN_FILE, 'utf8')],
			[[['vscode.openFolder', NEXT_FILE, { forceNewWindow: true }]], slipped]);
	});

	test('with the Brainstem\'s folder unknown (not running, none at the default), the open file keeps its data root', async () => {
		const data = path.join(FOLDER, '.brainstem_data');
		const text = JSON.stringify({ folders: [{ name: 'Agents', path: AGENTS }, { name: 'Brainstem data', uri: dataUri(data) }] });
		fs.mkdirSync(path.dirname(OWN_FILE), { recursive: true });
		fs.writeFileSync(OWN_FILE, text);
		stub.workspace.workspaceFile = stub.Uri.file(OWN_FILE);
		stub.workspace.workspaceFolders = [{ uri: stub.Uri.file(AGENTS) }, { uri: stub.Uri.parse(dataUri(data)) }];
		await withHome(path.join(ROOT, 'home-without-a-brainstem'), async () => {
			const { it, managed } = launcher([DOWN], 0, ADDRESS, new Map(), { brainstemFolder: '', agentsFolder: AGENTS });
			await it.onStartup();
			assert.deepStrictEqual(managed, [AGENTS], 'still the RAPP Workspace');
			it.dispose();
		});
		assert.strictEqual(fs.readFileSync(OWN_FILE, 'utf8'), text);
	});

	test('an Agents folder set apart from the Brainstem found by default keeps its file: another Brainstem\'s data never joins it', async () => {
		const home = path.join(ROOT, 'home-with-a-default');
		const other = path.join(home, '.brainstem', 'src', 'rapp_brainstem');
		fs.mkdirSync(path.join(other, 'agents'), { recursive: true });
		fs.mkdirSync(path.join(other, '.brainstem_data'), { recursive: true });
		fs.writeFileSync(path.join(other, 'brainstem.py'), 'raise SystemExit("never run by the tests")\n');
		const data = path.join(FOLDER, '.brainstem_data');
		const text = JSON.stringify({ folders: [{ name: 'Agents', path: AGENTS }, { name: 'Brainstem data', uri: dataUri(data) }] });
		fs.mkdirSync(path.dirname(OWN_FILE), { recursive: true });
		fs.writeFileSync(OWN_FILE, text);
		const otherAgents = path.join(other, 'agents');
		const otherFile = path.join(STORAGE, 'workspaces', workspaceKey(otherAgents), 'RAPP Workspace.code-workspace');
		fs.mkdirSync(path.dirname(otherFile), { recursive: true });
		fs.writeFileSync(otherFile, JSON.stringify({ folders: [{ name: 'Agents', path: otherAgents }] }));
		try {
			await withHome(home, async () => {
				stub.workspace.workspaceFile = stub.Uri.file(OWN_FILE);
				stub.workspace.workspaceFolders = [{ uri: stub.Uri.file(AGENTS) }, { uri: stub.Uri.parse(dataUri(data)) }];
				const first = launcher([DOWN], 0, ADDRESS, new Map(), { brainstemFolder: '', agentsFolder: AGENTS });
				await first.it.onStartup();
				first.it.dispose();
				assert.strictEqual(fs.readFileSync(OWN_FILE, 'utf8'), text, 'while its own Brainstem is down, its data root stays that Brainstem\'s');
				stub.workspace.workspaceFile = stub.Uri.file(otherFile);
				stub.workspace.workspaceFolders = [{ uri: stub.Uri.file(otherAgents) }];
				const second = launcher([DOWN], 0, ADDRESS, new Map(), { brainstemFolder: '', agentsFolder: otherAgents });
				await second.it.onStartup();
				second.it.dispose();
			});
			assert.deepStrictEqual(JSON.parse(fs.readFileSync(otherFile, 'utf8')).folders[1], { name: 'Brainstem data', uri: dataUri(path.join(other, '.brainstem_data')) }, 'set to the agents/ of the Brainstem found, its data joins');
		} finally {
			fs.rmSync(home, { recursive: true, force: true });
		}
	});

	test('an Agents folder set through a link to the found Brainstem\'s own agents/ is that Brainstem\'s: its data joins', async () => {
		const home = path.join(ROOT, 'home-with-a-linked-default');
		const other = path.join(home, '.brainstem', 'src', 'rapp_brainstem');
		fs.mkdirSync(path.join(other, 'agents'), { recursive: true });
		fs.mkdirSync(path.join(other, '.brainstem_data'), { recursive: true });
		fs.writeFileSync(path.join(other, 'brainstem.py'), 'raise SystemExit("never run by the tests")\n');
		const link = path.join(home, 'my-agents');
		fs.symlinkSync(path.join(other, 'agents'), link, 'junction');
		const file = path.join(STORAGE, 'workspaces', workspaceKey(link), 'RAPP Workspace.code-workspace');
		fs.mkdirSync(path.dirname(file), { recursive: true });
		fs.writeFileSync(file, JSON.stringify({ folders: [{ name: 'Agents', path: link }] }));
		try {
			await withHome(home, async () => {
				stub.workspace.workspaceFile = stub.Uri.file(file);
				stub.workspace.workspaceFolders = [{ uri: stub.Uri.file(link) }];
				const { it, managed } = launcher([DOWN], 0, ADDRESS, new Map(), { brainstemFolder: '', agentsFolder: link });
				await it.onStartup();
				it.dispose();
				assert.deepStrictEqual(managed, [link]);
			});
			assert.deepStrictEqual(JSON.parse(fs.readFileSync(file, 'utf8')).folders, [{ name: 'Agents', path: link }, { name: 'Brainstem data', uri: dataUri(path.join(other, '.brainstem_data')) }]);
		} finally {
			fs.rmSync(home, { recursive: true, force: true });
		}
	});

	test('with another program on the Brainstem\'s address, Start runs nothing and says why', async () => {
		const occupied: Status = { state: 'not-running', reason: `something else answers at ${ADDRESS} (HTTP 404)`, occupied: true };
		await launcher([occupied]).it.start();
		assert.deepStrictEqual([stub.recorded.terminals.length, commandIds()], [0, ['rapp.brainstem.focus']]);
		assert.match(stub.recorded.messages.join('\n'), /Your Brainstem was not started: something else is using its address \(http:\/\/127\.0\.0\.1:7071\)\. Close that program, then start your Brainstem\./);
	});

	test('a Brainstem that is running but slow to answer is never started a second time', async () => {
		const busy: Status = { state: 'not-running', reason: 'no answer within 5 s', busy: true };
		await launcher([busy]).it.start();
		assert.deepStrictEqual([stub.recorded.terminals.length, commandIds()], [0, ['rapp.brainstem.focus']]);
		assert.match(stub.recorded.messages.join('\n'), /Your Brainstem is already running\. It is busy and will answer in a moment\./);
	});

	test('with something on the Brainstem\'s address that closes every connection, Start runs nothing and points to a new agent', async () => {
		const dropped: Status = { state: 'not-running', reason: 'socket hang up', dropped: true };
		await launcher([dropped]).it.start();
		assert.deepStrictEqual([stub.recorded.terminals.length, commandIds()], [0, ['rapp.brainstem.focus']]);
		assert.match(stub.recorded.messages.join('\n'), /Your Brainstem was not started: something on its address closes every connection without an answer\. If you just added an agent, move it out of the top of agents\/, then check again\./);
	});

	test('a window whose open file is gone never makes it again: only Open your Brainstem and an empty window\'s startup make one', async () => {
		stub.workspace.workspaceFile = stub.Uri.file(OWN_FILE);
		stub.workspace.workspaceFolders = [{ uri: stub.Uri.file(AGENTS) }];
		const { it, managed } = launcher([UP]);
		await it.onStartup();
		assert.deepStrictEqual([managed, fs.existsSync(OWN_FILE)], [[AGENTS], false]);
		it.dispose();
	});

	test('a person\'s own root to another Brainstem\'s data folder is kept; this Brainstem\'s joins after Agents', async () => {
		const data = path.join(FOLDER, '.brainstem_data');
		const theirs = { name: 'Old memory', path: path.join(ROOT, 'old-brainstem', '.brainstem_data') };
		fs.mkdirSync(data, { recursive: true });
		fs.mkdirSync(path.dirname(OWN_FILE), { recursive: true });
		fs.writeFileSync(OWN_FILE, JSON.stringify({ folders: [{ name: 'Agents', path: AGENTS }, theirs] }));
		stub.workspace.workspaceFile = stub.Uri.file(OWN_FILE);
		stub.workspace.workspaceFolders = [{ uri: stub.Uri.file(AGENTS) }, { uri: stub.Uri.file(theirs.path) }];
		try {
			const { it } = launcher([UP]);
			await it.onStartup();
			it.dispose();
			assert.deepStrictEqual(JSON.parse(fs.readFileSync(OWN_FILE, 'utf8')).folders, [{ name: 'Agents', path: AGENTS }, { name: 'Brainstem data', uri: dataUri(data) }, theirs]);
		} finally {
			fs.rmSync(data, { recursive: true, force: true });
		}
	});

	test('a root of any other kind (not on this disk, not the data root) makes trust the host\'s to ask: the Brainstem asks nothing', async () => {
		stub.workspace.workspaceFile = stub.Uri.file(WORKSPACE_FILE);
		stub.workspace.workspaceFolders = [{ uri: stub.Uri.file(AGENTS) }, { uri: stub.Uri.parse('memfs:/elsewhere') }];
		stub.workspace.isTrusted = false;
		const { it, managed } = launcher([DOWN]);
		await it.onStartup();
		assert.deepStrictEqual([managed, stub.recorded.trustRequests.length], [[AGENTS], 0]);
		it.dispose();
	});

	test('after an earlier build\'s plain data root becomes the app\'s own, agents/ is alone and the Brainstem asks', async () => {
		const data = path.join(FOLDER, '.brainstem_data');
		fs.mkdirSync(data, { recursive: true });
		try {
			fs.mkdirSync(STORAGE, { recursive: true });
			fs.writeFileSync(WORKSPACE_FILE, JSON.stringify({ folders: [{ name: 'Agents', path: AGENTS }, { name: 'Brainstem data', path: data }] }));
			stub.workspace.workspaceFolders = [{ uri: stub.Uri.file(AGENTS) }, { uri: stub.Uri.file(data) }];
			stub.workspace.workspaceFile = stub.Uri.file(WORKSPACE_FILE);
			stub.workspace.isTrusted = false;
			const { it } = launcher([DOWN]);
			await it.onStartup();
			assert.strictEqual(stub.recorded.trustRequests.length, 0, 'not while the plain data folder is a root: the click would trust it too');
			assert.deepStrictEqual(JSON.parse(fs.readFileSync(WORKSPACE_FILE, 'utf8')).folders[1], { name: 'Brainstem data', uri: dataUri(data) });
			stub.workspace.workspaceFolders = [{ uri: stub.Uri.file(AGENTS) }, { uri: stub.Uri.parse(dataUri(data)) }];
			stub.workspace.fireWorkspaceFolders();
			await sleep(20);
			assert.deepStrictEqual(stub.recorded.trustRequests, [trustAsked(AGENTS)], 'once the host follows the file, agents/ is alone');
			it.dispose();
		} finally {
			fs.rmSync(data, { recursive: true, force: true });
		}
	});

	test('with other folders on disk in the RAPP Workspace, trust is the host\'s to ask: the Brainstem asks nothing, and Start says how', async () => {
		const mine = path.join(ROOT, 'some-project');
		stub.workspace.workspaceFolders = [{ uri: stub.Uri.file(mine) }, { uri: stub.Uri.file(AGENTS) }];
		stub.workspace.workspaceFile = stub.Uri.file(WORKSPACE_FILE);
		stub.workspace.isTrusted = false;
		const { it } = launcher([DOWN]);
		await it.onStartup();
		await it.start();
		assert.deepStrictEqual([stub.recorded.trustRequests.length, stub.recorded.terminals.length], [0, 0]);
		assert.match(stub.recorded.messages.join('\n'), /holds other folders too\. Trust them with Manage Workspace Trust/);
		it.dispose();
	});

	test('a workspace file that cannot be written never stops the window from showing the RAPP Workspace', async () => {
		const blocked = path.join(STORAGE, 'workspaces', '0123456789abcdef');
		fs.mkdirSync(path.dirname(blocked), { recursive: true });
		fs.writeFileSync(blocked, 'a file where a folder should be');
		const file = path.join(blocked, 'RAPP Workspace.code-workspace');
		stub.workspace.workspaceFolders = [{ uri: stub.Uri.file(AGENTS) }];
		stub.workspace.workspaceFile = stub.Uri.file(file);
		const { it, managed } = launcher([UP]);
		await it.onStartup();
		assert.deepStrictEqual([managed, commandIds(), shownNote().hosts.includes(process.pid)], [[AGENTS], ['workbench.action.browser.open'], true]);
		it.dispose();
		fs.rmSync(blocked, { force: true });
	});

	test('a new workspace file for a folder already asked about asks once more: the host trusts a workspace with its file', async () => {
		stub.workspace.workspaceFolders = [{ uri: stub.Uri.file(AGENTS) }];
		stub.workspace.isTrusted = false;
		const profile = new Map<string, unknown>([['rapp.trustAskedFor', [`${WORKSPACE_FILE}\n${AGENTS}`]]]);
		stub.workspace.workspaceFile = stub.Uri.file(WORKSPACE_FILE);
		await launcher([DOWN], 0, ADDRESS, profile).it.onStartup();
		assert.strictEqual(stub.recorded.trustRequests.length, 0, 'asked before in this workspace file');
		stub.workspace.workspaceFile = stub.Uri.file(OWN_FILE);
		await launcher([DOWN], 0, ADDRESS, profile).it.onStartup();
		assert.deepStrictEqual(stub.recorded.trustRequests, [trustAsked(AGENTS)], 'a new one asks, naming the folder');
	});

	test('the file earlier builds kept is reused while it lists this Agents folder anywhere', () => {
		fs.mkdirSync(STORAGE, { recursive: true });
		fs.writeFileSync(WORKSPACE_FILE, JSON.stringify({ folders: [{ name: 'Mine', path: path.join(ROOT, 'some-project') }, { name: 'Agents', path: AGENTS }] }));
		assert.strictEqual(launcher([DOWN]).it.workspaceFileFor(AGENTS), WORKSPACE_FILE);
		assert.strictEqual(launcher([DOWN]).it.workspaceFileFor(path.join(ROOT, 'old-agents')), path.join(STORAGE, 'workspaces', workspaceKey(path.join(ROOT, 'old-agents')), 'RAPP Workspace.code-workspace'));
		fs.rmSync(WORKSPACE_FILE);
		stub.workspace.workspaceFile = stub.Uri.file(WORKSPACE_FILE);
		stub.workspace.workspaceFolders = [{ uri: stub.Uri.file(AGENTS) }];
		assert.strictEqual(launcher([DOWN]).it.workspaceFileFor(AGENTS), OWN_FILE, 'once it is gone, never made again, even while a window still shows it');
	});

	test('a failed open from the Restricted Mode offer says so', async () => {
		const other = path.join(ROOT, 'some-project');
		fs.mkdirSync(other, { recursive: true });
		stub.workspace.workspaceFolders = [{ uri: stub.Uri.file(other) }];
		stub.workspace.isTrusted = false;
		stub.window.showInformationMessage = async (message: string) => (stub.recorded.messages.push(message), 'Open your Brainstem');
		const execute = stub.commands.executeCommand;
		try {
			stub.commands.executeCommand = async (...args: unknown[]) => {
				if (args[0] === 'vscode.openFolder') {
					throw new Error('cannot open');
				}
				stub.recorded.commands.push(args);
			};
			await launcher([DOWN]).it.start();
			await sleep(20);
			assert.ok(stub.recorded.messages.includes('Your RAPP Workspace could not be opened.'));
		} finally {
			stub.commands.executeCommand = execute;
		}
	});

	test('old status files of windows that are gone are swept after a week; others stay', () => {
		fs.mkdirSync(STORAGE, { recursive: true });
		const week = 7 * 24 * 60 * 60 * 1000;
		const names = [`start-status-${ENDED}-${Date.now() - week - 1000}-1`, `start-status-${ENDED}-${Date.now()}-2`, `start-status-${process.pid}-${Date.now() - week - 1000}-3`, 'start-status-notes.txt'];
		names.forEach(name => fs.writeFileSync(path.join(STORAGE, name), '1\n'));
		const stuck = path.join(STORAGE, `start-status-${ENDED}-${Date.now() - week - 1000}-9`);
		fs.mkdirSync(path.join(stuck, 'inside'), { recursive: true });
		assert.doesNotThrow(() => launcher([DOWN]), 'something it cannot remove never stops the app from starting');
		assert.deepStrictEqual(names.map(name => fs.existsSync(path.join(STORAGE, name))), [false, true, true, true]);
		names.forEach(name => fs.rmSync(path.join(STORAGE, name), { force: true }));
		fs.rmSync(stuck, { recursive: true, force: true });
	});

	test('only a status file of the app\'s own, by its exact name in its storage, is ever taken over', async () => {
		const victim = path.join(ROOT, 'victim.txt');
		fs.writeFileSync(victim, 'keep me');
		const sly = stub.window.createTerminal({ name: 'Brainstem', env: { [START_STATUS_ENV]: path.join(STORAGE, 'start-status-x', '..', '..', 'victim.txt') } });
		stub.recorded.terminals.length = 0;
		stub.window.terminals = [sly];
		const { it } = launcher([DOWN]);
		const run = it.start();
		await sleep(20);
		assert.strictEqual(stub.recorded.terminals.length, 1, 'not taken over: a start of its own runs');
		it.dispose();
		await run;
		assert.ok(fs.existsSync(victim), 'and nothing outside the app\'s storage is removed');
	});

	test('after an extension host restart, a start still running is taken over: shown, not run again, and its file kept', async () => {
		const file = path.join(STORAGE, 'start-status-1-2-3');
		fs.mkdirSync(STORAGE, { recursive: true });
		const running = stub.window.createTerminal({ name: 'Brainstem', env: { [START_STATUS_ENV]: file } });
		stub.recorded.terminals.length = 0;
		stub.window.terminals = [running];
		fs.writeFileSync(file, '');
		const { it } = launcher([DOWN]);
		await it.start();
		assert.deepStrictEqual([stub.recorded.terminals.length, running.shown], [0, 1]);
		assert.match(stub.recorded.messages.join('\n'), /start script is still running in its terminal/);
		it.dispose();
		assert.ok(fs.existsSync(file), 'its terminal still runs, so its file stays for the next extension host');
		fs.rmSync(file, { force: true });
	});

	test('a start that stops with an error says so with its exit code, and Start then runs it again', async () => {
		const { it } = launcher([DOWN]);
		const first = it.start();
		await sleep(20);
		const status = statusFileOf(stub.recorded.terminals[0]);
		fs.writeFileSync(status, '3\n');
		await first;
		assert.match(stub.recorded.messages.join('\n'), /Your Brainstem stopped before it answered \(exit code 3\)\. Its terminal shows why\./);
		const [failed] = stub.recorded.terminals;
		assert.strictEqual(failed.exitStatus, undefined, 'its terminal still shows why');
		const again = it.start();
		await sleep(20);
		assert.deepStrictEqual([stub.recorded.terminals.length, failed.disposed, fs.existsSync(status)], [2, true, false], 'the old terminal is closed, its status file removed, and the script runs again');
		assert.notStrictEqual(statusFileOf(stub.recorded.terminals[1]), status, 'with a status file of its own');
		it.dispose();
		await again;
		assert.ok(!fs.existsSync(statusFileOf(stub.recorded.terminals[1])));
	});

	test('another window\'s start never touches this window\'s status', async () => {
		const a = launcher([DOWN]);
		const b = launcher([DOWN]);
		const runA = a.it.start();
		await sleep(5);
		const runB = b.it.start();
		await sleep(20);
		const [fileA, fileB] = stub.recorded.terminals.map(statusFileOf);
		assert.notStrictEqual(fileA, fileB);
		fs.writeFileSync(fileB, '1\n');
		await runB;
		assert.strictEqual(stub.recorded.messages.filter(m => /exit code 1/.test(m)).length, 1, 'only the window whose start failed says so');
		a.it.dispose();
		await runA;
		assert.ok(!stub.recorded.messages.some(m => /exit code/.test(m) && !/exit code 1/.test(m)));
	});
});

describe('Brainstem web UI', () => {
	beforeEach(() => {
		stub.workspace.workspaceFolders = [{ uri: stub.Uri.file(AGENTS) }];
	});

	test('opens in the host\'s integrated browser, reusing any tab on the Brainstem\'s address, IPv6 included', async () => {
		await launcher([UP], 0, 'http://[::1]:7071').it.onStartup();
		assert.deepStrictEqual(stub.recorded.commands, [
			['workbench.action.browser.open', { url: 'http://[::1]:7071/', reuseUrlFilter: 'http://*::1*:7071/**' }],
		]);
		assert.deepStrictEqual(['http://127.0.0.1:7071', 'http://localhost:7071'].map(browserReuseFilter), ['http://127.0.0.1:7071/**', 'http://localhost:7071/**']);
	});

	test('showing it again focuses its tab as it is, never reloading it: Show, Open your Brainstem, a Start that finds it up, a restart', async () => {
		stub.workspace.workspaceFile = stub.Uri.file(WORKSPACE_FILE);
		const it = launcher([UP]).it;
		await it.openUI();
		await it.openFolder();
		await it.start();
		await it.onStartup();
		assert.deepStrictEqual(stub.recorded.commands, Array.from({ length: 4 }, () => ['workbench.action.browser.open', browserOpen]),
			'the reuse filter finds the tab, and the host (with the overlay) does not navigate a tab already on this address');
	});

	test('without the integrated browser, the Simple Browser shows it in the first column and keeps focus where it is', async () => {
		stub.registeredCommands.splice(0, Infinity, 'simpleBrowser.api.open');
		await launcher([UP]).it.openUI();
		assert.deepStrictEqual(stub.recorded.commands.map(([id, uri, options]) => [id, (uri as { fsPath: string }).fsPath, options]), [
			['simpleBrowser.api.open', `${ADDRESS}/`, { viewColumn: stub.ViewColumn.One, preserveFocus: true }],
		]);
	});

	test('with neither browser, it shows the Brainstem view instead of calling a missing command', async () => {
		stub.registeredCommands.length = 0;
		await launcher([UP]).it.openUI();
		assert.deepStrictEqual(stub.recorded.commands, [['rapp.brainstem.focus']]);
	});
});
