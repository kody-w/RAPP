// The agent card as the default editor for *_agent.py files: a CustomTextEditorProvider over the same text
// document, so the card follows every edit, "View code" opens the code, and Reopen Editor With… Text Editor
// keeps working. The card never runs the agent and never changes the file; basic_agent.py opens as text
// (workbench.editorAssociations in package.json).
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import * as vscode from 'vscode';
import { CardContext, cardBody, cardModel, cardPage, cardPlace, Reading, reading } from './agentCard';
import { localModuleNames, pythonCandidates, readAgent } from './agentCardHelper';
import { Status } from './chatView';
import { BrainstemFolder } from './startup';
import { contentSecurityPolicy, makeNonce } from './html';

export interface CardSources {
	/** The agents/ folder whose top is live: the RAPP Workspace's, else the Brainstem's. */
	agentsRoot(): string | undefined;
	/** The global Brainstem folder and where it was found (the setting, /health, or the default). */
	brainstem(): BrainstemFolder;
	pythonSetting(): string;
	/** Hives and references: no Python in them is ever run. */
	forbidden(): readonly string[];
	status(): Status;
	/** Asks the Brainstem's /health again, resolving once it has answered. */
	poll(): Promise<unknown>;
	readonly onDidChangeStatus: vscode.Event<Status>;
}

const EDIT_DELAY_MS = 250;
// Settings that change which Python reads a card, or which agents/ folder and Brainstem it is judged against.
const READ_SETTINGS = ['rapp.pythonPath', 'rapp.brainstemFolder', 'rapp.agentsFolder', 'rapp.brainstemUrl'];

export class AgentCardEditor implements vscode.CustomTextEditorProvider, vscode.Disposable {
	static readonly viewType = 'rapp.agentCard';

	private readonly cards = new Set<AgentCard>();
	private readonly subscriptions: vscode.Disposable[];

	constructor(private readonly extensionUri: vscode.Uri, readonly sources: CardSources) {
		this.subscriptions = [
			sources.onDidChangeStatus(() => this.cards.forEach(card => card.schedule(0))),
			vscode.workspace.onDidChangeConfiguration(event => {
				if (READ_SETTINGS.some(key => event.affectsConfiguration(key))) {
					this.cards.forEach(card => card.reread());
				}
			}),
		];
	}

	dispose(): void {
		this.subscriptions.forEach(s => s.dispose());
		this.cards.forEach(card => card.dispose());
		this.cards.clear();
	}

	get helper(): string {
		return vscode.Uri.joinPath(this.extensionUri, 'python', 'agent_card.py').fsPath;
	}

	resolveCustomTextEditor(document: vscode.TextDocument, panel: vscode.WebviewPanel): void {
		const card = new AgentCard(this, document, panel);
		this.cards.add(card);
		panel.onDidDispose(() => {
			this.cards.delete(card);
			card.dispose();
		});
		card.schedule(0);
	}
}

class AgentCard {
	private timer: NodeJS.Timeout | undefined;
	private readFor: string | undefined;
	private read: Reading | undefined;
	private shown: string | undefined;
	private generation = 0;
	// Each time the file on disk may have changed (opened, saved, changed outside the editor), the card asks
	// /health itself, and holds a live file's loaded state against the Brainstem only once that answer is in:
	// an answer asked for earlier may not have seen the file as it is now.
	private placement = 0;
	private asked = -1;
	private answered = -1;
	private readonly disposables: vscode.Disposable[] = [];

	constructor(private readonly owner: AgentCardEditor, private readonly document: vscode.TextDocument, private readonly panel: vscode.WebviewPanel) {
		panel.webview.options = { enableScripts: true, enableCommandUris: false, localResourceRoots: [] };
		const same = (doc: vscode.TextDocument) => doc.uri.toString() === document.uri.toString();
		this.disposables.push(
			vscode.workspace.onDidChangeTextDocument(event => {
				if (same(event.document)) {
					// Not dirty after a change: the text was reloaded from the file on disk.
					if (!event.document.isDirty) {
						this.readFor = undefined;
						this.placement++;
					}
					this.schedule();
				}
			}),
			vscode.workspace.onDidSaveTextDocument(doc => {
				if (same(doc)) {
					this.readFor = undefined;
					this.placement++;
					this.schedule(0);
				}
			}),
			panel.onDidChangeViewState(() => {
				if (panel.visible) {
					this.schedule(0);
				}
			}),
			panel.webview.onDidReceiveMessage(message => void this.onMessage(message)),
		);
	}

