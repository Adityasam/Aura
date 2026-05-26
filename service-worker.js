const CACHE_NAME = "Aura-V3.4";
const urlsToCache = [
  "/",
  "/static/css/all.min.css",
  "/static/manifest.json",
  "/static/css/myToastr.css",
  "/static/js/myToastr.js",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/icons/pause.png",
  "/static/icons/play.webp",
  "/static/img/bg.png",
  "/static/img/loader.gif",
  "/static/img/page_loader.gif",
  "https://fonts.googleapis.com/css2?family=Raleway:ital,wght@0,100..900;1,100..900&display=swap",
  "https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css",
  "https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js",
  "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/7.0.1/css/all.min.css"
];

// Install event - cache static files
self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(urlsToCache);
    })
  );
  console.log("Service Worker installed");
});

// Activate event - cleanup old caches
self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames
          .filter(name => name !== CACHE_NAME)
          .map(name => caches.delete(name))
      );
    })
  );
  console.log("Service Worker activated");
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Return from cache if available
        if (response) {
          return response;
        }
        // Otherwise, fetch from network
        return fetch(event.request)
          .then(response => {
            // Don't cache non-successful responses
            if (!response || response.status !== 200 || response.type === 'error') {
              return response;
            }
            // Clone and cache the successful response
            const copy = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(event.request, copy));
            return response;
          });
      })
      .catch(() => {
        // Return a custom offline response if needed
        console.log('Fetch failed for:', event.request.url);
      })
  );
});
