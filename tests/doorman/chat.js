#!/usr/bin/env node
//
// chat.js — drive a Doorman fixture through a real browser.
//
// Historical source restored from:
//   commit 6bd45f00981959a3fdfcc64fb32608533aae5021
//   git blob 6562be9e8948d11fffbe2937897314f024e63038
//
// The browser/chat implementation is retained. Automatic credential
// discovery and context-wide token injection are not: only an explicit
// synthetic test token may be written, after navigation, to the exact
// localhost or explicitly allowlisted fixture origin.

const HISTORICAL_SOURCE = Object.freeze({
  commit: "6bd45f00981959a3fdfcc64fb32608533aae5021",
  blob: "6562be9e8948d11fffbe2937897314f024e63038",
});

function arg(name) {
  const flag = "--" + name;
  for (const value of process.argv.slice(2)) {
    if (value === flag) return true;
    if (value.startsWith(flag + "=")) return value.slice(flag.length + 1);
  }
  return null;
}

function normalizeOrigin(value) {
  try {
    const url = new URL(value);
    if (!["http:", "https:"].includes(url.protocol)) return null;
    if (url.username || url.password) return null;
    return url.origin;
  } catch {
    return null;
  }
}

function allowedFixtureOrigins() {
  const allowed = new Set();
  const configured = process.env.RAPP_DOORMAN_FIXTURE_ORIGINS || "";
  for (const candidate of configured.split(",")) {
    const origin = normalizeOrigin(candidate.trim());
    if (origin) allowed.add(origin);
  }
  return allowed;
}

function isLoopbackFixture(target) {
  return ["localhost", "127.0.0.1", "[::1]"].includes(target.hostname);
}

function requireAllowedFixtureUrl(value) {
  let target;
  try {
    target = new URL(value);
  } catch {
    throw new Error("target must be an absolute http(s) fixture URL");
  }
  if (target.username || target.password) {
    throw new Error("fixture URLs must not contain credentials");
  }
  if (!isLoopbackFixture(target) && !allowedFixtureOrigins().has(target.origin)) {
    throw new Error(
      `fixture origin ${target.origin} is not localhost or listed in `
      + "RAPP_DOORMAN_FIXTURE_ORIGINS",
    );
  }
  return target;
}

function requireSyntheticToken(value) {
  if (!value) return null;
  if (value === true || value === "auto") {
    throw new Error("automatic credential discovery is disabled");
  }
  if (
    /^(?:gh[pousr]_|github_pat_)/i.test(value)
    || !/^(?:rapp[-_])?(?:synthetic|test|fixture)[-_]/i.test(value)
    || value.length > 256
  ) {
    throw new Error(
      "only an explicit synthetic/test credential is accepted; real GitHub tokens are refused",
    );
  }
  return value;
}

function ensureSameOrigin(actualUrl, expectedOrigin) {
  const actual = normalizeOrigin(actualUrl);
  if (actual !== expectedOrigin) {
    throw new Error(
      `fixture navigated to ${actual || "an invalid origin"}; refusing storage injection`,
    );
  }
}

