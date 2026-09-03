#!/usr/bin/env node
//
// smoke.js — sequential browser checks across explicit Doorman fixtures.
//
// Historical source restored from:
//   commit 6bd45f00981959a3fdfcc64fb32608533aae5021
//   git blob 56e95e0cd380f7fad7f9d53aa59df5909ae621e5
//
// The historical fleet and browser assertions remain executable. Browser
// startup is false by default, credentials are never discovered, and token
// storage occurs only after an exact fixture-origin check.

const HISTORICAL_SOURCE = Object.freeze({
  commit: "6bd45f00981959a3fdfcc64fb32608533aae5021",
  blob: "56e95e0cd380f7fad7f9d53aa59df5909ae621e5",
});

const HISTORICAL_FLEET = Object.freeze([
  {
    slug: "heimdall",
    url: "https://kody-w.github.io/heimdall/doorman/",
    expect_in_welcome: ["Heimdall"],
    test_message: "In one sentence — who are you?",
    expect_in_reply: ["Heimdall", "Bifrost"],
  },
  {
    slug: "kody-twin",
    url: "https://kody-w.github.io/kody-twin/doorman/",
    expect_in_welcome: ["Kody Wildfeuer"],
    test_message: "What's the bond cycle?",
    expect_in_reply: ["bond", "egg", "kernel"],
  },
  {
    slug: "pkstop-the-bean",
    url: "https://kody-w.github.io/pkstop-the-bean/doorman/",
    expect_in_welcome: ["Cloud Gate", "Bean"],
    test_message: "Where are you?",
    expect_in_reply: ["Chicago", "Millennium"],
  },
]);

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
    throw new Error(`invalid fixture URL: ${value}`);
  }
  if (target.username || target.password) {
    throw new Error(`fixture URL must not contain credentials: ${target.origin}`);
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

function loadFleet() {
  const configured = process.env.RAPP_DOORMAN_FIXTURES_JSON;
  if (!configured) return HISTORICAL_FLEET;
  let parsed;
  try {
    parsed = JSON.parse(configured);
  } catch (error) {
    throw new Error(`RAPP_DOORMAN_FIXTURES_JSON is invalid JSON: ${error.message}`);
  }
  if (!Array.isArray(parsed) || parsed.length === 0) {
    throw new Error("RAPP_DOORMAN_FIXTURES_JSON must be a non-empty array");
  }
  return parsed;
}

function ensureSameOrigin(actualUrl, expectedOrigin) {
  const actual = normalizeOrigin(actualUrl);
  if (actual !== expectedOrigin) {
    throw new Error(
      `fixture navigated to ${actual || "an invalid origin"}; refusing storage injection`,
    );
  }
}

const onlySlug = arg("only");
const anonymousOnly = Boolean(arg("anon"));
const verbose = Boolean(arg("verbose"));

let token;
let fleet;
try {
  token = requireSyntheticToken(arg("test-token") || arg("token"));
  if (!anonymousOnly && !token) {
    throw new Error(
      "authenticated fixture checks require --test-token=synthetic-...",
    );
  }
  fleet = loadFleet()
    .filter((scenario) => !onlySlug || scenario.slug === onlySlug)
    .map((scenario) => ({
      ...scenario,
      target: requireAllowedFixtureUrl(scenario.url),
    }));
} catch (error) {
  console.error(`[smoke] ${error.message}`);
  process.exit(2);
}

if (!fleet.length) {
  console.error("[smoke] no scenarios match --only=" + onlySlug);
  process.exit(2);
}

if (process.env.RAPP_DOORMAN_BROWSER_TESTS !== "1") {
  console.error(
    "[smoke] browser execution disabled; set RAPP_DOORMAN_BROWSER_TESTS=1 "
    + "only for explicit allowlisted fixtures",
  );
  console.error(
    `[smoke] retained ${fleet.length} scenario(s) from source `
    + `${HISTORICAL_SOURCE.commit} (blob ${HISTORICAL_SOURCE.blob})`,
  );
  process.exit(78);
}

let chromium;
try {
  ({ chromium } = await import("playwright"));
} catch (error) {
  console.error(
    `[smoke] supplied Playwright dependency is unavailable: ${error.message}`,
  );
  process.exit(2);
}

const browser = await chromium.launch({ headless: true });
let passed = 0;
let failed = 0;
const failures = [];

for (const scenario of fleet) {
  const tag = `${String(scenario.slug).padEnd(28)}`;
  process.stdout.write(`▸ ${tag}  `);

  const context = await browser.newContext();
  const page = await context.newPage();

  if (verbose) {
    page.on("console", (message) => {
      console.error("\n  [browser]", message.type(), message.text());
    });
    page.on("pageerror", (error) => {
      console.error("\n  [pageerror]", error.message);
    });
  }

  let ok = true;
  let detail = "";
  try {
    await page.goto(scenario.target.href, {
      waitUntil: "domcontentloaded",
      timeout: 25000,
    });
    ensureSameOrigin(page.url(), scenario.target.origin);

    if (token && !anonymousOnly) {
      await page.evaluate((syntheticToken) => {
        localStorage.setItem("rapp_settings", JSON.stringify({
          ghuToken: syntheticToken,
        }));
      }, token);
      await page.reload({
        waitUntil: "domcontentloaded",
        timeout: 25000,
      });
      ensureSameOrigin(page.url(), scenario.target.origin);
    }

    await page.waitForFunction(() => {
      const system = document.querySelector(".msg.system");
      if (system && system.textContent && system.textContent.trim()) return true;
      const auth = document.querySelector("#auth-pane");
      return Boolean(auth && !auth.hidden);
    }, null, { timeout: 25000 });

    let welcomeOk = false;
    let welcome = "";
    const deadline = Date.now() + 30000;
    while (Date.now() < deadline && !welcomeOk) {
      const all = await page.locator(".msg.system").allTextContents();
      welcome = all.join(" │ ");
      welcomeOk = scenario.expect_in_welcome.some((expected) => (
        all.some((message) => message.includes(expected))
      ));
      if (!welcomeOk) await page.waitForTimeout(500);
    }

    if (!welcomeOk) {
      ok = false;
      detail = (
        `welcome missing any of [${scenario.expect_in_welcome.join(",")}] `
        + `— got: ${welcome.slice(0, 200)}`
      );
    }

    if (ok && token && !anonymousOnly && scenario.test_message) {
      const beforeAssistant = await page.locator(".msg.assistant").count();
      await page.fill("#chat-input", scenario.test_message);
      await page.click("#btn-send");
      try {
        await page.waitForFunction(
          (previous) => document.querySelectorAll(".msg.assistant").length > previous,
          beforeAssistant,
          { timeout: 60000 },
        );
      } catch {
        ok = false;
        detail = "no assistant reply within 60s";
      }

      if (ok) {
        const replies = await page.locator(".msg.assistant").allTextContents();
        const reply = replies[replies.length - 1] || "";
        const replyOk = scenario.expect_in_reply.some((expected) => (
          reply.toLowerCase().includes(expected.toLowerCase())
        ));
        if (!replyOk) {
          ok = false;
          detail = (
            `reply missing any of [${scenario.expect_in_reply.join(",")}] `
            + `— got: ${reply.slice(0, 120)}`
          );
        }
      }
    }
  } catch (error) {
    ok = false;
    detail = "exception: " + (error.message || String(error)).slice(0, 200);
  }

  if (ok) {
    console.log("PASS");
    passed += 1;
  } else {
    console.log("FAIL  — " + detail);
    failed += 1;
    failures.push({ slug: scenario.slug, detail });
  }

  await context.close();
}

await browser.close();

console.log("");
console.log(`──────────  ${passed} passed, ${failed} failed  ──────────`);
if (failed > 0) {
  console.log("\nFailures:");
  for (const failure of failures) {
    console.log(`  • ${failure.slug}: ${failure.detail}`);
  }
  process.exit(1);
}
