// A small stand-in for the parts of the vscode API the tree providers and helpers use, for unit tests.
export enum TreeItemCollapsibleState { None = 0, Collapsed = 1, Expanded = 2 }

export class EventEmitter<T> {
	private readonly listeners: ((value: T) => void)[] = [];
	readonly event = (listener: (value: T) => void) => {
		this.listeners.push(listener);
		return { dispose: () => undefined };
	};
	fire(value: T): void {
		this.listeners.forEach(listener => listener(value));
	}
	dispose(): void {
		this.listeners.length = 0;
	}
}

export class ThemeColor {
	constructor(readonly id: string) { }
}

export class ThemeIcon {
	static readonly Folder = new ThemeIcon('folder');
	static readonly File = new ThemeIcon('file');
	constructor(readonly id: string, readonly color?: ThemeColor) { }
}

// A parsed URI keeps the whole text as its fsPath, as the tests of other schemes read it back.
export class Uri {
	private constructor(readonly scheme: string, readonly fsPath: string, readonly path: string, readonly authority = '', readonly query = '', readonly fragment = '') { }
	static file(fsPath: string): Uri {
		return new Uri('file', fsPath, fsPath.split('\\').join('/'));
	}
	static parse(value: string): Uri {
		const parts = /^([A-Za-z][A-Za-z0-9+.-]*):(?:\/\/([^/?#]*))?([^?#]*)(?:\?([^#]*))?(?:#(.*))?$/.exec(value);
		return parts
			? new Uri(parts[1], value, decodeURIComponent(parts[3]), parts[2] ?? '', parts[4] ?? '', parts[5] ?? '')
			: new Uri(value.split(':')[0], value, value);
	}
	static from(parts: { scheme: string; path: string; authority?: string }): Uri {
		return new Uri(parts.scheme, parts.path, parts.path, parts.authority ?? '');
	}
	static joinPath(base: Uri, ...parts: string[]): Uri {
		const joined = [base.path, ...parts].join('/');
		return new Uri(base.scheme, base.scheme === 'file' ? [base.fsPath, ...parts].join('/') : joined, joined, base.authority);
	}
	with(change: { path?: string }): Uri {
		const next = change.path ?? this.path;
		return new Uri(this.scheme, next, next, this.authority, this.query, this.fragment);
	}
	toString(): string {
		return this.scheme === 'file' ? `file://${this.fsPath}` : `${this.scheme}://${this.authority}${this.path}`;
	}
}

export enum FileType { Unknown = 0, File = 1, Directory = 2, SymbolicLink = 64 }
export enum FilePermission { Readonly = 1 }
export enum FileChangeType { Changed = 1, Created = 2, Deleted = 3 }

export class FileSystemError extends Error {
	constructor(readonly code: string, uri?: Uri) {
		super(`${code}: ${uri?.toString() ?? ''}`);
	}
	static FileNotFound(uri?: Uri): FileSystemError {
		return new FileSystemError('FileNotFound', uri);
	}
	static FileIsADirectory(uri?: Uri): FileSystemError {
		return new FileSystemError('FileIsADirectory', uri);
	}
	static NoPermissions(uri?: Uri): FileSystemError {
		return new FileSystemError('NoPermissions', uri);
	}
}

export interface Command {
	command: string;
	title: string;
	arguments?: unknown[];
}

export class TreeItem {
	label?: string;
	description?: string;
	tooltip?: string;
	iconPath?: ThemeIcon;
	contextValue?: string;
	command?: Command;
	resourceUri?: Uri;
	constructor(labelOrUri: string | Uri, readonly collapsibleState: TreeItemCollapsibleState = TreeItemCollapsibleState.None) {
		if (typeof labelOrUri === 'string') {
			this.label = labelOrUri;
		} else {
			this.resourceUri = labelOrUri;
		}
	}
}

// The window, command and terminal API the launcher uses, recording what it is asked to do.
export const recorded = {
	commands: [] as unknown[][],
	terminals: [] as FakeTerminal[],
	messages: [] as string[],
	trustRequests: [] as unknown[],
	statusMessages: [] as [string, number | undefined][],
	watchers: [] as FakeWatcher[],
};

export class Disposable {
	constructor(private readonly onDispose: () => void) { }
	static from(...items: { dispose(): unknown }[]): Disposable {
		return new Disposable(() => items.forEach(item => item.dispose()));
	}
	dispose(): void {
		this.onDispose();
	}
}

export class RelativePattern {
	constructor(readonly baseUri: Uri, readonly pattern: string) { }
}

// A file watcher whose events the tests fire.
export class FakeWatcher {
	private readonly created: ((uri: Uri) => void)[] = [];
	private readonly deleted: ((uri: Uri) => void)[] = [];
	disposed = false;
	constructor(readonly pattern: RelativePattern) { }
	onDidCreate = (listener: (uri: Uri) => void) => (this.created.push(listener), new Disposable(() => undefined));
	onDidDelete = (listener: (uri: Uri) => void) => (this.deleted.push(listener), new Disposable(() => undefined));
	onDidChange = () => new Disposable(() => undefined);
	fireCreate(uri: Uri): void {
		this.created.forEach(listener => listener(uri));
	}
	fireDelete(uri: Uri): void {
		this.deleted.forEach(listener => listener(uri));
	}
	dispose(): void {
		this.disposed = true;
	}
}

export enum ViewColumn { Active = -1, Beside = -2, One = 1 }
export class TabInputText { }
export class TabInputTextDiff { }
export class TabInputNotebook { }
export class TabInputNotebookDiff { }
export class TabInputCustom { }

export interface FakeTerminal {
	readonly options: unknown;
	readonly creationOptions: unknown;
	readonly sent: string[];
	exitStatus: { code: number | undefined } | undefined;
	disposed: boolean;
	shown: number;
	show(): void;
	sendText(text: string): void;
	dispose(): void;
}

export const window = {
	tabGroups: { all: [] as { tabs: { input: unknown }[] }[] },
	// The terminals the window already has when an extension host starts (the tests set them).
	terminals: [] as FakeTerminal[],
	createTerminal(options: unknown): FakeTerminal {
		const terminal: FakeTerminal = {
			options, creationOptions: options, sent: [], exitStatus: undefined, disposed: false, shown: 0,
			show: () => void terminal.shown++,
			sendText: (text: string) => void terminal.sent.push(text),
			dispose: () => {
				terminal.disposed = true;
				terminal.exitStatus ??= { code: undefined };
			},
		};
		recorded.terminals.push(terminal);
		return terminal;
	},
	showWarningMessage: async (message: string) => void recorded.messages.push(message),
	setStatusBarMessage: (text: string, hideAfterTimeout?: number) => (recorded.statusMessages.push([text, hideAfterTimeout]), new Disposable(() => undefined)),
	registerFileDecorationProvider: () => new Disposable(() => undefined),
	showInformationMessage: async (message: string, ..._items: string[]): Promise<string | undefined> => void recorded.messages.push(message),
};

// What the host has registered; the desktop app has both browsers, the --web build only the Simple Browser.
export const registeredCommands: string[] = [];

export const commands = {
	executeCommand: async (...args: unknown[]) => void recorded.commands.push(args),
	getCommands: async () => [...registeredCommands],
};

export const workspace = {
	workspaceFolders: undefined as { uri: Uri }[] | undefined,
	workspaceFile: undefined as Uri | undefined,
	isTrusted: true,
	createFileSystemWatcher: (pattern: RelativePattern) => {
		const watcher = new FakeWatcher(pattern);
		recorded.watchers.push(watcher);
		return watcher;
	},
	requestWorkspaceTrust: async (options?: unknown) => {
		recorded.trustRequests.push(options);
		return true;
	},
	// The tests change workspaceFolders, then fire this, as the host does when a root is added or removed.
	folderListeners: [] as (() => void)[],
	onDidChangeWorkspaceFolders(listener: () => void) {
		workspace.folderListeners.push(listener);
		return new Disposable(() => workspace.folderListeners.splice(workspace.folderListeners.indexOf(listener), 1));
	},
	fireWorkspaceFolders(): void {
		workspace.folderListeners.forEach(listener => listener());
	},
	onDidChangeConfiguration: () => new Disposable(() => undefined),
	textDocumentListeners: [] as ((event: { document: unknown }) => void)[],
	saveDocumentListeners: [] as ((document: unknown) => void)[],
	onDidChangeTextDocument(listener: (event: { document: unknown }) => void) {
		workspace.textDocumentListeners.push(listener);
		return new Disposable(() => workspace.textDocumentListeners.splice(workspace.textDocumentListeners.indexOf(listener), 1));
	},
	fireChangeTextDocument(document: unknown): void {
		workspace.textDocumentListeners.forEach(listener => listener({ document }));
	},
	onDidSaveTextDocument(listener: (document: unknown) => void) {
		workspace.saveDocumentListeners.push(listener);
		return new Disposable(() => workspace.saveDocumentListeners.splice(workspace.saveDocumentListeners.indexOf(listener), 1));
	},
	fireSaveTextDocument(document: unknown): void {
		workspace.saveDocumentListeners.forEach(listener => listener(document));
	},
};

export const env = {
	remoteName: undefined as string | undefined,
	clipboard: { writeText: async () => undefined },
};

export class DataTransferItem {
	constructor(readonly value: unknown) { }
	async asString(): Promise<string> {
		return typeof this.value === 'string' ? this.value : JSON.stringify(this.value);
	}
}

export class FileDecoration {
	constructor(readonly badge?: string, readonly tooltip?: string, readonly color?: ThemeColor) { }
}
