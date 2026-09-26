// Where the global Brainstem lives on this device, how it is started, and what the app does when a window
// starts. No vscode here, so all of it is unit tested.
import * as crypto from 'crypto';
import * as fs from 'fs';
import * as path from 'path';
import * as url from 'url';
import { isInside } from './hives';

export type FolderSource = 'setting' | 'health' | 'default';

export interface FolderRefusal {
	readonly source: FolderSource;
	readonly reason: string;
}

export interface BrainstemFolder {
	readonly folder?: string;
	readonly source?: FolderSource;
	readonly refused: readonly FolderRefusal[];
}

export interface FolderInputs {
	/** The setting rapp.brainstemFolder; empty when not set. */
	readonly setting: string;
	/** `brainstem_dir` from the running Brainstem's /health, when it answered with one. */
	readonly healthDir?: string;
	readonly home: string;
	/** The Hives folder and every reference: a Brainstem folder may never be inside one. */
	readonly forbidden: readonly string[];
	readonly platform?: NodeJS.Platform;
	/** This user's id, for the check on a folder /health reports; process.getuid() when left out. */
	readonly uid?: number;
}

/** The installer's default location of the global Brainstem. */
export function defaultBrainstemFolder(home: string): string {
	return path.join(home, '.brainstem', 'src', 'rapp_brainstem');
}

// A leading ~ in the setting is the home folder.
function expandHome(raw: string, home: string): string {
	return raw === '~' ? home : /^~[\\/]/.test(raw) ? path.join(home, raw.slice(2)) : raw;
}

function isFile(file: string): boolean {
	try {
		return fs.statSync(file).isFile();
	} catch {
		return false;
	}
}

/** Why a folder cannot be the global Brainstem, or undefined when it can. */
export function folderRefusal(folder: string, forbidden: readonly string[], platform: NodeJS.Platform = process.platform): string | undefined {
	return localFolderRefusal(folder, forbidden, platform) ?? (isFile(path.join(folder, 'brainstem.py')) ? undefined : 'has no brainstem.py');
}

type Owner = { readonly uid: number; readonly mode: number };

/**
 * Why a folder that /health reported is not taken on its own say. /health is an unauthenticated answer on a
 * loopback port, so such a folder, given as its real path, must be this user's and writable by no one else, and
 * every folder above it must be this user's or root's and writable by no one else unless sticky (as /tmp is, so
 * no one else can replace what is in it). Windows has no such mode bits: there a reported folder is never
 * taken on its own say.
 */
export function ownershipRefusal(folder: string, uid: number | undefined, platform: NodeJS.Platform = process.platform, stat: (folder: string) => Owner = fs.statSync): string | undefined {
	if (platform === 'win32' || uid === undefined) {
		return 'not the setting\'s or the default folder';
	}
	for (let current = folder, first = true; ; first = false) {
		let info: Owner;
		try {
			info = stat(current);
		} catch {
			return 'no such folder';
		}
		if (first) {
			if (info.uid !== uid) {
				return 'not owned by you';
			}
			if (info.mode & 0o022) {
				return 'writable by others';
			}
		} else if (info.uid !== uid && info.uid !== 0) {
			return 'inside a folder someone else owns';
		} else if (info.mode & 0o022 && !(info.mode & 0o1000)) {
			return 'inside a folder others can change';
		}
		const parent = path.dirname(current);
		if (parent === current) {
			return undefined;
		}
		current = parent;
	}
}

function realPath(folder: string): string | undefined {
	try {
		return fs.realpathSync.native(folder);
	} catch {
		return undefined;
	}
}

/**
 * The global Brainstem folder: the setting, else the running Brainstem's own folder, else the default. The folder
 * /health reports counts as the setting's or the default one when it is that folder (through a link or not),
 * and then under that folder's own path, never the reported one; otherwise only as its real path, when it passes
 * the ownership check above.
 */
export function resolveBrainstemFolder(inputs: FolderInputs): BrainstemFolder {
	const setting = inputs.setting.trim();
	const candidates: [FolderSource, string | undefined][] = [
		['setting', setting ? expandHome(setting, inputs.home) : undefined],
		['health', inputs.healthDir],
		['default', defaultBrainstemFolder(inputs.home)],
	];
	const known = candidates.filter((c): c is [FolderSource, string] => c[0] !== 'health' && c[1] !== undefined);
	const refused: FolderRefusal[] = [];
	for (const [source, reported] of candidates) {
		if (reported === undefined) {
			continue;
		}
		let folder = reported;
		let from = source;
		let reason = folderRefusal(folder, inputs.forbidden, inputs.platform);
		if (!reason && source === 'health') {
			const real = realPath(reported);
			const same = known.find(([, k]) => real !== undefined && realPath(k) === real);
			if (same) {
				[from, folder] = same;
			} else {
				folder = real ?? reported;
				reason = ownershipRefusal(folder, inputs.uid ?? process.getuid?.(), inputs.platform);
			}
		}
		if (!reason) {
			return { folder: path.resolve(folder), source: from, refused };
		}
		refused.push({ source, reason });
	}
	return { refused };
}

