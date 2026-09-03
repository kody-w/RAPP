/* =====================================================================
 * Historical RAPP browser worker, adapted as a fail-closed source artifact.
 *
 * Full route implementation restored from:
 *   commit 4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6
 *   git blob 030437b4fd79cb4bf833a4c14a204f4c05ec2bd5
 *
 * The historical OAuth, Copilot, catalog, and user routes remain executable,
 * but every capability is false by default. A route can reach an upstream
 * only when both RAPP_BROWSER_RUNTIME_ENABLED=true and the explicitly
 * reviewed RAPP_REVIEWED_BROWSER_RUNTIME fetch binding are supplied, and
 * that route's capability is named in RAPP_BROWSER_RUNTIME_CAPABILITIES.
 * No code path falls back to global fetch or a global cache.
 * ===================================================================== */

export const HISTORICAL_SOURCE = Object.freeze({
  commit: '4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6',
  blob: '030437b4fd79cb4bf833a4c14a204f4c05ec2bd5',
});

export const DEFAULT_CAPABILITIES = Object.freeze({
  oauthExchange: false,
  deviceFlow: false,
  copilotToken: false,
  copilotModels: false,
  copilotChat: false,
  catalog: false,
  user: false,
});

const RUNTIME_FLAG = 'RAPP_BROWSER_RUNTIME_ENABLED';
const RUNTIME_BINDING = 'RAPP_REVIEWED_BROWSER_RUNTIME';
const CAPABILITY_BINDING = 'RAPP_BROWSER_RUNTIME_CAPABILITIES';
const ORIGIN_BINDING = 'RAPP_BROWSER_ALLOWED_ORIGINS';
const CACHE_BINDING = 'RAPP_BROWSER_RUNTIME_CACHE';

const DEFAULT_ALLOWED_ORIGINS = Object.freeze([
  'http://localhost',
  'http://127.0.0.1',
]);

const COPILOT_CLIENT_ID = 'Iv1.b507a08c87ecfe98';

const UPSTREAMS = Object.freeze({
  oauthToken: 'https://github.com/login/oauth/access_token',
  deviceCode: 'https://github.com/login/device/code',
  copilotToken: 'https://api.github.com/copilot_internal/v2/token',
  copilotDefault: 'https://api.individual.githubcopilot.com',
  modelCatalog: 'https://models.github.ai/catalog/models',
  user: 'https://api.github.com/user',
});

const ROUTES = Object.freeze([
  { method: 'POST', path: '/api/auth/token', capability: 'oauthExchange', handler: handleOAuthToken },
  { method: 'POST', path: '/api/auth/device', capability: 'deviceFlow', handler: handleDeviceStart },
  { method: 'POST', path: '/api/auth/device/poll', capability: 'deviceFlow', handler: handleDevicePoll },
  { method: 'GET', path: '/api/copilot/token', capability: 'copilotToken', handler: handleCopilotToken },
  { method: 'GET', path: '/api/copilot/models', capability: 'copilotModels', handler: handleCopilotModels },
  { method: 'POST', path: '/api/copilot/chat', capability: 'copilotChat', handler: handleCopilotChat },
  { method: 'GET', path: '/api/models', capability: 'catalog', handler: handleModelCatalog },
  { method: 'GET', path: '/api/user', capability: 'user', handler: handleUser },
]);

function isTrue(value) {
  return value === true || value === 'true';
}

function normalizeOrigin(value) {
  if (typeof value !== 'string' || value.trim() === '') return null;
  try {
    const url = new URL(value.trim());
    if (!['http:', 'https:'].includes(url.protocol)) return null;
    return url.origin;
  } catch {
    return null;
  }
}

function parseAllowedOrigins(value) {
  const origins = new Set(DEFAULT_ALLOWED_ORIGINS);
  const candidates = Array.isArray(value)
    ? value
    : typeof value === 'string'
      ? value.split(',')
      : [];

  for (const candidate of candidates) {
    const origin = normalizeOrigin(candidate);
    if (origin) origins.add(origin);
  }
  return origins;
}

function isLoopbackOrigin(origin) {
  try {
    const hostname = new URL(origin).hostname;
    return ['localhost', '127.0.0.1', '[::1]'].includes(hostname);
  } catch {
    return false;
  }
}

