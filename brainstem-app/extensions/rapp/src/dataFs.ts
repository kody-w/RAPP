// The Brainstem data root, served read-only under brainstem-data:. The running Brainstem writes these files, so
// nothing here writes, creates, deletes or renames anything, and the provider tells the host so: the host then
// offers no way to edit a data file (not even its "toggle read-only for this session"), no delete, rename or
// new file in that root, and refuses drops into it and moves out of it. Only what sits inside a .brainstem_data
// folder next to a brainstem.py, outside Hives and references, is served, and never through a link. Its own
// .vscode folder is never served: as a workspace root's, the host would read settings, tasks and launch and
// MCP configurations from it, and the Brainstem's data is not the place for any of those.
import * as fs from 'fs';
import * as path from 'path';
import * as vscode from 'vscode';
import { isInside } from './hives';
import { DATA_FOLDER, DATA_SCHEME, dataLocalPath } from './startup';

export const READ_ONLY_REASON = 'Your Brainstem writes its data, so it is read-only here. To change what it remembers, ask your Brainstem.';
// How long a data folder's own checks (its brainstem.py, Hives and references) are trusted before they run again.
const CHECK_MS = 2000;

const SETTINGS_FOLDER = '.vscode';

/**
 * Why a local path is not served, or undefined when it is: it must be a plain full path inside (or at) a
 * .brainstem_data folder whose parent holds a brainstem.py, not in that folder's own .vscode, with no link
 * anywhere from that folder down. `folderRefusal` says why the data folder itself is not served (its
 * brainstem.py, Hives and references).
 */
export function dataPathRefusal(file: string, folderRefusal: (folder: string) => string | undefined, platform: NodeJS.Platform = process.platform): string | undefined {
	const paths = platform === 'win32' ? path.win32 : path.posix;
	if (!paths.isAbsolute(file) || paths.normalize(file) !== file) {
		return 'not a plain full path';
	}
	const parts = file.split(paths.sep);
	const at = parts.indexOf(DATA_FOLDER);
	if (at < 1) {
		return 'not in a Brainstem data folder';
	}
	if (isSettingsFolder(parts[at + 1], platform)) {
		return 'a settings folder';
	}
	const why = folderRefusal(parts.slice(0, at + 1).join(paths.sep));
	if (why) {
		return why;
	}
	for (let i = at; i < parts.length; i++) {
		try {
			if (fs.lstatSync(parts.slice(0, i + 1).join(paths.sep)).isSymbolicLink()) {
				return 'a link';
			}
		} catch {
			return 'no such file';
		}
	}
	return undefined;
}

function isSettingsFolder(name: string | undefined, platform: NodeJS.Platform): boolean {
	return name !== undefined && (platform === 'linux' ? name : name.toLowerCase()) === SETTINGS_FOLDER;
}

/** Why a .brainstem_data folder is not served: it needs a brainstem.py beside it, outside Hives and references. */
export function dataFolderRefusal(folder: string, forbidden: readonly string[], platform: NodeJS.Platform = process.platform): string | undefined {
	const paths = platform === 'win32' ? path.win32 : path.posix;
	try {
		if (!fs.statSync(paths.join(paths.dirname(folder), 'brainstem.py')).isFile()) {
			return 'no brainstem.py beside it';
		}
	} catch {
		return 'no brainstem.py beside it';
	}
	return forbidden.some(root => isInside(folder, root)) ? 'inside a Hive or a reference' : undefined;
}

export class DataFileSystem implements vscode.FileSystemProvider, vscode.Disposable {
	private readonly changes = new vscode.EventEmitter<vscode.FileChangeEvent[]>();
	readonly onDidChangeFile = this.changes.event;
	private readonly watchers = new Set<fs.FSWatcher>();
	private readonly checked = new Map<string, { readonly at: number; readonly why?: string }>();

	constructor(private readonly forbidden: () => readonly string[], private readonly platform: NodeJS.Platform = process.platform) { }

	dispose(): void {
		this.watchers.forEach(watcher => watcher.close());
		this.watchers.clear();
		this.changes.dispose();
	}

	/** The local path behind a brainstem-data: URI, or undefined when this provider does not serve it. */
	served(uri: vscode.Uri): string | undefined {
		const file = uri.scheme === DATA_SCHEME && !uri.authority && !uri.query && !uri.fragment ? dataLocalPath(uri.path.replace(/(.)\/+$/, '$1'), this.platform) : undefined;
		return file !== undefined && !dataPathRefusal(file, folder => this.folderRefusal(folder), this.platform) ? file : undefined;
	}

