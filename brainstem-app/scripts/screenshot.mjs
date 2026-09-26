#!/usr/bin/env node
// Headless screenshots of the --web build, driven over the Chrome DevTools Protocol with nothing but Node.
//
//   CHROME_PATH=<chrome binary> node scripts/screenshot.mjs --url http://127.0.0.1:9888 --out .build/screenshots
//                               [--chrome <path>] [--stub-brainstem <port>]
//
// --stub-brainstem serves a stand-in Brainstem (canned replies, version "screenshot stub") on that port so
// the chat can be shown without talking to a real Brainstem; point rapp.brainstemUrl at it.
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const APP_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const opts = Object.fromEntries(process.argv.slice(2).reduce((pairs, arg, i, all) => {
	if (arg.startsWith('--')) {
		pairs.push([arg.slice(2), all[i + 1] && !all[i + 1].startsWith('--') ? all[i + 1] : 'true']);
	}
	return pairs;
}, []));
const URL_ = opts.url || 'http://127.0.0.1:9888';
const OUT = path.resolve(opts.out || path.join(APP_DIR, '.build', 'screenshots'));
const WIDTH = Number(opts.width || 1440), HEIGHT = Number(opts.height || 900), SCALE = Number(opts.scale || 1);
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

function findChrome() {
	const given = opts.chrome || process.env.CHROME_PATH;
	if (given) {
		return given;
	}
	const names = ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'chrome'];
	for (const dir of (process.env.PATH || '').split(path.delimiter)) {
		for (const name of names) {
			const candidate = path.join(dir, process.platform === 'win32' ? `${name}.exe` : name);
			if (fs.existsSync(candidate)) {
				return candidate;
			}
		}
	}
	throw new Error('set CHROME_PATH (or --chrome) to a Chrome or Chromium binary');
}

function stubBrainstem(port) {
	const replies = [
		[/save my hand edits/i, 'Hive contoso-onboarding: 1 file changed by hand since the last save.\n\n- shared/onboarding/checklist.md (3 lines added)\n\nNothing has changed yet. Say yes to save it as one signed commit, or no to leave it.'],
		[/^yes\b/i, 'Saved: 1 change in one signed commit. Every commit up to it is signed and allowed.'],
		[/.*/, 'Your Hives are open beside this chat. Ask me to check one, save your edits, or read a room.'],
	];
	const server = http.createServer((req, res) => {
		let body = '';
		req.on('data', chunk => body += chunk);
		req.on('end', () => {
			res.setHeader('Content-Type', 'application/json');
			if (req.url === '/health') {
				return res.end(JSON.stringify({ status: 'ok', version: 'screenshot stub' }));
			}
			if (req.url === '/chat' && req.method === 'POST') {
				const input = String(JSON.parse(body || '{}').user_input || '');
				const reply = replies.find(([pattern]) => pattern.test(input))[1];
				return res.end(JSON.stringify({ response: reply, agent_logs: input.match(/save|yes/i) ? 'Hive: save (proposal only)' : '', session_id: 'screenshot' }));
			}
			res.statusCode = 404;
			res.end('{}');
		});
	});
	return new Promise(resolve => server.listen(port, '127.0.0.1', () => resolve(server)));
}

