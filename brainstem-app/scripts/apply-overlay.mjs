#!/usr/bin/env node
// Applies the Brainstem overlay (overlay.json + product.json + extensions/rapp + branding) to a
// checkout of the pinned fork. It only ever writes inside the checkout it is given.
//
//   node scripts/apply-overlay.mjs --checkout <dir> [--expect-commit <sha>] [--report <file>] [--webview-port <port>]
//   node scripts/apply-overlay.mjs --merge-product <upstream product.json> [--out <file>]
//   node scripts/apply-overlay.mjs --validate-product <product.json>
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { renderAsset } from './branding.mjs';

export const APP_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

export function readJson(file) {
	return JSON.parse(fs.readFileSync(file, 'utf8'));
}

export function loadOverlay(appDir = APP_DIR) {
	return readJson(path.join(appDir, 'overlay.json'));
}

const isObject = v => v !== null && typeof v === 'object' && !Array.isArray(v);
const isUrl = v => typeof v === 'string' && /^[a-z][a-z0-9+.-]*:\/\//i.test(v.trim());

// Objects merge key by key; arrays and scalars from the overlay replace upstream's.
export function deepMerge(base, overlay) {
	if (!isObject(base) || !isObject(overlay)) {
		return structuredClone(overlay);
	}
	const out = structuredClone(base);
	for (const [key, value] of Object.entries(overlay)) {
		out[key] = key in out ? deepMerge(out[key], value) : structuredClone(value);
	}
	return out;
}

function emptyUrls(value) {
	if (Array.isArray(value)) {
		return value.map(emptyUrls);
	}
	if (isObject(value)) {
		return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, emptyUrls(v)]));
	}
	return isUrl(value) ? '' : value;
}

function* walk(value, trail = []) {
	if (Array.isArray(value)) {
		for (const [i, v] of value.entries()) {
			yield { key: null, value: v, trail: [...trail, i] };
			yield* walk(v, [...trail, i]);
		}
	} else if (isObject(value)) {
		for (const [k, v] of Object.entries(value)) {
			yield { key: k, value: v, trail: [...trail, k] };
			yield* walk(v, [...trail, k]);
		}
	}
}

// Upstream product.json in, Brainstem product.json out: removals first, then the overlay, then the
// inert AI descriptor. Returns what changed so the build can report it.
export function mergeProduct(upstream, overlayProduct, spec) {
	const product = structuredClone(upstream);
	const removed = [];
	for (const key of [...Object.keys(spec.remove), ...spec.forbidden_keys]) {
		if (key in product) {
			delete product[key];
			removed.push(key);
		}
	}
	const merged = deepMerge(product, overlayProduct);
	const neutralized = [];
	for (const key of Object.keys(spec.neutralize)) {
		if (key in merged) {
			merged[key] = emptyUrls(merged[key]);
			neutralized.push(key);
		}
	}
	return { product: merged, removed, neutralized };
}

// Every reason the product is not a Brainstem product, as plain sentences (empty when it is).
export function validateProduct(product, spec) {
	const problems = [];
	const inert = new Set(Object.keys(spec.neutralize));
	const forbidden = new Set(spec.forbidden_keys);
	for (const { key, value, trail } of walk(product)) {
		const where = trail.join('.');
		const inInert = inert.has(trail[0]);
		if (key !== null && forbidden.has(key) && !(inInert && trail.length > 1)) {
			problems.push(`forbidden key ${where}`);
		}
		if (key !== null && !inInert) {
			const lower = key.toLowerCase();
			for (const pattern of spec.forbidden_key_patterns) {
				if (lower.includes(pattern)) {
					problems.push(`key ${where} matches forbidden pattern "${pattern}"`);
				}
			}
		}
		if (isUrl(value)) {
			if (inInert) {
				problems.push(`inert descriptor still holds an endpoint at ${where}`);
			} else if (!spec.allowed_url_prefixes.some(prefix => value.startsWith(prefix))) {
				problems.push(`endpoint outside the allowed prefixes at ${where}: ${value}`);
			}
		}
		if (typeof value === 'string' && !inInert) {
			const lower = value.toLowerCase();
			for (const text of spec.forbidden_branding_text) {
				if (lower.includes(text)) {
					problems.push(`value at ${where} carries "${text}"`);
				}
			}
		}
	}
	for (const key of spec.branding_keys) {
		if (typeof product[key] !== 'string' || !product[key]) {
			problems.push(`branding key ${key} is missing`);
		}
	}
	if (product.nameShort !== 'Brainstem' || product.nameLong !== 'Brainstem') {
		problems.push('the product is not named Brainstem');
	}
	// The app's own commands may never take a name another program installs, such as the grail's launcher.
	for (const key of spec.command_keys ?? []) {
		const name = String(product[key] ?? '').toLowerCase().replace(/\.(cmd|ps1|exe|desktop)$/, '');
		const why = Object.hasOwn(spec.reserved_commands ?? {}, name) ? spec.reserved_commands[name] : undefined;
		if (why) {
			problems.push(`${key} is "${product[key]}", which is reserved: ${why}`);
		}
	}
	if (Array.isArray(product.builtInExtensions) && product.builtInExtensions.length) {
		problems.push('builtInExtensions still downloads extensions');
	}
	if ('extensionsGallery' in product) {
		problems.push('an extension gallery is configured');
	}
	return problems;
}

