// Unit tests for the RAPP Workspace in the Explorer: which agent files are live (only the top of agents/),
// the Explorer's marks on them, and the status-bar notes from the watcher on agents/*_agent.py, against
// synthetic paths under the test temp folder and a stand-in vscode API.
import * as assert from 'assert';
import * as fs from 'fs';
import * as path from 'path';
import { describe, test } from 'node:test';

const loader = require('module') as { _resolveFilename: (request: string, ...rest: unknown[]) => string };
const resolveFilename = loader._resolveFilename;
loader._resolveFilename = function (this: unknown, request: string, ...rest: unknown[]): string {
	return request === 'vscode' ? path.join(__dirname, 'vscodeStub.js') : resolveFilename.call(this, request, ...rest);
};

const agents = require('../agents') as typeof import('../agents');
const { AgentDecorations, RappWorkspace } = require('../agentsView') as typeof import('../agentsView');
const stub = require('./vscodeStub') as typeof import('./vscodeStub');

const TMP = path.resolve(process.env.BRAINSTEM_TEST_TMP || path.join(__dirname, '..', '..', '.test-tmp'));
const ROOT = path.join(TMP, 'rapp-workspace', 'agents');
const at = (...parts: string[]) => path.join(ROOT, ...parts);
const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

describe('RAPP Workspace agents on Windows', () => {
	test('the loader\'s glob ignores case there, and only there: so do the marks, the base class and the watcher', () => {
		assert.deepStrictEqual(['WEATHER_AGENT.PY', 'Weather_Agent.py', 'weather_agent.py'].map(n => agents.isAgentFileName(n, 'win32')), [true, true, true]);
		assert.deepStrictEqual(['WEATHER_AGENT.PY', 'Weather_Agent.py'].map(n => agents.isAgentFileName(n, 'darwin')), [false, false]);
		assert.deepStrictEqual([agents.isBaseAgent('BASIC_AGENT.PY', 'win32'), agents.isBaseAgent('BASIC_AGENT.PY', 'linux')], [true, false]);
		assert.deepStrictEqual([agents.agentPlace(ROOT, at('WEATHER_AGENT.PY'), 'win32'), agents.agentPlace(ROOT, at('BASIC_AGENT.PY'), 'win32'), agents.agentPlace(ROOT, at('WEATHER_AGENT.PY'), 'darwin')], ['live', undefined, undefined]);
		assert.deepStrictEqual([agents.agentGlob('win32'), agents.agentGlob('darwin')], ['*_[aA][gG][eE][nN][tT].[pP][yY]', '*_agent.py']);
	});

	test('the watcher there listens for either case and names the file as it is', async () => {
		stub.recorded.watchers.length = 0;
		stub.recorded.statusMessages.length = 0;
		const workspace = new RappWorkspace(() => undefined, 5, 'win32');
		try {
			workspace.watch(ROOT);
			const [watcher] = stub.recorded.watchers;
			assert.strictEqual(watcher.pattern.pattern, '*_[aA][gG][eE][nN][tT].[pP][yY]');
			watcher.fireCreate(stub.Uri.file(at('WEATHER_AGENT.PY')));
			watcher.fireCreate(stub.Uri.file(at('BASIC_AGENT.PY')));
			await sleep(30);
			assert.deepStrictEqual(stub.recorded.statusMessages, [['WEATHER_AGENT.PY is live', 4000]]);
		} finally {
			workspace.dispose();
		}
	});
});

describe('RAPP Workspace agents', () => {
	test('an agent file at the top of agents/ is live, one in any folder is not, and the base class is neither', () => {
		assert.deepStrictEqual([
			at('weather_agent.py'),
			at('disabled_agents', 'old_agent.py'),
			at('team', 'tools', 'deep_agent.py'),
			at('basic_agent.py'),
			at('disabled_agents', 'basic_agent.py'),
			at('helper.py'),
			at('.hidden_agent.py'),
			at('__pycache__', 'cached_agent.py'),
			at('.git', 'x_agent.py'),
			path.join(ROOT, '..', 'brainstem_agent.py'),
			ROOT,
		].map(file => agents.agentPlace(ROOT, file) ?? null), ['live', 'folder', 'folder', null, null, null, null, null, null, null, null]);
	});

	test('the status bar says which agents became live and which stopped being live', () => {
		assert.deepStrictEqual([
			agents.liveMessage(['weather_agent.py'], []),
			agents.liveMessage([], ['weather_agent.py']),
			agents.liveMessage(['forecast_agent.py'], ['weather_agent.py']),
			agents.liveMessage(['a_agent.py', 'b_agent.py'], []),
			agents.liveMessage([], ['a_agent.py', 'b_agent.py', 'c_agent.py']),
			agents.liveMessage([], []),
		], [
			'weather_agent.py is live',
			'weather_agent.py is no longer live',
			'forecast_agent.py is live; weather_agent.py is no longer live',
			'a_agent.py and b_agent.py are live',
			'3 agents are no longer live',
			undefined,
		]);
	});
});

