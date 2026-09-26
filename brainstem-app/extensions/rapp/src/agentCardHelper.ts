// Runs the agent card's Python helper (python/agent_card.py): the agent's source goes in on stdin and one JSON
// object comes out. The helper parses the source and never imports or runs it; this side bounds it in size,
// time and output, and gives the Python it runs no inherited PYTHON* settings (-I), no site packages or .pth
// hooks (-S) and no bytecode files (-B).
import { spawn } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import { fileInside } from './hives';
import type { FolderSource } from './startup';

export const MAX_SOURCE = 1024 * 1024;
export const HELPER_TIMEOUT_MS = 3000;
const MAX_OUTPUT = 1024 * 1024;
const MAX_LOCAL = 500;
const IDENTIFIER = /^[A-Za-z_][A-Za-z0-9_]*$/;

export type HelperFailure = 'too-big' | 'timeout' | 'no-python' | 'failed';
export type HelperOutcome = { readonly ok: true; readonly facts: unknown } | { readonly ok: false; readonly reason: HelperFailure };

/**
 * The Pythons to try, in order: the Brainstem's own, the one that will load the agent, so its syntax and its
 * standard library are the ones that count. That is ~/.brainstem/venv, which the Brainstem's start.sh
 * (BRAINSTEM_HOME/venv/bin/python) and start.ps1 (.brainstem\venv\Scripts\python.exe) run it with; then a
 * .venv in the Brainstem's folder, when that folder is the setting's or the default (never one only /health
 * reported: that answer is unauthenticated, and must not choose what runs); then the rapp.pythonPath setting,
 * when it is a command name or a full path (as the Hive checker takes it); then python3. A Python given by full
 * path is never one inside a Hive or a reference (`forbidden`); a command name is looked up on PATH.
 */
export function pythonCandidates(options: { readonly home: string; readonly brainstemFolder?: string; readonly folderSource?: FolderSource; readonly setting: string; readonly forbidden?: readonly string[]; readonly platform?: NodeJS.Platform; readonly exists?: (file: string) => boolean }): string[] {
	const { home, brainstemFolder, folderSource, setting, forbidden = [], platform = process.platform, exists = fs.existsSync } = options;
	const paths = platform === 'win32' ? path.win32 : path.posix;
	const venvPython = (venv: string) => (platform === 'win32' ? paths.join(venv, 'Scripts', 'python.exe') : paths.join(venv, 'bin', 'python'));
	const allowed = (python: string) => !forbidden.some(root => fileInside(python, root));
	const found: string[] = [];
	const ownVenv = brainstemFolder && folderSource !== 'health' ? venvPython(paths.join(brainstemFolder, '.venv')) : undefined;
	for (const own of [home && venvPython(paths.join(home, '.brainstem', 'venv')), ownVenv]) {
		if (own && !found.includes(own) && exists(own) && allowed(own)) {
			found.push(own);
		}
	}
	const chosen = setting.trim();
	const usable = /^[A-Za-z0-9._-]+$/.test(chosen) || (paths.isAbsolute(chosen) && allowed(chosen));
	for (const candidate of [usable ? chosen : '', 'python3', ...(platform === 'win32' ? ['python'] : [])]) {
		if (candidate && !found.includes(candidate)) {
			found.push(candidate);
		}
	}
	return found;
}

/**
 * Module names the Brainstem's own folders provide (it puts its folder and agents/ on sys.path), so an import
 * of one is not a package to install. Only names are read, never the files.
 */
export function localModuleNames(folders: readonly (string | undefined)[]): string[] {
	const names = new Set<string>();
	for (const folder of folders) {
		if (!folder) {
			continue;
		}
		let entries: fs.Dirent[];
		try {
			entries = fs.readdirSync(folder, { withFileTypes: true });
		} catch {
			continue;
		}
		for (const entry of entries.slice(0, 5000)) {
			const stem = entry.isFile() && entry.name.endsWith('.py') ? entry.name.slice(0, -3) : entry.isDirectory() ? entry.name : '';
			if (IDENTIFIER.test(stem)) {
				names.add(stem);
			}
		}
	}
	return [...names].sort().slice(0, MAX_LOCAL);
}

// Only what a Python needs to start; nothing from this app's environment is handed on.
function helperEnv(): NodeJS.ProcessEnv {
	const env: NodeJS.ProcessEnv = { PATH: process.env.PATH ?? '' };
	for (const key of ['SystemRoot', 'SYSTEMROOT', 'WINDIR']) {
		if (process.env[key]) {
			env[key] = process.env[key];
		}
	}
	return env;
}

function runOnce(python: string, script: string, local: readonly string[], input: Buffer, timeoutMs: number): Promise<HelperOutcome> {
	return new Promise(resolve => {
		let done = false;
		const finish = (outcome: HelperOutcome) => {
			if (!done) {
				done = true;
				clearTimeout(timer);
				resolve(outcome);
			}
		};
		const args = ['-I', '-S', '-B', script, ...local.filter(name => IDENTIFIER.test(name)).flatMap(name => ['--local', name])];
		let child: ReturnType<typeof spawn>;
		try {
			child = spawn(python, args, { cwd: path.dirname(script), env: helperEnv(), stdio: ['pipe', 'pipe', 'ignore'], windowsHide: true, shell: false });
		} catch {
			resolve({ ok: false, reason: 'no-python' });
			return;
		}
		const timer = setTimeout(() => {
			child.kill('SIGKILL');
			finish({ ok: false, reason: 'timeout' });
		}, timeoutMs);
		const chunks: Buffer[] = [];
		let size = 0;
		child.stdout?.on('data', (chunk: Buffer) => {
			size += chunk.length;
			if (size > MAX_OUTPUT) {
				child.kill('SIGKILL');
				finish({ ok: false, reason: 'failed' });
				return;
			}
			chunks.push(chunk);
		});
		child.on('error', (error: NodeJS.ErrnoException) => finish({ ok: false, reason: error.code === 'ENOENT' || error.code === 'EACCES' ? 'no-python' : 'failed' }));
		child.on('close', () => {
			let facts: unknown;
			try {
				facts = JSON.parse(Buffer.concat(chunks).toString('utf8'));
			} catch {
				facts = undefined;
			}
			const ours = typeof facts === 'object' && facts !== null && (facts as { schema?: unknown }).schema === 'rapp-agent-card/1';
			finish(ours ? { ok: true, facts } : { ok: false, reason: 'failed' });
		});
		// A helper that stops reading early (the size cap) closes its stdin; that is not an error here.
		child.stdin?.on('error', () => undefined);
		child.stdin?.end(input);
	});
}

/**
 * Reads one agent with the helper, trying each Python in turn until one answers: its bytes as they are on disk,
 * which the helper decodes as Python would, or its text (unsaved edits) as UTF-8. A Python that does not start,
 * or starts and gives no answer (such as the Windows store's python3 stand-in), is passed over.
 */
export async function readAgent(source: string | Uint8Array, options: { readonly pythons: readonly string[]; readonly script: string; readonly local?: readonly string[]; readonly timeoutMs?: number }): Promise<HelperOutcome> {
	const input = typeof source === 'string' ? Buffer.from(source, 'utf8') : Buffer.from(source);
	if (input.length > MAX_SOURCE) {
		return { ok: false, reason: 'too-big' };
	}
	let last: HelperOutcome = { ok: false, reason: 'no-python' };
	for (const python of options.pythons) {
		last = await runOnce(python, options.script, options.local ?? [], input, options.timeoutMs ?? HELPER_TIMEOUT_MS);
		if (last.ok || last.reason === 'timeout') {
			return last;
		}
	}
	return last;
}