function parseCapabilities(value) {
  const capabilities = { ...DEFAULT_CAPABILITIES };
  let requested = value;

  if (typeof requested === 'string') {
    const trimmed = requested.trim();
    if (!trimmed) return Object.freeze(capabilities);
    if (trimmed.startsWith('{')) {
      try {
        requested = JSON.parse(trimmed);
      } catch {
        return Object.freeze(capabilities);
      }
    } else {
      requested = Object.fromEntries(
        trimmed.split(',').map((name) => [name.trim(), true]),
      );
    }
  }

  if (!requested || typeof requested !== 'object') {
    return Object.freeze(capabilities);
  }

  for (const name of Object.keys(capabilities)) {
    capabilities[name] = requested[name] === true;
  }
  return Object.freeze(capabilities);
}

function resolveRuntime(env = {}) {
  const requested = isTrue(env[RUNTIME_FLAG]);
  const binding = env[RUNTIME_BINDING];
  const bindingReady = Boolean(binding && typeof binding.fetch === 'function');
  const cache = env[CACHE_BINDING];
  const cacheReady = Boolean(
    cache
    && typeof cache.match === 'function'
    && typeof cache.put === 'function',
  );

  return Object.freeze({
    requested,
    enabled: requested && bindingReady,
    binding: bindingReady ? binding : null,
    cache: cacheReady ? cache : null,
    capabilities: parseCapabilities(env[CAPABILITY_BINDING]),
    allowedOrigins: parseAllowedOrigins(env[ORIGIN_BINDING]),
  });
}

function corsHeaders(request, allowedOrigins) {
  const headers = {
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Max-Age': '86400',
    'Vary': 'Origin',
  };
  const origin = normalizeOrigin(request.headers.get('Origin'));
  if (origin && (isLoopbackOrigin(origin) || allowedOrigins.has(origin))) {
    headers['Access-Control-Allow-Origin'] = origin;
  }
  return headers;
}

function json(body, init = {}, request, runtime) {
  return new Response(JSON.stringify(body), {
    ...init,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'no-store',
      ...corsHeaders(request, runtime.allowedOrigins),
      ...(init.headers || {}),
    },
  });
}

async function passthroughText(upstream, request, runtime, extraHeaders = {}) {
  const text = await upstream.text();
  return new Response(text, {
    status: upstream.status,
    headers: {
      'Content-Type': upstream.headers.get('Content-Type') || 'application/json',
      'Cache-Control': 'no-store',
      ...corsHeaders(request, runtime.allowedOrigins),
      ...extraHeaders,
    },
  });
}

function runtimeRefusal(request, runtime, capability) {
  if (!runtime.enabled) {
    return json({
      error: 'runtime-disabled',
      code: 'explicit-reviewed-runtime-binding-required',
      capability,
      enabled: false,
      required_flag: `${RUNTIME_FLAG}=true`,
      required_binding: RUNTIME_BINDING,
      guidance: {
        kernel_pin: 'KERNEL_PIN.json',
        grail: 'kody-w/rapp-installer@brainstem-v0.6.9',
      },
    }, { status: 503 }, request, runtime);
  }

  if (!runtime.capabilities[capability]) {
    return json({
      error: 'capability-disabled',
      code: 'explicit-capability-required',
      capability,
      enabled: false,
      required_binding: CAPABILITY_BINDING,
    }, { status: 403 }, request, runtime);
  }

  return null;
}

function upstreamFetch(runtime, input, init) {
  return runtime.binding.fetch(input, init);
}

function requireAuthorization(request, runtime) {
  const authorization = request.headers.get('Authorization');
  if (!authorization) {
    return {
      response: json(
        { error: 'missing Authorization' },
        { status: 401 },
        request,
        runtime,
      ),
    };
  }
  return { authorization };
}

function copilotEndpoint(url, request, runtime) {
  const raw = url.searchParams.get('endpoint') || UPSTREAMS.copilotDefault;
  if (!/^https:\/\/[a-z0-9.-]*githubcopilot\.com\/?$/i.test(raw)) {
    return {
      response: json(
        { error: 'invalid endpoint' },
        { status: 400 },
        request,
        runtime,
      ),
    };
  }
  return { endpoint: raw.replace(/\/$/, '') };
}

