// tests/osi/browser/L4a-tether.spec.mjs
//
// Historical source restored from:
//   commit 6bd45f00981959a3fdfcc64fb32608533aae5021
//   git blob f416135f7ea8e95254668a4e046b539bad78870c
//
// The two-process Chromium + PeerJS DataChannel test remains executable.
// Default execution is an offline-safe skip. An external run requires the
// explicit opt-in plus caller-supplied Playwright, Chromium, PeerJS bundle,
// and broker configuration; this suite reads and uses no credentials.

import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HISTORICAL_SOURCE = Object.freeze({
  commit: "6bd45f00981959a3fdfcc64fb32608533aae5021",
  blob: "f416135f7ea8e95254668a4e046b539bad78870c",
});

if (process.env.RAPP_OSI_BROWSER_EXTERNAL !== "1") {
  console.log(
    "SKIP L4a browser tether: external PeerJS/Chromium execution is disabled "
    + `by default (source ${HISTORICAL_SOURCE.commit}, blob ${HISTORICAL_SOURCE.blob}).`,
  );
  process.exit(0);
}

const dirname = path.dirname(fileURLToPath(import.meta.url));
const fixtureFile = path.join(dirname, "fixture.html");

function requiredFile(name, { executable = false } = {}) {
  const configured = process.env[name];
  if (!configured) {
    throw new Error(`${name} must name a supplied local file`);
  }
  const resolved = path.resolve(process.cwd(), configured);
  const mode = executable ? fs.constants.X_OK : fs.constants.R_OK;
  fs.accessSync(resolved, mode);
  return resolved;
}

function requiredBrokerOptions() {
  const host = process.env.RAPP_PEERJS_BROKER_HOST;
  if (!host || !/^[a-z0-9.:[\]-]+$/i.test(host)) {
    throw new Error("RAPP_PEERJS_BROKER_HOST must be an explicit broker host");
  }

  const secureValue = process.env.RAPP_PEERJS_BROKER_SECURE;
  if (!["true", "false"].includes(secureValue)) {
    throw new Error("RAPP_PEERJS_BROKER_SECURE must be exactly true or false");
  }
  const secure = secureValue === "true";

  const defaultPort = secure ? 443 : 80;
  const port = Number.parseInt(
    process.env.RAPP_PEERJS_BROKER_PORT || String(defaultPort),
    10,
  );
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error("RAPP_PEERJS_BROKER_PORT must be a valid TCP port");
  }

  let brokerPath = process.env.RAPP_PEERJS_BROKER_PATH || "/";
  if (!brokerPath.startsWith("/")) brokerPath = "/" + brokerPath;
  if (!brokerPath.endsWith("/")) brokerPath += "/";

  return Object.freeze({
    host,
    port,
    path: brokerPath,
    secure,
    key: process.env.RAPP_PEERJS_BROKER_KEY || "peerjs",
    debug: 2,
  });
}

function moduleSpecifier(value) {
  if (!value) return "playwright";
  const candidate = path.resolve(process.cwd(), value);
  if (fs.existsSync(candidate)) return pathToFileURL(candidate).href;
  return value;
}

const peerjsBundle = requiredFile("RAPP_PEERJS_BUNDLE");
const chromiumExecutable = requiredFile(
  "RAPP_CHROMIUM_EXECUTABLE",
  { executable: true },
);
const peerOptions = requiredBrokerOptions();

let chromium;
try {
  const playwright = await import(
    moduleSpecifier(process.env.RAPP_PLAYWRIGHT_MODULE)
  );
  chromium = playwright.chromium;
  if (!chromium || typeof chromium.launch !== "function") {
    throw new Error("module does not export chromium.launch");
  }
} catch (error) {
  console.error(
    `L4a browser tether: supplied Playwright module is unavailable: ${error.message}`,
  );
  process.exit(2);
}

