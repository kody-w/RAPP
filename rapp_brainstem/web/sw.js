// rapp_brainstem/web/sw.js — service worker for the Brainstem desktop PWA.
//
// Strategy:
//   - Precache the static UI shell on install.
//   - Never cache /chat or /api/* — those need fresh server responses.
//   - For everything else under same-origin: cache-first with network fallback,
//     so the UI loads instantly even with flaky connectivity. The brainstem
//     itself still needs to be running on :7071 for chat to work; the SW only
//     promises that the *UI shell* is offline-resilient.

const CACHE_VERSION = 'rapp-brainstem-v1';
const SHELL = [
  './',
  './index.html',
  './rapp.js',
  './manifest.webmanifest',
  './icon-192.svg',
  './icon-512.svg',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) =>
      Promise.all(SHELL.map((url) =>
        cache.add(url).catch((err) => console.warn('precache miss', url, err))
      ))
    )
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Never cache the live chat surface or any API call.
  if (url.pathname.startsWith('/chat') ||
      url.pathname.startsWith('/api/') ||
      url.pathname.startsWith('/login') ||
      url.pathname.startsWith('/agents/files') ||
      url.pathname.startsWith('/voice/') ||
      url.pathname.startsWith('/twin/') ||
      url.pathname.startsWith('/models/')) {
    return;
  }

  // Same-origin shell assets: cache-first with network fallback.
  if (url.origin === self.location.origin) {
    event.respondWith(
      caches.match(event.request).then((cached) => {
        if (cached) return cached;
        return fetch(event.request).catch(() => {
          if (event.request.mode === 'navigate') return caches.match('./index.html');
          return new Response('offline', { status: 503 });
        });
      })
    );
  }
});