export interface StartCommand {
	readonly cwd: string;
	readonly shellPath: string;
	readonly shellArgs: readonly string[];
}

/**
 * The variable naming the file, in the app's own storage, where a start script that stopped with an error has
 * its exit code written, so the app can say so while the terminal still shows why.
 */
export const START_STATUS_ENV = 'BRAINSTEM_APP_START_STATUS';

// On macOS and Linux: a start script that stops with an error (anything but 0, or the 130 and 143 of Ctrl+C and a
// plain stop) leaves its terminal open on what it printed until Return is pressed, and its exit code in the file
// START_STATUS_ENV names (quoted: the app's storage folder can have a space in its path). A normal stop ends the
// terminal with 0, so the host raises no alert that quotes this command.
const POSIX_START = [
	'bash ./start.sh',
	's=$?',
	'case $s in 0|130|143) exit 0;; esac',
	`[ -z "$${START_STATUS_ENV}" ] || echo $s > "$${START_STATUS_ENV}"`,
	'echo',
	`echo Your Brainstem stopped with exit code $s. What it printed is above. Press Return to close this terminal.`,
	'read -r _',
	'exit 0',
].join('; ');

/**
 * How to run a Brainstem folder's own start script as a terminal's own process, or undefined when it has none:
 * the terminal then ends when the script does, except that on macOS and Linux a script that stops with an
 * error keeps its terminal open on what it printed. The script runs as a child of that process, never in its
 * place (the grail's start.sh ends by exec'ing its Python), so the host sees a program running there and asks
 * before quitting stops it (terminal.integrated.confirmOnExit).
 */
export function startCommand(folder: string, forbidden: readonly string[], platform: NodeJS.Platform = process.platform): StartCommand | undefined {
	const windows = platform === 'win32';
	const script = path.join(folder, windows ? 'start.ps1' : 'start.sh');
	if (!isFile(script) || forbidden.some(root => isInside(script, root))) {
		return undefined;
	}
	return windows
		? { cwd: folder, shellPath: 'powershell.exe', shellArgs: ['-ExecutionPolicy', 'Bypass', '-File', '.\\start.ps1'] }
		: { cwd: folder, shellPath: 'bash', shellArgs: ['-c', POSIX_START] };
}

/** A failed start's exit code, as the start wrapper wrote it to `file`; undefined while there is none. */
export function startFailure(file: string): number | undefined {
	let text: string;
	try {
		text = fs.readFileSync(file, 'utf8').trim();
	} catch {
		return undefined;
	}
	return /^\d{1,3}$/.test(text) ? Number(text) : undefined;
}

/**
 * The note, in the app's own storage, of which windows show the RAPP Workspace: this launch of the app, the
 * extension hosts (one per window) that show it, and when a window last left it (its folder closed, a reload, a
 * switch). Written only when that changes, synchronously, so it holds even as a window closes.
 */
export interface ShownNote {
	readonly launch: string;
	readonly hosts: readonly number[];
	readonly leftAt: number;
}

/** How long after a window left the RAPP Workspace an empty window still counts it as shown (a folder just closed). */
export const SHOWN_GRACE_MS = 15000;

export function readShownNote(file: string): ShownNote | undefined {
	try {
		const value: unknown = JSON.parse(fs.readFileSync(file, 'utf8'));
		if (typeof value !== 'object' || value === null) {
			return undefined;
		}
		const { launch, hosts, leftAt } = value as Record<string, unknown>;
		return typeof launch === 'string' && Array.isArray(hosts) && typeof leftAt === 'number'
			? { launch, hosts: hosts.filter((h): h is number => Number.isSafeInteger(h) && h > 0), leftAt }
			: undefined;
	} catch {
		return undefined;
	}
}

/**
 * Writes a file whole: a partial file, then a rename over it, so no reader ever sees it half written. On Windows a
 * rename can briefly fail while another program (a virus scanner, say) holds the file, so it is tried again a few
 * times, as the host itself does; a partial file is never left behind.
 */