// Anchored text edits: each `find` must occur exactly once in a pristine checkout.
export function applyEdits(checkout, edits) {
	const done = [];
	for (const edit of edits) {
		const file = path.join(checkout, edit.file);
		const text = fs.readFileSync(file, 'utf8');
		// A checkout with CRLF line endings (Git for Windows' default) gets the anchors in its own endings.
		const eol = text.includes('\r\n') ? (value => value.replace(/\r?\n/g, '\r\n')) : (value => value);
		const find = eol(edit.find), replace = eol(edit.replace);
		const count = text.split(find).length - 1;
		if (count !== 1) {
			throw new Error(`edit anchor for ${edit.file} found ${count} times (expected 1): ${edit.why}`);
		}
		fs.writeFileSync(file, text.replace(find, () => replace));
		done.push(`${edit.file}: ${edit.why}`);
	}
	return done;
}

// What the Brainstem needs from the fork: the overlay may not remove it, and the checkout must have it.
export function keepProblems(overlay, checkout) {
	const problems = [];
	for (const [kept, why] of Object.entries(overlay.keep_paths ?? {})) {
		for (const removed of Object.keys(overlay.remove_paths)) {
			if (removed === kept || removed.startsWith(`${kept}/`) || kept.startsWith(`${removed}/`)) {
				problems.push(`${removed} is removed, but ${kept} must stay: ${why}`);
			}
		}
		if (checkout && !fs.existsSync(path.join(checkout, kept))) {
			problems.push(`${kept} is missing from the checkout, but must stay: ${why}`);
		}
	}
	return problems;
}

const COPY_SKIP = new Set(['out', 'node_modules', '.test-tmp', '.DS_Store']);

export function copyTree(from, to) {
	fs.rmSync(to, { recursive: true, force: true });
	fs.mkdirSync(to, { recursive: true });
	for (const entry of fs.readdirSync(from, { withFileTypes: true })) {
		if (COPY_SKIP.has(entry.name)) {
			continue;
		}
		const src = path.join(from, entry.name), dst = path.join(to, entry.name);
		if (entry.isSymbolicLink()) {
			throw new Error(`refusing to copy a link: ${src}`);
		}
		if (entry.isDirectory()) {
			copyTree(src, dst);
		} else if (entry.isFile()) {
			fs.copyFileSync(src, dst);
		}
	}
}

