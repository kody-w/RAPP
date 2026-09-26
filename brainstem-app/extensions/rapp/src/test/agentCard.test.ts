// Unit tests for the agent card: the Python helper that reads an agent file without running it, what the card
// makes of what it reads, and the page it writes. Every agent here is synthetic, written at run time under the
// test temp folder: a weather agent with a manifest, required parameters and a choice; an agent without a
// manifest; a broken one; and one that reads settings, calls out to the internet and runs programs.
import * as assert from 'assert';
import { spawnSync } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import { after, describe, test } from 'node:test';

const loader = require('module') as { _resolveFilename: (request: string, ...rest: unknown[]) => string };
const resolveFilename = loader._resolveFilename;
loader._resolveFilename = function (this: unknown, request: string, ...rest: unknown[]): string {
	return request === 'vscode' ? path.join(__dirname, 'vscodeStub.js') : resolveFilename.call(this, request, ...rest);
};

const card = require('../agentCard') as typeof import('../agentCard');
const editor = require('../agentCardEditor') as typeof import('../agentCardEditor');
const helper = require('../agentCardHelper') as typeof import('../agentCardHelper');
const stub = require('./vscodeStub') as typeof import('./vscodeStub');
type Facts = import('../agentCard').Facts;
type CardContext = import('../agentCard').CardContext;

const TMP = path.resolve(process.env.BRAINSTEM_TEST_TMP || path.join(__dirname, '..', '..', '.test-tmp'));
const ROOT = path.join(TMP, `agent-card-${process.pid}`);
const AGENTS = path.join(ROOT, 'agents');
const SCRIPT = path.join(__dirname, '..', '..', 'python', 'agent_card.py');
const PYTHON = process.env.BRAINSTEM_TEST_PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
fs.mkdirSync(AGENTS, { recursive: true });
after(() => fs.rmSync(ROOT, { recursive: true, force: true }));
const waitFor = async (ready: () => boolean, label: string) => {
	const until = Date.now() + 5000;
	while (!ready() && Date.now() < until) {
		await new Promise(resolve => setTimeout(resolve, 25));
	}
	assert.ok(ready(), label);
};

const WEATHER = String.raw`"""Weather for any city, from a public forecast service.

Example prompts:
- "What's the weather in Lisbon?"
- Will it rain in Oslo tomorrow?
"""
import json
import os
import urllib.request

from agents.basic_agent import BasicAgent

__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "@example/weather",
    "version": "1.2.0",
    "display_name": "Weather",
    "description": "Tells you the weather for any city. It can add a short forecast too.",
    "author": "Example Author",
    "tags": ["weather", "starter"],
    "category": "integrations",
    "quality_tier": "community",
    "requires_env": ["WEATHER_API_KEY"],
    "dependencies": ["@rapp/basic_agent"],
    "example_call": "What's the weather in Lisbon right now?",
}

FORECAST = "https://api.weather.example/v1/forecast?units=metric"
UNITS = ["celsius", "fahrenheit"]


class WeatherAgent(BasicAgent):
    def __init__(self):
        self.name = "Weather"
        self.metadata = {
            "name": self.name,
            "description": __manifest__["description"],
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "The city to look up"},
                    "units": {"type": "string", "enum": UNITS, "description": "Temperature units"},
                    "days": {"type": "integer", "description": "How many days of forecast"},
                    "include_wind": {"type": "boolean", "description": "Add the wind speed"},
                    "stations": {"type": "array", "items": {"type": "string"}, "description": "Stations to prefer"},
                },
                "required": ["city", "units"],
            },
        }
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        key = os.environ.get("WEATHER_API_KEY", "")
        with urllib.request.urlopen(FORECAST + "&q=" + kwargs.get("city", ""), timeout=10) as reply:
            return json.dumps({"status": "success", "forecast": json.loads(reply.read()), "key": bool(key)})
`;

const NOTES = String.raw`from agents.basic_agent import BasicAgent


class NotesAgent(BasicAgent):
    """Keeps short notes for you.

    It writes them to a file next to the Brainstem.
    """

    def __init__(self):
        self.name = "notes_keeper"
        self.metadata = {
            "name": self.name,
            "description": f"Saves and lists short notes for {self.owner()}.",
            "parameters": {"type": "object", "properties": {}},
        }
        super().__init__(name=self.name, metadata=self.metadata)

    def owner(self):
        return "you"

    def perform(self, **kwargs):
        with open("notes.txt", "a", encoding="utf-8") as notes:
            notes.write(kwargs.get("text", ""))
        return "saved"
`;

const BROKEN = String.raw`from agents.basic_agent import BasicAgent


class BrokenAgent(BasicAgent):
    def __init__(self)
        self.name = "Broken"
`;

const OPS = String.raw`"""Ops checks. The handbook is at https://handbook.example.com/ops for people."""
import os
import subprocess
from os import environ as env

import requests
from bs4 import BeautifulSoup

try:
    import yaml
except ImportError:
    yaml = None

import team_helpers
from utils.azure_file_storage import AzureFileStorageManager
from agents.basic_agent import BasicAgent

TENANT = os.getenv("OPS_TENANT_HOST", "tenant-1234.example.net")
TOKEN_NAME = "OPS_API_TOKEN"
STATUS = "https://ops-user:hunter2@status.example.org:8443/v2/health?key=abc123#top"
WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


class OpsAgent(BasicAgent):
    def __init__(self):
        super().__init__(name="Ops", metadata={
            "name": "Ops",
            "description": "Checks the ops dashboard.",
            "parameters": {"type": "object", "properties": {"service": {"type": "string"}}, "required": ["service"]},
        })

    def perform(self, **kwargs):
        token = os.environ[TOKEN_NAME]
        region = env.get("OPS_REGION", "west-europe-secret")
        if "OPS_DEBUG" in os.environ:
            subprocess.run(["uptime"], check=False)
        os.system("true")
        host = f"https://{region}.example.net/api"
        page = requests.get(STATUS, headers={"Authorization": token}, timeout=5)
        return BeautifulSoup(page.text, "html.parser").get_text() + host
`;

