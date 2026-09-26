// A thin client for the Brainstem on this device: GET /health and POST /chat, loopback only.
import * as http from 'http';

export type Wire = 'grail' | 'rapp1';

export interface Endpoint {
	readonly host: string;
	readonly port: number;
	readonly url: string;
}

export interface Turn {
	readonly role: 'user' | 'assistant';
	readonly content: string;
}

export interface Reply {
	readonly response: string;
	readonly agentLogs: string;
	readonly sessionId?: string;
}

type Answered = { readonly version?: string; readonly brainstemDir?: string; readonly agentCount?: number; readonly agentNames?: readonly string[] };

export type Health =
	| ({ readonly state: 'connected' } & Answered)
	| ({ readonly state: 'signed-out' } & Answered)
	// `occupied`: something answered at the address, but not as a Brainstem does; `busy`: something listens there
	// but gave no answer in time; `dropped`: something listens there but closes the connection without an answer
	// (see health()).
	| { readonly state: 'not-running'; readonly reason: string; readonly occupied?: boolean; readonly busy?: boolean; readonly dropped?: boolean };

export interface HealthFacts {
	readonly signedOut: boolean;
	readonly version?: string;
	readonly brainstemDir?: string;
	/** How many agents it has loaded right now. */
	readonly agentCount?: number;
	/** Their names, only to tell whether an agent file's agent is among them; never shown or logged. */
	readonly agentNames?: readonly string[];
}

const LOOPBACK = new Set(['127.0.0.1', 'localhost', '[::1]']);
const MAX_BODY = 5 * 1024 * 1024;
// The grail loads every agent to answer /health, which takes a second or two with ten agents.
const HEALTH_TIMEOUT_MS = 5000;

// The Brainstem address, or why it is refused. Only this device is ever contacted.
export function parseEndpoint(raw: string): Endpoint | string {
	let url: URL;
	try {
		url = new URL(raw);
	} catch {
		return `"${raw}" is not an address`;
	}
	if (url.protocol !== 'http:') {
		return 'the Brainstem address must start with http://';
	}
	if (!LOOPBACK.has(url.hostname)) {
		return 'the Brainstem must be on this device (127.0.0.1, localhost or [::1])';
	}
	if (url.username || url.password || (url.pathname !== '/' && url.pathname !== '') || url.search || url.hash) {
		return 'give only the Brainstem\'s host and port, for example http://127.0.0.1:7071';
	}
	const host = url.hostname === 'localhost' ? '127.0.0.1' : url.hostname === '[::1]' ? '::1' : url.hostname;
	return { host, port: Number(url.port || 80), url: `http://${url.host}` };
}

// A failed request says whether this device's connection to the address was made first (`connected`: something
// listens there) and, when no answer came in time, has the code ETIMEDOUT.
type RequestFailure = Error & { code?: string; connected?: boolean };

function request(ep: Endpoint, method: 'GET' | 'POST', path: string, body: unknown, timeoutMs: number, signal?: AbortSignal): Promise<{ status: number; json: unknown }> {
	return new Promise((resolve, reject) => {
		const data = body === undefined ? undefined : Buffer.from(JSON.stringify(body), 'utf8');
		let connected = false;
		const fail = (error: RequestFailure) => reject(Object.assign(error, { connected }));
		// A connection of its own each time (no socket kept from an earlier request), so how one ends says
		// something about what listens there now.
		const req = http.request({
			host: ep.host,
			port: ep.port,
			path,
			method,
			agent: false,
			timeout: timeoutMs,
			signal,
			headers: data ? { 'Content-Type': 'application/json', 'Content-Length': data.length } : {},
		}, res => {
			const chunks: Buffer[] = [];
			let size = 0;
			res.on('data', (chunk: Buffer) => {
				size += chunk.length;
				if (size > MAX_BODY) {
					req.destroy(Object.assign(new Error('the Brainstem sent more than 5 MB'), { code: 'ETOOBIG' }));
					return;
				}
				chunks.push(chunk);
			});
			res.on('end', () => {
				const text = Buffer.concat(chunks).toString('utf8');
				let json: unknown = undefined;
				try {
					json = text ? JSON.parse(text) : undefined;
				} catch {
					json = undefined;
				}
				resolve({ status: res.statusCode ?? 0, json });
			});
			res.on('error', fail);
		});
		req.on('socket', socket => socket.once('connect', () => { connected = true; }));
		req.on('timeout', () => req.destroy(Object.assign(new Error(`no answer within ${Math.round(timeoutMs / 1000)} s`), { code: 'ETIMEDOUT' })));
		req.on('error', fail);
		if (data) {
			req.write(data);
		}
		req.end();
	});
}

