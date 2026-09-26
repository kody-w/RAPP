import * as vscode from 'vscode';
import { AgentCardEditor } from './agentCardEditor';
import { DataCardEditor } from './dataCardEditor';
import { RappWorkspace } from './agentsView';
import { Wire } from './brainstem';
import { BrainstemView, Status, statusTooltip } from './chatView';
import { checkerPythons, checkerRefusal, CheckResult, NOT_CONFIGURED, noticeText, runCheck } from './checker';
import { DataFileSystem, READ_ONLY_REASON } from './dataFs';
import { Hive, hivesHome, readReferences } from './hives';
import { HiveNode, HivesTreeProvider, NO_HIVES } from './hivesTree';
import { BrainstemLauncher } from './launcher';
import { openOnePage, OrganismView } from './organismView';
import { NO_REFERENCE_HIVES, ReferencesTreeProvider } from './referencesTree';
import { DATA_SCHEME, dataUri } from './startup';

interface Settings {
	readonly url: string;
	readonly wire: Wire;
	readonly agentPath: string;
	readonly python: string;
	readonly brainstemFolder: string;
	readonly agentsFolder: string;
	readonly openOnStartup: boolean;
	readonly showUI: boolean;
}

function settings(): Settings {
	const config = vscode.workspace.getConfiguration('rapp');
	return {
		url: config.get<string>('brainstemUrl', 'http://127.0.0.1:7071').trim(),
		wire: config.get<string>('chat.wire', 'grail') === 'rapp1' ? 'rapp1' : 'grail',
		agentPath: config.get<string>('hiveAgentPath', '').trim(),
		python: config.get<string>('pythonPath', 'python3').trim() || 'python3',
		brainstemFolder: config.get<string>('brainstemFolder', '').trim(),
		agentsFolder: config.get<string>('agentsFolder', '').trim(),
		openOnStartup: config.get<boolean>('openBrainstemOnStartup', true),
		showUI: config.get<boolean>('showBrainstemUI', true),
	};
}

const isHiveNode = (node: unknown): node is Extract<HiveNode, { kind: 'hive' }> =>
	typeof node === 'object' && node !== null && (node as { kind?: unknown }).kind === 'hive';