const REPORT = String.raw`from agents.basic_agent import BasicAgent

PREFIX = "Daily"
NAME = PREFIX + "Report"
LIMITS = [5, 10, 25]


def make_description():
    return "built when it runs"


class ReportAgent(BasicAgent):
    name = NAME

    def __init__(self):
        self.metadata = {
            "name": self.name,
            "description": make_description(),
            "parameters": {
                "type": "object",
                "properties": {
                    "day": {"type": ["string", "null"], "description": f"Which day, like {PREFIX.lower()}"},
                    "limit": {"type": "number", "enum": LIMITS},
                },
            },
        }
        super().__init__(name=None, metadata=self.metadata)

    def perform(self, **kwargs):
        return "report"
`;

async function facts(source: string, local: string[] = []): Promise<Facts> {
	const outcome = await helper.readAgent(source, { pythons: [PYTHON], script: SCRIPT, local });
	assert.ok(outcome.ok, `the helper did not answer: ${JSON.stringify(outcome)}`);
	const read = card.reading(outcome);
	assert.ok('facts' in read, `the helper reported a problem: ${JSON.stringify(read)}`);
	return read.facts;
}

async function raw(source: string): Promise<Record<string, unknown>> {
	const outcome = await helper.readAgent(source, { pythons: [PYTHON], script: SCRIPT });
	assert.ok(outcome.ok, `the helper did not answer: ${JSON.stringify(outcome)}`);
	return outcome.facts as Record<string, unknown>;
}

const context = (over: Partial<CardContext> = {}): CardContext => ({
	fileName: 'weather_agent.py',
	place: { kind: 'live' },
	brainstem: { up: true, loaded: ['Weather'], fresh: true },
	now: Date.UTC(2026, 8, 24, 12),
	...over,
});

const agentFacts = (over: Partial<Facts> = {}): Facts => ({ examples: [], manifestLiteral: false, agents: [], env: [], packages: [], ...over });

