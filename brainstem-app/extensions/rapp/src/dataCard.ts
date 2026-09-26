// The Brainstem's own data, shown for a person: what it remembers (shared_memories/memory.json and each user's
// memory/<guid>/user_memory.json, as its local_storage.py keeps them) and the agent collections its
// rar_collections agent puts together from RAR (rar_collections/collections.json). Read with JSON.parse only,
// shown read-only; every string from a file is untrusted and escaped where it is written into the page. Pure: no
// vscode API, no files.
import { CARD_STYLE } from './agentCard';
import { escapeHtml } from './html';
import { DATA_FOLDER } from './startup';

export type DataFile =
	| { readonly kind: 'shared' }
	| { readonly kind: 'user'; readonly user: string }
	| { readonly kind: 'memory' }
	| { readonly kind: 'collections' };

/** What a file is, from where it sits under a Brainstem's data folder; undefined for anything else. */
export function dataFile(file: string): DataFile | undefined {
	const parts = file.split(/[\\/]+/);
	const at = parts.lastIndexOf(DATA_FOLDER);
	if (at < 0) {
		return undefined;
	}
	const rel = parts.slice(at + 1);
	const name = rel[rel.length - 1];
	if (rel.length === 2 && rel[0] === 'shared_memories' && name === 'memory.json') {
		return { kind: 'shared' };
	}
	if (rel.length === 3 && rel[0] === 'memory' && (name === 'user_memory.json' || name === 'memory.json')) {
		return { kind: 'user', user: rel[1] };
	}
	if (rel.length >= 1 && (name === 'memory.json' || name === 'user_memory.json')) {
		return { kind: 'memory' };
	}
	if (rel.length === 2 && rel[0] === 'rar_collections' && name === 'collections.json') {
		return { kind: 'collections' };
	}
	return undefined;
}

type Loose = Record<string, unknown>;
const isRecord = (v: unknown): v is Loose => typeof v === 'object' && v !== null && !Array.isArray(v);
const text = (v: unknown): string | undefined => (typeof v === 'string' && v.trim() ? v.trim() : undefined);
const MAX_TEXT = 5000;
const clip = (s: string, max = MAX_TEXT) => (s.length <= max ? s : s.slice(0, max - 1) + '…');

/**
 * Where JSON text stops being JSON, in words: a small strict scan, so the card can say "Line 4, column 1" for
 * every kind of mistake (the engine's own message gives no place for some, and quotes the file for others).
 */
export function jsonStop(source: string): { readonly line: number; readonly column: number; readonly what: string } | undefined {
	let i = 0;
	const fail = (what: string): never => {
		throw { at: i, what };
	};
	const space = () => {
		while (i < source.length && ' \t\n\r'.includes(source[i])) {
			i++;
		}
	};
	const string = () => {
		const start = i;
		for (i++; ; i++) {
			if (i >= source.length) {
				i = start;
				fail('text that never ends');
			}
			const c = source.charCodeAt(i);
			if (c === 0x22) {
				i++;
				return;
			}
			if (c < 0x20) {
				fail('a line break or control character inside text');
			}
			if (c === 0x5c) {
				i++;
				if (source[i] === 'u' ? !/^[0-9a-fA-F]{4}$/.test(source.slice(i + 1, i + 5)) : !'"\\/bfnrt'.includes(source[i] ?? 'x')) {
					fail('a broken escape inside text');
				}
				if (source[i] === 'u') {
					i += 4;
				}
			}
		}
	};
	const value = (depth: number): void => {
		if (depth > 512) {
			fail('nested too deeply');
		}
		space();
		const c = source[i];
		if (c === '{' || c === '[') {
			const close = c === '{' ? '}' : ']';
			i++;
			space();
			if (source[i] === close) {
				i++;
				return;
			}
			for (;;) {
				if (c === '{') {
					space();
					if (source[i] !== '"') {
						fail('expected a quoted name');
					}
					string();
					space();
					if (source[i] !== ':') {
						fail('expected \':\'');
					}
					i++;
				}
				value(depth + 1);
				space();
				if (source[i] === ',') {
					i++;
					continue;
				}
				if (source[i] === close) {
					i++;
					return;
				}
				fail(i >= source.length ? 'the file ends too soon' : `expected ',' or '${close}'`);
			}
		}
		if (c === '"') {
			return string();
		}
		const number = /-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/y;
		number.lastIndex = i;
		if (c === '-' || (c >= '0' && c <= '9')) {
			if (!number.test(source)) {
				fail('a malformed number');
			}
			i = number.lastIndex;
			return;
		}
		for (const word of ['true', 'false', 'null']) {
			if (source.startsWith(word, i)) {
				i += word.length;
				return;
			}
		}
		fail(i >= source.length ? 'the file ends too soon' : 'expected a value');
	};
	try {
		value(0);
		space();
		if (i < source.length) {
			fail('more after the end');
		}
		return undefined;
	} catch (stop) {
		if (typeof stop !== 'object' || stop === null || !('at' in stop)) {
			throw stop;
		}
		const { at, what } = stop as { at: number; what: string };
		const before = source.slice(0, at);
		return { line: before.split('\n').length, column: at - before.lastIndexOf('\n'), what };
	}
}