export function writeWhole(file: string, text: string, platform: NodeJS.Platform = process.platform): void {
	fs.mkdirSync(path.dirname(file), { recursive: true });
	const partial = `${file}.${process.pid}.partial`;
	try {
		fs.writeFileSync(partial, text);
		for (let attempt = 0; ; attempt++) {
			try {
				fs.renameSync(partial, file);
				return;
			} catch (error) {
				const code = (error as NodeJS.ErrnoException).code ?? '';
				if (platform !== 'win32' || attempt >= 9 || !['EACCES', 'EPERM', 'EBUSY'].includes(code)) {
					throw error;
				}
				Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 20 * (attempt + 1));
			}
		}
	} catch (error) {
		removeLeftover(partial);
		throw error;
	}
}

/**
 * Creates a file whole, and only if it does not exist yet: a partial file, then a link to it under its name,
 * which fails if the name is taken, so a file someone else just made is never replaced. Says whether it made it.
 */
export function createWhole(file: string, text: string): boolean {
	fs.mkdirSync(path.dirname(file), { recursive: true });
	const partial = `${file}.${process.pid}.partial`;
	try {
		fs.writeFileSync(partial, text);
		try {
			fs.linkSync(partial, file);
			return true;
		} catch (error) {
			if ((error as NodeJS.ErrnoException).code === 'EEXIST') {
				return false;
			}
			// No links on this volume (FAT, exFAT, some network drives): made with an exclusive write instead,
			// which still never replaces a file someone else just made.
			fs.writeFileSync(file, text, { flag: 'wx' });
			return true;
		}
	} catch (error) {
		if ((error as NodeJS.ErrnoException).code === 'EEXIST') {
			return false;
		}
		throw error;
	} finally {
		removeLeftover(partial);
	}
}

// A partial file that cannot be removed now never hides the error that left it.
function removeLeftover(file: string): void {
	try {
		fs.rmSync(file, { force: true });
	} catch {
		// Left behind; harmless beside the file it was for.
	}
}

export function writeShownNote(file: string, note: ShownNote): void {
	writeWhole(file, JSON.stringify(note));
}

/** Whether a process is still running (one that exists but is another user's counts too). */
export function isRunning(pid: number): boolean {
	try {
		process.kill(pid, 0);
		return true;
	} catch (error) {
		return (error as NodeJS.ErrnoException).code === 'EPERM';
	}
}

/**
 * Whether another window of this launch shows the RAPP Workspace (its extension host still runs), or one left it
 * less than SHOWN_GRACE_MS ago. `self` is this window's extension host, which never counts.
 */
export function shownElsewhere(note: ShownNote | undefined, launch: string, self: number, now: number, running: (pid: number) => boolean = isRunning): boolean {
	if (!note || note.launch !== launch) {
		return false;
	}
	return note.hosts.some(pid => pid !== self && running(pid)) || Math.abs(now - note.leftAt) < SHOWN_GRACE_MS;
}

/**
 * The glob the host's integrated browser matches its open tabs against: any page of the Brainstem at `url`
 * (its `http://host:port`). The host reads [ ] as a character class, so [::1] becomes *::1*.
 */
export function browserReuseFilter(url: string): string {
	return `${url.replace(/[[\]]/g, '*')}/**`;
}

/**
 * The RAPP Workspace's agents/ folder: the setting rapp.agentsFolder when it names a usable folder, else the
 * Brainstem's own agents/, which must exist. Neither may sit inside a Hive or a reference.
 */
export function resolveAgentsFolder(inputs: { readonly setting: string; readonly root?: string; readonly home: string; readonly forbidden: readonly string[]; readonly platform?: NodeJS.Platform }): AgentsFolder {
	const refused: FolderRefusal[] = [];
	const setting = inputs.setting.trim();
	if (setting) {
		const folder = expandHome(setting, inputs.home);
		const reason = localFolderRefusal(folder, inputs.forbidden, inputs.platform);
		if (!reason) {
			return { folder: path.resolve(folder), source: 'setting', refused };
		}
		refused.push({ source: 'setting', reason });
	}
	if (inputs.root) {
		const folder = path.join(inputs.root, 'agents');
		const reason = localFolderRefusal(folder, inputs.forbidden, inputs.platform);
		if (!reason) {
			return { folder, source: 'brainstem', refused };
		}
		refused.push({ source: 'default', reason: `its agents/ ${reason === 'no such folder' ? 'is missing' : `is ${reason}`}` });
	}
	return { refused };
}

export interface AgentsFolder {
	readonly folder?: string;
	readonly source?: 'setting' | 'brainstem';
	readonly refused: readonly FolderRefusal[];
}

