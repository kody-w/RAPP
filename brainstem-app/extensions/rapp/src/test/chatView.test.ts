// Unit tests for the Brainstem view's /health polling: answers that arrive out of order never let an older one
// replace a newer one, and the offline card says whether nothing answered or something else did. A stand-in
// /health answers when the test says so.
import * as assert from 'assert';
import * as http from 'http';
import type { AddressInfo } from 'net';
import * as path from 'path';
import * as vm from 'vm';
import { describe, test } from 'node:test';

const loader = require('module') as { _resolveFilename: (request: string, ...rest: unknown[]) => string };
const resolveFilename = loader._resolveFilename;
loader._resolveFilename = function (this: unknown, request: string, ...rest: unknown[]): string {
	return request === 'vscode' ? path.join(__dirname, 'vscodeStub.js') : resolveFilename.call(this, request, ...rest);
};

const { BrainstemView, cardLayout, statusTooltip } = require('../chatView') as typeof import('../chatView');
const { failureWords } = require('../brainstem') as typeof import('../brainstem');
const stub = require('./vscodeStub') as typeof import('./vscodeStub');
type Health = import('../brainstem').Health;
type Status = import('../chatView').Status;

describe('Brainstem status', () => {
	test('a slow, older /health answer never replaces a newer one', async () => {
		const answers: ((health: Health) => void)[] = [];
		const view = new BrainstemView(stub.Uri.file(__dirname) as never, () => ({ url: 'http://127.0.0.1:7071', wire: 'grail' }), () => false,
			() => new Promise<Health>(resolve => answers.push(resolve)));
		try {
			const seen: Status[] = [];
			view.onDidChangeStatus(status => void seen.push(status));
			const older = view.poll();
			const newer = view.poll();
			answers[1]({ state: 'connected', agentCount: 10, agentNames: ['Weather'] });
			assert.deepStrictEqual(await newer, { state: 'connected', agentCount: 10, agentNames: ['Weather'] });
			answers[0]({ state: 'connected', agentCount: 9, agentNames: [] });
			assert.deepStrictEqual(await older, { state: 'connected', agentCount: 10, agentNames: ['Weather'] }, 'the late poll returns the newest state too');
			assert.deepStrictEqual(view.currentStatus, { state: 'connected', agentCount: 10, agentNames: ['Weather'] });
			assert.strictEqual(seen.length, 1, 'the stale answer is never announced');
			const next = view.poll();
			answers[2]({ state: 'not-running', reason: 'connect ECONNREFUSED' });
			assert.strictEqual((await next).state, 'not-running', 'a later answer still applies');
		} finally {
			view.dispose();
		}
	});

	test('the offline card says what it found: nothing, or something else on the Brainstem\'s address, with Check again as its one step', async () => {
		const view = new BrainstemView(stub.Uri.file(__dirname) as never, () => ({ url: 'http://127.0.0.1:7071', wire: 'grail' }), () => true,
			async () => ({ state: 'not-running', reason: 'connect ECONNREFUSED' }));
		try {
			const card = (status: Status) => (view as unknown as { describe(s: Status): Record<string, unknown> }).describe(status);
			const nothing = card({ state: 'not-running', reason: 'connect ECONNREFUSED' });
			const other = card({ state: 'not-running', reason: 'something else answers at http://127.0.0.1:7071 (HTTP 404)', occupied: true });
			assert.deepStrictEqual([nothing.title, nothing.detail, nothing.canStart, nothing.occupied], ['Your Brainstem isn\'t running', 'Nothing answered at http://127.0.0.1:7071.', true, undefined]);
			assert.deepStrictEqual([other.title, other.detail, other.canStart, other.occupied],
				['Something else is using your Brainstem\'s address', 'Close the program that answers at http://127.0.0.1:7071, then check again.', false, true], 'starting or installing it cannot help then');
			const busy = card({ state: 'not-running', reason: 'no answer within 5 s', busy: true });
			assert.deepStrictEqual([busy.title, busy.canStart, busy.busy], ['Your Brainstem is busy', false, true], 'it is running: a second copy could only fail');
			const dropped = card({ state: 'not-running', reason: 'socket hang up', dropped: true });
			assert.deepStrictEqual([dropped.title, dropped.detail, dropped.canStart, dropped.dropped],
				['Your Brainstem isn\'t answering', 'It closes the connection without an answer. If you just added an agent, move it out of the top of agents/, then check again.', false, true]);
			// What the page shows for each: the page runs cardLayout itself.
			const shown = (c: Record<string, unknown>) => cardLayout(c as Parameters<typeof cardLayout>[0]);
			assert.deepStrictEqual(shown(nothing), { statusClass: 'status not-running', signIn: false, offline: true, startRow: true, startHint: true, install: !!nothing.oneLiner, note: !!nothing.note, recheckPrimary: false });
			for (const waiting of [other, busy, dropped]) {
				assert.deepStrictEqual(shown(waiting), { statusClass: 'status not-running waiting', signIn: false, offline: true, startRow: false, startHint: false, install: false, note: false, recheckPrimary: true },
					`${String(waiting.title)}: Check again is the one step, with the waiting dot`);
			}
			assert.deepStrictEqual(shown(card({ state: 'connected', version: '0.6.16' })), { statusClass: 'status connected', signIn: false, offline: false, startRow: false, startHint: false, install: false, note: false, recheckPrimary: false });
			assert.deepStrictEqual([card({ state: 'signed-out' }).detail, shown(card({ state: 'signed-out' })).signIn], ['Sign in on its page: the sign-in opens there, or its link is at the top. This updates by itself.', true], 'its one step is the button that opens its page');
			stub.recorded.commands.length = 0;
			await (view as unknown as { onMessage(message: unknown): Promise<void> }).onMessage({ type: 'openUI' });
			assert.deepStrictEqual(stub.recorded.commands, [['rapp.openBrainstemUI']], 'the sign-in button opens the Brainstem\'s own page, where its sign-in is');
			view.setStarting(true);
			assert.deepStrictEqual([card({ state: 'not-running', reason: 'x', occupied: true }).title, card({ state: 'not-running', reason: 'x' }).title, shown(card({ state: 'not-running', reason: 'x', occupied: true })).statusClass],
				['Something else is using your Brainstem\'s address', 'Starting your Brainstem…', 'status not-running waiting'], 'while it starts, another program on its address still says so, as the status bar does, with the yellow dot');
			view.setStarting(false);
		} finally {
			view.dispose();
		}
	});

	test('while something else is using the Brainstem\'s address, the chat sends it nothing, not even the conversation', async () => {
		const seen: string[] = [];
		const other = http.createServer((req, res) => {
			seen.push(`${req.method} ${req.url}`);
			res.statusCode = 404;
			res.setHeader('Content-Type', 'text/html');
			res.end('<html><body>Not Found</body></html>');
		});
		await new Promise<void>(resolve => other.listen(0, '127.0.0.1', resolve));
		const url = `http://127.0.0.1:${(other.address() as AddressInfo).port}`;
		const posted: Record<string, unknown>[] = [];
		const view = new BrainstemView(stub.Uri.file(__dirname) as never, () => ({ url, wire: 'grail' }), () => true);
		try {
			view.resolveWebviewView({
				webview: {
					options: {}, html: '', cspSource: 'vscode-webview:',
					onDidReceiveMessage: () => ({ dispose: () => undefined }),
					postMessage: async (message: Record<string, unknown>) => void posted.push(message),
				},
				onDidChangeVisibility: () => ({ dispose: () => undefined }),
				onDidDispose: () => ({ dispose: () => undefined }),
				visible: true,
			} as never);
			await view.poll();
			await view.ask('What can you do?');
			assert.deepStrictEqual(seen.filter(request => !request.startsWith('GET /health')), [], 'no message went to the other program');
			const turns = posted.filter(message => message.type === 'turn').map(message => message.turn as { role: string; text: string });
			assert.deepStrictEqual(turns.map(turn => turn.role), ['user', 'note']);
			assert.match(turns[1].text, /^Nothing was sent: something else is using your Brainstem's address\. Close that program, then check again\.$/);
		} finally {
			view.dispose();
			await new Promise<void>(resolve => other.close(() => resolve()));
		}
	});

	test('the status bar says each state in the card\'s words', () => {
		assert.deepStrictEqual([
			statusTooltip({ state: 'connected' }),
			statusTooltip({ state: 'signed-out' }),
			statusTooltip({ state: 'checking' }),
			statusTooltip({ state: 'misconfigured', reason: 'x' }),
			statusTooltip({ state: 'not-running', reason: 'x' }),
			statusTooltip({ state: 'not-running', reason: 'x', occupied: true }),
			statusTooltip({ state: 'not-running', reason: 'x', busy: true }),
			statusTooltip({ state: 'not-running', reason: 'x', dropped: true }),
			statusTooltip({ state: 'not-running', reason: 'x' }, true),
		], ['Your Brainstem is running', 'Your Brainstem is not signed in yet', 'Looking for your Brainstem', 'The Brainstem address is not allowed', 'Your Brainstem isn\'t running',
			'Something else is using your Brainstem\'s address', 'Your Brainstem is busy', 'Your Brainstem isn\'t answering', 'Starting your Brainstem…']);
	});


	test('a failed message says why in the Brainstem view\'s words, never as a raw network error', () => {
		const failed = (code: string | undefined, connected: boolean) => failureWords(Object.assign(new Error(code ?? 'x'), { code, connected }));
		assert.deepStrictEqual([
			failed('ECONNREFUSED', false),
			failed('ETIMEDOUT', true),
			failed('HPE_INVALID_CONSTANT', true),
			failed('ECONNRESET', true),
			failureWords(new Error('the answer has no response text')),
		], [
			'it isn\'t running. Start it, then send it again.',
			'it took too long to answer, and may still be doing what you asked. Check before you send it again.',
			'something else is using its address. Close that program, then check again.',
			'it closed the connection without an answer. If you just added an agent, move it out of the top of agents/, then check again.',
			undefined,
		]);
	});


	test('the page\'s own script is whole JavaScript, with the card layout the tests check built into it', () => {
		const view = new BrainstemView(stub.Uri.file(__dirname) as never, () => ({ url: 'http://127.0.0.1:7071', wire: 'grail' }), () => false, async () => ({ state: 'not-running', reason: 'x' }));
		try {
			const page = (view as unknown as { html(webview: unknown): string }).html({ cspSource: 'vscode-webview:' });
			const script = /<script nonce="[^"]+">([\s\S]*?)<\/script>/.exec(page)?.[1] ?? '';
			assert.ok(script.includes(cardLayout.toString()), 'the page runs the very cardLayout these tests check');
			assert.doesNotThrow(() => new vm.Script(script), 'the page script parses');
		} finally {
			view.dispose();
		}
	});


	test('each message goes only on its own check of the very address it goes to: to a Brainstem answering there, signed in, even a slow one', async () => {
		let mode: 'other' | 'brainstem' | 'slow brainstem' | 'slow other' | 'signed out' | 'drops' | 'drops chat' = 'other';
		const seen: string[] = [];
		const handler = (req: http.IncomingMessage, res: http.ServerResponse) => {
			let body = '';
			req.on('data', chunk => body += chunk);
			req.on('end', () => {
				seen.push(`${mode}|${req.method} ${req.url} ${body}`);
				const json = (value: unknown, status = 200) => {
					res.statusCode = status;
					res.setHeader('Content-Type', 'application/json');
					res.end(JSON.stringify(value));
				};
				const brainstem = () => req.url === '/health' ? json({ status: 'ok', version: '0.6.16', agents: [] }) : json({ response: 'Hello.', agent_logs: [], session_id: 's1' });
				if (mode === 'brainstem') {
					brainstem();
				} else if (mode === 'slow brainstem') {
					setTimeout(brainstem, req.url === '/health' ? 800 : 0);
				} else if (mode === 'slow other') {
					setTimeout(() => res.end('<html>slow</html>'), 3000);
				} else if (mode === 'signed out') {
					req.url === '/health' ? json({ status: 'unauthenticated', version: '0.6.9', agents: [] }) : json({ error: 'Not authenticated. Visit /login in your browser to sign in with GitHub.' }, 500);
				} else if (mode === 'drops') {
					req.socket.destroy();
				} else if (mode === 'drops chat') {
					req.url === '/health' ? brainstem() : req.socket.destroy();
				} else {
					res.statusCode = 404;
					res.end('<html>Not Found</html>');
				}
			});
		};
		const server = http.createServer(handler);
		const elsewhere = http.createServer(handler);
		await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve));
		await new Promise<void>(resolve => elsewhere.listen(0, '127.0.0.1', resolve));
		const at = (s: http.Server) => `http://127.0.0.1:${(s.address() as AddressInfo).port}`;
		const port = (server.address() as AddressInfo).port;
		let url = at(server);
		const posted: Record<string, unknown>[] = [];
		// The view's own checks wait 300 ms here, a message's own check 2 s (60 s in the app).
		const check = (endpoint: import('../brainstem').Endpoint, timeoutMs?: number) => require('../brainstem').health(endpoint, timeoutMs === undefined ? 300 : 2000) as Promise<Health>;
		const view = new BrainstemView(stub.Uri.file(__dirname) as never, () => ({ url, wire: 'grail' }), () => true, check);
		const replies = () => posted.filter(m => m.type === 'turn').map(m => m.turn as { role: string; text: string }).filter(t => t.role !== 'user').map(t => t.text);
		const sent = (word: string) => seen.filter(r => r.includes('|POST /chat') && r.includes(word)).map(r => r.split('|')[0]);
		const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));
		try {
			view.resolveWebviewView({
				webview: { options: {}, html: '', cspSource: 'vscode-webview:', onDidReceiveMessage: () => ({ dispose: () => undefined }), postMessage: async (message: Record<string, unknown>) => void posted.push(message) },
				onDidChangeVisibility: () => ({ dispose: () => undefined }),
				onDidDispose: () => ({ dispose: () => undefined }),
				visible: true,
			} as never);
			await view.ask('Alpha');
			assert.deepStrictEqual([sent('Alpha'), replies()[0]], [[], 'Nothing was sent: something else is using your Brainstem\'s address. Close that program, then check again.']);
			mode = 'brainstem';
			await view.ask('Bravo');
			assert.deepStrictEqual([sent('Bravo'), replies()[1]], [['brainstem'], 'Hello.']);
			mode = 'slow brainstem';
			await view.poll();
			assert.strictEqual((view.currentStatus as { busy?: boolean }).busy, true, 'too slow for the view\'s own check');
			await view.ask('Charlie');
			assert.deepStrictEqual([sent('Charlie'), replies()[2]], [['slow brainstem'], 'Hello.'], 'a message\'s own check waits: a slow Brainstem gets it');
			mode = 'slow other';
			await view.ask('Delta');
			assert.deepStrictEqual([sent('Delta'), replies()[3]], [[], 'Nothing was sent: your Brainstem did not answer within a minute. Send it again in a moment.'], 'no answer at all: nothing goes');
			mode = 'slow brainstem';
			const echo = view.ask('Echo');
			await sleep(50);
			await view.poll();
			await echo;
			assert.deepStrictEqual([sent('Echo'), replies()[4]], [['slow brainstem'], 'Hello.'], 'another check that ends first, and says busy, never decides for this message');
			mode = 'signed out';
			await view.ask('Foxtrot');
			assert.deepStrictEqual([sent('Foxtrot'), replies()[5]], [[], 'Nothing was sent: your Brainstem is not signed in yet. Sign in on its page, then send it again.']);
			mode = 'drops';
			await view.ask('Golf');
			assert.deepStrictEqual([sent('Golf'), replies()[6]], [[], 'Nothing was sent: your Brainstem isn\'t answering. If you just added an agent, move it out of the top of agents/, then check again.']);
			mode = 'drops chat';
			await view.ask('Golf two');
			assert.strictEqual(replies()[7], 'Your Brainstem could not answer: it closed the connection without an answer. If you just added an agent, move it out of the top of agents/, then check again.',
				'checked, sent, then failed: said in the view\'s words');
			mode = 'slow brainstem';
			const hotel = view.ask('Hotel');
			await sleep(50);
			url = at(elsewhere);
			await hotel;
			assert.deepStrictEqual([sent('Hotel'), replies()[8]], [[], 'Nothing was sent: your Brainstem\'s address or its chat setting changed while it was checked. Send it again.'], 'never to the address it checked before the setting changed');
			url = at(server);
			await new Promise<void>(resolve => server.close(() => resolve()));
			await view.ask('India');
			view.setStarting(true);
			await view.ask('Juliett');
			view.setStarting(false);
			assert.deepStrictEqual([replies()[9], replies()[10]], ['Nothing was sent: your Brainstem isn\'t running. Start it, then send it again.', 'Nothing was sent: your Brainstem is still starting. Send it again once it is running.']);
			server.listen(port, '127.0.0.1');
			await new Promise<void>(resolve => server.once('listening', () => resolve()));
			mode = 'slow brainstem';
			const kilo = view.ask('Kilo: my dentist is on Tuesday');
			await sleep(50);
			await (view as unknown as { onMessage(message: unknown): Promise<void> }).onMessage({ type: 'restart' });
			await kilo;
			assert.deepStrictEqual(sent('dentist'), [], 'a message whose conversation was cleared while it checked is not sent');
		} finally {
			view.dispose();
			await new Promise<void>(resolve => server.close(() => resolve()));
			await new Promise<void>(resolve => elsewhere.close(() => resolve()));
		}
	});

	test('what was said is only what was sent: a message that was not sent never goes later as history, and a conversation stays with its address and wire', async () => {
		let mode: 'signed out' | 'brainstem' | 'slow brainstem' = 'signed out';
		const bodies: { at: string; body: Record<string, unknown> }[] = [];
		const handler = (name: string) => (req: http.IncomingMessage, res: http.ServerResponse) => {
			let body = '';
			req.on('data', chunk => body += chunk);
			req.on('end', () => {
				if (req.url === '/chat') {
					bodies.push({ at: name, body: JSON.parse(body) as Record<string, unknown> });
				}
				const json = (value: unknown) => {
					res.setHeader('Content-Type', 'application/json');
					res.end(JSON.stringify(value));
				};
				if (req.url === '/health') {
					setTimeout(() => json({ status: mode === 'signed out' ? 'unauthenticated' : 'ok', version: '0.6.16', agents: [] }), mode === 'slow brainstem' ? 3000 : 0);
				} else {
					json({ response: `Hello from ${name}.`, agent_logs: [], session_id: `${name}-session` });
				}
			});
		};
		const first = http.createServer(handler('first'));
		const second = http.createServer(handler('second'));
		await new Promise<void>(resolve => first.listen(0, '127.0.0.1', resolve));
		await new Promise<void>(resolve => second.listen(0, '127.0.0.1', resolve));
		const at = (s: http.Server) => `http://127.0.0.1:${(s.address() as AddressInfo).port}`;
		let url = at(first);
		let wire: 'grail' | 'rapp1' = 'grail';
		const posted: Record<string, unknown>[] = [];
		const check = (endpoint: import('../brainstem').Endpoint, timeoutMs?: number, signal?: AbortSignal) => require('../brainstem').health(endpoint, timeoutMs === undefined ? 300 : 5000, { signal }) as Promise<Health>;
		const view = new BrainstemView(stub.Uri.file(__dirname) as never, () => ({ url, wire }), () => true, check);
		const notes = () => posted.filter(m => m.type === 'turn').map(m => m.turn as { role: string; text: string }).filter(t => t.role === 'note').map(t => t.text);
		try {
			view.resolveWebviewView({
				webview: { options: {}, html: '', cspSource: 'vscode-webview:', onDidReceiveMessage: () => ({ dispose: () => undefined }), postMessage: async (message: Record<string, unknown>) => void posted.push(message) },
				onDidChangeVisibility: () => ({ dispose: () => undefined }),
				onDidDispose: () => ({ dispose: () => undefined }),
				visible: true,
			} as never);
			await view.ask('Forget everything about my dentist');
			assert.match(notes()[0], /^Nothing was sent: your Brainstem is not signed in yet/);
			mode = 'brainstem';
			await view.ask('Bravo');
			await view.ask('Charlie');
			assert.deepStrictEqual(bodies.map(b => [b.at, b.body.user_input, b.body.conversation_history, b.body.session_id]), [
				['first', 'Bravo', undefined, undefined],
				['first', 'Charlie', [{ role: 'user', content: 'Bravo' }, { role: 'assistant', content: 'Hello from first.' }], 'first-session'],
			], 'the unsent message never goes, not even as history; what was sent, and its reply, does');
			url = at(second);
			await view.ask('Delta');
			assert.deepStrictEqual([bodies[2].at, bodies[2].body.conversation_history, bodies[2].body.session_id], ['second', undefined, undefined], 'another Brainstem gets a new conversation: none of the first one\'s session or words');
			assert.strictEqual(notes()[1], 'A new conversation began here: your Brainstem\'s address or its chat setting changed.');
			wire = 'rapp1';
			await view.ask('Echo');
			assert.deepStrictEqual([bodies[3].body.session_id, Object.keys(bodies[3].body).sort()], [undefined, ['user_input']], 'the RAPP/1 wire starts afresh too');
			wire = 'grail';
			url = at(first);
			mode = 'slow brainstem';
			const pending = view.ask('Foxtrot');
			await new Promise(resolve => setTimeout(resolve, 100));
			const pressed = Date.now();
			await (view as unknown as { onMessage(message: unknown): Promise<void> }).onMessage({ type: 'restart' });
			await pending;
			const freed = posted.slice().reverse().find(m => m.type === 'busy');
			assert.deepStrictEqual([freed?.busy, Date.now() - pressed < 1500, bodies.some(b => b.body.user_input === 'Foxtrot')], [false, true, false],
				'New conversation lets go of a message still being checked at once: the view is free, and the message never goes');
			assert.strictEqual(view.currentStatus.state, 'connected', 'a check let go of says nothing about the Brainstem: the view still shows the last real answer');
			const fresh = posted.slice(posted.map(m => m.type).lastIndexOf('restore') + 1);
			assert.deepStrictEqual(fresh.filter(m => m.type === 'turn'), [], 'and the new conversation starts empty: no note about the message let go of');
		} finally {
			view.dispose();
			await new Promise<void>(resolve => first.close(() => resolve()));
			await new Promise<void>(resolve => second.close(() => resolve()));
		}
	});

	test('New conversation during a send lets go at once, and says the last message may still be carried out; a wire switched while it is checked, a send refused, a reply in another shape', async () => {
		let mode: 'brainstem' | 'slow chat' | 'slow health' | 'stops after health' | 'grail shape' = 'brainstem';
		const bodies: Record<string, unknown>[] = [];
		const server = http.createServer((req, res) => {
			let body = '';
			req.on('data', chunk => body += chunk);
			req.on('end', () => {
				const json = (value: unknown, delay = 0) => setTimeout(() => {
					res.setHeader('Content-Type', 'application/json');
					res.end(JSON.stringify(value));
				}, delay);
				if (req.url === '/health') {
					json({ status: 'ok', version: '0.6.16', agents: [] }, mode === 'slow health' ? 1500 : 0);
					if (mode === 'stops after health') {
						res.once('finish', () => server.close());
					}
					return;
				}
				bodies.push(JSON.parse(body) as Record<string, unknown>);
				json(mode === 'grail shape' ? { response: 'Done.', agent_logs: [], session_id: 's9', model: 'm' } : { response: 'Hello.', agent_logs: [], session_id: 's1' }, mode === 'slow chat' ? 1500 : 0);
			});
		});
		await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve));
		const port = (server.address() as AddressInfo).port;
		let wire: 'grail' | 'rapp1' = 'grail';
		const posted: Record<string, unknown>[] = [];
		const check = (endpoint: import('../brainstem').Endpoint, timeoutMs?: number, signal?: AbortSignal) => require('../brainstem').health(endpoint, timeoutMs === undefined ? 300 : 5000, { signal }) as Promise<Health>;
		const view = new BrainstemView(stub.Uri.file(__dirname) as never, () => ({ url: `http://127.0.0.1:${port}`, wire }), () => true, check);
		const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));
		const lastRestore = () => posted.map(m => m.type).lastIndexOf('restore');
		const turnsSince = (index: number) => posted.slice(index + 1).filter(m => m.type === 'turn').map(m => (m.turn as { role: string; text: string }));
		try {
			view.resolveWebviewView({
				webview: { options: {}, html: '', cspSource: 'vscode-webview:', onDidReceiveMessage: () => ({ dispose: () => undefined }), postMessage: async (message: Record<string, unknown>) => void posted.push(message) },
				onDidChangeVisibility: () => ({ dispose: () => undefined }),
				onDidDispose: () => ({ dispose: () => undefined }),
				visible: true,
			} as never);
			mode = 'slow chat';
			const sending = view.ask('Email the team the plan');
			await sleep(300);
			assert.strictEqual(bodies.length, 1, 'it was sent');
			const pressed = Date.now();
			await (view as unknown as { onMessage(message: unknown): Promise<void> }).onMessage({ type: 'restart' });
			await sending;
			const freed = posted.slice().reverse().find(m => m.type === 'busy');
			assert.deepStrictEqual([freed?.busy, Date.now() - pressed < 1000], [false, true], 'the view is free at once');
			await sleep(1500);
			assert.deepStrictEqual(turnsSince(lastRestore()), [{ role: 'note', text: 'Your last message was already sent: your Brainstem may still carry it out. Check before you send it again.' }],
				'the new conversation says the last message may still be carried out, and no reply to it ever lands there');
			mode = 'slow health';
			const switched = view.ask('Delta');
			await sleep(300);
			wire = 'rapp1';
			await switched;
			assert.deepStrictEqual([bodies.length, turnsSince(lastRestore()).pop()?.text], [1, 'Nothing was sent: your Brainstem\'s address or its chat setting changed while it was checked. Send it again.'], 'a wire switched while it is checked: nothing goes');
			wire = 'grail';
			mode = 'stops after health';
			await view.ask('Delete the notes about my dentist');
			assert.strictEqual(turnsSince(lastRestore()).pop()?.text, 'Your Brainstem could not answer: it isn\'t running. Start it, then send it again.');
			server.listen(port, '127.0.0.1');
			await new Promise<void>(resolve => server.once('listening', () => resolve()));
			mode = 'brainstem';
			await view.ask('Hi again');
			assert.ok(!JSON.stringify(bodies[bodies.length - 1].conversation_history ?? []).includes('dentist'), 'a send refused before it reached the Brainstem is not what was said');
			wire = 'rapp1';
			mode = 'grail shape';
			await view.ask('Golf');
			assert.strictEqual(turnsSince(lastRestore()).pop()?.text,
				'Your Brainstem answered in a shape the setting rapp.chat.wire (rapp1: the exact RAPP/1 section 8 reply) does not accept, and may have done what you asked. Check before you send it again.');
		} finally {
			view.dispose();
			await new Promise<void>(resolve => server.close(() => resolve()));
		}
	});
});
