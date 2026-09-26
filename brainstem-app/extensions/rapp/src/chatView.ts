import * as vscode from 'vscode';
import { chat, Endpoint, failureWords, health, Health, parseEndpoint, Turn, Wire } from './brainstem';
import { GRAIL, grailOneLiner } from './grail';
import { contentSecurityPolicy, makeNonce } from './html';

export interface ChatSettings {
	readonly url: string;
	readonly wire: Wire;
}

export type Status = Health | { readonly state: 'checking' } | { readonly state: 'misconfigured'; readonly reason: string };

interface ShownTurn {
	readonly role: 'user' | 'assistant' | 'note';
	readonly text: string;
	readonly logs?: string;
	// A message of the person's that was sent: only these, and the replies to them, are the conversation so far.
	sent?: boolean;
}

const HISTORY_TURNS = 24;
// How long a message's own check of its address may take: as long as a person already waits for a reply to start.
const MESSAGE_CHECK_MS = 60000;
const isRecord = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v);

// Voice and Twin slots are presentation that derives from the response; the chat shows the text part.
export function shownText(response: string): string {
	return response.split(/\|\|\|(?:VOICE|TWIN)\|\|\|/)[0].trim();
}

/** The status bar's words for a status (and while the Brainstem's own start script runs). */
export function statusTooltip(s: Status, starting = false): string {
	if (starting && s.state === 'not-running' && !s.occupied) {
		return 'Starting your Brainstem…';
	}
	switch (s.state) {
		case 'connected': return 'Your Brainstem is running';
		case 'signed-out': return 'Your Brainstem is not signed in yet';
		case 'checking': return 'Looking for your Brainstem';
		case 'misconfigured': return 'The Brainstem address is not allowed';
		case 'not-running': return s.occupied ? 'Something else is using your Brainstem\'s address' : s.busy ? 'Your Brainstem is busy'
			: s.dropped ? 'Your Brainstem isn\'t answering' : 'Your Brainstem isn\'t running';
	}
}

// What to do about a Brainstem that closes every connection without an answer.
const JUST_ADDED = 'If you just added an agent, move it out of the top of agents/, then check again.';

// Why a message was not sent, in the card's words, from its own check.
function notSentNote(s: Status, starting: boolean): string {
	if (s.state === 'signed-out') {
		return 'Nothing was sent: your Brainstem is not signed in yet. Sign in on its page, then send it again.';
	}
	if (s.state === 'not-running' && s.occupied) {
		return 'Nothing was sent: something else is using your Brainstem\'s address. Close that program, then check again.';
	}
	if (s.state === 'not-running' && s.busy) {
		return 'Nothing was sent: your Brainstem did not answer within a minute. Send it again in a moment.';
	}
	if (s.state === 'not-running' && s.dropped) {
		return `Nothing was sent: your Brainstem isn't answering. ${JUST_ADDED}`;
	}
	if (starting) {
		return 'Nothing was sent: your Brainstem is still starting. Send it again once it is running.';
	}
	return 'Nothing was sent: your Brainstem isn\'t running. Start it, then send it again.';
}


export interface CardLayout {
	readonly statusClass: string;
	readonly signIn: boolean;
	readonly offline: boolean;
	readonly startRow: boolean;
	readonly startHint: boolean;
	readonly install: boolean;
	readonly note: boolean;
	readonly recheckPrimary: boolean;
}

/**
 * What the Brainstem view's card shows for a described status. The page runs this very function (its source is
 * put into the page's script), so what is tested here is what shows. While another program holds the address,
 * or the Brainstem is busy or not answering, starting or installing it cannot help: Check again is the one step.
 */
export function cardLayout(s: { state: string; starting?: boolean; canStart?: boolean; occupied?: boolean; busy?: boolean; dropped?: boolean; oneLiner?: string; note?: string }): CardLayout {
	const offline = s.state === 'not-running';
	const waiting = !!(s.occupied || s.busy || s.dropped);
	return {
		statusClass: `status ${s.state}${s.starting && !waiting ? ' starting' : ''}${waiting ? ' waiting' : ''}`,
		signIn: s.state === 'signed-out',
		offline,
		startRow: offline && !waiting && !!s.canStart,
		startHint: offline && !waiting,
		install: offline && !waiting && !!s.oneLiner,
		note: offline && !waiting && !!s.note,
		recheckPrimary: waiting,
	};
}

