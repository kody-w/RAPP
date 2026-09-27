// Unit tests for the Brainstem data cards: what a memory file says (the dict the Brainstem writes, a list, missing
// fields, bad JSON), newest first, and the agent collections file, as read-only pages that escape every string.
// Every memory and collection here is synthetic.
import * as assert from 'assert';
import * as path from 'path';
import { describe, test } from 'node:test';

const loader = require('module') as { _resolveFilename: (request: string, ...rest: unknown[]) => string };
const resolveFilename = loader._resolveFilename;
loader._resolveFilename = function (this: unknown, request: string, ...rest: unknown[]): string {
	return request === 'vscode' ? path.join(__dirname, 'vscodeStub.js') : resolveFilename.call(this, request, ...rest);
};

const data = require('../dataCard') as typeof import('../dataCard');
type Memory = import('../dataCard').Memory;

const BRAINSTEM = path.join(path.sep, 'synthetic', 'home', '.brainstem', 'src', 'rapp_brainstem');
const SHARED_FILE = path.join(BRAINSTEM, '.brainstem_data', 'shared_memories', 'memory.json');
const USER_FILE = path.join(BRAINSTEM, '.brainstem_data', 'memory', '0a1b2c3d-1111-4222-8333-444455556666', 'user_memory.json');

// The shape the Brainstem's memory agent writes: a dict of id to entry.
const SHARED = JSON.stringify({
	'a1': { conversation_id: 'current', session_id: 'current', message: 'Prefers meetings before noon.', mood: 'neutral', theme: 'preference', importance: 4, tags: ['work', 'calendar'], date: '2026-09-20', time: '09:15:02' },
	'b2': { message: 'Their dog is called Biscuit.', mood: 'happy', theme: 'fact', importance: '2', tags: 'pets, family', date: '2026-09-24', time: '18:40:11' },
	'c3': { message: 'Wants a weekly summary on Fridays.', theme: 'task', date: '2026-09-22' },
	'd4': { content: 'An older note without a date.' },
	'e5': 'A memory kept as a bare string.',
	'f6': null,
}, null, 2);

const read = (source: string): readonly Memory[] => {
	const result = data.readMemories(source);
	assert.ok('memories' in result, JSON.stringify(result));
	return result.memories;
};

