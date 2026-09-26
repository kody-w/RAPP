// Runs the Hive agent's own checker (`hive_agent.py check <hive>`) and reads its verdict. The checker is
// the file named by rapp.hiveAgentPath; it may never live inside a Hive or a reference, so nothing from a
// Hive is ever run.
import { execFile } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import { fileInside } from './hives';

export type CheckState = 'verified' | 'refused' | 'failed' | 'not-configured' | 'checking';

export interface CheckResult {
	readonly state: CheckState;
	readonly summary: string;
	readonly output: string;
	/** The Python given could not be started at all (so the next one may be tried). */
	readonly notStarted?: boolean;
}

export const NOT_CONFIGURED: CheckResult = { state: 'not-configured', summary: 'checker not configured', output: '' };

/**
 * Text from a Hive (its name, the checker's words) as a notification shows it: the host turns [label](target)
 * there into a link, a command link included, so no such link is left to form.
 */
export function noticeText(text: string): string {
	return text.replace(/\]\(/g, '] (');
}

// Why the configured checker may not run, or undefined when it may.
export function checkerRefusal(agentPath: string, python: string, forbiddenRoots: readonly string[]): string | undefined {
	if (!path.isAbsolute(agentPath)) {
		return 'rapp.hiveAgentPath must be a full path to hive_agent.py';
	}
	let stat: fs.Stats;
	try {
		stat = fs.statSync(agentPath);
	} catch {
		return `the Hive agent is not at ${agentPath}`;
	}
	if (!stat.isFile() || !agentPath.endsWith('.py')) {
		return 'rapp.hiveAgentPath must name the Hive agent\'s .py file';
	}
	if (forbiddenRoots.some(root => fileInside(agentPath, root))) {
		return 'the checker may not live inside a Hive or a reference';
	}
	if (!/^[A-Za-z0-9._-]+$/.test(python) && !path.isAbsolute(python)) {
		return 'rapp.pythonPath must be a command name such as python3, or a full path';
	}
	if (path.isAbsolute(python) && forbiddenRoots.some(root => fileInside(python, root))) {
		return 'rapp.pythonPath may not point inside a Hive or a reference';
	}
	return undefined;
}

export function readVerdict(code: number | null, stdout: string, stderr: string): CheckResult {
	const lines = `${stdout}\n${stderr}`.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
	const output = `${stdout}${stderr ? `\n${stderr}` : ''}`.trim();
	const verified = lines.find(l => l.startsWith('verified:'));
	if (code === 0 && verified) {
		return { state: 'verified', summary: verified, output };
	}
	const refused = lines.find(l => l.startsWith('REFUSED'));
	if (refused) {
		return { state: 'refused', summary: refused, output };
	}
	return { state: 'failed', summary: lines[lines.length - 1] || `the checker exited with ${code}`, output };
}

/**
 * The Pythons the checker may run with, in order: the setting, and on Windows, when that is the default python3,
 * python after it (the traditional Windows installer has no python3, and its python3 is a store stand-in that exits
 * 9009), as the grail's own start.ps1 and the agent card's helper do.
 */
export function checkerPythons(setting: string, platform: NodeJS.Platform = process.platform): string[] {
	return platform === 'win32' && setting === 'python3' ? ['python3', 'python'] : [setting];
}

export function runCheck(python: string, agentPath: string, hivePath: string, timeoutMs = 60000): Promise<CheckResult> {
	// The verdict may not depend on ambient git settings (GIT_DIR, GIT_CONFIG_*, ...); the agent passes the
	// git flags it needs itself.
	const env: NodeJS.ProcessEnv = Object.fromEntries(Object.entries(process.env).filter(([name]) => !/^GIT_/i.test(name)));
	env.PYTHONDONTWRITEBYTECODE = '1';
	return new Promise(resolve => {
		execFile(python, ['-B', agentPath, 'check', hivePath], {
			cwd: path.dirname(agentPath),
			timeout: timeoutMs,
			maxBuffer: 1024 * 1024,
			windowsHide: true,
			env,
		}, (error, stdout, stderr) => {
			if (!error) {
				resolve(readVerdict(0, String(stdout), String(stderr)));
			} else if (typeof error.code === 'number') {
				// 9009: Windows found no such program (or only its store stand-in).
				resolve({ ...readVerdict(error.code, String(stdout), String(stderr)), ...(process.platform === 'win32' && error.code === 9009 ? { notStarted: true } : {}) });
			} else {
				resolve({ state: 'failed', summary: error.killed ? 'the checker ran out of time' : error.message, output: String(stderr || ''), ...(error.code === 'ENOENT' ? { notStarted: true } : {}) });
			}
		});
	});
}