// The Brainstem view: a chat with the local Brainstem. The webview has no network access; every request
// goes through the extension host to this device's Brainstem only.
export class BrainstemView implements vscode.WebviewViewProvider, vscode.Disposable {
	static readonly id = 'rapp.brainstem';

	private view: vscode.WebviewView | undefined;
	private readonly turns: ShownTurn[] = [];
	private readonly pending: string[] = [];
	private sessionId: string | undefined;
	private conversation = 0;
	private busy = false;
	private starting = false;
	// The address and wire the conversation's first message went to: a conversation never follows the chat elsewhere.
	private conversationWith: string | undefined;
	// The message now being checked or sent, so New conversation can let go of it.
	private inFlight: AbortController | undefined;
	private inFlightTurn: ShownTurn | undefined;
	private status: Status = { state: 'checking' };
	private readonly statusChanged = new vscode.EventEmitter<Status>();
	readonly onDidChangeStatus = this.statusChanged.event;
	private readonly timer: NodeJS.Timeout;
	private polls = 0;
	private applied = 0;

	// `startable` says whether this device has a Brainstem folder whose own start script can be run; `check`
	// asks a Brainstem's /health.
	constructor(
		private readonly extensionUri: vscode.Uri,
		private readonly settings: () => ChatSettings,
		private readonly startable: () => boolean = () => false,
		private readonly check: (endpoint: Endpoint, timeoutMs?: number, signal?: AbortSignal) => Promise<Health> = (endpoint, timeoutMs, signal) => health(endpoint, timeoutMs, { signal }),
	) {
		this.timer = setInterval(() => void this.poll(), 15000);
	}

	dispose(): void {
		clearInterval(this.timer);
		this.statusChanged.dispose();
	}

	get currentStatus(): Status {
		return this.status;
	}

	/** Whether the Brainstem's own start script runs, started from this window. */
	get isStarting(): boolean {
		return this.starting;
	}

	resolveWebviewView(view: vscode.WebviewView): void {
		this.view = view;
		view.webview.options = { enableScripts: true, localResourceRoots: [vscode.Uri.joinPath(this.extensionUri, 'media')] };
		view.webview.html = this.html(view.webview);
		view.webview.onDidReceiveMessage(message => void this.onMessage(message));
		view.onDidChangeVisibility(() => {
			if (view.visible) {
				void this.poll();
			}
		});
		view.onDidDispose(() => {
			this.view = undefined;
		});
	}

	// Sends a message as if the person typed it, revealing the view first.
	async ask(text: string): Promise<void> {
		this.pending.push(text);
		await vscode.commands.executeCommand(`${BrainstemView.id}.focus`);
		await this.drain();
	}

	// Answers can arrive out of order (a slow one after a quick later one): an older answer never replaces a
	// newer one, so the live count and an agent card's "didn't load" check see the latest state only.
	async poll(): Promise<Status> {
		const endpoint = this.endpoint();
		if (typeof endpoint === 'string') {
			const id = ++this.polls;
			if (id > this.applied) {
				this.applied = id;
				this.setStatus({ state: 'misconfigured', reason: endpoint });
			}
			return this.status;
		}
		await this.checkAt(endpoint);
		return this.status;
	}

	// A check of one address: shown when it is the newest, and its own result returned to the one who asked, since
	// another check (older or newer, maybe of another address) may be what the view shows.
	private async checkAt(endpoint: Endpoint, timeoutMs?: number, signal?: AbortSignal): Promise<Status> {
		const id = ++this.polls;
		const status = await this.check(endpoint, timeoutMs, signal);
		// A check let go of (New conversation) says nothing about the Brainstem.
		if (id > this.applied && !signal?.aborted) {
			this.applied = id;
			this.setStatus(status);
		}
		return status;
	}

	// While the Brainstem's own start script runs, the offline card says so instead of offering it again.
	setStarting(on: boolean): void {
		this.starting = on;
		this.statusChanged.fire(this.status);
		this.post({ type: 'status', status: this.describe(this.status) });
	}

	private endpoint(): Endpoint | string {
		return parseEndpoint(this.settings().url);
	}

	private setStatus(status: Status): void {
		this.status = status;
		this.statusChanged.fire(status);
		this.post({ type: 'status', status: this.describe(status) });
	}