export function activate(context: vscode.ExtensionContext): void {
	const home = () => hivesHome();
	const checks = new Map<string, CheckResult>();
	const hivesTree = new HivesTreeProvider(home, name => checks.get(name));
	const referencesTree = new ReferencesTreeProvider(home);
	// The Hives folder and every pinned reference: nothing in them is ever run or opened as the Brainstem.
	const forbidden = () => [home(), ...hivesTree.hives().flatMap(h => readReferences(h.path).map(r => r.path))];
	// The Brainstem data root, read-only: registered first, since the window may need it to show its roots.
	const dataFs = new DataFileSystem(forbidden);
	context.subscriptions.push(dataFs, vscode.workspace.registerFileSystemProvider(DATA_SCHEME, dataFs, {
		isCaseSensitive: process.platform === 'linux',
		isReadonly: new vscode.MarkdownString(READ_ONLY_REASON),
	}));
	// View raw shows a data file read-only, as the data root serves it, even when the card was opened on the file itself.
	const rawOf = (uri: vscode.Uri) => (uri.scheme === 'file' && dataFs.serves(uri.fsPath) ? vscode.Uri.parse(dataUri(uri.fsPath)) : uri);
	const brainstem = new BrainstemView(context.extensionUri, settings, () => launcher.canStart());
	// After an agent file arrives at the top of agents/ or leaves it, the live count is asked for again.
	const workspace = new RappWorkspace(() => void brainstem.poll());
	const launcher = new BrainstemLauncher(context, brainstem, settings, forbidden, root => workspace.watch(root));
	// An agent file opens as its card: what it can do, in plain words, read without running it.
	const located = () => launcher.locate(brainstem.currentStatus);
	const cards = new AgentCardEditor(context.extensionUri, {
		agentsRoot: () => workspace.folder ?? launcher.agentsFolder(located().folder).folder,
		brainstem: located,
		pythonSetting: () => settings().python,
		forbidden,
		status: () => brainstem.currentStatus,
		poll: () => brainstem.poll(),
		onDidChangeStatus: brainstem.onDidChangeStatus,
	});
	const status = vscode.window.createStatusBarItem('rapp.brainstem.status', vscode.StatusBarAlignment.Left, 100);
	status.name = 'Brainstem';
	status.command = `${BrainstemView.id}.focus`;

	const showStatus = (s: Status) => {
		const up = s.state === 'connected';
		// How many agents it has live right now, from /health: "Brainstem · 10 live".
		const live = up && typeof s.agentCount === 'number' ? ` · ${s.agentCount} live` : '';
		status.text = `$(${up ? 'circle-filled' : s.state === 'checking' ? 'loading~spin' : 'circle-outline'}) Brainstem${live}`;
		status.tooltip = statusTooltip(s, brainstem.isStarting);
		status.show();
	};
	showStatus(brainstem.currentStatus);

	const hivesView = vscode.window.createTreeView('rapp.hives', { treeDataProvider: hivesTree, showCollapseAll: true });
	const referencesView = vscode.window.createTreeView('rapp.references', { treeDataProvider: referencesTree });
	// With no Hives, each view says so above its empty tree, where the words wrap.
	const showEmpty = () => {
		const none = hivesTree.hives().length === 0;
		hivesView.message = none ? NO_HIVES : undefined;
		referencesView.message = none ? NO_REFERENCE_HIVES : undefined;
	};
	showEmpty();
	const refresh = () => {
		hivesTree.refresh();
		referencesTree.refresh();
		showEmpty();
	};

	let checking: Promise<void> = Promise.resolve();
	const check = (hives: readonly Hive[]) => {
		checking = checking.then(async () => {
			const { agentPath, python } = settings();
			if (!agentPath) {
				hives.forEach(h => checks.set(h.name, NOT_CONFIGURED));
				refresh();
				return;
			}
			const refusal = checkerRefusal(agentPath, python, forbidden());
			for (const hive of hives) {
				if (refusal) {
					checks.set(hive.name, { state: 'failed', summary: refusal, output: '' });
					continue;
				}
				checks.set(hive.name, { state: 'checking', summary: 'checking…', output: '' });
				hivesTree.refresh();
				let result: CheckResult | undefined;
				for (const candidate of checkerPythons(python)) {
					result = await runCheck(candidate, agentPath, hive.path);
					if (!result.notStarted) {
						break;
					}
				}
				checks.set(hive.name, result as CheckResult);
			}
			refresh();
		});
		return checking;
	};

	const pickHive = async (node: unknown): Promise<Hive | undefined> => {
		if (isHiveNode(node)) {
			return node.hive;
		}
		const hives = hivesTree.hives();
		if (!hives.length) {
			void vscode.window.showInformationMessage('There are no Hives on this device yet. Ask your Brainstem to create or join one.');
			return undefined;
		}
		if (hives.length === 1) {
			return hives[0];
		}
		const pick = await vscode.window.showQuickPick(hives.map(hive => ({ label: hive.name, hive })), { placeHolder: 'Which Hive?' });
		return pick?.hive;
	};

	let pendingRefresh: NodeJS.Timeout | undefined;
	const watcher = vscode.workspace.createFileSystemWatcher(new vscode.RelativePattern(vscode.Uri.file(home()), '**/*'));
	const later = () => {
		clearTimeout(pendingRefresh);
		pendingRefresh = setTimeout(refresh, 400);
	};

	context.subscriptions.push(
		launcher,
		workspace,
		cards,
		brainstem,
		status,
		watcher,
		watcher.onDidCreate(later),
		watcher.onDidDelete(later),
		watcher.onDidChange(later),
		brainstem.onDidChangeStatus(showStatus),
		vscode.window.registerWebviewViewProvider(BrainstemView.id, brainstem, { webviewOptions: { retainContextWhenHidden: true } }),
		vscode.window.registerWebviewViewProvider(OrganismView.id, new OrganismView(context.extensionUri)),
		vscode.window.registerCustomEditorProvider(AgentCardEditor.viewType, cards, { supportsMultipleEditorsPerDocument: true }),
		// What the Brainstem remembers, and the agent collections it put together: its data, read-only.
		vscode.window.registerCustomEditorProvider(DataCardEditor.memoryType, new DataCardEditor('memory', rawOf), { supportsMultipleEditorsPerDocument: true }),
		vscode.window.registerCustomEditorProvider(DataCardEditor.collectionsType, new DataCardEditor('collections', rawOf), { supportsMultipleEditorsPerDocument: true }),
		hivesView,
		referencesView,

		vscode.commands.registerCommand('rapp.ask', async (text?: unknown) => {
			const message = typeof text === 'string' && text.trim() ? text : await vscode.window.showInputBox({
				prompt: 'Ask your Brainstem',
				placeHolder: 'What would you like to do?',
				ignoreFocusOut: true,
			});
			if (message?.trim()) {
				await brainstem.ask(message.trim());
			}
		}),
		vscode.commands.registerCommand('rapp.hive.check', async (node?: unknown) => {
			const hive = await pickHive(node);
			if (hive) {
				await check([hive]);
				const result = checks.get(hive.name);
				if (result && result.state !== 'verified') {
					void vscode.window.showWarningMessage(noticeText(`Hive ${hive.name}: ${result.summary}`));
				}
			}
		}),
		vscode.commands.registerCommand('rapp.hive.reveal', async (node?: unknown) => {
			const hive = await pickHive(node);
			if (hive) {
				try {
					await vscode.commands.executeCommand('revealFileInOS', vscode.Uri.file(hive.path));
				} catch {
					void vscode.window.showInformationMessage(noticeText(`Hive ${hive.name} is at ${hive.path}`));
				}
			}
		}),
		vscode.commands.registerCommand('rapp.hive.save', async (node?: unknown) => {
			const hive = await pickHive(node);
			if (hive) {
				await brainstem.ask(`Save my hand edits in the Hive "${hive.name}". Show me exactly what would be saved and change nothing yet; I will confirm in my next message.`);
			}
		}),
		vscode.commands.registerCommand('rapp.hives.refresh', async () => {
			refresh();
			await check(hivesTree.hives());
		}),
		vscode.commands.registerCommand('rapp.organism.open', () => {
			openOnePage(context.extensionUri);
		}),
		vscode.commands.registerCommand('rapp.openBrainstem', () => launcher.openFolder()),
		vscode.commands.registerCommand('rapp.startBrainstem', () => launcher.start()),
		vscode.commands.registerCommand('rapp.openBrainstemUI', () => launcher.openUI()),
		vscode.commands.registerCommand('rapp.agentCard.show', async (uri?: unknown) => {
			const target = uri instanceof vscode.Uri ? uri : vscode.window.activeTextEditor?.document.uri;
			if (target) {
				await vscode.commands.executeCommand('vscode.openWith', target, AgentCardEditor.viewType);
			}
		}),
		vscode.workspace.onDidChangeConfiguration(event => {
			if (event.affectsConfiguration('rapp.hiveAgentPath') || event.affectsConfiguration('rapp.pythonPath')) {
				void check(hivesTree.hives());
			}
			if (event.affectsConfiguration('rapp.brainstemUrl') || event.affectsConfiguration('rapp.brainstemFolder') || event.affectsConfiguration('rapp.agentsFolder')) {
				void brainstem.poll();
			}
		}),
		{ dispose: () => clearTimeout(pendingRefresh) },
	);

	void launcher.onStartup().catch(() => undefined);
	void check(hivesTree.hives());
}

export function deactivate(): void { }