const isRecord = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v);

// What the app takes from /health: the version, the folder the Brainstem runs from, the agents it has
// loaded, and whether it still needs its sign-in. No other field is read, kept, shown or logged; /health also
// carries account names. Of the loaded agents (brainstem.py health(): list(agents.keys()), each agent's name)
// the app shows only how many there are, and uses their names only to tell an agent card whether its agent
// is among them.
export function parseHealth(json: unknown): HealthFacts {
	const body = isRecord(json) ? json : {};
	const agents = Array.isArray(body.agents) ? body.agents : undefined;
	return {
		signedOut: body.status === 'unauthenticated',
		...(typeof body.version === 'string' ? { version: body.version } : {}),
		...(typeof body.brainstem_dir === 'string' ? { brainstemDir: body.brainstem_dir } : {}),
		...(agents ? { agentCount: agents.length, agentNames: agents.filter((n): n is string => typeof n === 'string' && n.length <= 200).slice(0, 5000) } : {}),
	};
}

// A Brainstem answers /health with HTTP 200 and a JSON object: the grail's own (its status "ok", or
// "unauthenticated" before its sign-in) and a RAPP/1 section 8 endpoint's alike. The grail loads every agent to
// answer (and installs what a new one needs), so an answer can take seconds: a connection made but not answered
// in time is a busy Brainstem, not a missing one. An answer that is not a Brainstem's (a 404 page, a web app's
// HTML, bytes that are not HTTP at all) is some other program on the address. A connection closed without any
// answer is asked once more: a Brainstem that is stopping closes the connections it has, and is then gone
// (refused); one that keeps closing them is not answering (an agent that stops its loading can do that). Only a
// refused connection means nothing is there.
export async function health(ep: Endpoint, timeoutMs = HEALTH_TIMEOUT_MS, options: { readonly again?: boolean; readonly signal?: AbortSignal } = {}): Promise<Health> {
	const { again = true, signal } = options;
	let reply: { status: number; json: unknown };
	try {
		reply = await request(ep, 'GET', '/health', undefined, timeoutMs, signal);
	} catch (error) {
		const failure = error as RequestFailure;
		const reason = error instanceof Error ? error.message : String(error);
		if (!failure.connected) {
			return { state: 'not-running', reason };
		}
		if (failure.code === 'ETIMEDOUT') {
			return { state: 'not-running', reason, busy: true };
		}
		if (failure.code?.startsWith('HPE_') || failure.code === 'ETOOBIG') {
			return { state: 'not-running', reason, occupied: true };
		}
		const next = again && !signal?.aborted ? await health(ep, timeoutMs, { again: false, signal }) : undefined;
		return next && !(next.state === 'not-running' && next.dropped) ? next : { state: 'not-running', reason, dropped: true };
	}
	if (reply.status !== 200 || !isRecord(reply.json)) {
		return { state: 'not-running', reason: `something else answers at ${ep.url} (HTTP ${reply.status})`, occupied: true };
	}
	const { signedOut, ...facts } = parseHealth(reply.json);
	return { state: signedOut ? 'signed-out' : 'connected', ...facts };
}

