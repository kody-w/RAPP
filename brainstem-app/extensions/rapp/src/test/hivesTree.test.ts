// Unit tests for the Hives and References providers, the checker and the Brainstem client, against a
// synthetic Hives folder built under the test temp folder (BRAINSTEM_TEST_TMP, or .test-tmp here).
import * as assert from 'assert';
import * as fs from 'fs';
import * as http from 'http';
import * as net from 'net';
import * as path from 'path';
import { spawnSync } from 'child_process';
import { createHash } from 'crypto';
import { after, before, describe, test } from 'node:test';

const loader = require('module') as { _resolveFilename: (request: string, ...rest: unknown[]) => string };
const resolveFilename = loader._resolveFilename;
loader._resolveFilename = function (this: unknown, request: string, ...rest: unknown[]): string {
	return request === 'vscode' ? path.join(__dirname, 'vscodeStub.js') : resolveFilename.call(this, request, ...rest);
};

const hives = require('../hives') as typeof import('../hives');
const { HivesTreeProvider, NO_HIVES } = require('../hivesTree') as typeof import('../hivesTree');
const { ReferencesTreeProvider } = require('../referencesTree') as typeof import('../referencesTree');
const checker = require('../checker') as typeof import('../checker');
const brainstem = require('../brainstem') as typeof import('../brainstem');
const { shownText } = require('../chatView') as typeof import('../chatView');
const { hardenPinnedPage } = require('../organismView') as typeof import('../organismView');
const { GRAIL, grailOneLiner } = require('../grail') as typeof import('../grail');

type Node = import('../hivesTree').HiveNode;
type Item = { label?: string; description?: string; tooltip?: string; contextValue?: string; command?: { command: string; arguments?: unknown[] }; resourceUri?: { fsPath: string }; collapsibleState: number };

const TMP = path.resolve(process.env.BRAINSTEM_TEST_TMP || path.join(__dirname, '..', '..', '.test-tmp'));
const ROOT = path.join(TMP, `hives-fixture-${process.pid}`);
const HOME = path.join(ROOT, 'Hives');
const HIVE = path.join(HOME, 'team-notes');
const REF = path.join(ROOT, 'notes', 'old-vault');
const PYTHON = process.env.BRAINSTEM_TEST_PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
const hasPython = spawnSync(PYTHON, ['--version']).status === 0;

function write(file: string, text = '# note\n'): void {
	fs.mkdirSync(path.dirname(file), { recursive: true });
	fs.writeFileSync(file, text);
}

function link(target: string, at: string): void {
	try {
		// A folder link is a junction on Windows, which needs no privilege; a file link does.
		fs.symlinkSync(target, at, process.platform === 'win32' && fs.statSync(target).isDirectory() ? 'junction' : undefined);
	} catch {
		// Symlinks need privileges on some systems; the link cases are then simply absent.
	}
}

// A checker file of a test's own, outside every Hive.
function realAgentFor(base: string): string {
	const file = path.join(base, 'checker', 'hive_agent.py');
	fs.mkdirSync(path.dirname(file), { recursive: true });
	fs.writeFileSync(file, '');
	return file;
}

// Whether a file link can be made here (Windows without the privilege cannot).
const canLinkFiles = (() => {
	const probe = path.join(TMP, `file-link-probe-${process.pid}`);
	try {
		fs.mkdirSync(TMP, { recursive: true });
		fs.writeFileSync(`${probe}.target`, '');
		fs.symlinkSync(`${probe}.target`, probe, 'file');
		return true;
	} catch {
		return false;
	} finally {
		fs.rmSync(probe, { force: true });
		fs.rmSync(`${probe}.target`, { force: true });
	}
})();

