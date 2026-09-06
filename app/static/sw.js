// Sauti Pesa — service worker
// Caches the app shell so it installs cleanly and opens instantly,
// even with a weak connection. Does NOT cache API calls — once the real
// backend is connected, /process-voice and /confirm-transaction should
// always go to the network, not the cache.

const CACHE_NAME = "sauti-pesa-v1";
const APP_SHELL = [
  "./index.html",
  "./manifest.json",
  "./icon-192.png",
  "./icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(names.filter((n) => n !== CACHE_NAME).map((n) => caches.delete(n)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // Never cache API calls — always hit the network once the backend exists
  if (url.pathname.startsWith("/process-voice") || url.pathname.startsWith("/confirm-transaction")) {
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});