// The checks every folder here passes: a full local path to an existing folder outside Hives and references.
function localFolderRefusal(folder: string, forbidden: readonly string[], platform: NodeJS.Platform = process.platform): string | undefined {
	if (/^[A-Za-z][A-Za-z0-9+.-]+:/.test(folder) || /^[\\/]{2}/.test(folder)) {
		return 'not a local path';
	}
	if (!(platform === 'win32' ? /^[A-Za-z]:[\\/]/.test(folder) : folder.startsWith('/'))) {
		return 'not an absolute path';
	}
	let stat: fs.Stats;
	try {
		stat = fs.statSync(folder);
	} catch {
		return 'no such folder';
	}
	if (!stat.isDirectory()) {
		return 'not a folder';
	}
	return forbidden.some(root => isInside(folder, root)) ? 'inside a Hive or a reference' : undefined;
}

/** The name of the workspace file the app keeps in its own storage for the RAPP Workspace. */
export const WORKSPACE_FILE = 'RAPP Workspace.code-workspace';

/** Where each Agents folder's own RAPP Workspace file lives in the app's storage, one folder per Agents folder. */
export const WORKSPACES_FOLDER = 'workspaces';

/**
 * The folder name of an Agents folder's own workspace file: a short digest of its real path (links followed, and
 * letter case folded where the file system ignores it, as isInside compares), so one folder has one file.
 */
export function workspaceKey(agentsFolder: string, platform: NodeJS.Platform = process.platform): string {
	let real: string;
	try {
		real = fs.realpathSync.native(agentsFolder);
	} catch {
		real = path.resolve(agentsFolder);
	}
	return crypto.createHash('sha256').update(platform === 'linux' ? real : real.toLowerCase()).digest('hex').slice(0, 16);
}

/**
 * Whether a workspace file is one of the app's own: the one earlier builds kept, or an Agents folder's own. Its
 * name and its key folder's are matched ignoring letter case where the file system does, as samePath does.
 */
export function isOwnWorkspaceFile(file: string, storage: string, platform: NodeJS.Platform = process.platform): boolean {
	if (samePath(file, path.join(storage, WORKSPACE_FILE))) {
		return true;
	}
	const fold = (name: string) => (platform === 'linux' ? name : name.toLowerCase());
	const folder = path.dirname(path.resolve(file));
	return fold(path.basename(file)) === fold(WORKSPACE_FILE) && /^[0-9a-f]{16}(-\d{1,3})?$/.test(fold(path.basename(folder))) && samePath(path.dirname(folder), path.join(storage, WORKSPACES_FOLDER));
}

/**
 * The roots on disk a workspace file names, as full paths, read the way the host reads it (readTolerant, past a
 * slip such as a missing comma, and with the host's own test of a folder entry). None when it cannot be read now,
 * or when the host would refuse to open it as a workspace (it holds no list of folders: empty, say, or cut short
 * before them).
 */
export function rootsOf(file: string): string[] {
	let parsed: unknown;
	try {
		parsed = readTolerant(fs.readFileSync(file, 'utf8'));
	} catch {
		return [];
	}
	const folders = isRecord(parsed) && Array.isArray(parsed.folders) ? parsed.folders : [];
	const roots: string[] = [];
	for (const entry of folders) {
		if (!isRecord(entry) || (entry.name && typeof entry.name !== 'string')) {
			continue;
		}
		if (typeof entry.path === 'string') {
			roots.push(path.resolve(path.dirname(file), entry.path));
		} else if (typeof entry.uri === 'string' && /^file:/i.test(entry.uri)) {
			try {
				roots.push(url.fileURLToPath(entry.uri));
			} catch {
				// Not a local file address.
			}
		}
	}
	return roots;
}

type TokenKind = '{' | '}' | '[' | ']' | ',' | ':' | 'value' | 'end';

/**
 * A JSON value read the way the host reads a workspace file, with comments and trailing commas, and past slips
 * (a missing comma or colon, a stray character or word, a cut-short end), leaving out only what cannot be read.
 * It follows the recovery rules of the host's fault-tolerant reader (src/vs/base/common/json.ts in Code - OSS),
 * and a test compares the two on many damaged files. Undefined for text that holds no value.
 */