function buildFixture(): void {
	fs.rmSync(ROOT, { recursive: true, force: true });
	write(path.join(HIVE, '.git', 'rapp-hive', 'device.json'), '{"name": "ana", "device": "laptop"}\n');
	write(path.join(HIVE, '.git', 'rapp-hive', 'references.json'), JSON.stringify({
		'old-vault': REF,
		'gone': path.join(ROOT, 'notes', 'moved-away'),
		'Not A Label': REF,
		'relative': 'notes/old-vault',
	}));
	write(path.join(HIVE, 'HIVE.md'), '---\nhive: h-1\nversion: 1\napprovals: 2\n---\n# Team notes\n');
	write(path.join(HIVE, 'members', 'ana', 'keys', 'laptop.md'));
	write(path.join(HIVE, 'members', 'ana', 'keys', 'phone.md'));
	write(path.join(HIVE, 'members', 'ben', 'keys', 'desk.md'));
	write(path.join(HIVE, 'members', 'cara', 'approvals', 'admit-dev.md'));
	write(path.join(HIVE, 'requests', 'dev', 'tablet.md'));
	write(path.join(HIVE, 'shared', 'plans', '2026-q4.md'));
	write(path.join(HIVE, 'shared', 'plans', 'drafts', 'idea.md'));
	write(path.join(HIVE, 'shared', 'plans', '.hidden.md'));
	write(path.join(HIVE, 'shared', 'notes', 'readme.md'));
	link(path.join(HIVE, 'HIVE.md'), path.join(HIVE, 'shared', 'plans', 'linked.md'));
	write(path.join(HOME, 'not-a-hive', 'README.md'));
	write(path.join(HOME, '.hidden-hive', '.git', 'rapp-hive', 'device.json'), '{}');
	link(HIVE, path.join(HOME, 'linked-hive'));
	const sly = path.join(HOME, 'sly-hive');
	write(path.join(sly, '.git', 'rapp-hive', 'device.json'), '{}');
	write(path.join(ROOT, 'outside', 'secret.md'));
	write(path.join(ROOT, 'outside', 'keys', 'x.md'));
	link(path.join(ROOT, 'outside'), path.join(sly, 'shared'));
	link(path.join(ROOT, 'outside'), path.join(sly, 'members'));
	link(path.join(ROOT, 'outside'), path.join(sly, 'requests'));
	link(HOME, path.join(ROOT, 'Hives-link'));
	write(path.join(REF, 'index.md'));
	write(path.join(ROOT, 'tools', 'fake_checker.py'), [
		'import os, sys',
		'hive = sys.argv[2]',
		'if any(name.startswith("GIT_") for name in os.environ):',
		'    print("REFUSED ambient git settings reached the checker")',
		'    sys.exit(1)',
		'if hive.endswith("team-notes"):',
		'    print("verified: every commit up to 0123456789 is signed and allowed")',
		'else:',
		'    print("REFUSED commit 9876543210 changes keys it may not")',
		'    print("everything after that point is untrusted")',
		'    sys.exit(1)',
		'',
	].join('\n'));
	write(path.join(HIVE, 'shared', 'notes', 'hive_agent.py'), 'print("never run")\n');
}

function snapshot(dir: string): string[] {
	const out: string[] = [];
	const walk = (d: string) => {
		for (const name of fs.readdirSync(d).sort()) {
			const full = path.join(d, name);
			const stat = fs.lstatSync(full);
			out.push(`${path.relative(ROOT, full)} ${stat.isDirectory() ? 'd' : stat.size} ${stat.mtimeMs}`);
			if (stat.isDirectory() && !stat.isSymbolicLink()) {
				walk(full);
			}
		}
	};
	walk(dir);
	return out;
}

const tree = new HivesTreeProvider(() => HOME, () => undefined);
const item = (node: Node) => tree.getTreeItem(node) as unknown as Item;
const labels = (nodes: readonly Node[]) => nodes.map(n => item(n).label);

// Suites collect their tests as the file loads, so the fixture is built first.
buildFixture();
const untouched = snapshot(ROOT);

after(() => {
	assert.deepStrictEqual(snapshot(ROOT), untouched, 'the fixture changed: something wrote into a Hive or a reference');
	fs.rmSync(ROOT, { recursive: true, force: true });
});

describe('Hives folder', () => {
	test('is RAPP_HIVES when set, else Hives in the home folder', () => {
		assert.strictEqual(hives.hivesHome({ RAPP_HIVES: HOME }), HOME);
		assert.strictEqual(path.basename(hives.hivesHome({})), 'Hives');
	});

	test('lists only real Hives: device state present, no hidden folders, no links', () => {
		assert.deepStrictEqual(hives.listHives(HOME), ['sly-hive', 'team-notes']);
	});

	test('never follows a link out of a Hive, even for its fixed folders', () => {
		const sly = hives.readHive(HOME, 'sly-hive');
		assert.deepStrictEqual([sly.members, sly.requests, sly.rooms], [[], [], []]);
		assert.deepStrictEqual(hives.listFolder(path.join(HOME, 'sly-hive', 'shared')).entries, []);
	});

	test('a Hives folder that is itself a link still lists its Hives', { skip: !fs.existsSync(path.join(ROOT, 'Hives-link')) && 'links need privileges here' }, () => {
		assert.deepStrictEqual(hives.listHives(path.join(ROOT, 'Hives-link')), ['sly-hive', 'team-notes']);
	});

	test('with no Hives the tree is empty, and the view says so above it', () => {
		const empty = new HivesTreeProvider(() => path.join(ROOT, 'nowhere'), () => undefined);
		assert.deepStrictEqual(empty.getChildren(), []);
		assert.match(NO_HIVES, /^No Hives on this device yet\. Ask your Brainstem to create or join one\.$/);
	});
});