function headCommit(checkout) {
	return execFileSync('git', ['-C', checkout, 'rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
}

export function applyOverlay({ checkout, expectCommit, webviewPort, appDir = APP_DIR }) {
	const overlay = loadOverlay(appDir);
	if (expectCommit) {
		const head = headCommit(checkout);
		if (head !== expectCommit) {
			throw new Error(`refusing: the checkout is at ${head}, the pin is ${expectCommit}`);
		}
	}
	const report = { commit: expectCommit || null, removed_paths: [], kept_paths: Object.keys(overlay.keep_paths ?? {}), edits: [], product: {}, extensions: [], branding: [] };

	for (const rel of Object.keys(overlay.remove_paths)) {
		const target = path.join(checkout, rel);
		if (fs.existsSync(target)) {
			fs.rmSync(target, { recursive: true, force: true });
			report.removed_paths.push(rel);
		}
	}

	const missing = keepProblems(overlay, checkout);
	if (missing.length) {
		throw new Error('the overlay must keep what the Brainstem needs:\n  ' + missing.join('\n  '));
	}

	report.edits = applyEdits(checkout, overlay.edits);

	const productFile = path.join(checkout, 'product.json');
	const { product, removed, neutralized } = mergeProduct(
		readJson(productFile), readJson(path.join(appDir, overlay.product.overlay)), overlay.product);
	const problems = validateProduct(product, overlay.product);
	if (problems.length) {
		throw new Error('the merged product.json is not clean:\n  ' + problems.join('\n  '));
	}
	fs.writeFileSync(productFile, JSON.stringify(product, null, '\t') + '\n');
	// The fork's from-source launches read product.overrides.json (gitignored upstream); the browser path
	// takes its product names from nothing else, so it gets the same Brainstem product.
	const devProduct = { ...product };
	if (webviewPort) {
		devProduct.webviewContentExternalBaseUrlTemplate = `http://{{uuid}}.localhost:${webviewPort}/`;
	}
	fs.writeFileSync(path.join(checkout, 'product.overrides.json'), JSON.stringify(devProduct, null, '\t') + '\n');
	report.product = { removed, neutralized };

	for (const rel of Object.keys(overlay.builtin_extensions)) {
		copyTree(path.join(appDir, rel), path.join(checkout, rel));
		report.extensions.push(rel);
	}

	for (const [rel, kind] of Object.entries(overlay.branding.generated)) {
		const target = path.join(checkout, rel);
		fs.mkdirSync(path.dirname(target), { recursive: true });
		fs.writeFileSync(target, renderAsset(kind));
		report.branding.push(rel);
	}
	return report;
}

function args(argv) {
	const out = {};
	for (let i = 0; i < argv.length; i++) {
		if (argv[i].startsWith('--')) {
			out[argv[i].slice(2)] = argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : true;
		}
	}
	return out;
}

function main() {
	const opts = args(process.argv.slice(2));
	const overlay = loadOverlay();
	if (opts['merge-product']) {
		const { product, removed, neutralized } = mergeProduct(
			readJson(opts['merge-product']), readJson(path.join(APP_DIR, overlay.product.overlay)), overlay.product);
		const problems = validateProduct(product, overlay.product);
		const text = JSON.stringify(product, null, '\t') + '\n';
		if (opts.out) {
			fs.writeFileSync(opts.out, text);
		} else {
			process.stdout.write(text);
		}
		console.error(`removed: ${removed.join(', ') || 'nothing'}; inert: ${neutralized.join(', ') || 'nothing'}`);
		problems.forEach(p => console.error(`PROBLEM ${p}`));
		return problems.length ? 1 : 0;
	}
	if (opts['validate-product']) {
		const problems = validateProduct(readJson(opts['validate-product']), overlay.product);
		problems.forEach(p => console.error(`PROBLEM ${p}`));
		console.log(problems.length ? `not clean: ${problems.length} problem(s)` : 'clean: no telemetry, AI endpoints, gallery or vendor branding');
		return problems.length ? 1 : 0;
	}
	if (!opts.checkout || opts.checkout === true) {
		console.error('usage: apply-overlay.mjs --checkout <dir> [--expect-commit <sha>] [--report <file>] [--webview-port <port>]');
		return 2;
	}
	const report = applyOverlay({ checkout: path.resolve(opts.checkout), expectCommit: opts['expect-commit'], webviewPort: /^\d+$/.test(opts['webview-port'] || '') ? opts['webview-port'] : undefined });
	if (opts.report) {
		fs.writeFileSync(opts.report, JSON.stringify(report, null, 2) + '\n');
	}
	console.log(`overlay applied: removed ${report.removed_paths.length} path(s), kept ${report.kept_paths.join(', ') || 'nothing named'}, ${report.edits.length} edit(s), `
		+ `product keys removed [${report.product.removed.join(', ')}], inert [${report.product.neutralized.join(', ')}], `
		+ `${report.extensions.length} built-in extension(s), ${report.branding.length} branding file(s)`);
	return 0;
}

const realOrNothing = file => {
	try {
		return fs.realpathSync(file);
	} catch {
		return undefined;
	}
};

// Run as a script (also through a link to it), not when imported by the tests.
if (process.argv[1] && realOrNothing(process.argv[1]) === realOrNothing(fileURLToPath(import.meta.url))) {
	try {
		process.exitCode = main();
	} catch (error) {
		console.error(`apply-overlay: ${error.message}`);
		process.exitCode = 1;
	}
}
