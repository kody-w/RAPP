import * as vscode from 'vscode';
import { CheckResult, NOT_CONFIGURED } from './checker';
import { Entry, Hive, listFolder, listHives, readHive } from './hives';

export type HiveNode =
	| { readonly kind: 'hive'; readonly hive: Hive }
	| { readonly kind: 'rules'; readonly path: string }
	| { readonly kind: 'section'; readonly hive: Hive; readonly section: 'members' | 'requests' | 'rooms' }
	| { readonly kind: 'member'; readonly name: string; readonly keys: readonly Entry[] }
	| { readonly kind: 'request'; readonly name: string; readonly device: string; readonly path: string }
	| { readonly kind: 'entry'; readonly entry: Entry }
	| { readonly kind: 'message'; readonly text: string; readonly tooltip?: string };

const SECTIONS = {
	members: { label: 'Members', icon: 'organization' },
	requests: { label: 'Waiting requests', icon: 'mail' },
	rooms: { label: 'Rooms', icon: 'comment-discussion' },
} as const;

const CHECK_LOOK: Record<CheckResult['state'], { text: string; icon: string; color?: string }> = {
	'verified': { text: 'verified', icon: 'verified-filled', color: 'testing.iconPassed' },
	'refused': { text: 'refused', icon: 'error', color: 'testing.iconFailed' },
	'failed': { text: 'check failed', icon: 'warning', color: 'problemsWarningIcon.foreground' },
	'not-configured': { text: 'checker not configured', icon: 'shield' },
	'checking': { text: 'checking…', icon: 'loading~spin' },
};

/** What the Hives view says above its empty tree, where it wraps (a tree row would be cut off). */
export const NO_HIVES = 'No Hives on this device yet. Ask your Brainstem to create or join one.';

// The Hives on this device, read-only: members, waiting requests and rooms. Opening a file opens it in
// the editor; nothing here writes to a Hive.
export class HivesTreeProvider implements vscode.TreeDataProvider<HiveNode> {
	private readonly changed = new vscode.EventEmitter<HiveNode | undefined>();
	readonly onDidChangeTreeData = this.changed.event;

	constructor(
		private readonly home: () => string,
		private readonly checkOf: (hiveName: string) => CheckResult | undefined,
	) { }

	refresh(): void {
		this.changed.fire(undefined);
	}

	hives(): Hive[] {
		const home = this.home();
		return listHives(home).map(name => readHive(home, name));
	}

	getChildren(node?: HiveNode): HiveNode[] {
		if (!node) {
			return this.hives().map(hive => ({ kind: 'hive', hive }));
		}
		switch (node.kind) {
			case 'hive': {
				const sections: HiveNode[] = (['members', 'requests', 'rooms'] as const).map(section => ({ kind: 'section', hive: node.hive, section }));
				return node.hive.rules ? [{ kind: 'rules', path: node.hive.rules }, ...sections] : sections;
			}
			case 'section':
				if (node.section === 'members') {
					return node.hive.members.map(m => ({ kind: 'member', name: m.name, keys: m.keys }));
				}
				if (node.section === 'requests') {
					return node.hive.requests.map(r => ({ kind: 'request', name: r.name, device: r.device, path: r.path }));
				}
				return node.hive.rooms.map(entry => ({ kind: 'entry', entry }));
			case 'member':
				return node.keys.map(entry => ({ kind: 'entry', entry }));
			case 'entry': {
				if (node.entry.kind !== 'folder') {
					return [];
				}
				const listing = listFolder(node.entry.path);
				const children: HiveNode[] = listing.entries.map(entry => ({ kind: 'entry', entry }));
				return listing.more ? [...children, { kind: 'message', text: `… and ${listing.more} more` }] : children;
			}
			default:
				return [];
		}
	}

	getTreeItem(node: HiveNode): vscode.TreeItem {
		const { TreeItemCollapsibleState: State } = vscode;
		switch (node.kind) {
			case 'hive': {
				const check = this.checkOf(node.hive.name) ?? NOT_CONFIGURED;
				const look = CHECK_LOOK[check.state];
				const item = new vscode.TreeItem(node.hive.name, State.Expanded);
				item.description = look.text;
				item.iconPath = new vscode.ThemeIcon(look.icon, look.color ? new vscode.ThemeColor(look.color) : undefined);
				item.tooltip = [node.hive.path, check.summary, check.output && check.output !== check.summary ? `\n${check.output}` : ''].filter(Boolean).join('\n');
				item.contextValue = 'rapp.hive';
				return item;
			}
			case 'rules':
				return this.fileItem('HIVE.md', node.path, 'the rules');
			case 'section': {
				const count = node.section === 'members' ? node.hive.members.length : node.section === 'requests' ? node.hive.requests.length : node.hive.rooms.length;
				const item = new vscode.TreeItem(SECTIONS[node.section].label, count ? State.Collapsed : State.None);
				item.description = count ? String(count) : 'none';
				item.iconPath = new vscode.ThemeIcon(SECTIONS[node.section].icon);
				item.contextValue = `rapp.section.${node.section}`;
				return item;
			}
			case 'member': {
				const item = new vscode.TreeItem(node.name, State.Collapsed);
				item.description = node.keys.length === 1 ? '1 device' : `${node.keys.length} devices`;
				item.iconPath = new vscode.ThemeIcon('account');
				item.contextValue = 'rapp.member';
				return item;
			}
			case 'request': {
				const item = this.fileItem(node.name, node.path, node.device);
				item.iconPath = new vscode.ThemeIcon('mail');
				item.contextValue = 'rapp.request';
				return item;
			}
			case 'entry':
				if (node.entry.kind === 'folder') {
					const item = new vscode.TreeItem(vscode.Uri.file(node.entry.path), State.Collapsed);
					item.label = node.entry.name;
					item.tooltip = node.entry.path;
					item.contextValue = 'rapp.folder';
					return item;
				}
				return this.fileItem(node.entry.name, node.entry.path);
			case 'message': {
				const item = new vscode.TreeItem(node.text, State.None);
				item.tooltip = node.tooltip;
				item.contextValue = 'rapp.message';
				return item;
			}
		}
	}

	private fileItem(label: string, file: string, description?: string): vscode.TreeItem {
		const uri = vscode.Uri.file(file);
		const item = new vscode.TreeItem(uri, vscode.TreeItemCollapsibleState.None);
		item.label = label;
		item.description = description;
		item.tooltip = file;
		item.contextValue = 'rapp.file';
		item.command = { command: 'vscode.open', title: 'Open', arguments: [uri] };
		return item;
	}
}