describe('Hives tree', () => {
	const hiveNode = () => tree.getChildren().find(n => n.kind === 'hive' && n.hive.name === 'team-notes') as Node;
	const sections = () => tree.getChildren(hiveNode());

	test('the checker and its Python may not be inside a Hive, even as a link there to a file outside', { skip: !canLinkFiles && 'file links need privileges here' }, () => {
		// A folder of this test's own: the Hives fixture is checked, at the end, to be exactly as it was.
		const base = path.join(TMP, `checker-links-${process.pid}`);
		after(() => fs.rmSync(base, { recursive: true, force: true }));
		const outside = path.join(base, 'outside');
		fs.mkdirSync(outside, { recursive: true });
		const realAgent = path.join(outside, 'hive_agent.py');
		const realPython = path.join(outside, 'python3');
		fs.writeFileSync(realAgent, '');
		fs.writeFileSync(realPython, '');
		const hive = path.join(base, 'LinkedHives', 'team');
		fs.mkdirSync(path.join(hive, 'venv', 'bin'), { recursive: true });
		const linkedAgent = path.join(hive, 'hive_agent.py');
		const linkedPython = path.join(hive, 'venv', 'bin', 'python');
		fs.symlinkSync(realAgent, linkedAgent, 'file');
		fs.symlinkSync(realPython, linkedPython, 'file');
		const roots = [path.join(base, 'LinkedHives')];
		assert.deepStrictEqual([
			checker.checkerRefusal(realAgent, realPython, roots),
			checker.checkerRefusal(linkedAgent, realPython, roots),
			checker.checkerRefusal(realAgent, linkedPython, roots),
		], [undefined, 'the checker may not live inside a Hive or a reference', 'rapp.pythonPath may not point inside a Hive or a reference'],
			'a program started through a link inside a Hive reads that folder\'s own settings');
	});

	test('a Python given inside a Hive is refused however its folders are linked out: Python reads its settings where it is started', () => {
		const base = path.join(TMP, `venv-links-${process.pid}`);
		after(() => fs.rmSync(base, { recursive: true, force: true }));
		const outside = path.join(base, 'outside');
		fs.mkdirSync(path.join(outside, 'bin'), { recursive: true });
		fs.mkdirSync(path.join(outside, 'venv', 'bin'), { recursive: true });
		fs.writeFileSync(path.join(outside, 'bin', 'python3'), '');
		fs.writeFileSync(path.join(outside, 'venv', 'bin', 'python3'), '');
		const hives = path.join(base, 'Hives');
		fs.mkdirSync(path.join(hives, 'team', 'venv'), { recursive: true });
		fs.writeFileSync(path.join(hives, 'team', 'venv', 'pyvenv.cfg'), 'home = synthetic\n');
		const folderLink = process.platform === 'win32' ? 'junction' : 'dir';
		// Its bin/ is a link out, beside a real pyvenv.cfg; or the whole venv is a link out.
		fs.symlinkSync(path.join(outside, 'bin'), path.join(hives, 'team', 'venv', 'bin'), folderLink);
		fs.symlinkSync(path.join(outside, 'venv'), path.join(hives, 'team', 'linked-venv'), folderLink);
		// And given through a path outside that leads into the Hive, its bin/ linked out again.
		fs.symlinkSync(path.join(hives, 'team'), path.join(base, 'team-shortcut'), folderLink);
		const refused = 'rapp.pythonPath may not point inside a Hive or a reference';
		assert.deepStrictEqual([
			checker.checkerRefusal(realAgentFor(base), path.join(hives, 'team', 'venv', 'bin', 'python3'), [hives]),
			checker.checkerRefusal(realAgentFor(base), path.join(hives, 'team', 'linked-venv', 'bin', 'python3'), [hives]),
			checker.checkerRefusal(realAgentFor(base), path.join(base, 'team-shortcut', 'venv', 'bin', 'python3'), [hives]),
			checker.checkerRefusal(realAgentFor(base), path.join(outside, 'bin', 'python3'), [hives]),
		], [refused, refused, refused, undefined]);
	});

	test('on Windows the checker\'s default Python falls back to python, as the grail\'s start.ps1 does; one that cannot start is noted as such', async () => {
		assert.deepStrictEqual([checker.checkerPythons('python3', 'win32'), checker.checkerPythons('python3', 'darwin'), checker.checkerPythons('python3.12', 'win32'), checker.checkerPythons('C:\\py\\python.exe', 'win32')],
			[['python3', 'python'], ['python3'], ['python3.12'], ['C:\\py\\python.exe']]);
		const missing = await checker.runCheck(path.join(ROOT, 'no-such-python'), path.join(ROOT, 'tools', 'fake_checker.py'), HIVE);
		assert.deepStrictEqual([missing.state, missing.notStarted], ['failed', true], 'a Python that is not there lets the next one be tried');
	});

	test('shows one node per Hive, with its checker state', () => {
		assert.deepStrictEqual(labels(tree.getChildren()), ['sly-hive', 'team-notes']);
		assert.strictEqual(hiveNode().kind, 'hive');
		const hiveItem = item(hiveNode());
		assert.strictEqual(hiveItem.label, 'team-notes');
		assert.strictEqual(hiveItem.description, 'checker not configured');
		assert.strictEqual(hiveItem.contextValue, 'rapp.hive');
		assert.match(String(hiveItem.tooltip), /team-notes/);
	});

	test('reports a verdict when the checker ran', () => {
		const verdicts = new HivesTreeProvider(() => HOME, () => ({ state: 'verified', summary: 'verified: every commit up to 0123456789 is signed and allowed', output: '' }));
		const hiveItem = verdicts.getTreeItem(verdicts.getChildren()[1]) as unknown as Item;
		assert.strictEqual(hiveItem.description, 'verified');
		assert.match(String(hiveItem.tooltip), /signed and allowed/);
	});

	test('has the rules, members, waiting requests and rooms', () => {
		assert.deepStrictEqual(labels(sections()), ['HIVE.md', 'Members', 'Waiting requests', 'Rooms']);
		assert.deepStrictEqual(sections().slice(1).map(n => item(n).description), ['2', '1', '2']);
	});

	test('members are folders holding key files; devices are the key files', () => {
		const members = tree.getChildren(sections()[1]);
		assert.deepStrictEqual(labels(members), ['ana', 'ben']);
		assert.deepStrictEqual(members.map(n => item(n).description), ['2 devices', '1 device']);
		assert.deepStrictEqual(labels(tree.getChildren(members[0])), ['laptop.md', 'phone.md']);
	});

	test('waiting requests open in the editor', () => {
		const [request] = tree.getChildren(sections()[2]);
		const requestItem = item(request);
		assert.strictEqual(requestItem.label, 'dev');
		assert.strictEqual(requestItem.description, 'tablet');
		assert.strictEqual(requestItem.command?.command, 'vscode.open');
		assert.strictEqual((requestItem.command?.arguments?.[0] as { fsPath: string }).fsPath, path.join(HIVE, 'requests', 'dev', 'tablet.md'));
	});

	test('rooms list folders first, skip hidden files and links, and open files in the editor', () => {
		const rooms = tree.getChildren(sections()[3]);
		assert.deepStrictEqual(labels(rooms), ['notes', 'plans']);
		const plans = tree.getChildren(rooms[1]);
		assert.deepStrictEqual(labels(plans), ['drafts', '2026-q4.md']);
		assert.strictEqual(item(plans[0]).collapsibleState, 1);
		assert.strictEqual(item(plans[1]).command?.command, 'vscode.open');
	});

	test('the rules file opens in the editor', () => {
		const rules = item(sections()[0]);
		assert.strictEqual(rules.command?.command, 'vscode.open');
		assert.strictEqual(rules.resourceUri?.fsPath, path.join(HIVE, 'HIVE.md'));
	});
});

