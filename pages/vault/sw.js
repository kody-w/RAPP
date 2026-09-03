// One-release retirement worker for the former RAPP Vault PWA.
//
// Existing registrations still request this URL even though the current page
// no longer registers a worker. Publishing this inert replacement lets those
// browsers delete the old cache, unregister the worker, and reload onto the
// current network-served historical viewer.

const RETIRED_CACHE_PREFIX = 'rapp-vault-';

self.addEventListener('install', (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(
      names
        .filter((name) => name.startsWith(RETIRED_CACHE_PREFIX))
        .map((name) => caches.delete(name)),
    );
    await self.registration.unregister();
    const windows = await self.clients.matchAll({
      type: 'window',
      includeUncontrolled: true,
    });
    await Promise.all(
      windows.map((client) => client.navigate(client.url).catch(() => null)),
    );
  })());
});
