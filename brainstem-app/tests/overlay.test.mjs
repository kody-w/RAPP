// The product overlay: no telemetry, AI endpoints, experiments, gallery or vendor branding survive the merge.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { test } from 'node:test';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { APP_DIR, applyEdits, keepProblems, loadOverlay, mergeProduct, readJson, validateProduct } from '../scripts/apply-overlay.mjs';
import { renderAsset } from '../scripts/branding.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const overlay = loadOverlay();
const overlayProduct = readJson(path.join(APP_DIR, 'product.json'));
const upstream = readJson(path.join(here, 'fixtures', 'upstream-product.json'));
const { product, removed, neutralized } = mergeProduct(upstream, overlayProduct, overlay.product);

function* strings(value, trail = []) {
	if (typeof value === 'string') {
		yield [trail.join('.'), value];
	} else if (value && typeof value === 'object') {
		for (const [k, v] of Object.entries(value)) {
			yield* strings(v, [...trail, k]);
		}
	}
}

test('the merged product is clean by the overlay rules', () => {
	assert.deepEqual(validateProduct(product, overlay.product), []);
});

test('the validator bites: upstream as it is does not pass', () => {
	const problems = validateProduct(upstream, overlay.product);
	for (const expected of [/forbidden key enableTelemetry/, /forbidden key extensionsGallery/, /agentsTelemetryAppName/, /builtInExtensions still downloads/, /not named Brainstem/]) {
		assert.ok(problems.some(p => expected.test(p)), `expected a problem matching ${expected}`);
	}
});

test('no telemetry, crash reporting, experiment, AI voice or gallery keys remain', () => {
	for (const key of ['enableTelemetry', 'aiConfig', 'crashReporter', 'tasConfig', 'extensionsGallery', 'voiceWsUrl',
		'agentsTelemetryAppName', 'trustedExtensionAuthAccess', 'onboardingKeymaps', 'onboardingThemes', 'updateUrl', 'documentationUrl']) {
		assert.ok(!(key in product), `${key} survived`);
		assert.ok(removed.includes(key), `${key} was not reported as removed`);
	}
	const keys = JSON.stringify(Object.keys(product)).toLowerCase();
	for (const word of ['telemetry', 'experiment', 'crash', 'gallery', 'voice']) {
		assert.ok(!keys.includes(word), `a key mentions ${word}`);
	}
});

test('no MS-only extension downloads and no auto-updated AI extension', () => {
	assert.deepEqual(product.builtInExtensions, []);
	assert.deepEqual(product.builtInExtensionsEnabledWithAutoUpdates, []);
});