/** JSON.parse, with where it stopped in words when the text is not JSON. Blank text reads as nothing. */
export function readJson(source: string): { readonly value: unknown } | { readonly problem: string } {
	if (!source.trim()) {
		return { value: undefined };
	}
	try {
		return { value: JSON.parse(source) };
	} catch {
		const stop = jsonStop(source);
		return { problem: stop ? `Line ${stop.line}, column ${stop.column}: ${stop.what}.` : 'It isn’t valid JSON.' };
	}
}

// ── What it remembers ─────────────────────────────────────────────────────────────────────────────────────

export interface Memory {
	readonly id: string;
	readonly text: string;
	readonly theme?: string;
	readonly mood?: string;
	readonly tags: readonly string[];
	readonly importance?: number;
	/** The date and time as the file gives them, for showing. */
	readonly when?: string;
	/** The same as a time, for sorting; absent when the file gives none that reads. */
	readonly at?: number;
}

export type MemoryReading = { readonly memories: readonly Memory[] } | { readonly problem: string };

const TEXT_KEYS = ['message', 'content', 'text', 'memory', 'note', 'summary'];
const pad = (n: number) => String(n).padStart(2, '0');

// A timestamp shown the way dates and times are: its date and time on this device, to the minute.
function shownStamp(stamp: string, at: number): string {
	if (!Number.isFinite(at) || !/^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}/.test(stamp)) {
		return clip(stamp, 100);
	}
	const d = new Date(at);
	return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function memoryOf(id: string, entry: unknown): Memory {
	if (!isRecord(entry)) {
		return { id, text: typeof entry === 'string' ? clip(entry) : entry === null || entry === undefined ? '(empty)' : clip(JSON.stringify(entry)), tags: [] };
	}
	const said = TEXT_KEYS.map(key => text(entry[key])).find(Boolean);
	const rawTags = entry.tags;
	const tags = Array.isArray(rawTags) ? rawTags.filter((t): t is string => typeof t === 'string' && !!t.trim()) : typeof rawTags === 'string' ? rawTags.split(',') : [];
	const importance = typeof entry.importance === 'number' ? entry.importance : typeof entry.importance === 'string' && entry.importance.trim() ? Number(entry.importance) : NaN;
	const date = text(entry.date);
	const time = text(entry.time);
	const stamp = text(entry.timestamp) ?? text(entry.created_at);
	let at = NaN;
	if (date && /^\d{4}-\d{2}-\d{2}$/.test(date)) {
		at = Date.parse(time && /^\d{2}:\d{2}(:\d{2})?$/.test(time) ? `${date}T${time}` : `${date}T00:00:00`);
	} else if (stamp) {
		at = Date.parse(stamp);
	}
	const shownTime = time && /^\d{2}:\d{2}/.test(time) ? time.slice(0, 5) : time;
	return {
		id,
		text: clip(said ?? '(no text)'),
		theme: text(entry.theme) ? clip(text(entry.theme) as string, 200) : undefined,
		mood: text(entry.mood) ? clip(text(entry.mood) as string, 200) : undefined,
		tags: tags.map(t => clip(t.trim(), 100)).filter(Boolean).slice(0, 20),
		importance: Number.isFinite(importance) ? Math.max(0, Math.min(10, Math.round(importance))) : undefined,
		when: date || shownTime ? clip([date, shownTime].filter(Boolean).join(' '), 100) : stamp ? shownStamp(stamp, at) : undefined,
		at: Number.isFinite(at) ? at : undefined,
	};
}