export function readTolerant(text: string): unknown {
	const length = text.length;
	let at = 0;
	let kind: TokenKind = 'end';
	let value: unknown;
	const isSpace = (c: number) => c === 0x20 || c === 0x09 || c === 0x0b || c === 0x0c || c === 0xa0 || c === 0x1680
		|| (c >= 0x2000 && c <= 0x200b) || c === 0x202f || c === 0x205f || c === 0x3000 || c === 0xfeff;
	const isBreak = (c: number) => c === 0x0a || c === 0x0d || c === 0x2028 || c === 0x2029;
	const isDigit = (c: number) => c >= 0x30 && c <= 0x39;
	const isWordChar = (c: number) => !isSpace(c) && !isBreak(c) && !'{}[]":,/'.includes(String.fromCharCode(c));

	function readString(): string {
		let out = '';
		let start = at;
		for (;;) {
			if (at >= length) {
				return out + text.slice(start, at);
			}
			const c = text.charCodeAt(at);
			if (c === 0x22) {
				out += text.slice(start, at);
				at++;
				return out;
			}
			if (c === 0x5c) {
				out += text.slice(start, at);
				at++;
				if (at >= length) {
					return out;
				}
				const escaped = text[at++];
				const simple: Record<string, string> = { '"': '"', '\\': '\\', '/': '/', b: '\b', f: '\f', n: '\n', r: '\r', t: '\t' };
				if (escaped in simple) {
					out += simple[escaped];
				} else if (escaped === 'u') {
					let digits = 0;
					let code = 0;
					while (digits < 4 && /[0-9a-fA-F]/.test(text[at] ?? '')) {
						code = code * 16 + parseInt(text[at], 16);
						at++;
						digits++;
					}
					if (digits === 4) {
						out += String.fromCharCode(code);
					}
				}
				start = at;
				continue;
			}
			if (c === 0x0a || c === 0x0d) {
				return out + text.slice(start, at);
			}
			at++;
		}
	}

	function readNumber(): string {
		const start = at;
		if (text.charCodeAt(at) === 0x2d) {
			at++;
		}
		if (text.charCodeAt(at) === 0x30) {
			at++;
		} else {
			while (at < length && isDigit(text.charCodeAt(at))) {
				at++;
			}
		}
		if (text[at] === '.') {
			at++;
			if (!isDigit(text.charCodeAt(at))) {
				return text.slice(start, at);
			}
			while (at < length && isDigit(text.charCodeAt(at))) {
				at++;
			}
		}
		let end = at;
		if (text[at] === 'e' || text[at] === 'E') {
			at++;
			if (text[at] === '+' || text[at] === '-') {
				at++;
			}
			if (isDigit(text.charCodeAt(at))) {
				while (at < length && isDigit(text.charCodeAt(at))) {
					at++;
				}
				end = at;
			}
		}
		return text.slice(start, end);
	}

	// The next token that carries meaning: white space, comments and anything unreadable are passed over.
	function next(): TokenKind {
		for (;;) {
			if (at >= length) {
				return kind = 'end';
			}
			const c = text.charCodeAt(at);
			const ch = text[at];
			if (isSpace(c) || isBreak(c)) {
				at++;
			} else if ('{}[],:'.includes(ch)) {
				at++;
				return kind = ch as TokenKind;
			} else if (ch === '"') {
				at++;
				value = readString();
				return kind = 'value';
			} else if (ch === '/' && text[at + 1] === '/') {
				while (at < length && !isBreak(text.charCodeAt(at))) {
					at++;
				}
			} else if (ch === '/' && text[at + 1] === '*') {
				const close = text.indexOf('*/', at + 2);
				at = close < 0 ? length : close + 2;
			} else if (ch === '/' || (ch === '-' && !isDigit(text.charCodeAt(at + 1)))) {
				at++;
			} else if (ch === '-' || isDigit(c)) {
				const raw = readNumber();
				try {
					const n: unknown = JSON.parse(raw);
					value = typeof n === 'number' ? n : 0;
				} catch {
					value = 0;
				}
				return kind = 'value';
			} else {
				const start = at;
				while (at < length && isWordChar(text.charCodeAt(at))) {
					at++;
				}
				const word = text.slice(start, at);
				if (word === 'true' || word === 'false' || word === 'null') {
					value = word === 'null' ? null : word === 'true';
					return kind = 'value';
				}
			}
		}
	}

	// Passes over tokens up to one of `until`.
	function skip(until: readonly TokenKind[]): void {
		while (kind !== 'end' && !until.includes(kind)) {
			next();
		}
	}

	function readValue(put: (v: unknown) => void): boolean {
		if (kind === '{') {
			const object: Record<string, unknown> = {};
			put(object);
			readMembers(object);
			return true;
		}
		if (kind === '[') {
			const list: unknown[] = [];
			put(list);
			readItems(list);
			return true;
		}
		if (kind === 'value') {
			put(value);
			next();
			return true;
		}
		return false;
	}

	function readMembers(object: Record<string, unknown>): void {
		next();
		while (kind !== '}' && kind !== 'end') {
			if (kind === ',' && next() === '}') {
				break;
			}
			if (kind !== 'value' || typeof value !== 'string') {
				skip(['}', ',']);
				continue;
			}
			const key = value;
			if (next() !== ':') {
				skip(['}', ',']);
				continue;
			}
			next();
			if (!readValue(v => { object[key] = v; })) {
				skip(['}', ',']);
			}
		}
		next();
	}

	function readItems(list: unknown[]): void {
		next();
		while (kind !== ']' && kind !== 'end') {
			if (kind === ',' && next() === ']') {
				break;
			}
			if (!readValue(v => { list.push(v); })) {
				skip([']', ',']);
			}
		}
		next();
	}

	let result: unknown;
	next();
	readValue(v => { result = v; });
	return result;
}

