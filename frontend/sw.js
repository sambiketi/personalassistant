const CACHE_NAME = 'focus-agent-v3';
const urlsToCache = [
  '/', '/index.html', '/css/style.css', '/js/app.js', '/js/agent.js',
  '/manifest.json', '/icons/icon-192.png', '/icons/icon-512.png',
];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache)));
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))))
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  const { request } = event;

  // Network-first for API calls so data stays fresh; fall back to cache offline.
  if (request.url.includes('/api/')) {
    event.respondWith(
      fetch(request)
        .then(response => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
          return response;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // Cache-first for static assets, with offline fallback to the app shell.
  event.respondWith(
    caches.match(request).then(response => response || fetch(request).catch(() => caches.match('/index.html')))
  );
});