// One DevTools session over the browser connection. Frames are auto-attached too, which keeps the
// out-of-process webview frames rendering in headless Chrome.
class Page {
	constructor(ws, sessionId) {
		this.ws = ws;
		this.sessionId = sessionId;
		this.id = 0;
		this.waiting = new Map();
		ws.addEventListener('message', event => {
			const message = JSON.parse(event.data);
			const pending = this.waiting.get(message.id);
			if (pending) {
				this.waiting.delete(message.id);
				message.error ? pending.reject(new Error(message.error.message)) : pending.resolve(message.result);
			}
		});
	}
	send(method, params = {}, sessionId = this.sessionId) {
		const id = ++this.id;
		this.ws.send(JSON.stringify({ id, method, params, sessionId }));
		return new Promise((resolve, reject) => this.waiting.set(id, { resolve, reject }));
	}
	async evaluate(expression) {
		const result = await this.send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
		if (result.exceptionDetails) {
			throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
		}
		return result.result.value;
	}
	async waitFor(expression, what, timeoutMs = 60000) {
		const deadline = Date.now() + timeoutMs;
		while (Date.now() < deadline) {
			if (await this.evaluate(expression).catch(() => false)) {
				return;
			}
			await sleep(300);
		}
		throw new Error(`timed out waiting for ${what}`);
	}
	async click(expression, what) {
		await this.waitFor(`!!(${expression})`, what);
		const box = await this.evaluate(`(() => { const r = (${expression}).getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; })()`);
		for (const type of ['mouseMoved', 'mousePressed', 'mouseReleased']) {
			await this.send('Input.dispatchMouseEvent', { type, x: box.x, y: box.y, button: 'left', clickCount: 1 });
		}
		await sleep(400);
	}
	async key(key, code, keyCode) {
		for (const type of ['keyDown', 'keyUp']) {
			await this.send('Input.dispatchKeyEvent', { type, key, code, windowsVirtualKeyCode: keyCode, nativeVirtualKeyCode: keyCode });
		}
		await sleep(300);
	}
	async type(text) {
		await this.send('Input.insertText', { text });
		await sleep(300);
	}
	// Headless Chrome paints a webview frame that was hidden, or that has no scripts, only on its next
	// layout; a one-pixel resize forces that before each capture.
	async nudge() {
		await this.send('Emulation.setDeviceMetricsOverride', { width: WIDTH - 1, height: HEIGHT, deviceScaleFactor: SCALE, mobile: false });
		await sleep(600);
		await this.send('Emulation.clearDeviceMetricsOverride');
		await sleep(1500);
	}
	async shot(name) {
		await this.nudge();
		const { data } = await this.send('Page.captureScreenshot', { format: 'png' });
		const file = path.join(OUT, name);
		fs.writeFileSync(file, Buffer.from(data, 'base64'));
		console.log(`screenshot: ${file}`);
	}
	async command(title) {
		await this.key('Escape', 'Escape', 27);
		await this.key('F1', 'F1', 112);
		await this.waitFor('!!document.querySelector(".quick-input-widget:not([style*=\\"display: none\\"]) input")', 'the command palette');
		await this.type(title);
		await sleep(700);
		await this.key('Enter', 'Enter', 13);
	}
}

const byText = (selector, text) => `[...document.querySelectorAll(${JSON.stringify(selector)})].find(e => e.textContent.trim() === ${JSON.stringify(text)})`;

// One Chrome with a fresh profile per session, so every session starts from a new window's state.
async function session(steps) {
	const port = 9300 + Math.floor(Math.random() * 500);
	const profile = path.join(OUT, `.chrome-profile-${port}`);
	fs.rmSync(profile, { recursive: true, force: true });
	const chrome = spawn(findChrome(), ['--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, '--no-first-run',
		'--no-default-browser-check', '--disable-extensions', `--window-size=${WIDTH},${HEIGHT}`, `--force-device-scale-factor=${SCALE}`, 'about:blank'], { stdio: 'ignore' });
	try {
		let target;
		for (let i = 0; i < 50 && !target; i++) {
			await sleep(200);
			target = await fetch(`http://127.0.0.1:${port}/json/list`).then(r => r.json()).then(list => list.find(t => t.type === 'page')).catch(() => undefined);
		}
		if (!target) {
			throw new Error('Chrome did not start');
		}
		const { webSocketDebuggerUrl } = await fetch(`http://127.0.0.1:${port}/json/version`).then(r => r.json());
		const ws = new WebSocket(webSocketDebuggerUrl);
		await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
		const page = new Page(ws);
		page.sessionId = (await page.send('Target.attachToTarget', { targetId: target.id, flatten: true }, undefined)).sessionId;
		await page.send('Target.setAutoAttach', { autoAttach: true, waitForDebuggerOnStart: false, flatten: true });
		await page.send('Page.enable');
		await page.send('Runtime.enable');
		try {
			await run(page, steps);
		} catch (error) {
			await page.shot('failed-step.png').catch(() => undefined);
			throw error;
		}
		ws.close();
	} finally {
		const exited = new Promise(resolve => chrome.once('exit', resolve));
		chrome.kill();
		await Promise.race([exited, sleep(5000)]);
		fs.rmSync(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 200 });
	}
}