	dispose(): void {
		clearTimeout(this.timer);
		this.generation++;
		this.disposables.forEach(d => d.dispose());
		this.disposables.length = 0;
	}

	schedule(delay = EDIT_DELAY_MS): void {
		clearTimeout(this.timer);
		this.timer = setTimeout(() => void this.render().catch(() => undefined), delay);
	}

	/** Reads the agent again, as when a setting chose another Python. */
	reread(): void {
		this.readFor = undefined;
		this.placement++;
		this.schedule(0);
	}

	private async render(): Promise<void> {
		const generation = ++this.generation;
		const { sources } = this.owner;
		const found = sources.brainstem();
		const folder = found.folder;
		const root = sources.agentsRoot();
		const uri = this.document.uri;
		const text = this.document.getText();
		if (!this.read || this.readFor !== text) {
			// What is saved is read as the file's own bytes, as the Brainstem will read it; unsaved edits as text.
			const bytes = uri.scheme === 'file' && !this.document.isDirty ? await fs.promises.readFile(uri.fsPath).catch(() => undefined) : undefined;
			const outcome = await readAgent(bytes ?? text, {
				pythons: pythonCandidates({ home: os.homedir(), brainstemFolder: folder, folderSource: found.source, setting: sources.pythonSetting(), forbidden: sources.forbidden() }),
				script: this.owner.helper,
				local: localModuleNames([folder, root]),
			});
			if (generation !== this.generation) {
				return;
			}
			this.read = reading(outcome);
			// A missing Python, a slow start or a failed run may pass; only what the file itself says is kept.
			const transient = 'problem' in this.read && ['no-python', 'timeout', 'failed'].includes(this.read.problem.kind);
			this.readFor = transient ? undefined : text;
		}
		const stat = uri.scheme === 'file' ? await fs.promises.stat(uri.fsPath).catch(() => undefined) : undefined;
		if (generation !== this.generation) {
			return;
		}
		const place = uri.scheme === 'file' ? cardPlace(root, uri.fsPath) : { kind: 'outside' as const };
		const status = sources.status();
		const up = status.state === 'connected' || status.state === 'signed-out';
		if (place.kind === 'live' && up && this.asked !== this.placement) {
			const placement = this.asked = this.placement;
			void sources.poll().then(() => {
				if (placement === this.placement) {
					this.answered = placement;
					this.schedule(0);
				}
			}, () => undefined);
		}
		const fresh = this.answered === this.placement;
		const context: CardContext = {
			fileName: path.basename(uri.fsPath),
			place,
			folderPath: path.dirname(uri.fsPath),
			size: stat?.size,
			modified: stat?.mtimeMs,
			dirty: this.document.isDirty,
			missing: uri.scheme === 'file' && !stat,
			brainstem: { up, loaded: up ? status.agentNames : undefined, fresh, version: up ? status.version : undefined },
			now: Date.now(),
		};
		const body = cardBody(cardModel(this.read, context));
		if (body === this.shown) {
			return;
		}
		this.shown = body;
		const nonce = makeNonce();
		this.panel.webview.html = cardPage(body, { csp: contentSecurityPolicy(this.panel.webview, nonce, { scripts: true }), nonce });
	}

	// The page sends only which button was pressed; nothing it sends names a file or a command.
	private async onMessage(message: unknown): Promise<void> {
		if (typeof message !== 'object' || message === null) {
			return;
		}
		const { type, line } = message as { type?: unknown; line?: unknown };
		if (type === 'viewCode') {
			const at = typeof line === 'number' && Number.isInteger(line) && line >= 1 && line <= this.document.lineCount ? line - 1 : undefined;
			await vscode.commands.executeCommand('vscode.openWith', this.document.uri, 'default', at === undefined ? undefined : { selection: new vscode.Range(at, 0, at, 0) });
		} else if (type === 'reveal') {
			await vscode.commands.executeCommand('revealInExplorer', this.document.uri);
		}
	}
}
