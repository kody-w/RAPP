// A read-only view of the Hives on this device (HIVE-MD). Nothing here writes, runs or follows links;
// file contents are never read except the device's own references.json pin list.
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';

export const MAX_ENTRIES = 500;
const MAX_PIN_FILE = 64 * 1024;
const LABEL = /^[a-z0-9][a-z0-9-]{0,31}$/;

export interface Entry {
	readonly name: string;
	readonly path: string;
	readonly kind: 'file' | 'folder';
}

export interface Listing {
	readonly entries: readonly Entry[];
	readonly more: number;
}

export interface Member {
	readonly name: string;
	readonly keys: readonly Entry[];
}

export interface WaitingRequest {
	readonly name: string;
	readonly device: string;
	readonly path: string;
}

export interface Hive {
	readonly name: string;
	readonly path: string;
	readonly rules?: string;
	readonly members: readonly Member[];
	readonly requests: readonly WaitingRequest[];
	readonly rooms: readonly Entry[];
}

export interface Reference {
	readonly label: string;
	readonly path: string;
	readonly present: boolean;
}

function expandHome(p: string): string {
	return p === '~' ? os.homedir() : p.startsWith('~/') || p.startsWith('~\\') ? path.join(os.homedir(), p.slice(2)) : p;
}

// RAPP_HIVES, or Hives in the home folder: the same place the Hive agent looks.
export function hivesHome(env: NodeJS.ProcessEnv = process.env): string {
	return path.resolve(expandHome(env.RAPP_HIVES || path.join('~', 'Hives')));
}

function kindOf(full: string): Entry['kind'] | undefined {
	let stat: fs.Stats;
	try {
		stat = fs.lstatSync(full);
	} catch {
		return undefined;
	}
	if (stat.isSymbolicLink()) {
		return undefined;
	}
	return stat.isDirectory() ? 'folder' : stat.isFile() ? 'file' : undefined;
}

// `root` joined with `parts`, when no part on the way is a link (a Hive may not point outside itself).
function plainPath(root: string, ...parts: string[]): string | undefined {
	let at = root;
	for (const part of parts) {
		at = path.join(at, part);
		if (!kindOf(at)) {
			return undefined;
		}
	}
	return at;
}

// A folder's plain files and folders: hidden names and links are left out, and the list stops at
// MAX_ENTRIES. A folder that is itself a link lists nothing.
export function listFolder(folder: string): Listing {
	if (kindOf(folder) !== 'folder') {
		return { entries: [], more: 0 };
	}
	let names: string[];
	try {
		names = fs.readdirSync(folder);
	} catch {
		return { entries: [], more: 0 };
	}
	const entries: Entry[] = [];
	for (const name of names.filter(n => !n.startsWith('.')).sort((a, b) => a.localeCompare(b))) {
		const full = path.join(folder, name);
		const kind = kindOf(full);
		if (kind) {
			entries.push({ name, path: full, kind });
		}
	}
	entries.sort((a, b) => (a.kind === b.kind ? 0 : a.kind === 'folder' ? -1 : 1));
	return { entries: entries.slice(0, MAX_ENTRIES), more: Math.max(0, entries.length - MAX_ENTRIES) };
}

// The Hives the Brainstem keeps here: folders holding .git/rapp-hive/device.json, with no link on the way.
// The Hives folder itself may be a link the person made; nothing inside a Hive may be.
export function listHives(home: string): string[] {
	let root = home;
	try {
		root = fs.realpathSync(home);
	} catch {
		return [];
	}
	return listFolder(root).entries
		.filter(e => e.kind === 'folder' && plainPath(e.path, '.git', 'rapp-hive', 'device.json') && kindOf(path.join(e.path, '.git', 'rapp-hive', 'device.json')) === 'file')
		.map(e => e.name);
}

const folders = (dir: string) => listFolder(dir).entries.filter(e => e.kind === 'folder');
const mdFiles = (dir: string) => listFolder(dir).entries.filter(e => e.kind === 'file' && e.name.endsWith('.md'));