	private describe(status: Status): Record<string, unknown> {
		const offline = () => {
			const grail = grailOneLiner();
			return { oneLiner: grail.command, platform: grail.label, note: grail.note, start: GRAIL.start, canStart: this.startable(), starting: this.starting };
		};
		switch (status.state) {
			case 'checking':
				return { state: 'checking', title: 'Looking for your Brainstem…' };
			case 'connected':
				return { state: 'connected', title: 'Your Brainstem is running', detail: status.version ? `version ${status.version}` : '' };
			case 'signed-out':
				return { state: 'signed-out', title: 'Your Brainstem is running but is not signed in yet', detail: 'Sign in on its page: the sign-in opens there, or its link is at the top. This updates by itself.' };
			case 'not-running':
				if (this.starting && !status.occupied) {
					return { state: 'not-running', title: 'Starting your Brainstem…', detail: 'Its start script is running in the Brainstem terminal.', ...offline() };
				}
				// Starting it or installing it cannot help while another program holds its address, or while it is
				// running but busy or not answering: the one step is to check again.
				if (status.occupied) {
					return { state: 'not-running', title: 'Something else is using your Brainstem\'s address', detail: `Close the program that answers at ${this.settings().url}, then check again.`, ...offline(), canStart: false, occupied: true };
				}
				if (status.busy) {
					return { state: 'not-running', title: 'Your Brainstem is busy', detail: 'It is taking a while to answer, as it can while it gets what a new agent needs. Check again in a moment.', ...offline(), canStart: false, busy: true };
				}
				if (status.dropped) {
					return { state: 'not-running', title: 'Your Brainstem isn\'t answering', detail: `It closes the connection without an answer. ${JUST_ADDED}`, ...offline(), canStart: false, dropped: true };
				}
				return { state: 'not-running', title: 'Your Brainstem isn\'t running', detail: `Nothing answered at ${this.settings().url}.`, ...offline() };
			case 'misconfigured':
				return { state: 'misconfigured', title: 'The Brainstem address is not allowed', detail: `${status.reason} (setting rapp.brainstemUrl).` };
		}
	}

	private post(message: Record<string, unknown>): void {
		void this.view?.webview.postMessage(message);
	}

	private addTurn(turn: ShownTurn): void {
		this.turns.push(turn);
		this.post({ type: 'turn', turn });
	}

	private async onMessage(message: unknown): Promise<void> {
		if (!isRecord(message)) {
			return;
		}
		switch (message.type) {
			case 'ready':
				this.post({ type: 'restore', turns: this.turns, status: this.describe(this.status), busy: this.busy });
				await this.poll();
				await this.drain();
				return;
			case 'send':
				if (typeof message.text === 'string' && message.text.trim()) {
					this.pending.push(message.text.trim());
					await this.drain();
				}
				return;
			case 'copy': {
				const { command } = grailOneLiner();
				if (command) {
					await vscode.env.clipboard.writeText(command);
					void vscode.window.showInformationMessage('Copied the grail one-liner. Paste it into a terminal to install your Brainstem.');
				}
				return;
			}
			case 'recheck':
				await this.poll();
				return;
			case 'start':
				await vscode.commands.executeCommand('rapp.startBrainstem');
				return;
			case 'openUI':
				await vscode.commands.executeCommand('rapp.openBrainstemUI');
				return;
			case 'restart':
				this.pending.length = 0;
				this.beginConversation();
				return;
		}
	}