/**
 * The memories in a memory file, newest first: a dict of id to entry (what the Brainstem writes) or a list of
 * entries. Missing fields are left out; memories with no date keep their order, after the dated ones.
 */
export function readMemories(source: string): MemoryReading {
	const read = readJson(source);
	if ('problem' in read) {
		return read;
	}
	const value = read.value;
	let entries: [string, unknown][];
	if (value === undefined || value === null) {
		entries = [];
	} else if (Array.isArray(value)) {
		entries = value.map((entry, i) => [isRecord(entry) && typeof entry.id === 'string' ? entry.id : String(i), entry]);
	} else if (isRecord(value)) {
		entries = Object.entries(value);
	} else {
		return { problem: 'It holds a single value, not a set of memories.' };
	}
	// All of them, then sorted: the Brainstem adds each new memory at the end, so no cap may come first.
	const memories = entries.map(([id, entry]) => memoryOf(id, entry));
	const dated = memories.filter(m => m.at !== undefined).sort((a, b) => (b.at as number) - (a.at as number));
	return { memories: [...dated, ...memories.filter(m => m.at === undefined)] };
}

// ── Agent collections ─────────────────────────────────────────────────────────────────────────────────────

export interface Collection {
	readonly name: string;
	readonly task?: string;
	readonly created?: string;
	readonly agents: readonly { readonly name: string; readonly publisher?: string }[];
}

export type CollectionsReading = { readonly collections: readonly Collection[] } | { readonly problem: string };

/** The collections in rar_collections/collections.json: {collections: {<name>: {task, matches, agent_ids, created_at}}}. */
export function readCollections(source: string): CollectionsReading {
	const read = readJson(source);
	if ('problem' in read) {
		return read;
	}
	const all = isRecord(read.value) ? read.value.collections : undefined;
	const entries: [string, unknown][] = isRecord(all) ? Object.entries(all) : Array.isArray(all) ? all.map((c, i) => [isRecord(c) ? text(c.name) ?? String(i + 1) : String(i + 1), c]) : [];
	const collections = entries.map(([name, entry]): Collection => {
		const c = isRecord(entry) ? entry : {};
		const matches = Array.isArray(c.matches) ? c.matches.filter(isRecord) : [];
		const ids = Array.isArray(c.agent_ids) ? c.agent_ids.filter((id): id is string => typeof id === 'string') : [];
		const agents = matches.length
			? matches.map(m => ({ name: clip(text(m.name) ?? text(m.id) ?? '(unnamed)', 200), publisher: text(m.publisher) ? clip(text(m.publisher) as string, 100) : undefined }))
			: ids.map(id => {
				const [publisher, slug] = id.startsWith('@') && id.includes('/') ? [id.slice(0, id.indexOf('/')), id.slice(id.indexOf('/') + 1)] : [undefined, id];
				return { name: clip(slug, 200), publisher };
			});
		return { name: clip(name, 200), task: text(c.task) ? clip(text(c.task) as string, 1000) : undefined, created: text(c.created_at) ? clip(text(c.created_at) as string, 60) : undefined, agents: agents.slice(0, 100) };
	});
	collections.sort((a, b) => (b.created ?? '').localeCompare(a.created ?? ''));
	return { collections };
}

// ── The pages ─────────────────────────────────────────────────────────────────────────────────────────────

const e = escapeHtml;
// Rows shown at first; search looks through up to SEARCHED of the newest, the rest waiting hidden in the page.
const SHOWN = 1000;
const SEARCHED = 20000;
const READ_ONLY = 'To change what it remembers, ask your Brainstem.';

