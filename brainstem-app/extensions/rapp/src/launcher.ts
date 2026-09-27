// Opens the global Brainstem: its RAPP Workspace (its agents/ folder and its data, read-only) in this window,
// its own web UI in an editor tab, and, only when the person clicks, its own start script in a visible
// terminal. Nothing here writes into a Hive, a reference, agents/ or the Brainstem's data; the RAPP
// Workspace's workspace files (one per Agents folder) live in the app's own storage.
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import * as vscode from 'vscode';
import { Endpoint, parseEndpoint } from './brainstem';
import { BrainstemView, Status } from './chatView';
import { grailOneLiner } from './grail';
import { AgentsFolder, BrainstemFolder, browserReuseFilter, DATA_FOLDER, DATA_SCHEME, dataLocalPath, FolderSource, isOwnWorkspaceFile, isRappWorkspaceWindow, isRunning, readShownNote, resolveAgentsFolder, resolveBrainstemFolder, resolveDataFolder, rootsOf, samePath, shownElsewhere, START_STATUS_ENV, startCommand, startFailure, startupAction, StartupInputs, WORKSPACE_FILE, workspaceFileUpdate, workspaceKey, WORKSPACES_FOLDER, writeShownNote, writeWhole, createWhole } from './startup';

export interface LauncherSettings {
	readonly url: string;
	readonly brainstemFolder: string;
	readonly agentsFolder: string;
	readonly openOnStartup: boolean;
	readonly showUI: boolean;
}

const INTEGRATED_BROWSER = 'workbench.action.browser.open';
const SIMPLE_BROWSER = 'simpleBrowser.api.open';
// Which windows show the RAPP Workspace, in a small file in the app's own storage: an empty window that starts
// while one does, or a moment after one left it (its folder was just closed), stays empty.
const SHOWN_FILE = 'workspace-shown.json';
const TRUST_ASKED = 'rapp.trustAskedFor';
const TRUST_MESSAGE = 'Your Brainstem already runs these agents. Trust your RAPP Workspace so you can manage them here.';
const START_TRUST_MESSAGE = 'Starting your Brainstem runs its own start script in a terminal, which Restricted Mode does not allow. Trust your RAPP Workspace to start it here.';
// Each start's own file (this window's extension host, the time and a count), so windows never read or clear
// another's.
const START_STATUS_PREFIX = 'start-status-';
const START_STATUS_NAME = /^start-status-(\d+)-(\d+)-\d+$/;
const STATUS_KEPT_MS = 7 * 24 * 60 * 60 * 1000;
let startRuns = 0;
const START_WAIT_MS = 60000;
const SOURCES: Record<FolderSource, string> = {
	setting: 'the setting rapp.brainstemFolder',
	health: 'the running Brainstem\'s folder',
	default: 'the default folder',
};

// A file of the app's own that may already be gone, or cannot go now: never a reason to fail.
function removeQuietly(file: string): void {
	try {
		fs.rmSync(file, { force: true });
	} catch {
		// Left for the next sweep.
	}
}

function isUp(status: Status): boolean {
	return status.state === 'connected' || status.state === 'signed-out';
}

function brainstemDirOf(status: Status | undefined): string | undefined {
	return status && (status.state === 'connected' || status.state === 'signed-out') ? status.brainstemDir : undefined;
}

// One launch of the app: its main process, which every window's extension host shares.
function launchId(): string {
	return process.env.VSCODE_PID || String(process.ppid);
}

function openDocuments(): number {
	return vscode.window.tabGroups.all.flatMap(group => group.tabs).filter(tab =>
		tab.input instanceof vscode.TabInputText || tab.input instanceof vscode.TabInputTextDiff
		|| tab.input instanceof vscode.TabInputNotebook || tab.input instanceof vscode.TabInputNotebookDiff
		|| tab.input instanceof vscode.TabInputCustom).length;
}

// The window's roots as local paths: the Brainstem data root (served read-only under brainstem-data:) as the
// folder it shows; undefined for a root that is not on this device's disk.
function windowFolders(): Pick<StartupInputs, 'openFolders' | 'workspaceFile'> {
	return {
		openFolders: (vscode.workspace.workspaceFolders ?? []).map(folder => folder.uri.scheme === 'file' ? folder.uri.fsPath
			: folder.uri.scheme === DATA_SCHEME && !folder.uri.authority ? dataLocalPath(folder.uri.path) : undefined),
		workspaceFile: vscode.workspace.workspaceFile !== undefined,
	};
}