const urlArg = process.argv.find((value) => /^https?:\/\//.test(value));
const message = process.argv
  .slice(2)
  .filter((value) => !value.startsWith("--") && !/^https?:\/\//.test(value))
  .join(" ")
  .trim();

if (!urlArg) {
  console.error(
    "Usage: node chat.js <fixture_url> "
    + "[--test-token=synthetic-...] [--headed] [--verbose] \"<message>\"",
  );
  process.exit(2);
}

let target;
let token;
try {
  target = requireAllowedFixtureUrl(urlArg);
  token = requireSyntheticToken(arg("test-token") || arg("token"));
} catch (error) {
  console.error(`[chat.js] ${error.message}`);
  process.exit(2);
}

if (message && !token) {
  console.error(
    "[chat.js] sending a message requires --test-token=synthetic-...; "
    + "anonymous mode only inspects the welcome state",
  );
  process.exit(3);
}

if (process.env.RAPP_DOORMAN_BROWSER_TESTS !== "1") {
  console.error(
    "[chat.js] browser execution disabled; set RAPP_DOORMAN_BROWSER_TESTS=1 "
    + "only for an explicit fixture run",
  );
  console.error(
    `[chat.js] retained source ${HISTORICAL_SOURCE.commit} `
    + `(blob ${HISTORICAL_SOURCE.blob})`,
  );
  process.exit(78);
}

let chromium;
try {
  ({ chromium } = await import("playwright"));
} catch (error) {
  console.error(
    `[chat.js] supplied Playwright dependency is unavailable: ${error.message}`,
  );
  process.exit(2);
}

const headed = Boolean(arg("headed"));
const verbose = Boolean(arg("verbose"));
const slow = Boolean(arg("slow"));
const keepOpen = Boolean(arg("keep-open"));
const timeoutSec = Number.parseInt(arg("timeout") || "60", 10);

const browser = await chromium.launch({
  headless: !headed,
  slowMo: slow ? 100 : 0,
});
const context = await browser.newContext();
const page = await context.newPage();

if (verbose) {
  page.on("console", (messageEvent) => {
    console.error("[browser]", messageEvent.type(), messageEvent.text());
  });
  page.on("pageerror", (error) => {
    console.error("[pageerror]", error.message);
  });
  page.on("requestfailed", (request) => {
    console.error("[request-failed]", request.url(), request.failure()?.errorText);
  });
  page.on("response", (response) => {
    if (response.status() >= 400) {
      console.error("[http-error]", response.status(), response.url());
    }
  });
}

try {
  console.error(
    "[chat.js] →",
    target.href,
    token ? "(synthetic fixture auth)" : "(anonymous fixture)",
  );

  await page.goto(target.href, {
    waitUntil: "domcontentloaded",
    timeout: 30000,
  });
  ensureSameOrigin(page.url(), target.origin);

  if (token) {
    await page.evaluate((syntheticToken) => {
      localStorage.setItem("rapp_settings", JSON.stringify({
        ghuToken: syntheticToken,
      }));
    }, token);
    await page.reload({
      waitUntil: "domcontentloaded",
      timeout: 30000,
    });
    ensureSameOrigin(page.url(), target.origin);
  }

  try {
    await page.waitForFunction(() => {
      const system = document.querySelector(".msg.system");
      if (system && system.textContent && system.textContent.trim()) return true;
      const auth = document.querySelector("#auth-pane");
      return Boolean(auth && !auth.hidden);
    }, null, { timeout: 25000 });
  } catch {
    console.error("[chat.js] fixture did not finish rendering within 25s");
  }

  const badgeText = await page
    .locator("#private-indicator .private-badge")
    .first()
    .textContent()
    .catch(() => "");
  const welcomeMsg = await page
    .locator(".msg.system")
    .first()
    .textContent()
    .catch(() => "");

  console.error(
    "[chat.js] welcome:",
    welcomeMsg.replace(/\s+/g, " ").slice(0, 200),
  );
  if (badgeText) console.error("[chat.js] badge:", badgeText.trim());

  if (!message) {
    console.log(welcomeMsg);
  } else {
    const beforeSystemCount = await page.locator(".msg.system").count();
    const beforeAssistantCount = await page.locator(".msg.assistant").count();

    await page.fill("#chat-input", message);
    await page.click("#btn-send");

    try {
      await page.waitForFunction(
        (previous) => document.querySelectorAll(".msg.assistant").length > previous,
        beforeAssistantCount,
        { timeout: timeoutSec * 1000 },
      );
    } catch {
      console.error(
        `[chat.js] no assistant reply within ${timeoutSec}s; printing visible state`,
      );
    }

    const allAssistant = await page.locator(".msg.assistant").allTextContents();
    const allSystem = await page.locator(".msg.system").allTextContents();
    const lastReply = allAssistant[allAssistant.length - 1] || "(no reply)";
    const newSystemMessages = allSystem.slice(beforeSystemCount);

    console.log("\n=== you ===");
    console.log(message);
    console.log("\n=== " + (badgeText.trim() || "doorman") + " ===");
    console.log(lastReply);

    if (newSystemMessages.length > 0) {
      console.log("\n=== system trace (tool calls, memory saves) ===");
      for (const systemMessage of newSystemMessages) {
        if (systemMessage.trim()) {
          console.log("· " + systemMessage.replace(/\s+/g, " ").trim());
        }
      }
    }
  }
} finally {
  if (!keepOpen) {
    await browser.close();
  } else {
    console.error(
      "[chat.js] --keep-open: explicit fixture browser remains open; Ctrl+C to exit",
    );
  }
}
