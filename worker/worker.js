/* =====================================================================
 * Historical RAPP browser worker tombstone.
 *
 * The former OAuth, Copilot, model-catalog, and user proxy was retired.
 * Every request receives the same HTTP 410 response. This module performs
 * no routing, credential handling, cache access, or network activity.
 * ===================================================================== */

const RETIRED_BODY = JSON.stringify({
  error: 'gone',
  code: 'runtime-retired',
  status: 410,
  message: 'The retired RAPP browser worker is unavailable.',
  guidance: 'RAPP1_STATUS.md',
});

const RETIRED_HEADERS = Object.freeze({
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, HEAD, POST, PUT, PATCH, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  'Cache-Control': 'no-store',
  'Content-Type': 'application/json; charset=utf-8',
});

export default {
  fetch() {
    return new Response(RETIRED_BODY, {
      status: 410,
      headers: RETIRED_HEADERS,
    });
  },
};