// The window's roots on this device's disk (the Brainstem data root is served under the app's own scheme).
function diskFolders(): string[] {
	return (vscode.workspace.workspaceFolders ?? []).filter(f => f.uri.scheme === 'file').map(f => f.uri.fsPath);
}

// Whether agents/ is the only root the host would need trust for: every other root, of any kind, but the
// Brainstem data root (which the host trusts by itself) makes trust the host's to ask.
function agentsAlone(agentsFolder: string): boolean {
	return (vscode.workspace.workspaceFolders ?? []).every(f => f.uri.scheme === DATA_SCHEME || (f.uri.scheme === 'file' && samePath(f.uri.fsPath, agentsFolder)));
}

// A path in the trust question, which the host shows as markdown: as code, fenced so no backtick in it ends it.
function codeSpan(text: string): string {
	const fence = '`'.repeat(Math.max(0, ...(text.match(/`+/g) ?? []).map(run => run.length)) + 1);
	return `${fence} ${text.replace(/[\r\n]+/g, ' ')} ${fence}`;
}

// The Brainstem's own page in an editor tab, in the host's integrated browser: titled by the page ("RAPP
// Brainstem"), with a URL bar, back, forward and reload. The reuse filter focuses the Brainstem's tab, a
// restored one included, instead of opening another, and shows it as it is: the overlay keeps the host from
// navigating a tab already on the Brainstem's address, which would reload it and lose the conversation the
// web UI keeps only in the page, unless its last load failed (nothing answered then), and then it loads the
// page again. Without that browser (the --web build), the Simple Browser shows it. Says whether either did.
async function openInEditor(endpoint: Endpoint): Promise<boolean> {
	const url = `${endpoint.url}/`;
	const commands = await vscode.commands.getCommands(true);
	if (commands.includes(INTEGRATED_BROWSER)) {
		await vscode.commands.executeCommand(INTEGRATED_BROWSER, { url, reuseUrlFilter: browserReuseFilter(endpoint.url) });
		return true;
	}
	if (commands.includes(SIMPLE_BROWSER)) {
		await vscode.commands.executeCommand(SIMPLE_BROWSER, vscode.Uri.parse(url), { viewColumn: vscode.ViewColumn.One, preserveFocus: true });
		return true;
	}
	return false;
}

export class BrainstemLauncher implements vscode.Disposable {
	private starting: Promise<void> | undefined;
	private terminal: vscode.Terminal | undefined;
	private dataWatcher: vscode.Disposable | undefined;
	private showing = false;
	private entered = false;
	private readonly folderListener: vscode.Disposable | undefined;
	private statusFile: string | undefined;
	private disposed = false;
	private askingTrust = false;

	// `onWorkspace` starts watching agents/ once this window shows the RAPP Workspace.
	constructor(
		private readonly context: vscode.ExtensionContext,
		private readonly view: BrainstemView,
		private readonly settings: () => LauncherSettings,
		private readonly forbidden: () => string[],
		private readonly onWorkspace: (agentsFolder: string | undefined) => void = () => undefined,
	) {
		this.adoptStart();
		this.sweepStatusFiles();
		// A root added or removed without a reload (Add Folder to Workspace puts it last): the window enters or
		// leaves the RAPP Workspace as it happens.
		this.folderListener = vscode.workspace.onDidChangeWorkspaceFolders?.(() => void this.onFoldersChanged().catch(() => undefined));
	}

	dispose(): void {
		this.disposed = true;
		this.folderListener?.dispose();
		this.dataWatcher?.dispose();
		if (this.showing) {
			// As the window goes (a folder closed, a reload, a quit): an empty window that follows stays empty.
			this.noteShown(false);
		}
		// A start still running outside this extension host (it restarted) keeps its file for the next one.
		if (this.statusFile && (!this.terminal || this.terminal.exitStatus !== undefined)) {
			removeQuietly(this.statusFile);
		}
	}

	// After an extension host restart, the start this window ran may still be running in its terminal: it is taken
	// over, so Start shows it instead of running the script a second time. Only a status file of the app's own,
	// by its exact name in the app's storage, is ever taken over (and so ever removed).
	private adoptStart(): void {
		const storage = path.resolve(this.context.globalStorageUri.fsPath);
		for (const terminal of vscode.window.terminals ?? []) {
			const file = (terminal.creationOptions as vscode.TerminalOptions | undefined)?.env?.[START_STATUS_ENV];
			if (terminal.exitStatus === undefined && typeof file === 'string' && path.dirname(path.resolve(file)) === storage && START_STATUS_NAME.test(path.basename(file))) {
				this.terminal = terminal;
				this.statusFile = path.resolve(file);
			}
		}
	}

	// A status file outlives its window only when the window went while its start's terminal still showed a
	// failure; one whose window's extension host is gone and that is a week old is removed.
	private sweepStatusFiles(): void {
		const storage = this.context.globalStorageUri.fsPath;
		let names: string[];
		try {
			names = fs.readdirSync(storage);
		} catch {
			return;
		}
		for (const name of names) {
			const match = START_STATUS_NAME.exec(name);
			const file = path.join(storage, name);
			if (match && path.resolve(file) !== this.statusFile && Number(match[1]) !== process.pid && !isRunning(Number(match[1])) && Date.now() - Number(match[2]) > STATUS_KEPT_MS) {
				removeQuietly(file);
			}
		}
	}

	locate(status?: Status): BrainstemFolder {
		return resolveBrainstemFolder({
			setting: this.settings().brainstemFolder,
			healthDir: brainstemDirOf(status),
			home: os.homedir(),
			forbidden: this.forbidden(),
		});
	}

	/** The RAPP Workspace's agents/ folder for the Brainstem at `root`. */
	agentsFolder(root: string | undefined): AgentsFolder {
		return resolveAgentsFolder({ setting: this.settings().agentsFolder, root, home: os.homedir(), forbidden: this.forbidden() });
	}

	/** The RAPP Workspace's read-only Brainstem data root for the Brainstem at `root`, when it is there. */
	dataFolder(root: string | undefined): string | undefined {
		return resolveDataFolder(root, this.forbidden());
	}

	/** Whether a Brainstem folder with its own start script is on this device. */
	canStart(): boolean {
		const { folder } = this.locate();
		return !!folder && !!startCommand(folder, this.forbidden());
	}

	/**
	 * What a window does when it starts. An empty one, or one on the Brainstem's own folder, opens the RAPP
	 * Workspace; the RAPP Workspace is managed here and shows the Brainstem's page.
	 */
	async onStartup(): Promise<void> {
		// Read before anything waits, so a folder just closed in this window still counts as shown a moment ago.
		const workspaceShown = shownElsewhere(readShownNote(this.shownFile()), launchId(), process.pid, Date.now());
		const status = await this.view.poll();
		const settings = this.settings();
		const found = this.locate(status);
		const agents = this.agentsFolder(found.folder);
		for (const [key, refused] of [['brainstemFolder', found.refused], ['agentsFolder', agents.refused]] as const) {
			const setting = refused.find(r => r.source === 'setting');
			if (setting) {
				void this.warnSetting(key, setting.reason);
			}
		}
		const data = this.dataFolder(found.folder);
		const inputs: StartupInputs = {
			...windowFolders(),
			openDocuments: openDocuments(),
			remote: vscode.env.remoteName !== undefined,
			root: found.folder,
			agents: agents.folder,
			data,
			ownFile: this.isOwnFile(),
			openOnStartup: settings.openOnStartup,
			showUI: settings.showUI,
			workspaceShown,
		};
		const action = startupAction(inputs);
		const inWorkspace = isRappWorkspaceWindow(inputs);
		if (action === 'open-workspace' && agents.folder) {
			await this.openWorkspace(agents.folder, data);
			return;
		}
		if (inWorkspace && agents.folder) {
			await this.enter(agents.folder, data, this.ownerOf(found, agents));
			if (action === 'show-ui') {
				await this.show(status);
			}
		}
	}

	// The Brainstem folder the Agents root is known to belong to: the one it is the agents/ of (by real path, so a
	// link to that folder counts), or the one the setting names. An Agents folder set apart from a Brainstem found
	// another way (its /health, or the default while it is down) is not known to go with that Brainstem's data, so
	// its open file is left as it is.
	private ownerOf(found: BrainstemFolder, agents: AgentsFolder): string | undefined {
		if (!found.folder || !agents.folder) {
			return undefined;
		}
		return agents.source === 'brainstem' || found.source === 'setting' || samePath(agents.folder, path.join(found.folder, 'agents')) ? found.folder : undefined;
	}

	/** "Open your Brainstem": its RAPP Workspace in this window (or a new one), or its page when that is already open. */
	async openFolder(newWindow = false): Promise<void> {
		const status = await this.view.poll();
		const found = this.locate(status);
		const agents = this.agentsFolder(found.folder);
		if (!agents.folder) {
			await this.notFound(found, agents);
			return;
		}
		const data = this.dataFolder(found.folder);
		// A workspace file from elsewhere with agents/ in it is not the RAPP Workspace: the app's own one opens.
		if (this.ownWorkspace() && isRappWorkspaceWindow({ ...windowFolders(), agents: agents.folder, data, ownFile: this.isOwnFile() })) {
			await this.show(status);
			return;
		}
		// A window on one of the app's own workspace files (for another Agents folder, say), or one the app treats
		// as the RAPP Workspace (a file saved elsewhere with agents/ in it), keeps it and its conversation: the RAPP
		// Workspace opens in a window of its own.
		await this.openWorkspace(agents.folder, data, newWindow || this.isOwnFile() || this.entered);
	}

	private shownFile(): string {
		return path.join(this.context.globalStorageUri.fsPath, SHOWN_FILE);
	}

	// Notes whether this window shows the RAPP Workspace: its extension host joins the note, or leaves it with the
	// time it left. A new window beside it, or a window whose folder was just closed, then stays empty, while
	// reopening the app after closing its windows (on macOS it keeps running) opens it again. Written at once, as
	// a plain file, because a window that closes can no longer save anything else.
	private noteShown(showing: boolean): void {
		const file = this.shownFile();
		const note = readShownNote(file);
		const same = note?.launch === launchId();
		// Hosts that no longer run (a window that crashed) go, so a reused process id never keeps a window counted.
		const hosts = (same && note ? note.hosts : []).filter(pid => pid !== process.pid && isRunning(pid));
		try {
			writeShownNote(file, {
				launch: launchId(),
				hosts: showing ? [...hosts, process.pid] : hosts,
				leftAt: showing ? (same && note ? note.leftAt : 0) : Date.now(),
			});
			this.showing = showing;
		} catch {
			// Without its note the app still works: an empty window may then open the RAPP Workspace once more.
		}
	}

	/**
	 * The RAPP Workspace file of an Agents folder, in the app's own storage (never inside agents/): the one earlier
	 * builds kept while it is there and lists that folder, else the folder's own. A new Agents folder so opens as a
	 * new workspace, which the host judges afresh and the Brainstem asks about by name: no open workspace changes its
	 * Agents in place.
	 */
	workspaceFileFor(agentsFolder: string): string {
		const storage = this.context.globalStorageUri.fsPath;
		// Read as the host reads it: past a slip it reads past, and a file it would refuse lists nothing.
		const lists = (file: string) => rootsOf(file).some(root => samePath(root, agentsFolder));
		const earlier = path.join(storage, WORKSPACE_FILE);
		if (lists(earlier)) {
			return earlier;
		}
		// Its own file, or, when a person took agents/ out of that one (or the host could not open it: empty, cut
		// short before its folders, or unreadable now), the next free one. A file passed over is never changed.
		const key = workspaceKey(agentsFolder);
		for (let n = 1; n < 1000; n++) {
			const file = path.join(storage, WORKSPACES_FOLDER, n === 1 ? key : `${key}-${n}`, WORKSPACE_FILE);
			if (!fs.existsSync(file) || lists(file)) {
				return file;
			}
		}
		throw new Error('Every RAPP Workspace file for this agents/ folder was changed by hand; remove some of them from the app\'s storage.');
	}

	// The window's workspace is the app's own: a folder, an untitled workspace, or the app's own workspace file. A
	// workspace file from anywhere else (trusting it would trust the file and its settings too) is never trusted
	// in the Brainstem's words.
	private ownWorkspace(): boolean {
		const file = vscode.workspace.workspaceFile;
		return !file || file.scheme === 'untitled' || this.isOwnFile();
	}

	/** Whether this window's workspace file is one of the app's own RAPP Workspace files. */
	private isOwnFile(): boolean {
		const file = vscode.workspace.workspaceFile;
		return file?.scheme === 'file' && isOwnWorkspaceFile(file.fsPath, this.context.globalStorageUri.fsPath);
	}

	// Writes the workspace file only when it is missing or its roots or settings need to change, keeping anything
	// else in it, so an open window and the person's own workspace settings are not disturbed. Written whole (a
	// partial file, then a rename), so no window ever reads it half written.
	// `create`: a missing file is made (only Open your Brainstem and an empty window's startup make one, and never
	// over a file someone else just made). A file that exists but cannot be read now is left as it is.
	private writeWorkspaceFile(agentsFolder: string, dataFolder: string | undefined, file = this.workspaceFileFor(agentsFolder), create = false): string {
		let current: string | undefined;
		try {
			current = fs.readFileSync(file, 'utf8');
		} catch (error) {
			if ((error as NodeJS.ErrnoException).code !== 'ENOENT' || !create) {
				return file;
			}
			createWhole(file, workspaceFileUpdate(undefined, agentsFolder, path.dirname(file), dataFolder) as string);
			return file;
		}
		const next = workspaceFileUpdate(current, agentsFolder, path.dirname(file), dataFolder);
		if (next !== undefined) {
			writeWhole(file, next);
		}
		return file;
	}

	// This Agents folder's own workspace, in this window or a new one. Only a file that does not exist yet is
	// written here: an existing one may be open in some window, whose roots are never changed under it (the window
	// that opens it adds its data root itself). A window that switches is noted at once (as a window that just left
	// it), so an empty window that starts meanwhile stays empty.
	private async openWorkspace(agentsFolder: string, dataFolder: string | undefined, newWindow = false): Promise<void> {
		const file = this.workspaceFileFor(agentsFolder);
		if (!fs.existsSync(file)) {
			this.writeWorkspaceFile(agentsFolder, dataFolder, file, true);
		}
		if (!newWindow) {
			this.noteShown(false);
		}
		await vscode.commands.executeCommand('vscode.openFolder', vscode.Uri.file(file), newWindow ? { forceNewWindow: true } : { forceReuseWindow: true });
	}

	// This window shows the RAPP Workspace: bring its roots up to date (the host follows a change to the open
	// workspace file, so a data folder that appeared joins as a root, and one that appears later joins then),
	// watch agents/ as the window names it, and ask once for trust. The data root is served read-only under
	// its own scheme, which the host needs no trust for; only the folders on disk are asked about.
	private async enter(agentsFolder: string, dataFolder: string | undefined, root: string | undefined): Promise<void> {
		// agents/ as the window names it, wherever it is among the roots.
		const disk = diskFolders();
		const shown = disk.find(f => samePath(f, agentsFolder)) ?? agentsFolder;
		this.entered = true;
		this.dataWatcher?.dispose();
		this.dataWatcher = undefined;
		// With the Brainstem's folder unknown (not running, not at the default), or not known to be the one these
		// agents belong to (`root` is then undefined), its data folder is unknown too: the file is left as it is
		// rather than losing its data root or taking another Brainstem's.
		const open = this.isOwnFile() && root ? vscode.workspace.workspaceFile?.fsPath : undefined;
		if (open) {
			// The file this window has open (the host follows it): only its data root and rules change here.
			this.writeQuietly(agentsFolder, dataFolder, open);
			if (!dataFolder && root) {
				const watcher = vscode.workspace.createFileSystemWatcher(new vscode.RelativePattern(vscode.Uri.file(root), DATA_FOLDER), false, true, true);
				watcher.onDidCreate(() => {
					const data = this.dataFolder(root);
					if (data && this.entered && this.isOwnFile()) {
						this.writeQuietly(agentsFolder, data, open);
						watcher.dispose();
					}
				});
				this.dataWatcher = watcher;
			}
		}
		this.onWorkspace(shown);
		this.noteShown(true);
		// The Brainstem asks about Agents alone: with any other root in the window, trust is the host's to ask.
		if (agentsAlone(agentsFolder)) {
			await this.askTrustOnce([shown]);
		}
	}

	// The window no longer shows the RAPP Workspace (agents/ was taken out of it): nothing of it is kept up.
	private leave(): void {
		this.entered = false;
		this.dataWatcher?.dispose();
		this.dataWatcher = undefined;
		this.onWorkspace(undefined);
		this.noteShown(false);
	}

	private async onFoldersChanged(): Promise<void> {
		const status = await this.view.poll();
		const found = this.locate(status);
		const resolved = this.agentsFolder(found.folder);
		const agents = resolved.folder;
		const data = this.dataFolder(found.folder);
		const showing = !!agents && isRappWorkspaceWindow({ ...windowFolders(), agents, data, ownFile: this.isOwnFile() });
		if (showing && agents && !this.entered) {
			await this.enter(agents, data, this.ownerOf(found, resolved));
		} else if (!showing && this.entered) {
			this.leave();
		} else if (showing && agents && agentsAlone(agents)) {
			// A root went (an earlier build's plain data root the app just turned into its own, say): agents/ is now
			// alone, so the Brainstem's question can be asked.
			await this.askTrustOnce([diskFolders().find(f => samePath(f, agents)) ?? agents]);
		}
	}

	// A workspace file that cannot be written now (on Windows another program may hold it) never stops the rest.
	private writeQuietly(agentsFolder: string, dataFolder: string | undefined, file: string): void {
		try {
			this.writeWorkspaceFile(agentsFolder, dataFolder, file);
		} catch {
			// Tried again the next time the window opens.
		}
	}

	// A folder as the host trusts it: by its path as written, not where a link leads, and, in a workspace file, with
	// that file too (the host trusts a workspace with its file), so a new workspace file for a folder asks once more.
	private folderId(folder: string): string {
		const file = vscode.workspace.workspaceFile;
		return file?.scheme === 'file' ? `${path.resolve(file.fsPath)}\n${path.resolve(folder)}` : path.resolve(folder);
	}

	private remembered(key: string, folder: string): boolean {
		return this.context.globalState.get<string[]>(key, []).includes(this.folderId(folder));
	}

	private async remember(key: string, folder: string): Promise<void> {
		const seen = this.context.globalState.get<string[]>(key, []);
		const id = this.folderId(folder);
		if (!seen.includes(id)) {
			await this.context.globalState.update(key, [...seen, id]);
		}
	}

	// Restricted Mode is the host's safe default; the Brainstem asks once, in its own words, per folder: a
	// workspace that gains a root (the data folder, say) asks once more. The question counts as asked once it is
	// answered (Trust, Manage or Cancel): a window closed while it shows, or an app quit, asks again next time.
	private async askTrustOnce(folders: readonly string[]): Promise<void> {
		if (vscode.workspace.isTrusted || this.askingTrust || !this.ownWorkspace() || folders.every(folder => this.remembered(TRUST_ASKED, folder))) {
			return;
		}
		this.askingTrust = true;
		try {
			await vscode.workspace.requestWorkspaceTrust({ message: `${TRUST_MESSAGE}\n\n${folders.length === 1 ? 'Folder' : 'Folders'}: ${folders.map(codeSpan).join(', ')}` });
			for (const folder of folders) {
				await this.remember(TRUST_ASKED, folder);
			}
		} finally {
			this.askingTrust = false;
		}
	}

	/** The Brainstem's own page in the editor, or the offline card when it is not running. */
	async openUI(): Promise<void> {
		await this.show(await this.view.poll());
	}

	/** "Start my Brainstem": its own start script, in a visible terminal in its folder, then its page. */
	async start(): Promise<void> {
		if (this.starting) {
			this.terminal?.show();
			return;
		}
		// Claimed before the first wait, so a second click while this one looks for the Brainstem runs nothing.
		const run = this.startOnce();
		this.starting = run;
		try {
			await run;
		} finally {
			if (this.starting === run) {
				this.starting = undefined;
			}
		}
	}

	private async startOnce(): Promise<void> {
		const status = await this.view.poll();
		if (isUp(status) || status.state === 'misconfigured') {
			await this.show(status);
			return;
		}
		if (status.state === 'not-running' && status.occupied) {
			// Its start script could only fail on an address another program holds.
			void vscode.window.showWarningMessage(`Your Brainstem was not started: something else is using its address (${this.settings().url}). Close that program, then start your Brainstem.`);
			await this.show(status);
			return;
		}
		if (status.state === 'not-running' && status.busy) {
			// It is running, only slow to answer: a second copy could only fail on its address.
			void vscode.window.showInformationMessage('Your Brainstem is already running. It is busy and will answer in a moment.');
			await this.show(status);
			return;
		}
		if (status.state === 'not-running' && status.dropped) {
			// Something listens on its address and closes every connection: a second copy could only fail there.
			void vscode.window.showWarningMessage('Your Brainstem was not started: something on its address closes every connection without an answer. If you just added an agent, move it out of the top of agents/, then check again.');
			await this.show(status);
			return;
		}
		// The start script this app ran is still running: starting slowly, or not answering. It is shown, not
		// run a second time; closing its terminal stops it. One that stopped with an error and still shows why
		// is closed, and the script runs again.
		const failed = !!this.statusFile && startFailure(this.statusFile) !== undefined;
		if (this.terminal && this.terminal.exitStatus === undefined && !failed) {
			this.terminal.show();
			void vscode.window.showInformationMessage('Your Brainstem\'s start script is still running in its terminal. Close that terminal to stop it, then start it again.');
			return;
		}
		const found = this.locate(status);
		if (!found.folder) {
			// Not waited for: a notice nobody answers must not hold Start.
			void this.notFound(found);
			return;
		}
		const start = startCommand(found.folder, this.forbidden());
		if (!start) {
			void vscode.window.showWarningMessage(`Your Brainstem folder has no ${process.platform === 'win32' ? 'start.ps1' : 'start.sh'} to start it with. Start it with the brainstem command in a terminal.`);
			return;
		}
		// Restricted Mode runs no terminal. The trust asked for is always this window's: in the RAPP Workspace the
		// Brainstem asks, in its own words, naming the folders; any other window in Restricted Mode starts nothing
		// and offers the RAPP Workspace, so no other folder is ever trusted in the Brainstem's name.
		if (!vscode.workspace.isTrusted) {
			const agents = this.agentsFolder(found.folder).folder;
			if (!this.ownWorkspace() || !isRappWorkspaceWindow({ ...windowFolders(), agents, data: this.dataFolder(found.folder), ownFile: this.isOwnFile() })) {
				// Not waited for: a notice nobody answers must not hold Start. The RAPP Workspace opens in a window
				// of its own (a new one, or the one that already shows it comes forward), so this one keeps its folder.
				const open = 'Open your Brainstem';
				void vscode.window.showInformationMessage('Your Brainstem was not started: this window is in Restricted Mode. Open your Brainstem to start it from its RAPP Workspace, in a window of its own.', open)
					.then(pick => pick === open ? this.openFolder(true) : undefined)
					.then(undefined, () => void vscode.window.showWarningMessage('Your RAPP Workspace could not be opened.'));
				return;
			}
			const folders = diskFolders();
			if (!agentsAlone(agents as string)) {
				// Other folders on disk in this RAPP Workspace: trust is the host's to ask, for all of them.
				const manage = 'Manage Workspace Trust';
				void vscode.window.showInformationMessage('Your Brainstem was not started: this window is in Restricted Mode, and its RAPP Workspace holds other folders too. Trust them with Manage Workspace Trust, then start your Brainstem.', manage)
					.then(pick => pick === manage ? vscode.commands.executeCommand('workbench.trust.manage') : undefined)
					.then(undefined, () => undefined);
				return;
			}
			if (await vscode.workspace.requestWorkspaceTrust({ message: `${START_TRUST_MESSAGE}\n\n${folders.length === 1 ? 'Folder' : 'Folders'}: ${folders.map(codeSpan).join(', ')}` }) !== true) {
				void vscode.window.showInformationMessage('Your Brainstem was not started: this window is in Restricted Mode. Trust your RAPP Workspace to start it here, or start it with the brainstem command in a terminal.');
				return;
			}
		}
		// The terminal runs the start script itself, so it ends when the Brainstem does, and is not revived
		// after a restart; the one a finished run left is closed first. A script that stops with an error writes
		// its exit code to a file in the app's own storage and keeps its terminal open on what it printed.
		this.terminal?.dispose();
		if (this.statusFile) {
			removeQuietly(this.statusFile);
		}
		const statusFile = path.join(this.context.globalStorageUri.fsPath, `${START_STATUS_PREFIX}${process.pid}-${Date.now()}-${++startRuns}`);
		this.statusFile = statusFile;
		fs.mkdirSync(path.dirname(statusFile), { recursive: true });
		const terminal = vscode.window.createTerminal({ name: 'Brainstem', cwd: start.cwd, shellPath: start.shellPath, shellArgs: [...start.shellArgs], env: { [START_STATUS_ENV]: statusFile }, isTransient: true });
		this.terminal = terminal;
		terminal.show();
		this.view.setStarting(true);
		try {
			await this.waitFor(terminal, statusFile);
		} finally {
			this.view.setStarting(false);
		}
	}

	private async waitFor(terminal: vscode.Terminal, statusFile: string): Promise<void> {
		const deadline = Date.now() + START_WAIT_MS;
		while (!this.disposed && Date.now() < deadline) {
			await new Promise(resolve => setTimeout(resolve, 1000));
			const status = await this.view.poll();
			if (isUp(status)) {
				if (this.settings().showUI) {
					await this.show(status);
				}
				return;
			}
			const failed = startFailure(statusFile);
			if (failed !== undefined) {
				terminal.show();
				void vscode.window.showWarningMessage(`Your Brainstem stopped before it answered (exit code ${failed}). Its terminal shows why.`);
				return;
			}
			if (terminal.exitStatus) {
				const code = terminal.exitStatus.code;
				void vscode.window.showWarningMessage(`The Brainstem terminal closed before your Brainstem answered${code ? ` (exit code ${code})` : ''}.`);
				return;
			}
		}
		if (!this.disposed) {
			void vscode.window.showWarningMessage('Your Brainstem did not answer within 60 seconds. Its terminal shows what happened.');
		}
	}

	// The Brainstem's page when it answers; otherwise, or with no browser to show it in, the Brainstem view:
	// the web UI, or the offline card.
	private async show(status: Status): Promise<void> {
		const endpoint = parseEndpoint(this.settings().url);
		if (typeof endpoint === 'string' || !isUp(status) || !await openInEditor(endpoint)) {
			await vscode.commands.executeCommand(`${BrainstemView.id}.focus`);
		}
	}

	private async notFound(found: BrainstemFolder, agents?: AgentsFolder): Promise<void> {
		const copy = 'Copy the one-liner', open = 'Open Settings';
		if (found.folder && agents) {
			const why = agents.refused.map(r => r.source === 'setting' ? `the setting rapp.agentsFolder: ${r.reason}` : r.reason).join('; ');
			if (await vscode.window.showWarningMessage(`Your Brainstem has no RAPP Workspace to open (${why}). Set rapp.agentsFolder to its agents/ folder.`, open) === open) {
				await vscode.commands.executeCommand('workbench.action.openSettings', 'rapp.agentsFolder');
			}
			return;
		}
		const why = found.refused.map(r => `${SOURCES[r.source]}: ${r.reason}`).join('; ');
		const { command } = grailOneLiner();
		const pick = await vscode.window.showWarningMessage(
			`No Brainstem folder was found on this device (${why}). ${command ? 'Install your Brainstem with the grail one-liner, or set' : 'Once your Brainstem is installed, set'} rapp.brainstemFolder.`,
			...(command ? [copy, open] : [open]));
		if (pick === copy && command) {
			await vscode.env.clipboard.writeText(command);
		} else if (pick === open) {
			await vscode.commands.executeCommand('workbench.action.openSettings', 'rapp.brainstemFolder');
		}
	}

	private async warnSetting(key: 'brainstemFolder' | 'agentsFolder', reason: string): Promise<void> {
		const open = 'Open Settings';
		if (await vscode.window.showWarningMessage(`The setting rapp.${key} is not used: ${reason}.`, open) === open) {
			await vscode.commands.executeCommand('workbench.action.openSettings', `rapp.${key}`);
		}
	}
}