	/** Whether a local file is one this provider serves. */
	serves(file: string): boolean {
		return !dataPathRefusal(file, folder => this.folderRefusal(folder), this.platform);
	}

	private folderRefusal(folder: string): string | undefined {
		const now = Date.now();
		const seen = this.checked.get(folder);
		if (seen && now - seen.at < CHECK_MS) {
			return seen.why;
		}
		const why = dataFolderRefusal(folder, this.forbidden(), this.platform);
		this.checked.set(folder, { at: now, why });
		return why;
	}

	private local(uri: vscode.Uri): string {
		const file = this.served(uri);
		if (file === undefined) {
			throw vscode.FileSystemError.FileNotFound(uri);
		}
		return file;
	}

	stat(uri: vscode.Uri): vscode.FileStat {
		const info = fs.lstatSync(this.local(uri));
		return {
			type: info.isDirectory() ? vscode.FileType.Directory : info.isFile() ? vscode.FileType.File : vscode.FileType.Unknown,
			ctime: info.ctimeMs,
			mtime: info.mtimeMs,
			size: info.size,
			permissions: vscode.FilePermission.Readonly,
		};
	}

	// Links, anything that is neither a file nor a folder, and the data folder's own .vscode are left out.
	readDirectory(uri: vscode.Uri): [string, vscode.FileType][] {
		const folder = this.local(uri);
		const top = path.basename(folder) === DATA_FOLDER;
		return fs.readdirSync(folder, { withFileTypes: true })
			.filter(entry => (entry.isFile() || entry.isDirectory()) && !(top && isSettingsFolder(entry.name, this.platform)))
			.map(entry => [entry.name, entry.isDirectory() ? vscode.FileType.Directory : vscode.FileType.File]);
	}

	readFile(uri: vscode.Uri): Uint8Array {
		const file = this.local(uri);
		if (!fs.lstatSync(file).isFile()) {
			throw vscode.FileSystemError.FileIsADirectory(uri);
		}
		return fs.readFileSync(file);
	}

	// A folder is watched as the host asks; a file through its folder, so a file the Brainstem replaces whole
	// (written aside, then renamed over it) is still followed.
	watch(uri: vscode.Uri, options: { readonly recursive: boolean; readonly excludes: readonly string[] }): vscode.Disposable {
		let target: string;
		let isFolder: boolean;
		try {
			target = this.local(uri);
			isFolder = fs.lstatSync(target).isDirectory();
		} catch {
			return new vscode.Disposable(() => undefined);
		}
		const folder = isFolder ? target : path.dirname(target);
		const only = isFolder ? undefined : path.basename(target);
		const base = isFolder ? uri : uri.with({ path: path.posix.dirname(uri.path) });
		let watcher: fs.FSWatcher;
		try {
			watcher = fs.watch(folder, { recursive: isFolder && options.recursive, persistent: false }, (event, name) => {
				const rel = name ? String(name) : '';
				if (only !== undefined && rel !== only) {
					return;
				}
				const changed = rel ? vscode.Uri.joinPath(base, ...rel.split(/[\\/]+/)) : uri;
				const type = event === 'change' ? vscode.FileChangeType.Changed
					: fs.existsSync(path.join(folder, rel)) ? vscode.FileChangeType.Created : vscode.FileChangeType.Deleted;
				this.changes.fire([{ type, uri: changed }]);
			});
		} catch {
			return new vscode.Disposable(() => undefined);
		}
		watcher.on('error', () => undefined);
		this.watchers.add(watcher);
		return new vscode.Disposable(() => {
			watcher.close();
			this.watchers.delete(watcher);
		});
	}

	createDirectory(uri: vscode.Uri): void {
		throw vscode.FileSystemError.NoPermissions(uri);
	}

	writeFile(uri: vscode.Uri): void {
		throw vscode.FileSystemError.NoPermissions(uri);
	}

	delete(uri: vscode.Uri): void {
		throw vscode.FileSystemError.NoPermissions(uri);
	}

	rename(oldUri: vscode.Uri): void {
		throw vscode.FileSystemError.NoPermissions(oldUri);
	}
}
