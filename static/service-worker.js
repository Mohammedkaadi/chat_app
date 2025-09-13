const CACHE_NAME = "star2chat-v2";
const urlsToCache = [
  "/",
  "/static/style-app.css",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png"
];

// Install
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(urlsToCache);
    })
  );
});

// Activate
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cache) => {
          if (cache !== CACHE_NAME) {
            return caches.delete(cache);
          }
        })
      );
    })
  );
});

// Fetch
self.addEventListener("fetch", (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    })
  );
});

// إشعار صوتي عند استقبال رسالة جديدة
self.addEventListener("push", (event) => {
  const data = event.data ? event.data.text() : "📩 رسالة جديدة";
  event.waitUntil(
    self.registration.showNotification("Star2Chat", {
      body: data,
      icon: "/static/icons/icon-192.png",
      badge: "/static/icons/icon-192.png"
    })
  );
});
