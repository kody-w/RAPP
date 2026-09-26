// Unit tests for the read-only Brainstem data root: which paths it serves (inside a .brainstem_data folder next to
// a brainstem.py, never through a link, never in a Hive), that it reads and lists them, and that it refuses every
// write. Every folder here is synthetic, built under the test temp folder.
import * as assert from 'assert';
import * as fs from 'fs';
import * as path from 'path';
import { after, describe, test } from 'node:test';

const loader = require('module') as { _resolveFilename: (request: string, ...rest: unknown[]) => string };
const resolveFilename = loader._resolveFilename;
loader._resolveFilename = function (this: unknown, request: string, ...rest: unknown[]): string {
	return request === 'vscode' ? path.join(__dirname, 'vscodeStub.js') : resolveFilename.call(this, request, ...rest);
};

const stub = require('./vscodeStub') as typeof import('./vscodeStub');
const { DataFileSystem, dataFolderRefusal, dataPathRefusal } = require('../dataFs') as typeof import('../dataFs');
const { dataUri } = require('../startup') as typeof import('../startup');

const TMP = path.resolve(process.env.BRAINSTEM_TEST_TMP || path.join(__dirname, '..', '..', '.test-tmp'));
const ROOT = path.join(TMP, `data-fs-${process.pid}`);
const BRAINSTEM = path.join(ROOT, 'home', '.brainstem', 'src', 'rapp_brainstem');
const DATA = path.join(BRAINSTEM, '.brainstem_data');
const MEMORY = path.join(DATA, 'shared_memories', 'memory.json');
const HIVES = path.join(ROOT, 'home', 'Hives');
const IN_HIVE = path.join(HIVES, 'team', 'rapp_brainstem', '.brainstem_data');
const OUTSIDE = path.join(ROOT, 'home', '.ssh');

function write(file: string, text = ''): void {
	fs.mkdirSync(path.dirname(file), { recursive: true });
	fs.writeFileSync(file, text);
}

fs.rmSync(ROOT, { recursive: true, force: true });
write(path.join(BRAINSTEM, 'brainstem.py'), 'raise SystemExit("never run by the tests")\n');
write(path.join(BRAINSTEM, '.brainstem_secret'), 'never served');
write(MEMORY, JSON.stringify({ a: { message: 'Synthetic memory' } }));
write(path.join(DATA, 'memory', '0a1b2c3d', 'user_memory.json'), '{}');
write(path.join(OUTSIDE, 'id_synthetic'), 'never served');
write(path.join(IN_HIVE, '..', 'brainstem.py'), '');
write(path.join(IN_HIVE, 'memory.json'), '{}');
write(path.join(DATA, '.vscode', 'settings.json'), '{"synthetic": true}');
write(path.join(DATA, 'shared_memories', '.vscode', 'notes.json'), '{}');
let linked = false;
try {
	fs.symlinkSync(path.join(OUTSIDE, 'id_synthetic'), path.join(DATA, 'linked.json'));
	fs.symlinkSync(OUTSIDE, path.join(DATA, 'linked-folder'));
	linked = true;
} catch {
	// Symlinks need privileges on some systems.
}
after(() => fs.rmSync(ROOT, { recursive: true, force: true }));

const provider = () => new DataFileSystem(() => [HIVES]);
type Uri = import('vscode').Uri;
const asUri = (u: unknown) => u as Uri;
const uri = (file: string) => asUri(stub.Uri.parse(dataUri(file)));
const code = (run: () => unknown) => {
	try {
		run();
	} catch (error) {
		return (error as { code?: string }).code;
	}
	return 'no error';
};