	private async drain(): Promise<void> {
		if (this.busy || !this.view) {
			return;
		}
		const text = this.pending.shift();
		if (!text) {
			return;
		}
		this.busy = true;
		const target = this.endpoint();
		const wire = this.settings().wire;
		// A conversation stays with the address and wire it began on: another Brainstem, or the RAPP/1 wire, starts
		// a new one (its session and what was said never go there).
		const key = typeof target === 'string' ? undefined : `${target.url} ${wire}`;
		if (this.conversationWith !== undefined && key !== undefined && key !== this.conversationWith) {
			this.beginConversation();
			this.addTurn({ role: 'note', text: 'A new conversation began here: your Brainstem\'s address or its chat setting changed.' });
		}
		const conversation = this.conversation;
		const turn: ShownTurn = { role: 'user', text };
		const before = this.turns.length;
		this.addTurn(turn);
		this.post({ type: 'busy', busy: true });
		const abort = new AbortController();
		this.inFlight = abort;
		this.inFlightTurn = turn;
		try {
			if (typeof target === 'string') {
				throw new Error(target);
			}
			// The conversation is the person's: each message goes only on its own check of the very address it goes
			// to, which waits as long as a person waits for a reply to start (so a slow Brainstem still gets it), and
			// only to a Brainstem that answers there, signed in: never to another program, nor on another check's word.
			const found = await this.checkAt(target, MESSAGE_CHECK_MS, abort.signal);
			const now = this.endpoint();
			if (conversation !== this.conversation) {
				// A new conversation began while it checked: this message went with the old one, and is not sent.
			} else if (typeof now === 'string' || now.url !== target.url || this.settings().wire !== wire) {
				this.addTurn({ role: 'note', text: 'Nothing was sent: your Brainstem\'s address or its chat setting changed while it was checked. Send it again.' });
			} else if (found.state !== 'connected') {
				this.addTurn({ role: 'note', text: notSentNote(found, this.starting) });
			} else {
				// What was said so far: the person's messages that were sent, and the replies to them.
				const history: Turn[] = this.turns.slice(0, before)
					.filter((t): t is ShownTurn & { role: 'user' | 'assistant' } => t.role === 'assistant' || (t.role === 'user' && !!t.sent))
					.slice(-HISTORY_TURNS)
					.map(t => ({ role: t.role, content: t.text }));
				turn.sent = true;
				this.conversationWith = key;
				const reply = await chat(target, wire, text, this.sessionId, history, undefined, abort.signal);
				if (conversation === this.conversation) {
					this.sessionId = reply.sessionId ?? this.sessionId;
					this.addTurn({ role: 'assistant', text: shownText(reply.response) || '(no text)', logs: reply.agentLogs || undefined });
				}
			}
		} catch (error) {
			// A message whose request never reached the Brainstem was not sent after all.
			if ((error as { connected?: boolean }).connected === false) {
				turn.sent = false;
			}
			if (conversation === this.conversation) {
				const words = failureWords(error) ?? (error instanceof Error ? error.message : String(error));
				this.addTurn({ role: 'note', text: (error as { answered?: boolean }).answered ? `Your Brainstem ${words}` : `Your Brainstem could not answer: ${words}` });
				void this.poll();
			}
		} finally {
			if (this.inFlight === abort) {
				this.inFlight = undefined;
				this.inFlightTurn = undefined;
			}
			this.busy = false;
			this.post({ type: 'busy', busy: false });
		}
		await this.drain();
	}

	// A new, empty conversation: what was said, its session and its address are let go of, and so is a message still
	// being checked or sent (its answer, if one comes, belongs to the old conversation and is dropped). A message
	// already sent may still be carried out by the Brainstem, which does not stop for a caller that left: the new
	// conversation begins by saying so.
	private beginConversation(): void {
		const alreadySent = !!this.inFlight && !!this.inFlightTurn?.sent;
		this.conversation++;
		this.inFlight?.abort();
		this.turns.length = 0;
		this.sessionId = undefined;
		this.conversationWith = undefined;
		this.post({ type: 'restore', turns: [], status: this.describe(this.status), busy: this.busy });
		if (alreadySent) {
			this.addTurn({ role: 'note', text: 'Your last message was already sent: your Brainstem may still carry it out. Check before you send it again.' });
		}
	}