function scale(importance: number, max: number): string {
	const dots = Math.round((importance / max) * 5);
	const said = `Importance ${importance} of ${max}`;
	return `<span class="scale" title="${e(said)}" aria-label="${e(said)}">${'●'.repeat(dots)}${'○'.repeat(5 - dots)}</span>`;
}

function memoryRow(memory: Memory, max: number, later: boolean): string {
	const meta = [
		memory.theme ? `<span class="choice">${e(memory.theme)}</span>` : '',
		...memory.tags.map(tag => `<span class="hash">#${e(tag)}</span>`),
		memory.importance !== undefined ? scale(memory.importance, max) : '',
		memory.mood ? `<span class="muted">${e(memory.mood)}</span>` : '',
		memory.when ? `<span class="muted">${e(memory.when)}</span>` : '',
	].filter(Boolean).join(' ');
	return `<article class="${later ? 'entry later' : 'entry'}"${later ? ' hidden' : ''}><p class="said">${e(memory.text)}</p>${meta ? `<div class="meta">${meta}</div>` : ''}</article>`;
}

const count = (n: number, one: string, many: string) => (n === 1 ? `1 ${one}` : `${n.toLocaleString('en')} ${many}`);

function unreadable(what: string, problem: string): string {
	return `<div class="problem" role="alert"><strong>${e(what)}</strong><p>${e(problem)}</p><button data-action="viewRaw">View raw</button></div>`;
}

/** The memory card: what the Brainstem remembers from one memory file, newest first, with a search box. */
export function memoryBody(read: MemoryReading, file: DataFile | undefined): string {
	const where = file?.kind === 'shared' ? 'Shared memory' : file?.kind === 'user' ? `Memory for user ${file.user.slice(0, 8)}` : 'Memory';
	const actions = '<div class="actions"><input id="search" type="search" placeholder="Search what it remembers" aria-label="Search what it remembers"><button data-action="viewRaw" class="secondary">View raw</button><span id="found" class="muted" aria-live="polite"></span></div>';
	if ('problem' in read) {
		return `<main class="card"><header><h1>What your Brainstem remembers</h1><p class="lead">${e(where)}</p>${unreadable('This memory file isn’t valid JSON, so this card can’t read it', read.problem)}</header></main>`;
	}
	const { memories } = read;
	const max = memories.some(m => (m.importance ?? 0) > 5) ? 10 : 5;
	const lead = `${where} · ${memories.length ? count(memories.length, 'memory', 'memories') : 'nothing yet'}`;
	const rows = memories.slice(0, SEARCHED).map((m, i) => memoryRow(m, max, i >= SHOWN)).join('');
	const newest = `Showing the newest ${SHOWN.toLocaleString('en')}`;
	const more = memories.length > SEARCHED ? `<p class="note">${newest}. Search looks through the newest ${SEARCHED.toLocaleString('en')}; View raw shows them all.</p>`
		: memories.length > SHOWN ? `<p class="note">${newest}. Search looks through all of them.</p>` : '';
	const list = memories.length
		? `<section class="entries">${rows}</section><p id="nothing" class="note" hidden>Nothing it remembers matches.</p>${more}`
		: '<section><p>Nothing remembered yet. Your Brainstem keeps what you ask it to remember here.</p></section>';
	return `<main class="card"><header><h1>What your Brainstem remembers</h1><p class="lead">${e(lead)}</p><p class="more">${e(READ_ONLY)}</p>${memories.length ? actions : '<div class="actions"><button data-action="viewRaw" class="secondary">View raw</button></div>'}</header>${list}</main>`;
}