/** The Brainstem's data folder: .brainstem_data next to brainstem.py, where its local_storage.py keeps memory. */
export const DATA_FOLDER = '.brainstem_data';
/** The scheme the app serves the Brainstem data root under, read-only (dataFs.ts). */
export const DATA_SCHEME = 'brainstem-data';
/** The RAPP Workspace's two roots, as the owner names them. */
export const AGENTS_ROOT = 'Agents';
export const DATA_ROOT = 'Brainstem data';
const TITLE = '${dirty}${activeEditorShort}${separator}RAPP Workspace${separator}${appName}';
// Noise in the data root: the share ledgers' SQLite files and RAR's catalog cache. The host matches files.exclude
// against each root's own relative paths only, so these hide such files in the Agents root too. The Brainstem's
// secret sits beside the data folder, never in it; it is hidden anyway.
const DATA_EXCLUDES = ['**/*.sqlite3*', '**/*cache*.json', '**/.brainstem_secret'];

/** The Brainstem's data folder, when it is there: a real folder (not a link) outside Hives and references. */
export function resolveDataFolder(root: string | undefined, forbidden: readonly string[], platform: NodeJS.Platform = process.platform): string | undefined {
	if (!root) {
		return undefined;
	}
	const folder = path.join(root, DATA_FOLDER);
	if (localFolderRefusal(folder, forbidden, platform)) {
		return undefined;
	}
	try {
		return fs.lstatSync(folder).isSymbolicLink() ? undefined : folder;
	} catch {
		return undefined;
	}
}

/**
 * A file or folder in the Brainstem's data, as a brainstem-data: URI of its own path, which the app's read-only
 * provider (dataFs.ts) serves: the Brainstem data root in the workspace file, and what View raw opens.
 */
export function dataUri(file: string, platform: NodeJS.Platform = process.platform): string {
	const slashed = platform === 'win32' ? `/${file.replace(/\\/g, '/')}` : file;
	return `${DATA_SCHEME}://${slashed.split('/').map(encodeURIComponent).join('/')}`;
}

/** The local path a brainstem-data: URI's path names, or undefined when it names none. */
export function dataLocalPath(uriPath: string, platform: NodeJS.Platform = process.platform): string | undefined {
	if (platform === 'win32') {
		const drive = /^\/([A-Za-z]:)(\/.*)?$/.exec(uriPath);
		return drive ? `${drive[1]}${(drive[2] ?? '/').replace(/\//g, '\\')}` : undefined;
	}
	return uriPath.startsWith('/') ? uriPath : undefined;
}

/** Absolute globs for a folder and everything in it: what earlier builds wrote to keep the data root read-only. */
export function folderGlobs(folder: string): string[] {
	const slashed = folder.split(path.sep).join('/').replace(/\/+$/, '');
	return [slashed, `${slashed}/**`];
}

function ourFolders(agentsFolder: string, dataFolder?: string): Record<string, string>[] {
	return [{ name: AGENTS_ROOT, path: agentsFolder }, ...(dataFolder ? [{ name: DATA_ROOT, uri: dataUri(dataFolder) }] : [])];
}

function ourSettings(dataFolder?: string): Record<string, unknown> {
	const settings: Record<string, unknown> = { 'window.title': TITLE };
	if (dataFolder) {
		settings['files.exclude'] = Object.fromEntries(DATA_EXCLUDES.map(glob => [glob, true]));
	}
	return settings;
}

/**
 * The RAPP Workspace as a workspace file with two roots, Agents (agents/) and Brainstem data (.brainstem_data/,
 * served read-only by the app's own provider, since the running Brainstem writes it), and nothing else of the
 * Brainstem's folder: VS Code's clean way to give a window its own title (window.title is a window setting) and
 * per-root rules without writing anything into the Brainstem's folder.
 */
export function workspaceFileText(agentsFolder: string, dataFolder?: string): string {
	return JSON.stringify({ folders: ourFolders(agentsFolder, dataFolder), settings: ourSettings(dataFolder) }, null, '\t') + '\n';
}

// A .code-workspace file is JSON with comments and trailing commas allowed: this reads it as plain JSON.
function withoutComments(text: string): string {
	return withoutTrailingCommas(commentsOut(text.replace(/^\uFEFF/, '')));
}

