// Service worker for Club Membership.
// Pages are dynamic and login-protected, so they are NEVER cached:
// the network always wins, and an offline page is shown if it fails.
// Only static assets (css/js/icons) are cached for speed.
const VERSION = "v1";
const STATIC_CACHE = `clubhouse-static-${VERSION}`;
const PRECACHE = [
  "/offline",
  "/static/style.css",
  "/static/theme.js",
  "/static/tabs.js",
  "/static/pwa.js",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== STATIC_CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;            // never touch form posts
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;  // let fonts etc. go to network

  // Page navigations: network only, offline page as fallback
  if (req.mode === "navigate") {
    event.respondWith(fetch(req).catch(() => caches.match("/offline")));
    return;
  }

  // Static assets: serve cached copy, refresh in background
  if (url.pathname.startsWith("/static/")) {
    event.respondWith(
      caches.open(STATIC_CACHE).then(async (cache) => {
        const cached = await cache.match(req);
        const fresh = fetch(req).then((res) => {
          if (res.ok) cache.put(req, res.clone());
          return res;
        }).catch(() => cached);
        return cached || fresh;
      })
    );
  }
});
