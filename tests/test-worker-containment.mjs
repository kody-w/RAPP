#!/usr/bin/env node

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");

const WORKER_COMMIT = "4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6";
const WORKER_BLOB = "030437b4fd79cb4bf833a4c14a204f4c05ec2bd5";
const BROWSER_COMMIT = "6bd45f00981959a3fdfcc64fb32608533aae5021";

function read(relativePath) {
  return fs.readFileSync(path.join(root, relativePath), "utf8");
}

function readJson(relativePath) {
  return JSON.parse(read(relativePath));
}

function lineCount(source) {
  return source.split(/\r?\n/).length;
}

function assertNoMatches(source, patterns, label) {
  for (const pattern of patterns) {
    assert.doesNotMatch(source, pattern, `${label} must not match ${pattern}`);
  }
}

function run(command, args, extraEnv = {}) {
  const result = spawnSync(command, args, {
    cwd: root,
    encoding: "utf8",
    timeout: 5000,
    env: {
      PATH: process.env.PATH || "/usr/bin:/bin",
      HOME: path.join(root, ".browser-runtime-no-home"),
      ...extraEnv,
    },
  });
  assert.equal(result.error, undefined, `${command} must terminate without spawn error`);
  assert.equal(result.signal, null, `${command} must not be killed`);
  return {
    ...result,
    output: `${result.stdout || ""}${result.stderr || ""}`,
  };
}

const workerSource = read("worker/worker.js");
assert.ok(
  lineCount(workerSource) >= 288,
  "worker.js must retain at least the full historical implementation volume",
);
assert.match(workerSource, new RegExp(WORKER_COMMIT));
assert.match(workerSource, new RegExp(WORKER_BLOB));
for (const retainedRoute of [
  "/api/auth/token",
  "/api/auth/device",
  "/api/auth/device/poll",
  "/api/copilot/token",
  "/api/copilot/models",
  "/api/copilot/chat",
  "/api/models",
  "/api/user",
]) {
  assert.match(workerSource, new RegExp(retainedRoute.replaceAll("/", "\\/")));
}
for (const retainedHandler of [
  "handleOAuthToken",
  "handleDeviceStart",
  "handleDevicePoll",
  "handleCopilotToken",
  "handleCopilotModels",
  "handleCopilotChat",
  "handleModelCatalog",
  "handleUser",
]) {
  assert.match(workerSource, new RegExp(`function ${retainedHandler}\\b`));
}
assert.match(workerSource, /RAPP_BROWSER_RUNTIME_ENABLED/);
assert.match(workerSource, /RAPP_REVIEWED_BROWSER_RUNTIME/);
assert.match(workerSource, /DEFAULT_CAPABILITIES/);
assert.doesNotMatch(workerSource, /globalThis\.fetch/);
assert.doesNotMatch(workerSource, /\bcaches\.default\b/);

const encodedWorker = Buffer.from(workerSource).toString("base64");
const workerModule = await import(`data:text/javascript;base64,${encodedWorker}`);
const worker = workerModule.default;
assert.deepEqual(workerModule.HISTORICAL_SOURCE, {
  commit: WORKER_COMMIT,
  blob: WORKER_BLOB,
});
assert.deepEqual(workerModule.DEFAULT_CAPABILITIES, {
  oauthExchange: false,
  deviceFlow: false,
  copilotToken: false,
  copilotModels: false,
  copilotChat: false,
  catalog: false,
  user: false,
});

const originalFetch = globalThis.fetch;
let globalFetchCalls = 0;
globalThis.fetch = async () => {
  globalFetchCalls += 1;
  throw new Error("worker attempted global network access");
};

const defaultRequests = [
  ["POST", "/api/auth/token", { code: "synthetic-code" }],
  ["POST", "/api/auth/device", {}],
  ["POST", "/api/auth/device/poll", { device_code: "synthetic-code" }],
  ["GET", "/api/copilot/token"],
  ["GET", "/api/copilot/models"],
  ["POST", "/api/copilot/chat", { messages: [] }],
  ["GET", "/api/models"],
  ["GET", "/api/user"],
];