describe('References tree', () => {
	const references = new ReferencesTreeProvider(() => HOME);

	test('shows each Hive with its pinned labels; bad labels and relative paths are dropped', () => {
		const hiveNode = references.getChildren()[1];
		const refs = references.getChildren(hiveNode);
		assert.deepStrictEqual(refs.map(n => references.getTreeItem(n).label), ['gone', 'old-vault']);
	});

	test('labels by default, full paths only on hover', () => {
		const refs = references.getChildren(references.getChildren()[1]);
		for (const node of refs) {
			const refItem = references.getTreeItem(node) as unknown as Item;
			assert.ok(!String(refItem.label).includes(path.sep));
			assert.ok(!String(refItem.description ?? '').includes(path.sep));
			assert.ok(String(refItem.tooltip).includes(ROOT));
			assert.strictEqual(refItem.command, undefined);
		}
		assert.strictEqual((references.getTreeItem(refs[0]) as unknown as Item).description, 'missing');
	});
});

describe('Hive checker', () => {
	const agent = path.join(ROOT, 'tools', 'fake_checker.py');

	test('inside means inside: a folder whose name starts with two dots is in its parent, and .. is not', () => {
		assert.deepStrictEqual([
			hives.isInside(path.join(REF, '..x', 'rapp_brainstem'), REF),
			hives.isInside(path.join(REF, '..', 'rapp_brainstem'), REF),
			hives.isInside(REF, REF),
			hives.isInside(path.join(REF, 'notes'), REF),
		], [true, false, true, true]);
		assert.deepStrictEqual(['..', `..${path.sep}x`, '..x', `..x${path.sep}y`, 'x'].map(hives.leaves), [true, true, false, false, false]);
	});

	test('refuses an agent path that is relative, missing, not .py, or inside a Hive or reference', () => {
		assert.match(String(checker.checkerRefusal('hive_agent.py', 'python3', [HOME])), /full path/);
		assert.match(String(checker.checkerRefusal(path.join(ROOT, 'none.py'), 'python3', [HOME])), /not at/);
		assert.match(String(checker.checkerRefusal(path.join(HIVE, 'HIVE.md'), 'python3', [HOME])), /\.py file/);
		assert.match(String(checker.checkerRefusal(path.join(HIVE, 'shared', 'notes', 'hive_agent.py'), 'python3', [HOME])), /inside a Hive/);
		assert.match(String(checker.checkerRefusal(path.join(REF, '..', '..', 'tools', 'fake_checker.py'), 'python3', [HOME, path.join(ROOT, 'tools')])), /inside a Hive or a reference/);
		assert.match(String(checker.checkerRefusal(agent, 'python3; rm', [HOME])), /pythonPath/);
		assert.match(String(checker.checkerRefusal(agent, path.join(REF, 'python3'), [HOME, REF])), /pythonPath may not point inside/);
		assert.strictEqual(checker.checkerRefusal(agent, 'python3', [HOME, REF]), undefined);
	});

	test('reads the checker verdicts', () => {
		assert.strictEqual(checker.readVerdict(0, 'root abc; founder\'s key SHA256:x\nverified: every commit up to 0123456789 is signed and allowed\n', '').state, 'verified');
		assert.strictEqual(checker.readVerdict(1, 'REFUSED bad\neverything after that point is untrusted\n', '').summary, 'REFUSED bad');
		assert.strictEqual(checker.readVerdict(1, '', 'ModuleNotFoundError: No module named \'cryptography\'\n').state, 'failed');
	});

	test('a Hive\'s own words never become a link in a notification', () => {
		assert.strictEqual(checker.noticeText('Hive [Open](command:workbench.action.terminal.new): REFUSED (unsigned) [x](https://example.org)'),
			'Hive [Open] (command:workbench.action.terminal.new): REFUSED (unsigned) [x] (https://example.org)');
		assert.strictEqual(checker.noticeText('verified: every commit is signed (3 members)'), 'verified: every commit is signed (3 members)');
	});

	test('runs the configured checker on a Hive, without ambient git settings', { skip: !hasPython && 'no python3' }, async () => {
		const saved = { count: process.env.GIT_CONFIG_COUNT, dir: process.env.GIT_DIR };
		process.env.GIT_CONFIG_COUNT = '3';
		process.env.GIT_DIR = path.join(ROOT, 'elsewhere');
		let verdict;
		try {
			verdict = await checker.runCheck(PYTHON, agent, HIVE);
		} finally {
			for (const [name, value] of [['GIT_CONFIG_COUNT', saved.count], ['GIT_DIR', saved.dir]] as const) {
				if (value === undefined) {
					delete process.env[name];
				} else {
					process.env[name] = value;
				}
			}
		}
		assert.strictEqual(verdict.state, 'verified', verdict.summary);
		const refusal = await checker.runCheck(PYTHON, agent, path.join(HOME, 'not-a-hive'));
		assert.strictEqual(refusal.state, 'refused');
		assert.match(refusal.summary, /^REFUSED/);
	});
});

