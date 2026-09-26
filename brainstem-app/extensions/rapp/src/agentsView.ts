// The RAPP Workspace's Agents root in the Explorer: marks on agent files (live at the top of agents/, dimmed
// in folders) and a transient status-bar note when an agent file arrives at the top or leaves it. The Explorer
// itself does every move, one drag each, and its own Undo reverses one; nothing here moves or writes a file.
import * as path from 'path';
import * as vscode from 'vscode';
import { agentGlob, agentPlace, isAgentFileName, isBaseAgent, liveMessage } from './agents';

const LIVE_TIP = 'Live — your Brainstem runs this';
const NOT_LIVE_TIP = 'Not live — drag to the top of agents/ to run it';
const NOTE_MS = 4000;

/** A small badge on live agent files, and agent files kept in folders dimmed. */
export class AgentDecorations implements vscode.FileDecorationProvider, vscode.Disposable {
	private readonly changed = new vscode.EventEmitter<undefined>();
	readonly onDidChangeFileDecorations = this.changed.event;

	constructor(private readonly root: () => string | undefined, private readonly platform: NodeJS.Platform = process.platform) { }

	/** Asks the Explorer for every mark again: once the root is known, files it already showed get theirs. */
	refresh(): void {
		this.changed.fire(undefined);
	}

	dispose(): void {
		this.changed.dispose();
	}

	provideFileDecoration(uri: vscode.Uri): vscode.FileDecoration | undefined {
		const root = this.root();
		const place = root && uri.scheme === 'file' ? agentPlace(root, uri.fsPath, this.platform) : undefined;
		if (place === 'live') {
			return new vscode.FileDecoration('●', LIVE_TIP);
		}
		return place === 'folder' ? new vscode.FileDecoration(undefined, NOT_LIVE_TIP, new vscode.ThemeColor('list.deemphasizedForeground')) : undefined;
	}
}

/** The RAPP Workspace: its decorations, and a watcher on agents/*_agent.py that says what became live. */
export class RappWorkspace implements vscode.Disposable {
	private root: string | undefined;
	private watcher: vscode.Disposable | undefined;
	private pending: NodeJS.Timeout | undefined;
	private readonly cameLive = new Set<string>();
	private readonly leftLive = new Set<string>();
	private readonly disposables: vscode.Disposable[] = [];
	private readonly decorations: AgentDecorations;

	// `changed` runs after each settled change, to refresh the Brainstem's live count.
	constructor(private readonly changed: () => void, private readonly settleMs = 250, private readonly platform: NodeJS.Platform = process.platform) {
		this.decorations = new AgentDecorations(() => this.root, platform);
		this.disposables.push(this.decorations, vscode.window.registerFileDecorationProvider(this.decorations));
	}

	/** The agents/ folder this window shows as the RAPP Workspace, once it is known. */
	get folder(): string | undefined {
		return this.root;
	}

	/** Starts watching the top of agents/ at `root`, the folder this window shows; undefined stops it. */
	watch(root: string | undefined): void {
		if (this.root === root) {
			return;
		}
		this.root = root;
		this.decorations.refresh();
		this.watcher?.dispose();
		this.watcher = undefined;
		if (!root) {
			return;
		}
		const watcher = vscode.workspace.createFileSystemWatcher(new vscode.RelativePattern(vscode.Uri.file(root), agentGlob(this.platform)), false, true, false);
		this.watcher = vscode.Disposable.from(watcher, watcher.onDidCreate(uri => this.note(uri, true)), watcher.onDidDelete(uri => this.note(uri, false)));
	}

	dispose(): void {
		clearTimeout(this.pending);
		this.watcher?.dispose();
		this.disposables.forEach(d => d.dispose());
	}

	// A move out and back (or a rewrite) inside one settle period says nothing: nothing changed.
	private note(uri: vscode.Uri, arrived: boolean): void {
		const name = path.basename(uri.fsPath);
		if (!isAgentFileName(name, this.platform) || isBaseAgent(name, this.platform) || !this.root || path.dirname(uri.fsPath) !== this.root) {
			return;
		}
		const [same, other] = arrived ? [this.cameLive, this.leftLive] : [this.leftLive, this.cameLive];
		if (!other.delete(name)) {
			same.add(name);
		}
		clearTimeout(this.pending);
		this.pending = setTimeout(() => this.settle(), this.settleMs);
	}

	private settle(): void {
		const message = liveMessage([...this.cameLive].sort(), [...this.leftLive].sort());
		this.cameLive.clear();
		this.leftLive.clear();
		if (message) {
			vscode.window.setStatusBarMessage(message, NOTE_MS);
		}
		this.changed();
	}
}