const colors = process.stdout.isTTY
  ? {
      green: "\x1b[32m",
      red: "\x1b[31m",
      yellow: "\x1b[33m",
      bold: "\x1b[1m",
      reset: "\x1b[0m",
    }
  : { green: "", red: "", yellow: "", bold: "", reset: "" };

let passed = 0;
let failed = 0;

function pass(message) {
  console.log(`  ${colors.green}✓${colors.reset} ${message}`);
  passed += 1;
}

function fail(message) {
  console.log(`  ${colors.red}✗${colors.reset} ${message}`);
  failed += 1;
}

function heading(message) {
  console.log(`\n${colors.bold}${message}${colors.reset}`);
}

function note(message) {
  console.log(`  ${colors.yellow}${message}${colors.reset}`);
}

function serveFixture() {
  return new Promise((resolve, reject) => {
    const server = http.createServer((request, response) => {
      const url = (request.url || "/").split("?")[0];
      if (url === "/" || url === "/fixture.html") {
        response.writeHead(200, {
          "Content-Type": "text/html; charset=utf-8",
          "Cache-Control": "no-store",
        });
        response.end(fs.readFileSync(fixtureFile));
        return;
      }
      if (url === "/peerjs.min.js") {
        response.writeHead(200, {
          "Content-Type": "text/javascript; charset=utf-8",
          "Cache-Control": "no-store",
        });
        response.end(fs.readFileSync(peerjsBundle));
        return;
      }
      if (url === "/runtime-config.js") {
        response.writeHead(200, {
          "Content-Type": "text/javascript; charset=utf-8",
          "Cache-Control": "no-store",
        });
        response.end(
          "window.__RAPP_PEER_OPTIONS = Object.freeze("
          + JSON.stringify(peerOptions)
          + ");",
        );
        return;
      }
      response.writeHead(404, { "Content-Type": "text/plain" });
      response.end("not found");
    });
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => resolve(server));
  });
}