// A trailing comma before } or ], outside strings (comments are gone by now).
function withoutTrailingCommas(text: string): string {
	let out = '';
	for (let i = 0; i < text.length; i++) {
		const c = text[i];
		if (c === '"') {
			const start = i;
			for (i++; i < text.length && text[i] !== '"'; i++) {
				if (text[i] === '\\') {
					i++;
				}
			}
			out += text.slice(start, i + 1);
		} else if (!(c === ',' && /^\s*[}\]]/.test(text.slice(i + 1)))) {
			out += c;
		}
	}
	return out;
}

function commentsOut(text: string): string {
	let out = '';
	for (let i = 0; i < text.length; i++) {
		const c = text[i];
		if (c === '"') {
			const start = i;
			for (i++; i < text.length && text[i] !== '"'; i++) {
				if (text[i] === '\\') {
					i++;
				}
			}
			out += text.slice(start, i + 1);
		} else if (c === '/' && text[i + 1] === '/') {
			while (i < text.length && text[i] !== '\n') {
				i++;
			}
			out += '\n';
		} else if (c === '/' && text[i + 1] === '*') {
			i = text.indexOf('*/', i + 2);
			i = i < 0 ? text.length : i + 1;
		} else {
			out += c;
		}
	}
	return out;
}

const isRecord = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v);

// The same JSON, whatever the order of an object's keys (a person's own order is never a reason to rewrite a file).
function sameJson(a: unknown, b: unknown): boolean {
	const canonical = (v: unknown): unknown => Array.isArray(v) ? v.map(canonical)
		: isRecord(v) ? Object.fromEntries(Object.keys(v).sort().map(k => [k, canonical(v[k])])) : v;
	return JSON.stringify(canonical(a)) === JSON.stringify(canonical(b));
}


// Our data entry, as someone left it (their name) when it names this very folder.
function ourDataEntry(entry: unknown, dataFolder: string): Record<string, unknown> {
	const uri = dataUri(dataFolder);
	return isRecord(entry) && entry.uri === uri ? entry : { name: DATA_ROOT, uri };
}

// The person's settings, with the data root's rules added where they are missing, and a person's own value for
// any key winning. Earlier builds kept the data root read-only with a pair of absolute globs; the pair written
// for a data root that is now served read-only, moved or went away is dropped, and nothing else.
function mergedSettings(theirs: Record<string, unknown>, dataFolder: string | undefined, replaced: string | undefined): Record<string, unknown> {
	const ours = ourSettings(dataFolder);
	const merged: Record<string, unknown> = { ...theirs };
	for (const key of ['files.readonlyInclude', 'files.exclude']) {
		const current: Record<string, unknown> = isRecord(theirs[key]) ? { ...theirs[key] } : {};
		const mine = isRecord(ours[key]) ? ours[key] : {};
		if (key === 'files.readonlyInclude' && replaced) {
			folderGlobs(replaced).forEach(glob => delete current[glob]);
		}
		const combined = { ...current, ...Object.fromEntries(Object.entries(mine).filter(([glob]) => !(glob in current))) };
		if (Object.keys(combined).length) {
			merged[key] = combined;
		} else {
			delete merged[key];
		}
	}
	return merged;
}

/**
 * What to write to a RAPP Workspace file, or undefined to leave it as it is. A new file (no current text) gets the
 * app's roots, Agents and then Brainstem data (only while that folder is there), and its settings. An existing
 * file that lists this Agents folder gets only its data root added, updated or removed, and the app's settings
 * where they are missing; Agents and every other root, and everything else someone keeps there, stay as written.
 * A file that does not read as a workspace, or does not list this Agents folder, is left alone.
 */
export function workspaceFileUpdate(current: string | undefined, agentsFolder: string, fileFolder: string, dataFolder?: string): string | undefined {
	if (current === undefined) {
		return workspaceFileText(agentsFolder, dataFolder);
	}
	let parsed: unknown;
	try {
		parsed = JSON.parse(withoutComments(current));
	} catch {
		return undefined;
	}
	if (!isRecord(parsed)) {
		return undefined;
	}
	const folders = Array.isArray(parsed.folders) ? parsed.folders : [];
	const pathOf = (entry: unknown) => (isRecord(entry) && typeof entry.path === 'string' ? path.resolve(fileFolder, entry.path) : undefined);
	// Only a file that lists this Agents folder is updated, and only its data root and rules: Agents and every other
	// root stay exactly as written (a link's spelling, a person's name, their order).
	const agentsAt = folders.findIndex(entry => {
		const where = pathOf(entry);
		return !!where && samePath(where, agentsFolder);
	});
	if (agentsAt < 0) {
		return undefined;
	}
	// The data root is the app's: the first brainstem-data: root, or an earlier build's plain path to this Brainstem's
	// own .brainstem_data folder (only while that folder is known). Every other root stays.
	const isData = (entry: unknown) => (isRecord(entry) && typeof entry.uri === 'string' && entry.uri.startsWith(`${DATA_SCHEME}:`))
		|| (!!dataFolder && path.basename(pathOf(entry) ?? '') === DATA_FOLDER && samePath(pathOf(entry) as string, dataFolder));
	const dataAt = folders.findIndex(isData);
	const previous = dataAt >= 0 ? folders[dataAt] : undefined;
	const dataEntry = dataFolder ? ourDataEntry(previous, dataFolder) : undefined;
	const settings = mergedSettings(isRecord(parsed.settings) ? parsed.settings : {}, dataFolder, pathOf(previous));
	const placed: unknown[] = [...folders];
	if (dataAt >= 0 && dataEntry) {
		placed[dataAt] = dataEntry;
	} else if (dataAt >= 0) {
		placed.splice(dataAt, 1);
	} else if (dataEntry) {
		placed.splice(agentsAt + 1, 0, dataEntry);
	}
	const next: Record<string, unknown> = {
		...parsed,
		folders: placed,
		...(isRecord(parsed.settings) || Object.keys(settings).length ? { settings } : {}),
	};
	if (sameJson(next, parsed)) {
		return undefined;
	}
	// Written anyway: the window's title is added where it is missing.
	next.settings = { 'window.title': TITLE, ...settings };
	return JSON.stringify(next, null, '\t') + '\n';
}