export function readHive(home: string, name: string): Hive {
	let base = home;
	try {
		base = fs.realpathSync(home);
	} catch {
		// an unreadable Hives folder lists nothing below
	}
	const root = path.join(base, name);
	const members = folders(path.join(root, 'members'))
		.map(m => ({ name: m.name, keys: mdFiles(path.join(m.path, 'keys')) }))
		.filter(m => m.keys.length > 0);
	const requests = folders(path.join(root, 'requests'))
		.flatMap(r => mdFiles(r.path).map(f => ({ name: r.name, device: f.name.slice(0, -3), path: f.path })));
	const rules = path.join(root, 'HIVE.md');
	return {
		name,
		path: root,
		rules: kindOf(rules) === 'file' ? rules : undefined,
		members,
		requests,
		rooms: folders(path.join(root, 'shared')),
	};
}

// The references this device pinned for a Hive (label to folder). Pins live outside the committed tree.
export function readReferences(hivePath: string): Reference[] {
	const file = plainPath(hivePath, '.git', 'rapp-hive', 'references.json');
	if (!file || kindOf(file) !== 'file') {
		return [];
	}
	let pins: unknown;
	try {
		if (fs.statSync(file).size > MAX_PIN_FILE) {
			return [];
		}
		pins = JSON.parse(fs.readFileSync(file, 'utf8'));
	} catch {
		return [];
	}
	if (typeof pins !== 'object' || pins === null || Array.isArray(pins)) {
		return [];
	}
	return Object.entries(pins as Record<string, unknown>)
		.filter((pin): pin is [string, string] => LABEL.test(pin[0]) && typeof pin[1] === 'string' && path.isAbsolute(pin[1]))
		.map(([label, folder]) => ({ label, path: folder, present: kindOf(folder) === 'folder' }))
		.sort((a, b) => a.label.localeCompare(b.label));
}

/**
 * Whether a path.relative() result leaves the folder it is relative to: `..`, `../…`, or another drive. A name
 * that merely starts with two dots, such as `..notes`, stays inside.
 */
export function leaves(rel: string): boolean {
	return rel === '..' || rel.startsWith(`..${path.sep}`) || path.isAbsolute(rel);
}

// Whether `inner` is `outer` or inside it, judged on real paths, case-insensitively where the system is.
/**
 * Whether a program given by full path lies inside `outer`, as it is given or where a link leads: a program started
 * by a path inside a Hive reads the settings of the folders it was started from (Python reads a venv's pyvenv.cfg
 * beside itself or one folder up, as given, and on Linux its standard library from there), whatever those folders
 * are links to. So the path as given counts, and so do the real places of the program, its folder and the one above.
 */
export function fileInside(file: string, outer: string): boolean {
	const given = path.resolve(file);
	return [given, path.dirname(given), path.dirname(path.dirname(given))].some(place => isInside(place, outer)) || isInsideAsGiven(given, outer);
}

// Inside `outer` as the path is written, no link followed (against `outer` as given and as it really is).
function isInsideAsGiven(inner: string, outer: string): boolean {
	const fold = (p: string) => (process.platform === 'linux' ? p : p.toLowerCase());
	let real = path.resolve(outer);
	try {
		real = fs.realpathSync.native(outer);
	} catch {
		// Not there: judged as given.
	}
	return [path.resolve(outer), real].some(root => {
		const rel = path.relative(fold(root), fold(inner));
		return rel === '' || !leaves(rel);
	});
}

export function isInside(inner: string, outer: string): boolean {
	const real = (p: string) => {
		try {
			return fs.realpathSync.native(p);
		} catch {
			return path.resolve(p);
		}
	};
	const fold = (p: string) => (process.platform === 'linux' ? p : p.toLowerCase());
	const a = fold(real(inner)), b = fold(real(outer));
	const rel = path.relative(b, a);
	return rel === '' || !leaves(rel);
}