describe('Brainstem client', () => {
	let server: http.Server;
	let url = '';
	const seen: Record<string, unknown>[] = [];
	// The grail's /health, account fields included: only the version and the folder may come out of it.
	const grailHealth = {
		status: 'ok', version: '0.6.9', model: 'hidden-model', voice_mode: false, soul: path.join(TMP, 'soul.md'), agents: ['Weather'],
		quarantined: [], copilot: 'no_access', copilot_username: 'hidden-account', brainstem_dir: path.join(TMP, 'rapp_brainstem'),
	};

	before(async () => {
		server = http.createServer((req, res) => {
			let body = '';
			req.on('data', chunk => body += chunk);
			req.on('end', () => {
				res.setHeader('Content-Type', 'application/json');
				if (req.url === '/health') {
					res.end(JSON.stringify(grailHealth));
				} else if (req.url === '/chat') {
					const parsed = JSON.parse(body) as Record<string, unknown>;
					seen.push(parsed);
					res.end(JSON.stringify({ response: `heard: ${String(parsed.user_input)}|||VOICE|||spoken`, agent_logs: ['Hive: status'], session_id: 's-1' }));
				} else {
					res.statusCode = 404;
					res.end('{}');
				}
			});
		});
		await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve));
		url = `http://127.0.0.1:${(server.address() as { port: number }).port}`;
	});

	after(() => new Promise<void>(resolve => server.close(() => resolve())));

	test('accepts only this device', () => {
		assert.strictEqual(typeof brainstem.parseEndpoint('http://127.0.0.1:7071'), 'object');
		assert.strictEqual(typeof brainstem.parseEndpoint('http://localhost:7071'), 'object');
		assert.strictEqual(typeof brainstem.parseEndpoint('http://[::1]:7071'), 'object');
		assert.match(String(brainstem.parseEndpoint('http://192.168.1.4:7071')), /this device/);
		assert.match(String(brainstem.parseEndpoint('https://127.0.0.1:7071')), /http:\/\//);
		assert.match(String(brainstem.parseEndpoint('http://user:pw@127.0.0.1:7071')), /host and port/);
		assert.match(String(brainstem.parseEndpoint('http://127.0.0.1:7071/chat')), /host and port/);
	});

	test('the grail wire carries the conversation; the RAPP/1 wire is exactly section 8', () => {
		const history = [{ role: 'user' as const, content: 'save my edits' }, { role: 'assistant' as const, content: 'proposal 1a2b' }];
		assert.deepStrictEqual(Object.keys(brainstem.chatBody('grail', 'yes', 's-1', history)).sort(), ['conversation_history', 'session_id', 'user_input']);
		assert.deepStrictEqual(Object.keys(brainstem.chatBody('rapp1', 'yes', 's-1', history)).sort(), ['session_id', 'user_input']);
		assert.throws(() => brainstem.parseReply('rapp1', 200, { response: 'x', agent_logs: [], session_id: 's', model: 'm' }), (error: Error & { answered?: boolean }) =>
			error.answered === true && /^answered in a shape the setting rapp\.chat\.wire \(rapp1: the exact RAPP\/1 section 8 reply\) does not accept, and may have done what you asked\. Check before you send it again\.$/.test(error.message));
		assert.throws(() => brainstem.parseReply('rapp1', 422, { error: { code: 'inference-refused', step: 'adapter' } }), /inference-refused at adapter/);
		assert.strictEqual(brainstem.parseReply('grail', 200, { response: 'ok', agent_logs: 'a\nb', session_id: 's' }).agentLogs, 'a\nb');
	});

	test('reads only the version, the Brainstem folder, the loaded agents and whether it needs its sign-in', () => {
		assert.deepStrictEqual([
			brainstem.parseHealth(grailHealth),
			brainstem.parseHealth({ status: 'unauthenticated', version: '0.6.9', model: 'm', soul: 's', agents: [], auth_error: 'invalid_credentials' }),
			brainstem.parseHealth({ version: 7, brainstem_dir: ['x'], copilot_username: 'hidden-account', agents: ['Notes', 7, null, { name: 'hidden-object' }] }),
			brainstem.parseHealth('not json'),
		], [
			{ signedOut: false, version: '0.6.9', brainstemDir: path.join(TMP, 'rapp_brainstem'), agentCount: 1, agentNames: ['Weather'] },
			{ signedOut: true, version: '0.6.9', agentCount: 0, agentNames: [] },
			{ signedOut: false, agentCount: 4, agentNames: ['Notes'] },
			{ signedOut: false },
		]);
	});

	test('talks to a Brainstem on this device', async () => {
		const endpoint = brainstem.parseEndpoint(url);
		assert.ok(typeof endpoint === 'object');
		const status = await brainstem.health(endpoint);
		assert.deepStrictEqual(status, { state: 'connected', version: '0.6.9', brainstemDir: path.join(TMP, 'rapp_brainstem'), agentCount: 1, agentNames: ['Weather'] });
		assert.ok(!/hidden-account|hidden-model|no_access|soul\.md/.test(JSON.stringify(status)), 'another /health field came through');
		const reply = await brainstem.chat(endpoint, 'grail', 'hello', undefined, []);
		assert.strictEqual(shownText(reply.response), 'heard: hello');
		assert.strictEqual(reply.agentLogs, 'Hive: status');
		assert.strictEqual(reply.sessionId, 's-1');
		assert.deepStrictEqual(seen[0], { user_input: 'hello' });
	});

	test('says plainly when nothing is running', async () => {
		const closed = brainstem.parseEndpoint('http://127.0.0.1:9');
		assert.ok(typeof closed === 'object');
		const status = await brainstem.health(closed, 800);
		assert.deepStrictEqual([status.state, 'occupied' in status, 'busy' in status], ['not-running', false, false], 'a refused connection: nothing is there');
	});

	test('a Brainstem that takes a few seconds to answer (it loads every agent for /health) is running', async () => {
		const slow = http.createServer((_req, res) => setTimeout(() => {
			res.setHeader('Content-Type', 'application/json');
			res.end(JSON.stringify(grailHealth));
		}, 2500));
		await new Promise<void>(resolve => slow.listen(0, '127.0.0.1', resolve));
		try {
			const endpoint = brainstem.parseEndpoint(`http://127.0.0.1:${(slow.address() as net.AddressInfo).port}`);
			assert.ok(typeof endpoint === 'object');
			assert.strictEqual((await brainstem.health(endpoint)).state, 'connected');
		} finally {
			await new Promise<void>(resolve => slow.close(() => resolve()));
		}
	});

	test('a Brainstem that answered once and is then slow to answer is busy: each check has a connection of its own', async () => {
		let answers = 0;
		const server = http.createServer((_req, res) => {
			if (answers++ === 0) {
				res.setHeader('Content-Type', 'application/json');
				res.end(JSON.stringify(grailHealth));
			}
		});
		await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve));
		try {
			const endpoint = brainstem.parseEndpoint(`http://127.0.0.1:${(server.address() as net.AddressInfo).port}`);
			assert.ok(typeof endpoint === 'object');
			assert.strictEqual((await brainstem.health(endpoint, 1000)).state, 'connected');
			const slow = await brainstem.health(endpoint, 300);
			assert.deepStrictEqual([slow.state, 'busy' in slow && slow.busy], ['not-running', true], 'a socket kept from the first check would never say it connected');
		} finally {
			server.closeAllConnections();
			await new Promise<void>(resolve => server.close(() => resolve()));
		}
	});

	test('a connection made but not answered in time is a busy Brainstem; bytes that are not HTTP are something else; a connection closed without an answer is asked once more', async () => {
		let mode: 'silent' | 'other protocol' | 'dropped' | 'stopping' = 'silent';
		const sockets = new Set<net.Socket>();
		const raw = net.createServer(socket => {
			sockets.add(socket);
			socket.on('close', () => sockets.delete(socket));
			socket.on('error', () => undefined);
			if (mode === 'other protocol') {
				socket.end('SSH-2.0-OpenSSH_9.6\r\n');
			} else if (mode === 'dropped') {
				socket.destroy();
			} else if (mode === 'stopping') {
				// A Brainstem that is stopping: it drops the connection it has, and then is gone.
				raw.close();
				socket.destroy();
			}
		});
		await new Promise<void>(resolve => raw.listen(0, '127.0.0.1', resolve));
		try {
			const endpoint = brainstem.parseEndpoint(`http://127.0.0.1:${(raw.address() as net.AddressInfo).port}`);
			assert.ok(typeof endpoint === 'object');
			const flags = (status: import('../brainstem').Health) => [status.state, ...(['occupied', 'busy', 'dropped'] as const).map(flag => flag in status && (status as Record<string, unknown>)[flag] === true)];
			assert.deepStrictEqual(flags(await brainstem.health(endpoint, 300)), ['not-running', false, true, false], 'accepted, then no answer: it is there, only busy');
			mode = 'other protocol';
			assert.deepStrictEqual(flags(await brainstem.health(endpoint, 2000)), ['not-running', true, false, false]);
			mode = 'dropped';
			assert.deepStrictEqual(flags(await brainstem.health(endpoint, 2000)), ['not-running', false, false, true], 'closed without an answer twice: it is there, not answering');
			mode = 'stopping';
			assert.deepStrictEqual(flags(await brainstem.health(endpoint, 2000)), ['not-running', false, false, false], 'closed, then refused: it stopped');
		} finally {
			sockets.forEach(socket => socket.destroy());
			await new Promise<void>(resolve => raw.close(() => resolve()));
		}
	});

	test('the grail\'s "no Copilot access" reply is said in plain words, without its code or the account\'s name', () => {
		for (const [status, reply] of [[200, { error: 'NO_COPILOT_ACCESS:hidden-account', no_copilot_access: true, copilot_username: 'hidden-account' }], [500, { error: 'NO_COPILOT_ACCESS:hidden-account' }]] as const) {
			assert.throws(() => brainstem.parseReply('grail', status, reply), (error: Error) =>
				/has no Copilot access; sign it in with an account that has/.test(error.message) && !/hidden-account|NO_COPILOT_ACCESS/.test(error.message), `HTTP ${status}`);
		}
		assert.throws(() => brainstem.parseReply('grail', 502, { error: 'Copilot usage limit reached — wait a minute and try again.', model: 'm' }), /^Error: Copilot usage limit reached/);
		assert.throws(() => brainstem.parseReply('grail', 500, { error: 'Not authenticated. Visit /login in your browser to sign in with GitHub.' }),
			(error: Error) => error.message === 'it is not signed in yet. Sign in on its page, then send it again', 'its own words point at a page the person cannot open');
	});

	test('something else on its address is never taken for a running Brainstem; a RAPP/1 endpoint\'s own JSON is', async () => {
		let answer = { status: 404, type: 'text/html', body: '<html><body>Not Found</body></html>' };
		const other = http.createServer((_req, res) => {
			res.statusCode = answer.status;
			res.setHeader('Content-Type', answer.type);
			res.end(answer.body);
		});
		await new Promise<void>(resolve => other.listen(0, '127.0.0.1', resolve));
		try {
			const at = `http://127.0.0.1:${(other.address() as { port: number }).port}`;
			const endpoint = brainstem.parseEndpoint(at);
			assert.ok(typeof endpoint === 'object');
			assert.deepStrictEqual(await brainstem.health(endpoint), { state: 'not-running', reason: `something else answers at ${at} (HTTP 404)`, occupied: true });
			answer = { status: 200, type: 'text/html', body: '<!doctype html><title>Some web app</title>' };
			assert.deepStrictEqual(await brainstem.health(endpoint), { state: 'not-running', reason: `something else answers at ${at} (HTTP 200)`, occupied: true }, 'a web app that serves its page for every path');
			answer = { status: 200, type: 'application/json', body: JSON.stringify({ status: 'pre-acceptance', authenticated: false, fully_conformant: false }) };
			assert.deepStrictEqual(await brainstem.health(endpoint), { state: 'connected' }, 'a RAPP/1 section 8 endpoint answers /health with a JSON object of its own');
		} finally {
			await new Promise<void>(resolve => other.close(() => resolve()));
		}
	});
});