async function run(page, steps) {
	await page.send('Page.navigate', { url: URL_ });
	await page.waitFor('!!document.querySelector(".monaco-workbench .part.activitybar")', 'the workbench', 120000);
	await page.click('document.querySelector(".part.activitybar [aria-label^=\\"Brainstem\\"]")', 'the Brainstem activity-bar item');
	for (const view of ['Hives', 'References', 'Organism']) {
		await page.waitFor(`!!(${byText('.pane-header h3.title', view)})`, `the ${view} view`);
	}
	// References and Organism start collapsed, so only the Brainstem view's webview is ready at first.
	await page.waitFor('document.querySelectorAll("iframe.webview.ready").length >= 1', 'the Brainstem webview', 60000);
	await page.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: WIDTH - 20, y: HEIGHT / 2 });
	await steps(page);
}

async function main() {
	fs.mkdirSync(OUT, { recursive: true });
	const stub = opts['stub-brainstem'] ? await stubBrainstem(Number(opts['stub-brainstem'])) : undefined;
	try {
		await session(async page => {
			await page.waitFor(`!!(${byText('.monaco-list-row .label-name', 'Members')})`, 'the Hive sections', 60000);
			await sleep(2500);
			await page.shot('brainstem-app-overview.png');

			const toggle = view => page.click(byText('.pane-header h3.title', view), `the ${view} view header`);
			await toggle('Brainstem');
			for (const section of ['Members', 'Waiting requests', 'Rooms']) {
				await page.click(byText('.monaco-list-row .label-name', section), section);
			}
			await page.click(byText('.monaco-list-row .label-name', 'onboarding'), 'the onboarding room');
			await page.click(byText('.monaco-list-row .label-name', 'checklist.md'), 'a file in the room');
			await page.waitFor('!!document.querySelector(".editor-instance .monaco-editor .view-lines")', 'the file in the editor');
			await sleep(1500);
			await page.shot('brainstem-app-hives.png');

			await toggle('Brainstem');
			await toggle('Hives');
			await page.command('Hive: Save changes (asks your Brainstem)');
			await sleep(2500);
			await page.command('Brainstem: Ask');
			await page.waitFor('!!document.querySelector(".quick-input-widget input")', 'the Ask box');
			await page.type('yes');
			await page.key('Enter', 'Enter', 13);
			await sleep(2500);
			await page.shot('brainstem-app-chat.png');
		});

		await session(async page => {
			await page.click(byText('.pane-header h3.title', 'Organism'), 'the Organism view header');
			await page.waitFor('document.querySelectorAll("iframe.webview.ready").length >= 2', 'the Organism webview', 60000);
			await page.click('document.querySelector(".pane-header .action-label[aria-label^=\\"Open the organism one-page view\\"]")', 'the Organism view title action');
			await page.waitFor('document.querySelectorAll("iframe.webview.ready").length >= 3', 'the one-page view', 60000);
			await sleep(5000);
			await page.shot('brainstem-app-organism.png');
		});
	} finally {
		await new Promise(resolve => (stub ? stub.close(resolve) : resolve()));
	}

	if (stub) {
		await session(async page => {
			await page.waitFor(`[...document.querySelectorAll('.monaco-workbench .statusbar-item')].some(e => /Brainstem/.test(e.textContent) && e.querySelector('.codicon-circle-outline'))`, 'the not-running status', 60000);
			await sleep(2500);
			await page.shot('brainstem-app-offline.png');
		});
	}
}

main().catch(error => {
	console.error(`screenshot: ${error.message}`);
	process.exitCode = 1;
});