describe('Memory card', () => {
	test('reads the dict the Brainstem writes, newest first, with what each entry has and nothing it lacks', () => {
		const memories = read(SHARED);
		assert.deepStrictEqual(memories.map(m => m.id), ['b2', 'c3', 'a1', 'd4', 'e5', 'f6'], 'dated newest first, then the rest in file order');
		assert.deepStrictEqual(memories.map(m => [m.text, m.theme, m.tags, m.importance, m.mood, m.when]), [
			['Their dog is called Biscuit.', 'fact', ['pets', 'family'], 2, 'happy', '2026-09-24 18:40'],
			['Wants a weekly summary on Fridays.', 'task', [], undefined, undefined, '2026-09-22'],
			['Prefers meetings before noon.', 'preference', ['work', 'calendar'], 4, 'neutral', '2026-09-20 09:15'],
			['An older note without a date.', undefined, [], undefined, undefined, undefined],
			['A memory kept as a bare string.', undefined, [], undefined, undefined, undefined],
			['(empty)', undefined, [], undefined, undefined, undefined],
		]);
	});

	test('reads a list too, and tells a file that is not memories from one that is empty', () => {
		const list = read(JSON.stringify([{ id: 'x', message: 'One', date: '2026-01-02', time: '10:00:00' }, { message: 'Two', date: '2026-01-03' }, 42, { note: 'Noted', timestamp: '2025-12-31T08:00:00Z' }]));
		assert.deepStrictEqual(list.map(m => [m.id, m.text]), [['1', 'Two'], ['x', 'One'], ['3', 'Noted'], ['2', '42']]);
		const noted = new Date(Date.parse('2025-12-31T08:00:00Z'));
		const two = (n: number) => String(n).padStart(2, '0');
		assert.strictEqual(list[2].when, `${noted.getFullYear()}-${two(noted.getMonth() + 1)}-${two(noted.getDate())} ${two(noted.getHours())}:${two(noted.getMinutes())}`, 'a timestamp is shown like the other dates, in this device\'s time');
		assert.strictEqual(read(JSON.stringify([{ note: 'Odd', timestamp: 'last Tuesday' }]))[0].when, 'last Tuesday', 'one that does not read as a date is shown as written');
		assert.deepStrictEqual([read(''), read('{}'), read('[]'), read('null')], [[], [], [], []]);
		assert.deepStrictEqual(data.readMemories('"just a string"'), { problem: 'It holds a single value, not a set of memories.' });
	});

	test('bad JSON says where it stops, and the card offers the raw file', () => {
		const result = data.readMemories('{\n  "a": { "message": "one" },\n  "b": \n}\n');
		assert.ok('problem' in result);
		assert.strictEqual(result.problem, 'Line 4, column 1: expected a value.');
		assert.deepStrictEqual(['{ nope', '{"a": 1,}', '[1, 2', '{"a": "never', '{"a": 1} more', '{"a": 01}'].map(data.readJson).map(r => 'problem' in r ? r.problem : 'read'), [
			'Line 1, column 3: expected a quoted name.', 'Line 1, column 9: expected a quoted name.', 'Line 1, column 6: the file ends too soon.',
			'Line 1, column 7: text that never ends.', 'Line 1, column 10: more after the end.', 'Line 1, column 8: expected \',\' or \'}\'.',
		]);
		assert.ok(!result.problem.includes('one'), 'the file\'s text is never quoted');
		const body = data.memoryBody(result, data.dataFile(SHARED_FILE));
		assert.match(body, /This memory file isn’t valid JSON, so this card can’t read it/);
		assert.match(body, /data-action="viewRaw"/);
	});

	test('the page: what it remembers, where from, how many, read-only, searchable, newest first', () => {
		const body = data.memoryBody(data.readMemories(SHARED), data.dataFile(SHARED_FILE));
		assert.match(body, /<h1>What your Brainstem remembers<\/h1>/);
		assert.match(body, /Shared memory · 6 memories/);
		assert.match(body, /To change what it remembers, ask your Brainstem\./);
		assert.match(body, /<input id="search" type="search"/);
		assert.match(body, /data-action="viewRaw"/);
		assert.ok(body.indexOf('Biscuit') < body.indexOf('weekly summary') && body.indexOf('weekly summary') < body.indexOf('before noon'));
		assert.match(body, /title="Importance 4 of 5"[^>]*>●●●●○</);
		assert.match(data.memoryBody(data.readMemories(JSON.stringify({ a: { message: 'x', importance: 8 } })), undefined), /title="Importance 8 of 10"[^>]*>●●●●○</);
		const user = data.memoryBody(data.readMemories(JSON.stringify({ a: { message: 'Only one' } })), data.dataFile(USER_FILE));
		assert.match(user, /Memory for user 0a1b2c3d · 1 memory/);
		const empty = data.memoryBody(data.readMemories('{}'), data.dataFile(SHARED_FILE));
		assert.match(empty, /Shared memory · nothing yet/);
		assert.ok(!empty.includes('id="search"'), 'no search box with nothing to search');
		const many = JSON.stringify(Object.fromEntries(Array.from({ length: 1005 }, (_, i) => [`m${i}`, { message: `Memory ${i}` }])));
		const manyBody = data.memoryBody(data.readMemories(many), undefined);
		assert.match(manyBody, /Showing the newest 1,000\. Search looks through all of them\./);
		assert.deepStrictEqual([manyBody.match(/<article class="entry">/g)?.length, manyBody.match(/<article class="entry later" hidden>/g)?.length], [1000, 5], 'the rest wait hidden, for search');
		// The Brainstem adds each new memory at the end: however many there are, the newest come first and all count.
		const hour = (i: number) => new Date(Date.UTC(2024, 0, 1) + i * 3600000).toISOString();
		const lots = JSON.stringify(Object.fromEntries(Array.from({ length: 20005 }, (_, i) => [`m${i}`, { message: `Memory ${i}`, date: hour(i).slice(0, 10), time: hour(i).slice(11, 19) }])));
		const lotsBody = data.memoryBody(data.readMemories(lots), undefined);
		assert.match(lotsBody, /Memory · 20,005 memories/);
		assert.match(lotsBody, /Showing the newest 1,000\. Search looks through the newest 20,000; View raw shows them all\./);
		assert.strictEqual(lotsBody.match(/<article class="entry/g)?.length, 20000);
		assert.ok(lotsBody.indexOf('Memory 20004') >= 0 && lotsBody.indexOf('Memory 20004') < lotsBody.indexOf('Memory 20003'), 'the newest memory is the first row');
	});

	test('the card is for memory files under a Brainstem data folder, shared or per user', () => {
		const at = (...parts: string[]) => path.join(BRAINSTEM, ...parts);
		assert.deepStrictEqual([
			data.dataFile(SHARED_FILE),
			data.dataFile(USER_FILE),
			data.dataFile(at('.brainstem_data', 'memory.json')),
			data.dataFile(at('.brainstem_data', 'rar_collections', 'collections.json')),
			data.dataFile(at('.brainstem_data', 'rar_collections', 'catalog_cache.json')),
			data.dataFile(at('agents', 'memory.json')),
			data.dataFile(['C:', 'Users', 'someone', '.brainstem', 'src', 'rapp_brainstem', '.brainstem_data', 'shared_memories', 'memory.json'].join('\\')),
		], [
			{ kind: 'shared' }, { kind: 'user', user: '0a1b2c3d-1111-4222-8333-444455556666' }, { kind: 'memory' }, { kind: 'collections' }, undefined, undefined, { kind: 'shared' },
		]);
	});

	test('every string from the file is escaped, and the page runs only its own nonce\'d script', () => {
		const hostile = '<img src=x onerror=alert(1)><script>alert(2)</script>"\'&';
		const source = JSON.stringify({ [hostile]: { message: hostile, theme: hostile, mood: hostile, tags: [hostile], date: hostile, time: hostile, importance: 3 } });
		const body = data.memoryBody(data.readMemories(source), data.dataFile(SHARED_FILE));
		assert.ok(!/<img|<script|onerror=alert\(1\)>/i.test(body), 'raw markup from the file reached the page');
		assert.ok(body.includes('&lt;img src=x onerror=alert(1)&gt;&lt;script&gt;alert(2)&lt;/script&gt;&quot;&#39;&amp;'));
		const attributes = [...body.matchAll(/<[a-z0-9]+([^<>]*)>/gi)].flatMap(tag => [...tag[1].matchAll(/\s([a-zA-Z-]+)="/g)].map(m => m[1]));
		assert.deepStrictEqual([...new Set(attributes)].filter(name => !['class', 'title', 'aria-label', 'aria-live', 'role', 'id', 'type', 'placeholder', 'data-action'].includes(name)), []);
		const page = data.dataPage(body, { csp: 'default-src \'none\'', nonce: 'abc' });
		assert.strictEqual(page.match(/<script/g)?.length, 1);
		assert.match(page, /<script nonce="abc">/);
		assert.match(page, /<style nonce="abc">/);
		assert.ok(!/\sstyle=|\son[a-z]+=/i.test(page.replace(body, '')));
	});
});

describe('Agent collections card', () => {
	const COLLECTIONS = JSON.stringify({
		collections: {
			'trip planning': { task: 'Plan a team offsite', agent_ids: ['@example/travel'], matches: [{ id: '@example/travel', name: 'TravelPlanner', publisher: '@example', category: 'productivity', score: 0.91 }], created_at: '2026-09-21T10:00:00Z', catalog_generated: '2026-09-20T00:00:00Z' },
			'notes': { task: 'Keep meeting notes', agent_ids: ['@example/notes_keeper', 'plain_id'], created_at: '2026-09-23T08:00:00Z' },
			'bare': {},
		},
	});

	test('one line per collection, newest first: its task, then the agents it found, by name and publisher', () => {
		const result = data.readCollections(COLLECTIONS);
		assert.ok('collections' in result);
		assert.deepStrictEqual(result.collections.map(c => [c.name, c.task, c.agents]), [
			['notes', 'Keep meeting notes', [{ name: 'notes_keeper', publisher: '@example' }, { name: 'plain_id', publisher: undefined }]],
			['trip planning', 'Plan a team offsite', [{ name: 'TravelPlanner', publisher: '@example' }]],
			['bare', undefined, []],
		]);
		const body = data.collectionsBody(result);
		assert.match(body, /<h1>Agent collections<\/h1>/);
		assert.match(body, /3 collections of RAR agents your Brainstem picked for a task/);
		assert.ok(body.indexOf('Keep meeting notes') < body.indexOf('Plan a team offsite'));
		assert.match(body, /TravelPlanner <span class="muted">@example<\/span>/);
		assert.match(body, /<span class="agents">notes_keeper <span class="muted">@example<\/span>, plain_id<\/span>/, 'the agents are one item in the row, so no gap comes before a comma');
		assert.match(data.collectionsBody(data.readCollections('{"collections": {}}')), /None yet/);
		assert.match(data.collectionsBody(data.readCollections('{ nope')), /This collections file isn’t valid JSON/);
		const hostile = '<script>alert(1)</script>';
		assert.ok(!data.collectionsBody(data.readCollections(JSON.stringify({ collections: { [hostile]: { task: hostile, matches: [{ name: hostile, publisher: hostile }] } } }))).includes('<script'));
	});
});