describe('Agent card helper', () => {
	test('reads an agent with ast only: the manifest, its name, and metadata resolved through self.name, constants and __manifest__', async () => {
		const weather = await facts(WEATHER);
		assert.strictEqual(weather.manifestLiteral, true);
		assert.strictEqual((weather.manifest as Record<string, unknown>).display_name, 'Weather');
		assert.strictEqual(weather.agents.length, 1);
		const [agent] = weather.agents;
		assert.strictEqual(agent.className, 'WeatherAgent');
		assert.strictEqual(agent.name, 'Weather');
		const metadata = agent.metadata as { name: string; description: string; parameters: { properties: Record<string, { enum?: unknown }>; required: string[] } };
		assert.strictEqual(metadata.name, 'Weather');
		assert.strictEqual(metadata.description, 'Tells you the weather for any city. It can add a short forecast too.');
		assert.deepStrictEqual(Object.keys(metadata.parameters.properties), ['city', 'units', 'days', 'include_wind', 'stations']);
		assert.deepStrictEqual(metadata.parameters.properties.units.enum, ['celsius', 'fahrenheit']);
		assert.deepStrictEqual(metadata.parameters.required, ['city', 'units']);
		assert.deepStrictEqual(weather.examples, ['What\'s the weather in Lisbon?', 'Will it rain in Oslo tomorrow?']);
		assert.deepStrictEqual(weather.env, ['WEATHER_API_KEY']);
		assert.deepStrictEqual(weather.packages, []);
		assert.deepStrictEqual(weather.internet, { via: ['urllib.request'], domains: ['api.weather.example'] });
		assert.strictEqual(weather.files, undefined);
		assert.strictEqual(weather.programs, undefined);
	});

	test('a value that only exists once the agent runs is marked, and literals around it are still read', async () => {
		const report = await facts(REPORT);
		const [agent] = report.agents;
		assert.strictEqual(agent.name, 'DailyReport', 'a class-level name from module constants, kept when BasicAgent.__init__ gets None');
		const metadata = agent.metadata as { name: string; description: unknown; parameters: { properties: { day: { type: unknown; description: unknown }; limit: { enum: unknown } } } };
		assert.strictEqual(metadata.name, 'DailyReport');
		assert.ok(card.isRuntime(metadata.description), 'a call is only known when the agent runs');
		assert.ok(card.isRuntime(metadata.parameters.properties.day.description), 'an f-string with a call in it too');
		assert.deepStrictEqual(metadata.parameters.properties.day.type, ['string', 'null']);
		assert.deepStrictEqual(metadata.parameters.properties.limit.enum, [5, 10, 25]);
		const notes = await facts(NOTES);
		assert.strictEqual(notes.manifest, undefined);
		assert.ok(card.isRuntime((notes.agents[0].metadata as { description: unknown }).description));
		assert.deepStrictEqual(notes.files, ['open']);
	});

	test('an agent built on a class from another file is a maybe, with what only it knows marked; one built on a class here inherits its details', async () => {
		const elsewhere = await facts(['from agents import implementation', 'from agents.weather_base import WeatherBase', '',
			'class WeatherAgent(implementation.WeatherAgent):', '    """Weather, from the shared implementation."""', '    pass', '',
			'class StormAgent(WeatherBase):', '    pass', '', 'class Helper(dict):', '    pass', ''].join('\n'));
		assert.deepStrictEqual(elsewhere.agents.map(a => [a.className, a.maybe, card.isRuntime(a.name), card.isRuntime(a.metadata)]), [['WeatherAgent', true, true, true], ['StormAgent', true, true, true]]);
		const model = card.cardModel({ facts: elsewhere }, context({ brainstem: { up: true, loaded: ['Other'], fresh: true } }));
		assert.strictEqual(model.problem, undefined, 'a maybe is not "no agent"');
		assert.strictEqual(model.status.kind, 'live', 'its name is only known when it runs, so the loaded list cannot be held against it');
		assert.deepStrictEqual(model.asks, { state: 'runtime' });
		assert.match(model.note ?? '', /built on an agent from another file/);
		assert.strictEqual(model.lead, 'Weather, from the shared implementation.');
		const family = await facts(['from agents.basic_agent import BasicAgent', '', 'class BaseWeather(BasicAgent):', '    def __init__(self):',
			'        self.name = "Weather"',
			'        self.metadata = {"name": self.name, "description": "Weather.", "parameters": {"type": "object", "properties": {"city": {"type": "string"}}}}',
			'        super().__init__(name=self.name, metadata=self.metadata)', '', 'class StormAgent(BaseWeather):', '    def perform(self, **kwargs):',
			'        return "storm"', ''].join('\n'));
		const storm = family.agents.find(a => a.className === 'StormAgent');
		assert.strictEqual(storm?.name, 'Weather');
		assert.strictEqual(storm?.maybe, false);
		assert.deepStrictEqual(Object.keys((storm?.metadata as { parameters: { properties: object } }).parameters.properties), ['city']);
	});

	test('a syntax error comes back with its line, and nothing else', async () => {
		const outcome = await helper.readAgent(BROKEN, { pythons: [PYTHON], script: SCRIPT });
		const read = card.reading(outcome);
		assert.ok('problem' in read && read.problem.kind === 'syntax');
		assert.strictEqual(read.problem.line, BROKEN.split('\n').findIndex(line => line.includes('def __init__(self)')) + 1);
		assert.match(read.problem.message ?? '', /expected ':'|invalid syntax/);
		const late = await helper.readAgent('import json\nfrom __future__ import annotations\n', { pythons: [PYTHON], script: SCRIPT });
		const lateRead = card.reading(late);
		assert.ok('problem' in lateRead && lateRead.problem.kind === 'syntax' && lateRead.problem.line === 2, 'compile() catches what parses yet fails to load');
	});

	test('settings are read by name only, never with a value', async () => {
		const ops = await raw(OPS);
		assert.deepStrictEqual([...(ops.env as string[])].sort(), ['OPS_API_TOKEN', 'OPS_DEBUG', 'OPS_REGION', 'OPS_TENANT_HOST']);
		const text = JSON.stringify(ops);
		for (const value of ['tenant-1234.example.net', 'west-europe-secret', 'hunter2', 'ops-user', 'abc123', '/v2/health', '8443']) {
			assert.ok(!text.includes(value), `${value} came out of the helper`);
		}
	});

	test('packages outside the standard library, the Brainstem\'s own modules and optional imports', async () => {
		const ops = await facts(OPS, ['team_helpers']);
		assert.deepStrictEqual(ops.packages, [
			{ module: 'requests', pip: 'requests', optional: false },
			{ module: 'bs4', pip: 'beautifulsoup4', optional: false },
			{ module: 'yaml', pip: 'pyyaml', optional: true },
		]);
		const unknown = await facts(OPS);
		assert.ok(unknown.packages.some(p => p.module === 'team_helpers'), 'without --local it is a package like any other');
	});

	test('URLs become their domain only; docstrings, templated hosts and vocabulary names are not places it talks to', async () => {
		const ops = await facts(OPS);
		assert.deepStrictEqual(ops.internet, { via: ['requests'], domains: ['status.example.org'] });
		assert.deepStrictEqual(ops.files, ['your Brainstem\'s local storage']);
	});

	test('running programs is noticed through subprocess and os.system', async () => {
		const ops = await facts(OPS);
		assert.deepStrictEqual(ops.programs, ['subprocess', 'subprocess.run', 'os.system']);
		assert.strictEqual((await facts(WEATHER)).programs, undefined);
	});

	test('the agent is never run: top-level code that would leave a mark leaves none', async () => {
		const mark = path.join(ROOT, 'ran.txt');
		const source = `import pathlib\npathlib.Path(${JSON.stringify(mark)}).write_text("ran")\nraise SystemExit("ran")\n${WEATHER}`;
		const read = await facts(source);
		assert.strictEqual(read.agents[0].name, 'Weather');
		assert.ok(!fs.existsSync(mark), 'the agent ran');
	});

	test('guards: over 1 MB is refused on both sides, deep nesting and slow reads stop cleanly, and a missing Python is skipped', async () => {
		const big = '#'.repeat(helper.MAX_SOURCE + 1);
		assert.deepStrictEqual(await helper.readAgent(big, { pythons: [PYTHON], script: SCRIPT }), { ok: false, reason: 'too-big' });
		const direct = spawnSync(PYTHON, ['-I', '-S', '-B', SCRIPT], { input: Buffer.from(big) });
		assert.deepStrictEqual(JSON.parse(direct.stdout.toString()), { schema: 'rapp-agent-card/1', problem: { kind: 'too-big' } });

		const brackets = await raw(`x = ${'['.repeat(300)}${']'.repeat(300)}\n`);
		assert.strictEqual((brackets.problem as { kind: string }).kind, 'syntax', 'the parser refuses nesting the Brainstem could not load either');
		const chain = await raw(`x = ${'1 + '.repeat(20000)}1\n`);
		assert.ok(chain.problem === undefined || (chain.problem as { kind: string }).kind === 'too-deep', JSON.stringify(chain.problem));
		const nested = `${'{"a": '.repeat(60)}1${'}'.repeat(60)}`;
		const deep = await raw(`from agents.basic_agent import BasicAgent\nclass DeepAgent(BasicAgent):\n    def __init__(self):\n        self.name = "Deep"\n        self.metadata = ${nested}\n    def perform(self, **kwargs):\n        return ""\n`);
		assert.ok(JSON.stringify(deep).includes('"$deep":true'), 'values nested past the card\'s depth are marked, not followed');

		assert.deepStrictEqual(await helper.readAgent(WEATHER, { pythons: [PYTHON], script: SCRIPT, timeoutMs: 1 }), { ok: false, reason: 'timeout' });
		const missing = path.join(ROOT, 'no-python-here');
		assert.deepStrictEqual(await helper.readAgent(WEATHER, { pythons: [missing], script: SCRIPT }), { ok: false, reason: 'no-python' });
		assert.ok((await helper.readAgent(WEATHER, { pythons: [missing, PYTHON], script: SCRIPT })).ok);
	});

	test('the Brainstem\'s own Python comes first, one that answers nothing is passed over, and its folders\' module names are local', async () => {
		const home = path.join(ROOT, 'home');
		const folder = path.join(ROOT, 'rapp_brainstem');
		const managed = path.posix.join(home, '.brainstem', 'venv', 'bin', 'python');
		const dotVenv = path.posix.join(folder, '.venv', 'bin', 'python');
		assert.deepStrictEqual(helper.pythonCandidates({ home, brainstemFolder: folder, setting: 'python3', platform: 'darwin', exists: file => file === managed || file === dotVenv }), [managed, dotVenv, 'python3']);
		assert.deepStrictEqual(helper.pythonCandidates({ home, brainstemFolder: folder, setting: 'python3', platform: 'darwin', exists: file => file === dotVenv }), [dotVenv, 'python3']);
		assert.deepStrictEqual(helper.pythonCandidates({ home, brainstemFolder: folder, folderSource: 'health', setting: 'python3', platform: 'darwin', exists: () => true }), [managed, 'python3'],
			'a folder only /health reported never chooses the Python');
		assert.deepStrictEqual(helper.pythonCandidates({ home, brainstemFolder: folder, setting: '/opt/py/bin/python3', platform: 'linux', exists: () => false }), ['/opt/py/bin/python3', 'python3']);
		// Like the Hive checker: a command name or a full path, and never a Python inside a Hive or a reference.
		const hives = path.join(ROOT, 'Hives');
		const inHive = path.join(hives, 'team', '.venv', 'bin', 'python');
		assert.deepStrictEqual([
			helper.pythonCandidates({ home, setting: inHive, forbidden: [hives], exists: () => false }),
			helper.pythonCandidates({ home, setting: './bin/python', exists: () => false }),
			helper.pythonCandidates({ home, setting: 'python3.12', exists: () => false }),
			helper.pythonCandidates({ home: path.join(hives, 'someone'), setting: 'python3', forbidden: [hives], exists: () => true }),
		], [['python3', ...(process.platform === 'win32' ? ['python'] : [])], ['python3', ...(process.platform === 'win32' ? ['python'] : [])],
			['python3.12', 'python3', ...(process.platform === 'win32' ? ['python'] : [])], ['python3', ...(process.platform === 'win32' ? ['python'] : [])]]);
		// A Python inside a Hive that is a link to one outside it still reads its folder's settings: it is inside.
		// (A file link needs a privilege on Windows; without it this part is left out.)
		const outside = path.join(ROOT, 'outside-python');
		fs.writeFileSync(outside, '');
		const linked = path.join(hives, 'team', 'linked', 'bin', 'python');
		fs.mkdirSync(path.dirname(linked), { recursive: true });
		let fileLinks = true;
		try {
			fs.symlinkSync(outside, linked, 'file');
		} catch {
			fileLinks = false;
		}
		if (fileLinks) {
			assert.deepStrictEqual(helper.pythonCandidates({ home, setting: linked, forbidden: [hives], exists: () => false }), ['python3', ...(process.platform === 'win32' ? ['python'] : [])],
				'a link inside a Hive to a Python outside it is inside the Hive');
		}
		const winHome = path.win32.join('C:' + path.win32.sep, 'profiles', 'someone');
		assert.deepStrictEqual(helper.pythonCandidates({ home: winHome, setting: 'python3', platform: 'win32', exists: () => true }), [path.win32.join(winHome, '.brainstem', 'venv', 'Scripts', 'python.exe'), 'python3', 'python']);
		// A Python that starts and gives no answer (here node, which refuses -I) is passed over for the next one.
		assert.ok((await helper.readAgent(WEATHER, { pythons: [process.execPath, PYTHON], script: SCRIPT })).ok);
		assert.deepStrictEqual(await helper.readAgent(WEATHER, { pythons: [process.execPath], script: SCRIPT }), { ok: false, reason: 'failed' });
		fs.mkdirSync(path.join(folder, 'utils'), { recursive: true });
		fs.mkdirSync(path.join(folder, '.venv'), { recursive: true });
		fs.writeFileSync(path.join(folder, 'local_storage.py'), '');
		fs.writeFileSync(path.join(folder, 'not-a-module.py'), '');
		fs.writeFileSync(path.join(folder, 'notes.txt'), '');
		assert.deepStrictEqual(helper.localModuleNames([folder, undefined, path.join(ROOT, 'missing')]), ['local_storage', 'utils']);
	});
});