test('the AI descriptor the host needs at startup is inert: every endpoint is empty', () => {
	assert.deepEqual(neutralized, ['defaultChatAgent']);
	for (const [where, value] of strings(product.defaultChatAgent)) {
		assert.ok(!/:\/\//.test(value), `${where} still holds ${value}`);
	}
	assert.equal(product.defaultChatAgent.entitlementUrl, '');
	assert.equal(product.defaultChatAgent.tokenEntitlementUrl, '');
});

test('every remaining address points at kody-w/RAPP', () => {
	for (const [where, value] of strings(product)) {
		if (/:\/\//.test(value)) {
			assert.ok(value.startsWith('https://github.com/kody-w/RAPP/'), `${where} = ${value}`);
		}
	}
	assert.equal(product.reportIssueUrl, 'https://github.com/kody-w/RAPP/issues/new');
	assert.equal(product.licenseUrl, 'https://github.com/kody-w/RAPP/blob/main/LICENSE');
});

test('Brainstem is the only brand: no Microsoft trademarks or upstream product names', () => {
	assert.equal(product.nameShort, 'Brainstem');
	assert.equal(product.nameLong, 'Brainstem');
	assert.equal(product.applicationName, 'brainstem-app');
	assert.equal(product.dataFolderName, '.brainstem-app');
	assert.equal(product.urlProtocol, 'brainstem');
	assert.equal(product.darwinBundleIdentifier, 'io.github.kody-w.brainstem');
	assert.match(product.win32x64AppId, /^\{\{[0-9A-F-]{36}\}$/);
	const outsideInert = { ...product, defaultChatAgent: undefined };
	for (const [where, value] of strings(outsideInert)) {
		assert.ok(!/visual studio|vs ?code|microsoft|code - oss|code-oss|copilot/i.test(value), `${where} = ${value}`);
	}
});

test('the app\'s commands are brainstem-app, never the grail\'s brainstem launcher', () => {
	for (const source of [product, overlayProduct]) {
		assert.equal(source.applicationName, 'brainstem-app');
		assert.equal(source.serverApplicationName, 'brainstem-app-server');
		assert.equal(source.tunnelApplicationName, 'brainstem-app-tunnel');
		assert.equal(source.linuxDesktopName, 'brainstem-app');
		for (const key of overlay.product.command_keys) {
			assert.notEqual(String(source[key]).toLowerCase(), 'brainstem', key);
			assert.ok(String(source[key]).startsWith('brainstem-app'), `${key} = ${source[key]}`);
		}
	}
	assert.ok(Object.hasOwn(overlay.product.reserved_commands, 'brainstem'));
});

test('the display names, bundle id, data folder and URL protocol keep their names', () => {
	assert.equal(product.nameShort, 'Brainstem');
	assert.equal(product.nameLong, 'Brainstem');
	assert.equal(product.darwinBundleIdentifier, 'io.github.kody-w.brainstem');
	assert.equal(product.dataFolderName, '.brainstem-app');
	assert.equal(product.urlProtocol, 'brainstem');
});

test('the validator refuses the grail\'s launcher name for any of the app\'s commands', () => {
	for (const [key, value] of [['applicationName', 'brainstem'], ['serverApplicationName', 'Brainstem'],
		['tunnelApplicationName', 'brainstem.exe'], ['linuxDesktopName', 'brainstem.desktop'], ['applicationName', 'brainstem.cmd']]) {
		const problems = validateProduct({ ...product, [key]: value }, overlay.product);
		assert.ok(problems.some(p => p.startsWith(`${key} is "${value}", which is reserved`)), `${key}=${value}: ${problems.join('; ')}`);
	}
});

test('the committed overlay itself adds nothing forbidden', () => {
	const text = JSON.stringify(overlayProduct);
	assert.ok(!/extensionsGallery|telemetry|aiConfig|crashReporter|tasConfig/i.test(text));
	assert.ok(!/visual studio|vs ?code|microsoft|code - oss/i.test(text));
});

test('the pin names the fork, its upstream, the tag and the full commit', () => {
	const pin = readJson(path.join(APP_DIR, 'UPSTREAM.json'));
	assert.equal(pin.fork, 'https://github.com/kody-w/vscode');
	assert.equal(pin.upstream, 'microsoft/vscode');
	assert.equal(pin.tag, '1.139.0');
	assert.match(pin.commit, /^[0-9a-f]{40}$/);
	assert.equal(pin.commit, '2242ebbb54efeeb0129e08e919e7e8d43033cd83');
});

test('every overlay edit is anchored, explained and actually changes something', () => {
	assert.ok(overlay.edits.length > 0);
	for (const edit of overlay.edits) {
		assert.ok(edit.file && edit.find && typeof edit.replace === 'string' && edit.why, JSON.stringify(edit));
		assert.notEqual(edit.find, edit.replace, edit.file);
	}
	assert.ok(overlay.edits.some(e => e.file === 'build/gulpfile.extensions.ts' && e.replace.includes('extensions/rapp/tsconfig.json')));
});

test('the Simple Browser the Brainstem\'s web UI opens in is kept, and removing it stops the build', () => {
	assert.ok(overlay.keep_paths['extensions/simple-browser']);
	assert.deepEqual(keepProblems(overlay), []);
	const removing = { ...overlay, remove_paths: { ...overlay.remove_paths, 'extensions/simple-browser': 'no' } };
	assert.deepEqual(keepProblems(removing).map(p => p.split(':')[0]), ['extensions/simple-browser is removed, but extensions/simple-browser must stay']);
	assert.deepEqual(keepProblems(overlay, path.join(APP_DIR, 'tests')).map(p => p.split(':')[0]), ['extensions/simple-browser is missing from the checkout, but must stay']);
});

test('the host\'s integrated browser stays: nothing in the overlay removes or configures it away, and its one edit keeps a tab as it is', () => {
	assert.deepEqual(Object.keys(overlay.remove_paths).filter(p => /browser/i.test(p)), []);
	const browserEdits = overlay.edits.filter(e => /browserView|workbench\.browser\.|workbench\.desktop\.main/.test(`${e.file}\n${e.find}\n${e.replace}`));
	assert.deepEqual(browserEdits.map(e => e.file), ['src/vs/workbench/contrib/browserView/electron-browser/features/browserTabManagementFeatures.ts'], 'only the reuse branch of its Open command');
	// Focusing the Brainstem's tab (the reuse filter) must not reload it: the web UI keeps its conversation in the page.
	assert.match(browserEdits[0].find, /if \(options\.url\) \{\n\t+matchingEditor\.navigate\(options\.url\);/);
	assert.match(browserEdits[0].replace, /if \(options\.url && \(origin\(matchingEditor\.url\) !== origin\(options\.url\) \|\| matchingEditor\.model\?\.error\)\) \{\n\t+matchingEditor\.navigate\(options\.url\);/, 'another origin, or a tab whose last load failed, is still navigated to');
	assert.deepEqual(Object.keys(product).filter(k => /browser/i.test(k)), []);
	const defaults = readJson(path.join(APP_DIR, 'extensions', 'rapp', 'package.json')).contributes.configurationDefaults;
	assert.deepEqual(Object.keys(defaults).filter(k => /^workbench\.browser\./.test(k)), []);
});

test('the Git extension\'s empty-Explorer welcome keeps Clone Repository (shown when Git is on) but drops the link to the vendor\'s docs', () => {
	const dir = path.join(process.env.BRAINSTEM_TEST_TMP || path.join(APP_DIR, '.build', 'test-tmp'), `git-welcome-${process.pid}`);
	fs.rmSync(dir, { recursive: true, force: true });
	const edit = overlay.edits.find(e => e.file === 'extensions/git/package.json');
	const file = path.join(dir, edit.file);
	fs.mkdirSync(path.dirname(file), { recursive: true });
	const clone = '      {\n        "view": "explorer",\n        "contents": "%view.workbench.cloneRepository%",\n        "when": "config.git.enabled && git.state == initialized",\n        "group": "5_scm@1"\n      }';
	fs.writeFileSync(file, `{\n  "contributes": {\n    "viewsWelcome": [\n${clone}${edit.find}    ]\n  }\n}\n`);
	applyEdits(dir, [edit]);
	const welcome = JSON.parse(fs.readFileSync(file, 'utf8')).contributes.viewsWelcome;
	assert.deepEqual(welcome.map(w => [w.contents, w.when]), [['%view.workbench.cloneRepository%', 'config.git.enabled && git.state == initialized']], 'shown only when Git is on');
	fs.rmSync(dir, { recursive: true, force: true });
});

test('the built-in extension has one Brainstem container with its four views and the commands', () => {
	const manifest = readJson(path.join(APP_DIR, 'extensions', 'rapp', 'package.json'));
	const containers = manifest.contributes.viewsContainers.activitybar;
	assert.deepEqual(containers.map(c => c.title), ['Brainstem']);
	assert.deepEqual(manifest.contributes.views[containers[0].id].map(v => v.name), ['Brainstem', 'Hives', 'References', 'Organism']);
	const titles = manifest.contributes.commands.map(c => `${c.category}: ${c.title}`);
	for (const title of ['Brainstem: Ask', 'Hive: Check', 'Hive: Reveal in Finder/Explorer', 'Hive: Save changes (asks your Brainstem)',
		'Brainstem: Open your Brainstem', 'Brainstem: Start my Brainstem']) {
		assert.ok(titles.includes(title), title);
	}
	const settings = manifest.contributes.configuration.properties;
	assert.equal(settings['rapp.hiveAgentPath'].default, '');
	assert.equal(settings['rapp.brainstemFolder'].default, '');
	assert.equal(settings['rapp.openBrainstemOnStartup'].default, true);
	assert.equal(settings['rapp.showBrainstemUI'].default, true);
	for (const key of ['rapp.hiveAgentPath', 'rapp.pythonPath', 'rapp.brainstemUrl', 'rapp.brainstemFolder', 'rapp.agentsFolder', 'rapp.openBrainstemOnStartup', 'rapp.showBrainstemUI']) {
		assert.equal(settings[key].scope, 'machine', `${key} must not be settable by a workspace`);
	}
	assert.deepEqual(manifest.contributes.viewsWelcome.map(w => [w.view, w.when, w.group, w.contents.match(/\]\(command:[\w.]+\)/g)]), [
		['explorer', 'workbenchState == empty', '1_brainstem@1', ['](command:rapp.openBrainstem)', '](command:rapp.startBrainstem)']],
	]);
	assert.deepEqual(manifest.enabledApiProposals, ['contribViewsWelcome', 'workspaceTrust']);
	assert.equal(manifest.capabilities.untrustedWorkspaces.supported, true, 'the views work before the RAPP Workspace is trusted');
});

test('the Explorer is the RAPP Workspace: one drag moves an agent, the base class is hidden and read-only, and there is no separate view', () => {
	const manifest = readJson(path.join(APP_DIR, 'extensions', 'rapp', 'package.json'));
	const defaults = manifest.contributes.configurationDefaults;
	assert.equal(defaults['explorer.confirmDragAndDrop'], false);
	assert.deepEqual(defaults['files.exclude'], { 'basic_agent.py': true, '**/__pycache__': true, '**/*.pyc': true, '**/.pytest_cache': true, '**/.DS_Store': true });
	assert.deepEqual(defaults['files.readonlyInclude'], { 'basic_agent.py': true });
	assert.deepEqual(Object.keys(manifest.contributes.views), ['brainstem']);
	assert.deepEqual(manifest.contributes.commands.filter(c => /^rapp\.agents?\./.test(c.command)), []);
	assert.ok(!overlay.edits.some(e => /explorerViewlet\.ts$/.test(e.file)), 'the Explorer needs no view order of its own');
});

test('an agent file opens as its card: the default editor for *_agent.py, never for the base class, read by a stdlib-only helper that ships', () => {
	const dir = path.join(APP_DIR, 'extensions', 'rapp');
	const manifest = readJson(path.join(dir, 'package.json'));
	assert.deepEqual(manifest.contributes.customEditors, [
		{ viewType: 'rapp.agentCard', displayName: 'Agent card', selector: [{ filenamePattern: '**/*_agent.py' }], priority: 'default' },
		{ viewType: 'rapp.memoryCard', displayName: 'Memory card', selector: [{ filenamePattern: '**/.brainstem_data/**/memory.json' }, { filenamePattern: '**/.brainstem_data/**/user_memory.json' }], priority: 'default' },
		{ viewType: 'rapp.collectionsCard', displayName: 'Agent collections card', selector: [{ filenamePattern: '**/.brainstem_data/rar_collections/collections.json' }], priority: 'default' },
	]);
	assert.deepEqual(manifest.contributes.configurationDefaults['workbench.editorAssociations'], { 'basic_agent.py': 'default' }, 'the base class opens as text');
	assert.equal(manifest.contributes.configurationDefaults['workbench.editor.decorations.badges'], false, 'a tab never shows the live badge, which reads as unsaved changes');
	const show = manifest.contributes.menus['editor/title'].find(m => m.command === 'rapp.agentCard.show');
	assert.ok(show.when.includes('!(resourceFilename =~ /^basic_agent\\.py$/i)'), 'never for the base class, in any letter case');
	const helper = fs.readFileSync(path.join(dir, 'python', 'agent_card.py'), 'utf8');
	const imports = [...helper.matchAll(/^\s*(?:import|from)\s+([\w.]+)/gm)].map(m => m[1]);
	assert.deepEqual([...new Set(imports)].sort(), ['ast', 'importlib.machinery', 'json', 'os', 're', 'sys', 'sysconfig', 'warnings'], 'the helper uses only the standard library');
	assert.doesNotMatch(helper, /\b(?:exec|eval|__import__|import_module|spec_from_file_location|exec_module|runpy|subprocess)\b\s*\(/, 'the helper never runs or imports what it reads');
	const ignored = fs.readFileSync(path.join(dir, '.vscodeignore'), 'utf8').split('\n').map(line => line.trim()).filter(Boolean);
	assert.ok(!ignored.some(pattern => /^python\b|^\*\*\/\*\.py$/.test(pattern)), 'the helper is packaged with the app');
});

// The host's own glob code from the compiled fork, matched the way its editor resolver does (globMatchesResource:
// a pattern with a slash is matched against scheme:path, one without against the file name).
const hostGlob = path.join(APP_DIR, '.build', 'vscode', 'out', 'vs', 'base', 'common', 'glob.js');

test('the host opens each card only where it belongs: memory only under the Brainstem data folder', { skip: !fs.existsSync(hostGlob) && 'the fork is not compiled here' }, async () => {
	const glob = await import(pathToFileURL(hostGlob).href);
	const manifest = readJson(path.join(APP_DIR, 'extensions', 'rapp', 'package.json'));
	const editorFor = file => manifest.contributes.customEditors
		.filter(editor => editor.selector.some(({ filenamePattern: p }) => glob.match(p, p.includes('/') ? `file:${file}` : path.posix.basename(file), { ignoreCase: true })))
		.map(editor => editor.viewType);
	const brainstem = '/synthetic/profile/.brainstem/src/rapp_brainstem';
	assert.deepEqual([
		`${brainstem}/.brainstem_data/shared_memories/memory.json`,
		`${brainstem}/.brainstem_data/memory/0a1b2c3d-0000-4000-8000-000000000000/user_memory.json`,
		`${brainstem}/.brainstem_data/rar_collections/collections.json`,
		`${brainstem}/.brainstem_data/rar_collections/catalog_cache.json`,
		`${brainstem}/agents/memory.json`,
		`${brainstem}/agents/team/user_memory.json`,
		`${brainstem}/.brainstem_data_old/shared_memories/memory.json`,
		`${brainstem}/notes/rar_collections/collections.json`,
		`${brainstem}/agents/weather_agent.py`,
	].map(editorFor), [
		['rapp.memoryCard'], ['rapp.memoryCard'], ['rapp.collectionsCard'], [], [], [], [], [], ['rapp.agentCard'],
	]);
	const base = manifest.contributes.configurationDefaults['workbench.editorAssociations'];
	assert.ok(Object.keys(base).every(p => !p.includes('/')) && glob.match('basic_agent.py', 'basic_agent.py'), 'basic_agent.py opens as text wherever it is');
});

test('with Git off, nothing Git saved for terminals\' environment stays in them', () => {
	const edits = overlay.edits.filter(e => e.file === 'extensions/git/src/main.ts');
	assert.equal(edits.length, 1);
	assert.match(edits[0].find, /^\tif \(!enabled\) \{\n/);
	assert.match(edits[0].replace, /context\.environmentVariableCollection\.clear\(\);/);
});

test('a workspace whose only folder is the Brainstem data root still activates the extension that serves it', () => {
	const manifest = readJson(path.join(APP_DIR, 'extensions', 'rapp', 'package.json'));
	assert.equal(manifest.capabilities.virtualWorkspaces.supported, 'limited');
	assert.ok(manifest.activationEvents.includes('onFileSystem:brainstem-data'));
});

test('the host is kept quiet: no Git, no agent plugins or MCP servers of other tools, no shell of its own at startup', () => {
	const defaults = readJson(path.join(APP_DIR, 'extensions', 'rapp', 'package.json')).contributes.configurationDefaults;
	assert.deepEqual(
		['git.enabled', 'git.terminalAuthentication', 'chat.plugins.enabled', 'chat.mcp.access', 'terminal.integrated.hideOnStartup', 'chat.disableAIFeatures'].map(k => defaults[k]),
		[false, false, false, 'none', 'whenEmpty', true]);
});

test('a drop below the Explorer\'s tree goes to the first writable root, never the read-only Brainstem data root', () => {
	const drop = overlay.edits.filter(e => e.file === 'src/vs/workbench/contrib/files/browser/views/explorerViewer.ts');
	assert.equal(drop.length, 1);
	assert.match(drop[0].find, /target = this\.explorerService\.roots\[this\.explorerService\.roots\.length - 1\];/, 'upstream sends it to the last root');
	assert.match(drop[0].replace, /target = last\.isReadonly \? \(this\.explorerService\.roots\.find\(root => !root\.isReadonly\) \?\? last\) : last;/);
});

test('a read-only item in the Explorer is never deleted: its delete menu items are greyed out and a key says so', () => {
	const menus = overlay.edits.filter(e => e.file === 'src/vs/workbench/contrib/files/browser/fileActions.contribution.ts');
	assert.equal(menus.length, 2);
	for (const id of ['MOVE_FILE_TO_TRASH_ID', 'DELETE_FILE_ID']) {
		assert.ok(menus.some(e => e.find.includes(`id: ${id},`) && !e.find.includes('precondition')), `${id} upstream has no precondition`);
	}
	assert.equal(menus.map(e => e.replace.match(/precondition: ExplorerResourceWritableContext/g)?.length ?? 0).reduce((a, b) => a + b, 0), 3, 'Move to Trash, its Delete Permanently alternative, and Delete Permanently alone');
	const guard = overlay.edits.filter(e => e.file === 'src/vs/workbench/contrib/files/browser/fileActions.ts');
	assert.equal(guard.length, 1);
	assert.match(guard[0].find, /\/\/ Handle dirty\n\tconst distinctElements = /, 'before the question about unsaved changes');
	assert.match(guard[0].replace, /distinctElements\.filter\(e => e\.isReadonly\)/, 'read-only as the menus judge it');
	assert.match(guard[0].replace, /await dialogService\.info\([\s\S]*nothing was deleted[\s\S]*so it was not deleted[\s\S]*\);\n\t\treturn;/);
	assert.ok(guard[0].replace.startsWith(guard[0].find), 'the upstream lines stay as they are');
});

test('the defaults an extension cannot set are flipped by anchored edits', () => {
	const flips = overlay.edits.map(e => e.replace).join('\n');
	assert.match(flips, /'default': TelemetryConfiguration\.OFF/);
	assert.match(flips, /\[ChatAIDisabledSettingId\]: \{[^}]*default: true,/);
	const hidden = overlay.edits.filter(e => /\/(outline|timeline)\.contribution\.ts$/.test(e.file)).map(e => /hideByDefault(: | = )true/.test(e.replace));
	assert.deepEqual(hidden, [true, true], 'Outline and Timeline are hidden by default');
	assert.match(flips, /default: 'off'/);
	assert.match(flips, /"id":"workbench\.view\.extension\.brainstem","pinned":true/);
	for (const id of ['search', 'scm', 'debug', 'extensions']) {
		assert.match(flips, new RegExp(`"id":"workbench\\.view\\.${id}","pinned":false`));
	}
});

test('the branding assets are generated, well-formed and carry no upstream marks', () => {
	assert.deepEqual([...renderAsset('png:32').subarray(0, 8)], [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
	assert.equal(renderAsset('icns').subarray(0, 4).toString('ascii'), 'icns');
	const ico = renderAsset('ico');
	assert.equal(ico.readUInt16LE(2), 1);
	assert.equal(ico.readUInt16LE(4), 7);
	for (const kind of Object.values(overlay.branding.generated).filter(k => k.startsWith('svg:'))) {
		const svg = renderAsset(kind).toString('utf8');
		assert.match(svg, /^<svg xmlns="http:\/\/www\.w3\.org\/2000\/svg"/);
		assert.ok(!/code - oss|vs ?code/i.test(svg));
	}
	assert.ok(fs.existsSync(path.join(APP_DIR, 'extensions', 'rapp', 'media', 'brainstem.svg')));
});

test('anchors also apply to a checkout with CRLF line endings, and a missing anchor stops the build', () => {
	const dir = path.join(process.env.BRAINSTEM_TEST_TMP || path.join(APP_DIR, '.build', 'test-tmp'), `crlf-${process.pid}`);
	fs.rmSync(dir, { recursive: true, force: true });
	fs.mkdirSync(path.join(dir, 'build', 'npm'), { recursive: true });
	const edit = overlay.edits.find(e => e.file === 'build/npm/dirs.ts');
	const file = path.join(dir, edit.file);
	fs.writeFileSync(file, `export const dirs = [\r\n\t'',\r\n${edit.find.replace(/\n/g, '\r\n')}\t'remote',\r\n];\r\n`);
	applyEdits(dir, [edit]);
	assert.equal(fs.readFileSync(file, 'utf8'), `export const dirs = [\r\n\t'',\r\n\t'remote',\r\n];\r\n`);
	assert.throws(() => applyEdits(dir, [edit]), /found 0 times/);
	fs.rmSync(dir, { recursive: true, force: true });
});