async function waitFor(
  predicate,
  { timeoutMs = 15000, intervalMs = 100, label = "condition" } = {},
) {
  const start = Date.now();
  let lastError = null;
  while (Date.now() - start < timeoutMs) {
    try {
      if (await predicate()) return true;
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  throw new Error(
    `timed out waiting for ${label}`
    + (lastError ? ` (last error: ${lastError.message})` : ""),
  );
}

console.log(
  `${colors.bold}=== L4a — Tether (explicit PeerJS/Chromium run) ===${colors.reset}`,
);
note(
  `broker ${peerOptions.secure ? "https" : "http"}://${peerOptions.host}:`
  + `${peerOptions.port}${peerOptions.path}; supplied local dependencies only`,
);

const server = await serveFixture();
const port = server.address().port;
const fixtureUrl = `http://127.0.0.1:${port}/fixture.html`;
console.log(`  fixture serving at ${fixtureUrl}`);

const args = [
  "--disable-features=WebRtcHideLocalIpsWithMdns,IsolateOrigins,site-per-process",
  "--disable-dev-shm-usage",
];
if (process.env.RAPP_CHROMIUM_NO_SANDBOX === "1") {
  args.push("--no-sandbox");
}

const launchOptions = {
  executablePath: chromiumExecutable,
  headless: true,
  args,
};

let browserA = null;
let browserB = null;
try {
  [browserA, browserB] = await Promise.all([
    chromium.launch(launchOptions),
    chromium.launch(launchOptions),
  ]);
} catch (error) {
  fail(`failed to launch supplied Chromium: ${error.message}`);
  server.close();
  process.exit(1);
}

const pageA = await browserA.newPage();
const pageB = await browserB.newPage();

for (const [name, page] of [["A", pageA], ["B", pageB]]) {
  page.on("pageerror", (error) => {
    note(`page${name} pageerror: ${error.message}`);
  });
  page.on("console", (message) => {
    if (message.type() === "error") {
      note(`page${name} console.error: ${message.text()}`);
    }
  });
}

try {
  heading("Step 1 — Open both local fixture pages");
  await Promise.all([pageA.goto(fixtureUrl), pageB.goto(fixtureUrl)]);
  pass("both pages loaded from the loopback fixture");

  heading("Step 2 — Both peers register with the explicit PeerJS broker");
  await waitFor(async () => {
    const a = await pageA.evaluate(() => window.__rappTest.getMyId());
    const b = await pageB.evaluate(() => window.__rappTest.getMyId());
    return a && a !== "connecting…" && b && b !== "connecting…" && a !== b;
  }, {
    timeoutMs: 20000,
    label: "both peers to register with the supplied broker",
  });
  const idA = await pageA.evaluate(() => window.__rappTest.getMyId());
  const idB = await pageB.evaluate(() => window.__rappTest.getMyId());
  pass(`peer A registered: ${idA}`);
  pass(`peer B registered: ${idB}`);

  heading("Step 3 — Open DataChannel A → B");
  await pageA.evaluate((id) => window.__rappTest.startConnect(id), idB);
  try {
    await waitFor(async () => {
      const statusA = await pageA.evaluate(() => window.__rappTest.getStatus());
      const statusB = await pageB.evaluate(() => window.__rappTest.getStatus());
      return statusA === "connected" && statusB === "connected";
    }, {
      timeoutMs: 30000,
      label: "DataChannel to open on both sides",
    });
    pass("DataChannel open on both sides");
  } catch (error) {
    const statusA = await pageA.evaluate(() => window.__rappTest.getStatus());
    const statusB = await pageB.evaluate(() => window.__rappTest.getStatus());
    const eventsA = await pageA.evaluate(() => window.__rappTest.getEvents());
    const eventsB = await pageB.evaluate(() => window.__rappTest.getEvents());
    const stateA = await pageA.evaluate(() => window.__rappTest.getPeerState());
    const stateB = await pageB.evaluate(() => window.__rappTest.getPeerState());
    note(`A status: "${statusA}" | B status: "${statusB}"`);
    note(`A peer state: ${JSON.stringify(stateA)}`);
    note(`B peer state: ${JSON.stringify(stateB)}`);
    note(`A events: ${JSON.stringify(eventsA)}`);
    note(`B events: ${JSON.stringify(eventsB)}`);
    throw error;
  }

  heading("Step 4 — Message A → B over the tether");
  const messageAtoB = `hello-from-A-${Date.now()}`;
  await pageA.evaluate((message) => window.__rappTest.send(message), messageAtoB);
  await waitFor(async () => {
    const messages = await pageB.evaluate(() => window.__rappTest.getMessages());
    return messages && messages.includes(messageAtoB);
  }, { timeoutMs: 8000, label: `B to receive "${messageAtoB}"` });
  pass(`A → B: B received "${messageAtoB}"`);

  heading("Step 5 — Message B → A over the tether");
  const messageBtoA = `hello-from-B-${Date.now()}`;
  await pageB.evaluate((message) => window.__rappTest.send(message), messageBtoA);
  await waitFor(async () => {
    const messages = await pageA.evaluate(() => window.__rappTest.getMessages());
    return messages && messages.includes(messageBtoA);
  }, { timeoutMs: 8000, label: `A to receive "${messageBtoA}"` });
  pass(`B → A: A received "${messageBtoA}"`);

  heading("Step 6 — Envelope shape includes rapp-tether/1.0");
  const messagesB = await pageB.evaluate(() => window.__rappTest.getMessages());
  if (messagesB.includes("rapp-tether/1.0")) {
    pass("payload includes the rapp-tether/1.0 schema field");
  } else {
    fail("payload missing rapp-tether/1.0 schema");
  }
} catch (error) {
  fail(`error during run: ${error.message}`);
} finally {
  try {
    await browserA.close();
  } catch {}
  try {
    await browserB.close();
  } catch {}
  server.close();
}

const total = passed + failed;
console.log(
  `\n${colors.bold}${passed} passing, ${failed} failing${colors.reset} (of ${total})`,
);
process.exit(failed === 0 ? 0 : 1);
