/* =====================================================================
 * rapp-auth — Cloudflare Worker for the RAPP Virtual Brainstem.
 *
 * Two responsibilities:
 *   1. OAuth code-for-token exchange — the only step that requires the
 *      client_secret, which can't live in the browser.
 *   2. Catalog proxy — adds CORS headers to https://models.github.ai/
 *      so the browser can fetch the live model list (the upstream
 *      doesn't send Access-Control-Allow-Origin for kody-w.github.io).
 *
 * Endpoints:
 *   POST /api/auth/token   { code, redirect_uri? }   → { access_token }
 *   GET  /api/models       (no auth required)        → upstream catalog JSON
 *   GET  /api/user         (Authorization: Bearer …) → upstream /user JSON
 *   GET  /healthz                                    → "ok"
 *
 * Required secrets (set via `wrangler secret put`):
 *   GH_CLIENT_ID       — the OAuth App client id
 *   GH_CLIENT_SECRET   — the OAuth App client secret
 *
 * Deploy:  npx wrangler deploy
 * ===================================================================== */

const ALLOWED_ORIGINS = [
  'https://kody-w.github.io',
  'http://localhost',
  'http://127.0.0.1',
];

function corsHeaders(req) {
  const origin = req.headers.get('Origin') || '';
  const allow = ALLOWED_ORIGINS.some(o => origin === o || origin.startsWith(o + ':') || origin.startsWith(o + '/'));
  return {
    'Access-Control-Allow-Origin': allow ? origin : ALLOWED_ORIGINS[0],
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Max-Age': '86400',
    'Vary': 'Origin',
  };
}

function json(body, init = {}, req) {
  return new Response(JSON.stringify(body), {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...corsHeaders(req),
      ...(init.headers || {}),
    },
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders(request) });
    }

    if (url.pathname === '/healthz') {
      return new Response('ok', { status: 200, headers: corsHeaders(request) });
    }

    // POST /api/auth/token — exchange the OAuth `code` for an access_token
    if (url.pathname === '/api/auth/token' && request.method === 'POST') {
      try {
        const body = await request.json();
        const code = body.code;
        if (!code) return json({ error: 'missing code' }, { status: 400 }, request);
        const params = new URLSearchParams({
          client_id: env.GH_CLIENT_ID,
          client_secret: env.GH_CLIENT_SECRET,
          code,
        });
        if (body.redirect_uri) params.set('redirect_uri', body.redirect_uri);
        const ghResp = await fetch('https://github.com/login/oauth/access_token', {
          method: 'POST',
          headers: { 'Accept': 'application/json', 'Content-Type': 'application/x-www-form-urlencoded' },
          body: params.toString(),
        });
        const data = await ghResp.json();
        return json(data, { status: ghResp.status }, request);
      } catch (e) {
        return json({ error: 'exchange_failed', detail: String(e) }, { status: 500 }, request);
      }
    }

    // GET /api/models — proxy the public GitHub Models catalog with CORS
    if (url.pathname === '/api/models' && request.method === 'GET') {
      try {
        const upstream = await fetch('https://models.github.ai/catalog/models', {
          headers: { 'Accept': 'application/json' },
          cf: { cacheTtl: 300 },   // edge-cache 5 min — catalog rarely changes
        });
        const text = await upstream.text();
        return new Response(text, {
          status: upstream.status,
          headers: {
            'Content-Type': 'application/json',
            'Cache-Control': 'public, max-age=300',
            ...corsHeaders(request),
          },
        });
      } catch (e) {
        return json({ error: 'upstream_failed', detail: String(e) }, { status: 502 }, request);
      }
    }

    // GET /api/user — proxy github.com/user with CORS (browser can call directly,
    // but routing through the worker lets us cache and gives one consistent surface).
    if (url.pathname === '/api/user' && request.method === 'GET') {
      const auth = request.headers.get('Authorization');
      if (!auth) return json({ error: 'unauthorized' }, { status: 401 }, request);
      const upstream = await fetch('https://api.github.com/user', {
        headers: { 'Authorization': auth, 'Accept': 'application/json', 'User-Agent': 'rapp-auth-worker' },
      });
      const text = await upstream.text();
      return new Response(text, {
        status: upstream.status,
        headers: {
          'Content-Type': 'application/json',
          ...corsHeaders(request),
        },
      });
    }

    return json({ error: 'not_found', path: url.pathname }, { status: 404 }, request);
  },
};