// The request body. `grail` is the local Brainstem's own /chat, which takes the conversation so far so a
// Hive proposal can be confirmed in the next message; `rapp1` is exactly RAPP/1 section 8.
export function chatBody(wire: Wire, userInput: string, sessionId: string | undefined, history: readonly Turn[]): Record<string, unknown> {
	const body: Record<string, unknown> = { user_input: userInput };
	if (sessionId) {
		body.session_id = sessionId;
	}
	if (wire === 'grail' && history.length) {
		body.conversation_history = history.map(turn => ({ role: turn.role, content: turn.content }));
	}
	return body;
}

function logsText(logs: unknown): string {
	if (typeof logs === 'string') {
		return logs;
	}
	return Array.isArray(logs) ? logs.filter(line => typeof line === 'string').join('\n') : '';
}

/** A request's own failure (not the Brainstem's answer) in plain words, in the Brainstem view's terms. */
export function failureWords(error: unknown): string | undefined {
	const failure = error as RequestFailure;
	if (!(error instanceof Error) || failure.connected === undefined) {
		return undefined;
	}
	if (!failure.connected) {
		return 'it isn\'t running. Start it, then send it again.';
	}
	if (failure.code === 'ETIMEDOUT') {
		return 'it took too long to answer, and may still be doing what you asked. Check before you send it again.';
	}
	if (failure.code?.startsWith('HPE_') || failure.code === 'ETOOBIG') {
		return 'something else is using its address. Close that program, then check again.';
	}
	return 'it closed the connection without an answer. If you just added an agent, move it out of the top of agents/, then check again.';
}

// The grail's own error, in plain words. Its "no Copilot access" error carries the account's name, which is never
// shown.
function grailError(json: Record<string, unknown>): string | undefined {
	const error = json.error;
	if (json.no_copilot_access === true || (typeof error === 'string' && error.startsWith('NO_COPILOT_ACCESS'))) {
		return 'the GitHub account it is signed in with has no Copilot access; sign it in with an account that has';
	}
	if (typeof error === 'string' && /^Not authenticated\b/.test(error)) {
		return 'it is not signed in yet. Sign in on its page, then send it again';
	}
	return typeof error === 'string' && error.trim() ? error : undefined;
}

export function parseReply(wire: Wire, status: number, json: unknown): Reply {
	if (!isRecord(json)) {
		throw new Error(`the answer at its address (HTTP ${status}) was not a Brainstem's`);
	}
	if (status === 200) {
		if (wire === 'rapp1') {
			const keys = Object.keys(json).sort().join(',');
			if (keys !== 'agent_logs,response,session_id' || typeof json.response !== 'string'
				|| !Array.isArray(json.agent_logs) || typeof json.session_id !== 'string') {
				// It answered: the note says so, without "could not answer".
				throw Object.assign(new Error('answered in a shape the setting rapp.chat.wire (rapp1: the exact RAPP/1 section 8 reply) does not accept, and may have done what you asked. Check before you send it again.'), { answered: true });
			}
		} else if (typeof json.response !== 'string') {
			throw new Error(grailError(json) ?? 'the answer has no response text');
		}
		return {
			response: json.response as string,
			agentLogs: logsText(json.agent_logs),
			sessionId: typeof json.session_id === 'string' ? json.session_id : undefined,
		};
	}
	const error = json.error;
	if (isRecord(error) && typeof error.code === 'string') {
		throw new Error(`the Brainstem refused (${error.code}${typeof error.step === 'string' ? ` at ${error.step}` : ''})`);
	}
	throw new Error(grailError(json) ?? `the Brainstem answered HTTP ${status}`);
}

export async function chat(ep: Endpoint, wire: Wire, userInput: string, sessionId: string | undefined, history: readonly Turn[], timeoutMs = 180000, signal?: AbortSignal): Promise<Reply> {
	const reply = await request(ep, 'POST', '/chat', chatBody(wire, userInput, sessionId, history), timeoutMs, signal);
	return parseReply(wire, reply.status, reply.json);
}