async function handleOAuthToken({ request, env, runtime }) {
  try {
    const body = await request.json();
    if (!body.code) {
      return json({ error: 'missing code' }, { status: 400 }, request, runtime);
    }
    if (!env.GH_CLIENT_ID || !env.GH_CLIENT_SECRET) {
      return json(
        { error: 'oauth-binding-incomplete' },
        { status: 503 },
        request,
        runtime,
      );
    }
    const params = new URLSearchParams({
      client_id: env.GH_CLIENT_ID,
      client_secret: env.GH_CLIENT_SECRET,
      code: body.code,
    });
    if (body.redirect_uri) params.set('redirect_uri', body.redirect_uri);
    const upstream = await upstreamFetch(runtime, UPSTREAMS.oauthToken, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: params.toString(),
    });
    return passthroughText(upstream, request, runtime);
  } catch (error) {
    return json(
      { error: 'exchange_failed', detail: String(error) },
      { status: 502 },
      request,
      runtime,
    );
  }
}

async function handleDeviceStart({ request, env, runtime }) {
  try {
    const body = await request.json().catch(() => ({}));
    const clientId = body.client_id || env.GH_DEVICE_CLIENT_ID || COPILOT_CLIENT_ID;
    const scope = body.scope || 'read:user';
    const upstream = await upstreamFetch(runtime, UPSTREAMS.deviceCode, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: `client_id=${encodeURIComponent(clientId)}&scope=${encodeURIComponent(scope)}`,
    });
    return passthroughText(upstream, request, runtime);
  } catch (error) {
    return json(
      { error: 'device_start_failed', detail: String(error) },
      { status: 502 },
      request,
      runtime,
    );
  }
}

async function handleDevicePoll({ request, env, runtime }) {
  try {
    const body = await request.json();
    if (!body.device_code) {
      return json(
        { error: 'missing device_code' },
        { status: 400 },
        request,
        runtime,
      );
    }
    const clientId = body.client_id || env.GH_DEVICE_CLIENT_ID || COPILOT_CLIENT_ID;
    const upstream = await upstreamFetch(runtime, UPSTREAMS.oauthToken, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: [
        `client_id=${encodeURIComponent(clientId)}`,
        `device_code=${encodeURIComponent(body.device_code)}`,
        'grant_type=urn:ietf:params:oauth:grant-type:device_code',
      ].join('&'),
    });
    return passthroughText(upstream, request, runtime);
  } catch (error) {
    return json(
      { error: 'device_poll_failed', detail: String(error) },
      { status: 502 },
      request,
      runtime,
    );
  }
}

async function handleCopilotToken({ request, runtime }) {
  const auth = requireAuthorization(request, runtime);
  if (auth.response) return auth.response;

  const raw = auth.authorization.replace(/^(Bearer|token)\s+/i, '');
  const upstreamAuth = raw.startsWith('ghu_') ? `token ${raw}` : `Bearer ${raw}`;
  const upstream = await upstreamFetch(runtime, UPSTREAMS.copilotToken, {
    method: 'GET',
    headers: {
      'Authorization': upstreamAuth,
      'Accept': 'application/json',
      'Editor-Version': 'vscode/1.95.0',
      'Editor-Plugin-Version': 'copilot/1.0.0',
      'User-Agent': 'GitHubCopilotChat/0.22.2024',
    },
  });
  return passthroughText(upstream, request, runtime);
}

async function handleCopilotModels({ request, runtime, url }) {
  const auth = requireAuthorization(request, runtime);
  if (auth.response) return auth.response;
  const endpoint = copilotEndpoint(url, request, runtime);
  if (endpoint.response) return endpoint.response;

  const upstream = await upstreamFetch(runtime, `${endpoint.endpoint}/models`, {
    method: 'GET',
    headers: {
      'Authorization': auth.authorization,
      'Accept': 'application/json',
      'Editor-Version': 'vscode/1.95.0',
      'Editor-Plugin-Version': 'copilot/1.0.0',
      'Copilot-Integration-Id': 'vscode-chat',
      'User-Agent': 'GitHubCopilotChat/0.22.2024',
    },
  });
  return passthroughText(upstream, request, runtime);
}