describe('RAPP Workspace in the Explorer', () => {
	test('live agent files carry a badge; agent files in folders are dimmed; the base class and other files are unmarked', () => {
		const decorations = new AgentDecorations(() => ROOT);
		const mark = (file: string) => {
			const d = decorations.provideFileDecoration(stub.Uri.file(file) as never) as { badge?: string; tooltip?: string; color?: { id: string } } | undefined;
			return d ? [d.badge ?? null, d.tooltip, d.color?.id ?? null] : null;
		};
		assert.deepStrictEqual([at('weather_agent.py'), at('disabled_agents', 'old_agent.py'), at('basic_agent.py'), at('notes.md')].map(mark), [
			['●', 'Live — your Brainstem runs this', null],
			[null, 'Not live — drag to the top of agents/ to run it', 'list.deemphasizedForeground'],
			null,
			null,
		]);
		assert.strictEqual(new AgentDecorations(() => undefined).provideFileDecoration(stub.Uri.file(at('weather_agent.py')) as never), undefined);
		const asked: unknown[] = [];
		decorations.onDidChangeFileDecorations(value => void asked.push(value));
		decorations.refresh();
		assert.deepStrictEqual(asked, [undefined], 'the Explorer is asked for every mark again once the root is known');
	});

	test('an agent dragged into or out of a folder gives one short status note, and the live count is asked for again', async () => {
		stub.recorded.watchers.length = 0;
		stub.recorded.statusMessages.length = 0;
		let asked = 0;
		const workspace = new RappWorkspace(() => void asked++, 10);
		workspace.watch(ROOT);
		const [watcher] = stub.recorded.watchers;
		assert.deepStrictEqual([watcher.pattern.baseUri.fsPath, watcher.pattern.pattern], [ROOT, agents.agentGlob()], 'the loader\'s glob, as this system matches it');
		const file = (name: string) => stub.Uri.file(at(name));
		const settle = () => sleep(40);
		watcher.fireDelete(file('weather_agent.py'));
		await settle();
		watcher.fireCreate(file('weather_agent.py'));
		await settle();
		watcher.fireDelete(file('old_agent.py'));
		watcher.fireCreate(file('new_agent.py'));
		await settle();
		watcher.fireDelete(file('notes_agent.py'));
		watcher.fireCreate(file('notes_agent.py'));
		await settle();
		watcher.fireCreate(file('basic_agent.py'));
		watcher.fireCreate(file('helper.py'));
		watcher.fireCreate(stub.Uri.file(at('disabled_agents', 'old_agent.py')));
		await settle();
		assert.deepStrictEqual(stub.recorded.statusMessages, [
			['weather_agent.py is no longer live', 4000],
			['weather_agent.py is live', 4000],
			['new_agent.py is live; old_agent.py is no longer live', 4000],
		]);
		assert.strictEqual(asked, 4, 'the live count is asked for after each settled change, the rewrite included');
		workspace.dispose();
		assert.strictEqual(watcher.disposed, true);
	});

	test('Show agent card is offered for every agent file its card opens for, in any letter case, and never for the base class', () => {
		const manifest = JSON.parse(fs.readFileSync(path.join(__dirname, '..', '..', 'package.json'), 'utf8')) as { contributes: { menus: Record<string, { command: string; when?: string }[]> } };
		const whens = Object.values(manifest.contributes.menus).flat().filter(item => item.command === 'rapp.agentCard.show').map(item => item.when ?? '');
		assert.strictEqual(whens.length, 2, 'the title bar and the command palette');
		for (const when of whens) {
			// The host reads `=~ /…/flags` as a JavaScript regular expression, and `!( … )` as its negation.
			const tests = [...when.matchAll(/(!\()?resourceFilename =~ \/((?:\\\/|[^/])+)\/([a-z]*)\)?/g)];
			assert.strictEqual(tests.length, 2, when);
			const offered = (name: string) => tests.every(([, negated, body, flags]) => new RegExp(body, flags).test(name) !== !!negated);
			assert.deepStrictEqual(['weather_agent.py', 'WEATHER_AGENT.PY', 'Weather_Agent.py', 'basic_agent.py', 'BASIC_AGENT.PY', 'notes.py'].map(offered), [true, true, true, false, false, false], when);
		}
	});
});
