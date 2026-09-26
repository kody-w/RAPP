// The RAPP Workspace: the Brainstem's agents/ folder, in the native Explorer.
//
// Only the top of agents/ is live. load_agents() in rapp_brainstem/brainstem.py globs
// os.path.join(AGENTS_PATH, "*_agent.py"), a flat glob (lines 1202-1205 at brainstem-v0.6.9, the LTS pin;
// lines 1832-1835 at brainstem-v0.6.16, the newest channel), and imports every match on every /chat and
// /health, and once as it starts. An agent file at the top of agents/ runs;
// one in any folder never does. So dragging a file to the top makes it live, and dragging it into any
// folder takes it out. The app moves nothing itself: the Explorer does, as the person drags, and the
// Explorer's own Undo reverses a move. basic_agent.py, the base class every agent builds on, is hidden
// and read-only.
import * as path from 'path';
import { leaves } from './hives';

export const BASE_AGENT = 'basic_agent.py';
export const AGENT_SUFFIX = '_agent.py';

// The loader's glob follows the platform: Python's fnmatch ignores case on Windows (os.path.normcase), and
// only there.
const folded = (name: string, platform: NodeJS.Platform) => (platform === 'win32' ? name.toLowerCase() : name);

/** What the loader's *_agent.py glob matches: hidden files never match a glob's *. */
export function isAgentFileName(name: string, platform: NodeJS.Platform = process.platform): boolean {
	return folded(name, platform).endsWith(AGENT_SUFFIX) && !name.startsWith('.');
}

/** Whether a file name is the base class, basic_agent.py, as this platform's file system names it. */
export function isBaseAgent(name: string, platform: NodeJS.Platform = process.platform): boolean {
	return folded(name, platform) === BASE_AGENT;
}

/** The file watcher's pattern for agent files: either case on Windows, as the loader matches them there. */
export function agentGlob(platform: NodeJS.Platform = process.platform): string {
	return platform === 'win32' ? '*_[aA][gG][eE][nN][tT].[pP][yY]' : `*${AGENT_SUFFIX}`;
}

/**
 * Where a file sits in agents/: 'live' for an agent file at the top, 'folder' for one kept in a folder,
 * undefined for anything else (the base class, hidden and cache files, files outside agents/).
 */
export function agentPlace(root: string, file: string, platform: NodeJS.Platform = process.platform): 'live' | 'folder' | undefined {
	const rel = path.relative(root, file);
	if (!rel || leaves(rel)) {
		return undefined;
	}
	const parts = rel.split(path.sep);
	const name = parts[parts.length - 1] ?? '';
	if (!isAgentFileName(name, platform) || isBaseAgent(name, platform) || parts.some(p => p.startsWith('.') || p === '__pycache__' || p === 'node_modules')) {
		return undefined;
	}
	return parts.length === 1 ? 'live' : 'folder';
}

const listed = (names: readonly string[]) => (names.length <= 2 ? names.join(' and ') : `${names.length} agents`);

/** The status-bar note for agents that became live and agents that stopped being live, or undefined for none. */
export function liveMessage(cameLive: readonly string[], leftLive: readonly string[]): string | undefined {
	const notes: string[] = [];
	if (cameLive.length) {
		notes.push(`${listed(cameLive)} ${cameLive.length === 1 ? 'is' : 'are'} live`);
	}
	if (leftLive.length) {
		notes.push(`${listed(leftLive)} ${leftLive.length === 1 ? 'is' : 'are'} no longer live`);
	}
	return notes.length ? notes.join('; ') : undefined;
}
