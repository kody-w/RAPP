import { createHash } from 'crypto';
import * as fs from 'fs';
import * as vscode from 'vscode';
import { contentSecurityPolicy, escapeHtml, makeNonce } from './html';

const LAYERS: readonly [number, string, string][] = [
	[6, 'You', 'Talk to your Brainstem. Nothing applies until you confirm the exact plan in a later turn.'],
	[5, 'Brainstem', 'The one surface you talk to: your own AI, with the Hive agent as one of its agents.'],
	[4, 'Your device', 'Your Hive copies, read-only references and private workspaces, one key per device.'],
	[3, 'Hive', 'A folder of markdown with git underneath; every change is a signed commit.'],
	[2, 'Organization', 'The accountable body: one owner, one policy, exactly one Hive.'],
	[1, 'Estate', 'An owner\'s signed registry.'],
	[0, 'RAPP/1', 'Bytes and identity: RAPPIDs, frames, hashes, signatures, eggs, registries.'],
];

function media(extensionUri: vscode.Uri): vscode.Uri {
	return vscode.Uri.joinPath(extensionUri, 'media', 'organism');
}

// The pinned one-page view, made safe to show: scripts are dropped (the pinned copy has none), its style
// blocks get the nonce and its style attributes are allowed by hash. The bytes on disk stay as pinned.
export function hardenPinnedPage(html: string, webview: vscode.Webview): string {
	const nonce = makeNonce();
	const withoutScripts = html.replace(/<script\b[\s\S]*?<\/script\s*>/gi, '');
	const hashes = [...new Set([...withoutScripts.matchAll(/\sstyle="([^"]*)"/g)]
		.map(m => `sha256-${createHash('sha256').update(m[1], 'utf8').digest('base64')}`))];
	const styled = withoutScripts.replace(/<style(\s[^>]*)?>/gi, `<style nonce="${nonce}">`);
	const meta = `<meta http-equiv="Content-Security-Policy" content="${contentSecurityPolicy(webview, nonce, { scripts: false, styleHashes: hashes })}">`;
	return /<head>/i.test(styled) ? styled.replace(/<head>/i, `<head>\n${meta}`) : `${meta}\n${styled}`;
}

export function openOnePage(extensionUri: vscode.Uri): vscode.WebviewPanel {
	const panel = vscode.window.createWebviewPanel('rapp.organismOnePage', 'The organism', vscode.ViewColumn.Active, {
		enableScripts: false,
		localResourceRoots: [media(extensionUri)],
	});
	panel.iconPath = vscode.Uri.joinPath(extensionUri, 'media', 'brainstem.svg');
	const raw = fs.readFileSync(vscode.Uri.joinPath(media(extensionUri), 'one-page.html').fsPath, 'utf8');
	panel.webview.html = hardenPinnedPage(raw, panel.webview);
	return panel;
}

// The Organism view: where this app sits (layers 4 to 6), the graph, and the one-page view.
export class OrganismView implements vscode.WebviewViewProvider {
	static readonly id = 'rapp.organism';

	constructor(private readonly extensionUri: vscode.Uri) { }

	resolveWebviewView(view: vscode.WebviewView): void {
		view.webview.options = { enableScripts: true, localResourceRoots: [media(this.extensionUri)] };
		const nonce = makeNonce();
		const graph = view.webview.asWebviewUri(vscode.Uri.joinPath(media(this.extensionUri), 'organism.svg'));
		const rows = LAYERS.map(([n, name, text]) =>
			`<li class="${n >= 4 ? 'here' : ''}"><span class="n">${n}</span><div><b>${escapeHtml(name)}</b> <span class="desc">${escapeHtml(text)}</span></div></li>`).join('');
		view.webview.html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="${contentSecurityPolicy(view.webview, nonce, { scripts: true })}">
<style nonce="${nonce}">
	body { margin: 0; padding: 8px 12px 12px; font-family: var(--vscode-font-family); font-size: var(--vscode-font-size); color: var(--vscode-foreground); }
	p { margin: 4px 0 8px; line-height: 1.4; }
	ol { list-style: none; margin: 0 0 10px; padding: 0; display: flex; flex-direction: column; gap: 4px; }
	li { display: flex; gap: 8px; align-items: flex-start; padding: 4px 6px; border-radius: 5px; line-height: 1.35; }
	li .desc { color: var(--vscode-descriptionForeground); }
	li.here { background: var(--vscode-list-inactiveSelectionBackground); }
	li.here .desc { color: var(--vscode-foreground); }
	.n { flex: none; width: 18px; height: 18px; border-radius: 50%; text-align: center; line-height: 18px; font-size: 0.85em; font-weight: 700; color: var(--vscode-button-foreground); background: var(--vscode-button-background); }
	li:not(.here) .n { background: var(--vscode-badge-background); color: var(--vscode-badge-foreground); }
	button.graph { display: block; width: 100%; padding: 0; border: 1px solid var(--vscode-widget-border, transparent); border-radius: 6px; background: #fff; cursor: zoom-in; overflow: hidden; }
	button.graph img { display: block; width: 100%; height: auto; }
	.row { margin-top: 8px; }
	button.open { font: inherit; border: none; border-radius: 3px; padding: 4px 10px; cursor: pointer; color: var(--vscode-button-foreground); background: var(--vscode-button-background); }
	.pin { font-size: 0.85em; color: var(--vscode-descriptionForeground); }
</style>
</head>
<body>
<p>This app is layers 4 to 6: you talk to your Brainstem, with your Hives and references beside it.</p>
<ol>${rows}</ol>
<button class="graph" id="graph" title="Open the one-page view"><img src="${graph}" alt="The RAPP organism, bottom to top"></button>
<div class="row"><button class="open" id="open">Open the one-page view</button></div>
<p class="pin">Pinned copy of the organism views from kody-w/rapp-work at ef74030. Its “experimental” marks are newest-channel work, not part of RAPP/1.</p>
<script nonce="${nonce}">
(function () {
	const vscode = acquireVsCodeApi();
	for (const id of ['graph', 'open']) {
		document.getElementById(id).addEventListener('click', () => vscode.postMessage({ type: 'open' }));
	}
}());
</script>
</body>
</html>`;
		view.webview.onDidReceiveMessage(message => {
			if (message && message.type === 'open') {
				void vscode.commands.executeCommand('rapp.organism.open');
			}
		});
	}
}
