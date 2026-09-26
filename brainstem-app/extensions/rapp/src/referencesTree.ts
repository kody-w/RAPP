import * as vscode from 'vscode';
import { listHives, readReferences, Reference } from './hives';
import * as path from 'path';

export type ReferenceNode =
	| { readonly kind: 'hive'; readonly name: string; readonly path: string }
	| { readonly kind: 'reference'; readonly reference: Reference }
	| { readonly kind: 'message'; readonly text: string; readonly tooltip?: string };

/** What the References view says above its empty tree. */
export const NO_REFERENCE_HIVES = 'No Hives on this device yet, so no references either.';

// Each Hive's pinned references on this device, by label. Read-only: labels show, full paths only on hover.
export class ReferencesTreeProvider implements vscode.TreeDataProvider<ReferenceNode> {
	private readonly changed = new vscode.EventEmitter<ReferenceNode | undefined>();
	readonly onDidChangeTreeData = this.changed.event;

	constructor(private readonly home: () => string) { }

	refresh(): void {
		this.changed.fire(undefined);
	}

	getChildren(node?: ReferenceNode): ReferenceNode[] {
		if (!node) {
			const home = this.home();
			return listHives(home).map(name => ({ kind: 'hive', name, path: path.join(home, name) }));
		}
		if (node.kind === 'hive') {
			const references = readReferences(node.path);
			return references.length
				? references.map(reference => ({ kind: 'reference', reference }))
				: [{ kind: 'message', text: 'No references pinned', tooltip: 'Ask your Brainstem to pin a folder of notes as a reference.' }];
		}
		return [];
	}

	getTreeItem(node: ReferenceNode): vscode.TreeItem {
		if (node.kind === 'hive') {
			const item = new vscode.TreeItem(node.name, vscode.TreeItemCollapsibleState.Expanded);
			item.iconPath = new vscode.ThemeIcon('repo');
			item.contextValue = 'rapp.referenceHive';
			return item;
		}
		if (node.kind === 'reference') {
			const item = new vscode.TreeItem(node.reference.label, vscode.TreeItemCollapsibleState.None);
			item.description = node.reference.present ? undefined : 'missing';
			item.tooltip = `${node.reference.path}\nRead-only: never changed, trusted, run or loaded.`;
			item.iconPath = new vscode.ThemeIcon(node.reference.present ? 'book' : 'warning');
			item.contextValue = 'rapp.reference';
			return item;
		}
		const item = new vscode.TreeItem(node.text, vscode.TreeItemCollapsibleState.None);
		item.tooltip = node.tooltip;
		item.contextValue = 'rapp.message';
		return item;
	}
}
