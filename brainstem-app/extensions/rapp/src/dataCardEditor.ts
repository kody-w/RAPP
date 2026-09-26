// The Brainstem data cards as default editors: what it remembers (memory.json and user_memory.json under
// .brainstem_data) and its agent collections (rar_collections/collections.json). Custom text editors over the
// same documents, which the RAPP Workspace serves read-only (dataFs.ts): a card follows the Brainstem's own
// writes, and View raw opens the JSON, read-only too. Nothing here changes a file.
import * as vscode from 'vscode';
import { collectionsBody, dataFile, dataPage, memoryBody, readCollections, readMemories } from './dataCard';
import { contentSecurityPolicy, makeNonce } from './html';

const CHANGE_DELAY_MS = 250;

export class DataCardEditor implements vscode.CustomTextEditorProvider {
	static readonly memoryType = 'rapp.memoryCard';
	static readonly collectionsType = 'rapp.collectionsCard';

	// `raw` is where View raw opens a document: the read-only data root's copy of it.
	constructor(private readonly kind: 'memory' | 'collections', private readonly raw: (uri: vscode.Uri) => vscode.Uri = uri => uri) { }

	resolveCustomTextEditor(document: vscode.TextDocument, panel: vscode.WebviewPanel): void {
		panel.webview.options = { enableScripts: true, enableCommandUris: false, localResourceRoots: [] };
		let shown: string | undefined;
		let timer: NodeJS.Timeout | undefined;
		const render = () => {
			const body = this.kind === 'memory'
				? memoryBody(readMemories(document.getText()), dataFile(document.uri.fsPath))
				: collectionsBody(readCollections(document.getText()));
			if (body !== shown) {
				shown = body;
				const nonce = makeNonce();
				panel.webview.html = dataPage(body, { csp: contentSecurityPolicy(panel.webview, nonce, { scripts: true }), nonce });
			}
		};
		const subscriptions = [
			vscode.workspace.onDidChangeTextDocument(event => {
				if (event.document.uri.toString() === document.uri.toString()) {
					clearTimeout(timer);
					timer = setTimeout(render, CHANGE_DELAY_MS);
				}
			}),
			// The page sends only which button was pressed.
			panel.webview.onDidReceiveMessage((message: unknown) => {
				if (typeof message === 'object' && message !== null && (message as { type?: unknown }).type === 'viewRaw') {
					void vscode.commands.executeCommand('vscode.openWith', this.raw(document.uri), 'default');
				}
			}),
		];
		panel.onDidDispose(() => {
			clearTimeout(timer);
			subscriptions.forEach(s => s.dispose());
		});
		render();
	}
}