let reviewedBindingCalls = 0;
const reviewedBinding = {
  async fetch() {
    reviewedBindingCalls += 1;
    return new Response("{}", {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  },
};

try {
  for (const [method, route, body] of defaultRequests) {
    const init = {
      method,
      headers: {
        Authorization: "Bearer synthetic-worker-token",
        "Content-Type": "application/json",
        Origin: "http://localhost",
      },
    };
    if (body !== undefined) init.body = JSON.stringify(body);

    const response = await worker.fetch(
      new Request(`https://worker.example${route}`, init),
      {},
      {
        waitUntil() {
          throw new Error("disabled worker attempted background work");
        },
      },
    );
    assert.equal(response.status, 503, `${method} ${route} must fail closed`);
    const refusal = await response.json();
    assert.equal(refusal.error, "runtime-disabled");
    assert.equal(
      refusal.code,
      "explicit-reviewed-runtime-binding-required",
    );
    assert.equal(refusal.enabled, false);
  }

  const noFlag = await worker.fetch(
    new Request("https://worker.example/api/models"),
    { RAPP_REVIEWED_BROWSER_RUNTIME: reviewedBinding },
    {},
  );
  assert.equal(noFlag.status, 503, "binding without the false-by-default flag must refuse");

  const noBinding = await worker.fetch(
    new Request("https://worker.example/api/models"),
    {
      RAPP_BROWSER_RUNTIME_ENABLED: "true",
      RAPP_BROWSER_RUNTIME_CAPABILITIES: "catalog",
    },
    {},
  );
  assert.equal(noBinding.status, 503, "flag without the reviewed binding must refuse");

  const noCapability = await worker.fetch(
    new Request("https://worker.example/api/models"),
    {
      RAPP_BROWSER_RUNTIME_ENABLED: "true",
      RAPP_REVIEWED_BROWSER_RUNTIME: reviewedBinding,
    },
    {},
  );
  assert.equal(noCapability.status, 403, "binding without an explicit capability must refuse");
  assert.equal((await noCapability.json()).error, "capability-disabled");

  assert.equal(reviewedBindingCalls, 0, "all disabled combinations must avoid the binding");
  assert.equal(globalFetchCalls, 0, "disabled requests must avoid global fetch");

  const health = await worker.fetch(
    new Request("https://worker.example/healthz", {
      headers: { Origin: "http://localhost" },
    }),
    {},
    {},
  );
  assert.equal(health.status, 200);
  const healthBody = await health.json();
  assert.equal(healthBody.mode, "read-only");
  assert.equal(healthBody.runtime_enabled, false);
  assert.deepEqual(healthBody.historical_source, {
    commit: WORKER_COMMIT,
    blob: WORKER_BLOB,
  });
  assert.equal(health.headers.get("Access-Control-Allow-Origin"), "http://localhost");

  const arbitraryPreflight = await worker.fetch(
    new Request("https://worker.example/api/models", {
      method: "OPTIONS",
      headers: { Origin: "https://arbitrary.example" },
    }),
    {},
    {},
  );
  assert.equal(arbitraryPreflight.status, 204);
  assert.equal(
    arbitraryPreflight.headers.get("Access-Control-Allow-Origin"),
    null,
    "an arbitrary origin must not receive a CORS grant",
  );

  const upstreamCalls = [];
  const syntheticUpstream = {
    async fetch(input, init = {}) {
      upstreamCalls.push({
        input: String(input),
        method: init.method || "GET",
        headers: new Headers(init.headers),
        body: init.body,
        redirect: init.redirect,
      });
      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    },
  };

  const rejectedEndpointCalls = [];
  const rejectedEndpointBinding = {
    async fetch(input, init = {}) {
      rejectedEndpointCalls.push({
        input: String(input),
        headers: new Headers(init.headers),
      });
      return new Response(JSON.stringify({ leaked: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    },
  };
  const rejectedEndpoints = [
    ["suffix without label boundary", "https://notgithubcopilot.com"],
    ["approved suffix followed by attacker domain", "https://githubcopilot.com.evil.invalid"],
    ["userinfo", "https://user@api.individual.githubcopilot.com"],
    ["empty userinfo", "https://@api.individual.githubcopilot.com"],
    ["non-HTTPS", "http://api.individual.githubcopilot.com"],
    ["unexpected scheme", "ftp://api.individual.githubcopilot.com"],
    ["unexpected port", "https://api.individual.githubcopilot.com:444"],
    ["Unicode lookalike", "https://api.individual.gіthubcopilot.com"],
    ["Unicode hostname separator", "https://api.individual.githubcopilot。com"],
    ["punycode lookalike", "https://api.individual.xn--gthubcopilot-1ok.com"],
    ["percent-encoded hostname", "https://%61pi.individual.githubcopilot.com"],
    ["IPv4 literal", "https://127.0.0.1"],
    ["IPv6 literal", "https://[::1]"],
  ];
  const protectedCopilotRoutes = [
    {
      capability: "copilotModels",
      method: "GET",
      path: "/api/copilot/models",
    },
    {
      capability: "copilotChat",
      method: "POST",
      path: "/api/copilot/chat",
      body: JSON.stringify({ messages: [] }),
    },
  ];

  for (const route of protectedCopilotRoutes) {
    for (const [label, endpoint] of rejectedEndpoints) {
      const target = new URL(`https://worker.example${route.path}`);
      target.searchParams.set("endpoint", endpoint);
      const authorization = `Bearer rejected-endpoint-${route.capability}`;
      const init = {
        method: route.method,
        headers: {
          Authorization: authorization,
          "Content-Type": "application/json",
        },
      };
      if (route.body) init.body = route.body;

      const response = await worker.fetch(
        new Request(target, init),
        {
          RAPP_BROWSER_RUNTIME_ENABLED: true,
          RAPP_REVIEWED_BROWSER_RUNTIME: rejectedEndpointBinding,
          RAPP_BROWSER_RUNTIME_CAPABILITIES: {
            [route.capability]: true,
          },
        },
        {},
      );
      assert.equal(
        response.status,
        400,
        `${route.path} must reject ${label}`,
      );
      assert.equal((await response.json()).error, "invalid endpoint");
      assert.equal(
        rejectedEndpointCalls.length,
        0,
        `${route.path} must not call the binding for ${label}`,
      );
      assert.equal(
        rejectedEndpointCalls.some(
          (call) => call.headers.get("Authorization") === authorization,
        ),
        false,
        `${route.path} must not forward Authorization for ${label}`,
      );
    }
  }

  const catalog = await worker.fetch(
    new Request("https://worker.example/api/models", {
      headers: { Origin: "http://localhost" },
    }),
    {
      RAPP_BROWSER_RUNTIME_ENABLED: "true",
      RAPP_REVIEWED_BROWSER_RUNTIME: syntheticUpstream,
      RAPP_BROWSER_RUNTIME_CAPABILITIES: "catalog",
    },
    {},
  );
  assert.equal(catalog.status, 200);
  assert.equal(catalog.headers.get("X-RAPP-Cache"), "MISS");
  assert.equal(upstreamCalls[0].input, "https://models.github.ai/catalog/models");

  const chatBody = JSON.stringify({
    model: "synthetic-model",
    messages: [{ role: "user", content: "fixture" }],
  });
  const chat = await worker.fetch(
    new Request("https://worker.example/api/copilot/chat", {
      method: "POST",
      headers: {
        Authorization: "Bearer synthetic-worker-token",
        "Content-Type": "application/json",
        Origin: "http://localhost",
      },
      body: chatBody,
    }),
    {
      RAPP_BROWSER_RUNTIME_ENABLED: true,
      RAPP_REVIEWED_BROWSER_RUNTIME: syntheticUpstream,
      RAPP_BROWSER_RUNTIME_CAPABILITIES: { copilotChat: true },
    },
    {},
  );
  assert.equal(chat.status, 200);
  assert.equal(
    upstreamCalls[1].input,
    "https://api.individual.githubcopilot.com/chat/completions",
  );
  assert.equal(upstreamCalls[1].method, "POST");
  assert.equal(upstreamCalls[1].body, chatBody);
  assert.equal(upstreamCalls[1].redirect, "manual");
  assert.equal(
    upstreamCalls[1].headers.get("Authorization"),
    "Bearer synthetic-worker-token",
  );

  const businessModelsUrl = new URL(
    "https://worker.example/api/copilot/models",
  );
  businessModelsUrl.searchParams.set(
    "endpoint",
    "https://api.business.githubcopilot.com",
  );
  const businessModels = await worker.fetch(
    new Request(businessModelsUrl, {
      headers: { Authorization: "Bearer approved-business-fixture" },
    }),
    {
      RAPP_BROWSER_RUNTIME_ENABLED: true,
      RAPP_REVIEWED_BROWSER_RUNTIME: syntheticUpstream,
      RAPP_BROWSER_RUNTIME_CAPABILITIES: { copilotModels: true },
    },
    {},
  );
  assert.equal(businessModels.status, 200);
  const businessModelsCall = upstreamCalls.at(-1);
  assert.equal(
    businessModelsCall.input,
    "https://api.business.githubcopilot.com/models",
  );
  assert.equal(businessModelsCall.redirect, "manual");
  assert.equal(
    businessModelsCall.headers.get("Authorization"),
    "Bearer approved-business-fixture",
  );

  const redirectCalls = [];
  const redirectingBinding = {
    async fetch(input, init = {}) {
      redirectCalls.push({
        input: String(input),
        headers: new Headers(init.headers),
        redirect: init.redirect,
      });
      return new Response(null, {
        status: 302,
        headers: {
          Location: "https://notgithubcopilot.com/credential-capture",
        },
      });
    },
  };
  const redirectAuthorization = "Bearer redirect-secret-fixture";
  const redirectedModels = await worker.fetch(
    new Request("https://worker.example/api/copilot/models", {
      headers: { Authorization: redirectAuthorization },
    }),
    {
      RAPP_BROWSER_RUNTIME_ENABLED: true,
      RAPP_REVIEWED_BROWSER_RUNTIME: redirectingBinding,
      RAPP_BROWSER_RUNTIME_CAPABILITIES: { copilotModels: true },
    },
    {},
  );
  assert.equal(redirectedModels.status, 502);
  assert.equal(
    (await redirectedModels.json()).code,
    "approved-copilot-redirect-required",
  );
  assert.equal(
    redirectCalls.length,
    1,
    "an unapproved redirect target must never reach the binding",
  );
  assert.equal(
    redirectCalls[0].input,
    "https://api.individual.githubcopilot.com/models",
  );
  assert.equal(redirectCalls[0].redirect, "manual");
  assert.equal(
    redirectCalls.some(
      (call) => new URL(call.input).hostname === "notgithubcopilot.com",
    ),
    false,
    "the binding must never receive the unapproved redirect target",
  );
  assert.equal(
    redirectCalls.some(
      (call) => new URL(call.input).hostname === "notgithubcopilot.com"
        && call.headers.get("Authorization") === redirectAuthorization,
    ),
    false,
    "Authorization must never be forwarded to the unapproved redirect target",
  );

  const approvedRedirectCalls = [];
  const approvedRedirectBinding = {
    async fetch(input, init = {}) {
      approvedRedirectCalls.push({
        input: String(input),
        headers: new Headers(init.headers),
        redirect: init.redirect,
      });
      if (approvedRedirectCalls.length === 1) {
        return new Response(null, {
          status: 307,
          headers: {
            Location: "https://api.enterprise.githubcopilot.com/models",
          },
        });
      }
      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    },
  };
  const approvedRedirect = await worker.fetch(
    new Request("https://worker.example/api/copilot/models", {
      headers: { Authorization: "Bearer approved-redirect-fixture" },
    }),
    {
      RAPP_BROWSER_RUNTIME_ENABLED: true,
      RAPP_REVIEWED_BROWSER_RUNTIME: approvedRedirectBinding,
      RAPP_BROWSER_RUNTIME_CAPABILITIES: { copilotModels: true },
    },
    {},
  );
  assert.equal(approvedRedirect.status, 200);
  assert.deepEqual(
    approvedRedirectCalls.map((call) => call.input),
    [
      "https://api.individual.githubcopilot.com/models",
      "https://api.enterprise.githubcopilot.com/models",
    ],
  );
  assert.equal(
    approvedRedirectCalls.every(
      (call) => call.redirect === "manual"
        && call.headers.get("Authorization") === "Bearer approved-redirect-fixture",
    ),
    true,
    "approved redirects must be revalidated before credential forwarding",
  );

  assert.equal(globalFetchCalls, 0, "enabled tests must use only the reviewed binding");
} finally {
  globalThis.fetch = originalFetch;
}

const workerReadme = read("worker/README.md");
assert.match(workerReadme, new RegExp(WORKER_COMMIT));
assert.match(workerReadme, /false by default/i);
assert.match(workerReadme, /KERNEL_PIN\.json/);
assert.match(workerReadme, /rapp-installer@brainstem-v0\.6\.9/);
assertNoMatches(workerReadme, [
  /\bwrangler\s+(?:deploy|dev|login|secret|tail)\b/i,
  /\bnpx\s+wrangler\b/i,
], "worker README");

const wranglerConfig = read("worker/wrangler.toml");
assert.match(wranglerConfig, /RAPP_BROWSER_RUNTIME_ENABLED = "false"/);
assert.match(wranglerConfig, new RegExp(WORKER_COMMIT));
assert.doesNotMatch(wranglerConfig, /RAPP_REVIEWED_BROWSER_RUNTIME\s*=/);

const chatSource = read("tests/doorman/chat.js");
const smokeSource = read("tests/doorman/smoke.js");
assert.ok(lineCount(chatSource) >= 218, "chat.js must retain the full CLI/browser flow");
assert.ok(lineCount(smokeSource) >= 173, "smoke.js must retain the full fleet flow");
assert.match(chatSource, new RegExp(BROWSER_COMMIT));
assert.match(smokeSource, new RegExp(BROWSER_COMMIT));
for (const [source, label] of [
  [chatSource, "chat.js"],
  [smokeSource, "smoke.js"],
]) {
  assert.match(source, /await import\("playwright"\)/);
  assert.match(source, /chromium\.launch/);
  assert.match(source, /page\.goto/);
  assert.match(source, /localStorage\.setItem\("rapp_settings"/);
  assert.match(source, /ensureSameOrigin/);
  assertNoMatches(source, [
    /node:child_process/,
    /node:fs/,
    /node:os/,
    /\.copilot_token/,
    /\bgh\s+auth\s+token\b/i,
    /\bexecSync\b/,
    /\baddInitScript\b/,
  ], label);
}

const disabledChat = run(process.execPath, [
  path.join(root, "tests/doorman/chat.js"),
  "http://127.0.0.1:4173/doorman/",
]);
assert.equal(disabledChat.status, 78);
assert.match(disabledChat.output, /browser execution disabled/);

const disabledSyntheticChat = run(process.execPath, [
  path.join(root, "tests/doorman/chat.js"),
  "http://127.0.0.1:4173/doorman/",
  "--test-token=synthetic-doorman-fixture",
  "hello fixture",
]);
assert.equal(disabledSyntheticChat.status, 78);
assert.match(disabledSyntheticChat.output, /browser execution disabled/);
assert.doesNotMatch(disabledSyntheticChat.output, /synthetic-doorman-fixture/);

const arbitraryChat = run(process.execPath, [
  path.join(root, "tests/doorman/chat.js"),
  "https://arbitrary.example/doorman/",
  "--test-token=synthetic-doorman-fixture",
  "hello fixture",
]);
assert.equal(arbitraryChat.status, 2);
assert.match(arbitraryChat.output, /not localhost or listed/);

const realTokenSentinel = "ghp_real_token_must_be_rejected";
const realTokenChat = run(process.execPath, [
  path.join(root, "tests/doorman/chat.js"),
  "http://localhost:4173/doorman/",
  `--test-token=${realTokenSentinel}`,
  "hello fixture",
]);
assert.equal(realTokenChat.status, 2);
assert.match(realTokenChat.output, /real GitHub tokens are refused/);
assert.doesNotMatch(realTokenChat.output, new RegExp(realTokenSentinel));

const localFixtures = JSON.stringify([
  {
    slug: "local-fixture",
    url: "http://127.0.0.1:4173/doorman/",
    expect_in_welcome: ["Fixture"],
    test_message: "fixture",
    expect_in_reply: ["fixture"],
  },
]);
const disabledSmoke = run(
  process.execPath,
  [path.join(root, "tests/doorman/smoke.js"), "--anon"],
  { RAPP_DOORMAN_FIXTURES_JSON: localFixtures },
);
assert.equal(disabledSmoke.status, 78);
assert.match(disabledSmoke.output, /browser execution disabled/);

const doormanManifest = readJson("tests/doorman/package.json");
assert.equal(doormanManifest.private, true);
assert.equal(doormanManifest.dependencies.playwright, "^1.49.0");
assert.equal(doormanManifest.rappHistoricalSource.commit, BROWSER_COMMIT);
assert.equal(
  doormanManifest.rappSafetyDefaults.credentialDiscovery,
  false,
);

const tetherShell = read("tests/osi/L4a-tether-browser.sh");
const tetherSpec = read("tests/osi/browser/L4a-tether.spec.mjs");
const tetherFixture = read("tests/osi/browser/fixture.html");
assert.ok(lineCount(tetherShell) >= 59, "L4a shell must retain its substantive launcher");
assert.ok(lineCount(tetherSpec) >= 202, "L4a spec must retain the full browser test");
assert.ok(lineCount(tetherFixture) >= 156, "L4a fixture must retain its full peer logic");
assert.match(tetherShell, new RegExp(BROWSER_COMMIT));
assert.match(tetherSpec, new RegExp(BROWSER_COMMIT));
assert.match(tetherFixture, new RegExp(BROWSER_COMMIT));
assert.match(tetherSpec, /chromium\.launch/);
assert.match(tetherSpec, /serveFixture/);
assert.match(tetherSpec, /RAPP_PEERJS_BUNDLE/);
assert.match(tetherSpec, /RAPP_CHROMIUM_EXECUTABLE/);
assert.match(tetherFixture, /\/peerjs\.min\.js/);
assert.match(tetherFixture, /new window\.Peer/);
assert.match(tetherFixture, /rapp-tether\/1\.0/);
assert.doesNotMatch(tetherFixture, /unpkg\.com/i);
assertNoMatches(`${tetherShell}\n${tetherSpec}\n${tetherFixture}`, [
  /\bGH_TOKEN\b/,
  /\bGITHUB_TOKEN\b/,
  /\.copilot_token/,
  /\bAuthorization\b/,
], "OSI tether sources");
assertNoMatches(tetherShell, [
  /\bnpm\s+install\b/i,
  /\bnpx\b/i,
  /\bcurl\b/i,
  /\bwget\b/i,
], "OSI tether launcher");

const shellSkip = run("/bin/bash", [
  path.join(root, "tests/osi/L4a-tether-browser.sh"),
]);
assert.equal(shellSkip.status, 0);
assert.match(shellSkip.output, /^SKIP L4a browser tether:/m);

const specSkip = run(process.execPath, [
  path.join(root, "tests/osi/browser/L4a-tether.spec.mjs"),
], {
  RAPP_PLAYWRIGHT_MODULE: "definitely-not-installed",
});
assert.equal(specSkip.status, 0);
assert.match(specSkip.output, /^SKIP L4a browser tether:/m);

const missingDependencies = run(
  "/bin/bash",
  [path.join(root, "tests/osi/L4a-tether-browser.sh")],
  { RAPP_OSI_BROWSER_EXTERNAL: "1" },
);
assert.equal(missingDependencies.status, 2);
assert.match(missingDependencies.output, /RAPP_PEERJS_BUNDLE/);

const tetherManifest = readJson("tests/osi/browser/package.json");
assert.equal(tetherManifest.private, true);
assert.equal(tetherManifest.scripts.test, "node L4a-tether.spec.mjs");
assert.equal(tetherManifest.scripts["install-chromium"], undefined);
assert.equal(tetherManifest.rappHistoricalSource.commit, BROWSER_COMMIT);
assert.deepEqual(tetherManifest.rappSafetyDefaults, {
  externalExecutionEnabled: false,
  automaticInstall: false,
  automaticDownload: false,
  credentialUse: false,
});

console.log(
  `browser/runtime adaptation: ${defaultRequests.length} worker capabilities `
  + "fail closed; historical worker, Doorman, and L4a sources retained",
);
