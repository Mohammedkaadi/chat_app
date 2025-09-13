const CACHE_NAME = 'star2chat-cache-v1';
const OFFLINE_URL = '/';

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll([
        '/',
        '/static/style-app.css',
        '/static/icons/icon-192.png',
        '/static/icons/icon-512.png'
      ]);
    })
  );
  self.skipWaiting();
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  event.respondWith(
    caches.match(event.request).then((r) => {
      return r || fetch(event.request).catch(()=>caches.match(OFFLINE_URL));
    })
  );
});
