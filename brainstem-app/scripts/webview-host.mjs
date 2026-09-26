#!/usr/bin/env node
// Serves the host's webview bootstrap (index.html, fake.html, service-worker.js) to *.localhost origins,
// so the --web development path needs no vendor webview CDN. Read-only, loopback-only, and nothing else
// is ever served; webview content itself reaches the frames through the authenticated workbench.
//
//   node scripts/webview-host.mjs --root <fork>/out/vs/workbench/contrib/webview/browser/pre --port 9889
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';

const arg = name => {
	const at = process.argv.indexOf(name);
	return at > 0 ? process.argv[at + 1] : undefined;
};
const root = path.resolve(arg('--root') || '.');
const port = Number(arg('--port'));
const FILES = { '/index.html': 'text/html', '/fake.html': 'text/html', '/service-worker.js': 'text/javascript' };
const HOST = new RegExp(`^[0-9a-z]+\\.localhost:${port}$`);

if (!Number.isInteger(port) || port <= 0 || !fs.existsSync(path.join(root, 'index.html'))) {
	console.error('usage: webview-host.mjs --root <webview pre folder> --port <port>');
	process.exit(2);
}

http.createServer((req, res) => {
	const pathname = new URL(req.url || '/', 'http://localhost').pathname;
	const type = FILES[pathname];
	if (req.method !== 'GET' || !type || !HOST.test(String(req.headers.host || ''))) {
		res.writeHead(404, { 'Content-Type': 'text/plain' });
		res.end('not found');
		return;
	}
	res.writeHead(200, { 'Content-Type': type, 'Cache-Control': 'no-cache', 'X-Content-Type-Options': 'nosniff' });
	fs.createReadStream(path.join(root, pathname.slice(1))).pipe(res);
}).listen(port, '127.0.0.1', () => console.log(`webview host: http://*.localhost:${port}/ (bootstrap only)`));