async function handleCopilotChat({ request, runtime, url }) {
  const auth = requireAuthorization(request, runtime);
  if (auth.response) return auth.response;
  const endpoint = copilotEndpoint(url, request, runtime);
  if (endpoint.response) return endpoint.response;

  const body = await request.text();
  const upstream = await upstreamFetch(
    runtime,
    `${endpoint.endpoint}/chat/completions`,
    {
      method: 'POST',
      headers: {
        'Authorization': auth.authorization,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Editor-Version': 'vscode/1.95.0',
        'Editor-Plugin-Version': 'copilot/1.0.0',
        'Copilot-Integration-Id': 'vscode-chat',
        'User-Agent': 'GitHubCopilotChat/0.22.2024',
      },
      body,
    },
  );
  return passthroughText(upstream, request, runtime);
}

async function handleModelCatalog({ request, runtime, context }) {
  const cacheKey = new Request('https://rapp-auth-cache.invalid/api/models/v1');
  if (runtime.cache) {
    const cached = await runtime.cache.match(cacheKey);
    if (cached) {
      const headers = new Headers(cached.headers);
      Object.entries(corsHeaders(request, runtime.allowedOrigins))
        .forEach(([name, value]) => headers.set(name, value));
      headers.set('X-RAPP-Cache', 'HIT');
      return new Response(cached.body, {
        status: cached.status,
        headers,
      });
    }
  }

  try {
    const upstream = await upstreamFetch(runtime, UPSTREAMS.modelCatalog, {
      headers: {
        'Accept': 'application/json',
        'User-Agent': 'rapp-auth-worker/1',
      },
    });
    const body = await upstream.text();
    if (upstream.ok && runtime.cache) {
      const cacheResponse = new Response(body, {
        status: upstream.status,
        headers: {
          'Content-Type': 'application/json',
          'Cache-Control': 'public, max-age=3600',
        },
      });
      context?.waitUntil?.(runtime.cache.put(cacheKey, cacheResponse.clone()));
    }
    return new Response(body, {
      status: upstream.status,
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'public, max-age=3600',
        'X-RAPP-Cache': upstream.ok ? 'MISS' : 'BYPASS',
        ...corsHeaders(request, runtime.allowedOrigins),
      },
    });
  } catch (error) {
    return json(
      { error: 'upstream_failed', detail: String(error) },
      { status: 502 },
      request,
      runtime,
    );
  }
}

async function handleUser({ request, runtime }) {
  const auth = requireAuthorization(request, runtime);
  if (auth.response) return auth.response;
  const upstream = await upstreamFetch(runtime, UPSTREAMS.user, {
    headers: {
      'Authorization': auth.authorization,
      'Accept': 'application/json',
      'User-Agent': 'rapp-auth-worker',
    },
  });
  return passthroughText(upstream, request, runtime);
}

export default {
  async fetch(request, env = {}, context = {}) {
    const runtime = resolveRuntime(env);
    const url = new URL(request.url);

    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: corsHeaders(request, runtime.allowedOrigins),
      });
    }

    if (url.pathname === '/healthz') {
      return json({
        ok: true,
        mode: 'read-only',
        runtime_enabled: runtime.enabled,
        runtime_requested: runtime.requested,
        capabilities: runtime.capabilities,
        historical_source: HISTORICAL_SOURCE,
        guidance: {
          kernel_pin: 'KERNEL_PIN.json',
          grail: 'kody-w/rapp-installer@brainstem-v0.6.9',
        },
      }, { status: 200 }, request, runtime);
    }

    const route = ROUTES.find(
      (candidate) => candidate.method === request.method
        && candidate.path === url.pathname,
    );
    if (!route) {
      return json(
        { error: 'not_found', path: url.pathname },
        { status: 404 },
        request,
        runtime,
      );
    }

    const refusal = runtimeRefusal(request, runtime, route.capability);
    if (refusal) return refusal;

    return route.handler({
      request,
      env,
      runtime,
      context,
      url,
    });
  },
};