describe('Organism view', () => {
	const media = path.join(__dirname, '..', '..', 'media', 'organism');

	test('ships the pinned copies byte for byte', () => {
		const pin = JSON.parse(fs.readFileSync(path.join(media, 'PIN.json'), 'utf8')) as { commit: string; files: Record<string, { sha256: string; bytes: number }> };
		assert.match(pin.commit, /^[0-9a-f]{40}$/);
		for (const [name, want] of Object.entries(pin.files)) {
			const bytes = fs.readFileSync(path.join(media, name));
			assert.strictEqual(createHash('sha256').update(bytes).digest('hex'), want.sha256, name);
			assert.strictEqual(bytes.length, want.bytes, name);
		}
	});

	test('shows the one-page view under a strict policy, without scripts', () => {
		const page = hardenPinnedPage(fs.readFileSync(path.join(media, 'one-page.html'), 'utf8'), { cspSource: 'vscode-resource:' } as never);
		const policy = /<meta http-equiv="Content-Security-Policy" content="([^"]+)">/.exec(page)?.[1] ?? '';
		assert.match(policy, /default-src 'none'/);
		assert.match(policy, /script-src 'none'/);
		assert.match(policy, /connect-src 'none'/);
		assert.strictEqual((policy.match(/'sha256-/g) ?? []).length, 2);
		assert.ok(!/<script/i.test(page));
		assert.match(page, /<style nonce="[^"]+">/);
		const hardened = hardenPinnedPage('<html><head></head><body><script>alert(1)</script></body></html>', { cspSource: 'x' } as never);
		assert.ok(!hardened.includes('alert(1)'));
	});
});

describe('Grail one-liner', () => {
	test('is pinned to the kernel release RAPP pins', () => {
		assert.match(GRAIL.unix, /rapp-installer\/brainstem-v0\.6\.9\/install\.sh \| bash -s -- --version brainstem-v0\.6\.9$/);
		assert.ok(!/\/main\//.test(GRAIL.unix));
		assert.ok(!('windows' in GRAIL), 'the Windows script at the tag follows the installer\'s main branch, so it is not offered');
		assert.deepStrictEqual(grailOneLiner('win32').command, undefined);
		assert.match(grailOneLiner('win32').note ?? '', /no pinned one-liner for Windows/);
		assert.deepStrictEqual(['darwin', 'linux'].map(p => grailOneLiner(p as NodeJS.Platform).command), [GRAIL.unix, GRAIL.unix]);
	});
});