	private html(webview: vscode.Webview): string {
		const nonce = makeNonce();
		return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="${contentSecurityPolicy(webview, nonce, { scripts: true })}">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style nonce="${nonce}">
	html, body { height: 100%; }
	body { margin: 0; padding: 0 12px; font-family: var(--vscode-font-family); font-size: var(--vscode-font-size); color: var(--vscode-foreground); display: flex; flex-direction: column; box-sizing: border-box; overflow-x: hidden; overflow-y: auto; }
	.status, .detail, #offline, .composer { flex: none; }
	.status { display: flex; align-items: center; gap: 8px; padding: 10px 0 8px; font-weight: 600; }
	.status .dot { width: 9px; height: 9px; border-radius: 50%; background: var(--vscode-descriptionForeground); flex: none; }
	.status.connected .dot { background: var(--vscode-testing-iconPassed, #3fa66a); }
	.status.not-running .dot, .status.misconfigured .dot { background: var(--vscode-testing-iconFailed, #c94f4f); }
	.status.waiting .dot { background: var(--vscode-problemsWarningIcon-foreground, #c9a24f); }
	.status.signed-out .dot { background: var(--vscode-problemsWarningIcon-foreground, #c9a24f); }
	.status.starting .dot { background: var(--vscode-descriptionForeground); }
	.detail { color: var(--vscode-descriptionForeground); margin: -4px 0 8px 17px; }
	#offline { border: 1px solid var(--vscode-widget-border, var(--vscode-panel-border)); border-radius: 6px; padding: 8px 10px; margin-bottom: 10px; }
	#offline p { margin: 6px 0; }
	#offline .start { margin: 6px 0 8px; }
	pre, code { font-family: var(--vscode-editor-font-family); font-size: calc(var(--vscode-editor-font-size) * 0.92); }
	pre { white-space: pre-wrap; word-break: break-all; background: var(--vscode-textCodeBlock-background); padding: 6px 8px; border-radius: 4px; margin: 6px 0; }
	.note { color: var(--vscode-descriptionForeground); }
	.row { display: flex; gap: 6px; flex-wrap: wrap; }
	button { font: inherit; border: none; border-radius: 3px; padding: 4px 10px; cursor: pointer; color: var(--vscode-button-foreground); background: var(--vscode-button-background); }
	button:hover { background: var(--vscode-button-hoverBackground); }
	button.secondary { color: var(--vscode-button-secondaryForeground); background: var(--vscode-button-secondaryBackground); }
	button:disabled { opacity: 0.6; cursor: default; }
	#log { flex: 1 1 auto; min-height: 7em; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; padding: 2px 0 10px; }
	.intro { color: var(--vscode-descriptionForeground); line-height: 1.45; }
	.turn .who { font-size: 0.85em; color: var(--vscode-descriptionForeground); margin-bottom: 2px; }
	.turn .text { white-space: pre-wrap; line-height: 1.45; overflow-wrap: anywhere; }
	.turn.user .text { background: var(--vscode-input-background); border: 1px solid var(--vscode-input-border, transparent); border-radius: 6px; padding: 6px 8px; }
	.turn.note .text { color: var(--vscode-descriptionForeground); font-style: italic; }
	details { margin-top: 4px; color: var(--vscode-descriptionForeground); }
	.composer { padding: 6px 0 10px; display: flex; flex-direction: column; gap: 6px; border-top: 1px solid var(--vscode-widget-border, transparent); }
	textarea { font: inherit; resize: vertical; min-height: 44px; box-sizing: border-box; width: 100%; color: var(--vscode-input-foreground); background: var(--vscode-input-background); border: 1px solid var(--vscode-input-border, var(--vscode-widget-border, transparent)); border-radius: 4px; padding: 6px 8px; }
	textarea:focus { outline: 1px solid var(--vscode-focusBorder); outline-offset: -1px; }
	.hint { font-size: 0.85em; color: var(--vscode-descriptionForeground); }
	[hidden] { display: none !important; }
</style>
</head>
<body>
<div id="status" class="status checking"><span class="dot"></span><span id="status-title">Looking for your Brainstem…</span></div>
<div id="status-detail" class="detail" hidden></div>
<div id="signin-row" class="row start" hidden><button id="open-signin">Sign in</button></div>
<section id="offline" hidden>
	<div id="start-row" class="row start" hidden><button id="start-brainstem">Start my Brainstem</button></div>
	<p id="start-hint"><span id="start-lead">Start it</span> with <code id="start"></code> in a terminal.</p>
	<p id="install-lead">Not installed yet? The grail one-liner for <span id="platform"></span>:</p>
	<pre id="one-liner"></pre>
	<p id="one-liner-note" class="note" hidden></p>
	<div class="row"><button id="copy">Copy the one-liner</button><button id="recheck" class="secondary">Check again</button></div>
</section>
<main id="log" aria-live="polite"></main>
<div class="composer">
	<textarea id="input" placeholder="Talk to your Brainstem" aria-label="Message to your Brainstem"></textarea>
	<div class="row"><button id="send">Send</button><button id="restart" class="secondary" title="Start a new conversation">New conversation</button></div>
	<div class="hint">Enter sends, Shift+Enter adds a line.</div>
</div>
<script nonce="${nonce}">
(function () {
	${cardLayout.toString()}
	const vscode = acquireVsCodeApi();
	const $ = id => document.getElementById(id);
	const log = $('log');
	const input = $('input');
	let busy = false;

	function intro() {
		const p = document.createElement('p');
		p.className = 'intro';
		p.textContent = 'Talk to your Brainstem. It proposes; you decide. Nothing in a Hive changes until you confirm the exact plan in your next message.';
		return p;
	}

	function render(turn) {
		if (log.firstElementChild && log.firstElementChild.classList.contains('intro')) {
			log.firstElementChild.remove();
		}
		const div = document.createElement('div');
		div.className = 'turn ' + turn.role;
		if (turn.role !== 'note') {
			const who = document.createElement('div');
			who.className = 'who';
			who.textContent = turn.role === 'user' ? 'You' : 'Brainstem';
			div.append(who);
		}
		const text = document.createElement('div');
		text.className = 'text';
		text.textContent = turn.text;
		div.append(text);
		if (turn.logs) {
			const details = document.createElement('details');
			const summary = document.createElement('summary');
			summary.textContent = 'What your Brainstem did';
			const pre = document.createElement('pre');
			pre.textContent = turn.logs;
			details.append(summary, pre);
			div.append(details);
		}
		log.append(div);
		log.scrollTop = log.scrollHeight;
	}

	function showStatus(s) {
		const layout = cardLayout(s);
		$('status').className = layout.statusClass;
		$('status-title').textContent = s.title;
		$('status-detail').textContent = s.detail || '';
		$('status-detail').hidden = !s.detail;
		$('signin-row').hidden = !layout.signIn;
		$('offline').hidden = !layout.offline;
		if (layout.offline) {
			$('start-row').hidden = !layout.startRow;
			$('start-brainstem').disabled = !!s.starting;
			$('start-brainstem').textContent = s.starting ? 'Starting your Brainstem…' : 'Start my Brainstem';
			$('start-hint').hidden = !layout.startHint;
			$('start-lead').textContent = s.canStart ? 'Or start it' : 'Start it';
			$('copy').className = s.canStart ? 'secondary' : '';
			$('start').textContent = s.start;
			$('platform').textContent = s.platform;
			$('install-lead').hidden = !layout.install;
			$('one-liner').hidden = !layout.install;
			$('copy').hidden = !layout.install;
			$('one-liner').textContent = s.oneLiner || '';
			$('one-liner-note').textContent = s.note ? (s.oneLiner ? s.note : 'Not installed yet? ' + s.note) : '';
			$('one-liner-note').hidden = !layout.note;
			$('recheck').className = layout.recheckPrimary ? '' : 'secondary';
		}
	}

	function setBusy(on) {
		busy = on;
		$('send').disabled = on;
		$('send').textContent = on ? 'Waiting…' : 'Send';
	}

	function send() {
		const text = input.value.trim();
		if (!text || busy) {
			return;
		}
		input.value = '';
		vscode.postMessage({ type: 'send', text });
	}

	window.addEventListener('message', event => {
		const m = event.data;
		if (m.type === 'status') {
			showStatus(m.status);
		} else if (m.type === 'turn') {
			render(m.turn);
		} else if (m.type === 'busy') {
			setBusy(m.busy);
		} else if (m.type === 'restore') {
			log.replaceChildren(intro());
			m.turns.forEach(render);
			showStatus(m.status);
			setBusy(m.busy);
		}
	});
	$('send').addEventListener('click', send);
	$('copy').addEventListener('click', () => vscode.postMessage({ type: 'copy' }));
	$('recheck').addEventListener('click', () => vscode.postMessage({ type: 'recheck' }));
	$('start-brainstem').addEventListener('click', () => vscode.postMessage({ type: 'start' }));
	$('open-signin').addEventListener('click', () => vscode.postMessage({ type: 'openUI' }));
	$('restart').addEventListener('click', () => vscode.postMessage({ type: 'restart' }));
	input.addEventListener('keydown', event => {
		if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
			event.preventDefault();
			send();
		}
	});
	log.append(intro());
	vscode.postMessage({ type: 'ready' });
}());
</script>
</body>
</html>`;
	}
}