export type StartupAction = 'open-workspace' | 'show-ui' | 'nothing';

export interface StartupInputs {
	/** The window's folders as local paths; undefined for a folder that is not on this device's disk. */
	readonly openFolders: readonly (string | undefined)[];
	/** A workspace file (or an untitled workspace) is open. */
	readonly workspaceFile: boolean;
	/** Documents open in the window, such as a file opened from the command line. */
	readonly openDocuments: number;
	readonly remote: boolean;
	/** The resolved global Brainstem folder. */
	readonly root?: string;
	/** Its agents/ folder: the RAPP Workspace's first root. */
	readonly agents?: string;
	/** Its data folder, the RAPP Workspace's second root, when it is there. */
	readonly data?: string;
	/** The open workspace file is the app's own RAPP Workspace file. */
	readonly ownFile?: boolean;
	readonly openOnStartup: boolean;
	readonly showUI: boolean;
	/**
	 * A window of this launch shows the RAPP Workspace, or did a moment ago (the folder was just closed there):
	 * an empty window then stays empty, as a new window beside it or a closed folder should.
	 */
	readonly workspaceShown: boolean;
}

/** Whether two paths name the same folder, judged on real paths. */
export function samePath(a: string, b: string): boolean {
	return isInside(a, b) && isInside(b, a);
}

/**
 * The window shows the RAPP Workspace: one of the app's own workspace files with agents/ among its roots (in
 * whatever order a person put them, with whatever else they added), or agents/ first, on its own or with the
 * Brainstem's data folder after it.
 */
export function isRappWorkspaceWindow(inputs: Pick<StartupInputs, 'openFolders' | 'agents' | 'data' | 'ownFile'>): boolean {
	const agents = inputs.agents;
	if (!agents) {
		return false;
	}
	if (inputs.ownFile) {
		return inputs.openFolders.some(folder => !!folder && samePath(folder, agents));
	}
	const [first, ...rest] = inputs.openFolders;
	if (!first || !samePath(first, agents)) {
		return false;
	}
	return !rest.length || (rest.length === 1 && !!rest[0] && !!inputs.data && samePath(rest[0], inputs.data));
}

/** The window shows the Brainstem's own folder, which the app opened before it opened agents/ instead. */
export function isBrainstemRootWindow(inputs: Pick<StartupInputs, 'openFolders' | 'workspaceFile' | 'root'>): boolean {
	const [only] = inputs.openFolders;
	return !!inputs.root && !inputs.workspaceFile && inputs.openFolders.length === 1 && !!only && samePath(only, inputs.root);
}

/**
 * The RAPP Workspace shows the Brainstem's own web UI. An empty window opens the RAPP Workspace when no window
 * shows it (never over a document someone opened), and so does a window on the Brainstem's own folder. Any
 * other window is left alone.
 */
export function startupAction(inputs: StartupInputs): StartupAction {
	if (inputs.remote || !inputs.agents) {
		return 'nothing';
	}
	if (isRappWorkspaceWindow(inputs)) {
		return inputs.showUI ? 'show-ui' : 'nothing';
	}
	if (!inputs.workspaceFile && inputs.openFolders.length === 0) {
		return inputs.openOnStartup && !inputs.workspaceShown && inputs.openDocuments === 0 ? 'open-workspace' : 'nothing';
	}
	return isBrainstemRootWindow(inputs) && inputs.openOnStartup ? 'open-workspace' : 'nothing';
}