describe('Brainstem data root', () => {
	test('serves only what is inside a .brainstem_data folder next to a brainstem.py, outside Hives, as a plain full path', () => {
		const folder = (f: string) => dataFolderRefusal(f, [HIVES]);
		assert.deepStrictEqual([
			dataPathRefusal(MEMORY, folder),
			dataPathRefusal(DATA, folder),
			dataPathRefusal(path.join(BRAINSTEM, '.brainstem_secret'), folder),
			dataPathRefusal(path.join(OUTSIDE, 'id_synthetic'), folder),
			dataPathRefusal(path.join(IN_HIVE, 'memory.json'), folder),
			dataPathRefusal(`${DATA}${path.sep}..${path.sep}.brainstem_secret`, folder),
			dataPathRefusal(path.join('relative', '.brainstem_data', 'memory.json'), folder),
			dataPathRefusal(path.join(DATA, 'missing.json'), folder),
			dataPathRefusal(path.join(ROOT, 'no-brainstem', '.brainstem_data', 'memory.json'), folder),
			dataPathRefusal(path.join(DATA, '.vscode', 'settings.json'), folder),
			dataPathRefusal(path.join(DATA, '.vscode'), folder),
			dataPathRefusal(path.join(DATA, 'shared_memories', '.vscode', 'notes.json'), folder),
		], [
			undefined, undefined, 'not in a Brainstem data folder', 'not in a Brainstem data folder', 'inside a Hive or a reference',
			'not a plain full path', 'not a plain full path', 'no such file', 'no brainstem.py beside it',
			'a settings folder', 'a settings folder', undefined,
		]);
	});

	test('never through a link, and links are left out of its folders', { skip: !linked && 'symlinks need privileges here' }, () => {
		const fsp = provider();
		assert.strictEqual(dataPathRefusal(path.join(DATA, 'linked.json'), f => dataFolderRefusal(f, [])), 'a link');
		assert.strictEqual(dataPathRefusal(path.join(DATA, 'linked-folder', 'id_synthetic'), f => dataFolderRefusal(f, [])), 'a link');
		assert.strictEqual(code(() => fsp.readFile(uri(path.join(DATA, 'linked.json')))), 'FileNotFound');
		assert.ok(!fsp.readDirectory(uri(DATA)).some(([name]) => name.startsWith('linked')));
	});

	test('reads, lists and stats what it serves, read-only', () => {
		const fsp = provider();
		assert.strictEqual(Buffer.from(fsp.readFile(uri(MEMORY))).toString('utf8'), JSON.stringify({ a: { message: 'Synthetic memory' } }));
		assert.deepStrictEqual(fsp.readDirectory(uri(DATA)).filter(([name]) => !name.startsWith('linked')).sort(), [['memory', stub.FileType.Directory], ['shared_memories', stub.FileType.Directory]],
			'the data folder\'s own .vscode, where the host would read settings and tasks, is left out');
		assert.strictEqual(code(() => fsp.readFile(uri(path.join(DATA, '.vscode', 'settings.json')))), 'FileNotFound');
		const stat = fsp.stat(uri(MEMORY));
		assert.deepStrictEqual([stat.type, stat.size, stat.permissions], [stub.FileType.File, fs.statSync(MEMORY).size, stub.FilePermission.Readonly]);
		assert.strictEqual(fsp.stat(uri(DATA)).type, stub.FileType.Directory);
		assert.strictEqual(code(() => fsp.readFile(uri(DATA))), 'FileIsADirectory');
		assert.ok(fsp.serves(MEMORY) && !fsp.serves(path.join(BRAINSTEM, 'brainstem.py')));
	});

	test('refuses every write, and anything it does not serve is not found', () => {
		const fsp = provider();
		assert.deepStrictEqual([
			code(() => fsp.writeFile(uri(MEMORY))),
			code(() => fsp.delete(uri(MEMORY))),
			code(() => fsp.rename(uri(MEMORY))),
			code(() => fsp.createDirectory(uri(path.join(DATA, 'new')))),
			code(() => fsp.readFile(uri(path.join(BRAINSTEM, '.brainstem_secret')))),
			code(() => fsp.readFile(uri(path.join(IN_HIVE, 'memory.json')))),
			code(() => fsp.readFile(asUri(stub.Uri.parse(`brainstem-data://elsewhere${dataUri(MEMORY).slice('brainstem-data://'.length)}`)))),
			code(() => fsp.readFile(asUri(stub.Uri.file(MEMORY)))),
		], ['NoPermissions', 'NoPermissions', 'NoPermissions', 'NoPermissions', 'FileNotFound', 'FileNotFound', 'FileNotFound', 'FileNotFound']);
		assert.strictEqual(fs.readFileSync(MEMORY, 'utf8'), JSON.stringify({ a: { message: 'Synthetic memory' } }), 'the file is as it was');
	});

	test('follows the Brainstem\'s own writes to a file it shows, even one replaced whole', async () => {
		const fsp = provider();
		const seen: string[] = [];
		fsp.onDidChangeFile(events => events.forEach(event => seen.push(event.uri.path)));
		const watching = fsp.watch(uri(MEMORY), { recursive: false, excludes: [] });
		try {
			// The file system's watcher can miss what happens just after it starts: the Brainstem's replace-whole
			// write is repeated, a few times at most, until a change is seen.
			for (let attempt = 0; attempt < 5 && !seen.length; attempt++) {
				await new Promise(resolve => setTimeout(resolve, 200));
				const aside = `${MEMORY}.tmp`;
				fs.writeFileSync(aside, JSON.stringify({ b: { message: `Replaced ${attempt}` } }));
				fs.renameSync(aside, MEMORY);
				for (let i = 0; i < 20 && !seen.length; i++) {
					await new Promise(resolve => setTimeout(resolve, 100));
				}
			}
			assert.ok(seen.length, 'no change was seen');
			assert.ok(seen.every(p => p === uri(MEMORY).path), `only the file itself is reported: ${seen.join(', ')}`);
		} finally {
			watching.dispose();
			fsp.dispose();
		}
	});
});