/** The collections card: one line per collection, its task and then the agents it found. */
export function collectionsBody(read: CollectionsReading): string {
	if ('problem' in read) {
		return `<main class="card"><header><h1>Agent collections</h1>${unreadable('This collections file isn’t valid JSON, so this card can’t read it', read.problem)}</header></main>`;
	}
	const { collections } = read;
	const rows = collections.slice(0, SHOWN).map(c => {
		const agents = c.agents.length ? `<span class="agents">${c.agents.map(a => `${e(a.name)}${a.publisher ? ` <span class="muted">${e(a.publisher)}</span>` : ''}`).join(', ')}</span>` : '<span class="muted">No agents found</span>';
		return `<article class="entry"><p class="said"><strong>${e(c.task ?? c.name)}</strong></p><div class="meta">${agents}${c.created ? ` <span class="muted">· ${e(c.created.slice(0, 10))}</span>` : ''}</div></article>`;
	}).join('');
	const lead = collections.length ? `${count(collections.length, 'collection', 'collections')} of RAR agents your Brainstem picked for a task` : 'None yet: ask your Brainstem to put a collection together';
	return `<main class="card"><header><h1>Agent collections</h1><p class="lead">${e(lead)}</p><p class="more">To change them, ask your Brainstem.</p><div class="actions"><button data-action="viewRaw" class="secondary">View raw</button></div></header>${collections.length ? `<section class="entries">${rows}</section>` : ''}</main>`;
}

/** The whole page: the cards' style, and one nonce'd script for the buttons and the search box. */
export function dataPage(body: string, options: { readonly csp: string; readonly nonce: string }): string {
	const nonce = e(options.nonce);
	return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="${e(options.csp)}">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style nonce="${nonce}">
${CARD_STYLE}
	.actions input { font: inherit; min-width: 260px; flex: 1 1 260px; max-width: 420px; color: var(--vscode-input-foreground); background: var(--vscode-input-background); border: 1px solid var(--vscode-input-border, var(--vscode-widget-border, transparent)); border-radius: 3px; padding: 4px 8px; }
	.actions input:focus { outline: 1px solid var(--vscode-focusBorder); outline-offset: -1px; }
	.actions #found { align-self: center; }
	.entries { padding-top: 6px; }
	.entry { padding: 10px 0; border-top: 1px solid var(--vscode-widget-border, var(--vscode-panel-border, transparent)); }
	.entry:first-child { border-top: none; }
	.said { margin: 0 0 4px; white-space: pre-wrap; overflow-wrap: anywhere; }
	.meta { display: flex; flex-wrap: wrap; gap: 4px 10px; align-items: center; font-size: 0.92em; }
	.hash { color: var(--vscode-textLink-foreground); }
	.scale { letter-spacing: 1px; color: var(--vscode-descriptionForeground); }
	[hidden] { display: none !important; }
</style>
</head>
<body>
${body}
<script nonce="${nonce}">
(function () {
	const vscode = acquireVsCodeApi();
	const state = vscode.getState() || {};
	document.querySelectorAll('button[data-action]').forEach(function (button) {
		button.addEventListener('click', function () { vscode.postMessage({ type: button.dataset.action }); });
	});
	const search = document.getElementById('search');
	if (search) {
		const rows = Array.from(document.querySelectorAll('.entry'));
		const found = document.getElementById('found');
		const nothing = document.getElementById('nothing');
		const filter = function () {
			const query = search.value.trim().toLowerCase();
			let shown = 0;
			rows.forEach(function (row) {
				const hit = query ? row.textContent.toLowerCase().indexOf(query) >= 0 : !row.classList.contains('later');
				row.hidden = !hit;
				shown += hit ? 1 : 0;
			});
			found.textContent = query ? shown.toLocaleString('en') + ' of ' + rows.length.toLocaleString('en') : '';
			if (nothing) { nothing.hidden = shown > 0; }
			vscode.setState({ query: search.value, y: window.scrollY });
		};
		search.value = typeof state.query === 'string' ? state.query : '';
		search.addEventListener('input', filter);
		filter();
	}
	if (typeof state.y === 'number') { window.scrollTo(0, state.y); }
	let saving;
	window.addEventListener('scroll', function () {
		clearTimeout(saving);
		saving = setTimeout(function () { vscode.setState({ query: search ? search.value : '', y: window.scrollY }); }, 150);
	});
}());
</script>
</body>
</html>`;
}