describe('Agent card', () => {
	test('the name is the manifest\'s display name, else the metadata name, else self.name, else the file name', () => {
		const agent = (name?: string, metaName?: string) => ({ className: 'A', examples: [], ...(name ? { name } : {}), ...(metaName ? { metadata: { name: metaName } } : {}) });
		const title = (f: Facts, fileName = 'city_weather_agent.py') => card.cardModel({ facts: f }, context({ fileName })).title;
		assert.strictEqual(title(agentFacts({ manifest: { display_name: 'Weather Pro' }, agents: [agent('WeatherPro', 'weather_pro')] })), 'Weather Pro');
		assert.strictEqual(title(agentFacts({ agents: [agent('WeatherPro', 'weather_pro')] })), 'Weather pro');
		assert.strictEqual(title(agentFacts({ agents: [agent('WeatherPro')] })), 'WeatherPro');
		assert.strictEqual(title(agentFacts({ agents: [{ className: 'A', examples: [], name: { $runtime: true } }] })), 'City weather');
		assert.strictEqual(title(agentFacts()), 'City weather');
	});

	test('what it does: the manifest\'s description, else the metadata\'s, else the docstring\'s first line', () => {
		const lead = (f: Facts) => card.cardModel({ facts: f }, context()).lead;
		const agent = { className: 'A', examples: [], name: 'A', metadata: { description: 'From the metadata. More here.' }, doc: 'From the class.\nSecond line.' };
		assert.strictEqual(lead(agentFacts({ manifest: { description: 'From the manifest.' }, agents: [agent] })), 'From the manifest.');
		assert.strictEqual(lead(agentFacts({ agents: [agent] })), 'From the metadata.');
		assert.strictEqual(card.cardModel({ facts: agentFacts({ agents: [agent] }) }, context()).more, 'More here.');
		assert.strictEqual(lead(agentFacts({ agents: [{ ...agent, metadata: { description: { $runtime: true } } }] })), 'From the class.');
		assert.strictEqual(lead(agentFacts({ doc: 'From the module.', agents: [{ className: 'A', examples: [] }] })), 'From the module.');
	});

	test('the status: live at the top of agents/, not live in a folder, and whether the Brainstem really loaded it', async () => {
		const weather = { facts: await facts(WEATHER) };
		const status = (over: Partial<CardContext>) => card.cardModel(weather, context(over)).status;
		assert.deepStrictEqual(status({}), { kind: 'live', label: 'Live', hint: 'Your Brainstem runs this' });
		assert.deepStrictEqual(status({ brainstem: { up: true, loaded: ['Notes'], fresh: true } }),
			{ kind: 'not-loaded', label: 'Live file, but your Brainstem didn’t load it', hint: 'Your Brainstem skips an agent that fails to import, or whose name or details aren’t valid' });
		assert.strictEqual(status({ brainstem: { up: true, loaded: ['Notes'], fresh: false } }).kind, 'live', 'an answer from before the file was opened or saved is not trusted');
		assert.deepStrictEqual(status({ brainstem: { up: false, fresh: true } }), { kind: 'live', label: 'Live', hint: 'Your Brainstem runs this whenever it is running' });
		assert.strictEqual(status({ brainstem: { up: true, loaded: ['Notes'], fresh: true }, dirty: true }).kind, 'live', 'unsaved edits are not held against the file the Brainstem loaded');
		assert.deepStrictEqual(status({ place: { kind: 'folder', folder: 'disabled_agents' } }), { kind: 'not-live', label: 'Not live — in disabled_agents/', hint: 'Drag it to the top of agents/ to run it' });
		assert.strictEqual(status({ place: { kind: 'folder', folder: 'team/tools' } }).label, 'Not live — in team/tools/');
		assert.strictEqual(status({ place: { kind: 'outside' } }).kind, 'outside');
		const byMetadataName = agentFacts({ agents: [{ className: 'A', examples: [], name: { $runtime: true }, metadata: { name: 'weather_tool' } }] });
		assert.strictEqual(card.cardModel({ facts: byMetadataName }, context({ brainstem: { up: true, loaded: ['weather_tool'], fresh: true } })).status.kind, 'live');
		const broken = card.reading(await helper.readAgent(BROKEN, { pythons: [PYTHON], script: SCRIPT }));
		assert.strictEqual(card.cardModel(broken, context()).status.label, 'Live file, but your Brainstem can’t load it');
		assert.deepStrictEqual(status({ missing: true }), { kind: 'outside', label: 'Not found — this file was moved or deleted', hint: 'Your Brainstem runs only what is in agents/ now' });
		assert.deepStrictEqual(status({ fileName: '.weather_agent.py', place: { kind: 'folder', folder: '.' } }), { kind: 'not-live', label: 'Not live', hint: 'Hidden files never run; take the dot off the start of its name' });
		assert.strictEqual(status({ fileName: '.weather_agent.py', place: { kind: 'folder', folder: 'team' } }).hint, 'Hidden files never run, even at the top of agents/');
	});

	test('where a file is: the top of agents/, a folder in it, the base class, or elsewhere', () => {
		assert.deepStrictEqual([
			card.cardPlace(AGENTS, path.join(AGENTS, 'weather_agent.py')),
			card.cardPlace(AGENTS, path.join(AGENTS, 'basic_agent.py')),
			card.cardPlace(AGENTS, path.join(AGENTS, 'disabled_agents', 'weather_agent.py')),
			card.cardPlace(AGENTS, path.join(AGENTS, 'team', 'tools', 'weather_agent.py')),
			card.cardPlace(AGENTS, path.join(ROOT, 'weather_agent.py')),
			card.cardPlace(undefined, path.join(AGENTS, 'weather_agent.py')),
			card.cardPlace(AGENTS, path.join(AGENTS, '..old', 'weather_agent.py')),
			card.cardPlace(AGENTS, path.join(AGENTS, '..weather_agent.py')),
		], [
			{ kind: 'live' }, { kind: 'base' }, { kind: 'folder', folder: 'disabled_agents' }, { kind: 'folder', folder: 'team/tools' }, { kind: 'outside' }, { kind: 'outside' },
			{ kind: 'folder', folder: '..old' }, { kind: 'folder', folder: '.' },
		]);
	});

	test('what you can ask it, in plain words; no parameters means just ask', async () => {
		const model = card.cardModel({ facts: await facts(WEATHER) }, context());
		assert.ok(model.asks?.state === 'rows');
		assert.deepStrictEqual(model.asks.rows.map(r => [r.label, r.type, r.needed, r.choices]), [
			['City', 'text', true, []],
			['Units', 'text', true, ['celsius', 'fahrenheit']],
			['Days', 'number', false, []],
			['Include wind', 'yes/no', false, []],
			['Stations', 'list of text', false, []],
		]);
		const notes = card.cardModel({ facts: await facts(NOTES) }, context({ fileName: 'notes_agent.py' }));
		assert.deepStrictEqual(notes.asks, { state: 'none' });
		assert.match(card.cardBody(notes), /Just ask — it doesn’t need any details\./);
		const report = card.cardModel({ facts: await facts(REPORT) }, context());
		assert.ok(report.asks?.state === 'rows');
		assert.deepStrictEqual(report.asks.rows.map(r => [r.label, r.type, r.description, r.choices]), [['Day', 'text', card.RUNTIME_TEXT, []], ['Limit', 'number', undefined, ['5', '10', '25']]]);
		assert.deepStrictEqual(card.cardModel({ facts: agentFacts({ agents: [{ className: 'A', examples: [], name: 'A', metadata: { $runtime: true } }] }) }, context()).asks, { state: 'runtime' });
	});

	test('try asking only what the agent itself offers; needs by name; mentions as hints; RAR readiness', async () => {
		const weather = card.cardModel({ facts: await facts(WEATHER) }, context());
		assert.deepStrictEqual(weather.examples, ['What\'s the weather in Lisbon right now?', 'What\'s the weather in Lisbon?', 'Will it rain in Oslo tomorrow?']);
		assert.deepStrictEqual(weather.settings, [{ name: 'WEATHER_API_KEY', needed: true }]);
		assert.deepStrictEqual(weather.rar, { ready: true });
		const notes = card.cardModel({ facts: await facts(NOTES) }, context());
		assert.deepStrictEqual(notes.examples, [], 'no example is ever made up');
		assert.ok(!card.cardBody(notes).includes('Try asking'));
		assert.strictEqual(notes.rar, undefined);
		const ops = card.cardModel({ facts: await facts(OPS) }, context());
		assert.deepStrictEqual(ops.packages, [{ name: 'requests', installs: undefined, optional: false }, { name: 'bs4', installs: 'beautifulsoup4', optional: false }, { name: 'yaml', installs: 'pyyaml', optional: true }, { name: 'team_helpers', installs: undefined, optional: false }]);
		assert.deepStrictEqual(Object.keys(ops.mentions ?? {}).filter(k => (ops.mentions as Record<string, unknown>)[k]), ['internet', 'files', 'programs']);
		// RAR's own rules, as build_registry.py applies them, through the helper that mirrors it.
		const rar = async (from: string, to: string) => card.rarReadiness(await facts(WEATHER.replace(from, to)));
		// RAR reads the text as UTF-8 and keeps a byte order mark, where the Brainstem (and the card) read the bytes.
		assert.deepStrictEqual(card.rarReadiness(await facts(`\uFEFF${WEATHER}`)), { ready: false, why: 'it starts with a byte order mark, which RAR stops at: save it as UTF-8 without one' });
		const latin = await helper.readAgent(Buffer.from(`# -*- coding: latin-1 -*-\n${WEATHER.replace('from a public forecast service', 'from a public forecast service, caf\u00e9')}`, 'latin1'), { pythons: [PYTHON], script: SCRIPT });
		const latinRead = card.reading(latin);
		assert.ok('facts' in latinRead, JSON.stringify(latinRead));
		assert.deepStrictEqual(card.rarReadiness(latinRead.facts), { ready: false, why: 'RAR reads agent files as UTF-8, and this one isn’t: save it as UTF-8' });
		assert.deepStrictEqual(await rar('"version": "1.2.0",', '"version": "1.2",'), { ready: false, why: 'its version must look like 1.0.0' });
		assert.deepStrictEqual(await rar('"version": "1.2.0",', ''), { ready: false, why: 'its manifest has no version' });
		assert.deepStrictEqual(await rar('"name": "@example/weather",', '"name": "weather",'), { ready: false, why: 'its package name must look like @publisher/slug' });
		assert.deepStrictEqual(await rar('"tags": ["weather", "starter"],', '"tags": ("weather", "starter"),'), { ready: false, why: 'its tags must be a list' });
		assert.deepStrictEqual(await rar('"name": self.name,', '"name": "WeatherTool",'), { ready: false, why: 'its metadata name must match its name' });
		assert.deepStrictEqual(await rar('self.name = "Weather"', 'self.name = AGENT_NAME'), { ready: false, why: 'its name must be written plainly in the file' }, 'RAR does not follow module constants');
		assert.deepStrictEqual(await rar('__manifest__ = {', '__manifest__: dict = {'), { ready: false, why: 'RAR reads a manifest only from a plain __manifest__ = {…}' });
		const alias = WEATHER + '\n\nclass WeatherAlias(WeatherAgent):\n    pass\n';
		assert.deepStrictEqual(card.rarReadiness(await facts(alias)), { ready: true }, 'RAR checks the classes with a perform() of their own, not an alias');
	});

	test('RAR readiness also follows scan_security(), over the whole text, and RAR\'s rule against dashes in file names', async () => {
		const rar = async (added: string, fileName?: string) => card.rarReadiness(await facts(`${WEATHER}\n${added}\n`), fileName);
		assert.deepStrictEqual(await rar('# os.system("uptime") would be refused, even in a comment'), { ready: false, why: 'its text has os.system( in it, which RAR refuses even in a comment; use subprocess instead' });
		assert.deepStrictEqual(await rar('SETTINGS = open("/etc/hosts").read'), { ready: false, why: 'RAR refuses code that opens /etc, /proc, .env, .ssh or passwd' });
		assert.deepStrictEqual(await rar('api' + '_key = "not-real"'), { ready: false, why: 'it looks like it has a secret written into it, which RAR refuses' });
		assert.deepStrictEqual(await rar('API' + '_KEY = "UPPER-CASE-IS-NOT-MATCHED"'), { ready: true }, 'as case-sensitive as RAR\'s own patterns');
		assert.deepStrictEqual(await rar('tok' + 'en = os.environ.get("WEATHER_TOKEN")'), { ready: true }, 'a setting read by name is fine');
		assert.deepStrictEqual(await rar('', 'city-weather_agent.py'), { ready: false, why: 'its file name has a dash, and RAR needs snake_case, like weather_agent.py' });
		assert.deepStrictEqual(await rar('', 'city_weather_agent.py'), { ready: true });
		const ops = await raw(OPS.replace('from agents.basic_agent import BasicAgent', 'from agents.basic_agent import BasicAgent\n__manifest__ = {"schema": "rapp-agent/1.0"}'));
		assert.ok(JSON.stringify(ops.rar).includes('security-system'), 'os.system() in the code itself');
		assert.ok(!JSON.stringify(ops).includes('true")'), 'the scan names the rule, never the text it matched');
	});

	test('the file\'s own bytes decide what Python reads: a file it could not decode is a problem, a declared encoding is honoured', async () => {
		const latin = Buffer.concat([Buffer.from('from agents.basic_agent import BasicAgent\n\nNOTE = "caf'), Buffer.from([0xe9]), Buffer.from('"\n')]);
		const plain = card.reading(await helper.readAgent(latin, { pythons: [PYTHON], script: SCRIPT }));
		assert.ok('problem' in plain && plain.problem.kind === 'syntax', 'Python refuses a file that is not UTF-8 and does not say what it is');
		assert.match(plain.problem.message ?? '', /^a character on this line isn’t UTF-8: save the file as UTF-8, or name its encoding in a coding: line$/, 'said in plain words, not as Python\'s codec error');
		assert.strictEqual(plain.problem.line, 3);
		const read = async (source: string) => card.reading(await helper.readAgent(Buffer.from(source), { pythons: [PYTHON], script: SCRIPT }));
		const escape = await read('x = "\\N{nope}"\n');
		assert.ok('problem' in escape && escape.problem.kind === 'syntax' && /^a backslash in a text on this line starts an escape Python can’t read$/.test(escape.problem.message ?? ''));
		const ascii = card.reading(await helper.readAgent(Buffer.concat([Buffer.from('# -*- coding: ascii -*-\nNOTE = "caf'), Buffer.from([0xe9]), Buffer.from('"\n')]), { pythons: [PYTHON], script: SCRIPT }));
		assert.ok('problem' in ascii && ascii.problem.kind === 'syntax' && ascii.problem.message === 'a character in it isn’t one the encoding its coding: line names can hold', JSON.stringify(ascii));
		const bytesEscape = await read('x = b"\\x"\n');
		assert.ok('problem' in bytesEscape && bytesEscape.problem.kind === 'syntax' && bytesEscape.problem.message === 'a backslash in a text on this line starts an escape Python can’t read', JSON.stringify(bytesEscape));
		const nul = await read('x = 1\0\n');
		assert.ok('problem' in nul && nul.problem.kind === 'syntax' && nul.problem.message === 'the file contains a null character', JSON.stringify(nul));
		const bomLatin = card.reading(await helper.readAgent(Buffer.concat([Buffer.from([0xef, 0xbb, 0xbf]), Buffer.from('# -*- coding: latin-1 -*-\nx = 1\n')]), { pythons: [PYTHON], script: SCRIPT }));
		assert.ok('problem' in bomLatin && bomLatin.problem.kind === 'syntax' && /^its coding: line doesn’t match how the file begins/.test(bomLatin.problem.message ?? ''), JSON.stringify(bomLatin));
		const unknown = await read('# -*- coding: nosuch -*-\nx = 1\n');
		assert.ok('problem' in unknown && unknown.problem.kind === 'syntax' && unknown.problem.message === 'its coding: line names an encoding Python doesn’t know' && unknown.problem.line === undefined, JSON.stringify(unknown));
		const declared = Buffer.concat([Buffer.from('# -*- coding: latin-1 -*-\n'), latin]);
		assert.ok('facts' in card.reading(await helper.readAgent(declared, { pythons: [PYTHON], script: SCRIPT })));
		const bom = Buffer.concat([Buffer.from([0xef, 0xbb, 0xbf]), Buffer.from(NOTES)]);
		assert.ok('facts' in card.reading(await helper.readAgent(bom, { pythons: [PYTHON], script: SCRIPT })), 'a byte order mark is fine');
	});

	test('an agent with its own perform() built on a class from another file says so', async () => {
		const built = await facts(['from agents.shared.base import SharedBase', '', 'class TicketAgent(SharedBase):', '    def perform(self, **kwargs):', '        return "ok"', ''].join('\n'));
		assert.deepStrictEqual(built.agents.map(a => [a.className, a.maybe, a.elsewhere]), [['TicketAgent', false, true]]);
		assert.strictEqual(card.cardModel({ facts: built }, context()).note, 'It builds on code from another file, so some of what it does comes from there.');
		assert.strictEqual(card.cardModel({ facts: await facts(WEATHER) }, context()).note, undefined);
	});

	test('what the Brainstem would refuse, when the file says so plainly', () => {
		const refused = (name: unknown, metadata: unknown) => card.cannotLoad({ className: 'A', examples: [], name: name as never, metadata: metadata as never });
		assert.deepStrictEqual(refused('Weather Poet', { parameters: { type: 'object' } }), ['its name “Weather Poet” may use only letters, numbers, - and _']);
		assert.deepStrictEqual(refused('Weather', { parameters: { type: 'array' } }), ['its parameters need "type": "object"']);
		assert.deepStrictEqual(refused('Weather', { parameters: { type: 'object', properties: [] } }), ['its parameters’ properties aren’t a dictionary']);
		assert.deepStrictEqual(refused({ $runtime: true }, { $runtime: true }), []);
		assert.deepStrictEqual(refused('Weather', { description: 'no parameters is fine' }), []);
	});

	test('the page escapes everything from the file and runs only its own nonce\'d script', () => {
		const hostile = '<img src=x onerror=alert(1)><script>alert(2)</script>"\'&';
		const facts: Facts = agentFacts({
			manifest: { display_name: hostile, description: hostile, version: hostile, tags: [hostile] },
			examples: [hostile],
			agents: [{ className: 'A', examples: [], name: 'A', metadata: { name: 'A', parameters: { type: 'object', properties: { [hostile]: { type: 'string', description: hostile, enum: [hostile] } } } } }],
			env: ['HOSTILE_NAME'],
			packages: [{ module: hostile, pip: hostile, optional: false }],
			internet: { via: [hostile], domains: [hostile] },
		});
		const body = card.cardBody(card.cardModel({ facts }, context({ fileName: 'x_agent.py', folderPath: hostile })));
		assert.ok(!/<img|<script|onerror=alert\(1\)>/i.test(body), 'raw markup from the file reached the page');
		assert.ok(body.includes('&lt;img src=x onerror=alert(1)&gt;&lt;script&gt;alert(2)&lt;/script&gt;&quot;&#39;&amp;'));
		// Inside tags (escaped text has no < or >), every attribute is one the card writes itself.
		const attributes = [...body.matchAll(/<[a-z0-9]+([^<>]*)>/gi)].flatMap(tag => [...tag[1].matchAll(/\s([a-zA-Z-]+)="/g)].map(m => m[1]));
		assert.deepStrictEqual([...new Set(attributes)].filter(name => !['class', 'title', 'role', 'data-action', 'data-line'].includes(name)), [], 'an attribute was broken out of');
		const page = card.cardPage(body, { csp: 'default-src \'none\'; script-src \'nonce-abc\'', nonce: 'abc' });
		assert.strictEqual(page.match(/<script/g)?.length, 1);
		assert.match(page, /<script nonce="abc">/);
		assert.match(page, /<style nonce="abc">/);
		assert.ok(!/\sstyle=|\son[a-z]+=/i.test(page.replace(body, '')), 'the page has inline styles or handlers of its own');
	});

	test('plain words for sizes, times and names', () => {
		assert.deepStrictEqual([card.formatSize(812), card.formatSize(4300), card.formatSize(3 * 1024 * 1024)], ['812 bytes', '4.2 KB', '3.0 MB']);
		const now = Date.UTC(2026, 8, 24, 12);
		assert.deepStrictEqual([0.5, 3, 90, 60 * 30, 60 * 24 * 3].map(minutes => card.whenChanged(now - minutes * 60000, now)), ['just now', '3 minutes ago', '2 hours ago', 'yesterday', '3 days ago']);
		assert.deepStrictEqual(['include_wind', 'cityName', 'user_guid', 'q', 'cityIDs', 'image_urls', 'os', 'dns', 'bus', 'use_oss'].map(card.humanize), ['Include wind', 'City name', 'User GUID', 'Q', 'City IDs', 'Image URLs', 'OS', 'DNS', 'Bus', 'Use oss']);
		assert.deepStrictEqual(['weather_poet', 'HackerNews', 'context-memory'].map(n => card.friendly(n)), ['Weather poet', 'HackerNews', 'Context memory']);
		assert.deepStrictEqual(card.firstSentence('Fetches the news. Use it when asked.'), { sentence: 'Fetches the news.', rest: 'Use it when asked.' });
		const long = `Checks ${'every item '.repeat(40)}against the list. Then it reports.`;
		const cut = card.firstSentence(long, 60);
		assert.ok(cut.sentence.endsWith('…') && cut.sentence.length <= 61);
		assert.strictEqual(cut.rest, long, 'a first sentence too long for one line leaves the whole text below it');
		assert.deepStrictEqual([card.typeWords('boolean'), card.typeWords('array', { type: 'integer' }), card.typeWords('object'), card.typeWords(undefined)], ['yes/no', 'list of numbers', 'details', undefined]);
	});

	test('what the Brainstem refuses as it loads an agent: the LTS pin\'s checks always, the newest channel\'s stricter ones when it says it is 0.6.16 or newer', () => {
		const agent = (metadata: Record<string, unknown>) => ({ name: 'Weather', metadata: { name: 'Weather', ...metadata } }) as never;
		const good = { description: 'Weather.', parameters: { type: 'object', properties: { city: { type: 'string', description: 'A city.' } }, required: ['city'] } };
		const cases: [Record<string, unknown>, string[]][] = [
			[good, []],
			[{ ...good, description: ['Weather.'] }, ['its description isn’t text']],
			[{ ...good, parameters: null }, ['its parameters aren’t a dictionary']],
			[{ ...good, parameters: { ...good.parameters, required: 'city' } }, ['“required” in its parameters must be a list of names']],
			[{ ...good, parameters: { type: 'object', properties: { city: 'text' } } }, ['the detail “city” in its parameters must be described by a dictionary']],
			[{ ...good, parameters: { type: 'object', properties: { tags: { type: 'array', items: { type: 7 } } } } }, ['the type of the items of the detail “tags” must be text, or a list of text']],
			[{ ...good, parameters: { type: 'object', anyOf: [] } }, ['“anyOf” in its parameters must be a list of choices']],
		];
		for (const [metadata, newest] of cases) {
			assert.deepStrictEqual([card.cannotLoad(agent(metadata), '0.6.9'), card.cannotLoad(agent(metadata), '0.6.16'), card.cannotLoad(agent(metadata), '0.7.0'), card.cannotLoad(agent(metadata))],
				[[], newest, newest, []], `${JSON.stringify(metadata)}: the LTS pin loads it, the newest channel says why not; with no version known, nothing is claimed`);
		}
	});

	test('a save re-reads the file bytes, so RAR readiness does not keep a stale byte-order-mark verdict', async () => {
		const file = path.join(AGENTS, 'saved_bytes_agent.py');
		fs.writeFileSync(file, `\uFEFF${WEATHER}`);
		const document = {
			uri: stub.Uri.file(file),
			getText: () => WEATHER,
			isDirty: false,
			lineCount: WEATHER.split(/\r?\n/).length,
		};
		const panel = {
			visible: true,
			webview: {
				options: {},
				html: '',
				cspSource: 'vscode-webview:',
				onDidReceiveMessage: () => ({ dispose: () => undefined }),
			},
			onDidDispose: () => ({ dispose: () => undefined }),
			onDidChangeViewState: () => ({ dispose: () => undefined }),
		};
		const sources = {
			agentsRoot: () => AGENTS,
			brainstem: () => ({ folder: ROOT, source: 'default' as const, refused: [] }),
			pythonSetting: () => PYTHON,
			forbidden: () => [],
			status: () => ({ state: 'not-running' as const, reason: 'test' }),
			poll: async () => undefined,
			onDidChangeStatus: () => ({ dispose: () => undefined }),
		};
		const provider = new editor.AgentCardEditor(stub.Uri.file(path.join(__dirname, '..', '..')) as never, sources);
		provider.resolveCustomTextEditor(document as never, panel as never);
		await waitFor(() => panel.webview.html.includes('byte order mark'), 'the saved BOM is shown first');
		fs.writeFileSync(file, WEATHER);
		stub.workspace.fireSaveTextDocument(document);
		await waitFor(() => panel.webview.html.includes('Ready to share through RAR'), 'saving UTF-8 without BOM clears the stale refusal');
		provider.dispose();
	});
});
