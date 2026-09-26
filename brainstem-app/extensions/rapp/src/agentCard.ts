// The agent card: what an agent file's facts (from python/agent_card.py, read without running it) mean for a
// person who wants to know what the agent can do, in plain words, and that as a page. Pure: no vscode API, no
// files, no processes. Every string from the file is untrusted and escaped where it is written into the page.
import * as path from 'path';
import { AGENT_SUFFIX, isAgentFileName, isBaseAgent } from './agents';
import { leaves } from './hives';
import { HelperOutcome } from './agentCardHelper';
import { escapeHtml } from './html';

export type Shown = null | boolean | number | string | readonly Shown[] | { readonly [key: string]: Shown };

export interface AgentFacts {
	readonly className: string;
	readonly line?: number;
	/** Built on BasicAgent through classes in this file. */
	readonly basic?: boolean;
	/** Has a perform() of its own. */
	readonly perform?: boolean;
	/** Built on a class from another file: an agent only if that class has a perform(), known when it runs. */
	readonly maybe?: boolean;
	/** Built, in part, on a class from another file. */
	readonly elsewhere?: boolean;
	readonly doc?: string;
	readonly examples: readonly string[];
	/** Absent when the agent never sets it. */
	readonly name?: Shown;
	readonly metadata?: Shown;
}

export interface PackageFact {
	readonly module: string;
	readonly pip: string;
	readonly optional: boolean;
}

export interface RarProblem {
	readonly code: string;
	readonly field?: string;
}

export interface Facts {
	readonly doc?: string;
	/** What stops RAR from taking the agent (build_registry.py, as the helper mirrors it); absent without a manifest. */
	readonly rar?: readonly RarProblem[];
	readonly examples: readonly string[];
	readonly manifest?: Shown;
	readonly manifestLiteral: boolean;
	readonly agents: readonly AgentFacts[];
	readonly env: readonly string[];
	readonly packages: readonly PackageFact[];
	readonly internet?: { readonly via: readonly string[]; readonly domains: readonly string[] };
	readonly files?: readonly string[];
	readonly programs?: readonly string[];
}

export type Problem =
	| { readonly kind: 'syntax'; readonly line?: number; readonly message?: string }
	| { readonly kind: 'too-big' | 'too-deep' | 'timeout' | 'no-python' | 'failed' };

export type Reading = { readonly facts: Facts } | { readonly problem: Problem };

export type Place =
	| { readonly kind: 'live' }
	| { readonly kind: 'folder'; readonly folder: string }
	| { readonly kind: 'base' }
	| { readonly kind: 'outside' };

export interface CardContext {
	readonly fileName: string;
	readonly place: Place;
	/** The folder the file is in, shown only on hover. */
	readonly folderPath?: string;
	readonly size?: number;
	readonly modified?: number;
	readonly dirty?: boolean;
	/** The file is no longer on disk where the card opened it: moved or deleted. */
	readonly missing?: boolean;
	/** `loaded` is /health's agents list; `fresh` says it was asked for after the file was opened or saved. */
	readonly brainstem: { readonly up: boolean; readonly loaded?: readonly string[]; readonly fresh: boolean; readonly version?: string };
	readonly now: number;
}

export interface ParamRow {
	readonly label: string;
	readonly key: string;
	readonly description?: string;
	readonly needed: boolean;
	readonly choices: readonly string[];
	readonly type?: string;
}

export type StatusKind = 'live' | 'not-loaded' | 'not-live' | 'outside';

export interface CardModel {
	readonly title: string;
	readonly lead?: string;
	readonly more?: string;
	readonly note?: string;
	readonly status: { readonly kind: StatusKind; readonly label: string; readonly hint?: string };
	readonly problem?: { readonly title: string; readonly detail?: string; readonly line?: number };
	/** Why the Brainstem would refuse the agent as it is, when the file says so plainly. */
	readonly cannotLoad: readonly string[];
	readonly asks?: { readonly state: 'rows'; readonly rows: readonly ParamRow[] } | { readonly state: 'none' | 'runtime' };
	readonly examples: readonly string[];
	readonly settings: readonly { readonly name: string; readonly needed: boolean }[];
	readonly packages: readonly { readonly name: string; readonly installs?: string; readonly optional: boolean }[];
	readonly mentions?: { readonly internet?: { readonly via: readonly string[]; readonly domains: readonly string[] }; readonly files?: readonly string[]; readonly programs?: readonly string[] };
	readonly rar?: { readonly ready: boolean; readonly why?: string };
	readonly about: readonly AboutRow[];
	readonly others: readonly string[];
}

export interface AboutRow {
	readonly term: string;
	readonly value: string;
	readonly title?: string;
	readonly tags?: readonly string[];
}

export const RUNTIME_TEXT = '(set when it runs)';
const DEEP_TEXT = '(too detailed to show)';
const TOOL_NAME = /^[a-zA-Z0-9_-]+$/;
const ENV_NAME = /^[A-Za-z_][A-Za-z0-9_]{0,127}$/;
const MAX_ROWS = 60;
const MAX_EXAMPLES = 6;
const EXAMPLE_KEYS = ['example_call', 'example_calls', 'example_prompts', 'sample_prompts', 'try_asking'];
const ACRONYMS = new Set(['id', 'url', 'uri', 'api', 'guid', 'uuid', 'ai', 'ip', 'sql', 'json', 'csv', 'pdf', 'html', 'http', 'https', 'ui', 'llm', 'crm', 'erp', 'os', 'sms', 'dns', 'ssh', 'utc']);
// An acronym's plural keeps its small s: ids is IDs, urls is URLs (only these, so oss stays a word).
const PLURALS = new Set(['ids', 'urls', 'uris', 'apis', 'guids', 'uuids', 'ips', 'uis', 'llms', 'pdfs', 'csvs']);
const acronym = (word: string) => (ACRONYMS.has(word) ? word.toUpperCase() : PLURALS.has(word) ? `${word.slice(0, -1).toUpperCase()}s` : word);

