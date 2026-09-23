// Network-first so reviewers always get fresh code; the cache is only a fallback when offline.
const CACHE = 'visiontech-shell-v1';
const SHELL = ['./', 'index.html', 'css/base.css', 'css/workspace.css', 'css/documents.css', 'js/domain.js', 'js/storage.js', 'js/ui.js', 'js/workplans.js', 'js/people.js', 'js/operations.js', 'js/geo.js', 'js/documents.js', 'js/app.js', 'js/offline.js'];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', event => {
  // Only clean up this app's own caches; other apps may share the origin.
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k.startsWith('visiontech-shell-') && k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET' || new URL(request.url).origin !== self.location.origin) return;
  event.respondWith(fetch(request).then(response => {
    if (response.ok) { const copy = response.clone(); caches.open(CACHE).then(cache => cache.put(request, copy)); }
    return response;
  }).catch(() => caches.match(request, { ignoreSearch: true }).then(hit => hit || (request.mode === 'navigate' ? caches.match('index.html') : Response.error()))));
});