// ── What the helper said, checked ────────────────────────────────────────────────────────────────────────────

type Loose = Record<string, unknown>;
const isRecord = (v: unknown): v is Loose => typeof v === 'object' && v !== null && !Array.isArray(v);
const str = (v: unknown): string | undefined => (typeof v === 'string' ? v : undefined);
const strings = (v: unknown): string[] => (Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string') : []);

export function isRuntime(v: unknown): boolean {
	return isRecord(v) && v.$runtime === true && Object.keys(v).length === 1;
}

function isDeep(v: unknown): boolean {
	return isRecord(v) && v.$deep === true && Object.keys(v).length === 1;
}

const isMarker = (v: unknown) => isRuntime(v) || isDeep(v);

function shownValue(v: unknown, depth = 0): Shown | undefined {
	if (depth > 40) {
		return undefined;
	}
	if (v === null || typeof v === 'boolean' || typeof v === 'string' || (typeof v === 'number' && Number.isFinite(v))) {
		return v;
	}
	if (Array.isArray(v)) {
		return v.map(item => shownValue(item, depth + 1) ?? null);
	}
	if (isRecord(v)) {
		const out: Record<string, Shown> = {};
		for (const [key, item] of Object.entries(v)) {
			const value = shownValue(item, depth + 1);
			if (value !== undefined) {
				out[key] = value;
			}
		}
		return out;
	}
	return undefined;
}

/** The helper's answer as a reading, or the problem that stopped it. Anything unexpected is dropped. */
export function reading(outcome: HelperOutcome): Reading {
	if (!outcome.ok) {
		return { problem: { kind: outcome.reason === 'no-python' ? 'no-python' : outcome.reason === 'too-big' ? 'too-big' : outcome.reason === 'timeout' ? 'timeout' : 'failed' } };
	}
	const facts = isRecord(outcome.facts) ? outcome.facts : {};
	if (isRecord(facts.problem)) {
		const kind = facts.problem.kind;
		if (kind === 'syntax') {
			const line = facts.problem.line;
			return { problem: { kind, line: typeof line === 'number' && Number.isInteger(line) && line > 0 ? line : undefined, message: str(facts.problem.message) } };
		}
		return { problem: { kind: kind === 'too-big' || kind === 'too-deep' ? kind : 'failed' } };
	}
	const agents = (Array.isArray(facts.agents) ? facts.agents : []).filter(isRecord).map((agent): AgentFacts => ({
		className: str(agent.class) ?? '',
		line: typeof agent.line === 'number' ? agent.line : undefined,
		basic: agent.basic === true,
		perform: agent.perform === true,
		maybe: agent.maybe === true,
		elsewhere: agent.elsewhere === true,
		doc: str(agent.doc),
		examples: strings(agent.examples),
		...('name' in agent ? { name: shownValue(agent.name) ?? null } : {}),
		...('metadata' in agent ? { metadata: shownValue(agent.metadata) ?? null } : {}),
	}));
	const capability = (v: unknown) => (isRecord(v) ? strings(v.via) : undefined);
	const internet = isRecord(facts.internet) ? { via: strings(facts.internet.via), domains: strings(facts.internet.domains) } : undefined;
	return {
		facts: {
			doc: str(facts.doc),
			examples: strings(facts.examples),
			...(facts.manifest !== undefined && facts.manifest !== null ? { manifest: shownValue(facts.manifest) ?? null } : {}),
			manifestLiteral: facts.manifestLiteral === true,
			...(Array.isArray(facts.rar) ? { rar: facts.rar.filter(isRecord).flatMap(p => typeof p.code === 'string' ? [{ code: p.code, field: str(p.field) }] : []) } : {}),
			agents,
			env: strings(facts.env).filter(name => ENV_NAME.test(name)),
			packages: (Array.isArray(facts.packages) ? facts.packages : []).filter(isRecord).flatMap(p => {
				const module = str(p.module);
				return module ? [{ module, pip: str(p.pip) ?? module, optional: p.optional === true }] : [];
			}),
			internet,
			files: capability(facts.files),
			programs: capability(facts.programs),
		},
	};
}

// ── Plain words ──────────────────────────────────────────────────────────────────────────────────────────────

function textOf(v: Shown | undefined): string | undefined {
	return typeof v === 'string' && v.trim() ? v.trim() : undefined;
}

/** A tool name as a person would say it: weather_poet becomes "Weather poet"; HackerNews stays as it is. */
export function friendly(name: string | undefined): string | undefined {
	if (!name) {
		return undefined;
	}
	const spaced = name.replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim();
	if (!spaced) {
		return undefined;
	}
	return spaced === spaced.toLowerCase() ? spaced[0].toUpperCase() + spaced.slice(1) : spaced;
}

/** A parameter key as a label: include_wind and includeWind both become "Include wind". */
export function humanize(key: string): string {
	const words = key.replace(/([a-z0-9])([A-Z])/g, '$1 $2').replace(/[_\-\s]+/g, ' ').trim().toLowerCase().split(' ').filter(Boolean);
	if (!words.length) {
		return key;
	}
	const shown = words.map(acronym);
	return shown[0][0].toUpperCase() + shown[0].slice(1) + (shown.length > 1 ? ' ' + shown.slice(1).join(' ') : '');
}

export function fileTitle(fileName: string): string {
	const stem = fileName.toLowerCase().endsWith(AGENT_SUFFIX) ? fileName.slice(0, -AGENT_SUFFIX.length) : fileName.replace(/\.py$/i, '');
	return friendly(stem) ?? fileName;
}

/**
 * The first sentence, found the way the Brainstem's own roster shortens a description (brainstem.py
 * _first_sentence), and the rest. A first sentence longer than `max` is cut at a word, and the whole text
 * then follows as the rest, so nothing is lost.
 */
export function firstSentence(text: string, max = 200): { readonly sentence: string; readonly rest?: string } {
	const flat = text.split(/\s+/).filter(Boolean).join(' ');
	const end = /\.(?:\s|$)/.exec(flat);
	const sentence = end ? flat.slice(0, end.index + 1) : flat;
	const rest = flat.slice(sentence.length).trim();
	if (sentence.length <= max) {
		return rest ? { sentence, rest } : { sentence };
	}
	const cut = sentence.slice(0, max);
	const word = cut.lastIndexOf(' ');
	return { sentence: (word > max / 2 ? cut.slice(0, word) : cut).trimEnd() + '…', rest: flat };
}

function firstLine(text: string | undefined): string | undefined {
	const line = text?.split('\n').map(l => l.trim()).find(Boolean);
	return line || undefined;
}

export function typeWords(type: Shown | undefined, items?: Shown): string | undefined {
	const kind = Array.isArray(type) ? type.find(t => t !== 'null') : type;
	switch (kind) {
		case 'string': return 'text';
		case 'integer':
		case 'number': return 'number';
		case 'boolean': return 'yes/no';
		case 'object': return 'details';
		case 'array': {
			const inner = isRecord(items) ? typeWords(items.type as Shown) : undefined;
			return inner === 'text' || inner === 'yes/no' ? `list of ${inner}` : inner === 'number' ? 'list of numbers' : inner === 'details' ? 'list of details' : 'list';
		}
		default: return undefined;
	}
}

function choiceText(v: Shown): string {
	if (isRuntime(v)) {
		return RUNTIME_TEXT;
	}
	if (isDeep(v)) {
		return DEEP_TEXT;
	}
	return v === null ? 'none' : typeof v === 'object' ? JSON.stringify(v) : String(v);
}

export function formatSize(bytes: number): string {
	if (bytes < 1024) {
		return `${bytes} ${bytes === 1 ? 'byte' : 'bytes'}`;
	}
	return bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function whenChanged(modified: number, now: number): string {
	const seconds = Math.max(0, Math.round((now - modified) / 1000));
	if (seconds < 60) {
		return 'just now';
	}
	const minutes = Math.round(seconds / 60);
	if (minutes < 60) {
		return minutes === 1 ? 'a minute ago' : `${minutes} minutes ago`;
	}
	const hours = Math.round(minutes / 60);
	if (hours < 24) {
		return hours === 1 ? 'an hour ago' : `${hours} hours ago`;
	}
	const days = Math.round(hours / 24);
	if (days < 7) {
		return days === 1 ? 'yesterday' : `${days} days ago`;
	}
	return new Date(modified).toLocaleDateString('en', { year: 'numeric', month: 'short', day: 'numeric' });
}

// ── Where the file is ────────────────────────────────────────────────────────────────────────────────────────

/** Where a file sits for the card: at the top of agents/ (live), in one of its folders, or elsewhere. */
export function cardPlace(root: string | undefined, file: string, platform: NodeJS.Platform = process.platform): Place {
	if (!root) {
		return { kind: 'outside' };
	}
	const rel = path.relative(root, file);
	if (!rel || leaves(rel)) {
		return { kind: 'outside' };
	}
	const parts = rel.split(path.sep);
	const name = parts[parts.length - 1];
	if (parts.length === 1) {
		return isBaseAgent(name, platform) ? { kind: 'base' } : isAgentFileName(name, platform) ? { kind: 'live' } : { kind: 'folder', folder: '.' };
	}
	return { kind: 'folder', folder: parts.slice(0, -1).join('/') };
}

// ── The card ─────────────────────────────────────────────────────────────────────────────────────────────────

const record = (v: Shown | undefined): { readonly [key: string]: Shown } | undefined => (isRecord(v) && !isMarker(v) ? v as { readonly [key: string]: Shown } : undefined);

// The grail's newest channel (0.6.16 and later) checks more as it loads an agent than the LTS pin (0.6.9) does.
function newestChannel(version: string | undefined): boolean {
	const parts = /^(\d+)\.(\d+)\.(\d+)/.exec(version ?? '');
	if (!parts) {
		return false;
	}
	const [major, minor, patch] = parts.slice(1).map(Number);
	return major > 0 || minor > 6 || (minor === 6 && patch >= 16);
}

// The first thing the newest channel's schema check (_validate_agent_schema) refuses in a parameters schema.
function schemaProblem(schema: unknown, where: string): string | undefined {
	if (isMarker(schema)) {
		return undefined;
	}
	if (!isRecord(schema)) {
		return `${where} must be a dictionary`;
	}
	const type = schema.type;
	if ('type' in schema && !isMarker(type) && !(typeof type === 'string' || (Array.isArray(type) && type.length > 0 && type.every(t => typeof t === 'string')))) {
		return `the type of ${where} must be text, or a list of text`;
	}
	if ('description' in schema && !isMarker(schema.description) && typeof schema.description !== 'string') {
		return `the description of ${where} must be text`;
	}
	const required = schema.required;
	if ('required' in schema && !isMarker(required) && !(Array.isArray(required) && required.every(name => typeof name === 'string'))) {
		return `“required” in ${where} must be a list of names`;
	}
	const properties = schema.properties;
	if ('properties' in schema && !isMarker(properties)) {
		if (!isRecord(properties)) {
			return `the properties of ${where} must be a dictionary`;
		}
		for (const [name, property] of Object.entries(properties)) {
			if (isMarker(property)) {
				continue;
			}
			if (!isRecord(property)) {
				return `the detail “${name}” in ${where} must be described by a dictionary`;
			}
			const inner = schemaProblem(property, `the detail “${name}”`);
			if (inner) {
				return inner;
			}
		}
	}
	if ('items' in schema) {
		const inner = schemaProblem(schema.items, `the items of ${where}`);
		if (inner) {
			return inner;
		}
	}
	for (const keyword of ['allOf', 'anyOf', 'oneOf']) {
		if (!(keyword in schema) || isMarker(schema[keyword])) {
			continue;
		}
		const branches = schema[keyword];
		if (!Array.isArray(branches) || !branches.length) {
			return `“${keyword}” in ${where} must be a list of choices`;
		}
		for (const [index, branch] of branches.entries()) {
			const inner = schemaProblem(branch, `choice ${index + 1} of “${keyword}” in ${where}`);
			if (inner) {
				return inner;
			}
		}
	}
	return undefined;
}

/**
 * Why the Brainstem's hot-load boundary would refuse this agent (brainstem.py _validate_agent_instance), when the
 * file says so plainly: the LTS pin's checks always, and the newest channel's stricter ones when the running
 * Brainstem says it is 0.6.16 or newer.
 */
export function cannotLoad(agent: AgentFacts | undefined, version?: string): string[] {
	if (!agent) {
		return [];
	}
	const reasons: string[] = [];
	const name = agent.name;
	if (typeof name === 'string') {
		if (!name) {
			reasons.push('its name is empty');
		} else if (!TOOL_NAME.test(name)) {
			reasons.push(`its name “${name}” may use only letters, numbers, - and _`);
		}
	} else if (name !== undefined && !isMarker(name)) {
		reasons.push('its name isn’t text');
	}
	const metadata = agent.metadata;
	if (metadata === undefined || isMarker(metadata)) {
		return reasons;
	}
	if (!isRecord(metadata)) {
		reasons.push('its metadata isn’t a dictionary');
		return reasons;
	}
	const newest = newestChannel(version);
	if (newest && 'description' in metadata && !isMarker(metadata.description) && typeof metadata.description !== 'string') {
		reasons.push('its description isn’t text');
	}
	const params = metadata.parameters;
	if (newest && 'parameters' in metadata && params === null) {
		reasons.push('its parameters aren’t a dictionary');
		return reasons;
	}
	if (params === undefined || params === null || isMarker(params)) {
		return reasons;
	}
	if (!isRecord(params)) {
		reasons.push('its parameters aren’t a dictionary');
		return reasons;
	}
	if (!isMarker(params.type) && params.type !== 'object') {
		reasons.push('its parameters need "type": "object"');
	}
	const props = params.properties;
	if (props !== undefined && props !== null && !isMarker(props) && !isRecord(props)) {
		reasons.push('its parameters’ properties aren’t a dictionary');
	}
	const schema = newest && !reasons.length ? schemaProblem(params, 'its parameters') : undefined;
	if (schema) {
		reasons.push(schema);
	}
	return reasons;
}

const RAR_WORDS: Record<string, string> = {
	'not-found': 'RAR reads a manifest only from a plain __manifest__ = {…}',
	'not-literal': 'its manifest is only complete when the agent runs',
	'not-dict': 'its manifest isn’t a dictionary',
	'schema': 'its manifest schema isn’t rapp-agent/1.0',
	'name': 'its package name must look like @publisher/slug',
	'version': 'its version must look like 1.0.0',
	'tags': 'its tags must be a list',
	'no-name': 'its name must be written plainly in the file',
	'name-unsafe': 'its name may use only letters, numbers, - and _',
	'name-mismatch': 'its metadata name must match its name',
	'security-system': 'its text has os.system( in it, which RAR refuses even in a comment; use subprocess instead',
	'security-file': 'RAR refuses code that opens /etc, /proc, .env, .ssh or passwd',
	'security-secret': 'it looks like it has a secret written into it, which RAR refuses',
	'file-name': 'its file name has a dash, and RAR needs snake_case, like weather_agent.py',
	'not-utf8': 'RAR reads agent files as UTF-8, and this one isn’t: save it as UTF-8',
	'bom': 'it starts with a byte order mark, which RAR stops at: save it as UTF-8 without one',
};

/**
 * Whether RAR would take this agent as it is: what build_registry.py checks, as the helper mirrors it, and first
 * of all its file name, which may have no dash.
 */
export function rarReadiness(facts: Facts, fileName = ''): { readonly ready: boolean; readonly why?: string } | undefined {
	if (!facts.rar) {
		return undefined;
	}
	const problems: readonly RarProblem[] = [...(fileName.replace(/\.py$/, '').includes('-') ? [{ code: 'file-name' }] : []), ...facts.rar];
	const [first] = problems;
	if (!first) {
		return { ready: true };
	}
	const why = first.code === 'missing' && first.field ? `its manifest has no ${first.field.replace(/_/g, ' ')}` : RAR_WORDS[first.code] ?? 'RAR would not take it as it is';
	return { ready: false, why };
}

function examplesOf(facts: Facts, agent: AgentFacts | undefined): string[] {
	const manifest = record(facts.manifest);
	const found: string[] = [];
	const push = (text: string) => {
		const clean = text.trim().replace(/^["'“‘]+|["'”’]+$/g, '').trim();
		if (clean && found.length < MAX_EXAMPLES && !found.some(e => e.toLowerCase() === clean.toLowerCase())) {
			found.push(clean.length > 200 ? clean.slice(0, 199) + '…' : clean);
		}
	};
	for (const key of EXAMPLE_KEYS) {
		const value = manifest?.[key];
		if (typeof value === 'string') {
			push(value);
		} else if (Array.isArray(value)) {
			value.forEach(item => typeof item === 'string' && push(item));
		}
	}
	[...(agent?.examples ?? []), ...facts.examples].forEach(push);
	return found;
}

function asksOf(agent: AgentFacts | undefined): CardModel['asks'] {
	const metadata = agent?.metadata;
	if (metadata === undefined || metadata === null) {
		return { state: 'none' };
	}
	if (isMarker(metadata)) {
		return { state: 'runtime' };
	}
	const params = record(metadata)?.parameters;
	if (isMarker(params)) {
		return { state: 'runtime' };
	}
	const props = record(params)?.properties;
	if (isMarker(props)) {
		return { state: 'runtime' };
	}
	const entries = Object.entries(record(props) ?? {});
	if (!entries.length) {
		return { state: 'none' };
	}
	const required = record(params)?.required;
	const needed = new Set(Array.isArray(required) ? required.filter((k): k is string => typeof k === 'string') : []);
	const rows = entries.slice(0, MAX_ROWS).map(([key, prop]): ParamRow => {
		const p = record(prop);
		const description = isMarker(prop) || isMarker(p?.description) ? RUNTIME_TEXT : textOf(p?.description);
		const type = typeWords(p?.type, p?.items);
		const choicesFrom = Array.isArray(p?.enum) ? p?.enum : type?.startsWith('list') && Array.isArray(record(p?.items)?.enum) ? record(p?.items)?.enum : undefined;
		return {
			label: humanize(key),
			key,
			description,
			needed: needed.has(key),
			choices: Array.isArray(choicesFrom) ? choicesFrom.slice(0, 40).map(choiceText) : [],
			type,
		};
	});
	return { state: 'rows', rows };
}

function statusOf(ctx: CardContext, agent: AgentFacts | undefined, blocked: string | undefined, reasons: readonly string[]): CardModel['status'] {
	if (ctx.missing) {
		return { kind: 'outside', label: 'Not found — this file was moved or deleted', hint: 'Your Brainstem runs only what is in agents/ now' };
	}
	// The loader's glob never matches a hidden file (one whose name starts with a dot), wherever it is.
	const hidden = ctx.fileName.startsWith('.');
	switch (ctx.place.kind) {
		case 'folder':
			return ctx.place.folder === '.'
				? { kind: 'not-live', label: 'Not live', hint: hidden ? 'Hidden files never run; take the dot off the start of its name' : 'Only files named like weather_agent.py at the top of agents/ run' }
				: { kind: 'not-live', label: `Not live — in ${ctx.place.folder}/`, hint: hidden ? 'Hidden files never run, even at the top of agents/' : 'Drag it to the top of agents/ to run it' };
		case 'outside':
			return { kind: 'outside', label: 'Not in your Brainstem’s agents/ folder', hint: 'Only agents at the top of agents/ run' };
		case 'base':
			return { kind: 'outside', label: 'The base every agent builds on', hint: 'Your Brainstem needs it as it is; it is not an agent itself' };
	}
	if (blocked) {
		return { kind: 'not-loaded', label: blocked, hint: 'See the problem below' };
	}
	const names = [textOf(record(agent?.metadata)?.name), textOf(agent?.name)].filter((n): n is string => !!n);
	const { up, loaded, fresh } = ctx.brainstem;
	// The Brainstem loads the file on disk, so unsaved edits are not held against it.
	if (up && fresh && !ctx.dirty && loaded && names.length && !names.some(name => loaded.includes(name))) {
		return {
			kind: 'not-loaded',
			label: 'Live file, but your Brainstem didn’t load it',
			hint: reasons.length ? 'See why below' : 'Your Brainstem skips an agent that fails to import, or whose name or details aren’t valid',
		};
	}
	return { kind: 'live', label: 'Live', hint: up ? 'Your Brainstem runs this' : 'Your Brainstem runs this whenever it is running' };
}

function problemOf(problem: Problem): NonNullable<CardModel['problem']> {
	switch (problem.kind) {
		case 'syntax':
			return {
				title: 'This agent has a problem, so your Brainstem can’t load it',
				detail: problem.line ? `Line ${problem.line}: ${problem.message ?? 'invalid syntax'}` : problem.message,
				line: problem.line,
			};
		case 'too-big':
			return { title: 'This file is too big to show as a card', detail: 'Agent files over 1 MB are shown as code only.' };
		case 'too-deep':
			return { title: 'This agent is nested too deeply to read safely', detail: 'Open its code to see it.' };
		case 'timeout':
			return { title: 'Reading this agent took too long', detail: 'The card gives up after 3 seconds. Open its code to see it.' };
		case 'no-python':
			return { title: 'No Python was found to read this agent', detail: 'The card reads agents with your Brainstem’s own Python. Start your Brainstem once, or set rapp.pythonPath.' };
		case 'failed':
			return { title: 'This card couldn’t read the agent', detail: 'Open its code to see it.' };
	}
}

function aboutOf(facts: Facts | undefined, agent: AgentFacts | undefined, ctx: CardContext): AboutRow[] {
	const rows: AboutRow[] = [];
	const manifest = record(facts?.manifest);
	for (const [term, key] of [['Version', 'version'], ['Author', 'author'], ['Category', 'category']] as const) {
		const value = textOf(manifest?.[key]);
		if (value) {
			rows.push({ term, value });
		}
	}
	const rawTags = manifest?.tags;
	const tags = Array.isArray(rawTags) ? rawTags.filter((t): t is string => typeof t === 'string' && !!t.trim()).slice(0, 30) : [];
	if (tags.length) {
		rows.push({ term: 'Tags', value: tags.join(', '), tags });
	}
	const tool = textOf(agent?.name) ?? textOf(record(agent?.metadata)?.name);
	if (tool) {
		rows.push({ term: 'Tool name', value: tool, title: 'The name your Brainstem calls it by' });
	}
	rows.push({ term: 'File', value: ctx.fileName });
	const folder = ctx.place.kind === 'live' || ctx.place.kind === 'base' ? 'The top of agents/' : ctx.place.kind === 'folder' ? (ctx.place.folder === '.' ? 'The top of agents/' : `${ctx.place.folder}/ in agents/`) : 'Outside agents/';
	rows.push({ term: 'Folder', value: folder, title: ctx.folderPath });
	if (typeof ctx.size === 'number') {
		rows.push({ term: 'Size', value: formatSize(ctx.size) });
	}
	if (typeof ctx.modified === 'number') {
		rows.push({
			term: 'Last changed',
			value: whenChanged(ctx.modified, ctx.now) + (ctx.dirty ? ' (with unsaved changes here)' : ''),
			title: new Date(ctx.modified).toLocaleString('en'),
		});
	}
	return rows;
}

/** Everything the card shows, non-technical first. */
export function cardModel(read: Reading, ctx: CardContext): CardModel {
	const fallbackTitle = fileTitle(ctx.fileName);
	if ('problem' in read) {
		const blocked = read.problem.kind === 'syntax' ? 'Live file, but your Brainstem can’t load it' : undefined;
		return {
			title: fallbackTitle,
			status: statusOf(ctx, undefined, blocked, []),
			problem: problemOf(read.problem),
			cannotLoad: [],
			examples: [],
			settings: [],
			packages: [],
			about: aboutOf(undefined, undefined, ctx),
			others: [],
		};
	}
	const { facts } = read;
	const manifest = record(facts.manifest);
	const agent = facts.agents[0];
	const metadata = record(agent?.metadata);
	const title = textOf(manifest?.display_name) ?? friendly(textOf(metadata?.name)) ?? friendly(textOf(agent?.name)) ?? fallbackTitle;
	const description = textOf(manifest?.description) ?? textOf(metadata?.description);
	const { sentence, rest } = description ? firstSentence(description, 300) : { sentence: firstLine(agent?.doc) ?? firstLine(facts.doc), rest: undefined };
	const reasons = cannotLoad(agent, ctx.brainstem.version);
	const noAgent = !agent;
	const rawRequires = manifest?.requires_env;
	const requires = Array.isArray(rawRequires) ? rawRequires.filter((n): n is string => typeof n === 'string' && ENV_NAME.test(n)) : [];
	const settings = [...requires.map(name => ({ name, needed: true })), ...facts.env.filter(name => !requires.includes(name)).map(name => ({ name, needed: false }))].slice(0, 60);
	const mentions = facts.internet || facts.files?.length || facts.programs?.length
		? { internet: facts.internet, files: facts.files?.length ? facts.files : undefined, programs: facts.programs?.length ? facts.programs : undefined }
		: undefined;
	return {
		title,
		lead: sentence,
		more: rest,
		note: agent?.maybe ? 'It is built on an agent from another file, so some of its details only exist when it runs.'
			: agent?.elsewhere ? 'It builds on code from another file, so some of what it does comes from there.' : undefined,
		status: statusOf(ctx, agent, noAgent ? 'Live file, but there’s no agent in it' : undefined, reasons),
		problem: noAgent ? { title: 'There’s no agent in this file', detail: 'Your Brainstem runs classes built on BasicAgent that have a perform() method, and this file has none.' } : undefined,
		cannotLoad: reasons,
		asks: noAgent ? undefined : asksOf(agent),
		examples: examplesOf(facts, agent),
		settings,
		packages: facts.packages.map(p => ({ name: p.module, installs: p.pip !== p.module ? p.pip : undefined, optional: p.optional })),
		mentions,
		rar: rarReadiness(facts, ctx.fileName),
		about: aboutOf(facts, agent, ctx),
		others: facts.agents.slice(1).map(a => friendly(textOf(a.name)) ?? a.className).filter(Boolean),
	};
}

// ── The page ─────────────────────────────────────────────────────────────────────────────────────────────────

const e = escapeHtml;

function section(title: string, body: string, note?: string): string {
	return `<section><h2>${e(title)}</h2>${note ? `<p class="note">${e(note)}</p>` : ''}${body}</section>`;
}

function runtimeOr(text: string | undefined): string {
	return text === RUNTIME_TEXT ? `<span class="runtime">${e(RUNTIME_TEXT)}</span>` : e(text ?? '');
}

function asksHtml(asks: CardModel['asks']): string {
	if (!asks) {
		return '';
	}
	if (asks.state !== 'rows') {
		return section('What you can ask it', asks.state === 'none' ? '<p>Just ask — it doesn’t need any details.</p>' : `<p><span class="runtime">${e(RUNTIME_TEXT)}</span></p>`);
	}
	const rows = asks.rows.map(row => {
		const tags = [row.needed ? '<span class="tag">needed</span>' : '', row.type ? `<span class="type">${e(row.type)}</span>` : ''].join('');
		const choices = row.choices.length ? `<div class="choices"><span class="muted">Choices:</span> ${row.choices.map(c => `<span class="choice">${e(c)}</span>`).join(' ')}</div>` : '';
		return `<div class="row"><div class="label" title="${e(row.key)}">${e(row.label)}${tags}</div><div>${row.description ? `<div>${runtimeOr(row.description)}</div>` : ''}${choices}</div></div>`;
	}).join('');
	return section('What you can ask it', `<div class="rows">${rows}</div>`);
}

function needsHtml(model: CardModel): string {
	const parts: string[] = [];
	if (model.settings.length) {
		const names = model.settings.map(s => `<li><code>${e(s.name)}</code>${s.needed ? '<span class="tag">needed</span>' : ''}</li>`).join('');
		parts.push(`<h3>Settings it reads</h3><ul class="plain">${names}</ul><p class="note">Agents read these from your Brainstem’s environment, including the .env file in its folder. Only names are shown, never values.</p>`);
	}
	if (model.packages.length) {
		const names = model.packages.map(p => `<li><code>${e(p.name)}</code>${p.installs ? ` <span class="muted">(installs as ${e(p.installs)})</span>` : ''}${p.optional ? ' <span class="muted">(optional)</span>' : ''}</li>`).join('');
		parts.push(`<h3>Python packages</h3><ul class="plain">${names}</ul><p class="note">Your Brainstem installs missing packages when it loads the agent.</p>`);
	}
	return section('What it needs', parts.length ? parts.join('') : '<p>Nothing extra: no settings and no packages beyond Python’s own.</p>');
}

function mentionsHtml(mentions: CardModel['mentions']): string {
	const note = 'A hint from the names in its code, not a guarantee.';
	if (!mentions) {
		return section('What the code mentions', '<p>Nothing that reaches the internet, touches files or runs programs.</p>', note);
	}
	const chips: string[] = [];
	if (mentions.internet) {
		chips.push(`<span class="chip" title="${e(mentions.internet.via.join(', '))}">Uses the internet</span>`);
	}
	if (mentions.files) {
		chips.push(`<span class="chip" title="${e(mentions.files.join(', '))}">Reads or writes files</span>`);
	}
	if (mentions.programs) {
		chips.push(`<span class="chip" title="${e(mentions.programs.join(', '))}">Runs programs</span>`);
	}
	const domains = mentions.internet?.domains.length ? `<p>Sites it mentions: ${mentions.internet.domains.map(d => `<code>${e(d)}</code>`).join(', ')}</p>` : '';
	return section('What the code mentions', `<div class="chips">${chips.join('')}</div>${domains}`, note);
}

function aboutHtml(model: CardModel): string {
	const rows = model.about.map(row => {
		const value = row.tags ? row.tags.map(tag => `<span class="choice">${e(tag)}</span>`).join(' ') : e(row.value);
		return `<dt>${e(row.term)}</dt><dd${row.title ? ` title="${e(row.title)}"` : ''}>${value}</dd>`;
	}).join('');
	const rar = model.rar ? `<p class="${model.rar.ready ? 'ready' : 'note'}">${model.rar.ready ? '✓ Ready to share through RAR' : `Not ready to share through RAR yet: ${e(model.rar.why ?? '')}.`}</p>` : '';
	const others = model.others.length ? `<p class="note">Also in this file: ${model.others.map(o => e(o)).join(', ')}.</p>` : '';
	return section('About', `${rar}<dl>${rows}</dl>${others}`);
}

/** The card's content: everything but the page's head, so an unchanged card is not drawn again. */
export function cardBody(model: CardModel): string {
	const status = `<div class="status ${model.status.kind}"><span class="pill"><span class="dot"></span>${e(model.status.label)}</span>${model.status.hint ? `<span class="hint">${e(model.status.hint)}</span>` : ''}</div>`;
	const problem = model.problem
		? `<div class="problem" role="alert"><strong>${e(model.problem.title)}</strong>${model.problem.detail ? `<p>${e(model.problem.detail)}</p>` : ''}${model.problem.line ? `<button data-action="viewCode" data-line="${model.problem.line}">Show me line ${model.problem.line}</button>` : ''}</div>`
		: '';
	const refused = model.cannotLoad.length
		? `<div class="problem warning"><strong>Your Brainstem won’t load it as it is</strong><ul>${model.cannotLoad.map(r => `<li>${e(r)}</li>`).join('')}</ul></div>`
		: '';
	const head = `<header><h1>${e(model.title)}</h1>${model.lead ? `<p class="lead">${e(model.lead)}</p>` : ''}${model.more ? `<p class="more">${e(model.more)}</p>` : ''}${model.note ? `<p class="more">${e(model.note)}</p>` : ''}${status}<div class="actions"><button data-action="viewCode">View code</button><button data-action="reveal" class="secondary">Reveal in Explorer</button></div>${problem}${refused}</header>`;
	if (model.problem && !model.asks) {
		return `<main class="card">${head}${aboutHtml(model)}</main>`;
	}
	const examples = model.examples.length ? section('Try asking', `<ul class="examples">${model.examples.map(x => `<li>“${e(x)}”</li>`).join('')}</ul>`) : '';
	return `<main class="card">${head}${asksHtml(model.asks)}${examples}${needsHtml(model)}${mentionsHtml(model.mentions)}${aboutHtml(model)}</main>`;
}

/** The cards' shared, theme-aware style: the agent card and the Brainstem data cards look alike. */
export const CARD_STYLE = `	body { margin: 0; padding: 22px 28px 40px; font-family: var(--vscode-font-family); font-size: var(--vscode-font-size); color: var(--vscode-foreground); background: var(--vscode-editor-background); line-height: 1.5; }
	.card { max-width: 780px; }
	header { padding-bottom: 16px; border-bottom: 1px solid var(--vscode-widget-border, var(--vscode-panel-border, transparent)); }
	h1 { font-size: 1.75em; font-weight: 600; margin: 0 0 4px; overflow-wrap: anywhere; }
	.lead { font-size: 1.12em; margin: 0 0 6px; }
	.more { color: var(--vscode-descriptionForeground); margin: 0 0 8px; }
	.status { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 10px; margin-top: 10px; }
	.pill { display: inline-flex; align-items: center; gap: 7px; border-radius: 999px; padding: 2px 11px; font-weight: 600; border: 1px solid var(--vscode-widget-border, var(--vscode-panel-border, currentColor)); }
	.dot { width: 8px; height: 8px; border-radius: 50%; background: var(--vscode-descriptionForeground); flex: none; }
	.status.live .dot { background: var(--vscode-testing-iconPassed, #3fa66a); }
	.status.not-loaded .dot { background: var(--vscode-problemsWarningIcon-foreground, #c9a24f); }
	.status.not-live .pill, .status.outside .pill { color: var(--vscode-descriptionForeground); }
	.hint { color: var(--vscode-descriptionForeground); }
	.actions { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 14px; }
	button { font: inherit; border: none; border-radius: 3px; padding: 4px 12px; cursor: pointer; color: var(--vscode-button-foreground); background: var(--vscode-button-background); }
	button:hover { background: var(--vscode-button-hoverBackground); }
	button.secondary { color: var(--vscode-button-secondaryForeground); background: var(--vscode-button-secondaryBackground); }
	button.secondary:hover { background: var(--vscode-button-secondaryHoverBackground); }
	.problem { border: 1px solid var(--vscode-inputValidation-errorBorder, #c94f4f); background: var(--vscode-inputValidation-errorBackground, transparent); border-radius: 6px; padding: 10px 12px; margin-top: 14px; }
	.problem.warning { border-color: var(--vscode-inputValidation-warningBorder, #c9a24f); background: var(--vscode-inputValidation-warningBackground, transparent); }
	.problem p, .problem ul { margin: 6px 0; }
	.problem button { margin-top: 4px; }
	section { padding: 18px 0 2px; }
	h2 { font-size: 0.82em; text-transform: uppercase; letter-spacing: 0.07em; color: var(--vscode-descriptionForeground); margin: 0 0 8px; font-weight: 600; }
	h3 { font-size: 1em; font-weight: 600; margin: 10px 0 4px; }
	.note { color: var(--vscode-descriptionForeground); margin: 4px 0 8px; }
	.rows .row { display: grid; grid-template-columns: minmax(150px, 230px) 1fr; gap: 2px 18px; padding: 8px 0; border-top: 1px solid var(--vscode-widget-border, var(--vscode-panel-border, transparent)); }
	.rows .row:first-child { border-top: none; }
	.label { font-weight: 600; }
	.tag { display: inline-block; font-size: 0.78em; font-weight: 600; border-radius: 3px; padding: 0 6px; margin-left: 7px; color: var(--vscode-badge-foreground); background: var(--vscode-badge-background); vertical-align: 1px; }
	.type { display: block; font-weight: normal; font-size: 0.9em; color: var(--vscode-descriptionForeground); }
	.choices { margin-top: 3px; }
	.choice { display: inline-block; font-size: 0.92em; border-radius: 3px; padding: 0 7px; margin: 2px 2px 0 0; background: var(--vscode-textCodeBlock-background); }
	.muted, .runtime { color: var(--vscode-descriptionForeground); }
	.runtime { font-style: italic; }
	.examples { margin: 0; padding-left: 20px; }
	.examples li { margin: 4px 0; }
	ul.plain { margin: 0; padding-left: 20px; }
	ul.plain li { margin: 2px 0; }
	code { font-family: var(--vscode-editor-font-family); font-size: 0.95em; }
	.chips { display: flex; flex-wrap: wrap; gap: 6px; }
	.chip { display: inline-block; border: 1px solid var(--vscode-widget-border, var(--vscode-panel-border, currentColor)); border-radius: 999px; padding: 2px 11px; }
	.ready { color: var(--vscode-testing-iconPassed, #3fa66a); font-weight: 600; margin: 0 0 8px; }
	dl { display: grid; grid-template-columns: max-content 1fr; gap: 4px 18px; margin: 0; }
	dt { color: var(--vscode-descriptionForeground); }
	dd { margin: 0; overflow-wrap: anywhere; }
`;

/** The whole page. The only script is the nonce'd one wiring the buttons (and keeping the scroll position). */
export function cardPage(body: string, options: { readonly csp: string; readonly nonce: string }): string {
	const nonce = e(options.nonce);
	return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="${e(options.csp)}">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style nonce="${nonce}">
${CARD_STYLE}</style>
</head>
<body>
${body}
<script nonce="${nonce}">
(function () {
	const vscode = acquireVsCodeApi();
	const state = vscode.getState();
	if (state && typeof state.y === 'number') {
		window.scrollTo(0, state.y);
	}
	let saving;
	window.addEventListener('scroll', function () {
		clearTimeout(saving);
		saving = setTimeout(function () { vscode.setState({ y: window.scrollY }); }, 150);
	});
	document.querySelectorAll('button[data-action]').forEach(function (button) {
		button.addEventListener('click', function () {
			vscode.postMessage({ type: button.dataset.action, line: Number(button.dataset.line) || undefined });
		});
	});
}());
</script>
</body>
</html>`;
}
